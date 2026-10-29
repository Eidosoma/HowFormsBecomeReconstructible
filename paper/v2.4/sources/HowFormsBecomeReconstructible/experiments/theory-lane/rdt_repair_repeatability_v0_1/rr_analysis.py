"""Cross-replicate conditional-effect variance, without clipping or fitting."""
from collections import Counter
import itertools
import numpy as np
from scipy.stats import t
from rr_common import C, REGIMES, MODELS, require


def statistics_of(d, weights):
    d, weights = np.asarray(d, float), np.asarray(weights, float)
    require(d.ndim == 2 and d.shape[0] == len(weights) and d.shape[1] >= 2, 'Repeated observations required')
    require(np.isfinite(d).all() and np.isfinite(weights).all() and np.all(weights > 0) and abs(weights.sum() - 1) < 1e-12, 'Finite normalized weights required')
    means = weights @ d
    pairs = [float(weights @ (d[:, r] * d[:, s]) - means[r] * means[s])
             for r, s in itertools.combinations(range(d.shape[1]), 2)]
    return dict(variance=float(np.mean(pairs)), future_noise=float(weights @ d.var(axis=1, ddof=1)),
                mean_benefit=float(np.mean(means)), replicate_means=means.tolist(), pair_covariances=pairs)


def interval(value, se, blocks):
    radius = float(t.ppf(.975, blocks - 1)) * se
    return dict(estimate=float(value), standard_error=float(se), lower=float(value-radius), upper=float(value+radius),
                zero_variance_caution=bool(se == 0))


def block_interval(values):
    a = np.asarray(values, float)
    return dict(**interval(float(a.mean()), float(a.std(ddof=1)/np.sqrt(len(a))), len(a)), block_values=a.tolist())


def analyze(rows, forecasts, outcomes):
    keys = [tuple(r['key']) for r in rows]
    blocks = sorted({r['block'] for r in rows})
    reps = C['cohort']['new_replicates']
    require(len(set(keys)) == len(keys) and len(blocks) >= 2, 'Unique cohort and multiple blocks required')
    labels = {(tuple(o['key']), o['regime'], o['replicate']): o for o in outcomes}
    expected = {(k, g, r) for k in keys for g in REGIMES for r in reps}
    require(len(labels) == len(outcomes) == len(expected) and set(labels) == expected, 'Incomplete or duplicated replicate set')
    pred = {(tuple(f['key']), f['regime']): f['probabilities'] for f in forecasts}
    require(len(pred) == len(forecasts) == 2*len(rows) and set(pred) == {(k,g) for k in keys for g in REGIMES}, 'Forecast coverage')
    counts = Counter((r['block'], r['current_pass']) for r in rows)
    require(all(counts[b, c] > 0 for b in blocks for c in (0, 1)), 'Missing current-expression class')
    weights = np.array([1/(2*len(blocks)*counts[r['block'], r['current_pass']]) for r in rows])
    result = dict(records=len(rows), acquisition_blocks=len(blocks), replicates=len(reps), regimes={})
    for regime in REGIMES:
        control = np.array([[labels[k, regime, rep]['control'] for rep in reps] for k in keys])
        repaired = np.array([[labels[k, regime, rep]['repaired'] for rep in reps] for k in keys])
        require(np.isin(control, (0,1)).all() and np.isin(repaired, (0,1)).all(), 'Binary paired outcomes required')
        d = repaired - control
        stats = statistics_of(d, weights)
        leave = []
        block_benefit = []
        masks = [np.array([r['block'] == b for r in rows]) for b in blocks]
        for b, mask in zip(blocks, masks, strict=True):
            w = weights[~mask] / weights[~mask].sum()
            leave.append(dict(block=b, variance=statistics_of(d[~mask], w)['variance']))
            block_benefit.append(float(weights[mask] @ d[mask].mean(axis=1) * len(blocks)))
        values = np.array([v['variance'] for v in leave])
        se = float(np.sqrt((len(blocks)-1)/len(blocks) * np.square(values-values.mean()).sum()))
        uncertainty = interval(stats['variance'], se, len(blocks))
        signal = 'REPEATABILITY_SIGNAL' if se > 0 and uncertainty['lower'] > 0 else 'UNRESOLVED'
        event_conditions = dict(rescue=(d == 1), harm=(d == -1), both_pass=(control == 1)&(repaired == 1), neither_pass=(control == 0)&(repaired == 0))
        events = {name: dict(count=int(a.sum()), fraction=float(weights @ a.mean(axis=1))) for name,a in event_conditions.items()}
        forecast_scores = {}
        losses = {}
        for model in MODELS:
            probabilities = np.array([pred[k, regime][model] for k in keys])
            require(np.isfinite(probabilities).all() and np.all((probabilities >= 0)&(probabilities <= 1)), 'Valid fixed forecast required')
            losses[model] = ((control - probabilities[:, None])**2).mean(axis=1)
            bv = [float(weights[m] @ losses[model][m] * len(blocks)) for m in masks]
            forecast_scores[model] = dict(**block_interval(bv), extra_native_probes=C['costs']['extra_frozen_probe_reads_per_record_regime'][model])
        gains = {}
        for rival in ('tt008','direct_rival'):
            differences = losses[rival] - losses['candidate']
            gains[rival+'_minus_successor'] = block_interval([float(weights[m] @ differences[m] * len(blocks)) for m in masks])
        result['regimes'][regime] = dict(**stats, primary=uncertainty, signal=signal, leave_one_block=leave,
            mean_benefit_interval=block_interval(block_benefit), events=events,
            control_success=float(weights @ control.mean(axis=1)), repair_success=float(weights @ repaired.mean(axis=1)),
            packets=[dict(key=list(k), weight=float(weights[i]), differences=d[i].tolist(), mean_benefit=float(d[i].mean()), sample_variance=float(d[i].var(ddof=1))) for i,k in enumerate(keys)],
            control_forecasts=forecast_scores, control_forecast_gains=gains)
    result['signal'] = 'BOTH_REGIMES_REPEATABILITY_SIGNAL' if all(result['regimes'][g]['signal'] == 'REPEATABILITY_SIGNAL' for g in REGIMES) else 'UNRESOLVED'
    return result


