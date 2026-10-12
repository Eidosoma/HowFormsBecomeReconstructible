from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from laws_confirmation import l22_active_form as study
from laws_confirmation import l22_fixed_record_readout as reading


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts/check_l22_active_form_boundary.py"
    spec = importlib.util.spec_from_file_location("d183_independent_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    cfg = replace(study.source.CONFIG, replicates=2, settle=4, imprint=8,
                  sweeps=6, times=(0, 1, 6))
    ctx = study.source.context(study.DISPOSABLE, cfg)
    _, parent = study.source.prepare_parent(ctx)
    kept, _, fresh, damaged = study.source.boundary(ctx, parent)
    result = study.construct(parent["theta"], kept["V"], fresh, damaged, study.DISPOSABLE, 2)
    return dict(ctx=ctx, parent=parent, kept=kept["V"], fresh=fresh,
                residual=damaged, result=result)


def test_fixed_scope_and_involution():
    assert study.DEVELOPMENT == tuple(range(30056, 30072))
    assert study.DISPOSABLE not in study.DEVELOPMENT
    assert study.PAIRS == ((0, 2), (1, 3))
    p = study.partners(4)
    np.testing.assert_array_equal(p[p], np.arange(16))
    assert np.all(p != np.arange(16)) and np.all(p % 4 == np.arange(16) % 4)


@pytest.mark.parametrize("rep", (0, -1, 1.0, True, None))
def test_invalid_replicates(rep):
    with pytest.raises(ValueError):
        study.partners(rep)
    with pytest.raises(ValueError):
        study.decode(b"", rep)


def test_scalar_construction_and_input_immutability(example, checker):
    e = example
    before = [v.tobytes() for v in (e["parent"]["theta"], e["kept"], e["fresh"], e["residual"])]
    proof = checker.check(e["parent"]["theta"], e["kept"], e["fresh"], e["residual"],
                          study.DISPOSABLE, 2, e["result"])
    assert proof["passes"] and proof["records"] == 8 and proof["unordered_pairs"] == 4
    assert before == [v.tobytes() for v in (e["parent"]["theta"], e["kept"], e["fresh"], e["residual"])]
    assert all(not v.flags.writeable for v in e["result"].values())


def test_common_is_symmetric_but_not_claimed_information_free(example):
    e = example
    theta = e["parent"]["theta"]
    p = study.partners(2)
    actual = study.common_records(theta, 2)
    swapped = study.common_records(theta[p], 2)
    assert actual.tobytes() == swapped.tobytes()
    for i, j in enumerate(p):
        assert actual[i].tobytes() == actual[j].tobytes()
    np.testing.assert_allclose(actual.std(axis=(1, 2)), .3, rtol=0., atol=1e-13)
    np.testing.assert_allclose(actual.mean(axis=(1, 2)), 0., rtol=0., atol=1e-13)
    assert not np.all(actual == 0.)


def test_cancellation_is_a_failure_not_a_replacement(example):
    theta = example["parent"]["theta"].copy()
    theta[4:6], theta[6:8] = -theta[:2], -theta[2:4]
    with pytest.raises(study.DegenerateCommonRecord):
        study.common_records(theta, 2)


@pytest.mark.parametrize("kind", ("nan", "float32", "wrong_shape", "bad_mask", "different_mask", "different_fill"))
def test_bad_sources_rejected(example, kind):
    e = deepcopy(example)
    if kind == "nan": e["parent"]["theta"][0, 0, 0] = np.nan
    if kind == "float32": e["parent"]["theta"] = e["parent"]["theta"].astype(np.float32)
    if kind == "wrong_shape": e["kept"] = e["kept"][:-1]
    if kind == "bad_mask": e["fresh"] = e["fresh"].astype(float)
    if kind == "different_mask": e["fresh"][4] = ~e["fresh"][4]
    if kind == "different_fill": e["kept"][4][e["fresh"][4]] += .1
    with pytest.raises(ValueError):
        study.construct(e["parent"]["theta"], e["kept"], e["fresh"], e["residual"], study.DISPOSABLE, 2)


@pytest.mark.parametrize("kind", ("common", "one_ulp_identity", "fresh", "residual", "partners", "permutations",
                                   "body_own", "body_partner", "body_own_scrambled", "body_partner_scrambled",
                                   "body_history_erased", "extra"))
