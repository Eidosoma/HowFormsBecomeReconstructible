"""Fixed three-boundary, whole-block terminal prediction check. No native dynamics."""
import csv
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import time
import traceback

import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parent
KEYS = ('block', 'pairing', 'source_writer', 'founder', 'recipient')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def write_csv(path, rows):
    with Path(path).open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def key(row):
    return (int(float(row['block'])), row['pairing'], row['source_writer'],
            int(float(row['founder'])), int(float(row['recipient'])))


def assemble(rows, cfg):
    """Join only whitelisted early measurements; one terminal label per lineage."""
    generations = cfg['probe_generations']
    allowed = cfg['expression_features'] + cfg['mechanistic_features']
    groups = {}
    ignored = 0
    for row in rows:
        g = int(float(row['generation']))
        if g not in generations:
            ignored += 1
            continue
        k = key(row)
        history = groups.setdefault(k, {})
        if g in history:
            raise ValueError(f'Duplicate early boundary: {k}, {g}')
        # No next-body or terminal-margin fields are accessed here.
        measurements = {name: float(row[name]) for name in allowed}
        y = float(row[cfg['target']])
        if y not in (0., 1.) or measurements['current_pass'] not in (0., 1.):
            raise ValueError('Nonbinary score')
        if not all(np.isfinite(v) for v in measurements.values()):
            raise ValueError('Nonfinite early feature')
        history[g] = (measurements, y)
    expected = set(product(cfg['blocks'], cfg['pairings'], cfg['writers'],
                           cfg['founders'], cfg['recipients']))
    if set(groups) != expected:
        raise ValueError('Incomplete or unexpected lineage cohort')
    records = []
    for k in sorted(groups):
        history = groups[k]
        if set(history) != set(generations):
            raise ValueError(f'Missing early boundary: {k}')
        if len({y for _, y in history.values()}) != 1:
            raise ValueError(f'Changing terminal target: {k}')
        record = dict(zip(KEYS, k, strict=True))
        record['observed'] = int(history[generations[0]][1])
        for g in generations:
            record.update({f'g{g}_{name}': value for name, value in history[g][0].items()})
        records.append(record)
    return records, dict(lineages=len(records), boundaries_joined=len(records)*len(generations),
                         later_rows_ignored=ignored, independent_blocks=len(cfg['blocks']),
                         complete_cohort=True, terminal_targets_consistent=True)


def condition_names(cfg):
    return [p + '/' + w for p in cfg['pairings'] for w in cfg['writers']]


def condition(record):
    return record['pairing'] + '/' + record['source_writer']


def design(records, spec, cfg):
    generations = spec['generations']
    columns = [f'g{g}_{name}' for g in generations for name in cfg['expression_features']]
    x = np.array([[r[name] for name in columns] for r in records], dtype=float)
    if len(generations) == 1:
        columns.append('generation_fraction')
        x = np.column_stack([x, np.full(len(records), generations[0]/cfg['horizon'])])
    if spec['context'] == 'additive':
        context_columns = ['tolerance_writer', *cfg['pairings'][1:]]
        context = [[float(r['source_writer'] == 'tolerance_rewrite'),
                    *[float(r['pairing'] == p) for p in cfg['pairings'][1:]]] for r in records]
    else:
        context_columns = condition_names(cfg)[1:]
        context = [[float(condition(r) == c) for c in context_columns] for r in records]
    x = np.column_stack([x, context])
    columns.extend(context_columns)
    if spec['mechanistic']:
        extra = [f'g{g}_{name}' for g in generations for name in cfg['mechanistic_features']]
        x = np.column_stack([x, [[r[name] for name in extra] for r in records]])
        columns.extend(extra)
    return x, columns


