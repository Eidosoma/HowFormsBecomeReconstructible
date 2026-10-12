from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from laws_confirmation import l23_layout_transfer as s


@pytest.fixture(scope="module")
def check():
    return s.checker()


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    root = tmp_path_factory.mktemp("l23-layout-cell")
    cfg = replace(s.CONFIG, draws=2, sweeps=4, times=(0, 1, 4))
    directory = root/"cell"
    records, verified = {}, {}
    for stage in ("calibration", "panel"):
        records[stage], verified[stage] = s.execute_cell(root, 402085, stage, directory, cfg)
    return dict(root=root, directory=directory, config=cfg, records=records, verified=verified)


def test_contract_and_counts(check):
    c = s.contract()
    for name in ("TISSUES", "DISPOSABLES", "LAYOUTS", "NORMS", "PAIRS", "BUDGETS", "READERS", "MEASURED", "METRICS", "CASES", "CAL_CASES", "GROUPS"):
        assert getattr(s, name) == getattr(check, name)
    check.close(asdict(s.CONFIG), check.CFG)
    check.close(s.TERMS, check.terms())
    assert len(s.CASES) == 252 and len(s.TERMS) == 33 and len(s.METRICS) == 6
    assert c["main_lives"] == 3*12*3*7*2*8*16 == 193536
    assert c["total_executed_lives"] == 2*(193536+1024+16) == 389152
    assert c["output_hashes"] == 16*11+5 == 181
    assert c["focal_endpoints"] == len(s.FOCAL)*len(s.FOCAL_METRICS)*2 == 16
    assert c["scientific_training_lives"] == c["learned_writing_lives"] == c["law_verdict_changes"] == 0
    assert c["engineered_readdressing"] and not c["learned_layout_invariance"] and not c["fresh_prototypes"]


def test_bijective_layouts_exact_contents_and_common_budget(check):
    ctx = s.old.context(402085)
    inst = s.instruments(ctx)
    assert check.check_instruments(inst, 402085) == [32, 32, 128]
    for g in range(3):
        local = s.layout_instrument(inst, g)
        assert all(local[k].flags.c_contiguous for k in ("forms", "left", "targets", "packets"))
        np.testing.assert_array_equal(local["target_means"], inst["target_means"])
        for ni in range(2):
            theta, offset, ids = s.old.case_inputs(local, ni, s.CASES)
            original, baseline_offset, _ = s.old.case_inputs(inst, ni, s.CASES)
            np.testing.assert_array_equal(offset, baseline_offset)
            np.testing.assert_array_equal(np.sort(theta.reshape(252, 256), axis=1), np.sort(original.reshape(252, 256), axis=1))
            for pi in range(12):
                rows = ids[:, 0] == pi
                assert np.unique(offset[rows]).size == (1 if pi in (0, 3) else 3)
        scores = s.old.half_scores(local["targets"], local["forms"], local["left"])
        for pi, pair in enumerate(s.PAIRS):
            assert scores[pi, 0, ord(pair[0])-65] == scores[pi, 1, ord(pair[1])-65] == 1


@pytest.mark.parametrize("kind", ("map", "map_swap", "map_type", "mask", "form", "target", "mean", "packet", "extra"))
def test_instrument_corruption_rejected(check, kind):
    inst = s.instruments(s.old.context(402085))
    if kind == "map": inst["layout_maps"][2, 0] += 1
    elif kind == "map_swap": inst["layout_maps"][[1, 2]] = inst["layout_maps"][[2, 1]]
    elif kind == "map_type": inst["layout_maps"] = inst["layout_maps"].astype(float)
    elif kind == "mask": inst["left"][0, 0] = False
    elif kind == "form": inst["forms"].flat[0] *= -1
    elif kind == "target": inst["targets"].flat[0] *= -1
    elif kind == "mean": inst["target_means"][0] += .1
    elif kind == "packet": inst["packets"].flat[0] += .1
    else: inst["undeclared"] = np.zeros(1)
    with pytest.raises(AssertionError): check.check_instruments(inst, 402085)


