"""D077: functional reading of frozen D076 residual donor-record differences."""

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

from . import l22_fixed_reader_intervention as prior
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

readout, source = prior.bodies.readout, prior.source
strict_json, save_npz = prior.strict_json, prior.save_npz
RUN_ID = "l22_residual_record_readout_v1_attempt1"
SOURCE_ID, ANCESTOR_ID = prior.RUN_ID, prior.SOURCE_ID
TISSUES, WORKERS, CONFIG = tuple(range(30040, 30056)), 4, readout.CONFIG
MAIN = ("donor_native", "scrambled_native", "donor_damaged", "scrambled_damaged")
PACKETS = (*MAIN, "parent", "damaged")
ARMS = (*PACKETS, "wrong", "reader_off")
STAGES = ("calibration", "readout")
ANCHORS = {"donor_damaged": "donor_fixed", "scrambled_damaged": "scrambled_fixed", "parent": "parent", "damaged": "damaged"}
CONTRASTS = {
    "donor_minus_scrambled_native": {"donor_native": 1, "scrambled_native": -1},
    "donor_minus_scrambled_damaged": {"donor_damaged": 1, "scrambled_damaged": -1},
    "donor_specific_reader_interaction": {"donor_native": 1, "scrambled_native": -1, "donor_damaged": -1, "scrambled_damaged": 1},
    "donor_native_minus_damaged": {"donor_native": 1, "donor_damaged": -1},
    "scrambled_native_minus_damaged": {"scrambled_native": 1, "scrambled_damaged": -1},
}


