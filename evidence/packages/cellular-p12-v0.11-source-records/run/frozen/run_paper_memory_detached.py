"""Detached six-hour P1 experiment; no retries, retuning or downstream launch."""

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

from paper_memory_design import ROOT, LOCAL_FILES, digest, validate_config, execution_manifest
from run_rewrite_tradeoff_detached import now, run_child, status, write_status

JOBS = ROOT / "runs/jobs"
RUNNER = ROOT / "scripts/run_paper_memory.py"
ANALYZER = ROOT / "scripts/analyze_paper_memory.py"
CONFIG = ROOT / "configs/paper_memory_v1.json"


def discover_run(job):
    log = job / "runner.log"
    if log.exists():
        for line in log.read_text(errors="replace").splitlines():
            if line.startswith("Run artifacts: "):
                run = Path(line.removeprefix("Run artifacts: ")).resolve()
                if run.parent != ROOT / "runs" or not run.name.startswith("paper-memory-"):
                    raise ValueError("Unexpected P1 output directory")
                return run
    return None


def launch():
    validate_config(json.loads(CONFIG.read_text()))
    JOBS.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / "runs/paper-memory.lock").open("a+")
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("P1 is already supervised; poll it instead of duplicating it")
        if shutil.disk_usage(ROOT).free < 5*1024**3:
            raise RuntimeError("Require 5 GiB free")
        hashes = execution_manifest()
        job = Path(tempfile.mkdtemp(prefix="paper-memory-"+time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())+"-",dir=JOBS))
        (job / "frozen").mkdir()
        frozen = {}
        for path in LOCAL_FILES:
            if path.name in frozen:
                raise ValueError("Frozen filename collision")
            shutil.copyfile(path,job / "frozen" / path.name)
            frozen[path.name] = hashes[str(path.relative_to(ROOT))]
            if digest(job / "frozen" / path.name) != frozen[path.name]:
                raise RuntimeError("Launch input changed while freezing")
        write_status(job / "launch.json",dict(launched_utc=now(),hashes_sha256=hashes,
            frozen_hashes_sha256=frozen,runner_watchdog_seconds=21900,audit_watchdog_seconds=900,
            total_watchdog_seconds=23400,automatic_retry=False,downstream_launch=False))
        write_status(job / "status.json",dict(job=str(job),phase="launching",launched_utc=now(),
            heartbeat_utc=now(),heartbeat_epoch=time.time(),completed_cases=0,valid_cases=0,planned_cases=42))
        command = [sys.executable,"-B",str(Path(__file__).resolve()),"--supervise",str(job),"--lock-fd",str(lock.fileno())]
        with (job / "supervisor.log").open("x") as output:
            process = subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,
                stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
    finally:
        lock.close()
    print(json.dumps(dict(job=str(job),supervisor_pid=process.pid,
        status_command=f".venv/bin/python -B scripts/run_paper_memory_detached.py --status {job.relative_to(ROOT)}",
        note="Check a subsequent heartbeat; a launcher return alone does not prove persistent execution"),indent=2),flush=True)
    return 0


def supervise(job,lock_fd):
    launch_record = json.loads((job / "launch.json").read_text())
    meta = json.loads((job / "status.json").read_text())
    meta.update(supervisor_pid=os.getpid(),supervisor_session=os.getsid(0))
    deadline = time.monotonic()+23400

    def update(pid=None):
        meta.update(heartbeat_utc=now(),heartbeat_epoch=time.time())
        if pid is not None:
            meta["child_pid"] = pid
        run = discover_run(job)
        if run is not None:
            meta["run"] = str(run)
            path = run / "summary.json"
            if path.exists():
                summary = json.loads(path.read_text())
                meta.update(completed_cases=len(summary["cases"]),
                    valid_cases=sum(bool(r["execution_pass"]) for r in summary["cases"]),
                    benchmark_gate_pass=(summary.get("benchmark_gate") or {}).get("quality_gate"))
                if meta["phase"] in ("preflight","source_benchmarks","memory_extension"):
                    meta["phase"] = "memory_extension" if meta["benchmark_gate_pass"] else "source_benchmarks"
        write_status(job / "status.json",meta)

    def child(command,name,limit):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Overall P1 supervisor limit")
        return run_child(command,job / name,min(limit,remaining),update)

    def interrupted(signum,frame):
        raise KeyboardInterrupt(f"Signal {signum}")

    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    code = 1
    try:
        if lock_fd is None:
            raise ValueError("An inherited exclusive lock is required")
        os.fstat(lock_fd)
        if not all(digest(ROOT / p) == h for p,h in launch_record["hashes_sha256"].items()):
            raise RuntimeError("Execution files changed after launch")
        if not all(digest(job / "frozen" / p) == h for p,h in launch_record["frozen_hashes_sha256"].items()):
            raise RuntimeError("Frozen launch files changed")
        if shutil.disk_usage(ROOT).free < 5*1024**3:
            raise RuntimeError("Require 5 GiB free")
        meta["phase"] = "preflight"
        update()
        rc = child([sys.executable,"-B",str(RUNNER),"--config",str(CONFIG)],"runner.log",21900)
        meta["runner_exit_code"] = rc
        if rc:
            raise RuntimeError(f"Runner exited {rc}; no retry or downstream launch")
        run = discover_run(job)
        if run is None:
            raise RuntimeError("Runner did not identify its output")
        meta["phase"] = "independent_audit"
        update()
        rc = child([sys.executable,"-B",str(ANALYZER),str(run),"--save","--compact"],"audit.log",900)
        meta["audit_exit_code"] = rc
        if rc:
            raise RuntimeError(f"Independent audit exited {rc}")
        audit = json.loads((run / "independent_audit.json").read_text())
        if not audit["quality_gate"]:
            raise RuntimeError("Audit quality gate did not pass")
        meta.update(phase="complete",quality_gate=True,ready_for_interpretation=True,
            independent_checks=audit["independent_check_count"],source_benchmarks_pass=audit["benchmark_gate"]["quality_gate"],
            selected_fine_agreement=audit["all_selected_fine_agree"],
            next_action="Review population conversion, removal and onward memory; no follow-on run launched")
        code = 0
    except BaseException as error:
        meta.update(phase="failed",error=f"{type(error).__name__}: {error}")
        print(meta["error"],file=sys.stderr,flush=True)
    finally:
        meta.update(exit_code=code,finished_utc=now())
        update()
        if lock_fd is not None:
            os.close(lock_fd)
    return code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--launch",action="store_true")
    g.add_argument("--status",type=Path)
    g.add_argument("--supervise",type=Path,help=argparse.SUPPRESS)
    p.add_argument("--lock-fd",type=int,help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.status:
        print(json.dumps(status(args.status.resolve()),indent=2))
        return 0
    if args.supervise:
        job = args.supervise.resolve()
        if job.parent != JOBS:
            raise ValueError("Supervisor outside runs/jobs")
        return supervise(job,args.lock_fd)
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
