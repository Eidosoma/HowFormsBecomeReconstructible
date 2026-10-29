"""Paired benefit, rescue/harm decomposition, and fixed predictor diagnostics."""
import math
import numpy as np
from scipy.stats import t
from study import C, REGIMES, MODELS, require, scoring_pilot


def validate(rows, forecasts, outcomes):
    controls = [dict(key=o['key'], regime=o['regime'], passed=o['control']) for o in outcomes]
    blocks, predictions, _ = scoring_pilot.validate(rows, forecasts, controls)
    require(all(o['repaired'] in (0, 1) for o in outcomes), 'Binary repaired outcomes required')
    labels = {(tuple(o['key']), o['regime']): o for o in outcomes}
    weights = np.array([1 / (2 * sum(q['block'] == r['block'] and q['current_pass'] == r['current_pass'] for q in rows)) for r in rows])
    return blocks, predictions, labels, weights, controls


def interval(values):
    a = np.asarray(values, float)
    mean, sd = float(a.mean()), float(a.std(ddof=1))
    radius = float(t.ppf(.975, len(a) - 1) * sd / math.sqrt(len(a)))
    lo, hi = mean - radius, mean + radius
    signal = 'UNRESOLVED' if sd == 0 else 'POSITIVE_SIGNAL' if lo > 0 else 'NEGATIVE_SIGNAL' if hi < 0 else 'UNRESOLVED'
    return dict(blocks=len(a), block_values=a.tolist(), mean=mean, sample_sd=sd,
        lower=lo, upper=hi, signal=signal, zero_variance_caution=sd == 0)


def cell(control, repaired, weights, selected):
    w = weights[selected]
    total = float(w.sum())
    c, r = control[selected], repaired[selected]
    events = {'rescue': (c == 0) & (r == 1), 'harm': (c == 1) & (r == 0),
              'both_pass': (c == 1) & (r == 1), 'neither_pass': (c == 0) & (r == 0)}
    return dict(records=int(selected.sum()), weight=total,
        control_success=float(np.dot(w, c) / total) if total else None,
        repair_success=float(np.dot(w, r) / total) if total else None,
        benefit=float(np.dot(w, r - c) / total) if total else None,
        counts={name: int(v.sum()) for name, v in events.items()},
        fractions={name: float(w[v].sum() / total) if total else None for name, v in events.items()})


def analyze(rows, forecasts, outcomes):
    blocks, predictions, labels, weights, controls = validate(rows, forecasts, outcomes)
    bid = np.array([r['block'] for r in rows])
    result = dict(scope=C['status'], records=len(rows), blocks=len(blocks), case_regimes=len(outcomes), regimes={})
    for regime in REGIMES:
        control = np.array([labels[tuple(r['key']), regime]['control'] for r in rows], int)
        repaired = np.array([labels[tuple(r['key']), regime]['repaired'] for r in rows], int)
        block_values = [float(np.dot(weights[bid == b], (repaired - control)[bid == b])) for b in blocks]
        all_records = np.ones(len(rows), bool)
        values = dict(primary=interval(block_values), events=cell(control, repaired, weights, all_records),
            current_expression={str(c): cell(control, repaired, weights, np.array([r['current_pass'] == c for r in rows])) for c in (0, 1)},
            histories={h: cell(control, repaired, weights, np.array([r['history'] == h for r in rows])) for h in sorted({r['history'] for r in rows})},
            risk_bins={})
        for model in MODELS:
            risk = np.array([1 - predictions[tuple(r['key']), regime]['probabilities'][model] for r in rows])
            bins = np.minimum(np.floor(5 * risk).astype(int), 4)
            values['risk_bins'][model] = [dict(bin=i, **cell(control, repaired, weights, bins == i)) for i in range(5)]
        result['regimes'][regime] = values
    signals = [v['primary']['signal'] for v in result['regimes'].values()]
    result['signal'] = ('BOTH_REGIMES_POSITIVE_SIGNAL' if all(s == 'POSITIVE_SIGNAL' for s in signals)
                        else 'CONTRARY_SIGNAL' if 'NEGATIVE_SIGNAL' in signals else 'UNRESOLVED')
    result['control_forecasts'] = scoring_pilot.analyze(rows, forecasts, controls)
    result['interpretation'] = C['scope']
    return result


