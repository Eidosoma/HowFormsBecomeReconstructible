from copy import deepcopy
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_early_signal_loss as study


def synthetic(write=True, hold=False):
    codes = study.checker().source.common.codebook()
    own = np.repeat(codes, 4, axis=0)
    donor = np.roll(own, -4, axis=0)
    extra = np.concatenate((codes, codes[[0, 2]]))
    theta, r = .3*own, np.zeros_like(own)
    body = donor.copy()
    raw, bt, rt, tt, targets, scales = {}, [], [], [], [], []
    def project(field, axes):
        return np.einsum("whk,ahk->wa", field, axes)/256
    for s in range(1001):
        if s:
            body = (.8*donor if s <= 10 else .6*own) + .01*np.sin(s)
            if not hold:
                r = .998*r+.002*body
            target = np.tanh(r)
            target -= target.mean(axis=(1, 2), keepdims=True)
            if write:
                pre = .999*theta+.001*target
                pre -= pre.mean(axis=(1, 2), keepdims=True)
                scale = .3/pre.std(axis=(1, 2))
                theta = pre*scale[:, None, None]
            else:
                scale = np.ones(16)
            targets.append(project(target, extra))
            scales.append(scale)
        bt.append(project(body, codes))
        rt.append(project(r, codes))
        tt.append(project(theta, extra))
        if s in study.STEPS:
            raw.update({f"s{s}_{k}": v.copy() for k, v in dict(V=body, ema=body, R=r, theta=theta).items()})
    raw.update(body_trace=np.array(bt), reference_trace=np.array(rt), theta_trace=np.array(tt),
               target_trace=np.array(targets), projection_scale=np.array(scales))
    return raw


@pytest.fixture(scope="module")
def example():
    variants = {(True, False): synthetic(), (False, False): synthetic(False), (True, True): synthetic(True, True)}
    raw = {a: variants[write, hold] for a, (_, _, write, hold) in study.ARMS.items()}
    results = [study.analyze_arm(raw[a], write, hold) for a, (_, _, write, hold) in study.ARMS.items()]
    data = {key: np.stack([r[i] for r in results]) for i, key in enumerate(("curves", "strata", "R_components", "theta_components"))}
    saved = dict(tissue=30040, passes=True, arms=study.describe(data))
    return raw, data, saved


def test_contract_is_outcome_known_without_dynamics():
    c = study.contract()
    assert c["new_simulations"] == c["law_verdict_changes"] == 0
    assert c["workers"] == 1 and c["outcome_known"] is True
    assert c["tissues"] == list(range(30040, 30056)) and len(c["arms"]) == 14
    assert c["bands"] == [[1, 1], [2, 50], [51, 250], [251, 500], [501, 1000]]
    assert "blueprint_step" not in inspect.getsource(study)


def test_observer_labels_ties_and_donor_are_independently_scored():
    rng = np.random.default_rng(13)
    values = rng.normal(size=(7, 16, 6))
    values[0] = 0.
    expected = study.checker().observer(values)
    np.testing.assert_array_equal(study.observers(values), expected)
    assert np.all(expected[0, :, 3:] == .25)
    for invalid in (values[:, :15], np.full_like(values, np.nan)):
        with pytest.raises(ValueError):
            study.observers(invalid)


@pytest.mark.parametrize("mode", ("constant", "early", "late", "reversal", "off"))
def test_forward_components_equal_reverse_products(mode):
    n, bands, ends = 8, ((1, 1), (2, 4), (5, 8)), (4, 8)
    initial = np.array([[.3, -.2], [.1, .4]])
    forcing = np.ones((n, 2, 2))
    if mode == "early":
        forcing[1:] = 0.
    elif mode == "late":
        forcing[:4] = 0.
    elif mode == "reversal":
        forcing[4:] = -1.
    a = np.broadcast_to(np.linspace(.8, 1.01, n)[:, None], (n, 2)).copy()
    b = .1*a
    if mode == "off":
        a[:] = 1.
        b[:] = 0.
    actual = study.components(initial, forcing, a, b, ends, bands)
    expected = study.checker().reverse_parts(initial, forcing, a, b, ends, bands)
    np.testing.assert_allclose(actual, expected, rtol=0., atol=1e-14)
    for j, end in enumerate(ends):
        value = initial.copy()
        for s in range(end):
            value = a[s, :, None]*value+b[s, :, None]*forcing[s]
        np.testing.assert_allclose(actual[j].sum(axis=0), value, rtol=0., atol=1e-14)
    if mode == "off":
        np.testing.assert_array_equal(actual[:, 1:], np.zeros_like(actual[:, 1:]))


@pytest.mark.parametrize("bands", (((1, 2), (2, 8)), ((2, 8),), ((1, 7),)))
def test_windows_cannot_duplicate_or_omit_updates(bands):
    with pytest.raises(ValueError, match="partition"):
        study.components(np.zeros((2, 3)), np.zeros((8, 2, 3)), np.ones((8, 2)), np.ones((8, 2)), (8,), bands)


