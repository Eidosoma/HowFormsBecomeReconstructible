"""D173 fixed two-copy decoder/report core; qualification uses synthetic data only."""
import numpy as np
from . import group_models as ridge, difference_ablation as tied, target_models as forward

ALPHAS = (.001, .01, .1)
OBSERVERS = ('starting', 'one_copy', 'tied:passive', 'tied:pulse')
MEASUREMENTS = ('start', 'u0', 'u1', 'pulse')
PAIRS = (('tied:pulse', 'tied:passive'), ('tied:pulse', 'starting'), ('tied:pulse', 'one_copy'),
         ('tied:passive', 'starting'), ('tied:passive', 'one_copy'), ('one_copy', 'starting'))


def matrices(measured):
    if set(measured) != set(MEASUREMENTS):
        raise ValueError('only declared measurement channels')
    start = measured['start']
    if start.ndim != 4 or start.shape[1:] != (4, 4, 7):
        raise ValueError('complete starting measurements')
    for key in MEASUREMENTS:
        value = measured[key]
        want = start.shape if key == 'start' else start.shape[:3] + (6,)
        if value.shape != want or value.dtype != np.float64 or not np.isfinite(value).all():
            raise ValueError('finite complete ' + key)
    first = np.concatenate((start, measured['u0']), -1)
    return dict(starting=start.copy(), one_copy=first,
        **{'tied:passive': np.concatenate((first, measured['u1']), -1),
           'tied:pulse': np.concatenate((first, measured['pulse']), -1)})


def validate(data):
    if set(data) != set(MEASUREMENTS) | {'block_ids', 'futures'}:
        raise ValueError('declared features, IDs and four-future target only')
    matrices({k: data[k] for k in MEASUREMENTS})
    n = len(data['start']); ids = data['block_ids']; y = data['futures']
    if n < 4 or ids.shape != (n,) or ids.dtype != np.int64 or len(set(ids.tolist())) != n:
        raise ValueError('at least four unique whole founders')
    if y.shape != (n, 4, 4, 4) or y.dtype != np.float64 or not np.isfinite(y).all() or np.max(abs(y)) > 1:
        raise ValueError('four complete bounded saved futures')
    return n


def fit_observer(data, name):
    n = validate(data)
    if name not in OBSERVERS:
        raise ValueError('declared observer')
    x = matrices({k: data[k] for k in MEASUREMENTS})[name].reshape(n * 16, -1)
    y = data['futures'].mean(-1).ravel(); ids = data['block_ids']
    groups = np.tile(np.arange(4, dtype=np.int64), n * 4)
    owners = np.repeat(np.arange(n), 16)
    raw, folds = [], []
    fit = tied.fit if name.startswith('tied:') else ridge.fit
    for block in range(n):
        train, test = owners != block, owners == block
        models = [fit(x[train], y[train], groups[train], alpha) for alpha in ALPHAS]
        raw.append(np.stack([forward.raw_predict(m, x[test], groups[test]).reshape(4, 4) for m in models]))
        folds.append(dict(validation_block=int(ids[block]), training_blocks=ids[np.arange(n) != block].tolist(), models=models))
    raw = np.stack(raw, axis=1)
    record = dict(observer=name, blocks=ids.tolist(), alphas=list(ALPHAS), target='future_mean', folds=folds)
    return np.clip(raw, -1, 1), raw, record


def fixture(n=16):
    if type(n) is not int or not 4 <= n <= 16:
        raise ValueError('four to sixteen synthetic founders')
    random = np.random.default_rng(17320260924)
    start = random.normal(size=(n, 4, 4, 7))
    u0 = random.normal(size=(n, 4, 4, 6))
    u1 = random.normal(size=u0.shape)
    pulse = .7 * u1 + .3 * random.normal(size=u0.shape)
    label = .15 * start[..., 0] + .05 * (u0[..., 0] + u1[..., 0])
    futures = np.tanh(label[..., None] + random.normal(0, .3, (n, 4, 4, 4)))
    return dict(start=start, u0=u0, u1=u1, pulse=pulse, futures=futures,
        block_ids=np.arange(n, dtype=np.int64))


