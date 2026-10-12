from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.atlas import state_payload
from grn_reset_audit.causal_carrier import (
    EXPECTED_COUNTS,
    apply_component_transplant,
    build_carrier_models,
    carrier_decision,
    condition_spec,
    donor_recipient_envelope,
    erase_rescue_decision,
    fit_multioutput_ridge,
    geometry_decision,
    load_causal_carrier_config,
    local_radius_cap,
    select_diverse_plane_rows,
    source_enclosing_envelope,
    transfer_metrics,
)
from grn_reset_audit.engine import State
from grn_reset_audit.exposure_autopsy import _shard


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-causal-carrier-transplant-v1.json"


def test_protocol_freezes_fresh_split_counts_and_four_hour_cap():
    config = load_causal_carrier_config(CONFIG)
    assert config["discovery_seed_indices"] == [204, 205]
    assert config["fresh_seed_indices"] == list(range(208, 216))
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14_400.0
    assert config["hard_aggregate_cpu_seconds"] == 57_600.0
    assert config["registered_condition_count"] == 2_640
    assert config["registered_record_counts"] == EXPECTED_COUNTS
    assert sum(EXPECTED_COUNTS.values()) == 2_640


def test_plane_census_selection_is_deterministic_unique_and_spread():
    rows = []
    for angle in range(12):
        for radius in (0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25):
            rows.append(
                {
                    "task_id": f"plane-{angle}-{radius}",
                    "angle_radians": 2.0 * np.pi * angle / 12.0,
                    "radius_fraction": radius,
                    "valid": True,
                    "terminal_state": {"valid": True},
                }
            )
    first = select_diverse_plane_rows(rows, 16)
    second = select_diverse_plane_rows(list(reversed(rows)), 16)
    assert [row["task_id"] for row in first] == [row["task_id"] for row in second]
    assert len({row["task_id"] for row in first}) == 16
    assert len({round(float(row["angle_radians"]), 6) for row in first}) >= 8
    assert len({float(row["radius_fraction"]) for row in first}) >= 4


def test_plane_census_preserves_feasible_rows_and_marks_null_slots():
    rows = [
        {
            "task_id": f"row-{index}",
            "angle_radians": 2.0 * np.pi * index / 20.0,
            "radius_fraction": 0.01 * (1 + index % 4),
            "valid": index < 6,
            "terminal_state": {"valid": True} if index < 6 else None,
        }
        for index in range(20)
    ]
    selected = select_diverse_plane_rows(rows, 16)
    assert len(selected) == 16
    assert {f"row-{index}" for index in range(6)} <= {
        row["task_id"] for row in selected
    }
    assert sum(bool(row["valid"]) for row in selected) == 6


def test_observer_ridge_recovers_affine_multioutput_map():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(40, 3))
    matrix = np.asarray([[0.5, -0.2, 0.0], [0.0, 0.3, 0.7]])
    intercept = np.asarray([1.2, -0.4])
    y = x @ matrix.T + intercept
    fitted = fit_multioutput_ridge(x, y, [1e-12, 1e-8], 5)
    assert np.asarray(fitted["matrix"]) == pytest.approx(matrix, abs=1e-7)
    assert np.asarray(fitted["intercept"]) == pytest.approx(intercept, abs=1e-7)


def _state(y: list[float]) -> State:
    return State(np.asarray(y, dtype=float), np.asarray([1.0]), np.asarray([2.0]), 10.0)


def test_coordinate_swap_is_exact_and_preserves_unswapped_state():
    recipient = _state([0.2, 0.8, 0.4])
    donor = _state([0.9, 0.1, 0.7])
    result, alpha, requested = apply_component_transplant(
        recipient,
        donor,
        {"kind": "coordinates", "indices": [0, 2]},
        [1.0, 1.0, 1.0],
    )
    assert result is not None
    assert alpha == pytest.approx(1.0)
    assert requested > 0.0
    assert result.y == pytest.approx([0.9, 0.8, 0.7])
    assert result.w == pytest.approx(recipient.w)


def test_subspace_line_search_never_clips_and_reports_shortfall():
    recipient = _state([0.9, 0.1])
    donor = _state([0.1, 0.9])
    result, alpha, _ = apply_component_transplant(
        recipient,
        donor,
        {"kind": "subspace", "basis": [[1.0], [-2.0]]},
        [1.0, 1.0],
        tolerance=0.0,
    )
    assert result is not None
    assert alpha < 0.9
    envelope = donor_recipient_envelope(recipient, donor)
    assert result.y == pytest.approx([0.5, 0.9])
    assert np.all(result.y >= envelope[:, 0]) and np.all(result.y <= envelope[:, 1])


def test_exact_coordinate_swap_accepts_observed_endpoints_outside_static_bounds():
    recipient = _state([-0.1, 2.0])
    donor = _state([-0.2, 3.0])
    result, alpha, _ = apply_component_transplant(
        recipient,
        donor,
        {"kind": "coordinates", "indices": [0]},
        [1.0, 1.0],
    )
    assert result is not None
    assert alpha == 1.0
    assert result.y == pytest.approx([-0.2, 2.0])


