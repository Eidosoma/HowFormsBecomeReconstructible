from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from fep_lab.integrity import read_json, verify_seal
from fep_ph16.campaign import run_all, status
from fep_ph16.causal_model import (
    expected_information_gain,
    fit_ensemble,
    model_digest,
    uniform_weights,
)
from fep_ph16.config import MECHANISM_KEYS, RIDGE_GRID, profile_config
from fep_ph16.controllers import exact_multiset_yoke
from fep_ph16.data import development_cell, load_conditions
from fep_ph16.state import clr_proportions, composition_clr
from fep_ph16.types import CONTROLLERS
from fep_ph16.validation import _synthetic_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def test_frozen_factorial_and_development_actions() -> None:
    config = profile_config("smoke")
    conditions = load_conditions(SCREEN)
    assert len(conditions) == 24
    assert {condition.mechanism_key for condition in conditions} == set(MECHANISM_KEYS)
    arrays, metadata = development_cell(config, conditions[0])
    assert arrays["coarse_features"].shape[1] == 48
    assert arrays["rich_features"].shape[1] == 149
    assert arrays["coarse_targets"].shape[1] == 12
    assert arrays["rich_targets"].shape[1] == 112
    assert metadata["learned_feature_firewall"] == [
        "true_regime",
        "beta",
        "rng_state",
        "f12",
        "strict8",
    ]
    assert set(np.unique(arrays["action"])) == {0, 1, 2, 3}
    counts = np.bincount(arrays["action"], minlength=4)
    assert counts.max() - counts.min() == 0


def test_clr_round_trip_and_exact_action_yoke() -> None:
    composition = np.arange(101, 201, dtype=np.int64)
    clr = composition_clr(composition)
    expected = (composition + 0.5) / float(np.sum(composition + 0.5))
    assert abs(float(clr.mean())) < 1.0e-12
    assert np.allclose(clr_proportions(clr), expected, atol=1.0e-12, rtol=0.0)

    actions = np.asarray((0, 0, 1, 2, 2, 2, 3, 3, 1, 0), dtype=np.int8)
    yoked = exact_multiset_yoke(actions, 16_620)
    assert np.array_equal(
        np.bincount(actions, minlength=4), np.bincount(yoked, minlength=4)
    )
    assert not np.shares_memory(actions, yoked)


def test_causal_ensemble_is_deterministic_and_epistemic_value_is_finite() -> None:
    data = _synthetic_data(2)
    first = fit_ensemble(data, rich=True, members=2, ridge_grid=RIDGE_GRID)
    second = fit_ensemble(data, rich=True, members=2, ridge_grid=RIDGE_GRID)
    assert model_digest(first) == model_digest(second)
    prediction = first.predict(data.rich_features[0], int(data.actions[0]))
    information = expected_information_gain(prediction, uniform_weights(first))
    assert np.isfinite(information)
    assert 0.0 <= information <= 1.0
    assert first.cross_validation["next_clr_rmse"] >= 0.0


def test_all_path_smoke_replays_exactly(tmp_path: Path) -> None:
    # This is deliberately smaller than the command-line smoke profile while
    # retaining all 24 conditions, all ten controllers, both model classes,
    # both replay stages, registration, analysis, and the timing gate.
    config = replace(
        profile_config("smoke"),
        horizon=4,
        oracle_depth=1,
        oracle_replicas=1,
        mpc_depth=1,
        bootstrap_repetitions=16,
    )
    run_root = tmp_path / "runs-fep-ph16"
    analysis = run_all(run_root, config)
    root = run_root / "smoke"
    assert analysis == root / "analysis"
    for stage in (
        "validation",
        "development",
        "development-replay",
        "fit",
        "fit-replay",
        "benchmark",
        "simulation",
        "replay",
        "analysis",
    ):
        assert verify_seal(root / stage), stage
    assert read_json(root / "development-replay" / "replay.json")["all_exact"]
    assert read_json(root / "fit-replay" / "replay.json")["all_exact"]
    assert read_json(root / "replay" / "replay.json")["all_exact"]
    benchmark = read_json(root / "benchmark" / "benchmark.json")
    assert benchmark["registration_eligible"] is True
    assert benchmark["benchmark_master_seed"] != config.master_seed
    assert benchmark["benchmark_seed_domain"].startswith("disposable_timing")
    expected_scaled = (
        benchmark["median_whole_cell_seconds"]
        * benchmark["full_horizon"]
        / benchmark["short_horizon"]
        * benchmark["full_branches"]
        / benchmark["short_branches"]
    )
    assert benchmark["horizon_scaled_cell_seconds"] == expected_scaled
    metrics = read_json(root / "analysis" / "metrics.json")
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["positive_negative_classifier"] is None
    assert metrics["matrix_controller_rows"] == 24 * len(CONTROLLERS)
    observed = status(run_root, "smoke")
    assert observed["current_stage"] == "complete"
    assert observed["registered_source_current"] is True
    assert observed["simulation_cells_present"] == 24
