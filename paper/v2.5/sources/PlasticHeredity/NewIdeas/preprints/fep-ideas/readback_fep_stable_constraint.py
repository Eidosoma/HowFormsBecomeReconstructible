#!/usr/bin/env python3
"""Independent normalized Bellman and forward-occupancy certificate verifier."""
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    a = Path(sys.argv[1])
    counts, totals = {}, {'graphs': 0, 'nodes': 0, 'worlds': 0, 'certificates': 0}

    def check(name, result):
        counts[name] = counts.get(name, 0)+1
        if not result:
            raise AssertionError(name)

    def read(name):
        return json.loads((a/name).read_text())

    manifest, freeze = read('MANIFEST.json'), read('FREEZE.json')
    check('completed', manifest['status'] == 'COMPLETE')
    for name, identity in manifest['outputs'].items():
        check('output_hash', digest(a/name) == identity)
    for name, identity in freeze['inputs'].items():
        check('input_hash', digest(name) == identity)
    for name, identity in freeze['snapshots'].items():
        check('snapshot_hash', digest(a/'inputs'/name) == identity)
    refpath = next(Path(name) for name in freeze['inputs'] if name.endswith('/RESULTS.json'))
    references = json.loads(refpath.read_text())['conditions']

    def verify(case, main_case):
        T, eta, rho = case['T'], case['eta'], Q(case['rho'])
        eps, price, budget = Q(eta, 20), Q(1, 10), Q(case['budget'])
        prior = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        check('physical_parameters', Q(case['c']) == price and case['noise_denominator'] == 20)
        if main_case:
            check('main_parameters', T == 10 and rho == Q(1, 2) and eta in (0, 1))
            check('fixed_budget', budget == Q(references[str(eta)]['policies']['hybrid']['summary']['stable']))

        def changed(t, j):
            return 0 < j <= t

        def update(t, weights, label):
            raw = [w*(20-eta if label == int(changed(t, j)) else eta) for j, w in enumerate(weights)]
            probability = Q(sum(raw), 20*sum(weights))
            common = math.gcd(*raw)
            return probability, tuple(v//common for v in raw) if common else None

        def summarize(worlds, alpha):
            S = worlds[0]['cost']/T
            B = (1-rho)*S+rho*sum(w['cost'] for w in worlds[1:])/(T*T)
            R = sum(w['recovery'] for w in worlds[1:])/T
            return {'stable': S, 'B': B, 'R': R, 'J': B+R, 'C': alpha*B+R,
                    'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
                    'mean_changed_errors': sum(w['errors'] for w in worlds[1:])/T,
                    'mean_changed_purchases': sum(w['purchases'] for w in worlds[1:])/T,
                    'mean_post_errors': sum(w['post_errors'] for w in worlds[1:])/T,
                    'mean_post_purchases': sum(w['post_purchases'] for w in worlds[1:])/T,
                    'capped_first_delay': sum(w['delay'] for w in worlds[1:])/T,
                    'no_post_purchase_probability': sum(w['missing'] for w in worlds[1:])/T}

        def equal_fields(saved, actual, prefix):
            check(prefix+'_keys', set(saved) == set(actual))
            for key, value in actual.items():
                check(prefix+'_'+key, saved[key] is None if value is None else Q(saved[key]) == value)

        for name, problem in case['problems'].items():
            alpha, erased = problem['alpha'], problem['erased']
            check('problem_scope', alpha == (1 if name.endswith('_primary') else 0)
                  and erased == name.startswith('erased') and Q(problem['budget']) == budget)
            rebuilt_policies = {}
            for pid, policy in problem['policies'].items():
                graph = policy['graph']
                mu = None if policy['mu'] is None else Q(policy['mu'])
                totals['graphs'] += 1
                totals['nodes'] += len(graph)

                @lru_cache(None)
                def value(t, weights):
                    return Q(0) if t > T else min(scores(t, weights).values())

                def scores(t, weights):
                    n = sum(weights)
                    out = dict(F=Q(0), R=Q(0), B=Q(0))
                    for j, w in enumerate(weights):
                        z = changed(t, j)
                        utility = Q(alpha, T)+(1/(rho*(T-j+1)) if z else 0)
                        if j == 0:
                            utility += mu/((1-rho)*T)
                        factor = Q(w, n)*utility
                        forward_risk = 1-eps if z else eps
                        out['F'] += factor*forward_risk
                        out['R'] += factor*(1-forward_risk)
                        out['B'] += factor*price
                    later = value(t+1, weights)
                    out['F'] += later
                    out['R'] += later
                    if erased:
                        out['B'] += later
                    else:
                        for label in (0, 1):
                            probability, posterior = update(t, weights, label)
                            if probability:
                                out['B'] += probability*value(t+1, posterior)
                    return out

                check('initial_beliefs', graph[0]['t'] == 1 and tuple(graph[0]['weights']) == prior)
                reachable = {0}
                order = sorted(range(len(graph)), key=lambda i: graph[i]['t'])
                for i in order:
                    node = graph[i]
                    t, weights, action = node['t'], tuple(node['weights']), node['action']
                    check('graph_reachable', i in reachable)
                    check('valid_beliefs', len(weights) == T+1 and math.gcd(*weights) == 1
                          and min(weights) >= 0 and sum(weights) > 0)
                    check('no_hidden_interface', set(node) == {'t', 'weights', 'clock', 'action', 'children'}
                          and node['clock'] == 0)
                    if eta > 0:
                        check('positive_noise_support', min(weights) > 0)
                    if erased:
                        check('erased_beliefs', weights == prior)
                    if mu is not None:
                        choices = scores(t, weights)
                        expected = min(('B', 'F', 'R'), key=lambda x: choices[x])
                        check('optimal_saved_action', action == expected)
                    else:
                        check('floor_policy', action == ('F' if eps <= price else 'B'))
                    branches = {}
                    if action == 'B':
                        for label in (0, 1):
                            probability, posterior = update(t, weights, label)
                            if probability:
                                branches[str(label)] = weights if erased else posterior
                    else:
                        branches['N'] = weights
                    check('observation_mask', set(branches) == set(node['children']))
                    for label, posterior in branches.items():
                        child = node['children'][label]
                        if t == T:
                            check('terminal', child is None)
                        else:
                            check('posterior_edge', child is not None and graph[child]['t'] == t+1
                                  and tuple(graph[child]['weights']) == posterior)
                            reachable.add(child)
                check('complete_graph', len(reachable) == len(graph))
                if mu is not None:
                    check('independent_root', value(1, prior) == Q(policy['root']))
                value.cache_clear()

                worlds = []
                check('world_order', [w['onset'] for w in policy['worlds']] == [None, *range(1, T+1)])
                for saved in policy['worlds']:
                    tau = saved['onset']
                    # Probability flow tracks whether a post-change purchase
                    # has occurred, without calling a policy or Bellman solver.
                    flow = {(0, False): Q(1)}
                    totals['worlds'] += 1
                    row = {k: Q(0) for k in ('cost', 'errors', 'purchases', 'post_cost',
                                             'post_errors', 'post_purchases', 'delay', 'missing')}
                    terminal_mass = Q(0)
                    for i in order:
                        node = graph[i]
                        t, action = node['t'], node['action']
                        z = tau is not None and t >= tau
                        error = Q(0) if action == 'B' else eps if (action == 'R') == z else 1-eps
                        buy = int(action == 'B')
                        cost = error+price*buy
                        for hit in (False, True):
                            mass = flow.get((i, hit), Q(0))
                            if not mass:
                                continue
                            row['cost'] += mass*cost
                            row['errors'] += mass*error
                            row['purchases'] += mass*buy
                            if z:
                                row['post_cost'] += mass*cost
                                row['post_errors'] += mass*error
                                row['post_purchases'] += mass*buy
                            if z and not hit and not buy:
                                row['delay'] += mass
                            new_hit = hit or bool(z and buy)
                            branches = [('N', Q(1))] if not buy else [('0', eps if z else 1-eps),
                                                                    ('1', 1-eps if z else eps)]
                            for label, probability in branches:
                                if not probability:
                                    continue
                                child = node['children'][label]
                                amount = mass*probability
                                if child is None:
                                    terminal_mass += amount
                                    if not new_hit:
                                        row['missing'] += amount
                                else:
                                    key = child, new_hit
                                    flow[key] = flow.get(key, Q(0))+amount
                    # With no reversal there is no post-change purchase, so
                    # missing remains 1 and delay 0, matching the saved schema.
                    check('world_probability', terminal_mass == 1)
                    row['onset'] = tau
                    row['recovery'] = None if tau is None else row['post_cost']/(T-tau+1)
                    equal_fields(saved, row, 'world')
                    check('world_floor', row['cost']/T >= min(eps, price))
                    worlds.append(row)
                s = summarize(worlds, alpha)
                equal_fields(policy['summary'], s, 'summary')
                if mu is not None:
                    check('world_scalar_identity', s['C']+mu*s['stable'] == Q(policy['root']))
                rebuilt_policies[pid] = dict(worlds=worlds, summary=s)

            solution = problem['solution']
            components = solution['components']
            check('mixture_count', 1 <= len(components) <= 2)
            check('mixture_probability', all(Q(p['weight']) > 0 for p in components)
                  and sum(Q(p['weight']) for p in components) == 1)
            worlds = []
            for i, saved in enumerate(solution['worlds']):
                world = {}
                for key in saved:
                    if key == 'onset':
                        world[key] = None if i == 0 else i
                    elif i == 0 and key == 'recovery':
                        world[key] = None
                    else:
                        world[key] = sum(Q(p['weight'])*rebuilt_policies[p['policy']]['worlds'][i][key]
                                         for p in components)
                equal_fields(saved, world, 'mixture_world')
                worlds.append(world)
            s = summarize(worlds, alpha)
            equal_fields(solution['summary'], s, 'mixture_summary')
            cert = problem['certificate']
            mu = Q(cert['mu'])
            witness = problem['policies'][cert['oracle']]
            check('dual_multiplier', mu >= 0 and mu == Q(witness['mu']))
            lower = Q(witness['root'])-mu*budget
            check('primal_feasible', s['stable'] <= budget)
            check('dual_certificate', s['C'] == lower == Q(cert['lower_bound']) and Q(cert['duality_gap']) == 0)
            check('complementarity', mu*(budget-s['stable']) == 0)
            for component in components:
                cs = rebuilt_policies[component['policy']]['summary']
                check('supporting_policy', cs['C']+mu*cs['stable'] == Q(witness['root']))
            totals['certificates'] += 1
            check('oracle_ceiling', problem['oracle_calls'] == sum(p.startswith('oracle') for p in problem['policies']) <= 128)
            best = problem['best_saved_feasible_deterministic']
            candidates = [p['summary']['C'] for p in rebuilt_policies.values() if p['summary']['stable'] <= budget]
            check('saved_deterministic', rebuilt_policies[best]['summary']['stable'] <= budget
                  and rebuilt_policies[best]['summary']['C'] == min(candidates))
            for step in problem['trace']:
                pi = problem['policies'][step['oracle']]
                if 'low' in step:
                    low = rebuilt_policies[step['low']]['summary']
                    high = rebuilt_policies[step['high']]['summary']
                    slope = (low['C']-high['C'])/(high['stable']-low['stable'])
                    chord = low['C']+slope*low['stable']
                    check('search_bracket', low['stable'] <= budget < high['stable'])
                    check('search_multiplier', Q(pi['mu']) == slope and Q(step['chord']) == chord)
                    check('search_lower_bound', Q(pi['root']) <= chord)
            if main_case:
                hr = Q(references[str(eta)]['policies']['hybrid']['summary']['R'])
                g = {'below_always': s['R'] < price, 'below_hybrid': s['R'] < hr,
                     'stable_not_higher': s['stable'] <= budget}
                g['joint'] = all(g.values())
                check('scientific_gate', problem['gate'] == g)
                if alpha == 1:
                    before = references[str(eta)]['policies']['erased' if erased else 'recovery']['worlds']
                    now = rebuilt_policies['oracle000']['worlds']
                    for x, y in zip(now, before):
                        for key in x:
                            check('frozen_control', y[key] is None if x[key] is None else Q(y[key]) == x[key])

    result = read('RESULTS.json')
    check('main_conditions', set(result['conditions']) == {'0', '1'} and result['main_condition'] == '1')
    for case in result['conditions'].values():
        verify(case, True)
    for case in read('SHORT_FIXTURES.json'):
        verify(case, False)
    resources, benchmark = read('STARTED.json'), read('BENCHMARK.json')
    check('resources', len(resources['affinity']) == 1 and resources['nice'] >= 10)
    check('detachment', benchmark['forecast_seconds'] <= 600 or resources['detached'])
    output = {'passed': True, 'completed': datetime.now(timezone.utc).isoformat(),
              'seconds': time.monotonic()-start, 'checks': counts, 'total_checks': sum(counts.values()),
              'totals': totals, 'manifest_sha256': digest(a/'MANIFEST.json'),
              'source_sha256': digest(__file__),
              'method': 'Independent normalized Bellman recursion, forward saved-graph occupancy, and exact primal/dual equality.'}
    with (a/'READBACK.json').open('x') as stream:
        json.dump(output, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'checks': output['total_checks'], 'seconds': output['seconds'],
                      'totals': totals}, sort_keys=True))


if __name__ == '__main__':
    main()
