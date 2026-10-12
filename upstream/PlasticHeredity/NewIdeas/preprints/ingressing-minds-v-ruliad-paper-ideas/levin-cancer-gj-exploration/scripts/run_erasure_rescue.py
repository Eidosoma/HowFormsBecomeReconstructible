"""Bounded mid-lineage regulatory overwrite/rescue, followed by two replacements."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

from memory_metrics import REGULATORS, classify, opposite
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, SOURCE, REVISION, source_check
from run_renewal import round_worker


def edit_plan(kind, desired):
    other = opposite(desired)
    plans = {"sham": (None, None), "overwrite": (other, None),
             "rescue": (other, desired), "wrong": (other, other)}
    if kind not in plans:
        raise ValueError("Unknown intervention")
    return plans[kind]


def overwrite_regulators(packet, later, indices, label):
    if packet.shape != (17, 2) or later.shape != (17, 2):
        raise ValueError("Expected two-cell packet and E/M references")
    if not np.isfinite(packet).all() or (packet < 0).any():
        raise ValueError("Invalid input state")
    result = packet.copy()
    if label is not None:
        opposite(label)  # Validate E/M; do not silently interpret X.
        reg = [indices[name] for name in REGULATORS]
        values = later[reg, {"E": 0, "M": 1}[label], None]
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Invalid reference values")
        result[reg] = values
    return result


def branch_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    stem = case["state"].lower()
    prefix_meta = json.loads((inputs / f"{stem}_prefix.json").read_text())
    with np.load(inputs / f"{stem}_prefix.npz", allow_pickle=False) as saved:
        packet = saved["outgoing_packet"].copy()
    if classify(packet, indices).tolist() != [case["state"]] * 2:
        raise RuntimeError("Unexpected prefix state")
    ids = prefix_meta["outgoing_ids"].copy()
    seen = set(prefix_meta["incoming_ids"] + ids)
    original, endpoints = packet.copy(), {"prefix_packet": packet.copy()}
    intervention_dir = folder / "intervention"
    intervention_dir.mkdir()
    exp = Experiment(intervention_dir, config, fine=case.get("fine", False))
    stages, setups = [], []
    for stage, label in enumerate(edit_plan(case["intervention"], case["state"]), 1):
        edited = overwrite_regulators(packet, later, indices, label)
        endpoints[f"before_{stage}"] = packet.copy()
        endpoints[f"edited_{stage}"] = edited.copy()
        evolved, phase_records = [], []
        for cell in (1, 2):
            setup = exp.build(1, edited[:, cell - 1:cell], active=False)
            if exp.indices != indices:
                raise RuntimeError("Ion indices changed")
            setups.append(setup)
            final, record = exp.phase(f"stage_{stage}_cell_{cell}", config["intervention_horizon"])
            evolved.append(final)
            phase_records.append(record)
        packet = np.concatenate(evolved, axis=1)
        endpoints[f"after_{stage}"] = packet.copy()
        stages.append({"stage": stage, "anchor": label, "labels_after_wait": "".join(classify(packet, indices)),
                       "phases": phase_records})
    np.savez_compressed(intervention_dir / "endpoints.npz", **endpoints)
    intervention = {"stages": stages, "audits": exp.audits, "setups": setups,
                    "incoming_ids": ids.copy(), "outgoing_ids": ids.copy(),
                    "nominal_extra_duration": 2 * config["intervention_horizon"]}
    write_json(intervention_dir / "result.json", intervention)
    fresh = prepared[:, {"E": 0, "M": 1}[opposite(case["state"])], None].copy()
    continuing_start, rounds = packet.copy(), []
    for number in config["continuing_rounds"]:
        round_dir = folder / f"round_{number:02}"
        round_dir.mkdir()
        packet, ids, result = round_worker(round_dir, config, case, packet, ids, seen, fresh, later, indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"RESCUE_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
    np.savez_compressed(folder / "endpoints.npz", prefix_packet=original,
                        continuing_start=continuing_start, final_packet=packet, fresh_target=fresh)
    offset = intervention["nominal_extra_duration"]
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "intervention": intervention, "rounds": rounds, "final_ids": ids, "distinct_fresh_targets": len(seen) - 4,
        "all_rounds_transmitted": all(row["round_success"] for row in rounds),
        "nominal_schedule_with_intervention": [{"round": row["round"], "start": row["nominal_round_start"] + offset,
                                               "end": row["nominal_round_end"] + offset} for row in rounds]})
    return 0


def freeze_inputs(run_dir, config):
    from analyze_renewal import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input run must be within exploration runs")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged")
    if summary["revision"] != REVISION or not all(summary.get(key) for key in required):
        raise RuntimeError("Invalid predecessor run")
    audit = analyze(previous)
    if not audit["all_array_checks_pass"] or not audit["input_hashes_valid"]:
        raise RuntimeError("Predecessor array audit failed")
    write_json(run_dir / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json",
             "references.npz": previous / "inputs/references.npz", "reference.json": previous / "inputs/reference.json"}
    for stem in ("e", "m"):
        folder = previous / f"{stem}_learned/round_01"
        meta = json.loads((folder / "result.json").read_text())
        if not meta["round_success"] or set(meta["incoming_ids"]) & set(meta["outgoing_ids"]):
            raise RuntimeError("Prefix did not replace founders successfully")
        paths[f"{stem}_prefix.npz"] = folder / "endpoints.npz"
        paths[f"{stem}_prefix.json"] = folder / "result.json"
    target = run_dir / "inputs"
    target.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (target / name).write_bytes(path.read_bytes())
        if digest != file_hash(target / name) or digest != file_hash(path):
            raise RuntimeError("Input changed during copying")
        manifest[name] = {"source": str(path), "sha256": digest}
    write_json(target / "manifest.json", manifest)
    return manifest


def run_worker(case, config, run_dir, deadline, env):
    record = {"id": case["id"], "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder = run_dir / case["id"]
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case, "config": config, "inputs": str(run_dir / "inputs")})
    began = time.monotonic()
    print(f"Starting {case['id']}", flush=True)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    with (folder / "stdout.log").open("x") as log:
        try:
            completed = subprocess.run(command, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       timeout=min(remaining, config["worker_timeout_seconds"]))
            record.update(status="finished", returncode=completed.returncode)
        except subprocess.TimeoutExpired:
            record.update(status="timeout", returncode=None)
    record["elapsed_seconds"] = time.monotonic() - began
    if (folder / "result.json").exists():
        record["result"] = json.loads((folder / "result.json").read_text())
        record["execution_pass"] = record["returncode"] == 0 and record["result"]["execution_pass"]
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)", flush=True)
    return record


def validate_config(config):
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Unexpected revision, width, or continuing rounds")
    if config["intervention_horizon"] != 1000:
        raise ValueError("Unexpected intervention wait")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime/concurrency limits")
    names = [case["id"] for case in config["cases"]]
    if not names or len(names) != len(set(names)) or any(Path(name).name != name or name in (".", "..") for name in names):
        raise ValueError("Invalid case IDs")
    for case in config["cases"]:
        edit_plan(case["intervention"], case["state"])
        if case["history"] != "learned":
            raise ValueError("This continuation requires learned-prefix cases")


def run_suite(config_path):
    config = json.loads(config_path.read_text())
    validate_config(config)
    source_check()
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "runs").mkdir(exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix=f"erasure-rescue-{stamp}-", dir=ROOT / "runs"))
    inputs = freeze_inputs(run_dir, config)
    frozen = run_dir / "frozen"
    frozen.mkdir()
    files = [Path(__file__).resolve(), config_path, ROOT / "ERASURE_RESCUE_PROTOCOL.md", ROOT / "requirements-smoke.txt"]
    files += [ROOT / "scripts" / name for name in (
        "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "run_memory_probe.py", "memory_metrics.py", "run_pilot.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "test_erasure_rescue.py")]
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
    frozen_hashes = {path.name: file_hash(path) for path in files}
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files += [SOURCE / name for name in native]
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in files}
    audit_hash = file_hash(run_dir / "predecessor_audit.json")
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
        "config": config, "inputs": inputs, "hashes_sha256": hashes, "frozen_hashes_sha256": frozen_hashes,
        "predecessor_audit_sha256": audit_hash, "cases": [],
        "scope": "Regulatory identity overwrite/rescue in a finite externally managed relay"}
    write_json(run_dir / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache/matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Run artifacts: {run_dir}", flush=True)
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        pending = [pool.submit(run_worker, case, config, run_dir, deadline, env) for case in config["cases"]]
        for future in as_completed(pending):
            summary["cases"].append(future.result())
            write_json(run_dir / "summary.json", summary)
    source_check()
    inputs_ok = all(file_hash(Path(entry["source"])) == entry["sha256"] == file_hash(run_dir / "inputs" / name)
                    for name, entry in inputs.items())
    files_ok = all(file_hash(ROOT / path) == digest for path, digest in hashes.items())
    frozen_ok = all(file_hash(frozen / name) == digest for name, digest in frozen_hashes.items())
    audit_ok = file_hash(run_dir / "predecessor_audit.json") == audit_hash
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
        inputs_unchanged=inputs_ok, files_unchanged=files_ok, frozen_files_unchanged=frozen_ok, predecessor_audit_unchanged=audit_ok,
        all_execution_valid=inputs_ok and files_ok and frozen_ok and audit_ok and len(summary["cases"]) == len(config["cases"])
            and all(record["execution_pass"] for record in summary["cases"]))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/erasure_rescue_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    return run_suite(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
