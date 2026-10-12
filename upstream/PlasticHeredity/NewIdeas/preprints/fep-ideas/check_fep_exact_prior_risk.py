#!/usr/bin/env python3
"""Exact continuous-prior risk against the frozen KL-plus-odds policies."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import getcontext
import json
import os
from pathlib import Path
import platform
import time
import traceback

from check_fep_risk_certificate import (
    D, ZERO, ONE, TWO, TOL, identity, kl, expectation, evaluate, free_choice,
)

getcontext().prec = 80
HERE = Path(__file__).resolve().parent
PRIOR = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-odds-robustness-v1/attempt-01')
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-exact-prior-risk-v1')
FACTORS = (ONE, D('1.1'), D(2), D(10))
COUNTS, WORK = Counter(), Counter()
MAX_RESIDUAL = ZERO
COMPLETED = []
BUDGET = D('.1')


def check(condition, label):
    COUNTS[label] += 1
    if not condition:
        raise AssertionError(label)


def close(x, y, label):
    global MAX_RESIDUAL
    MAX_RESIDUAL = max(MAX_RESIDUAL, abs(x-y))
    check(abs(x-y) <= TOL, label)


def parameters(h):
    if not ZERO < h < BUDGET:
        raise ValueError('require 0<h<0.1')
    a, b, c = h*(TWO-h), BUDGET+h-BUDGET*h, BUDGET*(TWO-BUDGET)
    return a, b, c, [h, h, BUDGET, BUDGET], [a, b, b, c]


def posterior(a, b, c, x):
    if min(a, b, c, x) <= ZERO:
        raise ValueError('require positive likelihood weights and exponential tilt')
    weights = [a, b*x, b/x, c]
    return [w/sum(weights) for w in weights]


def roots(alpha, beta, gamma):
    if alpha == ZERO:
        return ([] if beta == ZERO else [-gamma/beta]), {
            'degree': 0 if beta == ZERO else 1,
            'flat': beta == gamma == ZERO, 'discriminant': None}
    disc = beta*beta-D(4)*alpha*gamma
    metadata = {'degree': 2, 'flat': False, 'discriminant': disc}
    if disc < ZERO:
        return [], metadata
    if disc == ZERO:
        return [-beta/(TWO*alpha)], metadata
    q = -(beta+(disc.sqrt() if beta >= ZERO else -disc.sqrt()))/TWO
    return [q/alpha, gamma/q], metadata


def losses(r, f0, f1):
    return [(ONE-r)*x+r*y for x, y in zip(f0, f1)]


def family_support(a, b, c, g, factor):
    if min(a, b, c) <= ZERO or len(g) != 4 or factor < ONE:
        raise ValueError('require positive weights, four losses and factor>=1')
    WORK['family_support_calls'] += 1
    upper = factor.sqrt()
    lower = ONE/upper
    k = a+c
    aa, bb, cc = b*g[1], a*g[0]+c*g[3], b*g[2]
    coeff = [aa*k-bb*b, TWO*b*(aa-cc), bb*b-cc*k]
    if min(g) == max(g):
        coeff = [ZERO]*3
    stationary, root_info = roots(*coeff)
    candidates = [('lower', lower), ('upper', upper)]
    for x in stationary:
        if lower-TOL <= x <= upper+TOL:
            candidates.append(('stationary', min(upper, max(lower, x))))
    evaluated = []
    for origin, x in candidates:
        p = posterior(a, b, c, x)
        risk = expectation(p, g)
        numerator, denominator = aa*x*x+bb*x+cc, b*x*x+k*x+b
        derivative_numerator = coeff[0]*x*x+coeff[1]*x+coeff[2]
        quotient_numerator = (TWO*aa*x+bb)*denominator-numerator*(TWO*b*x+k)
        close(risk, numerator/denominator, 'rational risk equals full joint expectation')
        close(derivative_numerator, quotient_numerator, 'quotient-rule quadratic identity')
        close(sum(p), ONE, 'family witness normalization')
        close(p[1]/p[2], x*x, 'family witness cause odds')
        close(c*p[0], a*p[3], 'family diagonal likelihood invariant')
        close(a*c*p[1]*p[2], b*b*p[0]*p[3], 'family product likelihood invariant')
        check(lower-TOL <= x <= upper+TOL, 'candidate inside continuous prior interval')
        if origin == 'stationary':
            close(derivative_numerator, ZERO, 'admitted stationary root residual')
        evaluated.append({'origin': origin, 'x': x, 'prior_tilt': x.ln(),
                          'p': p, 'risk': risk, 'derivative_numerator': derivative_numerator})
    maximum = max(x['risk'] for x in evaluated)
    winners = [i for i, x in enumerate(evaluated) if abs(x['risk']-maximum) <= TOL]
    WORK['admitted_candidates'] += len(evaluated)
    return {'maximum_risk': maximum, 'maximizer_indices': winners,
            'flat_over_interval': root_info['flat'], 'stationary_equation': coeff,
            'stationary_roots': stationary, 'root_metadata': root_info,
            'candidates': evaluated}


def cap_at(h, x):
    a, b, c, _, _ = parameters(h)
    e = a*(a-h)+c*(c-BUDGET)
    return (BUDGET-h)*x*(b*x+a)/(b*(b-h)*x*x+e*x+b*(b-BUDGET))


def reference(h, factor):
    a, b, c, f0, f1 = parameters(h)
    x = ONE/factor.sqrt()
    e = a*(a-h)+c*(c-BUDGET)
    bracket = e-a*(b-h)
    close(bracket, c*(c-BUDGET)+a*(a-b), 'cap derivative bracket identity')
    check(bracket > ZERO and b-BUDGET > ZERO, 'strict positive cap derivative coefficients')
    r = cap_at(h, x)
    p = posterior(a, b, c, x)
    risks = [expectation(p, f) for f in (f0, f1)]
    close(r, (BUDGET-risks[0])/(risks[1]-risks[0]), 'closed-form risk boundary identity')
    cert = family_support(a, b, c, losses(r, f0, f1), factor)
    close(cert['maximum_risk'], BUDGET, 'closed-form policy has exact family risk budget')
    close(cert['candidates'][0]['risk'], BUDGET, 'lower prior attains robust risk budget')
    check(0 in cert['maximizer_indices'], 'lower prior is a global risk maximizer')
    check(ZERO < r < ONE/TWO, 'interior exact-family policy below free optimum')
    if factor > ONE:
        check(r < cap_at(h, ONE) < cap_at(h, factor.sqrt()), 'strict cap ordering across prior interval')
    probe = (r+ONE)/TWO
    probe_risk = expectation(p, losses(probe, f0, f1))
    check(probe_risk > BUDGET, 'larger policy violates budget at same family witness')
    p0 = posterior(a, b, c, ONE)
    nominal_risks = [expectation(p0, f) for f in (f0, f1)]
    return {'baseline': h, 'odds_factor': factor, 'prior_half_width': factor.ln()/TWO,
            'precision_probability': r, 'nominal_exact_allowance': cap_at(h, ONE),
            'physical_uncertainty_loss': cap_at(h, ONE)-r,
            'nominal_decision': evaluate(r, nominal_risks), 'risk_certificate': cert,
            'larger_policy_check': {'precision_probability': probe, 'risk_at_lower_prior': probe_risk}}


def qualify():
    for coeff, expected in (((ONE, -D(3), TWO), [ONE, TWO]),
                            ((ZERO, TWO, -D(4)), [TWO]),
                            ((ONE, -TWO, ONE), [ONE]),
                            ((ONE, ZERO, ONE), []),
                            ((ZERO, ZERO, ONE), []),
                            ((ZERO, ZERO, ZERO), [])):
        values, metadata = roots(*coeff)
        check(sorted(values) == expected, 'polynomial root qualification')
        check(metadata['flat'] == all(x == ZERO for x in coeff), 'flat polynomial qualification')
    h = D('.01')
    a, b, c, f0, f1 = parameters(h)
    economy = family_support(a, b, c, f0, D(10))
    check(economy['maximizer_indices'] == [0], 'economy endpoint maximum qualification')
    precision = family_support(a, b, c, f1, D(10))
    check(len(precision['maximizer_indices']) == 1, 'unique precision interior maximum')
    winner = precision['candidates'][precision['maximizer_indices'][0]]
    check(winner['origin'] == 'stationary', 'endpoint-only maximum would fail')
    close(winner['x'], ONE, 'precision interior maximum at symmetric prior')
    constant = family_support(a, b, c, [D('.4')]*4, D(2))
    check(constant['flat_over_interval'], 'constant risk retains continuum of maximizers')
    close(constant['maximum_risk'], D('.4'), 'constant risk qualification')
    point = family_support(a, b, c, f0, ONE)
    close(point['maximum_risk'], expectation(posterior(a, b, c, ONE), f0), 'zero-width qualification')
    for bad in (ZERO, BUDGET):
        try:
            parameters(bad)
        except ValueError:
            check(True, 'invalid physical baseline rejected')
        else:
            check(False, 'invalid physical baseline rejected')
    try:
        family_support(a, b, c, f0, D('.9'))
    except ValueError:
        check(True, 'invalid prior factor rejected')
    else:
        check(False, 'invalid prior factor rejected')


def verify_manifest(path):
    data = json.loads(path.read_text())
    for kind in ('inputs', 'outputs'):
        for entry in data[kind]:
            check(identity(Path(entry['path'])) == entry, 'sealed '+kind+' identity')


def run():
    verify_manifest(PRIOR/'MANIFEST.json')
    verify_manifest(Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-symmetric-risk-v1/attempt-01/MANIFEST.json'))
    qualify()
    qualification_count = sum(COUNTS.values())
    saved = json.loads((PRIOR/'RESULTS.json').read_text())
    check(len(saved['rows']) == 22, 'all inherited beliefs retained')
    references = [reference(D(h), factor) for h in ('0.000001', '0.01') for factor in FACTORS]
    indexed = {(x['baseline'], x['odds_factor']): x for x in references}
    beliefs = []
    for row in saved['rows']:
        h, q = D(row['baseline']), list(map(D, row['q']))
        a, b, c, f0, f1 = parameters(h)
        p0 = posterior(a, b, c, ONE)
        q_risks = [expectation(q, f) for f in (f0, f1)]
        nominal_risks = [expectation(p0, f) for f in (f0, f1)]
        free = free_choice(q_risks)
        check(free > ONE/TWO, 'unchanged original objective binds at family limit')
        for x, y in zip(p0, map(D, row['nominal_pi'])):
            close(x, y, 'nominal posterior unchanged')
        check([x['source'] for x in row['cases']] == ['exact', 'union', 'maximum'],
              'three inherited evidence sources retained')
        beliefs.append({'belief': row['belief'], 'baseline': h, 'q': q, 'free_choice': free})
        for case in row['cases']:
            curve = case['curves']['prior_family']
            check([D(x['odds_factor']) for x in curve] == list(FACTORS),
                  'four inherited prior widths retained')
            original_zero = D(curve[0]['decision']['precision_probability'])
            for old in curve:
                factor = D(old['odds_factor'])
                ref = indexed[h, factor]
                r = ref['precision_probability']
                nominal_cap = ref['nominal_exact_allowance']
                certified = D(old['decision']['precision_probability'])
                gap = D(old['gap_upper'])
                close(D(old['prior_half_width']), ref['prior_half_width'], 'inherited prior width unchanged')
                exact_risk = family_support(a, b, c, losses(certified, f0, f1), factor)
                check(exact_risk['maximum_risk'] <= BUDGET+TOL, 'old certificate feasible across exact family')
                check(certified <= r+TOL <= nominal_cap+TOL, 'nominal exact-family certificate allowance hierarchy')
                close(exact_risk['maximum_risk'], exact_risk['candidates'][0]['risk'],
                      'old feasible policy worst risk attained at lower prior')
                for candidate in exact_risk['candidates']:
                    check(kl(q, candidate['p']) <= gap+TOL, 'every risk candidate inside old KL envelope')
                worst = [D(x) for x in old['boundary']['safe_certificate']['p']]
                old_upper = D(old['boundary']['safe_certificate']['dual'])
                close(expectation(worst, losses(certified, f0, f1)), old_upper,
                      'old worst-case physical risk unchanged')
                check(old_upper >= exact_risk['maximum_risk']-TOL,
                      'old generic certificate bounds exact-family risk')
                x = (worst[1]/worst[2]).sqrt()
                fitted = posterior(a, b, c, x)
                fit_error = max(abs(v-w) for v, w in zip(worst, fitted))
                check(ONE/factor.sqrt()-TOL <= x <= factor.sqrt()+TOL,
                      'old witness odds fit declared prior interval')
                physical = nominal_cap-r
                extra = r-certified
                total = nominal_cap-certified
                close(total, physical+extra, 'nominal action-loss decomposition')
                widening_extra = extra-(nominal_cap-original_zero)
                close(original_zero-certified, physical+widening_extra,
                      'broadening-only loss decomposition')
                nominal_decision = evaluate(r, nominal_risks)
                q_objective = evaluate(r, q_risks)
                for k, value in evaluate(certified, nominal_risks).items():
                    close(value, D(old['decision'][k]), 'saved nominal '+k)
                check(nominal_decision['task_value'] >= D(old['decision']['task_value'])-TOL,
                      'exact-family choice recovers nominal task value')
                check(nominal_decision['reference_score'] <= D(old['decision']['reference_score'])+TOL,
                      'exact-family choice improves nominal reference score')
                check(q_objective['reference_score'] <= evaluate(certified, q_risks)['reference_score']+TOL,
                      'exact-family choice improves unchanged original objective')
                if gap == ZERO:
                    close(r, certified, 'zero-gap nominal exact control recovered')
                    check(fit_error <= TOL, 'zero-gap witness belongs to exact family')
                COMPLETED.append({
                    'belief': row['belief'], 'baseline': h, 'source': case['source'],
                    'odds_factor': factor, 'old_gap_upper': gap, 'old_allowance': certified,
                    'exact_family_allowance': r, 'nominal_exact_allowance': nominal_cap,
                    'physical_uncertainty_loss': physical, 'extra_certificate_loss': extra,
                    'total_loss_from_nominal_exact': total,
                    'physical_share_of_total_loss': None if abs(total) <= TOL else physical/total,
                    'captured_robust_allowance': certified/r,
                    'certificate_broadening_loss': original_zero-certified,
                    'change_in_extra_loss_with_broadening': widening_extra,
                    'old_policy_exact_family_risk': exact_risk,
                    'old_policy_exact_family_budget_slack': BUDGET-exact_risk['maximum_risk'],
                    'old_risk_ceiling': old_upper,
                    'old_ceiling_minus_exact_risk': old_upper-exact_risk['maximum_risk'],
                    'old_witness_family_diagnostic': {
                        'p': worst, 'x_from_odds': x, 'reconstructed_family_p': fitted,
                        'max_component_difference': fit_error, 'inside_family': fit_error <= TOL,
                        'diagonal_cross_residual': c*worst[0]-a*worst[3],
                        'product_cross_residual': a*c*worst[1]*worst[2]-b*b*worst[0]*worst[3]},
                    'exact_family_nominal_decision': nominal_decision,
                    'exact_family_objective_under_q': q_objective})
    check(len(COMPLETED) == 264, 'all prior-family comparisons retained')
    return references, beliefs, qualification_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--checker-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require verified external FEP destination')
    paths = [HERE/'FEP_EXACT_PRIOR_RISK_V1.md', Path(__file__).resolve(),
             PRIOR/'MANIFEST.json', PRIOR/'RESULTS.json', HERE/'FEP_ODDS_ROBUSTNESS_V1.md',
             HERE/'check_fep_odds_robustness.py', HERE/'FEP_ODDS_ROBUSTNESS_V1_REPORT.md',
             HERE/'FEP_VARIATIONAL_PRIOR_SENSITIVITY_V1.md',
             HERE/'check_fep_risk_certificate.py', HERE/'FEP_SYMMETRIC_RISK_V1_REPORT.md',
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
        references, beliefs, qualified = run()
        for entry in inputs:
            check(identity(Path(entry['path'])) == entry, 'input unchanged after check')
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'tolerance': TOL,
                  'max_identity_residual': MAX_RESIDUAL, 'assertion_count': sum(COUNTS.values()),
                  'qualification_assertions': qualified, 'assertions_by_label': dict(COUNTS),
                  'work': dict(WORK), 'reference_count': len(references), 'belief_count': len(beliefs),
                  'comparison_count': len(COMPLETED), 'references': references, 'beliefs': beliefs,
                  'comparisons': COMPLETED, 'elapsed_seconds': time.perf_counter()-clock}
        (output/'RESULTS.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
        with log.open('a') as stream:
            stream.write(f"Passed {result['assertion_count']} assertions in {result['elapsed_seconds']:.9f} s.\n")
            stream.write(f'Max residual {MAX_RESIDUAL}; work {dict(WORK)}.\n')
        manifest.update(status='passed', outputs=[identity(output/n) for n in ('RESULTS.json', 'RUN_LOG.txt')])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ('references', 'beliefs', 'comparisons', 'assertions_by_label')}, default=str))
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
