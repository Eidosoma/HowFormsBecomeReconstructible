"""Local, four-CPU qualification/freeze/benchmark/run entry point."""
import argparse
import contextlib
import datetime as dt
import hashlib
import io
import json
import multiprocessing as mp
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import traceback
import unittest

# Apply before loading NumPy or spawning any numerical worker.
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
for _name in THREAD_VARS:
    os.environ[_name] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import numpy as np
import numpy.core._multiarray_umath as numpy_core

from .audit import audit_block, audit_summary
from .model import generate_block, block_metrics, block_diagnostics
from .reporting import report_text, summarize
from .spec import SPEC

PROJECT = Path(__file__).resolve().parents[1]
RUNS = PROJECT / "runs-interface-maintenance"


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value, exclusive=False):
    path = Path(path)
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if exclusive:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    else:
        temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text())


def safe_root(path):
    root = Path(path).resolve()
    if root == RUNS.resolve() or RUNS.resolve() not in root.parents:
        raise ValueError("Run root must be a named capsule below fep-ideas/runs-interface-maintenance")
    return root


def cpu_limit():
    allowed = sorted(os.sched_getaffinity(0))
    if len(allowed) < SPEC["workers"]:
        raise RuntimeError("Four allowed CPUs are required")
    cpus = allowed[:SPEC["workers"]]
    os.sched_setaffinity(0, cpus)
    return cpus


def workflow_probe(queue):
    """Disposable spawned-process check; never generates scientific data."""
    queue.put({"pid": os.getpid(), "cpus": sorted(os.sched_getaffinity(0)),
               "threads": {key: os.environ.get(key) for key in THREAD_VARS}})


def source_hashes():
    paths = [PROJECT / "EXPERIMENT_IM3_CAUSAL_PROBE_V1.md",
             PROJECT / "requirements-im3-lock.txt",
             PROJECT / "tests/test_im3_causal_probe.py"]
    paths += sorted((PROJECT / "causal_probe").glob("*.py"))
    paths += [PROJECT / "learned_reference" / name for name in ("__init__.py", "model.py", "audit.py", "spec.py")]
    return {str(path.relative_to(PROJECT)): file_hash(path) for path in paths}


def environment():
    with contextlib.redirect_stdout(io.StringIO()) as capture:
        np.__config__.show()
    return {"python": sys.version, "executable": str(Path(sys.executable).resolve()),
            "executable_sha256": file_hash(sys.executable), "numpy": np.__version__,
            "numpy_core_sha256": file_hash(numpy_core.__file__),
            "numpy_config": capture.getvalue(), "cpus": sorted(os.sched_getaffinity(0)),
            "thread_environment": {key: os.environ.get(key) for key in THREAD_VARS}}


def qualify(root):
    root.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    env = environment()
    start = time.monotonic()
    name = "qualification-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log = root / (name + ".log")
    suite = unittest.defaultTestLoader.discover(str(PROJECT / "tests"), pattern="test_im3_causal_probe.py")
    with log.open("x") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = source_hashes()
    passed = result.wasSuccessful() and result.testsRun > 0 and before == after and not result.skipped
    receipt = {"passed": passed, "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "source_hashes": before, "source_stable": before == after,
               "environment": env, "completed_utc": utc(),
               "wall_seconds": time.monotonic() - start, "log_sha256": file_hash(log)}
    write_json(root / (name + ".json"), receipt, exclusive=True)
    print(log.read_text(), flush=True)
    print(json.dumps({"qualification": str(root / (name + '.json')), **{k: receipt[k] for k in ("passed", "tests", "wall_seconds")}}), flush=True)
    if not passed:
        raise RuntimeError("Qualification failed; no freeze or main run allowed")


def freeze(root):
    if (root / "FREEZE.json").exists():
        raise FileExistsError("This capsule is already frozen")
    candidates = sorted(root.glob("qualification-*.json"))
    if not candidates:
        raise RuntimeError("Qualification is required")
    receipt_path = candidates[-1]
    receipt = read_json(receipt_path)
    hashes, env = source_hashes(), environment()
    if not receipt["passed"] or receipt["source_hashes"] != hashes or receipt["environment"] != env:
        raise RuntimeError("Current source/environment lacks passed qualification")
    if file_hash(receipt_path.with_suffix(".log")) != receipt["log_sha256"]:
        raise RuntimeError("Qualification log changed")
    snapshot = root / "frozen_inputs"
    snapshot.mkdir()
    for relative, digest in hashes.items():
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT / relative, destination)
        if file_hash(destination) != digest:
            raise RuntimeError("Snapshot copy mismatch")
    value = {"study": SPEC["study"], "frozen_utc": utc(), "spec": SPEC,
             "source_hashes": hashes, "environment": env,
             "qualification": receipt_path.name,
             "qualification_sha256": file_hash(receipt_path)}
    write_json(root / "FREEZE.json", value, exclusive=True)
    print(json.dumps({"freeze": str(root / "FREEZE.json"), "sha256": file_hash(root / "FREEZE.json")}), flush=True)


