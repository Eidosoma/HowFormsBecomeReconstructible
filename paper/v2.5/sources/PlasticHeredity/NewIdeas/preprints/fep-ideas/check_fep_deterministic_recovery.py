#!/usr/bin/env python3
"""Exact, bounded single-state changes to a frozen belief policy."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import copy
import json
import os
import platform
import subprocess
import sys
import time

import check_fep_noisy_recovery as physical
import check_fep_stable_constraint as prior

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-deterministic-recovery-v1')
PREVIOUS = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-stable-constraint-v1/attempt-01')
NOISY = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-noisy-recovery-v1/attempt-01')
SOURCES = ('FEP_DETERMINISTIC_RECOVERY_V1.md', 'check_fep_deterministic_recovery.py',
           'readback_fep_deterministic_recovery.py')
REFERENCES = ('FEP_STABLE_CONSTRAINT_V1.md', 'FEP_STABLE_CONSTRAINT_V1_REPORT.md',
              'check_fep_stable_constraint.py', 'FEP_NOISY_RECOVERY_V1.md',
              'check_fep_noisy_recovery.py')
save, sha, utc = physical.save, physical.sha, physical.utc
ZERO = (F(0),)*4


class StateSpace:
    def __init__(self, model, mu):
        self.m, self.mu = model, mu
        self.planner = prior.Oracle(model, 1, mu, False)
        self.nodes = physical.graph_for(model, self.planner, 'constrained')
        self.base_count = len(self.nodes)
        self.index = {(n['t'], tuple(n['weights'])): i for i, n in enumerate(self.nodes)}
        self.values = lru_cache(None)(self._values)

    def ensure(self, t, weights):
        if t > self.m.T:
            return None
        key = t, tuple(weights)
        if key in self.index:
            return self.index[key]
        i = len(self.nodes)
        self.index[key] = i
        self.nodes.append(None)
        action = self.m.best(self.planner.scores(t, weights, self.m.T-t+1))
        children = self.children(t, weights, action)
        self.nodes[i] = dict(t=t, weights=weights, clock=0, action=action, children=children)
        return i

    def children(self, t, weights, action):
        if action != 'B':
            return {'N': self.ensure(t+1, weights)}
        result = {}
        for label in (0, 1):
            w, common = self.m.update(t, weights, label)
            if common:
                result[str(label)] = self.ensure(t+1, w)
        return result

    def probabilities(self, t, tau, action):
        if action != 'B':
            return [('N', F(1))]
        return [(str(d), F(self.m.likelihood(t, 0 if tau is None else tau, d), 20)) for d in (0, 1)]

    def action_values(self, i, tau, action, children):
        node = self.nodes[i]
        t = node['t']
        assert node['weights'][0 if tau is None else tau] > 0
        post = tau is not None and t >= tau
        error = F(0) if action == 'B' else F(self.m.eta if (action == 'R') == post else 20-self.m.eta, 20)
        buy = F(int(action == 'B'))
        result = [error, buy, error if post else F(0), buy if post else F(0)]
        for label, probability in self.probabilities(t, tau, action):
            if probability:
                result = [v+probability*w for v, w in zip(result, self.values(children[label], tau))]
        return tuple(result)

    def _values(self, i, tau):
        if i is None:
            return ZERO
        node = self.nodes[i]
        return self.action_values(i, tau, node['action'], node['children'])

    def occupancy(self, tau):
        flow = [F(0)]*self.base_count
        flow[0] = F(1)
        for i in sorted(range(self.base_count), key=lambda j: self.nodes[j]['t']):
            n = self.nodes[i]
            if not flow[i]:
                continue
            for label, probability in self.probabilities(n['t'], tau, n['action']):
                if probability:
                    child = n['children'][label]
                    if child is not None:
                        flow[child] += flow[i]*probability
        return flow


def world_row(m, tau, values):
    errors, purchases, post_errors, post_purchases = values
    cost, post_cost = errors+m.c*purchases, post_errors+m.c*post_purchases
    return dict(onset=tau, errors=errors, purchases=purchases, post_errors=post_errors,
                post_purchases=post_purchases, cost=cost, post_cost=post_cost,
                recovery=None if tau is None else post_cost/(m.T-tau+1))


def summarize(m, worlds):
    S = worlds[0]['cost']/m.T
    B = (1-m.rho)*S+m.rho*sum(w['cost'] for w in worlds[1:])/(m.T*m.T)
    R = sum(w['recovery'] for w in worlds[1:])/m.T
    return dict(stable=S, B=B, R=R, J=B+R)


def compact_graph(nodes, override):
    graph, mapping = [], {}

    def visit(i):
        if i is None:
            return None
        if i in mapping:
            return mapping[i]
        j = len(graph)
        mapping[i] = j
        graph.append(None)
        node = nodes[i]
        changed = override is not None and override['state'] == i
        action = override['action'] if changed else node['action']
        children = override['children'] if changed else node['children']
        graph[j] = dict(t=node['t'], weights=node['weights'], clock=0, action=action,
                        children={label: visit(child) for label, child in children.items()})
        return j

    visit(0)
    return graph


def calculate(T, eta, rho, mu, budget, hybrid_R, reference=None, lower_bound=None):
    m = physical.Model(T, eta, rho)
    space = StateSpace(m, mu)
    base_graph = copy.deepcopy(space.nodes)
    if reference is not None:
        assert json.loads(json.dumps(base_graph)) == reference['graph']
    worlds = [None, *range(1, T+1)]
    roots = [space.values(0, tau) for tau in worlds]
    prefix = [space.occupancy(tau) for tau in worlds]
    candidates = []

    def candidate(override):
        values = []
        reaches = None if override is None else []
        for j, tau in enumerate(worlds):
            value = roots[j]
            if override is not None:
                i = override['state']
                probability = prefix[j][i]
                reaches.append(probability)
                if probability:
                    alternative = space.action_values(i, tau, override['action'], override['children'])
                    current = space.values(i, tau)
                    value = tuple(v+probability*(x-y) for v, x, y in zip(value, alternative, current))
            values.append(world_row(m, tau, value))
        s = summarize(m, values)
        if lower_bound is not None and s['stable'] <= budget:
            assert s['J'] >= lower_bound
        result = {'id': len(candidates), 'override': override, 'reach_by_world': reaches,
                  'worlds': values, 'summary': s, 'gate': prior.gate(s, budget, hybrid_R)}
        candidates.append(result)

    candidate(None)
    for i in range(space.base_count):
        node = space.nodes[i]
        for action in ('B', 'F', 'R'):
            if action != node['action']:
                candidate({'state': i, 'action': action,
                           'children': space.children(node['t'], tuple(node['weights']), action)})
    assert len(candidates) == 1+2*space.base_count
    if reference is not None:
        for actual, saved in zip(candidates[0]['worlds'], reference['worlds']):
            for key, value in actual.items():
                assert saved[key] is None if value is None else value == F(saved[key])
        assert space.planner.root() == F(reference['root'])
    feasible = [p for p in candidates if p['summary']['stable'] <= budget]
    passing = [p for p in feasible if p['gate']['joint']]
    key_J = lambda p: (p['summary']['J'], p['summary']['R'], p['summary']['stable'], p['id'])
    key_R = lambda p: (p['summary']['R'], p['summary']['J'], p['id'])
    selected = {'primary': min(feasible, key=key_J)['id'] if feasible else None,
                'minimum_R': min(feasible, key=key_R)['id'] if feasible else None,
                'passing_witness': min(passing, key=key_J)['id'] if passing else None}
    policies = {}
    for i in sorted({v for v in selected.values() if v is not None}):
        graph = compact_graph(space.nodes, candidates[i]['override'])
        p = prior.record(m, 1, graph, False)
        for full, short in zip(p['worlds'], candidates[i]['worlds']):
            for key, value in short.items():
                assert full[key] == value
        for key, value in candidates[i]['summary'].items():
            assert p['summary'][key] == value
        policies[str(i)] = p
    result = dict(T=T, eta=eta, rho=rho, c=m.c, noise_denominator=20, anchor_mu=mu,
                  budget=budget, hybrid_R=hybrid_R, randomized_J_bound=lower_bound,
                  base_node_count=space.base_count, nodes=space.nodes, candidates=candidates,
                  selected=selected, selected_policies=policies,
                  counts={'candidates': len(candidates), 'stable_feasible': len(feasible),
                          'joint_pass': len(passing), 'continuation_states': len(space.nodes)})
    space.planner.value.cache_clear()
    space.values.cache_clear()
    return result


def brute_world(case, candidate, tau):
    T, eta = case['T'], case['eta']
    masses = [0]*4
    override = candidate['override']
    for bits in range(1 << T):
        ones = bits.bit_count()
        probability = eta**ones*(20-eta)**(T-ones)
        if not probability:
            continue
        i, values = 0, [0]*4
        for t in range(1, T+1):
            node = case['nodes'][i]
            replacement = override is not None and override['state'] == i
            action = override['action'] if replacement else node['action']
            children = override['children'] if replacement else node['children']
            post = tau is not None and t >= tau
            label = int(post)^((bits >> (t-1)) & 1)
            error = int(action != 'B' and (action == 'R') != bool(label))
            buy = int(action == 'B')
            values = [values[0]+error, values[1]+buy, values[2]+int(post)*error, values[3]+int(post)*buy]
            i = children[str(label) if buy else 'N']
        assert i is None
        masses = [a+probability*v for a, v in zip(masses, values)]
    return tuple(F(x, 20**T) for x in masses)


def qualify():
    checks = 0
    feasible_cases = infeasible_cases = 0
    fixtures = []
    settings = [(T, eta, rho, F(mu)) for T in (1, 2, 3) for eta in (0, 1, 2)
                for rho in (F(1, 3), F(1, 2)) for mu in (0, 2)]
    settings += [(4, 1, F(1, 2), F(mu)) for mu in (0, 2)]
    for T, eta, rho, mu in settings:
        budget = (F(eta, 20)+F(1, 10))/2
        case = calculate(T, eta, rho, mu, budget, F(1, 10))
        m = physical.Model(T, eta, rho)
        assert len(case['candidates']) == 1+2*case['base_node_count']
        checks += 1
        for candidate in case['candidates']:
            for row in candidate['worlds']:
                rebuilt = world_row(m, row['onset'], brute_world(case, candidate, row['onset']))
                assert rebuilt == row
                checks += 1
        feasible_cases += bool(case['counts']['stable_feasible'])
        infeasible_cases += not case['counts']['stable_feasible']
        if T == 4 or (T == 3 and eta == 0 and rho == F(1, 2) and mu == 2):
            fixtures.append(case)
    assert feasible_cases and infeasible_cases
    checks += 1
    return dict(passed=True, checks=checks, cases=len(settings), feasible_cases=feasible_cases,
                infeasible_cases=infeasible_cases, method='Complete noise-string replay of every short candidate.'), fixtures


def check_freeze(a):
    frozen = json.loads((a/'FREEZE.json').read_text())
    for path, h in frozen['inputs'].items():
        assert sha(path) == h, path
    for name, h in frozen['snapshots'].items():
        assert sha(a/'inputs'/name) == h, name


def log(a, message):
    line = utc()+' '+message
    with (a/'RUN_LOG.txt').open('a') as out:
        out.write(line+'\n')
    print(line, flush=True)


def run_main(a, detached):
    check_freeze(a)
    forecast = json.loads((a/'BENCHMARK.json').read_text())['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a/'STARTED.json', dict(utc=utc(), pid=os.getpid(), sid=os.getsid(0),
         affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0), detached=detached))
    start = time.monotonic()
    log(a, 'MAIN_START')
    original = json.loads((PREVIOUS/'RESULTS.json').read_text())
    control = json.loads((NOISY/'RESULTS.json').read_text())['conditions']['1']['policies']['hybrid']['summary']
    problem = original['conditions']['1']['problems']['retained_primary']
    budget = F(problem['budget'])
    assert budget == F(control['stable']) == F(19568652557, 204800000000)
    above = [p['policy'] for p in problem['solution']['components']
             if F(problem['policies'][p['policy']]['summary']['stable']) > budget]
    assert len(above) == 1
    anchor_name = above[0]
    anchor = problem['policies'][anchor_name]
    result = calculate(10, 1, F(1, 2), F(anchor['mu']), budget, F(control['R']), anchor,
                       F(problem['solution']['summary']['J']))
    result['anchor_reference'] = anchor_name
    result['inherited_bounds'] = {
        'noiseless_min_R': original['conditions']['0']['problems']['retained_recovery_bound']['solution']['summary']['R'],
        'noisy_erased_min_R': original['conditions']['1']['problems']['erased_recovery_bound']['solution']['summary']['R']}
    assert all(F(x) > F(1, 10) for x in result['inherited_bounds'].values())
    save(a/'RESULTS.json', result)
    check_freeze(a)
    log(a, 'MAIN_COMPLETE')
    save(a/'MANIFEST.json', dict(status='COMPLETE', finished=utc(), wall_seconds=time.monotonic()-start,
         outputs={str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_deterministic_recovery.py'), str(a)],
                       stdout=out, stderr=subprocess.STDOUT, check=True)
    print('READBACK_COMPLETE '+str(a), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='attempt-01')
    parser.add_argument('--main-only', action='store_true')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt
    assert Path('/mnt/bioIce1').is_mount()
    disk = os.statvfs('/mnt/bioIce1')
    assert disk.f_bavail*disk.f_frsize > 300_000_000
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        os.nice(10-os.getpriority(os.PRIO_PROCESS, 0))
    a = STORE/args.attempt
    if args.main_only:
        assert a.is_dir() and not (a/'STARTED.json').exists()
    else:
        a.mkdir(parents=True, exist_ok=False)
    try:
        if not args.main_only:
            (a/'inputs').mkdir()
            for n in SOURCES:
                (a/'inputs'/n).write_bytes((ROOT/n).read_bytes())
            paths = [ROOT/n for n in SOURCES+REFERENCES]
            paths += [base/n for base in (PREVIOUS, NOISY) for n in ('RESULTS.json', 'MANIFEST.json', 'READBACK.json')]
            save(a/'FREEZE.json', dict(created=utc(), inputs={str(p): sha(p) for p in paths},
                 snapshots={n: sha(a/'inputs'/n) for n in SOURCES}, T=10, eta=1, rho='1/2',
                 c='1/10', budget='19568652557/204800000000', python=platform.python_version()))
            log(a, 'QUALIFICATION_START')
            start = time.monotonic()
            qualified, fixtures = qualify()
            qualified['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', qualified)
            save(a/'SHORT_FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic()
            bench = calculate(7, 1, F(1, 3), F(2), F(3, 40), F(1, 10))
            seconds = time.monotonic()-start
            forecast = 120+6*3**3*seconds
            save(a/'BENCHMARK.json', dict(T=7, eta=1, rho='1/3', anchor_mu='2', budget='3/40',
                 seconds=seconds, forecast_seconds=forecast, counts=bench['counts']))
            log(a, 'BENCHMARK_COMPLETE')
            if forecast > 7200:
                log(a, 'FEASIBILITY_CEILING_EXCEEDED')
                return
            if forecast > 600:
                print('DETACHED_MAIN_REQUIRED', flush=True)
                return
        run_main(a, args.detached)
    except Exception as error:
        name = 'READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():
            save(a/name, dict(utc=utc(), error=repr(error)))
        raise


if __name__ == '__main__':
    main()
