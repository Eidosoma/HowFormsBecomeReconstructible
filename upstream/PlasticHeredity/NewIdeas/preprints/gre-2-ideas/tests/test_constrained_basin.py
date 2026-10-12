from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.atlas import state_payload
from grn_reset_audit.constrained_basin import (
    apply_standardized_direction,
    load_constrained_basin_config,
    maximum_feasible_radius,
    project_to_feasible_cone,
    recovery_metrics,
    select_feasible_directions,
    source_decision,
    transverse_decision,
)
from grn_reset_audit.engine import State


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-constrained-basin-recovery-v1.json"


def test_protocol_freezes_condition_counts_and_four_hour_cap():
    config = load_constrained_basin_config(CONFIG)
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert config["registered_condition_count"] == 2_888
    assert sum(config["registered_record_counts"].values()) == 2_888
    assert config["geometry"]["direction_count"] == 16
    assert config["geometry"]["minimum_qualified_directions"] == 12


def test_feasible_cone_respects_active_bounds_and_fixed_components():
    projected = project_to_feasible_cone(
        [-2.0, 3.0, 4.0, 9.0],
        [0.0, 1.0, 0.5, 0.5],
        fixed=[False, False, False, True],
    )
    assert projected is not None
    assert projected[0] == 0.0
    assert projected[1] == 0.0
    assert projected[2] == pytest.approx(1.0)
    assert projected[3] == 0.0
    assert maximum_feasible_radius([0.0, 1.0, 0.5], [1.0, -1.0, 0.0]) == pytest.approx(
        np.sqrt(2.0)
    )


def test_direction_selection_is_deterministic_legal_and_low_axis_cosine():
    config = load_constrained_basin_config(CONFIG)
    first = select_feasible_directions(
        position=[0.5] * 6,
        axis=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        fixed=[False] * 6,
        radius=0.1,
        config=config,
        seed=17,
    )
    second = select_feasible_directions(
        position=[0.5] * 6,
        axis=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        fixed=[False] * 6,
        radius=0.1,
        config=config,
        seed=17,
    )
    assert first["selected_count"] == 16
    assert [row["candidate_index"] for row in first["directions"]] == [
        row["candidate_index"] for row in second["directions"]
    ]
    for row in first["directions"]:
        direction = np.asarray(row["direction"], dtype=float)
        assert np.linalg.norm(direction) == pytest.approx(1.0)
        assert abs(direction[0]) <= 0.25 + 1e-12
        assert row["maximum_feasible_radius"] >= 0.1


def test_standardized_perturbation_has_exact_norm_and_never_clips():
    base = State(
        np.asarray([0.0, 0.5]), np.asarray([3.0]), np.asarray([7.0]), 12.0
    )
    valid, actual = apply_standardized_direction(
        base,
        [1.0, 0.0],
        0.2,
        [1.0, 2.0],
        [[0.0, 1.0], [0.0, 2.0]],
        1e-8,
    )
    invalid, invalid_norm = apply_standardized_direction(
        base,
        [-1.0, 0.0],
        0.2,
        [1.0, 2.0],
        [[0.0, 1.0], [0.0, 2.0]],
        1e-8,
    )
    assert valid is not None and actual == pytest.approx(0.2)
    assert valid.y.tolist() == pytest.approx([0.2, 0.5])
    assert valid.w.tolist() == [3.0]
    assert valid.c.tolist() == [7.0]
    assert invalid is None and invalid_norm is None


def _result_row(task_id: str, arm: str, y0: float, y1: float, fp: float) -> dict:
    checkpoints = {
        key: {"state": state_payload(State(np.asarray([value]), np.asarray([]), np.asarray([]), 0.0))}
        for key, value in (("0", y0), ("250", y1), ("2500", y1), ("12500", y1))
    }
    return {
        "task_id": f"row|{task_id}|{arm}|{y0}",
        "condition_id": "condition",
        "assay": "axial",
        "memory_task_id": task_id,
        "seed_index": 0,
        "arm": arm,
        "valid": True,
        "checkpoints": checkpoints,
        "fingerprint": [fp],
        "bipolar_score": -1.0 if arm == "low" else 1.0,
    }


def test_recovery_metrics_use_matched_no_op_drift():
    config = copy.deepcopy(load_constrained_basin_config(CONFIG))
    reference = _result_row("x", "low", 1.0, 2.0, 0.0)
    reference["assay"] = "no-op"
    perturbed = _result_row("x", "low", 1.4, 2.05, 0.1)
    geometry = {"models": [{"memory_task_id": "x", "scale": [1.0]}]}
    metrics = recovery_metrics([reference], [[perturbed]], geometry, config)
    assert len(metrics) == 1
    assert metrics[0]["initial_distance"] == pytest.approx(0.4)
    assert metrics[0]["final_distance"] == pytest.approx(0.05)
    assert metrics[0]["contraction_ratio"] == pytest.approx(0.125)
    assert metrics[0]["returned"] is True


def _decision_config() -> dict:
    config = copy.deepcopy(load_constrained_basin_config(CONFIG))
    config["exposure_task_ids"] = ["x"]
    config["validation_seed_indices"] = [0, 1, 2, 3]
    config["node_counts"] = {"x": 2}
    return config


def _transverse_metrics(mode: str) -> list[dict]:
    rows = []
    for multiplier in (0.25, 0.5, 1.0):
        for seed in range(4):
            for arm in ("low", "high"):
                for index in range(16):
                    returned = mode == "robust" or (mode == "limited" and multiplier == 0.25)
                    switched = mode == "switch" and multiplier == 1.0 and index < 4
                    persistent = mode == "persistent" and multiplier == 1.0
                    rows.append(
                        {
                            "task_id": f"metric|{multiplier}|{seed}|{arm}|{index}",
                            "assay": "transverse",
                            "memory_task_id": "x",
                            "seed_index": seed,
                            "arm": arm,
                            "radius_multiplier": multiplier,
                            "valid": True,
                            "returned": returned,
                            "switched": switched,
                            "same_arm": not switched,
                            "contraction_ratio": 0.1 if returned else 1.0 if persistent else 0.5,
                        }
                    )
    return rows


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("robust", "robust-constrained-basin-compatible"),
        ("limited", "radius-limited-basin-compatible"),
        ("switch", "switch-prone"),
        ("persistent", "persistent-without-restoration"),
    ],
)
def test_transverse_classifications_are_ordered_and_frozen(mode: str, expected: str):
    config = _decision_config()
    geometry = {
        "models": [
            {
                "memory_task_id": "x",
                "eligible": True,
                "selected_radius_fraction": 0.01,
            }
        ]
    }
    decision = transverse_decision(_transverse_metrics(mode), geometry, config)
    assert decision["candidate_summaries"][0]["classification"] == expected


def test_geometrically_unavailable_task_is_classified_not_dropped():
    config = _decision_config()
    geometry = {
        "models": [
            {
                "memory_task_id": "x",
                "eligible": False,
                "selected_radius_fraction": None,
            }
        ]
    }
    decision = transverse_decision([], geometry, config)
    assert decision["candidate_summaries"][0]["classification"] == "constraint-corner-pinned"


def test_source_gate_requires_all_registered_no_ops():
    config = _decision_config()
    records = []
    for seed in range(4):
        for arm in ("low", "high"):
            records.append(
                {
                    "memory_task_id": "x",
                    "seed_index": seed,
                    "arm": arm,
                    "valid": True,
                    "correct_source_arm": True,
                    "source_fingerprint_distance": 0.01,
                }
            )
    assert source_decision(records, config)["pass"] is True
    records.pop()
    assert source_decision(records, config)["pass"] is False
