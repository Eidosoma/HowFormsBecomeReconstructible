#!/usr/bin/env python3
"""Bounded, specified diagnostics of the frozen anytime learner; no new policy."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
from time import perf_counter
import traceback

import numpy as np
import check_fep_anytime_horizon as H
import qualify_fep_anytime_change as Q

A, BOUNDS = H.A, H.BOUNDARIES
SOURCE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-reversal-feedback-audit-v1')
PREVIOUS = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-horizon-v1')
SPEC = SOURCE/'FEP_REVERSAL_FEEDBACK_AUDIT_V1.md'
PROFILES = {'strong': (58, 3, 3, 0), 'mixed': (44, 10, 8, 2),
            'neutral': (16, 16, 16, 16)}
SCHEDULES = ('withhold', 'consistent', 'contradictory', 'on_policy')
PRIOR = [F(1, 2)]+[F(1, 600)]*300
CHECKS = {}
FROZEN = {
    SOURCE/'check_fep_anytime_horizon.py': 'b2e4b9d6a6b1dbe4d8892f71eddb5b45a4d42737ccec371e2a53b40521fe690c',
    SOURCE/'check_fep_anytime_change.py': 'a6997b617a4f100f73cdedc45ebd2eecf4471d809e878a445793e8049ac70708',
    SOURCE/'qualify_fep_anytime_change.py': '31cbcfa97e43d7ef50ddfd0c52d6a3217606871d5a8c37b2dfd28c41a74e102a',
    SOURCE/'FEP_ANYTIME_HORIZON_V1_REPORT.md': 'fb2170cc841bce4837658154504613bca5f5f616d38348c198adf976a38c4444',
    PREVIOUS/'attempt-01/MANIFEST.json': '501d636751615f5ec0592d23baf5baccdc432f47aa665c023def6fc3c6a0d545',
    PREVIOUS/'readback-2026-10-13/READBACK.json': '8b2e9c501984942df1676b5bdd12d2a5a8c817478733ad13ad97a213bde9d60e',
}


def check(group, ok):
    if not bool(ok):
        raise AssertionError(group)
    CHECKS[group] = CHECKS.get(group, 0)+1


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def constrain():
    allowed = sorted(os.sched_getaffinity(0))[:4]
    os.sched_setaffinity(0, allowed)
    check('cpu_limit', len(os.sched_getaffinity(0)) <= 4)


@lru_cache(maxsize=100000)
def beta_moment(a, b, ones, zeros):
    """Independent rising-factorial integral of a Bernoulli sequence."""
    num, den = F(1), F(1)
    for i in range(ones):
        num *= a+i
    for i in range(zeros):
        num *= b+i
    for i in range(ones+zeros):
        den *= a+b+i
    return num/den


def segment(counts, history, kind=0):
    """Integrate a segment directly from counts, without filtering its rows."""
    n = len(history)
    if kind:
        labels = [y ^ (3*x) for y, x in history if x is not None]
        ones = sum((e & 1) if kind == 1 else (e >> 1) for e in labels)
        return F(1, 4**n)*beta_moment(F(1), F(1), ones, len(labels)-ones)
    c = list(map(F, counts))
    parity = [((y >> 1) ^ (y & 1)) for y, _ in history]
    ng = sum(parity)
    value = F(1, 2**n)*beta_moment(c[1]+c[2]+1, c[0]+c[3]+1, ng, n-ng)
    for z, wrong, right in ((0, 3, 0), (1, 2, 1)):
        errors = [y ^ (3*x) for (y, x), zz in zip(history, parity)
                  if zz == z and x is not None]
        ones = sum(e == wrong for e in errors)
        value *= beta_moment(c[wrong]+F(1, 2), c[right]+F(1, 2), ones, len(errors)-ones)
    return value


def integrated(counts, history, boundaries=BOUNDS):
    prior = [F(1, 2)]+[F(1, 6*len(boundaries))]*(3*len(boundaries))
    evidence = [segment(counts, history)]
    for t in boundaries:
        old, new = history[:t-1], history[t-1:]
        prefix = segment(counts, old)
        evidence.extend(prefix*segment((0, 0, 0, 0), new, kind) for kind in range(3))
    return [p*e for p, e in zip(prior, evidence)]


def compare_state(f, w, p):
    check('rational_posterior', np.max(np.abs(f.w[0]-np.array(w, dtype=float))) < 8e-14)
    check('rational_parameters', np.array_equal(f.p[0], np.array(p, dtype=float)))


def metrics(counts, history, w, p, t, y):
    masses = integrated(counts, history)
    evidence = sum(masses)
    check('integrated_posterior', w == [m/evidence for m in masses])
    wf = np.array(w, dtype=float)
    logjoint = np.array([math.log(float(m)) for m in masses])
    optimum = -math.log(float(evidence))
    value = float(wf@(np.log(wf)-logjoint))
    perturbed = .9*wf+.1*np.array(PRIOR, dtype=float)
    perturbed_value = float(perturbed@(np.log(perturbed)-logjoint))
    divergence = float(perturbed@(np.log(perturbed)-np.log(wf)))
    check('conditional_vfe_optimum', abs(value-optimum) < 3e-12)
    check('conditional_vfe_kl_identity', abs(perturbed_value-optimum-divergence) < 3e-12)
    check('conditional_vfe_nonnegative_kl', divergence >= -1e-14)
    groups = [F(0)]*4
    u = F(0)
    for j, (weight, row) in enumerate(zip(w, p)):
        changed = j > 0 and BOUNDS[(j-1)//3] <= t
        kind = Q.kind_at(j, t, BOUNDS)
        groups[1+kind if changed else 0] += weight
        law = Q.law(row, kind)
        e = y ^ (3*((y >> 1) ^ 1))
        u += weight*law[e]/(law[y]+law[y ^ 3])
    return dict(groups=list(map(float, groups)), groups_exact=list(map(str, groups)),
                no_change_hypothesis=float(w[0]), parameter_error_same_parity=float(u),
                parameter_error_exact=str(u), evidence_exact=str(evidence),
                negative_log_evidence=optimum, posterior_vfe=value,
                perturbed_vfe=perturbed_value, perturbation_kl=divergence,
                weights=wf.tolist(), log_joint=logjoint.tolist())


def decisions(f):
    oldw, oldp = f.w.copy(), f.p.copy()
    result = {}
    for depth in (1, 3, 4):
        r, q, delta = f.scores(f.w, f.p, f.z, f.t, depth)
        action, value, _, _ = f.choose(depth)
        check('decision_information_value', delta[0] >= -2e-12 and abs(value[0]-delta[0]) < 1e-14)
        check('planner_noninvasive', np.array_equal(oldw, f.w) and np.array_equal(oldp, f.p))
        result[str(depth)] = dict(action=int(action[0]), answer_score=float(r[0]),
                                 purchase_score=float(q[0]), information_value=float(delta[0]),
                                 subjective_answer_risk=float(min(f.u[0], 1-f.u[0])))
    return result


def physical_risk(counts, y, action, reversed_law):
    law = [F(2*c+1, 132) for c in counts]
    if reversed_law:
        law.reverse()
    pw1 = law[y ^ 3]/(law[y]+law[y ^ 3])
    return float(F(1, 10) if action == 2 else (pw1 if action == 0 else 1-pw1))


def case(job):
    name, onset = job
    CHECKS.clear()
    started = perf_counter()
    counts = PROFILES[name]
    prefix = [(0 if t % 2 else 3, (0 if t % 2 else 1) if t % 4 == 0 else None)
              for t in range(1, onset)]
    traces, exact_planners = [], []
    for schedule in SCHEDULES:
        f = A.Filter(np.array([counts]))
        w, p = PRIOR[:], [Q.initial(counts) for _ in PRIOR]
        reset = Q.reset_rows(counts, False, BOUNDS)
        history = []
        for t, (y, target) in enumerate(prefix, 1):
            f.start(t)
            f.warning(np.array([y], dtype=np.int8))
            p = Q.advance(p, reset, t, BOUNDS)
            w, p, _ = Q.warning(w, p, y, t, BOUNDS)
            if target is not None:
                w, p, _ = Q.label(w, p, y, target, t, BOUNDS)
            f.retain(np.array([-1 if target is None else target]))
            compare_state(f, w, p)
            history.append((y, target))
        rows = []
        for k in range(1, 9):
            t, y = onset+k-1, (0 if k % 2 else 3)
            f.start(t)
            f.warning(np.array([y], dtype=np.int8))
            p = Q.advance(p, reset, t, BOUNDS)
            w, p, warning_probability = Q.warning(w, p, y, t, BOUNDS)
            compare_state(f, w, p)
            history.append((y, None))
            pre = metrics(counts, history, w, p, t, y)
            decision = decisions(f)
            if name == 'strong' and schedule == 'contradictory' and k in (1, 2):
                tick = perf_counter()
                r, q, delta, u = Q.direct_scores(w, p, reset, y, t, 4, BOUNDS)
                expected = (r, q, delta)
                observed = [decision['4'][key] for key in ('answer_score', 'purchase_score', 'information_value')]
                check('rational_ct4_scores', max(abs(a-float(b)) for a, b in zip(observed, expected)) < 2e-13)
                check('rational_ct4_action', decision['4']['action'] == Q.exact_action(r, q, u, y))
                exact_planners.append(dict(schedule=schedule, onset=onset, k=k,
                                           scores=list(map(str, expected)), seconds=perf_counter()-tick))
            action = decision['4']['action']
            target = ((y >> 1) if schedule == 'consistent' else ((y >> 1) ^ 1))
            if schedule == 'withhold' or (schedule == 'on_policy' and action != 2):
                target = None
            feedback = None
            if target is not None:
                oldp, oldw = p, w
                w, p, probability = Q.label(w, p, y, target, t, BOUNDS)
                history[-1] = (y, target)
                for j in range(len(w)):
                    if Q.kind_at(j, t, BOUNDS) == 0:
                        check('general_label_parameter_locality', p[j][:2] == oldp[j][:2] and p[j][4:] == oldp[j][4:])
                changed = [j > 0 and BOUNDS[(j-1)//3] <= t for j in range(len(w))]
                old_changed = sum(v for v, flag in zip(oldw, changed) if flag)
                new_changed = sum(v for v, flag in zip(w, changed) if flag)
                bf = (new_changed/(1-new_changed))/(old_changed/(1-old_changed))
                feedback = dict(target=target, probability=float(probability), probability_exact=str(probability),
                                surprise=-math.log(float(probability)), changed_bayes_factor=float(bf),
                                changed_bayes_factor_exact=str(bf))
            f.retain(np.array([-1 if target is None else target]))
            compare_state(f, w, p)
            post = metrics(counts, history, w, p, t, y) if target is not None else pre
            probes = []
            if k in (1, 2, 4, 8):
                for probe_y in (0, 1):
                    probe = copy.deepcopy(f)
                    probe.start(t+1)
                    probe.warning(np.array([probe_y], dtype=np.int8))
                    pp = Q.advance(p, reset, t+1, BOUNDS)
                    ww, pp, _ = Q.warning(w, pp, probe_y, t+1, BOUNDS)
                    compare_state(probe, ww, pp)
                    probe_decisions = decisions(probe)
                    probes.append(dict(y=probe_y, decisions=probe_decisions,
                                       first_sensor_error=float(probe.u[0]),
                                       physical_risk=physical_risk(counts, probe_y,
                                           probe_decisions['4']['action'], schedule != 'consistent')))
            rows.append(dict(k=k, t=t, y=y, warning_probability_exact=str(warning_probability),
                             pre=pre, post=post, decisions=decision, feedback=feedback, probes=probes,
                             physical_risk=physical_risk(counts, y, action, schedule != 'consistent')))
        traces.append(dict(profile=name, counts=counts, onset=onset, schedule=schedule,
                           prefix=prefix, history=history, rows=rows))
    return dict(profile=name, onset=onset, traces=traces, exact_planners=exact_planners,
                checks=dict(CHECKS), seconds=perf_counter()-started)


def qualify():
    CHECKS.clear()
    started = perf_counter()
    boundaries = (1, 2, 4)
    for counts in ((0, 0, 0, 0), (20, 4, 8, 32)):
        for history in (((0, None),), ((0, 1), (1, None), (3, 1)),
                        ((2, 0), (3, None), (1, 1), (0, None))):
            check('integrated_vs_latent_enumeration', integrated(counts, history, boundaries) == Q.latent_evidence(counts, history, boundaries))
    population = json.loads((PREVIOUS/'attempt-01/POPULATION.json').read_text())['bases']
    proof = []
    for meta in population:
        q, rev = [list(map(F, meta['laws'][i])) for i in (0, 3)]
        check('physical_reversal_definition', rev == list(reversed(q)))
        a = [(q[y]+q[y ^ 3])/2 for y in range(4)]
        b = [(rev[y]+rev[y ^ 3])/2 for y in range(4)]
        check('unlabelled_reversal_identifiability', a == b)
        proof.append(dict(label=meta['label'], warning_likelihood=list(map(str, a))))
    check('all_frozen_laws', len(population) == 27)
    check('neutral_calibration_symmetry', Q.law(Q.initial(PROFILES['neutral']), 0) == (F(1, 4),)*4)
    counts = (20, 4, 8, 32)
    hist = [(t % 4, (t % 2) if t % 3 == 0 else None) for t in range(1, 13)]
    tick = perf_counter()
    Q.compare(A, counts, hist, 0, BOUNDS, steps=4, paths=False)
    rational_seconds = perf_counter()-tick
    f = A.Filter(np.array([counts]))
    for t, (y, x) in enumerate(hist, 1):
        f.start(t); f.warning(np.array([y], dtype=np.int8))
        f.retain(np.array([-1 if x is None else x]))
    f.start(13); f.warning(np.array([0], dtype=np.int8))
    tick = perf_counter()
    decision = decisions(f)
    planning_seconds = perf_counter()-tick
    twin = copy.deepcopy(f)
    twin.ys[:, 12] = 3
    other = decisions(twin)
    for depth in decision:
        for key in ('answer_score', 'purchase_score', 'information_value'):
            check('warning_flip_scores', decision[depth][key] == other[depth][key])
        action, flip = decision[depth]['action'], other[depth]['action']
        check('warning_flip_action', flip == (2 if action == 2 else 1-action))
    w, p, _ = Q.rational_state(counts, hist, 0, BOUNDS)
    tick = perf_counter()
    metrics(counts, hist+[(0, None)], w, p, 13, 0)
    metrics_seconds = perf_counter()-tick
    # Four workers; factor six allows larger fractions/longer histories and imbalance.
    forecast = 6*(4*rational_seconds+384*planning_seconds+384*metrics_seconds)/4+60
    return dict(passed=True, checks=dict(CHECKS), legacy_checks=dict(A.CHECKS),
                proof=proof, seconds=perf_counter()-started, rational_seconds=rational_seconds,
                planning_seconds=planning_seconds, metrics_seconds=metrics_seconds,
                conservative_forecast_seconds=forecast, detach_required=forecast > 600)


def inputs():
    paths = {Path(__file__).resolve(), SPEC, PREVIOUS/'attempt-01/POPULATION.json', *FROZEN}
    for module in list(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file and Path(file).resolve().parent == SOURCE:
            paths.add(Path(file).resolve())
        expected = getattr(module, 'EXPECTED', None)
        if isinstance(expected, dict) and file and Path(file).resolve().parent == SOURCE:
            for name, expected_digest in expected.items():
                path = SOURCE/name
                check('frozen_dependency', digest(path) == expected_digest)
                paths.add(path)
    for path, expected in FROZEN.items():
        check('preserved_horizon', digest(path) == expected)
    return {str(p): digest(p) for p in sorted(paths)}


def prepare(output):
    check('external_mount', os.path.ismount('/mnt/bioIce1'))
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    identities = inputs()
    for path in (Path(__file__).resolve(), SPEC):
        shutil.copyfile(path, output/'inputs'/path.name)
    write(output/'FREEZE.json', dict(created=utc(), inputs=identities, affinity=sorted(os.sched_getaffinity(0)),
                                   profiles=PROFILES, onsets=[13, 63], schedules=SCHEDULES,
                                   diagnostic_tasks=192, probes=192, rational_main_planners=4))
    qualification = qualify()
    write(output/'QUALIFICATION.json', qualification)
    print(json.dumps({k: qualification[k] for k in ('passed', 'seconds', 'conservative_forecast_seconds', 'detach_required')}), flush=True)


def check_inputs(output):
    frozen = json.loads((output/'FREEZE.json').read_text())
    for path, expected in frozen['inputs'].items():
        check('frozen_input_readback', digest(path) == expected)
    for path in (Path(__file__).resolve(), SPEC):
        check('source_snapshot', digest(output/'inputs'/path.name) == frozen['inputs'][str(path)])


def run(output):
    check_inputs(output)
    check('qualification_passed', json.loads((output/'QUALIFICATION.json').read_text())['passed'])
    started = perf_counter()
    write(output/'STARTED.json', dict(started=utc(), pid=os.getpid(), affinity=sorted(os.sched_getaffinity(0))))
    results = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(case, (name, onset)): (name, onset)
                   for name in PROFILES for onset in (13, 63)}
        for future in as_completed(futures):
            result = future.result()
            write(output/(result['profile']+'-'+str(result['onset'])+'.json'), result)
            results.append(result)
            print(json.dumps(dict(completed=[result['profile'], result['onset']], seconds=result['seconds'])), flush=True)
    results.sort(key=lambda d: (d['profile'], d['onset']))
    summary = []
    for result in results:
        for trace in result['traces']:
            rows = trace['rows']
            summary.append(dict(profile=trace['profile'], onset=trace['onset'], schedule=trace['schedule'],
                                recommended_purchases=sum(r['decisions']['4']['action'] == 2 for r in rows),
                                supplied_labels=sum(r['feedback'] is not None for r in rows),
                                first_reversed_answer=next((r['k'] for r in rows if r['decisions']['4']['action'] == ((r['y'] >> 1) ^ 1)), None),
                                first_purchase=next((r['k'] for r in rows if r['decisions']['4']['action'] == 2), None),
                                selected=[dict(k=r['k'], action=r['decisions']['4']['action'],
                                               changed_before=1-r['pre']['groups'][0],
                                               changed_after=1-r['post']['groups'][0],
                                               parameter_error_after=r['post']['parameter_error_same_parity'],
                                               label_probability=None if r['feedback'] is None else r['feedback']['probability'],
                                               probes=[dict(y=p['y'], first_sensor_error=p['first_sensor_error'],
                                                            action=p['decisions']['4']['action']) for p in r['probes']])
                                          for r in rows if r['k'] in (1, 2, 4, 8)]))
    write(output/'SUMMARY.json', dict(traces=summary, seconds=perf_counter()-started,
                                     completed=utc(), diagnostic_tasks=192, probes=192,
                                     checks=[r['checks'] for r in results],
                                     rational_planners=[p for r in results for p in r['exact_planners']]))
    check_inputs(output)
    outputs = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.suffix == '.json'}
    write(output/'MANIFEST.json', dict(completed=utc(), outputs=outputs, checks=dict(CHECKS), seconds=perf_counter()-started))
    print('Completed all 24 traces; saved-data readback remains.', flush=True)


def readback(output):
    CHECKS.clear()
    check_inputs(output)
    manifest = json.loads((output/'MANIFEST.json').read_text())
    for name, expected in manifest['outputs'].items():
        check('output_identity', digest(output/name) == expected)
    ntasks = nprobes = nexact = 0
    summary = json.loads((output/'SUMMARY.json').read_text())
    indexed = {(t['profile'], t['onset'], t['schedule']): t for t in summary['traces']}
    for name in PROFILES:
        for onset in (13, 63):
            saved = json.loads((output/(name+'-'+str(onset)+'.json')).read_text())
            nexact += len(saved['exact_planners'])
            check('all_schedules', [t['schedule'] for t in saved['traces']] == list(SCHEDULES))
            for trace in saved['traces']:
                check('eight_tasks', len(trace['rows']) == 8)
                item = indexed[(name, onset, trace['schedule'])]
                check('summary_purchases', item['recommended_purchases'] == sum(r['decisions']['4']['action'] == 2 for r in trace['rows']))
                check('summary_labels', item['supplied_labels'] == sum(r['feedback'] is not None for r in trace['rows']))
                for row in trace['rows']:
                    ntasks += 1
                    nprobes += len(row['probes'])
                    for phase in ('pre', 'post'):
                        state = row[phase]
                        weights = np.array(state['weights'])
                        logjoint = np.array(state['log_joint'])
                        loge = -state['negative_log_evidence']
                        check('saved_posterior_normalization', abs(weights.sum()-1) < 2e-14)
                        check('saved_posterior_from_joint', np.max(np.abs(np.exp(logjoint-loge)-weights)) < 3e-14)
                        fvalue = float(weights@(np.log(weights)-logjoint))
                        check('saved_vfe_identity', abs(fvalue+loge) < 3e-12 and abs(fvalue-state['posterior_vfe']) < 1e-13)
                        exact_evidence = F(state['evidence_exact'])
                        check('saved_exact_evidence', abs(math.log(float(exact_evidence))-loge) < 1e-13)
                        check('saved_groups', sum(map(F, state['groups_exact'])) == 1 and np.max(np.abs(np.array(list(map(lambda x: float(F(x)), state['groups_exact'])))-state['groups'])) < 1e-15)
                    feedback = row['feedback']
                    check('feedback_schedule', (feedback is not None) == (trace['schedule'] in ('consistent', 'contradictory') or (trace['schedule'] == 'on_policy' and row['decisions']['4']['action'] == 2)))
                    if feedback:
                        check('feedback_probability', F(row['post']['evidence_exact'])/F(row['pre']['evidence_exact']) == F(feedback['probability_exact']))
                        check('feedback_target', feedback['target'] == ((row['y'] >> 1) ^ int(trace['schedule'] != 'consistent')))
                        before = 1-F(row['pre']['groups_exact'][0])
                        after = 1-F(row['post']['groups_exact'][0])
                        check('saved_bayes_factor', (after/(1-after))/(before/(1-before)) == F(feedback['changed_bayes_factor_exact']))
                    else:
                        check('unobserved_label_no_effect', row['pre'] == row['post'])
                    check('saved_physical_risk', abs(row['physical_risk']-physical_risk(PROFILES[name], row['y'], row['decisions']['4']['action'], trace['schedule'] != 'consistent')) < 1e-15)
    check('complete_counts', (ntasks, nprobes, nexact) == (192, 192, 4))
    write(output/'READBACK.json', dict(passed=True, completed=utc(), checks=CHECKS, total_checks=sum(CHECKS.values()),
                                     diagnostic_tasks=ntasks, probes=nprobes, exact_planners=nexact,
                                     main_manifest_sha256=digest(output/'MANIFEST.json')))
    print(json.dumps(dict(passed=True, total_checks=sum(CHECKS.values()), diagnostic_tasks=ntasks, probes=nprobes)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run', 'readback'))
    parser.add_argument('--output', type=Path, default=ROOT/'attempt-01')
    args = parser.parse_args()
    constrain()
    check('output_namespace', args.output.resolve().parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        {'prepare': prepare, 'run': run, 'readback': readback}[args.mode](args.output)
    except BaseException:
        if args.output.exists():
            failure = args.output/('FAILURE-'+args.mode+'.json')
            if not failure.exists():
                write(failure, dict(at=utc(), mode=args.mode, traceback=traceback.format_exc(), checks=CHECKS))
        raise


if __name__ == '__main__':
    main()
