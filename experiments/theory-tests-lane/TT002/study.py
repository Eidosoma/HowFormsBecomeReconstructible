"""Add matched-channel current forecasts to immutable TT001 development results."""
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
import time
import warnings

import numpy as np

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
PLAN = json.loads((HERE/'plan.json').read_text())
PRIOR = LANE/PLAN['prior_run']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_prior():
    if sha(PRIOR/'COMPLETE.json') != PLAN['prior_complete_sha256']:
        raise ValueError('Prior completion identity changed')
    record = json.loads((PRIOR/'COMPLETE.json').read_text())
    for name, expected in record['outputs_sha256'].items():
        if sha(PRIOR/name) != expected:
            raise ValueError('Prior output changed: '+name)
    return record


verify_prior()
spec = importlib.util.spec_from_file_location('tt001_frozen_evaluator', PRIOR/'inputs/TT001/evaluator.py')
e = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = e
spec.loader.exec_module(e)
REUSED = {'prevalence': 'prevalence', 'current6_logistic': 'current_logistic',
          'history24_logistic': 'prefix_logistic', 'history24_boosted': 'prefix_boosted'}


def load_data():
    with np.load(PRIOR/'development_dataset.npz', allow_pickle=False) as z:
        return e.Dataset(*(z[k] for k in ('groups', 'features', 'observed', 'body', 'terminal')))


def current_design(probe, columns=None):
    columns = np.arange(24) if columns is None else np.asarray(columns)
    values = probe.features[:, -1, columns]
    if not probe.observed[:, -1, columns].all() or not np.isfinite(values).all():
        raise ValueError('Missing or invalid latest diagnostic')
    return values.copy()


def predict(model, params, train, test_probe, k, endpoint, columns=None):
    if test_probe.body.shape[1] != k or set(train.groups) & set(test_probe.groups):
        raise ValueError('Observation budget or block separation violated')
    x, z = current_design(e.probe(train, k), columns), current_design(test_probe, columns)
    y = e.target(train, k, endpoint)
    if len(np.unique(y)) < 2:
        return np.full(len(z), e.prevalence(y))
    if model == 'current24_logistic':
        fit = e.make_pipeline(e.StandardScaler(), e.LogisticRegression(
            C=params['C'], solver='lbfgs', max_iter=1000, tol=1e-8))
    elif model == 'current24_boosted':
        fit = e.HistGradientBoostingClassifier(max_iter=100, learning_rate=.1,
            min_samples_leaf=24, max_leaf_nodes=params['leaves'],
            l2_regularization=params['l2'], early_stopping=False, random_state=0)
    else:
        raise ValueError(model)
    with warnings.catch_warnings():
        warnings.simplefilter('error', e.ConvergenceWarning)
        fit.fit(x, y)
    return fit.predict_proba(z)[:, 1]


def tune(model, data, k, endpoint, plan):
    reference = 'current_logistic' if model.endswith('logistic') else 'prefix_boosted'
    grid = e.candidates(reference, plan)
    folds = e.group_folds(data.groups, plan['inner_folds'])
    scores = []
    for parameters in grid:
        predictions = np.full(len(data.groups), np.nan)
        for fold in range(plan['inner_folds']):
            train, test = data.take(folds != fold), data.take(folds == fold)
            predictions[folds == fold] = predict(model, parameters, train, e.probe(test, k), k, endpoint)
        value = e.block_means(e.losses(e.target(data, k, endpoint), predictions)[0], data.groups).mean()
        scores.append(dict(parameters=parameters, block_brier=float(value)))
    selected = int(np.argmin([x['block_brier'] for x in scores]))
    return grid[selected], scores, len(grid)*plan['inner_folds']


def scalar_scores(data, key, probabilities):
    cutoff, endpoint, _ = key.split('.')
    k = int(cutoff[1:])
    labels = [int(bool(data.terminal[i]) and
        (endpoint == 'terminal' or all(bool(v) for v in data.body[i, k:])))
        for i in range(len(data.groups))]
    blocks, logarithms = [], []
    for group in np.unique(data.groups):
        rows = np.flatnonzero(data.groups == group)
        blocks.append(sum((labels[i]-float(probabilities[i]))**2 for i in rows)/len(rows))
        logarithms.append(sum(-math.log(min(1-1e-6, max(1e-6,
            float(probabilities[i]))) if labels[i] else
            1-min(1-1e-6, max(1e-6, float(probabilities[i])))) for i in rows)/len(rows))
    by_vector = e.block_means(e.losses(e.target(data, k, endpoint), probabilities)[0], data.groups)
    np.testing.assert_allclose(by_vector, blocks, rtol=0, atol=1e-14)
    return dict(brier=float(np.mean(blocks)), log_loss=float(np.mean(logarithms)),
        block_brier=blocks, block_log_loss=logarithms, observed_rate=float(np.mean(labels)),
        mean_prediction=float(np.mean(probabilities)))


