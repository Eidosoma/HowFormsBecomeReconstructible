import json
from pathlib import Path

import pytest

from laws_confirmation.l5_audit import _recursive_close
from laws_confirmation.selfhood_math import (
    bootstrap_mean_interval,
    direction_counts,
    recalculate_e26_regeneration,
    recalculate_e26_screen,
)


def test_direction_counts_keeps_ties_visible():
    assert direction_counts([-2, 0, 3, 4]) == {
        "positive": 2,
        "ties": 1,
        "negative": 1,
        "n": 4,
    }


def test_bootstrap_contract_is_deterministic_and_row_level():
    first = bootstrap_mean_interval([1.0, 2.0, 3.0], seed=7, draws=32)
    second = bootstrap_mean_interval([1.0, 2.0, 3.0], seed=7, draws=32)
    assert first == second
    assert first["unit"] == "retained tissue row"
    assert first["n_units"] == 3
    assert first["draws"] == 32
    assert first["mean"] == 2.0


def test_screen_recalculation_separates_reconstructable_components():
    row = {
        "overrides": {"coupling": 1.0, "sigma": 0.3, "activity_budget": 64},
        "criteria": {
            "h_straddles": True,
            "multi_attractor": True,
            "survival": True,
            "break_dispersion": True,
            "clock_alive": True,
            "parental_inheritance": True,
            "pass": True,
        },
        "h_above": 0.3,
        "h_below": 0.05,
        "distinct_pairs": 3,
        "median_survival": 0.3,
        "fragment_h": 0.92,
        "random_fragment_h": 0.90,
    }
    result = recalculate_e26_screen(
        {
            "grid": [row],
            "n_passing": 1,
            "gate_regime_exists": True,
            # A one-cell grid has no interior coupling, so this is false.
            "gate_coupling_sweet_spot": False,
            "best": row["overrides"],
        }
    )
    assert result["stored_grid_gates_match"]
    assert result["row_reconstruction"]["reconstructable_component_matches"] == 4
    assert len(result["row_reconstruction"]["missing_lower_level_fields"]) == 2


def test_regeneration_recalculation_uses_retained_seed_means():
    payload = {
        "fragment": {
            "mean_h": 0.95,
            "per_seed_h": [0.94, 0.96],
            "survival_8": 0.8,
        },
        "random_fragment": {
            "mean_h": 0.90,
            "per_seed_h": [0.91, 0.89],
            "survival_8": 0.7,
        },
        "gate_regeneration": True,
    }
    result = recalculate_e26_regeneration(payload)
    assert result["stored_gate_matches"]
    assert result["fragment_minus_random_mean"] == pytest.approx(0.05)
    assert result["per_seed_index_directions"]["positive"] == 2
    assert result["paired_trajectory_streams"] is False


def test_recursive_close_handles_nested_numeric_roundoff():
    assert _recursive_close(
        {"x": [1.0, {"gate": False}]},
        {"x": [1.0 + 1e-14, {"gate": False}]},
    )
    assert not _recursive_close({"gate": False}, {"gate": 0})


def test_retained_e26_screen_and_regeneration_reconstruct():
    ideas = Path(__file__).resolve().parents[2]
    root = ideas / "voltage_web/results/full"
    screen = json.loads((root / "screen.json").read_text(encoding="utf-8"))
    regeneration = json.loads(
        (root / "regeneration.json").read_text(encoding="utf-8")
    )
    screen_result = recalculate_e26_screen(screen)
    regeneration_result = recalculate_e26_regeneration(regeneration)
    assert screen_result["stored_grid_gates_match"]
    assert screen_result["calculated"]["n_passing"] == 1
    assert regeneration_result["stored_gate_matches"]
    assert regeneration_result["per_seed_index_directions"] == {
        "positive": 11,
        "ties": 0,
        "negative": 5,
        "n": 16,
    }
