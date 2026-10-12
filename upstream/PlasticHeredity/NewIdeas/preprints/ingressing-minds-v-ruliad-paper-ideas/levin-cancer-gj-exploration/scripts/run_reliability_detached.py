"""One detached, bounded overnight H3 chain; no tuning, retries or H4/H5 launch."""

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

from run_rewrite_tradeoff_detached import digest, now, run_child, write_status

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "runs/jobs"
RUNNER = ROOT / "scripts/run_reliability.py"
ANALYZER = ROOT / "scripts/analyze_reliability.py"
CONFIGS = {s: ROOT / f"configs/reliability_{s}_v1.json" for s in ("screen", "confirmation")}
NEW_FILES = [RUNNER, ANALYZER, Path(__file__).resolve(), ROOT / "scripts/bounded_overnight.py",
    ROOT / "scripts/reliability_relay.py", ROOT / "scripts/test_reliability.py",
    ROOT / "scripts/test_detached_reliability.py", *CONFIGS.values(),
    ROOT / "RELIABILITY_SCREEN_PROTOCOL.md", ROOT / "RELIABILITY_CONFIRMATION_PROTOCOL.md"]


def status(job):
    meta = json.loads((job / "status.json").read_text())
    meta["heartbeat_age_seconds"] = max(0., time.time()-meta["heartbeat_epoch"])
    meta["heartbeat_stale"] = meta["phase"] not in ("complete", "failed", "stopped_after_screen") and meta["heartbeat_age_seconds"] > 30
    if meta["heartbeat_stale"]:
        meta["warning"] = "No recent heartbeat; do not infer liveness or relaunch automatically"
    return meta


def discover_run(folder, stage):
    log = folder / "runner.log"
    if not log.exists():
        return None
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("Run artifacts: "):
            path = Path(line.removeprefix("Run artifacts: ")).resolve()
            if path.parent != ROOT / "runs" or not path.name.startswith("reliability-"+stage+"-"):
                raise ValueError("Unexpected stage artifact path")
            return path
    return None


def execution_manifest():
    old = json.loads((ROOT / "runs/rewrite-tradeoff-20260906T233148Z-3fq2onfn/summary.json").read_text())
    paths = {ROOT / n for n in old["hashes_sha256"]} | set(NEW_FILES)
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def launch():
    JOBS.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / "runs/reliability-overnight.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("An overnight reliability supervisor already holds the lock; poll it")
    try:
        if shutil.disk_usage(ROOT).free < 5*1024**3:
            raise RuntimeError("Require at least 5 GiB free; no data will be deleted")
        hashes = execution_manifest()
        job = Path(tempfile.mkdtemp(prefix="reliability-overnight-"+time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())+"-", dir=JOBS))
        write_status(job / "launch.json", dict(launched_utc=now(), hashes_sha256=hashes,
            runner_watchdog_seconds=14700, audit_watchdog_seconds=600, total_watchdog_seconds=30600,
            stage_order=["screen", "confirmation"], retuning=False))
        (job / "frozen").mkdir()
        for p in NEW_FILES:
            (job / "frozen" / p.name).write_bytes(p.read_bytes())
            if digest(job / "frozen" / p.name) != hashes[str(p.relative_to(ROOT))]:
                raise RuntimeError("Launch file changed during freeze")
        write_status(job / "status.json", dict(job=str(job), phase="launching", launched_utc=now(),
            heartbeat_utc=now(), heartbeat_epoch=time.time(), planned_cases=96, completed_cases=0, valid_cases=0, stages=[]))
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--supervise", str(job), "--lock-fd", str(lock.fileno())]
        with (job / "supervisor.log").open("x") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
    finally:
        lock.close()
    print(json.dumps(dict(job=str(job), supervisor_pid=child.pid,
        status_command=f".venv/bin/python -B scripts/run_reliability_detached.py --status {job.relative_to(ROOT)}",
        note="Verify a subsequent heartbeat after launch returns; screening and confirmation are fixed"), indent=2), flush=True)
    return 0


