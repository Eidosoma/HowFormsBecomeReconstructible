#!/usr/bin/env python3
"""Exact physical evaluation of frozen policies under fixed noise mismatch."""
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-mismatch-v1')
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
DATA = {'deterministic': BASE/'fep-deterministic-recovery-v1/attempt-01',
        'constraint': BASE/'fep-stable-constraint-v1/attempt-01',
        'noisy': BASE/'fep-noisy-recovery-v1/attempt-01'}
SOURCES = ('FEP_NOISE_MISMATCH_V1.md', 'check_fep_noise_mismatch.py', 'readback_fep_noise_mismatch.py')
REFERENCES = ('FEP_DETERMINISTIC_RECOVERY_V1.md', 'FEP_DETERMINISTIC_RECOVERY_V1_REPORT.md',
              'FEP_STABLE_CONSTRAINT_V1.md', 'FEP_NOISY_RECOVERY_V1.md')
RATES = ('0.04', '0.05', '0.06')
SHARED = ('cost', 'errors', 'purchases', 'post_cost', 'post_errors', 'post_purchases',
          'delay', 'missing', 'recovery')


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())


def encode(value):
    if isinstance(value, F): return str(value)
    raise TypeError(type(value).__name__)


def save(p, value):
    with Path(p).open('x') as out:
        json.dump(value, out, default=encode, indent=2, sort_keys=True)
        out.write('\n')


def roster():
    d, c, n = (read(DATA[k]/'RESULTS.json') for k in ('deterministic', 'constraint', 'noisy'))
    problem = c['conditions']['1']['problems']['retained_primary']
    primary_id = d['selected']['primary']
    assert primary_id == 37 and d['candidates'][primary_id]['gate']['joint']
    policies = {'deterministic': d['selected_policies'][str(primary_id)]}
    for name in ('hybrid', 'ordinary', 'recovery', 'erased'):
        policies[name] = n['conditions']['1']['policies'][name]
    high = d['anchor_reference']
    low = next(x['policy'] for x in problem['solution']['components'] if x['policy'] != high)
    policies.update(anchor=problem['policies'][high], low_component=problem['policies'][low])
    mapping = {high: 'anchor', low: 'low_component'}
    components = [dict(policy=mapping[x['policy']], weight=x['weight']) for x in problem['solution']['components']]
    changed = d['nodes'][d['candidates'][primary_id]['override']['state']]
    graphs = {}
    for name, p in policies.items():
        guard = [i for i, v in enumerate(p['graph']) if v['t'] == changed['t'] and v['weights'] == changed['weights']]
        graphs[name] = dict(graph=p['graph'], erased=name == 'erased',
                            guard_node=guard[0] if name in ('deterministic', 'anchor') else None,
                            nominal_worlds=p['worlds'], nominal_summary=p['summary'])
        if name in ('deterministic', 'anchor'):
            assert len(guard) == 1
    return dict(T=10, rho='1/2', price='1/10', assumed_epsilon='1/20',
                budget='19568652557/204800000000', policies=graphs, mixture=components,
                nominal_mixture=problem['solution'])


def orientation(node):
    w = node['weights']
    return F(sum(w[1:node['t']+1]), sum(w))


def branches(node, tau, eps):
    if node['action'] != 'B':
        return [('N', F(1))]
    z = tau is not None and node['t'] >= tau
    return [('0', eps if z else 1-eps), ('1', 1-eps if z else eps)]


def evaluate_world(graph, tau, eps, guard=None):
    T = max(n['t'] for n in graph)

    @lru_cache(None)
    def walk(i):
        if i is None:
            return (F(0),)*5+(F(1), F(0))
        node = graph[i]
        t, action = node['t'], node['action']
        post = tau is not None and t >= tau
        error = F(0) if action == 'B' else eps if (action == 'R') == post else 1-eps
        buy = F(int(action == 'B'))
        after = [F(0)]*7
        for label, probability in branches(node, tau, eps):
            if probability:
                after = [x+probability*y for x, y in zip(after, walk(node['children'][label]))]
        current = [error, buy, error if post else F(0), buy if post else F(0), F(0), F(0), (orientation(node)-int(post))**2]
        result = [x+y for x, y in zip(current, after)]
        if post and buy:
            result[4] = result[5] = F(0)
        elif post:
            result[4] += 1
        return tuple(result)

    errors, buys, pe, pb, delay, missing, brier = walk(0)
    flow = [F(0)]*len(graph)
    flow[0] = F(1)
    for i in sorted(range(len(graph)), key=lambda j: graph[j]['t']):
        if not flow[i]:
            continue
        for label, probability in branches(graph[i], tau, eps):
            if probability:
                child = graph[i]['children'][label]
                if child is not None:
                    flow[child] += flow[i]*probability
    row = dict(onset=tau, cost=errors+buys/10, errors=errors, purchases=buys,
               post_cost=pe+pb/10, post_errors=pe, post_purchases=pb, delay=delay,
               missing=missing, brier=brier,
               recovery=None if tau is None else (pe+pb/10)/(T-tau+1),
               guard_probability=None if guard is None else flow[guard])
    return row, flow


