"""Fresh networks and a strictly six-replacement observation budget."""
import numpy as np
from h025.design import rng
from h029 import design as old
from h030.design import directions as all_directions
from h031.design import features as probe_features

SEED = 33033
DTS = old.DTS
CELLS = (0, 2, 15)
SOURCES = 128
CHUNK = 8
PROBES = 8
TAILS = 4
HORIZON = 24
OBSERVATION = 6
LOG_SCALE = .001
FRACTIONS = (.01, .1)
SELECTIONS = ('fixed_probe_0', 'maximum_of_eight')
DIRECTIONS = ('maximum', 'minimum')
BOOTSTRAPS = 10000
MODELS = ('labels6', 'margins6', 'raw6', 'persistence3', 'persistence6', 'same_observation')
CANDIDATE = 'persistence6'
COMPARATORS = ('labels6', 'margins6', 'raw6', 'same_observation')
ABLATION = 'persistence3'
RIDGES = (.001, .01, .1, 1.)
FIT_COUNT = 118
PREDICTION_MARGIN = .005
DIMENSIONS = dict(labels6=73, margins6=91, raw6=194, persistence3=99, persistence6=126, full6=265)


def codes(mode, split):
    if mode not in ('benchmark', 'prediction') or split not in ('train', 'test'):
        raise ValueError('Undeclared cohort')
    return int(mode == 'prediction'), int(split == 'test')


def branches():
    rows = [dict(branch=0, fraction=0., direction='baseline', sign=0)]
    for e, f in enumerate(FRACTIONS):
        for k, direction in enumerate(DIRECTIONS):
            for sign in (-1, 1):
                rows.append(dict(branch=1+4*e+2*k+int(sign == 1), fraction=f, direction=direction, sign=sign))
    return rows


def inputs(mode, split, ids, cell):
    m, s = codes(mode, split); ids = list(ids)
    assert cell in CELLS
    family, interval, law = old.CELLS[cell]; offset, width = old.LAWS[law]
    keys = np.array([[SEED, 0, m, s, i] for i in ids], np.uint32)
    initial, weights = [], []
    for key in keys:
        g = rng(key); initial.append(g.uniform(1.5, 3.5, 3))
        w = np.diag(g.uniform(1.55, 1.85)+g.uniform(-.025, .025, 3))
        for (a, b), jitter in zip(((0, 1), (0, 2), (1, 2)), g.uniform(-.05, .05, 3)):
            w[a, b] = w[b, a] = old.COUPLINGS[family]+jitter
        weights.append(w)
    probe_keys = np.array([[[SEED, 1, m, s, cell, i, j] for j in range(PROBES)] for i in ids], np.uint32)
    uniforms = np.array([[rng(key).random(3) for key in row] for row in probe_keys])
    tail_keys = np.array([[[[SEED, 2, m, s, cell, i, j, k] for k in range(TAILS)]
                          for j in range(PROBES)] for i in ids], np.uint32)
    tail_uniforms = np.array([[[rng(key).random(21) for key in probe] for probe in row] for row in tail_keys])
    return dict(initial=np.array(initial), weights=np.array(weights), source_id=np.array(ids), source_keys=keys,
        entrants=-offset-width*uniforms, probe_uniforms=uniforms, probe_keys=probe_keys,
        tail_keys=tail_keys, tail_uniforms=tail_uniforms, cell=np.array(cell), mode=np.array(m), split=np.array(s),
        interval=np.array(interval), stress=np.array(width), offset=np.array(offset))


def task_specs(n=SOURCES):
    return [dict(key=f'{split}_c{cell:02d}_{j:02d}', mode='prediction', split=split, cell=cell,
                 ids=list(range(start, min(start+CHUNK, n))))
            for split in ('train', 'test') for cell in CELLS for j, start in enumerate(range(0, n, CHUNK))]