def test_independent_checker_rejects_tampering(example, checker, kind):
    e = example
    modified = {k: v.copy() for k, v in e["result"].items()}
    if kind == "extra": modified["old_reference"] = np.zeros_like(e["kept"])
    elif kind == "one_ulp_identity": modified["common"][4, 0, 0] = np.nextafter(modified["common"][4, 0, 0], np.inf)
    elif kind == "fresh": modified[kind][0, 0, 0] = ~modified[kind][0, 0, 0]
    elif kind == "partners": modified[kind][0] = 0
    elif kind == "permutations": modified[kind][0, :2] = modified[kind][0, :2][::-1]
    else: modified[kind].flat[0] += .1
    with pytest.raises(AssertionError):
        checker.check(e["parent"]["theta"], e["kept"], e["fresh"], e["residual"],
                      study.DISPOSABLE, 2, modified)


@pytest.mark.parametrize("body", study.BODIES)
@pytest.mark.parametrize("packet", study.PACKETS)
def test_all_initials_remove_old_R_and_ema(example, checker, body, packet):
    initial = study.initial(example["result"], body, packet)
    checker.check_initial(example["result"], body, packet, initial)
    assert not np.shares_memory(initial["V"], example["result"][f"body_{body}"])
    assert not np.shares_memory(initial["theta"], example["result"][packet])


def test_invalid_arm_and_seed_rejected(example):
    with pytest.raises(ValueError): study.initial(example["result"], "old_body")
    with pytest.raises(ValueError): study.initial(example["result"], "own", "intact")
    with pytest.raises(ValueError): study.seeded(study.DISPOSABLE, "target_A")
    with pytest.raises(ValueError): study.Mode(reader="native")
    with pytest.raises(ValueError): study.Mode(write=1)


def test_native_update_bridge_and_selective_controls(example):
    e = example
    ctx = study.runtime_context(e["ctx"])
    cfg = ctx["config"]
    initial = study.initial(e["result"], "own")
    live = study.repair(ctx, initial, study.DISPOSABLE)
    fixed = study.repair(ctx, initial, study.DISPOSABLE, study.Mode(reader="fixed"))
    off = study.repair(ctx, initial, study.DISPOSABLE, study.Mode(write=False))
    repeat = study.repair(ctx, initial, study.DISPOSABLE)
    assert live["outgoing"] == repeat["outgoing"]
    assert live["rng_final"] == fixed["rng_final"] == off["rng_final"]
    native = study.source.base.state_copy(initial)
    rng = study.RepairRNG(study.DISPOSABLE, cfg.replicates)
    for s in range(1, cfg.sweeps + 1):
        native = dict(zip(study.STATE_KEYS, e["ctx"]["api"]["cascade_sweep"](
            *(native[k] for k in study.STATE_KEYS), ctx["tissue"], ctx["ladder"], ctx["bp"],
            rng, cfg.lam, cfg.norm)))
        if s in cfg.times:
            for key in study.STATE_KEYS:
                np.testing.assert_array_equal(native[key], live["raw"][f"s{s}_{key}"])
    for s in cfg.times:
        for key in ("V", "ema", "R"):
            np.testing.assert_array_equal(off["raw"][f"s{s}_{key}"], fixed["raw"][f"s{s}_{key}"])
        assert off["raw"][f"s{s}_theta"].tobytes() == initial["theta"].tobytes()
    for key in study.STATE_KEYS:
        np.testing.assert_array_equal(live["raw"][f"s1_{key}"], fixed["raw"][f"s1_{key}"])


@pytest.mark.parametrize("kind", ("target", "parent", "ema", "R", "extra_state"))
def test_repair_rejects_hidden_inputs(example, kind):
    ctx = study.runtime_context(example["ctx"])
    state = study.initial(example["result"], "own")
    if kind in ("target", "parent"): ctx[kind] = example["parent"]
    elif kind == "extra_state": state["old_theta"] = example["parent"]["theta"]
    else: state[kind].flat[0] = .1
    with pytest.raises(ValueError): study.repair(ctx, state, study.DISPOSABLE)


@pytest.mark.parametrize("packet", (None, {}, b"", np.zeros((4, 16, 16)), np.full((8, 16, 16), np.nan).tobytes()))
def test_fresh_boundary_rejects_nonpacket_inputs(packet):
    with pytest.raises(ValueError): study.decode(packet, 2)


