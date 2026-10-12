"""D176 fixed normal-geometry x own-reading interactions, saved data only."""
import numpy as np
from . import settings_prediction as prior

ALPHAS = (.001, .01, .1)
OBSERVERS = ('starting', 'one_copy', 'tied:passive', 'tied:pulse')
VERSIONS = ('old', 'settings', 'interaction')
KEYS = tuple(v+'/'+k for v in VERSIONS for k in OBSERVERS if (v, k) != ('interaction', 'starting'))
NEW = ('settings/tied:pulse', 'interaction/one_copy', 'interaction/tied:passive', 'interaction/tied:pulse')
REFERENCES = tuple(k for k in KEYS if k not in NEW)
CHEAP = ('old/starting', 'old/one_copy', 'settings/starting', 'settings/one_copy', 'interaction/one_copy')
TWO = tuple(v+'/'+k for v in VERSIONS for k in OBSERVERS[2:])
MEASUREMENTS = ('start', 'u0', 'u1', 'pulse', 'q')
CLASS = 'normal_geometry_times_own_reading_shared_slot_rule_v1'


def observer_features(key, inputs):
    if key not in KEYS: raise ValueError('fixed version/observer')
    version, name = key.split('/', 1)
    required = {'start'} | ({'q'} if version != 'old' else set())
    if name != 'starting': required.add('u0')
    if name.startswith('tied:'): required.add('second')
    if set(inputs) != required: raise ValueError('only own readings/settings; labels/IDs/third copy forbidden')
    start = np.asarray(inputs['start'])
    if start.ndim != 4: raise ValueError('complete life/group shape')
    n = len(start); parts = [prior.finite(start, (n, 4, 4, 7))]
    for field in ('u0', 'second'):
        if field in inputs: parts.append(prior.finite(inputs[field], (n, 4, 4, 6)))
    if version != 'old':
        q = prior.finite(inputs['q'], (n, 4, 4, 2))
        if np.any(abs(q) > 1) or np.any(q[:, :, (1, 3)] != 1): raise ValueError('normal effective settings')
        parts.append(q)
        if version == 'interaction':
            parts.append((q[..., 0:1]-1)*inputs['u0'])
            if 'second' in inputs: parts.append((q[..., 1:2]-1)*inputs['second'])
    return np.concatenate(parts, -1)


def panels(measured):
    if set(measured) != set(MEASUREMENTS): raise ValueError('feature-only assembly')
    out = {}
    for key in KEYS:
        version, name = key.split('/', 1)
        own = dict(start=measured['start'])
        if version != 'old': own['q'] = measured['q']
        if name != 'starting': own['u0'] = measured['u0']
        if name.startswith('tied:'): own['second'] = measured['pulse' if name.endswith('pulse') else 'u1']
        out[key] = observer_features(key, own)
    return out


def validate(data, development=False):
    if set(data) != set(MEASUREMENTS) | {'futures', 'block_ids'}: raise ValueError('fixed data schema; original target forbidden')
    n = len(data['start']); ids = prior.finite(data['block_ids'], (n,), np.int64)
    if n < 4 or len(set(ids.tolist())) != n: raise ValueError('whole unique founders')
    if development and ids.tolist() != list(range(90000, 90016)): raise ValueError('only sixteen development founders')
    y = prior.finite(data['futures'], (n, 4, 4, 4))
    if np.any(abs(y) > 1): raise ValueError('bounded four-future target')
    panels({k: data[k] for k in MEASUREMENTS})
    return n


def embedding(scale, tied):
    s = np.asarray(scale); d = len(s)
    if not np.isfinite(s).all() or np.any(s <= 0): raise ValueError('positive training scales')
    if not tied:
        if d not in (7, 9, 13, 15, 21): raise ValueError('cheap dimensions')
        return np.eye(d)
    if d in (19, 21): return prior.embedding(s, True)
    if d != 33: raise ValueError('two-copy interaction dimension')
    t = np.zeros((33, 21)); t[:21, :15] = prior.embedding(s[:21], True)
    h = np.hypot(s[21:27], s[27:33])
    for j in range(6):
        t[21+j, 15+j], t[27+j, 15+j] = s[21+j]/h[j], s[27+j]/h[j]
    return t


def fit(x, y, g, alpha, key):
    if key not in KEYS or alpha not in ALPHAS: raise ValueError('fixed key and alpha')
    version, name = key.split('/', 1); tied = name.startswith('tied:')
    expected = (7 if name == 'starting' else 13 if name == 'one_copy' else 19)
    expected += 0 if version == 'old' else 2 if version == 'settings' else 8 if name == 'one_copy' else 14
    if x.shape[1] != expected: raise ValueError('fixed feature count')
    mu, offset, scale, z, target = prior.prepare(x, y, g)
    t = embedding(scale, tied); a = prior.design(z @ t, g)
    eta = np.linalg.solve(a.T@a/len(y)+alpha*np.eye(a.shape[1]), a.T@target/len(y)).reshape(4, t.shape[1])
    klass = CLASS if version == 'interaction' else (prior.OLD_CLASSES if version == 'old' else prior.NEW_CLASSES)[int(tied)]
    return dict(alpha=alpha, means=mu.tolist(), offsets=offset.tolist(), scale=scale.tolist(),
        coefficients=(eta @ t.T).tolist(), reduced_coefficients=eta.tolist(), model_class=klass)


