"""Independent D075 observers and reverse-product trajectory accounting."""

import importlib.util
import math
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("d075_frozen_source_checker", Path(__file__).with_name("audit_l22_body_source_outputs.py"))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
runtime, close = source.runtime, source.common.close
NAMES = ("kept_live", "kept_fixed", "kept_off", "scrambled_live", "scrambled_fixed", "scrambled_off",
         "donor_live", "donor_fixed", "donor_off", "native_reader", "native_off", "reference_off", "wrong_fixed", "backup")
OFF = ("kept_off", "scrambled_off", "donor_off", "native_off")
STEPS = (0, 1, 50, 250, 500, 1000)
ENDS = (50, 1000)
PARTS = ("initial", "1", "2-50", "51-250", "251-500", "501-1000")
FIELDS = ("V", "R", "theta")
METRICS = ("own_projection", "donor_projection", "own_minus_donor", "own_accuracy", "donor_accuracy")
PAIRS = {"organization": (0, 3), "donor_vs_scrambled": (6, 3), "kept_live_vs_fixed": (0, 1),
         "scrambled_live_vs_fixed": (3, 4), "donor_live_vs_fixed": (6, 7), "kept_native_vs_fixed": (9, 1)}


def observer(trace):
    assert trace.shape[1] == 16 and trace.shape[2] >= 4 and np.isfinite(trace).all()
    result = np.empty((len(trace), 16, 5))
    for world in range(16):
        own, donor = world//4, (world//4+1) % 4
        scores = trace[:, world, :4]
        ties = abs(scores-scores.max(axis=1)[:, None]) <= 1e-12
        result[:, world, 0] = scores[:, own]
        result[:, world, 1] = scores[:, donor]
        result[:, world, 2] = scores[:, own]-scores[:, donor]
        result[:, world, 3] = ties[:, own]/ties.sum(axis=1)
        result[:, world, 4] = ties[:, donor]/ties.sum(axis=1)
    return result


def check_cell(raws, data, saved):
    assert set(raws) == set(NAMES) and saved["tissue"] in range(30040, 30056)
    shapes = {"curves": (14, 1001, 3, 5), "strata": (14, 6, 4, 3, 5),
              "R_components": (14, 2, 6, 16, 4), "theta_components": (14, 2, 6, 16, 6)}
    assert set(data) == set(shapes)
    for key, shape in shapes.items():
        assert data[key].shape == shape and data[key].dtype == np.float64 and np.isfinite(data[key]).all()
    for arm, name in enumerate(NAMES):
        raw = raws[name]
        assert raw["projection_scale"].shape == (1000, 16) and np.all(raw["projection_scale"] > 0)
        assert np.isfinite(raw["projection_scale"]).all()
        assert raw["target_trace"].shape == (1000, 16, 6) and np.isfinite(raw["target_trace"]).all()
        traces = (raw["body_trace"], raw["reference_trace"], raw["theta_trace"])
        for f, (field, trace) in enumerate(zip(FIELDS, traces)):
            values = observer(trace)
            mean = sum(values[:, w] for w in range(16))/16
            np.testing.assert_allclose(data["curves"][arm, :, f], mean, rtol=0., atol=1e-11)
            for j, step in enumerate(STEPS):
                state = raw[f"s{step}_{field}"]
                assert state.shape == (16, 16, 16) and np.isfinite(state).all()
                np.testing.assert_allclose(trace[step, :, :4], source.common.scores(state), rtol=0., atol=1e-12)
                for message in range(4):
                    group = [math.fsum(float(values[step, w, k]) for w in range(4*message, 4*message+4))/4 for k in range(5)]
                    np.testing.assert_allclose(data["strata"][arm, j, message, f], group, rtol=0., atol=1e-11)
        for step in STEPS[1:]:
            target = np.tanh(raw[f"s{step}_R"])
            target -= target.mean(axis=(1, 2), keepdims=True)
            np.testing.assert_allclose(raw["target_trace"][step-1, :, :4], source.common.scores(target), rtol=0., atol=1e-12)
        ones = np.ones((1000, 16))
        ra, rb = (ones, np.zeros_like(ones)) if name == "reference_off" else (.998*ones, .002*ones)
        ta, tb = (ones, np.zeros_like(ones)) if name in OFF else (.999*raw["projection_scale"], .001*raw["projection_scale"])
        for field, initial, forcing, a, b, actual in (
            ("R", traces[1][0], traces[0][1:], ra, rb, traces[1]),
            ("theta", traces[2][0], raw["target_trace"], ta, tb, traces[2])):
            expected = reverse_parts(initial, forcing, a, b)
            np.testing.assert_allclose(data[f"{field}_components"][arm], expected, rtol=0., atol=1e-11)
            np.testing.assert_allclose(expected.sum(axis=1), actual[list(ENDS)], rtol=0., atol=1e-11)
            np.testing.assert_allclose(actual[1:], actual[:-1]*a[..., None]+forcing*b[..., None], rtol=0., atol=1e-11)
        if name in OFF:
            np.testing.assert_array_equal(raw["projection_scale"], ones)
            for step in STEPS:
                np.testing.assert_array_equal(raw[f"s{step}_theta"], raw["s0_theta"])
    alias_fields = ("body_trace", "reference_trace", *(f"s{s}_{k}" for s in STEPS for k in ("V", "ema", "R")))
    for body in ("kept", "scrambled", "donor"):
        for key in alias_fields:
            np.testing.assert_array_equal(raws[f"{body}_fixed"][key], raws[f"{body}_off"][key])
        for key in ("V", "ema", "R", "theta"):
            np.testing.assert_array_equal(raws[f"{body}_live"][f"s1_{key}"], raws[f"{body}_fixed"][f"s1_{key}"])
    for key in alias_fields:
        np.testing.assert_array_equal(raws["native_reader"][key], raws["native_off"][key])
    close(saved, {"tissue": saved["tissue"], "passes": True, "arms": description(data)})
    return dict(tissue=saved["tissue"], passes=True, recovery_arms=14, recorded_batch_steps=14000,
                reference_coordinates_checked=896000, theta_coordinates_checked=1344000,
                fixed_off_pairs=4, live_fixed_first_steps=3)


