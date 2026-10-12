"""Independent saved-array audit of D071, with benchmarked no-poll execution."""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from laws_confirmation.io import (atomic_text, canonical_digest, external_root,
                                  sha256_file, utc_now, write_hash_manifest)
from laws_confirmation.l17_r_channel import verify_hashes

_spec = importlib.util.spec_from_file_location("frozen_l22_checker", Path(__file__).with_name("audit_l22_source_recovery_outputs.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)
SOURCE_ID = "l22_backup_free_feedback_v1_attempt1"
RUN_ID = SOURCE_ID + "_independent_rescore_v1"
TISSUES = list(range(30008, 30024))
CFG = dict(replicates=4, settle=120, imprint=1000, sweeps=1000,
           times=[0, 1, 50, 250, 500, 1000], norm=.3, lam=.001, damage=.3)
KEYS = ("V", "ema", "R", "theta")


def modes():
    def m(body="kept", reference="zero", write=True, hold=False, reader="live"):
        return dict(body=body, reference=reference, write=write, hold=hold, reader=reader)
    return {"loop": m(), "writer_off": m(write=False), "theta_read_off": m(reader="native"),
            "reference_write_off": m(hold=True), "fixed_damaged_reader": m(reader="damaged"),
            "scrambled_loop": m(body="scrambled"), "scrambled_fixed_reader": m(body="scrambled", reader="damaged"),
            "body_writer_off": m(reader="native", write=False), "wrong_fixed_reader": m(reader="wrong_damaged"),
            "backup": m(reference="copy")}


def strict_json(path, value, root):
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", root)


def check_tissue(directory, saved, cfg):
    rep, times = cfg["replicates"], cfg["times"]
    audit.close(saved["config"], cfg)
    parent, b, before = [audit.arrays(directory / f"{name}.npz") for name in ("parent", "boundary", "before")]
    assert set(parent) == set(before) == set(KEYS)
    assert audit.state_digest(parent) == saved["source_parent_sha256"]
    for value in before.values():
        assert all(np.array_equal(value[:rep], value[m * rep:(m + 1) * rep]) for m in range(4))
    for value in (before["theta"], parent["theta"], b["native_theta"]):
        np.testing.assert_allclose(value.std(axis=(-2, -1)), cfg["norm"], rtol=0., atol=1e-12)
    native = np.ascontiguousarray(b["native_theta"])
    assert hashlib.sha256(f"{native.dtype}:{native.shape}:".encode() + native.tobytes()).hexdigest() == saved["source_native_sha256"]
    fresh = audit.check_boundary(parent, b, saved["tissue"], cfg, saved["tissue_config"])
    # Reconstruct the incoming corruption, not new recovery dynamics.
    rng = audit.seeded(saved["tissue"], "damage")
    for i, old in enumerate(parent["theta"]):
        centered = old - old.mean()
        unit = centered / max(np.linalg.norm(centered), 1e-12)
        noise = rng.standard_normal(old.shape)
        noise -= noise.mean()
        noise -= (noise * unit).sum() * unit
        noise /= max(np.linalg.norm(noise), 1e-12)
        mixed = (cfg["damage"] * unit + math.sqrt(1 - cfg["damage"] ** 2) * noise) * np.linalg.norm(centered)
        mixed -= mixed.mean()
        expected = mixed * cfg["norm"] / max(mixed.std(), 1e-9)
        np.testing.assert_allclose(b["damaged_theta"][i], expected, rtol=0., atol=1e-12)
    recovery, probes, raws = {}, {}, {}
    for name, mode in modes().items():
        initial = {k: b[f"kept_{k}"].copy() for k in KEYS}
        if mode["body"] == "scrambled":
            initial["V"] = b["scrambled_V"].copy()
        initial["ema"] = initial["V"].copy()
        if mode["reference"] == "zero":
            initial["R"] = np.zeros_like(initial["R"])
        initial["theta"] = b["damaged_theta"].copy()
        assert audit.state_digest(initial) == saved["initial_hashes"][name]
        raw = audit.arrays(directory / f"recovery_{name}.npz")
        raws[name] = raw
        engine = {k: mode[k] for k in ("body", "reference", "write", "hold")}
        engine.update(theta_read=mode["reader"] == "live", intact=False)
        recovery[name] = audit.check_recovery(raw, initial, parent, fresh, engine, cfg, saved["recovery"][name])
        if mode["reader"] == "live":
            assert "fixed_reader" not in raw
        else:
            expected = (b["native_theta"] if mode["reader"] == "native" else b["damaged_theta"]
                        if mode["reader"] == "damaged" else np.concatenate((b["damaged_theta"][rep:], b["damaged_theta"][:rep])))
            np.testing.assert_array_equal(raw["fixed_reader"], expected)
    for left, right in (("fixed_damaged_reader", "writer_off"), ("theta_read_off", "body_writer_off")):
        for s in times:
            for k in ("V", "ema", "R"):
                np.testing.assert_array_equal(raws[left][f"s{s}_{k}"], raws[right][f"s{s}_{k}"])
        for key in ("body_trace", "reference_trace"):
            np.testing.assert_array_equal(raws[left][key], raws[right][key])
    for k in KEYS:
        np.testing.assert_array_equal(raws["loop"][f"s1_{k}"], raws["fixed_damaged_reader"][f"s1_{k}"])
    for s in times:
        assert np.all(raws["reference_write_off"][f"s{s}_R"] == 0.)
        np.testing.assert_allclose(raws["reference_write_off"][f"s{s}_theta"], b["damaged_theta"], rtol=0., atol=1e-11)
    v = .2 * np.tile(audit.seeded(saved["tissue"], "assay_birth").standard_normal((rep, 16, 16)), (4, 1, 1))
    v -= v.mean(axis=(-2, -1), keepdims=True)
    for name in (*modes(), "parent", "damaged", "reader_off"):
        raw = audit.arrays(directory / f"probe_{name}.npz")
        assert set(raw) == {f"s{s}_{k}" for s in times for k in KEYS}
        incoming = (parent["theta"] if name in ("parent", "reader_off") else b["damaged_theta"]
                    if name == "damaged" else raws[name][f"s{cfg['sweeps']}_theta"])
        assert hashlib.sha256(incoming.tobytes()).hexdigest() == saved["probe_packet_hashes"][name]
        for k in ("V", "ema"):
            np.testing.assert_array_equal(raw[f"s0_{k}"], v)
        probes[name] = {}
        for s in times:
            assert all(raw[f"s{s}_{k}"].shape == (4 * rep, 16, 16) and np.isfinite(raw[f"s{s}_{k}"]).all() for k in KEYS)
            np.testing.assert_array_equal(raw[f"s{s}_theta"], incoming)
            assert np.all(raw[f"s{s}_R"] == 0.)
            computed = audit.metrics({k: raw[f"s{s}_{k}"] for k in KEYS}, parent, np.ones_like(fresh), rep)
            audit.close(saved["probe"][name][str(s)], computed)
            probes[name][str(s)] = computed["mean"]
            if name == "reader_off":
                assert computed["mean"]["V_accuracy"] == .25
                assert all(np.array_equal(raw[f"s{s}_V"][:rep], raw[f"s{s}_V"][m * rep:(m + 1) * rep]) for m in range(4))
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    assert set(saved["recovery"]) == set(recovery) and set(saved["probe"]) == set(probes)
    return {"tissue": saved["tissue"], "recovery": recovery, "probe": probes}


def adjudicate(rows):
    assert [r["tissue"] for r in rows] == TISSUES
    parents = [r["probe"]["parent"]["1000"]["V_accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for i, right in enumerate(("writer_off", "theta_read_off", "fixed_damaged_reader")):
        values = [r["probe"]["loop"]["1000"]["V_accuracy"] - r["probe"][right]["1000"]["V_accuracy"] for r in rows]
        seed = 20260908097101 + i
        draws = np.random.default_rng(seed).integers(0, 16, (10000, 16))
        samples = [math.fsum(values[int(j)] for j in draw) / 16 for draw in draws]
        interval = np.quantile(samples, [.05 / 6, 1 - .05 / 6]).tolist()
        positive = sum(v > 0 for v in values)
        contrasts[f"readout_vs_{right}"] = {"mean": math.fsum(values) / 16, "tissue_differences": values,
            "interval": interval, "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000,
            "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= 12)}
    first, second, third = [v["supported"] for v in contrasts.values()]
    if not eligible:
        label = "PARENT_THETA_NOT_READABLE"
    elif not first:
        label = "NO_QUALIFIED_BACKUP_FREE_BENEFIT"
    elif not second:
        label = "BACKUP_FREE_WRITING_BENEFIT_ONLY"
    elif not third:
        label = "DAMAGED_READER_ASSISTED_WRITING_SUPPORTED"
    else:
        label = "BACKUP_FREE_RECIPROCAL_LOOP_SUPPORTED"
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def source_info(root):
    run, output = root / "runs" / SOURCE_ID, root / "outputs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"] is True
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    counts = [audit.manifest_check(output / f"{k}_hashes.sha256") for k in ("input", "output")]
    manifest = json.loads((run / "MANIFEST.json").read_text())
    input_hashes = {p: d for d, p in (line.split("  ", 1) for line in (output / "input_hashes.sha256").read_text().splitlines())}
    assert input_hashes == manifest["input_sha256"]
    assert canonical_digest(input_hashes) == manifest["hash_contract"]
    audit.close(manifest["config"], CFG)
    audit.close(manifest["modes"], modes())
    assert manifest["tissues"] == TISSUES and manifest["workers"] == 4 and manifest["minimum_positive_tissues"] == 12
    assert manifest["bootstrap_seeds"] == list(range(20260908097101, 20260908097104))
    assert manifest["quantiles"] == [.05 / 6, 1 - .05 / 6]
    assert manifest["endpoints"] == [[f"readout_vs_{a}", a] for a in ("writer_off", "theta_read_off", "fixed_damaged_reader")]
    assert manifest["probes"] == [*modes(), "parent", "damaged", "reader_off"]
    assert manifest["replays"] == ["loop", "fixed_damaged_reader"]
    study = json.loads((output / "feedback.json").read_text())
    assert study["completed_cleanly"] is True and type(study["calibration_qualified"]) is bool
    assert study["law_verdict_changes"] == 0 and [r["tissue"] for r in study["calibrations"]] == TISSUES
    if study["calibration_qualified"]:
        assert [r["tissue"] for r in study["results"]] == TISSUES and counts[1] == 482
    else:
        assert study["results"] == [] and not list(output.glob("tissue_*/experiment.json"))
    assert status["classification"] == study["classification"]["label"]
    return study, counts


def input_paths(root):
    ws = Path(__file__).resolve().parents[1]
    paths = [Path(__file__).resolve(), Path(audit.__file__).resolve(),
             ws / "protocols/L22_BACKUP_FREE_FEEDBACK_V1.md", ws / "tests/test_l22_backup_free_feedback.py"]
    for kind in ("input", "output"):
        manifest = root / "outputs" / SOURCE_ID / f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root / "runs" / SOURCE_ID / name for name in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    return sorted(set(paths))


def runtime(root):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k) == "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"))
    assert sys.version_info[:2] == (3, 13) and np.__version__ == "2.5.2"
    assert shutil.disk_usage(root).free >= (1024 + 128) * 1024**2
    return sorted(os.sched_getaffinity(0))


def timing_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("immutable independent audit already exists")
    cpus = runtime(root)
    study, counts = source_info(root)
    start = time.monotonic()
    directory = root / "outputs" / SOURCE_ID / "tissue_30008"
    audit.check_calibration(directory, study["calibrations"][0], CFG)
    if study["calibration_qualified"]:
        check_tissue(directory, study["results"][0], CFG)
    elapsed = time.monotonic() - start
    estimate = elapsed * 16 * 1.5 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "tissue_seconds": elapsed,
              "projected_seconds": estimate, "must_detach": bool(estimate > 600), "passes": True,
              "new_simulations": 0, "effects_not_reported": True, "cpu_affinity": cpus,
              "source_manifest_counts": counts, "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    strict_json(timing_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable independent audit already exists")
    timing = json.loads(timing_path(root).read_text())
    cpus = runtime(root)
    _, counts = source_info(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["passes"] is True and hashes == timing["input_sha256"]
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = {"run_id": RUN_ID, "source_run": SOURCE_ID, "prepared_utc": utc_now(), "new_simulations": 0,
                "benchmark": timing, "cpu_affinity": cpus, "source_manifest_counts": counts,
                "input_sha256": hashes, "hash_contract": canonical_digest(hashes)}
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    strict_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    strict_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID}, root)
    print(json.dumps({"status": "PREPARED", "input_hashes": len(hashes), "estimated_seconds": timing["projected_seconds"]}), flush=True)
    return manifest


