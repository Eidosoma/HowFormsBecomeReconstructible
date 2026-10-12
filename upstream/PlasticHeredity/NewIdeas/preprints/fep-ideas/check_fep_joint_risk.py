#!/usr/bin/env python3
"""Sharp reverse-KL risk certificates for the frozen 22-belief assay."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import time
import traceback

from check_fep_risk_certificate import (
    D, ZERO, ONE, TWO, TOL, identity, kl, expectation, evaluate, free_choice, mix,
)

HERE = Path(__file__).resolve().parent
PRIOR = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-risk-certificate-v1/attempt-01')
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-joint-risk-v1')
INNER_TARGET, OUTER_TARGET, INWARD = D('1e-60'), D('1e-55'), D('1e-40')
COUNTS, WORK = Counter(), Counter()
MAX_RESIDUAL = ZERO


def check(condition, label):
    COUNTS[label] += 1
    if not condition:
        raise AssertionError(label)


def close(x, y, label):
    global MAX_RESIDUAL
    MAX_RESIDUAL = max(MAX_RESIDUAL, abs(x-y))
    check(abs(x-y) <= TOL, label)


def support(q, loss, gap):
    """Feasible witness and dual upper bound; scalar monotone Newton solve."""
    WORK['support_calls'] += 1
    if (len(q) != len(loss) or not q or any(x <= ZERO for x in q)
            or abs(sum(q)-ONE) > TOL or gap < ZERO):
        raise ValueError('require normalized full-support Q, matching losses and nonnegative gap')
    lower, upper = min(loss), max(loss)
    if gap == ZERO or lower == upper:
        value = expectation(q, loss)
        return {'p': list(q), 'kl': ZERO, 'primal': value, 'dual': value,
                'nu': None, 'inner_steps': 0, 'gap_residual': ZERO}
    width = upper-lower
    z = [(upper-x)/width for x in loss]

    def moments(t):
        den = [t+x for x in z]
        a = sum((x/y for x, y in zip(q, den)), ZERO)
        b = sum((x/y**2 for x, y in zip(q, den)), ZERO)
        logs = sum((x*y.ln() for x, y in zip(q, den)), ZERO)
        return logs+a.ln(), a-b/a, a, logs, den

    lo, hi = ZERO, ONE
    for _ in range(256):
        if moments(hi)[0] <= gap:
            break
        hi *= TWO
    else:
        raise AssertionError('inner bracketing guard')
    t = hi/TWO
    for step in range(1, 257):
        k, derivative, a, logs, den = moments(t)
        if abs(k-gap) <= INNER_TARGET:
            break
        if k > gap:
            lo = t
        else:
            hi = t
        candidate = t-(k-gap)/derivative
        t = candidate if lo < candidate < hi else (lo+hi)/TWO
    else:
        raise AssertionError('inner Newton guard')
    WORK['inner_steps'] += step
    WORK['max_inner_steps'] = max(WORK['max_inner_steps'], step)
    if k > gap:
        t += max(t*D('1e-48'), D('1e-70'))
        k, derivative, a, logs, den = moments(t)
    p = [x/(y*a) for x, y in zip(q, den)]
    actual_kl = kl(q, p)
    primal = expectation(p, loss)
    dual = upper+width*(t-(logs-gap).exp())
    nu = upper+width*t
    check(derivative < ZERO, 'strictly decreasing inner gap')
    check(all(x > ZERO for x in p), 'positive worst-case distribution')
    close(sum(p), ONE, 'worst-case normalization')
    close(actual_kl, k, 'reverse KL scalar identity')
    close(actual_kl, gap, 'active reverse KL constraint')
    check(actual_kl <= gap+TOL, 'worst-case witness feasible')
    close(primal, upper+width*(t-ONE/a), 'support value identity')
    check(dual >= primal-TOL, 'primal below dual certificate')
    close(primal, dual, 'primal dual agreement')
    for x, y, g in zip(p, q, loss):
        close(x*(nu-g)/y, width/a, 'stationarity')
    return {'p': p, 'kl': actual_kl, 'primal': primal, 'dual': dual,
            'nu': nu, 'inner_steps': step, 'gap_residual': actual_kl-gap}


def losses_at(r, f0, f1):
    return [(ONE-r)*a+r*b for a, b in zip(f0, f1)]


def joint_boundary(q, f0, f1, gap, old_r, separate_r):
    if gap == ZERO:
        bound = support(q, losses_at(old_r, f0, f1), gap)
        return old_r, {'root': old_r, 'root_risk_residual': ZERO,
                       'root_certificate': bound, 'safe_certificate': bound,
                       'outer_steps': 0}
    lo, hi = separate_r, old_r
    r = (lo+hi)/TWO
    increments = [b-a for a, b in zip(f0, f1)]
    for step in range(1, 257):
        cert = support(q, losses_at(r, f0, f1), gap)
        residual = cert['dual']-D('.1')
        if abs(residual) <= OUTER_TARGET:
            break
        if residual > ZERO:
            hi = r
        else:
            lo = r
        derivative = expectation(cert['p'], increments)
        check(derivative > ZERO, 'positive outer derivative')
        candidate = r-residual/derivative
        r = candidate if lo < candidate < hi else (lo+hi)/TWO
    else:
        raise AssertionError('outer Newton guard')
    WORK['outer_steps'] += step
    WORK['max_outer_steps'] = max(WORK['max_outer_steps'], step)
    safe_r = max(ZERO, r-INWARD)
    safe = support(q, losses_at(safe_r, f0, f1), gap)
    check(safe['dual'] <= D('.1'), 'inward joint policy dual feasibility')
    check(abs(residual) <= OUTER_TARGET, 'outer boundary residual')
    return safe_r, {'root': r, 'root_risk_residual': residual,
                    'root_certificate': cert, 'safe_certificate': safe,
                    'outer_steps': step}


def verify_manifest(path):
    manifest = json.loads(path.read_text())
    for kind in ('inputs', 'outputs'):
        for record in manifest[kind]:
            check(identity(Path(record['path'])) == record, 'sealed '+kind+' identity')


def qualify():
    q, g = [D('.5'), D('.5')], [ZERO, ONE]
    gap = (D(4)/D(3)).ln()/TWO
    result = support(q, g, gap)
    close(result['dual'], D('.75'), 'two-state closed-form risk')
    close(result['p'][0], D('.25'), 'two-state closed-form witness')
    check(abs(kl(result['p'], q)-gap) > D('.001'), 'KL orientation control')
    close(support(q, [D(2), D(4)], gap)['dual'], D('3.5'), 'affine loss scaling')
    close(support(q, g, ZERO)['dual'], D('.5'), 'zero gap qualification')
    close(support(q, [D(5), D(5)], gap)['dual'], D(5), 'constant loss qualification')
    for badq, badg, badk in ((q, g, -ONE), ([ZERO, ONE], g, gap), (q, [ONE], gap)):
        try:
            support(badq, badg, badk)
        except ValueError:
            check(True, 'invalid support or gap rejected')
        else:
            check(False, 'invalid support or gap rejected')


def run():
    verify_manifest(PRIOR/'MANIFEST.json')
    verify_manifest(Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-finite-updates-v1/attempt-01/MANIFEST.json'))
    qualify()
    qualification_count = sum(COUNTS.values())
    saved = json.loads((PRIOR/'RESULTS.json').read_text())
    check(len(saved['rows']) == 22, 'all inherited beliefs retained')
    output = []
    for row in saved['rows']:
        h, d = D(row['baseline']), D('.1')
        q = list(map(D, row['q']))
        a, b, c = h*(TWO-h), d+h-d*h, d*(TWO-d)
        f0, f1 = [h, h, d, d], [a, b, b, c]
        pi = [x/sum(f1) for x in f1]
        model_risks = [expectation(pi, f) for f in (f0, f1)]
        q_risks = [expectation(q, f) for f in (f0, f1)]
        free = free_choice(q_risks)
        old_r = D(row['existing_decision']['precision_probability'])
        close(mix(old_r, q_risks), d, 'original approximate budget binding')
        check(old_r < free, 'original objective decreasing through certified interval')
        for key, value in evaluate(old_r, model_risks).items():
            close(value, D(row['existing_decision'][key]), 'saved original '+key)
        previous_joint = previous_sep = None
        cases = []
        check(len(row['certificates']) == 3, 'all gap sources retained')
        for old in row['certificates']:
            gap = D(old['gap_upper'])
            check(kl(q, pi) <= gap+TOL, 'true posterior inside certified set')
            s0, s1 = support(q, f0, gap), support(q, f1, gap)
            binary = old['methods']['binary']
            binary_upper = list(map(D, binary['action_risk_upper']))
            binary_r = D(binary['decision']['precision_probability'])
            close(s0['dual'], binary_upper[0], 'economy binary bound is exact')
            check(s1['dual'] <= binary_upper[1]+TOL, 'precision binary relaxation')
            check(s0['dual'] < d < s1['dual'], 'unique interior robust risk boundary')
            separate_r = min(free, (d-s0['dual'])/(s1['dual']-s0['dual']))
            original = support(q, losses_at(old_r, f0, f1), gap)
            separate_at_original = mix(old_r, (s0['dual'], s1['dual']))
            binary_at_original = D(binary['existing_policy_risk_upper'])
            check(original['dual'] <= separate_at_original+TOL <= binary_at_original+TOL,
                  'joint separate binary hierarchy')
            joint_r, boundary = joint_boundary(q, f0, f1, gap, old_r, separate_r)
            sep_eval, joint_eval = evaluate(separate_r, model_risks), evaluate(joint_r, model_risks)
            if gap > ZERO:
                check(ZERO < binary_r < separate_r < joint_r < old_r,
                      'strict recovered action hierarchy')
                check(original['primal'] > d, 'original policy worst-case violation witness')
                check(original['dual'] < separate_at_original < binary_at_original,
                      'strict two sources of certificate looseness')
                check(any(abs(x-y) > TOL for x, y in zip(s0['p'], s1['p'])),
                      'incompatible action worst cases')
            else:
                for value in (binary_r, separate_r, joint_r):
                    close(value, old_r, 'zero gap recovers original policy')
            for decision in (sep_eval, joint_eval):
                check(decision['risk'] <= d+TOL, 'exact-model certified feasibility')
            check(joint_eval['task_value'] >= sep_eval['task_value']-TOL >=
                  D(binary['decision']['task_value'])-TOL, 'recovered model task value')
            check(joint_eval['reference_score'] <= sep_eval['reference_score']+TOL <=
                  D(binary['decision']['reference_score'])+TOL, 'recovered model reference score')
            if previous_joint is not None:
                check(joint_r <= previous_joint+TOL and separate_r <= previous_sep+TOL,
                      'looser evidence reduces certified action')
            previous_joint, previous_sep = joint_r, separate_r
            cases.append({'source': old['source'], 'gap_upper': gap,
                          'previous_binary_decision': binary['decision'],
                          'action_support': [s0, s1], 'original_policy_support': original,
                          'original_policy_binary_upper': binary_at_original,
                          'original_policy_separate_upper': separate_at_original,
                          'binary_relaxation_loss': binary_at_original-separate_at_original,
                          'incompatible_extrema_loss': separate_at_original-original['dual'],
                          'separate_decision': sep_eval, 'joint_decision': joint_eval,
                          'joint_boundary': boundary,
                          'precision_recovered_from_binary': joint_r-binary_r,
                          'precision_still_excluded': old_r-joint_r})
        output.append({'belief': row['belief'], 'baseline': h, 'q': q, 'pi': pi,
                       'original_decision': row['existing_decision'], 'cases': cases})
    return output, qualification_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--checker-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require verified external FEP destination')
    paths = [HERE/'FEP_JOINT_RISK_V1.md', Path(__file__).resolve(),
             PRIOR/'MANIFEST.json', PRIOR/'RESULTS.json', HERE/'FEP_RISK_CERTIFICATE_V1.md',
             HERE/'check_fep_risk_certificate.py', HERE/'FEP_RISK_CERTIFICATE_V1_REPORT.md',
             HERE/'FEP_ORDER_SYMMETRY_V1.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
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
        rows, qualification_count = run()
        for record in inputs:
            check(identity(Path(record['path'])) == record, 'input unchanged after check')
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'tolerance': TOL,
                  'max_identity_residual': MAX_RESIDUAL, 'assertion_count': sum(COUNTS.values()),
                  'qualification_assertions': qualification_count, 'assertions_by_label': dict(COUNTS),
                  'work': dict(WORK), 'belief_count': len(rows), 'case_count': len(rows)*3,
                  'rows': rows, 'elapsed_seconds': time.perf_counter()-clock}
        (output/'RESULTS.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
        with log.open('a') as stream:
            stream.write(f"Passed {result['assertion_count']} assertions in {result['elapsed_seconds']:.9f} s.\n")
            stream.write(f'Max residual {MAX_RESIDUAL}; work {dict(WORK)}.\n')
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