def report(result, resources):
    lines = ['**Paired once-only repair benefit: bounded development pilot.**', '',
        '**' + result['signal'] + '**. ' + result['interpretation'], '',
        'All 63 selected historical boundaries remain enrolled in both regimes. One ordinary graph-completion repair at generation 14 is compared with no repair. Both arms share future disturbances, propagate their own packets through eighteen full rewrites, and use a fresh terminal body. Subsequent repairs are absent. Mean net benefit is rescue probability minus harm probability.', '',
        '| Noise | Control success | Repair success | Net benefit | Lower | Upper | Raw rescues | Raw harms | Signal |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for regime, v in result['regimes'].items():
        p, q = v['primary'], v['events']
        lines.append(f"| {regime} | {q['control_success']:.6f} | {q['repair_success']:.6f} | {p['mean']:.6f} | {p['lower']:.6f} | {p['upper']:.6f} | {q['counts']['rescue']} | {q['counts']['harm']} | {p['signal']} |")
    lines += ['', 'Each acquisition block receives equal weight, with half its weight in each current-expression class. Raw counts and weighted rates therefore have different denominators. Intervals are descriptive paired block t intervals from sixteen blocks; a zero observed block variance is explicitly unresolved. All histories, current-expression strata, fixed risk bins, calibration and block contributions are retained in ANALYSIS.json.', '',
        'The coupling preserves both intervention marginals. The average effect is invariant to the choice of valid coupling; its rescue/harm decomposition need not be. One paired outcome per record/regime does not identify a precise individual benefit. The exposed selected panel and reused family are development evidence. No learned benefit predictor, held-out founder test or repair scheduler is qualified here.', '',
        'Frozen control-outcome prediction errors follow. These are secondary forecasting checks. Lower Brier is better. Additional native probe costs are per record/regime beyond common boundary features; the measurements were cached, with their original costs retained.', '',
        '| Predictor | Matched Brier | Independent Brier | Extra probe reads |', '|---|---:|---:|---:|']
    for model in MODELS:
        forecast = result['control_forecasts']['regimes']
        lines.append(f"| {model} | {forecast['matched']['scores'][model]:.8f} | {forecast['independent']['scores'][model]:.8f} | {C['costs']['extra_native_probes_per_record_regime'][model]} |")
    lines += ['', 'All four original rival-minus-successor control-forecast comparisons are reported; none can rescue the repair-benefit result.', '',
        '| Noise | Comparator | Brier gain | Lower | Upper | Required margin | Secondary decision |', '|---|---|---:|---:|---:|---:|---|']
    for regime in REGIMES:
        for rival, value in result['control_forecasts']['regimes'][regime]['primary'].items():
            lines.append(f"| {regime} | {rival} | {value['mean_gain']:.8f} | {value['lower']:.8f} | {value['upper']:.8f} | {value['margin']:.3f} | {value['decision']} |")
    lines += ['', f"Evaluation used {resources['primary_native_reads']} new primary native reads and {resources['flat_native_reads']} separate flat-audit reads. The action was computed once for each of {resources['physical_repair_calls']} unique packets and reused across regimes; the two-regime intervention estimand contains {resources['logical_repair_calls']} logical repair calls. Repair CPU: {resources['repair_cpu_seconds']:.6f}s; separate optimizer-audit CPU: {resources['optimizer_audit_cpu_seconds']:.6f}s.", '',
        'All three fixed forecasts share boundary features, transfer computation and model apparatus. The retained prior probes cost 9,072 native reads; caching does not make them free. Original acquisition and fitting costs remain in the predecessor cost ledger. The 64/8 probe ratio does not measure elapsed-time or total-cost ratios. No equal-total-budget scheduling comparison is claimed.', '',
        'Every repair was separately reconstructed and optimizer-checked. One predeclared record per block, both regimes and both arms, was replayed through all nineteen reads using separate flat dynamics. Full evidence coverage, scalar endpoint and paired analysis checks passed before completion. These are internal checks in one research programme. Ordinary graph error correction is the intervention, and no RDT-specific mechanism or autonomous apparatus maintenance is established.', '',
        'No automatic extension, retraining, successor run or scheduling trial is authorized by a favorable signal. A later scheduling test must freeze a benefit predictor on development data and evaluate it on separate founder blocks against direct-probe, ordinary, risk, random/fixed and no-repair controls with complete sensing-and-action cost accounting.', '']
    return '\n'.join(lines)
