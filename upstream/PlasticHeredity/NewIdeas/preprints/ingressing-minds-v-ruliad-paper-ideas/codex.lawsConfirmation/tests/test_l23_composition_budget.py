from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l23_composition_budget as s


@pytest.fixture(scope="module")
def check():
    return s.checker()


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    root = tmp_path_factory.mktemp("l23-budget-cell")
    cfg = replace(s.CONFIG, draws=2, sweeps=4, times=(0, 1, 4))
    directory = root/"cell"
    records, verified = {}, {}
    for stage in ("calibration", "panel"):
        records[stage], verified[stage] = s.execute_cell(root, 402083, stage, directory, cfg)
    return dict(root=root, directory=directory, config=cfg, records=records, verified=verified)


def test_registry_and_counts(check):
    c = s.contract()
    assert s.TISSUES == check.TISSUES == tuple(range(31000, 31016))
    for name in ("PAIRS", "READERS", "MEASURED", "BUDGETS", "NORMS", "METRICS", "CASES", "CAL_CASES", "GROUPS"):
        assert getattr(s, name) == getattr(check, name)
    check.close(asdict(s.CONFIG), check.CFG)
    check.close(s.TERMS, check.terms())
    assert len(s.CASES) == 252 and len(s.TERMS) == 33 and len(s.FOCAL)*2 == 8
    assert c["main_lives"] == 12*3*7*2*8*16 == 64512
    assert c["calibration_lives"] == 1024 and c["historical_lives"] == 16
    assert c["total_executed_lives"] == 2*(c["main_lives"]+c["calibration_lives"]+c["historical_lives"])
    assert c["output_hashes"] == 16*7+5 == 117
    assert c["scientific_training_lives"] == c["learned_writing_lives"] == c["law_verdict_changes"] == 0
    assert set(s.GROUPS["eligible"]) | set(s.GROUPS["excluded"]) == set(s.PAIRS)
    assert len(s.GROUPS["excluded"]) == 10 and not c["fresh_prototypes"]


def test_source_instruments_offsets_and_no_filter(example, check):
    inst = check.arrays(example["directory"]/"instruments.npz")
    check.check_instruments(inst, 402083)
    theta, means, ids = s.case_inputs(inst, 0, s.CASES)
    assert theta.shape == (252, 16, 16) and np.any(means < 0) and np.any(means > 0)
    for p in s.PAIRS:
        for reader in s.READERS:
            ix = [s.CASES.index((p, b, reader)) for b in s.BUDGETS]
            assert means[ix[0]] == 0 and means[ix[1]] == -means[ix[2]]
            for i in ix:
                np.testing.assert_array_equal(theta[i], theta[ix[0]])
        target = inst["targets"][s.PAIRS.index(p)]
        assert set(np.unique(target)) == {-1., 1.}
    assert np.any(abs(inst["packets"][0, :, 0].std(axis=(-2, -1))-.15) > 1e-5)
    assert len(list(example["directory"].iterdir())) == 7
    assert example["verified"]["panel"]["calibration_anchors"] == 8


@pytest.mark.parametrize("kind", ("form", "mask", "target", "target_mean", "permutation", "splice", "normalized", "wrong", "off"))
def test_instrument_corruption_rejected(example, check, kind):
    inst = check.arrays(example["directory"]/"instruments.npz")
    if kind in ("form", "target", "target_mean", "permutation"):
        key = {"form": "forms", "target": "targets", "target_mean": "target_means", "permutation": "permutations"}[kind]
        inst[key].flat[0] += 1
    elif kind == "mask":
        inst["left"].flat[0] = False
    else:
        inst["packets"][0, 0, s.READERS.index(kind), 0, 0] += .1
    with pytest.raises(AssertionError):
        check.check_instruments(inst, 402083)


