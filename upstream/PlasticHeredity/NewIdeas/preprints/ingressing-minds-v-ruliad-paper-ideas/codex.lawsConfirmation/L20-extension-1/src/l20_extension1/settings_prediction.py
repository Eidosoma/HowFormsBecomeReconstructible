"""D171: fixed saved-data settings extension; no simulation or source access."""
import numpy as np

ALPHAS = (.001, .01, .1)
EDITED = ('passive', 'shuffle', 'attenuate', 'sham_plus', 'sham_minus')
OBSERVERS = ('starting', 'one_copy') + tuple('tied:' + k for k in EDITED)
VERSIONS = ('old', 'settings')
Q = np.array([[-.5, -.5, .5], [-.5, .5, -.5], [.5, -.5, -.5], [.5, .5, .5]])
OLD_CLASSES = ('common_plus_zero_sum_group_deviations_penalty_ratio_1',
               'raw_reading_difference_zero_original_ridge_penalty')
NEW_CLASSES = ('settings_known_group_ridge_v1', 'settings_known_raw_reading_tied_ridge_v1')
MEASUREMENTS = ('start', 'endpoint', 'targeted', 'shifts')
DATA_KEYS = set(MEASUREMENTS) | {'futures', 'block_ids'}


def finite(value, shape, dtype=np.float64):
    a = np.asarray(value)
    if a.shape != shape or a.dtype != dtype or not np.isfinite(a).all():
        raise ValueError('finite exact array schema: ' + str(shape))
    return a


def effective_q(shifts):
    s = np.asarray(shifts)
    if s.ndim != 5 or s.shape[1:] != (4, 4, 2, 2) or s.dtype != np.int64:
        raise ValueError('four lives, ordered A-ordinary/A-aligned/B-ordinary/B-aligned, two shifts')
    if np.any(s < 0) or np.any(s >= 16):
        raise ValueError('legal diagnostic shifts 0..15')
    result = np.ones(s.shape[:-1], dtype=np.float64)
    dy = s[:, :, 0, :, 0]
    dx = s[:, :, 2, :, 1] % 8
    result[:, :, 0] = 1 - np.minimum(dy, 16 - dy) / 4
    result[:, :, 2] = 1 - np.minimum(dx, 8 - dx) / 2
    return result


def observer_features(name, inputs, settings=True):
    """Per-observer inference boundary: never accepts labels, IDs or a third reading."""
    if name not in OBSERVERS:
        raise ValueError('fixed observer')
    keys = {'start'} | ({'q'} if settings else set())
    if name != 'starting':
        keys.add('u0')
    if name.startswith('tied:'):
        keys.add('second')
    if set(inputs) != keys:
        raise ValueError('only this observer\'s permitted inputs')
    a = np.asarray(inputs['start'])
    if a.ndim != 4:
        raise ValueError('complete life/group array')
    n = len(a)
    parts = [finite(a, (n, 4, 4, 7))]
    for key in ('u0', 'second'):
        if key in keys:
            parts.append(finite(inputs[key], (n, 4, 4, 6)))
    if settings:
        q = finite(inputs['q'], (n, 4, 4, 2))
        if np.any(abs(q) > 1) or np.any(q[:, :, (1, 3), :] != 1):
            raise ValueError('effective settings including aligned q=1')
        parts.append(q)
    return np.concatenate(parts, axis=-1)


def panels(measurements, settings=True):
    if set(measurements) != set(MEASUREMENTS):
        raise ValueError('feature assembly excludes outcomes, IDs and extra responses')
    a = np.asarray(measurements['start']); n = len(a)
    finite(a, (n, 4, 4, 7))
    e = finite(measurements['endpoint'], (n, 4, 4, 3, 6))
    t = finite(measurements['targeted'], e.shape)
    q = effective_q(measurements['shifts'])
    finite(q, (n, 4, 4, 2))
    base = {'start': a, **({'q': q} if settings else {})}
    result = {'starting': observer_features('starting', base, settings),
              'one_copy': observer_features('one_copy', dict(base, u0=e[..., 0, :]), settings)}
    for name, second in zip(OBSERVERS[2:], (e[..., 1, :], e[..., 2, :],
                                            t[..., 0, :], t[..., 1, :], t[..., 2, :])):
        result[name] = observer_features(name, dict(base, u0=e[..., 0, :], second=second), settings)
    return result


