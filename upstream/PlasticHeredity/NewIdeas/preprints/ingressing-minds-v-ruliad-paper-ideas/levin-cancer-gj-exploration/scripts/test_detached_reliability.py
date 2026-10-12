from contextlib import redirect_stderr, redirect_stdout
import fcntl
import io
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_reliability_detached as detached


class DetachedReliabilityTests(unittest.TestCase):
    def fixture(self, temp):
        root = Path(temp)
        job = root / "runs/jobs/test"
        job.mkdir(parents=True)
        detached.write_status(job / "launch.json", dict(hashes_sha256={}))
        detached.write_status(job / "status.json", dict(phase="launching", heartbeat_epoch=time.time(),
            planned_cases=96, stages=[]))
        fd = os.open(root / "lock", os.O_CREAT | os.O_RDWR, 0o600)
        return root, job, fd

    def test_terminal_status_and_stale_heartbeat(self):
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp)
            for phase, stale in (("runner", True), ("complete", False), ("stopped_after_screen", False), ("failed", False)):
                detached.write_status(job / "status.json", dict(phase=phase, heartbeat_epoch=time.time()-100))
                self.assertEqual(detached.status(job)["heartbeat_stale"], stale)
                self.assertFalse((job / "status.json.tmp").exists())

    def test_discovery_checks_stage_and_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = root / "job"
            job.mkdir()
            with patch.object(detached, "ROOT", root):
                self.assertIsNone(detached.discover_run(job, "screen"))
                for path in (Path("/tmp/unrelated"), root / "runs/reliability-confirmation-wrong"):
                    (job / "runner.log").write_text(f"Run artifacts: {path}\n")
                    with self.assertRaises(ValueError): detached.discover_run(job, "screen")
                correct = root / "runs/reliability-screen-example"
                (job / "runner.log").write_text(f"Run artifacts: {correct}\n")
                self.assertEqual(detached.discover_run(job, "screen"), correct)

    def test_failure_before_stage_does_not_mask_error_or_launch_child(self):
        with tempfile.TemporaryDirectory() as temp:
            root, job, fd = self.fixture(temp)
            (root / "dependency").write_text("changed")
            detached.write_status(job / "launch.json", dict(hashes_sha256={"dependency": "wrong"}))
            with patch.object(detached, "ROOT", root), patch.object(detached, "NEW_FILES", []), patch.object(
                    detached.signal, "signal"), patch.object(detached, "run_child") as child, redirect_stderr(io.StringIO()):
                self.assertEqual(detached.supervise(job, fd), 1)
            child.assert_not_called()
            self.assertEqual(detached.status(job)["phase"], "failed")
            self.assertIn("changed since initial launch", detached.status(job)["error"])

    def test_runner_failure_stops_without_audit_retry_or_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root, job, fd = self.fixture(temp)
            with patch.object(detached, "ROOT", root), patch.object(detached, "NEW_FILES", []), patch.object(
                    detached.signal, "signal"), patch.object(detached, "run_child", return_value=7) as child, redirect_stderr(io.StringIO()):
                self.assertEqual(detached.supervise(job, fd), 1)
            child.assert_called_once()
            meta = detached.status(job)
            self.assertEqual(meta["phase"], "failed")
            self.assertEqual(meta["stages"][0]["runner_exit_code"], 7)

    def run_mock_chain(self, temp, gate=True, mutate_after_screen=False, audit_fail=False):
        root, job, fd = self.fixture(temp)
        calls = []
        if mutate_after_screen:
            (root / "dependency").write_text("initial")
            detached.write_status(job / "launch.json", dict(hashes_sha256={"dependency": detached.digest(root / "dependency")}))
        def child(command, log, timeout, update):
            stage = log.parent.name
            calls.append((stage, log.name, command, timeout))
            run = root / ("runs/reliability-"+stage+"-example")
            if log.name == "runner.log":
                run.mkdir()
                log.write_text(f"Run artifacts: {run}\n")
                detached.write_status(run / "summary.json", dict(cases=[dict(execution_pass=True)], config=dict(cases=[{}])))
            else:
                if audit_fail:
                    return 9
                detached.write_status(run / "independent_audit.json", dict(array_check_count=123, quality_gate=gate,
                    panel={"fixture": {"strict_successes": 0}}, eligible_for_confirmation=gate,
                    ready_for_benefit_design=gate))
                if stage == "screen" and mutate_after_screen:
                    (root / "dependency").write_text("changed after audit")
            update(1234)
            return 0
        with patch.object(detached, "ROOT", root), patch.object(detached, "NEW_FILES", []), patch.object(
                detached.signal, "signal"), patch.object(detached, "run_child", child), redirect_stderr(io.StringIO()):
            rc = detached.supervise(job, fd)
        return rc, detached.status(job), calls

    def test_valid_negative_result_still_runs_fixed_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.run_mock_chain(temp)
            self.assertEqual(rc, 0)
            self.assertEqual(meta["phase"], "complete")
            self.assertEqual(meta["completed_cases"], 2)
            self.assertEqual([c[0:2] for c in calls], [("screen", "runner.log"), ("screen", "audit.log"),
                ("confirmation", "runner.log"), ("confirmation", "audit.log")])
            self.assertEqual([c[3] for c in calls], [14700, 600, 14700, 600])
            self.assertIn("--screen-run", calls[2][2])
            self.assertTrue(meta["ready_for_benefit_design"])
            self.assertEqual(len(meta["stages"]), 2)

    def test_failed_quality_gate_skips_confirmation_even_when_execution_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.run_mock_chain(temp, gate=False)
            self.assertEqual(rc, 0)
            self.assertEqual(meta["phase"], "stopped_after_screen")
            self.assertTrue(meta["confirmation_skipped"])
            self.assertEqual(len(calls), 2)
            self.assertEqual(meta["stages"][0]["phase"], "complete")

    def test_audit_error_prevents_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.run_mock_chain(temp, audit_fail=True)
            self.assertEqual(rc, 1)
            self.assertEqual(meta["phase"], "failed")
            self.assertEqual(meta["stages"][0]["audit_exit_code"], 9)
            self.assertEqual(len(calls), 2)

    def test_between_stage_file_change_cannot_retune_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.run_mock_chain(temp, mutate_after_screen=True)
            self.assertEqual(rc, 1)
            self.assertEqual(meta["phase"], "failed")
            self.assertEqual(len(calls), 2)
            self.assertIn("changed since initial launch", meta["error"])

    def test_low_disk_stops_without_deleting_or_launching(self):
        with tempfile.TemporaryDirectory() as temp:
            root, job, fd = self.fixture(temp)
            with patch.object(detached, "ROOT", root), patch.object(detached, "NEW_FILES", []), patch.object(
                    detached.signal, "signal"), patch.object(detached.shutil, "disk_usage", return_value=SimpleNamespace(free=1)), patch.object(
                    detached, "run_child") as child, redirect_stderr(io.StringIO()):
                self.assertEqual(detached.supervise(job, fd), 1)
            child.assert_not_called()
            self.assertIn("Low disk", detached.status(job)["error"])

    def test_launch_passes_exclusive_lock_into_new_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jobs = root / "runs/jobs"
            with patch.object(detached, "ROOT", root), patch.object(detached, "JOBS", jobs), patch.object(
                    detached, "NEW_FILES", []), patch.object(detached, "execution_manifest", return_value={}), patch.object(
                    detached.subprocess, "Popen", return_value=SimpleNamespace(pid=1234)) as popen, redirect_stdout(io.StringIO()):
                self.assertEqual(detached.launch(), 0)
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertEqual(len(popen.call_args.kwargs["pass_fds"]), 1)
                job = next(jobs.iterdir())
                self.assertEqual(detached.status(job)["planned_cases"], 96)
                with (root / "runs/reliability-overnight.lock").open("a+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    with self.assertRaises(RuntimeError): detached.launch()


if __name__ == "__main__":
    unittest.main()

