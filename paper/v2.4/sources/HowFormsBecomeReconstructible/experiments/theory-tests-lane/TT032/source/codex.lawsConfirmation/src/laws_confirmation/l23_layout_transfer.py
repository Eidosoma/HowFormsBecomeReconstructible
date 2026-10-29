"""D082: transport identical pattern pieces across controlled spatial layouts."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

from . import l23_composition_budget as old
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

RUN_ID, TAG = "l23_layout_transfer_v1_attempt1", "l23-layout-transfer-v1"
TRACE_RUN = "l23_composition_trace_v1_attempt1"
TISSUES, DISPOSABLES, WORKERS = tuple(range(31016, 31032)), (402085, 402086), 4
LAYOUTS = ("left_right", "above_below", "checker4")
NORMS, PAIRS, BUDGETS, READERS = old.NORMS, old.PAIRS, old.BUDGETS, old.READERS
MEASURED, CASES, CAL_CASES, GROUPS = old.MEASURED, old.CASES, old.CAL_CASES, old.GROUPS
METRICS = (*old.METRICS, "own_centered_alignment")
CONFIG, TERMS = old.CONFIG, old.TERMS
FOCAL = (("by_layout", "checker4", "expression_gain_matched"),
         ("by_layout", "checker4", "organization_matched"),
         ("by_layout", "checker4", "composition_cost_matched"),
         ("minus_left_right", "checker4", "composition_cost_matched"))
FOCAL_METRICS = ("half_accuracy", "own_centered_alignment")
base, strict_json, legacy, qualification = old.base, old.strict_json, old.legacy, old.qualification


def checker():
    p = Path(__file__).resolve().parents[2]/"scripts/audit_l23_layout_transfer_outputs.py"
    spec = importlib.util.spec_from_file_location("d082_layout_checker", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded(tissue, phase, tag=TAG):
    seed = int.from_bytes(hashlib.sha256(f"{tag}:{tissue}:{phase}".encode()).digest()[:16], "little")
    return np.random.default_rng(seed)


def layout_maps():
    ids = np.arange(256, dtype=np.int64).reshape(16, 16)
    checkerboard = np.empty_like(ids)
    source_tiles = [(r, c) for side in range(2) for r in range(4) for c in range(2*side, 2*side+2)]
    destination_tiles = [(r, c) for side in range(2) for r in range(4) for c in range(4) if (r+c) % 2 == side]
    for (sr, sc), (dr, dc) in zip(source_tiles, destination_tiles):
        checkerboard[4*dr:4*dr+4, 4*dc:4*dc+4] = ids[4*sr:4*sr+4, 4*sc:4*sc+4]
    return np.stack((ids.ravel(), np.rot90(ids, -1).ravel(), checkerboard.ravel()))


def transport(value, mapping):
    # Advanced indexing otherwise changes the memory strides, and hence the
    # source engine's floating-point reduction order even for the identity map.
    return np.ascontiguousarray(np.asarray(value).reshape(*value.shape[:-2], 256)[..., mapping].reshape(value.shape))


def instruments(ctx):
    return old.instruments(ctx) | dict(layout_maps=layout_maps())


def layout_instrument(inst, geometry):
    mapping = inst["layout_maps"][geometry]
    return {key: transport(inst[key], mapping) for key in ("forms", "left", "targets", "packets")} | dict(
        target_means=inst["target_means"], permutations=inst["permutations"])


def centered_alignment(v, forms, mask):
    result = []
    for region in (mask, ~mask):
        z, f = v[..., region], forms[:, region]
        z = z-z.mean(axis=-1, keepdims=True)
        f = f-f.mean(axis=-1, keepdims=True)
        numerator = np.einsum("...i,fi->...f", z, f)
        denom = np.sqrt(np.square(z).sum(axis=-1)[..., None]*np.square(f).sum(axis=-1))
        result.append(np.divide(numerator, denom, out=np.zeros_like(numerator), where=denom > 0))
    return np.stack(result, axis=-2)


class MappedNoise:
    def __init__(self, generator, draws, mapping):
        self.generator, self.draws, self.mapping = generator, draws, mapping

    def standard_normal(self, shape):
        assert len(shape) == 4 and tuple(shape[1:]) == (self.draws, 16, 16)
        return np.broadcast_to(transport(self.generator.standard_normal((self.draws, 16, 16)), self.mapping), shape)


def simulate(ctx, inst, geometry, norm_index, cases, tag=TAG):
    cfg = ctx["config"]
    local = layout_instrument(inst, geometry)
    mapping = inst["layout_maps"][geometry]
    theta, means, ids = old.case_inputs(local, norm_index, cases)
    rng = seeded(ctx["index"], "expression", tag)
    noise = .2*rng.standard_normal((cfg.draws, 16, 16))
    noise -= noise.mean(axis=(-2, -1), keepdims=True)
    noise = transport(noise, mapping)
    v = noise[None]+means[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    draws = MappedNoise(rng, cfg.draws, mapping)
    raw = dict(theta=theta, case_ids=ids, offsets=means, birth_noise=noise)
    traces = {k: [] for k in ("mean", "rms", "boundary_fraction")}
    for t in range(cfg.sweeps+1):
        if t:
            v, ema, ref = ctx["api"]["blueprint_step"](v, ema, ref, theta[:, None],
                ctx["tissue"], ctx["ladder"], ctx["bp"], "T", draws, c_m=0.)
        if t in cfg.times:
            raw.update({f"s{t}_{k}": x.copy() for k, x in (("V", v), ("ema", ema), ("R", ref))})
        traces["mean"].append(v.mean(axis=(-2, -1)))
        traces["rms"].append(np.sqrt((v*v).mean(axis=(-2, -1))))
        traces["boundary_fraction"].append((abs(v) == 2.).mean(axis=(-2, -1)))
    raw.update({k: np.array(x) for k, x in traces.items()})
    raw["scores"] = old.half_scores(v, local["forms"], local["left"])
    raw["probabilities"] = old.probabilities(raw["scores"])
    raw["alignment"] = centered_alignment(v, local["forms"], local["left"])
    return raw, canonical_digest(rng.bit_generator.state)


def metrics(scores, probabilities, alignment, pair):
    x, y = (ord(c)-65 for c in pair)
    own = (alignment[..., 0, x]+alignment[..., 1, y])/2
    return np.concatenate((old.metrics(scores, probabilities, pair), own[..., None]), axis=-1)


def panel_metrics(raw):
    original = old.panel_metrics(raw)
    align = raw["alignment"].reshape(12, 3, 7, -1, 2, 4)
    rows = []
    for j, pair in enumerate(PAIRS):
        x, y = (ord(c)-65 for c in pair)
        values = []
        for b in range(3):
            real = (align[j, b, :, :, 0, x]+align[j, b, :, :, 1, y])/2
            isolated = (align[j, b, 2, :, 0, x]+align[j, b, 3, :, 1, y])/2
            values.append(np.concatenate((real, isolated[None]), axis=0))
        rows.append(values)
    return np.concatenate((original, np.array(rows)[..., None]), axis=-1)


def execute_cell(root, index, stage, directory, cfg=CONFIG):
    if index not in (*TISSUES, *DISPOSABLES):
        raise ValueError("undeclared tissue")
    require_beneath(directory, root).mkdir(parents=True, exist_ok=True)
    ctx = old.context(index, cfg)
    inst = instruments(ctx)
    check = checker()
    if stage == "calibration":
        base.atomic_npz(directory/"instruments.npz", inst, root)
        accuracy, endpoints = [], []
        for n in range(2):
            raw, digest = simulate(ctx, inst, 0, n, CAL_CASES)
            base.atomic_npz(directory/f"calibration_{n}.npz", raw, root)
            acc = [metrics(raw["scores"][j], raw["probabilities"][j], raw["alignment"][j], p)[:, 0].mean()
                   for j, (p, _, _) in enumerate(CAL_CASES)]
            accuracy.append(np.array(acc).reshape(2, 2).mean(axis=0).tolist())
            endpoints.append(digest)
        record = dict(tissue=index, config=asdict(cfg), accuracy=accuracy, rng_final=endpoints, passes=True)
        strict_json(directory/"calibration.json", record, root)
        verified = check.check_calibration(directory, index, asdict(cfg))
    elif stage == "panel":
        arrays, endpoints = [], []
        for g in range(3):
            values, digests = [], []
            for n in range(2):
                raw, digest = simulate(ctx, inst, g, n, CASES)
                base.atomic_npz(directory/f"panel_{g}_{n}.npz", raw, root)
                values.append(panel_metrics(raw))
                digests.append(digest)
            arrays.append(values)
            endpoints.append(digests)
        record = dict(tissue=index, config=asdict(cfg), metrics=np.array(arrays).tolist(),
                      rng_final=endpoints, passes=True)
        strict_json(directory/"panel.json", record, root)
        verified = check.check_panel(directory, index, asdict(cfg))
    else:
        raise ValueError("unknown stage")
    return record, verified


def distribution(values):
    values = np.asarray(values)
    return dict(mean=float(values.mean()), minimum=float(values.min()), maximum=float(values.max()),
                positive=int((values > 1e-12).sum()), tied=int((abs(values) <= 1e-12).sum()),
                negative=int((values < -1e-12).sum()), tissue_differences=values.tolist())


def pooled_one(rows):
    data = np.array([r["metrics"] for r in rows])  # tissue,norm,pair,budget,reader,draw,metric
    contrasts = {}
    for name, terms in TERMS.items():
        values = sum(w*data[:, :, :, BUDGETS.index(b), MEASURED.index(r)] for b, r, w in terms)
        by_norm = []
        for n in range(2):
            groups = {}
            for group, pairs in GROUPS.items():
                indices = [PAIRS.index(p) for p in pairs]
                selected = values[:, n, indices]
                groups[group] = {m: distribution(selected[..., k].mean(axis=(1, 2))) |
                    dict(pair_mean=values[:, n, :, :, k].mean(axis=(0, 2)).tolist(),
                         paired_positive=float((selected[..., k] > 1e-12).mean()),
                         paired_tied=float((abs(selected[..., k]) <= 1e-12).mean()),
                         paired_negative=float((selected[..., k] < -1e-12).mean())) for k, m in enumerate(METRICS)}
            by_norm.append(groups)
        contrasts[name] = by_norm
    return dict(arm_means=data.mean(axis=(0, 5)).tolist(), contrasts=contrasts)


def projected_rows(rows, geometry, subtract=None):
    result = []
    for row in rows:
        value = np.array(row["metrics"])[geometry]
        if subtract is not None:
            value = value-np.array(row["metrics"])[subtract]
        result.append(dict(tissue=row["tissue"], metrics=value.tolist()))
    return result


def pooled(rows):
    return dict(by_layout={g: pooled_one(projected_rows(rows, i)) for i, g in enumerate(LAYOUTS)},
                minus_left_right={g: pooled_one(projected_rows(rows, i, 0)) for i, g in enumerate(LAYOUTS) if i})


def contract():
    return dict(run_id=RUN_ID, law="L23", decision="D082", tissues=list(TISSUES), config=asdict(CONFIG),
        layouts=list(LAYOUTS), norms=list(NORMS), pairs=list(PAIRS), budgets=list(BUDGETS),
        readers=list(READERS), measured=list(MEASURED), groups=GROUPS, metrics=list(METRICS),
        contrasts=TERMS, focal=list(FOCAL), focal_group="all", focal_metrics=list(FOCAL_METRICS),
        focal_endpoints=16, workers=4, output_hashes=181, main_lives=193536, calibration_lives=1024,
        historical_lives=16, replay_lives=194576, total_executed_lives=389152,
        scientific_training_lives=0, learned_writing_lives=0, law_verdict_changes=0,
        known_forms=4, fresh_prototypes=False, engineered_readdressing=True,
        learned_layout_invariance=False, isometry_state_atol=1e-10, source_trace=TRACE_RUN)


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    paths = old.input_paths(root)
    paths += [ws/p for p in ("src/laws_confirmation/l23_layout_transfer.py",
        "scripts/audit_l23_layout_transfer_outputs.py", "tests/test_l23_layout_transfer.py",
        "scripts/run_l23_layout_transfer.sh", "protocols/L23_LAYOUT_TRANSFER_V1.md")]
    trace = root/"outputs"/TRACE_RUN
    for name in ("input_hashes.sha256", "output_hashes.sha256"):
        manifest = trace/name
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    return sorted(set(p.resolve() for p in paths))


def provenance(root):
    trace = root/"outputs"/TRACE_RUN
    check = old.checker()
    assert check.check_hashes(trace/"output_hashes.sha256") == 4
    assert check.check_hashes(trace/"input_hashes.sha256") == 259
    saved = json.loads((trace/"verification.json").read_text())
    assert saved["passes"] is True and saved["snapshot_batches"] == 160
    assert json.loads((trace/"analysis.json").read_text())["new_simulation_lives"] == 0


def preflight(root):
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus) > 4:
        raise RuntimeError("at most four logical CPUs required")
    if any(os.environ.get(k) != "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")):
        raise RuntimeError("numerical thread limits must all equal one")
    if shutil.disk_usage(root).free < 4*1024**3:
        raise RuntimeError("external free space is below four GiB")
    return cpus


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root):
    provenance(root)
    cpus = preflight(root)
    path = timing_path(root)
    if path.exists():
        raise FileExistsError("benchmark is immutable")
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    directory = Path(tempfile.mkdtemp(prefix="l23-layout-transfer-benchmark-", dir=root/"tmp"))
    start = time.monotonic()
    for stage in ("calibration", "panel"):
        _, checked = execute_cell(root, DISPOSABLES[1], stage, directory)
        assert checked["passes"] is True
    elapsed = time.monotonic()-start
    assert hashes == {str(p): sha256_file(p) for p in input_paths(root)}
    estimate = 24*elapsed+120
    record = dict(run_id=RUN_ID, completed_utc=utc_now(), passes=True, effects_not_reported=True,
        disposable_tissue=DISPOSABLES[1], directory=str(directory), tissue_seconds=elapsed,
        cell_bytes=sum(p.stat().st_size for p in directory.iterdir()),
        projected_seconds=estimate, must_detach=estimate > 600, input_sha256=hashes, cpu_affinity=cpus)
    strict_json(path, record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, out = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError("immutable run already exists")
    provenance(root)
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    assert type(timing["cell_bytes"]) is int and timing["cell_bytes"] > 0
    if shutil.disk_usage(root).free < 4*1024**3+24*timing["cell_bytes"]:
        raise RuntimeError("insufficient space for conservative output forecast plus four GiB reserve")
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["run_id"] == RUN_ID and timing["passes"] is True and timing["effects_not_reported"] is True
    assert timing["disposable_tissue"] == DISPOSABLES[1] and timing["input_sha256"] == hashes
    assert np.isfinite(timing["tissue_seconds"]) and timing["tissue_seconds"] > 0
    assert timing["projected_seconds"] == 24*timing["tissue_seconds"]+120
    assert timing["must_detach"] is (timing["projected_seconds"] > 600)
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), input_sha256=hashes, hash_contract=canonical_digest(hashes),
        benchmark=timing, cpu_affinity=cpus, environment=environment_manifest())
    run.mkdir(parents=True)
    out.mkdir(parents=True)
    strict_json(run/"MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], out/"input_hashes.sha256", root)
    strict_json(run/"STATUS.json", dict(status="PREPARED", run_id=RUN_ID), root)
    print(json.dumps(dict(status="PREPARED", input_hashes=len(hashes), estimated_seconds=timing["projected_seconds"])), flush=True)
    return manifest


def verify(root):
    run = root/"runs"/RUN_ID
    manifest = json.loads((run/"MANIFEST.json").read_text())
    assert json.loads((run/"STATUS.json").read_text())["status"] == "PREPARED"
    assert not (run/"COMPLETE").exists() and not (run/"FAILED").exists()
    for k, v in contract().items():
        assert canonical_digest(v) == canonical_digest(manifest[k]), k
    hashes = manifest["input_sha256"]
    assert set(hashes) == {str(p) for p in input_paths(root)+[timing_path(root)]}
    assert canonical_digest(hashes) == manifest["hash_contract"]
    assert all(sha256_file(Path(p)) == h for p, h in hashes.items())
    assert manifest["benchmark"] == json.loads(timing_path(root).read_text())
    assert manifest["benchmark"]["must_detach"] is (manifest["benchmark"]["projected_seconds"] > 600)
    return manifest


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest = verify(root)
    run = root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    logs = [root/"logs"/f"{RUN_ID}.{k}.log" for k in ("stdout", "stderr")]
    logs[0].parent.mkdir(exist_ok=True)
    with logs[0].open("xb") as out, logs[1].open("xb") as err:
        child = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l23_layout_transfer", "--external-root", str(root), "--run"],
            cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=child.pid, launched_utc=utc_now(), polling_owner="user",
        estimated_seconds=manifest["benchmark"]["projected_seconds"], status=str(run/"STATUS.json"),
        stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    strict_json(run/"LAUNCH.json", record, root)
    atomic_text(run/"RUN.pid", f"{child.pid}\n", root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # No wait or polling.


def cells(root, out, stage):
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(execute_cell, root, t, stage, out/f"tissue_{t}"): t for t in TISSUES}
        for future in as_completed(futures):
            yield futures[future], future.result()


def run_study(root):
    manifest = verify(root)
    run, out = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached execution required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        strict_json(run/"STATUS.json", dict(status="RUNNING", stage="historical", run_id=RUN_ID, updated_utc=utc_now()), root)
        historical, historical_check = legacy(root, out)
        values, checks = {}, {}
        for stage in ("calibration", "panel"):
            values[stage], checks[stage] = {}, {}
            strict_json(run/"STATUS.json", dict(status="RUNNING", stage=stage, checked_tissues=0, updated_utc=utc_now(), run_id=RUN_ID), root)
            for t, (record, check) in cells(root, out, stage):
                assert record["tissue"] == check["tissue"] == t and record["passes"] is True and check["passes"] is True
                values[stage][t], checks[stage][t] = record, check
                strict_json(run/"STATUS.json", dict(status="RUNNING", stage=stage, checked_tissues=len(checks[stage]), updated_utc=utc_now(), run_id=RUN_ID), root)
                print(f"D082 {stage} and saved-data replay verified: tissue {t}", flush=True)
            assert sorted(values[stage]) == list(TISSUES)
            if stage == "calibration" and not qualification([values[stage][t] for t in TISSUES]):
                raise RuntimeError("positive-control calibration failed; full pair panel not permitted")
        rows = [values["panel"][t] for t in TISSUES]
        summary = pooled(rows)
        assert checker().check_pool(rows, summary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        analysis = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, calibration_qualified=True,
            historical=historical, calibrations=[values["calibration"][t] for t in TISSUES], results=rows, pooled=summary)
        strict_json(out/"analysis.json", analysis, root)
        strict_json(out/"verification.json", dict(passes=True, historical=historical_check, pooled_verified=True,
            checks={s: [checks[s][t] for t in TISSUES] for s in checks}, checked_utc=utc_now()), root)
        published = json.loads((out/"analysis.json").read_text())
        assert checker().check_pool(published["results"], published["pooled"])
        paths = [out/p for p in ("historical.npz", "historical.json", "input_hashes.sha256", "analysis.json", "verification.json")]
        paths.extend(p for t in TISSUES for p in (out/f"tissue_{t}").iterdir())
        assert len(paths) == 181
        write_hash_manifest(paths, out/"output_hashes.sha256", root)
        assert checker().check_hashes(out/"output_hashes.sha256") == 181
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
            completed_cleanly=True, verified_saved_analysis=True, checked_tissues=16, scored_expression_lives=193536,
            new_training_lives=0, learned_writing_lives=0)
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--external-root", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    for op in ("benchmark", "prepare", "detach", "run"):
        g.add_argument(f"--{op}", action="store_true")
    args = p.parse_args()
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