def benchmark_specs():
    return [dict(key=f'benchmark_c{cell:02d}_{j:02d}', mode='benchmark', split='train', cell=cell,
                 ids=list(range(CHUNK if j == 3 else 0, 2*CHUNK if j == 3 else CHUNK)))
            for j, cell in enumerate((0, 2, 15, 2))]


def support(data):
    low, high = -float(data['offset'])-float(data['stress']), -float(data['offset'])
    return bool(((data['entrants'] > low) & (data['entrants'] <= high)).all())


def derive(data, raws):
    """Derive both selections from short probes only; every direction shares a radius."""
    assert len(raws) == 3
    for raw, dt in zip(raws, DTS):
        assert float(raw['dt']) == dt and float(raw['interval']) == float(data['interval'])
    n = len(data['initial']); indices = np.tile(np.arange(n), 2)
    b = raws[-1]['sensitivities'][:, :, -1, :, 3:]
    gains = np.linalg.svd(b, compute_uv=False)[..., 0]
    probes = np.r_[np.zeros(n, int), np.argmax(gains, axis=1)]
    selections = np.repeat([0, 1], n)
    vectors, singular = zip(*(all_directions(matrix) for matrix in b[indices, probes]))
    vectors, singular = np.array(vectors)[:, 4:6], np.array(singular)
    base = data['entrants'][indices, probes]
    width, offset = float(data['stress']), float(data['offset'])
    distance = np.minimum(base+offset+width, -offset-base)
    assert (distance >= 0).all()
    component = abs(vectors).max(axis=1)
    radius = np.divide(distance, component, out=np.full_like(distance, np.inf), where=component > 0).min(axis=1)
    sizes = np.minimum(width*np.array(FRACTIONS)[None], .9*radius[:, None])
    case = dict(initial=data['initial'][indices], weights=data['weights'][indices],
        source_id=data['source_id'][indices], selection=selections, probe_id=probes,
        source_keys=data['source_keys'][indices], probe_keys=data['probe_keys'][indices, probes],
        directions=vectors, singular_values=singular, base_entrants=base,
        support_radius=radius, actual_sizes=sizes, capped=sizes < width*np.array(FRACTIONS)[None])
    case.update({key: data[key] for key in ('interval', 'stress', 'offset', 'cell', 'mode', 'split')})
    for level, raw in enumerate(raws):
        for key in ('history', 'entries', 'independent_history', 'independent_entries', 'target'):
            case[f'archive_{key}_{level}'] = raw[key][indices, probes]
        case[f'jacobian_{level}'] = raw['sensitivities'][indices, probes, -1, :, 3:]
        case[f'state_jacobian_{level}'] = raw['sensitivities'][indices, probes, -1, :, :3]
    deltas = np.zeros((2*n, 9, 3))
    for row in branches()[1:]:
        e = FRACTIONS.index(row['fraction']); k = DIRECTIONS.index(row['direction'])
        deltas[:, row['branch']] = row['sign']*sizes[:, e, None]*vectors[:, k]
    finite = dict(case, entrants=base[:, None]+deltas, deltas=deltas)
    tail_uniforms = data['tail_uniforms'][indices, probes]
    tails = -offset-width*tail_uniforms
    prefixes = np.repeat(finite['entrants'][:, :, None], TAILS, axis=2)
    joined = np.concatenate((prefixes, np.repeat(tails[:, None], 9, axis=1)), axis=-1)
    future = dict(case, entrants=joined.reshape(2*n, 9*TAILS, HORIZON),
        tail_keys=data['tail_keys'][indices, probes], tail_uniforms=tail_uniforms)
    assert support(finite) and support(future)
    return finite, future


def observation_inputs(future):
    """Strip unseen entrants and RNG keys before running the observation stage."""
    fields = ('initial', 'weights', 'source_id', 'selection', 'probe_id',
              'interval', 'stress', 'offset', 'cell', 'mode', 'split')
    fields += tuple(f'archive_{key}_{level}' for level in range(3)
                    for key in ('history', 'entries', 'independent_history', 'independent_entries', 'target'))
    result = {key: future[key].copy() for key in fields}
    result['entrants'] = future['entrants'][..., :OBSERVATION].copy()
    assert result['entrants'].shape[1:] == (9*TAILS, OBSERVATION)
    return result


