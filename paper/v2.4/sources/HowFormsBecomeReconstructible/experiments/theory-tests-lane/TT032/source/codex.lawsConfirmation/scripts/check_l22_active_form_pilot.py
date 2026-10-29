"""D184 independent routing, replay and scalar scoring checks.

Does not import the pilot, D183 constructor, writer or production scorer.
The physical blueprint_step API is deliberately shared, not independently
reimplemented. Conventional averaging uses an independent online mean.
"""

from dataclasses import replace
import hashlib
import json
import math

import numpy as np

KEYS = ("V", "ema", "R", "theta")


def plan(reported):
    expected = {}
    for packet in ('common', 'residual'):
        for body in ('own', 'partner', 'own_scrambled', 'partner_scrambled', 'history_erased'):
            for mode in ('live', 'fixed', 'writer_off'):
                expected[f'{packet}__{body}__{mode}'] = dict(packet=packet, body=body,
                    reader='fixed' if mode == 'fixed' else 'live', write=mode != 'writer_off',
                    reference_write=True, reset='zero')
        expected[f'{packet}__own__reference_off'] = dict(packet=packet, body='own', reader='live',
            write=True, reference_write=False, reset='zero')
    for body, mode in (('own', 'live'), ('own', 'fixed'), ('own', 'writer_off'), ('own_scrambled', 'live')):
        expected[f'native__{body}__{mode}'] = dict(packet='residual', body=body,
            reader='fixed' if mode == 'fixed' else 'live', write=mode != 'writer_off',
            reference_write=True, reset='native')
    assert reported == expected
    return dict(passes=True, repair_arms=36)


