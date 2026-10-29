"""Fresh-panel confirmation of backup-free writing and online theta feedback."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
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

from . import l22_source_recovery as source
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 sha256_file, utc_now, write_hash_manifest)

RUN_ID = "l22_backup_free_feedback_v1_attempt1"
TISSUES, WORKERS = tuple(range(30008, 30024)), 4
CONFIG = replace(source.CONFIG, times=(0, 1, 50, 250, 500, 1000))
KEYS = source.KEYS
QUANTILES = (.05 / 6, 1 - .05 / 6)
SEEDS = tuple(range(20260908097101, 20260908097104))
MIN_POSITIVE = 12


@dataclass(frozen=True)
class Mode:
    body: str = "kept"
    reference: str = "zero"
    write: bool = True
    hold: bool = False
    reader: str = "live"


MODES = {
    "loop": Mode(),
    "writer_off": Mode(write=False),
    "theta_read_off": Mode(reader="native"),
    "reference_write_off": Mode(hold=True),
    "fixed_damaged_reader": Mode(reader="damaged"),
    "scrambled_loop": Mode(body="scrambled"),
    "scrambled_fixed_reader": Mode(body="scrambled", reader="damaged"),
    "body_writer_off": Mode(reader="native", write=False),
    "wrong_fixed_reader": Mode(reader="wrong_damaged"),
    "backup": Mode(reference="copy"),
}
ARMS = tuple(MODES)
PROBES = (*ARMS, "parent", "damaged", "reader_off")
REPLAYS = ("loop", "fixed_damaged_reader")
ENDPOINTS = (
    ("readout_vs_writer_off", "writer_off"),
    ("readout_vs_theta_read_off", "theta_read_off"),
    ("readout_vs_fixed_damaged_reader", "fixed_damaged_reader"),
)


def strict_json(path, value, root):
    """Validate the entire payload before creating any file; never stringify scalars."""
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    atomic_text(path, encoded, root)


def engine_mode(mode):
    if mode.reader not in ("live", "native", "damaged", "wrong_damaged"):
        raise ValueError("unknown theta reader")
    return source.Mode(body=mode.body, reference=mode.reference, write=mode.write,
                       hold=mode.hold, theta_read=mode.reader == "live")


def reader_context(ctx, initial, mode):
    """Route a fixed reader in a local context, without modifying frozen globals."""
    engine_mode(mode)
    if mode.reader == "live":
        return ctx, None
    fixed = (ctx["native"] if mode.reader == "native" else
             source.donor(initial["theta"], ctx["config"].replicates)
             if mode.reader == "wrong_damaged" else initial["theta"]).copy()
    fixed.setflags(write=False)
    return ctx | {"native": fixed}, fixed


def recover(ctx, initial, mode, parent, fresh):
    local, fixed = reader_context(ctx, initial, mode)
    digest = source.base.state_digest(initial)
    result = source.recover(local, initial, engine_mode(mode), parent, fresh)
    if fixed is not None:
        result["raw"]["fixed_reader"] = fixed.copy()
    assert digest == source.base.state_digest(initial)
    return result


def aliases(left, right, cfg, keys=("V", "ema", "R")):
    return all(np.array_equal(left[f"s{s}_{k}"], right[f"s{s}_{k}"])
               for s in cfg.times for k in keys)


def experiment(ctx):
    cfg = ctx["config"]
    before, parent = source.prepare_parent(ctx)
    kept, scrambled, fresh, damaged = source.boundary(ctx, parent)
    parent_hash = source.base.state_digest(parent)
    native_hash = source.base.array_digest(ctx["native"])
    initials = {a: source.initial_state(ctx, parent, kept, scrambled, damaged, engine_mode(m))
                for a, m in MODES.items()}
    recovery = {a: recover(ctx, initials[a], m, parent, fresh) for a, m in MODES.items()}
    probes = {}
    for name in PROBES:
        theta = (parent["theta"] if name in ("parent", "reader_off") else damaged
                 if name == "damaged" else recovery[name]["final"]["theta"])
        probes[name] = source.assay(ctx, theta.tobytes(), name == "reader_off")
    for name in REPLAYS:
        replay = recover(ctx, initials[name], MODES[name], parent, fresh)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in recovery[name]["raw"].items())
    anchor = source.base.state_copy(initials["backup"])
    rng = source.RNG(ctx["index"], "recovery", cfg.replicates)
    for s in range(1, cfg.sweeps + 1):
        anchor = dict(zip(KEYS, ctx["api"]["cascade_sweep"](
            *(anchor[k] for k in KEYS), ctx["tissue"], ctx["ladder"], ctx["bp"], rng, cfg.lam, cfg.norm)))
        if s in cfg.times:
            assert all(np.array_equal(v, recovery["backup"]["raw"][f"s{s}_{k}"]) for k, v in anchor.items())
    raw = {a: r["raw"] for a, r in recovery.items()}
    for s in cfg.times:
        np.testing.assert_allclose(raw["reference_write_off"][f"s{s}_theta"], damaged, rtol=0., atol=1e-11)
        assert np.all(raw["reference_write_off"][f"s{s}_R"] == 0.)
    assert 1 in cfg.times
    gates = {
        "source_preparation_and_native_backup_anchor": True,
        "two_full_replays": True,
        "parents_unchanged": source.base.state_digest(parent) == parent_hash,
        "native_context_unchanged": source.base.array_digest(ctx["native"]) == native_hash,
        "primary_R_initially_zero": all(np.all(initials[a]["R"] == 0.) for a in ARMS if a != "backup"),
        "common_damaged_written_theta": all(np.array_equal(s["theta"], damaged) for s in initials.values()),
        "fixed_reader_writer_off_body_alias": aliases(raw["fixed_damaged_reader"], raw["writer_off"], cfg),
        "fixed_reader_writer_off_trace_alias": all(np.array_equal(raw["fixed_damaged_reader"][k], raw["writer_off"][k])
                                                     for k in ("body_trace", "reference_trace")),
        "native_reader_writer_off_body_alias": aliases(raw["theta_read_off"], raw["body_writer_off"], cfg),
        "live_fixed_first_step_exact": all(np.array_equal(raw["loop"][f"s1_{k}"], raw["fixed_damaged_reader"][f"s1_{k}"])
                                             for k in KEYS),
        "zero_reference_writer_null": True,
        "recovery_streams": len({r["rng_final"] for r in recovery.values()}) == 1,
        "assay_streams": len({r["rng_final"] for r in probes.values()}) == 1,
        "off_assay_chance": source.accuracy(ctx, probes["reader_off"]["final"]["V"]) == .25,
        "assay_births": all(np.array_equal(p["raw"][f"s0_{k}"], source.assay_birth(ctx)[k])
                            for p in probes.values() for k in ("V", "ema", "R")),
    }
    assert all(v is True for v in gates.values())
    metrics = {a: {str(s): source.measure(ctx, {k: p["raw"][f"s{s}_{k}"] for k in KEYS},
                                            parent, np.ones_like(fresh)) for s in cfg.times}
               for a, p in probes.items()}
    result = {
        "tissue": ctx["index"], "passes": True, "gates": gates, "config": asdict(cfg),
        "tissue_config": asdict(ctx["tissue"]), "recovery": {a: r["metrics"] for a, r in recovery.items()},
        "probe": metrics, "initial_hashes": {a: r["initial_hash"] for a, r in recovery.items()},
        "probe_packet_hashes": {a: p["packet_sha256"] for a, p in probes.items()},
        "source_parent_sha256": parent_hash, "source_native_sha256": native_hash,
        "recovery_rng_final": recovery["loop"]["rng_final"], "probe_rng_final": probes["loop"]["rng_final"],
    }
    artifacts = {"before": before, "parent": parent, "boundary": {
        **{f"kept_{k}": v for k, v in kept.items()}, "scrambled_V": scrambled, "fresh": fresh,
        "damaged_theta": damaged, "codes": ctx["codes"], "native_theta": ctx["native"]}}
    artifacts.update({f"recovery_{a}": r["raw"] for a, r in recovery.items()})
    artifacts.update({f"probe_{a}": p["raw"] for a, p in probes.items()})
    json.dumps(result, allow_nan=False)  # Exercise the successful scientific payload before publication.
    return result, artifacts


def calibrated(rows):
    return bool(len(rows) == len(TISSUES) and sorted(r["tissue"] for r in rows) == list(TISSUES)
                and all(r["passes"] is True and all(v is True for v in r["gates"].values())
                        and r["positive_accuracy"] > .25 for r in rows)
                and math.fsum(r["positive_accuracy"] for r in rows) / len(TISSUES) >= .75)


def classify(results, calibration_pass=True):
    if (sorted(r["tissue"] for r in results) != list(TISSUES)
            or not all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in results)):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    rows = sorted(results, key=lambda r: r["tissue"])
    final = str(CONFIG.sweeps)
    parents = [r["probe"]["parent"][final]["mean"]["V_accuracy"] for r in rows]
    eligible = bool(calibration_pass and min(parents) > .25 and math.fsum(parents) / len(rows) >= .75)
    contrasts = {}
    for (name, right), seed in zip(ENDPOINTS, SEEDS):
        values = np.array([r["probe"]["loop"][final]["mean"]["V_accuracy"] -
                           r["probe"][right][final]["mean"]["V_accuracy"] for r in rows])
        draws = np.random.default_rng(seed).integers(0, len(rows), (10000, len(rows)))
        interval = np.quantile(values[draws].mean(axis=1), QUANTILES).tolist()
        positive = int((values > 0).sum())
        contrasts[name] = {"mean": float(values.mean()), "tissue_differences": values.tolist(),
                           "interval": interval, "quantiles": list(QUANTILES), "seed": seed, "resamples": 10000,
                           "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= MIN_POSITIVE)}
    flags = [contrasts[name]["supported"] for name, _ in ENDPOINTS]
    label = ("PARENT_THETA_NOT_READABLE" if not eligible else "NO_QUALIFIED_BACKUP_FREE_BENEFIT" if not flags[0]
             else "BACKUP_FREE_WRITING_BENEFIT_ONLY" if not flags[1]
             else "DAMAGED_READER_ASSISTED_WRITING_SUPPORTED" if not flags[2]
             else "BACKUP_FREE_RECIPROCAL_LOOP_SUPPORTED")
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def worker(index, root_text, stage):
    assert source.runtime()["passes"]
    root = external_root(root_text)
    ctx = source.context(index, CONFIG)
    result, artifacts = source.calibration(ctx) if stage == "calibration" else experiment(ctx)
    output = root / "outputs" / RUN_ID / f"tissue_{index}"
    for name, arrays in artifacts.items():
        source.base.atomic_npz(output / f"{'calibration_' if stage == 'calibration' else ''}{name}.npz", arrays, root)
    strict_json(output / f"{stage}.json", result, root)
    return result


def input_paths():
    ws = Path(__file__).resolve().parents[2]
    return sorted(set(source.input_paths() + [Path(__file__).resolve(),
        ws / "protocols/L22_BACKUP_FREE_FEEDBACK_V1.md", ws / "scripts/run_l22_backup_free_feedback.sh",
        ws / "scripts/audit_l22_backup_free_feedback_outputs.py", ws / "tests/test_l22_backup_free_feedback.py",
        ws / "reviews/L22_INFORMATION_SOURCE_RECOVERY_2026-09-08.md"]))


def contract():
    worlds = len(TISSUES) * 4 * CONFIG.replicates
    return {"run_id": RUN_ID, "config": asdict(CONFIG), "tissues": list(TISSUES), "workers": WORKERS,
            "modes": {a: asdict(m) for a, m in MODES.items()}, "probes": list(PROBES), "replays": list(REPLAYS),
            "endpoints": ENDPOINTS, "quantiles": list(QUANTILES), "bootstrap_seeds": list(SEEDS),
            "minimum_positive_tissues": MIN_POSITIVE, "parent_lives": worlds, "recovery_lives": worlds * len(ARMS),
            "assay_lives": worlds * len(PROBES), "calibration_lives_including_replay": worlds * 3,
            "integrity_lives": worlds * 4, "law_verdict_changes": 0}


def benchmark_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot change a prepared benchmark")
    rt = source.runtime()
    if not rt["passes"] or not source.disk_preflight(root)["passes"]:
        raise RuntimeError("runtime/storage gate failed")
    cfg = source.Config(replicates=2, settle=32, imprint=32, sweeps=32, times=(0, 1, 8, 16, 32))
    ctx = source.context(40080, cfg)
    start = time.monotonic()
    cal, _ = source.calibration(ctx)
    result, _ = experiment(ctx)
    elapsed = time.monotonic() - start
    estimate = elapsed * 2 * (1000 / 32) * math.ceil(len(TISSUES) / WORKERS) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "disposable_tissue": 40080,
              "effect_sizes_not_reported": True, "config": asdict(cfg), "seconds": elapsed,
              "projected_seconds": estimate, "must_detach": bool(estimate > 600),
              "passes": bool(cal["passes"] and result["passes"]), "runtime": rt,
              "input_sha256": {str(p): sha256_file(p) for p in input_paths()}}
    strict_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2, allow_nan=False), flush=True)
    return record


def prepare(root):
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("unique immutable run already exists")
    timing = json.loads(benchmark_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths()}
    rt, disk = source.runtime(), source.disk_preflight(root)
    if not (timing["passes"] is True and timing["input_sha256"] == hashes and rt["passes"] and disk["passes"]):
        raise RuntimeError("benchmark/source/runtime/storage contract changed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    manifest = contract() | {"prepared_utc": utc_now(), "benchmark": timing, "runtime": rt, "disk": disk,
                             "input_sha256": hashes, "hash_contract": canonical_digest(hashes),
                             "environment": environment_manifest()}
    json.dumps(manifest, allow_nan=False)
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    strict_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    strict_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID, "updated_utc": utc_now()}, root)
    return manifest


def verify_prepared(root):
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    if (status["status"] != "PREPARED" or (run / "COMPLETE").exists() or (run / "FAILED").exists()
            or not source.base.verify_hashes(manifest["input_sha256"])
            or manifest["hash_contract"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths() + [benchmark_path(root)]}
            or any(canonical_digest(manifest.get(k)) != canonical_digest(v) for k, v in contract().items())):
        raise RuntimeError("not uniquely prepared or frozen contract changed")
    return manifest


def detach(root):
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest, run = verify_prepared(root), root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    (root / "logs").mkdir(exist_ok=True)
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l22_backup_free_feedback", "--external-root", str(root), "--run"]
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
    return record  # No poll or wait.


def run_study(root):
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        if not source.runtime()["passes"] or not source.disk_preflight(root)["passes"]:
            raise RuntimeError("runtime/storage gate failed")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        results, calibrations = [], []
        for stage, records in (("calibration", calibrations), ("experiment", results)):
            if stage == "experiment" and not calibrated(calibrations):
                break
            strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage, "completed_tissues": 0,
                                              "updated_utc": utc_now()}, root)
            with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
                futures = [pool.submit(worker, t, str(root), stage) for t in TISSUES]
                for future in as_completed(futures):
                    records.append(future.result())
                    strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage,
                                                      "completed_tissues": len(records), "updated_utc": utc_now()}, root)
            records.sort(key=lambda r: r["tissue"])
        qualified = calibrated(calibrations)
        classification = classify(results, qualified) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        assert len(calibrations) == len(TISSUES) and all(r["passes"] is True for r in calibrations)
        assert classification["label"] != "INVALID_STRUCTURAL_FAILURE"
        assert source.base.verify_hashes(manifest["input_sha256"])
        result = {"run_id": RUN_ID, "generated_utc": utc_now(), "completed_cleanly": True,
                  "calibration_qualified": qualified, "calibrations": calibrations, "results": results,
                  "classification": classification, "law_verdict_changes": 0}
        strict_json(output / "feedback.json", result, root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"),
                            output / "output_hashes.sha256", root)
        hashes = {p: d for d, p in (line.split("  ", 1) for line in (output / "output_hashes.sha256").read_text().splitlines())}
        assert source.base.verify_hashes(hashes)
        status = {"status": "COMPLETE", "run_id": RUN_ID, "completed_cleanly": True, "completed_utc": utc_now(),
                  "elapsed_seconds": time.monotonic() - start, "classification": classification["label"],
                  "calibration_qualified": qualified, "completed_tissues": len(results),
                  "cpu_affinity": sorted(os.sched_getaffinity(0)), "output_manifest_self_verifies": True}
        encoded_status = json.dumps(status, indent=2, allow_nan=False)
        strict_json(run / "STATUS.json", status, root)
        atomic_text(run / "COMPLETE", status["completed_utc"] + "\n", root)
        print(encoded_status, flush=True)
        return 0
    except Exception as error:
        failure = {"status": "FAILED", "run_id": RUN_ID, "failed_utc": utc_now(), "error": str(error),
                   "traceback": traceback.format_exc()}
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
        record = prepare(root)
        print(json.dumps({"status": "PREPARED", "input_hashes": len(record["input_sha256"]),
                          "estimated_seconds": record["benchmark"]["projected_seconds"]}, allow_nan=False))
    elif args.detach:
        detach(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
