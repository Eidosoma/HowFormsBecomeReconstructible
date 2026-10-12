"""Independent saved-array and clustered-endpoint checks for D072."""

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

from laws_confirmation.io import atomic_text, canonical_digest, external_root, sha256_file, utc_now, write_hash_manifest
from laws_confirmation.l17_r_channel import verify_hashes

_spec = importlib.util.spec_from_file_location("l22_frozen_common_checker", Path(__file__).with_name("audit_l22_source_recovery_outputs.py"))
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)
SOURCE_ID = "l22_fixed_record_readout_v1_attempt1"
PARENT_ID = "l22_backup_free_feedback_v1_attempt1"
RUN_ID = SOURCE_ID + "_independent_rescore_v1"
TISSUES = list(range(30008, 30024))
CFG = dict(parents=4, draws=16, sweeps=1000, times=[0, 1, 1000])
ARMS = ("damaged", "fixed", "loop", "parent", "wrong", "reader_off")
KEYS = ("V", "ema", "R", "theta")
ENDPOINTS = (("loop_vs_damaged", "loop", "damaged"), ("fixed_vs_damaged", "fixed", "damaged"), ("loop_vs_fixed", "loop", "fixed"))


def strict_json(path, value, root):
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", root)


def seeded(tissue, phase, legacy=False):
    namespace = "l22-source-recovery-v1" if legacy else "l22-fixed-record-readout-v1"
    seed = int.from_bytes(hashlib.sha256(f"{namespace}:{tissue}:{phase}".encode()).digest()[:16], "little")
    return np.random.default_rng(seed)


def measure(v, cfg):
    parents, draws = cfg["parents"], cfg["draws"]
    codes = common.codebook()
    score_rows, probability_rows, correct, margin, good, active_good = [], [], [], [], [], []
    for i, field in enumerate(v):
        label = i // (parents * draws)
        sc = np.array([math.fsum((field * code).ravel()) / 256 for code in codes])
        ties = np.isclose(sc, sc.max(), rtol=0., atol=1e-12)
        probabilities = ties / ties.sum()
        score_rows.append(sc)
        probability_rows.append(probabilities)
        correct.append(float(probabilities[label]))
        margin.append(float(sc[label] - max(sc[k] for k in range(4) if k != label)))
        mask = (field > 0) == (codes[label] > 0)
        good.append(float(mask.mean()))
        active_good.append(float((mask & (abs(field) > .2)).mean()))
    records = [correct[i:i + draws] for i in range(0, len(correct), draws)]
    record_means = [math.fsum(row) / draws for row in records]
    mean = math.fsum(record_means) / len(records)
    variances = [math.fsum((x - m) ** 2 for x in row) / draws for row, m in zip(records, record_means)]
    within = math.fsum(variances) / len(records)
    between = math.fsum((m - mean) ** 2 for m in record_means) / len(records)
    total = math.fsum((x - mean) ** 2 for x in correct) / len(correct)
    assert abs(within + between - total) < 1e-12
    probabilities = np.array(probability_rows)
    metrics = {"accuracy": mean, "margin": math.fsum(margin) / len(margin),
        "sign_fidelity": math.fsum(good) / len(good), "amplitude_fidelity": math.fsum(active_good) / len(active_good),
        "V_mean": math.fsum(v.ravel()) / v.size, "V_rms": math.sqrt(math.fsum((v * v).ravel()) / v.size),
        "record_accuracy": record_means, "record_within_variance": variances,
        "within_record_variance": within, "between_record_variance": between, "total_variance": total,
        "varying_records": sum(min(row) != max(row) for row in records),
        "always_correct_records": sum(all(x == 1. for x in row) for row in records),
        "always_incorrect_records": sum(all(x == 0. for x in row) for row in records),
        "records": 4 * parents, "draws_per_record": draws,
        "confusion": probabilities.reshape(4, parents * draws, 4).mean(axis=1).tolist()}
    observer = {"scores": np.array(score_rows), "probabilities": probabilities,
                "correctness": np.array(records), "margins": np.array(margin).reshape(4 * parents, draws)}
    return metrics, observer


