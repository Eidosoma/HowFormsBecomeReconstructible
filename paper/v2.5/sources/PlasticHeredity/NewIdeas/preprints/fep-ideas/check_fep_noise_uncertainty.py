#!/usr/bin/env python3
"""Exact joint noise/onset beliefs with one-constraint robust certificates."""
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import time

# Exact posterior-score sums can have thousands of decimal digits.
sys.set_int_max_str_digits(0)

ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE = BASE/'fep-noise-uncertainty-v1'
DATA = {k: BASE/('fep-'+n+'-v1')/'attempt-01' for k, n in
        [('mismatch', 'noise-mismatch'), ('stable', 'stable-constraint'),
         ('deterministic', 'deterministic-recovery')]}
SOURCES = ('FEP_NOISE_UNCERTAINTY_V1.md', 'check_fep_noise_uncertainty.py',
           'readback_fep_noise_uncertainty.py')
REFERENCES = ('FEP_NOISE_MISMATCH_V1.md', 'FEP_NOISE_MISMATCH_V1_REPORT.md',
              'FEP_STABLE_CONSTRAINT_V1.md', 'FEP_STABLE_CONSTRAINT_V1_REPORT.md',
              'FEP_DETERMINISTIC_RECOVERY_V1.md', 'FEP_DETERMINISTIC_RECOVERY_V1_REPORT.md')
FIELDS = ('cost', 'errors', 'purchases', 'post_cost', 'post_errors',
          'post_purchases', 'delay', 'missing', 'recovery')
BUDGET = F(19568652557, 204800000000)
MAX_CALLS = 128


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())


def save(p, value):
    with Path(p).open('x') as out:
        json.dump(value, out, default=lambda x: str(x) if isinstance(x, F) else x,
                  indent=2, sort_keys=True)
        out.write('\n')


