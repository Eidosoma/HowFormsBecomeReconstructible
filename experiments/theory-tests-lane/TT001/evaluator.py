"""Conventional forecasts with a prefix-only evaluation interface."""
from dataclasses import dataclass
import itertools
import time
import warnings

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = (
    'body.both_correct', 'body.both_reversed', 'body.locked_output_failure',
    'body.other_failure', 'body.individual_cue_accuracy', 'body.worst_margin',
    'body.cue_amplitude_A', 'body.cue_amplitude_B', 'body.absolute_bias_A',
    'body.absolute_bias_B', 'incoming.strong', 'injury.strong_lost',
    'injury.strong_available', 'prior_write.strong_weakened',
    'prior_write.weak_promoted', 'prior_write.strong_sign_flips', 'outgoing.strong',
    'current_write.strong_weakened', 'current_write.weak_promoted',
    'current_write.strong_sign_flips', 'repair.returning',
    'repair.returning_nonzero', 'repair.young_weak', 'repair.young_promoted',
)


@dataclass(frozen=True)
class Dataset:
    groups: np.ndarray
    features: np.ndarray  # lineage, generation, feature
    observed: np.ndarray
    body: np.ndarray  # lineage, generation
    terminal: np.ndarray

    def take(self, rows):
        return Dataset(*(np.array(x[rows], copy=True) for x in
                         (self.groups, self.features, self.observed,
                          self.body, self.terminal)))


@dataclass(frozen=True)
class Probe:
    groups: np.ndarray
    features: np.ndarray
    observed: np.ndarray
    body: np.ndarray


def probe(data, k):
    if not 1 <= k <= data.body.shape[1]:
        raise ValueError('Invalid prefix')
    return Probe(data.groups.copy(), data.features[:, :k].copy(),
                 data.observed[:, :k].copy(), data.body[:, :k].copy())


def target(data, k, endpoint):
    if endpoint == 'terminal':
        return data.terminal.astype(bool).copy()
    if endpoint == 'future_path_and_terminal':
        return data.body[:, k:].all(axis=1) & data.terminal
    raise ValueError(endpoint)


def design(p, model):
    if model == 'current_logistic':
        cols = [0, 5, 6, 7, 8, 9]
        if not p.observed[:, -1, cols].all():
            raise ValueError('Current readout missing')
        return p.features[:, -1, cols].copy()
    a, mask = p.features, p.observed
    if not mask[:, -1].all():
        raise ValueError('Last measurements missing')
    count = mask.sum(axis=1)
    if (count == 0).any():
        raise ValueError('Entire measurement channel missing')
    avg = np.where(mask, a, 0.).sum(axis=1) / count
    clock = np.arange(1, a.shape[1]+1)[None, :, None]
    tmean = (clock*mask).sum(axis=1)/count
    dt = clock-tmean[:, None]
    den = (dt*dt*mask).sum(axis=1)
    slope = np.divide((dt*np.where(mask, a-avg[:, None], 0.)).sum(axis=1),
                      den, out=np.zeros_like(avg), where=den > 0)
    # Reverse cumulative products count only the trailing failed run.
    streak = np.cumprod((~p.body)[:, ::-1], axis=1).sum(axis=1)
    extra = np.column_stack((a[:, :, 5].min(axis=1),
                             (~p.body).mean(axis=1), streak))
    x = np.concatenate((a[:, -1], avg, slope, extra), axis=1)
    if x.shape[1] != 75 or not np.isfinite(x).all():
        raise ValueError('Invalid prefix features')
    return x


def group_folds(groups, nfold):
    unique = np.unique(groups)
    if len(unique) < nfold:
        raise ValueError('Too few independent blocks')
    mapping = {g: i % nfold for i, g in enumerate(unique)}
    return np.array([mapping[g] for g in groups], dtype=int)


def block_means(values, groups):
    values = np.asarray(values, float)
    if len(values) != len(groups) or not np.isfinite(values).all():
        raise ValueError('Invalid scores')
    return np.array([values[groups == g].mean() for g in np.unique(groups)])


