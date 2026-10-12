"""Benchmark, conservative runtime/storage forecast and durable detached workflow."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E029_maturing_renewal.run import input_paths

FORECAST = HERE/"analysis/forecast_v1.json"
BENCHMARK_FORECAST = HERE/"analysis/benchmark_forecast_v1.json"
FIXTURES = HERE/"analysis/fixtures_v1.json"


def fixtures():
    receipt = json.loads(FIXTURES.read_text())
    assert receipt["status"] == "PASS" and receipt["tests"] == 8
    for relative, digest in receipt["inputs_sha256"].items(): assert sha(ROOT/relative) == digest
    assert receipt["log_sha256"] == sha(HERE/"analysis/fixtures_v1.log")


def forecast():
    benchmark = HERE/"runs/benchmark_v1"
    worker = json.loads((benchmark/"worker_900029.json").read_text())
    audit = json.loads((benchmark/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(benchmark/"COMPLETE.json")
    assert audit["audit_code_sha256"] == sha(HERE/"audit.py")
    check_inputs(benchmark)
    fixtures()
    complete = json.loads((benchmark/"COMPLETE.json").read_text())
    for relative, digest in complete["outputs_sha256"].items(): assert sha(benchmark/relative) == digest
    affinity = cap_cpus(8)
    workers = min(8, len(affinity) or (os.cpu_count() or 1))
    seconds = 2.5*(worker["seconds"]+audit["seconds"])*4*4*math.ceil(32/workers)+90
    benchmark_bytes = sum(p.stat().st_size for p in benchmark.rglob("*") if p.is_file())
    source_bytes = (benchmark/"source_900029.npz").stat().st_size
    storage = source_bytes*32+(benchmark_bytes-source_bytes)*4*32+1024**3
    available = shutil.disk_usage(HERE).free
    if storage > available: raise RuntimeError(f"Insufficient storage: need {storage}, available {available}")
    result = dict(created_utc=utc(), blocks=32, workers=workers, cpu_affinity=affinity, numerical_threads=1,
        benchmark_lineages_per_founder=1, cohort_lineages_per_founder=4,
        benchmark_read_steps=512, scientific_read_steps=2048, throughput_only_benchmark=True,
        formula="2.5*(worker_seconds+audit_seconds )*4_read_duration*4_recipients*ceil(32/workers)+90", worker_seconds=worker["seconds"],
        audit_seconds=audit["seconds"], forecast_seconds=seconds, detached_required=seconds > 600,
        benchmark_bytes=benchmark_bytes, benchmark_source_bytes=source_bytes,
        storage_formula="source_bytes*32+(benchmark_bytes-source_bytes)*4*32+1GiB", storage_with_reserve_bytes=storage, available_bytes=available,
        benchmark_complete_sha256=sha(benchmark/"COMPLETE.json"), benchmark_audit_sha256=sha(benchmark/"INDEPENDENT_AUDIT.json"),
        fixture_receipt_sha256=sha(FIXTURES), inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in input_paths()})
    assert not FORECAST.exists()
    dump(FORECAST, result)
    print(json.dumps(result, indent=2), flush=True)


def benchmark_forecast():
    fixtures()
    source = ROOT/'E027_selective_renewal/runs/benchmark_v1'
    check_inputs(source)
    complete = json.loads((source/'COMPLETE.json').read_text())
    for rel, digest in complete['outputs_sha256'].items(): assert sha(source/rel) == digest
    old_audit = json.loads((source/'INDEPENDENT_AUDIT.json').read_text())
    assert old_audit['status'] == 'PASS' and old_audit['complete_sha256'] == sha(source/'COMPLETE.json')
    worker = json.loads((source/'worker_900027.json').read_text())
    seconds = 1.5*(worker['seconds']+old_audit['seconds'])*(42/34)*((512+128)/(2048+128))+60
    result = dict(created_utc=utc(), blocks=1, workers=1, cpu_affinity=cap_cpus(8), numerical_threads=1,
        formula='1.5*(E027_worker_seconds+E027_audit_seconds)*(42/34)*((512+128)/(2048+128))+60',
        source_worker_seconds=worker['seconds'], source_audit_seconds=old_audit['seconds'],
        source_complete_sha256=sha(source/'COMPLETE.json'), source_audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'),
        benchmark_read_steps=512, scientific_read_steps=2048, excluded_throughput_only=True,
        forecast_seconds=seconds, detached_required=seconds > 600, storage_with_reserve_bytes=256*1024**2,
        fixture_receipt_sha256=sha(FIXTURES), inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in input_paths()})
    assert not BENCHMARK_FORECAST.exists()
    dump(BENCHMARK_FORECAST, result)
    print(json.dumps(result, indent=2), flush=True)


def execute(job, output, benchmark=False):
    started = time.monotonic()
    check_inputs(job)
    dump(job/"pid.json", dict(pid=os.getpid(), recorded_utc=utc()))
    workers = str(json.loads((job/"manifest.json").read_text())["contract"]["workers"])
    run_args = ["--output", str(output), "--workers", workers]
    if benchmark: run_args.append("--benchmark")
    try:
        for stage, command in (("simulation", ["run.py", *run_args]),
            ("audit", ["audit.py", str(output), "--workers", workers]),
            ("figures", ["plot.py", str(output)])):
            dump(job/"status.json", dict(status="RUNNING", stage=stage, utc=utc(), pid=os.getpid()))
            print("Starting", stage, flush=True)
            with (job/"workflow.log").open("a") as log:
                subprocess.run([sys.executable, "-B", str(HERE/command[0]), *command[1:]], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        dump(job/"status.json", dict(status="COMPLETE", utc=utc(), seconds=time.monotonic()-started,
            scientific_complete_sha256=sha(output/"COMPLETE.json"), audit_sha256=sha(output/"INDEPENDENT_AUDIT.json"),
            figure_provenance_sha256=sha(HERE/"figures"/output.name/"provenance.json")))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(job/"status.json", dict(status="FAILED", utc=utc(), traceback=traceback.format_exc()))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast", action="store_true")
    parser.add_argument("--benchmark-forecast", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--run-name", default="maturing_v1")
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    cap_cpus(8)
    if args.benchmark_forecast:
        benchmark_forecast()
        return
    if args.forecast:
        forecast()
        return
    if args.benchmark: args.run_name = "benchmark_v1"
    if not re.fullmatch(r"[a-z0-9_]+", args.run_name): raise ValueError("Invalid run name")
    output, job = HERE/"runs"/args.run_name, HERE/"jobs"/args.run_name
    fixtures()
    estimate_path = BENCHMARK_FORECAST if args.benchmark else FORECAST
    estimate = json.loads(estimate_path.read_text())
    if estimate:
        for relative, digest in estimate["inputs_sha256"].items(): assert sha(ROOT/relative) == digest
    assert cap_cpus(8) == estimate["cpu_affinity"], "CPU affinity differs from forecast"
    if args.child:
        execute(job, output, args.benchmark)
        return
    if estimate and estimate["detached_required"] and not args.detach: raise ValueError("Forecast exceeds 600 seconds; detached required")
    if estimate and shutil.disk_usage(HERE).free < estimate["storage_with_reserve_bytes"]: raise RuntimeError("Storage reserve no longer available")
    if output.exists(): raise FileExistsError(output)
    new_run(job, input_paths()+[FIXTURES, estimate_path],
        dict(experiment="E029", detached=args.detach, run_name=args.run_name,
             benchmark=args.benchmark, workers=estimate["workers"] if estimate else 1,
             forecast_seconds=estimate["forecast_seconds"] if estimate else None))
    dump(job/"status.json", dict(status="PREPARED", utc=utc()))
    if args.detach:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--run-name", args.run_name]
        if args.benchmark: command.append("--benchmark")
        with (job/"launcher.log").open("x") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(job/"launch.json", dict(pid=process.pid, utc=utc(), command=command, job=str(job)))
        print("Detached PID", process.pid, "status:", job/"status.json", flush=True)
    else:
        execute(job, output, args.benchmark)


if __name__ == "__main__": main()