class Model:
    def __init__(self, T, rho=F(1, 2), noises=(4, 5, 6)):
        self.T, self.rho, self.noises, self.c = T, rho, tuple(noises), F(1, 10)
        assert T > 0 and 0 < rho < 1 and all(0 < n <= 10 for n in noises)
        self.M = len(noises)
        block = (T*(rho.denominator-rho.numerator),)+(rho.numerator,)*T
        common = math.gcd(*block)
        self.prior = tuple(w//common for w in block)*self.M
        self.hypotheses = tuple((e, tau) for e in range(self.M) for tau in range(T+1))
        self.update = lru_cache(None)(self._update)

    def _update(self, t, weights, label):
        raw = tuple(w*(100-self.noises[e] if label == int(0 < tau <= t)
                       else self.noises[e]) for w, (e, tau) in zip(weights, self.hypotheses))
        common = math.gcd(*raw)
        return tuple(w//common for w in raw), common


class Oracle:
    def __init__(self, m, mu, erased):
        self.m, self.mu, self.erased = m, mu, erased
        utility = {t: tuple(F(1, m.T)
                   + (1/(m.rho*(m.T-tau+1)) if 0 < tau <= t else 0)
                   + (m.M*mu/((1-m.rho)*m.T) if e == m.M-1 and tau == 0 else 0)
                   for e, tau in m.hypotheses) for t in range(1, m.T+1)}
        den = math.lcm(*(v.denominator for row in utility.values() for v in row))
        self.coeff = {t: tuple(int(v*den) for v in row) for t, row in utility.items()}
        self.scale = 100*den
        self.value = lru_cache(None)(self._value)

    def scores(self, t, weights):
        m = self.m
        total = sum(w*c for w, c in zip(weights, self.coeff[t]))
        follow = sum(w*c*(100-m.noises[e] if 0 < tau <= t else m.noises[e])
                     for w, c, (e, tau) in zip(weights, self.coeff[t], m.hypotheses))
        future = self.value(t+1, weights)
        scores = dict(F=follow+future, R=100*total-follow+future, B=10*total)
        if self.erased:
            scores['B'] += future
        else:
            for label in (0, 1):
                new, common = m.update(t, weights, label)
                scores['B'] += F(common, 100)*self.value(t+1, new)
        return scores

    def _value(self, t, weights):
        return F(0) if t > self.m.T else min(self.scores(t, weights).values())

    def root(self):
        return self.value(1, self.m.prior)/(self.scale*sum(self.m.prior))

    def graph(self):
        m, nodes, index = self.m, [], {}

        def visit(t, weights):
            if t > m.T: return None
            key = t, weights
            if key in index: return index[key]
            i = index[key] = len(nodes)
            nodes.append(None)
            scores = self.scores(t, weights)
            action = min(('B', 'F', 'R'), key=lambda a: scores[a])
            if action == 'B':
                children = {str(d): visit(t+1, weights if self.erased else m.update(t, weights, d)[0])
                            for d in (0, 1)}
            else:
                children = {'N': visit(t+1, weights)}
            nodes[i] = dict(t=t, weights=weights, action=action, children=children)
            return i

        visit(1, m.prior)
        return nodes


def evaluate(m, graph, e, tau):
    eps = F(m.noises[e], 100)

    @lru_cache(None)
    def walk(i):
        if i is None: return (F(0),)*5+(F(1),)
        node = graph[i]
        t, action = node['t'], node['action']
        post, buy = tau is not None and t >= tau, action == 'B'
        risk = 1-eps if post else eps
        branches = [(str(d), risk if d else 1-risk) for d in (0, 1)] if buy else [('N', F(1))]
        future = [sum(p*walk(node['children'][label])[k] for label, p in branches) for k in range(6)]
        error = F(0) if buy else risk if action == 'F' else 1-risk
        future[0] += error
        future[1] += buy
        if post:
            future[2] += error
            future[3] += buy
            if buy: future[4], future[5] = F(0), F(0)
            else: future[4] += 1
        return tuple(future)

    errors, purchases, pe, pb, delay, missing = walk(0)
    return dict(noise_index=e, onset=tau, cost=errors+m.c*purchases, errors=errors, purchases=purchases,
                post_cost=pe+m.c*pb, post_errors=pe, post_purchases=pb, delay=delay, missing=missing,
                recovery=None if tau is None else (pe+m.c*pb)/(m.T-tau+1))


def summarize(m, worlds):
    rates = {}
    for e in range(m.M):
        rows = worlds[e*(m.T+1):(e+1)*(m.T+1)]
        S = rows[0]['cost']/m.T
        B = (1-m.rho)*S+m.rho*sum(w['cost'] for w in rows[1:])/(m.T*m.T)
        R = sum(w['recovery'] for w in rows[1:])/m.T
        rates[str(e)] = dict(stable=S, B=B, R=R, J=B+R,
            stable_errors=rows[0]['errors'], stable_purchases=rows[0]['purchases'],
            mean_changed_errors=sum(w['errors'] for w in rows[1:])/m.T,
            mean_changed_purchases=sum(w['purchases'] for w in rows[1:])/m.T,
            mean_post_errors=sum(w['post_errors'] for w in rows[1:])/m.T,
            mean_post_purchases=sum(w['post_purchases'] for w in rows[1:])/m.T,
            capped_first_delay=sum(w['delay'] for w in rows[1:])/m.T,
            no_post_purchase_probability=sum(w['missing'] for w in rows[1:])/m.T)
    return dict(rates=rates, C=sum(s['J'] for s in rates.values())/m.M,
                S_last=rates[str(m.M-1)]['stable'])


def record(m, graph, mu=None, root=None):
    worlds = [evaluate(m, graph, e, tau) for e in range(m.M) for tau in [None, *range(1, m.T+1)]]
    summary = summarize(m, worlds)
    if root is not None: assert root == summary['C']+mu*summary['S_last']
    return dict(graph=graph, worlds=worlds, summary=summary, mu=mu, root=root)


def oracle(m, mu, erased):
    p = Oracle(m, mu, erased)
    result = record(m, p.graph(), mu, p.root())
    p.value.cache_clear()
    return result


def mix(m, policies, components):
    assert sum(c['weight'] for c in components) == 1 and all(c['weight'] >= 0 for c in components)
    worlds = []
    for i in range(m.M*(m.T+1)):
        example = policies[components[0]['policy']]['worlds'][i]
        row = {k: example[k] for k in ('noise_index', 'onset')}
        for k in FIELDS:
            row[k] = None if example[k] is None else sum(
                c['weight']*policies[c['policy']]['worlds'][i][k] for c in components)
        worlds.append(row)
    return dict(components=components, worlds=worlds, summary=summarize(m, worlds))


def constrained(m, budget, erased):
    assert budget >= F(m.noises[-1], 100)
    floor = [dict(t=t, weights=m.prior, action='F', children={'N': t if t < m.T else None})
             for t in range(1, m.T+1)]
    policies = dict(floor=record(m, floor), oracle000=oracle(m, F(0), erased))
    low, high, witness, mu, trace = 'floor', 'oracle000', 'oracle000', F(0), []
    if policies[high]['summary']['S_last'] <= budget:
        components = [dict(policy=high, weight=F(1))]
        trace.append(dict(oracle=high, decision='unconstrained_feasible'))
    else:
        for call in range(1, MAX_CALLS):
            a, b = policies[low]['summary'], policies[high]['summary']
            assert a['S_last'] <= budget < b['S_last'] and a['C'] >= b['C']
            mu = (a['C']-b['C'])/(b['S_last']-a['S_last'])
            witness = f'oracle{call:03d}'
            p = policies[witness] = oracle(m, mu, erased)
            chord = a['C']+mu*a['S_last']
            assert p['root'] <= chord
            step = dict(oracle=witness, low=low, high=high, chord=chord)
            if p['root'] == chord:
                h = (budget-a['S_last'])/(b['S_last']-a['S_last'])
                components = [c for c in [dict(policy=low, weight=1-h), dict(policy=high, weight=h)] if c['weight']]
                step['decision'] = 'dual_certificate'
                trace.append(step)
                break
            if p['summary']['S_last'] == budget:
                components = [dict(policy=witness, weight=F(1))]
                step['decision'] = 'exact_budget'
                trace.append(step)
                break
            step['decision'] = 'replace_low' if p['summary']['S_last'] < budget else 'replace_high'
            trace.append(step)
            if p['summary']['S_last'] < budget: low = witness
            else: high = witness
        else: raise RuntimeError('Fixed 128-call oracle ceiling exceeded')
    solution = mix(m, policies, components)
    lower = policies[witness]['root']-mu*budget
    assert solution['summary']['S_last'] <= budget and solution['summary']['C'] == lower
    feasible = [n for n, p in policies.items() if all(s['stable'] <= budget for s in p['summary']['rates'].values())]
    best = min(feasible, key=lambda n: (policies[n]['summary']['C'], n))
    return dict(erased=erased, budget=budget, policies=policies, trace=trace, solution=solution,
                best_saved_feasible_deterministic=best,
                full_stable_optimum=all(s['stable'] <= budget for s in solution['summary']['rates'].values()),
                certificate=dict(mu=mu, oracle=witness, lower_bound=lower, duality_gap=F(0)),
                oracle_calls=len(policies)-1)


def diagnostics(m, graph, erased):
    rows = []
    for e in range(m.M):
        eps = F(m.noises[e], 100)
        for tau in [None, *range(1, m.T+1)]:
            @lru_cache(None)
            def walk(i):
                node = graph[i]
                t, w = node['t'], tuple(node['weights'])
                risk = 1-eps if tau is not None and t >= tau else eps
                branches = [(str(d), risk if d else 1-risk) for d in (0, 1)] if node['action'] == 'B' else [('N', F(1))]
                result = [F(0), F(0)]
                for label, mass in branches:
                    child = node['children'][label]
                    if child is None:
                        final = m.update(t, w, int(label))[0] if label != 'N' and not erased else w
                        probs = [F(sum(final[j*(m.T+1):(j+1)*(m.T+1)]), sum(final)) for j in range(m.M)]
                        pair = probs[e], sum((q-int(j == e))**2 for j, q in enumerate(probs))
                    else: pair = walk(child)
                    result = [a+mass*b for a, b in zip(result, pair)]
                return tuple(result)
            p, b = walk(0)
            rows.append(dict(noise_index=e, onset=tau, true_probability=p, brier=b))
    per_noise = {}
    for e in range(m.M):
        group = rows[e*(m.T+1):(e+1)*(m.T+1)]
        per_noise[str(e)] = {k: (1-m.rho)*group[0][k]+m.rho*sum(w[k] for w in group[1:])/m.T
                             for k in ('true_probability', 'brier')}
    average = {k: sum(r[k] for r in per_noise.values())/m.M for k in ('true_probability', 'brier')}
    assert average['brier'] == 1-average['true_probability']
    prior = 1-F(1, m.M)
    if erased: assert average['brier'] == prior
    return dict(worlds=rows, rates=per_noise, average=average, prior_brier=prior, brier_gain=prior-average['brier'])


def calculate(T, rho, budget):
    m = Model(T, rho)
    problems = {}
    for erased in (False, True):
        p = constrained(m, budget, erased)
        chosen = {'oracle000', p['best_saved_feasible_deterministic']} | {c['policy'] for c in p['solution']['components']}
        p['diagnostics'] = {n: diagnostics(m, p['policies'][n]['graph'], erased) for n in sorted(chosen)}
        problems['erased' if erased else 'retained'] = p
    return dict(T=T, rho=rho, noises=m.noises, c=m.c, budget=budget, problems=problems)


def gates(summary, references, budget):
    rates = {}
    for e, rate in enumerate(('0.04', '0.05', '0.06')):
        s, h = summary['rates'][str(e)], references['conditions'][rate]['policies']['hybrid']['summary']
        row = dict(below_always=s['R'] < F(1, 10), below_hybrid=s['R'] < F(h['R']),
                   stable_not_higher=s['stable'] <= budget)
        row['joint'] = all(row.values())
        row['matched_stable_not_higher'] = s['stable'] <= F(h['stable'])
        rates[rate] = row
    return dict(rates=rates, joint=all(r['joint'] for r in rates.values()))


def controls(case, references):
    m = Model(case['T'], case['rho'])
    frozen = {}
    for name in references['conditions']['0.05']['policies']:
        worlds = []
        for e, rate in enumerate(('0.04', '0.05', '0.06')):
            for row in references['conditions'][rate]['policies'][name]['worlds']:
                worlds.append(dict(noise_index=e, onset=row['onset'], **{k: None if row[k] is None else F(row[k]) for k in FIELDS}))
        frozen[name] = dict(worlds=worlds, summary=summarize(m, worlds))
    low, high = frozen['low_component'], frozen['anchor']
    lower, upper = F(0), F(1)
    for e in range(m.M):
        a, b = low['summary']['rates'][str(e)]['stable'], high['summary']['rates'][str(e)]['stable']
        if b > a: upper = min(upper, (case['budget']-a)/(b-a))
        elif b < a: lower = max(lower, (case['budget']-a)/(b-a))
        else: assert a <= case['budget']
    assert 0 <= lower <= upper <= 1
    probability = upper if high['summary']['C'] < low['summary']['C'] else lower
    result = mix(m, frozen, [dict(policy='low_component', weight=1-probability), dict(policy='anchor', weight=probability)])
    result.update(feasible_interval=[lower, upper], probability_high=probability,
                  gate=gates(result['summary'], references, case['budget']))
    for p in case['problems'].values():
        p['gate'] = gates(p['solution']['summary'], references, case['budget'])
        best = p['best_saved_feasible_deterministic']
        p['deterministic_gate'] = gates(p['policies'][best]['summary'], references, case['budget'])
    joint = case['problems']['retained']['policies']['oracle000']['summary']['C']
    delta = joint-frozen['recovery']['summary']['C']
    assert delta <= 0
    return dict(frozen=frozen, fixed_pool=result, unconstrained_C_delta=delta)


@lru_cache(None)
def trees(T):
    if T == 0: return (None,)
    sub = trees(T-1)
    return tuple([(a, x) for a in ('F', 'R') for x in sub]+[('B', x, y) for x in sub for y in sub])


def exhaustive_points(m, erased):
    if erased:
        def build(word):
            tree = None
            for a in reversed(word): tree = (a, tree, tree) if a == 'B' else (a, tree)
            return tree
        candidates = [build(w) for w in itertools.product('FBR', repeat=m.T)]
    else: candidates = trees(m.T)

    @lru_cache(None)
    def walk(tree, t, e, tau):
        if tree is None: return F(0), F(0)
        post = 0 < tau <= t
        eps = F(m.noises[e], 100)
        risk = 1-eps if post else eps
        if tree[0] == 'B':
            left, right = walk(tree[1], t+1, e, tau), walk(tree[2], t+1, e, tau)
            future = tuple((1-risk)*a+risk*b for a, b in zip(left, right))
            loss = m.c
        else:
            future = walk(tree[1], t+1, e, tau)
            loss = risk if tree[0] == 'F' else 1-risk
        return loss+future[0], (loss if post else 0)+future[1]

    points = set()
    for tree in candidates:
        C = F(0)
        for e in range(m.M):
            S = walk(tree, 1, e, 0)[0]/m.T
            changed = [walk(tree, 1, e, tau) for tau in range(1, m.T+1)]
            B = (1-m.rho)*S+m.rho*sum(x[0] for x in changed)/(m.T*m.T)
            R = sum(x[1]/(m.T-tau+1) for tau, x in enumerate(changed, 1))/m.T
            C += (B+R)/m.M
        points.add((S, C))
    return points, len(candidates)


def exhaustive_min(points, budget):
    by_s = {}
    for s, c in points: by_s[s] = min(c, by_s.get(s, c))
    lows, highs = [(s, c) for s, c in by_s.items() if s <= budget], [(s, c) for s, c in by_s.items() if s > budget]
    best = min(c for _, c in lows)
    for s, c in lows:
        for u, v in highs:
            weight = (budget-s)/(u-s)
            best = min(best, (1-weight)*c+weight*v)
    return best


def qualify():
    checks, cases, candidate_total = 0, 0, 0
    for T in range(1, 5):
        for rho in (F(1, 3), F(1, 2)):
            for erased in (False, True):
                if T == 4 and not erased: continue
                m = Model(T, rho)
                points, count = exhaustive_points(m, erased)
                candidate_total += count
                for mu in (F(0), F(1), F(3)):
                    assert oracle(m, mu, erased)['root'] == min(c+mu*s for s, c in points)
                    checks += 1
                for budget in (F(6, 100), F(8, 100), F(1, 10)):
                    p = constrained(m, budget, erased)
                    assert p['solution']['summary']['C'] == exhaustive_min(points, budget)
                    checks += 1
                    for q in p['policies'].values():
                        if q['mu'] is not None:
                            assert q['root'] == min(c+q['mu']*s for s, c in points)
                            checks += 1
                cases += 1
    for T, rho, erased, mu in itertools.product((1, 2, 3), (F(1, 3), F(1, 2)), (False, True), (F(0), F(1), F(3))):
        one, three = Model(T, rho, (5,)), Model(T, rho, (5, 5, 5))
        # Duplicate physical classes: last-class stable penalty averages to the
        # same scalar penalty because no history distinguishes the class labels.
        a, b = oracle(one, mu, erased), oracle(three, mu, erased)
        assert a['root'] == b['root'] and a['summary']['C'] == b['summary']['C']
        checks += 2
    m = Model(3)
    post, _ = m.update(1, m.prior, 1)
    joint = [F(w, sum(post)) for w in post]
    marginal_e = [sum(joint[e*4:(e+1)*4]) for e in range(3)]
    marginal_tau = [sum(joint[e*4+j] for e in range(3)) for j in range(4)]
    assert any(joint[e*4+j] != marginal_e[e]*marginal_tau[j] for e in range(3) for j in range(4))
    checks += 1
    for eps, z, y in itertools.product((F(4, 100), F(5, 100), F(6, 100)), (0, 1), (0, 1)):
        assert sum(F(1, 2)*(eps if (x ^ z ^ y) else 1-eps) for x in (0, 1)) == F(1, 2)
        checks += 1
    fixtures = [calculate(3, rho, F(8, 100)) for rho in (F(1, 3), F(1, 2))]
    for case in fixtures:
        for diag in case['problems']['erased']['diagnostics'].values():
            assert diag['brier_gain'] == 0
            checks += 1
    return dict(passed=True, checks=checks, cases=cases, candidate_total=candidate_total,
                tree_counts={str(t): len(trees(t)) for t in (1, 2, 3)}), fixtures


def check_freeze(a):
    freeze = read(a/'FREEZE.json')
    for p, h in freeze['inputs'].items(): assert sha(p) == h, p
    for n, h in freeze['snapshots'].items(): assert sha(a/'inputs'/n) == h, n


def log(a, message):
    line = utc()+' '+message
    with (a/'RUN_LOG.txt').open('a') as out: out.write(line+'\n')
    print(line, flush=True)


def run_main(a, detached):
    check_freeze(a)
    forecast = read(a/'BENCHMARK.json')['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a/'STARTED.json', dict(utc=utc(), pid=os.getpid(), sid=os.getsid(0),
         affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0), detached=detached,
         library_threads={k: os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')}))
    start = time.monotonic(); log(a, 'MAIN_START')
    case = calculate(10, F(1, 2), BUDGET)
    case['controls'] = controls(case, read(DATA['mismatch']/'RESULTS.json'))
    prior = read(DATA['stable']/'RESULTS.json')['conditions']['1']['problems']['erased_recovery_bound']
    case['inherited_erased_R_lower_bound'] = prior['certificate']['lower_bound']
    assert F(case['inherited_erased_R_lower_bound']) > F(1, 10)
    save(a/'RESULTS.json', case)
    check_freeze(a); log(a, 'MAIN_COMPLETE')
    save(a/'MANIFEST.json', dict(status='COMPLETE', finished=utc(), wall_seconds=time.monotonic()-start,
         outputs={str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a/'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_noise_uncertainty.py'), str(a)],
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
            save(a/'FREEZE.json', dict(created=utc(), inputs={str(p): sha(p) for p in paths},
                 snapshots={n: sha(a/'inputs'/n) for n in SOURCES}, T=10, rho='1/2', noises=[4, 5, 6],
                 noise_denominator=100, price='1/10', budget=BUDGET, max_oracle_calls=MAX_CALLS,
                 python=platform.python_version()))
            log(a, 'QUALIFICATION_START'); start = time.monotonic()
            q, fixtures = qualify(); q['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', q); save(a/'SHORT_FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic(); bench = calculate(7, F(1, 3), F(3, 40)); seconds = time.monotonic()-start
            forecast = 120+6*3**3*seconds
            save(a/'BENCHMARK.json', dict(T=7, rho='1/3', noises=[4, 5, 6], budget='3/40', seconds=seconds,
                 forecast_seconds=forecast, oracle_calls={k:p['oracle_calls'] for k,p in bench['problems'].items()}))
            log(a, 'BENCHMARK_COMPLETE')
            if forecast > 7200: log(a, 'FEASIBILITY_CEILING_EXCEEDED'); return
            if forecast > 600: print('DETACHED_MAIN_REQUIRED', flush=True); return
        run_main(a, args.detached)
    except Exception as error:
        n = 'READBACK_FAILURE.json' if (a/'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a/n).exists(): save(a/n, dict(utc=utc(), error=repr(error)))
        raise


if __name__ == '__main__': main()
