#!/usr/bin/env python3
"""Independent normalized Bayes recursion and complete-noise-string readback."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    a = Path(sys.argv[1])
    counts = {}
    noise_paths = 0

    def check(name, passed):
        counts[name] = counts.get(name, 0)+1
        if not passed:
            raise AssertionError(name)

    def load(name):
        return json.loads((a/name).read_text())

    manifest, freeze, result = load('MANIFEST.json'), load('FREEZE.json'), load('RESULTS.json')
    check('completed', manifest['status'] == 'COMPLETE')
    for name, identity in manifest['outputs'].items():
        check('output_hash', digest(a/name) == identity)
    for name, identity in freeze['inputs'].items():
        check('input_hash', digest(name) == identity)
    for name, identity in freeze['snapshots'].items():
        check('snapshot_hash', digest(a/'inputs'/name) == identity)

    def verify_case(case, main_case):
        nonlocal noise_paths
        T, eta, rho = case['T'], case['eta'], Q(case['rho'])
        eps, price = Q(eta, 20), Q(1, 10)
        prior = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        check('case_price', Q(case['c']) == price and case['noise_denominator'] == 20)
        if main_case:
            check('main_parameters', T == 10 and rho == Q(1, 2) and eta in (0, 1))

        def orientation(t, j):
            return int(j > 0 and j <= t)

        def posterior(t, weights, label):
            likelihood = [eps if label != orientation(t, j) else 1-eps for j in range(T+1)]
            raw = [w*l for w, l in zip(weights, likelihood)]
            probability = sum(raw)/sum(weights)
            if probability == 0:
                return Q(0), None
            integers = [int(v*20) for v in raw]
            common = math.gcd(*integers)
            updated = tuple(v//common for v in integers)
            return probability, updated

        def immediates(t, weights, lam):
            q = [Q(w, sum(weights)) for w in weights]
            F, R, B = Q(0), Q(0), Q(0)
            for j, probability in enumerate(q):
                z = orientation(t, j)
                utility = Q(1, T)+(Q(lam, 1)/(rho*(T-j+1)) if z else 0)
                error = 1-eps if z else eps
                F += probability*utility*error
                R += probability*utility*(1-error)
                B += probability*utility*price
            return {'F': F, 'R': R, 'B': B}

        def choose(scores):
            minimum = min(scores.values())
            return next(a for a in ('B', 'F', 'R') if scores[a] == minimum)

        @lru_cache(None)
        def value(t, weights, h, lam, erased):
            if not h:
                return Q(0)
            return min(scores(t, weights, h, lam, erased).values())

        def scores(t, weights, h, lam, erased):
            values = immediates(t, weights, lam)
            continuation = value(t+1, weights, h-1, lam, erased)
            values['F'] += continuation
            values['R'] += continuation
            if erased:
                values['B'] += continuation
            else:
                for label in (0, 1):
                    probability, updated = posterior(t, weights, label)
                    if probability:
                        values['B'] += probability*value(t+1, updated, h-1, lam, False)
            return values

        totals = {}
        for arm, policy in case['policies'].items():
            lam = 1 if arm in ('recovery', 'erased') else 0
            erased, cap = arm == 'erased', arm == 'hybrid'
            graph = policy['graph']
            check('root_information', graph[0]['t'] == 1 and tuple(graph[0]['weights']) == prior and graph[0]['clock'] == 0)
            reachable = {0}
            # Edges are checked using Bayes' rule, without physical onsets.
            before_p, after_p = {}, {}
            for i in sorted(range(len(graph)), key=lambda i: graph[i]['t']):
                node = graph[i]
                t, weights, clock = node['t'], tuple(node['weights']), node['clock']
                check('graph_reachable', i in reachable)
                check('posterior_support', len(weights) == T+1 and min(weights) >= 0 and sum(weights) > 0 and math.gcd(*weights) == 1)
                if eta > 0:
                    check('no_noisy_certainty', all(w > 0 for w in weights))
                if erased:
                    check('erased_memory', weights == prior)
                h = min(4, T-t+1) if cap else T-t+1
                expected = 'B' if cap and clock else choose(scores(t, weights, h, lam, erased))
                check('independent_action', expected == node['action'])
                check('clock_range', clock in (0, 1) and (cap or clock == 0))
                if cap and clock:
                    check('compulsory_clock', node['action'] == 'B')
                before_p[i] = Q(sum(weights[1:t+1]), sum(weights))
                if node['action'] == 'B':
                    expected_labels = set()
                    for label in (0, 1):
                        probability, updated = posterior(t, weights, label)
                        if not probability:
                            continue
                        expected_labels.add(str(label))
                        retained = weights if erased else updated
                        after_p[i, label] = Q(sum(retained[1:t+1]), sum(retained))
                        child = node['children'][str(label)]
                        if t == T:
                            check('terminal_edge', child is None)
                        else:
                            check('bought_edge', child is not None and graph[child]['t'] == t+1
                                  and tuple(graph[child]['weights']) == retained and graph[child]['clock'] == 0)
                            reachable.add(child)
                    check('label_support', set(node['children']) == expected_labels)
                else:
                    check('unpaid_observation_mask', set(node['children']) == {'N'})
                    child = node['children']['N']
                    if t == T:
                        check('terminal_edge', child is None)
                    else:
                        check('unpaid_edge', child is not None and graph[child]['t'] == t+1
                              and tuple(graph[child]['weights']) == weights and graph[child]['clock'] == int(cap))
                        reachable.add(child)
            check('complete_graph', len(reachable) == len(graph))
            if arm != 'hybrid':
                check('independent_root', value(1, prior, T, lam, erased) == Q(policy['root_value']))
            check('world_order', [w['onset'] for w in policy['worlds']] == [None, *range(1, T+1)])
            reconstructed = []
            # Replay saved graph actions for every complete noise string. No policy calls.
            denominator = 20**T
            streams = []
            for mask in range(1 << T):
                ones = mask.bit_count()
                mass = eta**ones*(20-eta)**(T-ones)
                if mass:
                    streams.append((mask, mass))
            check('noise_probability_total', sum(mass for _, mass in streams) == denominator)
            for saved in policy['worlds']:
                tau = saved['onset']
                cost_ticks = error_mass = buy_mass = post_ticks = post_error_mass = post_buy_mass = 0
                delay_mass = missing_mass = 0
                visits, first_visits = {}, {}
                for mask, mass in streams:
                    noise_paths += 1
                    node_id, errors, buys, post_errors, post_buys, first = 0, 0, 0, 0, 0, None
                    for t in range(1, T+1):
                        node = graph[node_id]
                        visits[node_id] = visits.get(node_id, 0)+mass
                        changed = tau is not None and t >= tau
                        label = int(changed)^((mask >> (t-1)) & 1)
                        action = node['action']
                        error = int(action != 'B' and (action == 'R') != bool(label))
                        buy = int(action == 'B')
                        errors += error
                        buys += buy
                        if changed:
                            post_errors += error
                            post_buys += buy
                            if buy and first is None:
                                first = t
                                key = (node_id, label)
                                first_visits[key] = first_visits.get(key, 0)+mass
                        node_id = node['children'][str(label) if buy else 'N']
                    check('noise_path_terminal', node_id is None)
                    cost_ticks += mass*(10*errors+buys)
                    error_mass += mass*errors
                    buy_mass += mass*buys
                    post_ticks += mass*(10*post_errors+post_buys)
                    post_error_mass += mass*post_errors
                    post_buy_mass += mass*post_buys
                    if first is None:
                        missing_mass += mass
                    if tau is not None:
                        delay_mass += mass*(T-tau+1 if first is None else first-tau)
                brier = sum(mass*(before_p[i]-int(tau is not None and graph[i]['t'] >= tau))**2
                            for i, mass in visits.items())/denominator
                first_brier = sum(mass*(after_p[key]-1)**2 for key, mass in first_visits.items())/denominator
                rebuilt = {'cost': Q(cost_ticks, 10*denominator), 'errors': Q(error_mass, denominator),
                           'purchases': Q(buy_mass, denominator), 'brier': brier,
                           'post_cost': Q(post_ticks, 10*denominator), 'post_errors': Q(post_error_mass, denominator),
                           'post_purchases': Q(post_buy_mass, denominator), 'delay': Q(delay_mass, denominator),
                           'missing': Q(missing_mass, denominator), 'first_brier_mass': first_brier,
                           'onset': tau}
                rebuilt['recovery'] = None if tau is None else rebuilt['post_cost']/(T-tau+1)
                rebuilt['first_brier_conditional'] = first_brier/(1-rebuilt['missing']) if tau is not None and rebuilt['missing'] < 1 else None
                for field, actual in rebuilt.items():
                    check('world_'+field, (actual is None and saved[field] is None) or
                          (actual is not None and actual == Q(saved[field])))
                floor = min(eps, price)
                check('full_known_orientation_floor', rebuilt['cost']/T >= floor)
                if tau is not None:
                    check('recovery_known_orientation_floor', rebuilt['recovery'] >= floor)
                reconstructed.append(rebuilt)
            worlds = reconstructed
            stable = worlds[0]['cost']/T
            changed = sum(w['cost'] for w in worlds[1:])/(T*T)
            B, R = (1-rho)*stable+rho*changed, sum(w['recovery'] for w in worlds[1:])/T
            missing = sum(w['missing'] for w in worlds[1:])/T
            first_mass = sum(w['first_brier_mass'] for w in worlds[1:])/T
            summary = {'stable': stable, 'changed_full': changed, 'B': B, 'R': R,
                       'J': B+lam*R, 'lambda': lam,
                       'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
                       'stable_orientation_brier': worlds[0]['brier']/T,
                       'mean_changed_errors': sum(w['errors'] for w in worlds[1:])/T,
                       'mean_changed_purchases': sum(w['purchases'] for w in worlds[1:])/T,
                       'mean_post_errors': sum(w['post_errors'] for w in worlds[1:])/T,
                       'mean_post_purchases': sum(w['post_purchases'] for w in worlds[1:])/T,
                       'capped_first_delay': sum(w['delay'] for w in worlds[1:])/T,
                       'no_post_purchase_probability': missing,
                       'first_brier_conditional': first_mass/(1-missing) if missing < 1 else None}
            for field, actual in summary.items():
                check('summary_'+field, (actual is None and policy['summary'][field] is None) or
                      (actual is not None and actual == Q(policy['summary'][field])))
            if arm != 'hybrid':
                check('world_bellman_identity', summary['J'] == Q(policy['root_value']))
            totals[arm] = summary
        r, o, h, e = (totals[k] for k in ('recovery', 'ordinary', 'hybrid', 'erased'))
        gate = {'below_always': r['R'] < price, 'below_hybrid': r['R'] < h['R'],
                'stable_not_higher': r['stable'] <= h['stable']}
        gate['joint'] = all(gate.values())
        check('feasibility_gate', case['gate'] == gate)
        check('ordinary_optimum', o['B'] <= r['B'] and o['B'] <= h['B'] and o['B'] <= price)
        check('recovery_preference_ordering', r['R'] <= o['R'] and r['J'] <= o['B']+o['R'])
        check('retention_value', r['J'] <= e['J'])
        check('analytic_always', all(Q(x) == price for x in case['always'].values()))
        check('saved_floor', Q(case['known_orientation_floor']) == min(eps, price))
        return {'gate': gate, 'nodes': {k: len(v['graph']) for k, v in case['policies'].items()}}

    fixtures = load('SHORT_FIXTURES.json')
    for fixture in fixtures:
        verify_case(fixture, False)
    check('main_condition_names', set(result['conditions']) == {'0', '1'} and result['main_condition'] == '1')
    main_summaries = {name: verify_case(case, True) for name, case in result['conditions'].items()}
    q = load('QUALIFICATION.json')['noisy_contradictions']
    weights = [10]+[1]*10
    for t, field, target in [(1, 'after_first', Q(1, 2)), (2, 'after_second', Q(190, 199))]:
        weights = [w*(19 if 0 < j <= t else 1) for j, w in enumerate(weights)]
        posterior = Q(sum(weights[1:t+1]), sum(weights))
        check('contradiction_update', posterior == target == Q(q[field]))
        check('no_support_elimination', min(weights) > 0)
    started = load('STARTED.json')
    check('resources', 1 <= len(started['affinity']) <= 4 and started['nice'] >= 10)
    check('detachment', load('BENCHMARK.json')['forecast_seconds'] <= 600 or started['detached'])
    record = {'passed': True, 'completed': datetime.now(timezone.utc).isoformat(),
              'seconds': time.monotonic()-start, 'checks': counts, 'total_checks': sum(counts.values()),
              'saved_graph_noise_paths_enumerated': noise_paths,
              'verification_method': 'Independent normalized optimality recursion and exact replay of saved graph actions over all noise strings; no new samples.',
              'conditions': main_summaries, 'manifest_sha256': digest(a/'MANIFEST.json'),
              'source_sha256': digest(__file__)}
    with (a/'READBACK.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
