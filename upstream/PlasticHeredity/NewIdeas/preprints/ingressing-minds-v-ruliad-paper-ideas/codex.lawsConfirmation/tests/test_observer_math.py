import numpy as np

from laws_confirmation.observer_math import (
    coverage_diagnostics,
    e25_gate_recalculation,
    e28_gate_recalculation,
    e63_criteria,
    nearest_centroid_accuracy,
    screen_census,
)


def test_nearest_centroid_accuracy_uses_test_partition_only():
    features = np.array([[0.0], [0.1], [0.9], [1.0]])
    labels = np.array([0, 0, 1, 1])
    train = np.array([True, False, True, False])
    assert nearest_centroid_accuracy(features, labels, train) == 1.0


def test_e25_recalculates_positive_and_failed_controls():
    rows = [
        {"rule": 110, "strict": 0.02},
        {"rule": 54, "strict": 0.03},
        {"rule": 18, "strict": 0.06},
        {"rule": 35, "strict": 0.04},
        {"rule": 57, "strict": 0.003},
    ]
    result = e25_gate_recalculation(
        rows, class4=(110, 54), core3=(18,), champions=(35, 57)
    )
    assert result["gate_redemption_110"]
    assert result["all_four_class4_in_band"]
    assert not result["gate_chaos_stays_chaos"]
    assert not result["gate_champions_stable"]


def test_coverage_diagnostics_separates_necessity_from_sufficiency():
    rows = [
        {"coverage": 0.95, "dictionary_size": 4, "strict": 0.02},
        {"coverage": 0.92, "dictionary_size": 8, "strict": 0.0},
        {"coverage": 0.60, "dictionary_size": 64, "strict": 0.0},
    ]
    result = coverage_diagnostics(rows)
    assert result["capable_among_target_missed"] == 0
    assert result["capable_among_target_achieved"] == 1
    assert result["n_target_achieved"] == 2


def test_e28_gate_components_are_recomputed():
    payload = {
        "gate1": {
            "raw_accuracy": 0.2,
            "figure_accuracy": 0.1,
            "per_tissue_raw": [0.2, 0.2],
            "per_tissue_figure": [0.1, 0.1],
        },
        "gate2": {
            "rho_coverage_vs_capability": -0.1,
            "null_q95": 0.2,
            "n_tissues": 80,
        },
        "gate3": {
            "ladder": {
                "0": {"mean_h": 0.95, "figure_in": 0.05},
                "4": {"mean_h": 0.90, "figure_in": 0.3,
                      "patch_h": 0.8, "rest_h": 0.9},
            }
        },
        "gates": {
            "gate_memory_at_boundaries": False,
            "gate_compressibility_law": False,
            "gate_decoupled_tumor": True,
        },
    }
    result = e28_gate_recalculation(payload)
    assert result["all_stored_gates_match"]
    assert result["gate3_components"]["whole_fidelity_nonincreasing"]


def test_e63_registered_and_revised_criteria_diverge():
    row = {
        "clone_bar": 0.99,
        "clone_dt_mean": 0.97,
        "clone_noise_mean": 0.95,
        "within_mean": 0.82,
        "same_tissue_mean": 0.78,
        "n_within": 960,
        "gap_within_minus_same_ci90": [0.03, 0.05],
    }
    result = e63_criteria(row)
    assert not result["registered"]["instrumented"]
    assert not result["registered"]["individuality"]
    assert result["round4_revision"]["instrumented"]
    assert result["round4_revision"]["individuality"]


def test_screen_census_does_not_conflate_no_pass_with_uninstrumented():
    rows = [
        {"h_above": 0.1, "instrumented": True, "pass": False},
        {"h_above": 0.4, "instrumented": False, "pass": False},
        {"pass": False, "reason": "all dead"},
    ]
    result = screen_census(rows)
    assert result["n_passing"] == 0
    assert result["n_instrumented"] == 1
    assert result["n_explicitly_uninstrumented"] == 1
    assert result["n_without_instrument_decision"] == 1
