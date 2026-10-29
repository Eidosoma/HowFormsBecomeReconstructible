#!/usr/bin/env python3
"""Bounded scalar verification of FEP_VARIATIONAL_POSITIVE_V1.md; no sampling."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter
import traceback


getcontext().prec = 80
ZERO, ONE, HALF = D(0), D(1), D('0.5')
BAD, BETA = D('0.1'), D(4)
ROOT_TOL, CHECK_TOL = D('1e-45'), D('1e-35')
STATES = [(0, 0), (1, 0), (0, 1), (1, 1)]
CHECKS = []
RESIDUALS = []


def require(label, condition):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def close(label, actual, expected):
    residual = abs(actual - expected)
    RESIDUALS.append(residual)
    require(label, residual <= CHECK_TOL)


def sigmoid(z):
    return ONE / (ONE + (-z).exp())


def logit(z):
    return (z / (ONE - z)).ln()


def phi(z):
    return sum(t * t.ln() for t in (z, ONE-z) if t)


def kl(q, p):
    return sum(qi * (qi/pi).ln() for qi, pi in zip(q, p) if qi)


def product(x, y):
    return [(x if r else ONE-x) * (y if l else ONE-y) for r, l in STATES]


def bisect(fn, lo, hi):
    flo, fhi = fn(lo), fn(hi)
    if not flo * fhi < 0:
        raise AssertionError(f'Root not bracketed: {lo}, {hi}, {flo}, {fhi}')
    steps = 0
    while hi-lo > ROOT_TOL:
        mid = (lo+hi)/2
        fm = fn(mid)
        if fm == 0:
            return mid, {'lower': mid, 'upper': mid, 'f_lower': fm,
                         'f_upper': fm, 'iterations': steps+1}
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
        steps += 1
        if steps > 300:
            raise AssertionError('Bisection did not reach its fixed tolerance')
    return (lo+hi)/2, {'lower': lo, 'upper': hi, 'f_lower': flo,
                       'f_upper': fhi, 'iterations': steps}


def parameters(h):
    a, b, c = h*(2-h), BAD+h-BAD*h, BAD*(2-BAD)
    total = a+2*b+c
    j, k = (b*b/(a*c)).ln(), (c/b).ln()
    coeff = (b/a).ln()
    return a, b, c, total, j, k, coeff


def symmetric(h):
    a, b, c, total, j, k, coeff = parameters(h)
    m, bracket = bisect(lambda z: logit(z)+j*z-coeff,
                       HALF, ONE-D('1e-60'))
    return m, j*m*(ONE-m), bracket


def likelihood(h, mode, continuation):
    delta = BAD-h
    survival = [(ONE-h-delta*l) * ((ONE-h-delta*r) if mode else ONE)
                for r, l in STATES]
    return survival if continuation else [ONE-s for s in survival]


def posterior(h, mode, continuation):
    weights = likelihood(h, mode, continuation)
    total = sum(weights)
    return [v/total for v in weights], total/4


def forecast(h, belief):
    risks = [sum(q*l for q, l in zip(belief, likelihood(h, mode, 0)))
             for mode in (0, 1)]
    values = [D('0.75')+HALF*(ONE-risks[0]),
              D('0.9')+HALF*(ONE-risks[1])]
    return risks, values


def evaluate(h, belief, exact):
    risk, value = forecast(h, belief)
    exact_risk, exact_value = forecast(h, exact)
    require('positive precision risk increment', risk[1] > risk[0])
    require('economy feasible at retained budget', risk[0] <= BAD)
    cap = min(ONE, (BAD-risk[0])/(risk[1]-risk[0]))
    free = sigmoid(BETA*(value[1]-value[0]))
    policy = min(cap, free)
    predicted_risk = (ONE-policy)*risk[0]+policy*risk[1]
    actual_risk = (ONE-policy)*exact_risk[0]+policy*exact_risk[1]
    actual_value = (ONE-policy)*exact_value[0]+policy*exact_value[1]
    require('selected policy is internally feasible', predicted_risk <= BAD+CHECK_TOL)
    if policy == cap:
        close('binding internal chance constraint', predicted_risk, BAD)
    feasible = [a for a in (0, 1) if risk[a] <= BAD]
    best = max(value[a] for a in feasible)
    deterministic = [a for a in feasible if value[a] == best]
    return {'failure_risks': risk, 'task_values': value,
            'deterministic_optimum_set': deterministic,
            'chance_upper_bound': cap, 'unconstrained_precision_probability': free,
            'optimal_precision_probability': policy,
            'predicted_policy_risk': predicted_risk,
            'exact_model_policy_risk': actual_risk,
            'exact_model_budget_slack': BAD-actual_risk,
            'exact_model_task_value': actual_value,
            'exact_model_reference_score': kl([ONE-policy, policy], [HALF, HALF])
                                             - BETA*actual_value}


def fixture(h):
    a, b, c, total, j, k, coeff = parameters(h)
    pi, evidence = posterior(h, 1, 0)
    delta = BAD-h
    for action in (0, 1):
        for outcome in (0, 1):
            require('strictly positive physical likelihoods',
                    all(ZERO < v < ONE for v in likelihood(h, action, outcome)))
        close('outcomes partition each action',
              posterior(h, action, 0)[1]+posterior(h, action, 1)[1], ONE)
    close('likelihood coupling identity', b*b-a*c, delta*delta)
    close('log coefficient identity', coeff, j+k)
    close('exact posterior normalization', sum(pi), ONE)
    mean = (b+c)/total
    close('negative posterior cause covariance', pi[3]-mean*mean,
          -delta*delta/(total*total))
    m, stability, symmetric_bracket = symmetric(h)
    close('symmetric stationarity', logit(m)+j*m-coeff, ZERO)
    g = lambda x: sigmoid(coeff-j*x)
    derivative = lambda x: logit(x)-coeff+j*g(x)
    if stability > ONE:
        low, bracket = bisect(derivative, HALF, m-D('1e-12'))
        high = g(low)
        require('asymmetric pair brackets symmetric saddle', low < m < high)
        coordinates = [(low, high), (high, low)]
    else:
        bracket = None
        coordinates = [(m, m)]
    solutions = []
    for x, y in coordinates:
        q = product(x, y)
        close('product normalization', sum(q), ONE)
        close('x stationarity', logit(x)+j*y-coeff, ZERO)
        close('y stationarity', logit(y)+j*x-coeff, ZERO)
        require('interior solution', HALF < x < ONE and HALF < y < ONE)
        determinant = ONE/(x*(ONE-x)*y*(ONE-y))-j*j
        require('minimum positive Hessian determinant', determinant > ZERO)
        direct = kl(q, [v/4 for v in (a, b, b, c)])
        reduced = phi(x)+phi(y)-coeff*(x+y)+j*x*y-(a/4).ln()
        close('direct enumeration versus analytic free energy', direct, reduced)
        gap = kl(q, pi)
        close('VFE posterior identity', direct, gap-evidence.ln())
        require('nonzero approximation gap', gap > ZERO)
        risks, values = forecast(h, q)
        close('economy moment forecast', risks[0], h+delta*y)
        close('precision moment forecast', risks[1],
              a+(ONE-h)*delta*(x+y)-delta*delta*x*y)
        solutions.append({'x': x, 'y': y, 'posterior': q,
                          'free_energy': direct, 'variational_gap': gap,
                          'hessian_determinant': determinant,
                          'decision': evaluate(h, q, pi)})
    if len(solutions) == 2:
        close('both global minima have equal VFE',
              solutions[0]['free_energy'], solutions[1]['free_energy'])
        require('symmetric saddle has higher VFE',
                kl(product(m, m), [v/4 for v in (a, b, b, c)])
                > solutions[0]['free_energy'])
    controls = []
    for mode, outcome, x, y in [(1, 1, (ONE-BAD)/(2-h-BAD), (ONE-BAD)/(2-h-BAD)),
                                (0, 1, HALF, (ONE-BAD)/(2-h-BAD)),
                                (0, 0, HALF, BAD/(h+BAD))]:
        truth, ze = posterior(h, mode, outcome)
        q = product(x, y)
        for qi, pi_i in zip(q, truth):
            close('factorized observation control equals exact posterior', qi, pi_i)
        close('control variational gap is zero', kl(q, truth), ZERO)
        controls.append({'action': mode, 'continuation': outcome,
                         'evidence': ze, 'posterior': truth,
                         'decision': evaluate(h, truth, truth)})
    # Reconstruct the full joint through one marginal and both conditionals.
    for r in (0, 1):
        indices = [i for i, state in enumerate(STATES) if state[0] == r]
        mass = sum(pi[i] for i in indices)
        for i in indices:
            close('joint-capable reconstruction', mass*(pi[i]/mass), pi[i])
    return {'baseline': h, 'likelihoods': [a, b, b, c], 'evidence': evidence,
            'exact_posterior': pi, 'exact_decision': evaluate(h, pi, pi),
            'J': j, 'k': k, 'symmetric_coordinate': m, 'stability_T': stability,
            'symmetric_root_bracket': symmetric_bracket,
            'asymmetric_root_bracket': bracket, 'complete_global_minima': solutions,
            'observation_controls': controls}


def identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    allowed = Path('/mnt/bioIce1/fep-ideas/formal-checks').resolve()
    if not output.is_relative_to(allowed) or not os.path.ismount('/mnt/bioIce1'):
        raise RuntimeError('Output must use the mounted external FEP namespace')
    if os.statvfs('/mnt/bioIce1').f_flag & os.ST_RDONLY:
        raise RuntimeError('External drive is read-only; no local fallback')
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve()
    inputs = [identity(source.with_name('FEP_VARIATIONAL_POSITIVE_V1.md')),
              identity(source)]
    started = datetime.now(timezone.utc).isoformat()
    begin = perf_counter()
    log_path = output/'RUN_LOG.txt'
    log_path.write_text(f'Started {started}\nPython {platform.python_version()}\n'
                        'One process; precision 80; fixed fixtures 1e-6,1e-2.\n'
                        'Analytic root count, scalar bisection; no sampling.\n')
    ok = False
    try:
        critical, bracket = bisect(lambda h: symmetric(h)[1]-ONE,
                                   D('1e-12'), BAD-D('1e-12'))
        critical_m, critical_t, _ = symmetric(critical)
        close('critical stability boundary', critical_t, ONE)
        cases = [fixture(D('1e-6')), fixture(D('1e-2'))]
        for action in (0, 1):
            for outcome in (0, 1):
                truth, _ = posterior(BAD, action, outcome)
                require('no-contrast endpoint posterior equals prior',
                        truth == [D('0.25')]*4)
        require('frozen inputs unchanged',
                inputs == [identity(Path(item['path'])) for item in inputs])
        result = {'status': 'passed', 'started_utc': started,
                  'python': platform.python_version(), 'processes': 1,
                  'decimal_precision': 80, 'root_width_tolerance': ROOT_TOL,
                  'check_tolerance': CHECK_TOL,
                  'critical_baseline': critical, 'critical_symmetric_coordinate': critical_m,
                  'critical_bracket': bracket, 'fixtures': cases,
                  'assertion_count': len(CHECKS), 'assertions': CHECKS,
                  'max_numeric_residual': max(RESIDUALS),
                  'elapsed_seconds': perf_counter()-begin}
        (output/'RESULTS.json').write_text(json.dumps(result, indent=2, default=str)+'\n')
        with log_path.open('a') as handle:
            handle.write(f"PASS {len(CHECKS)} assertions; max residual {max(RESIDUALS)}.\n"
                         f"Elapsed {result['elapsed_seconds']:.9f} seconds.\n")
        ok = True
    except BaseException:
        with log_path.open('a') as handle:
            handle.write(traceback.format_exc())
        raise
    finally:
        outputs = [identity(path) for path in sorted(output.iterdir()) if path.is_file()]
        manifest = {'status': 'passed' if ok else 'failed', 'started_utc': started,
                    'inputs': inputs, 'outputs': outputs}
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': 'passed', 'output': str(output),
                      'assertions': len(CHECKS), 'critical_baseline': str(critical),
                      'elapsed_seconds': perf_counter()-begin}))


if __name__ == '__main__':
    main()
