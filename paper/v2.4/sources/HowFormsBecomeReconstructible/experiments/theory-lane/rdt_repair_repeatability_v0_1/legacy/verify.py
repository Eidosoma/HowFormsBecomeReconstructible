"""Independent scalar endpoints and analysis, plus committed chain checks."""
from collections import Counter
import math
import statistics
import numpy as np
from scipy.stats import t
from study import C, ARMS, REGIMES, MODELS, ev, read, digest, require, independent_arithmetic, audit_pilot


def near(a, b):
    require(math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-12, 'Scalar arithmetic disagreement')


def continuation(folder, rows, initial, regime, stage, seal_sha, audit_key):
    receipt = read(folder / 'future.json')
    raw = independent_arithmetic.load(folder / 'future.npz')
    outcomes = read(folder / 'OUTCOMES.json')
    require(ev.sha(folder / 'future.npz') == receipt['raw_sha256'], 'Future raw hash differs')
    require(receipt['keys'] == [r['key'] for r in rows] and receipt['arms'] == list(ARMS), 'Future enrollment/arms differ')
    require(receipt['regime'] == regime and receipt['stage'] == stage and receipt['seal_sha256'] == seal_sha, 'Future binding differs')
    require(raw['generations'].tolist() == list(range(15, 34)), 'Wrong full native horizon')
    require(raw['incoming'].shape == (19, len(rows), 2, 2, 16, 16), 'Wrong paired chain shape')
    require(raw['windows'].shape == (19, len(rows), C['reader']['observe_steps'], 2, 2, 2), 'Wrong paired response shape')
    for a, b in ((raw['initial_packets'], initial), (raw['incoming'][0], initial),
                 (raw['incoming'][1:], raw['outgoing'][:-1]),
                 (raw['g32_packets'], raw['outgoing'][-2]), (raw['g32_packets'], raw['incoming'][-1])):
        require(a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), 'Broken own-state rewrite chain')
    require(len(outcomes) == len(rows), 'Incomplete paired labels')
    for index, row in enumerate(rows):
        require(digest(initial[index, 0]) == row['packet_sha256'], 'Wrong control starting packet')
        value = outcomes[index]
        require(value['key'] == row['key'] and value['regime'] == regime, 'Wrong paired label identity')
        for arm, label, margin in ((0, 'control', 'control_margin'), (1, 'repaired', 'repair_margin')):
            aligned = []
            for cue in range(2):
                for port in range(2):
                    mean = math.fsum(raw['windows'][-1, index, :, arm, cue, port]) / C['reader']['observe_steps']
                    signed = mean * row['rule'] * (1 if cue == port else -1)
                    near(signed, raw['terminal_aligned'][index, arm, cue, port])
                    aligned.append(signed)
            minimum = min(aligned)
            near(minimum, value[margin]); near(minimum, raw['terminal_margin'][index, arm])
            require(int(minimum > .25) == value[label] == raw['terminal_passed'][index, arm], 'Wrong paired endpoint')
    require(receipt['primary_native_reads'] == 38 * len(rows) and receipt['flat_native_reads'] == 38, 'Wrong paired read costs')
    expected = [dict(key=audit_key, generation=g, arms=list(ARMS), byte_exact=True) for g in range(15, 34)]
    require(receipt['audits'] == expected, 'Flat audit coverage mismatch')
    require(np.all(raw['mask'].sum(axis=(-2, -1)) == 24), 'Wrong injury count')
    require(len(receipt['forcing']) == 19 * len(rows), 'Forcing count mismatch')
    for gi, g in enumerate(range(15, 34)):
        for j, row in enumerate(rows):
            r = receipt['forcing'][gi * len(rows) + j]
            require(r['key'] == row['key'] and r['generation'] == g and r['purpose'] == ('writer' if g < 33 else 'evaluation'), 'Forcing identity mismatch')
            for name in ('mask', 'birth'):
                require(digest(raw[name][gi, j]) == r['sha256'][name], 'Forcing hash mismatch')
    return dict(status='PASS', paired_terminal_records=len(rows), branches=2, flat_native_reads=38)


