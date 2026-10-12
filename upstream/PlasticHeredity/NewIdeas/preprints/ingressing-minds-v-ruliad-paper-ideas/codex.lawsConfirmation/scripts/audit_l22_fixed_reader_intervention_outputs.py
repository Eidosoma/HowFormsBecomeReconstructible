"""Independent D076 saved-state, replay, recurrence and factorial checks."""

import importlib.util
import hashlib
import json
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("d076_frozen_diagnostic_checker", Path(__file__).with_name("audit_l22_early_signal_loss_outputs.py"))
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
source = diagnostic.source
common, runtime = source.common, source.runtime
TISSUES = tuple(range(30040, 30056))
STEPS, FIELDS, METRICS = (0, 1, 50, 250, 500, 1000), ("V", "R", "theta"), diagnostic.METRICS
MAIN = ("kept_damaged", "kept_native", "scrambled_damaged", "scrambled_native", "donor_damaged", "donor_native")
ARMS = (*MAIN, "scrambled_native_off", "donor_native_off")
ANCHORS = {"kept_damaged": ("writing", "fixed_damaged_reader"), "kept_native": ("writing", "theta_read_off"),
           "scrambled_damaged": ("writing", "scrambled_fixed_reader"), "donor_damaged": ("intervention", "donor_fixed")}
TERMS = {
    "kept_native_minus_damaged": ((1, 1), (0, -1)),
    "scrambled_native_minus_damaged": ((3, 1), (2, -1)),
    "donor_native_minus_damaged": ((5, 1), (4, -1)),
    "donor_minus_scrambled_damaged": ((4, 1), (2, -1)),
    "donor_minus_scrambled_native": ((5, 1), (3, -1)),
    "donor_specific_reader_interaction": ((5, 1), (3, -1), (4, -1), (2, 1)),
    "kept_minus_scrambled_damaged": ((0, 1), (2, -1)),
    "kept_minus_scrambled_native": ((1, 1), (3, -1)),
}


def describe(data):
    result = {}
    for i, arm in enumerate(MAIN):
        result[arm] = {}
        for q, step in enumerate(STEPS):
            result[arm][str(step)] = {}
            for f, field in enumerate(FIELDS):
                result[arm][str(step)][field] = dict(
                    mean={m: float(data["curves"][i, step, f, k]) for k, m in enumerate(METRICS)},
                    messages=[{m: float(data["strata"][i, q, group, f, k]) for k, m in enumerate(METRICS)} for group in range(4)])
    return result


def check_observers(raws, data, saved_arms):
    assert set(data) == {"curves", "strata"}
    for key, shape in (("curves", (6, 1001, 3, 5)), ("strata", (6, 6, 4, 3, 5))):
        assert data[key].shape == shape and data[key].dtype == np.float64 and np.isfinite(data[key]).all()
    for i, arm in enumerate(MAIN):
        for f, key in enumerate(("body_trace", "reference_trace", "theta_trace")):
            scores = diagnostic.observer(raws[arm][key])
            curve = sum(scores[:, w] for w in range(16))/16
            np.testing.assert_allclose(data["curves"][i, :, f], curve, rtol=0., atol=1e-11)
            for q, step in enumerate(STEPS):
                for message in range(4):
                    value = sum(scores[step, w] for w in range(4*message, 4*message+4))/4
                    np.testing.assert_allclose(data["strata"][i, q, message, f], value, rtol=0., atol=1e-11)
    common.close(saved_arms, describe(data))


