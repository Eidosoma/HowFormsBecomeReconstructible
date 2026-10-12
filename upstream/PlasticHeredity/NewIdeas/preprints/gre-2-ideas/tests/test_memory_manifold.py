from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.atlas import state_payload
from grn_reset_audit.engine import State
from grn_reset_audit.memory_manifold import (
    _local_spectrum,
    build_plane_selections,
    common_nullspace,
    fit_linear_map,
    load_memory_manifold_config,
    manifold_decision,
    orthogonal_complement,
    projection_fraction,
    recovery_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-memory-manifold-v1.json"


def test_protocol_freezes_split_counts_and_four_hour_cap():
    config = load_memory_manifold_config(CONFIG)
    assert config["discovery_seed_indices"] == [204, 205]
    assert config["validation_seed_indices"] == [206, 207]
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert config["registered_condition_count"] == 2_784
    assert sum(config["registered_record_counts"].values()) == 2_784
    assert config["registered_record_counts"]["mode-plane.jsonl"] == 2_016


def test_common_nullspace_distinguishes_point_and_line_attractors():
    point_basis, point_singular = common_nullspace([np.diag([-1.0, -2.0])])
    line_basis, line_singular = common_nullspace([np.diag([-2.0, 0.0])])
    assert point_basis.shape == (2, 0)
    assert point_singular.tolist() == pytest.approx([2.0, 1.0])
    assert line_basis.shape == (2, 1)
    assert abs(float(line_basis[:, 0] @ np.asarray([0.0, 1.0]))) == pytest.approx(1.0)
    assert line_singular.tolist() == pytest.approx([2.0, 0.0])


def test_structural_quotient_is_basis_rotation_and_scale_invariant():
    basis = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    rotation = np.asarray(
        [[math.cos(0.4), -math.sin(0.4)], [math.sin(0.4), math.cos(0.4)]]
    )
    rotated = basis @ rotation @ np.diag([3.0, 0.5])
    complement = orthogonal_complement(rotated, 3)
    assert complement.shape == (3, 1)
    assert abs(float(complement[:, 0] @ np.asarray([0.0, 0.0, 1.0]))) == pytest.approx(1.0)
    assert projection_fraction([1.0, 1.0, 0.0], basis) == pytest.approx(1.0)
    assert projection_fraction([0.0, 0.0, 1.0], rotated) == pytest.approx(0.0)


def test_nonnormal_stable_system_is_not_called_locally_unstable():
    spectrum = _local_spectrum(np.asarray([[-1.0, 30.0], [0.0, -2.0]]), 1e-7)
    assert spectrum["positive_mode_count"] == 0
    assert spectrum["negative_mode_count"] == 2
    assert spectrum["departure_from_normality"] > 0.0


def test_finite_time_map_recovers_known_linear_operator():
    operator = np.asarray([[0.1, 0.3], [0.0, 0.8]])
    x = np.asarray([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.5]])
    y = x @ operator.T
    fitted = fit_linear_map(x, y, [1e-12, 1e-8], 2)
    assert np.asarray(fitted["matrix"]) == pytest.approx(operator, abs=1e-7)
    assert fitted["sample_count"] == 4


def _checkpoint(value: list[float]) -> dict:
    return {
        key: {
            "state": state_payload(
                State(np.asarray(value, dtype=float), np.asarray([]), np.asarray([]), 0.0)
            )
        }
        for key in ("0", "250", "2500", "12500")
    }


def test_recovery_metrics_keep_full_and_structural_return_separate():
    config = load_memory_manifold_config(CONFIG)
    low = {
        "task_id": "noop-low",
        "memory_task_id": "37-10-41",
        "seed_index": 206,
        "arm": "low",
        "valid": True,
        "fingerprint": [-1.0],
        "checkpoints": _checkpoint([0.0, 0.0]),
    }
    high = {
        "task_id": "noop-high",
        "memory_task_id": "37-10-41",
        "seed_index": 206,
        "arm": "high",
        "valid": True,
        "fingerprint": [1.0],
        "checkpoints": _checkpoint([4.0, 0.0]),
    }
    perturbed = {
        "task_id": "target",
        "assay": "targeted-ray",
        "memory_task_id": "37-10-41",
        "seed_index": 206,
        "seed_role": "validation",
        "arm": "low",
        "direction_kind": "invariant-memory-aligned",
        "radius_fraction": 0.01,
        "valid": True,
        "fingerprint": [-1.0],
        "bipolar_score": -1.0,
        "checkpoints": {
            **_checkpoint([1.0, 1.0]),
            "12500": {
                "state": state_payload(
                    State(np.asarray([0.1, 1.0]), np.asarray([]), np.asarray([]), 0.0)
                )
            },
        },
    }
    structural = {
        "models": [
            {
                "memory_task_id": "37-10-41",
                "scale": [1.0, 1.0],
                "structural_invariant_basis": [[0.0], [1.0]],
            }
        ]
    }
    metric = recovery_metrics([perturbed], [low, high], structural, config)[0]
    assert metric["full_returned"] is False
    assert metric["quotient_returned"] is True
    assert metric["quotient_contraction_ratio"] == pytest.approx(0.1)
    assert metric["functional_returned"] is True


