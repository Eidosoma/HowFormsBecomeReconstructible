from __future__ import annotations

import json
import time

import numpy as np
import pytest

from fep_surprise_25.campaign import (
    analyze,
    benchmark,
    generate_confirmation,
    prepare_confirmation,
    register,
    replay_confirmation,
    screen,
    status,
    validate_stage,
)
from fep_surprise_25.analysis import _apply_holm, _paired_inference
from fep_surprise_25.budget import TimeBudgetExhausted, guard_budget
from fep_surprise_25.config import ARMS, profile_config
from fep_surprise_25.interventions import (
    arm_launches25,
    beta_variants25,
    log_beta_sigma,
)
from fep_surprise_25.regime import classify_break_regime, mass_preserving_perturbations
from plastic_heredity.config import GardConfig
from plastic_heredity.simulator import generate_beta, generate_initial_composition


def test_sigma_and_morph_transforms_separate_spread_from_mean() -> None:
    gard = GardConfig()
    rng = np.random.default_rng(25)
    beta = generate_beta(gard, rng)
    state = generate_initial_composition(gard, rng)
    order = np.arange(gard.n_types, dtype=np.int64)[::-1]
    variants = beta_variants25(beta, order)
    assert log_beta_sigma(variants["sigma_250"]) == pytest.approx(2.50, abs=1e-12)
    assert log_beta_sigma(variants["sigma_325"]) == pytest.approx(3.25, abs=1e-12)
    assert log_beta_sigma(variants["sigma_500"]) == pytest.approx(5.00, abs=1e-12)
    assert log_beta_sigma(variants["normalized_morph_050"]) == pytest.approx(
        log_beta_sigma(beta), abs=1e-12
    )
    assert log_beta_sigma(variants["raw_morph_050"]) < log_beta_sigma(beta)
    for key, value in variants.items():
        if key not in ("native", "raw_morph_050"):
            assert float(value.mean()) == pytest.approx(float(beta.mean()), rel=1e-12)
    launches = arm_launches25(beta, state, order)
    assert tuple(launches) == ARMS
    assert np.array_equal(launches["ALIGNED_NATIVE"].beta, beta)


def test_regime_thresholds_and_damage_transfers_are_frozen() -> None:
    config = profile_config("full")
    assert classify_break_regime({"02": 0.10, "03": 0.02}, config) == "stable"
    assert classify_break_regime({"02": 0.30, "03": 0.70}, config) == "transitional"
    assert classify_break_regime({"02": 0.95, "03": 0.90}, config) == "saturated"
    assert classify_break_regime({"02": 0.20, "03": 0.95}, config) is None
    state = np.zeros(100, dtype=np.int64)
    state[:5] = [10, 20, 15, 5, 30]
    changed = mass_preserving_perturbations(state, 8, 25)
    assert np.all(changed.sum(axis=1) == state.sum())
    assert np.all(changed >= 0)
    assert np.all(np.abs(changed - state).sum(axis=1) == 2)
    assert np.array_equal(changed, mass_preserving_perturbations(state, 8, 25))


def test_budget_and_directional_verdict_fixtures(tmp_path) -> None:
    config = profile_config("smoke")
    root = tmp_path / "smoke"
    root.mkdir(parents=True)
    (root / "budget_start.json").write_text(
        json.dumps(
            {
                "format": "fep-surprise-25-budget-v1",
                "started_epoch": time.time() - config.graceful_stop_seconds - 1,
                "budget_seconds": config.scientific_budget_seconds,
                "graceful_stop_seconds": config.graceful_stop_seconds,
            }
        )
    )
    with pytest.raises(TimeBudgetExhausted, match="TIME_BUDGET_EXHAUSTED_NO_VERDICT"):
        guard_budget(tmp_path, config, "fixture")

    positive = _paired_inference(np.ones(12), 128, 25)
    negative = _paired_inference(-np.ones(12), 128, 26)
    fixtures = {"positive": positive, "negative": negative}
    _apply_holm(fixtures)
    assert positive["pass"] is True
    assert negative["pass"] is False


def test_complete_experiment_25_smoke_campaign_enforces_firewalls(tmp_path) -> None:
    config = profile_config("smoke")
    validate_stage(tmp_path, config)
    benchmark(tmp_path, config, workers=2)
    register(tmp_path, config)
    screen(tmp_path, config, workers=2)
    confirmation = prepare_confirmation(tmp_path, config, workers=2)
    assert (confirmation / "confirmation_design.json").is_file()
    assert not list((confirmation / "cells").glob("*_futures.joblib"))
    generate_confirmation(tmp_path, config, workers=2)
    assert not (confirmation / "metrics.json").exists()
    assert not (confirmation / "REPORT.md").exists()
    with pytest.raises(FileNotFoundError):
        analyze(tmp_path, config)
    replay = replay_confirmation(tmp_path, config, workers=2)
    replay_payload = json.loads((replay / "replay.json").read_text())
    assert replay_payload["all_exact"] is True
    result = analyze(tmp_path, config)
    metrics = json.loads((result / "metrics.json").read_text())
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["regime_verdict"] == "NONSCIENTIFIC_PROFILE"
    assert metrics["decision"]["profile_is_scientifically_eligible"] is False
    state = status(tmp_path, "smoke")
    assert all(
        state[name]["sealed"]
        for name in (
            "validation",
            "benchmark",
            "registration",
            "screen",
            "confirmation",
            "confirmation_replay",
            "analysis",
        )
    )
