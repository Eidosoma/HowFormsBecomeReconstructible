#!/usr/bin/env python3
"""Known posterior symmetry in the frozen 22-belief reverse-KL audit."""
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
PRIOR = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-joint-risk-v1/attempt-01')
DEST = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-symmetric-risk-v1')
BUDGET = D('.1')


def lift(p):
    return [p[0], p[1]/TWO, p[1]/TWO, p[2]]


def reduce_q(q):
    if len(q) != 4 or any(x <= ZERO for x in q) or abs(sum(q)-ONE) > TOL:
        raise ValueError('require normalized four-state full-support Q')
    bar = [q[0], q[1]+q[2], q[3]]
    sym = lift(bar)
    cost = sum((q[i]*(q[i]/sym[i]).ln() for i in (1, 2)), ZERO)
    check(cost >= ZERO, 'nonnegative symmetry cost')
    close(kl(q, sym), cost, 'symmetry cost direct KL')
    return bar, sym, cost


def reduced_gap(gap, cost):
    if gap < cost:
        raise ValueError('empty symmetry-constrained posterior set')
    return gap-cost


def annotate(cert, q, bar, cost, raw_gap, full_loss, reduced_loss):
    p = lift(cert['p'])
    full_kl = kl(q, p)
    close(sum(p), ONE, 'lifted normalization')
    close(p[1], p[2], 'lifted symmetry')
    close(full_kl, cost+kl(bar, cert['p']), 'full reduced KL decomposition')
    close(expectation(p, full_loss), expectation(cert['p'], reduced_loss),
          'full reduced physical risk')
    close(expectation(p, full_loss), cert['primal'], 'lifted witness attains support')
    check(full_kl <= raw_gap+TOL, 'lifted witness inside original gap')
    close(full_kl, raw_gap, 'lifted active raw constraint')
    return dict(cert, lifted_p=p, full_kl=full_kl)


def qualify():
    joint.qualify()
    q = list(map(D, ('.1', '.2', '.4', '.3')))
    bar, sym, cost = reduce_q(q)
    pbar = list(map(D, ('.2', '.5', '.3')))
    close(kl(q, lift(pbar)), cost+kl(bar, pbar), 'synthetic KL chain rule')
    full_loss = list(map(D, ('1', '2', '4', '6')))
    reduced_loss = list(map(D, ('1', '3', '6')))
    close(expectation(lift(pbar), full_loss), expectation(pbar, reduced_loss),
          'synthetic loss reduction')
    singleton = support(bar, reduced_loss, reduced_gap(cost, cost))
    for x, y in zip(lift(singleton['p']), sym):
        close(x, y, 'symmetry singleton qualification')
    annotate(singleton, q, bar, cost, cost, full_loss, reduced_loss)
    try:
        reduced_gap(cost-D('.01'), cost)
    except ValueError:
        check(True, 'empty symmetric set rejected')
    else:
        check(False, 'empty symmetric set rejected')


