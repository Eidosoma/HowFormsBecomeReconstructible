#!/usr/bin/env python3
"""Exact noisy finite POMDP: integer likelihoods and homogeneous costs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-noisy-recovery-v1')
OLD = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-recovery-objective-v1/attempt-01')
SOURCES = ('FEP_NOISY_RECOVERY_V1.md', 'check_fep_noisy_recovery.py', 'readback_fep_noisy_recovery.py')
REFERENCES = ('FEP_RECOVERY_OBJECTIVE_V1.md', 'FEP_RECOVERY_OBJECTIVE_V1_REPORT.md',
              'check_fep_recovery_objective.py')
ARMS = ('ordinary', 'recovery', 'erased', 'hybrid')
FIELDS = ('cost', 'errors', 'purchases', 'brier', 'post_cost', 'post_errors',
          'post_purchases', 'delay', 'missing', 'first_brier_mass')


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(x):
    if isinstance(x, F):
        return str(x)
    raise TypeError(type(x).__name__)


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, default=encode, indent=2, sort_keys=True)
        stream.write('\n')


class Model:
    def __init__(self, T, eta, rho=F(1, 2)):
        self.T, self.eta, self.rho, self.c = T, eta, rho, F(1, 10)
        assert 0 <= eta <= 10 and rho in (F(1, 2), F(1, 3))
        self.prior = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        self.L = math.lcm(*range(1, T+1))
        self.scale = 20*T*self.L
        self.coefficients = {}
        for lam in (0, 1):
            for t in range(1, T+1):
                self.coefficients[lam, t] = tuple(self.L+(lam*int(
                    F(T*self.L, 1)/(rho*(T-j+1))) if 0 < j <= t else 0)
                    for j in range(T+1))
        self.update = lru_cache(None)(self._update)

    def likelihood(self, t, j, observed):
        orientation = int(0 < j <= t)
        return 20-self.eta if observed == orientation else self.eta

    def _update(self, t, weights, observed):
        raw = tuple(v*self.likelihood(t, j, observed) for j, v in enumerate(weights))
        common = math.gcd(*raw)
        return (tuple(v//common for v in raw), common) if common else (None, 0)

    def immediate(self, t, weights, lam):
        coefficients = self.coefficients[lam, t]
        total = sum(w*h for w, h in zip(weights, coefficients))
        follow = sum(w*h*(20-self.eta if 0 < j <= t else self.eta)
                     for j, (w, h) in enumerate(zip(weights, coefficients)))
        return {'F': follow, 'R': 20*total-follow, 'B': 2*total}

    @staticmethod
    def best(scores):
        return min(scores, key=lambda a: (scores[a], {'B': 0, 'F': 1, 'R': 2}[a]))

    def reversal(self, t, weights):
        return F(sum(weights[1:t+1]), sum(weights))


class Planner:
    def __init__(self, model, lam, erased=False):
        self.model, self.lam, self.erased = model, lam, erased
        self.value = lru_cache(None)(self._value)

    def scores(self, t, weights, h):
        m = self.model
        scores = m.immediate(t, weights, self.lam)
        following = self.value(t+1, weights, h-1)
        scores['F'] += following
        scores['R'] += following
        if self.erased:
            assert weights == m.prior
            scores['B'] += following
        else:
            for observed in (0, 1):
                new, common = m.update(t, weights, observed)
                if common:
                    scores['B'] += F(common, 20)*self.value(t+1, new, h-1)
        return scores

    def _value(self, t, weights, h):
        if h == 0:
            return F(0)
        return min(self.scores(t, weights, h).values())

    def normalized_root(self):
        m = self.model
        return self.value(1, m.prior, m.T)/(m.scale*sum(m.prior))


def graph_for(model, planner, arm):
    nodes, index = [], {}

    def visit(t, weights, clock):
        if t > model.T:
            return None
        key = (t, weights, clock)
        if key in index:
            return index[key]
        node_id = len(nodes)
        index[key] = node_id
        nodes.append(None)
        horizon = min(4, model.T-t+1) if arm == 'hybrid' else model.T-t+1
        action = 'B' if arm == 'hybrid' and clock else model.best(planner.scores(t, weights, horizon))
        children = {}
        if action == 'B':
            for observed in (0, 1):
                new, common = model.update(t, weights, observed)
                if common:
                    children[str(observed)] = visit(t+1, weights if planner.erased else new, 0)
        else:
            children['N'] = visit(t+1, weights, 1 if arm == 'hybrid' else 0)
        nodes[node_id] = {'t': t, 'weights': weights, 'clock': clock,
                          'action': action, 'children': children}
        return node_id

    visit(1, model.prior, 0)
    return nodes


def evaluate(model, graph, tau, erased):
    @lru_cache(None)
    def value(node_id):
        if node_id is None:
            return (F(0),)*8+(F(1), F(0))
        node = graph[node_id]
        t, weights, action = node['t'], tuple(node['weights']), node['action']
        post = tau is not None and t >= tau
        z = int(post)
        children = []
        if action == 'B':
            for observed in (0, 1):
                probability = F(20-model.eta if observed == z else model.eta, 20)
                if probability:
                    child = node['children'][str(observed)]
                    new = weights if erased else model.update(t, weights, observed)[0]
                    children.append((probability, value(child), new))
        else:
            children = [(F(1), value(node['children']['N']), weights)]
        future = [sum(p*v[i] for p, v, _ in children) for i in range(len(FIELDS))]
        error = F(0) if action == 'B' else F(
            model.eta if (action == 'R') == bool(z) else 20-model.eta, 20)
        buy = int(action == 'B')
        cost = error+model.c*buy
        current = [cost, error, F(buy), (model.reversal(t, weights)-z)**2,
                   cost if post else F(0), error if post else F(0),
                   F(buy) if post else F(0), F(0), F(0), F(0)]
        total = [x+y for x, y in zip(current, future)]
        if post and buy:
            total[7] = F(0)
            total[8] = F(0)
            total[9] = sum(p*(model.reversal(t, new)-1)**2 for p, _, new in children)
        elif post:
            total[7] += 1
        return tuple(total)

    result = dict(zip(FIELDS, value(0)))
    result['onset'] = tau
    if tau is not None:
        result['recovery'] = result['post_cost']/(model.T-tau+1)
        result['first_brier_conditional'] = result['first_brier_mass']/(1-result['missing']) if result['missing'] < 1 else None
    else:
        result['recovery'] = result['first_brier_conditional'] = None
    return result


def summarize(model, worlds, lam):
    T = model.T
    stable = worlds[0]['cost']/T
    changed = sum(w['cost'] for w in worlds[1:])/(T*T)
    B = (1-model.rho)*stable+model.rho*changed
    R = sum(w['recovery'] for w in worlds[1:])/T
    hit = sum(1-w['missing'] for w in worlds[1:])/T
    first_brier = sum(w['first_brier_mass'] for w in worlds[1:])/T
    return {'stable': stable, 'changed_full': changed, 'B': B, 'R': R,
            'J': B+lam*R, 'lambda': lam,
            'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
            'stable_orientation_brier': worlds[0]['brier']/T,
            'mean_changed_errors': sum(w['errors'] for w in worlds[1:])/T,
            'mean_changed_purchases': sum(w['purchases'] for w in worlds[1:])/T,
            'mean_post_errors': sum(w['post_errors'] for w in worlds[1:])/T,
            'mean_post_purchases': sum(w['post_purchases'] for w in worlds[1:])/T,
            'capped_first_delay': sum(w['delay'] for w in worlds[1:])/T,
            'no_post_purchase_probability': 1-hit,
            'first_brier_conditional': first_brier/hit if hit else None}


def calculate(T, eta, rho=F(1, 2)):
    model = Model(T, eta, rho)
    planners = {'ordinary': Planner(model, 0), 'recovery': Planner(model, 1),
                'erased': Planner(model, 1, True)}
    planners['hybrid'] = planners['ordinary']
    policies = {}
    for arm in ARMS:
        planner = planners[arm]
        graph = graph_for(model, planner, arm)
        worlds = [evaluate(model, graph, tau, planner.erased) for tau in [None, *range(1, T+1)]]
        summary = summarize(model, worlds, planner.lam)
        root = None if arm == 'hybrid' else planner.normalized_root()
        if root is not None:
            assert root == summary['J']
        policies[arm] = {'graph': graph, 'worlds': worlds, 'summary': summary, 'root_value': root}
    r, hybrid = policies['recovery']['summary'], policies['hybrid']['summary']
    gate = {'below_always': r['R'] < model.c, 'below_hybrid': r['R'] < hybrid['R'],
            'stable_not_higher': r['stable'] <= hybrid['stable']}
    gate['joint'] = all(gate.values())
    return {'T': T, 'eta': eta, 'noise_denominator': 20, 'rho': rho, 'c': model.c,
            'policies': policies, 'gate': gate,
            'always': {'stable': model.c, 'B': model.c, 'R': model.c},
            'known_orientation_floor': min(F(eta, 20), model.c)}


@lru_cache(None)
def trees(h):
    if not h:
        return (None,)
    sub = trees(h-1)
    return tuple([('F', child) for child in sub]+[('R', child) for child in sub]+
                 [('B', left, right) for left in sub for right in sub])


def exhaustive(model, lam):
    @lru_cache(None)
    def cost(tree, t, tau):
        if tree is None:
            return F(0)
        post = tau is not None and t >= tau
        weight = F(1, model.T)+(F(lam, 1)/(model.rho*(model.T-tau+1)) if post else 0)
        if tree[0] == 'B':
            p1 = F(20-model.eta if post else model.eta, 20)
            return model.c*weight+(1-p1)*cost(tree[1], t+1, tau)+p1*cost(tree[2], t+1, tau)
        error = F(model.eta if (tree[0] == 'R') == post else 20-model.eta, 20)
        return error*weight+cost(tree[1], t+1, tau)
    return min((1-model.rho)*cost(tree, 1, None)+model.rho*sum(
        cost(tree, 1, tau) for tau in range(1, model.T+1))/model.T for tree in trees(model.T))


def erased_exhaustive(model, lam):
    def score(word):
        result = F(0)
        for tau in [None, *range(1, model.T+1)]:
            prior = 1-model.rho if tau is None else model.rho/model.T
            for t, action in enumerate(word, 1):
                post = tau is not None and t >= tau
                loss = model.c if action == 'B' else F(model.eta if (action == 'R') == post else 20-model.eta, 20)
                weight = F(1, model.T)+(F(lam, 1)/(model.rho*(model.T-tau+1)) if post else 0)
                result += prior*loss*weight
        return result
    return min(score(word) for word in itertools.product('FBR', repeat=model.T))


def qualify():
    checks = 0
    for T in range(1, 4):
        for rho in (F(1, 3), F(1, 2)):
            for eta in (0, 1, 10):
                model = Model(T, eta, rho)
                for lam in (0, 1):
                    p = Planner(model, lam)
                    assert p.normalized_root() == exhaustive(model, lam)
                    checks += 1
                    erased = Planner(model, lam, True)
                    assert erased.normalized_root() == erased_exhaustive(model, lam)
                    checks += 1
                    if eta == 10:
                        assert p.normalized_root() == F(1, 10)*(1+lam)
                        checks += 1
                for t in range(1, T+1):
                    for j in range(T+1):
                        assert model.likelihood(t, j, 0)+model.likelihood(t, j, 1) == 20
                        checks += 1
                    assert sum(F(common*sum(new), 20*sum(model.prior)) for observed in (0, 1)
                               for new, common in [model.update(t, model.prior, observed)] if common) == 1
                    checks += 1
    for eta in (0, 1, 10):
        for rho in (F(1, 3), F(1, 2)):
            model = Model(4, eta, rho)
            for lam in (0, 1):
                assert Planner(model, lam, True).normalized_root() == erased_exhaustive(model, lam)
                checks += 1
        for z in (0, 1):
            for y in (0, 1):
                marginal = sum(F(1, 2)*F(eta if noise else 20-eta, 20)
                               for x in (0, 1) for noise in (0, 1) if x ^ z ^ noise == y)
                assert marginal == F(1, 2)
                checks += 1
    spec = importlib.util.spec_from_file_location('frozen_perfect_objective', ROOT/'check_fep_recovery_objective.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    for T in range(1, 7):
        for rho in (F(1, 3), F(1, 2)):
            model = Model(T, 0, rho)
            for lam in (0, 1):
                for erased in (False, True):
                    assert Planner(model, lam, erased).normalized_root() == previous.Solver(
                        T, rho, F(1, 10), F(lam), erased).value(1, 0)
                    checks += 1
    model = Model(10, 1)
    first, _ = model.update(1, model.prior, 1)
    second, _ = model.update(2, first, 1)
    assert model.reversal(1, first) == F(1, 2)
    assert model.reversal(2, second) == F(190, 199)
    assert all(w > 0 for w in first+second)
    checks += 3
    fixtures = [calculate(3, eta) for eta in (0, 1, 10)]+[calculate(4, 1)]
    return {'passed': True, 'exact_assertions': checks,
            'policy_tree_counts': {str(h): len(trees(h)) for h in range(1, 4)},
            'noisy_contradictions': {'after_first': model.reversal(1, first),
                                    'after_second': model.reversal(2, second),
                                    'first_weights': first, 'second_weights': second}}, fixtures


def check_freeze(a):
    frozen = json.loads((a/'FREEZE.json').read_text())
    for name, identity in frozen['inputs'].items():
        assert sha(name) == identity, name
    for name, identity in frozen['snapshots'].items():
        assert sha(a/'inputs'/name) == identity, name


def log(a, message):
    line = utc()+' '+message
    with (a/'RUN_LOG.txt').open('a') as stream:
        stream.write(line+'\n')
    print(line, flush=True)


def run_main(a, detached):
    check_freeze(a)
    forecast = json.loads((a/'BENCHMARK.json').read_text())['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a/'STARTED.json', {'utc': utc(), 'pid': os.getpid(), 'sid': os.getsid(0),
         'affinity': sorted(os.sched_getaffinity(0)), 'nice': os.getpriority(os.PRIO_PROCESS, 0),
         'detached': detached})
    start = time.monotonic()
    log(a, 'MAIN_START')
    results = {}
    for eta in (0, 1):
        results[str(eta)] = calculate(10, eta)
        log(a, 'NOISE_CONDITION_COMPLETE '+str(eta)+'/20')
    save(a/'RESULTS.json', {'conditions': results, 'main_condition': '1'})
    check_freeze(a)
    log(a, 'MAIN_COMPLETE')
    outputs = {str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}
    save(a/'MANIFEST.json', {'status': 'COMPLETE', 'finished': utc(),
         'wall_seconds': time.monotonic()-start, 'outputs': outputs})
    with (a/'READBACK_STDOUT.log').open('x') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_noisy_recovery.py'), str(a)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
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
    assert disk.f_bavail*disk.f_frsize > 200_000_000
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
            for name in SOURCES:
                (a/'inputs'/name).write_bytes((ROOT/name).read_bytes())
            paths = [ROOT/name for name in SOURCES+REFERENCES]
            paths += [OLD/name for name in ('RESULTS.json', 'MANIFEST.json', 'READBACK.json')]
            save(a/'FREEZE.json', {'created': utc(), 'inputs': {str(p): sha(p) for p in paths},
                 'snapshots': {name: sha(a/'inputs'/name) for name in SOURCES},
                 'python': platform.python_version(), 'T': 10, 'eta': [0, 1], 'noise_denominator': 20,
                 'rho': '1/2', 'c': '1/10', 'lambda': [0, 1]})
            log(a, 'QUALIFICATION_START')
            start = time.monotonic()
            qualified, fixtures = qualify()
            qualified['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', qualified)
            save(a/'SHORT_FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic()
            benchmark = calculate(7, 2, F(1, 3))
            seconds = time.monotonic()-start
            forecast = 120+12*3**3*seconds
            save(a/'BENCHMARK.json', {'T': 7, 'eta': 2, 'rho': '1/3', 'seconds': seconds,
                 'forecast_seconds': forecast, 'graph_nodes': {k: len(v['graph']) for k, v in benchmark['policies'].items()}})
            log(a, 'BENCHMARK_COMPLETE')
            if forecast > 7200:
                log(a, 'FEASIBILITY_CEILING_EXCEEDED')
                return
            if forecast > 600:
                print('DETACHED_MAIN_REQUIRED', flush=True)
                return
        run_main(a, args.detached)
    except Exception as exc:
        name = 'READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/name).exists():
            save(a/name, {'utc': utc(), 'error': repr(exc)})
        raise


if __name__ == '__main__':
    main()