def test_metrics_ties_and_future_not_batch_decoding(check):
    scores = np.array([[[1., 0., 0., 0.], [0., 1., 0., 0.]],
                       [[0., 1., 0., 0.], [1., 0., 0., 0.]],
                       [[.5, .5, .5, .5], [.5, .5, .5, .5]]])
    probs = s.probabilities(scores)
    actual = s.metrics(scores, probs, "AB")
    np.testing.assert_array_equal(actual, check.paired_metrics(scores, probs, "AB"))
    np.testing.assert_array_equal(actual[:, 0], [1., 0., .25])
    np.testing.assert_array_equal(actual[:, 1], [1., 0., .0625])
    np.testing.assert_array_equal(actual[:, 3], [1., -1., 0.])
    assert actual[:, 0].mean() != s.metrics(scores.mean(axis=0)[None], s.probabilities(scores.mean(axis=0)[None]), "AB")[0, 0]


def test_off_reader_is_not_assumed_chance(example, check):
    raw = check.arrays(example["directory"]/"panel_0.npz")
    rows = example["records"]["panel"]["metrics"]
    assert not np.allclose(np.array(rows)[0, :, :, s.READERS.index("off"), :, 0], .25)
    check.close(rows[0], check.recompute_metrics(raw).tolist())


def test_batch_instrument_matches_original_three_dimensional_source():
    cfg = replace(s.CONFIG, draws=2, sweeps=8, times=(0, 1, 8))
    ctx = s.context(402083, cfg)
    inst = s.instruments(ctx)
    cases = (("CD", "matched", "normalized"), ("AD", "opposite", "splice"), ("AB", "neutral", "off"))
    raw, _ = s.simulate(ctx, inst, 0, cases)
    for j in range(len(cases)):
        rng = s.seeded(402083, "expression")
        rng.standard_normal((2, 16, 16))  # Match birth consumption; V0 supplied explicitly.
        v = ctx["api"]["express"](ctx["api"]["AlphabetConfig"](), ctx["tissue"], raw["theta"][j],
            rng, sweeps=cfg.sweeps, V0=raw["s0_V"][j], futures=2)
        np.testing.assert_array_equal(raw["s8_V"][j], v)


def test_reference_cannot_feed_back_in_frozen_expression():
    ctx = s.context(402083)
    a = ctx["api"]
    v = s.seeded(402083, "test").standard_normal((2, 16, 16))*.2
    th = a["write_form"](ctx["forms"][0], .15, 1.5)
    outputs = [a["blueprint_step"](v.copy(), v.copy(), r, th, ctx["tissue"], ctx["ladder"], ctx["bp"],
                                  "T", s.seeded(402083, "step"), c_m=0.) for r in (v.copy(), np.full_like(v, 100.))]
    for k in (0, 1):
        np.testing.assert_array_equal(outputs[0][k], outputs[1][k])
    assert not np.array_equal(outputs[0][2], outputs[1][2])


RAW_CORRUPTIONS = ("theta", "case_ids", "offsets", "birth_noise", "s0_V", "s0_ema", "s0_R", "s1_V", "s4_ema", "s4_R",
                   "scores", "probabilities", "mean", "rms", "boundary_fraction")


@pytest.mark.parametrize("kind", RAW_CORRUPTIONS)
def test_raw_corruption_rejected(example, check, kind):
    raw = check.arrays(example["directory"]/"panel_0.npz")
    inst = check.arrays(example["directory"]/"instruments.npz")
    raw[kind].flat[0] += 1 if kind == "case_ids" else .1
    with pytest.raises(AssertionError):
        check.check_raw(raw, inst, 402083, 0, s.CASES, asdict(example["config"]))


@pytest.mark.parametrize("kind", ("tissue", "config", "rng", "metrics", "passes", "calibration_anchor"))
def test_saved_panel_metadata_and_anchor_corruption(example, check, tmp_path, kind):
    d = tmp_path/"cell"
    shutil.copytree(example["directory"], d)
    record = deepcopy(example["records"]["panel"])
    if kind == "tissue": record["tissue"] = 31000
    elif kind == "config": record["config"]["draws"] = 8
    elif kind == "rng": record["rng_final"][0] = "0"*64
    elif kind == "metrics": record["metrics"][0][0][0][0][0][0] += .1
    elif kind == "passes": record["passes"] = False
    else:
        raw = check.arrays(d/"calibration_0.npz")
        raw["s1_ema"].flat[0] += .1
        s.base.atomic_npz(d/"calibration_0.npz", raw, tmp_path)
    s.strict_json(d/"panel.json", record, tmp_path)
    with pytest.raises(AssertionError):
        check.check_panel(d, 402083, asdict(example["config"]))


