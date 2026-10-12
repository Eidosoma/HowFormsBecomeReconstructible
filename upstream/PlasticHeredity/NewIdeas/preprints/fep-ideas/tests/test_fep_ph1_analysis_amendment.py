from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


AMENDMENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "amend_fep_ph1_constant_correlation.py"
)
SPEC = importlib.util.spec_from_file_location("fep_ph1_analysis_amendment", AMENDMENT_PATH)
assert SPEC is not None and SPEC.loader is not None
AMENDMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AMENDMENT)


def test_safe_spearman_preserves_defined_calculation() -> None:
    result = AMENDMENT._safe_spearman(
        np.asarray([1.0, 2.0, 3.0, 4.0]),
        np.asarray([4.0, 3.0, 2.0, 1.0]),
    )
    assert result["rho"] == pytest.approx(-1.0)
    assert result["p_exploratory"] == pytest.approx(0.0)
    assert result["pairs"] == 4
    assert result["undefined_reason"] is None


@pytest.mark.parametrize(
    ("predictor", "outcome", "reason"),
    [
        ([1.0, 1.0, 1.0], [1.0, 2.0, 3.0], "constant_probe"),
        ([1.0, 2.0, 3.0], [2.0, 2.0, 2.0], "constant_outcome"),
        ([1.0, np.nan, 3.0], [1.0, 2.0, 3.0], "insufficient_pairs"),
    ],
)
def test_safe_spearman_records_undefined_as_null(
    predictor: list[float], outcome: list[float], reason: str
) -> None:
    result = AMENDMENT._safe_spearman(np.asarray(predictor), np.asarray(outcome))
    assert result["rho"] is None
    assert result["p_exploratory"] is None
    assert result["undefined_reason"] == reason


def test_amended_dynamic_correlations_treats_outcomes_independently() -> None:
    rows = []
    for matrix_id in range(4):
        common = {
            "matrix_id": matrix_id,
            "candidate": "02",
            "family": "nutrient",
            "channel": "uptake",
            "regime": "s1-slow",
            "amplification_probe": float(matrix_id),
        }
        rows.append(
            {
                **common,
                "controller": "ai_pooled",
                "completion_fraction": 0.5,
                "inherited_fixed_fraction": 0.1 * matrix_id,
            }
        )
        rows.append(
            {
                **common,
                "controller": "noop",
                "completion_fraction": 0.25,
                "inherited_fixed_fraction": 0.0,
            }
        )
    result = AMENDMENT.amended_dynamic_correlations(rows)[0]
    assert result["viability_rho"] is None
    assert result["viability_undefined_reason"] == "constant_outcome"
    assert result["heredity_rho"] == pytest.approx(1.0)
    assert result["heredity_undefined_reason"] is None


def test_amended_dynamic_correlations_preserves_original_defined_values() -> None:
    rows = []
    for matrix_id in range(5):
        common = {
            "matrix_id": matrix_id,
            "candidate": "03",
            "family": "catalytic",
            "channel": "molecular",
            "regime": "s2-fast",
            "amplification_probe": float(matrix_id),
        }
        rows.append(
            {
                **common,
                "controller": "ai_pooled",
                "completion_fraction": 0.4 + 0.02 * matrix_id,
                "inherited_fixed_fraction": 0.3 - 0.01 * matrix_id,
            }
        )
        rows.append(
            {
                **common,
                "controller": "noop",
                "completion_fraction": 0.2,
                "inherited_fixed_fraction": 0.1,
            }
        )
    original = AMENDMENT.original_analysis._dynamic_correlations(rows)[0]
    amended = AMENDMENT.amended_dynamic_correlations(rows)[0]
    for name in (
        "viability_rho",
        "viability_p_exploratory",
        "heredity_rho",
        "heredity_p_exploratory",
    ):
        assert amended[name] == pytest.approx(original[name])
