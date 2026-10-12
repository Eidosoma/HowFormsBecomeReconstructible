"""Independent D186 reset, replay and contrasts. Shares only frozen physics."""

from dataclasses import replace
import importlib.util
import math
from pathlib import Path

import numpy as np


def old_checker():
    spec = importlib.util.spec_from_file_location('d186_frozen_d184_checks', Path(__file__).with_name('check_l22_active_form_pilot.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = old_checker()
KEYS = ('V', 'ema', 'R', 'theta')


def plan(reported):
    base = {k:v['base'] for k,v in reported.items() if not k.startswith('capture__')}
    old.plan(base)
    expected = {k:dict(base=v, capture=False) for k,v in base.items()}
    for k,v in base.items():
        if v['reset'] == 'zero':
            expected['capture__'+k.replace('reference_off','reference_held')] = dict(base=v, capture=True)
    assert reported == expected and len(reported) == 68
    return dict(passes=True, repair_paths=68)


def initial(built, original, spec, actual):
    assert set(actual) == set(KEYS)
    s, capture = spec['base'], spec['capture']
    v = built['body_'+s['body']]
    if s['reset'] == 'native':
        assert not capture
        v = original['kept_V' if s['body'] == 'own' else 'scrambled_V']
    expected = dict(V=v, theta=built[s['packet']], R=v if capture else np.zeros_like(v),
                    ema=v if s['reset'] == 'native' else np.zeros_like(v))
    for k in KEYS: old.exact(actual[k], expected[k])
    return dict(passes=True, reference_from_current_body=capture, parent_memory_used=False)


def repair(ctx, start, index, spec, raw, outgoing, average, meta):
    cfg, s, capture = ctx['config'], spec['base'], spec['capture']
    assert meta['spec'] == spec and meta['birth_capture_observations'] == int(capture)
    assert meta['body_observations_available_per_record'] == cfg.sweeps+int(capture)
    assert meta['reference_held'] is (not s['reference_write'])
    assert meta['initialization_seconds'] >= 0
    if not capture:
        proof = old.repair(ctx, start, index, s, raw, outgoing, average, meta | {'spec':s})
        return proof | dict(birth_capture=False)
    old.exact(start['R'], start['V'])
    old.exact(start['ema'], np.zeros_like(start['V']))
    use_average = s['reader'] == 'fixed' and s['write']
    expected = {f's{t}_{k}' for t in cfg.times for k in KEYS}
    if use_average: expected |= {f'a{t}_{k}' for t in cfg.times for k in ('mean','theta')}
    assert set(raw) == expected
    state = {k:v.copy() for k,v in start.items()}
    mean, conventional = state['V'].copy(), state['theta'].copy()
    rng = old.Coupled(index, 'repair', cfg.replicates, 'l22-active-form-boundary-v1')
    bp = ctx['bp'] if s['reference_write'] else replace(ctx['bp'],rho=0.)
    maximum = 0.

    def compare(t):
        nonlocal maximum
        for k in KEYS: old.exact(state[k],raw[f's{t}_{k}'])
        if use_average:
            for k,v in (('mean',mean),('theta',conventional)):
                maximum = max(maximum,float(np.max(np.abs(v-raw[f'a{t}_{k}']))))
                np.testing.assert_allclose(v,raw[f'a{t}_{k}'],rtol=0.,atol=2e-12)

    compare(0)
    for t in range(1,cfg.sweeps+1):
        theta = state['theta'] if s['reader'] == 'live' else start['theta']
        state['V'],state['ema'],state['R'] = ctx['api']['blueprint_step'](
            state['V'],state['ema'],state['R'],theta,ctx['tissue'],ctx['ladder'],bp,'T',rng)
        if s['write']:
            state['theta'] = old.project((1-cfg.lam)*state['theta']+cfg.lam*np.tanh(state['R']),cfg.norm)
        if use_average:
            mean += (state['V']-mean)/(t+1)
            conventional = old.project((1-cfg.lam)*conventional+cfg.lam*np.tanh(mean),cfg.norm)
        if t in cfg.times: compare(t)
    assert outgoing == raw[f's{cfg.sweeps}_theta'].tobytes()
    assert meta['rng_final'] == rng.digest()
    assert (average is not None) == use_average
    assert meta['observations_per_record'] == (cfg.sweeps+1 if use_average else 0)
    assert meta['carrier_bytes_per_record'] == 2048
    assert meta['conventional_extra_fields'] == (2 if use_average else 0)
    assert meta['body_and_native_writer_seconds'] >= 0 and meta['averaging_writer_seconds'] >= 0
    if use_average: assert average == raw[f'a{cfg.sweeps}_theta'].tobytes()
    return dict(passes=True, full_dynamics_replayed=True, birth_capture=True,
                native_state_max_abs=0., averaging_max_abs=maximum)


def comparisons(records, reported):
    ordinary = {k:v for k,v in reported.items() if not k.startswith('capture__')}
    old.comparisons(records, ordinary)
    expected = {}
    for p in ('common','residual'):
        prefix = f'capture__{p}__'
        own = prefix+'own__live'
        targets = dict(capture_gain=f'{p}__own__live', source=prefix+'partner__live',
            gain='input__'+p, organization=prefix+'own_scrambled__live',
            erasure=prefix+'history_erased__live', feedback=prefix+'own__fixed',
            versus_average=prefix+'own__average', reference_refresh=prefix+'own__reference_held',
            writer=prefix+'own__writer_off')
        expected.update({prefix+k:(own,v) for k,v in targets.items()})
        expected[prefix+'fixed_vs_average'] = (prefix+'own__fixed',prefix+'own__average')
        expected[prefix+'average_gain'] = (prefix+'own__average','input__'+p)
        expected[prefix+'average_source'] = (prefix+'own__average',prefix+'partner__average')
    assert set(reported)-set(ordinary) == set(expected) and len(reported) == 44
    fields = {'accuracy','partner_accuracy','preference','projection_gap','theta_corr_parent'}
    for name,(left,right) in expected.items():
        item = reported[name]
        assert item['left'] == left and item['right'] == right
        assert set(item['mean']) == fields and len(item['messages']) == 4
        assert all(set(v) == fields for v in item['messages'])
        a,b = records[left],records[right]
        assert len(a) == len(b)
        for message,observed in [(None,item['mean']),*enumerate(item['messages'])]:
            pairs = [(x,y) for x,y in zip(a,b) if message is None or x['message'] == message]
            assert pairs
            for key,value in observed.items():
                wanted = math.fsum(x[key]-y[key] for x,y in pairs)/len(pairs)
                assert abs(wanted-value) <= 2e-12
    return dict(passes=True, contrasts=44, confirmatory_test=False)
