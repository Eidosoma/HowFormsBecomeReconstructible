"""Restart the unchanged audited integrator at endpoint 6 (same cycle phase)."""
from pathlib import Path
import time
import numpy as np
from h007.io import save, verify
from h019.audit import load, refinement
from h022 import numerics
from h034 import design as d


def engine_inputs(data, level):
    entrants = data['entrants']
    if bool(data['benchmark']):
        # Extra disposable replay checks restart against an old full-origin run.
        entrants = np.concatenate((entrants, data['archive_entrants'][:, None]), axis=1)
    return dict(initial=data[f'initial_{level}'], weights=data['weights'], entrants=entrants)


def window_target(history):
    assert history.shape[-2:] == (19, 3)
    # Local endpoint 0 is absolute endpoint 6; absolute 13 is local 7.
    return (np.tanh(2*history[..., 7:19, :]) > .5).all(axis=(-2, -1))


def global_identities():
    ids = np.array([9, 7, 8]); result = [ids.copy()]
    for j in range(d.START, d.END):
        ids[(1, 2, 0)[j % 3]] = 4+j
        result.append(ids.copy())
    return np.array(result)


def simulate(data, level, dt=None):
    assert d.START % 3 == 0
    inputs = engine_inputs(data, level)
    raw = numerics.simulate(inputs, d.DTS[level] if dt is None else dt,
                           d.END-d.START, float(data['interval']))
    raw.update(window_target=window_target(raw['history']),
        global_endpoints=np.arange(d.START, d.END+1), global_identities=global_identities())
    return raw


def audit_one(raw, data, level, dt=None):
    result = numerics.audit(raw, engine_inputs(data, level))
    expected_dt = d.DTS[level] if dt is None else dt
    clocks = (float(raw['dt']) == expected_dt and float(raw['interval']) == float(data['interval'])
              and raw['history'].shape[-2:] == (19, 3)
              and np.array_equal(raw['global_endpoints'], np.arange(6, 25))
              and np.array_equal(raw['global_identities'], global_identities()))
    observer = (np.array_equal(raw['window_target'], window_target(raw['history'])) and
                np.array_equal(raw['window_target'], window_target(raw['independent_history'])))
    initial = np.broadcast_to(data[f'initial_{level}'][:, None], raw['history'][..., 0, :].shape)
    restored = np.array_equal(raw['history'][..., 0, :], initial)
    replay = True
    if bool(data['benchmark']):
        replay = all(np.array_equal(raw[key][:, -1], data[f'archive_{key}_{level}'])
                     for key in ('history', 'entries'))
    result.update(clocks=bool(clocks), window_observer=bool(observer), saved_endpoint_exact=bool(restored),
        archived_full_origin_replay_exact=bool(replay) if bool(data['benchmark']) else None)
    result['qualified'] = bool(result['qualified'] and clocks and observer and restored and replay)
    return result


def outcomes(history):
    assert history.shape[0] % 2 == 0 and history.shape[-2:] == (19, 3)
    states = history.reshape(-1, 2, history.shape[1], 19, 3)
    activation = np.tanh(2*states)
    labels = activation > .5
    endpoint = labels.all(axis=-1)
    target = endpoint[..., 7:19].all(axis=-1)
    baseline, intervention = target[:, 0], target[:, 1]
    flip = baseline != intervention
    components = (labels[:, 0, :, 7:] != labels[:, 1, :, 7:]).any(axis=(-2, -1))
    endpoints = (endpoint[:, 0, :, 7:] != endpoint[:, 1, :, 7:]).any(axis=-1)
    category = np.where(flip, 3, np.where(endpoints, 2, np.where(components, 1, 0)))
    first = endpoint[:, 0, :, 1:] != endpoint[:, 1, :, 1:]
    return dict(flip=flip, gain=~baseline & intervention, loss=baseline & ~intervention,
        baseline_success=baseline, intervention_success=intervention, category=category,
        both_fail=~baseline & ~intervention,
        first_endpoint_disagreement=np.where(first.any(axis=-1), 7+first.argmax(axis=-1), 0),
        window_activation_displacement=abs(activation[:, 0, :, 7:]-activation[:, 1, :, 7:]).max(axis=(-2, -1)),
        final_state_distance=np.linalg.norm(states[:, 0, :, -1]-states[:, 1, :, -1], axis=-1))


def task(args):
    started = time.perf_counter(); out = Path(args['out']); name = args['name']
    verify(out, 'freeze.json')
    data = load(out/'inputs'/f'{args["input_name"]}.npz'); d.validate(data)
    folder = out/'raw'/name; folder.mkdir(parents=True, exist_ok=False)
    raws, audits, derived = [], [], []
    for level in range(3):
        raw = simulate(data, level)
        np.savez_compressed(folder/f'raw_{level}.npz', **raw)
        audits.append(audit_one(raw, data, level)); raws.append(raw)
        measured = outcomes(raw['history'][:, :d.TAILS])
        independent = outcomes(raw['independent_history'][:, :d.TAILS])
        categorical = all(np.array_equal(measured[key], independent[key]) for key in measured
                          if key not in ('window_activation_displacement', 'final_state_distance'))
        audits[-1]['diagnostic_categories_replay'] = categorical
        audits[-1]['qualified'] &= categorical
        derived.append(measured)
    refined = refinement(raws)
    categorical = all(np.array_equal(a[key], b[key]) for a, b in zip(derived[:-1], derived[1:])
        for key in a if key not in ('window_activation_displacement', 'final_state_distance'))
    observer = all(np.array_equal(a['window_target'], b['window_target']) for a, b in zip(raws[:-1], raws[1:]))
    result = dict(qualified=bool(refined['qualified'] and categorical and observer and all(a['qualified'] for a in audits)),
        audits=audits, refinement=refined, diagnostic_categories_refine=categorical, window_target_refines=observer,
        old_global_bound_all_passed=all(a['old_global_2e11_passed'] for a in audits))
    save(folder/'audit.json', result)
    np.savez_compressed(folder/'outcomes.npz', **derived[-1])
    return dict(name=name, qualified=result['qualified'], pairs=len(data['row_index']),
        paths=2*len(data['row_index'])*d.TAILS,
        archived_replay_paths=2*len(data['row_index']) if bool(data['benchmark']) else 0,
        elapsed_seconds=time.perf_counter()-started)
