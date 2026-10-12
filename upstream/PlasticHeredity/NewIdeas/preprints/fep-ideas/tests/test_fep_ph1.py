from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fep_ph1.campaign import analyze_stage, run_all, status
from fep_ph1.config import profile_config, regime_specs
from fep_ph1.controllers import yoked_random_schedule
from fep_ph1.endpoints import f12_break_renewal, strict_eight
from fep_ph1.environment import EnvironmentDesign, GardActiveInferenceEnvironment
from fep_ph1.gard import (
    apply_ranked_substitution,
    generate_beta,
    generate_initial_composition,
    normalized_gate,
    simultaneous_permutation,
    variance_restored_log_morph,
)
from fep_ph1.models import ModelCounts, model_from_counts
from fep_ph1.types import Action, ActionChannel, EnvironmentFamily
from fep_ph1.validation import NEUTRAL_REFERENCE, _neutral_digest


def _model(config):
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, state % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    return model_from_counts(counts, config)


def test_neutral_kernel_matches_retained_record_and_rng_digests() -> None:
    config = profile_config("smoke")
    assert _neutral_digest(config, "02") == NEUTRAL_REFERENCE["02"]
    assert _neutral_digest(config, "03") == NEUTRAL_REFERENCE["03"]


def test_control_primitives_preserve_frozen_invariants() -> None:
    config = profile_config("smoke")
    beta = generate_beta(config.gard, np.random.default_rng(10))
    order = np.random.default_rng(11).permutation(config.gard.n_types)
    altered = variance_restored_log_morph(
        beta, simultaneous_permutation(beta, order), 0.35
    )
    assert np.log(altered).mean() == pytest.approx(np.log(beta).mean(), abs=1e-12)
    assert np.log(altered).std() == pytest.approx(np.log(beta).std(), abs=1e-12)
    gate = normalized_gate(np.linspace(-1.0, 1.0, 100), 1, 0.8)
    assert gate.mean() == pytest.approx(1.0, abs=1e-12)
    composition = generate_initial_composition(config.gard, np.random.default_rng(12))
    edited, remove, add = apply_ranked_substitution(composition, gate)
    assert remove >= 0 and add >= 0
    assert edited.sum() == composition.sum()
    assert np.abs(edited - composition).sum() == 2


def test_sampling_is_more_informative_and_has_physical_cost() -> None:
    config = profile_config("smoke")
    beta = generate_beta(config.gard, np.random.default_rng(20))
    initial = generate_initial_composition(config.gard, np.random.default_rng(21))
    design = EnvironmentDesign(
        EnvironmentFamily.CATALYTIC,
        ActionChannel.UPTAKE,
        regime_specs()[0],
        "02",
        22,
        23,
    )
    passive = GardActiveInferenceEnvironment(config, design, beta, initial, 24, 25, 26)
    sampled = GardActiveInferenceEnvironment(config, design, beta, initial, 24, 25, 26)
    passive_correct = np.mean([passive._cue(False) == passive.regime + 1 for _ in range(2000)])
    sampled_correct = np.mean([sampled._cue(True) == sampled.regime + 1 for _ in range(2000)])
    assert sampled_correct > passive_correct + 0.30
    result = sampled.step(int(Action.SAMPLE))
    assert result.abstract_action_cost == config.action_cost_sample
    assert result.physical_action_cost == pytest.approx(
        1.0 - config.sampling_exposure_multiplier
    )


def test_preferences_and_yoked_random_contracts() -> None:
    config = profile_config("smoke")
    model = _model(config)
    assert np.all(model.C[1] == 0.0)
    assert np.all(model.C[2] == 0.0)
    assert np.all(model.C[3] == 0.0)
    actions = np.asarray([0, 1, 3, 2, 0, 3, 1, 0], dtype=np.int64)
    schedule = yoked_random_schedule(actions, 91)
    assert np.count_nonzero(schedule == int(Action.SAMPLE)) == 2
    assert np.count_nonzero(
        (schedule == int(Action.ADAPT_A)) | (schedule == int(Action.ADAPT_B))
    ) == 3


def test_descriptive_endpoint_fixtures() -> None:
    completed = np.ones(12, dtype=np.int8)
    similarities = np.asarray([0.8, 0.95, 0.96, 0.97, *([0.5] * 8)])
    assert f12_break_renewal(completed, similarities)

    parents = np.zeros((10, 100), dtype=np.int64)
    daughters = np.zeros_like(parents)
    anchor = np.zeros(100, dtype=np.int64)
    anchor[0] = 80
    form = np.zeros(100, dtype=np.int64)
    form[1] = 40
    parents[0] = anchor
    daughters[0, 0] = 40
    parents[1:] = form * 2
    daughters[1:] = form
    strict_similarity = np.asarray([0.5, *([1.0] * 9)])
    assert strict_eight(np.ones(10), strict_similarity, parents, daughters)


def test_full_profile_freezes_eight_hour_contract() -> None:
    config = profile_config("full")
    assert config.wall_time_limit_seconds == 28_800
    assert config.graceful_stop_seconds == 27_900
    assert config.registration_projection_ceiling_seconds == 23_400
    assert config.development_matrices == 32
    assert config.evaluation_matrices == 128
    assert config.branches == 4
    assert config.horizon == 60


def test_complete_smoke_atlas_replays_before_analysis(tmp_path: Path) -> None:
    config = profile_config("smoke")
    with pytest.raises((FileNotFoundError, RuntimeError)):
        analyze_stage(tmp_path, config)
    result = run_all(tmp_path, config)
    metrics = json.loads((result / "metrics.json").read_text())
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["positive_negative_classifier"] is None
    replay = json.loads((tmp_path / "smoke" / "replay" / "replay.json").read_text())
    assert replay["all_exact"] is True
    state = status(tmp_path, "smoke")
    assert all(
        state[name]
        for name in (
            "validation",
            "benchmark",
            "registered",
            "fit",
            "simulation",
            "replay",
            "analysis",
        )
    )
