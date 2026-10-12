"""Detached simulation → independent audit → fixed figures, with durable status."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import run as study


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--detach", action="store_true")
    args = parser.parse_args(); study.cap_cpus()
    output = args.output.resolve(); forecast_path = args.forecast.resolve()
    if not output.is_relative_to(study.HERE / "runs"): raise ValueError("Local E014 run required")
    if not forecast_path.is_relative_to(study.HERE): raise ValueError("Local forecast required")
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    forecast = json.loads(forecast_path.read_text())
    assert forecast["blocks"] == list(study.BLOCKS) and forecast["workers"] == args.workers
    for rel, digest in forecast["inputs_sha256"].items(): assert study.sha(study.ROOT / rel) == digest, rel
    benchmark = study.ROOT / forecast["benchmark"]
    from E014_long_renewal.audit import verify
    verify(benchmark)
    bench_audit = json.loads((benchmark / "INDEPENDENT_AUDIT.json").read_text())
    assert bench_audit["status"] == "PASS" and bench_audit["complete_sha256"] == study.sha(benchmark / "COMPLETE.json")
    assert study.sha(benchmark / "INDEPENDENT_AUDIT.json") == forecast["benchmark_audit_sha256"]
    measured = json.loads((benchmark / f"worker_{study.BENCHMARK}.json").read_text())["seconds"]
    expected = 2 * (measured + bench_audit["seconds"]) * math.ceil(len(study.BLOCKS) / args.workers) + 120
    assert expected == forecast["forecast_seconds"]
    control = study.HERE / "analysis"; control.mkdir(exist_ok=True)
    status_path = control / f"{output.name}_status.json"
    launch_path = control / f"{output.name}_launch.json"
    log_path = control / f"{output.name}.log"
    if args.detach:
        if output.exists() or status_path.exists() or launch_path.exists(): raise FileExistsError("Workflow already exists")
        assert expected > 600, "Only forecasts over ten minutes need detachment"
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--output", str(output),
                   "--forecast", str(forecast_path), "--workers", str(args.workers)]
        study.dump(status_path, dict(status="LAUNCHING", time=study.utc(), output=str(output)))
        with log_path.open("x") as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     cwd=study.ROOT, start_new_session=True, close_fds=True)
        receipt = dict(status="LAUNCHED", pid=child.pid, launched_utc=study.utc(), command=command,
            output=str(output), log=str(log_path), status_file=str(status_path), forecast_sha256=study.sha(forecast_path),
            forecast_seconds=expected, workers=args.workers, numerical_threads=1)
        study.dump(launch_path, receipt)
        print(json.dumps(receipt, indent=2), flush=True)
        return
    started = time.monotonic()
    base = dict(pid=os.getpid(), started_utc=study.utc(), output=str(output), forecast_sha256=study.sha(forecast_path),
                workers=args.workers, numerical_threads=1)
    phase = "starting"
    try:
        for phase, command in (
            ("simulation", [sys.executable, "-B", str(study.HERE / "run.py"), "--output", str(output), "--workers", str(args.workers)]),
            ("independent_audit", [sys.executable, "-B", str(study.HERE / "audit.py"), str(output), "--workers", str(args.workers)]),
            ("figures", [sys.executable, "-B", str(study.HERE / "plot.py"), str(output)])):
            study.dump(status_path, dict(**base, status="RUNNING", phase=phase, updated_utc=study.utc()))
            subprocess.run(command, check=True, stdin=subprocess.DEVNULL)
        summary = json.loads((output / "summary.json").read_text())
        study.dump(status_path, dict(**base, status="COMPLETE", phase="complete", finished_utc=study.utc(),
            seconds=time.monotonic() - started, scientific_status=summary["status"],
            complete_sha256=study.sha(output / "COMPLETE.json"), audit_sha256=study.sha(output / "INDEPENDENT_AUDIT.json"),
            report=str(output / "REPORT.md"), figures=str(study.HERE / "figures" / output.name)))
    except BaseException:
        study.dump(status_path, dict(**base, status="FAILED", phase=phase, failed_utc=study.utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
