import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from grn_reset_audit.ca_bridge import (
    FORM_ARMS,
    STAGES,
    _form_reference,
    _identity_worker,
    _parallel,
    build_codebooks,
    common_damage,
    cosine_alignment,
    decode_codec,
    encode_codec,
    form_score,
    load_ca_bridge_config,
    next_native_donor,
    normalized_shuffle,
    qualification_screen_decision,
    qualification_validation_decision,
    renew_packet,
    state_from_vector,
    state_mode_available,
    transform_fingerprint,
    vector_rms,
)
from grn_reset_audit.engine import State


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-ca-bridge-ladder-v1.json"


def test_protocol_freezes_six_sealed_stages_and_four_workers():
    config = load_ca_bridge_config(CONFIG)
    assert tuple(config["stages"]) == STAGES
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14400.0
    assert config["hard_aggregate_cpu_seconds"] == 57600.0
    assert len(config["fixed_cohort_task_ids"]) == 24
    assert config["stage_parents"]["native-lineage"] == "native-transfer"
    assert config["stage_parents"]["g16-replication"] == "engineered-renewal"


def test_protocol_rejects_worker_or_stage_graph_changes(tmp_path):
    payload = json.loads(CONFIG.read_text())
    payload["max_workers"] = 5
    bad_workers = tmp_path / "workers.json"
    bad_workers.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="cap workers at four"):
        load_ca_bridge_config(bad_workers)
    payload = json.loads(CONFIG.read_text())
    payload["stage_parents"]["compression"] = "form-qualification"
    bad_graph = tmp_path / "graph.json"
    bad_graph.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="stage-parent graph"):
        load_ca_bridge_config(bad_graph)


def test_frozen_form_coordinate_has_exact_polarity_and_zero_guard():
    a = np.asarray([2.0, -1.0, 0.5, 3.0])
    b = np.asarray([-2.0, 1.0, -0.5, -1.0])
    midpoint = 0.5 * (a + b)
    assert form_score(a, a, b) == pytest.approx(1.0)
    assert form_score(b, a, b) == pytest.approx(-1.0)
    assert form_score(midpoint, a, b) == pytest.approx(0.0)
    assert form_score(a, a, a) is None
    assert cosine_alignment(a - b, a - b) == pytest.approx(1.0)
    assert cosine_alignment(a, np.zeros_like(a)) is None
    assert vector_rms([3.0, 4.0]) == pytest.approx(np.sqrt(12.5))
    assert np.allclose(transform_fingerprint(a), np.arcsinh(a))


def test_state_transfer_never_inherits_rulebook_c():
    baseline = State(
        np.asarray([0.1, 0.2]),
        np.asarray([0.3]),
        np.asarray([7.0, 8.0]),
        12.0,
    )
    memory = SimpleNamespace(bounds=np.asarray([[-1.0, 1.0], [-2.0, 2.0]]))
    child_y = state_from_vector([0.8, -0.7], baseline, memory, "y")
    assert np.array_equal(child_y.c, baseline.c)
    assert np.array_equal(child_y.w, baseline.w)
    child_yw = state_from_vector([0.8, -0.7, 9.0], baseline, memory, "yw")
    assert np.array_equal(child_yw.c, baseline.c)
    assert child_yw.w[0] == pytest.approx(9.0)
    form_a = State(baseline.y, np.asarray([1.0]), baseline.c, baseline.t)
    form_b = State(baseline.y, np.asarray([-1.0]), baseline.c, baseline.t)
    assert state_mode_available(form_a, form_b, "yw")
    assert not state_mode_available(form_a, form_a, "yw")


def test_common_philox_damage_and_scalar_shuffle_are_not_silent_noops():
    config = load_ca_bridge_config(CONFIG)
    env = {"dropout": 0.1, "noise_sigma": 0.05}
    first = common_damage(config, "x", "10-1-25", 2, 3, 8, env)
    repeated = common_damage(config, "x", "10-1-25", 2, 3, 8, env)
    later = common_damage(config, "x", "10-1-25", 2, 4, 8, env)
    assert np.array_equal(first[0], repeated[0])
    assert np.array_equal(first[1], repeated[1])
    assert first[2] == repeated[2]
    assert first[2] != later[2]
    shuffled, method = normalized_shuffle(
        np.asarray([0.8]), np.random.Generator(np.random.Philox(9))
    )
    assert method == "singleton-random-sign-surrogate"
    assert abs(shuffled[0]) == pytest.approx(0.8)


