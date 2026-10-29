#!/usr/bin/env python3
"""Frozen, matched-feedback comparison; all generated files stay on the external drive."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
import json
import math
from pathlib import Path
import shutil
from time import perf_counter
import traceback
import numpy as np
import fep_structured_reversal as M

OLD, A, Q = M.OLD, M.A, M.Q
SOURCE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-reversal-v1')
PREVIOUS = OLD.ROOT/'attempt-01'
SPEC = SOURCE/'FEP_STRUCTURED_REVERSAL_V1.md'
SCHEDULES = ('withhold', 'consistent', 'contradictory')
PROFILES = OLD.PROFILES
CHECKS = {}
write, digest, utc = OLD.write, OLD.digest, OLD.utc
FROZEN = {
    SOURCE/'check_fep_reversal_feedback_audit.py': '1a0f628873cdc6bb2943458a1ba8eff226c95f9e532458a02f053ae51e34a661',
    SOURCE/'FEP_REVERSAL_FEEDBACK_AUDIT_V1.md': 'aaa45c8b15a8d6e963251eb91038815a0bd1b01686ab9bd9515c37c9c69088e4',
    SOURCE/'FEP_REVERSAL_FEEDBACK_AUDIT_V1_REPORT.md': '152416b9c3853df3e3c298976e173a1c37ab89393c975a8df5258828a59062d4',
    PREVIOUS/'MANIFEST.json': '8bcd01a737410e19e5757614eea3423630bbddec1c999e3d366357ac1ed68ab1',
    PREVIOUS/'READBACK.json': 'b3badb4dffe8463edcd9005ee286b54670fae254e0be8ec66965c4e2444bc2de',
}


def check(group, ok):
    if not bool(ok):
        raise AssertionError(group)
    CHECKS[group] = CHECKS.get(group, 0)+1


def compare(f, w, p):
    check('rational_posterior', np.max(np.abs(f.w[0]-np.array(w, dtype=float))) < 1e-13)
    check('rational_parameters', np.array_equal(f.p[0], np.array(p, dtype=float)))


def metrics(counts, history, w, ref):
    masses = M.integrated(counts, history, ref.boundaries, ref.share)
    evidence = sum(masses)
    check('integrated_posterior', w == [m/evidence for m in masses])
    wf = np.array(w, dtype=float)
    logjoint = np.array([math.log(float(v)) for v in masses])
    optimum = -math.log(float(evidence))
    value = float(wf@(np.log(wf)-logjoint))
    perturb = .9*wf+.1*np.array(ref.prior, dtype=float)
    other = float(perturb@(np.log(perturb)-logjoint))
    kl = float(perturb@(np.log(perturb)-np.log(wf)))
    check('vfe_optimum', abs(value-optimum) < 3e-12)
    check('vfe_kl_identity', abs(other-optimum-kl) < 3e-12 and kl >= -1e-14)
    groups = [F(0)]*5
    for j, ((tau, kind), weight) in enumerate(zip(ref.hypotheses, w)):
        groups[1+kind if j and tau <= len(history) else 0] += weight
    return dict(evidence_exact=str(evidence), negative_log_evidence=optimum,
                posterior_vfe=value, perturbed_vfe=other, perturbation_kl=kl,
                weights=wf.tolist(), log_joint=logjoint.tolist(),
                groups=list(map(float, groups)), groups_exact=list(map(str, groups)))


def decisions(f):
    oldw, oldp = f.w.copy(), f.p.copy()
    result = {}
    for horizon in (1, 3, 4):
        r, q, delta = f.scores(f.w, f.p, f.z, f.t, horizon)
        action, value, _, _ = f.choose(horizon)
        check('information_value', delta[0] >= -2e-12 and abs(delta[0]-value[0]) < 1e-14)
        check('planner_noninvasive', np.array_equal(oldw, f.w) and np.array_equal(oldp, f.p))
        result[str(horizon)] = dict(action=int(action[0]), answer_score=float(r[0]),
                                   purchase_score=float(q[0]), information_value=float(delta[0]),
                                   subjective_answer_risk=float(min(f.u[0], 1-f.u[0])))
    return result


def risk(counts, y, action, reverse):
    q = [F(2*c+1, 132) for c in counts]
    if reverse:
        q.reverse()
    p1 = q[y ^ 3]/(q[y]+q[y ^ 3])
    return F(1, 10) if action == 2 else (p1 if action == 0 else 1-p1)


def load_filter(counts, history, y, boundaries=M.BOUNDS, share=M.SHARE):
    f = M.Filter(np.array([counts]), boundaries, share)
    for t, (yy, target) in enumerate(history, 1):
        f.start(t); f.warning(np.array([yy], dtype=np.int8))
        f.retain(np.array([-1 if target is None else target]))
    f.start(len(history)+1); f.warning(np.array([y], dtype=np.int8))
    return f


def rational_planning(f, ref, w, p, y, horizon=4, lesion=False):
    started = perf_counter()
    exact = ref.scores(w, p, y, f.t, horizon, not lesion)
    actual = f.scores(f.w, f.p, f.z, f.t, horizon, not lesion)
    check('rational_planning_scores', max(abs(a[0]-float(b)) for a, b in zip(actual, exact[:3])) < 2e-13)
    action = f.choose(horizon, not lesion)[0][0]
    check('rational_planning_action', action == Q.exact_action(exact[0], exact[1], exact[3], y))
    check('rational_information_nonnegative', exact[2] >= 0)
    if lesion:
        check('no_retention_information_value', exact[2] == 0 and actual[2][0] == 0)
    return dict(scores=list(map(str, exact[:3])), seconds=perf_counter()-started)


def qualify():
    CHECKS.clear()
    started = perf_counter()
    boundaries = (1, 2, 4)
    histories = (((0, None),), ((0, 1), (1, None), (3, 1)),
                 ((2, 0), (3, None), (1, 1), (0, None)))
    for counts in ((0, 0, 0, 0), (20, 4, 8, 32)):
        for history in histories:
            complete = list(history)+[(2, None)]
            masses = M.integrated(counts, complete, boundaries)
            check('complete_latent_paths', masses == M.latent_paths(counts, complete, boundaries))
            ref = M.Reference(counts, boundaries)
            w, p = ref.state(history, 2)
            check('reference_integrated', w == [m/sum(masses) for m in masses])
            f = load_filter(counts, history, 2, boundaries)
            compare(f, w, p)
            check('label_normalization', sum(ref.label(w, p, 2, x, f.t)[2] for x in (0, 1)) == 1)
            pp = ref.advance(p, f.t+1)
            check('warning_normalization', sum(ref.warning(w, pp, y, f.t+1)[2] for y in range(4)) == 1)
            rational_planning(f, ref, w, p, 2, 3)
    # Four-step recursion and lesion on small support, independently summed over all warnings.
    counts, history = (20, 4, 8, 32), histories[1]
    ref = M.Reference(counts, boundaries)
    w, p = ref.state(history, 0)
    f = load_filter(counts, history, 0, boundaries)
    rational_planning(f, ref, w, p, 0, 4)
    rational_planning(f, ref, w, p, 0, 4, lesion=True)
    flipped = [(y ^ 3, None if x is None else x ^ 1) for y, x in history]
    twin = load_filter(counts, flipped, 3, boundaries)
    check('warning_flip_belief', np.array_equal(f.w, twin.w) and np.array_equal(f.p, twin.p))
    d1, d2 = decisions(f), decisions(twin)
    for h in d1:
        check('warning_flip_scores', all(d1[h][key] == d2[h][key] for key in ('answer_score', 'purchase_score', 'information_value')))
        check('warning_flip_actions', d2[h]['action'] == (2 if d1[h]['action'] == 2 else 1-d1[h]['action']))
    # R preserves the old latent law at onset, while G resets it.
    ref = M.Reference(counts, boundaries)
    w, p = ref.initial()
    w, p, _ = ref.warning(w, ref.advance(p, 1), 0, 1)
    w, p, _ = ref.label(w, p, 0, 0, 1)
    j = ref.hypotheses.index((2, 3))
    check('reversal_no_reset', ref.advance(p, 2)[j] == p[j])
    before = p[j][:]
    w, p, _ = ref.warning(w, ref.advance(p, 2), 3, 2)
    w, p, _ = ref.label(w, p, 3, 0, 2)
    check('reversal_shared_orientation', p[j][2] == before[2] and p[j][3] == before[3]+1)
    unlabeled = [(i % 4, None) for i in range(6)]
    ev = M.integrated(counts, unlabeled, boundaries)
    prior = M.priors(boundaries)
    for j, (_, kind) in enumerate(ref.hypotheses):
        if kind == 3:
            check('no_label_reversal_invariance', ev[j]/prior[j] == ev[0]/prior[0])
    # Removing R's prior must reproduce the original model on all original components.
    for bounds in (boundaries, M.BOUNDS):
        new = M.Filter(np.array([counts]), bounds, F(0))
        old = A.Filter(np.array([counts]), bounds)
        selected = new.kinds != 3
        for t in range(1, 13):
            y, label = t % 4, (-1 if t % 3 else t % 2)
            for learner in (new, old):
                learner.start(t); learner.warning(np.array([y], dtype=np.int8))
            check('zero_R_posterior', np.max(np.abs(new.w[:, selected]-old.w)) < 1e-13)
            check('zero_R_parameters', np.array_equal(new.p[:, selected], old.p))
            if t in (1, 4, 12):
                for depth in (1, 3, 4):
                    ns = new.scores(new.w, new.p, new.z, t, depth)
                    oscores = old.scores(old.w, old.p, old.z, t, depth)
                    check('zero_R_scores', max(np.max(np.abs(a-b)) for a, b in zip(ns, oscores)) < 2e-13)
                    check('zero_R_actions', np.array_equal(new.choose(depth)[0], old.choose(depth)[0]))
            for learner in (new, old):
                learner.retain(np.array([label]))
            check('zero_R_postlabel', np.max(np.abs(new.w[:, selected]-old.w)) < 1e-13 and np.array_equal(new.p[:, selected], old.p))
    # Full-support independent planner benchmark on synthetic observations, not a main history.
    history = [(t % 4, t % 2 if t % 3 == 0 else None) for t in range(1, 13)]
    f = load_filter(counts, history, 0)
    ref = M.Reference(counts)
    w, p = ref.state(history, 0)
    compare(f, w, p)
    full = rational_planning(f, ref, w, p, 0)
    tick = perf_counter(); decisions(f); planning_seconds = perf_counter()-tick
    tick = perf_counter(); metrics(counts, history+[(0, None)], w, ref); metric_seconds = perf_counter()-tick
    forecast = 6*(4*full['seconds']+288*planning_seconds+288*metric_seconds)/4+60
    check('fixed_prior', sum(ref.prior) == 1 and len(ref.prior) == 401 and ref.prior[0] == F(1, 2)
          and ref.prior[1:5] == [F(1, 1200), F(1, 600), F(1, 600), F(1, 1200)])
    return dict(passed=True, checks=dict(CHECKS), seconds=perf_counter()-started,
                full_rational=full, planning_seconds=planning_seconds, metric_seconds=metric_seconds,
                conservative_forecast_seconds=forecast, detach_required=forecast > 600)


def case(job):
    name, onset = job
    started = perf_counter()
    CHECKS.clear()
    counts = PROFILES[name]
    source = PREVIOUS/(name+'-'+str(onset)+'.json')
    previous = json.loads(source.read_text())
    traces, exact_planners = [], []
    for baseline in previous['traces']:
        schedule = baseline['schedule']
        if schedule not in SCHEDULES:
            continue
        check('frozen_history_shape', baseline['counts'] == list(counts) and len(baseline['prefix']) == onset-1 and len(baseline['rows']) == 8)
        f = M.Filter(np.array([counts]))
        ref = M.Reference(counts)
        w, p = ref.initial()
        history = []
        for t, (y, target) in enumerate(baseline['prefix'], 1):
            f.start(t); f.warning(np.array([y], dtype=np.int8))
            w, p, _ = ref.warning(w, ref.advance(p, t), y, t)
            if target is not None:
                w, p, _ = ref.label(w, p, y, target, t)
            f.retain(np.array([-1 if target is None else target]))
            compare(f, w, p)
            history.append((y, target))
        prefix_new = sum(M.integrated(counts, history))
        prefix_old = sum(OLD.integrated(counts, history))
        rows = []
        for oldrow in baseline['rows']:
            t, k, y = oldrow['t'], oldrow['k'], oldrow['y']
            target = None if oldrow['feedback'] is None else oldrow['feedback']['target']
            check('fixed_feedback_schedule', (target is None) == (schedule == 'withhold'))
            f.start(t); f.warning(np.array([y], dtype=np.int8))
            w, p, warning_probability = ref.warning(w, ref.advance(p, t), y, t)
            compare(f, w, p)
            history.append((y, None))
            check('baseline_prefeedback_evidence', sum(OLD.integrated(counts, history)) == F(oldrow['pre']['evidence_exact']))
            pre = metrics(counts, history, w, ref)
            decision = decisions(f)
            if name == 'strong' and schedule == 'contradictory' and k in (1, 2):
                exact = rational_planning(f, ref, w, p, y)
                exact_planners.append(dict(onset=onset, k=k, **exact))
            feedback = None
            if target is not None:
                w, p, probability = ref.label(w, p, y, target, t)
                history[-1] = (y, target)
                feedback = dict(target=target, probability=float(probability), probability_exact=str(probability),
                                old_probability_exact=oldrow['feedback']['probability_exact'],
                                log_score_gain=math.log(float(probability))-math.log(oldrow['feedback']['probability']))
            f.retain(np.array([-1 if target is None else target]))
            compare(f, w, p)
            check('baseline_postfeedback_evidence', sum(OLD.integrated(counts, history)) == F(oldrow['post']['evidence_exact']))
            post = metrics(counts, history, w, ref) if target is not None else pre
            probes = []
            for oldprobe in oldrow['probes']:
                yy = oldprobe['y']
                probe = copy.deepcopy(f)
                probe.start(t+1); probe.warning(np.array([yy], dtype=np.int8))
                ww, pp, _ = ref.warning(w, ref.advance(p, t+1), yy, t+1)
                compare(probe, ww, pp)
                pd = decisions(probe)
                probes.append(dict(y=yy, decisions=pd, baseline_decisions=oldprobe['decisions'],
                                   first_sensor_error=float(probe.u[0]), baseline_first_sensor_error=oldprobe['first_sensor_error'],
                                   risk_exact=str(risk(counts, yy, pd['4']['action'], schedule != 'consistent')),
                                   baseline_risk_exact=str(risk(counts, yy, oldprobe['decisions']['4']['action'], schedule != 'consistent'))))
            nr = risk(counts, y, decision['4']['action'], schedule != 'consistent')
            br = risk(counts, y, oldrow['decisions']['4']['action'], schedule != 'consistent')
            check('baseline_evaluator_risk', abs(float(br)-oldrow['physical_risk']) < 1e-15)
            rows.append(dict(t=t, k=k, y=y, pre=pre, post=post, decisions=decision, feedback=feedback, probes=probes,
                             warning_probability_exact=str(warning_probability),
                             baseline_decisions=oldrow['decisions'], baseline_pre_evidence=oldrow['pre']['evidence_exact'],
                             baseline_post_evidence=oldrow['post']['evidence_exact'],
                             risk_exact=str(nr), baseline_risk_exact=str(br)))
        check('identical_complete_history', [list(h) for h in history] == baseline['history'])
        traces.append(dict(profile=name, onset=onset, schedule=schedule, counts=counts,
                           prefix=baseline['prefix'], history=history, rows=rows,
                           prefix_evidence_new=str(prefix_new), prefix_evidence_old=str(prefix_old),
                           fallback_count=f.fallback))
    return dict(profile=name, onset=onset, traces=traces, exact_planners=exact_planners,
                checks=dict(CHECKS), source_sha256=digest(source), seconds=perf_counter()-started)


def analyze(results):
    table, primary_differences, stable_harms = [], [], []
    for result in sorted(results, key=lambda d: (d['profile'], d['onset'])):
        for trace in result['traces']:
            rows = trace['rows']
            nr = sum(F(r['risk_exact']) for r in rows)/8
            br = sum(F(r['baseline_risk_exact']) for r in rows)/8
            last = rows[-1]
            label_gain = sum(r['feedback']['log_score_gain'] for r in rows if r['feedback'])
            full_bf = F(last['post']['evidence_exact'])/F(last['baseline_post_evidence'])
            conditional_bf = full_bf/(F(trace['prefix_evidence_new'])/F(trace['prefix_evidence_old']))
            item = dict(profile=trace['profile'], onset=trace['onset'], schedule=trace['schedule'],
                        risk_new=float(nr), risk_old=float(br), risk_delta=float(nr-br), risk_delta_exact=str(nr-br),
                        purchases_new=sum(r['decisions']['4']['action'] == 2 for r in rows),
                        purchases_old=sum(r['baseline_decisions']['4']['action'] == 2 for r in rows),
                        first_reverse_new=next((r['k'] for r in rows if r['decisions']['4']['action'] == ((r['y'] >> 1) ^ 1)), None),
                        first_reverse_old=next((r['k'] for r in rows if r['baseline_decisions']['4']['action'] == ((r['y'] >> 1) ^ 1)), None),
                        label_log_score_gain=label_gain, full_log_bayes_factor=math.log(float(full_bf)),
                        conditional_log_bayes_factor=math.log(float(conditional_bf)),
                        posterior_reversal_after_eight=last['post']['groups'][4],
                        probes=[dict(k=r['k'], probes=r['probes']) for r in rows if r['probes']])
            table.append(item)
            if trace['profile'] == 'strong' and trace['schedule'] == 'contradictory':
                primary_differences.extend(F(r['risk_exact'])-F(r['baseline_risk_exact']) for r in rows)
            if trace['schedule'] == 'consistent' and nr > br:
                stable_harms.append(dict(profile=trace['profile'], onset=trace['onset'], risk_delta=float(nr-br), risk_delta_exact=str(nr-br)))
    check('primary_size', len(primary_differences) == 16)
    primary = sum(primary_differences)/16
    return dict(traces=table, primary=dict(mean_risk_difference=float(primary), exact=str(primary),
                                         improves_fixed_diagnostic=primary < 0, tasks=16),
                stable_harms=stable_harms, paired_tasks=144, paired_probes=144,
                main_checks=[r['checks'] for r in results],
                exact_planners=[r for group in results for r in group['exact_planners']])


def identities():
    result = OLD.inputs()
    for path, expected in FROZEN.items():
        check('preserved_audit', digest(path) == expected)
        result[str(path)] = expected
    previous_freeze = json.loads((PREVIOUS/'FREEZE.json').read_text())
    for path, expected in previous_freeze['inputs'].items():
        check('previous_inputs_preserved', digest(path) == expected)
        result[path] = expected
    previous_manifest = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    for name, expected in previous_manifest['outputs'].items():
        path = PREVIOUS/name
        check('previous_outputs_preserved', digest(path) == expected)
        result[str(path)] = expected
    for path in (SPEC, Path(__file__).resolve(), SOURCE/'fep_structured_reversal.py'):
        result[str(path)] = digest(path)
    return result


def check_inputs(output):
    frozen = json.loads((output/'FREEZE.json').read_text())
    for path, expected in frozen['inputs'].items():
        check('frozen_input', digest(path) == expected)
    for name in ('FEP_STRUCTURED_REVERSAL_V1.md', 'fep_structured_reversal.py', 'check_fep_structured_reversal.py'):
        check('source_snapshot', digest(output/'inputs'/name) == frozen['inputs'][str(SOURCE/name)])


def prepare(output):
    check('external_mount', os.path.ismount('/mnt/bioIce1'))
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    frozen = identities()
    for path in (SPEC, Path(__file__).resolve(), SOURCE/'fep_structured_reversal.py'):
        shutil.copyfile(path, output/'inputs'/path.name)
    write(output/'FREEZE.json', dict(created=utc(), inputs=frozen, prior_share=str(M.SHARE),
                                   schedules=SCHEDULES, profiles=PROFILES, onsets=[13, 63],
                                   paired_tasks=144, paired_probes=144, affinity=sorted(os.sched_getaffinity(0))))
    qualification = qualify()
    write(output/'QUALIFICATION.json', qualification)
    check_inputs(output)
    print(json.dumps({k: qualification[k] for k in ('passed', 'seconds', 'conservative_forecast_seconds', 'detach_required')}), flush=True)


def run(output):
    check_inputs(output)
    check('qualification_passed', json.loads((output/'QUALIFICATION.json').read_text())['passed'])
    started = perf_counter()
    write(output/'STARTED.json', dict(started=utc(), pid=os.getpid(), affinity=sorted(os.sched_getaffinity(0))))
    results = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(case, (name, onset)) for name in PROFILES for onset in (13, 63)]
        for future in as_completed(futures):
            result = future.result()
            write(output/(result['profile']+'-'+str(result['onset'])+'.json'), result)
            results.append(result)
            print(json.dumps(dict(completed=[result['profile'], result['onset']], seconds=result['seconds'])), flush=True)
    summary = analyze(results)
    summary.update(completed=utc(), seconds=perf_counter()-started)
    write(output/'SUMMARY.json', summary)
    check_inputs(output)
    outputs = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.suffix == '.json'}
    write(output/'MANIFEST.json', dict(completed=utc(), outputs=outputs, checks=dict(CHECKS), seconds=perf_counter()-started))
    print('All 18 paired traces complete; starting saved-data readback.', flush=True)


def readback(output):
    CHECKS.clear()
    check_inputs(output)
    manifest = json.loads((output/'MANIFEST.json').read_text())
    for name, expected in manifest['outputs'].items():
        check('output_identity', digest(output/name) == expected)
    summary = json.loads((output/'SUMMARY.json').read_text())
    indexed = {(t['profile'], t['onset'], t['schedule']): t for t in summary['traces']}
    ntasks = nprobes = nexact = 0
    primary, harms = [], []
    for name, counts in PROFILES.items():
        for onset in (13, 63):
            data = json.loads((output/(name+'-'+str(onset)+'.json')).read_text())
            original = json.loads((PREVIOUS/(name+'-'+str(onset)+'.json')).read_text())
            oldtraces = {t['schedule']: t for t in original['traces']}
            check('source_hash', data['source_sha256'] == digest(PREVIOUS/(name+'-'+str(onset)+'.json')))
            check('all_schedules', [t['schedule'] for t in data['traces']] == list(SCHEDULES))
            nexact += len(data['exact_planners'])
            for trace in data['traces']:
                schedule = trace['schedule']
                previous = oldtraces[schedule]
                check('identical_history', trace['history'] == previous['history'] and trace['prefix'] == previous['prefix'])
                check('eight_tasks', len(trace['rows']) == 8)
                table = indexed[(name, onset, schedule)]
                oldev, newev = F(trace['prefix_evidence_old']), F(trace['prefix_evidence_new'])
                differences, new_risks, old_risks = [], [], []
                label_gain, warning_gain = 0., 0.
                for row, oldrow in zip(trace['rows'], previous['rows']):
                    ntasks += 1
                    check('baseline_saved_decisions', row['baseline_decisions'] == oldrow['decisions'])
                    check('baseline_saved_evidence', row['baseline_pre_evidence'] == oldrow['pre']['evidence_exact'] and row['baseline_post_evidence'] == oldrow['post']['evidence_exact'])
                    newpre = F(row['pre']['evidence_exact'])
                    oldpre = F(row['baseline_pre_evidence'])
                    check('warning_evidence_ratio', newpre/newev == F(row['warning_probability_exact']))
                    warning_gain += math.log(float(newpre/newev))-math.log(float(oldpre/oldev))
                    for phase in ('pre', 'post'):
                        state = row[phase]
                        wf, joint = np.array(state['weights']), np.array(state['log_joint'])
                        loge = math.log(float(F(state['evidence_exact'])))
                        check('saved_normalization', abs(wf.sum()-1) < 3e-14)
                        check('saved_posterior', np.max(np.abs(wf-np.exp(joint-loge))) < 5e-14)
                        value = float(wf@(np.log(wf)-joint))
                        check('saved_vfe', abs(value-state['posterior_vfe']) < 1e-13 and abs(value+loge) < 3e-12)
                        perturb = .9*wf+.1*np.array(M.priors(M.BOUNDS), dtype=float)
                        kl = float(perturb@(np.log(perturb)-np.log(wf)))
                        check('saved_kl', abs(kl-state['perturbation_kl']) < 1e-13 and abs(state['perturbed_vfe']+loge-kl) < 3e-12)
                        check('saved_groups', sum(map(F, state['groups_exact'])) == 1 and
                              np.max(np.abs(np.array([float(F(v)) for v in state['groups_exact']])-state['groups'])) < 1e-15)
                    feedback = row['feedback']
                    check('paid_feedback_protocol', (feedback is None) == (schedule == 'withhold'))
                    if feedback:
                        check('identical_label', feedback['target'] == oldrow['feedback']['target'])
                        probability = F(row['post']['evidence_exact'])/newpre
                        check('label_probability', probability == F(feedback['probability_exact']))
                        gain = math.log(float(probability))-math.log(float(F(feedback['old_probability_exact'])))
                        check('label_logscore', abs(gain-feedback['log_score_gain']) < 1e-14)
                        label_gain += gain
                    else:
                        check('no_label_no_update', row['pre'] == row['post'])
                    # Rebuild risk directly from error masses and actions, independently of the stored risk helper.
                    law = [F(2*c+1, 132) for c in counts]
                    if schedule != 'consistent':
                        law = law[::-1]
                    for field, decision_field, accumulator in (('risk_exact', 'decisions', new_risks),
                                                              ('baseline_risk_exact', 'baseline_decisions', old_risks)):
                        action, y = row[decision_field]['4']['action'], row['y']
                        value = F(1, 10) if action == 2 else law[y ^ (3*(1-action))]/(law[y]+law[y ^ 3])
                        check('saved_action_risk', F(row[field]) == value)
                        accumulator.append(value)
                    differences.append(new_risks[-1]-old_risks[-1])
                    check('probe_count', len(row['probes']) == len(oldrow['probes']))
                    for probe, oldprobe in zip(row['probes'], oldrow['probes']):
                        nprobes += 1
                        check('baseline_probe', probe['y'] == oldprobe['y'] and probe['baseline_decisions'] == oldprobe['decisions'])
                        for field, decision_field in (('risk_exact', 'decisions'), ('baseline_risk_exact', 'baseline_decisions')):
                            action, y = probe[decision_field]['4']['action'], probe['y']
                            value = F(1, 10) if action == 2 else law[y ^ (3*(1-action))]/(law[y]+law[y ^ 3])
                            check('probe_risk', F(probe[field]) == value)
                    newev, oldev = F(row['post']['evidence_exact']), F(row['baseline_post_evidence'])
                delta = sum(differences)/8
                check('table_risk_difference', delta == F(table['risk_delta_exact']) and abs(float(delta)-table['risk_delta']) < 1e-15)
                check('table_risk_means', abs(float(sum(new_risks)/8)-table['risk_new']) < 1e-15 and abs(float(sum(old_risks)/8)-table['risk_old']) < 1e-15)
                check('table_label_score', abs(label_gain-table['label_log_score_gain']) < 1e-13)
                check('evidence_telescoping', abs(label_gain+warning_gain-table['conditional_log_bayes_factor']) < 3e-12)
                check('full_history_evidence', abs(math.log(float(newev/oldev))-table['full_log_bayes_factor']) < 1e-13)
                for field, df in (('new', 'decisions'), ('old', 'baseline_decisions')):
                    check('table_purchase_count', table['purchases_'+field] == sum(r[df]['4']['action'] == 2 for r in trace['rows']))
                    first = next((r['k'] for r in trace['rows'] if r[df]['4']['action'] == ((r['y'] >> 1) ^ 1)), None)
                    check('table_first_reverse', table['first_reverse_'+field] == first)
                if name == 'strong' and schedule == 'contradictory':
                    primary.extend(differences)
                if schedule == 'consistent' and delta > 0:
                    harms.append((name, onset, str(delta)))
    check('complete_counts', (ntasks, nprobes, nexact, len(primary)) == (144, 144, 4, 16))
    primary_mean = sum(primary)/16
    check('primary_contrast', primary_mean == F(summary['primary']['exact']) and float(primary_mean) == summary['primary']['mean_risk_difference'])
    check('primary_sign', (primary_mean < 0) == summary['primary']['improves_fixed_diagnostic'])
    check('all_stable_harms', sorted(harms) == sorted((t['profile'], t['onset'], t['risk_delta_exact']) for t in summary['stable_harms']))
    write(output/'READBACK.json', dict(passed=True, completed=utc(), checks=dict(CHECKS), total_checks=sum(CHECKS.values()),
                                     paired_tasks=ntasks, paired_probes=nprobes, rational_main_states=nexact,
                                     manifest_sha256=digest(output/'MANIFEST.json')))
    print(json.dumps(dict(readback_passed=True, checks=sum(CHECKS.values()), paired_tasks=ntasks, paired_probes=nprobes)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run', 'readback'))
    parser.add_argument('--output', type=Path, default=ROOT/'attempt-01')
    args = parser.parse_args()
    OLD.constrain()
    check('output_namespace', args.output.resolve().parent == ROOT and args.output.name.startswith('attempt-'))
    if args.mode == 'prepare' and args.output.exists():
        raise FileExistsError('Preserve existing attempt; choose a new output path.')
    if args.mode == 'run' and (args.output/'STARTED.json').exists():
        raise FileExistsError('This attempt has already started; do not replay it.')
    try:
        {'prepare': prepare, 'run': run, 'readback': readback}[args.mode](args.output)
        if args.mode == 'run':
            readback(args.output)
    except BaseException:
        if args.output.exists():
            failure = args.output/('FAILURE-'+args.mode+'.json')
            if not failure.exists():
                write(failure, dict(at=utc(), mode=args.mode, traceback=traceback.format_exc(), checks=dict(CHECKS)))
        raise


if __name__ == '__main__':
    main()
