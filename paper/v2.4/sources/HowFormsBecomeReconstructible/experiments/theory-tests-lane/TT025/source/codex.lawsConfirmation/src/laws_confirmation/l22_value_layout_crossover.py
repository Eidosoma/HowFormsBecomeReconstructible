"""D080: retained donor-value distributions crossed with spatial rank layouts."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import importlib.util
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

from . import l22_fresh_donor_reversal as prior
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

source, writing, readout = prior.source, prior.writing, prior.readout
strict_json, save_npz = prior.strict_json, prior.save_npz
RUN_ID, SOURCE_ID = "l22_value_layout_crossover_v1_attempt1", prior.RUN_ID
TISSUES, WORKERS = tuple(range(30056, 30072)), 4
DISPOSABLES = (402081, 402082)
CONFIG, READOUT_CONFIG = prior.CONFIG, prior.READOUT_CONFIG
STAGES, FIELDS = ("calibration", "writing", "readout"), ("V", "R", "theta")
CROSSES = ("forwardvalues", "reversevalues")
BODIES = (*prior.BODIES, *CROSSES)
FACTORS = {"forward": ("forward", "forward"), "forwardvalues": ("forward", "reverse"),
           "reversevalues": ("reverse", "forward"), "reverse": ("reverse", "reverse")}
READERS = ("damaged", "native")
TARGETS = {"own": 0, "forward": 1, "reverse": -1}
METRICS = tuple(f"{t}_projection" for t in TARGETS) + tuple(f"{t}_accuracy" for t in TARGETS) + ("forward_minus_reverse",)
FUNCTIONAL = (*METRICS[3:],)
MAIN = tuple(f"{b}_{r}" for b in BODIES for r in READERS)
OFF = tuple(f"{b}_{r}_off" for b in BODIES[1:] for r in READERS)
RECOVERIES, REPLAYS = (*MAIN, *OFF), tuple(f"{b}_{r}" for b in CROSSES for r in READERS)
PACKETS = (*MAIN, "parent", "damaged")
ARMS = (*PACKETS, "wrong_forward", "wrong_reverse", "reader_off")
CONTRASTS = {k: dict(v) for k, v in prior.CONTRASTS.items()}
for r in READERS:
    ff, fr, rf, rr = (f"{b}_{r}" for b in ("forward", "forwardvalues", "reversevalues", "reverse"))
    additions = {
        "layout_at_forward_values": {ff: 1, fr: -1},
        "layout_at_reverse_values": {rf: 1, rr: -1},
        "values_at_forward_layout": {ff: 1, rf: -1},
        "values_at_reverse_layout": {fr: 1, rr: -1},
        "value_effect": {ff: .5, fr: .5, rf: -.5, rr: -.5},
        "layout_effect": {ff: .5, fr: -.5, rf: .5, rr: -.5},
        "value_layout_interaction": {ff: 1, fr: -1, rf: -1, rr: 1},
        "crossed_preference": {fr: 1, rf: -1},
        "forwardvalues_minus_forwardshuffled": {fr: 1, f"forwardshuffled_{r}": -1},
        "reversevalues_minus_reverseshuffled": {rf: 1, f"reverseshuffled_{r}": -1},
    }
    CONTRASTS.update({f"{name}_{r}": terms for name, terms in additions.items()})
for b in CROSSES:
    CONTRASTS[f"{b}_native_minus_damaged"] = {f"{b}_native": 1, f"{b}_damaged": -1}
for name in ("value_effect", "layout_effect", "value_layout_interaction"):
    CONTRASTS[f"{name}_reader_interaction"] = {
        **CONTRASTS[f"{name}_native"], **{a: -w for a, w in CONTRASTS[f"{name}_damaged"].items()}}
FOCAL = tuple((f"{name}_{r}", "forward_minus_reverse")
              for name in ("value_effect", "layout_effect", "value_layout_interaction") for r in READERS)


def checker():
    path = Path(__file__).resolve().parents[2]/"scripts/audit_l22_value_layout_crossover_outputs.py"
    spec = importlib.util.spec_from_file_location("d080_independent_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rank_transfer(values, layout):
    """Preserve the exact multiset; ties in layout are ordered by position."""
    assert values.dtype == layout.dtype == np.float64 and values.shape == layout.shape == (128,)
    assert np.isfinite(values).all() and np.isfinite(layout).all()
    order = np.argsort(layout, kind="stable")
    result = np.empty_like(values)
    result[order] = np.sort(values, kind="stable")
    return result, order


def make_bodies(boundary, tissue, cfg=CONFIG):
    result = prior.make_bodies(boundary, tissue, cfg)
    fresh = boundary["fresh"]
    orders = {d: [] for d in ("forward", "reverse")}
    for body, (values_from, layout_from) in FACTORS.items():
        value = boundary["kept_V"].copy()
        for i in range(len(fresh)):
            mask = ~fresh[i]
            transferred, order = rank_transfer(result[f"{values_from}_V"][i][mask],
                                                result[f"{layout_from}_V"][i][mask])
            value[i][mask] = transferred
            if body in ("forward", "reverse"):
                orders[body].append(order)
        if body in CROSSES:
            result[f"{body}_V"] = value
        else:
            np.testing.assert_array_equal(value, result[f"{body}_V"])
    result.update({f"{d}_layout_order": np.array(v) for d, v in orders.items()})
    return result


def geometry(bodies, fresh):
    kept = bodies["kept_V"][~fresh].reshape(len(fresh), 128)
    result = {}
    for b in BODIES:
        v = bodies[f"{b}_V"][~fresh].reshape(len(fresh), 128)
        result[b] = dict(retained_mean=v.mean(axis=1).tolist(), retained_std=v.std(axis=1).tolist(),
            retained_rms=np.sqrt(np.mean(v*v, axis=1)).tolist(), retained_min=v.min(axis=1).tolist(), retained_max=v.max(axis=1).tolist(),
            changed_positions=np.count_nonzero(v != kept, axis=1).tolist(), retained_delta_rms=np.sqrt(np.mean((v-kept)**2, axis=1)).tolist())
    return result


def mode(arm):
    if arm not in RECOVERIES:
        raise ValueError("undeclared body/reader intervention")
    return writing.Mode(reader=arm.split("_")[1], write=arm not in OFF)


def initial_states(boundary, bodies):
    return {a: dict(V=bodies[f"{a.split('_')[0]}_V"].copy(), ema=bodies[f"{a.split('_')[0]}_V"].copy(),
                    R=np.zeros_like(boundary["kept_V"]), theta=boundary["damaged_theta"].copy()) for a in RECOVERIES}


def observe(trace, replicates):
    scores = trace[..., :4]
    assert scores.shape[1] == 4*replicates
    ties = np.isclose(scores, scores.max(axis=2, keepdims=True), rtol=0., atol=1e-12)
    probabilities = ties/ties.sum(axis=2, keepdims=True)
    labels = np.arange(4*replicates)//replicates
    projections, accuracy = [], []
    for shift in TARGETS.values():
        indices = ((labels+shift) % 4)[None, :, None]
        projections.append(np.take_along_axis(scores, indices, axis=2)[..., 0])
        accuracy.append(np.take_along_axis(probabilities, indices, axis=2)[..., 0])
    return np.stack((*projections, *accuracy, accuracy[1]-accuracy[2]), axis=-1)


def observers(raws, cfg=CONFIG):
    full = np.stack([np.stack([observe(raws[a][k], cfg.replicates) for k in
                              ("body_trace", "reference_trace", "theta_trace")], axis=2) for a in MAIN])
    return dict(curves=full.mean(axis=2), strata=full[:, list(cfg.times)].reshape(
        len(MAIN), len(cfg.times), 4, cfg.replicates, 3, len(METRICS)).mean(axis=3))


def describe(data, cfg=CONFIG):
    return {a: {str(s): {f: dict(mean=dict(zip(METRICS, data["curves"][i, s, j].tolist())),
                messages=[dict(zip(METRICS, row)) for row in data["strata"][i, q, :, j].tolist()])
                for j, f in enumerate(FIELDS)} for q, s in enumerate(cfg.times)} for i, a in enumerate(MAIN)}


def experiment_writing(ctx, before, parent, boundary):
    cfg = ctx["config"]
    fresh, damaged = boundary["fresh"], boundary["damaged_theta"]
    bodies = make_bodies(boundary, ctx["index"], cfg)
    initial = initial_states(boundary, bodies)
    parent_hash, native_hash = source.base.state_digest(parent), source.base.array_digest(ctx["native"])
    outcomes = {a: writing.recover(ctx, initial[a], mode(a), parent, fresh) for a in RECOVERIES}
    raw = {a: r["raw"] for a, r in outcomes.items()}
    for a in REPLAYS:
        replay = writing.recover(ctx, initial[a], mode(a), parent, fresh)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in raw[a].items())
    for a in OFF:
        assert writing.aliases(raw[a[:-4]], raw[a], cfg)
        assert all(np.array_equal(raw[a][k], raw[a[:-4]][k]) for k in ("body_trace", "reference_trace"))
        assert all(np.array_equal(raw[a][f"s{s}_theta"], damaged) for s in cfg.times)
    assert source.base.state_digest(parent) == parent_hash and source.base.array_digest(ctx["native"]) == native_hash
    assert len({r["rng_final"] for r in outcomes.values()}) == 1
    data = observers(raw, cfg)
    record = dict(tissue=ctx["index"], passes=True, config=asdict(cfg), tissue_config=asdict(ctx["tissue"]),
        parent_origin="retained_D079_parent", four_crossover_replays=True, twelve_writer_off_aliases=True,
        source_parent_sha256=parent_hash, source_native_sha256=native_hash, geometry=geometry(bodies, fresh),
        initial_hashes={a: r["initial_hash"] for a, r in outcomes.items()}, recovery_rng_final={a: r["rng_final"] for a, r in outcomes.items()},
        recovery={a: r["metrics"] for a, r in outcomes.items()}, arms=describe(data, cfg))
    artifacts = dict(before=before, parent=parent, boundary=boundary, bodies=bodies, writing=data)
    artifacts.update({f"recovery_{a}": r for a, r in raw.items()})
    return record, artifacts


def target_values(raw, cfg):
    p = raw["probabilities"].reshape(4*cfg.parents, cfg.draws, 4)
    labels = np.arange(4*cfg.parents)//cfg.parents
    values = {f"{name}_accuracy": np.take_along_axis(p, ((labels+offset) % 4)[:, None, None], axis=2)[..., 0]
              for name, offset in TARGETS.items()}
    return values | {"forward_minus_reverse": values["forward_accuracy"]-values["reverse_accuracy"]}


def extra_metrics(raw, cfg):
    values = target_values(raw, cfg)
    record = {m: float(v.mean()) for m, v in values.items()}
    record["message_means"] = {m: v.reshape(4, -1).mean(axis=1).tolist() for m, v in values.items()}
    record["targets"] = {}
    for t in TARGETS:
        v = values[f"{t}_accuracy"]
        means = v.mean(axis=1)
        record["targets"][t] = dict(record_accuracy=means.tolist(), record_within_variance=v.var(axis=1).tolist(),
            within_variance=float(v.var(axis=1).mean()), between_variance=float(means.var()), total_variance=float(v.var()),
            always_correct=int(np.all(v == 1., axis=1).sum()), always_incorrect=int(np.all(v == 0., axis=1).sum()),
            varying=int(np.any(v != v[:, :1], axis=1).sum()))
    return record


def experiment(ctx, packets, cfg=READOUT_CONFIG):
    assert set(packets) == set(PACKETS) and cfg.parents == 4
    original = dict(packets)
    incoming = dict(packets)
    for d, shift in (("forward", 1), ("reverse", -1)):
        theta = np.frombuffer(packets[f"{d}values_native"], dtype=np.float64).reshape(4*cfg.parents, 16, 16)
        incoming[f"wrong_{d}"] = np.roll(theta, -shift*cfg.parents, axis=0).tobytes()
    incoming["reader_off"] = packets["forwardvalues_native"]
    results = {a: readout.assay(ctx, incoming[a], cfg, off=a == "reader_off") for a in ARMS}
    for a in REPLAYS:
        replay = readout.assay(ctx, packets[a], cfg)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in results[a]["raw"].items())
    assert packets == original
    assert all(r["theta_unchanged"] is True and r["R_zero_every_step"] is True for r in results.values())
    assert len({r["rng_final"] for r in results.values()}) == len({r["birth_rng_final"] for r in results.values()}) == 1
    values = {a: target_values(r["raw"], cfg) for a, r in results.items()}
    paired = {}
    for name, terms in CONTRASTS.items():
        paired[name] = {}
        for metric in FUNCTIONAL:
            d = sum(w*values[a][metric] for a, w in terms.items())
            paired[name][metric] = dict(positive=float((d > 1e-12).mean()), negative=float((d < -1e-12).mean()),
                                        tied=float((abs(d) <= 1e-12).mean()))
    record = dict(tissue=ctx["index"], passes=True, config=asdict(cfg), packet_origin="current_D080_writing_retained_D079_parent",
        four_crossover_replays=True, theta_unchanged_R_zero=True, arms={a: r["metrics"] | extra_metrics(r["raw"], cfg) for a, r in results.items()},
        paired=paired, packet_hashes={a: r["packet_sha256"] for a, r in results.items()},
        expanded_hashes={a: r["expanded_sha256"] for a, r in results.items()},
        rng_final=results["forwardvalues_native"]["rng_final"], birth_rng_final=results["forwardvalues_native"]["birth_rng_final"])
    artifacts = {f"readout_{a}": r["raw"] for a, r in results.items()}
    artifacts["packets"] = {a: np.frombuffer(p, dtype=np.float64).reshape(4*cfg.parents, 16, 16).copy() for a, p in packets.items()}
    return record, artifacts


def summarize(delta, groups):
    d = np.asarray(delta)
    return dict(tissue_differences=d.tolist(), mean=d.mean(axis=0).tolist(), minimum=d.min(axis=0).tolist(), maximum=d.max(axis=0).tolist(),
        positive=(d > 1e-12).sum(axis=0).tolist(), negative=(d < -1e-12).sum(axis=0).tolist(),
        tied=(abs(d) <= 1e-12).sum(axis=0).tolist(), message_mean=np.asarray(groups).mean(axis=0).tolist())


def pooled(rows):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    arms = {a: {m: float(np.mean([r["arms"][a][m] for r in rows])) for m in FUNCTIONAL} for a in ARMS}
    contrasts = {name: {m: summarize([sum(w*r["arms"][a][m] for a, w in terms.items()) for r in rows],
        [sum(w*np.array(r["arms"][a]["message_means"][m]) for a, w in terms.items()) for r in rows]) for m in FUNCTIONAL}
        for name, terms in CONTRASTS.items()}
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    return dict(arms=arms, contrasts=contrasts, parent_readability=parents,
                parent_readable=bool(min(parents) > .25 and np.mean(parents) >= .75))


def writing_pooled(rows, cfg=CONFIG):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    curves = np.array([[[[[r["arms"][a][str(s)][f]["mean"][m] for m in METRICS] for f in FIELDS]
                         for s in cfg.times] for a in MAIN] for r in rows])
    groups = np.array([[[[[[r["arms"][a][str(s)][f]["messages"][g][m] for m in METRICS] for f in FIELDS]
                          for g in range(4)] for s in cfg.times] for a in MAIN] for r in rows])
    contrasts = {name: summarize(sum(w*curves[:, MAIN.index(a)] for a, w in terms.items()),
                                sum(w*groups[:, MAIN.index(a)] for a, w in terms.items())) for name, terms in CONTRASTS.items()}
    return dict(arm_means=curves.mean(axis=0).tolist(), contrasts=contrasts)


def load_source(original, tissue, cfg):
    common = checker().common
    metadata = json.loads((original/"writing.json").read_text())
    assert metadata["tissue"] == tissue and metadata["passes"] is True
    assert metadata["parent_origin"] == "fresh_source_preparation" and metadata["source_prepare_anchor"] is True
    assert canonical_digest(metadata["config"]) == canonical_digest(asdict(cfg))
    before, parent, boundary = (common.arrays(original/f"{name}.npz") for name in ("before", "parent", "boundary"))
    assert source.base.state_digest(parent) == metadata["source_parent_sha256"]
    return before, parent, boundary, metadata


def disposable_source(root, tissue, directory, cfg=CONFIG, rcfg=READOUT_CONFIG):
    """Create legacy-shaped fixtures only at explicitly disposable addresses."""
    assert tissue in DISPOSABLES and cfg.replicates == rcfg.parents == 4
    directory = require_beneath(directory, root)
    directory.mkdir()
    ctx = source.context(tissue, cfg)
    cal, raw = readout.calibration(ctx, rcfg)
    for name, value in raw.items():
        save_npz(directory/f"calibration_{name}.npz", value, root)
    strict_json(directory/"calibration.json", cal, root)
    record, artifacts = prior.experiment_writing(ctx)
    for name, value in artifacts.items():
        save_npz(directory/f"{name}.npz", value, root)
    strict_json(directory/"writing.json", record, root)
    packets = {a: (artifacts[f"recovery_{a}"][f"s{cfg.sweeps}_theta"] if a in prior.MAIN else
                   artifacts["parent"]["theta"] if a == "parent" else artifacts["boundary"]["damaged_theta"]).tobytes()
               for a in prior.PACKETS}
    row, raws = prior.experiment(ctx, packets, rcfg)
    for name, value in raws.items():
        save_npz(directory/f"{name}.npz", value, root)
    strict_json(directory/"readout.json", row, root)
    return directory


def execute_cell(root, tissue, stage, output, cfg=CONFIG, rcfg=READOUT_CONFIG, original=None):
    assert tissue in (*TISSUES, *DISPOSABLES) and stage in STAGES
    assert cfg.replicates == rcfg.parents == 4 and cfg.sweeps == rcfg.sweeps
    if tissue in TISSUES:
        assert original is None and cfg == CONFIG and rcfg == READOUT_CONFIG
        original = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"
    else:
        assert original is not None
        original = require_beneath(original, root)
    check = checker()
    check.runtime(root)
    assert source.runtime()["passes"] is True
    ctx = source.context(tissue, cfg)
    output = require_beneath(output, root)
    if stage == "calibration":
        output.mkdir()
        record, raws = readout.calibration(ctx, rcfg)
        for name, raw in raws.items():
            save_npz(output/f"calibration_{name}.npz", raw, root)
        strict_json(output/"calibration.json", record, root)
        checked = check.check_calibration(original, output, tissue, asdict(rcfg))
    elif stage == "writing":
        assert (output/"calibration.json").is_file() and not (output/"writing.json").exists()
        before, parent, boundary, metadata = load_source(original, tissue, cfg)
        assert canonical_digest(asdict(ctx["tissue"])) == canonical_digest(metadata["tissue_config"])
        assert source.base.array_digest(ctx["native"]) == metadata["source_native_sha256"]
        np.testing.assert_array_equal(ctx["native"], boundary["native_theta"])
        record, raws = experiment_writing(ctx, before, parent, boundary)
        for name, raw in raws.items():
            save_npz(output/f"{name}.npz", raw, root)
        strict_json(output/"writing.json", record, root)
        checked = check.check_writing(original, output, tissue, asdict(cfg))
    else:
        assert (output/"writing.json").is_file() and not (output/"readout.json").exists()
        packets = {}
        for a in PACKETS:
            file, key = (f"recovery_{a}.npz", f"s{cfg.sweeps}_theta") if a in MAIN else ("parent.npz", "theta") if a == "parent" else ("boundary.npz", "damaged_theta")
            packets[a] = check.common.arrays(output/file)[key].tobytes()
        record, raws = experiment(ctx, packets, rcfg)
        for name, raw in raws.items():
            save_npz(output/f"{name}.npz", raw, root)
        strict_json(output/"readout.json", record, root)
        checked = check.check_readout(original, output, tissue, asdict(cfg), asdict(rcfg))
    return record, checked

def calibrated(rows):
    return bool([r["tissue"] for r in rows] == list(TISSUES) and all(r["passes"] is True and
        all(v is True for v in r["gates"].values()) and r["positive_accuracy"] > .25 for r in rows)
        and np.mean([r["positive_accuracy"] for r in rows]) >= .75)


def retained_panel(root):
    original = root/"outputs"/SOURCE_ID
    assert all((original/f"tissue_{t}"/"writing.json").is_file() for t in TISSUES)
    return dict(passes=True, tissues=list(TISSUES), source_run=SOURCE_ID, fresh=False)

def source_inputs(root):
    expected, paths = {}, set()
    for kind, count in (("input", 3843), ("output", 707)):
        manifest = root/"outputs"/SOURCE_ID/f"{kind}_hashes.sha256"
        rows = [line.split("  ", 1) for line in manifest.read_text().splitlines()]
        assert len(rows) == len({p for _, p in rows}) == count
        paths.add(manifest)
        for digest, filename in rows:
            assert Path(filename).is_absolute() and (filename not in expected or expected[filename] == digest)
            expected[filename] = digest
    run = root/"runs"/SOURCE_ID
    status = json.loads((run/"STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["run_id"] == SOURCE_ID
    assert status["completed_cleanly"] is True and status["verified_saved_analysis"] is True and status["checked_tissues"] == 16
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    result = json.loads((root/"outputs"/SOURCE_ID/"analysis.json").read_text())
    assert all(canonical_digest(result[k]) == canonical_digest(v) for k, v in prior.contract().items())
    verification = json.loads((root/"outputs"/SOURCE_ID/"verification.json").read_text())
    assert verification["passes"] is True and verification["pooled_verified"] is True
    assert set(verification["checks"]) == set(prior.STAGES)
    for rows in verification["checks"].values():
        assert [r["tissue"] for r in rows] == list(prior.TISSUES) and all(r["passes"] is True for r in rows)
    assert all(sha256_file(Path(p)) == d for p, d in expected.items())
    return sorted(paths | {Path(p) for p in expected} | {run/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE")})


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l22_value_layout_crossover.py", "scripts/audit_l22_value_layout_crossover_outputs.py",
           "tests/test_l22_value_layout_crossover.py", "scripts/run_l22_value_layout_crossover.sh",
           "protocols/L22_VALUE_LAYOUT_CROSSOVER_V1.md", "reviews/L22_FRESH_DONOR_REVERSAL_2026-09-09.md")
    return sorted(set(source_inputs(root)) | {ws/p for p in own})

def contract():
    return dict(run_id=RUN_ID, source_run=SOURCE_ID, config=asdict(CONFIG), readout_config=asdict(READOUT_CONFIG),
        tissues=list(TISSUES), workers=WORKERS, stages=list(STAGES), disposable_tissues=list(DISPOSABLES),
        bodies=list(BODIES), readers=list(READERS), targets=TARGETS, fields=list(FIELDS), metrics=list(METRICS),
        functional_metrics=list(FUNCTIONAL), main_arms=list(MAIN), recovery_arms=list(RECOVERIES), writer_off=list(OFF),
        replays=list(REPLAYS), packets=list(PACKETS), arms=list(ARMS), contrasts=CONTRASTS, focal_endpoints=[list(v) for v in FOCAL],
        factors={b: list(v) for b, v in FACTORS.items()}, layout_definition="ascending_value_ranks_stable_position_ties",
        direction_tolerance=1e-12, fresh_parent_panel=False, retained_parents=256, new_training_lives=0,
        donor_steps=[1, -1], parent_execution_lives=0, saved_recovery_cells=416, recovery_replay_cells=64,
        new_writing_lives=1024, reexecuted_prior_writable_lives=2560, total_recovery_lives=7680,
        scored_readout_lives=77824, replay_lives=16384, calibration_lives=12288, total_readout_lives=106496,
        total_executed_lives=114176, historical_recovery_anchors=288, historical_readout_anchors=192,
        writer_off_packet_aliases=192, original_records_per_tissue=16, output_hashes=899, law_verdict_changes=0,
        inference="outcome_informed_retained_panel_factorial_no_automatic_pass_gate")

def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def preflight(root):
    cpus = checker().runtime(root)
    assert source.runtime()["passes"] is True
    if shutil.disk_usage(root).free < 4*1024**3:
        raise RuntimeError("at least 4 GiB external free space required")
    retained_panel(root)
    return cpus


def benchmark(root):
    if any(p.exists() for p in (root/"runs"/RUN_ID, root/"outputs"/RUN_ID, timing_path(root))):
        raise FileExistsError("immutable benchmark or run already exists")
    cpus = preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    temporary = Path(tempfile.mkdtemp(prefix="l22-value-layout-benchmark-", dir=root/"tmp"))
    fixture_start = time.monotonic()
    original = disposable_source(root, DISPOSABLES[1], temporary/"disposable_source")
    fixture_seconds = time.monotonic()-fixture_start
    start = time.monotonic()
    for stage in STAGES:
        execute_cell(root, DISPOSABLES[1], stage, temporary/f"tissue_{DISPOSABLES[1]}", original=original)
    elapsed = time.monotonic()-start
    assert all(sha256_file(Path(p)) == d for p, d in hashes.items())
    record = dict(run_id=RUN_ID, measured_utc=utc_now(), disposable_tissue=DISPOSABLES[1], tissue_seconds=elapsed,
        projected_seconds=elapsed*24+90, must_detach=bool(elapsed*24+90 > 600), passes=True, effects_not_reported=True,
        directory=str(temporary), disposable_fixture_seconds=fixture_seconds, cpu_affinity=cpus, input_sha256=hashes)
    strict_json(timing_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable value/layout study already exists")
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["run_id"] == RUN_ID and timing["passes"] is True and timing["input_sha256"] == hashes
    assert timing["disposable_tissue"] == DISPOSABLES[1] and timing["effects_not_reported"] is True
    assert timing["tissue_seconds"] > 0 and np.isfinite(timing["tissue_seconds"])
    assert timing["projected_seconds"] == timing["tissue_seconds"]*24+90
    assert timing["must_detach"] is (timing["projected_seconds"] > 600)
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), benchmark=timing, cpu_affinity=cpus, reservation=retained_panel(root),
        input_sha256=hashes, hash_contract=canonical_digest(hashes), environment=environment_manifest())
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    strict_json(run/"MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output/"input_hashes.sha256", root)
    strict_json(run/"STATUS.json", dict(status="PREPARED", run_id=RUN_ID), root)
    print(json.dumps(dict(status="PREPARED", input_hashes=len(hashes), estimated_seconds=timing["projected_seconds"])), flush=True)
    return manifest


def verify(root):
    run = root/"runs"/RUN_ID
    manifest = json.loads((run/"MANIFEST.json").read_text())
    assert json.loads((run/"STATUS.json").read_text())["status"] == "PREPARED"
    assert not (run/"COMPLETE").exists() and not (run/"FAILED").exists()
    for k, v in contract().items():
        assert canonical_digest(manifest[k]) == canonical_digest(v), k
    hashes = manifest["input_sha256"]
    assert set(hashes) == {str(p) for p in input_paths(root)+[timing_path(root)]}
    assert hashes and canonical_digest(hashes) == manifest["hash_contract"]
    assert all(sha256_file(Path(p)) == d for p, d in hashes.items())
    timing = json.loads(timing_path(root).read_text())
    assert manifest["benchmark"] == timing and timing["must_detach"] is (timing["projected_seconds"] > 600)
    retained_panel(root)
    return manifest


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest, run = verify(root), root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    paths = [root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    paths[0].parent.mkdir(exist_ok=True)
    with paths[0].open("xb") as out, paths[1].open("xb") as err:
        process = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l22_value_layout_crossover",
            "--external-root", str(root), "--run"], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=process.pid, launched_utc=utc_now(), polling_owner="user",
        estimated_seconds=manifest["benchmark"]["projected_seconds"], stdout_log=str(paths[0]), stderr_log=str(paths[1]), status=str(run/"STATUS.json"))
    strict_json(run/"LAUNCH.json", record, root)
    atomic_text(run/"RUN.pid", f"{process.pid}\n", root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # Deliberately never wait or poll.


def cells(root, output, stage):
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        tasks = {pool.submit(execute_cell, root, t, stage, output/f"tissue_{t}"): t for t in TISSUES}
        for future in as_completed(tasks):
            yield tasks[future], future.result()


def run_study(root):
    manifest = verify(root)
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached execution required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        values, checks = {}, {}
        for stage in STAGES:
            values[stage], checks[stage] = {}, {}
            strict_json(run/"STATUS.json", dict(status="RUNNING", run_id=RUN_ID, stage=stage, checked_tissues=0, updated_utc=utc_now()), root)
            for tissue, (record, checked) in cells(root, output, stage):
                assert tissue not in values[stage] and record["tissue"] == checked["tissue"] == tissue
                assert record["passes"] is True and checked["passes"] is True
                values[stage][tissue], checks[stage][tissue] = record, checked
                strict_json(run/"STATUS.json", dict(status="RUNNING", run_id=RUN_ID, stage=stage, checked_tissues=len(checks[stage]), updated_utc=utc_now()), root)
                print(f"D080 {stage} and independent check: tissue {tissue} complete", flush=True)
            assert sorted(values[stage]) == sorted(checks[stage]) == list(TISSUES)
            if stage == "calibration" and not calibrated([values[stage][t] for t in TISSUES]):
                raise RuntimeError("readout calibration unqualified; no scientific writing/readouts allowed")
        rows, wrows = [values["readout"][t] for t in TISSUES], [values["writing"][t] for t in TISSUES]
        summary, wsummary = pooled(rows), writing_pooled(wrows)
        check = checker()
        assert check.check_pool(rows, summary) and check.check_writing_pool(wrows, wsummary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        result = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, calibration_qualified=True,
            calibrations=[values["calibration"][t] for t in TISSUES], writing_results=wrows, writing_pooled=wsummary, results=rows, pooled=summary)
        strict_json(output/"analysis.json", result, root)
        strict_json(output/"verification.json", dict(passes=True, checked_utc=utc_now(), law_verdict_changes=0,
            checks={stage: [checks[stage][t] for t in TISSUES] for stage in STAGES}, pooled_verified=True), root)
        published = json.loads((output/"analysis.json").read_text())
        assert check.check_pool(published["results"], published["pooled"])
        assert check.check_writing_pool(published["writing_results"], published["writing_pooled"])
        check.common.close(published["pooled"], summary)
        check.common.close(published["writing_pooled"], wsummary)
        paths = [output/"input_hashes.sha256", output/"analysis.json", output/"verification.json"]
        paths.extend(p for t in TISSUES for p in (output/f"tissue_{t}").iterdir())
        assert len(paths) == 899
        write_hash_manifest(paths, output/"output_hashes.sha256", root)
        assert check.common.manifest_check(output/"output_hashes.sha256") == 899
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
            completed_cleanly=True, verified_saved_analysis=True, checked_tissues=16, scored_readout_lives=77824,
            new_training_lives=0, new_writing_lives=1024, parent_readable=summary["parent_readable"])
        strict_json(run/"STATUS.json", status, root)
        atomic_text(run/"COMPLETE", status["completed_utc"]+"\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0
    except Exception as error:
        status = dict(status="FAILED", run_id=RUN_ID, failed_utc=utc_now(), error=str(error), traceback=traceback.format_exc())
        strict_json(run/"STATUS.json", status, root)
        atomic_text(run/"FAILED", status["failed_utc"]+"\n", root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for operation in ("benchmark", "prepare", "run", "detach"):
        group.add_argument(f"--{operation}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
