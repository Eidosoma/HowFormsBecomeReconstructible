#!/usr/bin/env python3
"""Exact recovery preference construction; no hidden onset in the policy API."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STORE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-recovery-objective-v1')
OLD = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-checking-tradeoff-v1/attempt-01')
SOURCES = ('FEP_RECOVERY_OBJECTIVE_V1.md', 'check_fep_recovery_objective.py',
           'readback_fep_recovery_objective.py')
REFERENCES = ('FEP_CHECKING_TRADEOFF_V1.md', 'FEP_CHECKING_TRADEOFF_V1_REPORT.md')
ARMS = {'ordinary': (F(0), False), 'recovery': (F(1), False), 'erased': (F(1), True)}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True,
                  default=lambda x: str(x) if isinstance(x, F) else None)
        stream.write('\n')


class Solver:
    def __init__(self, T, rho=F(1, 2), c=F(1, 10), lam=F(1), erased=False):
        assert T > 0 and 0 < rho <= 1 and c > 0 and lam >= 0
        self.T, self.rho, self.c, self.lam, self.erased = T, rho, c, lam, erased
        self.harmonic = [F(0)]
        for t in range(1, T+1):
            self.harmonic.append(self.harmonic[-1]+F(1, T-t+1))
        self.value = lru_cache(None)(self._value)

    def probability(self, t, k):
        return self.rho*(t-k)/(self.T-self.rho*k)

    def immediate(self, t, k):
        D = self.T-self.rho*k
        H = self.harmonic[t]-self.harmonic[k]
        return {'F': (self.rho*F(t-k, self.T)+self.lam*H)/D,
                'R': (self.T-self.rho*t)/(self.T*D),
                'B': self.c*(F(1, self.T)+self.lam*H/D)}

    def scores(self, t, k):
        scores = self.immediate(t, k)
        common = self.value(t+1, k)
        scores['F'] += common
        scores['R'] += common
        if self.erased:
            assert k == 0
            scores['B'] += common
        else:
            p = self.probability(t, k)
            if p < 1:
                scores['B'] += (1-p)*self.value(t+1, t)
        return scores

    def _value(self, t, k):
        if t > self.T:
            return F(0)
        return min(self.scores(t, k).values())

    @staticmethod
    def best(scores):
        return min(scores, key=lambda a: (scores[a], {'B': 0, 'F': 1, 'R': 2}[a]))

    def action(self, t, last_verified_old, retained_reversal):
        if self.erased:
            assert last_verified_old == 0 and not retained_reversal
        if retained_reversal:
            return 'R'
        return self.best(self.scores(t, last_verified_old))


def trace(solver, tau):
    k, known = 0, False
    actions, ticks, inversions = [], [], []
    first, purchases, errors = None, 0, 0
    weighted = F(0)
    for t in range(1, solver.T+1):
        a = solver.action(t, k, known)
        # The evaluator's physical state enters only after action selection.
        changed = tau is not None and t >= tau
        error = int(a != 'B' and (a == 'R') != changed)
        buy = int(a == 'B')
        physical = error+solver.c*buy
        weight = F(1, solver.T)
        if changed:
            weight += solver.lam/(solver.rho*(solver.T-tau+1))
        weighted += weight*physical
        actions.append(a)
        ticks.append(physical)
        if a == 'R' and not known:
            inversions.append(t)
        errors += error
        purchases += buy
        if buy:
            if changed and first is None:
                first = t
            if not solver.erased:
                if changed:
                    known = True
                else:
                    k = t
    return {'onset': tau, 'actions': ''.join(actions), 'cost': sum(ticks),
            'errors': errors, 'purchases': purchases,
            'recovery': None if tau is None else sum(ticks[tau-1:])/(solver.T-tau+1),
            'weighted_cost': weighted, 'first_post_purchase': first,
            'unverified_inversions': inversions}


def summary(solver, worlds):
    T = solver.T
    stable = worlds[0]['cost']/T
    changed = sum(w['cost'] for w in worlds[1:])/(T*T)
    recovery = sum(w['recovery'] for w in worlds[1:])/T
    B = (1-solver.rho)*stable+solver.rho*changed
    direct = (1-solver.rho)*worlds[0]['weighted_cost']+solver.rho*sum(
        w['weighted_cost'] for w in worlds[1:])/T
    assert direct == B+solver.lam*recovery == solver.value(1, 0)
    return {'stable': stable, 'changed_full': changed, 'B': B, 'R': recovery,
            'J': direct, 'lambda': solver.lam,
            'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
            'mean_changed_errors': F(sum(w['errors'] for w in worlds[1:]), T),
            'mean_changed_purchases': F(sum(w['purchases'] for w in worlds[1:]), T),
            'missing_post_purchase_worlds': sum(w['first_post_purchase'] is None for w in worlds[1:]),
            'unverified_inversions': sum(len(w['unverified_inversions']) for w in worlds),
            'onsets': {str(w['onset']): w['recovery'] for w in worlds[1:]
                       if w['onset'] in (13, 38, 63, 88)}}


def calculate(T=100, rho=F(1, 2), c=F(1, 10), references=True):
    results = {'T': T, 'rho': rho, 'c': c, 'policies': {}}
    for name, (lam, erased) in ARMS.items():
        solver = Solver(T, rho, c, lam, erased)
        worlds = [trace(solver, tau) for tau in [None, *range(1, T+1)]]
        results['policies'][name] = {'worlds': worlds, 'summary': summary(solver, worlds),
                                     'root_value': solver.value(1, 0)}
    if references:
        old = json.loads((OLD/'RESULTS.json').read_text())
        for previous, current in zip(old['policies']['full']['worlds'],
                                     results['policies']['ordinary']['worlds']):
            assert previous['actions'] == current['actions']
            assert F(previous['cost']) == current['cost']
            assert previous['onset'] == current['onset']
        refs = {name: record['summary'] for name, record in old['policies'].items()}
        refs['frontier_18'] = old['frontier']['rows'][18]
        results['references'] = {name: {'stable': F(s['stable']), 'B': F(s['prior_full']),
            'R': F(s['recovery']), 'J1': F(s['prior_full'])+F(s['recovery'])}
            for name, s in refs.items()}
        r = results['policies']['recovery']['summary']
        hybrid = results['references']['hybrid_ct4_gap1']
        gate = {'below_always': r['R'] < c, 'below_hybrid': r['R'] < hybrid['R'],
                'stable_not_higher': r['stable'] <= hybrid['stable']}
        gate['joint'] = all(gate.values())
        results['gate'] = gate
    return results


def brute(T, rho, c, lam, erased):
    optimum = None
    for word in itertools.product('FBR', repeat=T):
        full, recovery = {}, F(0)
        for tau in [None, *range(1, T+1)]:
            cost, post, detected = F(0), F(0), False
            for t, planned in enumerate(word, 1):
                changed = tau is not None and t >= tau
                a = 'R' if detected else planned
                loss = c if a == 'B' else F(int((a == 'R') != changed))
                cost += loss
                if changed:
                    post += loss
                if not erased and a == 'B' and changed:
                    detected = True
            full[tau] = cost
            if tau is not None:
                recovery += post/(T-tau+1)
        B = (1-rho)*full[None]/T+rho*sum(full[tau] for tau in range(1, T+1))/(T*T)
        J = B+lam*recovery/T
        optimum = J if optimum is None else min(J, optimum)
    return optimum


def qualify():
    checks = 0
    for T in range(1, 7):
        for rho in (F(1, 3), F(1, 2), F(1)):
            for lam in (F(0), F(1)):
                for erased in (False, True):
                    s = Solver(T, rho, F(1, 10), lam, erased)
                    assert s.value(1, 0) == brute(T, rho, s.c, lam, erased)
                    checks += 1
                    worlds = [trace(s, tau) for tau in [None, *range(1, T+1)]]
                    summary(s, worlds)
                    checks += 1
                    history_actions = {}
                    for world in worlds:
                        history = []
                        for t, a in enumerate(world['actions'], 1):
                            key = (t, tuple(history))
                            assert history_actions.setdefault(key, a) == a
                            checks += 1
                            if not erased and a == 'B':
                                history.append((t, int(world['onset'] is not None and t >= world['onset'])))
                s = Solver(T, rho, F(1, 10), lam)
                for k in range(T):
                    norm = 1-rho*F(k, T)
                    states = [(None, (1-rho)/norm)]+[(tau, rho/(T*norm)) for tau in range(k+1, T+1)]
                    assert sum(p for _, p in states) == 1
                    checks += 1
                    for t in range(k+1, T+1):
                        direct = {'F': F(0), 'R': F(0), 'B': F(0)}
                        for tau, probability in states:
                            changed = tau is not None and tau <= t
                            weight = F(1, T)+(lam/(rho*(T-tau+1)) if changed else 0)
                            direct['F'] += probability*weight*int(changed)
                            direct['R'] += probability*weight*int(not changed)
                            direct['B'] += probability*weight*s.c
                        assert direct == s.immediate(t, k)
                        assert s.probability(t, k) == sum(p for tau, p in states if tau is not None and tau <= t)
                        checks += 2
    s = Solver(40)
    correct = s.immediate(40, 0)
    mean_weight = correct['B']/s.c
    naive = {'F': mean_weight*s.probability(40, 0),
             'R': mean_weight*(1-s.probability(40, 0)), 'B': correct['B']}
    assert s.best(correct) == 'R' and s.best(naive) == 'B'
    checks += 1
    return {'passed': True, 'exact_assertions': checks,
            'T': list(range(1, 7)), 'rho': ['1/3', '1/2', '1'], 'lambda': ['0', '1'],
            'terminal_counterexample': {'T': 40, 'correct': correct, 'product_shortcut': naive,
                                       'correct_action': 'R', 'product_action': 'B'}}


def check_freeze(a):
    f = json.loads((a/'FREEZE.json').read_text())
    for path, identity in f['inputs'].items():
        assert sha(path) == identity, path
    for name, identity in f['snapshots'].items():
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
    save(a/'RESULTS.json', calculate())
    check_freeze(a)
    log(a, 'MAIN_COMPLETE')
    outputs = {str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}
    save(a/'MANIFEST.json', {'status': 'COMPLETE', 'finished': utc(),
         'wall_seconds': time.monotonic()-start, 'outputs': outputs})
    with (a/'READBACK_STDOUT.log').open('x') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/'readback_fep_recovery_objective.py'), str(a)],
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
    stat = os.statvfs('/mnt/bioIce1')
    assert stat.f_bavail*stat.f_frsize > 100_000_000
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
                 'python': platform.python_version(), 'T': 100, 'rho': '1/2', 'c': '1/10',
                 'lambda': ['0', '1'], 'weight_selection': 'fixed diagnostic, not fitted'})
            log(a, 'QUALIFICATION_START')
            start = time.monotonic()
            q = qualify()
            q['seconds'] = time.monotonic()-start
            save(a/'QUALIFICATION.json', q)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic()
            calculate(40, F(1, 3), F(1, 8), False)
            seconds = time.monotonic()-start
            forecast = 120+6*(100/40)**3*seconds
            save(a/'BENCHMARK.json', {'T': 40, 'rho': '1/3', 'c': '1/8',
                 'seconds': seconds, 'forecast_seconds': forecast})
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