def summarize(T, rho, worlds):
    S = worlds[0]['cost']/T
    B = (1-rho)*S+rho*sum(w['cost'] for w in worlds[1:])/(T*T)
    R = sum(w['recovery'] for w in worlds[1:])/T
    return dict(stable=S, B=B, R=R, J=B+R, stable_errors=worlds[0]['errors'],
                stable_purchases=worlds[0]['purchases'],
                mean_changed_errors=sum(w['errors'] for w in worlds[1:])/T,
                mean_changed_purchases=sum(w['purchases'] for w in worlds[1:])/T,
                mean_post_errors=sum(w['post_errors'] for w in worlds[1:])/T,
                mean_post_purchases=sum(w['post_purchases'] for w in worlds[1:])/T,
                capped_first_delay=sum(w['delay'] for w in worlds[1:])/T,
                no_post_purchase_probability=sum(w['missing'] for w in worlds[1:])/T,
                stable_orientation_brier=worlds[0]['brier']/T,
                prior_orientation_brier=((1-rho)*worlds[0]['brier']+rho*sum(w['brier'] for w in worlds[1:])/T)/T)


def calibration(graph, flows, T, rho, summary):
    prior = [1-rho]+[rho/T]*T
    nodes = []
    total_discrepancy = variance = total_mass = F(0)
    for i, node in enumerate(graph):
        mass = sum(p*flow[i] for p, flow in zip(prior, flows))
        if not mass:
            continue
        true_p = sum(prior[j]*flows[j][i] for j in range(1, node['t']+1))/mass
        assumed_p = orientation(node)
        discrepancy = mass*(assumed_p-true_p)**2/T
        component = mass*true_p*(1-true_p)/T
        total_discrepancy += discrepancy
        variance += component
        total_mass += mass
        nodes.append(dict(node=i, visit_mass=mass, assumed_probability=assumed_p,
                          true_state_conditional_probability=true_p, excess_brier=discrepancy))
    assert total_mass == T
    assert variance+total_discrepancy == summary['prior_orientation_brier']
    return dict(discrepancy=total_discrepancy, conditional_variance=variance,
                brier=summary['prior_orientation_brier'], nodes=nodes)


def policy_result(graph, T, rho, eps, guard=None):
    evaluated = [evaluate_world(graph, tau, eps, guard) for tau in [None, *range(1, T+1)]]
    worlds = [x[0] for x in evaluated]
    s = summarize(T, rho, worlds)
    return dict(worlds=worlds, summary=s,
                calibration=calibration(graph, [x[1] for x in evaluated], T, rho, s))


def mixture(policies, components, T, rho):
    assert sum(F(p['weight']) for p in components) == 1
    worlds = []
    for j in range(T+1):
        first = policies[components[0]['policy']]['worlds'][j]
        row = {'onset': first['onset']}
        for key in first:
            if key == 'onset':
                continue
            values = [(F(p['weight']), policies[p['policy']]['worlds'][j][key]) for p in components]
            row[key] = None if any(v is None for _, v in values) else sum(w*v for w, v in values)
        worlds.append(row)
    s = summarize(T, rho, worlds)
    cal = {key: sum(F(p['weight'])*policies[p['policy']]['calibration'][key] for p in components)
           for key in ('discrepancy', 'conditional_variance', 'brier')}
    assert cal['brier'] == s['prior_orientation_brier'] == cal['discrepancy']+cal['conditional_variance']
    return dict(worlds=worlds, summary=s, calibration=cal)


def gates(s, h, budget):
    common = dict(below_always=s['R'] < F(1, 10), below_hybrid=s['R'] < h['R'])
    fixed = dict(common, stable_within_fixed_budget=s['stable'] <= budget)
    matched = dict(common, stable_not_above_matched_hybrid=s['stable'] <= h['stable'])
    fixed['joint'], matched['joint'] = all(fixed.values()), all(matched.values())
    return dict(fixed_budget=fixed, matched_hybrid=matched)


