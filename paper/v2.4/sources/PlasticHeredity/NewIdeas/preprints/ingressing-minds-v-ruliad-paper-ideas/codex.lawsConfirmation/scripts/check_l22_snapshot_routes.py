"""D192 independent access/replay checks; shares the frozen ladder physics only.

No import of the new route implementation. Full body/reference/writer ordering
is reconstructed explicitly, with independently addressed coupled noise.
"""

import hashlib
import importlib.util
from pathlib import Path

import numpy as np


def historical_checker():
    spec = importlib.util.spec_from_file_location('d192_native_capture_checker',
        Path(__file__).with_name('check_l22_early_capture.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


historical = historical_checker()
exact, project, Coupled = historical.old.exact, historical.old.project, historical.old.Coupled
KEYS = ('V', 'ema', 'R', 'theta')


def plan(reported):
    expected = {}
    for p in ('common', 'residual'):
        def spec(kind='gated', b=True, w=True, write=True):
            return dict(packet=p, kind=kind, body_access=b, writer_access=w, write=write)
        for b in (False, True):
            for w in (False, True): expected[f'{p}__B{int(b)}W{int(w)}'] = spec(b=b, w=w)
        expected[p+'__held_B1W1'] = spec('held')
        expected[p+'__held_B0W1'] = spec('held', b=False)
        expected[p+'__snapshot_only'] = spec('snapshot_only')
        expected[p+'__writer_off'] = spec(write=False)
        expected[p+'__scrambled_B1W1'] = spec('scrambled')
        for k in ('ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live'):
            expected[p+'__'+k] = spec(k)
    assert reported == expected and len(reported) == 26
    return dict(passes=True, repair_paths=26, body_free_paths=2)


def repair(ctx, start, index, spec, result):
    from ladder_web.engine import ladder_step
    # Use the old state digest only for the wire identity, never route dynamics.
    from laws_confirmation.l17_r_channel import state_digest

    cfg, bp = ctx['config'], ctx['bp']
    raw, meta = result['raw'], result['metadata']
    assert set(start) == set(KEYS) and spec['packet'] in ('common', 'residual')
    assert meta['route_spec'] == spec and meta['boundary_input_sha256'] == state_digest(start)
    exact(start['R'], np.zeros_like(start['V'])); exact(start['ema'], np.zeros_like(start['V']))
    kind = spec['kind']
    if kind in ('ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live'):
        captured = kind.startswith('captured')
        original_spec = dict(base=dict(packet=spec['packet'], body='own',
            reader='fixed' if kind == 'ordinary_fixed' else 'live', write=True,
            reference_write=kind != 'captured_held_live', reset='zero'), capture=captured)
        state = {k: v.copy() for k, v in start.items()}
        if captured: state['R'] = state['V'].copy()
        assert meta['native_bridge'] is True and meta['body_free'] is False
        proof = historical.repair(ctx, state, index, original_spec, raw,
            result['outgoing'], result['average'], meta | {'initialization_seconds': 0.})
        return proof | dict(route_native_bridge=True)

    free = kind == 'snapshot_only'
    held = kind in ('held', 'snapshot_only')
    assert kind in ('gated', 'held', 'snapshot_only', 'scrambled')
    assert meta['native_bridge'] is False and meta['body_free'] is free and meta['body_theta_fixed'] is True
    s = start['V'].copy()
    if kind == 'scrambled':
        tag = f'd192-snapshot-routes-v1:{index}:snapshot_shuffle'.encode()
        g = np.random.default_rng(int.from_bytes(hashlib.sha256(tag).digest()[:16], 'little'))
        permutations = np.array([g.permutation(256) for _ in range(cfg.replicates)])
        exact(permutations, raw['snapshot_permutations'])
        for i in range(len(s)): s[i] = start['V'][i].ravel()[permutations[i % cfg.replicates]].reshape(16, 16)
        np.testing.assert_array_equal(np.sort(s.reshape(len(s), -1)), np.sort(start['V'].reshape(len(s), -1)))
    assert meta['snapshot_sha256'] == hashlib.sha256(s.tobytes()).hexdigest()
    assert meta['snapshot_bytes_per_record'] == meta['carrier_bytes_per_record'] == 2048
    assert meta['snapshot_observations_per_record'] == 1
    assert meta['body_sweeps'] == (0 if free else cfg.sweeps)
    assert meta['writer_sweeps'] == (cfg.sweeps if spec['write'] else 0)
    assert meta['seconds'] >= 0
    avg = kind == 'gated' and spec['body_access'] and spec['writer_access'] and spec['write']
    assert meta['average_observations_per_record'] == (cfg.sweeps+1 if avg else 0)
    wanted = {f's{t}_{k}' for t in cfg.times for k in (('theta', 'S', 'writer_input') if free
        else (*KEYS, 'S', 'U', 'body_input', 'writer_input', 'a'))}
    if avg: wanted |= {f'a{t}_{k}' for t in cfg.times for k in ('mean', 'theta')}
    if kind == 'scrambled': wanted.add('snapshot_permutations')
    assert set(raw) == wanted
    state = {k: v.copy() for k, v in start.items()}; state['R'] = s.copy()
    a, rho = 1., 0. if held else bp.rho
    b_input = s.copy() if spec['body_access'] else np.zeros_like(s)
    w_input = s.copy() if spec['writer_access'] else np.zeros_like(s)
    total, averaged = start['V'].copy(), start['theta'].copy()
    rng = None if free else Coupled(index, 'repair', cfg.replicates, 'l22-active-form-boundary-v1')
    inputs, observation_only, maximum = hashlib.sha256(), np.zeros_like(s), 0.

    def compare(t):
        if free:
            exact(state['theta'], raw[f's{t}_theta']); exact(s, raw[f's{t}_S'])
            exact(s, raw[f's{t}_writer_input'])
        else:
            for k in KEYS: exact(state[k], raw[f's{t}_{k}'])
            for k, v in (('S', s), ('U', state['R']-a*s), ('body_input', b_input),
                         ('writer_input', w_input), ('a', np.asarray(a, dtype=np.float64))):
                exact(v, raw[f's{t}_{k}'])
        if avg:
            exact(total/(t+1), raw[f'a{t}_mean']); exact(averaged, raw[f'a{t}_theta'])

    compare(0)
    for t in range(1, cfg.sweeps+1):
        if free:
            state['theta'] = project((1-cfg.lam)*state['theta']+cfg.lam*np.tanh(s), cfg.norm)
            inputs.update(s.tobytes())
        else:
            b_input = state['R'] if spec['body_access'] else state['R']-a*s
            v, e, _ = ladder_step(state['V'], state['ema'], start['theta'],
                                  ctx['tissue'], ctx['ladder'], 'A', rng, None, None)
            drift = bp.c_m*(b_input-v)
            drift = drift-drift.mean(axis=(-2, -1), keepdims=True)
            v = np.clip(v+ctx['tissue'].dt*drift, -2., 2.)
            r = state['R']+rho*(v-state['R'])
            a = (1-rho)*a
            observation_only = (1-rho)*observation_only+rho*v
            u = r-a*s
            maximum = max(maximum, float(np.max(np.abs(u-observation_only))))
            assert maximum <= 2e-12
            w_input = r if spec['writer_access'] else u
            th = project((1-cfg.lam)*state['theta']+cfg.lam*np.tanh(w_input), cfg.norm) if spec['write'] else state['theta'].copy()
            state = dict(V=v, ema=e, R=r, theta=th)
            inputs.update(b_input.tobytes()); inputs.update(w_input.tobytes())
            if avg:
                total += v
                averaged = project((1-cfg.lam)*averaged+cfg.lam*np.tanh(total/(t+1)), cfg.norm)
        if t in cfg.times: compare(t)
    assert result['outgoing'] == raw[f's{cfg.sweeps}_theta'].tobytes()
    assert (result['average'] is not None) == avg
    if avg: assert result['average'] == raw[f'a{cfg.sweeps}_theta'].tobytes()
    assert meta['rng_final'] == (None if free else rng.digest())
    assert meta['inputs_sha256'] == inputs.hexdigest()
    assert meta['decomposition_max_abs'] == maximum
    return dict(passes=True, full_dynamics_replayed=True, state_max_abs=0.,
                direct_inputs_replayed=True, body_free=free, decomposition_max_abs=maximum,
                independent_physics_implementation=False)
