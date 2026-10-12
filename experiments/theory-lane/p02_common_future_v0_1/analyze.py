"""Fixed P02 matching and whole-block-excluded models; no parameter search."""
import csv
import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from extract import HERE, read, sha, write_csv, write_json

KEYS = ('block', 'history', 'founder', 'recipient')
INTEGERS = {'block', 'founder', 'recipient', 'generation', 'task_rule', 'current_pass', 'terminal_success'}


def load_records(path):
    with Path(path).open() as f:
        return [{k: v if k == 'history' else int(v) if k in INTEGERS else float(v)
                 for k, v in row.items()} for row in csv.DictReader(f)]


def validate(records, cfg):
    keys = [tuple(r[k] for k in KEYS) for r in records]
    expected = set(itertools.product(cfg['blocks'], cfg['histories'], range(4), range(4)))
    assert len(keys) == len(set(keys)) and set(keys) == expected
    for r in records:
        assert r['generation'] == cfg['generation']
        aligned = [r[k] for k in cfg['expression_features'][:4]]
        assert r['current_margin'] == min(aligned)
        assert r['current_pass'] == int(min(aligned) > cfg['margin'])
        assert r['terminal_success'] in (0, 1)
        assert r['terminal_success'] == int(r['terminal_margin'] > cfg['margin'])


def design(records, cfg, model):
    # Explicit whitelist: future fields, seed, block, founder, recipient never enter.
    names = list(cfg['expression_features'])
    if model['unsigned']:
        names += cfg['conventional_features']
    columns = [np.array([r[k] for r in records], float) for k in names]
    for history in cfg['histories'][1:]:
        names.append('history=' + history)
        columns.append(np.array([r['history'] == history for r in records], float))
    if model['quadratic']:
        for i, j in itertools.combinations_with_replacement(range(4), 2):
            names.append(cfg['expression_features'][i] + '*' + cfg['expression_features'][j])
            columns.append(columns[i] * columns[j])
    if model['signed']:
        names += cfg['candidate_features']
        columns.extend(np.array([r[k] for r in records], float) for k in cfg['candidate_features'])
    matrix = np.column_stack(columns)
    assert np.isfinite(matrix).all() and len(names) == len(set(names))
    return matrix, names


def fit_fold(x, y, train, test, cfg):
    mean, scale = x[train].mean(axis=0), x[train].std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.)
    a = np.column_stack((np.ones(np.sum(train)), (x[train]-mean)/scale))
    b = np.column_stack((np.ones(np.sum(test)), (x[test]-mean)/scale))
    target = y[train]
    ridge = cfg['logistic_ridge']

    def objective(w):
        z = a @ w
        loss = np.mean(np.logaddexp(0., z)-target*z) + .5*ridge*np.sum(w[1:]**2)
        gradient = a.T @ (expit(z)-target)/len(target)
        gradient[1:] += ridge*w[1:]
        return loss, gradient

    opts = cfg['optimizer']
    fit = minimize(objective, np.zeros(a.shape[1]), jac=True, method=opts['method'],
                   options={k: opts[k] for k in ('maxiter', 'ftol', 'gtol')})
    assert fit.success, str(fit.message)
    z = b @ fit.x
    return z, dict(mean=mean.tolist(), scale=scale.tolist(), coefficients=fit.x.tolist(),
                   objective=float(fit.fun), iterations=int(fit.nit), success=bool(fit.success),
                   maximum_gradient=float(np.max(np.abs(fit.jac))))


def rate_fold(records, y, train, test, cfg):
    rates, counts = {}, {}
    history = np.array([r['history'] for r in records])
    for h in cfg['histories']:
        subset = train & (history == h)
        count, successes = int(subset.sum()), int(y[subset].sum())
        assert count
        rates[h] = (successes+cfg['condition_rate_half_count'])/(count+2*cfg['condition_rate_half_count'])
        counts[h] = dict(n=count, successes=successes)
    return logit(np.array([rates[r['history']] for i, r in enumerate(records) if test[i]])), dict(rates=rates, counts=counts)


def choice_weight(a, b):
    return 1. if a > b else 0. if a < b else .5


