"""D078: actual surviving donor values as a source of functional record content."""

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

from . import l22_residual_record_readout as prior
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

fixed, source, readout = prior.prior, prior.source, prior.readout
writing = fixed.writing
RUN_ID = "l22_actual_donor_body_v1_attempt1"
SOURCE_ID, WRITING_ID, ANCESTOR_ID = prior.RUN_ID, fixed.RUN_ID, fixed.SOURCE_ID
TISSUES, WORKERS = tuple(range(30040, 30056)), 4
CONFIG, READOUT_CONFIG = fixed.CONFIG, readout.CONFIG
STEPS, FIELDS, METRICS = fixed.STEPS, fixed.FIELDS, fixed.METRICS
BODIES = ("kept", "scrambled", "ranked", "actual", "donorshuffled")
MAIN = tuple(f"{b}_{r}" for b in BODIES for r in ("damaged", "native"))
OFF = tuple(f"{b}_{r}_off" for b in ("actual", "donorshuffled") for r in ("damaged", "native"))
RECOVERIES = (*MAIN, *OFF)
PACKETS, ARMS = (*MAIN, "parent", "damaged"), (*MAIN, "parent", "damaged", "wrong", "reader_off")
STAGES = ("calibration", "writing", "readout")
RECOVERY_ANCHORS = {a: a.replace("ranked", "donor") for a in MAIN[:6]}
ANCHORS = {"kept_damaged": ("ancestor", "kept_fixed"),
           **{a: ("previous", a.replace("ranked", "donor")) for a in MAIN[2:6]},
           "parent": ("previous", "parent"), "damaged": ("previous", "damaged")}
CONTRASTS = {f"{left}_minus_{right}_{r}": {f"{left}_{r}": 1, f"{right}_{r}": -1}
             for left, right in (("actual", "kept"), ("actual", "ranked"), ("actual", "donorshuffled"),
                                 ("actual", "scrambled"), ("donorshuffled", "scrambled"))
             for r in ("damaged", "native")}
CONTRASTS.update(actual_specific_reader_interaction={"actual_native": 1, "donorshuffled_native": -1,
                                                    "actual_damaged": -1, "donorshuffled_damaged": 1})
CONTRASTS.update({f"{b}_native_minus_damaged": {f"{b}_native": 1, f"{b}_damaged": -1}
                 for b in ("actual", "donorshuffled")})
strict_json, save_npz = prior.strict_json, prior.save_npz
extra_metrics, donor_values = prior.extra_metrics, prior.donor_values