def fit_predict(x, y, train, test, cfg):
    """Same estimator as prior frozen analyze.py, with training-only scaling."""
    if np.any(train & test) or not np.any(train) or not np.any(test):
        raise ValueError('Invalid training/test split')
    mean = x[train].mean(axis=0)
    scale = x[train].std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.)
    a = np.column_stack([np.ones(train.sum()), (x[train]-mean)/scale])
    b = np.column_stack([np.ones(test.sum()), (x[test]-mean)/scale])
    target = y[train]
    ridge = cfg['logistic_ridge']

    def objective(w):
        z = a @ w
        loss = float(np.mean(np.logaddexp(0, z)-target*z) + ridge*.5*np.sum(w[1:]**2))
        gradient = a.T @ (expit(z)-target)/len(target)
        gradient[1:] += ridge*w[1:]
        return loss, gradient

    options = {k: v for k, v in cfg['optimizer'].items() if k != 'method'}
    fit = minimize(objective, np.zeros(a.shape[1]), jac=True,
                   method=cfg['optimizer']['method'], options=options)
    if not fit.success:
        raise RuntimeError(str(fit.message))
    logits = b @ fit.x
    return expit(logits), logits, dict(success=True, iterations=int(fit.nit),
        objective=float(fit.fun), mean=mean.tolist(), scale=scale.tolist(),
        coefficients=fit.x.tolist())


def rate_predict(y, conditions, train, test, cfg):
    rates = {}
    counts = {}
    half = cfg['condition_rate_half_count']
    for c in condition_names(cfg):
        selected = train & (conditions == c)
        n = int(selected.sum())
        if not n:
            raise ValueError('Unseen condition in training set')
        successes = int(y[selected].sum())
        rates[c] = (successes+half)/(n+2*half)
        counts[c] = dict(n=n, successes=successes, probability=rates[c])
    p = np.array([rates[c] for c in conditions[test]])
    return p, logit(p), dict(success=True, counts=counts)


def scores(y, p, z):
    return dict(n=len(y), successes=int(y.sum()),
                brier=float(np.mean((p-y)**2)),
                log_loss=float(np.mean(np.logaddexp(0, z)-y*z)))


def compare_models(spec, models, by_condition, cfg):
    baseline = models[spec['baseline']]
    candidate = models[spec['candidate']]
    difference = baseline['mean_block_brier']-candidate['mean_block_brier']
    folds = [dict(block=b['block'], brier_improvement=b['brier']-c['brier'],
                  log_loss_improvement=b['log_loss']-c['log_loss'])
             for b, c in zip(baseline['folds'], candidate['folds'], strict=True)]
    condition_gains = []
    for name in condition_names(cfg):
        base = [r for r in by_condition if r['model'] == spec['baseline'] and r['condition'] == name]
        cand = [r for r in by_condition if r['model'] == spec['candidate'] and r['condition'] == name]
        condition_gains.append(dict(condition=name,
            brier_improvement=float(np.mean([b['brier']-c['brier'] for b, c in zip(base, cand, strict=True)])),
            log_loss_improvement=float(np.mean([b['log_loss']-c['log_loss'] for b, c in zip(base, cand, strict=True)])),
            blocks_with_lower_brier=sum(b['brier'] > c['brier'] for b, c in zip(base, cand, strict=True))))
    return dict(**spec, brier_improvement=difference,
        relative_brier_improvement=difference/baseline['mean_block_brier'],
        log_loss_improvement=baseline['mean_block_log_loss']-candidate['mean_block_log_loss'],
        blocks_with_lower_brier=sum(r['brier_improvement'] > 0 for r in folds),
        folds=folds, conditions=condition_gains)


