"""Synthetic supervision checks, without spawning native simulations."""

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

import run_benefit_holdout_detached as detached
import bounded_holdout as bounded


class DetachedHoldoutTests(unittest.TestCase):
    def fixture(self, temp):
        root = Path(temp)
        job = root / "runs/jobs/test"
        job.mkdir(parents=True)
        detached.write_status(job / "launch.json", dict(hashes_sha256={}, frozen_hashes_sha256={}))
        detached.write_status(job / "status.json", dict(phase="launching", heartbeat_epoch=time.time(),
            planned_cases=144, completed_cases=0, valid_cases=0))
        fd = os.open(root / "lock", os.O_CREAT | os.O_RDWR, 0o600)
        return root, job, fd

    def test_stale_and_terminal_heartbeats(self):
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp)
            for phase, stale in (("preflight_and_runner", True), ("complete", False), ("failed", False)):
                detached.write_status(job / "status.json", dict(phase=phase, heartbeat_epoch=time.time()-100))
                self.assertEqual(detached.status(job)["heartbeat_stale"], stale)

    def test_discovery_confined_to_H4b_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = root / "job"
            job.mkdir()
            with patch.object(detached, "ROOT", root):
                self.assertIsNone(detached.discover_run(job))
                for p in (Path("/tmp/wrong"), root / "runs/reliability-screen-example"):
                    (job / "runner.log").write_text(f"Run artifacts: {p}\n")
                    with self.assertRaises(ValueError): detached.discover_run(job)

    def mock_chain(self, temp, runner_code=0, audit_code=0, quality=True):
        root, job, fd = self.fixture(temp)
        calls = []
        def child(command, log, timeout, update):
            calls.append((log.name, timeout, command))
            run = root / "runs/benefit-holdout-fixture"
            if log.name == "runner.log":
                if runner_code:
                    return runner_code
                run.mkdir()
                log.write_text(f"Run artifacts: {run}\n")
                detached.write_status(run / "summary.json", dict(cases=[dict(execution_pass=True)]*144))
            else:
                if audit_code:
                    return audit_code
                detached.write_status(run / "independent_audit.json", dict(quality_gate=quality,
                    ready_for_interpretation=quality, array_check_count=123, historical_benchmarks_pass=quality, selected_fine_agreement=quality))
            update(1234)
            return 0
        with patch.object(detached, "ROOT", root), patch.object(detached.signal, "signal"), patch.object(
                detached, "run_child", child), patch.object(detached.shutil, "disk_usage", return_value=SimpleNamespace(free=10*1024**3)), redirect_stderr(io.StringIO()):
            rc = detached.supervise(job, fd)
        return rc, detached.status(job), calls

    def test_only_panel_then_audit_no_retry_or_followup(self):
        for quality in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                rc, meta, calls = self.mock_chain(temp, quality=quality)
                self.assertEqual(rc, 0)
                self.assertEqual(meta["phase"], "complete")
                self.assertEqual(meta["completed_cases"], 144)
                self.assertEqual([(n, t) for n, t, _ in calls], [("runner.log", 86700), ("audit.log", 1800)])
                self.assertEqual(meta["ready_for_interpretation"], quality)
        for where in ("runner", "audit"):
            with tempfile.TemporaryDirectory() as temp:
                rc, meta, calls = self.mock_chain(temp, **{where+"_code": 124})
                self.assertEqual(rc, 1)
                self.assertEqual(meta["phase"], "failed")
                self.assertEqual(len(calls), 1 if where == "runner" else 2)

    def test_changed_execution_or_low_disk_prevents_child(self):
        for low in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root, job, fd = self.fixture(temp)
                if not low:
                    (root / "dependency").write_text("changed")
                    detached.write_status(job / "launch.json", dict(hashes_sha256={"dependency": "wrong"}, frozen_hashes_sha256={}))
                with patch.object(detached, "ROOT", root), patch.object(detached.signal, "signal"), patch.object(
                        detached.shutil, "disk_usage", return_value=SimpleNamespace(free=1 if low else 10*1024**3)), patch.object(
                        detached, "run_child") as child, redirect_stderr(io.StringIO()):
                    self.assertEqual(detached.supervise(job, fd), 1)
                child.assert_not_called()

    def test_launch_passes_lock_to_new_session_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jobs = root / "runs/jobs"
            with patch.object(detached, "ROOT", root), patch.object(detached, "JOBS", jobs), patch.object(
                    detached, "execution_files", return_value=[]), patch.object(detached, "execution_manifest", return_value={}), patch.object(
                    detached.shutil, "disk_usage", return_value=SimpleNamespace(free=10*1024**3)), patch.object(
                    detached.subprocess, "Popen", return_value=SimpleNamespace(pid=1234)) as popen, redirect_stdout(io.StringIO()):
                self.assertEqual(detached.launch(), 0)
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertEqual(len(popen.call_args.kwargs["pass_fds"]), 1)
                self.assertEqual(detached.status(next(jobs.iterdir()))["planned_cases"], 144)
                with (root / "runs/benefit-holdout.lock").open("a+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    with self.assertRaises(RuntimeError): detached.launch()

    def test_worker_no_launch_on_low_disk_or_expired_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            with patch.object(bounded.shutil, "disk_usage", return_value=SimpleNamespace(free=1)), patch.object(bounded.subprocess, "run") as child:
                row = bounded.run_worker(dict(id="case"), {}, run, time.monotonic()+10, {}, Path("unused"))
                self.assertEqual(row["status"], "not_launched_disk")
                row = bounded.run_worker(dict(id="case"), {}, run, time.monotonic()-1, {}, Path("unused"))
                self.assertEqual(row["status"], "not_launched_budget")
            child.assert_not_called()

    def test_registered_controls_are_frozen_first_and_gate_all_main_launches(self):
        for passed in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                script, config_path, protocol = [root / n for n in ("runner.py", "config.json", "protocol.md")]
                for path in (script, protocol, root / "requirements-smoke.txt"):
                    path.write_text("synthetic fixture\n")
                cases = [dict(id=f"prefix_{i}", kind="prefix") for i in range(8)]+[dict(id=f"main_{i}", kind="main") for i in range(2)]
                config = dict(cases=cases, workers=2, worker_timeout_seconds=3600, total_budget_seconds=86400,
                    prefix_cases=8, prefix_gate_required=True)
                detached.write_status(config_path, config)
                calls, ordering = [], []
                def prepare(run, cfg):
                    (run / "inputs").mkdir()
                    detached.write_status(run / "predecessor_audit.json", dict(synthetic=True))
                    return {}
                def worker(case, cfg, run, deadline, env, runner):
                    self.assertTrue((run / "frozen/protocol.md").exists())
                    self.assertEqual(json.loads((run / "frozen/config.json").read_text()), config)
                    if case["kind"] == "main":
                        self.assertEqual(ordering, ["gate_passed"])
                    calls.append(case["id"])
                    return dict(id=case["id"], execution_pass=True, returncode=0)
                def gate(run, cfg):
                    self.assertEqual(set(calls), {f"prefix_{i}" for i in range(8)})
                    if passed:
                        ordering.append("gate_passed")
                    return dict(quality_gate=passed)
                with patch.object(bounded, "ROOT", root), patch.object(bounded, "source_check"), patch.object(
                        bounded.subprocess, "check_output", return_value=""), patch.object(bounded, "run_worker", worker), redirect_stdout(io.StringIO()):
                    code = bounded.run_bounded(config_path, script, protocol, [], prepare, "holdout-fixture", "synthetic",
                        control_gate=gate)
                self.assertEqual(code, 0 if passed else 1)
                self.assertEqual(len(calls), 10 if passed else 8)


if __name__ == "__main__":
    unittest.main()