def matching(records, cfg):
    index = {tuple(r[k] for k in KEYS): r for r in records}
    pairs = []
    for block, founder, recipient in itertools.product(cfg['blocks'], range(4), range(4)):
        a, b = [index[(block, h, founder, recipient)] for h in cfg['matched_pair']]
        differences = [abs(a[k]-b[k]) for k in cfg['expression_features'][:4]]
        coarse = bool(a['current_pass'] and b['current_pass'])
        pairs.append(dict(block=block, founder=founder, recipient=recipient,
            max_expression_difference=max(differences), current_both_pass=int(coarse),
            strict_match=int(coarse and max(differences) <= cfg['match_caliper']),
            exact_expression=int(max(differences) == 0.),
            spaced_current=a['current_pass'], clustered_current=b['current_pass'],
            spaced_terminal=a['terminal_success'], clustered_terminal=b['terminal_success'],
            spaced_margin=a['current_margin'], clustered_margin=b['current_margin'],
            spaced_signed=a['signed_transfer'], clustered_signed=b['signed_transfer'],
            choose_spaced_constant=1., choose_spaced_margin=choice_weight(a['current_margin'], b['current_margin']),
            choose_spaced_signed=choice_weight(a['signed_transfer'], b['signed_transfer'])))

    def subset_summary(group):
        n = len(group)
        a = np.array([r['spaced_terminal'] for r in group], int)
        b = np.array([r['clustered_terminal'] for r in group], int)
        d = np.array([r['max_expression_difference'] for r in group])
        return dict(n=n, spaced_successes=int(a.sum()), clustered_successes=int(b.sum()),
            both_pass=int(((a == 1) & (b == 1)).sum()), both_fail=int(((a == 0) & (b == 0)).sum()),
            spaced_only=int(((a == 1) & (b == 0)).sum()), clustered_only=int(((a == 0) & (b == 1)).sum()),
            difference=float((a-b).mean()) if n else None,
            mean_expression_difference=float(d.mean()) if n else None,
            max_expression_difference=float(d.max()) if n else None)

    summaries = {}
    predicates = dict(all=lambda r: True, both_current_pass=lambda r: r['current_both_pass'],
                      strict=lambda r: r['strict_match'], exact=lambda r: r['exact_expression'])
    for name, predicate in predicates.items():
        group = [r for r in pairs if predicate(r)]
        summaries[name] = subset_summary(group)
        summaries[name]['by_block'] = {str(b): subset_summary([r for r in group if r['block'] == b]) for b in cfg['blocks']}
    strict = [r for r in pairs if r['strict_match']]
    decisions = {}

    def decide(group, rule):
        yields, regrets, ranks, ties = [], [], [], 0
        for r in group:
            a, b, w = r['spaced_terminal'], r['clustered_terminal'], r['choose_spaced_' + rule]
            attained = w*a + (1-w)*b
            yields.append(attained)
            regrets.append(max(a, b)-attained)
            if a != b:
                ranks.append(attained)
                ties += int(w == .5)
        return dict(n=len(group), successes=float(sum(yields)),
            success_rate=float(np.mean(yields)) if group else None,
            hindsight_oracle_successes=int(sum(max(r['spaced_terminal'], r['clustered_terminal']) for r in group)),
            regret=float(sum(regrets)), mean_regret=float(np.mean(regrets)) if group else None,
            discordant=len(ranks), discordant_accuracy=float(np.mean(ranks)) if ranks else None,
            discordant_ties=ties, discordant_nontie_coverage=(len(ranks)-ties)/len(ranks) if ranks else None)

    for rule in ('constant', 'margin', 'signed'):
        decisions[rule] = decide(strict, rule)
        decisions[rule]['by_block'] = {str(b): decide([r for r in strict if r['block'] == b], rule) for b in cfg['blocks']}
    return pairs, dict(subsets=summaries, choices_on_strict_matches=decisions)


