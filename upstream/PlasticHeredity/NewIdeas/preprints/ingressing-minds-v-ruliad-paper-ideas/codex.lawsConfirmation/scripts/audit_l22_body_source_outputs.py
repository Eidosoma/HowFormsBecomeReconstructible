"""Independent rank-transfer, saved-writer and functional-source audit for D074."""

import argparse
import hashlib
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

spec = importlib.util.spec_from_file_location("d074_frozen_checker", Path(__file__).with_name("audit_l22_fresh_writing_replication_outputs.py"))
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
common, writing, readout = prior.common, prior.writing, prior.readout
strict_json, runtime, check_calibration = prior.strict_json, prior.runtime, prior.check_calibration
SOURCE_ID = "l22_body_source_v1_attempt1"
RUN_ID = SOURCE_ID + "_independent_rescore_v1"
TISSUES = list(range(30040, 30056))
CFG = dict(replicates=4, settle=120, imprint=1000, sweeps=1000, times=[0, 1, 50, 250, 500, 1000], norm=.3, lam=.001, damage=.3)
RCFG = dict(parents=4, draws=16, sweeps=1000, times=[0, 1, 1000])
KEYS = ("V", "ema", "R", "theta")
EXTRA = {"scrambled_off": ("scrambled", False, False), "donor_loop": ("donor", True, False),
         "donor_fixed": ("donor", True, True), "donor_off": ("donor", False, False)}
MAPPING = {
    "kept_loop": ("writing", "loop"), "kept_fixed": ("writing", "fixed_damaged_reader"),
    "kept_off": ("writing", "writer_off"), "scrambled_loop": ("writing", "scrambled_loop"),
    "scrambled_fixed": ("writing", "scrambled_fixed_reader"),
    "scrambled_off": ("intervention", "scrambled_off"), "donor_loop": ("intervention", "donor_loop"),
    "donor_fixed": ("intervention", "donor_fixed"), "donor_off": ("intervention", "donor_off"),
    "damaged": ("writing", "damaged"), "parent": ("writing", "parent"),
}
ARMS = (*MAPPING, "wrong_packet", "reader_off")
ENDPOINTS = (("useful_repair", "kept_loop", "damaged", "accuracy"),
             ("body_organization", "kept_loop", "scrambled_loop", "accuracy"),
             ("donor_redirection", "donor_loop", "scrambled_loop", "donor_accuracy"))


def check_manifest(path, expected):
    assert common.manifest_check(path) == len(expected)
    rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
    assert len(rows) == len({p for _, p in rows}) and {p for _, p in rows} == {str(p) for p in expected}