class Coupled:
    def __init__(self, index, phase, rep, namespace):
        tag = f"{namespace}:{index}:{phase}".encode()
        self.rng = np.random.default_rng(int.from_bytes(hashlib.sha256(tag).digest()[:16], "little"))
        self.rep = rep

    def standard_normal(self, shape):
        assert tuple(shape) == (4*self.rep, 16, 16)
        return np.tile(self.rng.standard_normal((self.rep, 16, 16)), (4, 1, 1))

    def digest(self):
        raw = json.dumps(self.rng.bit_generator.state, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


def exact(a, b):
    assert a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


def project(value, norm):
    centered = value - value.mean(axis=(-2, -1), keepdims=True)
    return centered * (norm / np.maximum(centered.std(axis=(-2, -1), keepdims=True), 1e-9))


def repair(ctx, initial, index, spec, raw, outgoing, average, metadata):
    cfg = ctx["config"]
    assert spec["reader"] in ("live", "fixed") and spec["reset"] in ("zero", "native")
    assert set(initial) == set(KEYS)
    exact(initial["R"], np.zeros_like(initial["V"]))
    exact(initial["ema"], np.zeros_like(initial["V"]) if spec["reset"] == "zero" else initial["V"])
    use_average = spec["reader"] == "fixed" and spec["write"] and spec["reset"] == "zero"
    expected_keys = {f"s{s}_{k}" for s in cfg.times for k in KEYS}
    if use_average: expected_keys |= {f"a{s}_{k}" for s in cfg.times for k in ("mean", "theta")}
    assert set(raw) == expected_keys
    state = {k: v.copy() for k, v in initial.items()}
    mean = np.zeros_like(state["V"])
    conventional = state["theta"].copy()
    namespace, phase = ("l22-source-recovery-v1", "recovery") if spec["reset"] == "native" else ("l22-active-form-boundary-v1", "repair")
    rng = Coupled(index, phase, cfg.replicates, namespace)
    bp = ctx["bp"] if spec["reference_write"] else replace(ctx["bp"], rho=0.)
    maximum = 0.

    def compare(step):
        nonlocal maximum
        for k in KEYS: exact(state[k], raw[f"s{step}_{k}"])
        if use_average:
            for k, value in (("mean", mean), ("theta", conventional)):
                error = float(np.max(np.abs(value-raw[f"a{step}_{k}"])))
                maximum = max(maximum, error)
                np.testing.assert_allclose(value, raw[f"a{step}_{k}"], rtol=0., atol=2e-12)

    compare(0)
    for s in range(1, cfg.sweeps+1):
        applied = state["theta"] if spec["reader"] == "live" else initial["theta"]
        state["V"], state["ema"], state["R"] = ctx["api"]["blueprint_step"](
            state["V"], state["ema"], state["R"], applied,
            ctx["tissue"], ctx["ladder"], bp, "T", rng)
        if spec["write"]:
            state["theta"] = project((1-cfg.lam)*state["theta"]+cfg.lam*np.tanh(state["R"]), cfg.norm)
        if use_average:
            mean += (state["V"]-mean)/s
            conventional = project((1-cfg.lam)*conventional+cfg.lam*np.tanh(mean), cfg.norm)
        if s in cfg.times: compare(s)
    assert outgoing == raw[f"s{cfg.sweeps}_theta"].tobytes()
    assert metadata["rng_final"] == rng.digest() and metadata["spec"] == spec
    assert metadata["observations_per_record"] == (cfg.sweeps if use_average else 0)
    assert metadata["carrier_bytes_per_record"] == 2048
    assert metadata["body_and_native_writer_seconds"] >= 0. and metadata["averaging_writer_seconds"] >= 0.
    assert (average is not None) == use_average
    if use_average: assert average == raw[f"a{cfg.sweeps}_theta"].tobytes()
    return dict(passes=True, full_dynamics_replayed=True, native_state_max_abs=0., averaging_max_abs=maximum)


def assay(ctx, packet, cfg, raw, metadata, disabled=False):
    theta = np.frombuffer(packet, dtype=np.float64).reshape(4*cfg.parents, 16, 16)
    expanded = np.repeat(theta, cfg.draws, axis=0).copy()
    birth = Coupled(ctx["index"], "assay_birth", cfg.parents*cfg.draws, "l22-fixed-record-readout-v1")
    noise = Coupled(ctx["index"], "assay", cfg.parents*cfg.draws, "l22-fixed-record-readout-v1")
    v = .2*birth.standard_normal(expanded.shape)
    v -= v.mean(axis=(1, 2), keepdims=True)
    ema, ref = v.copy(), np.zeros_like(v)
    expected_keys = {f"s{s}_{k}" for s in cfg.times for k in KEYS} | {"scores", "probabilities", "correctness", "margins"}
    assert set(raw) == expected_keys
    for s in range(cfg.sweeps+1):
        if s:
            v, ema, ref = ctx["api"]["blueprint_step"](v, ema, ref,
                np.zeros_like(expanded) if disabled else expanded,
                ctx["tissue"], ctx["ladder"], replace(ctx["bp"], rho=0.), "T", noise, c_m=0.)
        assert np.all(ref == 0.)
        if s in cfg.times:
            for k, value in (("V", v), ("ema", ema), ("R", ref), ("theta", expanded)):
                exact(value, raw[f"s{s}_{k}"])
    scores = np.asarray([[math.fsum(float(x)*float(y) for x, y in zip(field.flat, code.flat))/256
                          for code in ctx["codes"]] for field in v])
    ties = abs(scores-scores.max(axis=1, keepdims=True)) <= 1e-12
    probabilities = ties/ties.sum(axis=1, keepdims=True)
    np.testing.assert_allclose(raw["scores"], scores, rtol=0., atol=2e-13)
    exact(raw["probabilities"], probabilities)
    labels = np.arange(len(v))//(cfg.parents*cfg.draws)
    accuracy = probabilities[np.arange(len(v)), labels].reshape(4*cfg.parents, cfg.draws)
    exact(raw["correctness"], accuracy)
    margins = np.asarray([row[m]-max(v for k, v in enumerate(row) if k != m) for row, m in zip(scores, labels)])
    np.testing.assert_allclose(raw["margins"], margins.reshape(4*cfg.parents, cfg.draws), rtol=0., atol=2e-13)
    assert metadata["packet_sha256"] == hashlib.sha256(packet).hexdigest()
    assert metadata["expanded_sha256"] == hashlib.sha256(expanded.tobytes()).hexdigest()
    assert metadata["rng_final"] == noise.digest() and metadata["birth_rng_final"] == birth.digest()
    assert metadata["theta_unchanged"] is metadata["R_zero_every_step"] is True
    assert metadata['accuracy'] == float(accuracy.mean())
    if disabled:
        assert accuracy.mean() == .25
        for group in range(1, 4): exact(v[:cfg.parents*cfg.draws], v[group*cfg.parents*cfg.draws:(group+1)*cfg.parents*cfg.draws])
    return dict(passes=True, full_dynamics_replayed=True, accuracy=float(accuracy.mean()), state_max_abs=0.)


def record_metrics(ctx, theta, parent, raw, cfg, reported):
    n, draws = 4*cfg.parents, cfg.draws
    assert len(reported) == n
    probs, scores = raw["probabilities"], raw["scores"]
    v = raw[f"s{cfg.sweeps}_V"]

    def corr(x, y):
        a, b = [float(z) for z in x.flat], [float(z) for z in y.flat]
        ma, mb = math.fsum(a)/256, math.fsum(b)/256
        a, b = [z-ma for z in a], [z-mb for z in b]
        den = math.sqrt(math.fsum(z*z for z in a)*math.fsum(z*z for z in b))
        return math.fsum(x*y for x, y in zip(a, b))/den if den else 0.

    for i in range(n):
        m, p = i//cfg.parents, ((i//cfg.parents+2) % 4)
        donor = p*cfg.parents+i % cfg.parents
        rows = range(i*draws, (i+1)*draws)
        own = math.fsum(float(probs[j, m]) for j in rows)/draws
        other = math.fsum(float(probs[j, p]) for j in rows)/draws
        expected = dict(world=i, message=m, replicate=i % cfg.parents,
            accuracy=own, partner_accuracy=other, preference=own-other,
            projection_gap=math.fsum(float(scores[j, m]-scores[j, p]) for j in rows)/draws,
            sign_fidelity=sum(bool(x>0)==bool(y>0) for j in rows for x, y in zip(v[j].flat, ctx["codes"][m].flat))/(256*draws),
            theta_corr_parent=corr(theta[i], parent["theta"][i]),
            theta_corr_partner=corr(theta[i], parent["theta"][donor]))
        assert set(reported[i]) == set(expected)
        for k, value in expected.items():
            assert abs(reported[i][k]-value) <= 2e-12, (i, k)
    return dict(passes=True, records=n, independent_scalar_scores=True)


def comparisons(records, reported):
    expected = {}
    for packet in ('common', 'residual'):
        for name, right in (('source', f'{packet}__partner__live'), ('gain', f'input__{packet}'),
                            ('organization', f'{packet}__own_scrambled__live'),
                            ('feedback', f'{packet}__own__fixed'), ('versus_average', f'{packet}__own__average')):
            expected[f'{packet}__{name}'] = (f'{packet}__own__live', right)
        expected[f'{packet}__average_source'] = (f'{packet}__own__average', f'{packet}__partner__average')
        expected[f'{packet}__average_gain'] = (f'{packet}__own__average', f'input__{packet}')
        expected[f'{packet}__fixed_vs_average'] = (f'{packet}__own__fixed', f'{packet}__own__average')
    expected.update(native_feedback=('native__own__live', 'native__own__fixed'),
                    native_organization=('native__own__live', 'native__own_scrambled__live'),
                    native_gain=('native__own__live', 'input__residual'),
                    reset_change=('residual__own__live', 'native__own__live'))
    assert set(reported) == set(expected)
    fields = {'accuracy', 'partner_accuracy', 'preference', 'projection_gap', 'theta_corr_parent'}
    for name, item in reported.items():
        assert (item['left'], item['right']) == expected[name]
        assert set(item['mean']) == fields and len(item['messages']) == 4
        assert all(set(m) == fields for m in item['messages'])
        left, right = records[item["left"]], records[item["right"]]
        assert len(left) == len(right)
        for key, observed in item["mean"].items():
            expected_mean = math.fsum(a[key]-b[key] for a, b in zip(left, right))/len(left)
            assert abs(expected_mean-observed) <= 2e-12
        for m, observed in enumerate(item["messages"]):
            group = [(a, b) for a, b in zip(left, right) if a["message"] == m]
            for key, value in observed.items():
                assert abs(math.fsum(a[key]-b[key] for a, b in group)/len(group)-value) <= 2e-12
    return dict(passes=True, contrasts=len(reported), pooling_unit="tissue", confirmatory_test=False)