def test_source_enclosing_envelope_contains_natural_state_outside_intervention_range():
    state = _state([-0.1, 1.2])
    envelope = source_enclosing_envelope(state, [[0.0, 1.0], [0.0, 1.0]])
    assert np.allclose(envelope, [[-0.1, 1.0], [0.0, 1.2]])


def test_endpoint_specific_radius_respects_both_caps():
    state = _state([0.9, 0.5])
    direction, feasible, cap = local_radius_cap(
        state,
        [1.0, 0.0],
        [1.0, 1.0],
        [[0.0, 1.0], [0.0, 1.0]],
        separation=2.0,
        separation_cap_fraction=0.1,
        feasible_radius_fraction=0.8,
        tolerance=0.0,
    )
    assert direction == pytest.approx([1.0, 0.0])
    assert feasible == pytest.approx(0.1)
    assert cap == pytest.approx(0.08)


def test_endpoint_specific_radius_disallows_motion_farther_outside_source_envelope():
    state = _state([-0.1, 0.5])
    direction, feasible, cap = local_radius_cap(
        state,
        [-1.0, 0.0],
        [1.0, 1.0],
        [[0.0, 1.0], [0.0, 1.0]],
        separation=2.0,
        separation_cap_fraction=0.1,
        feasible_radius_fraction=0.8,
    )
    assert direction == pytest.approx([-1.0, 0.0])
    assert feasible == 0.0
    assert cap == 0.0


def _model(primary: str = "top-nodes-1", role: str = "neutral-storage-lead") -> dict:
    return {
        "memory_task_id": "37-10-41",
        "task_role": role,
        "node_count": 4,
        "scale": [1.0] * 4,
        "ranked_nodes": [0, 1, 2, 3],
        "memory_axis": [1.0, 0.0, 0.0, 0.0],
        "observer_basis": np.eye(4).tolist(),
        "structural_neutral_basis": [[0.0], [1.0], [0.0], [0.0]],
        "tangent_basis": [[0.0], [1.0], [0.0], [0.0]],
        "normal_direction": [1.0, 0.0, 0.0, 0.0],
        "primary_condition": primary,
        "primary_effective_dimension": 1,
        "primary_selection_rule": "smallest-at-or-above-discovery-threshold",
        "anti_ranked_nodes": [3],
        "random_control_basis_1": [[0.0], [0.0], [1.0], [0.0]],
        "random_control_basis_2": [[0.0], [0.0], [0.0], [1.0]],
        "model_digest": "frozen",
    }


def test_condition_specs_cover_sparse_distributed_and_passive_modes():
    model = _model()
    assert condition_spec(model, "top-nodes-1")["indices"] == [0]
    assert np.asarray(condition_spec(model, "observer-rank-4")["basis"]).shape == (4, 4)
    assert np.asarray(condition_spec(model, "structural-neutral")["basis"]).shape == (4, 1)
    assert np.asarray(condition_spec(model, "random-control-2")["basis"]).shape == (4, 1)


def _checkpoints(value: float) -> dict:
    return {
        key: {"state": state_payload(_state([value, 0.0]))}
        for key in ("0", "250", "2500", "12500")
    }


def test_transfer_scoring_tracks_behavior_and_state_separately():
    config = load_causal_carrier_config(CONFIG)
    no_ops = [
        {
            "task_id": "low",
            "memory_task_id": "37-10-41",
            "seed_index": 208,
            "arm": "low",
            "valid": True,
            "fingerprint": [-1.0],
            "checkpoints": _checkpoints(0.0),
        },
        {
            "task_id": "high",
            "memory_task_id": "37-10-41",
            "seed_index": 208,
            "arm": "high",
            "valid": True,
            "fingerprint": [1.0],
            "checkpoints": _checkpoints(1.0),
        },
    ]
    row = {
        "task_id": "swap",
        "memory_task_id": "37-10-41",
        "seed_index": 208,
        "recipient_arm": "low",
        "target_arm": "high",
        "condition": "top-nodes-1",
        "is_primary_candidate": True,
        "primary_eligible": True,
        "valid": True,
        "fingerprint": [1.0],
        "bipolar_score": 1.0,
        "checkpoints": _checkpoints(1.0),
    }
    metrics = transfer_metrics(
        [row], no_ops, {"models": [{"memory_task_id": "37-10-41", "scale": [1.0, 1.0]}]}, config
    )[0]
    assert metrics["target_identity"] is True
    assert metrics["target_fingerprint_rms"] == pytest.approx(0.0)
    assert metrics["state_target_fraction_12500"] == pytest.approx(1.0)
    assert metrics["transfer_direction_cosine_2500_to_12500"] == pytest.approx(1.0)
    assert metrics["transfer_retention_fraction"] == pytest.approx(1.0)


def _passing_metric(task: str, seed: int, recipient: str, condition: str) -> dict:
    target = "high" if recipient == "low" else "low"
    return {
        "task_id": f"m-{task}-{seed}-{recipient}-{condition}",
        "memory_task_id": task,
        "seed_index": seed,
        "recipient_arm": recipient,
        "target_arm": target,
        "condition": condition,
        "is_primary_candidate": condition == "top-nodes-1",
        "primary_eligible": condition == "top-nodes-1",
        "valid": True,
        "target_identity": True,
        "target_oriented_bipolar_score": 1.0,
        "target_fingerprint_rms": 0.0,
        "transfer_direction_cosine_2500_to_12500": 1.0,
        "transfer_retention_fraction": 1.0,
        "state_target_fraction_12500": 1.0,
    }


