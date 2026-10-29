#!/usr/bin/env python3
"""Exact finite hidden-reversal experiment; standard library only."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-checking-tradeoff-v1')
POLICIES = ('full', 'full_gap1', 'hybrid_ct4_gap1', 'ct4', 'always', 'erase')
SOURCES = ('FEP_CHECKING_TRADEOFF_V1.md', 'check_fep_checking_tradeoff.py',
           'readback_fep_checking_tradeoff.py')
REFERENCES = ('FEP_PLANNED_RECOVERY_V1_REPORT.md',
              'FEP_REVERSAL_FEEDBACK_AUDIT_V1_REPORT.md',
              'FEP_PLANNED_CHECKING_V1_REPORT.md')


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
    def __init__(self, T, rho=F(1, 2), c=F(1, 10)):
        self.T, self.rho, self.c = T, rho, c
        self.value = lru_cache(None)(self._value)

    def p(self, t, k):
        return self.rho * (t-k) / (self.T-self.rho*k)

    def known_value(self, h, d, cap):
        return self.c * ((h+d)//2) if cap else F(0)

    def scores(self, t, k, h, d=0, cap=False, known=False):
        assert 1 <= h <= self.T-t+1
        if known:
            continuation = self.known_value(h-1, 1, cap)
            scores = {'F': 1+continuation, 'R': continuation,
                      'B': self.c+self.known_value(h-1, 0, cap)}
        else:
            p = self.p(t, k)
            following = self.value(t+1, k, h-1, 1 if cap else 0, cap)
            negative = self.value(t+1, t, h-1, 0, cap) if p < 1 else F(0)
            scores = {'F': p+following, 'R': 1-p+following,
                      'B': self.c+(1-p)*negative+p*self.known_value(h-1, 0, cap)}
        if cap and d:
            return {'B': scores['B']}
        return scores

    @staticmethod
    def best(scores):
        return min(scores, key=lambda a: (scores[a], {'B': 0, 'F': 1, 'R': 2}[a]))

    def _value(self, t, k, h, d=0, cap=False):
        if not h:
            return F(0)
        return min(self.scores(t, k, h, d, cap).values())

    def action(self, name, t, k, d, known):
        if name == 'always':
            return 'B'
        if name == 'erase':
            p = self.p(t, 0)
            return self.best({'F': p, 'R': 1-p, 'B': self.c})
        if name == 'hybrid_ct4_gap1' and d:
            return 'B'
        h = self.T-t+1 if name.startswith('full') else min(4, self.T-t+1)
        return self.best(self.scores(t, k, h, d, name == 'full_gap1', known))


def world(model, name, onset):
    k, d, known = 0, 0, False
    actions, errors, buys = [], [], []
    first, after_detection_buys = None, 0
    for t in range(1, model.T+1):
        a = model.action(name, t, k, d, known)
        flipped = onset is not None and t >= onset
        actions.append(a)
        errors.append(int(a != 'B' and (a == 'R') != flipped))
        buys.append(int(a == 'B'))
        if a == 'B':
            after_detection_buys += int(known)
            if flipped and first is None:
                first = t
            if name != 'erase':
                if flipped:
                    known = True
                else:
                    k = t
        d = 0 if a == 'B' else 1
    total = sum(errors)+model.c*sum(buys)
    post = None if onset is None else (sum(errors[onset-1:])+
             model.c*sum(buys[onset-1:]))/(model.T-onset+1)
    return {'onset': onset, 'actions': ''.join(actions), 'errors': sum(errors),
            'purchases': sum(buys), 'cost': total,
            'recovery': post, 'first_post_purchase': first,
            'purchases_after_retained_detection': after_detection_buys}


def summarize(model, worlds):
    stable = worlds[0]['cost']/model.T
    changed = sum(w['cost'] for w in worlds[1:])/(model.T*model.T)
    recovery = sum(w['recovery'] for w in worlds[1:])/model.T
    return {'stable': stable, 'changed_full': changed, 'recovery': recovery,
            'prior_full': (1-model.rho)*stable+model.rho*changed,
            'mean_purchases_stable': worlds[0]['purchases'],
            'mean_purchases_changed': F(sum(w['purchases'] for w in worlds[1:]), model.T),
            'mean_errors_changed': F(sum(w['errors'] for w in worlds[1:]), model.T),
            'missing_post_purchase_worlds': sum(w['first_post_purchase'] is None for w in worlds[1:]),
            'onsets': {str(w['onset']): w['recovery'] for w in worlds[1:]
                       if w['onset'] in (13, 38, 63, 88)}}


def schedule_metrics(model, schedule):
    T, c = model.T, model.c
    recovery, changed_cost, errors, buys = F(0), F(0), 0, 0
    for tau in range(1, T+1):
        next_index = next((i for i, t in enumerate(schedule) if t >= tau), None)
        if next_index is None:
            delay, count, post = T-tau+1, len(schedule), F(T-tau+1)
        else:
            delay, count = schedule[next_index]-tau, next_index+1
            post = delay+c
        recovery += post/(T-tau+1)
        changed_cost += delay+c*count
        errors += delay
        buys += count
    stable = c*len(schedule)/T
    changed = changed_cost/(T*T)
    return {'stable': stable, 'recovery': recovery/T, 'changed_full': changed,
            'prior_full': (1-model.rho)*stable+model.rho*changed,
            'mean_errors_changed': F(errors, T), 'mean_purchases_changed': F(buys, T)}


def frontier(model):
    T, c = model.T, model.c
    edge = [[F(0) for _ in range(T+1)] for _ in range(T+1)]
    for k in range(T):
        for j in range(k+1, T+1):
            edge[k][j] = sum((F(j-tau)+c)/(T*(T-tau+1)) for tau in range(k+1, j+1))
    prev = {0: F(0)}
    parents = {}
    rows = [{'m': 0, 'schedule': [], **schedule_metrics(model, [])}]
    for m in range(1, T+1):
        current = {}
        for j in range(m, T+1):
            candidates = ((prev[k]+edge[k][j], k) for k in prev if k < j)
            current[j], parents[m, j] = min(candidates)
        optimum, last = min((v+F(T-j, T), j) for j, v in current.items())
        schedule = []
        for remaining in range(m, 0, -1):
            schedule.append(last)
            last = parents[remaining, last]
        schedule.reverse()
        metrics = schedule_metrics(model, schedule)
        assert metrics['recovery'] == optimum
        rows.append({'m': m, 'schedule': schedule, **metrics})
        prev = current
    nondominated = []
    for row in rows:
        if not nondominated or row['recovery'] < rows[nondominated[-1]]['recovery']:
            nondominated.append(row['m'])
    hull = []
    for m in nondominated:
        while len(hull) >= 2:
            a, b, z = rows[hull[-2]], rows[hull[-1]], rows[m]
            cross = ((b['stable']-a['stable'])*(z['recovery']-a['recovery'])-
                     (b['recovery']-a['recovery'])*(z['stable']-a['stable']))
            if cross > 0:
                break
            hull.pop()
        hull.append(m)
    return {'rows': rows, 'nondominated_m': nondominated, 'convex_envelope_m': hull}


def calculate(T=100, rho=F(1, 2), c=F(1, 10)):
    model = Model(T, rho, c)
    policies = {}
    for name in POLICIES:
        worlds = [world(model, name, onset) for onset in [None, *range(1, T+1)]]
        policies[name] = {'worlds': worlds, 'summary': summarize(model, worlds)}
    front = frontier(model)
    hybrid = policies['hybrid_ct4_gap1']['summary']
    feasible = [row['m'] for row in front['rows'] if row['stable'] < hybrid['stable']
                and row['recovery'] < min(hybrid['recovery'], c)]
    return {'T': T, 'rho': rho, 'c': c, 'policies': policies, 'frontier': front,
            'feasibility': {'feasible_m': feasible,
                            'smallest_m': min(feasible) if feasible else None,
                            'exists': bool(feasible)},
            'bellman_total': {'full': model.value(1, 0, T),
                              'full_gap1': model.value(1, 0, T, 0, True)},
            'cache': model.value.cache_info()._asdict()}


def brute(model, cap):
    best = None
    for actions in itertools.product('FBR', repeat=model.T):
        d = 0
        valid = True
        for a in actions:
            if cap and d and a != 'B':
                valid = False
                break
            d = 0 if a == 'B' else 1
        if not valid:
            continue
        expected = F(0)
        for tau in [None, *range(1, model.T+1)]:
            cost = F(0)
            for t, a in enumerate(actions, 1):
                flipped = tau is not None and t >= tau
                if a == 'B':
                    cost += model.c
                    if flipped:
                        cost += model.c*((model.T-t)//2) if cap else 0
                        break
                else:
                    cost += int((a == 'R') != flipped)
            expected += cost*((1-model.rho) if tau is None else model.rho/model.T)
        best = expected if best is None else min(best, expected)
    return best


def qualify():
    checks = 0
    for T in range(1, 7):
        for rho in (F(0), F(1, 2), F(1)):
            model = Model(T, rho)
            for cap in (False, True):
                assert model.value(1, 0, T, 0, cap) == brute(model, cap)
                checks += 1
            front = frontier(model)
            for m in range(T+1):
                optimum = min(schedule_metrics(model, schedule)['recovery']
                              for schedule in itertools.combinations(range(1, T+1), m))
                assert front['rows'][m]['recovery'] == optimum
                checks += 1
            for k in range(T):
                for t in range(k+1, T+1):
                    weights = [(1-rho)]+[rho/T if tau > k else F(0)
                                        for tau in range(1, T+1)]
                    p = sum(weights[1:t+1])/sum(weights)
                    assert p == model.p(t, k)
                    assert 0 <= p <= 1
                    checks += 2
            for name in POLICIES:
                worlds = [world(model, name, tau) for tau in [None, *range(1, T+1)]]
                summary = summarize(model, worlds)
                if name in ('full', 'full_gap1'):
                    assert summary['prior_full']*T == model.value(1, 0, T, 0, name == 'full_gap1')
                    checks += 1
                for w in worlds:
                    if name.endswith('gap1'):
                        assert all('B' in w['actions'][j:j+2] for j in range(T-1))
                        checks += 1
                if name == 'erase':
                    assert len({w['actions'] for w in worlds}) == 1
                    checks += 1
            for z in (0, 1):
                for y in (0, 1):
                    assert sum(F(1, 2) for x in (0, 1) if x ^ z == y) == F(1, 2)
                    checks += 1
            if rho == 0:
                assert model.value(1, 0, T) == 0
                assert model.value(1, 0, T, 0, True) == model.c*(T//2)
                checks += 2
    return {'passed': True, 'exact_assertions': checks,
            'brute_force_horizons': list(range(1, 7)), 'rho': ['0', '1/2', '1']}


def verify_inputs(attempt):
    freeze = json.loads((attempt/'FREEZE.json').read_text())
    for path, identity in freeze['inputs'].items():
        assert sha(path) == identity, path
    for name, identity in freeze['snapshots'].items():
        assert sha(attempt/'inputs'/name) == identity, name


def log(attempt, message):
    line = utc()+' '+message
    with (attempt/'RUN_LOG.txt').open('a') as stream:
        stream.write(line+'\n')
    print(line, flush=True)


def main_run(attempt, detached):
    verify_inputs(attempt)
    bench = json.loads((attempt/'BENCHMARK.json').read_text())
    assert bench['forecast_seconds'] <= 7200
    assert bench['forecast_seconds'] <= 600 or detached
    assert not (attempt/'STARTED.json').exists()
    save(attempt/'STARTED.json', {'utc': utc(), 'pid': os.getpid(),
         'sid': os.getsid(0), 'affinity': sorted(os.sched_getaffinity(0)),
         'nice': os.getpriority(os.PRIO_PROCESS, 0), 'detached': detached})
    begin = time.monotonic()
    log(attempt, 'MAIN_START')
    result = calculate()
    save(attempt/'RESULTS.json', result)
    verify_inputs(attempt)
    log(attempt, 'MAIN_COMPLETE')
    outputs = {str(p.relative_to(attempt)): sha(p) for p in sorted(attempt.rglob('*'))
               if p.is_file()}
    save(attempt/'MANIFEST.json', {'status': 'COMPLETE', 'finished': utc(),
         'wall_seconds': time.monotonic()-begin, 'outputs': outputs})
    with (attempt/'READBACK_STDOUT.log').open('x') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_checking_tradeoff.py'),
                        str(attempt)], stdout=stream, stderr=subprocess.STDOUT, check=True)
    print('READBACK_COMPLETE '+str(attempt), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='attempt-01')
    parser.add_argument('--main-only', action='store_true')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt
    assert Path('/mnt/bioIce1').is_mount()
    assert os.statvfs('/mnt/bioIce1').f_bavail*os.statvfs('/mnt/bioIce1').f_frsize > 100_000_000
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        os.nice(10-os.getpriority(os.PRIO_PROCESS, 0))
    attempt = STORE/args.attempt
    if args.main_only:
        assert attempt.is_dir()
    else:
        attempt.mkdir(parents=True, exist_ok=False)
    try:
        if not args.main_only:
            (attempt/'inputs').mkdir()
            for name in SOURCES:
                (attempt/'inputs'/name).write_bytes((ROOT/name).read_bytes())
            save(attempt/'FREEZE.json', {'created': utc(),
                 'inputs': {str(ROOT/name): sha(ROOT/name) for name in SOURCES+REFERENCES},
                 'snapshots': {name: sha(attempt/'inputs'/name) for name in SOURCES},
                 'python': platform.python_version(), 'T': 100, 'rho': '1/2', 'c': '1/10'})
            log(attempt, 'QUALIFICATION_START')
            begin = time.monotonic()
            qualified = qualify()
            qualified['seconds'] = time.monotonic()-begin
            save(attempt/'QUALIFICATION.json', qualified)
            log(attempt, 'QUALIFICATION_PASS')
            begin = time.monotonic()
            benchmark = calculate(40, F(1, 3), F(1, 8))
            seconds = time.monotonic()-begin
            save(attempt/'BENCHMARK.json', {'seconds': seconds,
                 'forecast_seconds': 120+6*(100/40)**3*seconds,
                 'T': 40, 'rho': '1/3', 'c': '1/8', 'policy_count': len(benchmark['policies']),
                 'frontier_rows': len(benchmark['frontier']['rows'])})
            log(attempt, 'BENCHMARK_COMPLETE')
            if 120+6*(100/40)**3*seconds > 600:
                print('DETACHED_MAIN_REQUIRED', flush=True)
                return
        main_run(attempt, args.detached)
    except Exception as exc:
        failure = attempt/('READBACK_FAILURE.json' if (attempt/'MANIFEST.json').exists()
                           else 'FAILURE.json')
        if not failure.exists():
            save(failure, {'utc': utc(), 'error': repr(exc), 'stage': 'prepared/main/readback'})
        raise


if __name__ == '__main__':
    main()