def reverse_parts(initial, forcing, a, b, endpoints=ENDS, bands=((1, 1), (2, 50), (51, 250), (251, 500), (501, 1000))):
    result = []
    for end in endpoints:
        carry = np.ones(len(initial))
        parts = np.zeros((len(bands)+1, *initial.shape))
        for s in range(end, 0, -1):
            band = next(i+1 for i, (lo, hi) in enumerate(bands) if lo <= s <= hi)
            parts[band] += (carry*b[s-1])[:, None]*forcing[s-1]
            carry *= a[s-1]
        parts[0] = carry[:, None]*initial
        result.append(parts)
    return np.stack(result)


def description(data):
    result = {}
    for arm, name in enumerate(NAMES):
        checkpoints = {}
        for j, step in enumerate(STEPS):
            checkpoints[str(step)] = {}
            for f, field in enumerate(FIELDS):
                mean = {m: float(data["curves"][arm, step, f, k]) for k, m in enumerate(METRICS)}
                groups = [{m: float(data["strata"][arm, j, group, f, k]) for k, m in enumerate(METRICS)} for group in range(4)]
                checkpoints[str(step)][field] = {"mean": mean, "messages": groups}
        accounting = {}
        for j, step in enumerate(ENDS):
            accounting[str(step)] = {}
            for field in ("R", "theta"):
                records = {}
                for c, component in enumerate(PARTS):
                    values = data[f"{field}_components"][arm, j, c]
                    own = math.fsum(float(values[w, w//4]) for w in range(16))/16
                    donor = math.fsum(float(values[w, (w//4+1) % 4]) for w in range(16))/16
                    records[component] = dict(own_projection=own, donor_projection=donor, own_minus_donor=own-donor)
                accounting[str(step)][field] = records
        result[name] = {"checkpoints": checkpoints, "accounting": accounting}
    return result


def check_pool(arrays, saved):
    assert len(arrays) == 16
    mean = {k: sum(a[k] for a in arrays)/16 for k in arrays[0]}
    close(saved["arms"], description(mean))
    assert set(saved["contrasts"]) == set(PAIRS)
    for name, (left, right) in PAIRS.items():
        delta = [a["curves"][left, list(STEPS)]-a["curves"][right, list(STEPS)] for a in arrays]
        expected = {"mean": (sum(delta)/16).tolist(), "minimum": np.minimum.reduce(delta).tolist(),
                    "maximum": np.maximum.reduce(delta).tolist(),
                    "positive": sum((v > 1e-12).astype(int) for v in delta).tolist(),
                    "negative": sum((v < -1e-12).astype(int) for v in delta).tolist(),
                    "tied": sum((abs(v) <= 1e-12).astype(int) for v in delta).tolist()}
        close(saved["contrasts"][name], expected)
    return True
