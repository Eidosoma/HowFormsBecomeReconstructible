"""Outcome-known D074 trace diagnostic; no dynamical simulation entry points."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np

from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

RUN_ID = "l22_early_signal_loss_v1_attempt1"
SOURCE_ID = "l22_body_source_v1_attempt1"
SOURCE_AUDIT = SOURCE_ID + "_independent_rescore_v1"
TISSUES = tuple(range(30040, 30056))
STEPS = (0, 1, 50, 250, 500, 1000)
ENDPOINTS = (50, 1000)
BANDS = ((1, 1), (2, 50), (51, 250), (251, 500), (501, 1000))
COMPONENTS = ("initial", "1", "2-50", "51-250", "251-500", "501-1000")
FIELDS = ("V", "R", "theta")
METRICS = ("own_projection", "donor_projection", "own_minus_donor", "own_accuracy", "donor_accuracy")
# name: source folder, source arm, theta writing, reference held
ARMS = {
    "kept_live": ("writing", "loop", True, False),
    "kept_fixed": ("writing", "fixed_damaged_reader", True, False),
    "kept_off": ("writing", "writer_off", False, False),
    "scrambled_live": ("writing", "scrambled_loop", True, False),
    "scrambled_fixed": ("writing", "scrambled_fixed_reader", True, False),
    "scrambled_off": ("intervention", "scrambled_off", False, False),
    "donor_live": ("intervention", "donor_loop", True, False),
    "donor_fixed": ("intervention", "donor_fixed", True, False),
    "donor_off": ("intervention", "donor_off", False, False),
    "native_reader": ("writing", "theta_read_off", True, False),
    "native_off": ("writing", "body_writer_off", False, False),
    "reference_off": ("writing", "reference_write_off", True, True),
    "wrong_fixed": ("writing", "wrong_fixed_reader", True, False),
    "backup": ("writing", "backup", True, False),
}
CONTRASTS = {
    "organization": ("kept_live", "scrambled_live"),
    "donor_vs_scrambled": ("donor_live", "scrambled_live"),
    **{f"{b}_live_vs_fixed": (f"{b}_live", f"{b}_fixed") for b in ("kept", "scrambled", "donor")},
    "kept_native_vs_fixed": ("native_reader", "kept_fixed"),
}


def strict_json(path, value, root):
    atomic_text(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", root)


def checker():
    path = Path(__file__).resolve().parents[2] / "scripts/audit_l22_early_signal_loss_outputs.py"
    spec = importlib.util.spec_from_file_location("d075_independent_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_raw(directory):
    result = {}
    for name, (folder, old, _, _) in ARMS.items():
        with np.load(directory / folder / f"recovery_{old}.npz", allow_pickle=False) as saved:
            result[name] = {k: saved[k] for k in saved.files}
    return result


def observers(trace):
    if trace.ndim != 3 or trace.shape[1] != 16 or trace.shape[2] < 4 or not np.isfinite(trace).all():
        raise ValueError("expected finite time/world/four-template scores")
    sc = trace[:, :, :4]
    world, own = np.arange(16), np.arange(16) // 4
    donor = (own + 1) % 4
    ties = np.isclose(sc, sc.max(axis=2, keepdims=True), rtol=0., atol=1e-12)
    probabilities = ties / ties.sum(axis=2, keepdims=True)
    a, b = sc[:, world, own], sc[:, world, donor]
    return np.stack((a, b, a-b, probabilities[:, world, own], probabilities[:, world, donor]), axis=-1)


def components(initial, forcing, a, b, endpoints=ENDPOINTS, bands=BANDS):
    n, worlds, axes = forcing.shape
    if [s for lo, hi in bands for s in range(lo, hi+1)] != list(range(1, n+1)):
        raise ValueError("windows must partition all updates")
    if (initial.shape != (worlds, axes) or a.shape != (n, worlds) or b.shape != a.shape
            or not all(np.isfinite(x).all() for x in (initial, forcing, a, b))
            or any(t < 1 or t > n for t in endpoints) or len(set(endpoints)) != len(endpoints)):
        raise ValueError("invalid component inputs")
    parts = np.zeros((len(bands)+1, worlds, axes))
    parts[0] = initial
    saved = {}
    for s in range(1, n+1):
        parts *= a[s-1][None, :, None]
        band = next(i+1 for i, (lo, hi) in enumerate(bands) if lo <= s <= hi)
        parts[band] += b[s-1, :, None] * forcing[s-1]
        if s in endpoints:
            saved[s] = parts.copy()
    return np.stack([saved[t] for t in endpoints])


def analyze_arm(raw, write, hold):
    traces = [raw[k] for k in ("body_trace", "reference_trace", "theta_trace")]
    body, reference, theta = traces
    target, scale = raw["target_trace"], raw["projection_scale"]
    for value, shape in zip((*traces, target, scale), ((1001, 16, 4), (1001, 16, 4), (1001, 16, 6), (1000, 16, 6), (1000, 16))):
        if value.shape != shape or value.dtype != np.float64 or not np.isfinite(value).all():
            raise ValueError("invalid trace shape, dtype or value")
    if np.any(scale <= 0):
        raise ValueError("normalization must be positive")
    ra = np.full((1000, 16), 1. if hold else .998)
    rb = np.full_like(ra, 0. if hold else .002)
    ta = .999 * scale if write else np.ones_like(scale)
    tb = .001 * scale if write else np.zeros_like(scale)
    np.testing.assert_allclose(reference[1:], ra[..., None]*reference[:-1]+rb[..., None]*body[1:], rtol=0., atol=1e-11)
    np.testing.assert_allclose(theta[1:], ta[..., None]*theta[:-1]+tb[..., None]*target, rtol=0., atol=1e-11)
    if not write:
        np.testing.assert_array_equal(scale, np.ones_like(scale))
        np.testing.assert_array_equal(theta, np.broadcast_to(theta[0], theta.shape))
    rp = components(reference[0], body[1:], ra, rb)
    tp = components(theta[0], target, ta, tb)
    for parts, trace in ((rp, reference), (tp, theta)):
        np.testing.assert_allclose(parts.sum(axis=1), trace[list(ENDPOINTS)], rtol=0., atol=1e-11)
    full = np.stack([observers(v) for v in traces], axis=2)
    return full.mean(axis=1), full[list(STEPS)].reshape(6, 4, 4, 3, 5).mean(axis=2), rp, tp


def describe(arrays):
    world, own = np.arange(16), np.arange(16)//4
    donor = (own+1) % 4
    result = {}
    for i, name in enumerate(ARMS):
        checkpoints = {}
        for j, step in enumerate(STEPS):
            checkpoints[str(step)] = {
                field: {"mean": dict(zip(METRICS, arrays["curves"][i, step, f].tolist())),
                        "messages": [dict(zip(METRICS, v)) for v in arrays["strata"][i, j, :, f].tolist()]}
                for f, field in enumerate(FIELDS)}
        accounting = {}
        for j, step in enumerate(ENDPOINTS):
            accounting[str(step)] = {}
            for field in ("R", "theta"):
                parts = arrays[f"{field}_components"][i, j]
                a, b = parts[:, world, own].mean(axis=1), parts[:, world, donor].mean(axis=1)
                accounting[str(step)][field] = {
                    name: dict(own_projection=float(a[k]), donor_projection=float(b[k]), own_minus_donor=float(a[k]-b[k]))
                    for k, name in enumerate(COMPONENTS)}
        result[name] = {"checkpoints": checkpoints, "accounting": accounting}
    return result


def analyze_cell(directory, tissue):
    for folder in ("writing", "intervention"):
        assert json.loads((directory/folder/"experiment.json").read_text())["tissue"] == tissue
    raw = load_raw(directory)
    values = [analyze_arm(raw[a], write, hold) for a, (_, _, write, hold) in ARMS.items()]
    arrays = {key: np.stack([v[i] for v in values]) for i, key in enumerate(("curves", "strata", "R_components", "theta_components"))}
    record = {"tissue": tissue, "passes": True, "arms": describe(arrays)}
    checked = checker().check_cell(raw, arrays, record)
    return arrays, record, checked


def pooled(arrays):
    if len(arrays) != 16:
        raise ValueError("all sixteen tissues required")
    means = {k: np.mean([a[k] for a in arrays], axis=0) for k in arrays[0]}
    contrasts = {}
    names = list(ARMS)
    for label, (left, right) in CONTRASTS.items():
        delta = np.stack([a["curves"][names.index(left), list(STEPS)]-a["curves"][names.index(right), list(STEPS)] for a in arrays])
        contrasts[label] = {"mean": delta.mean(axis=0).tolist(), "minimum": delta.min(axis=0).tolist(),
                            "maximum": delta.max(axis=0).tolist(), "positive": (delta > 1e-12).sum(axis=0).tolist(),
                            "negative": (delta < -1e-12).sum(axis=0).tolist(), "tied": (abs(delta) <= 1e-12).sum(axis=0).tolist()}
    return {"arms": describe(means), "contrasts": contrasts}


def source_inputs(root):
    expected, paths = {}, []
    for name, counts in ((SOURCE_ID, (1655, 1138)), (SOURCE_AUDIT, (2798, 2))):
        for kind, count in zip(("input", "output"), counts):
            path = root/"outputs"/name/f"{kind}_hashes.sha256"
            rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
            assert len(rows) == len({p for _, p in rows}) == count
            paths.append(path)
            for digest, filename in rows:
                assert Path(filename).is_absolute()
                assert filename not in expected or expected[filename] == digest
                expected[filename] = digest
        run = root/"runs"/name
        status = json.loads((run/"STATUS.json").read_text())
        assert status["status"] == "COMPLETE" and status["run_id"] == name
        assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
        assert status["classification"] == "BODY_ORGANIZATION_BENEFIT_ONLY"
        if name == SOURCE_ID:
            assert status["completed_cleanly"] is True
        else:
            assert status["verified_scientific_data"] is True and status["new_simulations"] == 0
        paths.extend(run/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    audit = json.loads((root/"outputs"/SOURCE_AUDIT/"rescore.json").read_text())
    assert audit["passes"] is True and audit["new_simulations"] == 0
    assert audit["run_id"] == SOURCE_AUDIT and audit["source_run"] == SOURCE_ID
    assert audit["source_manifest_counts"] == [1655, 1138] and audit["rank_transfers_checked"] == 256
    assert [r["tissue"] for r in audit["checked"]] == list(TISSUES)
    assert all(Path(p).is_file() and sha256_file(Path(p)) == d for p, d in expected.items())
    return sorted(set(paths) | {Path(p) for p in expected})


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l22_early_signal_loss.py", "scripts/audit_l22_early_signal_loss_outputs.py",
           "tests/test_l22_early_signal_loss.py", "scripts/run_l22_early_signal_loss.sh",
           "protocols/L22_EARLY_SIGNAL_LOSS_V1.md", "reviews/L22_BODY_SOURCE_2026-09-08.md")
    return sorted(set(source_inputs(root)) | {ws/p for p in own})


def contract():
    return dict(run_id=RUN_ID, source_run=SOURCE_ID, source_audit=SOURCE_AUDIT, tissues=list(TISSUES),
                arms={k: list(v) for k, v in ARMS.items()}, checkpoints=list(STEPS), endpoints=list(ENDPOINTS),
                bands=[list(v) for v in BANDS], components=list(COMPONENTS), fields=list(FIELDS), metrics=list(METRICS),
                contrasts={k: list(v) for k, v in CONTRASTS.items()}, direction_tolerance=1e-12,
                workers=1, new_simulations=0, law_verdict_changes=0, outcome_known=True,
                output_hashes=35, theta_accounting="recorded_normalization_not_counterfactual")


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root/"runs"/RUN_ID).exists() or (root/"outputs"/RUN_ID).exists():
        raise FileExistsError("immutable diagnostic already exists")
    cpus = checker().runtime(root)
    inputs = input_paths(root)
    start = time.monotonic()
    analyze_cell(root/"outputs"/SOURCE_ID/"tissue_30040", 30040)
    elapsed = time.monotonic()-start
    estimate = elapsed*16*1.5+60
    record = dict(run_id=RUN_ID, measured_utc=utc_now(), tissue_seconds=elapsed, projected_seconds=estimate,
                  must_detach=bool(estimate > 600), passes=True, new_simulations=0, effects_not_reported=True,
                  cpu_affinity=cpus, input_sha256={str(p): sha256_file(p) for p in inputs})
    strict_json(timing_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable diagnostic already exists")
    cpus = checker().runtime(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["run_id"] == RUN_ID and timing["passes"] is True and timing["input_sha256"] == hashes
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
        assert manifest[k] == v, k
    expected = {str(p) for p in input_paths(root) + [timing_path(root)]}
    hashes = manifest["input_sha256"]
    assert set(hashes) == expected and hashes and canonical_digest(hashes) == manifest["hash_contract"]
    assert all(sha256_file(Path(p)) == d for p, d in hashes.items())
    return manifest


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest, run = verify(root), root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    paths = [root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    paths[0].parent.mkdir(exist_ok=True)
    with paths[0].open("xb") as out, paths[1].open("xb") as err:
        process = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l22_early_signal_loss",
            "--external-root", str(root), "--run"], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=process.pid, launched_utc=utc_now(), polling_owner="user",
                  estimated_seconds=manifest["benchmark"]["projected_seconds"], stdout_log=str(paths[0]),
                  stderr_log=str(paths[1]), status=str(run/"STATUS.json"))
    strict_json(run/"LAUNCH.json", record, root)
    atomic_text(run/"RUN.pid", f"{process.pid}\n", root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # Never wait or poll the detached child.


def run_analysis(root):
    manifest = verify(root)
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached execution required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        checker().runtime(root)
        values, checks = [], []
        for tissue in TISSUES:
            arrays, record, checked = analyze_cell(root/"outputs"/SOURCE_ID/f"tissue_{tissue}", tissue)
            directory = require_beneath(output/f"tissue_{tissue}", root)
            directory.mkdir()
            with (directory/"analysis.npz").open("xb") as handle:
                np.savez_compressed(handle, **arrays)
            strict_json(directory/"analysis.json", record, root)
            with np.load(directory/"analysis.npz", allow_pickle=False) as saved:
                for k in arrays:
                    np.testing.assert_array_equal(saved[k], arrays[k])
            checker().close(json.loads((directory/"analysis.json").read_text()), record)
            values.append(arrays)
            checks.append(checked)
            strict_json(run/"STATUS.json", dict(status="RUNNING", run_id=RUN_ID, checked_tissues=len(checks), updated_utc=utc_now()), root)
            print(f"D075 retained analysis and independent check: tissue {tissue} complete", flush=True)
        summary = pooled(values)
        assert checker().check_pool(values, summary)
        assert [c["tissue"] for c in checks] == list(TISSUES)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        result = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, pooled=summary)
        strict_json(output/"analysis.json", result, root)
        strict_json(output/"verification.json", dict(passes=True, checked_utc=utc_now(), new_simulations=0,
                    law_verdict_changes=0, checks=checks, pooled_verified=True), root)
        paths = [output/"input_hashes.sha256", output/"analysis.json", output/"verification.json"]
        paths.extend(p for t in TISSUES for p in (output/f"tissue_{t}"/"analysis.json", output/f"tissue_{t}"/"analysis.npz"))
        assert len(paths) == 35
        write_hash_manifest(paths, output/"output_hashes.sha256", root)
        checker().source.common.manifest_check(output/"output_hashes.sha256")
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
                      completed_cleanly=True, verified_saved_analysis=True, new_simulations=0, checked_tissues=16)
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
        return run_analysis(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
