"""Separate scalar scoring and feature calculations; no simulator replay claim."""
import math
import numpy as np


def check(data, result, predictions, fold, plan, feature_function, probe_function):
    groups = sorted(set(data.groups.tolist()))
    expected_fold = np.array([groups.index(int(g)) % 4 for g in data.groups])
    np.testing.assert_array_equal(fold, expected_fold)
    for item in result['fits']:
        tr, te = set(item['training_blocks']), set(item['evaluation_blocks'])
        if tr & te or tr | te != set(groups):
            raise ValueError('Outer split contamination')
        if te != {g for i, g in enumerate(groups) if i % 4 == item['fold']}:
            raise ValueError('Incorrect evaluation split')
    checked = 0
    for key, p in predictions.items():
        cutoff, endpoint, _ = key.split('.')
        k = int(cutoff[1:])
        expected_y = []
        for i in range(len(p)):
            value = bool(data.terminal[i])
            if endpoint == 'future_path_and_terminal':
                value = value and all(bool(x) for x in data.body[i, k:])
            expected_y.append(int(value))
        by_block, ll_by_block = [], []
        for g in groups:
            rows = [i for i, owner in enumerate(data.groups) if owner == g]
            by_block.append(sum((expected_y[i]-float(p[i]))**2 for i in rows)/len(rows))
            score = 0.
            for i in rows:
                prob = min(1-1e-6, max(1e-6, float(p[i])))
                score -= math.log(prob if expected_y[i] else 1-prob)
            ll_by_block.append(score/len(rows))
        saved = result['scores'][key]
        np.testing.assert_allclose(saved['block_brier'], by_block, rtol=0, atol=1e-14)
        np.testing.assert_allclose(saved['block_log_loss'], ll_by_block, rtol=0, atol=1e-12)
        np.testing.assert_allclose(saved['brier'], sum(by_block)/len(groups), rtol=0, atol=1e-14)
        np.testing.assert_allclose(saved['log_loss'], sum(ll_by_block)/len(groups), rtol=0, atol=1e-12)
        for j, item in enumerate(saved['calibration_bins']):
            idx = [i for i, prob in enumerate(p) if j/10 <= prob and (prob < (j+1)/10 if j < 9 else prob <= 1)]
            if item['count'] != len(idx):
                raise ValueError('Calibration bin count mismatch')
            if idx:
                np.testing.assert_allclose(item['observed'], sum(expected_y[i] for i in idx)/len(idx), atol=1e-14)
                np.testing.assert_allclose(item['predicted'], sum(float(p[i]) for i in idx)/len(idx), atol=1e-14)
        checked += len(p)
    for k in plan['prefixes']:
        p = probe_function(data, k)
        x = feature_function(p, 'prefix_logistic')
        # All lineage/column means and slopes recomputed from explicit lists.
        for i in range(len(p.groups)):
            row = list(data.features[i, k-1])
            means, slopes = [], []
            for c in range(24):
                times = [t+1 for t in range(k) if data.observed[i, t, c]]
                values = [float(data.features[i, t-1, c]) for t in times]
                avg, tavg = sum(values)/len(values), sum(times)/len(times)
                den = sum((t-tavg)**2 for t in times)
                means.append(avg)
                slopes.append(sum((t-tavg)*(v-avg) for t, v in zip(times, values))/den if den else 0.)
            streak = 0
            for t in range(k-1, -1, -1):
                if data.body[i, t]:
                    break
                streak += 1
            row += means+slopes+[min(data.features[i, :k, 5]),
                sum(not bool(v) for v in data.body[i, :k])/k, streak]
            np.testing.assert_allclose(x[i], row, rtol=1e-12, atol=1e-12)
    # Recompute all fixed bootstrap contrasts separately.
    draws = np.random.default_rng(plan['random_seed']).integers(0, len(groups),
                                                             (plan['bootstrap_draws'], len(groups)))
    for key, item in result['scores'].items():
        k, endpoint, _ = key.split('.')
        baseline = result['scores'][f'{k}.{endpoint}.prevalence']['block_brier']
        differences = np.array([a-b for a, b in zip(baseline, item['block_brier'])])
        means = np.array([sum(differences[j] for j in row)/len(groups) for row in draws])
        np.testing.assert_allclose(item['brier_gain_over_prevalence']['descriptive_interval'],
                                   np.quantile(means, [.025, .975]), rtol=0, atol=1e-14)
    return dict(status='PASS', prediction_scores_checked=checked,
                feature_rows_checked=len(data.groups)*len(plan['prefixes']),
                scope='Separate feature/scoring/split arithmetic; original simulator and sklearn solvers not independently reimplemented.')
