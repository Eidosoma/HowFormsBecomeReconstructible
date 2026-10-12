from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_value_layout_crossover as study


@pytest.fixture(scope="module")
def check():
    return study.checker()


def fixture_cell(root, cfg, rcfg):
    root.mkdir(parents=True, exist_ok=True)
    original = study.disposable_source(root, 402081, root/"disposable_source", cfg, rcfg)
    records, checked = {}, {}
    for stage in study.STAGES:
        records[stage], checked[stage] = study.execute_cell(root, 402081, stage, root/"cell", cfg, rcfg, original=original)
    return dict(root=root, original=original, output=root/"cell", tissue=402081, cfg=cfg, rcfg=rcfg, records=records, checked=checked)


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    return fixture_cell(tmp_path_factory.mktemp("value-layout-fixture"),
        replace(study.CONFIG, settle=16, imprint=32, sweeps=16, times=(0, 1, 8, 16)),
        replace(study.READOUT_CONFIG, draws=2, sweeps=16, times=(0, 1, 16)))


def test_contract_and_frozen_sources(check, monkeypatch):
    c = study.contract()
    assert study.TISSUES == check.TISSUES == tuple(range(30056, 30072))
    assert study.TISSUES == study.prior.TISSUES
    for key in ("BODIES", "READERS", "MAIN", "OFF", "RECOVERIES", "REPLAYS", "PACKETS", "ARMS", "FIELDS", "METRICS", "FUNCTIONAL"):
        assert getattr(study, key) == getattr(check, key)
    assert {k: tuple(v.items()) for k, v in study.CONTRASTS.items()} == check.TERMS and len(study.CONTRASTS) == 49
    assert len(study.FOCAL) == 6 and c["fresh_parent_panel"] is False
    assert c["new_training_lives"] == c["parent_execution_lives"] == c["law_verdict_changes"] == 0
    assert c["retained_parents"] == 256 and c["new_writing_lives"] == 1024
    assert c["parent_execution_lives"]+c["total_recovery_lives"]+c["total_readout_lives"] == c["total_executed_lives"] == 114176
    assert c["scored_readout_lives"]+c["replay_lives"]+c["calibration_lives"] == 106496
    assert c["output_hashes"] == 899 and c["workers"] == 4
    monkeypatch.setattr(study, "source_inputs", lambda root: [])
    paths = study.input_paths(Path("/unused"))
    assert len(paths) == 6 and all(p.is_file() for p in paths)
    assert Path(check.__file__).resolve() in paths
    for arm in study.RECOVERIES:
        m = study.mode(arm)
        assert m.reader in ("native", "damaged") and m.reference == "zero" and not m.hold
        assert m.write is (arm not in study.OFF)
    with pytest.raises(ValueError):
        study.mode("reverse_live")


def test_donor_directions_value_matching_and_reset(example, check):
    e = example
    boundary = check.common.arrays(e["output"]/"boundary.npz")
    bodies = study.make_bodies(boundary, e["tissue"], e["cfg"])
    check.common.close(study.geometry(bodies, boundary["fresh"]), check.check_bodies(boundary, bodies, e["tissue"]))
    for d, shift in (("forward", 4), ("reverse", -4)):
        np.testing.assert_array_equal(bodies[f"{d}_V"], np.roll(boundary["kept_V"], -shift, axis=0))
        assert np.all(bodies[f"{d}_indices"] != np.arange(16))
        for i in range(16):
            mask = ~boundary["fresh"][i]
            np.testing.assert_array_equal(np.sort(bodies[f"{d}_V"][i][mask]), np.sort(bodies[f"{d}shuffled_V"][i][mask]))
    assert np.all(bodies["forward_indices"] != bodies["reverse_indices"])
    for body, (value_source, layout_source) in study.FACTORS.items():
        for i in range(16):
            mask = ~boundary["fresh"][i]
            values = bodies[f"{body}_V"][i][mask]
            expected_values = bodies[f"{value_source}_V"][i][mask]
            expected_layout = bodies[f"{layout_source}_V"][i][mask]
            np.testing.assert_array_equal(np.sort(values), np.sort(expected_values))
            order = np.argsort(expected_layout, kind="stable")
            np.testing.assert_array_equal(values[order], np.sort(expected_values))
    assert not np.array_equal(bodies["forwardvalues_V"], bodies["forward_V"])
    assert not np.array_equal(bodies["reversevalues_V"], bodies["reverse_V"])
    for b in study.BODIES:
        np.testing.assert_array_equal(bodies[f"{b}_V"][boundary["fresh"]], boundary["kept_V"][boundary["fresh"]])
    for state in study.initial_states(boundary, bodies).values():
        assert np.all(state["R"] == 0.)
        np.testing.assert_array_equal(state["ema"], state["V"])
        np.testing.assert_array_equal(state["theta"], boundary["damaged_theta"])


