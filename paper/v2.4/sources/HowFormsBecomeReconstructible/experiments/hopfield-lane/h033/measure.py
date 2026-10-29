"""Audited probes, six-replacement observations and sealed remaining futures."""
from datetime import datetime
from pathlib import Path
import json
import time
import numpy as np
from h007.io import checksum, save, verify
from h019.audit import load, refinement
from h022 import numerics
from h023.measure import simulate_probe
from h028.measure import audit as probe_audit
from h030.measure import baseline_parity
from h033 import design as d


def finite_diagnostics(raw, data, level):
    endpoint = raw['history'][..., -1, :]
    changes = (endpoint[:, 1:]-endpoint[:, :1]).reshape(len(endpoint), 2, 2, 2, 3)
    size = data['actual_sizes'][:, :, None, None, None]
    signed = np.divide(changes, size, out=np.zeros_like(changes), where=size > 0)
    signed /= np.array([-1., 1.])[None, None, None, :, None]
    zero = data['actual_sizes'] == 0
    assert not np.any(changes[zero] != 0)
    predicted = np.einsum('nij,nkj->nki', data[f'jacobian_{level}'], data['directions'])
    return dict(signed_secant=signed, finite_gain=np.linalg.norm(signed, axis=-1),
        predicted_direction=predicted,
        terminal_success=(np.tanh(2*endpoint) > .5).all(axis=-1),
        actual_sizes=data['actual_sizes'], zero_radius=zero)


def prefix_parity(finite, future):
    for key in ('history', 'entries', 'independent_history', 'independent_entries'):
        expected = np.repeat(finite[key][:, :, None], d.TAILS, axis=2)
        expected = expected.reshape(len(expected), 9*d.TAILS, *expected.shape[-2:])
        np.testing.assert_array_equal(expected, future[key][..., :expected.shape[-2], :])


def observation_parity(observation, future):
    for key in ('history', 'entries', 'independent_history', 'independent_entries'):
        count = d.OBSERVATION+int(key.endswith('history'))
        assert observation[key].shape[-2] == count
        np.testing.assert_array_equal(observation[key], future[key][..., :count, :])


def audit(raws, data, kind):
    assert kind in ('probe', 'finite', 'observation', 'future') and len(raws) == 3
    if kind == 'probe':
        result = probe_audit(raws, data, 'probe')
    else:
        audits = [numerics.audit(raw, data) for raw in raws]; refined = refinement(raws)
        horizon = {'finite': 3, 'observation': d.OBSERVATION, 'future': 24}[kind]
        clocks = all(float(raw['dt']) == dt and float(raw['interval']) == float(data['interval'])
                     and raw['history'].shape[-2] == horizon+1 for raw, dt in zip(raws, d.DTS))
        parity = all(baseline_parity(raw, data, level, kind) for level, raw in enumerate(raws))
        result = dict(qualified=bool(clocks and parity and refined['qualified'] and all(a['qualified'] for a in audits)),
            audits=audits, refinement=refined, clocks=bool(clocks), archived_baseline_exact=parity,
            old_global_bound_all_passed=all(a['old_global_2e11_passed'] for a in audits),
            global_bound=1e-4, local_roundoff_factor=64)
        if kind == 'finite':
            diagnostics = [finite_diagnostics(raw, data, level) for level, raw in enumerate(raws)]
            errors = [float(np.max(np.linalg.norm(a['signed_secant']-b['signed_secant'], axis=-1)/
                np.maximum(1., np.linalg.norm(b['signed_secant'], axis=-1)))) for a, b in zip(diagnostics[:-1], diagnostics[1:])]
            result['normalized_secant_refinement'] = errors
            result['qualified'] = bool(result['qualified'] and max(errors) <= 1e-4)
    result['entrants_within_original_support'] = d.support(data)
    result['qualified'] = bool(result['qualified'] and result['entrants_within_original_support'])
    return result


