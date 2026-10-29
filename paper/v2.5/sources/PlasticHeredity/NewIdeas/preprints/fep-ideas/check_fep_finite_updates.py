#!/usr/bin/env python3
"""Execute the frozen twelve-case static VMP comparison; no sampling or fitting."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
import hashlib
import json
import os
from pathlib import Path
import platform
from time import perf_counter
import traceback


getcontext().prec = 80
ZERO, ONE, HALF = D(0), D(1), D('0.5')
BAD, ETA, BETA, TOL = D('0.1'), D('0.25'), D(4), D('1e-35')
SWEEPS = 16
STATES = [(0, 0), (1, 0), (0, 1), (1, 1)]
SCHEDULES = ('R_first', 'L_first', 'simultaneous')
TREATMENTS = {'exact': ZERO, 'source_epsilon': D(-16).exp()}
PRIOR_RECORD = Path('/mnt/bioIce1/fep-ideas/formal-checks/'
                    'fep-variational-positive-v1/attempt-01')
CHECKS = Counter()
MAX_RESIDUAL = ZERO


def require(label, condition):
    if not condition:
        raise AssertionError(label)
    CHECKS[label] += 1


def close(label, actual, expected):
    global MAX_RESIDUAL
    error = abs(actual - expected)
    MAX_RESIDUAL = max(MAX_RESIDUAL, error)
    require(label, error <= TOL)


def sigmoid(z):
    return ONE / (ONE + (-z).exp())


def logit(z):
    return (z / (ONE-z)).ln()


def kl(q, p):
    return sum(qi*(qi/pi).ln() for qi, pi in zip(q, p) if qi)


def identity(path):
    content = path.read_bytes()
    return {'path': str(path), 'bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest()}


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, default=str)+'\n')


def world(h):
    survival = [[(ONE-h-(BAD-h)*l) *
                 ((ONE-h-(BAD-h)*r) if action else ONE)
                 for r, l in STATES] for action in (0, 1)]
    risk = [[ONE-v for v in law] for law in survival]
    likelihood = risk[1]
    pi = [v/sum(likelihood) for v in likelihood]
    a, b, _, c = likelihood
    return {'h': h, 'risk': risk, 'likelihood': likelihood,
            'pi': pi, 'evidence': sum(likelihood)/4,
            'A': (b/a).ln(), 'J': (b*b/(a*c)).ln()}


def forecast(model, belief):
    risk = [sum(q*f for q, f in zip(belief, law)) for law in model['risk']]
    value = [D('0.75')+HALF*(ONE-risk[0]), D('0.90')+HALF*(ONE-risk[1])]
    return risk, value


def decision(model, belief):
    risk, value = forecast(model, belief)
    exact_risk, exact_value = forecast(model, model['pi'])
    require('positive precision risk increment', risk[1] > risk[0])
    require('economy feasible', risk[0] <= BAD)
    cap = min(ONE, (BAD-risk[0])/(risk[1]-risk[0]))
    free = sigmoid(BETA*(value[1]-value[0]))
    r = min(cap, free)
    predicted = (ONE-r)*risk[0]+r*risk[1]
    actual = (ONE-r)*exact_risk[0]+r*exact_risk[1]
    utility = (ONE-r)*exact_value[0]+r*exact_value[1]
    require('policy in unit interval', ZERO <= r <= ONE)
    require('internal feasibility', predicted <= BAD+TOL)
    if cap < free:
        close('binding chance constraint', predicted, BAD)
    else:
        close('unconstrained policy stationarity', logit(r),
              BETA*(value[1]-value[0]))
    feasible = [a for a in (0, 1) if risk[a] <= BAD]
    best = max(value[a] for a in feasible)
    return {'failure_risks': risk, 'task_values': value,
            'chance_upper_bound': cap, 'unconstrained_precision_probability': free,
            'optimal_precision_probability': r,
            'deterministic_optimum_set': [a for a in feasible if value[a] == best],
            'predicted_policy_risk': predicted, 'exact_model_policy_risk': actual,
            'exact_model_budget_slack': BAD-actual,
            'exact_model_budget_violated': actual > BAD+TOL,
            'exact_model_task_value': utility,
            'exact_model_reference_score': kl([ONE-r, r], [HALF, HALF])-BETA*utility}


def coefficients(model, epsilon):
    a, b, _, c = [v+epsilon for v in model['likelihood']]
    return (b/a).ln(), (b*b/(a*c)).ln()


def component(model, own, other, epsilon):
    ae, je = coefficients(model, epsilon)
    old = ((own+epsilon)/(ONE-own+epsilon)).ln()
    updated = sigmoid((ONE-ETA)*old+ETA*(ae-je*other))
    # Independent probability-vector expected-log messages, including the prior.
    a, b, _, c = model['likelihood']
    messages = [(HALF+epsilon).ln()+(ONE-other)*(a+epsilon).ln()
                + other*(b+epsilon).ln(),
                (HALF+epsilon).ln()+(ONE-other)*(b+epsilon).ln()
                + other*(c+epsilon).ln()]
    logits = [(ONE-ETA)*(q+epsilon).ln()+ETA*message
              for q, message in zip((ONE-own, own), messages)]
    weights = [z.exp() for z in logits]
    close('scalar versus vector update', updated, weights[1]/sum(weights))
    return updated


def advance(model, x, y, epsilon, schedule):
    if schedule == 'simultaneous':
        return [('R,L', component(model, x, y, epsilon),
                 component(model, y, x, epsilon))]
    if schedule == 'R_first':
        nx = component(model, x, y, epsilon)
        return [('R', nx, y), ('L', nx, component(model, y, nx, epsilon))]
    if schedule == 'L_first':
        ny = component(model, y, x, epsilon)
        return [('L', x, ny), ('R', component(model, x, ny, epsilon), ny)]
    raise ValueError(schedule)


def snapshot(model, epsilon, x, y, sweep, phase, updated, endpoint):
    require('interior beliefs', ZERO < x < ONE and ZERO < y < ONE)
    q = [(x if r else ONE-x)*(y if l else ONE-y) for r, l in STATES]
    close('normalized product', sum(q), ONE)
    f = kl(q, [v/4 for v in model['likelihood']])
    gap = kl(q, model['pi'])
    close('VFE posterior identity', f, gap-model['evidence'].ln())
    entropy_term = sum(t*t.ln() for t in (x, ONE-x, y, ONE-y))
    reduced = (entropy_term-model['A']*(x+y)+model['J']*x*y
               -(model['likelihood'][0]/4).ln())
    close('enumerated versus reduced VFE', f, reduced)
    require('global lower bound', f >= model['global_minimum_F']-TOL)
    policy = decision(model, q)
    delta = BAD-model['h']
    close('economy moment forecast', policy['failure_risks'][0], model['h']+delta*y)
    close('precision moment forecast', policy['failure_risks'][1],
          model['likelihood'][0]+(ONE-model['h'])*delta*(x+y)-delta*delta*x*y)
    grad = [logit(x)-model['A']+model['J']*y,
            logit(y)-model['A']+model['J']*x]
    ae, je = coefficients(model, epsilon)
    residual = [logit(z)-(ONE-ETA)*((z+epsilon)/(ONE-z+epsilon)).ln()
                -ETA*(ae-je*w) for z, w in ((x, y), (y, x))]
    if epsilon == ZERO:
        for actual, expected in zip(residual, grad):
            close('exact-log fixed-point versus gradient residual', actual, ETA*expected)
    return {'sweep': sweep, 'phase': phase, 'updated': updated,
            'sweep_endpoint': endpoint, 'x': x, 'y': y, 'q': q,
            'true_vfe': f, 'posterior_kl': gap,
            'excess_over_global_vfe': f-model['global_minimum_F'],
            'true_vfe_gradient': grad, 'max_true_vfe_gradient': max(map(abs, grad)),
            'update_fixed_point_residual': residual,
            'max_update_fixed_point_residual': max(map(abs, residual)),
            'policy': policy}


def qualify(saved):
    models, references = [], []
    for old in saved['fixtures']:
        model = world(D(old['baseline']))
        require('fixed inherited baseline', model['h'] in (D('1e-6'), D('0.01')))
        for actual, expected in zip(model['pi'], old['exact_posterior']):
            close('saved exact joint', actual, D(expected))
        close('exact joint normalized', sum(model['pi']), ONE)
        exact_decision = decision(model, model['pi'])
        for key in ('optimal_precision_probability', 'exact_model_policy_risk',
                    'exact_model_task_value', 'exact_model_reference_score'):
            close('saved exact decision '+key, exact_decision[key], D(old['exact_decision'][key]))
        minima = []
        for item in old['complete_global_minima']:
            x, y = D(item['x']), D(item['y'])
            q = [(x if r else ONE-x)*(y if l else ONE-y) for r, l in STATES]
            f = kl(q, [v/4 for v in model['likelihood']])
            close('saved global VFE', f, D(item['free_energy']))
            policy = decision(model, q)
            for key in ('optimal_precision_probability', 'exact_model_policy_risk',
                        'exact_model_task_value', 'exact_model_reference_score'):
                close('saved global decision '+key, policy[key], D(item['decision'][key]))
            minima.append({'x': x, 'y': y, 'true_vfe': f, 'policy': policy})
        model['global_minimum_F'] = min(item['true_vfe'] for item in minima)
        model['minima'] = minima
        model['exact_decision'] = exact_decision
        for epsilon in TREATMENTS.values():
            ae, je = coefficients(model, epsilon)
            first = advance(model, HALF, HALF, epsilon, 'R_first')[-1]
            expected_x = sigmoid(ETA*(ae-je*HALF))
            expected_y = sigmoid(ETA*(ae-je*expected_x))
            close('derived first-sweep x', first[1], expected_x)
            close('derived first-sweep y', first[2], expected_y)
            require('first updated cause favored', first[1] > first[2])
        references.append({'baseline': model['h'], 'exact_joint': model['pi'],
                           'exact_decision': exact_decision, 'global_minima': minima,
                           'symmetric_stationary_coordinate': old['symmetric_coordinate']})
        models.append(model)
    require('exactly two inherited baselines',
            sorted(m['h'] for m in models) == [D('1e-6'), D('0.01')])
    return models, references


def contrast(first, second):
    a, b = first['final'], second['final']
    differences = {key: a[key]-b[key] for key in ('x', 'y', 'true_vfe')}
    differences.update({key: a['policy'][key]-b['policy'][key]
                        for key in ('optimal_precision_probability',
                                    'exact_model_policy_risk', 'exact_model_task_value',
                                    'exact_model_reference_score')})
    return {'first': first['case_id'], 'second': second['case_id'],
            'first_minus_second': differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve()
    spec = source.with_name('FEP_FINITE_UPDATES_V1.md')
    require('specification matches pre-execution freeze', identity(spec)['sha256'] == args.spec_sha256)
    require('checker matches pre-execution freeze', identity(source)['sha256'] == args.source_sha256)
    output = args.output.resolve()
    allowed = Path('/mnt/bioIce1/fep-ideas/formal-checks').resolve()
    if (not output.is_relative_to(allowed) or not os.path.ismount('/mnt/bioIce1')
            or os.statvfs('/mnt/bioIce1').f_flag & os.ST_RDONLY):
        raise RuntimeError('Require writable mounted external FEP namespace; no local fallback')
    output.mkdir(parents=True, exist_ok=False)
    input_paths = [spec, source, source.with_name('FEP_PUBLISHED_UPDATE_AUDIT_V1.md'),
                   source.with_name('FEP_VARIATIONAL_POSITIVE_V1.md'),
                   source.with_name('check_fep_variational_positive.py'),
                   source.with_name('FEP_VARIATIONAL_POSITIVE_V1_REPORT.md'),
                   PRIOR_RECORD/'MANIFEST.json', PRIOR_RECORD/'RESULTS.json']
    inputs = [identity(p) for p in input_paths]
    started = datetime.now(timezone.utc).isoformat()
    begin = perf_counter()
    manifest = {'status': 'running', 'started_utc': started, 'inputs': inputs}
    dump(output/'MANIFEST.json', manifest)
    log = output/'RUN_LOG.txt'
    log.write_text(f'Started {started}\nPython {platform.python_version()}; one process; Decimal 80.\n'
                   'Twelve fixed cases, sixteen sweeps; no sampling, fitting or adaptive stopping.\n'
                   f'Spec SHA256 {args.spec_sha256}\nChecker SHA256 {args.source_sha256}\n')
    passed = False
    try:
        old_manifest = json.loads((PRIOR_RECORD/'MANIFEST.json').read_text())
        for item in old_manifest['inputs']+old_manifest['outputs']:
            require('prior manifest identity', identity(Path(item['path'])) == item)
        saved = json.loads((PRIOR_RECORD/'RESULTS.json').read_text())
        models, references = qualify(saved)
        qualification_count = sum(CHECKS.values())
        with log.open('a') as handle:
            handle.write(f'Qualification PASS: {qualification_count} assertions including freeze/identity checks.\n')
        cases, all_traces = [], {}
        with (output/'UPDATES.jsonl').open('w') as events:
            for model in models:
                for treatment, epsilon in TREATMENTS.items():
                    for schedule in SCHEDULES:
                        case_id = f"h={model['h']}/{treatment}/{schedule}"
                        initial = snapshot(model, epsilon, HALF, HALF, 0, 0, '', False)
                        trace = [initial]
                        events.write(json.dumps({'case_id': case_id, **initial}, default=str)+'\n')
                        events.flush()
                        for sweep in range(1, SWEEPS+1):
                            states = advance(model, trace[-1]['x'], trace[-1]['y'], epsilon, schedule)
                            for phase, (updated, x, y) in enumerate(states, 1):
                                state = snapshot(model, epsilon, x, y, sweep, phase,
                                                 updated, phase == len(states))
                                state['true_vfe_change'] = state['true_vfe']-trace[-1]['true_vfe']
                                events.write(json.dumps({'case_id': case_id, **state}, default=str)+'\n')
                                events.flush()
                                if treatment == 'exact' and schedule != 'simultaneous':
                                    require('exact sequential coordinate descent', state['true_vfe_change'] <= TOL)
                                if schedule == 'simultaneous':
                                    require('simultaneous symmetry', x == y)
                                trace.append(state)
                        final = trace[-1]
                        exact = model['exact_decision']
                        cases.append({'case_id': case_id, 'baseline': model['h'],
                                      'treatment': treatment, 'epsilon': epsilon, 'schedule': schedule,
                                      'final': final, 'update_events': len(trace)-1,
                                      'final_distance_to_each_global_minimum':
                                      [max(abs(final['x']-m['x']), abs(final['y']-m['y']))
                                       for m in model['minima']],
                                      'task_value_loss_vs_exact': exact['exact_model_task_value']-
                                      final['policy']['exact_model_task_value'],
                                      'reference_score_excess_vs_exact': final['policy']['exact_model_reference_score']-
                                      exact['exact_model_reference_score'],
                                      'diagnostic_candidate_risk_range':
                                      [min(s['policy']['exact_model_policy_risk'] for s in trace),
                                       max(s['policy']['exact_model_policy_risk'] for s in trace)],
                                      'true_vfe_increase_events': sum(s.get('true_vfe_change', ZERO) > TOL for s in trace)})
                        all_traces[case_id] = trace
                        with log.open('a') as handle:
                            handle.write(f"Completed {case_id}: sixteen sweeps, {len(trace)-1} update events.\n")
        lookup = {(c['baseline'], c['treatment'], c['schedule']): c for c in cases}
        contrasts = []
        for model in models:
            h = model['h']
            for treatment in TREATMENTS:
                r, l, s = [lookup[h, treatment, schedule] for schedule in SCHEDULES]
                for a, b in zip(all_traces[r['case_id']], all_traces[l['case_id']]):
                    close('order-swap x/y', a['x'], b['y'])
                    close('order-swap y/x', a['y'], b['x'])
                    close('order-swap VFE', a['true_vfe'], b['true_vfe'])
                    close('order-swap precision forecast', a['policy']['failure_risks'][1],
                          b['policy']['failure_risks'][1])
                contrasts.extend([contrast(r, l), contrast(r, s), contrast(l, s)])
            for schedule in SCHEDULES:
                contrasts.append(contrast(lookup[h, 'source_epsilon', schedule], lookup[h, 'exact', schedule]))
        require('twelve complete cases', len(cases) == 12)
        require('320 atomic update events', sum(c['update_events'] for c in cases) == 320)
        require('192 completed sweeps', sum(s['sweep_endpoint'] for t in all_traces.values() for s in t) == 192)
        require('frozen inputs unchanged', inputs == [identity(p) for p in input_paths])
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'check_tolerance': TOL,
                  'eta': ETA, 'sweeps_per_case': SWEEPS, 'factor_updates': 384,
                  'atomic_update_events': 320, 'event_records_including_initial': 332,
                  'references': references, 'cases': cases, 'contrasts': contrasts,
                  'qualification_assertions': qualification_count, 'assertion_count': sum(CHECKS.values()),
                  'assertions_by_label': dict(CHECKS), 'max_identity_residual': MAX_RESIDUAL,
                  'elapsed_seconds': perf_counter()-begin}
        dump(output/'RESULTS.json', result)
        with log.open('a') as handle:
            handle.write(f"PASS {result['assertion_count']} assertions; max identity residual {MAX_RESIDUAL}.\n"
                         f"Elapsed {result['elapsed_seconds']:.9f} seconds through validation.\n")
        passed = True
    except BaseException:
        with log.open('a') as handle:
            handle.write(traceback.format_exc())
        raise
    finally:
        manifest['status'] = 'passed' if passed else 'failed'
        manifest['outputs'] = [identity(p) for p in sorted(output.iterdir())
                               if p.is_file() and p.name != 'MANIFEST.json']
        dump(output/'MANIFEST.json', manifest)
    print(json.dumps({'status': 'passed', 'output': str(output), 'cases': len(cases),
                      'assertions': result['assertion_count'], 'elapsed_seconds': perf_counter()-begin}))


if __name__ == '__main__':
    main()