def test_centered_alignment_not_density_or_winner(check):
    ctx = s.old.context(402085)
    inst = s.instruments(ctx)
    v = s.seeded(402085, "test-correlation").normal(size=(3, 2, 16, 16))
    for g in range(3):
        local = s.layout_instrument(inst, g)
        z = s.transport(v, inst["layout_maps"][g])
        actual = s.centered_alignment(z, local["forms"], local["left"])
        np.testing.assert_allclose(actual, check.alignment_of(z, local["forms"], local["left"]), rtol=0, atol=1e-12)
        np.testing.assert_allclose(actual, s.centered_alignment(z+.4, local["forms"], local["left"]), rtol=0, atol=1e-12)
        assert not np.array_equal(s.old.half_scores(z, local["forms"], local["left"]), s.old.half_scores(z+.4, local["forms"], local["left"]))
        assert not s.centered_alignment(np.ones_like(z), local["forms"], local["left"]).any()


def test_exact_d081_canonical_bridge_at_three_hundred_updates():
    cfg = replace(s.CONFIG, draws=2)
    ctx = s.old.context(402085, cfg)
    inst = s.instruments(ctx)
    cases = (("DC", "matched", "normalized"), ("CD", "neutral", "scrambled"), ("AB", "neutral", "off"))
    for ni in range(2):
        actual, digest = s.simulate(ctx, inst, 0, ni, cases, tag=s.old.TAG)
        expected, old_digest = s.old.simulate(ctx, inst, ni, cases)
        assert digest == old_digest
        for key in expected: np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("geometry", (0, 1, 2))
def test_batched_source_matches_three_dimensional_source(geometry):
    cfg = replace(s.CONFIG, draws=2, sweeps=8, times=(0, 1, 8))
    ctx = s.old.context(402085, cfg); inst = s.instruments(ctx)
    cases = (("DC", "matched", "normalized"), ("AD", "opposite", "splice"), ("AB", "neutral", "off"))
    raw, _ = s.simulate(ctx, inst, geometry, 0, cases)
    for i in range(3):
        generator = s.seeded(402085, "expression")
        generator.standard_normal((2, 16, 16))
        class Noise:
            def standard_normal(self, shape):
                assert tuple(shape) == (2, 16, 16)
                return s.transport(generator.standard_normal(shape), inst["layout_maps"][geometry])
        result = ctx["api"]["express"](ctx["api"]["AlphabetConfig"](), ctx["tissue"], raw["theta"][i],
            Noise(), sweeps=8, V0=raw["s0_V"][i], futures=2)
        np.testing.assert_array_equal(result, raw["s8_V"][i])


@pytest.mark.parametrize("key", ("theta", "case_ids", "offsets", "birth_noise", "s0_V", "s0_ema", "s0_R", "s1_V", "s4_ema", "s4_R", "mean", "rms", "boundary_fraction", "scores", "probabilities", "alignment"))
def test_raw_corruption_rejected(example, check, key):
    inst = check.arrays(example["directory"]/"instruments.npz")
    raw = check.arrays(example["directory"]/"panel_2_0.npz")
    raw[key].flat[0] += 1 if key == "case_ids" else .1
    with pytest.raises(AssertionError): check.check_raw(raw, inst, 402085, 2, 0, s.CASES, asdict(example["config"]))


def test_virtual_isolation_ties_and_metrics(example, check):
    raw = check.arrays(example["directory"]/"panel_2_0.npz")
    expected = check.recompute_metrics(raw)
    np.testing.assert_allclose(s.panel_metrics(raw), expected, rtol=0, atol=1e-12)
    scores = np.full((2, 2, 4), .5)
    probs = s.old.probabilities(scores)
    actual = s.metrics(scores, probs, np.zeros_like(scores), "AB")
    np.testing.assert_array_equal(actual[:, 0], .25)
    np.testing.assert_array_equal(actual[:, 1], .0625)
    np.testing.assert_array_equal(actual[:, 5], 0)
    assert len(list(example["directory"].iterdir())) == 11
    assert example["verified"]["panel"]["isometry_probability_arrays_equal"]


def test_wrong_noise_or_geometry_rejected(example, check):
    inst = check.arrays(example["directory"]/"instruments.npz")
    raw = check.arrays(example["directory"]/"panel_1_0.npz")
    for geometry in (0, 2):
        with pytest.raises(AssertionError): check.check_raw(raw, inst, 402085, geometry, 0, s.CASES, asdict(example["config"]))
    baseline = check.arrays(example["directory"]/"panel_0_0.npz")
    raw["s4_V"].flat[0] += 1e-5
    with pytest.raises(AssertionError): check.check_isometry(raw, baseline, inst["layout_maps"][1], asdict(example["config"]))