def require_test_seal(out):
    verify(out, 'prediction_sha256.json')
    sealed = json.loads((out/'PREDICTION_SEAL.json').read_text())
    submitted = json.loads((out/'TEST_SUBMISSION.json').read_text())
    assert sealed['test_future_tasks_submitted'] is False
    assert sealed['label'] == 'PROSPECTIVE_DEVELOPMENT'
    assert submitted['prediction_manifest_sha256'] == checksum(out/'prediction_sha256.json')
    for name, digest in sealed['bound_manifests'].items():
        assert checksum(out/name) == digest
    assert datetime.fromisoformat(submitted['submitted_utc']) > datetime.fromisoformat(sealed['sealed_utc'])


def simulate_folder(folder, data, kind, finite_folder=None, observation_folder=None):
    folder.mkdir(parents=True, exist_ok=False); raws = []
    interval = float(data['interval'])
    for level, dt in enumerate(d.DTS):
        raw = (simulate_probe(data, dt, interval) if kind == 'probe' else
               numerics.simulate(data, dt, {'finite': 3, 'observation': d.OBSERVATION, 'future': 24}[kind], interval))
        np.savez_compressed(folder/f'raw_{level}.npz', **raw); raws.append(raw)
        if kind in ('observation', 'future'):
            prefix_parity(load(finite_folder/f'raw_{level}.npz'), raw)
        if kind == 'future':
            observation_parity(load(observation_folder/f'raw_{level}.npz'), raw)
    result = audit(raws, data, kind)
    if kind in ('observation', 'future'):
        result['matched_prefix_verified'] = True
    if kind == 'future':
        result['matched_observation_verified'] = True
    save(folder/'audit.json', result)
    if kind == 'finite':
        np.savez_compressed(folder/'diagnostics.npz', **finite_diagnostics(raws[-1], data, 2))
    return raws, result


def task(args):
    started = time.perf_counter(); out = Path(args['out']); kind = args['kind']; spec = args['spec']
    verify(out, 'freeze.json')
    assert spec['mode'] == 'prediction' and kind in ('probe', 'finite', 'observation', 'future')
    if kind == 'probe':
        data = load(out/'inputs'/f'{spec["key"]}.npz')
    else:
        verify(out, 'derived_sha256.json')
        data = load(out/'derived'/spec['key']/f'{kind}.npz')
    if kind == 'future':
        verify(out, 'feature_sha256.json')
        if spec['split'] == 'test':
            require_test_seal(out)
    if kind == 'observation':
        verify(out, 'finite_sha256.json')
    _, result = simulate_folder(out/'raw'/args['name'], data, kind, out/'raw'/('finite_'+spec['key']),
                                out/'raw'/('observation_'+spec['key']))
    return dict(name=args['name'], kind=kind, qualified=result['qualified'],
        old_global_bound_all_passed=result['old_global_bound_all_passed'],
        paths=int(np.prod(data['entrants'].shape[:2])), elapsed_seconds=time.perf_counter()-started)


def benchmark_task(args):
    started = time.perf_counter(); out = Path(args['out']); verify(out, 'freeze.json')
    folder = out/'raw'/args['name']; folder.mkdir(parents=True, exist_ok=False)
    data = load(out/'inputs'/f'{args["spec"]["key"]}.npz')
    raws, p = simulate_folder(folder/'probe', data, 'probe')
    finite, future = d.derive(data, raws)
    observation = d.observation_inputs(future)
    np.savez_compressed(folder/'finite_inputs.npz', **finite)
    np.savez_compressed(folder/'future_inputs.npz', **future)
    np.savez_compressed(folder/'observation_inputs.npz', **observation)
    _, f = simulate_folder(folder/'finite', finite, 'finite')
    observed, o = simulate_folder(folder/'observation', observation, 'observation', folder/'finite')
    _, y = simulate_folder(folder/'future', future, 'future', folder/'finite', folder/'observation')
    table, rows = d.features(finite, observed[-1])
    np.savez_compressed(folder/'features.npz', **table); save(folder/'rows.json', rows)
    result = dict(qualified=all(a['qualified'] for a in (p, f, o, y)),
        old_global_bound_all_passed=all(a['old_global_bound_all_passed'] for a in (p, f, o, y)))
    save(folder/'audit.json', result)
    return dict(name=args['name'], kind='pipeline', **result, elapsed_seconds=time.perf_counter()-started)