def check_readout(raw, theta, tissue, cfg, off=False, legacy=False):
    assert theta.dtype == np.float64 and theta.shape == (4 * cfg["parents"], 16, 16)
    incoming = np.repeat(theta, cfg["draws"], axis=0)
    rng = seeded(tissue, "assay_birth", legacy)
    v = .2 * np.tile(rng.standard_normal((cfg["parents"] * cfg["draws"], 16, 16)), (4, 1, 1))
    v -= v.mean(axis=(-2, -1), keepdims=True)
    for key in ("V", "ema"):
        np.testing.assert_array_equal(raw[f"s0_{key}"], v)
    assert set(raw) == {f"s{s}_{k}" for s in cfg["times"] for k in KEYS} | {"scores", "probabilities", "correctness", "margins"}
    for s in cfg["times"]:
        for k in KEYS:
            assert raw[f"s{s}_{k}"].shape == incoming.shape and np.isfinite(raw[f"s{s}_{k}"]).all()
        np.testing.assert_array_equal(raw[f"s{s}_theta"], incoming)
        assert np.all(raw[f"s{s}_R"] == 0.)
        if off:
            grouped = raw[f"s{s}_V"].reshape(4, cfg["parents"] * cfg["draws"], 16, 16)
            assert all(np.array_equal(grouped[0], g) for g in grouped[1:])
    metrics, observer = measure(raw[f"s{cfg['sweeps']}_V"], cfg)
    for key, value in observer.items():
        np.testing.assert_allclose(raw[key], value, rtol=0., atol=1e-12)
    if off:
        assert metrics["accuracy"] == .25
    return metrics


def check_calibration(directory, saved, cfg):
    theta = .3 * np.repeat(common.codebook(), cfg["parents"], axis=0)
    metrics = {}
    for name in ("positive", "reader_off"):
        raw = common.arrays(directory / f"calibration_{name}.npz")
        metrics[name] = check_readout(raw, theta, saved["tissue"], cfg, name == "reader_off")
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    common.close(saved["positive_accuracy"], metrics["positive"]["accuracy"])
    return metrics["positive"]["accuracy"]