def losses(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if y.shape != p.shape or not np.isin(y, [0, 1]).all():
        raise ValueError('Invalid binary targets')
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Invalid probabilities')
    safe = np.clip(p, 1e-6, 1-1e-6)
    return (y-p)**2, -y*np.log(safe)-(1-y)*np.log1p(-safe)


def prevalence(y):
    return float((np.sum(y)+.5)/(len(y)+1))


def markov_fit(data, shrinkage=16.):
    body = data.body.astype(int)
    steps = body.shape[1]-1
    counts = np.zeros((steps, 2, 2), float)
    for t, s, dst in itertools.product(range(steps), range(2), range(2)):
        counts[t, s, dst] = np.sum((body[:, t] == s) & (body[:, t+1] == dst))
    pooled = counts.sum(axis=0)+.5
    pooled /= pooled.sum(axis=1, keepdims=True)
    transition = counts + shrinkage*pooled[None]
    transition /= transition.sum(axis=2, keepdims=True)
    readout = np.array([prevalence(data.terminal[body[:, -1] == s]) for s in range(2)])
    return transition, readout


def markov_predict(fitted, p, endpoint):
    transition, readout = fitted
    k = p.body.shape[1]
    state = np.eye(2)[p.body[:, -1].astype(int)]
    for matrix in transition[k-1:]:
        used = matrix.copy()
        if endpoint == 'future_path_and_terminal':
            used[:, 0] = 0.
        elif endpoint != 'terminal':
            raise ValueError(endpoint)
        state = state @ used
    return state @ readout


def predict(model, params, train, test_probe, k, endpoint):
    """The only evaluation argument is a Probe: it contains no future or target."""
    if test_probe.body.shape[1] != k:
        raise ValueError('Unexpected observation budget')
    if set(train.groups) & set(test_probe.groups):
        raise ValueError('Training and evaluation blocks overlap')
    y = target(train, k, endpoint)
    if model == 'prevalence':
        return np.full(len(test_probe.groups), prevalence(y))
    if model == 'markov':
        return markov_predict(markov_fit(train, params['shrinkage']), test_probe, endpoint)
    x, z = design(probe(train, k), model), design(test_probe, model)
    if len(np.unique(y)) < 2:
        return np.full(len(z), prevalence(y))
    if model in ('current_logistic', 'prefix_logistic'):
        estimator = make_pipeline(StandardScaler(), LogisticRegression(
            C=params['C'], solver='lbfgs', max_iter=1000, tol=1e-8))
    elif model == 'prefix_boosted':
        estimator = HistGradientBoostingClassifier(
            max_iter=100, learning_rate=.1, min_samples_leaf=24,
            max_leaf_nodes=params['leaves'], l2_regularization=params['l2'],
            early_stopping=False, random_state=0)
    else:
        raise ValueError(model)
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        estimator.fit(x, y)
    return estimator.predict_proba(z)[:, 1]


def candidates(model, plan):
    if model == 'prevalence':
        return [{}]
    if model == 'markov':
        return [{'shrinkage': plan['markov_shrinkage']}]
    if model.endswith('logistic'):
        return [{'C': c} for c in plan['logistic_C']]
    if model == 'prefix_boosted':
        return [dict(leaves=l, l2=r) for l in plan['boost_leaves'] for r in plan['boost_l2']]
    raise ValueError(model)


def tune(model, data, k, endpoint, plan):
    grid = candidates(model, plan)
    if len(grid) == 1:
        return grid[0], [], 0
    fold = group_folds(data.groups, plan['inner_folds'])
    scores = []
    fits = 0
    for param in grid:
        pred = np.full(len(data.groups), np.nan)
        for f in range(plan['inner_folds']):
            train, test = data.take(fold != f), data.take(fold == f)
            pred[fold == f] = predict(model, param, train, probe(test, k), k, endpoint)
            fits += 1
        score = block_means(losses(target(data, k, endpoint), pred)[0], data.groups).mean()
        scores.append(dict(parameters=param, block_brier=float(score)))
    winner = int(np.argmin([s['block_brier'] for s in scores]))
    return grid[winner], scores, fits


def evaluate(data, plan, progress=None):
    fold = group_folds(data.groups, plan['outer_folds'])
    outputs, fits, elapsed, predicted = {}, [], {}, {}
    for k, endpoint, model in itertools.product(plan['prefixes'], plan['endpoints'], plan['models']):
        key = f'k{k}.{endpoint}.{model}'
        started = time.monotonic()
        pred = np.full(len(data.groups), np.nan)
        for f in range(plan['outer_folds']):
            train, test = data.take(fold != f), data.take(fold == f)
            param, tuning, count = tune(model, train, k, endpoint, plan)
            pred[fold == f] = predict(model, param, train, probe(test, k), k, endpoint)
            fits.append(dict(key=key, fold=f, parameters=param, tuning=tuning,
                fit_calls=count+1, training_blocks=np.unique(train.groups).tolist(),
                evaluation_blocks=np.unique(test.groups).tolist(),
                training_lineages=len(train.groups), evaluation_lineages=len(test.groups)))
        y = target(data, k, endpoint)
        brier, logloss = losses(y, pred)
        outputs[key] = dict(brier=float(block_means(brier, data.groups).mean()),
            log_loss=float(block_means(logloss, data.groups).mean()),
            observed_rate=float(block_means(y, data.groups).mean()),
            mean_prediction=float(block_means(pred, data.groups).mean()),
            block_brier=block_means(brier, data.groups).tolist(),
            block_log_loss=block_means(logloss, data.groups).tolist(),
            calibration_bins=[dict(lower=j/10, upper=(j+1)/10,
                count=int(((pred >= j/10) & ((pred < (j+1)/10) if j < 9 else (pred <= 1))).sum()),
                predicted=float(pred[(pred >= j/10) & ((pred < (j+1)/10) if j < 9 else (pred <= 1))].mean())
                    if ((pred >= j/10) & ((pred < (j+1)/10) if j < 9 else (pred <= 1))).any() else None,
                observed=float(y[(pred >= j/10) & ((pred < (j+1)/10) if j < 9 else (pred <= 1))].mean())
                    if ((pred >= j/10) & ((pred < (j+1)/10) if j < 9 else (pred <= 1))).any() else None)
                for j in range(10)])
        predicted[key] = pred
        elapsed[key] = time.monotonic()-started
        if progress:
            progress(key)
    draws = np.random.default_rng(plan['random_seed']).integers(
        0, len(np.unique(data.groups)), (plan['bootstrap_draws'], len(np.unique(data.groups))))
    for k, endpoint in itertools.product(plan['prefixes'], plan['endpoints']):
        baseline = np.array(outputs[f'k{k}.{endpoint}.prevalence']['block_brier'])
        for model in plan['models']:
            key = f'k{k}.{endpoint}.{model}'
            diff = baseline-np.array(outputs[key]['block_brier'])
            outputs[key]['brier_gain_over_prevalence'] = dict(mean=float(diff.mean()),
                descriptive_interval=np.quantile(diff[draws].mean(axis=1), [.025, .975]).tolist())
    return dict(scores=outputs, fits=fits, model_seconds=elapsed,
                total_fit_calls=sum(f['fit_calls'] for f in fits)), predicted, fold


def synthetic(blocks=32, lineages=16, seed=0):
    """Excluded technical input with correlated group and lineage effects."""
    rng = np.random.default_rng(seed)
    n = blocks*lineages
    groups = np.repeat(np.arange(blocks), lineages)
    risk = rng.normal(size=(blocks, 1))[groups]+rng.normal(size=(n, 1))
    margin = .55-.016*np.arange(32)[None]+.15*risk+.2*rng.normal(size=(n, 32))
    body = margin > .25
    features = rng.normal(size=(n, 32, 24))
    features[:, :, 0] = body
    features[:, :, 5] = margin
    observed = np.ones_like(features, bool)
    observed[:, 0, 13:16] = False
    terminal = margin[:, -1]+rng.normal(scale=.25, size=n) > .25
    return Dataset(groups, features, observed, body, terminal)
