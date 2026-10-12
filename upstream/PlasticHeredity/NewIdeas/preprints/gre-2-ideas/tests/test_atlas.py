from __future__ import annotations

from pathlib import Path

import numpy as np

from grn_reset_audit.atlas import (
    choose_matched_negative,
    choose_reconstructed_ucs,
    load_atlas_config,
    normalized_state_distance,
    state_from_payload,
    state_payload,
)
from grn_reset_audit.atlas_analysis import (
    _cluster_atlas,
    _nearest_centroid_decoder,
    _ratio_distance,
)
from grn_reset_audit.engine import State


def test_atlas_protocol_freezes_parent_and_budget():
    root = Path(__file__).resolve().parents[1]
    config = load_atlas_config(root / "configs" / "grn-observer-atlas-v1.json")
    assert config["parent_experiment_id"] == "grn-historical-washout-v4"
    assert len(config["fixed_cohort_task_ids"]) == 24
    assert config["arms"][-1] == "matched_negative"
    assert config["analysis_scope"] == "exploratory-hypothesis-generation"
    assert config["hard_cpu_seconds"] == 14100.0
    assert config["hard_wall_seconds"] == 14400.0


def test_matched_negative_uses_log_displacement_and_stable_tie():
    candidates = [
        {"action_index": 7, "valid": True, "is_broken": False, "state_displacement": 2.0},
        {"action_index": 3, "valid": True, "is_broken": False, "state_displacement": 0.5},
        {"action_index": 1, "valid": True, "is_broken": True, "state_displacement": 1.0},
        {"action_index": 0, "valid": False, "is_broken": False, "state_displacement": 1.0},
    ]
    # 0.5 and 2.0 are equally distant in log space from 1.0; lower index wins.
    assert choose_matched_negative(1.0, candidates)["action_index"] == 3


def test_reconstructed_ucs_prefers_learned_margin_then_lower_bound():
    assert choose_reconstructed_ucs(
        [
            {"bound_index": 0, "valid": True, "learned_margin": 0.4},
            {"bound_index": 1, "valid": True, "learned_margin": 0.8},
        ]
    ) == 1
    assert choose_reconstructed_ucs(
        [
            {"bound_index": 0, "valid": True, "learned_margin": 0.8},
            {"bound_index": 1, "valid": True, "learned_margin": 0.8},
        ]
    ) == 0


def test_state_payload_round_trip_and_distance():
    state = State(
        np.asarray([1.0, 2.0]),
        np.asarray([3.0]),
        np.asarray([4.0]),
        12500.0,
    )
    restored = state_from_payload(state_payload(state))
    assert restored is not None
    assert np.array_equal(restored.y, state.y)
    bounds = np.asarray([[0.0, 2.0], [0.0, 4.0]])
    assert normalized_state_distance(state.y, state.y, bounds) == 0.0
    assert state_from_payload({"y": [None], "w": [], "c": [], "t": 0, "valid": False}) is None


def test_observer_distance_ratio_has_paired_reference_scale():
    naive = np.asarray([0.0, 0.0])
    trained = np.asarray([2.0, 2.0])
    halfway = np.asarray([1.0, 1.0])
    result = _ratio_distance(halfway, naive, trained, 1.0)
    assert result["valid"]
    assert np.isclose(result["ratio"], 0.5)
    assert result["nearest"] == "trained"  # exact tie uses the conservative branch


def test_history_decoder_holds_out_entire_biomodels():
    models = {"a": 1, "b": 1, "c": 2, "d": 2}
    features = {}
    for index, task_id in enumerate(models):
        offset = index * 0.01
        features[(task_id, "naive")] = np.asarray([offset, 0.0, 0.0])
        features[(task_id, "trained_no_reset")] = np.asarray([10.0 + offset, 9.0, 8.0])
        features[(task_id, "combined_reset")] = np.asarray([0.1 + offset, 0.0, 0.0])
    result, scores = _nearest_centroid_decoder(
        features,
        models,
        ["naive", "trained_no_reset", "combined_reset"],
        permutation_replicates=100,
    )
    assert result["accuracy"] == 1.0
    assert result["reference_row_count"] == 8
    assert all(scores[(task_id, "combined_reset")] < 0 for task_id in models)


def test_cluster_gate_reports_stable_only_when_both_thresholds_pass():
    rows = []
    fields = [
        "long_reset_margin",
        "trajectory_distance_ratio",
        "state_distance_ratio",
        "counterfactual_distance_ratio",
        "relearning_margin_delta",
        "reinstatement_learned_margin",
        "responsiveness_ratio",
        "combined_control_counterfactual_ratio",
    ]
    for index in range(10):
        center = 0.0 if index < 5 else 10.0
        row = {"memory_task_id": str(index), "model_id": index}
        row.update({name: center + index * 0.001 for name in fields})
        rows.append(row)
    config = {
        "cluster_k_values": [2],
        "cluster_bootstrap_replicates": 50,
        "cluster_silhouette_min": 0.25,
        "cluster_coassignment_min": 0.70,
    }
    result = _cluster_atlas(rows, config)
    assert result["chosen_k"] == 2
    assert result["silhouette"] > 0.25
    assert result["stable"]