def fit_key(data, key):
    n = validate(data); ids = data['block_ids']; g = np.tile(np.arange(4, dtype=np.int64), n*4)
    owners = np.repeat(np.arange(n), 16); y = data['futures'].mean(-1).ravel()
    x = panels({k: data[k] for k in MEASUREMENTS})[key].reshape(n*16, -1)
    raw = np.empty((3, n, 4, 4)); folds = []
    for block in range(n):
        train, test = owners != block, owners == block
        models = [fit(x[train], y[train], g[train], alpha, key) for alpha in ALPHAS]
        raw[:, block] = np.stack([prior.raw_predict(record, x[test], g[test]).reshape(4, 4) for record in models])
        folds.append(dict(validation_block=int(ids[block]), training_blocks=ids[np.arange(n) != block].tolist(), models=models))
    return np.clip(raw, -1, 1), raw, dict(observer=key.split('/', 1)[1], blocks=ids.tolist(),
        alphas=list(ALPHAS), target='future_mean', folds=folds)


def fit_new(data, predictions, raw, references):
    for box in (predictions, raw, references):
        if set(box) != set(REFERENCES): raise ValueError('exact reused reference set')
    p, r, fits = dict(predictions), dict(raw), dict(references)
    for key in NEW: p[key], r[key], fits[key] = fit_key(data, key)
    return p, r, fits


def synthetic_references(data):
    n = validate(data)
    if data['block_ids'].tolist() != list(range(n)): raise ValueError('synthetic-only reference fitting')
    p, r, fits = {}, {}, {}
    for key in REFERENCES: p[key], r[key], fits[key] = fit_key(data, key)
    return p, r, fits


def pairs():
    rows = [('settings/'+k, 'old/'+k) for k in OBSERVERS]
    rows += [('interaction/'+k, v+'/'+k) for v in ('settings', 'old') for k in OBSERVERS[1:]]
    rows += [(v+'/tied:pulse', v+'/tied:passive') for v in VERSIONS]
    rows += [(k, c) for k in TWO for c in CHEAP]
    rows += [(v+'/one_copy', ('settings' if v == 'interaction' else v)+'/starting') for v in VERSIONS]
    assert len(rows) == len(set(rows)) == 46
    return rows


def report(data, predictions, raw):
    n = validate(data); f = data['futures']; absolute, losses = {}, {}
    if set(predictions) != set(KEYS) or set(raw) != set(KEYS): raise ValueError('complete eleven-observer panel')
    for key in KEYS:
        p, r = predictions[key], raw[key]
        prior.finite(p, (3, n, 4, 4)); prior.finite(r, p.shape)
        np.testing.assert_array_equal(p, np.clip(r, -1, 1))
        absolute[key] = [prior.metrics(p[i], r[i], f) for i in range(3)]
        for row in absolute[key]: row['future_dispersion'] = row.pop('irreducible_future_variance')
        losses[key] = ((p[..., None]-f)**2).mean(-1)
    comparisons = []
    for c, r in pairs():
        for i, alpha in enumerate(ALPHAS):
            gain = losses[r][i]-losses[c][i]
            mean_gain = (predictions[r][i]-f.mean(-1))**2-(predictions[c][i]-f.mean(-1))**2
            np.testing.assert_allclose(gain, mean_gain, atol=1e-14, rtol=0)
            comparisons.append(dict(candidate=c, reference=r, alpha=alpha, **prior.gain_detail(gain)))
    changes = []
    for before, after in (('old', 'settings'), ('settings', 'interaction'), ('old', 'interaction')):
        for i, alpha in enumerate(ALPHAS):
            change = (losses[after+'/tied:passive'][i]-losses[after+'/tied:pulse'][i]
                      -losses[before+'/tied:passive'][i]+losses[before+'/tied:pulse'][i])
            changes.append(dict(before=before, after=after, alpha=alpha, **prior.gain_detail(change)))
    selected = {}
    for key in CHEAP:
        errors = [r['mse'] for r in absolute[key]]
        i = max(i for i in range(3) if errors[i] <= min(errors)+1e-12)
        selected[key] = dict(index=i, alpha=ALPHAS[i], metrics=absolute[key][i], selection_affected=True)
    contexts = [dict(candidate=c, candidate_alpha=.01, reference=r, reference_alpha=selected[r]['alpha'],
        selection_affected=True, **prior.gain_detail(losses[r][selected[r]['index']]-losses[c][1])) for c in TWO for r in CHEAP]
    return dict(schema='d176_contextual_prediction_v1', blocks=data['block_ids'].tolist(), cases=n*16,
        new_fits=n*12, reused_models=n*21, new_predictions=n*192, actual_reference_refits=0,
        absolute=absolute, comparisons=comparisons, gap_changes=changes,
        selected_cheap=selected, selected_contexts=contexts,
        focal=['interaction/tied:pulse', 'interaction/tied:passive', .01],
        prospective_evidence=False, confidence_intervals=False, equivalence=False,
        deployment_selected=False, new_dynamics=0, automatic_successor=False), losses


def fixture(n=16):
    rng = np.random.default_rng(17620261008)
    start = rng.normal(size=(n, 4, 4, 7)); u0 = rng.normal(size=(n, 4, 4, 6))
    u1 = rng.normal(size=u0.shape)*np.arange(1, 7); pulse = .8*u1+.2*rng.normal(size=u1.shape)
    shifts = rng.integers(0, 16, (n, 4, 4, 2, 2), dtype=np.int64); q = prior.effective_q(shifts)
    mean = np.tanh(.15*start[..., 0]+.08*u0[..., 0]+.08*u1[..., 0]+.03*(q[..., 1]-1)*u1[..., 0])
    futures = np.clip(mean[..., None]+rng.normal(0, .15, (n, 4, 4, 4)), -1, 1)
    return dict(start=start, u0=u0, u1=u1, pulse=pulse, q=q, futures=futures,
        block_ids=np.arange(n, dtype=np.int64))