def check_cell(original, output, tissue):
    assert tissue in TISSUES
    saved = json.loads((output/"analysis.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    common.close(saved["config"], source.CFG)
    parent = common.arrays(original/"writing/parent.npz")
    boundary = common.arrays(original/"writing/boundary.npz")
    ranked = common.arrays(original/"intervention/bodies.npz")
    metadata = json.loads((original/"writing/experiment.json").read_text())
    extra = json.loads((original/"intervention/experiment.json").read_text())
    assert metadata["tissue"] == extra["tissue"] == tissue
    assert metadata["passes"] is True and extra["passes"] is True
    for row in (metadata, extra):
        common.close(row["config"], source.CFG)
        assert all(v is True for v in row["gates"].values())
    assert common.state_digest(parent) == metadata["source_parent_sha256"]
    native = np.ascontiguousarray(boundary["native_theta"])
    digest = hashlib.sha256(f"{native.dtype}:{native.shape}:".encode()+native.tobytes()).hexdigest()
    assert digest == metadata["source_native_sha256"]
    reconstructed = source.rank_body(boundary["kept_V"], boundary["fresh"], 4)
    assert set(ranked) == set(reconstructed)
    for key in ranked:
        np.testing.assert_array_equal(ranked[key], reconstructed[key])
    assert all(set(saved[k]) == set(ARMS) for k in ("recovery", "initial_hashes", "recovery_rng_final"))
    raws = {}
    for arm in ARMS:
        raw = common.arrays(output/f"recovery_{arm}.npz")
        raws[arm] = raw
        body, reader = arm.split("_")[:2]
        value = ranked["donor_V"] if body == "donor" else boundary[f"{body}_V"]
        initial = dict(V=value, ema=value, R=np.zeros_like(value), theta=boundary["damaged_theta"])
        assert common.state_digest(initial) == saved["initial_hashes"][arm]
        expected_keys = {f"s{s}_{k}" for s in STEPS for k in common.KEYS} | {
            "fixed_reader", "body_trace", "reference_trace", "theta_trace", "target_trace", "projection_scale", "target_energy", "theta_target_cross"}
        assert set(raw) == expected_keys
        assert all(v.dtype == np.float64 and np.isfinite(v).all() for v in raw.values())
        fixed = boundary["native_theta"] if reader == "native" else boundary["damaged_theta"]
        np.testing.assert_array_equal(raw["fixed_reader"], fixed)
        common.check_recovery(raw, initial, parent, boundary["fresh"], dict(write=not arm.endswith("_off"), hold=False),
                              source.CFG, saved["recovery"][arm])
        assert saved["recovery_rng_final"][arm] == metadata["recovery_rng_final"]
    for arm, (folder, old) in ANCHORS.items():
        expected = common.arrays(original/folder/f"recovery_{old}.npz")
        assert set(expected) == set(raws[arm])
        for key in expected:
            np.testing.assert_array_equal(raws[arm][key], expected[key])
    off_kept = common.arrays(original/"writing/recovery_body_writer_off.npz")
    alias_keys = ("body_trace", "reference_trace", *(f"s{s}_{k}" for s in STEPS for k in ("V", "ema", "R")))
    for body in ("kept", "scrambled", "donor"):
        off = off_kept if body == "kept" else raws[f"{body}_native_off"]
        for key in alias_keys:
            np.testing.assert_array_equal(raws[f"{body}_native"][key], off[key])
    data = common.arrays(output/"analysis.npz")
    check_observers(raws, data, saved["arms"])
    return dict(tissue=tissue, passes=True, recovery_arms=8, replay_anchors=4, fixed_off_pairs=3,
                recorded_batch_steps=8000, reference_coordinates_checked=512000, theta_coordinates_checked=768000)


def check_pool(values, saved):
    assert len(values) == 16 and set(saved) == {"arms", "contrasts"}
    common.close(saved["arms"], describe({k: sum(d[k] for d in values)/16 for k in ("curves", "strata")}))
    assert set(saved["contrasts"]) == set(TERMS)
    for label, terms in TERMS.items():
        differences, groups = [], []
        for data in values:
            delta = np.zeros((6, 3, 5))
            group = np.zeros((6, 4, 3, 5))
            for arm, sign in terms:
                delta += sign*data["curves"][arm, list(STEPS)]
                group += sign*data["strata"][arm]
            differences.append(delta)
            groups.append(group)
        expected = dict(tissue_differences=[v.tolist() for v in differences], mean=(sum(differences)/16).tolist(),
            minimum=np.minimum.reduce(differences).tolist(), maximum=np.maximum.reduce(differences).tolist(),
            positive=sum((v > 1e-12).astype(int) for v in differences).tolist(),
            negative=sum((v < -1e-12).astype(int) for v in differences).tolist(),
            tied=sum((abs(v) <= 1e-12).astype(int) for v in differences).tolist(), message_mean=(sum(groups)/16).tolist())
        common.close(saved["contrasts"][label], expected)
    return True
