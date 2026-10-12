from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.engine import State
from grn_reset_audit.switch_boundary import (
    EXPECTED_COUNTS,
    FRESH_SEEDS,
    LATCH_NODE,
    load_switch_boundary_config,
    matched_latch_control_slots,
    pairwise_decision,
    reverse_mask_specs,
    specificity_decision,
    state_from_node_fractions,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-switch-boundary-mapping-v1.json"


def _state(values: list[float]) -> State:
    return State(np.asarray(values, dtype=float), np.asarray([1.0]), np.asarray([2.0]), 10.0)


def _model() -> dict:
    return {
        "scale": [1.0] * 8,
        "observer_map": {"matrix": np.eye(8).tolist()},
    }


def _metric(seed: int, success: bool, **extra: object) -> dict:
    return {
        "task_id": f"metric-{seed}-{len(extra)}-{extra}",
        "seed_index": seed,
        "valid": True,
        "target_oriented_bipolar_score": 1.0 if success else -1.0,
        "target_fingerprint_rms": 0.0 if success else 1.0,
        **extra,
    }


def test_protocol_freezes_cohort_counts_and_resource_caps():
    config = load_switch_boundary_config(CONFIG)
    assert tuple(config["fresh_seed_indices"]) == FRESH_SEEDS
    assert config["latch_node_index"] == LATCH_NODE
    assert config["registered_record_counts"] == EXPECTED_COUNTS
    assert sum(EXPECTED_COUNTS.values()) == 5_840
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0


def test_endpoint_node_fractions_are_exact_and_do_not_clip():
    recipient = _state([0.1] * 8)
    donor = _state([0.9] * 8)
    result, detail = state_from_node_fractions(
        recipient,
        donor,
        {7: 0.01, 1: 0.5},
        [1.0] * 8,
    )
    assert result is not None
    assert result.y[7] == pytest.approx(0.108)
    assert result.y[1] == pytest.approx(0.5)
    assert result.y[0] == pytest.approx(0.1)
    assert detail["effective_dimension"] == 2


def test_matched_controls_are_deterministic_orthogonal_and_norm_matched():
    config = load_switch_boundary_config(CONFIG)
    recipient = _state([0.5] * 8)
    donor_values = [0.5] * 8
    donor_values[7] = 0.9
    donor = _state(donor_values)
    bounds = np.asarray([[0.0, 1.0]] * 8)
    first = matched_latch_control_slots(config, recipient, donor, _model(), bounds, 232, 0.001)
    second = matched_latch_control_slots(config, recipient, donor, _model(), bounds, 232, 0.001)
    assert [row.get("candidate_index") for row in first] == [row.get("candidate_index") for row in second]
    assert all(row["available"] for row in first)
    assert all(row["target_norm"] == pytest.approx(0.0004) for row in first)
    assert all(row["latch_cosine"] <= 0.25 for row in first)


def test_reverse_masks_cover_leave_one_out_and_both_ordered_paths():
    specs = reverse_mask_specs()
    assert len(specs) == 24
    assert sum(row["family"] == "leave-one-behind" for row in specs) == 8
    assert sum(row["family"] == "ranked-cumulative" for row in specs) == 8
    assert sum(row["family"] == "anti-cumulative" for row in specs) == 8
    assert sorted(row["withheld_node"] for row in specs if row["family"] == "leave-one-behind") == list(range(8))


def test_specificity_requires_clean_controls_and_no_alternative_node():
    config = load_switch_boundary_config(CONFIG)
    fine = {
        "directional_thresholds": {
            "latch-node": {"low-to-high": 0.001, "high-to-low": None},
            "full-expression": {"low-to-high": 0.001, "high-to-low": 1.0},
        }
    }
    single = [
        _metric(seed, False, node_index=node, direction="low-to-high", dose=float(dose))
        for node in config["single_node"]["node_indices"]
        for dose in config["single_node"]["low_to_high_doses"]
        for seed in FRESH_SEEDS
    ]
    controls = [
        _metric(seed, False, direction="low-to-high", dose=0.001, control_slot=slot)
        for seed in FRESH_SEEDS
        for slot in range(8)
    ]
    result = specificity_decision([], single, controls, fine, config)
    assert result["node_specific"]
    assert not result["globally_fragile"]
    assert result["classification"] == "node-specific-forward-latch"


def test_pairwise_decision_detects_a_conditional_gate():
    config = load_switch_boundary_config(CONFIG)
    pair = [
        _metric(
            seed,
            True,
            partner_node=1,
            latch_dose=0.001,
            partner_dose=0.001,
        )
        for seed in FRESH_SEEDS
    ]
    fine = [
        _metric(seed, False, condition="latch-node", direction="low-to-high", dose=0.001)
        for seed in FRESH_SEEDS
    ]
    single = [
        _metric(seed, False, node_index=1, direction="low-to-high", dose=0.001)
        for seed in FRESH_SEEDS
    ]
    result = pairwise_decision(pair, fine, single, config)
    assert result["conditional_gate"]
    assert result["classification"] == "conditional-pair-gate"


def test_protocol_rejects_registered_count_drift(tmp_path: Path):
    payload = copy.deepcopy(load_switch_boundary_config(CONFIG))
    payload["registered_record_counts"]["fine-boundary.jsonl"] += 1
    path = tmp_path / "bad.json"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="registered"):
        load_switch_boundary_config(path)
