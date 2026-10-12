from copy import deepcopy
from concurrent.futures import Future
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l17_r_channel as channel


@pytest.fixture(scope="module")
def context():
    cfg = channel.ExperimentConfig(replicates=2, settle_sweeps=4, imprint_sweeps=6,
                                  render_sweeps=4, child_sweeps=12, sample_times=(0, 4, 12))
    return channel.make_context(30000, cfg)


def test_frozen_registry_and_historical_config():
    assert channel.TISSUES == tuple(range(10000, 10008))
    assert channel.CONFIG == channel.ExperimentConfig()
    assert channel.REGISTERED_CHILD_LIVES == 2560
    assert channel.WORKERS == 4
    api = channel.source_api()
    assert api["EigenConfig"]().digest() == "26e403f2e841da5a1fd5d2cb15fedf678174644be094e14a5c1a54de38a57f54"
    assert api["BlueprintConfig"]().rho == .002


def test_codebook_balanced_equal_interfaces_and_spatial_spectrum():
    codes = channel.codebook()
    assert codes.shape == (4, 16, 16)
    assert np.all(codes.mean(axis=(1, 2)) == 0)
    assert np.all(codes.sum(axis=0) == 0)
    interfaces = [(c != np.roll(c, 1, axis=1)).sum() for c in codes]
    assert interfaces == [64] * 4
    spectra = np.abs(np.fft.fft2(codes))
    np.testing.assert_allclose(spectra, np.repeat(spectra[:1], 4, axis=0), atol=1e-12)
    assert len({channel.array_digest(c) for c in codes}) == 4
    with pytest.raises(ValueError):
        channel.codebook(8, 8)


def test_decoder_known_message_flat_field_and_tie_accounting():
    codes = channel.codebook()
    _, probabilities = channel.decode(codes * 3., codes)
    np.testing.assert_array_equal(probabilities, np.eye(4))
    _, flat = channel.decode(np.zeros((4, 16, 16)), codes)
    np.testing.assert_array_equal(flat, np.full((4, 4), .25))
    _, shared = channel.decode((codes[0] + codes[1])[None], codes)
    np.testing.assert_array_equal(shared, [[.5, .5, 0., 0.]])
    assert channel.measure_field(np.full((16, 16), -.1), codes[0])["amplitude_fidelity"] == 0


def test_marginal_null_is_not_automatically_half():
    field = np.array([1., 1., 1., -.1])
    target = np.array([1., 1., 1., -1.])
    result = channel.measure_field(field, target)
    assert result["sign_fidelity"] == 1.
    assert result["amplitude_fidelity"] == .75
    assert result["sign_marginal_null"] == .625
    assert result["amplitude_marginal_null"] == .5625


def test_coupled_noise_has_exact_registered_marginal_and_cross_message_pairing():
    rng = channel.MessageCoupledRNG(30000, "unit", 2)
    reference = np.random.default_rng(channel.seed(30000, "unit"))
    for _ in range(3):
        observed = rng.standard_normal((8, 16, 16))
        expected = reference.standard_normal((2, 16, 16))
        np.testing.assert_array_equal(observed, np.tile(expected, (4, 1, 1)))
    np.testing.assert_array_equal(rng.integers(0, 2, 8), np.tile(reference.integers(0, 2, 2), 4))
    assert rng.digest() == channel.canonical_digest(reference.bit_generator.state)
    with pytest.raises(ValueError):
        rng.standard_normal((7, 16, 16))
    with pytest.raises(ValueError):
        rng.integers(0, 2, 7)


def test_event_namespaces_are_independent_and_reproducible():
    assert channel.seed(30000, "parent_birth") != channel.seed(30000, "fresh_body_birth")
    assert channel.seed(30000, "fragment_boundary") != channel.seed(30000, "child_development")
    assert channel.seed(30000, "child_development") != channel.seed(30001, "child_development")
    assert channel.seed(30000, "child_development") == channel.seed(30000, "child_development")


