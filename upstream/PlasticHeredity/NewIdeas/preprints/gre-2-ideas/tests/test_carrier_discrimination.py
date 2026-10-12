from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.carrier_discrimination import (
    EXPECTED_COUNTS,
    TASK_10,
    TASK_37,
    load_carrier_discrimination_config,
    matched_control_slots,
    neutral_37_decision,
    neutral_direction_slots,
    state_at_dose,
    switch_10_decision,
)
from grn_reset_audit.engine import State


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-causal-carrier-discrimination-v2.json"
REPAIR_CONFIG = ROOT / "configs" / "grn-causal-carrier-discrimination-v2r.json"


def _state(y: list[float]) -> State:
    return State(np.asarray(y, dtype=float), np.asarray([1.0]), np.asarray([2.0]), 10.0)


def _model(dimension: int = 4) -> dict:
    return {
        "scale": [1.0] * dimension,
        "ranked_nodes": list(range(dimension)),
        "anti_ranked_nodes": [dimension - 1],
        "memory_axis": [1.0] + [0.0] * (dimension - 1),
        "tangent_basis": np.eye(dimension)[:, :2].tolist(),
        "observer_map": {"matrix": np.asarray([[1.0] + [0.0] * (dimension - 1)]).tolist()},
    }


def test_protocol_freezes_counts_seed_split_and_four_hour_cap():
    config = load_carrier_discrimination_config(CONFIG)
    assert config["fresh_seed_indices"] == list(range(216, 224))
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert config["registered_record_counts"] == EXPECTED_COUNTS
    assert config["registered_condition_count"] == 3_384
    assert sum(EXPECTED_COUNTS.values()) == 3_384


def test_repair_protocol_uses_a_new_untouched_cohort():
    config = load_carrier_discrimination_config(REPAIR_CONFIG)
    assert config["experiment_id"] == "grn-causal-carrier-discrimination-v2r"
    assert config["fresh_seed_indices"] == list(range(224, 232))
    assert config["registered_record_counts"] == EXPECTED_COUNTS
    assert config["hard_wall_seconds"] == 9_600.0
    assert config["hard_aggregate_cpu_seconds"] == 40_000.0


def test_fractional_coordinate_intervention_is_exact_and_does_not_clip():
    recipient = _state([0.2, 0.4, 0.6, 0.8])
    donor = _state([0.8, 0.1, 0.9, 0.3])
    result, detail = state_at_dose(recipient, donor, "top-ranked-1", 0.25, _model())
    assert result is not None
    assert result.y == pytest.approx([0.35, 0.4, 0.6, 0.8])
    assert result.w == pytest.approx(recipient.w)
    assert detail["coefficient_fraction"] == 0.25
    assert detail["effective_dimension"] == 1


def test_memory_axis_preserves_registered_sign_and_fraction():
    recipient = _state([0.8, 0.4, 0.6, 0.8])
    donor = _state([0.2, 0.1, 0.9, 0.3])
    result, _ = state_at_dose(recipient, donor, "memory-axis", 0.5, _model())
    assert result is not None
    assert result.y == pytest.approx([0.5, 0.4, 0.6, 0.8])


def test_matched_controls_are_deterministic_norm_matched_and_observer_quiet():
    config = load_carrier_discrimination_config(CONFIG)
    recipient = _state([0.5, 0.5, 0.5, 0.5])
    donor = _state([0.9, 0.5, 0.5, 0.5])
    first = matched_control_slots(
        config,
        recipient,
        donor,
        _model(),
        np.asarray([[0.0, 1.0]] * 4),
        216,
        "low",
        0.1,
    )
    second = matched_control_slots(
        config,
        recipient,
        donor,
        _model(),
        np.asarray([[0.0, 1.0]] * 4),
        216,
        "low",
        0.1,
    )
    assert len(first) == 8
    assert [row.get("candidate_index") for row in first] == [row.get("candidate_index") for row in second]
    assert all(row["available"] for row in first)
    assert all(row["target_norm"] == pytest.approx(0.04) for row in first)
    assert all(row["carrier_cosine"] <= 0.25 for row in first)
    assert all(row["observer_fraction"] <= 0.25 for row in first)