def check_freeze(root):
    frozen = read_json(root / "FREEZE.json")
    if frozen["spec"] != SPEC or frozen["source_hashes"] != source_hashes() or frozen["environment"] != environment():
        raise RuntimeError("Frozen source, constants or environment changed")
    for relative, digest in frozen["source_hashes"].items():
        if file_hash(root / "frozen_inputs" / relative) != digest:
            raise RuntimeError("Frozen snapshot changed: " + relative)
    qualification = root / frozen["qualification"]
    receipt = read_json(qualification)
    if (file_hash(qualification) != frozen["qualification_sha256"] or not receipt["passed"]
            or file_hash(qualification.with_suffix(".log")) != receipt["log_sha256"]):
        raise RuntimeError("Qualification seal changed")
    return frozen


def run_block(job):
    phase, block, parent = job
    start, cpu_start = time.monotonic(), time.process_time()
    destination = Path(parent) / f"block-{block:03d}"
    destination.mkdir()
    arrays, metadata = generate_block(phase, block)
    np.savez(destination / "arrays.npz", **arrays)
    write_json(destination / "metadata.json", metadata, exclusive=True)
    with np.load(destination / "arrays.npz", allow_pickle=False) as saved:
        retained = {key: saved[key] for key in saved.files}
    result = audit_block(retained, read_json(destination / "metadata.json"))
    if len(os.sched_getaffinity(0)) != SPEC["workers"] or any(os.environ.get(key) != "1" for key in THREAD_VARS):
        raise RuntimeError("Worker CPU/thread contract violated")
    receipt = {"phase": phase, "block": block, "pid": os.getpid(),
               "cpus": sorted(os.sched_getaffinity(0)), "thread_environment": {key: os.environ[key] for key in THREAD_VARS},
               "arrays_sha256": file_hash(destination / "arrays.npz"),
               "metadata_sha256": file_hash(destination / "metadata.json"),
               "production_block_metrics": block_metrics(arrays).tolist(),
               "production_block_diagnostics": block_diagnostics(arrays),
               "independent_audit": result,
               "ambiguity_pairs_verified": metadata["ambiguity_pairs_verified"],
               "cpu_seconds": time.process_time() - cpu_start, "wall_seconds": time.monotonic() - start,
               "array_bytes": (destination / "arrays.npz").stat().st_size}
    write_json(destination / "REPLAY.json", receipt, exclusive=True)
    return receipt


def benchmark(root):
    check_freeze(root)
    folder = root / "benchmark"
    folder.mkdir()
    receipt = run_block(("benchmark", 0, str(folder)))
    forecast = 1.5 * SPEC["blocks"] * receipt["wall_seconds"] + 60
    projected = int(1.1 * SPEC["blocks"] * receipt["array_bytes"] + 32 * 1024 * 1024)
    value = {"freeze_sha256": file_hash(root / "FREEZE.json"), "completed_utc": utc(),
             "checked_block_wall_seconds": receipt["wall_seconds"],
             "forecast_seconds": forecast, "detach_required": forecast > 600,
             "projected_artifact_bytes": projected, "available_bytes": shutil.disk_usage(root).free,
             "benchmark_replay_sha256": file_hash(folder / "block-000/REPLAY.json")}
    check_freeze(root)
    write_json(root / "BENCHMARK.json", value, exclusive=True)
    print(json.dumps(value), flush=True)


def preflight(root):
    frozen = check_freeze(root)
    bench = read_json(root / "BENCHMARK.json")
    if bench["freeze_sha256"] != file_hash(root / "FREEZE.json"):
        raise RuntimeError("Benchmark belongs to another freeze")
    replay_path = root / "benchmark/block-000/REPLAY.json"
    replay = read_json(replay_path)
    if (file_hash(replay_path) != bench["benchmark_replay_sha256"]
            or file_hash(replay_path.parent / "arrays.npz") != replay["arrays_sha256"]
            or file_hash(replay_path.parent / "metadata.json") != replay["metadata_sha256"]):
        raise RuntimeError("Benchmark artifact changed")
    expected_forecast = 1.5 * SPEC["blocks"] * replay["wall_seconds"] + 60
    expected_bytes = int(1.1 * SPEC["blocks"] * replay["array_bytes"] + 32 * 1024 * 1024)
    if (bench["forecast_seconds"] != expected_forecast
            or bench["detach_required"] != (expected_forecast > 600)
            or bench["projected_artifact_bytes"] != expected_bytes
            or replay["phase"] != "benchmark" or replay["block"] != 0
            or not replay["independent_audit"]["passed"]):
        raise RuntimeError("Benchmark forecast/identity mismatch")
    projected = bench["projected_artifact_bytes"]
    if projected > SPEC["artifact_limit_bytes"] or shutil.disk_usage(root).free - projected < SPEC["free_reserve_bytes"]:
        raise RuntimeError("Artifact/reserve disk budget would be exceeded")
    return frozen, bench