def test_native_step_wrapper_is_bitwise_the_original_engine(context):
    initial = channel.naive_body(context, "unit_initial")
    before = channel.state_digest(initial)
    result = channel.simulate(context, initial, "unit_step", 5, sample_times=(0, 5))
    state = channel.state_copy(initial)
    rng = channel.MessageCoupledRNG(context["index"], "unit_step", context["config"].replicates)
    for _ in range(5):
        v, ema, reference = context["api"]["blueprint_step"](
            state["V"], state["ema"], state["R"], context["theta"], context["tissue"],
            context["ladder"], context["bp"], "T", rng,
        )
        state = {"V": v, "ema": ema, "R": reference}
    assert channel.state_digest(state) == result["final_sha256"]
    assert rng.digest() == result["rng_final_sha256"]
    assert before == channel.state_digest(initial)
    assert channel.state_digest(result["snapshots"][0]) == before


def test_parent_instruction_uses_pre_step_clamp_not_direct_reference_write(context):
    parent = channel.teach_parent(context)
    config = context["config"]
    state = channel.state_copy(parent["before_instruction"])
    hold = np.repeat(context["codes"], config.replicates, axis=0) * 1.2
    rng = channel.MessageCoupledRNG(context["index"], "parent_imprint", config.replicates)
    for _ in range(config.imprint_sweeps):
        v, ema, reference = context["api"]["blueprint_step"](
            hold.copy(), state["ema"], state["R"], context["theta"], context["tissue"],
            context["ladder"], context["bp"], "T", rng,
        )
        np.testing.assert_array_equal(reference, state["R"] + context["bp"].rho * (v - state["R"]))
        state = {"V": v, "ema": ema, "R": reference}
    assert channel.state_digest(state) == channel.state_digest(parent["after_instruction"])
    assert not np.array_equal(parent["after_instruction"]["R"], hold)


def test_fresh_body_contains_no_message_dependent_state(context):
    body = channel.naive_body(context, "fresh_body_birth")
    assert all(channel.message_independent(a, 2) for a in body.values())
    other = channel.naive_body(context, "parent_birth")
    assert channel.state_digest(body) != channel.state_digest(other)


def test_wrong_shuffle_and_reset_keep_the_intended_boundary_semantics(context):
    parent = channel.teach_parent(context)["after_render"]
    body = channel.naive_body(context, "fresh_body_birth")
    parent_before, body_before = channel.state_digest(parent), channel.state_digest(body)
    states, fresh = channel.boundary_states(context, parent, body)
    for arm in channel.ARMS[:6]:
        for key in ("V", "ema"):
            np.testing.assert_array_equal(states[arm][key], body[key])
            assert not np.shares_memory(states[arm][key], body[key])
    np.testing.assert_array_equal(states["copy"]["R"], parent["R"])
    np.testing.assert_array_equal(states["reset"]["R"], body["R"])
    for message in range(4):
        for replicate in range(2):
            i, donor = 2 * message + replicate, 2 * ((message + 1) % 4) + replicate
            np.testing.assert_array_equal(states["wrong"]["R"][i], parent["R"][donor])
            np.testing.assert_array_equal(np.sort(states["shuffle"]["R"][i].ravel()), np.sort(parent["R"][i].ravel()))
    assert fresh.shape == (8, 16, 16) and np.all(fresh.sum(axis=(1, 2)) == 128)
    assert parent_before == channel.state_digest(parent) and body_before == channel.state_digest(body)


def test_fragment_uses_frozen_fission_draw_for_draw_and_explicit_regrown_mask(context):
    parent = channel.teach_parent(context)["after_render"]
    offspring, fresh = channel.fragment_boundary(context, parent)
    rng = channel.MessageCoupledRNG(context["index"], "fragment_boundary", 2)
    reference = context["api"]["fission"](parent["V"].copy(), context["tissue"], rng)
    np.testing.assert_array_equal(offspring, reference)
    draw_rng = channel.MessageCoupledRNG(context["index"], "fragment_boundary", 2)
    axes, sides = draw_rng.integers(0, 2, 8), draw_rng.integers(0, 2, 8)
    noise = context["tissue"].copy_jitter * draw_rng.standard_normal(parent["V"].shape)
    expected = np.where(fresh, context["tissue"].resting, parent["V"]) + noise
    np.testing.assert_array_equal(offspring, expected)
    assert np.all(fresh.sum(axis=(1, 2)) == 128)
    assert channel.message_independent(fresh, 2)