def check_tissue(directory, parent_directory, saved, cfg):
    common.close(saved["config"], cfg)
    packets = common.arrays(directory / "packets.npz")
    assert set(packets) == {"damaged", "fixed", "loop", "parent"}
    mapping = {"damaged": ("boundary", "damaged_theta"), "fixed": ("recovery_fixed_damaged_reader", "s1000_theta"),
               "loop": ("recovery_loop", "s1000_theta"), "parent": ("parent", "theta")}
    for name, (file, key) in mapping.items():
        with np.load(parent_directory / f"{file}.npz", allow_pickle=False) as data:
            np.testing.assert_array_equal(packets[name], data[key])
    p = cfg["parents"]
    packets["wrong"] = np.concatenate((packets["loop"][p:], packets["loop"][:p]))
    packets["reader_off"] = packets["loop"]
    raws, arms, legacy = {}, {}, {}
    for name in ARMS:
        raw = common.arrays(directory / f"readout_{name}.npz")
        raws[name] = raw
        assert hashlib.sha256(packets[name].tobytes()).hexdigest() == saved["packet_hashes"][name]
        assert hashlib.sha256(np.repeat(packets[name], cfg["draws"], axis=0).tobytes()).hexdigest() == saved["expanded_hashes"][name]
        arms[name] = check_readout(raw, packets[name], saved["tissue"], cfg, name == "reader_off")
        common.close(saved["arms"][name], arms[name])
    for name in mapping:
        raw = common.arrays(directory / f"legacy_{name}.npz")
        legacy[name] = check_readout(raw, packets[name], saved["tissue"], cfg | {"draws": 1}, legacy=True)
        common.close(saved["legacy"][name], legacy[name])
        old_name = "fixed_damaged_reader" if name == "fixed" else name
        with np.load(parent_directory / f"probe_{old_name}.npz", allow_pickle=False) as data:
            for s in cfg["times"]:
                for k in KEYS:
                    np.testing.assert_array_equal(raw[f"s{s}_{k}"], data[f"s{s}_{k}"])
    cal_off = common.arrays(directory / "calibration_reader_off.npz")
    for s in cfg["times"]:
        for k in KEYS:
            expected = np.concatenate((raws["loop"][f"s{s}_{k}"][p * cfg["draws"]:], raws["loop"][f"s{s}_{k}"][:p * cfg["draws"]]))
            np.testing.assert_array_equal(raws["wrong"][f"s{s}_{k}"], expected)
        for k in ("V", "ema", "R"):
            np.testing.assert_array_equal(raws["reader_off"][f"s{s}_{k}"], cal_off[f"s{s}_{k}"])
    paired = {}
    for name, left, right in ENDPOINTS:
        pairs = list(zip(raws[left]["correctness"].ravel(), raws[right]["correctness"].ravel()))
        paired[name] = {"improved_draw_fraction": sum(a > b for a, b in pairs) / len(pairs),
                        "worsened_draw_fraction": sum(a < b for a, b in pairs) / len(pairs),
                        "tied_draw_fraction": sum(a == b for a, b in pairs) / len(pairs)}
    common.close(saved["paired"], paired)
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    assert set(saved["arms"]) == set(ARMS) and set(saved["legacy"]) == set(mapping)
    return {"tissue": saved["tissue"], "arms": arms, "paired": paired, "legacy": legacy}


def adjudicate(rows):
    assert [r["tissue"] for r in rows] == TISSUES
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for i, (name, left, right) in enumerate(ENDPOINTS):
        values = [r["arms"][left]["accuracy"] - r["arms"][right]["accuracy"] for r in rows]
        seed = 20260908097201 + i
        draws = np.random.default_rng(seed).integers(0, 16, (10000, 16))
        sample_means = [math.fsum(values[int(j)] for j in draw) / 16 for draw in draws]
        interval = np.quantile(sample_means, [.05 / 6, 1 - .05 / 6]).tolist()
        positive = sum(v > 0 for v in values)
        contrasts[name] = {"mean": math.fsum(values) / 16, "tissue_differences": values, "interval": interval,
                          "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000,
                          "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= 12)}
    live, fixed, extra = [contrasts[n]["supported"] for n, _, _ in ENDPOINTS]
    if not eligible:
        label = "PARENT_THETA_NOT_READABLE"
    elif not live:
        label = "FIXED_READER_RECORD_RELIABILITY_ONLY" if fixed else "NO_QUALIFIED_RECORD_RELIABILITY_BENEFIT"
    else:
        label = "LIVE_FEEDBACK_RECORD_RELIABILITY_SUPPORTED" if extra else "LIVE_WRITTEN_RECORD_RELIABILITY_SUPPORTED"
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def source_info(root):
    run, output = root / "runs" / SOURCE_ID, root / "outputs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"] is True
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    counts = [common.manifest_check(output / f"{kind}_hashes.sha256") for kind in ("input", "output")]
    manifest = json.loads((run / "MANIFEST.json").read_text())
    inputs = {p: d for d, p in (line.split("  ", 1) for line in (output / "input_hashes.sha256").read_text().splitlines())}
    assert inputs == manifest["input_sha256"] and canonical_digest(inputs) == manifest["hash_contract"]
    common.close(manifest["config"], CFG)
    assert manifest["run_id"] == SOURCE_ID and manifest["source_run"] == PARENT_ID
    assert manifest["tissues"] == TISSUES and manifest["workers"] == 4 and manifest["arms"] == list(ARMS)
    assert manifest["endpoints"] == [list(e) for e in ENDPOINTS]
    assert manifest["bootstrap_seeds"] == list(range(20260908097201, 20260908097204))
    assert manifest["quantiles"] == [.05 / 6, 1 - .05 / 6] and manifest["minimum_positive_tissues"] == 12
    assert manifest["scientific_readout_lives"] == 24576 and manifest["new_training_lives"] == 0
    assert manifest["calibration_lives_including_replay"] == 12288 and manifest["integrity_readout_lives"] == 5120
    assert manifest["source_panel_outcome_known"] is True and manifest["law_verdict_changes"] == 0
    study = json.loads((output / "readout.json").read_text())
    assert study["completed_cleanly"] is True and type(study["calibration_qualified"]) is bool
    assert study["law_verdict_changes"] == 0 and study["new_training_lives"] == 0
    assert study["source_panel_outcome_known"] is True and [r["tissue"] for r in study["calibrations"]] == TISSUES
    if study["calibration_qualified"]:
        assert [r["tissue"] for r in study["results"]] == TISSUES and counts[1] == 242
    else:
        assert study["results"] == [] and counts[1] == 50
        assert not list(output.glob("tissue_*/experiment.json"))
    assert status["classification"] == study["classification"]["label"]
    return study, counts


