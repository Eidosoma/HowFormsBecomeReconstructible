"""H4b day-long bound and an initial registered historical-control gate."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, SOURCE, REVISION, source_check


def run_worker(case, config, run, deadline, env, script):
    record = {"id": case["id"], "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    if shutil.disk_usage(ROOT).free < 5*1024**3:
        return dict(record, status="not_launched_disk", returncode=None)
    folder = run / case["id"]
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case, "config": config, "inputs": str(run / "inputs")})
    began = time.monotonic()
    print(f"Starting {case['id']}", flush=True)
    with (folder / "stdout.log").open("x") as log:
        try:
            proc = subprocess.run([sys.executable, str(script), "--worker", str(folder / "spec.json")],
                cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                timeout=min(remaining, config["worker_timeout_seconds"]))
            record.update(status="finished", returncode=proc.returncode)
        except subprocess.TimeoutExpired:
            record.update(status="timeout", returncode=None)
    record["elapsed_seconds"] = time.monotonic() - began
    if (folder / "result.json").exists():
        record["result"] = json.loads((folder / "result.json").read_text())
        record["execution_pass"] = record["returncode"] == 0 and record["result"]["execution_pass"]
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)", flush=True)
    return record


def run_bounded(config_path, script, protocol, helper_names, prepare_inputs, prefix, scope, extra_files=(), control_gate=None):
    config = json.loads(config_path.read_text())
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 3600 or not 0 < config["total_budget_seconds"] <= 86400:
        raise ValueError("Exceeds concurrency/runtime bounds")
    source_check()
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "runs").mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=f"{prefix}-{stamp}-", dir=ROOT / "runs"))
    inputs = prepare_inputs(run, config)
    frozen = run / "frozen"
    frozen.mkdir()
    files = [script, config_path, protocol, ROOT / "requirements-smoke.txt"] + list(extra_files)
    files += [ROOT / "scripts" / name for name in helper_names]
    if len({p.name for p in files}) != len(files):
        raise ValueError("Frozen filenames must be unique")
    frozen_hashes = {p.name: file_hash(p) for p in files}
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
        if file_hash(frozen / path.name) != frozen_hashes[path.name]:
            raise RuntimeError("File changed while being frozen")
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files += [SOURCE / name for name in native]
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in files}
    audit_hash = file_hash(run / "predecessor_audit.json")
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
        "config": config, "inputs": inputs, "hashes_sha256": hashes, "frozen_hashes_sha256": frozen_hashes,
        "predecessor_audit_sha256": audit_hash, "cases": [], "scope": scope}
    write_json(run / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache/matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Run artifacts: {run}", flush=True)
    if control_gate is None or config.get("prefix_cases") != 8 or not config.get("prefix_gate_required"):
        raise ValueError("H4b requires eight registered controls and their independent gate")
    chunks = [config["cases"][:8], config["cases"][8:]]
    if not all(c["kind"] == "prefix" for c in chunks[0]) or not all(c["kind"] == "main" for c in chunks[1]):
        raise ValueError("Historical controls must precede the main panel")
    for stage, cases in enumerate(chunks):
        with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            pending = [pool.submit(run_worker, case, config, run, deadline, env, script) for case in cases]
            for future in as_completed(pending):
                summary["cases"].append(future.result())
                write_json(run / "summary.json", summary)
        if stage == 0:
            gate = control_gate(run, config)
            write_json(run / "prefix_gate.json", gate)
            summary["prefix_gate_sha256"] = file_hash(run / "prefix_gate.json")
            summary["prefix_gate"] = gate
            write_json(run / "summary.json", summary)
            if not gate["quality_gate"]:
                summary["stopped_after_prefix_controls"] = True
                break
    source_check()
    inputs_ok = all(file_hash(Path(v["source"])) == v["sha256"] == file_hash(run / "inputs" / k) for k, v in inputs.items())
    files_ok = all(file_hash(ROOT / path) == digest for path, digest in hashes.items())
    frozen_ok = all(file_hash(frozen / name) == digest for name, digest in frozen_hashes.items())
    audit_ok = file_hash(run / "predecessor_audit.json") == audit_hash
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
        inputs_unchanged=inputs_ok, files_unchanged=files_ok, frozen_files_unchanged=frozen_ok, predecessor_audit_unchanged=audit_ok,
        all_execution_valid=inputs_ok and files_ok and frozen_ok and audit_ok and len(summary["cases"]) == len(config["cases"])
            and all(record["execution_pass"] for record in summary["cases"]))
    write_json(run / "summary.json", summary)
    print(f"Summary: {run / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1
