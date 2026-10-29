#!/usr/bin/env python3
"""Bounded substitutions for FEP_RISK_CERTIFICATE_V1.md; no inference reruns."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import traceback

getcontext().prec = 80
ZERO, ONE, TWO = D(0), D(1), D(2)
TOL, ROOT_WIDTH = D('1e-35'), D('1e-45')
HERE = Path(__file__).resolve().parent
PRIOR = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-finite-updates-v1/attempt-01')
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-risk-certificate-v1')
COUNTS = Counter()
MAX_RESIDUAL = ZERO
MAX_ROOT_WIDTH = ZERO


def check(condition, label):
    COUNTS[label] += 1
    if not condition:
        raise AssertionError(label)


def close(x, y, label):
    global MAX_RESIDUAL
    residual = abs(x-y)
    MAX_RESIDUAL = max(MAX_RESIDUAL, residual)
    check(residual <= TOL, label)


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def kl(q, p):
    return sum((x*(x/y).ln() for x, y in zip(q, p) if x), ZERO)


def binary_kl(m, n):
    if n == ZERO:
        return ZERO if m == ZERO else D('Infinity')
    if n == ONE:
        return ZERO if m == ONE else D('Infinity')
    return kl((m, ONE-m), (n, ONE-n))


def binary_upper(m, gap):
    global MAX_ROOT_WIDTH
    if gap < ZERO:
        raise ValueError('negative gap certificate')
    if gap == ZERO or m == ONE:
        return m
    if m == ZERO:
        return ONE-(-gap).exp()
    lo, hi = m, ONE
    while hi-lo > ROOT_WIDTH:
        mid = (lo+hi)/TWO
        if binary_kl(m, mid) <= gap:
            lo = mid
        else:
            hi = mid
    MAX_ROOT_WIDTH = max(MAX_ROOT_WIDTH, hi-lo)
    check(binary_kl(m, lo) <= gap+TOL, 'binary lower root bracket')
    check(binary_kl(m, hi) >= gap-TOL, 'binary upper root bracket')
    check(hi-lo <= ROOT_WIDTH, 'binary root width')
    return hi


def expectation(q, values):
    return sum((x*y for x, y in zip(q, values)), ZERO)


def product(x, y):
    return [(ONE-x)*(ONE-y), x*(ONE-y), (ONE-x)*y, x*y]


def free_choice(risks):
    return ONE/(ONE+(-D(4)*(D('.15')-D('.5')*(risks[1]-risks[0]))).exp())


def constrained_choice(free, upper):
    u0, u1 = upper
    check(u0 <= D('.1')+TOL and u1 > u0, 'economy feasible and increasing risk')
    if u1 <= D('.1'):
        return free
    return min(free, max(ZERO, (D('.1')-u0)/(u1-u0)))


def mix(r, values):
    return (ONE-r)*values[0]+r*values[1]


def evaluate(r, risks):
    risk = mix(r, risks)
    utility = D('1.25')+D('.15')*r-D('.5')*risk
    reference = kl((r, ONE-r), (D('.5'), D('.5')))-D(4)*utility
    return {'precision_probability': r, 'risk': risk,
            'task_value': utility, 'reference_score': reference}


def run():
    saved = json.loads((PRIOR/'RESULTS.json').read_text())
    for kind in ('inputs', 'outputs'):
        for record in json.loads((PRIOR/'MANIFEST.json').read_text())[kind]:
            check(identity(Path(record['path'])) == record, 'sealed '+kind+' identity')
    close(binary_upper(D('.3'), ZERO), D('.3'), 'zero gap qualification')
    close(binary_upper(ZERO, TWO), ONE-(-TWO).exp(), 'zero mean qualification')
    close(binary_upper(ONE, TWO), ONE, 'unit mean qualification')
    try:
        binary_upper(D('.3'), -ONE)
    except ValueError:
        check(True, 'reject negative gap')
    else:
        check(False, 'reject negative gap')
    close(binary_upper(D('.5'), (D(4)/D(3)).ln()/TWO), D('.75'),
          'known binary root qualification')

    beliefs = []
    for case in saved['cases']:
        beliefs.append((case['case_id'], D(case['baseline']),
                        list(map(D, case['final']['q'])), case['final']))
    for h in ('0.000001', '0.01'):
        for treatment in ('exact', 'source_epsilon'):
            pair = [case for case in saved['cases']
                    if case['baseline'] == h and case['treatment'] == treatment
                    and case['schedule'] in ('R_first', 'L_first')]
            check(len(pair) == 2, 'complete saved ordering pair')
            q0, q1 = [list(map(D, case['final']['q'])) for case in pair]
            for x, y in zip(q0, (q1[0], q1[2], q1[1], q1[3])):
                close(x, y, 'saved mirror relation')
            mixture = [(x+y)/TWO for x, y in zip(q0, q1)]
            m = mixture[1]+mixture[3]
            for label, q in (('M', mixture), ('P', product(m, m))):
                beliefs.append((f'h={h}/{treatment}/{label}', D(h), q, None))
    for ref in saved['references']:
        beliefs.append((f"h={ref['baseline']}/exact_joint", D(ref['baseline']),
                        list(map(D, ref['exact_joint'])), None))
    check(len(beliefs) == 22, 'predeclared belief count')

    rows = []
    for label, h, q, original in beliefs:
        d = D('.1')
        a, b, c = h*(TWO-h), d+h-d*h, d*(TWO-d)
        likelihood = [a, b, b, c]
        evidence = sum(likelihood)/D(4)
        pi = [x/(D(4)*evidence) for x in likelihood]
        risks = ([h, h, d, d], likelihood)
        lower, upper = [h, a], [d, c]
        ranges = [v-u for u, v in zip(lower, upper)]
        q_risks = [expectation(q, v) for v in risks]
        p_risks = [expectation(pi, v) for v in risks]
        f = sum((x*(D(4)*x/y).ln() for x, y in zip(q, likelihood)), ZERO)
        gap = kl(q, pi)
        close(sum(q), ONE, 'belief normalization')
        close(f+evidence.ln(), gap, 'VFE gap identity')
        check(gap >= -TOL, 'nonnegative posterior KL')
        if label.endswith('exact_joint'):
            close(gap, ZERO, 'exact posterior control')
            gap = ZERO
        free = free_choice(q_risks)
        old_r = constrained_choice(free, q_risks)
        old_eval = evaluate(old_r, p_risks)
        if original:
            close(f, D(original['true_vfe']), 'saved physical F')
            close(gap, D(original['posterior_kl']), 'saved posterior KL')
            close(old_r, D(original['policy']['optimal_precision_probability']),
                  'unchanged saved decision')
        check(evidence <= h+d < c < ONE, 'evidence bound ordering')
        actual_error = mix(old_r, p_risks)-mix(old_r, q_risks)
        close(evaluate(old_r, q_risks)['task_value']-old_eval['task_value'],
              D('.5')*actual_error, 'fixed policy utility error')
        close(evaluate(old_r, q_risks)['reference_score']-old_eval['reference_score'],
              -TWO*actual_error, 'fixed policy reference error')
        normalized_q = [(x-l)/w for x, l, w in zip(q_risks, lower, ranges)]
        normalized_p = [(x-l)/w for x, l, w in zip(p_risks, lower, ranges)]
        for m, n in zip(normalized_q, normalized_p):
            check(binary_kl(m, n) <= gap+TOL, 'binary data processing')
        certificates = []
        previous = None
        for source, evidence_upper in (('exact', evidence), ('union', h+d), ('maximum', c)):
            k = gap if source == 'exact' else f+evidence_upper.ln()
            check(k >= gap-TOL, 'valid upper gap')
            root = (k/TWO).sqrt()
            pin = [min(u, x+w*root) for u, x, w in zip(upper, q_risks, ranges)]
            binary = [l+w*binary_upper(m, k) for l, w, m in zip(lower, ranges, normalized_q)]
            for actual, approx, lo, up, ub, bp, w in zip(
                    p_risks, q_risks, lower, upper, binary, pin, ranges):
                check(lo-TOL <= actual <= ub+TOL <= bp+TOL <= up+TOL,
                      'binary and Pinsker risk coverage')
                check(abs(actual-approx) <= w*min(ONE, root)+TOL,
                      'two sided range error')
            methods = {}
            for method, bounds in (('pinsker', pin), ('binary', binary)):
                r = constrained_choice(free, bounds)
                evaluated = evaluate(r, p_risks)
                check(ZERO <= r <= old_r+TOL, 'certificate restricts original choice')
                check(evaluated['risk'] <= mix(r, bounds)+TOL <= d+TOL,
                      'certified policy feasibility')
                if source == 'exact' and label.endswith('exact_joint'):
                    close(r, old_r, 'zero gap recovers original policy')
                if previous:
                    check(r <= previous[method]['decision']['precision_probability']+TOL,
                          'looser evidence reduces certified choice')
                methods[method] = {
                    'action_risk_upper': bounds,
                    'existing_policy_risk_upper': mix(old_r, bounds),
                    'existing_policy_certified': mix(old_r, bounds) <= d+TOL,
                    'decision': evaluated,
                    'decision_risk_upper': mix(r, bounds)}
            check(methods['binary']['decision']['precision_probability']+TOL >=
                  methods['pinsker']['decision']['precision_probability'],
                  'binary admits at least Pinsker choice')
            check(methods['binary']['decision']['precision_probability'] > ZERO,
                  'finite binary certificate permits precision')
            previous = methods
            certificates.append({'source': source, 'evidence_upper': evidence_upper,
                                 'gap_upper': k,
                                 'existing_absolute_error_bound': mix(old_r, ranges)*min(ONE, root),
                                 'methods': methods})
        rows.append({'belief': label, 'baseline': h, 'q': q, 'evidence': evidence,
                     'F': f, 'posterior_kl': gap, 'risk_under_q': q_risks,
                     'risk_under_pi': p_risks, 'physical_ranges': ranges,
                     'existing_decision': old_eval,
                     'existing_predicted_risk': mix(old_r, q_risks),
                     'existing_signed_risk_error': actual_error,
                     'certificates': certificates})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--checker-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require verified external FEP destination')
    paths = [HERE/'FEP_RISK_CERTIFICATE_V1.md', Path(__file__).resolve(),
             PRIOR/'MANIFEST.json', PRIOR/'RESULTS.json', HERE/'FEP_ORDER_SYMMETRY_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    if inputs[0]['sha256'] != args.spec_sha256 or inputs[1]['sha256'] != args.checker_sha256:
        raise ValueError('prepared source freeze mismatch')
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    log = output/'RUN_LOG.txt'
    log.write_text(f'Started {started}\nOne process; Decimal precision 80; no inference updates.\n')
    manifest = {'status': 'started', 'started_utc': started, 'inputs': inputs}
    (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    try:
        rows = run()
        for record in inputs:
            check(identity(Path(record['path'])) == record, 'input unchanged after arithmetic')
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'tolerance': TOL,
                  'max_identity_residual': MAX_RESIDUAL, 'max_root_width': MAX_ROOT_WIDTH,
                  'assertion_count': sum(COUNTS.values()), 'assertions_by_label': dict(COUNTS),
                  'belief_count': len(rows), 'certificate_count': len(rows)*3,
                  'rows': rows, 'elapsed_seconds': time.perf_counter()-start}
        (output/'RESULTS.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
        with log.open('a') as stream:
            stream.write(f"Passed {result['assertion_count']} checks in {result['elapsed_seconds']:.9f} s.\n")
            stream.write(f'Max identity residual {MAX_RESIDUAL}; root width {MAX_ROOT_WIDTH}.\n')
        manifest.update(status='passed', outputs=[identity(output/n) for n in ('RESULTS.json', 'RUN_LOG.txt')])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'assertions_by_label')}, default=str))
    except Exception:
        with log.open('a') as stream:
            stream.write(traceback.format_exc())
        manifest.update(status='failed', outputs=[identity(log)])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