def test_neutral_direction_registration_has_16_tangent_and_16_normal_slots():
    config = load_carrier_discrimination_config(CONFIG)
    state = _state([0.5, 0.5, 0.5, 0.5])
    slots = neutral_direction_slots(
        config,
        state,
        _model(),
        np.asarray([[0.0, 1.0]] * 4),
        np.diag([-0.01, 0.0, -1.0, -2.0]),
        1.0,
        216,
        "low",
    )
    assert len(slots) == 32
    assert sum(row["kind"] == "tangent" for row in slots) == 16
    assert sum(row["kind"] == "normal" for row in slots) == 16
    assert all(row["available"] for row in slots)
    for row in slots:
        direction = np.asarray(row["direction"])
        assert np.linalg.norm(direction) == pytest.approx(1.0)
        if row["kind"] == "tangent":
            assert row["tangent_projection"] >= 0.8
        else:
            assert row["tangent_projection"] <= 0.25


def _metric(seed: int, direction: str, condition: str, dose: float, success: bool) -> dict:
    recipient = direction.split("-to-")[0]
    return {
        "task_id": f"metric-{seed}-{direction}-{condition}-{dose}",
        "memory_task_id": TASK_10,
        "seed_index": seed,
        "recipient_arm": recipient,
        "condition": condition,
        "dose": dose,
        "valid": True,
        "target_oriented_bipolar_score": 1.0 if success else -1.0,
        "target_fingerprint_rms": 0.0 if success else 1.0,
    }


def test_switch_decision_detects_directional_and_component_nonmonotonicity():
    config = load_carrier_discrimination_config(CONFIG)
    rows = []
    for condition in config["switch_10"]["conditions"]:
        for direction in ("low-to-high", "high-to-low"):
            for dose_index, dose in enumerate(config["switch_10"]["doses"]):
                for seed in config["fresh_seed_indices"]:
                    success = condition == "top-ranked-1" and direction == "low-to-high" and dose_index in (2, 3)
                    rows.append(_metric(seed, direction, condition, float(dose), success))
    decision = switch_10_decision(rows, config)
    assert decision["asymmetric"]
    assert any(row["kind"] == "dose-increase-removes-transfer" for row in decision["nonmonotone_events"])
    assert decision["classification"] == "asymmetric-nonmonotone-switch"


def test_neutral_decision_separates_tangent_persistence_from_normal_contraction():
    config = load_carrier_discrimination_config(CONFIG)
    rows = []
    for seed in config["fresh_seed_indices"]:
        for arm in ("low", "high"):
            for kind, ratio in (("tangent", 1.0), ("normal", 0.1)):
                for radius in config["neutral_37"]["radii"]:
                    rows.append(
                        {
                            "task_id": f"g-{seed}-{arm}-{kind}-{radius}",
                            "memory_task_id": TASK_37,
                            "seed_index": seed,
                            "arm": arm,
                            "direction_kind": kind,
                            "radius_fraction": radius,
                            "final_distance_ratio": ratio,
                            "checkpoint_distance_ratios": {"25": ratio, "250": ratio, "2500": ratio, "12500": ratio},
                            "behavior_returned": True,
                            "valid": True,
                        }
                    )
    bridge = []
    for seed in config["fresh_seed_indices"]:
        for alpha in config["neutral_37"]["bridge_alphas"]:
            bridge.append(
                {
                    "task_id": f"b-{seed}-{alpha}",
                    "seed_index": seed,
                    "alpha": alpha,
                    "bipolar_score": 2.0 * alpha - 1.0,
                    "valid": True,
                }
            )
    decision = neutral_37_decision(rows, bridge, config)
    assert decision["tangent_persists"]
    assert decision["normal_contracts"]
    assert decision["classification"] == "curved-neutral-sheet-with-contracting-walls"


def test_protocol_rejects_worker_or_record_count_drift(tmp_path: Path):
    payload = copy.deepcopy(load_carrier_discrimination_config(CONFIG))
    payload["max_workers"] = 5
    path = tmp_path / "bad.json"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="four"):
        load_carrier_discrimination_config(path)
