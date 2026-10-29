#!/usr/bin/env python3
"""Independent full-policy integer occupancy and fixed-anchor Bellman check."""
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
    started = time.monotonic()
    directory = Path(sys.argv[1])
    checks, totals = {}, dict(candidates=0, candidate_worlds=0, continuation_states=0, selected_graphs=0)

    def check(name, condition):
        checks[name] = checks.get(name, 0)+1
        if not condition:
            raise AssertionError(name)

    def load(name):
        return json.loads((directory/name).read_text())

    manifest, freeze = load('MANIFEST.json'), load('FREEZE.json')
    check('completed', manifest['status'] == 'COMPLETE')
    for name, identity in manifest['outputs'].items():
        check('output_hash', digest(directory/name) == identity)
    for name, identity in freeze['inputs'].items():
        check('input_hash', digest(name) == identity)
    for name, identity in freeze['snapshots'].items():
        check('snapshot_hash', digest(directory/'inputs'/name) == identity)
    paths = [Path(p) for p in freeze['inputs'] if p.endswith('/RESULTS.json')]
    previous_path = next(p for p in paths if 'fep-stable-constraint-v1' in str(p))
    noisy_path = next(p for p in paths if 'fep-noisy-recovery-v1' in str(p))
    previous, noisy = json.loads(previous_path.read_text()), json.loads(noisy_path.read_text())
    for path in paths:
        old_readback = json.loads((path.parent/'READBACK.json').read_text())
        check('inherited_readback', old_readback['passed'] and
              old_readback['manifest_sha256'] == digest(path.parent/'MANIFEST.json'))
        old_manifest = json.loads((path.parent/'MANIFEST.json').read_text())
        check('inherited_result', old_manifest['outputs']['RESULTS.json'] == digest(path))

    def verify(case, main_case):
        T, eta, rho, mu = case['T'], case['eta'], Q(case['rho']), Q(case['anchor_mu'])
        price, eps = Q(1, 10), Q(eta, 20)
        budget, hybrid_R = Q(case['budget']), Q(case['hybrid_R'])
        prior = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        nodes, nbase = case['nodes'], case['base_node_count']
        check('parameters', Q(case['c']) == price and case['noise_denominator'] == 20)
        if main_case:
            check('main_parameters', T == 10 and eta == 1 and rho == Q(1, 2))
            old_problem = previous['conditions']['1']['problems']['retained_primary']
            old_hybrid = noisy['conditions']['1']['policies']['hybrid']['summary']
            check('fixed_budget', budget == Q(old_problem['budget']) == Q(old_hybrid['stable'])
                  == Q(19568652557, 204800000000))
            check('frozen_comparator', hybrid_R == Q(old_hybrid['R']))
            anchors = [c['policy'] for c in old_problem['solution']['components']
                       if Q(old_problem['policies'][c['policy']]['summary']['stable']) > budget]
            check('fixed_anchor', len(anchors) == 1 and case['anchor_reference'] == anchors[0])
            anchor = old_problem['policies'][anchors[0]]
            check('anchor_multiplier', mu == Q(anchor['mu']))
            check('anchor_graph', nodes[:nbase] == anchor['graph'])
            check('randomized_bound', Q(case['randomized_J_bound']) == Q(old_problem['solution']['summary']['J']))
            for label, cond, problem in [('noiseless_min_R', '0', 'retained_recovery_bound'),
                                          ('noisy_erased_min_R', '1', 'erased_recovery_bound')]:
                p = previous['conditions'][cond]['problems'][problem]
                cert = p['certificate']
                check('inherited_feasibility_bound', Q(case['inherited_bounds'][label]) == Q(p['solution']['summary']['R']) > price)
                check('inherited_certificate', Q(cert['duality_gap']) == 0
                      and Q(cert['lower_bound']) == Q(p['solution']['summary']['R'])
                      and Q(p['policies'][cert['oracle']]['root'])-Q(cert['mu'])*Q(p['budget']) == Q(cert['lower_bound']))

        def posterior(t, weights, label):
            raw = [w*(20-eta if label == int(0 < j <= t) else eta) for j, w in enumerate(weights)]
            probability = Q(sum(raw), 20*sum(weights))
            common = math.gcd(*raw)
            return probability, tuple(v//common for v in raw) if common else None

        @lru_cache(None)
        def value(t, weights):
            return Q(0) if t > T else min(scores(t, weights).values())

        def scores(t, weights):
            result = dict(F=Q(0), R=Q(0), B=Q(0))
            for j, mass in enumerate(weights):
                z = 0 < j <= t
                utility = Q(1, T)+(1/(rho*(T-j+1)) if z else 0)
                if j == 0:
                    utility += mu/((1-rho)*T)
                w = Q(mass, sum(weights))*utility
                risk = 1-eps if z else eps
                result['F'] += w*risk
                result['R'] += w*(1-risk)
                result['B'] += w*price
            later = value(t+1, weights)
            result['F'] += later
            result['R'] += later
            for label in (0, 1):
                probability, updated = posterior(t, weights, label)
                if probability:
                    result['B'] += probability*value(t+1, updated)
            return result

        def edges(node, action, children, graph):
            t, weights = node['t'], tuple(node['weights'])
            expected = {'N': weights} if action != 'B' else {}
            if action == 'B':
                for label in (0, 1):
                    probability, updated = posterior(t, weights, label)
                    if probability:
                        expected[str(label)] = updated
            check('observation_mask', set(children) == set(expected))
            for label, child in children.items():
                if t == T:
                    check('terminal_edge', child is None)
                else:
                    check('posterior_edge', child is not None and graph[child]['t'] == t+1
                          and tuple(graph[child]['weights']) == expected[label])

        keys = set()
        for node in nodes:
            check('interface', set(node) == {'t', 'weights', 'clock', 'action', 'children'} and node['clock'] == 0)
            weights, t = tuple(node['weights']), node['t']
            key = t, weights
            check('deterministic_state_reuse', key not in keys)
            keys.add(key)
            check('posterior_support', len(weights) == T+1 and min(weights) >= 0
                  and sum(weights) > 0 and math.gcd(*weights) == 1 and 1 <= t <= T)
            if eta > 0:
                check('positive_support', min(weights) > 0)
            possible = scores(t, weights)
            expected = min(('B', 'F', 'R'), key=lambda a: possible[a])
            check('fixed_anchor_action', node['action'] == expected)
            edges(node, node['action'], node['children'], nodes)
        check('root_beliefs', nodes[0]['t'] == 1 and tuple(nodes[0]['weights']) == prior)
        root = value(1, prior)
        if main_case:
            check('independent_anchor_root', root == Q(anchor['root']))
        value.cache_clear()

        def forward(graph, override, tau, diagnostics=False):
            order = sorted(range(len(graph)), key=lambda i: graph[i]['t'])
            powers = [20**i for i in range(T+1)]
            # Each state's integer mass has denominator 20^(t-1).
            flows = {(0, False): 1}
            sums = [0]*4
            missing = delay = terminal = 0
            visits = set()
            override_mass = 0
            for i in order:
                node = graph[i]
                t = node['t']
                replace = override is not None and override['state'] == i
                action = override['action'] if replace else node['action']
                children = override['children'] if replace else node['children']
                post = tau is not None and t >= tau
                error = 0 if action == 'B' else eta if (action == 'R') == post else 20-eta
                buy = int(action == 'B')
                for hit in ((False, True) if diagnostics else (False,)):
                    mass = flows.get((i, hit), 0)
                    if not mass:
                        continue
                    visits.add(i)
                    if replace:
                        override_mass += mass
                    errors = mass*error*powers[T-t]
                    buys = mass*buy*powers[T-t+1]
                    sums[0] += errors
                    sums[1] += buys
                    if post:
                        sums[2] += errors
                        sums[3] += buys
                        if diagnostics and not hit and not buy:
                            delay += mass*powers[T-t+1]
                    new_hit = bool(diagnostics and (hit or (post and buy)))
                    branches = [('N', 20)] if not buy else [('0', eta if post else 20-eta),
                                                           ('1', 20-eta if post else eta)]
                    for label, likelihood in branches:
                        if not likelihood:
                            continue
                        child, amount = children[label], mass*likelihood
                        if child is None:
                            terminal += amount
                            if not new_hit:
                                missing += amount
                        else:
                            k = child, new_hit
                            flows[k] = flows.get(k, 0)+amount
            check('integer_probability', terminal == powers[T])
            e, b, pe, pb = (Q(x, powers[T]) for x in sums)
            row = dict(onset=tau, errors=e, purchases=b, post_errors=pe, post_purchases=pb,
                       cost=e+price*b, post_cost=pe+price*pb,
                       recovery=None if tau is None else (pe+price*pb)/(T-tau+1))
            if diagnostics:
                row.update(delay=Q(delay, powers[T]), missing=Q(missing, powers[T]))
            reach = None if override is None else Q(override_mass, powers[graph[override['state']]['t']-1])
            return row, reach, visits

        def equal(saved, actual, prefix):
            check(prefix+'_keys', set(saved) == set(actual))
            for key, v in actual.items():
                check(prefix+'_'+key, saved[key] is None if v is None else Q(saved[key]) == v)

        def summary(worlds):
            S = worlds[0]['cost']/T
            B = (1-rho)*S+rho*sum(w['cost'] for w in worlds[1:])/(T*T)
            R = sum(w['recovery'] for w in worlds[1:])/T
            return dict(stable=S, B=B, R=R, J=B+R)

        expected_candidates = [None]+[(i, a) for i in range(nbase) for a in ('B', 'F', 'R') if a != nodes[i]['action']]
        check('complete_candidate_set', len(case['candidates']) == len(expected_candidates) == 1+2*nbase)
        rebuilt, union = [], set()
        totals['candidates'] += len(case['candidates'])
        totals['continuation_states'] += len(nodes)
        for i, candidate in enumerate(case['candidates']):
            check('candidate_id', candidate['id'] == i)
            override = candidate['override']
            if i == 0:
                check('unchanged_anchor', override is None and candidate['reach_by_world'] is None)
            else:
                check('override_scope', set(override) == {'state', 'action', 'children'}
                      and (override['state'], override['action']) == expected_candidates[i])
                edges(nodes[override['state']], override['action'], override['children'], nodes)
            worlds = []
            for j, tau in enumerate([None, *range(1, T+1)]):
                row, reach, visited = forward(nodes, override, tau)
                totals['candidate_worlds'] += 1
                union |= visited
                equal(candidate['worlds'][j], row, 'candidate_world')
                if override is not None:
                    check('prefix_reach', Q(candidate['reach_by_world'][j]) == reach)
                check('physical_floor', row['cost']/T >= min(eps, price))
                worlds.append(row)
            s = summary(worlds)
            equal(candidate['summary'], s, 'candidate_summary')
            gate = dict(below_always=s['R'] < price, below_hybrid=s['R'] < hybrid_R,
                        stable_not_higher=s['stable'] <= budget)
            gate['joint'] = all(gate.values())
            check('candidate_gate', gate == candidate['gate'])
            if main_case and s['stable'] <= budget:
                check('randomized_lower_bound', s['J'] >= Q(case['randomized_J_bound']))
            rebuilt.append(dict(id=i, summary=s, worlds=worlds, gate=gate))
        check('reachable_union', union == set(range(len(nodes))))
        check('anchor_scalar_identity', rebuilt[0]['summary']['J']+mu*rebuilt[0]['summary']['stable'] == root)
        if main_case:
            for row, saved in zip(rebuilt[0]['worlds'], anchor['worlds']):
                for key, v in row.items():
                    check('frozen_anchor_world', saved[key] is None if v is None else Q(saved[key]) == v)
        feasible = [p for p in rebuilt if p['summary']['stable'] <= budget]
        passing = [p for p in feasible if p['gate']['joint']]
        by_J = lambda p: (p['summary']['J'], p['summary']['R'], p['summary']['stable'], p['id'])
        by_R = lambda p: (p['summary']['R'], p['summary']['J'], p['id'])
        selections = dict(primary=min(feasible, key=by_J)['id'] if feasible else None,
                          minimum_R=min(feasible, key=by_R)['id'] if feasible else None,
                          passing_witness=min(passing, key=by_J)['id'] if passing else None)
        check('selection', selections == case['selected'])
        check('counts', case['counts'] == dict(candidates=len(rebuilt), stable_feasible=len(feasible),
              joint_pass=len(passing), continuation_states=len(nodes)))
        selected_ids = {str(v) for v in selections.values() if v is not None}
        check('selected_graph_set', set(case['selected_policies']) == selected_ids)
        global_index = {(n['t'], tuple(n['weights'])): i for i, n in enumerate(nodes)}
        for pid, policy in case['selected_policies'].items():
            totals['selected_graphs'] += 1
            graph = policy['graph']
            change = case['candidates'][int(pid)]['override']
            check('selected_root', graph[0]['t'] == 1 and tuple(graph[0]['weights']) == prior)
            for node in graph:
                i = global_index[node['t'], tuple(node['weights'])]
                action = change['action'] if change is not None and change['state'] == i else nodes[i]['action']
                check('selected_action', node['action'] == action and node['clock'] == 0)
                edges(node, node['action'], node['children'], graph)
            worlds, used = [], set()
            for j, tau in enumerate([None, *range(1, T+1)]):
                row, _, visited = forward(graph, None, tau, True)
                equal(policy['worlds'][j], row, 'selected_world')
                used |= visited
                for key, v in rebuilt[int(pid)]['worlds'][j].items():
                    check('selected_candidate_identity', row[key] == v)
                worlds.append(row)
            check('selected_reachable', used == set(range(len(graph))))
            s = summary(worlds)
            s.update(C=s['J'], stable_errors=worlds[0]['errors'], stable_purchases=worlds[0]['purchases'],
                     mean_changed_errors=sum(w['errors'] for w in worlds[1:])/T,
                     mean_changed_purchases=sum(w['purchases'] for w in worlds[1:])/T,
                     mean_post_errors=sum(w['post_errors'] for w in worlds[1:])/T,
                     mean_post_purchases=sum(w['post_purchases'] for w in worlds[1:])/T,
                     capped_first_delay=sum(w['delay'] for w in worlds[1:])/T,
                     no_post_purchase_probability=sum(w['missing'] for w in worlds[1:])/T)
            equal(policy['summary'], s, 'selected_summary')

    result = load('RESULTS.json')
    verify(result, True)
    for fixture in load('SHORT_FIXTURES.json'):
        verify(fixture, False)
    start_record, benchmark = load('STARTED.json'), load('BENCHMARK.json')
    check('resources', len(start_record['affinity']) == 1 and start_record['nice'] >= 10)
    check('detachment', benchmark['forecast_seconds'] <= 600 or start_record['detached'])
    output = dict(passed=True, completed=datetime.now(timezone.utc).isoformat(),
                  seconds=time.monotonic()-started, checks=checks, total_checks=sum(checks.values()),
                  totals=totals, manifest_sha256=digest(directory/'MANIFEST.json'),
                  source_sha256=digest(__file__),
                  method='Normalized fixed-anchor Bellman verification and integer full-graph propagation for every candidate.')
    with (directory/'READBACK.json').open('x') as out:
        json.dump(output, out, indent=2, sort_keys=True)
        out.write('\n')
    print(json.dumps({k: output[k] for k in ('passed', 'seconds', 'total_checks', 'totals')}, sort_keys=True))


if __name__ == '__main__':
    main()