def checker():
    path = Path(__file__).resolve().parents[2]/"scripts/audit_l22_actual_donor_body_outputs.py"
    spec = importlib.util.spec_from_file_location("d078_independent_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_bodies(boundary, ranked, tissue, cfg=CONFIG):
    kept, fresh = boundary["kept_V"], boundary["fresh"]
    n = 4*cfg.replicates
    assert kept.shape == fresh.shape == (n,16,16) and kept.dtype == np.float64 and fresh.dtype == bool
    assert np.isfinite(kept).all() and np.all(fresh.sum(axis=(1,2)) == 128)
    indices = np.roll(np.arange(n), -cfg.replicates)
    rng = source.RNG(tissue, "shuffle", cfg.replicates).generator
    permutations = np.array([rng.permutation(128) for _ in range(cfg.replicates)])
    actual, shuffled, own_shuffle = kept.copy(), kept.copy(), kept.copy()
    for i,j in enumerate(indices):
        np.testing.assert_array_equal(fresh[i], fresh[j])
        mask = ~fresh[i]
        actual[i][mask] = kept[j][mask]
        shuffled[i][mask] = kept[j][mask][permutations[i % cfg.replicates]]
        own_shuffle[i][mask] = kept[i][mask][permutations[i % cfg.replicates]]
    np.testing.assert_array_equal(own_shuffle, boundary["scrambled_V"])
    return dict(kept_V=kept.copy(), scrambled_V=own_shuffle, ranked_V=ranked["donor_V"].copy(),
                actual_V=actual, donorshuffled_V=shuffled, donor_indices=indices, permutations=permutations)


def geometry(bodies, fresh):
    kept = bodies["kept_V"]
    result = {}
    for body in BODIES:
        value = bodies[f"{body}_V"]
        retained = value[~fresh].reshape(len(kept),128)
        result[body] = dict(retained_mean=retained.mean(axis=1).tolist(), retained_std=retained.std(axis=1).tolist(),
            retained_rms=np.sqrt(np.mean(retained**2,axis=1)).tolist(), retained_min=retained.min(axis=1).tolist(),
            retained_max=retained.max(axis=1).tolist(), changed_positions=np.count_nonzero(value != kept,axis=(1,2)).tolist(),
            retained_delta_rms=np.sqrt(np.mean((retained-kept[~fresh].reshape(len(kept),128))**2,axis=1)).tolist())
    return result


def mode(arm):
    if arm not in RECOVERIES:
        raise ValueError("undeclared body/reader intervention")
    return writing.Mode(reader=arm.split("_")[1], write=arm not in OFF)


def initial_states(boundary, bodies):
    result = {}
    for arm in RECOVERIES:
        v = bodies[f"{arm.split('_')[0]}_V"]
        result[arm] = dict(V=v.copy(), ema=v.copy(), R=np.zeros_like(v), theta=boundary["damaged_theta"].copy())
    return result


def observers(raws, cfg=CONFIG):
    full = np.stack([np.stack([fixed.prior.observers(raws[a][k]) for k in
                              ("body_trace", "reference_trace", "theta_trace")], axis=2) for a in MAIN])
    return dict(curves=full.mean(axis=2),
                strata=full[:,list(cfg.times)].reshape(len(MAIN),len(cfg.times),4,4,3,5).mean(axis=3))


def describe(data, cfg=CONFIG):
    return {a: {str(s): {f: dict(mean=dict(zip(METRICS,data["curves"][i,s,j].tolist())),
                messages=[dict(zip(METRICS,row)) for row in data["strata"][i,q,:,j].tolist()])
                for j,f in enumerate(FIELDS)} for q,s in enumerate(cfg.times)} for i,a in enumerate(MAIN)}


def experiment_writing(ctx, parent, boundary, ranked):
    cfg = ctx["config"]
    bodies = make_bodies(boundary,ranked,ctx["index"],cfg)
    initial = initial_states(boundary,bodies)
    parent_hash, native_hash = source.base.state_digest(parent), source.base.array_digest(ctx["native"])
    outcomes = {a: writing.recover(ctx,initial[a],mode(a),parent,boundary["fresh"]) for a in RECOVERIES}
    raw = {a:r["raw"] for a,r in outcomes.items()}
    for a in ("actual_damaged","actual_native"):
        repeat = writing.recover(ctx,initial[a],mode(a),parent,boundary["fresh"])
        assert all(np.array_equal(v,repeat["raw"][k]) for k,v in raw[a].items())
    for a in OFF:
        assert writing.aliases(raw[a[:-4]],raw[a],cfg)
        assert all(np.array_equal(raw[a][k],raw[a[:-4]][k]) for k in ("body_trace","reference_trace"))
        assert all(np.array_equal(raw[a][f"s{s}_theta"],boundary["damaged_theta"]) for s in cfg.times)
    assert source.base.state_digest(parent) == parent_hash and source.base.array_digest(ctx["native"]) == native_hash
    assert len({r["rng_final"] for r in outcomes.values()}) == 1
    data = observers(raw,cfg)
    record = dict(tissue=ctx["index"],passes=True,config=asdict(cfg),geometry=geometry(bodies,boundary["fresh"]),
        initial_hashes={a:r["initial_hash"] for a,r in outcomes.items()},
        recovery_rng_final={a:r["rng_final"] for a,r in outcomes.items()},
        recovery={a:r["metrics"] for a,r in outcomes.items()},arms=describe(data,cfg),
        two_actual_replays=True,four_writer_off_aliases=True,source_parent_sha256=parent_hash,source_native_sha256=native_hash)
    artifacts = {f"recovery_{a}":r for a,r in raw.items()} | {"bodies":bodies,"writing":data}
    return record,artifacts


def experiment(ctx, packets, cfg=READOUT_CONFIG):
    assert set(packets) == set(PACKETS) and cfg.parents == 4
    original = dict(packets)
    incoming = packets | {"wrong": source.donor(np.frombuffer(packets["actual_native"], dtype=np.float64).reshape(16,16,16), 4).tobytes(),
                          "reader_off": packets["actual_native"]}
    results = {a: readout.assay(ctx, incoming[a], cfg, off=a == "reader_off") for a in ARMS}
    for arm in ("actual_native", "actual_damaged"):
        replay = readout.assay(ctx, packets[arm], cfg)
        assert all(np.array_equal(v, replay["raw"][k]) for k, v in results[arm]["raw"].items())
    assert packets == original
    assert all(r["theta_unchanged"] is True and r["R_zero_every_step"] is True for r in results.values())
    assert len({r["rng_final"] for r in results.values()}) == len({r["birth_rng_final"] for r in results.values()}) == 1
    paired = {}
    for name, terms in CONTRASTS.items():
        if len(terms) != 2:
            continue
        paired[name] = {}
        for metric in ("own", "donor"):
            delta = sum(w*(results[a]["raw"]["correctness"] if metric == "own" else donor_values(results[a]["raw"], cfg)) for a, w in terms.items())
            paired[name][metric] = dict(improved=float((delta > 0).mean()), worsened=float((delta < 0).mean()), tied=float((delta == 0).mean()))
    record = dict(tissue=ctx["index"], passes=True, config=asdict(cfg), packet_origin="current_D078_writing_and_D074_anchors",
                  arms={a: r["metrics"] | extra_metrics(r["raw"], cfg) for a, r in results.items()}, paired=paired,
                  packet_hashes={a: r["packet_sha256"] for a, r in results.items()}, expanded_hashes={a: r["expanded_sha256"] for a, r in results.items()},
                  rng_final=results["actual_native"]["rng_final"], birth_rng_final=results["actual_native"]["birth_rng_final"],
                  two_new_packet_replays=True, theta_unchanged_R_zero=True)
    artifacts = {f"readout_{a}": r["raw"] for a, r in results.items()}
    artifacts["packets"] = {a: np.frombuffer(p, dtype=np.float64).reshape(16,16,16).copy() for a, p in packets.items()}
    return record, artifacts


def pooled(rows):
    if [r["tissue"] for r in rows] != list(TISSUES):
        raise ValueError("all sixteen ordered tissue rows required")
    arms = {a: {m: float(np.mean([r["arms"][a][m] for r in rows])) for m in ("accuracy", "donor_accuracy", "own_minus_donor")}
            for a in ARMS}
    contrasts = {}
    for name, terms in CONTRASTS.items():
        contrasts[name] = {}
        for metric, grouped in (("accuracy", "own_message_accuracy"), ("donor_accuracy", "donor_message_accuracy")):
            delta = np.array([sum(w*r["arms"][a][metric] for a, w in terms.items()) for r in rows])
            groups = np.array([sum(w*np.array(r["arms"][a][grouped]) for a, w in terms.items()) for r in rows])
            contrasts[name][metric] = dict(tissue_differences=delta.tolist(), mean=float(delta.mean()),
                minimum=float(delta.min()), maximum=float(delta.max()), positive=int((delta > 1e-12).sum()),
                negative=int((delta < -1e-12).sum()), tied=int((abs(delta) <= 1e-12).sum()), message_mean=groups.mean(axis=0).tolist())
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    return dict(arms=arms, contrasts=contrasts, parent_readability=parents,
                parent_readable=bool(min(parents) > .25 and np.mean(parents) >= .75))


def writing_pooled(rows, cfg=CONFIG):
    if [r["tissue"] for r in rows] != list(TISSUES):
        raise ValueError("all sixteen writing panels required")
    curves = np.array([[[[list(r["arms"][a][str(s)][f]["mean"][m] for m in METRICS)
                          for f in FIELDS] for s in cfg.times] for a in MAIN] for r in rows])
    groups = np.array([[[[[[r["arms"][a][str(s)][f]["messages"][g][m] for m in METRICS]
                           for f in FIELDS] for g in range(4)] for s in cfg.times] for a in MAIN] for r in rows])
    result = {}
    for name,terms in CONTRASTS.items():
        delta = sum(w*curves[:,MAIN.index(a)] for a,w in terms.items())
        strata = sum(w*groups[:,MAIN.index(a)] for a,w in terms.items())
        result[name] = dict(tissue_differences=delta.tolist(),mean=delta.mean(axis=0).tolist(),
            minimum=delta.min(axis=0).tolist(),maximum=delta.max(axis=0).tolist(),
            positive=(delta>1e-12).sum(axis=0).tolist(),negative=(delta< -1e-12).sum(axis=0).tolist(),
            tied=(abs(delta)<=1e-12).sum(axis=0).tolist(),message_mean=strata.mean(axis=0).tolist())
    return dict(arm_means=curves.mean(axis=0).tolist(),contrasts=result)


def load_source(root,tissue,cfg=CONFIG):
    original = root/"outputs"/ANCESTOR_ID/f"tissue_{tissue}"
    common = checker().common
    parent = common.arrays(original/"writing/parent.npz")
    boundary = common.arrays(original/"writing/boundary.npz")
    ranked = common.arrays(original/"intervention/bodies.npz")
    metadata = json.loads((original/"writing/experiment.json").read_text())
    assert metadata["tissue"] == tissue and metadata["passes"] is True and all(v is True for v in metadata["gates"].values())
    assert canonical_digest(metadata["config"]) == canonical_digest(asdict(cfg))
    assert source.base.state_digest(parent) == metadata["source_parent_sha256"]
    reconstructed = fixed.bodies.donor_ranked(boundary["kept_V"],boundary["fresh"],cfg.replicates)
    assert set(ranked) == set(reconstructed)
    for key in ranked:
        np.testing.assert_array_equal(ranked[key],reconstructed[key])
    return parent,boundary,ranked,metadata


def execute_cell(root,tissue,stage,output,cfg=CONFIG,rcfg=READOUT_CONFIG):
    assert stage in STAGES and cfg.replicates == rcfg.parents == 4
    assert cfg.sweeps == rcfg.sweeps
    check = checker()
    check.runtime(root)
    assert source.runtime()["passes"] is True
    ctx = source.context(tissue,cfg)
    original = root/"outputs"/ANCESTOR_ID/f"tissue_{tissue}"
    previous = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"
    writer = root/"outputs"/WRITING_ID/f"tissue_{tissue}"
    output = require_beneath(output,root)
    if stage == "calibration":
        output.mkdir()
        record,raws = readout.calibration(ctx,rcfg)
        for name,raw in raws.items():
            save_npz(output/f"calibration_{name}.npz",raw,root)
        strict_json(output/"calibration.json",record,root)
        checked = check.check_calibration(previous,output,tissue,asdict(rcfg))
    elif stage == "writing":
        assert (output/"calibration.json").is_file() and not (output/"writing.json").exists()
        parent,boundary,ranked,metadata = load_source(root,tissue,cfg)
        assert canonical_digest(asdict(ctx["tissue"])) == canonical_digest(metadata["tissue_config"])
        assert source.base.array_digest(ctx["native"]) == metadata["source_native_sha256"]
        np.testing.assert_array_equal(ctx["native"],boundary["native_theta"])
        record,raws = experiment_writing(ctx,parent,boundary,ranked)
        assert all(v == metadata["recovery_rng_final"] for v in record["recovery_rng_final"].values())
        for name,raw in raws.items():
            save_npz(output/f"{name}.npz",raw,root)
        strict_json(output/"writing.json",record,root)
        checked = check.check_writing(original,writer,output,tissue,asdict(cfg))
    else:
        assert (output/"writing.json").is_file() and not (output/"readout.json").exists()
        packets = {}
        for arm in PACKETS:
            file,key = ((output/f"recovery_{arm}.npz",f"s{cfg.sweeps}_theta") if arm in MAIN else
                        (original/"writing/parent.npz","theta") if arm == "parent" else
                        (original/"writing/boundary.npz","damaged_theta"))
            packets[arm] = check.common.arrays(file)[key].tobytes()
        record,raws = experiment(ctx,packets,rcfg)
        for name,raw in raws.items():
            save_npz(output/f"{name}.npz",raw,root)
        strict_json(output/"readout.json",record,root)
        checked = check.check_readout(original,previous,output,tissue,asdict(cfg),asdict(rcfg))
    return record,checked


def calibrated(rows):
    return bool([r["tissue"] for r in rows] == list(TISSUES)
                and all(r["passes"] is True and all(v is True for v in r["gates"].values()) and r["positive_accuracy"] > .25 for r in rows)
                and np.mean([r["positive_accuracy"] for r in rows]) >= .75)


def source_inputs(root):
    # D077 manifests already enumerate its full transitive dependency closure.
    # Rehash that closure once; do not repeatedly rehash each predecessor chain.
    paths = set()
    expected = {}
    for kind, count in (("input", 3031), ("output", 211)):
        path = root/"outputs"/SOURCE_ID/f"{kind}_hashes.sha256"
        rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
        assert len(rows) == len({p for _, p in rows}) == count
        paths.add(path)
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
        assert [r["tissue"] for r in rows] == list(TISSUES)
        assert all(r["passes"] is True for r in rows)
    assert all(sha256_file(Path(p)) == d for p, d in expected.items())
    return sorted(paths | {Path(p) for p in expected} | {run/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE")})


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l22_actual_donor_body.py", "scripts/audit_l22_actual_donor_body_outputs.py",
           "tests/test_l22_actual_donor_body.py", "scripts/run_l22_actual_donor_body.sh",
           "protocols/L22_ACTUAL_DONOR_BODY_V1.md", "reviews/L22_RESIDUAL_RECORD_READOUT_2026-09-08.md")
    return sorted(set(source_inputs(root)) | {ws/p for p in own})


def contract():
    return dict(run_id=RUN_ID,source_run=SOURCE_ID,writing_source=WRITING_ID,ancestor_run=ANCESTOR_ID,
        config=asdict(CONFIG),readout_config=asdict(READOUT_CONFIG),tissues=list(TISSUES),workers=WORKERS,
        bodies=list(BODIES),main_arms=list(MAIN),recovery_arms=list(RECOVERIES),writer_off=list(OFF),
        stages=list(STAGES),packets=list(PACKETS),arms=list(ARMS),contrasts=CONTRASTS,
        recovery_anchors=RECOVERY_ANCHORS,readout_anchors={k:list(v) for k,v in ANCHORS.items()},
        checkpoints=list(STEPS),fields=list(FIELDS),metrics=list(METRICS),direction_tolerance=1e-12,
        focal_endpoints=["actual_minus_kept_damaged:donor_accuracy:1000","actual_minus_kept_native:donor_accuracy:1000"],
        body_transplant="donor_values_at_retained_mask_only_same_replicate_next_message",
        shuffle="historical_per_replicate_permutation_no_new_selection",new_training_lives=0,
        saved_recovery_cells=224,historical_recovery_anchors=96,new_writable_cells=64,new_writer_off_cells=64,
        recovery_replay_cells=32,new_writing_lives=1024,total_recovery_lives=4096,
        scored_readout_lives=57344,replay_lives=8192,calibration_lives=12288,total_readout_lives=77824,
        total_executed_lives=81920,historical_readout_anchors=112,writer_off_packet_aliases=64,
        original_records_per_tissue=16,outcome_informed=True,birth_stream_reused_for_matching=True,
        law_verdict_changes=0,output_hashes=579,inference="retained_parent_body_package_intervention_not_fresh_confirmation")


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def preflight(root):
    cpus = checker().runtime(root)
    assert source.runtime()["passes"] is True
    if shutil.disk_usage(root).free < 3*1024**3:
        raise RuntimeError("at least 3 GiB external free space required")
    return cpus


def benchmark(root):
    if any(p.exists() for p in (root/"runs"/RUN_ID, root/"outputs"/RUN_ID, timing_path(root))):
        raise FileExistsError("immutable benchmark or run already exists")
    cpus = preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    temporary = Path(tempfile.mkdtemp(prefix="l22-actual-donor-benchmark-", dir=root/"tmp"))
    start = time.monotonic()
    for stage in STAGES:
        execute_cell(root, 30040, stage, temporary/"tissue_30040")
    elapsed = time.monotonic()-start
    estimate = elapsed*24+90
    assert all(sha256_file(Path(p)) == d for p, d in hashes.items())
    record = dict(run_id=RUN_ID, measured_utc=utc_now(), tissue_seconds=elapsed, projected_seconds=estimate,
                  must_detach=bool(estimate > 600), passes=True, effects_not_reported=True,
                  directory=str(temporary), cpu_affinity=cpus, input_sha256=hashes)
    strict_json(timing_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable body-source study already exists")
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["run_id"] == RUN_ID and timing["passes"] is True and timing["input_sha256"] == hashes
    assert timing["tissue_seconds"] > 0 and np.isfinite(timing["tissue_seconds"])
    assert timing["projected_seconds"] == timing["tissue_seconds"]*24+90
    assert timing["must_detach"] is (timing["projected_seconds"] > 600)
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), benchmark=timing, cpu_affinity=cpus,
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
    assert set(hashes) == {str(p) for p in input_paths(root) + [timing_path(root)]}
    assert hashes and canonical_digest(hashes) == manifest["hash_contract"]
    assert all(sha256_file(Path(p)) == d for p, d in hashes.items())
    timing = json.loads(timing_path(root).read_text())
    assert manifest["benchmark"] == timing
    assert timing["must_detach"] is (timing["projected_seconds"] > 600)
    return manifest


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest, run = verify(root), root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    paths = [root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    paths[0].parent.mkdir(exist_ok=True)
    with paths[0].open("xb") as out, paths[1].open("xb") as err:
        process = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l22_actual_donor_body",
            "--external-root", str(root), "--run"], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=process.pid, launched_utc=utc_now(), polling_owner="user",
                  estimated_seconds=manifest["benchmark"]["projected_seconds"], stdout_log=str(paths[0]),
                  stderr_log=str(paths[1]), status=str(run/"STATUS.json"))
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
                print(f"D078 {stage} and independent check: tissue {tissue} complete", flush=True)
            assert sorted(values[stage]) == sorted(checks[stage]) == list(TISSUES)
            if stage == "calibration" and not calibrated([values[stage][t] for t in TISSUES]):
                raise RuntimeError("readout calibration unqualified; no scientific writing or readouts allowed")
        rows = [values["readout"][t] for t in TISSUES]
        summary = pooled(rows)
        writing_rows = [values["writing"][t] for t in TISSUES]
        writing_summary = writing_pooled(writing_rows)
        assert checker().check_pool(rows, summary)
        assert checker().check_writing_pool(writing_rows, writing_summary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        result = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, calibration_qualified=True,
                    calibrations=[values["calibration"][t] for t in TISSUES], writing_results=writing_rows, writing_pooled=writing_summary, results=rows, pooled=summary)
        strict_json(output/"analysis.json", result, root)
        strict_json(output/"verification.json", dict(passes=True, checked_utc=utc_now(), law_verdict_changes=0,
                    checks={stage: [checks[stage][t] for t in TISSUES] for stage in STAGES}, pooled_verified=True), root)
        published = json.loads((output/"analysis.json").read_text())
        assert checker().check_pool(published["results"], published["pooled"])
        assert checker().check_writing_pool(published["writing_results"], published["writing_pooled"])
        checker().common.close(published["pooled"], summary)
        checker().common.close(published["writing_pooled"], writing_summary)
        paths = [output/"input_hashes.sha256", output/"analysis.json", output/"verification.json"]
        paths.extend(p for t in TISSUES for p in (output/f"tissue_{t}").iterdir())
        assert len(paths) == 579
        write_hash_manifest(paths, output/"output_hashes.sha256", root)
        assert checker().common.manifest_check(output/"output_hashes.sha256") == 579
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
                      completed_cleanly=True, verified_saved_analysis=True, checked_tissues=16,
                      scored_readout_lives=57344, new_training_lives=0, new_writing_lives=1024,
                      parent_readable=summary["parent_readable"])
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
