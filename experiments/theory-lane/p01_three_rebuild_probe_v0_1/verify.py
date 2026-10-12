"""Standard-library verification of hashes, splits, preprocessing, and scores."""
import csv
from collections import defaultdict
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
KEYS = ('block', 'pairing', 'source_writer', 'founder', 'recipient')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name):
    with (ROOT/'results'/name).open(newline='') as f:
        return list(csv.DictReader(f))


def key(r):
    return (int(r['block']), r['pairing'], r['source_writer'], int(r['founder']), int(r['recipient']))


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12), (a, b)


def mean(x):
    return statistics.fmean(x)


def condition(r):
    return r['pairing']+'/'+r['source_writer']


def main():
    cfg = json.loads((ROOT/'config.json').read_text())
    result = json.loads((ROOT/'results/analysis.json').read_text())
    complete = json.loads((ROOT/'results/COMPLETE.json').read_text())
    start = json.loads((ROOT/'results/START.json').read_text())
    assert complete['status'] == 'COMPLETE'
    assert start['config_sha256'] == complete['config_sha256'] == sha(ROOT/'config.json')
    assert start['protocol_sha256'] == complete['protocol_sha256'] == sha(ROOT/'PROTOCOL.md')
    assert start['code_sha256'] == complete['code_sha256'] == sha(ROOT/'analyze.py')
    assert start['input_bindings'] == cfg['inputs'] == complete['input_bindings']
    for item in cfg['inputs']:
        assert sha(ROOT/cfg['source']/item['path']) == item['sha256'], item['path']
    for name, expected in complete['results_sha256'].items():
        assert sha(ROOT/'results'/name) == expected, name
    for name, field in [('lineage_features.csv', 'lineage_feature_sha256'),
                        ('held_out_predictions.csv', 'prediction_sha256'),
                        ('condition_scores.csv', 'condition_scores_sha256')]:
        assert sha(ROOT/'results'/name) == result[field]
    predictions = read_csv('held_out_predictions.csv')
    feature_rows = read_csv('lineage_features.csv')
    features = {key(r): r for r in feature_rows}
    expected = set(product(cfg['blocks'], cfg['pairings'], cfg['writers'], cfg['founders'], cfg['recipients']))
    assert len(predictions) == len(feature_rows) == len(features) == len(expected)
    assert set(features) == {key(r) for r in predictions} == expected
    condition_names = [p+'/'+w for p in cfg['pairings'] for w in cfg['writers']]
    aggregates, conditional = {}, {}
    for spec in cfg['models']:
        name = spec['id']
        model = result['models'][name]
        columns = [f'g{g}_{n}' for g in spec['generations'] for n in cfg['expression_features']]
        if len(spec['generations']) == 1:
            columns.append('generation_fraction')
        if spec.get('estimator') != 'smoothed_condition_rate':
            columns += (['tolerance_writer', *cfg['pairings'][1:]] if spec['context'] == 'additive'
                        else condition_names[1:])
            if spec['mechanistic']:
                columns += [f'g{g}_{n}' for g in spec['generations'] for n in cfg['mechanistic_features']]
        assert model['columns'] == columns

        def values(r):
            record = {k: float(v) for k, v in r.items() if k.startswith('g')}
            record.update(tolerance_writer=float(r['source_writer'] == 'tolerance_rewrite'))
            record.update({p: float(r['pairing'] == p) for p in cfg['pairings'][1:]})
            record.update({c: float(condition(r) == c) for c in condition_names[1:]})
            if len(spec['generations']) == 1:
                record['generation_fraction'] = spec['generations'][0]/cfg['horizon']
            return [record[c] for c in columns]

        fold_metrics = []
        for fold in model['folds']:
            held = fold['block']
            train = [r for r in feature_rows if int(r['block']) != held]
            test = [r for r in predictions if int(r['block']) == held]
            assert fold['training_blocks'] == [b for b in cfg['blocks'] if b != held]
            fit = fold['fit']
            if columns:
                training_values = [values(r) for r in train]
                means = [mean(column) for column in zip(*training_values)]
                scales = [statistics.pstdev(column) for column in zip(*training_values)]
                scales = [s if s > 1e-12 else 1. for s in scales]
                for a, b in zip(means, fit['mean'], strict=True):
                    close(a, b)
                for a, b in zip(scales, fit['scale'], strict=True):
                    close(a, b)
            briers, losses, by_condition = [], [], defaultdict(list)
            for r in test:
                y = float(r['observed'])
                assert y in (0., 1.) and y == float(features[key(r)]['observed'])
                p, z = float(r[name]), float(r[name+'_logit'])
                assert 0 < p < 1 and math.isfinite(z)
                close(p, 1/(1+math.exp(-z)))
                if columns:
                    x = values(features[key(r)])
                    expected_z = fit['coefficients'][0] + math.fsum(
                        c*(v-m)/s for c, v, m, s in zip(fit['coefficients'][1:], x, fit['mean'], fit['scale'], strict=True))
                    close(z, expected_z)
                else:
                    reference = [t for t in train if condition(t) == condition(r)]
                    successes = sum(float(t['observed']) for t in reference)
                    half = cfg['condition_rate_half_count']
                    close(p, (successes+half)/(len(reference)+2*half))
                brier = (p-y)**2
                loss = max(z, 0)+math.log1p(math.exp(-abs(z)))-y*z
                briers.append(brier)
                losses.append(loss)
                by_condition[condition(r)].append((brier, loss, y))
            assert fold['n'] == len(test)
            assert fold['successes'] == sum(int(r['observed']) for r in test)
            close(fold['brier'], mean(briers))
            close(fold['log_loss'], mean(losses))
            fold_metrics.append((mean(briers), mean(losses)))
            aggregates[name, held] = fold_metrics[-1]
            for c, metrics in by_condition.items():
                conditional[name, held, c] = (len(metrics), sum(m[2] for m in metrics),
                                             mean(m[0] for m in metrics), mean(m[1] for m in metrics))
        close(model['mean_block_brier'], mean(m[0] for m in fold_metrics))
        close(model['mean_block_log_loss'], mean(m[1] for m in fold_metrics))
    for row in read_csv('condition_scores.csv'):
        n, successes, brier, loss = conditional[row['model'], int(row['block']), row['condition']]
        assert int(row['n']) == n and int(row['successes']) == successes
        close(float(row['brier']), brier)
        close(float(row['log_loss']), loss)
    for comparison in result['comparisons']:
        base, cand = comparison['baseline'], comparison['candidate']
        gains = [aggregates[base, b][0]-aggregates[cand, b][0] for b in cfg['blocks']]
        close(comparison['brier_improvement'], mean(gains))
        close(comparison['relative_brier_improvement'], mean(gains)/result['models'][base]['mean_block_brier'])
        close(comparison['log_loss_improvement'], mean(aggregates[base, b][1]-aggregates[cand, b][1] for b in cfg['blocks']))
        assert comparison['blocks_with_lower_brier'] == sum(g > 0 for g in gains)
        for row in comparison['folds']:
            b = row['block']
            close(row['brier_improvement'], aggregates[base, b][0]-aggregates[cand, b][0])
            close(row['log_loss_improvement'], aggregates[base, b][1]-aggregates[cand, b][1])
        for row in comparison['conditions']:
            gains = [conditional[base, b, row['condition']][2]-conditional[cand, b, row['condition']][2]
                     for b in cfg['blocks']]
            close(row['brier_improvement'], mean(gains))
            close(row['log_loss_improvement'], mean(conditional[base, b, row['condition']][3]-conditional[cand, b, row['condition']][3] for b in cfg['blocks']))
            assert row['blocks_with_lower_brier'] == sum(g > 0 for g in gains)
    snapshot_path = ROOT/'snapshot.json'
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text())
        for item in snapshot['files']:
            assert sha(ROOT/item['path']) == item['sha256'], item['path']
        print(f"Verified snapshot: {len(snapshot['files'])} bound files.")
    print('Verified 1024 lineage forecasts, 9 models, 72 whole-block folds, training-only scaling,')
    print('condition rates, prediction reconstruction, independent Brier/log-loss scores, and all calculation hashes.')
    print('Retrospective development; eight exposed blocks; no native dynamics replay.')


if __name__ == '__main__':
    main()