def rank_body(kept, fresh, rep):
    assert kept.dtype == np.float64 and fresh.dtype == bool and kept.shape == fresh.shape == (4 * rep, 16, 16)
    assert np.isfinite(kept).all()
    result, orders, ids = kept.copy(), [], []
    for i in range(4 * rep):
        donor = ((i // rep + 1) % 4) * rep + i % rep
        np.testing.assert_array_equal(fresh[i], fresh[donor])
        positions = [k for k, is_fresh in enumerate(fresh[i].ravel()) if not is_fresh]
        assert len(positions) == 128
        values = sorted(float(kept[i].flat[k]) for k in positions)
        ordering = sorted(range(128), key=lambda k: (float(kept[donor].flat[positions[k]]), k))
        for value, rank in zip(values, ordering):
            result[i].flat[positions[rank]] = value
        np.testing.assert_array_equal(np.sort(result[i][~fresh[i]]), np.sort(kept[i][~fresh[i]]))
        np.testing.assert_array_equal(result[i][fresh[i]], kept[i][fresh[i]])
        orders.append(ordering)
        ids.append(donor)
    return {"donor_V": result, "donor_indices": np.array(ids, dtype=np.int64), "donor_order": np.array(orders, dtype=np.int64),
            "changed_cells": np.count_nonzero(result != kept, axis=(1, 2))}


def donor_scores(raw, cfg):
    values, own = [], []
    width = cfg["parents"] * cfg["draws"]
    for i, probabilities in enumerate(raw["probabilities"]):
        values.append(float(probabilities[(i // width + 1) % 4]))
        own.append(float(probabilities[i // width]))
    draws = cfg["draws"]
    records = [math.fsum(values[i:i + draws]) / draws for i in range(0, len(values), draws)]
    return {"donor_accuracy": math.fsum(values) / len(values), "donor_record_accuracy": records,
            "own_minus_donor": math.fsum(a - b for a, b in zip(own, values)) / len(values)}


def check_writing(directory, saved, cfg=CFG):
    wd, ed = directory / "writing", directory / "intervention"
    rep, times, sweep = cfg["replicates"], cfg["times"], cfg["sweeps"]
    assert saved["passes"] is True and saved["tissue"] == saved["legacy"]["tissue"] == saved["intervention"]["tissue"]
    for folder, key in ((wd, "legacy"), (ed, "intervention")):
        common.close(json.loads((folder / "experiment.json").read_text()), saved[key])
    base_names = {"before", "parent", "boundary", *(f"recovery_{a}" for a in writing.modes()),
                  *(f"probe_{a}" for a in (*writing.modes(), "parent", "damaged", "reader_off"))}
    check_manifest(wd / "writing_hashes.sha256", {wd / f"{n}.npz" for n in base_names} | {wd / "experiment.json"})
    extra_names = {"bodies", *(f"{prefix}_{a}" for prefix in ("recovery", "probe") for a in EXTRA)}
    check_manifest(ed / "intervention_hashes.sha256", {ed / f"{n}.npz" for n in extra_names} | {ed / "experiment.json"})
    base_checked = writing.check_tissue(wd, saved["legacy"], cfg)
    parent, boundary, bodies = [common.arrays(p) for p in (wd / "parent.npz", wd / "boundary.npz", ed / "bodies.npz")]
    reconstructed = rank_body(boundary["kept_V"], boundary["fresh"], rep)
    assert set(bodies) == set(reconstructed)
    for key in bodies:
        assert bodies[key].dtype == reconstructed[key].dtype
        np.testing.assert_array_equal(bodies[key], reconstructed[key])
    extra = saved["intervention"]
    common.close(extra["config"], cfg)
    common.close(extra["changed_cells"], bodies["changed_cells"].tolist())
    common.close(extra["donor_indices"], bodies["donor_indices"].tolist())
    assert extra["passes"] is True and all(v is True for v in extra["gates"].values())
    assert all(set(extra[k]) == set(EXTRA) for k in ("recovery", "probe", "initial_hashes", "probe_packet_hashes"))
    recovery, probes, raws = {}, {}, {}
    fresh, damaged = boundary["fresh"], boundary["damaged_theta"]
    for name, (body, write, fixed) in EXTRA.items():
        v = bodies["donor_V"] if body == "donor" else boundary["scrambled_V"]
        initial = {"V": v, "ema": v.copy(), "R": np.zeros_like(v), "theta": damaged.copy()}
        assert common.state_digest(initial) == extra["initial_hashes"][name]
        raw = common.arrays(ed / f"recovery_{name}.npz")
        raws[name] = raw
        mode = dict(body="kept", reference="zero", write=write, hold=False, theta_read=not fixed, intact=False)
        recovery[name] = common.check_recovery(raw, initial, parent, fresh, mode, cfg, extra["recovery"][name])
        if fixed:
            np.testing.assert_array_equal(raw["fixed_reader"], damaged)
        else:
            assert "fixed_reader" not in raw
        probe = common.arrays(ed / f"probe_{name}.npz")
        assert set(probe) == {f"s{s}_{k}" for s in times for k in KEYS}
        packet = raw[f"s{sweep}_theta"]
        assert hashlib.sha256(packet.tobytes()).hexdigest() == extra["probe_packet_hashes"][name]
        birth = .2 * np.tile(common.seeded(saved["tissue"], "assay_birth").standard_normal((rep, 16, 16)), (4, 1, 1))
        birth -= birth.mean(axis=(-2, -1), keepdims=True)
        for k in ("V", "ema"):
            np.testing.assert_array_equal(probe[f"s0_{k}"], birth)
        probes[name] = {}
        for s in times:
            assert all(probe[f"s{s}_{k}"].shape == (4 * rep, 16, 16) and np.isfinite(probe[f"s{s}_{k}"]).all() for k in KEYS)
            np.testing.assert_array_equal(probe[f"s{s}_theta"], packet)
            assert np.all(probe[f"s{s}_R"] == 0.)
            computed = common.metrics({k: probe[f"s{s}_{k}"] for k in KEYS}, parent, np.ones_like(fresh), rep)
            common.close(extra["probe"][name][str(s)], computed)
            probes[name][str(s)] = computed["mean"]
    old_fixed = common.arrays(wd / "recovery_scrambled_fixed_reader.npz")
    for left, right in ((old_fixed, raws["scrambled_off"]), (raws["donor_fixed"], raws["donor_off"])):
        for k in ("body_trace", "reference_trace", *(f"s{s}_{k}" for s in times for k in ("V", "ema", "R"))):
            np.testing.assert_array_equal(left[k], right[k])
    old_loop = common.arrays(wd / "recovery_scrambled_loop.npz")
    for left, right in ((old_loop, old_fixed), (raws["donor_loop"], raws["donor_fixed"])):
        for k in KEYS:
            np.testing.assert_array_equal(left[f"s1_{k}"], right[f"s1_{k}"])
    return {"legacy": base_checked, "intervention": {"recovery": recovery, "probe": probes,
            "changed_cells": bodies["changed_cells"].tolist(), "donor_indices": bodies["donor_indices"].tolist()}}


def check_readouts(directory, saved, cfg=CFG, rcfg=RCFG):
    rd = directory / "readout"
    common.close(saved["config"], rcfg)
    common.close(json.loads((rd / "experiment.json").read_text()), saved)
    assert saved["packet_origin"] == "current_body_source_writing"
    hashes = {"writing": sha256_file(directory / "writing/writing_hashes.sha256"),
              "intervention": sha256_file(directory / "intervention/intervention_hashes.sha256")}
    assert saved["writing_manifest_sha256"] == hashes
    packets = common.arrays(rd / "packets.npz")
    assert set(packets) == set(MAPPING)
    for name, (folder, old) in MAPPING.items():
        filename, key = ("boundary", "damaged_theta") if name == "damaged" else ("parent", "theta") if name == "parent" else (f"recovery_{old}", f"s{cfg['sweeps']}_theta")
        with np.load(directory / folder / f"{filename}.npz", allow_pickle=False) as data:
            np.testing.assert_array_equal(packets[name], data[key])
    rep = rcfg["parents"]
    packets["wrong_packet"] = np.concatenate((packets["kept_loop"][rep:], packets["kept_loop"][:rep]))
    packets["reader_off"] = packets["kept_loop"]
    arms, raws, legacy = {}, {}, {}
    for name in ARMS:
        raw = common.arrays(rd / f"readout_{name}.npz")
        raws[name] = raw
        assert hashlib.sha256(packets[name].tobytes()).hexdigest() == saved["packet_hashes"][name]
        assert hashlib.sha256(np.repeat(packets[name], rcfg["draws"], axis=0).tobytes()).hexdigest() == saved["expanded_hashes"][name]
        arms[name] = readout.check_readout(raw, packets[name], saved["tissue"], rcfg, name == "reader_off") | donor_scores(raw, rcfg)
        common.close(saved["arms"][name], arms[name])
    for name, (folder, old) in MAPPING.items():
        raw = common.arrays(rd / f"legacy_{name}.npz")
        one = rcfg | {"draws": 1}
        legacy[name] = readout.check_readout(raw, packets[name], saved["tissue"], one, legacy=True) | donor_scores(raw, one)
        common.close(saved["legacy"][name], legacy[name])
        with np.load(directory / folder / f"probe_{old}.npz", allow_pickle=False) as data:
            for s in rcfg["times"]:
                for k in KEYS:
                    np.testing.assert_array_equal(raw[f"s{s}_{k}"], data[f"s{s}_{k}"])
    for name in ("kept_off", "scrambled_off", "donor_off"):
        for k in raws[name]:
            np.testing.assert_array_equal(raws[name][k], raws["damaged"][k])
    cal = common.arrays(rd / "calibration_reader_off.npz")
    for s in rcfg["times"]:
        for k in KEYS:
            field = raws["kept_loop"][f"s{s}_{k}"]
            n = rep * rcfg["draws"]
            np.testing.assert_array_equal(raws["wrong_packet"][f"s{s}_{k}"], np.concatenate((field[n:], field[:n])))
        for k in ("V", "ema", "R"):
            np.testing.assert_array_equal(raws["reader_off"][f"s{s}_{k}"], cal[f"s{s}_{k}"])
    assert saved["passes"] is True and all(v is True for v in saved["gates"].values())
    assert set(saved["arms"]) == set(saved["packet_hashes"]) == set(saved["expanded_hashes"]) == set(ARMS)
    assert set(saved["legacy"]) == set(MAPPING)
    return {"arms": arms, "legacy": legacy}


def check_tissue(directory, saved_writing, saved_readout, cfg=CFG, rcfg=RCFG):
    assert saved_writing["tissue"] == saved_readout["tissue"]
    checked = check_writing(directory, saved_writing, cfg)
    return {"tissue": saved_writing["tissue"], "writing": checked, "readout": check_readouts(directory, saved_readout, cfg, rcfg)}


def adjudicate(rows):
    assert [r["tissue"] for r in rows] == TISSUES
    parents = [r["readout"]["arms"]["parent"]["accuracy"] for r in rows]
    eligible = bool(min(parents) > .25 and math.fsum(parents) / 16 >= .75)
    contrasts = {}
    for i, (name, left, right, metric) in enumerate(ENDPOINTS):
        values = [r["readout"]["arms"][left][metric] - r["readout"]["arms"][right][metric] for r in rows]
        seed = 20260908097401 + i
        draws = np.random.default_rng(seed).integers(0, 16, (10000, 16))
        means = [math.fsum(values[int(j)] for j in draw) / 16 for draw in draws]
        interval = np.quantile(means, [.05 / 6, 1 - .05 / 6]).tolist()
        positive = sum(v > 0 for v in values)
        contrasts[name] = {"mean": math.fsum(values) / 16, "tissue_differences": values, "interval": interval,
                          "quantiles": [.05 / 6, 1 - .05 / 6], "seed": seed, "resamples": 10000,
                          "positive_tissues": positive, "supported": bool(interval[0] > 0 and positive >= 12)}
    useful, organization, donor = [contrasts[name]["supported"] for name, *_ in ENDPOINTS]
    if not eligible:
        label = "PARENT_THETA_NOT_READABLE"
    elif organization and donor:
        label = "BODY_CONTENT_SPECIFIC_REPAIR_SUPPORTED" if useful else "BODY_CONTENT_REDIRECTION_WITHOUT_QUALIFIED_REPAIR"
    elif organization:
        label = "BODY_ORGANIZATION_BENEFIT_ONLY"
    elif donor:
        label = "DONOR_BODY_REDIRECTION_ONLY"
    else:
        label = "REPAIR_WITHOUT_QUALIFIED_BODY_SOURCE" if useful else "NO_QUALIFIED_BODY_SOURCE_EFFECT"
    return {"label": label, "eligible": eligible, "parent_readout": parents, "co_primary": contrasts}


def source_info(root):
    run, output = root / "runs" / SOURCE_ID, root / "outputs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"] is True
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
    counts = [common.manifest_check(output / f"{kind}_hashes.sha256") for kind in ("input", "output")]
    manifest = json.loads((run / "MANIFEST.json").read_text())
    assert manifest["run_id"] == SOURCE_ID and manifest["source_run"] == "l22_fresh_writing_replication_v1_attempt1"
    inputs = {p: h for h, p in (line.split("  ", 1) for line in (output / "input_hashes.sha256").read_text().splitlines())}
    assert inputs == manifest["input_sha256"] and canonical_digest(inputs) == manifest["hash_contract"]
    common.close(manifest["config"], CFG)
    common.close(manifest["readout_config"], RCFG)
    common.close(manifest["legacy_modes"], writing.modes())
    expected_modes = {a: {"body_source": body, "mode": dict(body="kept", reference="zero", write=write, hold=False,
                      reader="damaged" if fixed else "live")} for a, (body, write, fixed) in EXTRA.items()}
    common.close(manifest["extra_modes"], expected_modes)
    common.close(manifest["packet_mapping"], {k: list(v) for k, v in MAPPING.items()})
    assert manifest["readout_arms"] == list(ARMS) and manifest["tissues"] == TISSUES and manifest["workers"] == 4
    assert manifest["stages"] == ["calibration", "writing", "readout"]
    assert manifest["endpoints"] == [list(e) for e in ENDPOINTS] and manifest["bootstrap_seeds"] == list(range(20260908097401, 20260908097404))
    assert manifest["quantiles"] == [.05 / 6, 1 - .05 / 6] and manifest["minimum_positive_tissues"] == 12
    assert manifest["body_operator"] == "recipient_values_in_stable_cyclic_donor_rank_order" and manifest["donor_offset"] == 1
    assert manifest["fresh_parents"] is True and manifest["retained_scientific_packets_used"] == manifest["law_verdict_changes"] == 0
    expected_counts = dict(parent_lives=256, recovery_lives=3584, legacy_diagnostic_readouts=4352, legacy_calibration_lives=768,
        writing_integrity_lives=1536, scientific_readout_lives=53248, readout_calibration_lives=12288,
        readout_replay_lives=8192, legacy_wrapper_replay_lives=2816, total_lives=87040,
        qualified_output_hashes=1138, unqualified_output_hashes=98)
    assert all(manifest[k] == v for k, v in expected_counts.items())
    study = json.loads((output / "body_source.json").read_text())
    assert study["run_id"] == SOURCE_ID and study["source_run"] == manifest["source_run"]
    assert study["completed_cleanly"] is True and type(study["calibration_qualified"]) is bool
    assert study["fresh_parents"] is True and study["retained_scientific_packets_used"] == study["law_verdict_changes"] == 0
    assert [r["tissue"] for r in study["calibrations"]] == TISSUES
    if study["calibration_qualified"]:
        assert [r["tissue"] for r in study["writing"]] == [r["tissue"] for r in study["readout"]] == TISSUES and counts[1] == 1138
    else:
        assert study["writing"] == study["readout"] == [] and counts[1] == 98
        assert not list(output.glob("tissue_*/*/experiment.json"))
    assert status["classification"] == study["classification"]["label"]
    return study, counts


def input_paths(root):
    paths = [Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(writing.__file__).resolve(), Path(readout.__file__).resolve()]
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
    directory = root / "outputs" / SOURCE_ID / "tissue_30040"
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
    timing, cpus = json.loads(timing_path(root).read_text()), runtime(root)
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
            print(f"independent L22 body source: tissue {tissue} verified", flush=True)
        qualified = bool(all(min(p[n] for p in positive) > .25 and math.fsum(p[n] for p in positive) / 16 >= .75 for n in ("legacy", "readout")))
        assert qualified is study["calibration_qualified"]
        classification = adjudicate(checked) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}
        common.close(study["classification"], classification)
        assert verify_hashes(manifest["input_sha256"])
        record = {"run_id": RUN_ID, "source_run": SOURCE_ID, "passes": True, "checked_utc": utc_now(), "new_simulations": 0,
                  "source_manifest_counts": counts, "calibration_scores": positive, "classification": classification,
                  "recovery_batches_checked": len(checked) * 14, "legacy_diagnostic_batches_checked": len(checked) * 17,
                  "scientific_readout_batches_checked": len(checked) * 13, "legacy_wrapper_batches_checked": len(checked) * 11,
                  "calibration_batches_checked": len(positive) * 4, "batch_writer_recurrences_checked": len(checked) * 14000,
                  "rank_transfers_checked": len(checked) * 16, "fresh_parents": True, "checked": checked}
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
