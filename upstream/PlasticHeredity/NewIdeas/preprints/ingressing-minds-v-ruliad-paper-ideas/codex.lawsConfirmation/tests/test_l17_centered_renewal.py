from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_centered_renewal as study
from laws_confirmation import l17_r_channel as base
from laws_confirmation import l17_r_channel_twelve as chain


@pytest.fixture(scope="module")
def context():
    cfg = replace(study.CONFIG, replicates=2, generations=3, settle_sweeps=4,
                  imprint_sweeps=8, render_sweeps=4, child_sweeps=12, sample_times=(0, 1, 12))
    return base.make_context(30032, cfg)


@pytest.fixture(scope="module")
def ancestor(context):
    return base.teach_parent(context)["after_render"]


@pytest.fixture(scope="module")
def small_result(context, ancestor):
    return study.lineage(context, ancestor)


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l17_centered_renewal_outputs.py"
    spec = importlib.util.spec_from_file_location("independent_centered_renewal_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_registry_physics_accounting_and_no_rescue_arms(context):
    assert study.TISSUES == tuple(range(10000, 10008))
    assert len(study.ARMS) == 10 and len(study.ANCHORS) == 2
    assert study.CONFIG.generations == 12 and study.CONFIG.sample_times == (0, 50, 1000)
    assert study.REGISTERED_LIVES == 30720 and study.REPLAY_LIVES == 3072 and study.WORKERS == 4
    assert context["bp"].rho == .002 and context["bp"].c_m == .2
    assert context["tissue"].resting == -1. and context["tissue"].copy_jitter == .05
    assert not any("ancestor" in a or "rescue" in a for a in study.ARMS)
    assert "ancestor" not in inspect.signature(study.birth).parameters


@pytest.mark.parametrize("generation", [1, 2, 12])
def test_birth_matches_independent_fission_and_only_actual_parent_R(context, ancestor, independent, generation):
    parent = base.state_copy(ancestor)
    parent["R"] = parent["R"] * .6 + .2  # Distinct from G0; a backup restore would fail.
    original = base.state_digest(parent)
    reset = study.reset_reference(context, generation)
    raw, fresh = independent.native_birth(context["index"], generation, parent["V"])
    for arm in study.ARMS:
        state, mask, native = study.birth(context, parent, reset, generation, arm)
        np.testing.assert_array_equal(mask, fresh)
        np.testing.assert_array_equal(native, raw)
        expected_v = raw - raw.mean(axis=(1, 2))[:, None, None] if arm.startswith("centered") else raw
        np.testing.assert_array_equal(state["V"], expected_v)
        np.testing.assert_array_equal(state["ema"], expected_v)
        expected_r = parent["R"] if "_copy_" in arm else reset
        np.testing.assert_array_equal(state["R"], expected_r)
        assert not np.shares_memory(state["R"], expected_r)
        assert not np.shares_memory(state["V"], parent["V"])
    assert base.state_digest(parent) == original


def test_centering_is_message_blind_and_not_a_birth_clip(context, ancestor):
    parent = base.state_copy(ancestor)
    parent["V"].fill(-1.)
    parent["V"][:, 0, 0] = 2.
    parent["V"][:, -1, -1] = 2.
    reset = study.reset_reference(context, 1)
    born, _, raw = study.birth(context, parent, reset, 1, "centered_copy_live")
    assert born["V"].max() > 2.
    assert abs(born["V"].mean(axis=(1, 2))).max() < 1e-14
    altered = base.state_copy(parent)
    altered["R"] *= -9.
    altered["ema"] += 5.
    other = study.birth(context, altered, -reset, 1, "centered_copy_live")[0]
    np.testing.assert_array_equal(born["V"], other["V"])
    np.testing.assert_allclose(born["V"] - raw, np.broadcast_to(-raw.mean(axis=(1, 2))[:, None, None], raw.shape), atol=1e-15, rtol=0.)


def test_each_intervention_uses_exact_native_first_step_and_off_still_writes(context, ancestor):
    reset = study.reset_reference(context, 2)
    for arm in study.ARMS:
        initial = study.birth(context, ancestor, reset, 2, arm)[0]
        trajectory = study.evolve(context, initial, 2, arm)
        rng = base.MessageCoupledRNG(context["index"], chain.phase(2, "child_development"), 2)
        bp = replace(context["bp"], rho=0.) if arm.endswith("held") else context["bp"]
        state = base.state_copy(initial)
        values = context["api"]["blueprint_step"](state["V"], state["ema"], state["R"], context["theta"],
            context["tissue"], context["ladder"], bp, "T", rng, c_m=0. if arm.endswith("off") else None)
        for key, expected in zip(("V", "ema", "R"), values):
            np.testing.assert_array_equal(trajectory["snapshots"][1][key], expected)
        changed = not np.array_equal(trajectory["final"]["R"], initial["R"])
        assert changed == (not arm.endswith("held"))


def test_three_boundaries_have_full_replay_links_and_writer_off_aliases(small_result):
    assert small_result["passes"]
    previous = None
    for row in small_result["generations"]:
        assert row["passes"] and all(row["structural_gates"].values())
        assert all(v["expected_sha256"] == v["birth_sha256"] for v in row["reference_links"].values())
        assert row["structural_gates"]["full_chain_exact_replay"]
        assert row["structural_gates"]["reader_off_full_body_alias"]
        if previous:
            assert row["parent_state_sha256"] == previous["final_state_sha256"]
            assert row["rng_initial_sha256"] != previous["rng_initial_sha256"]
        previous = row


def test_full_chain_replay_has_its_own_advanced_parent(context, ancestor, monkeypatch):
    original_birth, seen = study.birth, []
    def recording_birth(ctx, parent, reset, generation, arm):
        if arm == study.REPLAY_ARM:
            seen.append((generation, id(parent), base.state_digest(parent)))
        return original_birth(ctx, parent, reset, generation, arm)
    monkeypatch.setattr(study, "birth", recording_birth)
    study.lineage(context, ancestor)
    for i in range(0, 6, 2):
        actual, replay = seen[i:i+2]
        assert actual[0] == replay[0] and actual[1] != replay[1] and actual[2] == replay[2]
    assert seen[2][2] != seen[0][2]


def test_historical_anchor_failure_invalidates_future(context, ancestor, monkeypatch, tmp_path):
    original_reset = study.reset_reference
    monkeypatch.setattr(study, "reset_reference", lambda c, g, root: original_reset(c, g))
    monkeypatch.setattr(study, "anchor_matches", lambda *args: False)
    with pytest.raises(RuntimeError, match="native_historical_anchors"):
        study.lineage(context, ancestor, tmp_path)


def test_generation_coupling_does_not_touch_global_rng(context, ancestor):
    old = deepcopy(np.random.get_state())
    reset = study.reset_reference(context, 2)
    study.evolve(context, study.birth(context, ancestor, reset, 2, "centered_copy_off")[0], 2, "centered_copy_off")
    new = np.random.get_state()
    assert old[0] == new[0] and old[2:] == new[2:]
    np.testing.assert_array_equal(old[1], new[1])


def endpoint_records(flags=(True, True, True)):
    results = []
    for tissue in study.TISSUES:
        generations = []
        for generation in range(1, 13):
            f = flags if generation == 12 else (True, True, True)
            values = {"centered_copy_live": {"body_accuracy": 1., "reference_accuracy": 1.},
                      "centered_copy_held": {"body_accuracy": 1.},
                      "centered_reset_live": {"body_accuracy": .25 if f[0] else 1., "reference_accuracy": .25 if f[2] else 1.},
                      "centered_copy_off": {"body_accuracy": .25 if f[1] else 1.}}
            generations.append({"generation": generation, "passes": True, "summaries": {a: {"1000": v} for a, v in values.items()}})
        results.append({"tissue": tissue, "passes": True, "generations": generations})
    return results


@pytest.mark.parametrize("flags", [(True, True, True), (False, True, True), (True, False, True), (True, True, False), (False, False, False)])
def test_fixed_G12_requires_all_three_endpoints_including_reader_off(flags, independent):
    records = endpoint_records(flags)
    result = study.classify(records)
    expected = "CENTERED_NATIVE_RENEWAL_WITH_R_CONTRIBUTION" if all(flags) else "NO_QUALIFIED_CENTERED_RENEWAL_LEAD"
    assert result["label"] == expected
    assert tuple(c["supported"] for c in result["co_primary_G12"].values()) == flags
    endpoints = [{"tissue": r["tissue"], "arms": {a: v["1000"] for a, v in r["generations"][-1]["summaries"].items()}} for r in records]
    assert independent.adjudicate(endpoints, [[1.] * 12] * 8, result)["label"] == expected
    for i, c in enumerate(result["co_primary_G12"].values()):
        assert c["seed"] == 20260907170401 + i and c["quantiles"] == [1/120, 119/120]


def test_protected_control_must_qualify_every_generation_without_hiding_primary_stats():
    records = endpoint_records()
    records[0]["generations"][2]["summaries"]["centered_copy_held"]["1000"]["body_accuracy"] = .25
    result = study.classify(records)
    assert result["label"] == "PROTECTED_REFERENCE_CONTROL_NOT_QUALIFIED"
    assert all(c["supported"] for c in result["co_primary_G12"].values())
    records = endpoint_records()
    for row in records:
        row["generations"][0]["summaries"]["centered_copy_held"]["1000"]["body_accuracy"] = .7
    assert study.classify(records)["label"] == "PROTECTED_REFERENCE_CONTROL_NOT_QUALIFIED"


def test_classifier_refuses_missing_duplicate_generations_or_bad_structure():
    records = endpoint_records()
    for bad in (records[:-1], records + [records[0]], []):
        assert study.classify(bad)["label"] == "INVALID_STRUCTURAL_FAILURE"
    for mutation in ("passes", "count", "order"):
        bad = deepcopy(records)
        if mutation == "passes":
            bad[0]["generations"][0]["passes"] = False
        elif mutation == "count":
            bad[0]["generations"].pop()
        else:
            bad[0]["generations"][0]["generation"] = 12
        assert study.classify(bad)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert study.classify(records, False)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_positive_interval_alone_does_not_replace_six_tissue_rule():
    c = study.contrast([1.] * 5 + [0.] * 3, 1)
    assert c["paired_tissue_interval"][0] > 0 and c["positive_tissues"] == 5 and not c["supported"]


def test_independent_all_cell_metrics_and_multigeneration_links_reject_tampering(tmp_path, monkeypatch, independent):
    cfg = replace(study.CONFIG, generations=2, settle_sweeps=4, imprint_sweeps=8,
                  render_sweeps=4, child_sweeps=12, sample_times=(0, 1, 12))
    context = base.make_context(30033, cfg)
    ancestor = base.teach_parent(context)["after_render"]
    original_reset = study.reset_reference
    monkeypatch.setattr(study, "reset_reference", lambda c, g, root: original_reset(c, g))
    monkeypatch.setattr(study, "anchor_matches", lambda *args: True)
    output = tmp_path / "raw_lineage"
    result = study.lineage(context, ancestor, tmp_path, output)
    assert result == json.loads((output / "lineage.json").read_text())
    parents, counts = {a: ancestor for a in study.ARMS}, np.zeros_like(ancestor["V"], dtype=np.int32)
    for generation in (1, 2):
        gd = output / f"g{generation:02d}"
        saved = json.loads((gd / "generation.json").read_text())
        births = chain.load_arrays(gd / "births.npz")
        maps = {a: chain.load_arrays(gd / f"{a}_states.npz") for a in study.ARMS}
        reset = original_reset(context, generation)
        arguments = (context["index"], generation, ancestor, parents, counts, saved, maps, births, reset, cfg.sample_times)
        assert len(independent.check_generation(*arguments)) == 30
        # Isolated corruptions: bad native cut, hidden backup, and false summary.
        for target, key in ((births, "raw_centered_copy_live"), (maps["centered_copy_live"], "s0_R")):
            previous = target[key].copy()
            target[key][0, 0, 0] += 1e-7
            with pytest.raises(AssertionError):
                independent.check_generation(*arguments)
            target[key] = previous
        saved["summaries"]["centered_copy_live"]["12"]["body_accuracy"] += .01
        with pytest.raises(AssertionError):
            independent.check_generation(*arguments)
        counts = births["counts"]
        parents = {a: {k: maps[a][f"s12_{k}"] for k in ("V", "ema", "R")} for a in study.ARMS}


def test_real_reset_inputs_are_saved_naive_message_independent_references():
    root = study.external_root()
    context = base.make_context(10000, study.CONFIG)
    for generation in (1, 2, 12):
        expected = chain.load_arrays(study.old_directory(root, 10000, generation) / "newborn.npz")["R"]
        actual = study.reset_reference(context, generation, root)
        np.testing.assert_array_equal(actual, expected)
        assert base.message_independent(actual, 8) and np.any(actual != 0.)


def test_prepared_output_and_benchmark_are_never_overwritten(tmp_path):
    (tmp_path / "outputs" / study.RUN_ID).mkdir(parents=True)
    for method in (study.prepare, study.benchmark):
        with pytest.raises(FileExistsError):
            method(tmp_path)


def test_prepare_contract_verification_rejects_changed_config_inputs_status(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    path = tmp_path / "contract.txt"
    study.atomic_text(path, "frozen", tmp_path)
    bench = study.benchmark_path(tmp_path)
    study.atomic_json(bench, {"must_detach": True}, tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [path])
    hashes = {str(p): study.sha256_file(p) for p in (path, bench)}
    manifest = {"run_id": study.RUN_ID, "input_sha256": hashes, "contract_digest": study.canonical_digest(hashes),
                "config": asdict(study.CONFIG), "tissues": list(study.TISSUES), "arms": list(study.ARMS), "workers": 4}
    study.atomic_json(run / "MANIFEST.json", manifest, tmp_path)
    study.atomic_json(run / "STATUS.json", {"status": "PREPARED"}, tmp_path)
    assert study.verify_prepared(tmp_path)["run_id"] == study.RUN_ID
    for key, value in (("workers", 5), ("arms", list(study.ARMS)[:-1])):
        study.atomic_json(run / "MANIFEST.json", manifest | {key: value}, tmp_path)
        with pytest.raises(RuntimeError, match="contract changed"):
            study.verify_prepared(tmp_path)
    study.atomic_json(run / "MANIFEST.json", manifest, tmp_path)
    study.atomic_text(path, "changed", tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)


def test_long_jobs_require_detachment_before_execution(tmp_path, monkeypatch):
    (tmp_path / "runs" / study.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": True}})
    with pytest.raises(RuntimeError, match="detached launch required"):
        study.run_study(tmp_path)
    assert not (tmp_path / "runs" / study.RUN_ID / "EXECUTION.lock").exists()


def test_detached_launch_has_no_poll_and_records_external_handoff(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"projected_seconds_four_workers": 901}})
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=9876)  # No poll/wait methods provided.
    monkeypatch.setattr(study.subprocess, "Popen", launch)
    result = study.launch_detached(tmp_path)
    assert result["pid"] == 9876 and result["polling_owner"] == "user"
    assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"] == study.subprocess.DEVNULL
    assert (run / "RUN.pid").read_text().strip() == "9876" and (run / "LAUNCH.json").is_file()
    with pytest.raises(FileExistsError):
        study.launch_detached(tmp_path)


def test_runtime_failure_records_failed_sentinel_without_work(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(study.base, "runtime", lambda: {"passes": False})
    monkeypatch.setattr(study, "qualify_source", lambda root: {"passes": True})
    monkeypatch.setattr(study, "worker", lambda *args: pytest.fail("must not start scientific work"))
    with pytest.raises(RuntimeError, match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run / "FAILED").is_file() and not (run / "COMPLETE").exists()
