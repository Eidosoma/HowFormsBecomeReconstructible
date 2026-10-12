"""Independent current-writing provenance and reliability checks for D073."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np

from laws_confirmation.io import atomic_text, canonical_digest, external_root, sha256_file, utc_now, write_hash_manifest
from laws_confirmation.l17_r_channel import verify_hashes


def load_checker(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


writing = load_checker("d073_frozen_writing_checker", "audit_l22_backup_free_feedback_outputs.py")
readout = load_checker("d073_frozen_readout_checker", "audit_l22_fixed_record_readout_outputs.py")
common, strict_json, runtime = readout.common, readout.strict_json, readout.runtime
SOURCE_ID = "l22_fresh_writing_replication_v1_attempt1"
RUN_ID = SOURCE_ID + "_independent_rescore_v1"
TISSUES = list(range(30024, 30040))
CFG = dict(replicates=4, settle=120, imprint=1000, sweeps=1000, times=[0, 1, 50, 250, 500, 1000], norm=.3, lam=.001, damage=.3)
RCFG = dict(parents=4, draws=16, sweeps=1000, times=[0, 1, 1000])
ENDPOINTS = (("loop_vs_damaged", "loop", "damaged"), ("fixed_vs_damaged", "fixed", "damaged"), ("loop_vs_fixed", "loop", "fixed"))


def check_calibration(directory, saved, cfg=CFG, rcfg=RCFG):
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    assert saved["legacy"]["tissue"] == saved["readout"]["tissue"] == saved["tissue"]
    for name, key in (("writing", "legacy"), ("readout", "readout")):
        common.close(json.loads((directory / name / "calibration.json").read_text()), saved[key])
    return {"legacy": writing.audit.check_calibration(directory / "writing", saved["legacy"], cfg),
            "readout": readout.check_calibration(directory / "readout", saved["readout"], rcfg)}


def check_tissue(directory, saved_writing, saved_readout, cfg=CFG, rcfg=RCFG):
    wd, rd = directory / "writing", directory / "readout"
    assert saved_writing["tissue"] == saved_readout["tissue"]
    common.close(json.loads((wd / "experiment.json").read_text()), saved_writing)
    common.close(json.loads((rd / "experiment.json").read_text()), saved_readout)
    assert common.manifest_check(wd / "writing_hashes.sha256") == 27
    hashes = {p: h for h, p in (line.split("  ", 1) for line in (wd / "writing_hashes.sha256").read_text().splitlines())}
    expected = {wd / f"{n}.npz" for n in ("before", "parent", "boundary", *(f"recovery_{a}" for a in writing.modes()),
                    *(f"probe_{a}" for a in (*writing.modes(), "parent", "damaged", "reader_off")))}
    assert set(hashes) == {str(p) for p in expected | {wd / "experiment.json"}}
    assert saved_readout["packet_origin"] == "current_fresh_writing_cell"
    assert saved_readout["writing_manifest_sha256"] == sha256_file(wd / "writing_hashes.sha256")
    checked_writing = writing.check_tissue(wd, saved_writing, cfg)
    checked_readout = readout.check_tissue(rd, wd, saved_readout, rcfg)
    with np.load(wd / "recovery_writer_off.npz", allow_pickle=False) as off, np.load(wd / "boundary.npz", allow_pickle=False) as boundary:
        np.testing.assert_array_equal(off[f"s{cfg['sweeps']}_theta"], boundary["damaged_theta"])
    return {"tissue": saved_writing["tissue"], "writing": checked_writing, "readout": checked_readout}


def adjudicate(rows):
    assert [r["tissue"] for r in rows] == TISSUES
    parents = [r["readout"]["arms"]["parent"]["accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for i, (name, left, right) in enumerate(ENDPOINTS):
        values = [r["readout"]["arms"][left]["accuracy"] - r["readout"]["arms"][right]["accuracy"] for r in rows]
        seed = 20260908097301 + i
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
        label = "FIXED_READER_WRITING_REPLICATION_ONLY" if fixed else "NO_QUALIFIED_FRESH_WRITING_BENEFIT"
    else:
        label = "FRESH_FEEDBACK_RELIABILITY_REPLICATED" if extra else "FRESH_WRITING_RELIABILITY_REPLICATED"
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def source_info(root):
    run, output = root / "runs" / SOURCE_ID, root / "outputs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"] is True
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    counts = [common.manifest_check(output / f"{kind}_hashes.sha256") for kind in ("input", "output")]
    manifest = json.loads((run / "MANIFEST.json").read_text())
    assert manifest["run_id"] == SOURCE_ID and manifest["source_run"] == "l22_fixed_record_readout_v1_attempt1"
    inputs = {p: h for h, p in (line.split("  ", 1) for line in (output / "input_hashes.sha256").read_text().splitlines())}
    assert inputs == manifest["input_sha256"] and canonical_digest(inputs) == manifest["hash_contract"]
    common.close(manifest["config"], CFG)
    common.close(manifest["readout_config"], RCFG)
    common.close(manifest["modes"], writing.modes())
    assert manifest["tissues"] == TISSUES and manifest["workers"] == 4
    assert manifest["stages"] == ["calibration", "writing", "readout"]
    assert manifest["readout_arms"] == list(readout.ARMS)
    assert manifest["legacy_probes"] == [*writing.modes(), "parent", "damaged", "reader_off"]
    assert manifest["endpoints"] == [list(e) for e in ENDPOINTS]
    assert manifest["bootstrap_seeds"] == list(range(20260908097301, 20260908097304))
    assert manifest["quantiles"] == [.05 / 6, 1 - .05 / 6] and manifest["minimum_positive_tissues"] == 12
    assert manifest["fresh_parent_replication"] is True and manifest["retained_scientific_packets_used"] == 0
    assert manifest["law_verdict_changes"] == 0 and manifest["total_lives"] == 49920
    assert manifest["parent_lives"] == 256 and manifest["recovery_lives"] == 2560 and manifest["scientific_readout_lives"] == 24576
    study = json.loads((output / "replication.json").read_text())
    assert study["completed_cleanly"] is True and type(study["calibration_qualified"]) is bool
    assert study["fresh_parent_replication"] is True and study["retained_scientific_packets_used"] == study["law_verdict_changes"] == 0
    assert [r["tissue"] for r in study["calibrations"]] == TISSUES
    if study["calibration_qualified"]:
        assert [r["tissue"] for r in study["writing"]] == [r["tissue"] for r in study["readout"]] == TISSUES and counts[1] == 738
    else:
        assert study["writing"] == study["readout"] == [] and counts[1] == 98
        assert not list(output.glob("tissue_*/*/experiment.json"))
    assert status["classification"] == study["classification"]["label"]
    return study, counts


def input_paths(root):
    paths = [Path(__file__).resolve(), Path(writing.__file__).resolve(), Path(readout.__file__).resolve()]
    for kind in ("input", "output"):
        manifest = root / "outputs" / SOURCE_ID / f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root / "runs" / SOURCE_ID / name for name in ("MANIFEST.json", "STATUS.json", "COMPLETE"))
    return sorted(set(paths))


def timing_path(root):
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("immutable independent audit already exists")
    cpus = runtime(root)
    study, counts = source_info(root)
    start = time.monotonic()
    directory = root / "outputs" / SOURCE_ID / "tissue_30024"
    check_calibration(directory, study["calibrations"][0])
    if study["calibration_qualified"]:
        check_tissue(directory, study["writing"][0], study["readout"][0])
    elapsed = time.monotonic() - start
    estimate = elapsed * 16 * 1.5 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "tissue_seconds": elapsed, "projected_seconds": estimate,
              "must_detach": bool(estimate > 600), "passes": True, "new_simulations": 0, "effects_not_reported": True,
              "cpu_affinity": cpus, "source_manifest_counts": counts, "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
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
    command = [sys.executable, str(Path(__file__).resolve()), "--external-root", str(root), "--run"]
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[1], stdin=subprocess.DEVNULL,
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
            positive.append(check_calibration(directory, study["calibrations"][i]))
            if study["calibration_qualified"]:
                checked.append(check_tissue(directory, study["writing"][i], study["readout"][i]))
            strict_json(run / "STATUS.json", {"status": "RUNNING", "checked_tissues": i + 1, "updated_utc": utc_now()}, root)
            print(f"independent L22 fresh writing: tissue {tissue} verified", flush=True)
        qualified = bool(all(min(p[n] for p in positive) > .25 and math.fsum(p[n] for p in positive) / 16 >= .75
                             for n in ("legacy", "readout")))
        assert qualified is study["calibration_qualified"]
        classification = adjudicate(checked) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        common.close(study["classification"], classification)
        assert verify_hashes(manifest["input_sha256"])
        record = {"run_id": RUN_ID, "source_run": SOURCE_ID, "passes": True, "checked_utc": utc_now(), "new_simulations": 0,
                  "source_manifest_counts": counts, "calibration_scores": positive, "classification": classification,
                  "recovery_batches_checked": len(checked) * 10, "legacy_diagnostic_batches_checked": len(checked) * 13,
                  "scientific_readout_batches_checked": len(checked) * 6, "legacy_wrapper_batches_checked": len(checked) * 4,
                  "calibration_batches_checked": len(positive) * 4, "batch_writer_recurrences_checked": len(checked) * 10000,
                  "fresh_parent_replication": True, "checked": checked}
        strict_json(output / "rescore.json", record, root)
        write_hash_manifest([output / "input_hashes.sha256", output / "rescore.json"], output / "output_hashes.sha256", root)
        common.manifest_check(output / "output_hashes.sha256")
        status = {"status": "COMPLETE", "run_id": RUN_ID, "completed_utc": utc_now(), "elapsed_seconds": time.monotonic() - start,
                  "verified_scientific_data": True, "new_simulations": 0, "classification": classification["label"]}
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
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_audit(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