def validate(data, development=False):
    if set(data) != DATA_KEYS:
        raise ValueError('exact development dataset; original one-future label forbidden')
    ids = np.asarray(data['block_ids']); n = len(ids)
    if n < 4 or ids.shape != (n,) or ids.dtype != np.int64 or len(set(ids.tolist())) != n:
        raise ValueError('unique whole-founder IDs')
    if development and not np.array_equal(ids, np.arange(90000, 90016, dtype=np.int64)):
        raise ValueError('only ordered sixteen development founders; pilot forbidden')
    f = finite(data['futures'], (n, 4, 4, 4))
    if np.any(abs(f) > 1):
        raise ValueError('bounded four-future labels')
    panels({k: data[k] for k in MEASUREMENTS})
    return n


def prepare(x, y, g):
    if x.ndim != 2 or y.shape != (len(x),) or g.shape != y.shape or g.dtype != np.int64:
        raise ValueError('paired training rows')
    if set(g.tolist()) != set(range(4)) or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(abs(y) > 1):
        raise ValueError('complete groups and finite bounded labels')
    mu = np.stack([x[g == j].mean(0) for j in range(4)])
    offset = np.array([y[g == j].mean() for j in range(4)])
    centered = x - mu[g]
    scale = np.sqrt(np.mean(centered * centered, axis=0)); scale[scale <= 1e-12] = 1
    return mu, offset, scale, centered / scale, y - offset[g]


def embedding(scale, tied):
    s = np.asarray(scale)
    if s.ndim != 1 or not np.isfinite(s).all() or np.any(s <= 0):
        raise ValueError('positive scales')
    d = len(s)
    if not tied:
        if d not in (7, 9, 13, 15):
            raise ValueError('cheap baseline dimension')
        return np.eye(d)
    if d not in (19, 21):
        raise ValueError('two-copy dimension')
    t = np.zeros((d, d - 6)); t[:7, :7] = np.eye(7)
    h = np.hypot(s[7:13], s[13:19])
    for j in range(6):
        t[7 + j, 7 + j] = s[7 + j] / h[j]
        t[13 + j, 7 + j] = s[13 + j] / h[j]
    if d == 21:
        t[19:, 13:] = np.eye(2)
    return t


def design(z, g):
    return np.concatenate([z] + [z * Q[g, j, None] for j in range(3)], axis=1)


def fit(x, y, g, alpha, tied, settings=True):
    if alpha not in ALPHAS or x.shape[1] not in ((9, 15, 21) if settings else (7, 13, 19)):
        raise ValueError('fixed alpha and feature dimensions')
    mu, offset, scale, z, target = prepare(x, y, g)
    t = embedding(scale, tied); a = design(z @ t, g)
    eta = np.linalg.solve(a.T @ a / len(y) + alpha * np.eye(a.shape[1]),
                          a.T @ target / len(y)).reshape(4, t.shape[1])
    return dict(alpha=alpha, means=mu.tolist(), offsets=offset.tolist(), scale=scale.tolist(),
                coefficients=(eta @ t.T).tolist(), reduced_coefficients=eta.tolist(),
                model_class=(NEW_CLASSES if settings else OLD_CLASSES)[int(tied)])


def raw_predict(model, x, g):
    mu, offset, scale, beta = (np.asarray(model[k]) for k in ('means', 'offsets', 'scale', 'coefficients'))
    d = x.shape[1]
    if mu.shape != (4, d) or beta.shape != (4, d) or offset.shape != (4,) or scale.shape != (d,):
        raise ValueError('model dimensions')
    if not all(np.isfinite(v).all() for v in (mu, offset, scale, beta, x)) or np.any(scale <= 0):
        raise ValueError('finite model')
    return offset[g] + design((x - mu[g]) / scale, g) @ beta.ravel()


