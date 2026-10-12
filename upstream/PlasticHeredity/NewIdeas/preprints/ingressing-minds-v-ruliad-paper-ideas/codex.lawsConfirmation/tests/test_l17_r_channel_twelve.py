from copy import deepcopy
from concurrent.futures import Future
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_r_channel as base
from laws_confirmation import l17_r_channel_twelve as chain


@pytest.fixture(scope="module")
def context():
    config = chain.ChainConfig(replicates=2, generations=3, settle_sweeps=4, imprint_sweeps=8,
                               render_sweeps=4, child_sweeps=12, sample_times=(0, 4, 12))
    return base.make_context(30012, config)


@pytest.fixture(scope="module")
def small_run(context):
    parent = base.teach_parent(context)["after_render"]
    calibrated, bodies = chain.calibration_chain(context)
    result = chain.lineage_chain(context, parent, bodies)
    return parent, bodies, calibrated, result


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l17_r_channel_twelve_outputs.py"
    spec = importlib.util.spec_from_file_location("independent_l17_twelve_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_and_life_accounting():
    assert chain.CONFIG.generations == 12
    assert chain.CONFIG.replicates == 8
    assert chain.CONFIG.sample_times == (0, 50, 1000)
    assert chain.CONFIG.child_sweeps == 1000
    assert len(chain.ARMS) == 9 and len(chain.TISSUES) == 8
    assert chain.REGISTERED_LIVES == 33792
    assert chain.REPLAY_LIVES == 3072
    assert chain.WORKERS == 4
    assert set(chain.ANCHOR_ARMS) == set(chain.ARMS)


def test_generation_rng_namespaces_have_exact_G1_and_distinct_future():
    events = ("fresh_body_birth", "fragment_boundary", "child_development")
    assert all(chain.phase(1, e) == e for e in events)
    keys = [base.seed(10000, chain.phase(g, e)) for g in range(1, 13) for e in events]
    assert len(set(keys)) == 36
    assert chain.phase(12, "child_development") == "twelve_boundary_v1:g12:child_development"
    with pytest.raises(ValueError):
        chain.phase(0, "child_development")


def test_newborns_are_message_independent_and_new_each_generation(context):
    bodies = [chain.newborn(context, g) for g in range(1, 4)]
    assert len({base.state_digest(b) for b in bodies}) == 3
    assert all(base.message_independent(a, 2) for b in bodies for a in b.values())
    assert base.state_digest(bodies[0]) == base.state_digest(base.naive_body(context, "fresh_body_birth"))


def test_native_fission_exact_and_reproducible_masks(context, small_run):
    parent = small_run[0]
    initial = base.state_digest(parent)
    draws = []
    for generation in range(1, 4):
        observed, fresh = chain.fission(context, parent, generation)
        rng = base.MessageCoupledRNG(context["index"], chain.phase(generation, "fragment_boundary"), 2)
        expected = context["api"]["fission"](parent["V"].copy(), context["tissue"], rng)
        np.testing.assert_array_equal(observed, expected)
        assert fresh.dtype == bool and np.all(fresh.sum(axis=(1, 2)) == 128)
        assert base.message_independent(fresh, 2)
        draws.append(base.array_digest(observed))
    assert len(set(draws)) == 3
    assert base.state_digest(parent) == initial
    original, original_mask = base.fragment_boundary(context, parent)
    got, mask = chain.fission(context, parent, 1)
    np.testing.assert_array_equal(original, got)
    np.testing.assert_array_equal(original_mask, mask)


def test_fresh_renew_boundary_depends_only_on_R_not_parent_body(context, small_run):
    parent, bodies = small_run[:2]
    changed = base.state_copy(parent)
    changed["V"][:] = 1.9
    changed["ema"][:] = -1.9
    ordinary, fresh = chain.birth(context, "fresh_renew", parent, parent, bodies[2], 2)
    altered, _ = chain.birth(context, "fresh_renew", changed, changed, bodies[2], 2)
    assert base.state_digest(ordinary) == base.state_digest(altered)
    assert fresh is None
    for key in ("V", "ema"):
        np.testing.assert_array_equal(ordinary[key], bodies[2][key])
    np.testing.assert_array_equal(ordinary["R"], parent["R"])
    assert not np.shares_memory(ordinary["R"], parent["R"])


def test_only_rescue_reads_original_ancestor_after_G1(context, small_run):
    parent, bodies = small_run[:2]
    changed_ancestor = base.state_copy(parent)
    changed_ancestor["R"] += .123
    for arm in chain.ARMS:
        old, _ = chain.birth(context, arm, parent, parent, bodies[2], 2)
        changed, _ = chain.birth(context, arm, parent, changed_ancestor, bodies[2], 2)
        assert (base.state_digest(old) != base.state_digest(changed)) == arm.endswith("ancestor_rescue")


def test_wrong_swap_occurs_once_not_at_fourth_or_twelfth_boundary(context, small_run):
    ancestor, bodies = small_run[:2]
    first, _ = chain.birth(context, "fresh_wrong_seed", ancestor, ancestor, bodies[1], 1)
    np.testing.assert_array_equal(first["R"], chain.permute_message(ancestor["R"], 2))
    for generation in (2, 4, 8, 12):
        next_state, _ = chain.birth(context, "fresh_wrong_seed", first, ancestor, bodies[1], generation)
        np.testing.assert_array_equal(next_state["R"], first["R"])
        assert not np.array_equal(next_state["R"], ancestor["R"])


def test_reset_reference_is_newborn_not_zero_or_parent(context, small_run):
    parent, bodies = small_run[:2]
    for arm in ("fresh_reset", "fresh_reset_reader_off", "fragment_reset"):
        state, _ = chain.birth(context, arm, parent, parent, bodies[2], 2)
        np.testing.assert_array_equal(state["R"], bodies[2]["R"])
        assert not np.array_equal(state["R"], parent["R"])
        assert np.any(state["R"] != 0)


def test_fragment_birth_remains_parent_specific_after_first_boundary(context, small_run):
    parent, bodies = small_run[:2]
    changed = base.state_copy(parent)
    changed["V"] += .1
    one, mask = chain.birth(context, "fragment_renew", parent, parent, bodies[2], 2)
    two, mask2 = chain.birth(context, "fragment_reset", changed, parent, bodies[2], 2)
    np.testing.assert_array_equal(mask, mask2)
    np.testing.assert_array_equal(one["V"][mask], two["V"][mask])
    assert not np.array_equal(one["V"][~mask], two["V"][~mask])
    np.testing.assert_array_equal(two["V"], two["ema"])


def test_rescue_and_reader_off_keep_native_writing(context, small_run):
    parent, bodies = small_run[:2]
    for arm in ("fresh_ancestor_rescue", "fresh_reader_off"):
        state, _ = chain.birth(context, arm, parent, parent, bodies[1], 1)
        tr = base.simulate(context, state, "test-native-writing", 1, c_m=0. if arm.endswith("reader_off") else None)
        np.testing.assert_array_equal(tr["final"]["R"], state["R"] + .002 * (tr["final"]["V"] - state["R"]))
        assert not np.array_equal(tr["final"]["R"], state["R"])


def test_all_small_chain_structural_gates_and_parent_links(small_run):
    _, _, calibrated, result = small_run
    assert calibrated["passes"] and result["passes"]
    assert len(calibrated["generations"]) == len(result["generations"]) == 3
    for generation in result["generations"]:
        assert all(generation["structural_gates"].values())
        assert all(generation["reference_changed_in_life"].values())
        for arm, link in generation["reference_links"].items():
            assert link["expected_sha256"] == link["birth_sha256"]
            if arm.endswith("ancestor_rescue"):
                assert link["source"] == "external_ancestor_backup"
        if generation["generation"] > 1:
            previous = result["generations"][generation["generation"] - 2]
            assert generation["parent_sha256"] == previous["final_sha256"]


def test_empty_strict_mask_is_null_not_chance():
    field = np.ones((16, 16))
    empty = chain.masked_measure(field, -field, np.zeros_like(field, dtype=bool))
    assert empty == {"cells": 0, "metrics": None}
    full = chain.masked_measure(field, field, np.ones_like(field, dtype=bool))
    assert full["cells"] == 256 and full["metrics"]["amplitude_fidelity"] == 1


def test_fixed_ancestor_and_immediate_parent_not_conflated(context, small_run):
    parent, bodies = small_run[:2]
    ancestor = base.state_copy(parent)
    ancestor["V"] = -parent["V"]
    trajectory = {"snapshots": {0: parent}}
    rows = chain.measurements(context, trajectory, ancestor, parent)
    assert all(row["fixed_ancestor"]["sign_fidelity"] == 0. for row in rows)
    assert all(row["immediate_parent"]["sign_fidelity"] == 1. for row in rows)


def calibrated_records():
    return [{"tissue": t, "passes": True, "generations": [{"generation": g, "passes": True, "positive_accuracy": 1.} for g in range(1, 13)]} for t in chain.TISSUES]


def test_calibration_requires_every_generation_and_every_tissue():
    good = calibrated_records()
    assert chain.calibration_qualified(good)
    assert not chain.calibration_qualified(good[:-1])
    failed = deepcopy(good)
    failed[2]["generations"][8]["positive_accuracy"] = .25
    assert not chain.calibration_qualified(failed)
    failed = deepcopy(good)
    for record in failed:
        record["generations"][11]["positive_accuracy"] = .7
    assert not chain.calibration_qualified(failed)
    failed = deepcopy(good)
    failed[0]["generations"] = failed[0]["generations"][:-1]
    assert not chain.calibration_qualified(failed)


def endpoint_records(body, reference):
    return [{"tissue": t, "passes": True, "generations": [{"generation": g, "passes": True, "summaries": {
        "fresh_renew": {"1000": {"body_accuracy": body if g == 12 else 1., "reference_accuracy": reference if g == 12 else 1.}},
        "fresh_reset": {"1000": {"body_accuracy": .25, "reference_accuracy": .25}}}} for g in range(1, 13)]} for t in chain.TISSUES]


@pytest.mark.parametrize("body,reference,label", [
    (1., 1., "BODY_AND_REFERENCE_PERSIST_G12"), (.25, 1., "REFERENCE_ONLY_DETECTED_G12"),
    (1., .25, "BODY_ONLY_DETECTED_G12"), (.25, .25, "NO_QUALIFIED_G12_MESSAGE_LEAD")])
def test_classifier_uses_registered_G12_not_favorable_early_generation(body, reference, label):
    result = chain.classify(endpoint_records(body, reference), True)
    assert result["label"] == label
    assert result["co_primary_G12"]["body"]["mean"] == body - .25


def test_classifier_invalid_or_unqualified_is_not_negative_evidence():
    assert chain.classify([], False)["label"] == "INSTRUMENT_NOT_QUALIFIED"
    assert chain.classify([], True)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert chain.classify(endpoint_records(1., 1.), True, False)["label"] == "INVALID_STRUCTURAL_FAILURE"
    short = endpoint_records(1., 1.)
    short[0]["generations"] = short[0]["generations"][:-1]
    assert chain.classify(short, True)["label"] == "INVALID_STRUCTURAL_FAILURE"
    failed = endpoint_records(1., 1.)
    failed[1]["generations"][4]["passes"] = False
    assert chain.classify(failed, True)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_bootstrap_uses_whole_tissue_pairs_and_prespecified_tail_allocation():
    differences = [0., .1, .2, .3, .4, .5, .6, .7]
    result = chain.contrast(differences, 20260907171201)
    draws = np.random.default_rng(20260907171201).integers(0, 8, (10000, 8))
    expected = np.quantile(np.asarray(differences)[draws].mean(axis=1), [.0125, .9875]).tolist()
    assert result["paired_tissue_bootstrap_97_5"] == expected
    assert result["positive_tissues"] == 7 and result["supported"]
    assert not chain.contrast([1.] * 5 + [0.] * 3, 3)["supported"]


def test_private_rng_does_not_modify_global_state(context, small_run):
    initial = deepcopy(np.random.get_state())
    chain.lineage_chain(context, small_run[0], small_run[1])
    final = np.random.get_state()
    assert initial[0] == final[0] and initial[2:] == final[2:]
    np.testing.assert_array_equal(initial[1], final[1])


def test_independent_decoder_and_positional_calculations(independent):
    codes = base.codebook()
    _, probabilities = independent.probabilities(codes, codes)
    np.testing.assert_array_equal(probabilities, np.eye(4))
    _, flat = independent.probabilities(np.zeros((4, 16, 16)), codes)
    np.testing.assert_array_equal(flat, np.full((4, 4), .25))
    assert independent.positional(np.array([]), np.array([])) is None
    rng = np.random.default_rng(18)
    v, target = rng.normal(size=(2, 16, 16))
    independent.check_metrics(independent.positional(v, target), base.measure_field(v, target))
    assert independent.digest(v) == base.array_digest(v)


def test_external_artifact_roundtrip_and_independent_full_snapshot(tmp_path, monkeypatch, independent):
    cfg = chain.ChainConfig(generations=2, settle_sweeps=4, imprint_sweeps=8, render_sweeps=4,
                           child_sweeps=12, sample_times=(0, 4, 12))
    context = base.make_context(30013, cfg)
    original_newborn = chain.newborn
    monkeypatch.setattr(chain, "newborn", lambda ctx, g, root=None: original_newborn(ctx, g))
    monkeypatch.setattr(chain, "anchor_matches", lambda *args: True)
    ancestor = base.teach_parent(context)["after_render"]
    output = tmp_path / "outputs"
    calibration, _ = chain.calibration_chain(context, tmp_path, output)
    lineage = chain.lineage_chain(context, ancestor, root=tmp_path, output=output)
    assert calibration["passes"] and lineage["passes"]
    cumulative = np.zeros((32, 16, 16), dtype=np.int32)
    parents = {a: ancestor for a in chain.ARMS}
    for g in (1, 2):
        gd = output / f"g{g:02d}"
        saved = json.loads((gd / "lineage.json").read_text())
        growth = chain.load_arrays(gd / "regrowth.npz")
        cumulative += growth["fresh"]
        np.testing.assert_array_equal(cumulative, growth["counts"])
        for arm in chain.ARMS:
            raw = chain.load_arrays(gd / f"{arm}_states.npz")
            for sweep in cfg.sample_times:
                state = {k: raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
                rows = [r for r in saved["rows"][arm] if r["sweep"] == sweep]
                independent.check_snapshot(state, rows, saved["summaries"][arm][str(sweep)], context["codes"],
                                           ancestor, parents[arm], growth if arm.startswith("fragment") else None)
            parents[arm] = {k: raw[f"s12_{k}"] for k in ("V", "ema", "R")}
    assert (output / "PROGRESS.json").is_file()


def test_existing_immutable_targets_refused_before_any_benchmark_reads(tmp_path):
    (tmp_path / "outputs" / chain.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        chain.prepare(tmp_path)
    with pytest.raises(FileExistsError):
        chain.benchmark(tmp_path)


def test_detachment_does_not_poll_or_wait(tmp_path, monkeypatch):
    (tmp_path / "runs" / chain.RUN_ID).mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(chain, "verify_prepared", lambda root: {"benchmark": {"projected_seconds_four_workers": 900}})
    calls = []

    def start(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=12345)  # Deliberately no poll/wait methods.

    monkeypatch.setattr(chain.subprocess, "Popen", start)
    record = chain.launch_detached(tmp_path)
    assert len(calls) == 1 and calls[0][1]["start_new_session"] is True
    assert calls[0][1]["stdin"] == chain.subprocess.DEVNULL
    assert record["pid"] == 12345 and record["polling_owner"] == "user"
    assert (tmp_path / "runs" / chain.RUN_ID / "LAUNCH.json").is_file()
    assert not (tmp_path / "runs" / chain.RUN_ID / "STATUS.json").exists()


def test_long_projection_cannot_run_foreground(tmp_path, monkeypatch):
    (tmp_path / "runs" / chain.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(chain, "verify_prepared", lambda root: {"benchmark": {"must_detach": True}})
    with pytest.raises(RuntimeError, match="detached launch required"):
        chain.run_study(tmp_path)
    assert not (tmp_path / "runs" / chain.RUN_ID / "EXECUTION.lock").exists()


def test_failed_late_instrument_stops_entire_lineage_phase(tmp_path, monkeypatch):
    run, output = tmp_path / "runs" / chain.RUN_ID, tmp_path / "outputs" / chain.RUN_ID
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    chain.atomic_text(tmp_path / "fixture-input.txt", "unit fixture", tmp_path)
    hashes = {str(tmp_path / "fixture-input.txt"): chain.sha256_file(tmp_path / "fixture-input.txt")}
    manifest = {"benchmark": {"must_detach": False}, "input_sha256": hashes}
    monkeypatch.setattr(chain, "verify_prepared", lambda root: manifest)
    monkeypatch.setattr(chain.base, "runtime", lambda: {"passes": True, "cpu_affinity": [0, 1, 2, 3]})
    monkeypatch.setattr(chain, "qualify_source", lambda root: {"passes": True})
    monkeypatch.setattr(chain, "disk_preflight", lambda root: {"passes": True})
    jobs = []
    calibration = calibrated_records()
    calibration[3]["generations"][11]["positive_accuracy"] = .25

    class Pool:
        def __init__(self, **kwargs):
            assert kwargs["max_workers"] == 4

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def submit(self, fn, tissue, stage, root):
            jobs.append((tissue, stage))
            assert stage == "calibration"
            future = Future()
            future.set_result(next(r for r in calibration if r["tissue"] == tissue))
            return future

    monkeypatch.setattr(chain, "ProcessPoolExecutor", Pool)
    assert chain.run_study(tmp_path) == 0
    assert len(jobs) == 8 and all(stage == "calibration" for _, stage in jobs)
    status = json.loads((run / "STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["classification"] == "INSTRUMENT_NOT_QUALIFIED"
    study = json.loads((output / "r_channel_twelve.json").read_text())
    assert study["lineage_results"] == [] and study["replay_lives"] == 0
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