def test_pooled_all_geometries_and_unequal_tissue_axes(check):
    data = np.zeros((3, 3, 2, 12, 3, 8, 2, 6))
    for t in range(3):
        for g in range(3):
            for p in range(12):
                data[t, g, :, p, 1, 1, :, :] = (t+1)*(g+1)*(p+1)/1000
    rows = [dict(tissue=402085+t, metrics=data[t].tolist()) for t in range(3)]
    summary = s.pooled(rows)
    assert check.check_pool(rows, summary)
    for ni in range(2):
        cell = summary["minus_left_right"]["checker4"]["contrasts"]["composition_cost_matched"][ni]["all"]["own_centered_alignment"]
        np.testing.assert_allclose(cell["tissue_differences"], [(t+1)*2*6.5/1000 for t in range(3)], rtol=0, atol=1e-12)
        assert cell["positive"] == 3
    for kind in ("arm", "mean", "block", "pair", "paired", "missing"):
        bad = deepcopy(summary)
        cell = bad["minus_left_right"]["checker4"]["contrasts"]["composition_cost_matched"][0]["all"]["own_centered_alignment"]
        if kind == "arm": bad["by_layout"]["checker4"]["arm_means"][0][0][0][0][5] += .1
        elif kind == "mean": cell["mean"] += .1
        elif kind == "block": cell["tissue_differences"][0] += .1
        elif kind == "pair": cell["pair_mean"][0] += .1
        elif kind == "paired": cell["paired_tied"] += .1
        else: del bad["by_layout"]["above_below"]
        with pytest.raises(AssertionError): check.check_pool(rows, bad)


@pytest.mark.parametrize("kind", ("tissue", "config", "rng", "metrics", "passes", "calibration"))
def test_saved_metadata_corruption(example, check, tmp_path, kind):
    d = tmp_path/"cell"; shutil.copytree(example["directory"], d)
    record = deepcopy(example["records"]["panel"])
    if kind == "tissue": record["tissue"] = 31016
    elif kind == "config": record["config"]["draws"] = 8
    elif kind == "rng": record["rng_final"][2][0] = "0"*64
    elif kind == "metrics": record["metrics"][2][0][0][0][0][0][5] += .1
    elif kind == "passes": record["passes"] = False
    else:
        raw = check.arrays(d/"calibration_0.npz");raw["s1_ema"].flat[0] += .1
        s.base.atomic_npz(d/"calibration_0.npz", raw, tmp_path)
    s.strict_json(d/"panel.json", record, tmp_path)
    with pytest.raises(AssertionError): check.check_panel(d, 402085, asdict(example["config"]))


def test_full_three_hundred_update_cell(tmp_path):
    cfg = replace(s.CONFIG, draws=2)
    for stage in ("calibration", "panel"):
        _, verified = s.execute_cell(tmp_path, 402085, stage, tmp_path/"full", cfg)
        assert verified["passes"] is True
    assert verified["isometry_max_abs_state_difference"] < 1e-10
    assert verified["replayed_expression_lives"] == 3024


def test_calibration_failure_stops_panel(tmp_path, monkeypatch):
    run = tmp_path/"runs"/s.RUN_ID;run.mkdir(parents=True)
    (tmp_path/"outputs"/s.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "legacy", lambda root, directory: ({}, {}))
    stages = []
    def cells(root, out, stage):
        stages.append(stage)
        for t in s.TISSUES:
            yield t, (dict(tissue=t, passes=True, accuracy=[[.25, .25], [.25, .25]]), dict(tissue=t, passes=True))
    monkeypatch.setattr(s, "cells", cells)
    with pytest.raises(RuntimeError, match="positive-control"): s.run_study(tmp_path)
    assert stages == ["calibration"] and (run/"FAILED").exists() and not (run/"COMPLETE").exists()


