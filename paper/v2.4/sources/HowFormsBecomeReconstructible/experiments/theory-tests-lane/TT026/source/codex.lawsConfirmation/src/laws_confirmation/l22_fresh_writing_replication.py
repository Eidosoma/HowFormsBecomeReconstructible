"""Fresh D071 writing cells evaluated with the frozen D072 reliability instrument."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l22_fixed_record_readout as readout
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

writing, source = readout.prior, readout.source
strict_json = readout.strict_json
RUN_ID = "l22_fresh_writing_replication_v1_attempt1"
SOURCE_ID = readout.RUN_ID
SOURCE_AUDIT = SOURCE_ID + "_independent_rescore_v1"
TISSUES, WORKERS = tuple(range(30024, 30040)), 4
CONFIG, READOUT_CONFIG = writing.CONFIG, readout.CONFIG
ENDPOINTS = readout.ENDPOINTS
SEEDS = tuple(range(20260908097301, 20260908097304))
STAGES = ("calibration", "writing", "readout")


def calibration(ctx, cfg=READOUT_CONFIG):
    old, old_raw = source.calibration(ctx)
    new, new_raw = readout.calibration(ctx, cfg)
    gates = {"legacy_structural": old["passes"] is True, "readout_structural": new["passes"] is True}
    assert all(gates.values())
    return {"tissue": ctx["index"], "passes": True, "gates": gates, "legacy": old, "readout": new}, {"writing": old_raw, "readout": new_raw}


def calibrated(rows):
    if sorted(r["tissue"] for r in rows) != list(TISSUES):
        return False
    if not all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in rows):
        return False
    for name in ("legacy", "readout"):
        if not all(r[name]["passes"] is True and all(v is True for v in r[name]["gates"].values())
                   and r[name]["positive_accuracy"] > .25 for r in rows):
            return False
        if math.fsum(r[name]["positive_accuracy"] for r in rows) / 16 < .75:
            return False
    return True


def packets_from_arrays(arrays, cfg=CONFIG):
    fields = {"damaged": arrays["boundary"]["damaged_theta"], "parent": arrays["parent"]["theta"],
              "fixed": arrays["recovery_fixed_damaged_reader"][f"s{cfg.sweeps}_theta"],
              "loop": arrays["recovery_loop"][f"s{cfg.sweeps}_theta"]}
    np.testing.assert_array_equal(arrays["recovery_writer_off"][f"s{cfg.sweeps}_theta"], fields["damaged"])
    for value in fields.values():
        assert value.dtype == np.float64 and value.shape == (4 * cfg.replicates, 16, 16) and np.isfinite(value).all()
    return {name: field.tobytes() for name, field in fields.items()}


def save_arrays(directory, arrays, root, prefix=""):
    for name, raw in arrays.items():
        source.base.atomic_npz(directory / f"{prefix}{name}.npz", raw, root)


def save_writing(directory, result, arrays, root):
    assert len(arrays) == 26 and result["passes"] is True
    save_arrays(directory, arrays, root)
    strict_json(directory / "experiment.json", result, root)
    paths = [directory / f"{name}.npz" for name in arrays] + [directory / "experiment.json"]
    write_hash_manifest(paths, directory / "writing_hashes.sha256", root)
    assert len(readout.manifest_hashes(directory / "writing_hashes.sha256")) == 27


def load_written(directory, cfg=CONFIG, expected_tissue=None):
    hashes = readout.manifest_hashes(directory / "writing_hashes.sha256")
    assert len(hashes) == 27
    expected = {directory / f"{n}.npz" for n in ("before", "parent", "boundary", *(f"recovery_{a}" for a in writing.ARMS),
                                                         *(f"probe_{a}" for a in writing.PROBES))}
    assert set(hashes) == {str(p) for p in expected | {directory / "experiment.json"}}
    saved = json.loads((directory / "experiment.json").read_text())
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    if expected_tissue is not None:
        assert saved["tissue"] == expected_tissue
    assert canonical_digest(saved["config"]) == canonical_digest(asdict(cfg))
    arrays = {}
    for name in ("boundary", "parent", "recovery_fixed_damaged_reader", "recovery_loop", "recovery_writer_off"):
        with np.load(directory / f"{name}.npz", allow_pickle=False) as data:
            arrays[name] = {k: data[k].copy() for k in data.files}
    packets = packets_from_arrays(arrays, cfg)
    for name, packet in packets.items():
        assert hashlib.sha256(packet).hexdigest() == saved["probe_packet_hashes"]["fixed_damaged_reader" if name == "fixed" else name]
    return packets


def read_written(ctx, directory, cfg=READOUT_CONFIG):
    packets = load_written(directory, ctx["config"], expected_tissue=ctx["index"])
    result, arrays = readout.experiment(ctx, packets, cfg, legacy_directory=directory)
    readout.manifest_hashes(directory / "writing_hashes.sha256")
    result.update(packet_origin="current_fresh_writing_cell", writing_manifest_sha256=sha256_file(directory / "writing_hashes.sha256"))
    return result, arrays


def classify(rows):
    if (sorted(r["tissue"] for r in rows) != list(TISSUES)
            or not all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in rows)):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    rows = sorted(rows, key=lambda r: r["tissue"])
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for (name, left, right), seed in zip(ENDPOINTS, SEEDS):
        values = np.array([r["arms"][left]["accuracy"] - r["arms"][right]["accuracy"] for r in rows])
        draws = np.random.default_rng(seed).integers(0, 16, (10000, 16))
        interval = np.quantile(values[draws].mean(axis=1), [.05 / 6, 1 - .05 / 6]).tolist()
        positive = int((values > 0).sum())
        contrasts[name] = {"mean": float(values.mean()), "tissue_differences": values.tolist(), "interval": interval,
                          "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000,
                          "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= 12)}
    live, fixed, extra = [contrasts[n]["supported"] for n, _, _ in ENDPOINTS]
    label = ("PARENT_THETA_NOT_READABLE" if not eligible else
             "FIXED_READER_WRITING_REPLICATION_ONLY" if not live and fixed else
             "NO_QUALIFIED_FRESH_WRITING_BENEFIT" if not live else
             "FRESH_FEEDBACK_RELIABILITY_REPLICATED" if extra else "FRESH_WRITING_RELIABILITY_REPLICATED")
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def worker(index, root_text, stage):
    assert index in TISSUES and stage in STAGES and source.runtime()["passes"]
    root = external_root(root_text)
    directory = root / "outputs" / RUN_ID / f"tissue_{index}"
    ctx = source.context(index, CONFIG)
    if stage == "calibration":
        result, arrays = calibration(ctx)
        for name, raw in arrays.items():
            save_arrays(directory / name, raw, root, "calibration_")
            strict_json(directory / name / "calibration.json", result["legacy" if name == "writing" else "readout"], root)
    elif stage == "writing":
        result, arrays = writing.experiment(ctx)
        save_writing(directory / "writing", result, arrays, root)
    else:
        result, arrays = read_written(ctx, directory / "writing")
        save_arrays(directory / "readout", arrays, root)
        strict_json(directory / "readout" / "experiment.json", result, root)
    return result


def fresh_panel(root):
    conflicts = []
    def indices(value):
        found = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in ("tissues", "tissue_indices") and isinstance(item, list):
                    found.extend(i for i in item if type(i) is int)
                elif key.lower() == "tissue" and type(item) is int:
                    found.append(item)
                found.extend(indices(item))
        elif isinstance(value, list):
            for item in value:
                found.extend(indices(item))
        return found
    for path in (root / "runs").glob("*/MANIFEST.json"):
        if path.parent.name != RUN_ID and set(indices(json.loads(path.read_text()))) & set(TISSUES):
            conflicts.append(str(path))
    for directory in (root / "outputs").glob("*/tissue_*"):
        if directory.parent.name != RUN_ID and directory.name in {f"tissue_{i}" for i in TISSUES}:
            conflicts.append(str(directory))
    if conflicts:
        raise RuntimeError(f"fresh tissue reservation already used: {conflicts}")
    return {"passes": True, "tissues": list(TISSUES), "conflicts": []}


def source_info(root):
    counts = {}
    for name in (SOURCE_ID, SOURCE_AUDIT):
        run, output = root / "runs" / name, root / "outputs" / name
        status = json.loads((run / "STATUS.json").read_text())
        assert status["status"] == "COMPLETE" and (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
        assert status.get("completed_cleanly", status.get("verified_scientific_data")) is True
        counts[name] = [len(readout.manifest_hashes(output / f"{kind}_hashes.sha256")) for kind in ("input", "output")]
    assert counts == {SOURCE_ID: [639, 242], SOURCE_AUDIT: [886, 2]}
    checked = json.loads((root / "outputs" / SOURCE_AUDIT / "rescore.json").read_text())
    assert checked["passes"] is True and checked["classification"]["label"] == "LIVE_WRITTEN_RECORD_RELIABILITY_SUPPORTED"
    return counts


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), ws / "protocols/L22_FRESH_WRITING_REPLICATION_V1.md",
             ws / "scripts/run_l22_fresh_writing_replication.sh", ws / "scripts/audit_l22_fresh_writing_replication_outputs.py",
             ws / "tests/test_l22_fresh_writing_replication.py", ws / "reviews/L22_FIXED_RECORD_READOUT_2026-09-08.md"]
    for kind in ("input", "output"):
        manifest = root / "outputs" / SOURCE_AUDIT / f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root / "runs" / SOURCE_AUDIT / n for n in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    return sorted(set(paths))


def contract():
    return {"run_id": RUN_ID, "source_run": SOURCE_ID, "config": asdict(CONFIG), "readout_config": asdict(READOUT_CONFIG),
            "tissues": list(TISSUES), "workers": WORKERS, "stages": list(STAGES),
            "modes": {a: asdict(m) for a, m in writing.MODES.items()}, "legacy_probes": list(writing.PROBES),
            "readout_arms": list(readout.ARMS), "endpoints": ENDPOINTS, "bootstrap_seeds": list(SEEDS),
            "quantiles": [.05 / 6, 1 - .05 / 6], "minimum_positive_tissues": 12,
            "fresh_parent_replication": True, "retained_scientific_packets_used": 0, "law_verdict_changes": 0,
            "parent_lives": 256, "recovery_lives": 2560, "legacy_diagnostic_readouts": 3328,
            "legacy_calibration_lives": 768, "writing_integrity_lives": 1024, "scientific_readout_lives": 24576,
            "readout_calibration_lives": 12288, "readout_replay_lives": 4096, "legacy_wrapper_replay_lives": 1024,
            "total_lives": 49920, "qualified_output_hashes": 738, "unqualified_output_hashes": 98}


def benchmark_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("immutable run already exists")
    rt, disk, reservation = source.runtime(), source.disk_preflight(root), fresh_panel(root)
    assert rt["passes"] and disk["passes"]
    counts = source_info(root)
    cfg = source.Config(replicates=2, settle=32, imprint=32, sweeps=32, times=(0, 1, 8, 16, 32))
    rcfg = readout.Config(parents=2, draws=2, sweeps=32, times=(0, 1, 32))
    ctx = source.context(400100, cfg)
    start = time.monotonic()
    old_cal, _ = source.calibration(ctx)
    written, arrays = writing.experiment(ctx)
    writing_seconds = time.monotonic() - start
    packets = packets_from_arrays(arrays, cfg)
    start = time.monotonic()
    new_cal, _ = readout.calibration(ctx, rcfg)
    observed, _ = readout.experiment(ctx, packets, rcfg)
    readout_seconds = time.monotonic() - start
    estimate = writing_seconds * 437.5 + readout_seconds * 3500 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "disposable_tissue": 400100,
              "effect_sizes_not_reported": True, "config": asdict(cfg), "readout_config": asdict(rcfg),
              "writing_seconds": writing_seconds, "readout_seconds": readout_seconds,
              "projected_seconds": estimate, "must_detach": bool(estimate > 600),
              "passes": bool(all(r["passes"] for r in (old_cal, new_cal, written, observed))),
              "runtime": rt, "source_counts": counts, "reservation": reservation,
              "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    strict_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2, allow_nan=False), flush=True)
    return record


def prepare(root):
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("unique immutable run already exists")
    timing = json.loads(benchmark_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    rt, disk = source.runtime(), source.disk_preflight(root)
    reservation, counts = fresh_panel(root), source_info(root)
    if not (timing["passes"] is True and timing["input_sha256"] == hashes and rt["passes"] and disk["passes"]):
        raise RuntimeError("benchmark/source/runtime/storage contract changed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    manifest = contract() | {"prepared_utc": utc_now(), "benchmark": timing, "runtime": rt, "disk": disk,
                            "reservation": reservation, "source_counts": counts, "input_sha256": hashes,
                            "hash_contract": canonical_digest(hashes), "environment": environment_manifest()}
    json.dumps(manifest, allow_nan=False)
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    strict_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    strict_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID}, root)
    return manifest


def verify_prepared(root):
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    if (status["status"] != "PREPARED" or (run / "COMPLETE").exists() or (run / "FAILED").exists()
            or not source.base.verify_hashes(manifest["input_sha256"])
            or manifest["hash_contract"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root) + [benchmark_path(root)]}
            or any(canonical_digest(manifest.get(k)) != canonical_digest(v) for k, v in contract().items())):
        raise RuntimeError("not uniquely prepared or frozen contract changed")
    fresh_panel(root)
    return manifest


def detach(root):
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest, run = verify_prepared(root), root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    (root / "logs").mkdir(exist_ok=True)
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l22_fresh_writing_replication", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, start_new_session=True)
    record = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(),
              "estimated_seconds": manifest["benchmark"]["projected_seconds"], "stdout_log": str(stdout),
              "stderr_log": str(stderr), "status": str(run / "STATUS.json"), "complete": str(run / "COMPLETE"),
              "failed": str(run / "FAILED"), "polling_owner": "user", "command": command}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    strict_json(run / "LAUNCH.json", record, root)
    print(json.dumps(record, indent=2, allow_nan=False), flush=True)
    return record  # Never poll or wait after detached launch.


def run_study(root):
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        assert source.runtime()["passes"] and source.disk_preflight(root)["passes"]
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        records = {stage: [] for stage in STAGES}
        for stage in STAGES:
            if stage != "calibration" and not calibrated(records["calibration"]):
                break
            if stage == "readout":
                assert len(records["writing"]) == 16 and all(r["passes"] is True for r in records["writing"])
            strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage, "completed_tissues": 0, "updated_utc": utc_now()}, root)
            with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
                futures = [pool.submit(worker, index, str(root), stage) for index in TISSUES]
                for future in as_completed(futures):
                    records[stage].append(future.result())
                    strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage, "completed_tissues": len(records[stage]),
                                                      "updated_utc": utc_now()}, root)
            records[stage].sort(key=lambda r: r["tissue"])
        qualified = calibrated(records["calibration"])
        classification = classify(records["readout"]) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        assert len(records["calibration"]) == 16 and all(r["passes"] is True for r in records["calibration"])
        assert classification["label"] != "INVALID_STRUCTURAL_FAILURE"
        assert source.base.verify_hashes(manifest["input_sha256"])
        result = {"run_id": RUN_ID, "source_run": SOURCE_ID, "completed_cleanly": True, "generated_utc": utc_now(),
                  "calibration_qualified": qualified, "calibrations": records["calibration"], "writing": records["writing"],
                  "readout": records["readout"], "classification": classification, "fresh_parent_replication": True,
                  "retained_scientific_packets_used": 0, "law_verdict_changes": 0}
        strict_json(output / "replication.json", result, root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"),
                            output / "output_hashes.sha256", root)
        count = len(readout.manifest_hashes(output / "output_hashes.sha256"))
        assert count == (738 if qualified else 98)
        status = {"status": "COMPLETE", "run_id": RUN_ID, "completed_cleanly": True, "completed_utc": utc_now(),
                  "elapsed_seconds": time.monotonic() - start, "classification": classification["label"],
                  "calibration_qualified": qualified, "completed_writing_tissues": len(records["writing"]),
                  "completed_readout_tissues": len(records["readout"]), "cpu_affinity": sorted(os.sched_getaffinity(0)),
                  "output_manifest_self_verifies": True}
        encoded = json.dumps(status, indent=2, allow_nan=False)
        strict_json(run / "STATUS.json", status, root)
        atomic_text(run / "COMPLETE", status["completed_utc"] + "\n", root)
        print(encoded, flush=True)
        return 0
    except Exception as error:
        failure = {"status": "FAILED", "run_id": RUN_ID, "failed_utc": utc_now(), "error": str(error), "traceback": traceback.format_exc()}
        strict_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ("benchmark", "prepare", "run", "detach"):
        group.add_argument(f"--{name}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        manifest = prepare(root)
        print(json.dumps({"status": "PREPARED", "input_hashes": len(manifest["input_sha256"]),
                          "estimated_seconds": manifest["benchmark"]["projected_seconds"]}), flush=True)
    elif args.detach:
        detach(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
