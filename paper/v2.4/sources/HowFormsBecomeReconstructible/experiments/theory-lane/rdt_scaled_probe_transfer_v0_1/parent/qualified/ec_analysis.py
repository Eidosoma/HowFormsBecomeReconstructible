"""Whole-cohort development scores; all five fixed rivals remain visible."""
import math
import statistics

import numpy as np
from scipy.stats import t

from ec_common import require
from ec_source import D


def validate(rows, forecasts, outcomes, expected_blocks, expected_packets):
    keys = [tuple(r['key']) for r in rows]
    blocks = sorted({r['block'] for r in rows})
    require(len(rows) == expected_packets and len(set(keys)) == len(keys) and len(blocks) == expected_blocks,
            'Complete unique cohort required; no partial inference')
    for b in blocks:
        for c in (0, 1):
            require(1 <= sum(r['block'] == b and r['current_pass'] == c for r in rows) <= 2,
                    'Both current-expression classes required')
    fm = {(tuple(f['key']), f['regime']): f for f in forecasts}
    ym = {(tuple(y['key']), y['regime'], y['replicate']): y for y in outcomes}
    require(len(fm) == len(forecasts) and set(fm) == {(k, g) for k in keys for g in D['regimes']}, 'Complete unique forecasts required')
    require(len(ym) == len(outcomes) and set(ym) == {(k, g, r) for k in keys for g in D['regimes'] for r in D['repeats']}, 'Complete four-repeat outcomes required')
    require(all(y['passed'] in (0, 1) for y in outcomes), 'Binary outcomes required')
    for row in rows:
        for g in D['regimes']:
            f = fm[(tuple(row['key']), g)]
            require(all(f.get(k) == v for k, v in row.items()), 'Forecast boundary metadata differs')
            require(set(f['probabilities']) == set(D['models']) and
                    all(math.isfinite(p) and 0 <= p <= 1 for p in f['probabilities'].values()), 'Five finite fixed probabilities required')
    return blocks, fm, ym


def analyze(rows, forecasts, outcomes, expected_blocks=None, expected_packets=None):
    blocks, fm, ym = validate(rows, forecasts, outcomes,
        D['blocks'] if expected_blocks is None else expected_blocks,
        D['packets'] if expected_packets is None else expected_packets)
    require(len(blocks) >= 2, 'Block variation requires at least two blocks')
    result = dict(scope='EXPOSED_DEVELOPMENT_ONLY', decision='NO_NEW_CONFIRMATORY_VERDICT',
        blocks=len(blocks), packets=len(rows), saved_outcomes=len(outcomes), new_fits=0,
        new_scientific_outcomes=0, inference_unit='acquisition block', regimes={})
    joint, names = [], []
    for regime in D['regimes']:
        block_losses = {m: [] for m in D['models']}
        observed = []
        strata = {str(c): {m: [] for m in D['models']} for c in (0, 1)}
        for b in blocks:
            by_class, observed_class = [], []
            for c in (0, 1):
                enrolled = [r for r in rows if r['block'] == b and r['current_pass'] == c]
                y = np.array([[ym[(tuple(r['key']), regime, rep)]['passed'] for rep in D['repeats']] for r in enrolled])
                by_class.append({m: float(np.mean((np.array([fm[(tuple(r['key']), regime)]['probabilities'][m] for r in enrolled])[:, None] - y) ** 2)) for m in D['models']})
                observed_class.append(float(y.mean()))
                for m in D['models']:
                    strata[str(c)][m].append(by_class[-1][m])
            for m in D['models']:
                block_losses[m].append((by_class[0][m] + by_class[1][m]) / 2)
            observed.append(sum(observed_class) / 2)
        contrasts = {}
        for rival in D['models']:
            if rival == 'successor32':
                continue
            gain = np.array(block_losses[rival]) - np.array(block_losses['successor32'])
            mean, sd = float(gain.mean()), float(gain.std(ddof=1))
            radius = float(t.ppf(.975, len(blocks) - 1) * sd / np.sqrt(len(blocks)))
            contrasts[rival] = dict(mean_gain=mean, sample_sd=sd, descriptive_lower=mean - radius,
                descriptive_upper=mean + radius, block_gains=gain.tolist(),
                interpretation='Positive favors successor32. Exposed-data planning diagnostic; no significance gate.')
            joint.append(gain)
            names.append(regime + '/' + rival)
        result['regimes'][regime] = dict(block_ids=blocks, block_losses=block_losses,
            brier={m: float(np.mean(v)) for m, v in block_losses.items()},
            observed_success=float(np.mean(observed)), contrasts=contrasts,
            current_expression_brier={c: {m: float(np.mean(v)) for m, v in values.items()} for c, values in strata.items()})
    result['planning_covariance'] = dict(order=names, sample_covariance=np.cov(np.stack(joint), ddof=1).tolist(),
        warning='Conditional development estimate; effect uncertainty and new-cohort costs must be addressed before any fresh sample size is fixed.')
    return result


def scalar_check(rows, forecasts, outcomes, result):
    """Separate scalar aggregation, including unequal class sizes and futures."""
    fm = {(tuple(f['key']), f['regime']): f for f in forecasts}
    ym = {(tuple(y['key']), y['regime'], y['replicate']): y['passed'] for y in outcomes}
    blocks = sorted({r['block'] for r in rows})
    for g in D['regimes']:
        independent = {m: [] for m in D['models']}
        for b in blocks:
            for m in D['models']:
                means = []
                for c in (0, 1):
                    packet_losses = []
                    for r in rows:
                        if r['block'] == b and r['current_pass'] == c:
                            p = fm[(tuple(r['key']), g)]['probabilities'][m]
                            packet_losses.append(math.fsum((p - ym[(tuple(r['key']), g, rep)]) ** 2 for rep in D['repeats']) / len(D['repeats']))
                    means.append(math.fsum(packet_losses) / len(packet_losses))
                independent[m].append(math.fsum(means) / 2)
        saved = result['regimes'][g]
        for m in D['models']:
            require(max(abs(a - b) for a, b in zip(independent[m], saved['block_losses'][m], strict=True)) < 1e-12 and
                    abs(statistics.mean(independent[m]) - saved['brier'][m]) < 1e-12, 'Independent individual-loss weighting differs')
            if m != 'successor32':
                gain = [a - b for a, b in zip(independent[m], independent['successor32'], strict=True)]
                radius = float(t.ppf(.975, len(blocks) - 1)) * statistics.stdev(gain) / math.sqrt(len(blocks))
                check = saved['contrasts'][m]
                for key, expected in [('mean_gain', statistics.mean(gain)), ('sample_sd', statistics.stdev(gain)),
                    ('descriptive_lower', statistics.mean(gain) - radius), ('descriptive_upper', statistics.mean(gain) + radius)]:
                    require(abs(check[key] - expected) < 1e-12, 'Independent paired contrast differs')
    return dict(status='PASS', blocks=len(blocks), five_models=True, individual_future_losses=True, contrasts=8)