def check_reference(records, predictions, source, cfg):
    reference = {}
    with (source/'results/held_out_predictions.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            if row['target'] == 'terminal_from_generation1':
                k = key(row)
                if k in reference:
                    raise ValueError('Duplicate reference forecast')
                reference[k] = row
    if set(reference) != {key(r) for r in records}:
        raise ValueError('Reference forecast coverage differs')
    result = {}
    for name, old in [('g1_additive_expression', 'current_expression_and_context'),
                      ('g1_additive_mechanistic', 'plus_mechanistic_features')]:
        differences = []
        for i, r in enumerate(records):
            ref = reference[key(r)]
            if r['observed'] != float(ref['observed']):
                raise ValueError('Reference target differs')
            differences.append(abs(predictions[name][0][i]-float(ref[old])))
        maximum = max(differences)
        if maximum > cfg['reference_probability_tolerance']:
            raise ValueError(f'Reference mismatch {name}: {maximum}')
        result[name] = dict(max_probability_difference=maximum, n=len(differences))
    return result


def run(folder):
    started = time.perf_counter()
    cfg = json.loads((ROOT/'config.json').read_text())
    source = (ROOT/cfg['source']).resolve()
    folder.mkdir(exist_ok=False)
    start = dict(status='RUNNING', started_at_utc=stamp(), config_sha256=sha(ROOT/'config.json'),
        protocol_sha256=sha(ROOT/'PROTOCOL.md'), code_sha256=sha(Path(__file__)),
        input_bindings=cfg['inputs'], forecast_seconds=cfg['runtime']['forecast_seconds'],
        environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                         numerical_threads=1), native_simulator_steps=0)
    write_json(folder/'START.json', start)
    try:
        for item in cfg['inputs']:
            if sha(source/item['path']) != item['sha256']:
                raise ValueError(f'Input hash mismatch: {item["path"]}')
        with (source/'results/features.csv').open(newline='') as f:
            records, checks = assemble(csv.DictReader(f), cfg)
        write_csv(folder/'lineage_features.csv', records)
        y = np.array([r['observed'] for r in records])
        blocks = np.array([r['block'] for r in records])
        conditions = np.array([condition(r) for r in records])
        models, predictions, by_condition = {}, {}, []
        for spec in cfg['models']:
            p, z = np.zeros(len(y)), np.zeros(len(y))
            folds = []
            if spec.get('estimator') != 'smoothed_condition_rate':
                x, columns = design(records, spec, cfg)
            else:
                columns = []
            for held in cfg['blocks']:
                test = blocks == held
                train = ~test
                if spec.get('estimator') == 'smoothed_condition_rate':
                    p[test], z[test], fit = rate_predict(y, conditions, train, test, cfg)
                else:
                    p[test], z[test], fit = fit_predict(x, y, train, test, cfg)
                folds.append(dict(block=held, training_blocks=sorted(set(blocks[train].tolist())),
                                  **scores(y[test], p[test], z[test]), fit=fit))
                for c in condition_names(cfg):
                    selected = test & (conditions == c)
                    by_condition.append(dict(model=spec['id'], block=held, condition=c,
                                             **scores(y[selected], p[selected], z[selected])))
            models[spec['id']] = dict(columns=columns, folds=folds,
                mean_block_brier=float(np.mean([r['brier'] for r in folds])),
                mean_block_log_loss=float(np.mean([r['log_loss'] for r in folds])))
            predictions[spec['id']] = (p, z)
        reference = check_reference(records, predictions, source, cfg)
        prediction_rows = []
        for i, r in enumerate(records):
            row = {k: r[k] for k in (*KEYS, 'observed')}
            for name, (p, z) in predictions.items():
                row[name] = float(p[i])
                row[name+'_logit'] = float(z[i])
            prediction_rows.append(row)
        write_csv(folder/'held_out_predictions.csv', prediction_rows)
        write_csv(folder/'condition_scores.csv', by_condition)
        comparisons = [compare_models(s, models, by_condition, cfg) for s in cfg['comparisons']]
        report = dict(status=cfg['status'], created_at_utc=stamp(), checks=checks, reference_check=reference,
            models=models, comparisons=comparisons, native_simulator_steps=0,
            input_feature_sha256=cfg['inputs'][1]['sha256'],
            lineage_feature_sha256=sha(folder/'lineage_features.csv'),
            prediction_sha256=sha(folder/'held_out_predictions.csv'),
            condition_scores_sha256=sha(folder/'condition_scores.csv'),
            elapsed_seconds=time.perf_counter()-started,
            inference_limit='Eight exposed blocks; same known conditions; no independent confirmation or causal mediation test.')
        write_json(folder/'analysis.json', report)
        complete = dict(**{k: v for k, v in start.items() if k != 'status'}, status='COMPLETE',
            completed_at_utc=stamp(), elapsed_seconds=time.perf_counter()-started,
            results_sha256={p.name: sha(p) for p in sorted(folder.iterdir()) if p.is_file()})
        write_json(folder/'COMPLETE.json', complete)
        print(json.dumps(dict(seconds=report['elapsed_seconds'], checks=checks, reference=reference,
            models={k: {s: v[s] for s in ('mean_block_brier', 'mean_block_log_loss')} for k, v in models.items()},
            comparisons=[{k: v for k, v in r.items() if k not in ('folds', 'conditions')} for r in comparisons]), indent=2))
    except BaseException:
        write_json(folder/'FAILED.json', dict(status='FAILED', at_utc=stamp(), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    run(ROOT/'results')
