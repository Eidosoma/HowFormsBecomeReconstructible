#!/usr/bin/env python3
"""Exact constrained finite POMDP with a saved primal/dual certificate."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import itertools
import math
import os
import platform
import subprocess
import sys
import time

import check_fep_noisy_recovery as old

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-stable-constraint-v1')
REFERENCE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-noisy-recovery-v1/attempt-01')
SOURCES = ('FEP_STABLE_CONSTRAINT_V1.md', 'check_fep_stable_constraint.py',
           'readback_fep_stable_constraint.py')
REFERENCES = ('FEP_NOISY_RECOVERY_V1.md', 'FEP_NOISY_RECOVERY_V1_REPORT.md',
              'check_fep_noisy_recovery.py')
FIELDS = ('cost', 'errors', 'purchases', 'post_cost', 'post_errors',
          'post_purchases', 'delay', 'missing', 'recovery')
MAX_CALLS = 128
save, sha, utc = old.save, old.sha, old.utc


class Oracle:
    def __init__(self, model, alpha, mu, erased):
        self.model, self.alpha, self.mu, self.erased = model, alpha, mu, erased
        weights = {t: tuple(F(alpha, model.T)
                   + (1/(model.rho*(model.T-j+1)) if 0 < j <= t else 0)
                   + (mu/((1-model.rho)*model.T) if j == 0 else 0)
                   for j in range(model.T+1)) for t in range(1, model.T+1)}
        denominator = math.lcm(*(w.denominator for row in weights.values() for w in row))
        self.coefficients = {t: tuple(int(w*denominator) for w in row) for t, row in weights.items()}
        self.scale = 20*denominator
        self.value = lru_cache(None)(self._value)

    def scores(self, t, weights, h):
        m = self.model
        coeff = self.coefficients[t]
        total = sum(w*c for w, c in zip(weights, coeff))
        forward = sum(w*c*(20-m.eta if 0 < j <= t else m.eta)
                      for j, (w, c) in enumerate(zip(weights, coeff)))
        continuation = self.value(t+1, weights, h-1)
        scores = {'F': forward+continuation, 'R': 20*total-forward+continuation, 'B': 2*total}
        if self.erased:
            scores['B'] += continuation
        else:
            for label in (0, 1):
                new, common = m.update(t, weights, label)
                if common:
                    scores['B'] += F(common, 20)*self.value(t+1, new, h-1)
        return scores

    def _value(self, t, weights, h):
        return F(0) if not h else min(self.scores(t, weights, h).values())

    def root(self):
        m = self.model
        return self.value(1, m.prior, m.T)/(self.scale*sum(m.prior))


def summary(m, worlds, alpha):
    T = m.T
    S = worlds[0]['cost']/T
    B = (1-m.rho)*S+m.rho*sum(w['cost'] for w in worlds[1:])/(T*T)
    R = sum(w['recovery'] for w in worlds[1:])/T
    return {'stable': S, 'B': B, 'R': R, 'J': B+R, 'C': alpha*B+R,
            'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
            'mean_changed_errors': sum(w['errors'] for w in worlds[1:])/T,
            'mean_changed_purchases': sum(w['purchases'] for w in worlds[1:])/T,
            'mean_post_errors': sum(w['post_errors'] for w in worlds[1:])/T,
            'mean_post_purchases': sum(w['post_purchases'] for w in worlds[1:])/T,
            'capped_first_delay': sum(w['delay'] for w in worlds[1:])/T,
            'no_post_purchase_probability': sum(w['missing'] for w in worlds[1:])/T}


def record(m, alpha, graph, erased, mu=None, root=None):
    worlds = []
    for tau in [None, *range(1, m.T+1)]:
        full = old.evaluate(m, graph, tau, erased)
        worlds.append({'onset': tau, **{k: full[k] for k in FIELDS}})
    s = summary(m, worlds, alpha)
    if root is not None:
        assert root == s['C']+mu*s['stable']
    return {'graph': graph, 'worlds': worlds, 'summary': s, 'mu': mu, 'root': root}


def oracle(m, alpha, mu, erased):
    planner = Oracle(m, alpha, mu, erased)
    graph = old.graph_for(m, planner, 'constrained')
    result = record(m, alpha, graph, erased, mu, planner.root())
    planner.value.cache_clear()
    return result


def mixture(m, alpha, policies, components):
    assert sum(p['weight'] for p in components) == 1
    worlds = []
    for i in range(m.T+1):
        example = policies[components[0]['policy']]['worlds'][i]
        row = {'onset': example['onset']}
        for key in FIELDS:
            row[key] = None if example[key] is None else sum(
                p['weight']*policies[p['policy']]['worlds'][i][key] for p in components)
        worlds.append(row)
    return {'components': components, 'worlds': worlds, 'summary': summary(m, worlds, alpha)}


def constrained(m, alpha, budget, erased):
    floor = min(F(m.eta, 20), m.c)
    assert budget >= floor
    follow_graph = [{'t': t, 'weights': m.prior, 'clock': 0, 'action': 'F',
                     'children': {'N': t if t < m.T else None}} for t in range(1, m.T+1)]
    # Always following attains the minimum stable loss in the declared main
    # and benchmark models. For the uninformative qualification use always buy.
    if F(m.eta, 20) > m.c:
        follow_graph = [{'t': t, 'weights': m.prior, 'clock': 0, 'action': 'B',
                         'children': {'0': t if t < m.T else None,
                                      '1': t if t < m.T else None}} for t in range(1, m.T+1)]
    policies = {'floor': record(m, alpha, follow_graph, True)}
    policies['oracle000'] = oracle(m, alpha, F(0), erased)
    trace = []
    high, low, witness, multiplier = 'oracle000', 'floor', 'oracle000', F(0)
    if policies[high]['summary']['stable'] <= budget:
        components = [{'policy': high, 'weight': F(1)}]
        trace.append({'oracle': high, 'decision': 'unconstrained_feasible'})
    else:
        for call in range(1, MAX_CALLS):
            a, b = policies[low]['summary'], policies[high]['summary']
            assert a['stable'] <= budget < b['stable'] and a['C'] >= b['C']
            multiplier = (a['C']-b['C'])/(b['stable']-a['stable'])
            witness = f'oracle{call:03d}'
            p = policies[witness] = oracle(m, alpha, multiplier, erased)
            chord = a['C']+multiplier*a['stable']
            assert p['root'] <= chord
            step = {'oracle': witness, 'low': low, 'high': high, 'chord': chord}
            if p['root'] == chord:
                high_weight = (budget-a['stable'])/(b['stable']-a['stable'])
                components = [dict(policy=low, weight=1-high_weight), dict(policy=high, weight=high_weight)]
                components = [c for c in components if c['weight']]
                step['decision'] = 'dual_certificate'
                trace.append(step)
                break
            if p['summary']['stable'] == budget:
                components = [dict(policy=witness, weight=F(1))]
                step['decision'] = 'exact_budget'
                trace.append(step)
                break
            step['decision'] = 'replace_low' if p['summary']['stable'] < budget else 'replace_high'
            trace.append(step)
            if p['summary']['stable'] < budget:
                low = witness
            else:
                high = witness
        else:
            raise RuntimeError('Fixed 128-oracle ceiling reached before exact certificate.')
    solution = mixture(m, alpha, policies, components)
    lower_bound = policies[witness]['root']-multiplier*budget
    assert solution['summary']['stable'] <= budget
    assert solution['summary']['C'] == lower_bound
    feasible = [name for name, p in policies.items() if p['summary']['stable'] <= budget]
    best = min(feasible, key=lambda name: (policies[name]['summary']['C'], name))
    return {'alpha': alpha, 'erased': erased, 'budget': budget, 'policies': policies,
            'trace': trace, 'solution': solution, 'best_saved_feasible_deterministic': best,
            'certificate': {'mu': multiplier, 'oracle': witness, 'lower_bound': lower_bound,
                            'duality_gap': solution['summary']['C']-lower_bound},
            'oracle_calls': sum(name.startswith('oracle') for name in policies)}


def gate(s, budget, hybrid_R):
    result = {'below_always': s['R'] < F(1, 10), 'below_hybrid': s['R'] < hybrid_R,
              'stable_not_higher': s['stable'] <= budget}
    result['joint'] = all(result.values())
    return result


def calculate(T, eta, rho, budget, reference=None):
    m = old.Model(T, eta, rho)
    problems = {}
    for erased in (False, True):
        for alpha in (1, 0):
            name = ('erased' if erased else 'retained')+('_primary' if alpha else '_recovery_bound')
            problem = constrained(m, alpha, budget, erased)
            if reference is not None:
                problem['gate'] = gate(problem['solution']['summary'], budget,
                                       F(reference['policies']['hybrid']['summary']['R']))
                if alpha == 1:
                    prior = reference['policies']['erased' if erased else 'recovery']
                    for a, b in zip(problem['policies']['oracle000']['worlds'], prior['worlds']):
                        for key in FIELDS:
                            assert (a[key] is None and b[key] is None) or a[key] == F(b[key])
            problems[name] = problem
    return {'T': T, 'eta': eta, 'rho': rho, 'c': m.c, 'noise_denominator': 20,
            'budget': budget, 'problems': problems}


def exhaustive_points(m, erased):
    if erased:
        def make(word):
            tree = None
            for a in reversed(word):
                tree = (a, tree, tree) if a == 'B' else (a, tree)
            return tree
        trees = [make(word) for word in itertools.product('FBR', repeat=m.T)]
    else:
        trees = old.trees(m.T)

    @lru_cache(None)
    def cost(tree, t, tau):
        if tree is None:
            return F(0), F(0)
        changed = tau is not None and tau <= t
        if tree[0] == 'B':
            p = F(20-m.eta if changed else m.eta, 20)
            left, right = cost(tree[1], t+1, tau), cost(tree[2], t+1, tau)
            following = tuple((1-p)*x+p*y for x, y in zip(left, right))
            loss = m.c
        else:
            following = cost(tree[1], t+1, tau)
            loss = F(m.eta if (tree[0] == 'R') == changed else 20-m.eta, 20)
        return loss+following[0], (loss if changed else F(0))+following[1]

    points = set()
    for tree in trees:
        S = cost(tree, 1, None)[0]/m.T
        changed = [cost(tree, 1, tau) for tau in range(1, m.T+1)]
        B = (1-m.rho)*S+m.rho*sum(x[0] for x in changed)/(m.T*m.T)
        R = sum(v[1]/(m.T-tau+1) for tau, v in enumerate(changed, 1))/m.T
        points.add((S, B, R))
    return points, len(trees)


def exhaustive_min(points, alpha, budget):
    by_S = {}
    for s, b, r in points:
        by_S[s] = min(by_S.get(s, alpha*b+r), alpha*b+r)
    low = [(s, c) for s, c in by_S.items() if s <= budget]
    high = [(s, c) for s, c in by_S.items() if s > budget]
    best = min(c for s, c in low)
    for s, c in low:
        for u, v in high:
            weight = (budget-s)/(u-s)
            best = min(best, (1-weight)*c+weight*v)
    return best


def qualify():
    checks = 0
    active = inactive = mixtures = 0
    for T in range(1, 5):
        for rho in (F(1, 3), F(1, 2)):
            for eta in (0, 1, 2):
                for erased in (False, True):
                    if T == 4 and not erased:
                        continue
                    m = old.Model(T, eta, rho)
                    points, count = exhaustive_points(m, erased)
                    for alpha in (0, 1):
                        for budget in sorted({F(eta, 20), (F(eta, 20)+m.c)/2, m.c}):
                            result = constrained(m, alpha, budget, erased)
                            assert result['solution']['summary']['C'] == exhaustive_min(points, alpha, budget)
                            checks += 1
                            for p in result['policies'].values():
                                if p['mu'] is not None:
                                    assert p['root'] == min(alpha*b+r+p['mu']*s for s, b, r in points)
                                    checks += 1
                            active += result['certificate']['mu'] > 0
                            inactive += result['certificate']['mu'] == 0
                            mixtures += len(result['solution']['components']) == 2
    for alpha, erased in itertools.product((0, 1), (False, True)):
        m = old.Model(3, 10)
        x = constrained(m, alpha, m.c, erased)
        assert x['solution']['summary']['stable'] == m.c
        assert x['solution']['summary']['C'] == (alpha+1)*m.c
        checks += 2
    assert active and inactive and mixtures
    checks += 1
    fixtures = [calculate(3, eta, F(1, 2), F(3, 40)) for eta in (0, 1)]
    return {'passed': True, 'checks': checks, 'active_cases': active, 'inactive_cases': inactive,
            'two_component_cases': mixtures, 'tree_counts': {'1': 3, '2': 15, '3': 255}}, fixtures


def check_freeze(a):
    frozen = old.json.loads((a/'FREEZE.json').read_text())
    for p, h in frozen['inputs'].items():
        assert sha(p) == h, p
    for name, h in frozen['snapshots'].items():
        assert sha(a/'inputs'/name) == h, name


def log(a, message):
    line = utc()+' '+message
    with (a/'RUN_LOG.txt').open('a') as out:
        out.write(line+'\n')
    print(line, flush=True)


def run_main(a, detached):
    check_freeze(a)
    forecast = old.json.loads((a/'BENCHMARK.json').read_text())['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a/'STARTED.json', {'utc': utc(), 'pid': os.getpid(), 'sid': os.getsid(0),
         'affinity': sorted(os.sched_getaffinity(0)), 'nice': os.getpriority(os.PRIO_PROCESS, 0),
         'detached': detached})
    start = time.monotonic()
    log(a, 'MAIN_START')
    references = old.json.loads((REFERENCE/'RESULTS.json').read_text())['conditions']
    results = {}
    for eta in (0, 1):
        reference = references[str(eta)]
        budget = F(reference['policies']['hybrid']['summary']['stable'])
        assert budget == (F(1, 20) if eta == 0 else F(97843262785, 1024000000000))
        results[str(eta)] = calculate(10, eta, F(1, 2), budget, reference)
        log(a, 'CONDITION_COMPLETE '+str(eta)+'/20')
    save(a/'RESULTS.json', {'conditions': results, 'main_condition': '1'})
    check_freeze(a)
    log(a, 'MAIN_COMPLETE')
    save(a/'MANIFEST.json', {'status': 'COMPLETE', 'finished': utc(),
         'wall_seconds': time.monotonic()-start,
         'outputs': {str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}})
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_stable_constraint.py'), str(a)],
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
            for name in SOURCES:
                (a/'inputs'/name).write_bytes((ROOT/name).read_bytes())
            inputs = [ROOT/name for name in SOURCES+REFERENCES]
            inputs += [REFERENCE/name for name in ('RESULTS.json', 'MANIFEST.json', 'READBACK.json')]
            save(a/'FREEZE.json', {'created': utc(), 'inputs': {str(p): sha(p) for p in inputs},
                 'snapshots': {name: sha(a/'inputs'/name) for name in SOURCES},
                 'T': 10, 'eta': [0, 1], 'rho': '1/2', 'c': '1/10',
                 'alpha': [1, 0], 'max_oracle_calls': MAX_CALLS, 'python': platform.python_version()})
            log(a, 'QUALIFICATION_START')
            start = time.monotonic()
            qualified, fixtures = qualify()
            qualified['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', qualified)
            save(a/'SHORT_FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic()
            benchmark = calculate(7, 1, F(1, 3), F(3, 40))
            seconds = time.monotonic()-start
            forecast = 120+6*3**3*seconds
            save(a/'BENCHMARK.json', {'T': 7, 'eta': 1, 'rho': '1/3', 'K': '3/40',
                 'seconds': seconds, 'forecast_seconds': forecast,
                 'oracle_calls': {name: p['oracle_calls'] for name, p in benchmark['problems'].items()}})
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
            save(a/name, {'utc': utc(), 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