def test_codec_payload_and_codebook_accounting_round_trip():
    discovery = np.asarray(
        [
            [1.0, 0.0, 0.5],
            [0.9, 0.1, 0.4],
            [-1.0, 0.0, -0.5],
            [-0.9, -0.1, -0.4],
        ]
    )
    codebooks = build_codebooks(
        discovery,
        np.asarray([1.0, 0.0, 0.5]),
        np.asarray([-1.0, 0.0, -0.5]),
        3,
        [1, 2],
        [1, 2],
        [1, 2],
        np.eye(3),
    )
    assert {row["family"] for row in codebooks} == {
        "sparse",
        "pca",
        "observability",
        "direction",
    }
    assert all(row["payload_float_count"] <= row["codebook_float_count"] for row in codebooks)
    direction = next(row for row in codebooks if row["family"] == "direction")
    value = np.asarray([1.0, 0.0, 0.5])
    payload = encode_codec(direction, value)
    decoded = decode_codec(direction, payload)
    assert payload.shape == (1,)
    assert np.allclose(decoded, value)
    assert direction["codebook_hash"]
    tiny = build_codebooks(
        np.asarray([[1.0], [-1.0]]),
        np.asarray([1.0]),
        np.asarray([-1.0]),
        1,
        [1, 2, 3, 4, 5],
        [1],
        [1],
        np.eye(1),
    )
    assert [row["codec_id"] for row in tiny].count("sparse-k1") == 1


def test_passive_ancestry_uses_current_copy_and_packet_renewal_moves_to_adult():
    copied = State(np.asarray([1.0]), np.asarray([]), np.asarray([4.0]), 2.0)
    adult = State(np.asarray([3.0]), np.asarray([]), np.asarray([4.0]), 3.0)
    passive, source = next_native_donor("passive", copied, adult, 2)
    assert np.array_equal(passive.y, copied.y)
    assert source == "post-copy-g2"
    active, source = next_native_donor("active_rewrite", copied, adult, 2)
    assert np.array_equal(active.y, adult.y)
    assert source == "adult-g2"
    renewed = renew_packet(np.asarray([0.0]), np.asarray([1.0]), 1)
    assert renewed[0] == pytest.approx(0.5)


def _qualification_row(task_id, arm, seed_index=None):
    a = np.ones(6)
    b = -np.ones(6)
    value = a if arm == "form_a" else b if arm == "form_b" else np.zeros(6)
    return {
        "task_id": f"q|{task_id}|{seed_index}|{arm}",
        "memory_task_id": task_id,
        "model_id": int(task_id.split("-")[0]),
        "seed_index": seed_index,
        "condition": arm,
        "valid": True,
        "checkpoints": {
            "2500": {"fingerprint": value, "valid": True},
            "12500": {"fingerprint": value, "valid": True},
        },
    }


def test_zero_form_direction_is_a_clean_negative_not_an_analysis_error():
    config = load_ca_bridge_config(CONFIG)
    task_id = config["fixed_cohort_task_ids"][0]
    rows = {
        arm: _qualification_row(task_id, arm)
        for arm in FORM_ARMS
    }
    for arm in ("form_a", "form_b"):
        for checkpoint in ("2500", "12500"):
            rows[arm]["checkpoints"][checkpoint]["fingerprint"] = np.zeros(6)
    reference = _form_reference(task_id, rows, config)
    assert not reference["screen_pass"]
    assert np.isinf(reference["max_control_abs_score"])


def test_synthetic_qualification_passes_and_respects_distinct_model_caps():
    config = load_ca_bridge_config(CONFIG)
    screen_records = [
        _qualification_row(task_id, arm)
        for task_id in config["fixed_cohort_task_ids"]
        for arm in FORM_ARMS
    ]
    screen = qualification_screen_decision(screen_records, config)
    assert screen["pass"]
    assert len(screen["validation_nominations"]) == 8
    assert len({task.split("-")[0] for task in screen["validation_nominations"]}) == 8
    validation = [
        _qualification_row(task_id, arm, seed_index)
        for task_id in screen["validation_nominations"]
        for seed_index in range(4)
        for arm in FORM_ARMS
    ]
    decision = qualification_validation_decision(validation, screen, config)
    assert decision["pass"]
    assert len(decision["advanced_candidates"]) == 4
    assert len({task.split("-")[0] for task in decision["advanced_candidates"]}) == 4


def test_one_and_four_worker_sentinel_order_is_identical():
    args = [(1, "a"), (2, "b"), (3, "c"), (4, "d")]
    assert _parallel(_identity_worker, args, 1) == _parallel(_identity_worker, args, 4)
