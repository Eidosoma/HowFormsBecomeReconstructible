from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from fep_lab.integrity import read_json, verify_seal
from fep_ph19.campaign import run_all, status
from fep_ph19.causal_pomdp import fit_exact_model, model_digest
from fep_ph19.config import (
    MAX_WORKERS,
    MECHANISM_KEYS,
    SCALE_PAIRS,
    SWITCH_PROBABILITIES,
    profile_config,
)
from fep_ph19.data import (
    development_cell,
    development_conditions,
    stage_a_conditions,
    stage_b_conditions,
)
from fep_ph19.types import InformationArm, SensingTiming
from fep_ph19.validation import _synthetic_cells, validate_experiment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def test_frozen_factorials_resource_contract_and_firewall() -> None:
    smoke = profile_config("smoke")
    full = profile_config("full")
    assert MAX_WORKERS == full.workers == 4
    assert full.wall_time_limit_seconds == 8 * 60 * 60
    assert full.registration_projection_ceiling_seconds == 6 * 60 * 60 + 45 * 60
    assert SCALE_PAIRS == (
        (32, 48),
        (32, 40),
        (32, 32),
        (24, 24),
        (20, 20),
        (16, 16),
    )

    development = development_conditions(SCREEN)
    stage_a = stage_a_conditions(SCREEN)
    stage_b = stage_b_conditions(SCREEN)
    assert len(development) == 12
    assert len(stage_a) == 6
    assert len(stage_b) == 16
    assert {value.mechanism_key for value in stage_b} == set(MECHANISM_KEYS)
    assert {value.switch_probability for value in stage_a} == set(
        SWITCH_PROBABILITIES
    )
    assert {value.information_arm for value in stage_a} == {InformationArm.NONE}
    assert sum(value.sensing_timing == SensingTiming.SAME_CYCLE for value in stage_b) == 12
    assert sum(value.sensing_timing == SensingTiming.DELAYED for value in stage_b) == 4
    assert {
        value.switch_probability
        for value in stage_b
        if value.sensing_timing == SensingTiming.DELAYED
    } == {0.15}

    delayed = next(
        value for value in development if value.sensing_timing == SensingTiming.DELAYED
    )
    same_cycle = next(
        value for value in development if value.sensing_timing == SensingTiming.SAME_CYCLE
    )
    delayed_arrays, metadata = development_cell(smoke, delayed)
    same_cycle_arrays, _ = development_cell(smoke, same_cycle)
    assert set(np.unique(delayed_arrays["action"])).issubset({0, 1, 2, 3})
    assert set(np.unique(same_cycle_arrays["action"])).issubset({0, 1, 2, 4, 5, 6})
    assert metadata["runtime_feature_firewall"] == [
        "true_regime",
        "beta",
        "rng_state",
        "future_outcomes",
        "f12",
        "strict8",
    ]


def test_exact_causal_fit_and_validation_replay() -> None:
    config = profile_config("smoke")
    first = fit_exact_model(_synthetic_cells(), config)
    second = fit_exact_model(_synthetic_cells(), config)
    assert model_digest(first) == model_digest(second)
    assert first.qualification["qualified"] is True
    result = validate_experiment(config, SCREEN)
    assert result["all_passed"] is True
    assert all(item["passed"] for item in result["checks"])


def test_all_path_smoke_replays_exactly(tmp_path: Path) -> None:
    # Non-full profiles mechanically override the Stage A and recurrent-entry
    # gates only to exercise every conditional implementation path. They never
    # acquire a scientific classifier.
    config = replace(
        profile_config("smoke"),
        horizon=4,
        bootstrap_repetitions=16,
    )
    run_root = tmp_path / "runs-fep-ph19"
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
    for stage in (
        "development-replay",
        "fit-replay",
        "stage-a-replay",
        "stage-b-replay",
    ):
        assert read_json(root / stage / "replay.json")["all_exact"] is True

    qualification = read_json(root / "fit" / "model-qualification.json")
    assert qualification["uses_evaluation_outcomes"] is False
    assert qualification["full_evaluation_requires_exact"] is True
    assert qualification["recurrent_entry_is_conditional"] is True
    assert read_json(root / "stage-a-analysis" / "gate.json")["workflow_only_override"] is True
    assert read_json(root / "stage-b-registration.json")["action"] == "RUN"

    registration = read_json(root / "registration.json")
    assert registration["global_classifier"] is False
    metrics = read_json(root / "analysis" / "metrics.json")
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["global_classifier"] is None
    assert metrics["matrix_controller_rows"] == 16 * 12
    assert set(metrics["component_tests"]) == {
        "exact_model_qualified",
        "recurrent_model_qualified",
        "exact_efe_beats_reactive",
        "exact_efe_beats_pragmatic",
        "always_sense_equivalence",
        "sensing_reduction",
        "information_specificity",
        "sham_equivalence",
        "timing_yoke_advantage",
        "same_cycle_specificity",
    }

    observed = status(run_root, "smoke")
    assert observed["current_stage"] == "complete"
    assert observed["registered_source_current"] is True
    assert observed["stage_a_cells_present"] == 6
    assert observed["stage_b_cells_present"] == 16
    assert observed["stage_a_cell_fraction"] == 1.0
    assert observed["stage_b_cell_fraction"] == 1.0
    assert observed["benchmark_registration_eligible"] is True
    assert observed["projected_total_seconds"] > 0.0