def summaries(context, baseline, intervention, predicted, dose, horizon):
    """Same feature recipe at endpoints 3 and 6; no fitted cutoffs."""
    a, b = baseline[1:horizon+1], intervention[1:horizon+1]
    aa, ab = np.tanh(2*a), np.tanh(2*b)
    labels = np.r_[context, (aa > .5).all(axis=-1), (ab > .5).all(axis=-1),
                   ((aa > .5) != (ab > .5)).sum(axis=-1)]
    margins = np.r_[labels, aa.min(axis=-1)-.5, ab.min(axis=-1)-.5, aa[-1], ab[-1]]
    state = np.linalg.norm(b-a, axis=-1)
    activation = abs(ab-aa).max(axis=-1)
    log_state, log_activation = np.log1p(state/LOG_SCALE), np.log1p(activation/LOG_SCALE)
    actual = b[2]-a[2]
    linear_norm, actual_norm = np.linalg.norm(predicted), np.linalg.norm(actual)
    extra = np.r_[state, activation, log_state, log_activation,
        linear_norm, actual_norm, np.linalg.norm(actual-predicted)/max(LOG_SCALE, actual_norm, linear_norm),
        actual_norm/dose if dose > 0 else 0., log_state[-1]-log_state[2],
        log_activation[-1]-log_activation[2], state.max(), activation.max(), b[-1]-a[-1]]
    return labels, margins, np.r_[margins, extra]


def features(data, observation):
    """Only finite-input metadata and audited states/entries through endpoint 6.

    Refuse full future histories rather than silently slicing them. One row is
    one intervention and one observed tail. Network IDs remain the CV groups.
    """
    n = len(data['initial'])
    history, entries = observation['history'], observation['entries']
    assert history.shape == (n, 9*TAILS, OBSERVATION+1, 3)
    assert entries.shape == (n, 9*TAILS, OBSERVATION, 3)
    assert float(observation['dt']) == DTS[-1]
    assert float(observation['interval']) == float(data['interval'])
    assert np.isfinite(history).all() and np.isfinite(entries).all()
    history = history.reshape(n, 9, TAILS, OBSERVATION+1, 3)
    entries = entries.reshape(n, 9, TAILS, OBSERVATION, 3)
    previous, metadata = probe_features(data)
    result = {key: [] for key in DIMENSIONS}; rows = []
    for r, row in enumerate(metadata):
        case, branch = r//8, row['branch']
        delta = data['deltas'][case, branch]
        predicted = data['jacobian_2'][case]@delta
        dose = data['actual_sizes'][case, (branch-1)//4]
        for tail in range(TAILS):
            baseline, intervention = history[case, 0, tail], history[case, branch, tail]
            labels, margins, persistence = summaries(previous['context'][r], baseline, intervention, predicted, dose, 6)
            _, _, early = summaries(previous['context'][r], baseline, intervention, predicted, dose, 3)
            # These are observed entrant values, extracted from the saved overwrite
            # states. No tail seeds or post-observation entrant tapes are inputs.
            seen_entrants = entries[case, 0, tail, np.arange(3, 6), [1, 2, 0]]
            raw = np.r_[previous['raw'][r], baseline[1:].ravel(), intervention[1:].ravel(),
                entries[case, 0, tail].ravel(), entries[case, branch, tail].ravel(), seen_entrants]
            values = dict(labels6=labels, margins6=margins, raw6=raw, persistence3=early,
                          persistence6=persistence, full6=np.r_[raw, persistence[55:]])
            for key, value in values.items():
                assert value.shape == (DIMENSIONS[key],) and np.isfinite(value).all()
                result[key].append(value)
            rows.append(dict(row, tail=tail))
    return {key: np.array(value) for key, value in result.items()}, rows

