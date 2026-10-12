from __future__ import annotations

from pathlib import Path

import numpy as np

from grn_reset_audit.renewal import (
    _identity_model_worker,
    _run_model_workers,
    dilution_y,
    encode_mark,
    load_renewal_config,
    mark_scale,
    native_branch_decision,
    partition_mask,
    partition_y,
    read_mark,
    update_mark,
)


def config():
    root = Path(__file__).resolve().parents[1]
    return load_renewal_config(root / "configs" / "grn-latent-memory-renewal-v1.json")


def test_protocol_freezes_four_workers_eight_hours_and_balanced_cohort():
    value = config()
    assert value["max_workers"] == 4
    assert value["hard_wall_seconds"] == 28800.0
    assert sum(len(pair) for pair in value["fixed_model_pairs"].values()) == 8
    assert value["mark_discovery_models"] == [10, 16]
    assert value["mark_validation_models"] == [37, 204]


def test_renewal_operator_endpoints_and_shared_partition_mask():
    value = config()
    naive = np.asarray([0.0, 1.0, 2.0])
    parent = np.asarray([3.0, 4.0, 5.0])
    assert np.array_equal(dilution_y(naive, parent, 0), naive)
    assert np.array_equal(dilution_y(naive, parent, 1), parent)
    assert np.array_equal(
        partition_y(naive, parent, np.asarray([False, True, False])),
        np.asarray([0.0, 4.0, 2.0]),
    )
    first = partition_mask(3, 0.5, value, 10, 7)
    second = partition_mask(3, 0.5, value, 10, 7)
    assert np.array_equal(first, second)


def test_mark_zero_coupling_update_and_read_are_exact():
    naive = np.asarray([1.0, 2.0])
    trained = np.asarray([3.0, -2.0])

    class Memory:
        bounds = np.asarray([[0.0, 2.0], [-1.0, 1.0]])

    scale = mark_scale(Memory(), naive, trained)
    encoded = encode_mark(trained, naive, scale)
    assert np.all(np.abs(encoded) <= 1)
    assert np.array_equal(read_mark(naive, encoded, scale, 0.0), naive)
    updated = update_mark(np.zeros(2), encoded, half_life=1)
    assert np.allclose(updated, 0.5 * encoded)


def test_one_and_four_worker_spawn_order_is_identical():
    args = [
        (None, None, None, None, model, [f"{model}-task"])
        for model in (10, 16, 37, 204)
    ]
    serial = _run_model_workers(_identity_model_worker, args, 1)
    parallel = _run_model_workers(_identity_model_worker, args, 4)
    assert parallel == serial


def _native_record(task, operator, retention, arm, value, future=0):
    endpoint = {
        "learned_margin": float(value),
        "valid": True,
        "response_trajectory": [float(value), float(value)],
    }
    return {
        "task_id": f"x|{task}|{operator}|{retention}|{future}|{arm}",
        "memory_task_id": task,
        "model_id": int(task.split("-")[0]),
        "operator": operator,
        "retention": float(retention),
        "future": future,
        "arm": arm,
        "valid": True,
        "recall": endpoint,
        "relearn": endpoint,
    }


def test_native_gate_requires_reset_control_specificity():
    value = config()
    tasks = [task for pair in value["fixed_model_pairs"].values() for task in pair]
    records = []
    for task in tasks:
        for retention in (0.0, 0.5, 1.0):
            values = {
                "naive": 0.0,
                "trained_no_reset": 0.0 if retention == 0 else 10.0,
                "combined_reset": 0.0 if retention == 0 else 5.0,
                "control_only": 0.0,
            }
            for arm, score in values.items():
                records.append(
                    _native_record(task, "dilution", retention, arm, score)
                )
    decision = native_branch_decision(records, value)
    assert decision["assay_valid"]
    assert decision["native_pass"]
    assert decision["branch"] == "native-carrier"
    assert decision["selected_boundary"]["retention"] == 0.5

    for row in records:
        if row["retention"] == 0.5 and row["arm"] == "control_only":
            row["recall"]["learned_margin"] = 5.0
            row["relearn"]["learned_margin"] = 5.0
    decision = native_branch_decision(records, value)
    assert not decision["native_pass"]
    assert decision["branch"] == "engineered-mark"