def _control_metric(task: str, seed: int, recipient: str, condition: str) -> dict:
    row = _passing_metric(task, seed, recipient, condition)
    row.update(
        {
            "is_primary_candidate": False,
            "primary_eligible": False,
            "target_identity": False,
            "target_oriented_bipolar_score": -1.0,
            "target_fingerprint_rms": 1.0,
        }
    )
    return row


def test_single_coordinate_causal_carrier_requires_positive_and_negative_controls():
    config = copy.deepcopy(load_causal_carrier_config(CONFIG))
    config["focal_task_ids"] = ["37-10-41"]
    rows = []
    for seed in config["fresh_seed_indices"]:
        for recipient in ("low", "high"):
            rows.extend(
                [
                    _passing_metric("37-10-41", seed, recipient, "top-nodes-1"),
                    _passing_metric("37-10-41", seed, recipient, "full-state"),
                ]
            )
            for condition in ("sham", "anti-ranked", "random-control-1", "random-control-2"):
                rows.append(_control_metric("37-10-41", seed, recipient, condition))
    decision = carrier_decision(rows, {"models": [_model()]}, config)
    summary = decision["task_summaries"][0]
    assert summary["causal_transfer_pass"] is True
    assert summary["classification"] == "compact-causal-current-state-carrier"


def test_nonlinear_switch_role_has_distinct_operational_class():
    config = copy.deepcopy(load_causal_carrier_config(CONFIG))
    config["focal_task_ids"] = ["37-10-41"]
    config["task_roles"]["37-10-41"] = "nonlinear-switch-contrast"
    model = _model(role="nonlinear-switch-contrast")
    model["primary_selection_rule"] = "maximum-predicted-transfer-fallback"
    rows = []
    for seed in config["fresh_seed_indices"]:
        for recipient in ("low", "high"):
            rows += [
                _passing_metric("37-10-41", seed, recipient, "top-nodes-1"),
                _passing_metric("37-10-41", seed, recipient, "full-state"),
            ]
            rows += [
                _control_metric("37-10-41", seed, recipient, condition)
                for condition in ("sham", "anti-ranked", "random-control-1", "random-control-2")
            ]
    summary = carrier_decision(rows, {"models": [model]}, config)["task_summaries"][0]
    assert summary["classification"] == "nonlinear-switch-carrier"


def test_curved_geometry_requires_normal_return_and_tangent_persistence():
    config = copy.deepcopy(load_causal_carrier_config(CONFIG))
    config["focal_task_ids"] = ["37-10-41"]
    rows = []
    for seed in config["fresh_seed_indices"]:
        for center in ("source", "transplanted"):
            for arm in ("low", "high"):
                for direction in ("tangent", "normal"):
                    for sign in (-1, 1):
                        for radius in (0.5, 1.0):
                            rows.append(
                                {
                                    "memory_task_id": "37-10-41",
                                    "seed_index": seed,
                                    "center_type": center,
                                    "arm": arm,
                                    "direction_kind": direction,
                                    "sign": sign,
                                    "radius_factor": radius,
                                    "valid": True,
                                    "contraction_or_persistence_ratio": 1.0 if direction == "tangent" else 0.1,
                                    "behavior_returned": True,
                                }
                            )
    decision = geometry_decision(rows, config)
    assert decision["task_summaries"][0]["curved_attracting_functional_manifold"] is True


def test_erase_rescue_requires_effect_and_recovery_on_both_arms():
    config = copy.deepcopy(load_causal_carrier_config(CONFIG))
    config["focal_task_ids"] = ["37-10-41"]
    rows = [
        {
            "memory_task_id": "37-10-41",
            "seed_index": seed,
            "arm": arm,
            "valid": True,
            "erase_effect_fraction": 0.8,
            "rescue_fraction": 0.9,
            "source_fingerprint_rms_after_rescue": 0.1,
        }
        for seed in config["fresh_seed_indices"]
        for arm in ("low", "high")
    ]
    assert erase_rescue_decision(rows, config)["task_summaries"][0]["pass"] is True


def test_discovery_builder_rejects_any_fresh_outcome_before_reading_parents(tmp_path: Path):
    config = load_causal_carrier_config(CONFIG)
    with pytest.raises(ValueError, match="leaked"):
        build_carrier_models(
            config,
            [{"seed_index": 208}],
            tmp_path / "manifold",
            tmp_path / "constrained",
        )


def test_matching_digest_shard_is_resumable(tmp_path: Path):
    path = tmp_path / ".shards" / "stage" / "key.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"protocol_digest":"abc","records":[]}\n', encoding="utf-8")
    resolved, prior = _shard(tmp_path, "stage", "key", "abc")
    assert resolved == path
    assert prior == {"protocol_digest": "abc", "records": []}
