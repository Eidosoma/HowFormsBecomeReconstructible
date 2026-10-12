"""Software-only recovery tests. No new native simulation pilot is executed."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import recover_reliability as recovery
import test_reliability as fixtures


class RecoveryTests(unittest.TestCase):
    def minimal_records(self):
        config = json.loads((recovery.ROOT / "configs/reliability_confirmation_v1.json").read_text())
        rows = [dict(id=c["id"], execution_pass=True, returncode=0, status="finished", elapsed_seconds=700,
            result=dict(case=c, execution_pass=True)) for c in config["cases"]]
        timeout = next(r for r in rows if r["id"] == recovery.CASE_ID)
        replacement = copy.deepcopy(timeout)
        replacement["elapsed_seconds"] = 900
        timeout.update(execution_pass=False, returncode=None, status="timeout", elapsed_seconds=427)
        timeout.pop("result")
        original = dict(config=config, cases=rows, elapsed_seconds=14400.4, all_execution_valid=False,
            hashes_sha256={"old": "old_hash"}, frozen_hashes_sha256={"old": "old_hash"})
        manifest = dict(original_run="original", original_summary_sha256="original_hash",
            execution_hashes_sha256={"new": "new_hash"}, new_frozen_hashes_sha256={"new": "new_hash"})
        return original, replacement, manifest

    def test_combination_reuses_38_unchanged_and_preserves_failed_original(self):
        original, replacement, manifest = self.minimal_records()
        saved = copy.deepcopy(original)
        combined = recovery.combine_summary(original, replacement, manifest, "manifest_hash")
        self.assertEqual(original, saved)
        self.assertTrue(combined["all_execution_valid"])
        self.assertEqual(combined["config"], original["config"])
        self.assertEqual(combined["elapsed_seconds"], 15300.4)
        self.assertEqual(combined["execution_kind"], "composite_runtime_recovery")
        self.assertFalse(combined["recovery"]["original_attempt_passed"])
        self.assertEqual(combined["recovery"]["newly_executed_case_count"], 1)
        for old, new in zip(original["cases"], combined["cases"]):
            self.assertEqual(new, replacement if old["id"] == recovery.CASE_ID else old)

    def test_rejects_failed_replacement_wrong_case_and_retuned_seed(self):
        for mode in ("failed", "case", "seed"):
            original, replacement, manifest = self.minimal_records()
            if mode == "failed": replacement["execution_pass"] = False
            elif mode == "case": replacement["id"] = "another_case"
            else: replacement["result"]["case"]["seed"] += 1
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                recovery.combine_summary(original, replacement, manifest, "manifest_hash")

    def test_partial_prefix_checks_arrays_and_explicitly_reports_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old", Path(temp) / "new"
            old.mkdir()
            new.mkdir()
            np.savez_compressed(old / "state.npz", state=np.arange(4))
            np.savez_compressed(new / "state.npz", state=np.arange(4))
            (old / "unfinished.npz").write_bytes(b"interrupted zip")
            report = recovery.partial_prefix(old, new)
            self.assertEqual(report["matching_array_files"], ["state.npz"])
            self.assertEqual(report["unreadable_interrupted_files"], ["unfinished.npz"])
            np.savez_compressed(new / "state.npz", state=np.arange(4)+1)
            with self.assertRaisesRegex(RuntimeError, "diverges"):
                recovery.partial_prefix(old, new)

    def test_unreadable_completed_round_is_not_excused_as_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old", Path(temp) / "new"
            (old / "round_01").mkdir(parents=True)
            new.mkdir()
            recovery.write_status(old / "progress.json", [dict(round=1)])
            (old / "round_01/endpoints.npz").write_bytes(b"broken")
            with self.assertRaisesRegex(RuntimeError, "completed original round"):
                recovery.partial_prefix(old, new)

    def test_snapshot_detects_changes_added_files_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").write_text("original")
            before = recovery.snapshot(root)
            (root / "data").write_text("changed")
            self.assertNotEqual(before, recovery.snapshot(root))
            (root / "data").write_text("original")
            (root / "extra").write_text("new")
            self.assertNotEqual(before, recovery.snapshot(root))
            (root / "alias").symlink_to(root / "data")
            with self.assertRaisesRegex(RuntimeError, "symlinks"):
                recovery.snapshot(root)

    def test_full_composite_unchanged_analyzer_negative_hypothesis_and_provenance(self):
        factory = fixtures.ReliabilityTests()
        factory.setUp()
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            root = Path(temp)
            screen = factory.full_panel_fixture(temp, "screen")
            original = factory.full_panel_fixture(temp, "confirmation", screen)
            legacy = recovery.read(original / "summary.json")
            case = next(c for c in legacy["config"]["cases"] if c["id"] == recovery.CASE_ID)
            recovery.write_status(original / recovery.CASE_ID / "spec.json",
                dict(case=case, config=legacy["config"], inputs=str(original / "inputs")))
            retry = root / "synthetic_complete_retry"
            shutil.copytree(original / recovery.CASE_ID, retry)
            saved = root / "synthetic_excluded_future"
            saved.mkdir()
            for n in range(4, 13):
                (original / recovery.CASE_ID / f"round_{n:02}").rename(saved / f"round_{n:02}")
            for name in ("result.json", "endpoints.npz"):
                (original / recovery.CASE_ID / name).rename(saved / name)
            recovery.write_status(original / recovery.CASE_ID / "progress.json",
                recovery.read(original / recovery.CASE_ID / "progress.json")[:3])
            failed = next(r for r in legacy["cases"] if r["id"] == recovery.CASE_ID)
            replacement = copy.deepcopy(failed)
            replacement.update(status="finished", elapsed_seconds=900.)
            failed.clear()
            failed.update(id=recovery.CASE_ID, execution_pass=False, returncode=None, status="timeout", elapsed_seconds=427.)
            legacy.update(all_execution_valid=False, elapsed_seconds=14400.4, python=sys.version,
                packages={n: importlib.metadata.version(n) for n in ("numpy", "scipy", "matplotlib")},
                files_unchanged=True, frozen_files_unchanged=True, inputs_unchanged=True,
                predecessor_audit_unchanged=True, source_clean_after=True)
            recovery.write_status(original / "summary.json", legacy)
            recovery.write_status(original / "inputs/manifest.json", legacy["inputs"])
            old_job = root / "runs/jobs/original"
            old_job.mkdir(parents=True)
            recovery.write_status(old_job / "status.json", dict(phase="failed", current_stage="confirmation", exit_code=1))
            job = root / "runs/jobs/recovery"
            job.mkdir()
            recovery.write_status(job / "launch.json", dict(hashes_sha256=legacy["hashes_sha256"]))
            run = root / "runs/recovery"
            run.mkdir()
            before = recovery.snapshot(original)
            with patch.object(recovery, "ROOT", root), patch.object(recovery, "ORIGINAL", original), patch.object(
                    recovery, "ORIGINAL_JOB", old_job), patch.object(recovery, "NEW_FILES", ()), patch.object(recovery, "source_check"):
                self.assertEqual(recovery.prepare(run, job), 0)
                self.assertEqual(sum(p.is_symlink() for p in run.iterdir() if p.name.startswith("confirmation__")), 38)
                self.assertEqual((run / recovery.CASE_ID / "spec.json").read_bytes(), (original / recovery.CASE_ID / "spec.json").read_bytes())
                shutil.copytree(retry, run / recovery.CASE_ID, dirs_exist_ok=True)
                manifest = recovery.read(run / "recovery_manifest.json")
                combined = recovery.combine_summary(legacy, replacement, manifest, recovery.file_hash(run / "recovery_manifest.json"))
                recovery.write_status(run / "replacement_record.json", replacement)
                recovery.write_status(run / "summary.json", combined)
                self.assertEqual(recovery.audit_recovery(run), 0)
                report = recovery.read(run / "independent_audit.json")
                self.assertTrue(report["quality_gate"])
                self.assertTrue(report["ready_for_benefit_design"])
                self.assertEqual(report["new_integrations"], 132)
                self.assertEqual(report["reused_integrations"], 5016)
                self.assertEqual(report["represented_panel_integrations"], 5148)
                self.assertEqual(report["interrupted_prefix"]["completed_original_phase_integrations"], 33)
                self.assertFalse(next(b for b in report["branches"] if b["case"]["id"] == recovery.CASE_ID)["outcomes"]["strict_renewal"])
                self.assertEqual(recovery.snapshot(original), before)
                (original / "added_after_preflight").write_text("must reject")
                with self.assertRaisesRegex(RuntimeError, "changed since recovery preflight"):
                    recovery.audit_recovery(run)

    def supervisor_fixture(self, temp):
        root = Path(temp)
        job = root / "runs/jobs/test"
        job.mkdir(parents=True)
        run = root / "runs/recovery"
        run.mkdir()
        recovery.write_status(job / "launch.json", dict(run=str(run), hashes_sha256={}, new_frozen_hashes_sha256={}))
        recovery.write_status(job / "status.json", dict(phase="launching", heartbeat_epoch=time.time()))
        fd = os.open(root / "lock", os.O_CREAT | os.O_RDWR, 0o600)
        return root, job, run, fd

    def mock_supervisor(self, temp, fail_at=None, quality=True):
        root, job, run, fd = self.supervisor_fixture(temp)
        original, replacement, manifest = self.minimal_records()
        calls = []
        def child(command, logfile, timeout, update):
            calls.append((command, logfile.name, timeout))
            update(1234)
            if logfile.name == fail_at:
                return 124
            if logfile.name == "preflight.log":
                (run / recovery.CASE_ID).mkdir()
                recovery.write_status(run / "original_failed_summary.json", original)
                recovery.write_status(run / "recovery_manifest.json", manifest)
            elif logfile.name == "runner.log":
                recovery.write_status(run / recovery.CASE_ID / "result.json", replacement["result"])
                recovery.write_status(run / recovery.CASE_ID / "progress.json", [dict(round=n) for n in range(1, 13)])
            else:
                recovery.write_status(run / "independent_audit.json", dict(quality_gate=quality, array_check_count=123,
                    ready_for_benefit_design=quality, original_artifacts_unchanged=True, panel={}))
            return 0
        with patch.object(recovery, "ROOT", root), patch.object(recovery.signal, "signal"), patch.object(
                recovery, "run_child", child), redirect_stderr(io.StringIO()):
            rc = recovery.supervise(job, fd)
        return rc, recovery.status(job), calls

    def test_detached_chain_one_worker_then_audit_and_no_downstream_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.mock_supervisor(temp)
            self.assertEqual(rc, 0)
            self.assertEqual(meta["phase"], "complete")
            self.assertEqual(meta["replacement_rounds_complete"], 12)
            self.assertEqual([c[1:] for c in calls], [("preflight.log", 600), ("runner.log", 1800), ("audit.log", 600)])
            self.assertTrue(meta["ready_for_benefit_design"])

    def test_preflight_worker_and_audit_timeouts_stop_without_retry(self):
        for name, count in (("preflight.log", 1), ("runner.log", 2), ("audit.log", 3)):
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as temp:
                rc, meta, calls = self.mock_supervisor(temp, fail_at=name)
                self.assertEqual(rc, 1)
                self.assertEqual(meta["phase"], "failed")
                self.assertEqual(len(calls), count)
                self.assertIn("124", meta["error"])

    def test_quality_disagreement_is_reported_without_retuning(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, meta, calls = self.mock_supervisor(temp, quality=False)
            self.assertEqual(rc, 0)
            self.assertFalse(meta["quality_gate"])
            self.assertFalse(meta["ready_for_benefit_design"])
            self.assertIn("disagreement", meta["next_action"])
            self.assertEqual(len(calls), 3)

    def test_low_disk_and_changed_launch_files_never_start_child(self):
        for mode in ("disk", "hash"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root, job, run, fd = self.supervisor_fixture(temp)
                with ExitStack() as stack:
                    stack.enter_context(patch.object(recovery, "ROOT", root))
                    stack.enter_context(patch.object(recovery.signal, "signal"))
                    child = stack.enter_context(patch.object(recovery, "run_child"))
                    stack.enter_context(redirect_stderr(io.StringIO()))
                    if mode == "disk": stack.enter_context(patch.object(recovery.shutil, "disk_usage", return_value=SimpleNamespace(free=0)))
                    else: stack.enter_context(patch.object(recovery, "check_hashes", return_value=False))
                    self.assertEqual(recovery.supervise(job, fd), 1)
                    child.assert_not_called()

    def test_launch_new_session_inherits_exclusive_h3_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / "runs/original"
            old.mkdir(parents=True)
            recovery.write_status(old / "summary.json", dict(hashes_sha256={}))
            with patch.object(recovery, "ROOT", root), patch.object(recovery, "JOBS", root / "runs/jobs"), patch.object(
                    recovery, "ORIGINAL", old), patch.object(recovery, "NEW_FILES", ()), patch.object(
                    recovery.subprocess, "Popen", return_value=SimpleNamespace(pid=1234)) as popen, redirect_stdout(io.StringIO()):
                self.assertEqual(recovery.launch(), 0)
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertEqual(len(popen.call_args.kwargs["pass_fds"]), 1)
                with (root / "runs/reliability-overnight.lock").open("a+") as lock:
                    recovery.fcntl.flock(lock, recovery.fcntl.LOCK_EX | recovery.fcntl.LOCK_NB)
                    with self.assertRaisesRegex(RuntimeError, "already holds"):
                        recovery.launch()


if __name__ == "__main__":
    unittest.main()
