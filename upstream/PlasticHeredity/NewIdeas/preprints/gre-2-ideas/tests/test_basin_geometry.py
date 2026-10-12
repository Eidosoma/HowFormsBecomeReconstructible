from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.basin_geometry import (
    boundary_models,
    coordinate_decision,
    crossing_summary,
    hysteresis_decision,
    interpolate_state,
    load_basin_geometry_config,
    local_return_decision,
    orthogonal_directions,
    perturb_state,
)
from grn_reset_audit.engine import State


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-exposure-basin-geometry-v1.json"


def test_protocol_freezes_grids_split_condition_count_and_four_hour_cap():
    config = load_basin_geometry_config(CONFIG)
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert config["registered_condition_count"] == 2_840
    assert config["transect"]["alphas"] == pytest.approx(np.linspace(0.0, 1.0, 21))
    assert config["hysteresis"]["amplitudes"] == pytest.approx(np.linspace(0.0, 1.0, 11))
    assert set(config["discovery_seed_indices"]).isdisjoint(config["validation_seed_indices"])


def test_interpolation_and_orthogonal_basis_preserve_the_rulebook():
    low = State(np.asarray([0.0, 2.0, 4.0]), np.asarray([6.0]), np.asarray([9.0]), 10.0)
    high = State(np.asarray([2.0, 4.0, 8.0]), np.asarray([8.0]), np.asarray([9.0]), 12.0)
    middle = interpolate_state(low, high, 0.5)
    assert middle.y.tolist() == [1.0, 3.0, 6.0]
    assert middle.w.tolist() == [7.0]
    assert middle.c.tolist() == [9.0]
    assert middle.t == 12.0

    axis = np.asarray([1.0, 2.0, -1.0, 0.5, 3.0])
    controls = orthogonal_directions(axis, 4, seed=17)
    unit = axis / np.linalg.norm(axis)
    assert controls @ unit == pytest.approx(np.zeros(4), abs=1e-12)
    assert controls @ controls.T == pytest.approx(np.eye(4), abs=1e-12)
    assert np.array_equal(controls, orthogonal_directions(axis, 4, seed=17))


def test_bound_constrained_perturbations_are_rejected_without_clipping():
    base = State(np.asarray([0.9, 0.5]), np.asarray([]), np.asarray([1.0]), 0.0)
    scale = np.asarray([1.0, 1.0])
    bounds = np.asarray([[0.0, 1.0], [0.0, 1.0]])
    valid = perturb_state(base, [1.0, 0.0], 0.05, scale, bounds, 1e-10)
    invalid = perturb_state(base, [1.0, 0.0], 0.2, scale, bounds, 1e-10)
    assert valid is not None and valid.y.tolist() == pytest.approx([0.95, 0.5])
    assert invalid is None


def _transect_rows(task: str, seed: int, scores: list[float]) -> list[dict[str, object]]:
    return [
        {
            "memory_task_id": task,
            "seed_index": seed,
            "alpha": index / (len(scores) - 1),
            "bipolar_score": score,
            "valid": True,
        }
        for index, score in enumerate(scores)
    ]


def test_boundary_is_discovered_only_from_monotonic_single_crossings():
    summary = crossing_summary(_transect_rows("x", 0, [-1.0, -0.5, 0.5, 1.0]), 0.05)
    assert summary["monotonic"] is True
    assert summary["crossing_count"] == 1
    assert summary["crossing_locations"][0] == pytest.approx(0.5)

    config = copy.deepcopy(load_basin_geometry_config(CONFIG))
    config["exposure_task_ids"] = ["x"]
    config["discovery_seed_indices"] = [0, 1, 2, 3]
    rows = []
    for seed in config["discovery_seed_indices"]:
        rows.extend(_transect_rows("x", seed, [-1.0, -0.5, 0.5, 1.0]))
    model = boundary_models(rows, config)["models"][0]
    assert model["eligible"] is True
    assert model["boundary_alpha"] == pytest.approx(0.5)


def test_coordinate_decision_requires_specific_held_out_bidirectional_control():
    config = copy.deepcopy(load_basin_geometry_config(CONFIG))
    config["exposure_task_ids"] = ["x"]
    config["validation_seed_indices"] = [0, 1, 2, 3]
    config["collective_coordinate"]["boundary_radius_fractions_of_separation"] = [0.05]
    coordinates = {
        "models": [
            {
                "memory_task_id": "x",
                "energy_fraction": 0.95,
                "validation_alignments": [
                    {"seed_index": seed, "cosine": 0.95} for seed in range(4)
                ],
            }
        ]
    }
    boundaries = {"models": [{"memory_task_id": "x", "eligible": True}]}
    rows = []
    for seed in range(4):
        for sign, score in ((-1, -1.0), (1, 1.0)):
            rows.append(
                {
                    "memory_task_id": "x",
                    "seed_index": seed,
                    "radius_fraction": 0.05,
                    "direction_kind": "collective",
                    "direction_index": -1,
                    "sign": sign,
                    "bipolar_score": score,
                    "valid": True,
                }
            )
        for index in range(4):
            for sign in (-1, 1):
                rows.append(
                    {
                        "memory_task_id": "x",
                        "seed_index": seed,
                        "radius_fraction": 0.05,
                        "direction_kind": "orthogonal",
                        "direction_index": index,
                        "sign": sign,
                        "bipolar_score": 0.05 * sign,
                        "valid": True,
                    }
                )
    decision = coordinate_decision(rows, coordinates, boundaries, config)
    assert decision["pass"] is True
    assert decision["pass_count"] == 1
    assert decision["candidate_summaries"][0]["generic_threshold_sensitive"] is False


def test_local_return_requires_both_arms_on_three_validation_seeds():
    config = copy.deepcopy(load_basin_geometry_config(CONFIG))
    config["exposure_task_ids"] = ["x"]
    config["validation_seed_indices"] = [0, 1, 2, 3]
    rows = [
        {
            "memory_task_id": "x",
            "seed_index": seed,
            "arm": arm,
            "radius_fraction": 0.10,
            "returned": True,
            "valid": True,
        }
        for seed in range(4)
        for arm in ("low", "high")
        for _ in range(8)
    ]
    decision = local_return_decision(rows, config)
    assert decision["pass"] is True
    assert decision["candidate_summaries"][0]["consistent_seed_count"] == 4


def test_hysteresis_requires_two_adjacent_amplitudes_on_three_seeds():
    config = copy.deepcopy(load_basin_geometry_config(CONFIG))
    config["exposure_task_ids"] = ["x"]
    config["validation_seed_indices"] = [0, 1, 2, 3]
    config["hysteresis"]["amplitudes"] = [0.0, 0.1, 0.2]
    rows = []
    for amplitude in config["hysteresis"]["amplitudes"]:
        for seed in range(4):
            separated = amplitude in {0.1, 0.2}
            for arm, score in (
                ("low", -1.0 if separated else 0.0),
                ("high", 1.0 if separated else 0.0),
            ):
                rows.append(
                    {
                        "memory_task_id": "x",
                        "seed_index": seed,
                        "amplitude": amplitude,
                        "start_arm": arm,
                        "bipolar_score": score,
                        "valid": True,
                    }
                )
    decision = hysteresis_decision(rows, config)
    assert decision["pass"] is True
    assert decision["candidate_summaries"][0]["adjacent_qualifying_windows"] == [
        [0.1, 0.2]
    ]