def test_pool_and_all_contrast_strata(example, check):
    row = example["records"]["panel"]
    summary = s.pooled([row])
    assert check.check_pool([row], summary)
    for name in ("budget_gain_normalized", "budget_direction_normalized", "budget_gain_specificity_off"):
        for n in range(2):
            assert summary["contrasts"][name][n]["eligible"]["half_accuracy"]["mean"] == 0
    for kind in ("arm", "mean", "tissue", "pair", "paired", "missing"):
        bad = deepcopy(summary)
        cell = bad["contrasts"][s.FOCAL[0]][0]["excluded"]["half_accuracy"]
        if kind == "arm": bad["arm_means"][0][0][0][0][0] += .1
        elif kind == "mean": cell["mean"] += .1
        elif kind == "tissue": cell["tissue_differences"][0] += .1
        elif kind == "pair": cell["pair_mean"][0] += .1
        elif kind == "paired": cell["paired_tied"] += .1
        else: del bad["contrasts"][s.FOCAL[0]][0]["eligible"]
        with pytest.raises(AssertionError):
            check.check_pool([row], bad)


def test_historical_replay_and_fit(tmp_path):
    record, verified = s.legacy(tmp_path, tmp_path)
    assert verified["fit_matches_retained"] and verified["original_expressions"] == 4
    assert not verified["discarded_null_recreated"]
    assert record["fits"][0]["a_own"] == pytest.approx(.365234375)


def test_pool_preserves_tissue_axis_with_unequal_pair_effects(check):
    data = np.zeros((3, 2, 12, 3, 8, 2, 5))
    for t in range(3):
        for p in range(12):
            data[t, :, p, 0, 1, :, 0] = (t+1)*(p+1)/100
    rows = [dict(tissue=402083+t, metrics=data[t].tolist()) for t in range(3)]
    pooled = s.pooled(rows)
    assert check.check_pool(rows, pooled)
    cell = pooled["contrasts"]["expression_gain_neutral"][0]["excluded"]["half_accuracy"]
    ix = [s.PAIRS.index(p) for p in s.GROUPS["excluded"]]
    expected = [sum((t+1)*(p+1)/100 for p in ix)/len(ix) for t in range(3)]
    np.testing.assert_allclose(cell["tissue_differences"], expected, rtol=0., atol=1e-12)
    assert cell["positive"] == 3 and len(cell["tissue_differences"]) == 3


def test_full_three_hundred_update_cell(tmp_path):
    cfg = replace(s.CONFIG, draws=2)
    for stage in ("calibration", "panel"):
        _, verified = s.execute_cell(tmp_path, 402083, stage, tmp_path/"full", cfg)
        assert verified["passes"] is True
    assert verified["replayed_expression_lives"] == 1008


def test_positive_control_gate_has_no_block_filter():
    good = [dict(accuracy=[[.9, .25], [.9, .25]]) for _ in s.TISSUES]
    assert s.qualification(good)
    for bad_values in ((.25, .9), (.7, .7)):
        bad = deepcopy(good)
        if bad_values[0] == .25: bad[0]["accuracy"][0][0] = .25
        else:
            for r in bad: r["accuracy"][0][0] = .7
        assert not s.qualification(bad)
    bad = deepcopy(good)
    for r in bad: r["accuracy"][1][1] = .95
    assert not s.qualification(bad)


def test_failed_calibration_stops_before_main(tmp_path, monkeypatch):
    run, out = tmp_path/"runs"/s.RUN_ID, tmp_path/"outputs"/s.RUN_ID
    run.mkdir(parents=True); out.mkdir(parents=True)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "legacy", lambda root, directory: ({}, {}))
    stages = []
    def cells(root, directory, stage):
        stages.append(stage)
        assert stage == "calibration"
        for t in s.TISSUES:
            yield t, (dict(tissue=t, passes=True, accuracy=[[.25, .25], [.25, .25]]), dict(tissue=t, passes=True))
    monkeypatch.setattr(s, "cells", cells)
    with pytest.raises(RuntimeError, match="positive-control"):
        s.run_study(tmp_path)
    assert stages == ["calibration"] and (run/"FAILED").is_file() and not (run/"COMPLETE").exists()