def run_main(root, detached=False, ready_fd=None):
    frozen, bench = preflight(root)
    if bench["detach_required"] and not detached:
        raise RuntimeError("Forecast exceeds ten minutes; use the detached launcher")
    claim = {"started_utc": utc(), "pid": os.getpid(), "cpus": sorted(os.sched_getaffinity(0)),
             "workers": SPEC["workers"], "detached": detached,
             "freeze_sha256": file_hash(root / "FREEZE.json"),
             "benchmark_sha256": file_hash(root / "BENCHMARK.json")}
    write_json(root / "RUN_CLAIM.json", claim, exclusive=True)
    pool = None
    start, parent_cpu = time.monotonic(), time.process_time()
    try:
        blocks = root / "main"
        blocks.mkdir()
        write_json(root / "MANIFEST.json", {**claim, "spec": SPEC, "benchmark": bench,
                                           "environment": frozen["environment"]}, exclusive=True)
        (root / "RUN.pid").write_text(str(os.getpid()) + "\n")
        write_json(root / "STATUS.json", {"state": "RUNNING", "audited_blocks": 0, **claim})
        if ready_fd is not None:
            os.write(ready_fd, (json.dumps(claim) + "\n").encode())
            os.close(ready_fd)
        print(json.dumps({"event": "started", **claim}), flush=True)
        pool = mp.get_context("spawn").Pool(processes=SPEC["workers"])
        jobs = [("main", block, str(blocks)) for block in range(SPEC["blocks"])]
        pending = pool.imap_unordered(run_block, jobs, chunksize=1)
        collected = {}
        for done in range(SPEC["blocks"]):
            remaining = SPEC["wall_limit_seconds"] - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError("One-hour execution ceiling reached")
            receipt = pending.next(timeout=remaining)
            index = receipt["block"]
            if (index in collected or receipt["cpus"] != claim["cpus"]
                    or receipt["phase"] != "main" or index not in range(SPEC["blocks"])
                    or not receipt["independent_audit"]["passed"]):
                raise RuntimeError("Duplicate block or worker affinity mismatch")
            collected[index] = receipt
            write_json(root / "STATUS.json", {"state": "RUNNING", "audited_blocks": done + 1,
                                               "updated_utc": utc(), **claim})
            if (done + 1) % 16 == 0:
                print(json.dumps({"event": "audited", "blocks": done + 1, "wall_seconds": time.monotonic() - start}), flush=True)
        pool.close()
        pool.join()
        pool = None
        ordered = [collected[i] for i in range(SPEC["blocks"])]
        summary = summarize([r["production_block_metrics"] for r in ordered],
                            [r["production_block_diagnostics"] for r in ordered])
        aggregate_audit = audit_summary(summary, [r["independent_audit"]["independent_block_metrics"] for r in ordered],
                                        [r["independent_audit"]["independent_block_diagnostics"] for r in ordered])
        costs = {"wall_seconds": time.monotonic() - start,
                 "parent_cpu_seconds": time.process_time() - parent_cpu,
                 "worker_cpu_seconds": sum(r["cpu_seconds"] for r in ordered),
                 "cpus": claim["cpus"], "worker_pids": sorted({r["pid"] for r in ordered}),
                 "block_artifact_bytes": sum(p.stat().st_size for p in blocks.rglob("*") if p.is_file()),
                 "ambiguity_pairs_verified": sum(r["ambiguity_pairs_verified"] for r in ordered)}
        summary["costs"] = costs
        write_json(root / "SUMMARY.json", summary, exclusive=True)
        # Verify the JSON read back from disk, not only the in-memory result.
        audit_summary(read_json(root / "SUMMARY.json"), [r["independent_audit"]["independent_block_metrics"] for r in ordered],
                      [r["independent_audit"]["independent_block_diagnostics"] for r in ordered])
        write_json(root / "AGGREGATE_AUDIT.json", aggregate_audit, exclusive=True)
        (root / "REPORT.md").write_text(report_text(summary, costs))
        for i, receipt in enumerate(ordered):
            folder = blocks / f"block-{i:03d}"
            if (file_hash(folder / "arrays.npz") != receipt["arrays_sha256"]
                    or file_hash(folder / "metadata.json") != receipt["metadata_sha256"]
                    or read_json(folder / "REPLAY.json") != receipt):
                raise RuntimeError("Retained block changed after audit")
        check_freeze(root)
        if file_hash(root / "BENCHMARK.json") != claim["benchmark_sha256"]:
            raise RuntimeError("Benchmark changed during run")
        paths = sorted(p for p in blocks.rglob("*") if p.is_file())
        paths += [root / name for name in ("FREEZE.json", "BENCHMARK.json", "MANIFEST.json", "RUN_CLAIM.json", "SUMMARY.json", "REPORT.md", "AGGREGATE_AUDIT.json")]
        hashes = {str(p.relative_to(root)): file_hash(p) for p in paths}
        complete = {"state": "COMPLETE", "completed_utc": utc(), "valid_scientific_result": True,
                    "audited_blocks": len(ordered), "primary_label": summary["primary_label"],
                    "total_wall_seconds_including_final_hashes": time.monotonic() - start,
                    "hashes": hashes, "aggregate_audit": aggregate_audit}
        if complete["total_wall_seconds_including_final_hashes"] > SPEC["wall_limit_seconds"]:
            raise TimeoutError("Execution ceiling exceeded before final admission")
        write_json(root / "COMPLETE.json", complete, exclusive=True)
        write_json(root / "STATUS.json", {"state": "COMPLETE", "audited_blocks": len(ordered), "completed_utc": utc()})
        print(json.dumps({"event": "complete", "primary_label": summary["primary_label"],
                          "wall_seconds": complete["total_wall_seconds_including_final_hashes"],
                          "report": str(root / "REPORT.md")}), flush=True)
    except BaseException:
        if pool is not None:
            pool.terminate()
            pool.join()
        failure = {"state": "FAILED", "failed_utc": utc(), "valid_scientific_result": False,
                   "traceback": traceback.format_exc(), "wall_seconds": time.monotonic() - start}
        write_json(root / "FAILED.json", failure)
        write_json(root / "STATUS.json", failure)
        raise