@pytest.mark.parametrize("bad", ("extra", "float", "wrong_replicate", "self", "forward_as_reverse"))
def test_bad_donor_addresses_rejected(example, check, bad):
    boundary = check.common.arrays(example["output"]/"boundary.npz")
    bodies = study.make_bodies(boundary, example["tissue"], example["cfg"])
    if bad == "extra": bodies["reverse_indices"] = np.append(bodies["reverse_indices"], 0)
    elif bad == "float": bodies["reverse_indices"] = bodies["reverse_indices"].astype(float)
    elif bad == "wrong_replicate": bodies["reverse_indices"][0] += 1
    elif bad == "self": bodies["reverse_indices"][0] = 0
    else: bodies["reverse_indices"] = bodies["forward_indices"].copy()
    with pytest.raises(AssertionError):
        check.check_bodies(boundary, bodies, example["tissue"])


def test_directional_observers_know_reverse_and_ties(check):
    trace = np.zeros((2, 16, 6))
    for i in range(16):
        trace[1, i, (i//4-1) % 4] = 1.
    actual = study.observe(trace, 4)
    np.testing.assert_array_equal(actual, check.observer(trace, 4))
    np.testing.assert_array_equal(actual[0, :, 3:6], np.full((16, 3), .25))
    assert np.all(actual[1, :, 5] == 1.) and np.all(actual[1, :, 6] == -1.)
    cfg = replace(study.READOUT_CONFIG, draws=2)
    probabilities = np.repeat(np.eye(4)[(np.arange(16)//4-1) % 4], 2, axis=0)
    raw = dict(probabilities=probabilities)
    expected = check.extra(raw, asdict(cfg))
    check.common.close(study.extra_metrics(raw, cfg), expected)
    assert expected["reverse_accuracy"] == 1. and expected["forward_accuracy"] == 0.


def test_saved_cell_and_full_thousand_updates(example, tmp_path):
    assert len(list(example["output"].iterdir())) == 56
    assert example["checked"]["writing"]["retained_parent_matched"] is True
    full = fixture_cell(tmp_path, study.CONFIG, replace(study.READOUT_CONFIG, draws=2))
    assert full["checked"]["writing"]["recorded_batch_steps"] == 26000
    assert full["checked"]["writing"]["transplanted_records"] == 96
    assert full["checked"]["readout"]["scored_readout_lives"] == 608


WRITING_CORRUPTIONS = ("parent", "before", "damage", "body", "fresh_fill", "reverse_address", "permutation", "native",
    "initial_theta", "initial_R", "reader", "R_recurrence", "theta_trace", "scale", "off_ema", "off_theta", "curve", "stratum",
    "geometry", "writing_score", "writing_rng", "parent_origin", "tissue", "writer_replay")
READOUT_CORRUPTIONS = ("packet", "birth", "readout_R", "readout_theta", "probability", "forward_score", "reverse_score",
    "record_variation", "paired", "wrong_forward", "wrong_reverse", "disabled", "readout_rng", "birth_rng", "origin", "readout_replay")


@pytest.mark.parametrize("kind", (*WRITING_CORRUPTIONS, *READOUT_CORRUPTIONS))
def test_saved_corruption_rejected(example, tmp_path, check, kind):
    e, output = example, tmp_path/"cell"
    shutil.copytree(e["output"], output)
    maps = {
        "parent": ("parent", "V"), "before": ("before", "R"), "damage": ("boundary", "damaged_theta"),
        "body": ("bodies", "reversevalues_V"), "fresh_fill": ("bodies", "forwardvalues_V"), "reverse_address": ("bodies", "reverse_indices"),
        "permutation": ("bodies", "permutations"), "native": ("boundary", "native_theta"),
        "initial_theta": ("recovery_reversevalues_native", "s0_theta"), "initial_R": ("recovery_reversevalues_native", "s0_R"),
        "reader": ("recovery_reversevalues_native", "fixed_reader"), "R_recurrence": ("recovery_reversevalues_native", "reference_trace"),
        "theta_trace": ("recovery_reversevalues_native", "theta_trace"), "scale": ("recovery_reversevalues_native", "projection_scale"),
        "off_ema": ("recovery_reversevalues_native_off", "s1_ema"), "off_theta": ("recovery_reversevalues_native_off", "s16_theta"),
        "curve": ("writing", "curves"), "stratum": ("writing", "strata"), "packet": ("packets", "reversevalues_native"),
        "birth": ("readout_reversevalues_native", "s0_ema"), "readout_R": ("readout_reversevalues_native", "s1_R"),
        "readout_theta": ("readout_reversevalues_native", "s1_theta"), "probability": ("readout_reversevalues_native", "probabilities"),
        "wrong_forward": ("readout_wrong_forward", "s1_ema"), "wrong_reverse": ("readout_wrong_reverse", "s1_ema"),
        "disabled": ("readout_reader_off", "s1_ema")}
    if kind in maps:
        name, key = maps[kind]
        path = output/f"{name}.npz"
        arrays = check.common.arrays(path)
        if kind in ("body", "fresh_fill"):
            fresh = check.common.arrays(output/"boundary.npz")["fresh"]
            pos = np.flatnonzero((fresh if kind == "fresh_fill" else ~fresh).ravel())[0]
            arrays[key].flat[pos] += .1
        elif kind == "theta_trace": arrays[key][2, 0, 5] += .1
        else: arrays[key].flat[0] += 1 if arrays[key].dtype.kind in "iu" else .1
        study.source.base.atomic_npz(path, arrays, tmp_path)
    else:
        path = output/("writing.json" if kind in WRITING_CORRUPTIONS else "readout.json")
        row = json.loads(path.read_text())
        if kind == "geometry": row["geometry"]["reversevalues"]["retained_mean"][0] += .1
        elif kind == "writing_score": row["arms"]["reversevalues_native"]["1"]["V"]["mean"]["reverse_accuracy"] += .1
        elif kind == "writing_rng": row["recovery_rng_final"]["reversevalues_native"] = "0"*64
        elif kind == "parent_origin": row["parent_origin"] = "cached_parent"
        elif kind == "tissue": row["tissue"] = 30040
        elif kind in ("writer_replay", "readout_replay"): row["four_crossover_replays"] = False
        elif kind in ("forward_score", "reverse_score"): row["arms"]["reversevalues_native"][kind.replace("score", "accuracy")] += .1
        elif kind == "record_variation": row["arms"]["reversevalues_native"]["targets"]["reverse"]["record_accuracy"][0] += .1
        elif kind == "paired": row["paired"]["value_effect_native"]["forward_minus_reverse"]["positive"] += .1
        elif kind == "readout_rng": row["rng_final"] = "0"*64
        elif kind == "birth_rng": row["birth_rng_final"] = "0"*64
        elif kind == "origin": row["packet_origin"] = "imported_donor_memory"
        study.strict_json(path, row, tmp_path)
    with pytest.raises(AssertionError):
        if kind in WRITING_CORRUPTIONS: check.check_writing(e["original"], output, e["tissue"], asdict(e["cfg"]))
        else: check.check_readout(e["original"], output, e["tissue"], asdict(e["cfg"]), asdict(e["rcfg"]))


def test_pools_and_six_focal_endpoints(example, check):
    rows, wrows = [], []
    for t in study.TISSUES:
        rows.append(deepcopy(example["records"]["readout"]) | {"tissue": t})
        wrows.append(deepcopy(example["records"]["writing"]) | {"tissue": t})
    pool, wpool = study.pooled(rows), study.writing_pooled(wrows, example["cfg"])
    assert check.check_pool(rows, pool) and check.check_writing_pool(wrows, wpool, asdict(example["cfg"]))
    assert all(m in pool["contrasts"][n] for n, m in study.FOCAL)
    pool["contrasts"]["value_effect_native"]["forward_minus_reverse"]["message_mean"][0] += .1
    with pytest.raises(AssertionError): check.check_pool(rows, pool)
    wpool["contrasts"]["layout_effect_native"]["mean"][1][0][6] += .1
    with pytest.raises(AssertionError): check.check_writing_pool(wrows, wpool, asdict(example["cfg"]))
    with pytest.raises(AssertionError): study.pooled(rows[:-1])
    with pytest.raises(AssertionError): study.writing_pooled(wrows[::-1], example["cfg"])


def test_scientific_source_override_rejected(example, tmp_path):
    with pytest.raises(AssertionError):
        study.execute_cell(tmp_path, study.TISSUES[0], "calibration", tmp_path/"cell", original=example["original"])
    assert not (tmp_path/"cell").exists()
    with pytest.raises(AssertionError):
        study.disposable_source(tmp_path, study.TISSUES[0], tmp_path/"fake")
    assert not (tmp_path/"fake").exists()


def test_rank_transfer_ties_diagonal_and_invalid_inputs():
    values = np.repeat(np.arange(32, dtype=float), 4)[::-1].copy()
    layout = np.repeat(np.arange(16, dtype=float), 8)[::-1].copy()
    moved, order = study.rank_transfer(values, layout)
    expected_order = sorted(range(128), key=lambda i: (layout[i], i))
    assert order.tolist() == expected_order
    np.testing.assert_array_equal(np.sort(moved), np.sort(values))
    np.testing.assert_array_equal(moved[order], np.sort(values))
    diagonal, _ = study.rank_transfer(values, values)
    np.testing.assert_array_equal(diagonal, values)
    for bad in (values[:-1], values.astype(np.float32), np.full(128, np.nan), np.full(128, np.inf)):
        with pytest.raises(AssertionError):
            study.rank_transfer(bad, layout)


@pytest.mark.parametrize("body", ("forwardvalues", "reversevalues"))
def test_cross_layout_and_values_cannot_be_swapped(example, check, body):
    boundary = check.common.arrays(example["output"]/"boundary.npz")
    bodies = study.make_bodies(boundary, example["tissue"], example["cfg"])
    bodies[f"{body}_V"] = bodies[f"{study.FACTORS[body][0]}_V"].copy()
    with pytest.raises(AssertionError):
        check.check_bodies(boundary, bodies, example["tissue"])


@pytest.mark.parametrize("name", ("forward_layout_order", "reverse_layout_order"))
def test_layout_order_is_verified(example, check, name):
    boundary = check.common.arrays(example["output"]/"boundary.npz")
    bodies = study.make_bodies(boundary, example["tissue"], example["cfg"])
    bodies[name][0, :2] = bodies[name][0, :2][::-1]
    with pytest.raises(AssertionError):
        check.check_bodies(boundary, bodies, example["tissue"])


def test_factorial_scaling_and_decomposition():
    scores = {"forward": .7, "forwardvalues": .5, "reversevalues": -.2, "reverse": -.4}
    for reader in study.READERS:
        def value(name):
            return sum(w*scores[a.split("_")[0]] for a, w in study.CONTRASTS[f"{name}_{reader}"].items())
        assert value("value_effect") == pytest.approx(.9)
        assert value("layout_effect") == pytest.approx(.2)
        assert value("value_layout_interaction") == pytest.approx(0.)
        assert value("value_effect")+value("layout_effect") == pytest.approx(scores["forward"]-scores["reverse"])
        assert value("value_effect")-value("layout_effect") == pytest.approx(value("crossed_preference"))


def test_historical_recovery_and_readout_anchors_are_checked(example, check, tmp_path):
    original = tmp_path/"tampered-source"
    shutil.copytree(example["original"], original)
    for stage, file, key in (("writing", "recovery_forward_native", "s1_V"), ("readout", "readout_forward_native", "s1_V")):
        path = original/f"{file}.npz"
        raw = check.common.arrays(path)
        raw[key].flat[0] += .1
        study.source.base.atomic_npz(path, raw, tmp_path)
        with pytest.raises(AssertionError):
            if stage == "writing":
                check.check_writing(original, example["output"], example["tissue"], asdict(example["cfg"]))
            else:
                check.check_readout(original, example["output"], example["tissue"], asdict(example["cfg"]), asdict(example["rcfg"]))


def test_calibration_stops_before_any_parent_writing(tmp_path, monkeypatch):
    run, output = tmp_path/"runs"/study.RUN_ID, tmp_path/"outputs"/study.RUN_ID
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    monkeypatch.setattr(study, "verify", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(study, "preflight", lambda root: [0, 1, 2, 3])
    stages = []
    def cells(root, out, stage):
        stages.append(stage)
        assert stage == "calibration"
        for t in study.TISSUES:
            yield t, (dict(tissue=t, passes=True, gates={"ok": True}, positive_accuracy=.25), dict(tissue=t, passes=True))
    monkeypatch.setattr(study, "cells", cells)
    with pytest.raises(RuntimeError, match="no scientific writing"): study.run_study(tmp_path)
    assert stages == ["calibration"] and (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    assert not list(output.glob("tissue_*"))


def test_detach_never_polls_and_duplicate_launch_rejected(tmp_path, monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify", lambda root: {"benchmark": {"projected_seconds": 2000}})
    calls = []
    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=801080)
    monkeypatch.setattr(study.subprocess, "Popen", popen)
    record = study.detach(tmp_path)
    assert record["polling_owner"] == "user" and record["pid"] == 801080
    assert calls[0][1]["start_new_session"] is True and calls[0][1]["stdin"] is study.subprocess.DEVNULL
    assert (run/"RUN.pid").read_text() == "801080\n"
    with pytest.raises(FileExistsError): study.detach(tmp_path)
    assert len(calls) == 1


def test_long_run_requires_detach_before_work(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "verify", lambda root: {"benchmark": {"must_detach": True}})
    with pytest.raises(RuntimeError, match="detached execution required"): study.run_study(tmp_path)
    assert not (tmp_path/"runs"/study.RUN_ID/"EXECUTION.lock").exists()


def test_immutable_preparation_and_benchmark(tmp_path):
    (tmp_path/"runs"/study.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): study.prepare(tmp_path)
    with pytest.raises(FileExistsError): study.benchmark(tmp_path)


@pytest.mark.parametrize("tamper", ("input", "contract", "timing", "status"))
def test_preparation_freezes_inputs_contract_and_timing(tmp_path, monkeypatch, tamper):
    (tmp_path/"tmp").mkdir()
    source_path = tmp_path/"fixture-input.txt"
    study.atomic_text(source_path, "frozen input\n", tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [source_path])
    monkeypatch.setattr(study, "preflight", lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(study, "retained_panel", lambda root: {"passes": True})
    timing = dict(run_id=study.RUN_ID, passes=True, disposable_tissue=402082, effects_not_reported=True,
                  tissue_seconds=1., projected_seconds=114., must_detach=False,
                  input_sha256={str(source_path): study.sha256_file(source_path)})
    study.strict_json(study.timing_path(tmp_path), timing, tmp_path)
    study.prepare(tmp_path)
    assert study.verify(tmp_path)["tissues"] == list(study.TISSUES)
    run = tmp_path/"runs"/study.RUN_ID
    if tamper == "input": study.atomic_text(source_path, "changed input\n", tmp_path)
    elif tamper == "timing": study.strict_json(study.timing_path(tmp_path), timing | {"projected_seconds": 1.}, tmp_path)
    elif tamper == "status": study.strict_json(run/"STATUS.json", {"status": "RUNNING"}, tmp_path)
    else:
        manifest = json.loads((run/"MANIFEST.json").read_text())
        manifest["donor_steps"] = [1, 1]
        study.strict_json(run/"MANIFEST.json", manifest, tmp_path)
    with pytest.raises(AssertionError): study.verify(tmp_path)


def test_successful_publication(example, tmp_path, check, monkeypatch):
    run, output = tmp_path/"runs"/study.RUN_ID, tmp_path/"outputs"/study.RUN_ID
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    study.strict_json(output/"input_hashes.sha256", {}, tmp_path)
    monkeypatch.setattr(study, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {}})
    monkeypatch.setattr(study, "preflight", lambda root: [0, 1, 2, 3])
    phases = []
    def cells(root, out, stage):
        phases.append(stage)
        for t in study.TISSUES:
            directory = out/f"tissue_{t}"
            if stage == "calibration":
                directory.mkdir()
                for i in range(56): study.strict_json(directory/f"publication_fixture_{i}.json", {}, root)
            row = deepcopy(example["records"][stage]) | {"tissue": t}
            if stage == "calibration": row["positive_accuracy"] = 1.
            if stage == "writing":
                # This test exercises publication only; the full saved cell is tested above.
                row["arms"] = {a: {str(s): deepcopy(row["arms"][a]["0"]) for s in study.CONFIG.times} for a in study.MAIN}
            yield t, (row, dict(tissue=t, passes=True))
    monkeypatch.setattr(study, "cells", cells)
    assert study.run_study(tmp_path) == 0 and phases == list(study.STAGES)
    result = json.loads((output/"analysis.json").read_text())
    assert check.check_pool(result["results"], result["pooled"])
    assert check.check_writing_pool(result["writing_results"], result["writing_pooled"])
    assert check.common.manifest_check(output/"output_hashes.sha256") == 899
    assert (run/"COMPLETE").exists() and not (run/"FAILED").exists()