def evaluate(data, plan, *, benchmark=False, progress=None):
    folds = e.group_folds(data.groups, plan['outer_folds'])
    predictions, fits, seconds = {}, [], {}
    if not benchmark:
        old_summary = json.loads((PRIOR/'summary.json').read_text())
        with np.load(PRIOR/'predictions.npz', allow_pickle=False) as old:
            np.testing.assert_array_equal(folds, old['fold'])
            np.testing.assert_array_equal(data.groups, old['groups'])
            for k, endpoint, name in itertools.product(plan['prefixes'], plan['endpoints'], REUSED):
                predictions[f'k{k}.{endpoint}.{name}'] = old[f'k{k}.{endpoint}.{REUSED[name]}'].copy()
    else:
        # Technical placeholders exercise storage/scoring; they are not fitted comparators.
        for k, endpoint, name in itertools.product(plan['prefixes'], plan['endpoints'], REUSED):
            predictions[f'k{k}.{endpoint}.{name}'] = np.full(len(data.groups), .5)
    for k, endpoint, model in itertools.product(plan['prefixes'], plan['endpoints'], plan['new_models']):
        key = f'k{k}.{endpoint}.{model}'
        start = time.monotonic()
        p = np.full(len(data.groups), np.nan)
        for fold in range(plan['outer_folds']):
            train, test = data.take(folds != fold), data.take(folds == fold)
            parameters, tuning, count = tune(model, train, k, endpoint, plan)
            p[folds == fold] = predict(model, parameters, train, e.probe(test, k), k, endpoint)
            fits.append(dict(key=key, fold=fold, parameters=parameters, tuning=tuning,
                fit_calls=count+1, training_blocks=np.unique(train.groups).tolist(),
                evaluation_blocks=np.unique(test.groups).tolist()))
        predictions[key] = p
        seconds[key] = time.monotonic()-start
        if progress:
            progress(key)
    scores = {key: scalar_scores(data, key, p) for key, p in predictions.items()}
    if not benchmark:
        for key, result in scores.items():
            k, endpoint, name = key.split('.')
            if name in REUSED:
                previous = old_summary['scores'][f'{k}.{endpoint}.{REUSED[name]}']
                for metric in ('brier', 'log_loss', 'block_brier', 'block_log_loss'):
                    np.testing.assert_allclose(result[metric], previous[metric], rtol=0, atol=1e-12)
    draws = np.random.default_rng(plan['random_seed']).integers(0, len(np.unique(data.groups)),
        (plan['bootstrap_draws'], len(np.unique(data.groups))))
    contrasts = {}
    for k, endpoint in itertools.product(plan['prefixes'], plan['endpoints']):
        prefix = f'k{k}.{endpoint}.'
        pairs = [('history_gain_logistic', 'current24_logistic', 'history24_logistic'),
                 ('history_gain_boosted', 'current24_boosted', 'history24_boosted'),
                 ('additional_current_channels', 'current6_logistic', 'current24_logistic')]
        for name, reference, candidate in pairs:
            difference = np.asarray(scores[prefix+reference]['block_brier'])-scores[prefix+candidate]['block_brier']
            boot = difference[draws].mean(axis=1)
            # A separate scalar calculation checks the resampling contrast.
            scalar = np.array([sum(float(difference[i]) for i in row)/len(row) for row in draws])
            np.testing.assert_allclose(boot, scalar, rtol=0, atol=1e-14)
            contrasts[prefix+name] = dict(reference=reference, candidate=candidate,
                mean=float(difference.mean()), block_differences=difference.tolist(),
                descriptive_interval=np.quantile(boot, [.025, .975]).tolist())
    return dict(scores=scores, contrasts=contrasts, fits=fits, model_seconds=seconds,
        fit_calls=sum(x['fit_calls'] for x in fits), prediction_scores_checked=len(data.groups)*len(scores)), predictions, folds