def fit_all(data, settings=True):
    n = validate(data); ids = data['block_ids']; y = data['futures'].mean(-1).ravel()
    features = panels({k: data[k] for k in MEASUREMENTS}, settings)
    g = np.tile(np.arange(4, dtype=np.int64), n * 4); rows = np.repeat(np.arange(n), 16)
    predictions, raw, fits = {}, {}, {}
    for name in OBSERVERS:
        x = features[name].reshape(n * 16, -1); forecasts = np.empty((3, n, 4, 4)); folds = []
        for outer in range(n):
            train = rows != outer; test = ~train
            models = [fit(x[train], y[train], g[train], a, name.startswith('tied:'), settings) for a in ALPHAS]
            forecasts[:, outer] = np.stack([raw_predict(m, x[test], g[test]).reshape(4, 4) for m in models])
            folds.append(dict(validation_block=int(ids[outer]), training_blocks=ids[np.arange(n) != outer].tolist(), models=models))
        raw[name] = forecasts; predictions[name] = np.clip(forecasts, -1, 1)
        fits[name] = dict(observer=name, blocks=ids.tolist(), alphas=list(ALPHAS), target='future_mean', folds=folds)
    return predictions, raw, fits


def metrics(p, raw, futures):
    err = p[..., None] - futures; loss = err * err
    mean_loss = (p - futures.mean(-1)) ** 2
    return dict(mse=float(loss.mean()), mae_points=float(100 * abs(err).mean()),
                rmse_points=float(100 * np.sqrt(loss.mean())), bias_points=float(100 * err.mean()),
                clipped=int(np.count_nonzero(raw != p)), cases=int(p.size),
                block_mse=loss.mean((1, 2, 3)).tolist(), group_mse=loss.mean((0, 1, 3)).tolist(),
                block_mae_points=(100 * abs(err).mean((1, 2, 3))).tolist(),
                group_mae_points=(100 * abs(err).mean((0, 1, 3))).tolist(),
                block_bias_points=(100 * err.mean((1, 2, 3))).tolist(),
                group_bias_points=(100 * err.mean((0, 1, 3))).tolist(),
                group_clipped=np.count_nonzero(raw != p, axis=(0, 1)).tolist(),
                future_mse=loss.mean((0, 1, 2)).tolist(), mean_target_mse=float(mean_loss.mean()),
                block_mean_target_mse=mean_loss.mean((1, 2)).tolist(),
                irreducible_future_variance=float(np.var(futures, axis=-1).mean()))


def gain_detail(gain):
    blocks = gain.mean((1, 2)); n = len(blocks)
    return dict(mse_reduction=float(gain.mean()), block_gains=blocks.tolist(),
                group_gains=gain.mean((0, 1)).tolist(), positive_blocks=int(np.sum(blocks > 0)),
                negative_blocks=int(np.sum(blocks < 0)), zero_blocks=int(np.sum(blocks == 0)),
                score_only_omit_gains=((blocks.sum() - blocks) / (n - 1)).tolist())


def pairs():
    result = [(('settings', k), ('old', k)) for k in OBSERVERS]
    result += [((v, k), (v, 'tied:passive')) for v in VERSIONS for k in OBSERVERS[3:]]
    result += [((v, k), (w, cheap)) for v in VERSIONS for k in ('tied:passive', 'tied:sham_minus')
               for w in VERSIONS for cheap in OBSERVERS[:2]]
    return result


