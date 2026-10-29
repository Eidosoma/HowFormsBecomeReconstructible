#!/usr/bin/env python3
"""Frozen odds-band and unequal-prior certificates; no inference updates."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import time
import traceback

import check_fep_joint_risk as joint
from check_fep_joint_risk import (
    D, ZERO, ONE, TWO, TOL, identity, kl, expectation, evaluate,
    free_choice, mix, check, close, support, losses_at,
)

HERE = Path(__file__).resolve().parent
PRIOR = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-symmetric-risk-v1/attempt-01')
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-odds-robustness-v1')
FACTORS = (ONE, D('1.1'), D(2), D(10))
BUDGET = D('.1')
COMPLETED = []


def lift(bar, t):
    return [bar[0], t*bar[1], (ONE-t)*bar[1], bar[2]]


def cost_at(q, t):
    u = q[1]+q[2]
    if t == q[1]/u:
        return ZERO
    return q[1]*(q[1]/(u*t)).ln()+q[2]*(q[2]/(u*(ONE-t))).ln()


def band_support(q, loss, gap, factor):
    joint.WORK['band_support_calls'] += 1
    if (len(q) != 4 or len(loss) != 4 or any(x <= ZERO for x in q)
            or abs(sum(q)-ONE) > TOL or gap < ZERO
            or (factor is not None and factor < ONE)):
        raise ValueError('require positive normalized four-state Q, gap>=0 and factor>=1')
    bar = [q[0], q[1]+q[2], q[3]]
    z = q[1]/bar[1]
    lo, hi = (ZERO, ONE) if factor is None else (ONE/(ONE+factor), factor/(ONE+factor))
    nearest = min(hi, max(lo, z))
    minimum = cost_at(q, nearest)
    if gap < minimum:
        raise ValueError('empty odds-constrained posterior set')
    unconstrained = None
    if gap == minimum or min(loss) == max(loss):
        p = lift(bar, nearest)
        value = expectation(p, loss)
        cert = {'p': p, 'primal': value, 'dual': value, 'kl': kl(q, p),
                'branch': 'singleton' if gap == minimum else 'constant',
                'lambda': None, 'eta': None, 'nu': None, 'face_t': nearest,
                'face_cost': minimum, 'reduced_gap': gap-minimum}
    else:
        if lo == hi:
            face, branch = lo, 'equality'
        else:
            unconstrained = support(q, loss, gap)
            t_star = unconstrained['p'][1]/(unconstrained['p'][1]+unconstrained['p'][2])
            face = lo if t_star < lo else hi if t_star > hi else None
            branch = 'lower' if t_star < lo else 'upper' if t_star > hi else 'inactive'
        if face is None:
            p = unconstrained['p']
            nu = unconstrained['nu']
            lam = p[0]*(nu-loss[0])/q[0]
            eta, avec = ZERO, [ZERO]*4
            slice_cert, face_cost, radius = None, ZERO, gap
        else:
            face_cost = cost_at(q, face)
            radius = gap-face_cost
            check(radius > ZERO, 'positive selected-face radius')
            reduced_loss = [loss[0], face*loss[1]+(ONE-face)*loss[2], loss[3]]
            slice_cert = support(bar, reduced_loss, radius)
            p = lift(slice_cert['p'], face)
            avec = [ZERO, ONE-face, -face, ZERO]
            if slice_cert['nu'] is None:
                check(min(reduced_loss) == max(reduced_loss), 'constant reduced loss branch')
                nu, lam = reduced_loss[0], ZERO
            else:
                nu = slice_cert['nu']
                lam = slice_cert['p'][0]*(nu-reduced_loss[0])/bar[0]
            eta = loss[1]-loss[2]+lam/slice_cert['p'][1]*(q[1]/face-q[2]/(ONE-face))
            if branch == 'upper':
                check(eta >= ZERO, 'upper-face multiplier sign')
            if branch == 'lower':
                check(eta <= ZERO, 'lower-face multiplier sign')
            close(kl(q, p), face_cost+kl(bar, slice_cert['p']), 'face KL chain rule')
            close(expectation(p, loss), slice_cert['primal'], 'face loss reduction')
            close(expectation(p, avec), ZERO, 'odds complementary slackness')
        if lam == ZERO:
            dual = max(g-eta*a for g, a in zip(loss, avec))
        else:
            den = [nu-g+eta*a for g, a in zip(loss, avec)]
            check(lam > ZERO and min(den) > ZERO, 'positive dual multiplier and denominators')
            dual = nu+lam*(gap-ONE+lam.ln()-sum((x*y.ln() for x, y in zip(q, den)), ZERO))
            for x, y, divisor in zip(p, q, den):
                close(x*divisor, lam*y, 'full four-state stationarity')
            close(kl(q, p), gap, 'active full KL budget')
        cert = {'p': p, 'primal': expectation(p, loss), 'dual': dual, 'kl': kl(q, p),
                'branch': branch, 'lambda': lam, 'eta': eta, 'nu': nu,
                'face_t': face, 'face_cost': face_cost, 'reduced_gap': radius,
                'slice_certificate': slice_cert,
                'unconstrained_t': None if unconstrained is None else
                unconstrained['p'][1]/(unconstrained['p'][1]+unconstrained['p'][2])}
        if unconstrained is not None:
            check(dual <= unconstrained['dual']+TOL, 'band support below unrestricted support')
    p = cert['p']
    t = p[1]/(p[1]+p[2])
    close(sum(p), ONE, 'band witness normalization')
    check(min(p) > ZERO and lo-TOL <= t <= hi+TOL, 'band witness positive and inside odds')
    check(cert['kl'] <= gap+TOL, 'band witness inside KL budget')
    close(cert['primal'], cert['dual'], 'global primal dual agreement')
    check(cert['primal'] <= cert['dual']+TOL, 'global dual upper certificate')
    cert.update(witness_t=t, witness_odds=p[1]/p[2], minimum_gap=minimum)
    return cert


def policy_boundary(q, f0, f1, gap, factor):
    actions = [band_support(q, f, gap, factor) for f in (f0, f1)]
    check(actions[0]['dual'] < BUDGET < actions[1]['dual'], 'policy boundary endpoint bracket')
    if gap == ZERO:
        r = (BUDGET-actions[0]['dual'])/(actions[1]['dual']-actions[0]['dual'])
        cert = band_support(q, losses_at(r, f0, f1), gap, factor)
        return r, {'root': r, 'root_risk_residual': cert['dual']-BUDGET,
                   'root_certificate': cert, 'safe_certificate': cert,
                   'action_support': actions, 'outer_steps': 0}
    lo, hi, r = ZERO, ONE, ONE/TWO
    increments = [b-a for a, b in zip(f0, f1)]
    for step in range(1, 257):
        cert = band_support(q, losses_at(r, f0, f1), gap, factor)
        residual = cert['dual']-BUDGET
        if abs(residual) <= joint.OUTER_TARGET:
            break
        if residual > ZERO:
            hi = r
        else:
            lo = r
        derivative = expectation(cert['p'], increments)
        check(derivative > ZERO, 'positive band policy derivative')
        candidate = r-residual/derivative
        r = candidate if lo < candidate < hi else (lo+hi)/TWO
    else:
        raise AssertionError('band policy Newton guard')
    joint.WORK['band_outer_steps'] += step
    joint.WORK['max_band_outer_steps'] = max(joint.WORK['max_band_outer_steps'], step)
    safe_r = max(ZERO, r-joint.INWARD)
    safe = band_support(q, losses_at(safe_r, f0, f1), gap, factor)
    check(safe['dual'] <= BUDGET, 'inward band policy globally dual feasible')
    return safe_r, {'root': r, 'root_risk_residual': residual,
                    'root_certificate': cert, 'safe_certificate': safe,
                    'action_support': actions, 'outer_steps': step}


def qualify():
    joint.qualify()
    q = [D('.25')]*4
    loss = [ZERO, ONE, ZERO, ZERO]
    gap = D('.3')
    upper = band_support(q, loss, gap, D(2))
    lower = band_support(q, [ZERO, ZERO, ONE, ZERO], gap, D(2))
    check(upper['branch'] == 'upper' and lower['branch'] == 'lower', 'both active faces qualified')
    close(upper['dual'], lower['dual'], 'mirror synthetic support equality')
    loose = band_support(q, loss, gap, D(100))
    check(loose['branch'] == 'inactive', 'inactive band qualification')
    close(loose['dual'], support(q, loss, gap)['dual'], 'inactive band exact recovery')
    eq = band_support(q, loss, gap, ONE)
    close(eq['p'][1], eq['p'][2], 'equality control qualification')
    constant = band_support(q, [D(7)]*4, gap, D(2))
    close(constant['dual'], D(7), 'constant full loss qualification')
    face_constant = band_support(q, [ZERO, ONE, -ONE, ZERO], gap, ONE)
    close(face_constant['dual'], ZERO, 'constant face loss qualification')
    for factor in (ONE, D(2), None):
        close(band_support(q, loss, ZERO, factor)['dual'], D('.25'), 'zero gap band qualification')
    asymmetric = list(map(D, ('.1', '.6', '.2', '.1')))
    t = D(2)/D(3)
    cost = cost_at(asymmetric, t)
    singleton = band_support(asymmetric, loss, cost, D(2))
    check(singleton['branch'] == 'singleton', 'nonzero gap singleton qualification')
    pbar = list(map(D, ('.2', '.5', '.3')))
    p = lift(pbar, D('.6'))
    close(kl(asymmetric, p), cost_at(asymmetric, D('.6'))+
          kl([asymmetric[0], asymmetric[1]+asymmetric[2], asymmetric[3]], pbar),
          'asymmetric synthetic chain rule')
    candidate = list(map(D, ('.2', '.4', '.2', '.2')))
    check(kl(q, candidate) < gap and expectation(candidate, loss) <= upper['dual'],
          'global dual bounds independent feasible candidate')
    for badq, badgap, factor in ((q, -ONE, D(2)), (q, gap, D('.9')),
                                 (asymmetric, cost-D('.01'), D(2))):
        try:
            band_support(badq, loss, badgap, factor)
        except ValueError:
            check(True, 'invalid or empty odds set rejected')
        else:
            check(False, 'invalid or empty odds set rejected')


def run():
    joint.verify_manifest(PRIOR/'MANIFEST.json')
    joint.verify_manifest(Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-joint-risk-v1/attempt-01/MANIFEST.json'))
    qualify()
    qualified = sum(joint.COUNTS.values())
    saved = json.loads((PRIOR/'RESULTS.json').read_text())
    check(len(saved['rows']) == 22, 'all saved beliefs retained')
    rows = []
    for old in saved['rows']:
        h, q = D(old['baseline']), list(map(D, old['q']))
        a, b, c = h*(TWO-h), BUDGET+h-BUDGET*h, BUDGET*(TWO-BUDGET)
        f0, f1 = [h, h, BUDGET, BUDGET], [a, b, b, c]
        pi0 = [x/sum(f1) for x in f1]
        risks0 = [expectation(pi0, f) for f in (f0, f1)]
        free = free_choice([expectation(q, f) for f in (f0, f1)])
        check(free > ONE/TWO and mix(ONE/TWO, risks0) > BUDGET,
              'nominal model forces original objective constraint to bind')
        check([x['source'] for x in old['cases']] == ['exact', 'union', 'maximum'],
              'three original gap sources retained')
        cases, previous_source = [], {}
        for source_case in old['cases']:
            basegap = D(source_case['gap_upper'])
            symmetric_r = D(source_case['decision']['precision_probability'])
            joint_r = D(source_case['previous_joint_decision']['precision_probability'])
            check(kl(q, pi0) <= basegap+TOL, 'baseline KL certificate remains valid')
            curves = {}
            for arm, factors in (('fixed_gap', FACTORS+(None,)), ('prior_family', FACTORS)):
                curve, previous_r = [], None
                for factor in factors:
                    width = ZERO if factor is None else factor.ln()/TWO
                    padding = (width*abs(q[1]-q[2])+((width.exp()+(-width).exp())/TWO).ln()
                               if arm == 'prior_family' else ZERO)
                    gap = basegap+padding
                    r, boundary = policy_boundary(q, f0, f1, gap, factor)
                    decision = evaluate(r, risks0)
                    check(ZERO <= r <= symmetric_r+TOL and r < ONE/TWO < free,
                          'new certificate binds unchanged original objective')
                    check(decision['risk'] <= BUDGET+TOL, 'nominal policy risk feasible')
                    if previous_r is not None:
                        check(r <= previous_r+TOL, 'wider odds cannot increase allowance')
                    previous_r = r
                    key = (arm, factor)
                    if key in previous_source:
                        check(r <= previous_source[key]+TOL, 'looser evidence cannot increase allowance')
                    previous_source[key] = r
                    if arm == 'fixed_gap':
                        check(r >= joint_r-TOL, 'fixed-gap band improves unrestricted allowance')
                    else:
                        fixed = next(x for x in curves['fixed_gap'] if x['odds_factor'] == factor)
                        check(r <= fixed['decision']['precision_probability']+TOL,
                              'prior uncertainty cannot improve fixed-gap allowance')
                    if factor == ONE:
                        close(r, symmetric_r, 'zero-width saved policy recovery')
                        for x, y in zip(boundary['safe_certificate']['p'],
                                        map(D, source_case['boundary']['safe_certificate']['lifted_p'])):
                            close(x, y, 'zero-width saved witness recovery')
                    if factor is None:
                        close(r, joint_r, 'unrestricted saved policy recovery')
                    endpoints = []
                    if arm == 'prior_family':
                        for s in (-width, ZERO, width):
                            weights = [a, b*s.exp(), b*(-s).exp(), c]
                            pi = [x/sum(weights) for x in weights]
                            actual_kl = kl(q, pi)
                            tilt_log_moment = (sum(weights)/sum(f1)).ln()
                            close(actual_kl, kl(q, pi0)-s*(q[1]-q[2])+tilt_log_moment,
                                  'prior tilt KL identity')
                            check(tilt_log_moment <= ((width.exp()+(-width).exp())/TWO).ln()+TOL,
                                  'prior log-cosh envelope')
                            check(actual_kl <= gap+TOL, 'family endpoint covered by enlarged KL')
                            close(pi[1]/pi[2], (TWO*s).exp(), 'family posterior odds identity')
                            check(ONE/factor-TOL <= pi[1]/pi[2] <= factor+TOL,
                                  'family endpoint covered by odds interval')
                            risk = expectation(pi, losses_at(r, f0, f1))
                            check(risk <= boundary['safe_certificate']['dual']+TOL,
                                  'global dual covers family endpoint risk')
                            check(risk <= BUDGET+TOL, 'family endpoint policy feasibility')
                            endpoints.append({'prior_tilt': s, 'pi': pi, 'kl': actual_kl, 'risk': risk})
                    result = {'arm': arm, 'odds_factor': factor,
                              'prior_half_width': width if arm == 'prior_family' else None,
                              'gap_padding': padding, 'gap_upper': gap,
                              'decision': decision, 'boundary': boundary,
                              'fraction_of_equality_allowance': r/symmetric_r,
                              'difference_from_original_joint': r-joint_r,
                              'family_endpoint_checks': endpoints}
                    curve.append(result)
                    COMPLETED.append({'belief': old['belief'], 'source': source_case['source'], **result})
                curves[arm] = curve
            cases.append({'source': source_case['source'], 'baseline_gap': basegap,
                          'symmetric_allowance': symmetric_r, 'unrestricted_allowance': joint_r,
                          'curves': curves})
        rows.append({'belief': old['belief'], 'baseline': h, 'q': q, 'nominal_pi': pi0,
                     'original_decision': old['original_decision'], 'cases': cases})
    indexed = {x['belief']: x for x in rows}
    comparisons = []
    for h in ('0.000001', '0.01'):
        for treatment in ('exact', 'source_epsilon'):
            triplet = [indexed[f'h={h}/{treatment}/{s}'] for s in ('R_first', 'L_first', 'M')]
            for k in range(3):
                for arm in ('fixed_gap', 'prior_family'):
                    for j, center in enumerate(triplet[2]['cases'][k]['curves'][arm]):
                        rs = [x['cases'][k]['curves'][arm][j]['decision']['precision_probability']
                              for x in triplet]
                        if center['odds_factor'] == ONE:
                            close(rs[0], rs[1], 'exact-symmetry order equality')
                            close(rs[0], rs[2], 'exact-symmetry mixture equality')
                        comparisons.append({'baseline': h, 'treatment': treatment,
                                            'source': triplet[0]['cases'][k]['source'],
                                            'arm': arm, 'odds_factor': center['odds_factor'],
                                            'R_first': rs[0], 'L_first': rs[1], 'M': rs[2],
                                            'signed_order_gap': rs[0]-rs[1]})
    check(len(COMPLETED) == 594, 'all frozen policy evaluations retained')
    return rows, comparisons, qualified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--checker-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require verified external FEP destination')
    paths = [HERE/'FEP_ODDS_ROBUSTNESS_V1.md', Path(__file__).resolve(),
             PRIOR/'MANIFEST.json', PRIOR/'RESULTS.json', HERE/'FEP_SYMMETRIC_RISK_V1.md',
             HERE/'check_fep_symmetric_risk.py', HERE/'FEP_SYMMETRIC_RISK_V1_REPORT.md',
             HERE/'check_fep_joint_risk.py', HERE/'FEP_JOINT_RISK_V1.md',
             HERE/'check_fep_risk_certificate.py', HERE/'FEP_VARIATIONAL_PRIOR_SENSITIVITY_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    if inputs[0]['sha256'] != args.spec_sha256 or inputs[1]['sha256'] != args.checker_sha256:
        raise ValueError('prepared source freeze mismatch')
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    log = output/'RUN_LOG.txt'
    log.write_text(f'Started {started}\nOne process, Decimal precision 80; no inference updates.\n')
    manifest = {'status': 'started', 'started_utc': started, 'inputs': inputs}
    (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    try:
        rows, comparisons, qualified = run()
        for entry in inputs:
            check(identity(Path(entry['path'])) == entry, 'input unchanged after check')
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'tolerance': TOL,
                  'max_identity_residual': joint.MAX_RESIDUAL,
                  'assertion_count': sum(joint.COUNTS.values()), 'qualification_assertions': qualified,
                  'assertions_by_label': dict(joint.COUNTS), 'work': dict(joint.WORK),
                  'belief_count': len(rows), 'case_count': len(rows)*3, 'policy_count': len(COMPLETED),
                  'order_mixture_comparisons': comparisons, 'rows': rows,
                  'elapsed_seconds': time.perf_counter()-clock}
        (output/'RESULTS.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
        with log.open('a') as stream:
            stream.write(f"Passed {result['assertion_count']} assertions in {result['elapsed_seconds']:.9f} s.\n")
            stream.write(f'Max residual {joint.MAX_RESIDUAL}; work {dict(joint.WORK)}.\n')
        manifest.update(status='passed', outputs=[identity(output/n) for n in ('RESULTS.json', 'RUN_LOG.txt')])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ('rows', 'order_mixture_comparisons', 'assertions_by_label')}, default=str))
    except Exception:
        with log.open('a') as stream:
            stream.write(traceback.format_exc())
        partial = output/'PARTIAL_RESULTS.json'
        partial.write_text(json.dumps(COMPLETED, default=str, indent=2)+'\n')
        manifest.update(status='failed', outputs=[identity(log), identity(partial)])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