def test_all_small_acquired_arms_obey_exact_nulls_replay_and_rng_pairing(context):
    body = channel.naive_body(context, "fresh_body_birth")
    result, parents, trajectories, fresh = channel.acquired_experiment(context, body)
    assert result["passes"], result["structural_gates"]
    assert set(result["rows"]) == set(channel.ARMS)
    assert all(len(rows) == 3 * 4 * 2 for rows in result["rows"].values())
    assert "regrown_rendered_parent" in result["rows"]["fragment_copy"][0]
    assert "regrown_rendered_parent" not in result["rows"]["copy"][0]
    for arm in ("reset", "copy_reader_off", "reset_reader_off"):
        assert all(s["body_accuracy"] == .25 for s in result["summaries"][arm].values())
    assert not np.array_equal(trajectories["copy_reader_off"]["final"]["R"], trajectories["reset_reader_off"]["final"]["R"])
    np.testing.assert_array_equal(trajectories["copy_reader_off"]["final"]["V"], trajectories["reset_reader_off"]["final"]["V"])


def test_small_calibration_is_replayable_and_held_reference_is_explicit(context):
    result, body, trajectories = channel.calibration(context)
    assert result["passes"], result["structural_gates"]
    injected = np.repeat(context["codes"], 2, axis=0) * 3.
    for state in trajectories["injected"]["snapshots"].values():
        np.testing.assert_array_equal(state["R"], injected)
    assert result["summaries"]["injected_reader_off"]["12"]["body_accuracy"] == .25
    # Qualification cannot be inferred from a short disposable fixture.
    assert not channel.calibration_qualified([result])


def calibration_rows(value=.8):
    return [{"tissue": t, "passes": True, "positive_accuracy": value} for t in channel.TISSUES]


def test_instrument_gate_requires_every_tissue_above_chance_and_mean_three_quarters():
    assert channel.calibration_qualified(calibration_rows(.75))
    assert not channel.calibration_qualified(calibration_rows(.74))
    rows = calibration_rows(1.)
    rows[0]["positive_accuracy"] = .25
    assert not channel.calibration_qualified(rows)
    rows = calibration_rows(1.)
    rows[0]["passes"] = False
    assert not channel.calibration_qualified(rows)
    assert not channel.calibration_qualified(calibration_rows()[:-1])


def outcome_rows():
    rows = []
    for tissue in channel.TISSUES:
        summaries = {a: {"1000": {"body_accuracy": .25, "wrong_donor_body_accuracy": .25}} for a in channel.ARMS}
        summaries["copy"]["1000"]["body_accuracy"] = .75
        summaries["wrong"]["1000"] = {"body_accuracy": .125, "wrong_donor_body_accuracy": .75}
        rows.append({"tissue": tissue, "passes": True, "summaries": summaries})
    return rows


def test_classification_separates_instrument_failure_null_and_content_signal():
    rows = outcome_rows()
    result = channel.classify(rows, True)
    assert result["label"] == "CONTENT_SPECIFIC_R_TRANSMISSION"
    assert result["primary_copy_minus_reset"]["mean"] == .5
    assert result["primary_copy_minus_reset"]["paired_tissue_bootstrap_95"] == [.5, .5]
    assert channel.classify([], False)["label"] == "INSTRUMENT_NOT_QUALIFIED"
    assert channel.classify(rows, True, False)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert channel.classify(rows[:7], True)["label"] == "INVALID_STRUCTURAL_FAILURE"
    for row in rows:
        row["summaries"]["wrong"]["1000"]["wrong_donor_body_accuracy"] = .125
    assert channel.classify(rows, True)["label"] == "NO_QUALIFIED_R_TRANSMISSION_IN_THIS_ASSAY"


def test_primary_requires_six_positive_tissues_even_if_mean_large():
    rows = outcome_rows()
    for row in rows[:3]:
        row["summaries"]["copy"]["1000"]["body_accuracy"] = .25
    result = channel.classify(rows, True)
    assert result["primary_copy_minus_reset"]["positive_tissues"] == 5
    assert result["label"] == "NO_QUALIFIED_R_TRANSMISSION_IN_THIS_ASSAY"