def report(new, new_raw, old, old_raw, data):
    validate(data); f = data['futures']; values = {'old': old, 'settings': new}
    raws = {'old': old_raw, 'settings': new_raw}
    absolute, losses, mean_losses = {}, {}, {}
    for v in VERSIONS:
        for name in OBSERVERS:
            key = v + '/' + name; p = values[v][name]
            finite(p, (3,) + f.shape[:3]); finite(raws[v][name], p.shape)
            if not np.array_equal(p, np.clip(raws[v][name], -1, 1)):
                raise ValueError('clipped/raw prediction mismatch')
            absolute[key] = [metrics(p[i], raws[v][name][i], f) for i in range(3)]
            losses[key] = ((p[..., None] - f[None]) ** 2).mean(-1)
            mean_losses[key] = (p - f.mean(-1)) ** 2
    comparisons = []
    for candidate, reference in pairs():
        c, r = '/'.join(candidate), '/'.join(reference)
        for i, alpha in enumerate(ALPHAS):
            gain = losses[r][i] - losses[c][i]
            np.testing.assert_allclose(gain, mean_losses[r][i] - mean_losses[c][i], atol=1e-14, rtol=0)
            comparisons.append(dict(candidate=c, reference=r, alpha=alpha, **gain_detail(gain)))
    changes = []
    for name in OBSERVERS[3:]:
        for i, alpha in enumerate(ALPHAS):
            new_gain = losses['settings/tied:passive'][i] - losses['settings/' + name][i]
            old_gain = losses['old/tied:passive'][i] - losses['old/' + name][i]
            changes.append(dict(challenge=name, alpha=alpha, **gain_detail(new_gain - old_gain)))
    cheap_choices = {}
    for v in VERSIONS:
        for name in OBSERVERS[:2]:
            k = v + '/' + name; errors = np.array([a['mse'] for a in absolute[k]])
            index = max(i for i in range(3) if errors[i] <= errors.min() + 1e-12)
            cheap_choices[k] = dict(index=index, alpha=ALPHAS[index], metrics=absolute[k][index], selection_affected=True)
    selected_context = []
    for v in VERSIONS:
        for name in ('tied:passive', 'tied:sham_minus'):
            k = v + '/' + name
            for r, choice in cheap_choices.items():
                selected_context.append(dict(candidate=k, candidate_alpha=.01, reference=r,
                    reference_alpha=choice['alpha'], selection_affected=True,
                    **gain_detail(losses[r][choice['index']] - losses[k][1])))
    summary = dict(schema='d171_settings_prediction_development_v1', blocks=data['block_ids'].tolist(),
        cases=int(f[..., 0].size), new_fits=21 * len(f), new_predictions=336 * len(f),
        absolute=absolute, comparisons=comparisons, gap_changes=changes,
        cheap_selection_context=cheap_choices, selected_cheap_comparisons=selected_context,
        focal=dict(candidate='tied:sham_minus', reference='tied:passive', alpha=.01),
        prospective_evidence=False, new_dynamics=0, new_founders=0, new_lineages=0,
        actual_reference_refits=0, confidence_intervals=False, deployment_selection=False,
        automatic_successor=False, all_cases_retained=True, settings_equal_for_all_observers=True)
    return summary, losses


def fixture(n=16):
    """Synthetic-only, disjoint IDs. Never a fallback for missing real input."""
    rng = np.random.default_rng(17120260923)
    a = rng.normal(size=(n, 4, 4, 7)); e = rng.normal(size=(n, 4, 4, 3, 6))
    e[..., 0, :] *= np.arange(1, 7); e[..., 1, :] *= np.arange(6, 0, -1) / 4
    t = .7 * e + rng.normal(scale=.4, size=e.shape)
    shifts = rng.integers(0, 16, size=(n, 4, 4, 2, 2), dtype=np.int64)
    q = effective_q(shifts)
    y = np.tanh(.3 * a[..., 0] + .12 * e[..., 0, 0] + .13 * q[..., 1])
    f = np.clip(y[..., None] + rng.normal(scale=.15, size=(n, 4, 4, 4)), -1, 1)
    return dict(start=a, endpoint=e, targeted=t, shifts=shifts, futures=f,
                block_ids=np.arange(-n, 0, dtype=np.int64))
