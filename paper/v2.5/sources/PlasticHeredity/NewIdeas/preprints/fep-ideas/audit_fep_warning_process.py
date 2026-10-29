#!/usr/bin/env python3
"""Independent readback: stdlib only, no checker imports, stdout only."""
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

getcontext().prec = 80
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-warning-process-v1/attempt-01')
checks, residual_max = 0, D(0)


def check(condition):
    global checks
    assert condition
    checks += 1


def dec(x):
    if isinstance(x, D):
        return x
    x = F(x)
    return D(x.numerator)/D(x.denominator)


def close(x, y):
    global residual_max
    residual_max = max(residual_max, abs(dec(x)-dec(y)))
    check(abs(dec(x)-dec(y)) < D('1e-65'))


def k(r):
    return sum((dec(p)*(2*dec(p)).ln() for p in (r, 1-r) if p), D(0))


def l(sensor, w, y):
    return sensor[w] if y else 1-sensor[w]


def physical(h, pair):
    weights, ts = {}, {}
    for z in product((0, 1), repeat=3):
        t = tuple(h+(F('.1')-h)*bit for bit in z)
        weights[z] = (1-(1-t[0])*(1-t[1]))*(1-(1-t[1])*(1-t[2]))
        ts[z] = t
    total = sum(weights.values())
    pi = {z: p/total for z, p in weights.items()}
    i, j = pair
    a = sum(p*ts[z][j] for z, p in pi.items())
    g = sum(p*ts[z][i]*(1-ts[z][j]) for z, p in pi.items())
    hh = g+(1-a-g)/4
    # Integrate the utility tilt directly. The unused Y,M factors sum to one.
    norm = D(0)
    for z, p in pi.items():
        for w, action in product((0, 1), repeat=2):
            failure = ts[z][j] if not action else 1-(1-ts[z][i])*(1-ts[z][j])*(1-F(w, 4))
            correct = F('.75')+F('.15')*action
            norm += dec(p/4)*(1-dec(correct)+dec(correct)*D(4).exp())*(dec(failure)+(1-dec(failure))*D(2).exp())
    return pi, ts, a, g, hh, norm


manifest = json.loads((ROOT/'MANIFEST.json').read_text())
check(manifest['status'] == 'complete')
for entry in manifest['inputs']+manifest['outputs']:
    data = Path(entry['path']).read_bytes()
    check(len(data) == entry['bytes'])
    check(sha256(data).hexdigest() == entry['sha256'])
agents = json.loads((ROOT/'AGENT_RECORDS.json').read_text())
results = json.loads((ROOT/'RESULTS.json').read_text())
summary = results['summary']
check(len(agents) == len(results['cases']) == 16)
reconstructed = dict(calibrated_functional_passes=0,
                     calibrated_timely_posterior_predictive_failures=0,
                     calibrated_timely_per_world_per_signal_failures=0,
                     degraded_timely_primary_failures=0,
                     degraded_timely_posterior_predictive_failures=0,
                     degraded_timely_certificate_exceedances=0,
                     fallback_primary_failures=0)
rows = []
world_count = mixture_count = trace_count = 0
event_order = dict(stop=['prepared', 'purchase_selected', 'action_committed'],
                   timely=['prepared', 'purchase_selected', 'warning_delivered', 'action_committed'],
                   late=['prepared', 'purchase_selected', 'action_committed', 'warning_delivered'],
                   blocked=['prepared', 'purchase_selected', 'warning_delivered', 'action_committed'])
