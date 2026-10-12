import math

import numpy as np

from laws_confirmation.learning_math import (
    aggregate_speedup,
    detector_opportunities,
    exact_sign_flip_test,
    paired_condition,
    training_gate_projection,
    validate_training_entries,
)


def _entry(tissue, trained, region, delay, eligible, converted, pre=0):
    eligible = list(eligible)
    converted = list(converted)
    return {
        "tissue": tissue,
        "trained": trained,
        "test_region": region,
        "delay": delay,
        "eligible": sum(eligible),
        "converted": sum(converted),
        "fraction": sum(converted) / max(sum(eligible), 1),
        "pre_rewritten": pre,
        "eligible_mask": eligible,
        "converted_mask": converted,
    }


def test_detector_opportunity_count_exposes_fixed_horizon_censoring():
    assert detector_opportunities(horizon=26, run_length=8, test_generation=11)[
        "allowed_starts"
    ] == list(range(12, 19))
    assert detector_opportunities(horizon=26, run_length=8, test_generation=14)[
        "n_allowed_starts"
    ] == 4
    assert detector_opportunities(horizon=26, run_length=8, test_generation=17)[
        "allowed_starts"
    ] == [18]


def test_exact_sign_flip_enumerates_all_assignments():
    result = exact_sign_flip_test([1.0, 1.0])
    assert result["n_assignments"] == 4
    assert result["extreme_assignments"] == 2
    assert result["two_sided_p"] == 0.5


def test_paired_condition_uses_equal_tissue_and_pooled_estimands():
    entries = [
        _entry(0, True, "same", 0, [True] * 8, [True] * 4 + [False] * 4),
        _entry(0, False, "same", 0, [True] * 8, [True] * 2 + [False] * 6),
        _entry(1, True, "same", 0, [True] * 10, [True] * 2 + [False] * 8),
        _entry(1, False, "same", 0, [True] * 10, [True] + [False] * 9),
    ]
    result = paired_condition(
        entries,
        region="same",
        delay=0,
        rng=np.random.default_rng(7),
        bootstrap_draws=32,
    )
    assert result["source_equal_tissue"]["trained_rate"] == 0.35
    assert result["source_equal_tissue"]["naive_rate"] == 0.175
    assert math.isclose(
        result["pooled_common_eligible"]["effect"], (6 - 3) / 18
    )
    assert result["tissue_effect_summary"]["positive"] == 2


def test_speedup_requires_both_arrival_values():
    assert aggregate_speedup(40, 20, relative_bar=0.8)["gate"] is True
    void = aggregate_speedup(None, 17, relative_bar=0.8)
    assert void["gate"] is False
    assert void["speedup"] is None


def test_training_validation_rejects_incomplete_grid():
    row = _entry(0, True, "same", 0, [True] * 96, [False] * 96)
    result = validate_training_entries([row])
    assert result["passes"] is False
    assert result["missing_keys"]