def supervise(job, lock_fd):
    launch_record = json.loads((job / "launch.json").read_text())
    meta = json.loads((job / "status.json").read_text())
    meta.update(supervisor_pid=os.getpid(), supervisor_session=os.getsid(0))
    deadline = time.monotonic()+30600
    current, folder, current_row = None, None, None

    def update(pid=None):
        meta.update(heartbeat_utc=now(), heartbeat_epoch=time.time())
        if pid is not None:
            meta["child_pid"] = pid
        if current_row is not None and folder is not None:
            run = discover_run(folder, current)
            if run:
                meta["run"] = str(run)
                current_row["run"] = str(run)
                summary_file = run / "summary.json"
                if summary_file.exists():
                    summary = json.loads(summary_file.read_text())
                    current_row.update(completed_cases=len(summary["cases"]),
                        valid_cases=sum(bool(c["execution_pass"]) for c in summary["cases"]))
        meta["completed_cases"] = sum(s.get("completed_cases", 0) for s in meta["stages"])
        meta["valid_cases"] = sum(s.get("valid_cases", 0) for s in meta["stages"])
        write_status(job / "status.json", meta)

    def run_stage_child(command, logfile, timeout):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Overall overnight deadline reached")
        return run_child(command, logfile, min(timeout, remaining), update)

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Supervisor interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    exit_code, screen_run = 1, None
    try:
        if lock_fd is None:
            raise ValueError("Inherited exclusive lock is required")
        os.fstat(lock_fd)
        for current in ("screen", "confirmation"):
            folder, current_row = None, None
            meta["current_stage"] = current
            if not all(digest(ROOT / name) == value for name, value in launch_record["hashes_sha256"].items()):
                raise RuntimeError("Execution/configuration files changed since initial launch")
            if not all(digest(job / "frozen" / p.name) == launch_record["hashes_sha256"][str(p.relative_to(ROOT))] for p in NEW_FILES):
                raise RuntimeError("Frozen launch files changed")
            if shutil.disk_usage(ROOT).free < 5*1024**3:
                raise RuntimeError("Low disk space before stage; no deletion or retry")
            folder = job / current
            folder.mkdir()
            current_row = dict(stage=current, phase="runner", planned_cases=57 if current == "screen" else 39, completed_cases=0, valid_cases=0)
            meta["stages"].append(current_row)
            meta.update(phase="runner", current_stage=current)
            update()
            command = [sys.executable, "-B", str(RUNNER), "--config", str(CONFIGS[current])]
            if current == "confirmation":
                command += ["--screen-run", str(screen_run)]
            rc = run_stage_child(command, folder / "runner.log", 14700)
            current_row["runner_exit_code"] = rc
            if rc != 0:
                raise RuntimeError(f"{current} runner exited {rc}; no retry")
            run = discover_run(folder, current)
            if run is None:
                raise RuntimeError("Runner omitted artifact location")
            meta["phase"] = current_row["phase"] = "independent_audit"
            update()
            rc = run_stage_child([sys.executable, "-B", str(ANALYZER), str(run), "--save", "--compact"], folder / "audit.log", 600)
            current_row["audit_exit_code"] = rc
            if rc != 0:
                raise RuntimeError(f"{current} audit exited {rc}")
            audit = json.loads((run / "independent_audit.json").read_text())
            current_row.update(phase="complete", finished_utc=now(), independent_checks=audit["array_check_count"],
                quality_gate=audit["quality_gate"], panel=audit["panel"])
            if current == "screen":
                screen_run = run
                if not audit["eligible_for_confirmation"]:
                    meta.update(phase="stopped_after_screen", confirmation_skipped=True,
                        next_action="Review screening control/numerical failure; no retuning or automatic retry")
                    exit_code = 0
                    break
            else:
                meta.update(phase="complete", ready_for_benefit_design=audit["ready_for_benefit_design"],
                    next_action="Review both panels; H4/H5 have not been launched")
                exit_code = 0
            update()
    except BaseException as error:
        meta.update(phase="failed", error=f"{type(error).__name__}: {error}")
        print(meta["error"], file=sys.stderr, flush=True)
    finally:
        meta.update(exit_code=exit_code, finished_utc=now())
        update()
        if lock_fd is not None:
            os.close(lock_fd)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--launch", action="store_true")
    options.add_argument("--status", type=Path)
    options.add_argument("--supervise", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.status.resolve()), indent=2))
        return 0
    if args.supervise:
        job = args.supervise.resolve()
        if job.parent != JOBS:
            raise ValueError("Supervisor job is outside runs/jobs")
        return supervise(job, args.lock_fd)
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