for agent, case in zip(agents, results['cases']):
    plan = agent['plan']
    check(agent['agent_id'] == case['agent_id'])
    h, pair = F(plan['h']), tuple(plan['pair'])
    model_sensor = tuple(map(F, plan['sensor']))
    fallback, eps = F(plan['fallback']), F(plan['epsilon'])
    response = tuple(map(F, plan['response']))
    expected_hash = sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    pi, ts, a, g, hh, norm = physical(h, pair)
    close(norm, case['reference']['Z0'])
    for key, value in (('A', a), ('G', g), ('H', hh)):
        check(F(case['reference'][key]) == value)
    for z, value in case['reference']['pi']:
        check(pi[tuple(z)] == F(value))
    boundary = next(i for i in range(3) if i not in pair)
    for bit, line in enumerate(plan['rows']):
        mass = sum(p for z, p in pi.items() if z[boundary] == bit)
        ab = sum(p*ts[z][pair[1]] for z, p in pi.items() if z[boundary] == bit)/mass
        gb = sum(p*ts[z][pair[0]]*(1-ts[z][pair[1]]) for z, p in pi.items() if z[boundary] == bit)/mass
        check(tuple(map(F, line)) == (ab, gb, gb+(1-ab-gb)/4))
    check(response[0] == fallback+eps)
    check(response[1] == fallback-(1-model_sensor[1])*eps/model_sensor[1])
    for schedule, branches in agent['schedules'].items():
        for bit, branch in enumerate(branches):
            trace_count += 1
            events = branch['trace']
            check([e['event'] for e in events] == event_order[schedule])
            check(events[0]['plan_sha256'] == expected_hash)
            committed = next(e for e in events if e['event'] == 'action_committed')
            expected_r = response[bit] if schedule == 'timely' else fallback
            check(F(committed['r']) == F(branch['r']) == expected_r)
            py = model_sensor[1] if bit else 1-model_sensor[1]
            py /= (model_sensor[0] if bit else 1-model_sensor[0])+(model_sensor[1] if bit else 1-model_sensor[1])
            expected_belief = py if schedule in ('timely', 'blocked') else F('.5')
            check(F(committed['world_belief']) == expected_belief)
            check(F(branch['final_world_belief']) == (F('.5') if schedule == 'stop' else py))
            check(committed['used_warning'] == (schedule == 'timely'))
            check(branch['mode'] == int(schedule != 'stop'))
            check(branch['observed'] == (None if schedule == 'stop' else bit))
            drop = D(0) if schedule == 'stop' else (-(4*dec(py)*(1-dec(py))).ln()/2)
            close(drop, branch['model_vfe_drop'])
    for evaluation in case['evaluations']:
        actual = tuple(map(F, evaluation['actual_sensor']))
        condition = evaluation['sensor_condition']
        computed = {}
        for schedule, policy in evaluation['policies'].items():
            mixture_count += 1
            rs = tuple(F(b['r']) for b in agent['schedules'][schedule])
            check(tuple(map(F, policy['actions'])) == rs)
            risks, utilities, correctness, bounds, conditionals = [], [], [], [], []
            js, discrepancies = [], []
            for w in (0, 1):
                world_count += 1
                target = policy['worlds'][w]
                rmean = sum(l(actual, w, y)*rs[y] for y in (0, 1))
                rmodel = sum(l(model_sensor, w, y)*rs[y] for y in (0, 1))
                risk = a+(g, hh)[w]*rmean
                correct = F('.75')+F('.15')*rmean
                util = correct+(1-risk)/2
                bound = max(F(line[0])+F(line[w+1])*rmodel for line in plan['rows'])
                for field, value in (('risk', risk), ('correctness', correct), ('raw_utility', util), ('precision', rmean), ('reported_model_upper', bound)):
                    check(F(target[field]) == value)
                check(target['risk_violation'] == (risk > F('.1')))
                check(target['certificate_exceeded'] == (risk > bound))
                per_signal = [a+(g, hh)[w]*r for r in rs]
                for y in (0, 1):
                    check(F(target['per_signal'][y]['risk']) == per_signal[y])
                    check(target['per_signal'][y]['risk_violation'] == (per_signal[y] > F('.1')))
                j = sum((dec(l(actual, w, y))*k(rs[y]) for y in (0, 1)), D(0))-4*dec(util)
                discrepancy = sum((dec(l(actual, w, y))*(dec(l(actual, w, y))/dec(l(model_sensor, w, y))).ln() for y in (0, 1)), D(0))
                close(target['full_kl_kappa0'], 2*D(2).ln()+j+norm.ln()+discrepancy)
                close(target['sensor_discrepancy'], discrepancy)
                risks.append(risk)
                utilities.append(util)
                correctness.append(correct)
                bounds.append(bound)
                conditionals.extend(per_signal)
                js.append(j)
                discrepancies.append(discrepancy)
            raw = sum(utilities)/2
            score = D(2).ln()+sum(js)/2+norm.ln()+sum(discrepancies)/2
            check(F(policy['mixture']['raw_utility']) == raw)
            check(F(policy['mixture']['correctness']) == sum(correctness)/2)
            close(policy['mixture']['full_kl_kappa0'], score)
            pp = []
            for y in (0, 1):
                true_p = l(actual, 1, y)/(l(actual, 0, y)+l(actual, 1, y))
                model_p = l(model_sensor, 1, y)/(l(model_sensor, 0, y)+l(model_sensor, 1, y))
                risk = a+(g+true_p*(hh-g))*rs[y]
                check(F(policy['posterior_diagnostics'][y]['actual_conditional_pH']) == true_p)
                check(F(policy['posterior_diagnostics'][y]['model_conditional_pH']) == model_p)
                check(F(policy['posterior_diagnostics'][y]['actual_conditional_risk']) == risk)
                check(policy['posterior_diagnostics'][y]['posterior_predictive_violation'] == (risk > F('.1')))
                pp.append(risk)
            safe, pp_safe, strong_safe = max(risks) <= F('.1'), max(pp) <= F('.1'), max(conditionals) <= F('.1')
            check(policy['per_world_average_safe'] == safe)
            check(policy['posterior_predictive_safe'] == pp_safe)
            check(policy['per_world_per_signal_safe'] == strong_safe)
            computed[schedule] = dict(raw=raw, score=score, risks=risks, bounds=bounds,
                                      pp=pp, safe=safe, pp_safe=pp_safe, strong_safe=strong_safe,
                                      correct=sum(correctness)/2, missed=conditionals[2])
            if schedule != 'timely':
                reconstructed['fallback_primary_failures'] += sum(r > F('.1') for r in risks)
        for name, values in computed.items():
            change = evaluation['policies'][name]['comparison_to_stop']
            check(F(change['raw_gain']) == values['raw']-computed['stop']['raw'])
            close(change['full_kl_gain_kappa0'], computed['stop']['score']-values['score'])
        if case['panel'] == 'informative':
            timely, stop = computed['timely'], computed['stop']
            if condition == 'calibrated':
                functional = (timely['safe'] and timely['raw'] > stop['raw'] and timely['correct'] > stop['correct']
                              and timely['score'] < stop['score'] and D(plan['incremental_cost_ceiling']) > 0)
                check(evaluation['calibrated_functional_pass'] == functional)
                reconstructed['calibrated_functional_passes'] += functional
                reconstructed['calibrated_timely_posterior_predictive_failures'] += not timely['pp_safe']
                reconstructed['calibrated_timely_per_world_per_signal_failures'] += not timely['strong_safe']
            else:
                reconstructed['degraded_timely_primary_failures'] += not timely['safe']
                reconstructed['degraded_timely_posterior_predictive_failures'] += not timely['pp_safe']
                reconstructed['degraded_timely_certificate_exceedances'] += timely['risks'][1] > timely['bounds'][1]
            if pair in ((0, 1), (1, 0)):
                rows.append(dict(h=str(h), pair=pair, sensor=condition,
                                 hazard_risk=str(dec(timely['risks'][1])), max_posterior_risk=str(dec(max(timely['pp']))),
                                 missed_hazard_risk=str(dec(timely['missed'])),
                                 raw_gain=str(dec(timely['raw']-stop['raw'])),
                                 full_kl_gain=str(stop['score']-timely['score']),
                                 cost_ceiling=plan['incremental_cost_ceiling']))
for field, value in reconstructed.items():
    check(summary[field] == value)
check((mixture_count, world_count, trace_count) == (96, 192, 128))
print(json.dumps(dict(comparisons=checks, maximum_decimal_residual=str(residual_max),
                     identities=len(manifest['inputs'])+len(manifest['outputs']),
                     record_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),
                     main_started_utc=manifest['started_utc'], main_finished_utc=manifest['finished_utc'],
                     main_wall_seconds=manifest['wall_seconds'], main_cpu_seconds=manifest['cpu_seconds'],
                     counts=reconstructed, representative_rows=rows), indent=2))