def checker():
    path = Path(__file__).resolve().parents[2]/"scripts/audit_l22_residual_record_readout_outputs.py"
    spec = importlib.util.spec_from_file_location("d077_independent_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_packets(root, tissue):
    directory = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"
    saved = json.loads((directory/"analysis.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert canonical_digest(saved["config"]) == canonical_digest(asdict(prior.CONFIG))
    old = root/"outputs"/ANCESTOR_ID/f"tissue_{tissue}"/"writing"
    metadata = json.loads((old/"experiment.json").read_text())
    assert metadata["tissue"] == tissue and metadata["passes"] is True
    fields = {}
    for arm in MAIN:
        with np.load(directory/f"recovery_{arm}.npz", allow_pickle=False) as raw:
            fields[arm] = raw["s1000_theta"].copy()
    for arm, file, key in (("parent", "parent", "theta"), ("damaged", "boundary", "damaged_theta")):
        with np.load(old/f"{file}.npz", allow_pickle=False) as raw:
            fields[arm] = raw[key].copy()
    assert all(v.dtype == np.float64 and v.shape == (16, 16, 16) and np.isfinite(v).all() for v in fields.values())
    return {a: v.tobytes() for a, v in fields.items()}


def donor_values(raw, cfg):
    labels = (np.repeat(np.arange(4), cfg.parents*cfg.draws)+1) % 4
    return raw["probabilities"][np.arange(len(labels)), labels].reshape(4*cfg.parents, cfg.draws)


def extra_metrics(raw, cfg):
    own, donor = raw["correctness"], donor_values(raw, cfg)
    means = donor.mean(axis=1)
    return dict(donor_accuracy=float(donor.mean()), own_minus_donor=float((own-donor).mean()),
                donor_record_accuracy=means.tolist(), donor_record_within_variance=donor.var(axis=1).tolist(),
                donor_within_variance=float(donor.var(axis=1).mean()), donor_between_variance=float(means.var()),
                donor_total_variance=float(donor.var()), donor_always_correct=int(np.all(donor == 1., axis=1).sum()),
                donor_always_incorrect=int(np.all(donor == 0., axis=1).sum()),
                donor_varying=int(np.any(donor != donor[:, :1], axis=1).sum()),
                own_message_accuracy=own.reshape(4, -1).mean(axis=1).tolist(),
                donor_message_accuracy=donor.reshape(4, -1).mean(axis=1).tolist())


def experiment(ctx, packets, cfg=CONFIG):
    assert set(packets) == set(PACKETS) and cfg.parents == 4
    original = dict(packets)
    incoming = packets | {"wrong": source.donor(np.frombuffer(packets["donor_native"], dtype=np.float64).reshape(16,16,16), 4).tobytes(),
                          "reader_off": packets["donor_native"]}
    results = {a: readout.assay(ctx, incoming[a], cfg, off=a == "reader_off") for a in ARMS}
    for arm in ("donor_native", "scrambled_native"):
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
    record = dict(tissue=ctx["index"], passes=True, config=asdict(cfg), packet_origin="frozen_D076_final_theta_and_D074_anchors",
                  arms={a: r["metrics"] | extra_metrics(r["raw"], cfg) for a, r in results.items()}, paired=paired,
                  packet_hashes={a: r["packet_sha256"] for a, r in results.items()}, expanded_hashes={a: r["expanded_sha256"] for a, r in results.items()},
                  rng_final=results["donor_native"]["rng_final"], birth_rng_final=results["donor_native"]["birth_rng_final"],
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


def execute_cell(root, tissue, stage, output, cfg=CONFIG):
    assert stage in STAGES
    check = checker()
    check.runtime(root)
    assert source.runtime()["passes"] is True
    ctx = readout.context(tissue, cfg)
    old = root/"outputs"/ANCESTOR_ID/f"tissue_{tissue}"
    metadata = json.loads((old/"writing/experiment.json").read_text())
    assert metadata["tissue"] == tissue
    assert source.base.array_digest(ctx["native"]) == metadata["source_native_sha256"]
    output = require_beneath(output, root)
    if stage == "calibration":
        output.mkdir()
        record, artifacts = readout.calibration(ctx, cfg)
        for name, raw in artifacts.items():
            save_npz(output/f"calibration_{name}.npz", raw, root)
        strict_json(output/"calibration.json", record, root)
        checked = check.check_calibration(old/"readout", output, tissue, asdict(cfg))
    else:
        assert (output/"calibration.json").is_file() and not (output/"experiment.json").exists()
        packets = load_packets(root, tissue)
        record, artifacts = experiment(ctx, packets, cfg)
        for name, raw in artifacts.items():
            save_npz(output/f"{name}.npz", raw, root)
        strict_json(output/"experiment.json", record, root)
        checked = check.check_cell(root/"outputs"/SOURCE_ID/f"tissue_{tissue}", old, output, tissue, asdict(cfg))
    return record, checked


def calibrated(rows):
    return bool([r["tissue"] for r in rows] == list(TISSUES)
                and all(r["passes"] is True and all(v is True for v in r["gates"].values()) and r["positive_accuracy"] > .25 for r in rows)
                and np.mean([r["positive_accuracy"] for r in rows]) >= .75)


def source_inputs(root):
    paths = set(prior.source_inputs(root))
    expected = {}
    for kind, count in (("input", 2857), ("output", 163)):
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
    assert [r["tissue"] for r in verification["checks"]] == list(TISSUES)
    assert all(r["passes"] is True for r in verification["checks"])
    assert all(sha256_file(Path(p)) == d for p, d in expected.items())
    return sorted(paths | {Path(p) for p in expected} | {run/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE")})


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l22_residual_record_readout.py", "scripts/audit_l22_residual_record_readout_outputs.py",
           "tests/test_l22_residual_record_readout.py", "scripts/run_l22_residual_record_readout.sh",
           "protocols/L22_RESIDUAL_RECORD_READOUT_V1.md", "reviews/L22_FIXED_READER_INTERVENTION_2026-09-08.md")
    return sorted(set(source_inputs(root)) | {ws/p for p in own})


def contract():
    return dict(run_id=RUN_ID, source_run=SOURCE_ID, ancestor_run=ANCESTOR_ID, config=asdict(CONFIG),
                tissues=list(TISSUES), workers=4, stages=list(STAGES), packets=list(PACKETS), arms=list(ARMS),
                anchors=ANCHORS, contrasts=CONTRASTS, direction_tolerance=1e-12,
                focal_endpoint="donor_specific_reader_interaction:donor_accuracy:1000",
                new_training_lives=0, new_writing_lives=0, scored_readout_lives=32768, replay_lives=8192,
                calibration_lives=12288, total_readout_lives=53248, original_records_per_tissue=16,
                outcome_informed=True, birth_stream_reused_for_matching=True, law_verdict_changes=0,
                output_hashes=211, inference="conditional_retained_record_readout_not_fresh_parent_confirmation")


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def preflight(root):
    cpus = checker().runtime(root)
    assert source.runtime()["passes"] is True
    if shutil.disk_usage(root).free < 2*1024**3:
        raise RuntimeError("at least 2 GiB external free space required")
    return cpus


def benchmark(root):
    if any(p.exists() for p in (root/"runs"/RUN_ID, root/"outputs"/RUN_ID, timing_path(root))):
        raise FileExistsError("immutable benchmark or run already exists")
    cpus = preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    temporary = Path(tempfile.mkdtemp(prefix="l22-residual-readout-benchmark-", dir=root/"tmp"))
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
        raise FileExistsError("immutable readout already exists")
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
        process = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l22_residual_record_readout",
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


def run_readout(root):
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
                print(f"D077 {stage} and independent check: tissue {tissue} complete", flush=True)
            assert sorted(values[stage]) == sorted(checks[stage]) == list(TISSUES)
            if stage == "calibration" and not calibrated([values[stage][t] for t in TISSUES]):
                raise RuntimeError("readout calibration unqualified; no scientific readouts allowed")
        rows = [values["readout"][t] for t in TISSUES]
        summary = pooled(rows)
        assert checker().check_pool(rows, summary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        result = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, calibration_qualified=True,
                    calibrations=[values["calibration"][t] for t in TISSUES], results=rows, pooled=summary)
        strict_json(output/"analysis.json", result, root)
        strict_json(output/"verification.json", dict(passes=True, checked_utc=utc_now(), law_verdict_changes=0,
                    checks={stage: [checks[stage][t] for t in TISSUES] for stage in STAGES}, pooled_verified=True), root)
        assert checker().check_pool(json.loads((output/"analysis.json").read_text())["results"], summary)
        paths = [output/"input_hashes.sha256", output/"analysis.json", output/"verification.json"]
        paths.extend(p for t in TISSUES for p in (output/f"tissue_{t}").iterdir())
        assert len(paths) == 211
        write_hash_manifest(paths, output/"output_hashes.sha256", root)
        assert checker().common.manifest_check(output/"output_hashes.sha256") == 211
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
                      completed_cleanly=True, verified_saved_analysis=True, checked_tissues=16,
                      scored_readout_lives=32768, new_training_lives=0, new_writing_lives=0,
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
        return run_readout(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