def report(result, costs):
    lines = ['**Repeated paired repair benefit: development measurement.**', '', '**'+result['signal']+'**. Four new futures on each of 63 exposed packets; sixteen acquisition blocks. No new founders, fitted models or policy evaluation.', '',
             '| Noise | Between-packet variance estimate | Descriptive 95% interval | Single-future noise estimate | Repeatability |', '|---|---:|---|---:|---|']
    for regime, value in result['regimes'].items():
        q=value['primary']
        lines.append(f"| {regime} | {q['estimate']:.8f} | [{q['lower']:.8f}, {q['upper']:.8f}] | {value['future_noise']:.8f} | {value['signal']} |")
    lines += ['', 'The cross-products use distinct future streams. Negative estimates are retained and do not imply negative true variance. Delete-block jackknife intervals are approximate diagnostics across selected acquisition blocks, not exact fixed-panel uncertainty or calibrated confirmation. An unresolved result does not establish homogeneous repair benefit.', '', '| Noise | No-repair success | Repair success | Mean paired benefit | Descriptive 95% interval | Rescues | Harms |', '|---|---:|---:|---:|---|---:|---:|']
    for regime,value in result['regimes'].items():
        q=value['mean_benefit_interval']; e=value['events']
        lines.append(f"| {regime} | {value['control_success']:.6f} | {value['repair_success']:.6f} | {q['estimate']:.6f} | [{q['lower']:.6f}, {q['upper']:.6f}] | {e['rescue']['count']} | {e['harm']['count']} |")
    lines += ['', 'Success and benefit are block/class weighted; counts are raw across all four repeats. Rescue/harm frequencies depend on the specified common-disturbance pairing, while expected signed benefit has the ordinary branch marginals. Repeats do not supply new independent founders.', '', '| Fixed control forecast | Matched Brier | Independent Brier | Extra native probes per packet/regime |', '|---|---:|---:|---:|']
    for model in MODELS:
        a=result['regimes']['matched']['control_forecasts'][model]; b=result['regimes']['independent']['control_forecasts'][model]
        lines.append(f"| {model} | {a['estimate']:.8f} | {b['estimate']:.8f} | {a['extra_native_probes']} |")
    lines += ['', 'TT008 is the ordinary predictor, direct_rival the direct-probe predictor, and candidate the existing successor-risk predictor. The failed packet-benefit predictor is not fitted or evaluated here. These cached risk forecasts are secondary; all acquisition-block scores and paired forecast contrasts are retained in ANALYSIS.json. Shared boundary acquisition, transfer, stored apparatus and forecast arithmetic are additional costs. Reusing cached probes is not zero historical cost.', '',
        f"Workload: {costs['primary_native_reads']:,} primary native reads; {costs['flat_native_reads']:,} flat audit reads; {costs['physical_repair_calls']} physical repairs reused across {costs['logical_repaired_branches']} repaired continuations. Historical cached probing: {costs['cached_historical_probe_reads']:,} reads. No new probes, acquisition, model fits or automatic successor.", '',
        'Every continuation is retained with coupled forcing commitments, its own rewritten packet chain, two-arm flat checks on a hash-selected packet in every block/regime/repeat, and independently checked endpoints. A separate scalar implementation checks the cross-products, within-packet variances, block deletion, events and forecast scores.', '',
        'The experiment measures conventional intervention-effect repeatability in an externally supplied reconstruction apparatus. It establishes no RDT-specific predictive law, autonomous maintenance, new-founder generalization or qualified scheduler.', '']
    return '\n'.join(lines)
