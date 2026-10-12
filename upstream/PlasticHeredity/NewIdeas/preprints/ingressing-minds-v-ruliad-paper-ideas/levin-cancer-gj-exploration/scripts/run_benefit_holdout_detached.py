"""Detached H4b panel and audit only; bounded, no retry or H5 launch."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from benefit_holdout_design import PREDECESSOR, validate_config
from run_benefit_holdout import execution_files
from run_rewrite_tradeoff_detached import digest, now, run_child, status, write_status

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "runs/jobs"
RUNNER = ROOT / "scripts/run_benefit_holdout.py"
ANALYZER = ROOT / "scripts/analyze_benefit_holdout.py"
CONFIG = ROOT / "configs/benefit_holdout_v1.json"


def discover_run(job):
    log = job / "runner.log"
    if log.exists():
        for line in log.read_text(errors="replace").splitlines():
            if line.startswith("Run artifacts: "):
                run = Path(line.removeprefix("Run artifacts: ")).resolve()
                if run.parent != ROOT / "runs" or not run.name.startswith("benefit-holdout-"):
                    raise ValueError("Unexpected H4b artifact location")
                return run
    return None


def execution_manifest():
    old = json.loads((ROOT / PREDECESSOR / "summary.json").read_text())
    paths = set(execution_files()) | {ROOT / n for n in old["hashes_sha256"]}
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def launch():
    validate_config(json.loads(CONFIG.read_text()))
    JOBS.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / "runs/benefit-holdout.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("An H4b supervisor holds the lock; poll it, do not duplicate it")
    try:
        if shutil.disk_usage(ROOT).free < 5*1024**3:
            raise RuntimeError("Require 5 GiB free; no deletion")
        hashes, files = execution_manifest(), execution_files()
        job = Path(tempfile.mkdtemp(prefix="benefit-holdout-"+time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())+"-", dir=JOBS))
        frozen = job / "frozen"
        frozen.mkdir()
        frozen_hashes = {}
        for path in files:
            if path.name in frozen_hashes:
                raise ValueError("Frozen filename collision")
            (frozen / path.name).write_bytes(path.read_bytes())
            frozen_hashes[path.name] = hashes[str(path.relative_to(ROOT))]
            if digest(frozen / path.name) != frozen_hashes[path.name]:
                raise RuntimeError("Launch file changed while freezing")
        write_status(job / "launch.json", dict(launched_utc=now(), hashes_sha256=hashes,
            frozen_hashes_sha256=frozen_hashes, runner_watchdog_seconds=86700, audit_watchdog_seconds=1800,
            total_watchdog_seconds=90000, native_pilot_run=False, retuning=False, automatic_retry=False, H5_launch=False))
        write_status(job / "status.json", dict(job=str(job), phase="launching", launched_utc=now(),
            heartbeat_utc=now(), heartbeat_epoch=time.time(), planned_cases=144, completed_cases=0, valid_cases=0))
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--supervise", str(job), "--lock-fd", str(lock.fileno())]
        with (job / "supervisor.log").open("x") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
    finally:
        lock.close()
    print(json.dumps(dict(job=str(job), supervisor_pid=child.pid,
        status_command=f".venv/bin/python -B scripts/run_benefit_holdout_detached.py --status {job.relative_to(ROOT)}",
        note="Check a subsequent durable heartbeat; launch success alone is not liveness proof"), indent=2), flush=True)
    return 0


def supervise(job, lock_fd):
    launch_record = json.loads((job / "launch.json").read_text())
    meta = json.loads((job / "status.json").read_text())
    meta.update(supervisor_pid=os.getpid(), supervisor_session=os.getsid(0))
    deadline = time.monotonic()+90000

    def update(pid=None):
        meta.update(heartbeat_utc=now(), heartbeat_epoch=time.time())
        if pid is not None:
            meta["child_pid"] = pid
        run = discover_run(job)
        if run is not None:
            meta["run"] = str(run)
            summary = json.loads((run / "summary.json").read_text())
            meta.update(completed_cases=len(summary["cases"]), valid_cases=sum(bool(r["execution_pass"]) for r in summary["cases"]))
            meta["prefix_gate_pass"] = summary.get("prefix_gate", {}).get("quality_gate")
            if meta["phase"] in ("preflight_and_runner", "historical_controls", "holdout_runner"):
                meta["phase"] = "holdout_runner" if meta["prefix_gate_pass"] else "historical_controls"
        write_status(job / "status.json", meta)

    def child(command, name, timeout):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Overall H4b watchdog expired")
        return run_child(command, job / name, min(timeout, remaining), update)

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Supervisor interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    rc = 1
    try:
        if lock_fd is None:
            raise ValueError("Inherited exclusive lock required")
        os.fstat(lock_fd)
        if not all(digest(ROOT / n) == h for n, h in launch_record["hashes_sha256"].items()):
            raise RuntimeError("Execution/configuration files changed after launch")
        if not all(digest(job / "frozen" / n) == h for n, h in launch_record["frozen_hashes_sha256"].items()):
            raise RuntimeError("Frozen launch files changed")
        if shutil.disk_usage(ROOT).free < 5*1024**3:
            raise RuntimeError("Insufficient disk space")
        meta["phase"] = "preflight_and_runner"
        update()
        code = child([sys.executable, "-B", str(RUNNER), "--config", str(CONFIG)], "runner.log", 86700)
        meta["runner_exit_code"] = code
        if code != 0:
            raise RuntimeError(f"H4b runner exited {code}; no retry or downstream launch")
        run = discover_run(job)
        if run is None:
            raise RuntimeError("Runner did not identify artifacts")
        meta["phase"] = "independent_audit"
        update()
        code = child([sys.executable, "-B", str(ANALYZER), str(run), "--save", "--compact"], "audit.log", 1800)
        meta["audit_exit_code"] = code
        if code != 0:
            raise RuntimeError(f"H4b independent audit exited {code}")
        audit = json.loads((run / "independent_audit.json").read_text())
        meta.update(phase="complete", quality_gate=audit["quality_gate"], ready_for_interpretation=audit["ready_for_interpretation"],
            independent_checks=audit["array_check_count"], historical_benchmarks_pass=audit["historical_benchmarks_pass"],
            selected_fine_agreement=audit["selected_fine_agreement"],
            next_action="Review H4b held-out benefit boundaries and binary-reference mismatches; no H5 launched")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--launch", action="store_true")
    group.add_argument("--status", type=Path)
    group.add_argument("--supervise", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.status.resolve()), indent=2))
        return 0
    if args.supervise:
        job = args.supervise.resolve()
        if job.parent != JOBS:
            raise ValueError("Supervisor job outside runs/jobs")
        return supervise(job, args.lock_fd)
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
