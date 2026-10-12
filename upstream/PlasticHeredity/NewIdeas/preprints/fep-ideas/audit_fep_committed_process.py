#!/usr/bin/env python3
"""Independent readback arithmetic; no controller/checker imports."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
from time import perf_counter
import traceback

getcontext().prec = 80
COUNT, MAX_ERROR = 0, D(0)
BITS = (0, 1)
HIDDEN = tuple(product(BITS, repeat=2))
STATES = tuple(product(BITS, repeat=9))


def check(ok, label):
    global COUNT
    if not ok:
        raise AssertionError(label)
    COUNT += 1


def dec(value):
    if isinstance(value, D):
        return value
    value = F(value)
    return D(value.numerator)/D(value.denominator)


def near(a, b, label):
    global MAX_ERROR
    error = abs(dec(a)-dec(b))
    MAX_ERROR = max(MAX_ERROR, error)
    check(error <= D('1e-65'), label)


def bern(p, bit):
    return p if bit else 1-p


def k(r):
    return sum((dec(p)*(2*dec(p)).ln() for p in (r, 1-r) if p), D(0))


def cal(theta, x):
    return bern(F(8+theta, 10), x)


def sensor(theta, world, channel, y, changed=False):
    is_good = theta != channel
    alarm = (F(9, 10) if is_good else F(6 if changed else 8, 10)) if world else F(1 if is_good else 2, 10)
    return bern(alarm, y)


def risk(world, action):
    return F(2, 25)+(F(11, 40) if world else F(3, 50))*action


def joint_posterior(hx, channel, y, drift=False):
    raw = [F(1, 4)*(cal(th, hx) if hx is not None else 1)*sensor(th, w, channel, y, drift) for th, w in HIDDEN]
    total = sum(raw)
    return tuple(p/total for p in raw)


def canonical_hash(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_identity(entry):
    data = Path(entry['path']).read_bytes()
    check(len(data) == entry['bytes'], 'file size '+entry['path'])
    check(sha256(data).hexdigest() == entry['sha256'], 'file hash '+entry['path'])


def audit(folder):
    manifest = json.loads((folder/'MANIFEST.json').read_text())
    check(manifest['status'] == 'complete', 'main calculation completed')
    for entry in manifest['inputs']+manifest['outputs']+manifest['preserved']:
        verify_identity(entry)
    qualification = json.loads((folder/'QUALIFICATION.json').read_text())
    check(qualification['status'] == 'PASS' and len(qualification['rejected']) == 12, 'event qualification')
    saved = json.loads((folder/'AGENT_RECORDS.json').read_text())
    results = json.loads((folder/'RESULTS.json').read_text())
    lib = saved['library']
    check(canonical_hash(lib) == saved['library_sha256'], 'library seal')
    roots = {F(r['quality']): r for r in lib['responses']}
    check(set(roots) == {F(1, 3), F(2, 3), F(8, 17), F(9, 17), F(1, 2)}, 'five registered responses')
    for t, response in roots.items():
        r0, r1 = map(F, response['r'])
        beta = F(4, 5)+t/10
        c0 = (beta*F(3, 25)+(1-beta)*F(1, 80))/2
        c1 = ((1-beta)*F(3, 25)+beta*F(1, 80))/2
        utility = F(121, 100)+c0*r0+c1*r1
        near(response['utility'], utility, 'response utility from physical means')
        near(response['loss'], (k(r0)+k(r1))/2-4*dec(utility), 'response free energy')
        grad0 = (dec(r0)/(1-dec(r0))).ln()/2-4*dec(c0)
        grad1 = (dec(r1)/(1-dec(r1))).ln()/2-4*dec(c1)
        multiplier = -5*grad0
        near(grad1+dec(F(4, 5))*multiplier, 0, 'independent KKT stationarity')
        check(multiplier > 0 and 0 < r1 < r0 < 1, 'KKT interior and multiplier')
        check(r0/5+F(4, 5)*r1 == F(4, 55) and r0/10+F(9, 10)*r1 < F(4, 55), 'hazard constraints')
        check(F(9, 10)*r0+r1/10 < F(1, 3) and F(4, 5)*r0+r1/5 < F(1, 3), 'nominal constraints')
    for rule, lmb in ((lib['prior'], F(1, 2)), (lib['after'][0], F(1, 3)), (lib['after'][1], F(9, 17))):
        b = int(D(roots[1-lmb]['loss']) < D(roots[lmb]['loss']))
        selected = roots[1-lmb if b else lmb]
        check(F(rule['lambda_a']) == lmb and rule['channel'] == b and rule['response'] == selected['r'], 'backward channel choice')
        check(rule['utility'] == selected['utility'] and rule['loss'] == selected['loss'], 'chosen value')
    gain = D(lib['prior']['loss'])-dec(F(3, 20))*D(lib['after'][0]['loss'])-dec(F(17, 20))*D(lib['after'][1]['loss'])
    gu = F(3, 20)*F(lib['after'][0]['utility'])+F(17, 20)*F(lib['after'][1]['utility'])-F(lib['prior']['utility'])
    near(gain, lib['gain'], 'acquisition value')
    check(gu == F(lib['utility_gain']) and 0 < gain < 4*dec(gu), 'functional threshold')

    expected_cases = {f'optimized-{s}-{p}' for s in ('timely', 'late', 'blocked', 'frozen') for p in ('free', 'witness', 'costly')}
    expected_cases |= {f'forced-{s}' for s in ('timely', 'late', 'blocked', 'frozen', 'skip')}
    expected_cases |= {'unexpected-late', 'unexpected-blocked'}
    check({c['case_id'] for c in saved['cases']} == expected_cases and len(saved['cases']) == 19, 'registered cases')
    trace_count = 0
    for case in saved['cases']:
        plan = case['plan']
        price = D(plan['price'])
        name = case['case_id']
        if name.startswith('optimized-'):
            _, schedule, price_label = name.split('-')
            registered = (schedule, schedule, 'optimized', {'free': D(0), 'witness': D('.0001'), 'costly': D(3).ln()}[price_label])
        elif name == 'forced-skip':
            registered = ('timely', 'timely', 'skip', D('.0001'))
        elif name.startswith('forced-'):
            schedule = name.split('-')[1]
            registered = (schedule, schedule, 'buy', D('.0001'))
        else:
            registered = ('timely', name.split('-')[1], 'optimized', D('.0001'))
        check((plan['expected'], case['actual'], plan['override'], price) == registered, 'registered schedule and charge')
        check(plan['library_sha256'] == saved['library_sha256'], 'shared immutable library')
        expected_gain = gain if plan['expected'] == 'timely' else D(0)
        near(plan['expected_gain'], expected_gain, 'schedule-aware acquisition value')
        m = int(price < expected_gain) if plan['override'] == 'optimized' else int(plan['override'] == 'buy')
        check(m == plan['purchase'], 'purchase before evidence')
        check({(t['x'], t['y']) for t in case['traces']} == set(product(BITS, repeat=2)), 'four signal branches')
        for trace in case['traces']:
            trace_count += 1
            x, y = trace['x'], trace['y']
            available = x if m and case['actual'] in ('timely', 'frozen') else None
            used = available is not None and plan['expected'] != 'frozen'
            rule = lib['after'][x] if used else lib['prior']
            events = ['prepared', 'purchase_selected']
            if available is not None:
                events.append('calibration_delivered')
            events += ['channel_committed', 'warning_delivered', 'response_committed']
            if m and case['actual'] == 'late':
                events.append('calibration_delivered')
            check([e['event'] for e in trace['events']] == events, 'causal event sequence')
            check(trace['events'][0]['plan_sha256'] == canonical_hash(plan), 'plan sealed before evidence')
            check(trace['purchase'] == m and trace['available_x'] == available, 'available calibration')
            observed = x if m and case['actual'] != 'blocked' else None
            check(trace['observed_x'] == observed, 'delivered calibration record')
            check(trace['channel'] == rule['channel'] and trace['response'] == rule['response'], 'selected frozen rule')
            check(trace['r'] == rule['response'][y], 'response from frozen table')
            q = (F(1, 4),)*4
            for event in trace['events']:
                name = event['event']
                if name in ('calibration_delivered', 'warning_delivered'):
                    check(event['bit'] == (x if name == 'calibration_delivered' else y), 'delivered signal bit')
                    if name == 'calibration_delivered':
                        check(event['after_response'] == (case['actual'] == 'late'), 'late delivery flag')
                    ll = tuple(cal(th, x) if name == 'calibration_delivered' else sensor(th, w, rule['channel'], y) for th, w in HIDDEN)
                    raw = tuple(p*l for p, l in zip(q, ll))
                    evidence = sum(raw)
                    next_q = tuple(p/evidence for p in raw)
                    near(event['vfe_decrease'], sum((dec(a)*(dec(a)/dec(b)).ln() for a, b in zip(q, next_q)), D(0)), 'inference VFE at same evidence')
                    check(F(event['evidence']) == evidence, 'evidence probability')
                    q = next_q
                if name == 'channel_committed':
                    check(event['available_x'] == available and event['used_calibration'] == used, 'channel access record')
                if name == 'response_committed':
                    check(event['r'] == rule['response'][y] and event['response'] == rule['response'], 'commitment snapshot')
                    check(tuple(map(F, trace['belief_at_response'])) == q, 'decision-time posterior')
                if 'belief' in event:
                    check(tuple(map(F, event['belief'])) == q, 'Bayesian event belief')
                    check(all(p > 0 for p in q), 'all supported hidden states retained')
            check(tuple(map(F, trace['final_belief'])) == q, 'final belief')

    preferences = {}
    for price_string, z_saved in results['normalizers'].items():
        charge = D(price_string)
        raw = []
        for theta, w, x, m, b, y, a, t, v in STATES:
            mu = cal(theta, x)*sensor(theta, w, b, y)/32
            mu *= bern(F(15+3*a, 20), t)*bern(1-risk(w, a), v)
            raw.append(dec(mu)*(D(4*t+2*v)-charge*m).exp())
        z = sum(raw)
        near(z, z_saved, 'full preference normalizer')
        preferences[charge] = (z, tuple(p/z for p in raw))
    comparison_count = 0
    rows = []
    by_case = {c['case_id']: c for c in saved['cases']}
    check(len(results['evaluations']) == 38, 'two physical laws per case')
    check({(e['case_id'], e['drift']) for e in results['evaluations']} == {(name, shift) for name in expected_cases for shift in BITS}, 'complete physical panel')
    for evaluated in results['evaluations']:
        case = by_case[evaluated['case_id']]
        changed = evaluated['drift']
        traces = {(t['x'], t['y']): t for t in case['traces']}
        price, m = D(case['plan']['price']), case['plan']['purchase']
        z, target = preferences[price]
        check(evaluated['mixture']['actual'] is None and len(evaluated['worlds']) == 4
              and {tuple(score['actual']) for score in evaluated['worlds']} == set(HIDDEN), 'all physical conditionings')
        for saved_score in [evaluated['mixture'], *evaluated['worlds']]:
            actual = saved_score['actual']
            check(actual is None or tuple(actual) in HIDDEN, 'physical conditioning')
            mass, correct, failure, utility = F(0), F(0), F(0), F(0)
            full, response_term, discrepancy = D(0), D(0), D(0)
            for state, preferred in zip(STATES, target):
                theta, w, x, mode, b, y, a, t, v = state
                trace = traces[x, y]
                if mode != m or b != trace['channel']:
                    continue
                prob = F(1, 4) if actual is None else F((theta, w) == tuple(actual))
                prob *= cal(theta, x)*sensor(theta, w, b, y, changed)*bern(F(trace['r']), a)
                prob *= bern(F(15+3*a, 20), t)*bern(1-risk(w, a), v)
                if prob:
                    mass += prob
                    correct += prob*t
                    failure += prob*(1-v)
                    utility += prob*(F(t)+F(v, 2))
                    full += dec(prob)*(dec(prob)/preferred).ln()
            for theta, w, x, y in product(BITS, repeat=4):
                trace = traces[x, y]
                weight = F(1, 4) if actual is None else F((theta, w) == tuple(actual))
                b = trace['channel']
                weight *= cal(theta, x)*sensor(theta, w, b, y, changed)
                response_term += dec(weight)*k(F(trace['r']))
                discrepancy += dec(weight)*(dec(sensor(theta, w, b, y, changed))/dec(sensor(theta, w, b, y))).ln()
            check(mass == 1, 'physical normalization')
            for key, value in (('utility', utility), ('correctness', correct), ('risk', failure)):
                check(F(saved_score[key]) == value, 'reconstructed '+key)
            near(saved_score['net_utility'], dec(utility)-price*m/4, 'paid utility')
            near(saved_score['response_KL'], response_term, 'response KL')
            near(saved_score['warning_KL'], discrepancy, 'warning discrepancy')
            near(saved_score['full_KL'], full, 'complete KL readback')
            reduced = 2*D(2).ln()+response_term-4*dec(utility)+price*m+discrepancy
            near(saved_score['reduced_J'], reduced, 'reduced objective')
            near(full, reduced+z.ln()+(D(4).ln() if actual is not None else 0), 'complete identity')
            comparison_count += 1
        diag = evaluated['diagnostics']
        available_histories = {t['available_x'] for t in case['traces']}
        expected_primary = {(th, w, hx) for th, w in HIDDEN for hx in available_histories}
        expected_signal = {(th, w, hx, y) for th, w, hx in expected_primary for y in BITS}
        check(len(diag['primary']) == len(expected_primary)
              and {(r['theta'], r['world'], r['history_x']) for r in diag['primary']} == expected_primary, 'complete primary risk coverage')
        check(len(diag['per_signal']) == len(expected_signal)
              and {(r['theta'], r['world'], r['history_x'], r['y']) for r in diag['per_signal']} == expected_signal, 'complete warning subgroup coverage')
        check(len(diag['predictive']) == 2*len(available_histories)
              and {(r['history_x'], r['y']) for r in diag['predictive']} == {(hx, y) for hx in available_histories for y in BITS}, 'complete predictive coverage')
        for row in diag['primary']:
            numerator, denominator = F(0), F(0)
            for trace in case['traces']:
                if trace['available_x'] == row['history_x']:
                    p = cal(row['theta'], trace['x'])*sensor(row['theta'], row['world'], trace['channel'], trace['y'], changed)
                    denominator += p
                    numerator += p*risk(row['world'], F(trace['r']))
            check(F(row['risk']) == numerator/denominator, 'primary history risk')
        for row in diag['per_signal']:
            trace = next(t for t in case['traces'] if t['available_x'] == row['history_x'] and t['y'] == row['y'])
            check(F(row['risk']) == risk(row['world'], F(trace['r'])), 'per-world per-warning risk')
        for row in diag['predictive']:
            trace = next(t for t in case['traces'] if t['available_x'] == row['history_x'] and t['y'] == row['y'])
            for shift, key in ((False, 'agent_risk'), (changed, 'actual_risk')):
                q = joint_posterior(row['history_x'], trace['channel'], row['y'], shift)
                prediction = sum(p*risk(w, F(trace['r'])) for p, (th, w) in zip(q, HIDDEN))
                check(F(row[key]) == prediction, 'posterior-predictive risk')
        primary = [F(r['risk']) for r in diag['primary']]
        signal = [F(r['risk']) for r in diag['per_signal']]
        for key, values in (('primary', primary), ('signal', signal)):
            check(diag[key+'_cases'] == len(values), 'risk denominator')
            check(diag[key+'_failures'] == sum(v > F(1, 10) for v in values), 'risk failure count')
            check(F(diag[key+'_max']) == max(values), 'worst conditional risk')
        check(diag['primary_safe'] == all(v <= F(1, 10) for v in primary), 'primary safety flag')
        for label, key in (('agent', 'agent_risk'), ('actual', 'actual_risk')):
            check(diag['predictive_'+label+'_failures'] == sum(F(row[key]) > F(1, 10) for row in diag['predictive']), 'predictive failure count')
        rows.append(dict(case_id=case['case_id'], drift=changed, primary_failures=diag['primary_failures'],
                         primary_cases=diag['primary_cases'], primary_max=diag['primary_max']))
    check(trace_count == 76 and comparison_count == 190, 'complete readback scope')
    summary = results['summary']
    check(summary['nominal_primary_safe'] == sum(r['primary_failures'] == 0 for r in rows if not r['drift']), 'nominal summary')
    check(summary['drift_primary_unsafe'] == sum(r['primary_failures'] > 0 for r in rows if r['drift']), 'drift summary')
    return dict(status='PASS', assertions=COUNT, max_decimal_residual=str(MAX_ERROR),
                trace_count=trace_count, full_joint_comparisons=comparison_count,
                verified_inputs=len(manifest['inputs']), verified_outputs=len(manifest['outputs']),
                verified_preserved=len(manifest['preserved']),
                manifest_sha256=sha256((folder/'MANIFEST.json').read_bytes()).hexdigest(), rows=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', required=True, type=Path)
    args = parser.parse_args()
    folder = args.record.resolve()
    base = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-committed-process-v1').resolve()
    if not Path('/mnt/bioIce1').is_mount() or folder.parent != base or not folder.is_dir():
        raise SystemExit('Require an existing attempt on the external FEP mount')
    target = folder/'READBACK.json'
    if target.exists():
        raise SystemExit('Refusing to overwrite an existing readback')
    start, wall = datetime.now(timezone.utc).isoformat(), perf_counter()
    result = dict(status='failed')
    try:
        result = audit(folder)
    except BaseException:
        result.update(assertions=COUNT, error=traceback.format_exc())
        raise
    finally:
        result.update(started_utc=start, finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=perf_counter()-wall)
        with target.open('x') as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