def forecasts(records, cfg):
    blocks = np.array([r['block'] for r in records])
    y = np.array([r['terminal_success'] for r in records], float)
    predictions, fits = [], []
    for model in cfg['models']:
        if model.get('estimator') != 'rate':
            x, columns = design(records, cfg, model)
        else:
            columns = []
        for block in cfg['blocks']:
            test, train = blocks == block, blocks != block
            if model.get('estimator') == 'rate':
                z, fitted = rate_fold(records, y, train, test, cfg)
            else:
                z, fitted = fit_fold(x, y, train, test, cfg)
            fitted.update(model=model['id'], heldout_block=block, train_blocks=sorted(set(blocks[train].tolist())),
                          n_train=int(train.sum()), n_test=int(test.sum()), columns=columns)
            fits.append(fitted)
            for i, log_odds in zip(np.flatnonzero(test), z):
                p = float(expit(log_odds))
                predictions.append(dict(model=model['id'], **{k: records[i][k] for k in KEYS},
                    target=int(y[i]), probability=p, log_odds=float(log_odds),
                    brier=float((p-y[i])**2), log_loss=float(np.logaddexp(0., log_odds)-y[i]*log_odds)))
    score_rows = []
    for model in cfg['models']:
        for block in cfg['blocks']:
            for history in ['all', *cfg['histories']]:
                group = [r for r in predictions if r['model'] == model['id'] and r['block'] == block
                         and (history == 'all' or r['history'] == history)]
                score_rows.append(dict(model=model['id'], block=block, history=history, n=len(group),
                                       brier=float(np.mean([r['brier'] for r in group])),
                                       log_loss=float(np.mean([r['log_loss'] for r in group]))))
    scores = {}
    for model in cfg['models']:
        scores[model['id']] = {}
        for history in ['all', *cfg['histories']]:
            group = [r for r in score_rows if r['model'] == model['id'] and r['history'] == history]
            scores[model['id']][history] = {metric: float(np.mean([r[metric] for r in group])) for metric in ('brier', 'log_loss')}
    contrasts = []
    comparisons = [cfg['primary_comparison'], cfg['secondary_comparison']]
    comparisons += [['history_rate', m['id']] for m in cfg['models'][1:]]
    lookup = {(r['model'], r['block']): r for r in score_rows if r['history'] == 'all'}
    for base, candidate in comparisons:
        diffs = {str(b): lookup[(base, b)]['brier']-lookup[(candidate, b)]['brier'] for b in cfg['blocks']}
        contrasts.append(dict(baseline=base, candidate=candidate,
            mean_brier_improvement=float(np.mean(list(diffs.values()))),
            block_brier_improvements=diffs, positive_blocks=sum(d > 0 for d in diffs.values()),
            tied_blocks=sum(d == 0 for d in diffs.values()), negative_blocks=sum(d < 0 for d in diffs.values())))
    return predictions, fits, score_rows, dict(scores=scores, comparisons=contrasts)


def main():
    start = time.perf_counter()
    for name, digest in read(HERE / 'definition_snapshot.json')['files_sha256'].items():
        assert sha(HERE / name) == digest
    cfg = read(HERE / 'config.json')
    result = HERE / 'results'
    assert sha(result / 'records.csv') == read(result / 'extraction.json')['records_sha256']
    records = load_records(result / 'records.csv')
    validate(records, cfg)
    pairs, matched = matching(records, cfg)
    predictions, fits, score_rows, forecast = forecasts(records, cfg)
    write_csv(result / 'pairs.csv', pairs)
    write_csv(result / 'predictions.csv', predictions)
    write_csv(result / 'scores.csv', score_rows)
    write_json(result / 'fits.json', fits)
    counts = {h: dict(n=sum(r['history'] == h for r in records),
        current_successes=sum(r['current_pass'] for r in records if r['history'] == h),
        terminal_successes=sum(r['terminal_success'] for r in records if r['history'] == h)) for h in cfg['histories']}
    answer = dict(status='DEVELOPMENT_COMPLETE_NOT_CONFIRMATORY', generation=cfg['generation'],
        terminal_generation=cfg['terminal_generation'], native_simulations=False, records=len(records), blocks=len(cfg['blocks']),
        logistic_fits=40, seconds=time.perf_counter()-start, counts=counts, matching=matched, forecasts=forecast)
    write_json(result / 'analysis.json', answer)
    print(json.dumps(dict(status=answer['status'], seconds=answer['seconds'], counts=counts,
        matching={k: {f:v for f,v in x.items() if f != 'by_block'} for k,x in matched['subsets'].items()},
        model_scores={k: v['all'] for k,v in forecast['scores'].items()}, primary=forecast['comparisons'][0])))


if __name__ == '__main__':
    main()