def input_paths(root):
    paths = [Path(__file__).resolve(), Path(common.__file__).resolve()]
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
    check_calibration(directory, study["calibrations"][0], CFG)
    if study["calibration_qualified"]:
        check_tissue(directory, root / "outputs" / PARENT_ID / "tissue_30008", study["results"][0], CFG)
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
    json.dumps(manifest, allow_nan=False)
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
        process = subprocess.Popen(cmd, cwd=Path(__file__).resolve().parents[1], stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, start_new_session=True)
    result = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(),
              "estimated_seconds": manifest["benchmark"]["projected_seconds"], "stdout_log": str(stdout),
              "stderr_log": str(stderr), "status": str(run / "STATUS.json"), "complete": str(run / "COMPLETE"),
              "failed": str(run / "FAILED"), "polling_owner": "user"}
    strict_json(run / "LAUNCH.json", result, root)
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    print(json.dumps(result, indent=2), flush=True)
    return result  # Never poll or wait after detached launch.


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
            common.close(json.loads((directory / "calibration.json").read_text()), study["calibrations"][i])
            positive.append(check_calibration(directory, study["calibrations"][i], CFG))
            if study["calibration_qualified"]:
                common.close(json.loads((directory / "experiment.json").read_text()), study["results"][i])
                checked.append(check_tissue(directory, root / "outputs" / PARENT_ID / f"tissue_{tissue}", study["results"][i], CFG))
            strict_json(run / "STATUS.json", {"status": "RUNNING", "checked_tissues": i + 1, "updated_utc": utc_now()}, root)
            print(f"independent L22 fixed-record readout: tissue {tissue} verified", flush=True)
        qualified = bool(min(positive) > .25 and math.fsum(positive) / 16 >= .75)
        assert qualified is study["calibration_qualified"]
        classification = adjudicate(checked) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        common.close(study["classification"], classification)
        assert verify_hashes(manifest["input_sha256"])
        record = {"run_id": RUN_ID, "source_run": SOURCE_ID, "passes": True, "checked_utc": utc_now(),
                  "new_simulations": 0, "source_manifest_counts": counts, "calibration_scores": positive,
                  "classification": classification, "scientific_readout_batches_checked": len(checked) * 6,
                  "historical_readout_batches_checked": len(checked) * 4, "calibration_batches_checked": len(positive) * 2,
                  "source_panel_outcome_known": True, "checked": checked}
        strict_json(output / "rescore.json", record, root)
        write_hash_manifest([output / "input_hashes.sha256", output / "rescore.json"], output / "output_hashes.sha256", root)
        common.manifest_check(output / "output_hashes.sha256")
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