def _decision_structural(overlap: float) -> dict:
    return {
        "models": [
            {
                "memory_task_id": task,
                "structural_invariant_dimension": 1,
                "memory_axis_invariant_fraction": overlap if task == "37-10-41" else 0.1,
                "no_local_positive_mode": True,
            }
            for task in ("37-10-41", "204-5-10", "10-1-32")
        ]
    }


def _source() -> dict:
    return {
        "candidate_summaries": [
            {"memory_task_id": task, "pass": True}
            for task in ("37-10-41", "204-5-10", "10-1-32")
        ]
    }


def _decision_metrics(mode: str) -> list[dict]:
    rows = []
    for task in ("37-10-41", "204-5-10", "10-1-32"):
        task_mode = mode if task == "37-10-41" else "mixed"
        for seed in (206, 207):
            for arm in ("low", "high"):
                for direction in (
                    "invariant-memory-aligned",
                    "fastest-contracting",
                    "slowest-non-invariant",
                    "switch-predictive",
                ):
                    stable = direction in {"fastest-contracting", "slowest-non-invariant"}
                    invariant = direction == "invariant-memory-aligned"
                    quotient = task_mode in {"manifold", "passive"} and (stable or invariant)
                    full = task_mode == "point" and (stable or invariant)
                    functional = task_mode in {"manifold", "passive", "point", "observer"}
                    switched = task_mode == "switch" and direction == "switch-predictive"
                    rows.append(
                        {
                            "task_id": f"metric-{task}-{seed}-{arm}-{direction}",
                            "source_task_id": "source",
                            "assay": "targeted-ray",
                            "memory_task_id": task,
                            "seed_index": seed,
                            "seed_role": "validation",
                            "arm": arm,
                            "direction_kind": direction,
                            "radius_fraction": 0.0025,
                            "valid": True,
                            "quotient_returned": quotient,
                            "full_returned": full,
                            "functional_returned": functional and not switched,
                            "full_contraction_ratio": 0.1 if full else 1.0,
                            "switched": switched,
                        }
                    )
    return rows


@pytest.mark.parametrize(
    ("mode", "overlap", "expected"),
    [
        ("manifold", 0.2, "normally-attracting-memory-manifold"),
        ("passive", 0.9, "passive-neutral-register"),
        ("point", 0.2, "point-attractor-compatible"),
        ("observer", 0.2, "observer-equivalent-sheet"),
        ("switch", 0.2, "nonlinear-switch-sheet"),
    ],
)
def test_decision_categories_are_mutually_operational(mode: str, overlap: float, expected: str):
    config = copy.deepcopy(load_memory_manifold_config(CONFIG))
    result = manifold_decision(
        _decision_metrics(mode), [], _decision_structural(overlap), _source(), config
    )
    lead = next(row for row in result["candidate_summaries"] if row["memory_task_id"] == "37-10-41")
    assert lead["classification"] == expected


def test_plane_confirmation_selection_is_deterministic_and_unique():
    config = copy.deepcopy(load_memory_manifold_config(CONFIG))
    config["focal_task_ids"] = ["37-10-41"]
    config["all_seed_indices"] = [204]
    rows = []
    for index in range(5):
        rows.append(
            {
                "task_id": f"metric-{index}",
                "source_task_id": f"plane-{index}",
                "memory_task_id": "37-10-41",
                "seed_index": 204,
                "arm": "low",
                "valid": True,
                "angle_index": index,
                "radius_fraction": 0.01 * (index + 1),
                "quotient_returned": index % 2 == 0,
                "same_arm_geometric": index < 3,
                "switched_geometric": index >= 3,
                "full_contraction_ratio": 1.0 if index == 2 else 0.4,
                "quotient_contraction_ratio": 0.1 * index,
                "terminal_distance_to_source_arm": float(index),
                "terminal_distance_to_opposite_arm": float(5 - index),
            }
        )
    first = build_plane_selections(rows, config)
    second = build_plane_selections(rows, config)
    assert first == second
    chosen = [
        row["selected_plane_task_id"]
        for row in first["selections"]
        if row["arm"] == "low"
    ]
    assert len(chosen) == 3
    assert len(set(chosen)) == 3