def verify(root):
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    assert json.loads((run / "STATUS.json").read_text())["status"] == "PREPARED"
    assert not (run / "FAILED").exists() and not (run / "COMPLETE").exists()
    assert manifest["run_id"] == RUN_ID and manifest["source_run"] == SOURCE_ID and manifest["new_simulations"] == 0
    assert verify_hashes(manifest["input_sha256"]) and canonical_digest(manifest["input_sha256"]) == manifest["hash_contract"]
    assert set(manifest["input_sha256"]) == {str(p) for p in input_paths(root) + [timing_path(root)]}
    return manifest


def detach(root):
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest, run = verify(root), root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    (root / "logs").mkdir(exist_ok=True)
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    cmd = [sys.executable, str(Path(__file__).resolve()), "--external-root", str(root), "--run"]
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    result = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(),
              "estimated_seconds": manifest["benchmark"]["projected_seconds"], "stdout_log": str(stdout),
              "stderr_log": str(stderr), "status": str(run / "STATUS.json"), "complete": str(run / "COMPLETE"),
              "failed": str(run / "FAILED"), "polling_owner": "user"}
    strict_json(run / "LAUNCH.json", result, root)
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    print(json.dumps(result, indent=2), flush=True)
    return result


def run_audit(root):
    manifest = verify(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached audit required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        runtime(root)
        study, counts = source_info(root)
        checked, positive = [], []
        for i, tissue in enumerate(TISSUES):
            directory = root / "outputs" / SOURCE_ID / f"tissue_{tissue}"
            audit.close(json.loads((directory / "calibration.json").read_text()), study["calibrations"][i])
            positive.append(audit.check_calibration(directory, study["calibrations"][i], CFG))
            if study["calibration_qualified"]:
                audit.close(json.loads((directory / "experiment.json").read_text()), study["results"][i])
                checked.append(check_tissue(directory, study["results"][i], CFG))
            strict_json(run / "STATUS.json", {"status": "RUNNING", "checked_tissues": i + 1, "updated_utc": utc_now()}, root)
            print(f"independent L22 feedback: tissue {tissue} verified", flush=True)
        qualified = bool(min(positive) > .25 and math.fsum(positive) / 16 >= .75)
        assert qualified is study["calibration_qualified"]
        classification = adjudicate(checked) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        audit.close(study["classification"], classification)
        assert verify_hashes(manifest["input_sha256"])
        record = {"run_id": RUN_ID, "source_run": SOURCE_ID, "passes": True, "checked_utc": utc_now(),
                  "new_simulations": 0, "source_manifest_counts": counts, "calibration_scores": positive,
                  "classification": classification, "recovery_batches_checked": len(checked) * 10,
                  "assay_batches_checked": len(checked) * 13, "batch_writer_updates_checked": len(checked) * 10000,
                  "checked": checked}
        strict_json(output / "rescore.json", record, root)
        write_hash_manifest([output / "input_hashes.sha256", output / "rescore.json"], output / "output_hashes.sha256", root)
        audit.manifest_check(output / "output_hashes.sha256")
        status = {"status": "COMPLETE", "run_id": RUN_ID, "completed_utc": utc_now(),
                  "elapsed_seconds": time.monotonic() - start, "verified_scientific_data": True,
                  "new_simulations": 0, "classification": classification["label"]}
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
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_audit(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
