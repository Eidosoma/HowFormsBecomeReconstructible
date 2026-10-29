"""Reproduce fixed archived comparators; no fitting or scientific simulation."""
import argparse
import math
from pathlib import Path
import time

import numpy as np

from ec_common import ROOT, C, MODELS, ev, read, ledger, require, verify_sources, feature_matrix, probability_matrix, probability_scalar, complete


def check_training(x, y, fitted):
    """Separate scalar scaling, objective and score-equation check."""
    model = fitted['model']
    n = len(y)
    means = [math.fsum(x[:, j]) / n for j in range(x.shape[1])]
    scales = [math.sqrt(math.fsum((a - mu) ** 2 for a in x[:, j]) / n) for j, mu in enumerate(means)]
    scales = [1. if sd <= 1e-12 else sd for sd in scales]
    require(max(abs(a - b) for a, b in zip(means, model['scaling']['mean'], strict=True)) < 1e-12, 'Wrong training-only centers')
    require(max(abs(a - b) for a, b in zip(scales, model['scaling']['scale'], strict=True)) < 1e-12, 'Wrong training-only scales')
    coefficients = model['coefficients']
    z = [[1.] + [(a - mu) / sd for a, mu, sd in zip(row, means, scales, strict=True)] for row in x]
    eta = [math.fsum(a * b for a, b in zip(row, coefficients, strict=True)) for row in z]
    prob = [1 / (1 + math.exp(-v)) if v >= 0 else math.exp(v) / (1 + math.exp(v)) for v in eta]
    loss = math.fsum(max(v, 0) + math.log1p(math.exp(-abs(v))) - target * v for v, target in zip(eta, y, strict=True)) / n
    loss += .5 * model['ridge'] * math.fsum(b * b for b in coefficients[1:])
    gradient = [math.fsum(row[j] * (p - target) for row, p, target in zip(z, prob, y, strict=True)) / n
                + (model['ridge'] * coefficients[j] if j else 0.) for j in range(len(coefficients))]
    residual = max(abs(v) for v in gradient)
    require(abs(loss - model['loss']) < 1e-12, 'Archived fit objective differs')
    require(residual <= 1e-6 and model['solver_success'], 'Archived fit is not stationary')
    return residual


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    wall = time.monotonic()
    count = verify_sources()
    ledger.atomic_json(folder / 'START.json', dict(utc=ev.utc(), scope='exposed_archived_comparators', new_fits=0))
    source = read(ROOT / 'SOURCE_BINDINGS.json')['files']
    data = ev.load(ROOT / 'context/DATA.npz', source['DATA.npz']['sha256'])
    repeats = ev.load(ROOT / 'context/REPEATS.npz', source['REPEATS.npz']['sha256'])
    previous = ev.load(ROOT / 'context/ARCHIVED_PREDICTIONS.npz', source['ARCHIVED_PREDICTIONS.npz']['sha256'])
    meta = read(ROOT / 'context/REPEAT_META.json')
    fits = read(ROOT / 'context/ARCHIVED_FITS.json')
    blocks = np.unique(data['blocks'])
    require(len(blocks) == 8 and len(data['y']) == 512, 'Complete original development panel required')
    require(all(np.sum(data['blocks'] == b) == 64 for b in blocks), 'Unequal or missing original block')
    predictions = {name: np.empty(512) for name in C['models']}
    gradients = []
    for key in ['none', *[str(b) for b in blocks]]:
        state = fits[key]
        omitted = [] if key == 'none' else [int(key)]
        require(state['omitted_blocks'] == omitted, 'Wrong omitted block')
        train = np.flatnonzero(~np.isin(data['blocks'], omitted))
        test = np.flatnonzero(np.isin(data['blocks'], omitted))
        require(state['training_blocks'] == np.unique(data['blocks'][train]).tolist(), 'Training leakage')
        require(state['training_records'] == len(train), 'Training record count differs')
        for name, identifier in C['models'].items():
            fitted = state['models'][identifier]
            gradients.append(check_training(feature_matrix(data, train, fitted['spec']), data['y'][train], fitted))
            if len(test):
                features = feature_matrix(data, test, fitted['spec'])
                p = probability_matrix(features, fitted)
                scalar = [probability_scalar(row, fitted) for row in features]
                require(np.max(abs(p - scalar)) < 1e-12, 'Independent probability mismatch')
                predictions[name][test] = p
    errors = {name: float(np.max(abs(p - previous['fixed__' + C['models'][name]]))) for name, p in predictions.items()}
    require(max(errors.values()) < 1e-12, 'Archived whole-block predictions changed')
    block_scores = {name: [float(np.mean((p[data['blocks'] == b] - data['y'][data['blocks'] == b]) ** 2)) for b in blocks]
                    for name, p in predictions.items()}
    repeat_precision = {}
    for name, identifier in C['models'].items():
        changes = []
        for index, row in enumerate(meta):
            fitted = fits[str(row['key'][0])]['models'][identifier]
            p = probability_matrix(feature_matrix(repeats, [2 * index, 2 * index + 1], fitted['spec']), fitted)
            changes.append(dict(regime=row['regime'], current_pass=row['current_pass'], difference=float(abs(p[1] - p[0]))))
        repeat_precision[name] = {regime: {str(c): float(np.quantile([v['difference'] for v in changes
            if v['regime'] == regime and v['current_pass'] == c], .9)) for c in (0, 1)} for regime in ('matched', 'independent')}
    result = dict(scope='Exposed-data development diagnostic; no confirmatory inference.', models_checked=len(gradients),
        maximum_scalar_gradient=max(gradients), maximum_archived_forecast_error=max(errors.values()),
        training_blocks=blocks.tolist(), training_records=512, source_files_verified=count,
        brier={name: float(np.mean(values)) for name, values in block_scores.items()}, block_brier=block_scores,
        repeat_p90=repeat_precision, extra_native_reads={name: m['spec']['reads'] for name, m in MODELS.items()},
        new_fits=0, new_native_reads=0, new_future_outcomes=0, historical_selector_verdict='ORDINARY_LEAD_SCREEN_FAILED_UNCHANGED')
    ledger.atomic_json(folder / 'RESULTS.json', result)
    ev.save(folder / 'PREDICTIONS.npz', predictions)
    lines = ['Archived fixed comparators, all eight exposed training blocks excluded in turn.', '',
        'No new fitting, model selection, simulation or confirmatory inference. The earlier variable-budget selector remains failed.', '',
        '| Model | Whole-block-excluded Brier | Extra native reads |', '|---|---:|---:|']
    for name in C['models']:
        lines.append(f"| {name} | {result['brier'][name]:.8f} | {result['extra_native_reads'][name]} |")
    lines += ['', 'All five models share the original eleven boundary features, training records and ridge-logistic fitting contract. Both equal-read controls are retained regardless of this development ranking.', '',
        'All45 archived fits passed separate scalar scaling, objective and gradient checks. All512 predictions per model reproduce their archived whole-block-excluded values. The two-repeat precision diagnostics are saved for both noise regimes and expression classes; they do not change the historical selector verdict.', '']
    with (folder / 'REPORT.md').open('x') as stream:
        stream.write('\n'.join(lines))
    complete(folder, dict(decision='ARCHIVED_COMPARATORS_VERIFIED', scope='development_preparation',
        wall_seconds=time.monotonic() - wall, models_checked=45, new_fits=0, new_native_reads=0, new_future_outcomes=0,
        automatic_successor=False, source_bindings_sha256=ev.sha(ROOT / 'SOURCE_BINDINGS.json')))
    print(result, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
