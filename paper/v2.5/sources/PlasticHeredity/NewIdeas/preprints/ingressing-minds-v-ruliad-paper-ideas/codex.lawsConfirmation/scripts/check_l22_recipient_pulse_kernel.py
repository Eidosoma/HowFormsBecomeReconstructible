"""Independent D195 pulse replay: no import of the production pulse kernel.

Shares only the unchanged ladder physics, wire digest and historical scalar
projection/RNG helpers. Reconstructs all reference routing and writer updates.
"""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def historical():
    spec = importlib.util.spec_from_file_location('d193_old_checker',
        Path(__file__).with_name('check_l22_snapshot_routes.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


old = historical()
exact, project, Coupled = old.exact, old.project, old.Coupled
KEYS = ('V', 'ema', 'R', 'theta')
KINDS = ('LL', 'YL', 'LL_pulse', 'YL_pulse', 'writer_off', 'writer_off_pulse', 'trace_writer', 'snapshot_writer')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def array_digest(value): return hashlib.sha256(value.tobytes()).hexdigest()


def physical(ctx):
    return digest({k: asdict(ctx[k]) for k in ('config', 'tissue', 'ladder', 'bp')})


def validate_start(ctx, start, index, stream):
    assert type(index) is int and index >= 0 and stream in ('A', 'B')
    assert set(start) == set(KEYS)
    cfg = ctx['config']
    for value in start.values():
        assert value.dtype == np.float64 and value.shape == (4*cfg.replicates, 16, 16)
        assert np.isfinite(value).all()
    exact(start['ema'], np.zeros_like(start['V'])); exact(start['R'], np.zeros_like(start['V']))
    assert tuple(sorted(set(cfg.times))) == cfg.times and {0, 1, cfg.sweeps} <= set(cfg.times)
    assert cfg.times[0] == 0 and cfg.times[-1] == cfg.sweeps and 0 < cfg.lam < 1
    assert cfg.norm > 0 and 0 < ctx['bp'].rho < 1 and ctx['bp'].c_m > 0


def header(ctx, start, index, packet, stream, trace):
    from laws_confirmation.l17_r_channel import state_digest

    cfg, f, p = ctx['config'], trace.frames, trace.provenance
    assert f.dtype == np.float64 and f.shape == (cfg.sweeps+1, 4*cfg.replicates, 16, 16)
    assert f.flags.c_contiguous and np.isfinite(f).all()
    exact(f[0], start['V'])
    assert isinstance(p['rng_final'], str) and len(p['rng_final']) == 64
    assert all(c in '0123456789abcdef' for c in p['rng_final'])
    assert p == dict(schema='d193_reference_trace_v1', index=index, packet=packet, stream=stream,
        boundary_input_sha256=state_digest(start), physical_sha256=physical(ctx),
        frames_sha256=array_digest(f), rng_final=p['rng_final'], sweeps=cfg.sweeps,
        frame_count=cfg.sweeps+1, bytes_per_record=(cfg.sweeps+1)*2048)
    return digest(p)


def body_step(ctx, v, ema, theta0, reference, rng):
    from ladder_web.engine import ladder_step

    v, ema, _ = ladder_step(v, ema, theta0, ctx['tissue'], ctx['ladder'], 'A', rng, None, None)
    correction = ctx['bp'].c_m*(reference-v)
    correction -= correction.mean(axis=(-2, -1), keepdims=True)
    return np.clip(v+ctx['tissue'].dt*correction, -2., 2.), ema


def trace(ctx, start, index, packet, stream, value):
    """Replay the entire LL body, not merely the supplied trace's own hash."""
    validate_start(ctx, start, index, stream)
    identity = header(ctx, start, index, packet, stream, value)
    rng = Coupled(index, stream+':repair', ctx['config'].replicates, 'd193-yoked-reference-v1')
    v, e, r = start['V'].copy(), start['ema'].copy(), start['V'].copy()
    for t in range(1, ctx['config'].sweeps+1):
        v, e = body_step(ctx, v, e, start['theta'], r, rng)
        r = r+ctx['bp'].rho*(v-r)
        exact(r, value.frames[t])
    assert value.provenance['rng_final'] == rng.digest()
    return dict(passes=True, trace_sha256=identity, full_frames_replayed=True,
                dynamics_sweeps=ctx['config'].sweeps, independent_physics_implementation=False)


def repair(ctx, start, index, stream, spec, result, donor=None):
    from laws_confirmation.l17_r_channel import state_digest

    validate_start(ctx, start, index, stream)
    assert set(spec) == {'packet', 'kind'} and spec['packet'] in ('common', 'residual') and spec['kind'] in KINDS
    assert set(result) == {'raw', 'outgoing', 'trace', 'metadata'}
    cfg, kind, meta, raw = ctx['config'], spec['kind'], result['metadata'], result['raw']
    free = kind in ('trace_writer', 'snapshot_writer')
    byoke, wyoke = kind in ('YL', 'YL_pulse'), kind == 'trace_writer'
    pulse, event = kind.endswith('_pulse'), cfg.sweeps//2+1
    uses = byoke or wyoke
    assert uses == (donor is not None)
    donor_stream = (stream if kind == 'self_replay' else ('B' if stream == 'A' else 'A')) if uses else None
    donor_proof = trace(ctx, start, index, spec['packet'], donor_stream, donor) if uses else None
    captured = result['trace'] is not None
    assert not captured or kind == 'LL'
    assert meta['capture_trace'] is captured
    assert meta['seconds'] >= 0 and np.isfinite(meta['seconds'])
    expected_keys = {f's{t}_{k}' for t in cfg.times for k in
        (('theta', 'S', 'writer_input') if free else (*KEYS, 'S', 'body_input', 'writer_input'))}
    if pulse: expected_keys |= {'pulse_'+phase+'_'+k for phase in ('before','after','step') for k in KEYS}
    assert set(raw) == expected_keys
    theta, r, s = start['theta'].copy(), start['V'].copy(), start['V'].copy()
    v, e, b_input, w_input = start['V'].copy(), start['ema'].copy(), s.copy(), s.copy()
    rng = None if free else Coupled(index, stream+':repair', cfg.replicates, 'd193-yoked-reference-v1')
    inputs = hashlib.sha256()
    if captured:
        header(ctx, start, index, spec['packet'], stream, result['trace'])
        exact(result['trace'].frames[0], s)

    def checkpoint(t):
        wanted = dict(theta=theta, S=s, writer_input=w_input)
        if not free: wanted.update(V=v, ema=e, R=r, body_input=b_input)
        for k, value in wanted.items(): exact(raw[f's{t}_{k}'], value)

    def event_check(phase):
        for key, value in dict(V=v,ema=e,R=r,theta=theta).items(): exact(raw['pulse_'+phase+'_'+key],value)
    checkpoint(0)
    for t in range(1, cfg.sweeps+1):
        if pulse and t == event:
            event_check('before')
            v = v.copy()
            for row in range(4,12):
                for col in range(4,12): v[:,row,col] = -v[:,row,col]
            event_check('after')
        if not free:
            b_input = donor.frames[t-1] if byoke else r
            v, e = body_step(ctx, v, e, start['theta'], b_input, rng)
            r = r+ctx['bp'].rho*(v-r)
            inputs.update(b_input.tobytes())
        w_input = donor.frames[t] if wyoke else (s if free else r)
        if kind not in ('writer_off','writer_off_pulse'): theta = project((1-cfg.lam)*theta+cfg.lam*np.tanh(w_input), cfg.norm)
        inputs.update(w_input.tobytes())
        if pulse and t == event: event_check('step')
        if captured: exact(result['trace'].frames[t], r)
        if t in cfg.times: checkpoint(t)
    expected = dict(pulse=dict(enabled=pulse,step=event if pulse else None,rows=[4,12],columns=[4,12],operation='sign_inversion_V_only',random_draws=0), spec=spec, index=index, stream=stream, boundary_input_sha256=state_digest(start),
        physical_sha256=physical(ctx), snapshot_sha256=array_digest(s),
        donor_sha256=donor_proof['trace_sha256'] if uses else None, donor_stream=donor_stream,
        body_free=free, body_theta_fixed=True, rng_final=None if free else rng.digest(),
        inputs_sha256=inputs.hexdigest(), body_sweeps=0 if free else cfg.sweeps,
        writer_sweeps=0 if kind in ('writer_off','writer_off_pulse') else cfg.sweeps, carrier_bytes_per_record=2048,
        snapshot_bytes_per_record=2048, trace_input_bytes_per_record=(cfg.sweeps+1)*2048 if uses else 0,
        trace_output_bytes_per_record=(cfg.sweeps+1)*2048 if captured else 0,
        capture_trace=captured, seconds=meta['seconds'])
    assert meta == expected
    assert result['outgoing'] == theta.tobytes()
    if captured: assert result['trace'].provenance['rng_final'] == rng.digest()
    return dict(passes=True, pulse_checked=pulse, full_dynamics_replayed=True, all_inputs_replayed=True,
        trace_verified=uses or captured, recipient_dynamics_sweeps=0 if free else cfg.sweeps,
        donor_replay_sweeps=cfg.sweeps if uses else 0, independent_physics_implementation=False)