def calculate(graphs, eps):
    T, rho = graphs['T'], F(graphs['rho'])
    policies = {name: policy_result(p['graph'], T, rho, eps, p['guard_node']) for name, p in graphs['policies'].items()}
    policies['mixture'] = mixture(policies, graphs['mixture'], T, rho)
    if eps == F(1, 20):
        for name, result in policies.items():
            source = graphs['nominal_mixture'] if name == 'mixture' else graphs['policies'][name]
            old_worlds = source['worlds'] if name == 'mixture' else source['nominal_worlds']
            old_summary = source['summary'] if name == 'mixture' else source['nominal_summary']
            for row, saved in zip(result['worlds'], old_worlds):
                assert row['onset'] == saved['onset']
                for key in SHARED:
                    assert saved[key] is None if row[key] is None else row[key] == F(saved[key])
                if 'brier' in saved:
                    assert row['brier'] == F(saved['brier'])
            for key in result['summary']:
                if key in old_summary and key != 'J':
                    assert result['summary'][key] == F(old_summary[key])
            assert result['calibration']['discrepancy'] == 0
    return dict(true_epsilon=eps, policies=policies, always=dict(stable=F(1, 10), B=F(1, 10), R=F(1, 10)),
                gate=gates(policies['deterministic']['summary'], policies['hybrid']['summary'], F(graphs['budget'])))


@lru_cache(None)
def trees(T):
    if not T: return (None,)
    sub = trees(T-1)
    return tuple([('F', x) for x in sub]+[('R', x) for x in sub]+[('B', x, y) for x in sub for y in sub])