def test_fresh_reader_resets_and_exact_common_control(example):
    e = example
    cfg = replace(reading.CONFIG, parents=2, draws=2, sweeps=6, times=(0, 1, 6))
    packet = study.encode(e["result"]["common"], 2)
    result = study.fresh_read(e["ctx"], packet, cfg)
    disabled = study.fresh_read(e["ctx"], packet, cfg, off=True)
    assert result["theta_unchanged"] and result["R_zero_every_step"]
    assert disabled["metrics"]["accuracy"] == .25
    p = study.partners(2)
    for s in cfg.times:
        v = result["raw"][f"s{s}_V"].reshape(8, 2, 16, 16)
        for i, j in enumerate(p):
            assert v[i].tobytes() == v[j].tobytes()
        assert np.all(result["raw"][f"s{s}_R"] == 0.)
    assert len(packet) == 8 * 2048


def test_disabled_reference_and_writer_cannot_smuggle_body_identity(example):
    ctx = study.runtime_context(example["ctx"])
    own = study.initial(example["result"], "own")
    partner = study.initial(example["result"], "partner")
    left = study.repair(ctx, own, study.DISPOSABLE, study.Mode(write=False))
    right = study.repair(ctx, partner, study.DISPOSABLE, study.Mode(write=False))
    assert left["outgoing"] == right["outgoing"] == study.encode(own["theta"], 2)
    frozen_reference = study.repair(ctx, own, study.DISPOSABLE, study.Mode(reference_write=False))
    for s in ctx["config"].times:
        assert np.all(frozen_reference["raw"][f"s{s}_R"] == 0.)
    np.testing.assert_allclose(study.decode(frozen_reference["outgoing"], 2), own["theta"], rtol=0., atol=1e-13)


def receipt_fixture(path, failure=None):
    suites = ET.Element("testsuites")
    suite = ET.SubElement(suites, "testsuite", tests="50", failures="0", errors="0", skipped="0", time="1")
    names = ["test_native_update_bridge_and_selective_controls", "test_fresh_reader_resets_and_exact_common_control"]
    names += [f"other_{i}" for i in range(48)]
    for name in names:
        ET.SubElement(suite, "testcase", name=name)
    if failure == "second_suite": ET.SubElement(suites, "testsuite", tests="1", failures="1")
    if failure == "failure_tag": ET.SubElement(suite.find("testcase"), "failure")
    if failure == "skipped": suite.set("skipped", "1")
    if failure == "count": suite.set("tests", "51")
    if failure == "missing_bridge": suite.find("testcase").set("name", "not_the_bridge")
    ET.ElementTree(suites).write(path)


@pytest.mark.parametrize("failure", ("second_suite", "failure_tag", "skipped", "count", "missing_bridge"))
def test_qualification_rejects_bad_receipts(tmp_path, monkeypatch, failure):
    from laws_confirmation import l22_active_form_qualification as run
    monkeypatch.setattr(run, "ROOT", tmp_path)
    path = tmp_path / "receipt.xml"
    receipt_fixture(path, failure)
    with pytest.raises(AssertionError): run.test_receipt(path)


def test_qualification_receipt_and_exclusive_artifacts(tmp_path, monkeypatch):
    from laws_confirmation import l22_active_form_qualification as run
    monkeypatch.setattr(run, "ROOT", tmp_path)
    path = tmp_path / "receipt.xml"
    receipt_fixture(path)
    assert run.test_receipt(path)["cases"] == 50
    target = tmp_path / "record.json"
    run.write_json(target, dict(status="TEST_FIXTURE", value=1))
    assert json.loads(target.read_text())["value"] == 1
    with pytest.raises(FileExistsError): run.write_json(target, dict(value=2))
    with pytest.raises(ValueError): run.write_json(tmp_path / "nan.json", dict(value=float("nan")))
    with pytest.raises(AssertionError): run.write_json(tmp_path.parent / "escape.json", {})
    data = tmp_path / "record.npz"
    run.write_arrays(data, dict(x=np.arange(8)))
    np.testing.assert_array_equal(run.arrays(data)["x"], np.arange(8))
    with pytest.raises(FileExistsError): run.write_arrays(data, dict(x=np.arange(8)))