def test_freeze_detachment_and_no_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "provenance", lambda root: None)
    source = tmp_path/"frozen.txt";s.atomic_text(source, "fixed", tmp_path)
    monkeypatch.setattr(s, "input_paths", lambda root: [source])
    timing = dict(run_id=s.RUN_ID, passes=True, effects_not_reported=True, disposable_tissue=402086,
        tissue_seconds=30., cell_bytes=1, projected_seconds=840., must_detach=True, input_sha256={str(source): s.sha256_file(source)})
    s.strict_json(s.timing_path(tmp_path), timing, tmp_path)
    manifest = s.prepare(tmp_path)
    assert s.verify(tmp_path)["hash_contract"] == manifest["hash_contract"]
    with pytest.raises(FileExistsError): s.prepare(tmp_path)
    with pytest.raises(RuntimeError, match="detached"): s.run_study(tmp_path)
    s.atomic_text(source, "changed", tmp_path)
    with pytest.raises(AssertionError): s.verify(tmp_path)


def test_detach_never_polls(tmp_path, monkeypatch):
    run = tmp_path/"runs"/s.RUN_ID;run.mkdir(parents=True)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"projected_seconds": 900.}})
    class Process:
        pid = 54321
        def poll(self): raise AssertionError("must not poll")
        def wait(self): raise AssertionError("must not wait")
    def popen(args, **kwargs):
        assert args[2] == "laws_confirmation.l23_layout_transfer" and args[-1] == "--run"
        assert kwargs["start_new_session"] and kwargs["stdin"] == s.subprocess.DEVNULL
        return Process()
    monkeypatch.setattr(s.subprocess, "Popen", popen)
    assert s.detach(tmp_path)["polling_owner"] == "user"
    with pytest.raises(FileExistsError): s.detach(tmp_path)


@pytest.mark.parametrize("cell_bytes", (-1, 10**12))
def test_storage_forecast_refuses_before_creating_run(tmp_path, monkeypatch, cell_bytes):
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "provenance", lambda root: None)
    s.strict_json(s.timing_path(tmp_path), dict(cell_bytes=cell_bytes), tmp_path)
    with pytest.raises((AssertionError, RuntimeError)):
        s.prepare(tmp_path)
    assert not (tmp_path/"runs"/s.RUN_ID).exists()
    assert not (tmp_path/"outputs"/s.RUN_ID).exists()


def test_publication_count_without_scientific_rerun(example, tmp_path, monkeypatch):
    run, out = tmp_path/"runs"/s.RUN_ID, tmp_path/"outputs"/s.RUN_ID
    run.mkdir(parents=True);out.mkdir(parents=True)
    s.atomic_text(out/"input_hashes.sha256", "", tmp_path)
    monkeypatch.setattr(s, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {}})
    monkeypatch.setattr(s, "preflight", lambda root: [0])
    monkeypatch.setattr(s, "qualification", lambda rows: True)
    def legacy(root, directory):
        s.base.atomic_npz(directory/"historical.npz", {"fixture": np.zeros(1)}, root)
        s.strict_json(directory/"historical.json", {"fixture": True}, root)
        return {}, {"passes": True}
    def cells(root, directory, stage):
        for t in s.TISSUES:
            if stage == "calibration": shutil.copytree(example["directory"], directory/f"tissue_{t}")
            row = deepcopy(example["records"][stage]);row["tissue"] = t
            yield t, (row, {"passes": True, "tissue": t})
    monkeypatch.setattr(s, "legacy", legacy);monkeypatch.setattr(s, "cells", cells)
    assert s.run_study(tmp_path) == 0
    assert s.checker().check_hashes(out/"output_hashes.sha256") == 181
    assert (run/"COMPLETE").exists() and not (run/"FAILED").exists()


def test_input_closure_and_output_isolation(tmp_path):
    root = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation")
    paths = s.input_paths(root)
    assert all(p.is_absolute() and p.is_file() for p in paths)
    assert any(p.name == "traces.npz" for p in paths)
    assert any(p.name == "l23_composition_budget.py" for p in paths)
    with pytest.raises(ValueError): s.strict_json(tmp_path.parent/"escaped.json", {}, tmp_path)
    with pytest.raises(ValueError): s.execute_cell(tmp_path, 999, "panel", tmp_path/"not-created")
    assert not (tmp_path/"not-created").exists()