def synthetic_panel(data):
    n = validate(data)
    if not np.array_equal(data['block_ids'], np.arange(n, dtype=np.int64)):
        raise ValueError('reference fitting is for synthetic qualification IDs only')
    p, raw, fits = {}, {}, {}
    for name in OBSERVERS:
        p[name], raw[name], fits[name] = fit_observer(data, name)
    return p, raw, fits


def absolute(prediction, raw, futures):
    error = prediction[..., None] - futures
    loss = np.mean(error**2, -1)
    rows = []
    for i, alpha in enumerate(ALPHAS):
        rows.append(dict(alpha=alpha, mse=float(loss[i].mean()), mae=float(abs(error[i]).mean()),
            rmse_points=float(100 * np.sqrt(loss[i].mean())), bias=float(error[i].mean()),
            block_mse=loss[i].mean((1, 2)).tolist(), group_mse=loss[i].mean((0, 1)).tolist(),
            mean_target_mse=float(np.mean((prediction[i] - futures.mean(-1))**2)),
            future_dispersion=float(np.mean((futures - futures.mean(-1)[..., None])**2)),
            clipped=int(np.count_nonzero(prediction[i] != raw[i]))))
    return rows, loss


def paired(candidate, reference, ca, ra, losses, selected=False):
    gain = losses[reference][ra] - losses[candidate][ca]
    founder = gain.mean((1, 2)); n = len(founder)
    base = float(losses[reference][ra].mean())
    return dict(candidate=candidate, reference=reference, candidate_alpha=ALPHAS[ca], reference_alpha=ALPHAS[ra],
        gain=float(gain.mean()), percent_mse_reduction=float(100 * gain.mean() / base) if base else None,
        block_gains=founder.tolist(), group_gains=gain.mean((0, 1)).tolist(),
        positive=int(np.count_nonzero(founder > 0)), negative=int(np.count_nonzero(founder < 0)),
        zero=int(np.count_nonzero(founder == 0)), score_only_omit_gains=((founder.sum() - founder) / (n - 1)).tolist(),
        selection_affected_context=selected)


def summarize(data, predictions, raw):
    n = validate(data)
    if set(predictions) != set(OBSERVERS) or set(raw) != set(OBSERVERS):
        raise ValueError('complete observer panel')
    scores, losses = {}, {}
    for name in OBSERVERS:
        p, r = predictions[name], raw[name]
        if p.shape != (3, n, 4, 4) or r.shape != p.shape or not np.isfinite(r).all():
            raise ValueError('complete finite forecasts')
        np.testing.assert_array_equal(p, np.clip(r, -1, 1))
        scores[name], losses[name] = absolute(p, r, data['futures'])
    comparisons = [paired(c, r, i, i, losses) for i in range(3) for c, r in PAIRS]
    selected = {name: max(i for i in range(3) if scores[name][i]['mse'] <= min(row['mse'] for row in scores[name]) + 1e-12)
                for name in ('starting', 'one_copy')}
    context = [paired(c, r, 1, selected[r], losses, True) for c in ('tied:pulse', 'tied:passive') for r in ('starting', 'one_copy')]
    return dict(schema='d173_feedback_pulse_prediction_v1', blocks=data['block_ids'].tolist(),
        alphas=list(ALPHAS), observers=list(OBSERVERS), focal=['tied:pulse', 'tied:passive', .01],
        absolute=scores, comparisons=comparisons, selected_cheap_alphas={k: ALPHAS[v] for k, v in selected.items()},
        selected_cheap_comparisons=context, target='four_future_mean', cases=n * 16,
        prospective_evidence=False, confidence_intervals=False, equivalence_test=False,
        deployment_selected=False, automatic_successor=False), losses