def launch(root):
    preflight(root)
    write_json(root / "LAUNCH_REQUEST.json", {"requested_utc": utc()}, exclusive=True)
    read_fd, write_fd = os.pipe()
    with (root / "stdout.log").open("xb", buffering=0) as log:
        command = [sys.executable, "-m", "causal_probe", "--root", str(root),
                   "run", "--detached", "--ready-fd", str(write_fd)]
        child = subprocess.Popen(command, cwd=PROJECT, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(write_fd,))
    os.close(write_fd)
    try:
        readable, _, _ = select.select([read_fd], [], [], 55)
        data = os.read(read_fd, 65536) if readable else b""
        if not data:
            if child.poll() is None:
                child.terminate()
            raise RuntimeError("Detached startup did not acknowledge readiness; inspect stdout.log")
        receipt = {"launch_utc": utc(), "pid": child.pid, "startup_ack": json.loads(data),
                   "log": str(root / "stdout.log"), "automatic_progress_polling": False}
        write_json(root / "LAUNCH.json", receipt, exclusive=True)
        print(json.dumps(receipt), flush=True)
    finally:
        os.close(read_fd)


def audit_saved(root):
    check_freeze(root)
    complete = read_json(root / "COMPLETE.json")
    for relative, digest in complete["hashes"].items():
        if file_hash(root / relative) != digest:
            raise RuntimeError("Completion hash changed: " + relative)
    independent, diagnostics = [], []
    for block in range(SPEC["blocks"]):
        folder = root / "main" / f"block-{block:03d}"
        metadata = read_json(folder / "metadata.json")
        if metadata["phase"] != "main" or metadata["block"] != block:
            raise RuntimeError("Main block identity changed")
        with np.load(folder / "arrays.npz", allow_pickle=False) as saved:
            result = audit_block({key: saved[key] for key in saved.files}, metadata)
        independent.append(result["independent_block_metrics"])
        diagnostics.append(result["independent_block_diagnostics"])
    receipt = audit_summary(read_json(root / "SUMMARY.json"), independent, diagnostics)
    print(json.dumps({"saved_audit": receipt, "completion_sha256": file_hash(root / "COMPLETE.json")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(RUNS / "im3-v1"))
    parser.add_argument("command", choices=("qualify", "freeze", "benchmark", "run", "launch", "audit"))
    parser.add_argument("--detached", action="store_true")
    parser.add_argument("--ready-fd", type=int)
    args = parser.parse_args()
    root = safe_root(args.root)
    cpu_limit()
    if args.command == "run":
        run_main(root, args.detached, args.ready_fd)
    else:
        {"qualify": qualify, "freeze": freeze, "benchmark": benchmark,
         "launch": launch, "audit": audit_saved}[args.command](root)


if __name__ == "__main__":
    main()
