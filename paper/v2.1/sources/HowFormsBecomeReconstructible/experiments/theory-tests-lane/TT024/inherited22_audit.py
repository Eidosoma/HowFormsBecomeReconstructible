"""Independent serial routing, injury and scoring around qualified physics.

No production orchestration functions are imported. Shared inputs are the
declared structural parameters, packet bytes and the inherited independent
physical reference, with the original averaging/scalar tolerances.
"""
import hashlib
import json

import numpy as np

import reference as ref
import tt019_reference as physical


def address(index, future, generation, phase):
    assert phase in ('develop', 'fission', 'repair', 'terminal')
    raw = json.dumps(['TT022_serial_capture_v1', index, future, generation, phase], separators=(',', ':'))
    return int.from_bytes(hashlib.sha256(raw.encode('utf8')).digest()[:16], 'little')


def packet_array(packet, parents):
    assert type(packet) is bytes and len(packet) == 4*parents*2048
    value = np.frombuffer(packet, dtype=np.float64).reshape(4*parents, 16, 16)
    assert np.isfinite(value).all()
    return value


def injury(ctx, incoming, developed, future, generation, selected, boundary, raw, metadata):
    cfg = ctx['config']
    theta = packet_array(incoming, cfg.replicates)
    rng = physical.Coupled(physical.SOURCE_TAG,
        address(ctx['index'], future, generation, 'fission'), 'fission', cfg.replicates)
    axes = rng.integers(0, 2, len(theta)); sides = rng.integers(0, 2, len(theta))
    grid = np.indices((16, 16))
    kept = np.stack([grid[a]//8 == side for a, side in zip(axes, sides)])
    expected = np.where(kept, developed, ctx['tissue'].resting)
    expected = expected+ctx['tissue'].copy_jitter*rng.standard_normal(expected.shape)
    assert set(boundary) == {'fresh', 'injured_V'} and np.all(kept.sum((1, 2)) == 128)
    ref.exact(boundary['fresh'], ~kept, 'fresh half mask')
    ref.exact(boundary['injured_V'], expected, 'injury from this newly developed body')
    assert metadata['rng_final'] == rng.digest()
    state = dict(V=expected, ema=np.zeros_like(expected),
                 R=expected if selected.capture else np.zeros_like(expected), theta=theta)
    for name, value in state.items(): ref.exact(raw['s0_'+name], value, 'declared serial reset '+name)
    return state


def read(ctx, incoming, rcfg, future, generation, phase, raw, metadata, replay):
    key = address(ctx['index'], future, generation, phase)
    theta = packet_array(incoming, rcfg.parents)
    for step in rcfg.times:
        ref.exact(raw[f's{step}_theta'], theta, 'only current packet crosses replacement')
        ref.exact(raw[f's{step}_R'], np.zeros_like(theta), 'no reader memory')
    assert metadata['packet_sha256'] == hashlib.sha256(incoming).hexdigest()
    if replay:
        result = ref.fresh_read({k: ctx[k] for k in ('config', 'tissue', 'ladder', 'bp')},
                                incoming, key, rcfg, False, raw, metadata)
    else:
        result = dict(native_arrays=0, max_native_error=0.)
    ref.scores(ctx['codes'], raw, rcfg)
    return result


def repair(ctx, incoming, developed, rcfg, future, generation, selected, policy,
           boundary, boundary_meta, raw, metadata, body, outgoing, replay):
    cfg = ctx['config']
    state = injury(ctx, incoming, developed, future, generation, selected, boundary, raw, boundary_meta)
    if replay:
        checked = ref.repairs({k: ctx[k] for k in ('config', 'tissue', 'ladder', 'bp')},
            state, address(ctx['index'], future, generation, 'repair'), selected, raw, metadata)
    else:
        checked = dict(native_arrays=0, max_native_error=0., max_average_error=0.)
    expected = raw[f'{"a" if policy == "average" else "s"}{cfg.sweeps}_theta']
    assert outgoing == expected.tobytes(), 'wrong inherited writer output'
    if policy in ('capture_once', 'unchanged'):
        assert outgoing == incoming
        for step in cfg.times: ref.exact(raw[f's{step}_theta'], state['theta'], 'unchanged control')
    if policy == 'held':
        for step in cfg.times: ref.exact(raw[f's{step}_R'], state['R'], 'held only within current body')
    ref.scores(ctx['codes'], {**body, f's{rcfg.sweeps}_V': raw[f's{cfg.sweeps}_V']}, rcfg)
    return checked