def evaluate(rows, forecasts, outcomes, result):
    blocks = sorted({r['block'] for r in rows})
    keys = [tuple(r['key']) for r in rows]
    expected = {(key, regime) for key in keys for regime in REGIMES}
    labels = {(tuple(r['key']), r['regime']): r for r in outcomes}
    pred = {(tuple(r['key']), r['regime']): r['probabilities'] for r in forecasts}
    require(len(set(keys)) == len(keys) and len(labels) == len(outcomes) == len(expected) and set(labels) == expected and set(pred) == expected, 'Independent paired coverage check failed')
    count = Counter((r['block'], r['current_pass']) for r in rows)
    require(all(count[b, c] > 0 for b in blocks for c in (0, 1)), 'Missing block class')
    weights = {tuple(r['key']): 1 / (2 * count[r['block'], r['current_pass']]) for r in rows}
    def check_cell(group, regime, saved):
        weight = math.fsum(weights[tuple(r['key'])] for r in group)
        require(saved['records'] == len(group), 'Cell record count')
        near(weight, saved['weight'])
        sums = {k: [] for k in ('control_success', 'repair_success', 'benefit', 'rescue', 'harm', 'both_pass', 'neither_pass')}
        events = Counter()
        for row in group:
            key = tuple(row['key']); record = labels[key, regime]
            c, a = record['control'], record['repaired']; w = weights[key]
            require(c in (0, 1) and a in (0, 1), 'Nonbinary paired outcome')
            category = {(0, 0): 'neither_pass', (0, 1): 'rescue', (1, 0): 'harm', (1, 1): 'both_pass'}[c, a]
            events[category] += 1
            sums[category].append(w)
            for name, value in (('control_success', c), ('repair_success', a), ('benefit', a - c)):
                sums[name].append(w * value)
        for name, values in sums.items():
            value = math.fsum(values) / weight if weight else None
            target = saved[name] if name in ('control_success', 'repair_success', 'benefit') else saved['fractions'][name]
            if value is None: require(target is None, 'Empty cell must remain undefined')
            else: near(value, target)
        require(saved['counts'] == {k: events[k] for k in ('rescue', 'harm', 'both_pass', 'neither_pass')}, 'Rescue/harm count mismatch')
        if weight: near(saved['benefit'], saved['fractions']['rescue'] - saved['fractions']['harm'])
    signals = []
    for regime in REGIMES:
        saved = result['regimes'][regime]
        block_values = []
        for b in blocks:
            class_means = []
            for current in (0, 1):
                group = [r for r in rows if r['block'] == b and r['current_pass'] == current]
                differences = [labels[tuple(r['key']), regime]['repaired'] - labels[tuple(r['key']), regime]['control'] for r in group]
                class_means.append(statistics.mean(differences))
            block_values.append(statistics.mean(class_means))
        mean, sd = statistics.mean(block_values), statistics.stdev(block_values)
        radius = float(t.ppf(.975, len(blocks) - 1)) * sd / math.sqrt(len(blocks))
        low, high = mean - radius, mean + radius
        signal = 'UNRESOLVED' if sd == 0 else 'POSITIVE_SIGNAL' if low > 0 else 'NEGATIVE_SIGNAL' if high < 0 else 'UNRESOLVED'
        primary = saved['primary']
        for field, value in (('mean', mean), ('sample_sd', sd), ('lower', low), ('upper', high)):
            near(primary[field], value)
        require(primary['blocks'] == len(blocks) and primary['signal'] == signal and primary['zero_variance_caution'] == (sd == 0), 'Paired signal mismatch')
        for a, b in zip(block_values, primary['block_values'], strict=True): near(a, b)
        signals.append(signal)
        check_cell(rows, regime, saved['events'])
        near(saved['events']['benefit'], primary['mean'])
        for current in (0, 1):
            check_cell([r for r in rows if r['current_pass'] == current], regime, saved['current_expression'][str(current)])
        for h in sorted({r['history'] for r in rows}):
            check_cell([r for r in rows if r['history'] == h], regime, saved['histories'][h])
        for model in MODELS:
            for i in range(5):
                selected = [r for r in rows if min(math.floor(5 * (1 - pred[tuple(r['key']), regime][model])), 4) == i]
                check_cell(selected, regime, saved['risk_bins'][model][i])
    decision = 'BOTH_REGIMES_POSITIVE_SIGNAL' if all(s == 'POSITIVE_SIGNAL' for s in signals) else 'CONTRARY_SIGNAL' if 'NEGATIVE_SIGNAL' in signals else 'UNRESOLVED'
    require(result['signal'] == decision, 'Wrong joint development signal')
    controls = [dict(key=o['key'], regime=o['regime'], passed=o['control']) for o in outcomes]
    forecast_check = audit_pilot.evaluate(rows, forecasts, controls, result['control_forecasts'])
    # Separate scalar checks for all forecast calibration/class diagnostics.
    for regime in REGIMES:
        for model in MODELS:
            saved = result['control_forecasts']['regimes'][regime]
            for i in range(10):
                group = [r for r in rows if min(math.floor(10 * pred[tuple(r['key']), regime][model]), 9) == i]
                weight = math.fsum(weights[tuple(r['key'])] for r in group)
                cell = saved['calibration'][model][i]
                require(cell['records'] == len(group) and cell['bin'] == i, 'Forecast calibration count')
                near(cell['panel_mass'], weight / len(blocks))
                for field, get in (('mean_prediction', lambda k: pred[k, regime][model]), ('observed_fraction', lambda k: labels[k, regime]['control'])):
                    if weight: near(cell[field], math.fsum(weights[tuple(r['key'])] * get(tuple(r['key'])) for r in group) / weight)
                    else: require(cell[field] is None, 'Empty forecast bin')
            for current in (0, 1):
                means = [statistics.mean((pred[tuple(r['key']), regime][model] - labels[tuple(r['key']), regime]['control']) ** 2
                         for r in rows if r['block'] == b and r['current_pass'] == current) for b in blocks]
                near(statistics.mean(means), saved['current_expression'][str(current)]['scores'][model])
    return dict(status='PASS', paired_cases=len(outcomes), block_benefit_contrasts=2,
        event_and_history_cells_checked=True, risk_bin_cells=30, forecast_audit=forecast_check,
        forecast_calibration_bins=60, forecast_class_scores=12)
