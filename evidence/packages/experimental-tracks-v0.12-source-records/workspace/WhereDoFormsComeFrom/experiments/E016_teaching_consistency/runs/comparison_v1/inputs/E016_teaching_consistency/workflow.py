"""Benchmark forecast, durable orchestration, and optional detached launch."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E016_teaching_consistency.run import input_paths

FORECAST = HERE / "analysis/forecast_v1.json"


def forecast():
    benchmark = HERE / "runs/benchmark_v1"
    worker = json.loads((benchmark / "worker_900016.json").read_text())
    audit = json.loads((benchmark / "INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(benchmark / "COMPLETE.json")
    check_inputs(benchmark)
    seconds = 2*(worker["seconds"]+audit["seconds"])*math.ceil(32/12)+90
    result = dict(created_utc=utc(), blocks=32, workers=12, numerical_threads=1,
        formula="2*(worker_seconds+audit_seconds)*ceil(32/12)+90", worker_seconds=worker["seconds"],
        audit_seconds=audit["seconds"], forecast_seconds=seconds, detached_required=seconds > 600,
        benchmark_complete_sha256=sha(benchmark / "COMPLETE.json"),
        benchmark_audit_sha256=sha(benchmark / "INDEPENDENT_AUDIT.json"),
        inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in input_paths()})
    assert not FORECAST.exists()
    dump(FORECAST, result)
    print(json.dumps(result, indent=2), flush=True)


def execute(job, output):
    started = time.monotonic()
    check_inputs(job)
    dump(job / "pid.json", dict(pid=os.getpid(), recorded_utc=utc()))
    try:
        for stage, command in (
            ("simulation", ["run.py", "--output", str(output), "--workers", "12"]),
            ("audit", ["audit.py", str(output), "--workers", "12"]),
            ("figures", ["plot.py", str(output)]),
        ):
            dump(job / "status.json", dict(status="RUNNING", stage=stage, utc=utc(), pid=os.getpid()))
            print("Starting", stage, flush=True)
            with (job / "workflow.log").open("a") as log:
                subprocess.run([sys.executable, "-B", str(HERE / command[0]), *command[1:]],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        dump(job / "status.json", dict(status="COMPLETE", utc=utc(), seconds=time.monotonic()-started,
            scientific_complete_sha256=sha(output / "COMPLETE.json"),
            audit_sha256=sha(output / "INDEPENDENT_AUDIT.json"),
            figure_provenance_sha256=sha(HERE / "figures" / output.name / "provenance.json")))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(job / "status.json", dict(status="FAILED", utc=utc(), traceback=traceback.format_exc()))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast", action="store_true")
    parser.add_argument("--run-name", default="comparison_v1")
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    cap_cpus()
    if args.forecast:
        forecast()
        return
    if not re.fullmatch(r"[a-z0-9_]+", args.run_name): raise ValueError("Invalid run name")
    output = HERE / "runs" / args.run_name
    job = HERE / "jobs" / args.run_name
    estimate = json.loads(FORECAST.read_text())
    for relative, digest in estimate["inputs_sha256"].items(): assert sha(ROOT / relative) == digest
    if args.child:
        execute(job, output)
        return
    if estimate["detached_required"] and not args.detach: raise ValueError("Forecast exceeds 600 seconds; detached execution required")
    if output.exists(): raise FileExistsError(output)
    new_run(job, input_paths()+[FORECAST], dict(experiment="E016", detached=args.detach,
        run_name=args.run_name, forecast_seconds=estimate["forecast_seconds"]))
    dump(job / "status.json", dict(status="PREPARED", utc=utc()))
    if args.detach:
        with (job / "launcher.log").open("x") as log:
            process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--run-name", args.run_name],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(job / "launch.json", dict(pid=process.pid, utc=utc(), command="workflow.py --child", job=str(job)))
        print("Detached PID", process.pid, "status:", job / "status.json", flush=True)
    else:
        execute(job, output)


if __name__ == "__main__":
    main()
