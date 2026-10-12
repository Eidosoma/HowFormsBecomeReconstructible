"""One authorized, detached runtime-only recovery; original H3 remains immutable."""

import argparse
import copy
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np

from analyze_commitment_components import FLAGS
from analyze_reliability import analyze, expected_cases
from run_onward_transfer import file_hash
from run_pilot import source_check
from run_reliability import validate_config
from run_rewrite_tradeoff_detached import now, run_child, status, write_status

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "runs/jobs"
ORIGINAL = ROOT / "runs/reliability-confirmation-20260907T130242Z-wwcnp7xy"
ORIGINAL_JOB = JOBS / "reliability-overnight-20260907T093500Z-u5oxhr4u"
CASE_ID = "confirmation__pooled_rewritten_e_pair_strong_s1_fine"
RUNNER = ROOT / "scripts/run_reliability.py"
THIS = Path(__file__).resolve()
NEW_FILES = (THIS, ROOT / "scripts/test_reliability_recovery.py", ROOT / "RELIABILITY_RECOVERY_PROTOCOL.md")


def read(path):
    return json.loads(path.read_text())


def require(value, message):
    if not value:
        raise RuntimeError(message)


def snapshot(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Original artifacts must not contain symlinks")
        if path.is_file():
            result[str(path.relative_to(folder))] = file_hash(path)
    return result


def check_hashes(root, hashes):
    return all((root / name).is_file() and file_hash(root / name) == value for name, value in hashes.items())


def validate_original(original, original_job):
    summary, meta = read(original / "summary.json"), read(original_job / "status.json")
    validate_config(summary["config"])
    require(summary["config"]["stage"] == "confirmation", "Not the confirmation panel")
    require(meta["phase"] == "failed" and meta["current_stage"] == "confirmation" and meta["exit_code"] == 1,
        "Original supervisor is not terminal failed confirmation")
    require(not summary["all_execution_valid"], "Original panel is already complete")
    cases = {r["id"]: r for r in summary["cases"]}
    require(len(cases) == len(summary["cases"]) == 39 and set(cases) == {c["id"] for c in expected_cases("confirmation")},
        "Unexpected original case grid")
    failed = [r for r in summary["cases"] if not r["execution_pass"]]
    require(len(failed) == 1 and failed[0]["id"] == CASE_ID and failed[0]["status"] == "timeout"
        and failed[0]["returncode"] is None and "result" not in failed[0], "Not the single authorized timeout")
    require(14400 <= summary["elapsed_seconds"] < 14460 and 0 < failed[0]["elapsed_seconds"] < 1800,
        "Failure is not the documented panel-budget cutoff")
    require(all(summary[k] for k in ("files_unchanged", "frozen_files_unchanged", "inputs_unchanged",
        "predecessor_audit_unchanged", "source_clean_after")), "Original integrity flags failed")
    require(check_hashes(ROOT, summary["hashes_sha256"]), "Original execution files changed")
    require(check_hashes(original / "frozen", summary["frozen_hashes_sha256"]), "Original frozen files changed")
    require(file_hash(original / "predecessor_audit.json") == summary["predecessor_audit_sha256"], "H2 audit changed")
    require(read(original / "inputs/manifest.json") == summary["inputs"] and len(summary["inputs"]) == 65,
        "Unexpected input manifest")
    require(all(file_hash(original / "inputs" / name) == v["sha256"] == file_hash(Path(v["source"]))
        for name, v in summary["inputs"].items()), "Input states or gate changed")
    gate = read(original / "screening_gate.json")
    screen = Path(gate["run"])
    require(gate["audit"]["eligible_for_confirmation"] and all(gate["audit"][k] for k in FLAGS)
        and file_hash(screen / "summary.json") == gate["screen_summary_sha256"]
        and file_hash(screen / "frozen/reliability_confirmation_v1.json") == gate["config_sha256"]
        and read(screen / "frozen/reliability_confirmation_v1.json") == summary["config"], "Screening gate changed")
    require(summary["python"] == sys.version and all(importlib.metadata.version(k) == v for k, v in summary["packages"].items()),
        "Python or numerical packages changed")
    case = next(c for c in summary["config"]["cases"] if c["id"] == CASE_ID)
    require(read(original / CASE_ID / "spec.json") == dict(case=case, config=summary["config"], inputs=str(original / "inputs")),
        "Original worker spec differs from fixed configuration")
    for name, row in cases.items():
        if name != CASE_ID:
            require(row["returncode"] == 0 and row["result"] == read(original / name / "result.json"),
                "Completed record differs from its artifact")
    return summary


def prepare(run, job):
    source_check()
    summary = validate_original(ORIGINAL, ORIGINAL_JOB)
    launch = read(job / "launch.json")
    require(check_hashes(ROOT, launch["hashes_sha256"]), "Launch files changed before preflight")
    original_hashes, job_hashes = snapshot(ORIGINAL), snapshot(ORIGINAL_JOB)
    require(original_hashes["summary.json"] == file_hash(ORIGINAL / "summary.json"), "Summary changed during preflight")
    require(not any(run.iterdir()), "Recovery output directory is not empty")
    for name in ("inputs", "predecessor_audit.json", "screening_gate.json"):
        (run / name).symlink_to(ORIGINAL / name, target_is_directory=name == "inputs")
    shutil.copytree(ORIGINAL / "frozen", run / "frozen")
    for path in NEW_FILES:
        shutil.copyfile(job / "frozen" / path.name, run / "frozen" / path.name)
    shutil.copyfile(ORIGINAL / "summary.json", run / "original_failed_summary.json")
    for case in summary["config"]["cases"]:
        folder = run / case["id"]
        if case["id"] == CASE_ID:
            folder.mkdir()
            shutil.copyfile(ORIGINAL / CASE_ID / "spec.json", folder / "spec.json")
        else:
            folder.symlink_to(ORIGINAL / case["id"], target_is_directory=True)
    manifest = dict(kind="runtime_only_composite_confirmation_v1", original_run=str(ORIGINAL), original_job=str(ORIGINAL_JOB),
        original_artifacts_sha256=original_hashes, original_job_artifacts_sha256=job_hashes,
        original_summary_sha256=original_hashes["summary.json"],
        rerun_case=CASE_ID, reused_cases=[c["id"] for c in summary["config"]["cases"] if c["id"] != CASE_ID],
        original_timeout=next(r for r in summary["cases"] if r["id"] == CASE_ID),
        spec_sha256=file_hash(ORIGINAL / CASE_ID / "spec.json"),
        execution_hashes_sha256=launch["hashes_sha256"],
        new_frozen_hashes_sha256={p.name: file_hash(job / "frozen" / p.name) for p in NEW_FILES},
        preflight_utc=now(), worker_timeout_seconds=1800, audit_timeout_seconds=600,
        selection_by_outcome=False, restart_from_original_sources=True, no_additional_retries=True,
        provenance_note="38 original cases plus one unchanged-condition rerun; original timeout retained")
    write_status(run / "recovery_manifest.json", manifest)
    require(snapshot(ORIGINAL) == original_hashes and snapshot(ORIGINAL_JOB) == job_hashes,
        "Original artifacts changed during preflight")
    print(json.dumps(dict(preflight_pass=True, run=str(run), reused_cases=38, rerun_case=CASE_ID)), flush=True)
    return 0


def combine_summary(original, replacement, manifest, manifest_hash):
    require(replacement["id"] == CASE_ID and replacement["execution_pass"] and replacement["returncode"] == 0,
        "Replacement worker did not complete validly")
    case = next(c for c in original["config"]["cases"] if c["id"] == CASE_ID)
    require(replacement["result"]["case"] == case and replacement["result"]["execution_pass"], "Rerun case changed")
    combined = copy.deepcopy(original)
    combined["cases"] = [copy.deepcopy(replacement if row["id"] == CASE_ID else row) for row in original["cases"]]
    combined.update(all_execution_valid=True, execution_kind="composite_runtime_recovery",
        elapsed_seconds=original["elapsed_seconds"]+replacement["elapsed_seconds"],
        recovery=dict(manifest_sha256=manifest_hash, original_run=manifest["original_run"],
            original_summary_sha256=manifest["original_summary_sha256"], original_attempt_passed=False,
            rerun_case=CASE_ID, reused_case_count=38, newly_executed_case_count=1,
            original_elapsed_seconds=original["elapsed_seconds"], replacement_elapsed_seconds=replacement["elapsed_seconds"],
            aggregate_elapsed_is_not_one_panel_budget=True))
    combined["hashes_sha256"].update(manifest["execution_hashes_sha256"])
    combined["frozen_hashes_sha256"].update(manifest["new_frozen_hashes_sha256"])
    return combined


def partial_prefix(original_case, replacement_case):
    checked, unreadable, completed = [], [], set()
    if (original_case / "progress.json").exists():
        completed = {f"round_{r['round']:02}" for r in read(original_case / "progress.json")}
    for path in sorted(original_case.rglob("*.npz")):
        name = path.relative_to(original_case)
        try:
            with np.load(path, allow_pickle=False) as stored:
                arrays = {k: stored[k] for k in stored.files}
        except (OSError, ValueError, EOFError, zipfile.BadZipFile):
            require(name.parts[0] not in completed, "Unreadable array in a completed original round")
            unreadable.append(str(name))
            continue
        with np.load(replacement_case / name, allow_pickle=False) as new:
            require(set(arrays) == set(new.files) and all(np.array_equal(value, new[key]) for key, value in arrays.items()),
                "Replacement diverges from interrupted prefix: " + str(name))
        checked.append(str(name))
    require(bool(checked), "Interrupted attempt has no comparable arrays")
    return dict(matching_array_files=checked, unreadable_interrupted_files=unreadable,
        completed_original_rounds=sorted(completed),
        completed_original_phase_integrations=sum(Path(n).name != "endpoints.npz" for n in checked))


def audit_recovery(run):
    manifest = read(run / "recovery_manifest.json")
    original, original_job = Path(manifest["original_run"]), Path(manifest["original_job"])
    require(original == ORIGINAL and original_job == ORIGINAL_JOB, "Recovery origin differs from authorized paths")
    source_check()
    require(snapshot(original) == manifest["original_artifacts_sha256"] and snapshot(original_job) == manifest["original_job_artifacts_sha256"],
        "Original artifacts changed since recovery preflight")
    require(check_hashes(ROOT, manifest["execution_hashes_sha256"]), "Execution changed during recovery")
    legacy = read(run / "original_failed_summary.json")
    require(file_hash(run / "original_failed_summary.json") == manifest["original_summary_sha256"], "Preserved original summary changed")
    require(read(run / "summary.json") == combine_summary(legacy, read(run / "replacement_record.json"), manifest,
        file_hash(run / "recovery_manifest.json")), "Composite differs from the declared record selection")
    require(manifest["rerun_case"] == CASE_ID and manifest["reused_cases"] == [c["id"] for c in legacy["config"]["cases"] if c["id"] != CASE_ID],
        "Recovery selects unexpected cases")
    for name in manifest["reused_cases"]:
        require((run / name).is_symlink() and (run / name).resolve() == original / name, "Reused case points elsewhere")
    require(not (run / CASE_ID).is_symlink(), "Rerun must have a new independent directory")
    require(file_hash(run / CASE_ID / "spec.json") == manifest["spec_sha256"] == file_hash(original / CASE_ID / "spec.json"),
        "Rerun specification changed")
    require(read(run / CASE_ID / "design.json") == read(original / CASE_ID / "design.json"), "Rerun schedule changed")
    prefix = partial_prefix(original / CASE_ID, run / CASE_ID)
    report = analyze(run)
    source_check()
    require(snapshot(original) == manifest["original_artifacts_sha256"] and snapshot(original_job) == manifest["original_job_artifacts_sha256"],
        "Original artifacts changed during final audit")
    report["represented_panel_integrations"] = report.pop("new_integrations")
    report["represented_panel_snapshots"] = report.pop("new_snapshots")
    fresh = read(run / CASE_ID / "result.json")
    phases = [a for row in fresh["rounds"] for a in row["audits"]]
    report.update(new_integrations=len(phases), reused_integrations=38*12*11,
        new_snapshots=sum(p["samples"] for p in phases), new_fresh_recipients=24,
        new_integration_cpu_seconds=sum(p["cpu_seconds"] for p in phases),
        recovery_provenance_pass=True, original_artifacts_unchanged=True,
        interrupted_prefix=prefix, recovery=read(run / "summary.json")["recovery"])
    require(report["represented_panel_integrations"] == report["reused_integrations"]+report["new_integrations"] == 5148,
        "Incorrect new/reused integration accounting")
    write_status(run / "independent_audit.json", report)
    compact = {k: report[k] for k in (*FLAGS, "quality_gate", "ready_for_benefit_design", "array_check_count",
        "historical_prefixes_pass", "selected_fine_outcomes_and_labels_agree", "new_integrations", "reused_integrations",
        "represented_panel_integrations", "original_artifacts_unchanged", "interrupted_prefix", "panel")}
    print(json.dumps(compact, indent=2, allow_nan=False), flush=True)
    return 0 if all(report[k] for k in FLAGS) else 1


def supervise(job, lock_fd):
    meta, launch = read(job / "status.json"), read(job / "launch.json")
    run = Path(launch["run"])
    deadline = time.monotonic()+3600
    meta.update(supervisor_pid=os.getpid(), supervisor_session=os.getsid(0))

    def update(pid=None):
        meta.update(heartbeat_utc=now(), heartbeat_epoch=time.time())
        if pid is not None:
            meta["child_pid"] = pid
        progress = run / CASE_ID / "progress.json"
        if progress.exists():
            meta["replacement_rounds_complete"] = len(read(progress))
        write_status(job / "status.json", meta)

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Recovery interrupted by signal {signum}")

    def child(command, name, timeout):
        remaining = deadline-time.monotonic()
        require(remaining > 0, "Recovery total deadline reached")
        return run_child(command, job / name, min(timeout, remaining), update)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    rc = 1
    try:
        require(lock_fd is not None, "Inherited exclusive H3 lock required")
        os.fstat(lock_fd)
        require(check_hashes(ROOT, launch["hashes_sha256"]), "Launch execution files changed")
        require(check_hashes(job / "frozen", launch["new_frozen_hashes_sha256"]), "Frozen recovery files changed")
        require(shutil.disk_usage(ROOT).free >= 5*1024**3, "Require 5 GiB free; no deletion")
        meta["phase"] = "preflight"
        update()
        preflight_rc = child([sys.executable, "-B", str(THIS), "--prepare", str(job)], "preflight.log", 600)
        meta["preflight_exit_code"] = preflight_rc
        require(preflight_rc == 0, f"Preflight exited {preflight_rc}; no worker launched")
        meta["phase"] = "runner"
        update()
        began = time.monotonic()
        worker_rc = child([sys.executable, "-B", str(THIS), "--execute-worker", str(run)], "runner.log", 1800)
        elapsed = time.monotonic()-began
        meta["runner_exit_code"] = worker_rc
        record = dict(id=CASE_ID, execution_pass=False, status="timeout" if worker_rc == 124 else "finished",
            returncode=worker_rc, elapsed_seconds=elapsed, attempt_kind="runtime_only_full_case_restart")
        if (run / CASE_ID / "result.json").exists():
            record["result"] = read(run / CASE_ID / "result.json")
            record["execution_pass"] = worker_rc == 0 and record["result"]["execution_pass"]
        write_status(run / "replacement_record.json", record)
        require(record["execution_pass"], f"Replacement exited {worker_rc}; no retry or completed-panel claim")
        summary = combine_summary(read(run / "original_failed_summary.json"), record, read(run / "recovery_manifest.json"),
            file_hash(run / "recovery_manifest.json"))
        write_status(run / "summary.json", summary)
        meta.update(phase="independent_audit", completed_cases=1, valid_cases=1, combined_confirmation_valid_cases=39)
        update()
        audit_rc = child([sys.executable, "-B", str(THIS), "--audit", str(run)], "audit.log", 600)
        meta["audit_exit_code"] = audit_rc
        require(audit_rc == 0, f"Independent audit exited {audit_rc}; review required")
        report = read(run / "independent_audit.json")
        meta.update(phase="complete", quality_gate=report["quality_gate"], independent_checks=report["array_check_count"],
            ready_for_benefit_design=report["ready_for_benefit_design"],
            original_artifacts_unchanged=report["original_artifacts_unchanged"], panel=report["panel"],
            next_action="Review completed composite confirmation; no H4/H5 launch" if report["quality_gate"] else "Review numerical/control disagreement; no retuning or H4/H5 launch")
        rc = 0
    except BaseException as error:
        meta.update(phase="failed", error=f"{type(error).__name__}: {error}")
        print(meta["error"], file=sys.stderr, flush=True)
    finally:
        meta.update(exit_code=rc, finished_utc=now())
        update()
        if lock_fd is not None:
            os.close(lock_fd)
    return rc


def launch():
    JOBS.mkdir(parents=True, exist_ok=True)
    with (ROOT / "runs/reliability-overnight.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("An H3 supervisor already holds the lock; poll it")
        require(shutil.disk_usage(ROOT).free >= 5*1024**3, "Require 5 GiB free; no deletion")
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        hashes = dict(read(ORIGINAL / "summary.json")["hashes_sha256"])
        require(check_hashes(ROOT, hashes), "Original execution files have changed")
        hashes.update({str(p.relative_to(ROOT)): file_hash(p) for p in NEW_FILES})
        job = Path(tempfile.mkdtemp(prefix="reliability-recovery-"+stamp+"-", dir=JOBS))
        run = Path(tempfile.mkdtemp(prefix="reliability-confirmation-recovery-"+stamp+"-", dir=ROOT / "runs"))
        (job / "frozen").mkdir()
        for p in NEW_FILES:
            shutil.copyfile(p, job / "frozen" / p.name)
        frozen = {p.name: hashes[str(p.relative_to(ROOT))] for p in NEW_FILES}
        require(check_hashes(job / "frozen", frozen), "Recovery files changed during freezing")
        write_status(job / "launch.json", dict(run=str(run), launched_utc=now(), hashes_sha256=hashes,
            new_frozen_hashes_sha256=frozen, preflight_timeout_seconds=600, worker_timeout_seconds=1800,
            audit_timeout_seconds=600, total_timeout_seconds=3600))
        write_status(job / "status.json", dict(job=str(job), run=str(run), phase="launching", launched_utc=now(),
            heartbeat_epoch=time.time(), heartbeat_utc=now(), planned_cases=1, completed_cases=0, valid_cases=0,
            original_completed_cases_reused=38, replacement_rounds_complete=0, replacement_rounds_planned=12))
        with (job / "supervisor.log").open("x") as log:
            child = subprocess.Popen([sys.executable, "-B", str(THIS), "--supervise", str(job), "--lock-fd", str(lock.fileno())],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, pass_fds=(lock.fileno(),))
    print(json.dumps(dict(job=str(job), run=str(run), supervisor_pid=child.pid,
        status_command=f".venv/bin/python -B scripts/recover_reliability.py --status {job.relative_to(ROOT)}"), indent=2), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--launch", action="store_true")
    options.add_argument("--status", type=Path)
    options.add_argument("--supervise", type=Path, help=argparse.SUPPRESS)
    options.add_argument("--prepare", type=Path, help=argparse.SUPPRESS)
    options.add_argument("--execute-worker", type=Path, help=argparse.SUPPRESS)
    options.add_argument("--audit", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.status.resolve()), indent=2))
        return 0
    if args.supervise or args.prepare:
        job = (args.supervise or args.prepare).resolve()
        require(job.parent == JOBS and job.name.startswith("reliability-recovery-"), "Unexpected recovery job path")
        run = Path(read(job / "launch.json")["run"])
        require(run.parent == ROOT / "runs" and run.name.startswith("reliability-confirmation-recovery-"), "Unexpected recovery run")
        return supervise(job, args.lock_fd) if args.supervise else prepare(run, job)
    if args.execute_worker or args.audit:
        run = (args.execute_worker or args.audit).resolve()
        require(run.parent == ROOT / "runs" and run.name.startswith("reliability-confirmation-recovery-"), "Unexpected recovery run path")
        if args.audit:
            return audit_recovery(run)
        manifest = read(run / "recovery_manifest.json")
        require(check_hashes(ROOT, manifest["execution_hashes_sha256"]), "Execution changed before worker")
        spec = run / CASE_ID / "spec.json"
        require(file_hash(spec) == manifest["spec_sha256"], "Worker specification changed")
        os.chdir(spec.parent)
        os.execv(sys.executable, [sys.executable, "-B", str(RUNNER), "--worker", str(spec)])
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
