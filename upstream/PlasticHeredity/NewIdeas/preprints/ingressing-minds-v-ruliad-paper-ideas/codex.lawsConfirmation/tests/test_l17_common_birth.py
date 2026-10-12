from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_common_birth as study
from laws_confirmation import l17_r_channel as base
from laws_confirmation import l17_r_channel_twelve as chain


@pytest.fixture(scope="module")
def context():
    cfg = replace(study.CONFIG, replicates=2, settle_sweeps=4, imprint_sweeps=8,
                  render_sweeps=4, child_sweeps=12, sample_times=(0, 1, 4, 8, 12))
    return base.make_context(30022, cfg)


def common_fixture(context):
    ancestor = base.teach_parent(context)["after_render"]
    parent = base.state_copy(ancestor)
    parent["R"] = parent["R"] * .8 + .1
    v, fresh = chain.fission(context, parent, 2)
    return {"parent": parent, "ancestor": ancestor,
            "initial": {"V": v, "ema": v.copy(), "R": parent["R"].copy()},
            "fresh": fresh, "counts": fresh.astype(np.int32) + 1}


@pytest.fixture(scope="module")
def common(context):
    return common_fixture(context)


@pytest.fixture(scope="module")
def small_result(context, common):
    return study.experiment(context, common, 2)


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l17_common_birth_outputs.py"
    spec = importlib.util.spec_from_file_location("independent_common_birth_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_registry_accounting_and_native_physics():
    assert study.TISSUES == tuple(range(10000, 10008))
    assert study.CHECKPOINTS == (2, 12)
    assert len(study.CORE_ARMS) == 8 and len(study.ARMS) == 11
    assert study.CONFIG.sample_times == (0, 1, 50, 500, 1000)
    assert study.REGISTERED_LIVES == 5632 and study.REPLAY_LIVES == 512
    assert study.WORKERS == 4
    assert base.source_api()["BlueprintConfig"]().rho == .002


def test_centering_is_uniform_mean_zero_shape_preserving_and_not_clipped():
    original = np.full((4, 16, 16), -1.)
    original[:, 0, 0] = 2.
    centered = study.centered_body(original)
    assert abs(centered.mean(axis=(1, 2))).max() < 1e-14
    np.testing.assert_allclose(centered - original, np.broadcast_to(-original.mean(axis=(1, 2))[:, None, None], original.shape), rtol=0., atol=1e-15)
    assert centered.max() > 2.  # No hidden birth clipping/shape intervention.
    np.testing.assert_array_equal(original[:, 0, 0], [2.] * 4)
    np.testing.assert_allclose(study.centered_body(original + 4.25), centered, rtol=0., atol=1e-14)


def test_factorial_bodies_and_references_are_separate(common):
    sources = {k: base.state_digest(common[k]) for k in ("initial", "ancestor")}
    states = study.branches(common["initial"], common["ancestor"], 2)
    for arm, state in states.items():
        body, reference, _ = arm.split("_")
        expected_v = common["initial"]["V"] if body == "native" else study.centered_body(common["initial"]["V"])
        np.testing.assert_array_equal(state["V"], expected_v)
        np.testing.assert_array_equal(state["ema"], state["V"])
        expected_r = common["initial"]["R"] if reference == "current" else common["ancestor"]["R"] if reference == "ancestor" else chain.permute_message(common["ancestor"]["R"], 2)
        np.testing.assert_array_equal(state["R"], expected_r)
        assert not np.shares_memory(state["V"], common["initial"]["V"])
        assert not np.shares_memory(state["R"], expected_r)
    assert sources == {k: base.state_digest(common[k]) for k in sources}


def test_ancestor_body_and_ema_never_enter_branches(common):
    altered = base.state_copy(common["ancestor"])
    altered["V"] *= -7
    altered["ema"] += 12
    actual = study.branches(common["initial"], altered, 2)
    expected = study.branches(common["initial"], common["ancestor"], 2)
    assert {a: base.state_digest(s) for a, s in actual.items()} == {a: base.state_digest(s) for a, s in expected.items()}


def test_no_body_change_when_reference_is_changed(common):
    first = study.branches(common["initial"], common["ancestor"], 2)
    ancestor = base.state_copy(common["ancestor"])
    ancestor["R"] *= -1
    second = study.branches(common["initial"], ancestor, 2)
    for a in study.ARMS:
        for k in ("V", "ema"):
            np.testing.assert_array_equal(first[a][k], second[a][k])


def test_all_small_structural_gates_and_new_arm_replay(small_result):
    record, _ = small_result
    assert record["passes"] and all(record["structural_gates"].values())
    assert record["centered_shape_max_error"] < 1e-14
    assert all(r["expected_sha256"] == r["birth_sha256"] for r in record["reference_links"].values())
    assert "wrong_donor_trajectory_permutation" not in record["structural_gates"]


def test_first_step_is_native_engine_for_all_interventions(context, common, small_result):
    states = study.branches(common["initial"], common["ancestor"], 2)
    for arm, trajectory in small_result[1].items():
        writer = arm.split("_")[-1]
        rng = base.MessageCoupledRNG(context["index"], chain.phase(2, "child_development"), 2)
        bp = context["bp"] if writer == "live" else replace(context["bp"], rho=0.)
        start = states[arm]
        v, ema, reference = context["api"]["blueprint_step"](start["V"].copy(), start["ema"].copy(), start["R"].copy(),
            context["theta"], context["tissue"], context["ladder"], bp, "T", rng, c_m=0. if writer == "off" else None)
        for key, value in (("V", v), ("ema", ema), ("R", reference)):
            np.testing.assert_array_equal(value, trajectory["snapshots"][1][key])


def test_held_writer_is_not_accidentally_native_and_off_twins_alias(small_result):
    for arm, trajectory in small_result[1].items():
        if arm.endswith("live"):
            assert not np.array_equal(trajectory["snapshots"][0]["R"], trajectory["final"]["R"])
        else:
            for state in trajectory["snapshots"].values():
                np.testing.assert_array_equal(state["R"], trajectory["snapshots"][0]["R"])
    for t in (0, 1, 4, 8, 12):
        for k in ("V", "ema"):
            np.testing.assert_array_equal(small_result[1]["centered_ancestor_off"]["snapshots"][t][k], small_result[1]["centered_current_off"]["snapshots"][t][k])


def test_historical_anchor_detects_changed_state(context, common, small_result):
    with_anchor = deepcopy(common)
    with_anchor["anchor"] = base.trajectory_arrays(small_result[1]["native_current_live"])
    assert study.experiment(context, with_anchor, 2)[0]["passes"]
    with_anchor["anchor"]["s12_V"][0, 0, 0] += 1e-8
    with pytest.raises(RuntimeError, match="historical_anchor_exact"):
        study.experiment(context, with_anchor, 2)


def test_generation_stream_changes_but_global_rng_does_not(context, common, small_result):
    old = deepcopy(np.random.get_state())
    other = study.experiment(context, common, 12)[0]
    new = np.random.get_state()
    assert other["rng_initial_sha256"] != small_result[0]["rng_initial_sha256"]
    assert old[0] == new[0] and old[2:] == new[2:]
    np.testing.assert_array_equal(old[1], new[1])


def endpoint_records(body_supported, reference_supported):
    records = []
    for tissue in study.TISSUES:
        for generation in study.CHECKPOINTS:
            left = 1.
            right_body = .25 if body_supported or generation == 2 else 1.
            right_reference = .25 if reference_supported or generation == 2 else 1.
            summaries = {"centered_ancestor_held": {"1000": {"body_accuracy": left}},
                         "native_ancestor_held": {"1000": {"body_accuracy": right_body}},
                         "centered_current_held": {"1000": {"body_accuracy": right_reference}}}
            records.append({"tissue": tissue, "generation": generation, "passes": True, "summaries": summaries})
    return records


@pytest.mark.parametrize("body,reference,label", [(True, True, "BODY_AND_REFERENCE_LIMITATIONS"),
    (True, False, "BODY_LIMITATION_ONLY"), (False, True, "REFERENCE_LIMITATION_ONLY"), (False, False, "NO_QUALIFIED_COMMON_BIRTH_LEAD")])
def test_classifier_prespecified_G12_not_favorable_G2(body, reference, label):
    result = study.classify(endpoint_records(body, reference))
    assert result["label"] == label
    assert result["co_primary_G12"]["body_compatibility"]["seed"] == 20260907170301
    assert result["co_primary_G12"]["reference_quality"]["seed"] == 20260907170302


def test_classifier_refuses_partial_duplicate_or_invalid_results():
    records = endpoint_records(True, True)
    for bad in (records[:-1], records + [records[0]], []):
        assert study.classify(bad)["label"] == "INVALID_STRUCTURAL_FAILURE"
    records[0]["passes"] = False
    assert study.classify(records)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert study.classify(endpoint_records(True, True), False)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_independent_full_cell_rescores_and_rejects_altered_birth(tmp_path, independent):
    cfg = replace(study.CONFIG, settle_sweeps=4, imprint_sweeps=8, render_sweeps=4,
                  child_sweeps=12, sample_times=(0, 1, 4, 8, 12))
    context = base.make_context(30023, cfg)
    common = common_fixture(context)
    record, trajectories = study.experiment(context, common, 2)
    path = tmp_path / "branches.json"
    study.atomic_json(path, record, tmp_path)
    loaded = json.loads(path.read_text())
    raw_common = {**{f"{name}_{k}": v for name in ("initial", "ancestor", "parent") for k, v in common[name].items()},
                  "fresh": common["fresh"], "counts": common["counts"]}
    maps = {a: base.trajectory_arrays(tr) for a, tr in trajectories.items()}
    for arm, arrays in maps.items():
        base.atomic_npz(tmp_path / f"{arm}.npz", arrays, tmp_path)
    reloaded = {a: chain.load_arrays(tmp_path / f"{a}.npz") for a in maps}
    stages = independent.check_cell(raw_common, loaded, reloaded, independent.templates())
    assert len(stages) == 55
    reloaded["centered_ancestor_held"]["s0_V"][0, 0, 0] += 1e-7
    with pytest.raises(AssertionError):
        independent.check_cell(raw_common, loaded, reloaded, independent.templates())


def test_exact_existing_source_common_births_and_config():
    root = study.external_root()
    context = base.make_context(10000, study.CONFIG)
    for generation in study.CHECKPOINTS:
        common = study.load_common(root, context, generation)
        for k in ("V", "ema", "R"):
            np.testing.assert_array_equal(common["initial"][k], common["anchor"][f"s0_{k}"])
        assert common["fresh"].shape == (32, 16, 16)
    with pytest.raises(ValueError):
        study.load_common(root, context, 3)


def test_prepared_or_existing_targets_never_overwritten(tmp_path):
    (tmp_path / "outputs" / study.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        study.prepare(tmp_path)
    with pytest.raises(FileExistsError):
        study.benchmark(tmp_path)


def test_long_jobs_require_detachment(tmp_path, monkeypatch):
    (tmp_path / "runs" / study.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": True}})
    with pytest.raises(RuntimeError, match="detached launch required"):
        study.run_study(tmp_path)
    assert not (tmp_path / "runs" / study.RUN_ID / "EXECUTION.lock").exists()


def test_detached_launch_has_no_poll_and_explicit_external_records(tmp_path, monkeypatch):
    (tmp_path / "runs" / study.RUN_ID).mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"projected_seconds_four_workers": 901}})
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=9876)
    monkeypatch.setattr(study.subprocess, "Popen", launch)
    result = study.launch_detached(tmp_path)
    assert result["pid"] == 9876 and result["polling_owner"] == "user"
    assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"] == study.subprocess.DEVNULL
    assert (tmp_path / "runs" / study.RUN_ID / "LAUNCH.json").is_file()


def test_runtime_failure_gets_failed_sentinel_without_scientific_work(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(study.base, "runtime", lambda: {"passes": False})
    monkeypatch.setattr(study, "qualify_source", lambda root: {"passes": True})
    monkeypatch.setattr(study, "retained_diagnostics", lambda root: pytest.fail("must not start work"))
    with pytest.raises(RuntimeError, match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run / "FAILED").is_file() and not (run / "COMPLETE").exists()
    assert json.loads((run / "STATUS.json").read_text())["status"] == "FAILED"
