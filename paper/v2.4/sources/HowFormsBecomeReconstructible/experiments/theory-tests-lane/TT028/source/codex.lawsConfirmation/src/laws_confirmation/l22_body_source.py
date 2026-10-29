"""D074: matched body spatial content as a source of theta correction."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l22_fresh_writing_replication as prior
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

source, writing, readout = prior.source, prior.writing, prior.readout
strict_json, save_arrays = prior.strict_json, prior.save_arrays
RUN_ID = "l22_body_source_v1_attempt1"
SOURCE_ID, SOURCE_AUDIT = prior.RUN_ID, prior.RUN_ID + "_independent_rescore_v1"
TISSUES, WORKERS = tuple(range(30040, 30056)), 4
CONFIG, READOUT_CONFIG, KEYS = prior.CONFIG, prior.READOUT_CONFIG, source.KEYS
STAGES = ("calibration", "writing", "readout")
EXTRA = {
    "scrambled_off": ("scrambled", writing.Mode(write=False)),
    "donor_loop": ("donor", writing.Mode()),
    "donor_fixed": ("donor", writing.Mode(reader="damaged")),
    "donor_off": ("donor", writing.Mode(write=False)),
}
MAPPING = {
    "kept_loop": ("writing", "loop"), "kept_fixed": ("writing", "fixed_damaged_reader"),
    "kept_off": ("writing", "writer_off"), "scrambled_loop": ("writing", "scrambled_loop"),
    "scrambled_fixed": ("writing", "scrambled_fixed_reader"),
    **{name: ("intervention", name) for name in EXTRA},
    "damaged": ("writing", "damaged"), "parent": ("writing", "parent"),
}
PACKETS, ARMS = tuple(MAPPING), (*MAPPING, "wrong_packet", "reader_off")
ENDPOINTS = (
    ("useful_repair", "kept_loop", "damaged", "accuracy"),
    ("body_organization", "kept_loop", "scrambled_loop", "accuracy"),
    ("donor_redirection", "donor_loop", "scrambled_loop", "donor_accuracy"),
)
SEEDS = tuple(range(20260908097401, 20260908097404))


def donor_ranked(kept, fresh, replicates, indices=None):
    n = 4 * replicates
    assert kept.dtype == np.float64 and kept.shape == fresh.shape == (n, 16, 16)
    assert fresh.dtype == bool and np.isfinite(kept).all()
    indices = (np.roll(np.arange(n), -replicates) if indices is None else np.asarray(indices))
    assert indices.dtype.kind in "iu" and indices.shape == (n,) and set(indices.tolist()) == set(range(n))
    out, orders = kept.copy(), []
    for i, j in enumerate(indices):
        np.testing.assert_array_equal(fresh[i], fresh[j])
        mask = ~fresh[i]
        assert mask.sum() == 128
        order = np.argsort(kept[j][mask], kind="stable")
        values = np.empty(128, dtype=np.float64)
        values[order] = np.sort(kept[i][mask], kind="stable")
        out[i][mask] = values
        np.testing.assert_array_equal(np.sort(out[i][mask]), np.sort(kept[i][mask]))
        np.testing.assert_array_equal(out[i][fresh[i]], kept[i][fresh[i]])
        orders.append(order)
    return {"donor_V": out, "donor_indices": indices.copy(), "donor_order": np.asarray(orders),
            "changed_cells": np.count_nonzero(out != kept, axis=(1, 2))}


def experiment_writing(ctx):
    cfg = ctx["config"]
    old, arrays = writing.experiment(ctx)
    boundary, parent = arrays["boundary"], arrays["parent"]
    fresh, damaged = boundary["fresh"], boundary["damaged_theta"]
    bodies = donor_ranked(boundary["kept_V"], fresh, cfg.replicates)
    initials, recovery, probes = {}, {}, {}
    for name, (body, mode) in EXTRA.items():
        v = bodies["donor_V"] if body == "donor" else boundary["scrambled_V"]
        initials[name] = {"V": v.copy(), "ema": v.copy(), "R": np.zeros_like(v), "theta": damaged.copy()}
        recovery[name] = writing.recover(ctx, initials[name], mode, parent, fresh)
        probes[name] = source.assay(ctx, recovery[name]["final"]["theta"].tobytes())
    for name in ("donor_loop", "donor_fixed"):
        replay = writing.recover(ctx, initials[name], EXTRA[name][1], parent, fresh)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in recovery[name]["raw"].items())
    raw = {name: value["raw"] for name, value in recovery.items()}
    for left, right in ((arrays["recovery_scrambled_fixed_reader"], raw["scrambled_off"]),
                        (raw["donor_fixed"], raw["donor_off"])):
        assert writing.aliases(left, right, cfg)
        assert all(np.array_equal(left[k], right[k]) for k in ("body_trace", "reference_trace"))
    for left, right in ((arrays["recovery_scrambled_loop"], arrays["recovery_scrambled_fixed_reader"]),
                        (raw["donor_loop"], raw["donor_fixed"])):
        assert all(np.array_equal(left[f"s1_{k}"], right[f"s1_{k}"]) for k in KEYS)
    for name in ("scrambled_off", "donor_off"):
        assert all(np.array_equal(raw[name][f"s{s}_theta"], damaged) for s in cfg.times)
    metrics = {a: {str(s): source.measure(ctx, {k: p["raw"][f"s{s}_{k}"] for k in KEYS}, parent, np.ones_like(fresh))
                   for s in cfg.times} for a, p in probes.items()}
    gates = {"rank_preserves_values_and_fill": True, "two_extra_replays": True, "body_trace_aliases": True,
             "live_fixed_first_step": True, "all_off_theta_identical": True,
             "common_recovery_stream": all(r["rng_final"] == old["recovery_rng_final"] for r in recovery.values()),
             "common_probe_stream": all(p["rng_final"] == old["probe_rng_final"] for p in probes.values()),
             "zero_R_same_theta": all(np.all(s["R"] == 0.) and np.array_equal(s["theta"], damaged) for s in initials.values()),
             "parent_unchanged": source.base.state_digest(parent) == old["source_parent_sha256"],
             "native_context_unchanged": source.base.array_digest(ctx["native"]) == old["source_native_sha256"]}
    assert all(v is True for v in gates.values())
    extra = {"tissue": ctx["index"], "config": asdict(cfg), "passes": True, "gates": gates,
             "recovery": {a: r["metrics"] for a, r in recovery.items()}, "probe": metrics,
             "initial_hashes": {a: r["initial_hash"] for a, r in recovery.items()},
             "probe_packet_hashes": {a: p["packet_sha256"] for a, p in probes.items()},
             "changed_cells": bodies["changed_cells"].tolist(), "donor_indices": bodies["donor_indices"].tolist()}
    extra_arrays = {"bodies": bodies} | {f"recovery_{a}": r["raw"] for a, r in recovery.items()} | {
        f"probe_{a}": p["raw"] for a, p in probes.items()}
    result = {"tissue": ctx["index"], "passes": True, "legacy": old, "intervention": extra}
    json.dumps(result, allow_nan=False)
    return result, arrays, extra_arrays


def save_writing(directory, result, arrays, extras, root):
    prior.save_writing(directory / "writing", result["legacy"], arrays, root)
    part = directory / "intervention"
    assert set(extras) == {"bodies", *(f"{prefix}_{a}" for prefix in ("recovery", "probe") for a in EXTRA)}
    save_arrays(part, extras, root)
    strict_json(part / "experiment.json", result["intervention"], root)
    write_hash_manifest([part / f"{a}.npz" for a in extras] + [part / "experiment.json"], part / "intervention_hashes.sha256", root)


def packets_from_arrays(arrays, extras, cfg=CONFIG):
    packets = {}
    for name, (folder, old) in MAPPING.items():
        data = arrays if folder == "writing" else extras
        theta = (arrays["boundary"]["damaged_theta"] if name == "damaged" else arrays["parent"]["theta"]
                 if name == "parent" else data[f"recovery_{old}"][f"s{cfg.sweeps}_theta"])
        assert theta.dtype == np.float64 and theta.shape == (4 * cfg.replicates, 16, 16) and np.isfinite(theta).all()
        packets[name] = theta.tobytes()
    assert all(packets[a] == packets["damaged"] for a in ("kept_off", "scrambled_off", "donor_off"))
    return packets


def load_written(directory, cfg=CONFIG, expected_tissue=None):
    prior.load_written(directory / "writing", cfg, expected_tissue)  # Full base provenance and packet checks.
    extra_dir = directory / "intervention"
    hashes = readout.manifest_hashes(extra_dir / "intervention_hashes.sha256")
    names = {"bodies", *(f"{prefix}_{a}" for prefix in ("recovery", "probe") for a in EXTRA)}
    assert set(hashes) == {str(extra_dir / f"{n}.npz") for n in names} | {str(extra_dir / "experiment.json")}
    saved = {folder: json.loads((directory / folder / "experiment.json").read_text()) for folder in ("writing", "intervention")}
    assert saved["writing"]["tissue"] == saved["intervention"]["tissue"]
    assert expected_tissue is None or saved["intervention"]["tissue"] == expected_tissue
    assert saved["intervention"]["passes"] is True and all(v is True for v in saved["intervention"]["gates"].values())
    assert canonical_digest(saved["intervention"]["config"]) == canonical_digest(asdict(cfg))
    loaded = {"writing": {}, "intervention": {}}
    for name, (folder, old) in MAPPING.items():
        filename = "boundary" if name == "damaged" else "parent" if name == "parent" else f"recovery_{old}"
        with np.load(directory / folder / f"{filename}.npz", allow_pickle=False) as data:
            loaded[folder][filename] = {k: data[k].copy() for k in data.files}
    packets = packets_from_arrays(loaded["writing"], loaded["intervention"], cfg)
    assert all(hashlib.sha256(packets[name]).hexdigest() == saved[folder]["probe_packet_hashes"][old]
               for name, (folder, old) in MAPPING.items())
    return packets


def donor_metrics(raw, cfg):
    probabilities = raw["probabilities"]
    labels = (np.repeat(np.arange(4), cfg.parents * cfg.draws) + 1) % 4
    correct = probabilities[np.arange(len(labels)), labels].reshape(4 * cfg.parents, cfg.draws)
    own = raw["correctness"]
    return {"donor_accuracy": float(correct.mean()), "donor_record_accuracy": correct.mean(axis=1).tolist(),
            "own_minus_donor": float((own - correct).mean())}


def experiment_readout(ctx, packets, cfg=READOUT_CONFIG, directory=None, legacy_arrays=None):
    assert cfg.parents == ctx["config"].replicates and cfg.sweeps == ctx["config"].sweeps
    assert set(packets) == set(PACKETS)
    incoming = dict(packets)
    theta = np.frombuffer(packets["kept_loop"], dtype=np.float64).reshape(4 * cfg.parents, 16, 16)
    incoming["wrong_packet"] = source.donor(theta, cfg.parents).tobytes()
    incoming["reader_off"] = packets["kept_loop"]
    outcomes = {name: readout.assay(ctx, packet, cfg, name == "reader_off") for name, packet in incoming.items()}
    for name in ("kept_loop", "donor_loop"):
        replay = readout.assay(ctx, packets[name], cfg)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in outcomes[name]["raw"].items())
    legacy, artifacts = {}, {}
    for name, (folder, old) in MAPPING.items():
        observed = readout.assay(ctx, packets[name], replace(cfg, draws=1), legacy=True)
        if directory is None:
            assert legacy_arrays is not None
            expected = legacy_arrays[folder][f"probe_{old}"]
        else:
            with np.load(directory / folder / f"probe_{old}.npz", allow_pickle=False) as data:
                expected = {k: data[k].copy() for k in data.files}
        assert all(np.array_equal(observed["raw"][f"s{s}_{k}"], expected[f"s{s}_{k}"]) for s in cfg.times for k in KEYS)
        legacy[name] = observed["metrics"] | donor_metrics(observed["raw"], replace(cfg, draws=1))
        artifacts[f"legacy_{name}"] = observed["raw"]
    for s in cfg.times:
        for k in KEYS:
            np.testing.assert_array_equal(outcomes["wrong_packet"]["raw"][f"s{s}_{k}"],
                source.donor(outcomes["kept_loop"]["raw"][f"s{s}_{k}"], cfg.parents * cfg.draws))
    for name in ("kept_off", "scrambled_off", "donor_off"):
        assert all(np.array_equal(v, outcomes["damaged"]["raw"][k]) for k, v in outcomes[name]["raw"].items())
    gates = {"two_readout_replays": True, "eleven_current_legacy_anchors": True, "wrong_packet_permutation": True,
             "off_writer_readout_aliases": True,
             "reader_off_chance": outcomes["reader_off"]["metrics"]["accuracy"] == .25,
             "reader_off_message_independent": all(source.base.message_independent(outcomes["reader_off"]["raw"][f"s{s}_V"], cfg.parents * cfg.draws) for s in cfg.times),
             "matched_streams": len({v["rng_final"] for v in outcomes.values()}) == 1,
             "matched_births": all(np.array_equal(v["raw"][f"s0_{k}"], outcomes["kept_loop"]["raw"][f"s0_{k}"])
                                   for v in outcomes.values() for k in ("V", "ema", "R")),
             "theta_only_readout": all(v["theta_unchanged"] and v["R_zero_every_step"] for v in outcomes.values())}
    assert all(v is True for v in gates.values())
    result = {"tissue": ctx["index"], "config": asdict(cfg), "passes": True, "gates": gates,
              "arms": {a: v["metrics"] | donor_metrics(v["raw"], cfg) for a, v in outcomes.items()}, "legacy": legacy,
              "packet_hashes": {a: v["packet_sha256"] for a, v in outcomes.items()},
              "expanded_hashes": {a: v["expanded_sha256"] for a, v in outcomes.items()},
              "rng_final": outcomes["kept_loop"]["rng_final"], "birth_rng_final": outcomes["kept_loop"]["birth_rng_final"]}
    artifacts.update({f"readout_{a}": v["raw"] for a, v in outcomes.items()})
    artifacts["packets"] = {a: np.frombuffer(p, dtype=np.float64).reshape(4 * cfg.parents, 16, 16).copy() for a, p in packets.items()}
    json.dumps(result, allow_nan=False)
    return result, artifacts


def writing_manifests(directory):
    paths = {"writing": directory / "writing/writing_hashes.sha256", "intervention": directory / "intervention/intervention_hashes.sha256"}
    for path in paths.values():
        readout.manifest_hashes(path)
    return {name: sha256_file(path) for name, path in paths.items()}


def read_written(ctx, directory, cfg=READOUT_CONFIG):
    before = writing_manifests(directory)
    packets = load_written(directory, ctx["config"], ctx["index"])
    result, arrays = experiment_readout(ctx, packets, cfg, directory=directory)
    with np.load(directory / "readout/calibration_reader_off.npz", allow_pickle=False) as cal:
        assert all(np.array_equal(arrays["readout_reader_off"][f"s{s}_{k}"], cal[f"s{s}_{k}"])
                   for s in cfg.times for k in ("V", "ema", "R"))
    assert before == writing_manifests(directory)
    result.update(packet_origin="current_body_source_writing", writing_manifest_sha256=before)
    return result, arrays


def calibrated(rows):
    if sorted(r["tissue"] for r in rows) != list(TISSUES):
        return False
    if not all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in rows):
        return False
    return bool(all(all(r[name]["passes"] is True and all(v is True for v in r[name]["gates"].values())
                        and r[name]["tissue"] == r["tissue"] and r[name]["positive_accuracy"] > .25 for r in rows)
                    and math.fsum(r[name]["positive_accuracy"] for r in rows) / 16 >= .75 for name in ("legacy", "readout")))


def classify(rows):
    if sorted(r["tissue"] for r in rows) != list(TISSUES) or not all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in rows):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    rows = sorted(rows, key=lambda r: r["tissue"])
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for (name, left, right, metric), seed in zip(ENDPOINTS, SEEDS):
        values = np.array([r["arms"][left][metric] - r["arms"][right][metric] for r in rows])
        draws = np.random.default_rng(seed).integers(0, 16, (10000, 16))
        interval = np.quantile(values[draws].mean(axis=1), [.05 / 6, 1 - .05 / 6]).tolist()
        positive = int((values > 0).sum())
        contrasts[name] = {"mean": float(values.mean()), "tissue_differences": values.tolist(), "interval": interval,
                          "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000,
                          "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= 12)}
    useful, organized, donor = [contrasts[name]["supported"] for name, *_ in ENDPOINTS]
    label = ("PARENT_THETA_NOT_READABLE" if not eligible else
             "BODY_CONTENT_SPECIFIC_REPAIR_SUPPORTED" if organized and donor and useful else
             "BODY_CONTENT_REDIRECTION_WITHOUT_QUALIFIED_REPAIR" if organized and donor else
             "BODY_ORGANIZATION_BENEFIT_ONLY" if organized else "DONOR_BODY_REDIRECTION_ONLY" if donor else
             "REPAIR_WITHOUT_QUALIFIED_BODY_SOURCE" if useful else "NO_QUALIFIED_BODY_SOURCE_EFFECT")
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def worker(index, root_text, stage):
    assert index in TISSUES and stage in STAGES and source.runtime()["passes"]
    root = external_root(root_text)
    directory = root / "outputs" / RUN_ID / f"tissue_{index}"
    ctx = source.context(index, CONFIG)
    if stage == "calibration":
        result, arrays = prior.calibration(ctx, READOUT_CONFIG)
        for name, raw in arrays.items():
            save_arrays(directory / name, raw, root, "calibration_")
            strict_json(directory / name / "calibration.json", result["legacy" if name == "writing" else "readout"], root)
    elif stage == "writing":
        result, arrays, extras = experiment_writing(ctx)
        save_writing(directory, result, arrays, extras, root)
    else:
        result, arrays = read_written(ctx, directory)
        save_arrays(directory / "readout", arrays, root)
        strict_json(directory / "readout/experiment.json", result, root)
    return result


def fresh_panel(root):
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
    conflicts = [str(p) for p in (root / "runs").glob("*/MANIFEST.json")
                 if p.parent.name != RUN_ID and set(indices(json.loads(p.read_text()))) & set(TISSUES)]
    conflicts.extend(str(p) for p in (root / "outputs").glob("*/tissue_*")
                     if p.parent.name != RUN_ID and p.name in {f"tissue_{i}" for i in TISSUES})
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
    assert counts == {SOURCE_ID: [899, 738], SOURCE_AUDIT: [1642, 2]}
    checked = json.loads((root / "outputs" / SOURCE_AUDIT / "rescore.json").read_text())
    assert checked["passes"] is True and checked["classification"]["label"] == "FRESH_FEEDBACK_RELIABILITY_REPLICATED"
    return counts


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), ws / "protocols/L22_BODY_SOURCE_V1.md", ws / "scripts/run_l22_body_source.sh",
             ws / "scripts/audit_l22_body_source_outputs.py", ws / "tests/test_l22_body_source.py",
             ws / "reviews/L22_FRESH_WRITING_REPLICATION_2026-09-08.md"]
    for kind in ("input", "output"):
        manifest = root / "outputs" / SOURCE_AUDIT / f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root / "runs" / SOURCE_AUDIT / n for n in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    return sorted(set(paths))


def contract():
    return {"run_id": RUN_ID, "source_run": SOURCE_ID, "config": asdict(CONFIG), "readout_config": asdict(READOUT_CONFIG),
            "tissues": list(TISSUES), "workers": WORKERS, "stages": list(STAGES),
            "legacy_modes": {a: asdict(m) for a, m in writing.MODES.items()},
            "extra_modes": {a: {"body_source": body, "mode": asdict(mode)} for a, (body, mode) in EXTRA.items()},
            "packet_mapping": MAPPING, "readout_arms": list(ARMS), "endpoints": ENDPOINTS,
            "bootstrap_seeds": list(SEEDS), "quantiles": [.05 / 6, 1 - .05 / 6], "minimum_positive_tissues": 12,
            "body_operator": "recipient_values_in_stable_cyclic_donor_rank_order", "donor_offset": 1,
            "fresh_parents": True, "retained_scientific_packets_used": 0, "law_verdict_changes": 0,
            "parent_lives": 256, "recovery_lives": 3584, "legacy_diagnostic_readouts": 4352,
            "legacy_calibration_lives": 768, "writing_integrity_lives": 1536, "scientific_readout_lives": 53248,
            "readout_calibration_lives": 12288, "readout_replay_lives": 8192, "legacy_wrapper_replay_lives": 2816,
            "total_lives": 87040, "qualified_output_hashes": 1138, "unqualified_output_hashes": 98}


def disk_preflight(root):
    free, reserve = shutil.disk_usage(root).free, 4 * 1024**3
    return {"passes": bool(free >= reserve), "free_bytes": free, "required_bytes": reserve}


def benchmark_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("immutable run already exists")
    rt, disk, reservation = source.runtime(), disk_preflight(root), fresh_panel(root)
    assert rt["passes"] and disk["passes"]
    counts = source_info(root)
    cfg = source.Config(replicates=2, settle=32, imprint=32, sweeps=32, times=(0, 1, 8, 16, 32))
    rcfg = readout.Config(parents=2, draws=2, sweeps=32, times=(0, 1, 32))
    ctx = source.context(400110, cfg)
    start = time.monotonic()
    old_cal, _ = source.calibration(ctx)
    written, arrays, extras = experiment_writing(ctx)
    writing_seconds = time.monotonic() - start
    packets = packets_from_arrays(arrays, extras, cfg)
    start = time.monotonic()
    new_cal, _ = readout.calibration(ctx, rcfg)
    observed, _ = experiment_readout(ctx, packets, rcfg, legacy_arrays={"writing": arrays, "intervention": extras})
    readout_seconds = time.monotonic() - start
    estimate = writing_seconds * 437.5 + readout_seconds * 3500 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "disposable_tissue": 400110,
              "effect_sizes_not_reported": True, "config": asdict(cfg), "readout_config": asdict(rcfg),
              "writing_seconds": writing_seconds, "readout_seconds": readout_seconds, "projected_seconds": estimate,
              "must_detach": bool(estimate > 600), "passes": bool(all(r["passes"] for r in (old_cal, new_cal, written, observed))),
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
    rt, disk, reservation, counts = source.runtime(), disk_preflight(root), fresh_panel(root), source_info(root)
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
    if (json.loads((run / "STATUS.json").read_text())["status"] != "PREPARED" or (run / "COMPLETE").exists() or (run / "FAILED").exists()
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
    command = [sys.executable, "-m", "laws_confirmation.l22_body_source", "--external-root", str(root), "--run"]
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
    return record  # No polling or waiting after detached launch.


def run_study(root):
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        assert source.runtime()["passes"] and disk_preflight(root)["passes"]
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
                  "readout": records["readout"], "classification": classification, "fresh_parents": True,
                  "retained_scientific_packets_used": 0, "law_verdict_changes": 0}
        strict_json(output / "body_source.json", result, root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"),
                            output / "output_hashes.sha256", root)
        assert len(readout.manifest_hashes(output / "output_hashes.sha256")) == (1138 if qualified else 98)
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
