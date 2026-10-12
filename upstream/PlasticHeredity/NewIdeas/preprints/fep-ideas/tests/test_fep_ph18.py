from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from fep_lab.integrity import read_json, verify_seal
from fep_ph18.campaign import run_all, status
from fep_ph18.config import (
    CONFIRM_SWITCH_PROBABILITIES,
    MAX_WORKERS,
    MECHANISM_KEYS,
    SCALE_PAIRS,
    profile_config,
)
from fep_ph18.data import (
    development_cell,
    development_conditions,
    stage_a_conditions,
    stage_b_conditions,
)
from fep_ph18.hybrid_model import expected_regime_information, fit_projection
from fep_ph18.types import InformationArm, SensingTiming
from fep_ph18.validation import _synthetic_data, validate_experiment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def test_frozen_factorials_action_alphabet_and_feature_firewall() -> None:
    smoke = profile_config("smoke")
    full = profile_config("full")
    assert MAX_WORKERS == full.workers == 4
    assert full.wall_time_limit_seconds == 16 * 60 * 60
    assert full.registration_projection_ceiling_seconds == 14 * 60 * 60
    assert SCALE_PAIRS == ((48, 48), (40, 40), (32, 32), (24, 24), (20, 20), (16, 16))
    development = development_conditions(SCREEN)
    stage_a = stage_a_conditions(SCREEN)
    stage_b = stage_b_conditions(SCREEN)
    assert len(development) == 20
    assert len(stage_a) == 10
    assert len(stage_b) == 24
    assert {value.mechanism_key for value in stage_b} == set(MECHANISM_KEYS)
    assert {value.switch_probability for value in stage_b} == set(
        CONFIRM_SWITCH_PROBABILITIES
    )
    assert {value.sensing_timing for value in stage_b} == {
        SensingTiming.DELAYED,
        SensingTiming.SAME_CYCLE,
    }
    assert {value.information_arm for value in stage_b} == {
        InformationArm.INFORMATIVE,
        InformationArm.SHAM,
    }

    delayed = next(
        value for value in development if value.sensing_timing == SensingTiming.DELAYED
    )
    same = next(
        value for value in development if value.sensing_timing == SensingTiming.SAME_CYCLE
    )
    delayed_arrays, metadata = development_cell(smoke, delayed)
    same_arrays, _ = development_cell(smoke, same)
    assert delayed_arrays["coarse_features"].shape[1] == 48
    assert delayed_arrays["rich_features"].shape[1] == 149
    assert delayed_arrays["coarse_targets"].shape[1] == 12
    assert delayed_arrays["rich_targets"].shape[1] == 112
    assert set(np.unique(delayed_arrays["action"])).issubset({0, 1, 2, 3})
    assert set(np.unique(same_arrays["action"])).issubset({0, 1, 2, 4, 5, 6})
    assert metadata["learned_feature_firewall"] == [
        "true_regime",
        "beta",
        "rng_state",
        "f12",
        "strict8",
    ]


def test_scientific_scale_full_svd_is_bitwise_deterministic() -> None:
    data = _synthetic_data(8, rows_per_matrix=105)
    first = fit_projection(data, 12)
    second = fit_projection(data, 12)
    assert np.array_equal(first.mean, second.mean)
    assert np.array_equal(first.components, second.components)
    pivots = np.argmax(np.abs(first.components), axis=1)
    assert np.all(first.components[np.arange(12), pivots] >= 0.0)


def test_information_timing_and_validation_contract() -> None:
    belief = np.asarray((0.45, 0.45, 0.10), dtype=np.float64)
    sham = expected_regime_information(
        belief, 0.25, 0.05, 0.50, transition=False
    )
    informative_current = expected_regime_information(
        belief, 0.25, 0.05, 0.98, transition=False
    )
    informative_delayed = expected_regime_information(
        belief, 0.25, 0.05, 0.98, transition=True
    )
    assert 0.0 <= sham < informative_current <= 1.0
    assert 0.0 <= informative_delayed <= 1.0
    result = validate_experiment(profile_config("smoke"), SCREEN)
    assert result["all_passed"] is True
    assert all(item["passed"] for item in result["checks"])


def test_all_path_smoke_replays_exactly(tmp_path: Path) -> None:
    config = replace(
        profile_config("smoke"),
        horizon=4,
        bootstrap_repetitions=16,
    )
    run_root = tmp_path / "runs-fep-ph18"
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
        "stage-a",
        "stage-a-replay",
        "stage-a-analysis",
        "stage-b",
        "stage-b-replay",
        "analysis",
    ):
        assert verify_seal(root / stage), stage
    selection = read_json(root / "fit" / "model-selection.json")
    assert selection["schema"] == "fep-ph18-development-model-selection-v1"
    assert selection["uses_evaluation_outcomes"] is False
    for stage in (
        "development-replay",
        "fit-replay",
        "stage-a-replay",
        "stage-b-replay",
    ):
        assert read_json(root / stage / "replay.json")["all_exact"] is True
    gate = read_json(root / "stage-a-analysis" / "gate.json")
    assert gate["passed"] is True
    assert gate["workflow_only_override"] is True
    assert read_json(root / "stage-b-registration.json")["action"] == "RUN"
    metrics = read_json(root / "analysis" / "metrics.json")
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["positive_negative_classifier"] is None
    assert len(metrics["strict_gates"]) == 8
    assert metrics["matrix_controller_rows"] == 24 * 10

    observed = status(run_root, "smoke")
    assert observed["current_stage"] == "complete"
    assert observed["registered_source_current"] is True
    assert observed["stage_a_cells_present"] == 10
    assert observed["stage_b_cells_present"] == 24
