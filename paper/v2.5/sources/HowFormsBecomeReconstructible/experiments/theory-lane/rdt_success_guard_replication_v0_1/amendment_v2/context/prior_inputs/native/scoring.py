"""Frozen paired block inference and descriptive calibration; no model fitting."""
import math

import numpy as np
from scipy.stats import t

from bridge import P

MODELS = ('candidate', 'direct_rival', 'tt008')
REGIMES = ('matched', 'independent')
MARGINS = {'tt008': .002, 'direct_rival': 0.}


def limits(values, margin):
    values = np.asarray(values, float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError('At least two finite independent block contrasts required')
    mean = float(values.mean()); sd = float(values.std(ddof=1))
    radius = float(t.ppf(.975, len(values)-1)*sd/np.sqrt(len(values)))
    lower, upper = mean-radius, mean+radius
    decision = 'SUPPORTED' if lower > margin else 'REJECTED' if upper <= margin else 'UNRESOLVED'
    return dict(blocks=len(values), mean_gain=mean, sample_sd=sd, lower=lower, upper=upper,
                margin=margin, decision=decision, block_values=values.tolist())


def expected_pairs(spec):
    return {(tuple(key), regime) for key in spec['keys'] for regime in REGIMES}


def checked_rows(forecasts, outcomes, spec):
    expected = expected_pairs(spec)
    def collect(rows, outcome):
        mapping = {}
        for row in rows:
            key = (tuple(row['key']), row['regime'])
            if key in mapping or key not in expected:
                raise ValueError('Duplicate or undeclared record/regime')
            if outcome:
                if row['passed'] not in (0, 1):
                    raise ValueError('Binary terminal task outcome required')
            else:
                if set(row['probabilities']) != set(MODELS):
                    raise ValueError('All three fixed forecasts required')
                if any(not math.isfinite(v) or not 0 <= v <= 1 for v in row['probabilities'].values()):
                    raise ValueError('Finite probabilities in[0,1] required')
            mapping[key] = row
        if set(mapping) != expected:
            raise ValueError('Incomplete cohort: no scientific verdict')
        return mapping
    predictions, labels = collect(forecasts, False), collect(outcomes, True)
    result = []
    for key in spec['keys']:
        for regime in REGIMES:
            item = (tuple(key), regime); row = predictions[item]
            if row['block'] != key[0] or row['history'] != key[1] or row['current_pass'] not in (0, 1):
                raise ValueError('Forecast metadata differs from enrolled record')
            result.append(dict(key=key, block=key[0], history=key[1], current_pass=row['current_pass'],
                regime=regime, y=int(labels[item]['passed']), probabilities=row['probabilities']))
    return result


def analyze(forecasts, outcomes, spec):
    rows = checked_rows(forecasts, outcomes, spec)
    blocks = spec['blocks']; per_block = spec['records_per_block']
    if any(sum(key[0] == b for key in spec['keys']) != per_block for b in blocks):
        raise ValueError('Unequal or incomplete declared block sizes')
    result = dict(scope=spec['scope'], acquisition_blocks=len(blocks), records=len(spec['keys']),
                  case_regimes=len(rows), regimes={}, new_model_fits=0)
    decisions = []
    for regime in REGIMES:
        group = [r for r in rows if r['regime'] == regime]
        bid = np.array([r['block'] for r in group]); y = np.array([r['y'] for r in group])
        ps = {m: np.array([r['probabilities'][m] for r in group]) for m in MODELS}
        losses = {m: (v-y)**2 for m, v in ps.items()}
        scores = {m: float(np.mean([v[bid == b].mean() for b in blocks])) for m, v in losses.items()}
        contrasts = {m: losses[m]-losses['candidate'] for m in MARGINS}
        primary = {m: limits([v[bid == b].mean() for b in blocks], MARGINS[m]) for m, v in contrasts.items()}
        decisions.extend(v['decision'] for v in primary.values())
        calibration = {}
        for m, values in ps.items():
            bins = np.minimum((values*10).astype(int), 9)
            calibration[m] = []
            for i in range(10):
                mask = bins == i; n = int(mask.sum())
                calibration[m].append(dict(bin=i, records=n,
                    mean_prediction=float(values[mask].mean()) if n else None,
                    observed_fraction=float(y[mask].mean()) if n else None,
                    brier=float(losses[m][mask].mean()) if n else None))
        strata = {}
        for label, categories in [('current_pass', (0, 1)), ('history', P['acquisition']['histories'])]:
            strata[label] = {}
            for value in categories:
                mask = np.array([r[label] == value for r in group]); n = int(mask.sum())
                strata[label][str(value)] = dict(records=n, contributing_blocks=len(set(bid[mask])),
                    conditional_brier={m: float(v[mask].mean()) if n else None for m, v in losses.items()},
                    additive_contrasts={m: limits([v[mask & (bid == b)].sum()/per_block for b in blocks], MARGINS[m])
                                        for m, v in contrasts.items()})
                # Stratum intervals describe contributions only. They are never decision gates.
                for item in strata[label][str(value)]['additive_contrasts'].values():
                    item.pop('decision'); item.pop('margin')
        result['regimes'][regime] = dict(scores=scores, primary=primary, calibration=calibration, strata=strata)
    result['decision'] = ('ALL_FOUR_ADVANTAGES_SUPPORTED' if all(v == 'SUPPORTED' for v in decisions)
        else 'AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in decisions else 'UNRESOLVED')
    result['interpretation'] = ('Synthetic qualification fixture only; no scientific inference.' if spec['scope'] != 'scientific'
        else 'Fixed ordinary predictor comparison. Joint support is an intersection-union claim; component intervals are not simultaneous. No RDT-specific novelty or general law follows.')
    return result


def report(result):
    lines = ['# Fixed successor forecast: prospective outcome comparison', '',
             '**'+result['decision']+'**. '+result['interpretation'], '',
             '| Regime | Rival | Mean Brier gain | Lower limit | Upper limit | Required margin | Decision |',
             '|---|---|---:|---:|---:|---:|---|']
    for regime, values in result['regimes'].items():
        for rival, row in values['primary'].items():
            lines.append(f"| {regime} | {rival} | {row['mean_gain']:.8f} | {row['lower']:.8f} | {row['upper']:.8f} | {row['margin']:.3f} | {row['decision']} |")
    lines += ['', f"Complete cohort: {result['acquisition_blocks']} acquisition blocks, {result['records']} records, {result['case_regimes']} record/regime outcomes. No fitting or recalibration.", '',
        'Predictors, probes, decisions and complete-cohort forecasts were fixed before new continuation outcomes. The resource cap increased explicitly from 256 to 304 blocks under amendment 1; the parent feasibility failure remains recorded. Planning rests on eight exposed blocks and does not guarantee power under the independent-noise shift.', '',
        'The endpoint is a fresh terminal recipient after 18 rewrites. It is distinct from uninterrupted success. Calibration bins and both current-expression/history strata are reported in ANALYSIS.json; they do not rescue a failed primary comparison.', '']
    return '\n'.join(lines)
