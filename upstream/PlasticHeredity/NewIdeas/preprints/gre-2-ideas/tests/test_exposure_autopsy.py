from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from grn_reset_audit.atlas import state_payload
from grn_reset_audit.engine import State
from grn_reset_audit.exposure_autopsy import (
    ROUTES,
    STATE_CONDITIONS,
    load_exposure_autopsy_config,
    localization_states,
    long_horizon_decision,
    normalized_route_dose,
    route_epochs,
    route_factorial_decision,
    state_localization_decision,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-exposure-state-autopsy-v1.json"


def test_protocol_freezes_cohort_routes_seed_split_and_resource_contract():
    config = load_exposure_autopsy_config(CONFIG)
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert set(config["discovery_seed_indices"]).isdisjoint(
        config["validation_seed_indices"]
    )
    assert set(config["discovery_seed_indices"]) | set(
        config["validation_seed_indices"]
    ) == set(config["parent_seed_indices"])
    assert tuple(config["route_order"]) == ROUTES
    assert tuple(config["state_localization"]["conditions"]) == STATE_CONDITIONS
    equal_doses = [
        normalized_route_dose(config["route_specs"][name])
        for name in config["route_analysis"]["equal_dose_routes"]
    ]
    assert equal_doses == pytest.approx([5.0] * len(equal_doses))


def test_route_epochs_interpolates_registered_ucs_bounds():
    memory = SimpleNamespace(
        ucs_id=1,
        bounds=np.asarray([[-2.0, 2.0], [10.0, 30.0], [0.0, 1.0]]),
    )
    assert route_epochs(memory, [None, "low", 0.25, 1.0]) == [
        None,
        {1: 10.0},
        {1: 15.0},
        {1: 30.0},
    ]


def _state(y: list[float], time: float) -> State:
    return State(
        np.asarray(y, dtype=float),
        np.asarray([2.0], dtype=float),
        np.asarray([3.0], dtype=float),
        time,
    )


def test_long_horizon_classifies_a_stationary_functional_separation():
    config = copy.deepcopy(load_exposure_autopsy_config(CONFIG))
    config["exposure_task_ids"] = ["synthetic"]
    config["parent_seed_indices"] = list(range(8))
    config["long_horizon"]["ultra_task_ids"] = []
    rows = []
    for seed in config["parent_seed_indices"]:
        for arm, y, fingerprint in (
            ("low", [0.0, 0.0], [-1.0, -0.5]),
            ("high", [1.0, 0.0], [1.0, 0.5]),
        ):
            base = _state(y, 12_500.0)
            final = _state(y, 62_500.0)
            probe = _state(y, 65_000.0)
            rows.append(
                {
                    "memory_task_id": "synthetic",
                    "seed_index": seed,
                    "arm": arm,
                    "valid": True,
                    "state_scale": [1.0, 1.0],
                    "checkpoints": {
                        "12500": {
                            "state": state_payload(base),
                            "fingerprint": fingerprint,
                        },
                        "62500": {
                            "state": state_payload(final),
                            "fingerprint": fingerprint,
                        },
                    },
                    "stability_probe_state": state_payload(probe),
                }
            )
    decision = long_horizon_decision(rows, config)
    assert decision["pass"] is True
    assert decision["candidate_summaries"][0]["classification"] == (
        "stable-separate-compatible"
    )
    assert decision["candidate_summaries"][0]["median_state_retention"] == pytest.approx(
        1.0
    )


def test_route_factorial_reproduces_sources_and_detects_order_effect():
    config = copy.deepcopy(load_exposure_autopsy_config(CONFIG))
    config["exposure_task_ids"] = ["synthetic"]
    config["parent_seed_indices"] = list(range(6))
    scores = {
        "naive": 0.0,
        "low_spaced": -1.0,
        "quarter_spaced": -0.5,
        "mid_spaced": 0.0,
        "three_quarter_spaced": 0.5,
        "high_spaced": 1.0,
        "high_early": 0.2,
        "high_late": 0.9,
        "mid_continuous": 0.7,
        "ramp_up": 0.8,
        "ramp_down": 0.1,
    }
    rows = [
        {
            "memory_task_id": "synthetic",
            "seed_index": seed,
            "route": route,
            "valid": True,
            "bipolar_score": score,
            "fingerprint": [score, score],
        }
        for seed in config["parent_seed_indices"]
        for route, score in scores.items()
    ]
    decision = route_factorial_decision(rows, config)
    summary = decision["candidate_summaries"][0]
    assert decision["source_reproduction_pass"] is True
    assert summary["dose_rank_correlation"] == pytest.approx(1.0)
    assert summary["flags"]["recency_sensitive"] is True
    assert summary["flags"]["path_sensitive"] is True


def test_localization_states_change_only_registered_y_components():
    memory = SimpleNamespace(
        bounds=np.asarray([[0.0, 2.0], [0.0, 4.0], [0.0, 8.0]], dtype=float)
    )
    high = State(
        np.asarray([2.0, 4.0, 8.0]),
        np.asarray([7.0]),
        np.asarray([9.0]),
        12_500.0,
    )
    low = State(
        np.asarray([0.0, 0.0, 0.0]),
        np.asarray([7.0]),
        np.asarray([9.0]),
        12_500.0,
    )
    states = localization_states(high, low, memory, [0], [0, 2], seed=13)
    assert states["erase_top1"].y.tolist() == [0.0, 4.0, 8.0]
    assert states["erase_topk"].y.tolist() == [0.0, 4.0, 0.0]
    assert states["write_topk"].y.tolist() == [2.0, 0.0, 8.0]
    assert states["rescue_topk"].y.tolist() == high.y.tolist()
    for state in states.values():
        assert np.array_equal(state.w, high.w)
        assert np.array_equal(state.c, high.c)


def test_state_localization_requires_erase_write_rescue_and_clean_controls():
    config = copy.deepcopy(load_exposure_autopsy_config(CONFIG))
    config["exposure_task_ids"] = ["synthetic"]
    config["validation_seed_indices"] = [0, 1, 2]
    config["state_localization"]["release_horizons"] = [0.0]
    scores = {
        "high_intact": 1.0,
        "low_intact": -1.0,
        "midpoint": 0.0,
        "erase_top1": 0.5,
        "erase_topk": 0.0,
        "write_top1": -0.5,
        "write_topk": 0.0,
        "rescue_topk": 1.0,
        "shuffled_delta": 0.0,
        "norm_matched_random": 0.0,
    }
    rows = []
    for seed in config["validation_seed_indices"]:
        for condition, score in scores.items():
            rows.append(
                {
                    "memory_task_id": "synthetic",
                    "seed_index": seed,
                    "condition": condition,
                    "release_horizon": 0.0,
                    "valid": True,
                    "bipolar_score": score,
                    "source_state_distance": 0.0,
                    "source_fingerprint_distance": 0.0,
                }
            )
    decision = state_localization_decision(rows, config)
    assert decision["source_reproduction_pass"] is True
    assert decision["pass"] is True
    horizon = decision["candidate_summaries"][0]["horizons"]["0"]
    assert horizon["erase_fraction"] == pytest.approx(0.5)
    assert horizon["write_fraction"] == pytest.approx(0.5)
    assert horizon["rescue_fraction"] == pytest.approx(1.0)
