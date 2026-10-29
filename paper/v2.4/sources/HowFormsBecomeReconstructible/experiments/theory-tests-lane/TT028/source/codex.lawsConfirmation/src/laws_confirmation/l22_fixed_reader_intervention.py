"""D076: matched retained-body intervention on the fixed applied reader."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
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

from . import l22_body_source as bodies
from . import l22_early_signal_loss as prior
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

source, writing = bodies.source, bodies.writing
RUN_ID = "l22_fixed_reader_intervention_v1_attempt1"
SOURCE_ID, DIAGNOSTIC_ID = bodies.RUN_ID, prior.RUN_ID
TISSUES, WORKERS, CONFIG = tuple(range(30040, 30056)), 4, bodies.CONFIG
STEPS, FIELDS, METRICS = prior.STEPS, prior.FIELDS, prior.METRICS
MAIN = tuple(f"{body}_{reader}" for body in ("kept", "scrambled", "donor") for reader in ("damaged", "native"))
ARMS = (*MAIN, "scrambled_native_off", "donor_native_off")
ANCHORS = {"kept_damaged": ("writing", "fixed_damaged_reader"),
           "scrambled_damaged": ("writing", "scrambled_fixed_reader"),
           "donor_damaged": ("intervention", "donor_fixed"),
           "kept_native": ("writing", "theta_read_off")}
CONTRASTS = {
    **{f"{b}_native_minus_damaged": {f"{b}_native": 1, f"{b}_damaged": -1} for b in ("kept", "scrambled", "donor")},
    **{f"donor_minus_scrambled_{r}": {f"donor_{r}": 1, f"scrambled_{r}": -1} for r in ("damaged", "native")},
    "donor_specific_reader_interaction": {"donor_native": 1, "scrambled_native": -1, "donor_damaged": -1, "scrambled_damaged": 1},
    **{f"kept_minus_scrambled_{r}": {f"kept_{r}": 1, f"scrambled_{r}": -1} for r in ("damaged", "native")},
}
strict_json = prior.strict_json


def checker():
    path = Path(__file__).resolve().parents[2]/"scripts/audit_l22_fixed_reader_intervention_outputs.py"
    spec = importlib.util.spec_from_file_location("d076_independent_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(name):
    if name not in ARMS:
        raise ValueError("undeclared intervention")
    return writing.Mode(reader=name.split("_")[1], write=not name.endswith("_off"))


def load_source(directory, tissue):
    common = checker().common
    parent = common.arrays(directory/"writing/parent.npz")
    boundary = common.arrays(directory/"writing/boundary.npz")
    ranked = common.arrays(directory/"intervention/bodies.npz")
    metadata = json.loads((directory/"writing/experiment.json").read_text())
    extra = json.loads((directory/"intervention/experiment.json").read_text())
    assert metadata["tissue"] == extra["tissue"] == tissue
    assert metadata["passes"] is True and extra["passes"] is True
    assert all(v is True for r in (metadata, extra) for v in r["gates"].values())
    assert all(canonical_digest(r["config"]) == canonical_digest(asdict(CONFIG)) for r in (metadata, extra))
    reconstructed = bodies.donor_ranked(boundary["kept_V"], boundary["fresh"], CONFIG.replicates)
    assert set(reconstructed) == set(ranked)
    for key in ranked:
        np.testing.assert_array_equal(ranked[key], reconstructed[key])
    assert source.base.state_digest(parent) == metadata["source_parent_sha256"]
    return parent, boundary, ranked, metadata


def initial_states(boundary, ranked):
    result = {}
    for name in ARMS:
        body = name.split("_")[0]
        v = ranked["donor_V"] if body == "donor" else boundary[f"{body}_V"]
        result[name] = dict(V=v.copy(), ema=v.copy(), R=np.zeros_like(v), theta=boundary["damaged_theta"].copy())
    return result


def observers(raws):
    full = np.stack([np.stack([prior.observers(raws[a][k]) for k in
                              ("body_trace", "reference_trace", "theta_trace")], axis=2) for a in MAIN])
    return {"curves": full.mean(axis=2),
            "strata": full[:, list(STEPS)].reshape(6, 6, 4, 4, 3, 5).mean(axis=3)}


def describe(data):
    return {a: {str(s): {f: dict(mean=dict(zip(METRICS, data["curves"][i, s, j].tolist())),
                                messages=[dict(zip(METRICS, row)) for row in data["strata"][i, q, :, j].tolist()])
                         for j, f in enumerate(FIELDS)} for q, s in enumerate(STEPS)} for i, a in enumerate(MAIN)}


def pooled(values):
    if len(values) != 16:
        raise ValueError("all sixteen paired tissues required")
    contrasts = {}
    for name, terms in CONTRASTS.items():
        delta = np.stack([sum(weight*d["curves"][MAIN.index(arm), list(STEPS)] for arm, weight in terms.items()) for d in values])
        groups = np.stack([sum(weight*d["strata"][MAIN.index(arm)] for arm, weight in terms.items()) for d in values])
        contrasts[name] = dict(tissue_differences=delta.tolist(), mean=delta.mean(axis=0).tolist(),
            minimum=delta.min(axis=0).tolist(), maximum=delta.max(axis=0).tolist(),
            positive=(delta > 1e-12).sum(axis=0).tolist(), negative=(delta < -1e-12).sum(axis=0).tolist(),
            tied=(abs(delta) <= 1e-12).sum(axis=0).tolist(), message_mean=groups.mean(axis=0).tolist())
    return dict(arms=describe({k: np.mean([d[k] for d in values], axis=0) for k in values[0]}), contrasts=contrasts)


def save_npz(path, arrays, root):
    target = require_beneath(path, root)
    with target.open("xb") as handle:
        np.savez_compressed(handle, **arrays)


def execute_cell(root, tissue, output):
    check = checker()
    check.runtime(root)
    assert source.runtime()["passes"] is True
    directory = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"
    parent, boundary, ranked, metadata = load_source(directory, tissue)
    ctx = source.context(tissue, CONFIG)
    assert canonical_digest(asdict(ctx["tissue"])) == canonical_digest(metadata["tissue_config"])
    assert source.base.array_digest(ctx["native"]) == metadata["source_native_sha256"]
    np.testing.assert_array_equal(ctx["native"], boundary["native_theta"])
    inputs = initial_states(boundary, ranked)
    outcomes = {a: writing.recover(ctx, inputs[a], mode(a), parent, boundary["fresh"]) for a in ARMS}
    assert all(r["rng_final"] == metadata["recovery_rng_final"] for r in outcomes.values())
    assert source.base.state_digest(parent) == metadata["source_parent_sha256"]
    assert source.base.array_digest(ctx["native"]) == metadata["source_native_sha256"]
    raws = {a: r["raw"] for a, r in outcomes.items()}
    data = observers(raws)
    record = dict(tissue=tissue, passes=True, config=asdict(CONFIG),
                  initial_hashes={a: r["initial_hash"] for a, r in outcomes.items()},
                  recovery_rng_final={a: r["rng_final"] for a, r in outcomes.items()},
                  recovery={a: r["metrics"] for a, r in outcomes.items()}, arms=describe(data))
    output = require_beneath(output, root)
    output.mkdir()
    for a in ARMS:
        save_npz(output/f"recovery_{a}.npz", raws[a], root)
    save_npz(output/"analysis.npz", data, root)
    strict_json(output/"analysis.json", record, root)
    # Independent verification reads the published files, not in-memory outcomes.
    checked = check.check_cell(directory, output, tissue)
    return data, record, checked


def source_inputs(root):
    paths = set(prior.source_inputs(root))
    expected = {}
    for kind, count in (("input", 2811), ("output", 35)):
        path = root/"outputs"/DIAGNOSTIC_ID/f"{kind}_hashes.sha256"
        rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
        assert len(rows) == len({p for _, p in rows}) == count
        paths.add(path)
        for digest, filename in rows:
            assert Path(filename).is_absolute()
            assert filename not in expected or expected[filename] == digest
            expected[filename] = digest
    run = root/"runs"/DIAGNOSTIC_ID
    status = json.loads((run/"STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["run_id"] == DIAGNOSTIC_ID
    assert status["completed_cleanly"] is True and status["verified_saved_analysis"] is True
    assert status["new_simulations"] == 0 and status["checked_tissues"] == 16
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    result = json.loads((root/"outputs"/DIAGNOSTIC_ID/"analysis.json").read_text())
    assert all(result[k] == v for k, v in prior.contract().items())
    verification = json.loads((root/"outputs"/DIAGNOSTIC_ID/"verification.json").read_text())
    assert verification["passes"] is True and verification["pooled_verified"] is True
    assert [r["tissue"] for r in verification["checks"]] == list(TISSUES)
    assert all(sha256_file(Path(p)) == d for p, d in expected.items())
    return sorted(paths | {Path(p) for p in expected} | {run/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE")})


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l22_fixed_reader_intervention.py", "scripts/audit_l22_fixed_reader_intervention_outputs.py",
           "tests/test_l22_fixed_reader_intervention.py", "scripts/run_l22_fixed_reader_intervention.sh",
           "protocols/L22_FIXED_READER_INTERVENTION_V1.md", "reviews/L22_EARLY_SIGNAL_LOSS_2026-09-08.md")
    return sorted(set(source_inputs(root)) | {ws/p for p in own})


def contract():
    return dict(run_id=RUN_ID, source_run=SOURCE_ID, source_diagnostic=DIAGNOSTIC_ID,
                config=asdict(CONFIG), tissues=list(TISSUES), workers=WORKERS, main_arms=list(MAIN), arms=list(ARMS),
                anchors={k: list(v) for k, v in ANCHORS.items()}, checkpoints=list(STEPS), fields=list(FIELDS),
                metrics=list(METRICS), contrasts=CONTRASTS, focal_endpoint=[50, "V", "donor_accuracy"],
                direction_tolerance=1e-12, new_parents=0, executed_recovery_cells=128,
                new_factorial_cells=32, anchor_replays=64, new_off_cells=32, executed_batch_updates=128000,
                functional_readouts=0, law_verdict_changes=0, outcome_informed=True,
                output_hashes=163, inference="descriptive_matched_intervention_not_fresh_replication")


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def preflight(root):
    cpus = checker().runtime(root)
    assert source.runtime()["passes"] is True
    if shutil.disk_usage(root).free < 1024**3:
        raise RuntimeError("at least 1 GiB external free space required")
    return cpus


def benchmark(root):
    if any(p.exists() for p in (root/"runs"/RUN_ID, root/"outputs"/RUN_ID, timing_path(root))):
        raise FileExistsError("immutable benchmark or run already exists")
    cpus = preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    temporary = Path(tempfile.mkdtemp(prefix="l22-fixed-reader-benchmark-", dir=root/"tmp"))
    start = time.monotonic()
    execute_cell(root, 30040, temporary/"tissue_30040")
    elapsed = time.monotonic()-start
    estimate = elapsed*16*1.5+90
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
        raise FileExistsError("immutable intervention already exists")
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
        process = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l22_fixed_reader_intervention",
            "--external-root", str(root), "--run"], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=process.pid, launched_utc=utc_now(), polling_owner="user",
                  estimated_seconds=manifest["benchmark"]["projected_seconds"], stdout_log=str(paths[0]),
                  stderr_log=str(paths[1]), status=str(run/"STATUS.json"))
    strict_json(run/"LAUNCH.json", record, root)
    atomic_text(run/"RUN.pid", f"{process.pid}\n", root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # Deliberately no wait or poll.


def cells(root, output):
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        tasks = {pool.submit(execute_cell, root, t, output/f"tissue_{t}"): t for t in TISSUES}
        for future in as_completed(tasks):
            yield tasks[future], future.result()


def run_intervention(root):
    manifest = verify(root)
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached execution required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        values, checks = {}, {}
        for tissue, (data, record, checked) in cells(root, output):
            assert tissue not in values and record["tissue"] == checked["tissue"] == tissue
            assert record["passes"] is True and checked["passes"] is True
            values[tissue], checks[tissue] = data, checked
            strict_json(run/"STATUS.json", dict(status="RUNNING", run_id=RUN_ID, checked_tissues=len(checks), updated_utc=utc_now()), root)
            print(f"D076 saved recovery and independent check: tissue {tissue} complete", flush=True)
        assert sorted(values) == sorted(checks) == list(TISSUES)
        ordered = [values[t] for t in TISSUES]
        summary = pooled(ordered)
        assert checker().check_pool(ordered, summary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        result = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, pooled=summary)
        strict_json(output/"analysis.json", result, root)
        strict_json(output/"verification.json", dict(passes=True, checked_utc=utc_now(), law_verdict_changes=0,
                    checks=[checks[t] for t in TISSUES], pooled_verified=True), root)
        checker().common.close(json.loads((output/"analysis.json").read_text())["pooled"], summary)
        paths = [output/"input_hashes.sha256", output/"analysis.json", output/"verification.json"]
        paths.extend(p for t in TISSUES for p in (output/f"tissue_{t}").iterdir())
        assert len(paths) == 163
        write_hash_manifest(paths, output/"output_hashes.sha256", root)
        assert checker().common.manifest_check(output/"output_hashes.sha256") == 163
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
                      completed_cleanly=True, verified_saved_analysis=True, executed_recovery_cells=128, checked_tissues=16)
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
        return run_intervention(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