def test_complete_state_serialization_round_trip_is_exact(context, tmp_path):
    body = channel.naive_body(context, "serialization")
    trajectory = channel.simulate(context, body, "serialization_develop", 4, sample_times=(0, 4))
    path = tmp_path / "states.npz"
    channel.atomic_npz(path, channel.trajectory_arrays(trajectory), tmp_path)
    with np.load(path, allow_pickle=False) as loaded:
        for t, state in trajectory["snapshots"].items():
            reconstructed = {k: loaded[f"s{t}_{k}"] for k in state}
            assert channel.state_digest(reconstructed) == channel.state_digest(state)


def test_existing_target_refused_before_any_mutation(tmp_path):
    run = tmp_path / "runs" / channel.RUN_ID
    run.mkdir(parents=True)
    (run / "STATUS.json").write_text('{"status":"COMPLETE"}')
    with pytest.raises(FileExistsError):
        channel.prepare(tmp_path)
    with pytest.raises(FileExistsError):
        channel.benchmark(tmp_path)
    assert (run / "STATUS.json").read_text() == '{"status":"COMPLETE"}'


def test_frozen_input_inventory_includes_native_engine_dependencies_and_contract():
    paths = channel.input_paths()
    assert all(p.is_file() for p in paths)
    names = {str(p) for p in paths}
    assert str(channel.sources_root() / "blueprint_web/src/blueprint_web/engine.py") in names
    assert str(channel.sources_root() / "voltage_web/src/voltage_web/engine.py") in names
    assert str(channel.sources_root() / "ladder_web/src/ladder_web/engine.py") in names
    assert any(p.name == "L17_R_CHANNEL_ONE_BOUNDARY_V1.md" for p in paths)


def test_short_worker_round_trip_preserves_calibration_body_for_acquired_phase(context, tmp_path, monkeypatch):
    monkeypatch.setattr(channel, "CONFIG", context["config"])
    monkeypatch.setattr(channel, "external_root", lambda value: Path(value))
    monkeypatch.setattr(channel, "runtime", lambda: {"passes": True})
    control = channel.worker(context["index"], "calibration", str(tmp_path))
    result = channel.worker(context["index"], "acquired", str(tmp_path))
    assert control["passes"] and result["passes"]
    assert control["newborn_sha256"] == result["newborn_sha256"]
    stored = json.loads(Path(result["path"]).read_text())
    assert len(stored["rows"]) == 8
    with np.load(Path(result["path"]).parent / "copy_states.npz") as arrays:
        assert arrays["s12_V"].shape == (8, 16, 16)
    with np.load(Path(result["path"]).parent / "fragment_regrown_mask.npz") as arrays:
        assert arrays["fresh"].dtype == bool


def test_failed_positive_control_stops_before_teaching_any_acquired_parent(tmp_path, monkeypatch):
    submitted = []
    class ImmediateExecutor:
        def __init__(self, **kwargs):
            assert kwargs["max_workers"] <= 4
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def submit(self, fn, tissue, phase, root):
            submitted.append(phase)
            future = Future()
            future.set_result({"tissue": tissue, "passes": True, "positive_accuracy": .25})
            return future
    run = tmp_path / "runs" / channel.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(channel, "verify_prepared", lambda root: {"input_sha256": {"synthetic": "fixture"}})
    monkeypatch.setattr(channel, "verify_hashes", lambda hashes: True)
    monkeypatch.setattr(channel, "runtime", lambda: {"passes": True, "cpu_affinity": [0]})
    monkeypatch.setattr(channel, "ProcessPoolExecutor", ImmediateExecutor)
    assert channel.run_study(tmp_path) == 0
    assert submitted == ["calibration"] * len(channel.TISSUES)
    status = json.loads((run / "STATUS.json").read_text())
    assert status["classification"] == "INSTRUMENT_NOT_QUALIFIED"
    assert status["child_lives_run_excluding_replays"] == 512
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
