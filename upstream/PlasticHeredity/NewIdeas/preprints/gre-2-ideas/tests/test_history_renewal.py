import json
from pathlib import Path

import numpy as np
import pytest

from grn_reset_audit.history_renewal import (
    _identity_history_worker,
    _parallel,
    content_inversion,
    copy_local_mark,
    cosine_alignment,
    damage_noise,
    damaged_copy,
    encode_local_mark,
    load_history_config,
    local_mark_scale,
    native_next_donor,
    project_fingerprint,
    reference_record,
    renew_local_mark,
    transform_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-history-carrier-renewal-v2.json"


def test_protocol_is_frozen_to_two_workers_and_four_hours():
    config = load_history_config(CONFIG)
    assert config["max_workers"] == 2
    assert config["hard_wall_seconds"] == 14400.0
    assert config["hard_aggregate_cpu_seconds"] == 28800.0
    assert len(config["candidates"]) == 8


def test_fingerprint_transform_projection_and_zero_direction():
    raw = np.asarray([-3.0, -0.5, 0.0, 0.5, 3.0])
    assert np.allclose(transform_fingerprint(raw), np.arcsinh(raw))
    direction = np.asarray([1.0, -1.0, 0.5, 0.0, 2.0])
    baseline = np.asarray([0.1, 0.2, -0.1, 0.0, 1.0])
    assert project_fingerprint(baseline + 0.7 * direction, baseline, direction) == pytest.approx(0.7)
    assert project_fingerprint(baseline, baseline, np.zeros(5)) is None
    assert cosine_alignment(direction, np.zeros(5)) is None


def test_reference_gate_uses_both_rms_and_alignment():
    config = load_history_config(CONFIG)
    names = config["fingerprint_probes"]
    arms = {
        "naive": [0.0] * 5,
        "trained_no_reset": [1.0] * 5,
        "control_only": [0.0] * 5,
        "combined_reset": [1.0] * 5,
    }
    probes = {
        ("x", arm, name): {"valid": True, "learned_margin": values[index]}
        for arm, values in arms.items()
        for index, name in enumerate(names)
    }
    row = reference_record("x", probes, config)
    assert row["eligible"]
    probes[("x", "combined_reset", names[0])]["valid"] = False
    assert not reference_record("x", probes, config)["eligible"]


def test_philox_damage_is_unique_by_seed_and_common_within_seed():
    config = load_history_config(CONFIG)
    first = damage_noise(config, "10-1-25", 0, 1, 8)
    repeated = damage_noise(config, "10-1-25", 0, 1, 8)
    second = damage_noise(config, "10-1-25", 1, 1, 8)
    assert np.array_equal(first, repeated)
    assert not np.array_equal(first, second)
    naive = np.zeros(8)
    bounds = np.column_stack((np.full(8, -10.0), np.full(8, 10.0)))
    donor_a = np.ones(8)
    donor_b = np.full(8, 2.0)
    child_a = damaged_copy(naive, donor_a, bounds, 0.5, first)
    child_b = damaged_copy(naive, donor_b, bounds, 0.5, first)
    assert np.allclose(child_b, 2.0 * child_a)


def test_singleton_content_inversion_is_not_a_shuffle_noop():
    control = np.asarray([0.0])
    combined = np.asarray([0.8])
    bounds = np.asarray([[-2.0, 2.0]])
    inverted = content_inversion(control, combined, bounds)
    assert inverted[0] == pytest.approx(-0.8)
    assert not np.array_equal(inverted, combined)


def test_passive_native_ancestry_propagates_current_damaged_copy():
    founder = np.asarray([9.0, 7.0])
    copied = np.asarray([4.0, 3.0])
    adult = np.asarray([8.0, 6.0])
    donor, source = native_next_donor("passive_no_rewrite", founder, copied, adult, 2)
    assert np.array_equal(donor, copied)
    assert source == "post-copy-g2"
    assert not np.array_equal(donor, founder)
    rewritten, rewritten_source = native_next_donor("adult_rewrite", founder, copied, adult, 2)
    assert np.array_equal(rewritten, adult)
    assert rewritten_source == "adult-g2"


def test_local_mark_is_compact_scaled_and_renewable():
    bounds = np.asarray([[-10.0, 10.0], [-2.0, 2.0], [-1.0, 1.0]])
    control = np.zeros(3)
    combined = np.asarray([0.01, 1.0, 0.0])
    nodes = [0, 1]
    scale = local_mark_scale(bounds, control, combined, nodes)
    assert np.allclose(scale, [0.2, 1.0])
    mark = encode_local_mark(combined, control, scale, nodes)
    assert np.allclose(mark, [0.05, 1.0])
    copied = copy_local_mark(mark, np.asarray([True, False]), np.zeros(2), 0.85)
    assert np.allclose(copied, [0.0425, 0.0])
    renewed = renew_local_mark(copied, np.ones(2), 4)
    assert renewed[0] > copied[0]
    assert renewed[1] > copied[1]


def test_one_and_two_worker_sentinel_order_is_identical():
    args = [(1, "a"), (2, "b"), (3, "c")]
    assert _parallel(_identity_history_worker, args, 1) == _parallel(
        _identity_history_worker, args, 2
    )


def test_config_rejects_changed_worker_cap(tmp_path):
    payload = json.loads(CONFIG.read_text())
    payload["max_workers"] = 4
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="cap workers at two"):
        load_history_config(path)
