"""Detached, bounded supervisor for the commitment-robustness panel only."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "runs" / "jobs"
RUNNER = ROOT / "scripts/run_commitment_robustness.py"
ANALYZER = ROOT / "scripts/analyze_commitment_robustness.py"
CONFIG = ROOT / "configs/commitment_robustness_v1.json"
LAUNCH_FILES = (RUNNER, ANALYZER, CONFIG, Path(__file__).resolve(),
    ROOT / "COMMITMENT_ROBUSTNESS_PROTOCOL.md", ROOT / "scripts/test_commitment_robustness.py",
    ROOT / "scripts/test_detached_robustness.py", ROOT / "scripts/robust_relay.py")


def now():
    return datetime.now(timezone.utc).isoformat()


def write_status(path, value):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(job):
    meta = json.loads((job / "status.json").read_text())
    meta["heartbeat_age_seconds"] = max(0., time.time() - meta["heartbeat_epoch"])
    meta["heartbeat_stale"] = meta["phase"] not in ("complete", "failed", "probe_complete") and meta["heartbeat_age_seconds"] > 30
    if meta["heartbeat_stale"]:
        meta["warning"] = "No recent heartbeat; do not infer that the job is running and do not relaunch automatically."
    return meta


def discover_run(job):
    log = job / "runner.log"
    if not log.exists():
        return None
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("Run artifacts: "):
            run = Path(line.removeprefix("Run artifacts: ")).resolve()
            if run.parent != ROOT / "runs" or not run.name.startswith("commitment-robustness-"):
                raise ValueError("Unexpected runner artifact location")
            return run
    return None


def terminate_owned(process):
    """Signal only a process group created here, never a PID from a status file."""
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


def run_child(command, logfile, timeout, update):
    env = os.environ.copy()
    env.update(PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg",
        MPLCONFIGDIR=str(ROOT / ".cache/matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
        OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    with logfile.open("x") as output:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while child.poll() is None:
                update(child.pid)
                if time.monotonic() >= deadline:
                    terminate_owned(child)
                    return 124
                time.sleep(min(5, max(.001, deadline - time.monotonic())))
            return child.returncode
        finally:
            terminate_owned(child)


def supervise(job, lock_fd=None):
    launch = json.loads((job / "launch.json").read_text())
    meta = json.loads((job / "status.json").read_text())
    meta.update(supervisor_pid=os.getpid(), supervisor_session=os.getsid(0))

    def update(pid=None):
        meta.update(heartbeat_utc=now(), heartbeat_epoch=time.time())
        if pid is not None:
            meta["child_pid"] = pid
        run = discover_run(job)
        if run:
            meta["run"] = str(run)
            path = run / "summary.json"
            if path.exists():
                summary = json.loads(path.read_text())
                meta.update(completed_cases=len(summary["cases"]), planned_cases=len(summary["config"]["cases"]),
                    valid_cases=sum(bool(c["execution_pass"]) for c in summary["cases"]))
        write_status(job / "status.json", meta)

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Supervisor interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    exit_code = 1
    try:
        if launch["probe"]:
            meta["phase"] = "probe_running"
            for _ in range(4):
                update()
                time.sleep(2)
            meta["phase"] = "probe_complete"
            exit_code = 0
        else:
            if lock_fd is None:
                raise ValueError("The experimental supervisor requires its inherited exclusive lock")
            os.fstat(lock_fd)
            if not all(digest(ROOT / n) == h for n, h in launch["hashes_sha256"].items()):
                raise RuntimeError("Launch files changed before supervision")
            meta["phase"] = "runner"
            update()
            rc = run_child([sys.executable, "-B", str(RUNNER)], job / "runner.log", 3900, update)
            meta["runner_exit_code"] = rc
            if rc != 0:
                raise RuntimeError(f"Runner exited {rc}; no retry or downstream launch")
            run = discover_run(job)
            if run is None:
                raise RuntimeError("Completed runner did not identify artifacts")
            meta["phase"] = "independent_audit"
            update()
            ac = run_child([sys.executable, "-B", str(ANALYZER), str(run), "--save", "--compact"], job / "audit.log", 300, update)
            meta["audit_exit_code"] = ac
            if ac != 0:
                raise RuntimeError(f"Independent audit exited {ac}")
            audit = json.loads((run / "independent_audit.json").read_text())
            meta.update(phase="complete", independent_checks=audit["array_check_count"],
                ready_for_stage3_design=audit["ready_for_stage3_design"],
                audited_branches=[dict(id=b["case"]["id"], **b["outcomes"]) for b in audit["branches"]],
                next_action="Review results before specifying or launching any downstream experiment")
            exit_code = 0
    except BaseException as error:
        meta.update(phase="failed", error=f"{type(error).__name__}: {error}")
        print(meta["error"], file=sys.stderr, flush=True)
    finally:
        meta.update(exit_code=exit_code, finished_utc=now())
        update()
        if lock_fd is not None:
            os.close(lock_fd)
    return exit_code


def launch(probe=False):
    JOBS.mkdir(parents=True, exist_ok=True)
    lock = None
    if not probe:
        lock = (ROOT / "runs/commitment-robustness.lock").open("a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise RuntimeError("A commitment-robustness supervisor already holds the lock; poll it instead")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job = Path(tempfile.mkdtemp(prefix=("detach-probe-" if probe else "commitment-robustness-") + stamp + "-", dir=JOBS))
    hashes = {} if probe else {str(p.relative_to(ROOT)): digest(p) for p in LAUNCH_FILES}
    write_status(job / "launch.json", dict(probe=probe, launched_utc=now(), hashes_sha256=hashes,
        runner_watchdog_seconds=3900, audit_watchdog_seconds=300))
    write_status(job / "status.json", dict(job=str(job), phase="launching", launched_utc=now(),
        heartbeat_epoch=time.time(), heartbeat_utc=now(), completed_cases=0, planned_cases=0 if probe else 36))
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--supervise", str(job)]
    pass_fds = ()
    if lock:
        command += ["--lock-fd", str(lock.fileno())]
        pass_fds = (lock.fileno(),)
    try:
        with (job / "supervisor.log").open("x") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True, pass_fds=pass_fds)
    finally:
        if lock:
            lock.close()
    print(json.dumps(dict(job=str(job), supervisor_pid=child.pid,
        status_command=f".venv/bin/python -B scripts/run_commitment_robustness_detached.py --status {job.relative_to(ROOT)}",
        note="Verify a later heartbeat after this launch command returns; launch success alone is not detachment proof"), indent=2), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--launch", action="store_true")
    options.add_argument("--probe", action="store_true", help="Eight-second detachment check, no simulator")
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
            raise ValueError("Supervisor jobs must be inside runs/jobs")
        return supervise(job, args.lock_fd)
    return launch(probe=args.probe)


if __name__ == "__main__":
    raise SystemExit(main())
