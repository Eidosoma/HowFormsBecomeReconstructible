"""Conditional reliability of frozen D071 theta across independent fresh readouts."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
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

from . import l22_backup_free_feedback as prior
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

source = prior.source
strict_json = prior.strict_json
RUN_ID = "l22_fixed_record_readout_v1_attempt1"
SOURCE_ID = prior.RUN_ID
SOURCE_AUDIT = SOURCE_ID + "_independent_rescore_v1"
TISSUES, WORKERS = tuple(range(30008, 30024)), 4
ARMS = ("damaged", "fixed", "loop", "parent", "wrong", "reader_off")
PACKETS = ("damaged", "fixed", "loop", "parent")
ENDPOINTS = (("loop_vs_damaged", "loop", "damaged"), ("fixed_vs_damaged", "fixed", "damaged"),
             ("loop_vs_fixed", "loop", "fixed"))
SEEDS = tuple(range(20260908097201, 20260908097204))
KEYS = ("V", "ema", "R", "theta")


@dataclass(frozen=True)
class Config:
    parents: int = 4
    draws: int = 16
    sweeps: int = 1000
    times: tuple = (0, 1, 1000)


CONFIG = Config()


class RNG(source.base.MessageCoupledRNG):
    def __init__(self, tissue, phase, replicates):
        address = f"l22-fixed-record-readout-v1:{tissue}:{phase}".encode()
        self.generator = np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16], "little"))
        self.replicates = replicates


def context(index, cfg=CONFIG):
    return source.context(index, replace(source.CONFIG, replicates=cfg.parents, sweeps=cfg.sweeps, times=cfg.times))


def manifest_hashes(path):
    rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
    hashes = {p: d for d, p in rows}
    assert len(hashes) == len(rows) and source.base.verify_hashes(hashes), str(path)
    return hashes


def source_info(root):
    counts = {}
    for run_id in (SOURCE_ID, SOURCE_AUDIT):
        run, output = root / "runs" / run_id, root / "outputs" / run_id
        status = json.loads((run / "STATUS.json").read_text())
        assert status["status"] == "COMPLETE" and (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
        assert status.get("completed_cleanly", status.get("verified_scientific_data")) is True
        counts[run_id] = [len(manifest_hashes(output / f"{kind}_hashes.sha256")) for kind in ("input", "output")]
    assert counts == {SOURCE_ID: [139, 482], SOURCE_AUDIT: [626, 2]}
    manifest = json.loads((root / "runs" / SOURCE_ID / "MANIFEST.json").read_text())
    assert canonical_digest(manifest["config"]) == canonical_digest(asdict(prior.CONFIG))
    assert manifest["tissues"] == list(TISSUES) and manifest["workers"] == 4
    assert canonical_digest(manifest["modes"]) == canonical_digest({k: asdict(v) for k, v in prior.MODES.items()})
    result = json.loads((root / "outputs" / SOURCE_AUDIT / "rescore.json").read_text())
    assert result["passes"] is True and result["classification"]["label"] == "NO_QUALIFIED_BACKUP_FREE_BENEFIT"
    return counts


def load_packets(root, tissue):
    directory = root / "outputs" / SOURCE_ID / f"tissue_{tissue}"
    files = {"damaged": ("boundary", "damaged_theta"), "fixed": ("recovery_fixed_damaged_reader", "s1000_theta"),
             "loop": ("recovery_loop", "s1000_theta"), "parent": ("parent", "theta")}
    saved = json.loads((directory / "experiment.json").read_text())
    hashes = {p: d for d, p in (line.split("  ", 1) for line in
              (root / "outputs" / SOURCE_ID / "output_hashes.sha256").read_text().splitlines())}
    packets = {}
    for name, (file, key) in files.items():
        path = directory / f"{file}.npz"
        assert sha256_file(path) == hashes[str(path)]
        with np.load(path, allow_pickle=False) as arrays:
            value = arrays[key].copy()
        assert value.shape == (16, 16, 16) and value.dtype == np.float64 and np.isfinite(value).all()
        packet = value.tobytes()
        assert hashlib.sha256(packet).hexdigest() == saved["probe_packet_hashes"]["fixed_damaged_reader" if name == "fixed" else name]
        packets[name] = packet
    return packets


def expand(packet, cfg):
    if not isinstance(packet, bytes) or len(packet) != 4 * cfg.parents * 2048:
        raise ValueError("only a serialized float64 theta packet per original record is accepted")
    theta = np.frombuffer(packet, dtype=np.float64).reshape(4 * cfg.parents, 16, 16)
    if not np.isfinite(theta).all():
        raise ValueError("nonfinite theta packet")
    return np.repeat(theta, cfg.draws, axis=0).copy()


def assay(ctx, packet, cfg=CONFIG, off=False, legacy=False):
    if legacy and cfg.draws != 1:
        raise ValueError("legacy replay has exactly one readout per record")
    theta = expand(packet, cfg)
    theta.setflags(write=False)
    rng_class = source.RNG if legacy else RNG
    birth_rng = rng_class(ctx["index"], "assay_birth", cfg.parents * cfg.draws)
    v = .2 * birth_rng.standard_normal(theta.shape)
    v -= v.mean(axis=(-2, -1), keepdims=True)
    state = {"V": v, "ema": v.copy(), "R": np.zeros_like(v), "theta": theta}
    snapshots = {0: source.base.state_copy(state)}
    rng = rng_class(ctx["index"], "assay", cfg.parents * cfg.draws)
    bp = replace(ctx["bp"], rho=0.)
    applied = np.zeros_like(theta) if off else theta
    for s in range(1, cfg.sweeps + 1):
        state["V"], state["ema"], state["R"] = ctx["api"]["blueprint_step"](
            state["V"], state["ema"], state["R"], applied, ctx["tissue"], ctx["ladder"], bp, "T", rng, c_m=0.)
        assert np.all(state["R"] == 0.)
        if s in cfg.times:
            snapshots[s] = source.base.state_copy(state)
    np.testing.assert_array_equal(theta, expand(packet, cfg))
    raw = {f"s{s}_{k}": value for s, snap in snapshots.items() for k, value in snap.items()}
    measurement, observer = measure(ctx, state["V"], cfg)
    raw.update(observer)
    return {"raw": raw, "metrics": measurement, "packet_sha256": hashlib.sha256(packet).hexdigest(),
            "expanded_sha256": hashlib.sha256(theta.tobytes()).hexdigest(), "rng_final": rng.digest(),
            "birth_rng_final": birth_rng.digest(), "theta_unchanged": True, "R_zero_every_step": True}


def measure(ctx, v, cfg):
    scores = source.score(v, ctx["codes"])
    ties = np.isclose(scores, scores.max(axis=1, keepdims=True), rtol=0., atol=1e-12)
    probabilities = ties / ties.sum(axis=1, keepdims=True)
    labels = np.repeat(np.arange(4), cfg.parents * cfg.draws)
    correctness = probabilities[np.arange(len(v)), labels].reshape(4 * cfg.parents, cfg.draws)
    others = scores.copy()
    others[np.arange(len(v)), labels] = -np.inf
    margins = scores[np.arange(len(v)), labels] - others.max(axis=1)
    target = np.repeat(ctx["codes"], cfg.parents * cfg.draws, axis=0)
    good = (v > 0) == (target > 0)
    record_means = correctness.mean(axis=1)
    within = float(correctness.var(axis=1).mean())
    between = float(record_means.var())
    total = float(correctness.var())
    assert abs(within + between - total) < 1e-12
    metrics = {"accuracy": float(correctness.mean()), "margin": float(margins.mean()),
        "sign_fidelity": float(good.mean()), "amplitude_fidelity": float((good & (abs(v) > .2)).mean()),
        "V_mean": float(v.mean()), "V_rms": float(np.sqrt(np.mean(v ** 2))),
        "record_accuracy": record_means.tolist(), "record_within_variance": correctness.var(axis=1).tolist(),
        "within_record_variance": within, "between_record_variance": between, "total_variance": total,
        "varying_records": int(np.any(correctness != correctness[:, :1], axis=1).sum()),
        "always_correct_records": int(np.all(correctness == 1., axis=1).sum()),
        "always_incorrect_records": int(np.all(correctness == 0., axis=1).sum()),
        "records": 4 * cfg.parents, "draws_per_record": cfg.draws,
        "confusion": probabilities.reshape(4, cfg.parents * cfg.draws, 4).mean(axis=1).tolist()}
    return metrics, {"scores": scores, "probabilities": probabilities, "correctness": correctness,
                     "margins": margins.reshape(4 * cfg.parents, cfg.draws)}


def calibration(ctx, cfg=CONFIG):
    packet = (.3 * np.repeat(ctx["codes"], cfg.parents, axis=0)).astype(np.float64).tobytes()
    positive, off, replay = [assay(ctx, packet, cfg, disabled) for disabled in (False, True, False)]
    gates = {"positive_replay": all(np.array_equal(v, replay["raw"][k]) for k, v in positive["raw"].items()),
             "off_message_independent": all(source.base.message_independent(off["raw"][f"s{s}_V"], cfg.parents * cfg.draws) for s in cfg.times),
             "off_chance": off["metrics"]["accuracy"] == .25,
             "paired_rng": positive["rng_final"] == off["rng_final"]}
    assert all(gates.values())
    return {"tissue": ctx["index"], "passes": True, "gates": gates,
            "positive_accuracy": positive["metrics"]["accuracy"]}, {"positive": positive["raw"], "reader_off": off["raw"]}


def experiment(ctx, packets, cfg=CONFIG, legacy_directory=None):
    assert set(packets) == set(PACKETS)
    incoming = dict(packets)
    loop = np.frombuffer(packets["loop"], dtype=np.float64).reshape(4 * cfg.parents, 16, 16)
    incoming["wrong"] = source.donor(loop, cfg.parents).tobytes()
    incoming["reader_off"] = packets["loop"]
    outcomes = {a: assay(ctx, incoming[a], cfg, a == "reader_off") for a in ARMS}
    replay = assay(ctx, packets["loop"], cfg)
    assert all(np.array_equal(v, replay["raw"][k]) for k, v in outcomes["loop"]["raw"].items())
    legacy_cfg = replace(cfg, draws=1)
    legacy_metrics, legacy_raw = {}, {}
    for name in PACKETS:
        old = assay(ctx, packets[name], legacy_cfg, legacy=True)
        if legacy_directory is None:
            expected = source.assay(ctx, packets[name])["raw"]
        else:
            old_name = "fixed_damaged_reader" if name == "fixed" else name
            with np.load(legacy_directory / f"probe_{old_name}.npz", allow_pickle=False) as arrays:
                expected = {f"s{s}_{k}": arrays[f"s{s}_{k}"].copy() for s in cfg.times for k in KEYS}
        assert all(np.array_equal(old["raw"][f"s{s}_{k}"], expected[f"s{s}_{k}"]) for s in cfg.times for k in KEYS)
        legacy_metrics[name], legacy_raw[f"legacy_{name}"] = old["metrics"], old["raw"]
    for s in cfg.times:
        for key in KEYS:
            wrong = outcomes["wrong"]["raw"][f"s{s}_{key}"]
            expected = source.donor(outcomes["loop"]["raw"][f"s{s}_{key}"], cfg.parents * cfg.draws)
            np.testing.assert_array_equal(wrong, expected)
    gates = {"loop_replay": True, "four_historical_readout_anchors": True, "wrong_donor_exact_permutation": True,
        "off_message_independent": all(source.base.message_independent(outcomes["reader_off"]["raw"][f"s{s}_V"], cfg.parents * cfg.draws) for s in cfg.times),
        "off_chance": outcomes["reader_off"]["metrics"]["accuracy"] == .25,
        "paired_streams": len({r["rng_final"] for r in outcomes.values()}) == 1,
        "matched_births": all(np.array_equal(r["raw"][f"s0_{k}"], outcomes["loop"]["raw"][f"s0_{k}"])
                              for r in outcomes.values() for k in ("V", "ema", "R")),
        "theta_unchanged_R_zero": all(r["theta_unchanged"] and r["R_zero_every_step"] for r in outcomes.values())}
    assert all(v is True for v in gates.values())
    paired = {}
    for name, left, right in ENDPOINTS:
        delta = outcomes[left]["raw"]["correctness"] - outcomes[right]["raw"]["correctness"]
        paired[name] = {"improved_draw_fraction": float((delta > 0).mean()), "worsened_draw_fraction": float((delta < 0).mean()),
                        "tied_draw_fraction": float((delta == 0).mean())}
    result = {"tissue": ctx["index"], "passes": True, "gates": gates, "config": asdict(cfg),
              "arms": {a: r["metrics"] for a, r in outcomes.items()}, "paired": paired, "legacy": legacy_metrics,
              "packet_hashes": {a: r["packet_sha256"] for a, r in outcomes.items()},
              "expanded_hashes": {a: r["expanded_sha256"] for a, r in outcomes.items()},
              "rng_final": outcomes["loop"]["rng_final"], "birth_rng_final": outcomes["loop"]["birth_rng_final"]}
    artifacts = {f"readout_{a}": r["raw"] for a, r in outcomes.items()} | legacy_raw
    artifacts["packets"] = {a: np.frombuffer(p, dtype=np.float64).reshape(4 * cfg.parents, 16, 16).copy() for a, p in packets.items()}
    json.dumps(result, allow_nan=False)
    return result, artifacts


def calibrated(rows):
    return bool(len(rows) == 16 and sorted(r["tissue"] for r in rows) == list(TISSUES)
                and all(r["passes"] is True and all(v is True for v in r["gates"].values())
                        and r["positive_accuracy"] > .25 for r in rows)
                and math.fsum(r["positive_accuracy"] for r in rows) / 16 >= .75)


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
            "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000, "positive_tissues": positive,
            "supported": bool(interval[0] > 0 and positive >= 12)}
    live, fixed, extra = [contrasts[name]["supported"] for name, _, _ in ENDPOINTS]
    label = ("PARENT_THETA_NOT_READABLE" if not eligible else
             "FIXED_READER_RECORD_RELIABILITY_ONLY" if not live and fixed else
             "NO_QUALIFIED_RECORD_RELIABILITY_BENEFIT" if not live else
             "LIVE_FEEDBACK_RECORD_RELIABILITY_SUPPORTED" if extra else "LIVE_WRITTEN_RECORD_RELIABILITY_SUPPORTED")
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def worker(index, root_text, stage):
    assert source.runtime()["passes"]
    root = external_root(root_text)
    ctx = context(index)
    if stage == "calibration":
        result, artifacts = calibration(ctx)
    else:
        result, artifacts = experiment(ctx, load_packets(root, index), legacy_directory=root / "outputs" / SOURCE_ID / f"tissue_{index}")
    directory = root / "outputs" / RUN_ID / f"tissue_{index}"
    for name, arrays in artifacts.items():
        source.base.atomic_npz(directory / f"{'calibration_' if stage == 'calibration' else ''}{name}.npz", arrays, root)
    strict_json(directory / f"{stage}.json", result, root)
    return result


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), ws / "protocols/L22_FIXED_RECORD_READOUT_V1.md",
             ws / "scripts/run_l22_fixed_record_readout.sh", ws / "scripts/audit_l22_fixed_record_readout_outputs.py",
             ws / "tests/test_l22_fixed_record_readout.py", ws / "reviews/L22_BACKUP_FREE_FEEDBACK_2026-09-08.md"]
    for kind in ("input", "output"):
        manifest = root / "outputs" / SOURCE_AUDIT / f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root / "runs" / SOURCE_AUDIT / name for name in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    return sorted(set(paths))


def contract():
    worlds = len(TISSUES) * 4 * CONFIG.parents * CONFIG.draws
    return {"run_id": RUN_ID, "source_run": SOURCE_ID, "config": asdict(CONFIG), "tissues": list(TISSUES),
            "arms": list(ARMS), "workers": WORKERS, "endpoints": ENDPOINTS, "bootstrap_seeds": list(SEEDS),
            "quantiles": [.05 / 6, 1 - .05 / 6], "minimum_positive_tissues": 12,
            "scientific_readout_lives": worlds * 6, "calibration_lives_including_replay": worlds * 3,
            "integrity_readout_lives": worlds + len(TISSUES) * 4 * CONFIG.parents * 4,
            "new_training_lives": 0, "source_panel_outcome_known": True, "law_verdict_changes": 0}


def synthetic_packets(ctx, cfg):
    parent = .3 * np.repeat(ctx["codes"], cfg.parents, axis=0)
    damaged, _ = ctx["api"]["mix_theta"](parent, .3, np.random.default_rng(20260908097200), .3)
    arrays = {"parent": parent, "damaged": damaged,
              "fixed": ctx["api"]["project_theta"](.9 * damaged + .1 * parent, .3),
              "loop": ctx["api"]["project_theta"](.85 * damaged + .15 * parent, .3)}
    return {k: np.asarray(v, dtype=np.float64).tobytes() for k, v in arrays.items()}


def benchmark_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("immutable run already exists")
    rt = source.runtime()
    assert rt["passes"] and source.disk_preflight(root)["passes"]
    counts = source_info(root)
    cfg = Config(parents=2, draws=2, sweeps=32, times=(0, 1, 32))
    ctx = context(40090, cfg)
    packets = synthetic_packets(ctx, cfg)
    start = time.monotonic()
    cal, _ = calibration(ctx, cfg)
    result, _ = experiment(ctx, packets, cfg)
    elapsed = time.monotonic() - start
    estimate = elapsed * 2 * 8 * (1000 / 32) * 4 * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "disposable_tissue": 40090,
              "effect_sizes_not_reported": True, "config": asdict(cfg), "seconds": elapsed, "projected_seconds": estimate,
              "must_detach": bool(estimate > 600), "passes": bool(cal["passes"] and result["passes"]),
              "runtime": rt, "source_counts": counts, "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    strict_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2, allow_nan=False), flush=True)
    return record


def prepare(root):
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("unique immutable run already exists")
    timing = json.loads(benchmark_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    rt, disk, counts = source.runtime(), source.disk_preflight(root), source_info(root)
    if not (timing["passes"] is True and timing["input_sha256"] == hashes and rt["passes"] and disk["passes"]):
        raise RuntimeError("benchmark/source/runtime/storage contract changed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    manifest = contract() | {"prepared_utc": utc_now(), "benchmark": timing, "runtime": rt, "disk": disk,
                            "source_counts": counts, "input_sha256": hashes, "hash_contract": canonical_digest(hashes),
                            "environment": environment_manifest()}
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
    return manifest


def detach(root):
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest, run = verify_prepared(root), root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    (root / "logs").mkdir(exist_ok=True)
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l22_fixed_record_readout", "--external-root", str(root), "--run"]
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
        calibrations, results = [], []
        for stage, records in (("calibration", calibrations), ("experiment", results)):
            if stage == "experiment" and not calibrated(calibrations):
                break
            strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage, "completed_tissues": 0,
                                              "updated_utc": utc_now()}, root)
            with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
                futures = [pool.submit(worker, index, str(root), stage) for index in TISSUES]
                for future in as_completed(futures):
                    records.append(future.result())
                    strict_json(run / "STATUS.json", {"status": "RUNNING", "stage": stage,
                                                      "completed_tissues": len(records), "updated_utc": utc_now()}, root)
            records.sort(key=lambda r: r["tissue"])
        qualified = calibrated(calibrations)
        classification = classify(results) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        assert len(calibrations) == 16 and all(r["passes"] is True for r in calibrations)
        assert classification["label"] != "INVALID_STRUCTURAL_FAILURE"
        assert source.base.verify_hashes(manifest["input_sha256"])
        result = {"run_id": RUN_ID, "source_run": SOURCE_ID, "completed_cleanly": True, "generated_utc": utc_now(),
                  "calibration_qualified": qualified, "calibrations": calibrations, "results": results,
                  "classification": classification, "source_panel_outcome_known": True,
                  "new_training_lives": 0, "law_verdict_changes": 0}
        strict_json(output / "readout.json", result, root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"),
                            output / "output_hashes.sha256", root)
        manifest_hashes(output / "output_hashes.sha256")
        status = {"status": "COMPLETE", "run_id": RUN_ID, "completed_cleanly": True, "completed_utc": utc_now(),
                  "elapsed_seconds": time.monotonic() - start, "classification": classification["label"],
                  "calibration_qualified": qualified, "completed_tissues": len(results),
                  "cpu_affinity": sorted(os.sched_getaffinity(0)), "output_manifest_self_verifies": True}
        encoded = json.dumps(status, indent=2, allow_nan=False)
        strict_json(run / "STATUS.json", status, root)
        atomic_text(run / "COMPLETE", status["completed_utc"] + "\n", root)
        print(encoded, flush=True)
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