def run():
    joint.verify_manifest(PRIOR/'MANIFEST.json')
    joint.verify_manifest(joint.PRIOR/'MANIFEST.json')
    qualify()
    qualification_count = sum(joint.COUNTS.values())
    saved = json.loads((PRIOR/'RESULTS.json').read_text())
    check(len(saved['rows']) == 22, 'all saved beliefs retained')
    rows = []
    for old in saved['rows']:
        h, d = D(old['baseline']), BUDGET
        q = list(map(D, old['q']))
        bar, sym, cost = reduce_q(q)
        a, b, c = h*(TWO-h), d+h-d*h, d*(TWO-d)
        f0, f1 = [h, h, d, d], [a, b, b, c]
        b0, b1 = [h, (h+d)/TWO, d], [a, b, c]
        z = sum(f1)/D(4)
        pi = [x/(D(4)*z) for x in f1]
        for x, y in zip(pi, map(D, old['pi'])):
            close(x, y, 'saved exact posterior unchanged')
        close(pi[1], pi[2], 'model posterior symmetry')
        model_risks = [expectation(pi, f) for f in (f0, f1)]
        q_risks = [expectation(q, f) for f in (f0, f1)]
        free = free_choice(q_risks)
        exact_cap = (d-model_risks[0])/(model_risks[1]-model_risks[0])
        check(free > ONE/TWO, 'original free optimum above one half')
        check(mix(ONE/TWO, model_risks) > d, 'model risk at one half exceeds budget')
        check(all(y > x for x, y in zip(b0, b1)), 'strict reduced risk increments')
        original_r = D(old['original_decision']['precision_probability'])
        for k, v in evaluate(original_r, model_risks).items():
            close(v, D(old['original_decision'][k]), 'saved original decision '+k)
        full_f = sum((x*(x/(y/D(4))).ln() for x, y in zip(q, f1)), ZERO)
        sym_f = sum((x*(x/(y/D(4))).ln() for x, y in zip(sym, f1)), ZERO)
        close(full_f-sym_f, cost, 'free energy symmetry decomposition')
        check([x['source'] for x in old['cases']] == ['exact', 'union', 'maximum'],
              'all three inherited gap sources unchanged')
        previous_r = None
        cases = []
        for previous in old['cases']:
            source, gap = previous['source'], D(previous['gap_upper'])
            upper_z = {'exact': z, 'union': h+d, 'maximum': c}[source]
            radius = reduced_gap(gap, cost)
            close(gap, full_f+upper_z.ln(), 'unchanged evidence gap identity')
            close(radius, sym_f+upper_z.ln(), 'reduced evidence gap identity')
            check(kl(q, pi) <= gap+TOL, 'model posterior in original set')
            check(kl(bar, [pi[0], pi[1]+pi[2], pi[3]]) <= radius+TOL,
                  'model posterior in reduced set')
            actions = [annotate(support(bar, fb, radius), q, bar, cost, gap, f, fb)
                       for f, fb in ((f0, b0), (f1, b1))]
            check(actions[0]['dual'] < d < actions[1]['dual'],
                  'valid outer endpoint bracket')
            separate = (d-actions[0]['dual'])/(actions[1]['dual']-actions[0]['dual'])
            check(ZERO < separate < ONE, 'valid separate lower bracket')
            if radius == ZERO:
                risk0, risk1 = [expectation(bar, f) for f in (b0, b1)]
                r = (d-risk0)/(risk1-risk0)
                cert = support(bar, losses_at(r, b0, b1), radius)
                boundary = {'root': r, 'root_risk_residual': cert['dual']-d,
                            'root_certificate': cert, 'safe_certificate': cert,
                            'outer_steps': 0}
            else:
                r, boundary = joint.joint_boundary(bar, b0, b1, radius, ONE, separate)
            for name, use_r in (('root_certificate', boundary['root']),
                                ('safe_certificate', r)):
                boundary[name] = annotate(boundary[name], q, bar, cost, gap,
                                          losses_at(use_r, f0, f1), losses_at(use_r, b0, b1))
            original_cert = annotate(
                support(bar, losses_at(original_r, b0, b1), radius), q, bar, cost, gap,
                losses_at(original_r, f0, f1), losses_at(original_r, b0, b1))
            old_r = D(previous['joint_decision']['precision_probability'])
            check(original_cert['dual'] <= D(previous['original_policy_support']['dual'])+TOL,
                  'symmetric original-policy ceiling cannot increase')
            check(r >= old_r-TOL, 'symmetry cannot reduce certified allowance')
            check(r <= exact_cap+TOL < ONE/TWO < free,
                  'risk boundary binds unchanged original objective')
            check(boundary['safe_certificate']['dual'] <= d+TOL, 'certified risk feasibility')
            decision = evaluate(r, model_risks)
            check(decision['risk'] <= d+TOL, 'exact model feasibility')
            check(decision['task_value'] >= D(previous['joint_decision']['task_value'])-TOL,
                  'recovered model task value')
            check(decision['reference_score'] <= D(previous['joint_decision']['reference_score'])+TOL,
                  'recovered model reference score')
            if radius == ZERO:
                close(r, exact_cap, 'zero gap recovers exact policy')
            if previous_r is not None:
                check(r <= previous_r+TOL, 'looser evidence reduces allowance')
            previous_r = r
            cases.append({'source': source, 'evidence_upper': upper_z, 'gap_upper': gap,
                          'reduced_gap': radius, 'action_support': actions,
                          'separate_reduced_allowance': separate,
                          'original_policy_support': original_cert,
                          'original_policy_certified': original_cert['dual'] <= d+TOL,
                          'previous_joint_decision': previous['joint_decision'],
                          'decision': decision, 'boundary': boundary,
                          'precision_recovered': r-old_r,
                          'precision_minus_original': r-original_r,
                          'precision_below_exact_cap': exact_cap-r})
        rows.append({'belief': old['belief'], 'baseline': h, 'q': q, 'symmetric_q': sym,
                     'aggregate_q': bar, 'symmetry_cost': cost, 'free_energy': full_f,
                     'symmetric_free_energy': sym_f, 'pi': pi, 'free_choice': free,
                     'exact_model_cap': exact_cap, 'original_decision': old['original_decision'],
                     'cases': cases})
    indexed = {row['belief']: row for row in rows}
    triplets = []
    for h in ('0.000001', '0.01'):
        for treatment in ('exact', 'source_epsilon'):
            stem = f'h={h}/{treatment}/'
            right, left, mixture = [indexed[stem+s] for s in ('R_first', 'L_first', 'M')]
            for other in (right, left):
                for x, y in zip(other['aggregate_q'], mixture['aggregate_q']):
                    close(x, y, 'order mixture aggregate equality')
            for k in range(3):
                target = mixture['cases'][k]
                for other in (right, left):
                    candidate = other['cases'][k]
                    close(candidate['reduced_gap'], target['reduced_gap'], 'order mixture radius equality')
                    close(candidate['decision']['precision_probability'],
                          target['decision']['precision_probability'], 'order mixture policy equality')
                    for x, y in zip(candidate['boundary']['safe_certificate']['lifted_p'],
                                    target['boundary']['safe_certificate']['lifted_p']):
                        close(x, y, 'order mixture witness equality')
                triplets.append({'baseline': h, 'treatment': treatment, 'source': target['source'],
                                 'precision_probability': target['decision']['precision_probability']})
    return rows, triplets, qualification_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--checker-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != DEST or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('require verified external FEP destination')
    paths = [HERE/'FEP_SYMMETRIC_RISK_V1.md', Path(__file__).resolve(),
             PRIOR/'MANIFEST.json', PRIOR/'RESULTS.json', HERE/'FEP_JOINT_RISK_V1.md',
             HERE/'check_fep_joint_risk.py', HERE/'FEP_JOINT_RISK_V1_REPORT.md',
             HERE/'check_fep_risk_certificate.py', HERE/'FEP_ORDER_SYMMETRY_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
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
        rows, triplets, qualification_count = run()
        for record in inputs:
            check(identity(Path(record['path'])) == record, 'input unchanged after check')
        result = {'status': 'passed', 'started_utc': started, 'python': platform.python_version(),
                  'processes': 1, 'decimal_precision': 80, 'tolerance': TOL,
                  'max_identity_residual': joint.MAX_RESIDUAL,
                  'assertion_count': sum(joint.COUNTS.values()),
                  'qualification_assertions': qualification_count,
                  'assertions_by_label': dict(joint.COUNTS), 'work': dict(joint.WORK),
                  'belief_count': len(rows), 'case_count': len(rows)*3,
                  'order_mixture_comparisons': triplets, 'rows': rows,
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
        manifest.update(status='failed', outputs=[identity(log)])
        (output/'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
