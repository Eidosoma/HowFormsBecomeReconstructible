from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_commitment_robustness_detached as detached


class DetachedRobustnessTests(unittest.TestCase):
    def test_atomic_status_and_stale_running_state(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            detached.write_status(path / "status.json", dict(phase="runner", heartbeat_epoch=time.time() - 100))
            self.assertTrue(detached.status(path)["heartbeat_stale"])
            self.assertFalse((path / "status.json.tmp").exists())
            detached.write_status(path / "status.json", dict(phase="complete", heartbeat_epoch=time.time() - 100))
            self.assertFalse(detached.status(path)["heartbeat_stale"])

    def test_run_path_only_accepted_inside_expected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = root / "job"
            job.mkdir()
            with patch.object(detached, "ROOT", root):
                self.assertIsNone(detached.discover_run(job))
                (job / "runner.log").write_text("Run artifacts: /tmp/unrelated\n")
                with self.assertRaises(ValueError): detached.discover_run(job)
                correct = root / "runs/commitment-robustness-example"
                (job / "runner.log").write_text(f"Run artifacts: {correct}\n")
                self.assertEqual(detached.discover_run(job), correct)

    def test_child_persists_log_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "child.log"
            rc = detached.run_child([sys.executable, "-c", "print('child completed'); raise SystemExit(7)"], log, 10, lambda pid: None)
            self.assertEqual(rc, 7)
            self.assertIn("child completed", log.read_text())

    def test_timeout_kills_only_created_child_and_reports_124(self):
        with tempfile.TemporaryDirectory() as temp:
            pids = []
            rc = detached.run_child([sys.executable, "-c", "import time; time.sleep(60)"],
                Path(temp) / "child.log", .02, lambda pid: pids.append(pid))
            self.assertEqual(rc, 124)
            self.assertTrue(pids)
            with self.assertRaises(ProcessLookupError): os.kill(pids[0], 0)

    def fixture(self, temp):
        root = Path(temp)
        job = root / "runs/jobs/test"
        job.mkdir(parents=True)
        detached.write_status(job / "launch.json", dict(probe=False, hashes_sha256={}))
        detached.write_status(job / "status.json", dict(phase="launching", heartbeat_epoch=time.time()))
        fd = os.open(root / "lock", os.O_CREAT | os.O_RDWR, 0o600)
        return root, job, fd

    def test_runner_failure_records_exit_and_never_runs_audit_or_retries(self):
        with tempfile.TemporaryDirectory() as temp:
            root, job, fd = self.fixture(temp)
            with patch.object(detached, "ROOT", root), patch.object(detached.signal, "signal"), patch.object(
                    detached, "run_child", return_value=7) as runner, redirect_stderr(io.StringIO()):
                self.assertEqual(detached.supervise(job, fd), 1)
            runner.assert_called_once()
            status = detached.status(job)
            self.assertEqual(status["runner_exit_code"], 7)
            self.assertEqual(status["phase"], "failed")
            self.assertEqual(status["exit_code"], 1)
            self.assertNotIn("audit_exit_code", status)

    def test_changed_launch_file_fails_before_child(self):
        with tempfile.TemporaryDirectory() as temp:
            root, job, fd = self.fixture(temp)
            (root / "example").write_text("changed")
            detached.write_status(job / "launch.json", dict(probe=False, hashes_sha256={"example": "wrong"}))
            with patch.object(detached, "ROOT", root), patch.object(detached.signal, "signal"), patch.object(
                    detached, "run_child") as runner, redirect_stderr(io.StringIO()):
                self.assertEqual(detached.supervise(job, fd), 1)
            runner.assert_not_called()

    def test_success_runs_audit_records_gate_and_does_not_launch_next_stage(self):
        for gate in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root, job, fd = self.fixture(temp)
                run = root / "runs/commitment-robustness-example"
                run.mkdir()
                calls = []

                def child(command, logfile, timeout, update):
                    calls.append((command, timeout))
                    if len(calls) == 1:
                        logfile.write_text(f"Run artifacts: {run}\n")
                        detached.write_status(run / "summary.json", dict(cases=[dict(execution_pass=True)], config=dict(cases=[{}])))
                    else:
                        self.assertIn("--save", command)
                        detached.write_status(run / "independent_audit.json", dict(array_check_count=123,
                            ready_for_stage3_design=gate, branches=[]))
                    update(1234)
                    return 0

                with patch.object(detached, "ROOT", root), patch.object(detached.signal, "signal"), patch.object(detached, "run_child", child):
                    self.assertEqual(detached.supervise(job, fd), 0)
                status = detached.status(job)
                self.assertEqual(status["phase"], "complete")
                self.assertEqual(status["ready_for_stage3_design"], gate)
                self.assertEqual([c[1] for c in calls], [3900, 300])
                self.assertEqual(status["audit_exit_code"], 0)
                self.assertEqual(status["completed_cases"], 1)


if __name__ == "__main__":
    unittest.main()