def graph_from_tree(tree, T, rho, erased=False):
    graph, index = [], {}
    prior = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
    def visit(tree, t, weights):
        if tree is None: return None
        key = tree, t, weights
        if key in index: return index[key]
        i = len(graph); index[key] = i; graph.append(None)
        action, children = tree[0], {}
        if action == 'B':
            for d in (0, 1):
                raw = tuple(w*(19 if d == int(0 < j <= t) else 1) for j, w in enumerate(weights))
                common = math.gcd(*raw)
                new = weights if erased else tuple(w//common for w in raw)
                children[str(d)] = visit(tree[d+1], t+1, new)
        else:
            children['N'] = visit(tree[1], t+1, weights)
        graph[i] = dict(t=t, weights=weights, clock=0, action=action, children=children)
        return i
    visit(tree, 1, prior)
    return graph


def brute(graph, T, tau, eps):
    num, den = eps.numerator, eps.denominator
    totals = [0]*6
    visits = [0]*len(graph)
    for bits in range(1 << T):
        ones = bits.bit_count()
        mass = num**ones*(den-num)**(T-ones)
        if not mass: continue
        i, e, b, pe, pb, first = 0, 0, 0, 0, 0, None
        for t in range(1, T+1):
            node = graph[i]; visits[i] += mass
            post = tau is not None and t >= tau
            label = int(post)^((bits >> (t-1)) & 1)
            buy = int(node['action'] == 'B')
            error = int(not buy and (node['action'] == 'R') != bool(label))
            e += error; b += buy
            if post:
                pe += error; pb += buy
                if buy and first is None: first = t
            i = node['children'][str(label) if buy else 'N']
        assert i is None
        delay = 0 if tau is None else T-tau+1 if first is None else first-tau
        vals = (e, b, pe, pb, delay, int(first is None))
        totals = [x+mass*y for x, y in zip(totals, vals)]
    e, b, pe, pb, delay, missing = (F(x, den**T) for x in totals)
    brier = sum(F(mass, den**T)*(orientation(node)-int(tau is not None and node['t'] >= tau))**2
                for node, mass in zip(graph, visits))
    return dict(onset=tau, cost=e+b/10, errors=e, purchases=b, post_cost=pe+pb/10,
                post_errors=pe, post_purchases=pb, delay=delay, missing=missing, brier=brier,
                recovery=None if tau is None else (pe+pb/10)/(T-tau+1), guard_probability=None)


def qualify():
    checks, cases = 0, 0
    fixtures = []
    rates = (F(0), F(1, 25), F(1, 20), F(3, 50), F(1, 2))
    for T in (1, 2, 3):
        for rho in (F(1, 3), F(1, 2)):
            for tree in trees(T):
                graph = graph_from_tree(tree, T, rho)
                for eps in rates:
                    result = policy_result(graph, T, rho, eps)
                    for row in result['worlds']:
                        assert row == brute(graph, T, row['onset'], eps)
                        checks += 1
                    if eps == F(1, 20):
                        assert result['calibration']['discrepancy'] == 0
                        checks += 1
                    cases += 1
    tree = ('B', ('F', ('B', None, None)), ('B', ('R', None), ('F', None)))
    for eps in (F(0), F(1, 20), F(3, 50)):
        graph = graph_from_tree(tree, 3, F(1, 2))
        fixtures.append(dict(T=3, rho='1/2', true_epsilon=eps, erased=False, graph=graph,
                             result=policy_result(graph, 3, F(1, 2), eps)))
    graph = graph_from_tree(trees(3)[-1], 3, F(1, 2), True)
    result = policy_result(graph, 3, F(1, 2), F(1, 25))
    assert result['calibration']['discrepancy'] == 0
    assert result['summary']['B'] == result['summary']['R'] == F(1, 10)
    checks += 2
    fixtures.append(dict(T=3, rho='1/2', true_epsilon='1/25', erased=True, graph=graph, result=result))
    return dict(passed=True, checks=checks, cases=cases, tree_counts={str(T):len(trees(T)) for T in (1, 2, 3)}), fixtures


def check_freeze(a):
    freeze = read(a/'FREEZE.json')
    for p, h in freeze['inputs'].items(): assert sha(p) == h, p
    for n, h in freeze['snapshots'].items(): assert sha(a/'inputs'/n) == h, n


def log(a, text):
    line = utc()+' '+text
    with (a/'RUN_LOG.txt').open('a') as out: out.write(line+'\n')
    print(line, flush=True)


def run_main(a, detached):
    check_freeze(a)
    forecast = read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a/'STARTED.json', dict(utc=utc(), pid=os.getpid(), sid=os.getsid(0),
         affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0), detached=detached))
    start = time.monotonic(); log(a, 'MAIN_START')
    graphs = read(a/'GRAPHS.json')
    conditions = {}
    for rate in RATES:
        conditions[rate] = calculate(graphs, F(rate))
        log(a, 'NOISE_CONDITION_COMPLETE '+rate)
    result = dict(conditions=conditions, fixed_budget=graphs['budget'], assumed_epsilon='1/20',
                  primary_robustness=all(c['gate']['fixed_budget']['joint'] for c in conditions.values()),
                  matched_robustness=all(c['gate']['matched_hybrid']['joint'] for c in conditions.values()))
    save(a/'RESULTS.json', result)
    check_freeze(a); log(a, 'MAIN_COMPLETE')
    save(a/'MANIFEST.json', dict(status='COMPLETE', finished=utc(), wall_seconds=time.monotonic()-start,
         outputs={str(p.relative_to(a)):sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_noise_mismatch.py'), str(a)],
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
    disk = os.statvfs('/mnt/bioIce1'); assert disk.f_bavail*disk.f_frsize > 300_000_000
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS, 0) < 10: os.nice(10-os.getpriority(os.PRIO_PROCESS, 0))
    a = STORE/args.attempt
    if args.main_only: assert a.is_dir() and not (a/'STARTED.json').exists()
    else: a.mkdir(parents=True, exist_ok=False)
    try:
        if not args.main_only:
            (a/'inputs').mkdir()
            for n in SOURCES: (a/'inputs'/n).write_bytes((ROOT/n).read_bytes())
            paths = [ROOT/n for n in SOURCES+REFERENCES]
            paths += [p/n for p in DATA.values() for n in ('RESULTS.json', 'MANIFEST.json', 'READBACK.json')]
            save(a/'FREEZE.json', dict(created=utc(), inputs={str(p):sha(p) for p in paths},
                 snapshots={n:sha(a/'inputs'/n) for n in SOURCES}, true_noise=RATES, assumed_epsilon='1/20',
                 T=10, rho='1/2', price='1/10', python=platform.python_version()))
            graphs = roster(); save(a/'GRAPHS.json', graphs)
            log(a, 'QUALIFICATION_START'); start = time.monotonic()
            qualified, fixtures = qualify(); qualified['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', qualified); save(a/'SHORT_FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic(); bench = calculate(graphs, F(7, 100)); seconds = time.monotonic()-start
            forecast = 120+12*seconds
            save(a/'BENCHMARK.json', dict(true_epsilon='7/100', timing_only=True, seconds=seconds,
                 forecast_seconds=forecast, policies=len(bench['policies']),
                 graph_nodes=sum(len(p['graph']) for p in graphs['policies'].values())))
            log(a, 'BENCHMARK_COMPLETE')
            if forecast > 7200: log(a, 'FEASIBILITY_CEILING_EXCEEDED'); return
            if forecast > 600: print('DETACHED_MAIN_REQUIRED', flush=True); return
        run_main(a, args.detached)
    except Exception as error:
        n = 'READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/n).exists(): save(a/n, dict(utc=utc(), error=repr(error)))
        raise


if __name__ == '__main__': main()
