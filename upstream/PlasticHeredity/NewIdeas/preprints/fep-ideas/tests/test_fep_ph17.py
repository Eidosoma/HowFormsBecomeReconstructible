from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from fep_lab.integrity import read_json, verify_seal
from fep_ph17.campaign import run_all, status
from fep_ph17.config import (
    EPISTEMIC_MAX_SHAM_SHIFT,
    EPISTEMIC_MIN_ENTROPY_GAP,
    EPISTEMIC_MIN_INFORMATION_UPLIFT,
    EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL,
    MAX_WORKERS,
    MECHANISM_KEYS,
    SCALE_PAIRS,
    profile_config,
)
from fep_ph17.controllers import exact_multiset_yoke
from fep_ph17.data import (
    development_cell,
    development_conditions,
    stage_a_conditions,
    stage_b_conditions,
)
from fep_ph17.hybrid_model import expected_regime_information, fit_projection
from fep_ph17.tuning import tuning_row_eligible
from fep_ph17.validation import _synthetic_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def test_frozen_factorials_and_blanket_feature_firewall() -> None:
    config = profile_config("smoke")
    full = profile_config("full")
    assert MAX_WORKERS == full.workers == 4
    assert full.wall_time_limit_seconds == 16 * 60 * 60
    assert full.registration_projection_ceiling_seconds == 14 * 60 * 60
    assert SCALE_PAIRS[-1] == (12, 12)
    development = development_conditions(SCREEN)
    stage_a = stage_a_conditions(SCREEN)
    stage_b = stage_b_conditions(SCREEN, 1.0)
    assert len(development) == 4
    assert len(stage_a) == 10
    assert len(stage_b) == 4
    assert {value.mechanism_key for value in stage_a} == set(MECHANISM_KEYS)
    assert {value.authority_scale for value in stage_a} == {0.0, 1.0, 1.5}
    assert {str(value.information_arm) for value in stage_b} == {
        "informative",
        "sham",
    }

    arrays, metadata = development_cell(config, development[0])
    assert arrays["coarse_features"].shape[1] == 51
    assert arrays["rich_features"].shape[1] == 152
    assert arrays["coarse_targets"].shape[1] == 12
    assert arrays["rich_targets"].shape[1] == 112
    assert set(np.unique(arrays["action"])) == {0, 1, 2, 3}
    assert metadata["learned_feature_firewall"] == [
        "true_regime",
        "beta",
        "rng_state",
        "f12",
        "strict8",
    ]


def test_scientific_scale_full_svd_is_bitwise_deterministic() -> None:
    # This reproduces the 800 x 100 scale at which randomized PCA broke the
    # original Experiment 1 replay. The FEP-PH1.7 solver is deterministic full
    # SVD with canonical component signs.
    data = _synthetic_data(8, rows_per_matrix=100)
    first = fit_projection(data, 12)
    second = fit_projection(data, 12)
    assert np.array_equal(first.mean, second.mean)
    assert np.array_equal(first.components, second.components)
    pivots = np.argmax(np.abs(first.components), axis=1)
    assert np.all(first.components[np.arange(12), pivots] >= 0.0)


def test_information_specificity_and_exact_timing_yoke() -> None:
    belief = np.asarray((0.45, 0.45, 0.10), dtype=np.float64)
    sham = expected_regime_information(belief, 0.25, 0.05, 0.50)
    informative = expected_regime_information(belief, 0.25, 0.05, 0.98)
    assert 0.0 <= sham < informative <= 1.0

    actions = np.asarray((0, 3, 1, 2, 3, 3, 0, 2, 1, 0), dtype=np.int8)
    yoked = exact_multiset_yoke(actions, 17_701)
    assert np.array_equal(
        np.bincount(actions, minlength=4),
        np.bincount(yoked, minlength=4),
    )
    assert not np.shares_memory(actions, yoked)


def test_epistemic_tuning_requires_bounded_information_specific_activation() -> None:
    lower, upper = EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL
    qualifying = {
        "pooled_informative_sample_probability": (lower + upper) / 2.0,
        "informative_minus_sham_sample_probability": EPISTEMIC_MIN_INFORMATION_UPLIFT,
        "high_minus_low_informative_sample_probability": EPISTEMIC_MIN_ENTROPY_GAP,
        "sham_shift_from_pragmatic": EPISTEMIC_MAX_SHAM_SHIFT,
    }
    assert tuning_row_eligible(qualifying)
    for key, invalid in (
        ("pooled_informative_sample_probability", upper + 0.01),
        ("informative_minus_sham_sample_probability", EPISTEMIC_MIN_INFORMATION_UPLIFT - 0.01),
        ("high_minus_low_informative_sample_probability", EPISTEMIC_MIN_ENTROPY_GAP - 0.01),
        ("sham_shift_from_pragmatic", EPISTEMIC_MAX_SHAM_SHIFT + 1.0e-8),
    ):
        row = dict(qualifying)
        row[key] = invalid
        assert not tuning_row_eligible(row)


def test_all_path_smoke_replays_exactly(tmp_path: Path) -> None:
    # The non-full gate override exists only so this test exercises the entire
    # conditional Stage B implementation. It has no scientific classifier.
    config = replace(
        profile_config("smoke"),
        horizon=4,
        bootstrap_repetitions=16,
        legacy_oracle_depth=1,
        goal_short_depth=1,
        goal_long_depth=2,
        goal_long_beam=4,
        goal_long_replicas=1,
        hybrid_depth=1,
        hybrid_beam=4,
    )
    run_root = tmp_path / "runs-fep-ph17"
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
    tuning = read_json(root / "fit" / "epistemic-tuning.json")
    assert tuning["schema"] == "fep-ph17-epistemic-tuning-v2"
    assert tuning["selection_uses_counterfactual_sham_observation_kernel"] is True
    for stage in ("development-replay", "fit-replay", "stage-a-replay", "stage-b-replay"):
        assert read_json(root / stage / "replay.json")["all_exact"] is True
    gate = read_json(root / "stage-a-analysis" / "gate.json")
    assert gate["passed"] is True
    assert gate["workflow_only_override"] is True
    assert read_json(root / "stage-b-registration.json")["action"] == "RUN"
    metrics = read_json(root / "analysis" / "metrics.json")
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_status"] == "WORKFLOW_ONLY"
    assert metrics["decision"]["positive_negative_classifier"] is None
    assert metrics["decision"]["reduced_power_scale"] is True
    assert metrics["matrix_controller_rows"] == 4 * 8

    observed = status(run_root, "smoke")
    assert observed["current_stage"] == "complete"
    assert observed["registered_source_current"] is True
    assert observed["stage_a_cells_present"] == 10
    assert observed["stage_b_cells_present"] == 4