def test_manifest_guard_refuses_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    source = tmp_path/"frozen.txt"
    s.atomic_text(source, "fixed", tmp_path)
    monkeypatch.setattr(s, "input_paths", lambda root: [source])
    timing = dict(run_id=s.RUN_ID, passes=True, effects_not_reported=True, disposable_tissue=402084,
                  tissue_seconds=30., projected_seconds=840., must_detach=True, input_sha256={str(source): s.sha256_file(source)})
    s.strict_json(s.timing_path(tmp_path), timing, tmp_path)
    manifest = s.prepare(tmp_path)
    assert s.verify(tmp_path)["hash_contract"] == manifest["hash_contract"]
    with pytest.raises(FileExistsError): s.prepare(tmp_path)
    with pytest.raises(RuntimeError, match="detached"): s.run_study(tmp_path)
    s.atomic_text(source, "changed", tmp_path)
    with pytest.raises(AssertionError): s.verify(tmp_path)


def test_detach_returns_without_polling(tmp_path, monkeypatch):
    run = tmp_path/"runs"/s.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"projected_seconds": 900.}})
    class Process:
        pid = 12345
        def poll(self): raise AssertionError("must not poll")
        def wait(self): raise AssertionError("must not wait")
    def popen(args, **kwargs):
        assert kwargs["start_new_session"] and kwargs["stdin"] == s.subprocess.DEVNULL
        assert args[-1] == "--run"
        return Process()
    monkeypatch.setattr(s.subprocess, "Popen", popen)
    record = s.detach(tmp_path)
    assert record["pid"] == 12345 and record["polling_owner"] == "user"
    assert (run/"LAUNCH.lock").is_dir() and (run/"RUN.pid").read_text() == "12345\n"
    with pytest.raises(FileExistsError): s.detach(tmp_path)


def test_input_closure_and_output_isolation(tmp_path):
    paths = s.input_paths(tmp_path)
    assert paths and all(p.is_file() and p.is_absolute() for p in paths)
    for name in ("l23_audit.py", "artifact_audit.py", "eca_math.py", "stats.py", "io.py", "engine.py", "pipeline.py", "composition.json"):
        assert any(p.name == name for p in paths)
    with pytest.raises(ValueError): s.strict_json(tmp_path.parent/"escaped.json", {}, tmp_path)
    with pytest.raises(ValueError): s.execute_cell(tmp_path, 999, "panel", tmp_path/"not-created")
    assert not (tmp_path/"not-created").exists()


def test_scoped_publication_file_count(example, tmp_path, monkeypatch):
    run, out = tmp_path/"runs"/s.RUN_ID, tmp_path/"outputs"/s.RUN_ID
    run.mkdir(parents=True); out.mkdir(parents=True)
    s.atomic_text(out/"input_hashes.sha256", "", tmp_path)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {}})
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "qualification", lambda rows: True)  # Disposable short-cell fixture only.
    def legacy(root, directory):
        s.base.atomic_npz(directory/"historical.npz", {"fixture": np.zeros(1)}, root)
        s.strict_json(directory/"historical.json", {"fixture": True}, root)
        return {}, {"passes": True}
    def cells(root, directory, stage):
        for t in s.TISSUES:
            d = directory/f"tissue_{t}"
            if stage == "calibration": shutil.copytree(example["directory"], d)
            row = deepcopy(example["records"][stage]); row["tissue"] = t
            yield t, (row, {"passes": True, "tissue": t})
    monkeypatch.setattr(s, "legacy", legacy)
    monkeypatch.setattr(s, "cells", cells)
    assert s.run_study(tmp_path) == 0
    assert s.checker().check_hashes(out/"output_hashes.sha256") == 117
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