def test_full_cell_and_pool_pass_independent_check(example):
    raw, data, saved = example
    checked = study.checker().check_cell(raw, data, saved)
    assert checked["recovery_arms"] == 14 and checked["recorded_batch_steps"] == 14000
    assert study.checker().check_pool([data]*16, study.pooled([data]*16))
    with pytest.raises(ValueError):
        study.pooled([data]*15)


@pytest.mark.parametrize("kind", ("curve", "stratum", "component", "summary", "unsaved_body", "scale", "snapshot", "off_ema"))
def test_independent_tamper_rejection(example, kind):
    raw, data, saved = deepcopy(example)
    if kind == "curve":
        data["curves"][0, 2, 0, 0] += .01
    elif kind == "stratum":
        data["strata"][0, 0, 0, 0, 0] += .01
    elif kind == "component":
        data["theta_components"][0, 1, 1, 0, 0] += .01
    elif kind == "summary":
        saved["arms"]["kept_live"]["accounting"]["50"]["R"]["1"]["donor_projection"] += .01
    elif kind == "unsaved_body":
        raw["donor_live"]["body_trace"][2, 0, 0] += .01
    elif kind == "scale":
        raw["donor_live"]["projection_scale"][2, 0] += .01
    elif kind == "snapshot":
        raw["donor_live"]["s50_V"][0, 0, 0] += .1
    else:
        raw["donor_off"]["s50_ema"][0, 0, 0] += .1
    with pytest.raises(AssertionError):
        study.checker().check_cell(raw, data, saved)


def prepared(tmp_path, monkeypatch, detached=False):
    path = tmp_path/"fixture.txt"
    study.atomic_text(path, "frozen fixture", tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [path])
    timing = dict(run_id=study.RUN_ID, passes=True, must_detach=detached, projected_seconds=700 if detached else 60,
                  input_sha256={str(path): study.sha256_file(path)})
    study.strict_json(study.timing_path(tmp_path), timing, tmp_path)
    study.prepare(tmp_path)
    return tmp_path/"runs"/study.RUN_ID


@pytest.mark.parametrize("key,value", (("workers", 5), ("new_simulations", 1), ("endpoints", [1, 1000]), ("direction_tolerance", .01)))
def test_frozen_contract_tampering_rejected(tmp_path, monkeypatch, key, value):
    run = prepared(tmp_path, monkeypatch)
    record = json.loads((run/"MANIFEST.json").read_text())
    record[key] = value
    study.strict_json(run/"MANIFEST.json", record, tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_existing_output_and_changed_input_rejected(tmp_path, monkeypatch):
    prepared(tmp_path, monkeypatch)
    for fn in (study.prepare, study.benchmark):
        with pytest.raises(FileExistsError):
            fn(tmp_path)
    study.atomic_text(tmp_path/"fixture.txt", "changed", tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_detach_required_exclusive_and_never_polled(tmp_path, monkeypatch):
    run = prepared(tmp_path, monkeypatch, True)
    with pytest.raises(RuntimeError, match="detached"):
        study.run_analysis(tmp_path)
    assert not (run/"EXECUTION.lock").exists()
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(study.subprocess, "Popen", launch)
    record = study.detach(tmp_path)
    assert record["polling_owner"] == "user" and record["pid"] == 12345
    assert len(calls) == 1 and calls[0][1]["start_new_session"] is True
    assert "--run" in calls[0][0] and (run/"LAUNCH.lock").is_dir()
    with pytest.raises(FileExistsError):
        study.detach(tmp_path)


def test_failed_run_is_published_and_not_resumed(tmp_path, monkeypatch):
    run = prepared(tmp_path, monkeypatch)
    def fail(*args):
        raise ValueError("fixture analysis failure")
    monkeypatch.setattr(study, "analyze_cell", fail)
    with pytest.raises(ValueError):
        study.run_analysis(tmp_path)
    assert (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    with pytest.raises(AssertionError):
        study.run_analysis(tmp_path)


def test_successful_publication_and_hashes(example, tmp_path, monkeypatch):
    raw, data, saved = example
    run = prepared(tmp_path, monkeypatch)
    checked = study.checker().check_cell(raw, data, saved)
    monkeypatch.setattr(study, "analyze_cell", lambda directory, tissue: (data, saved | {"tissue": tissue}, checked | {"tissue": tissue}))
    assert study.run_analysis(tmp_path) == 0
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    output = tmp_path/"outputs"/study.RUN_ID
    assert study.checker().source.common.manifest_check(output/"output_hashes.sha256") == 35
    result = json.loads((output/"analysis.json").read_text())
    assert result["verified_saved_analysis"] is True and result["new_simulations"] == 0
    with pytest.raises(AssertionError):
        study.run_analysis(tmp_path)


@pytest.mark.parametrize("bad", (float("nan"), np.bool_(True)))
def test_strict_json_does_not_publish_invalid_payload(tmp_path, bad):
    path = tmp_path/"invalid.json"
    with pytest.raises((ValueError, TypeError)):
        study.strict_json(path, {"value": bad}, tmp_path)
    assert not path.exists()


def test_invalid_normalization_rejected():
    raw = synthetic()
    raw["projection_scale"][1, 0] = -1.
    with pytest.raises(ValueError, match="positive"):
        study.analyze_arm(raw, True, False)
