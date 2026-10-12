#!/usr/bin/env python3
"""Trace the frozen seven-arm C3 cohort and attribute unchanged recovery costs."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
assert sha256((SOURCE/'check_fep_three_decision_checking.py').read_bytes()).hexdigest() == '6198011cb6fe32d2a2c1acc0bc977300e6c8b2281c58e706e2da98b9ed231349'
import check_fep_three_decision_checking as T
import numpy as np
M, A, B = T.M, T.A, T.B
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-c3-recovery-audit-v1')
PREVIOUS = T.ROOT/'attempt-01'
PREVIOUS_SHA = 'b00a901b57ae65086f578e6834d2af760ce42ba39ba8927ece92a8a10bec3ddd'
REPORT_SHA = '22cecd08f7f1b9427f9be10d4e017e82d3d96a92434147ff21ce67ae9d5fd48f'
ARMS, ANCHORS, PHASES = T.ARMS, A.ANCHORS, A.PHASES
COUNTS = (*A.COUNTS, 'extra_references')
SUMS = (*A.SUMS, 'physical_myopic_cost', 'subjective_myopic_cost')
FIELDS = ('phase_counts', 'phase_sums', 'first_query', 'whole_units')
BASE_FILTER, BASE_FUTURE, BASE_THREE = M.Filter, B.choose_future, T.choose_three
CHECKS = {}


def check(group, description, condition):
    if not bool(condition):
        raise AssertionError(group+': '+description)
    CHECKS[group] = CHECKS.get(group, 0)+1


class TracedFilter(BASE_FILTER):
    instances = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_actions = np.empty((self.n, 5, 100), dtype=np.int8)
        self.audit_myopic = np.empty_like(self.audit_actions)
        self.audit_u = np.empty((self.n, 5, 100))
        TracedFilter.instances.append(self)

    def warning(self, y):
        result = super().warning(y)
        self.audit_actions[:, :, self.t-1] = result[0]
        self.audit_myopic[:, :, self.t-1] = result[0]
        self.audit_u[:, :, self.t-1] = result[3]
        return result


def traced_future(learner, y, myopic):
    result = BASE_FUTURE(learner, y, myopic)
    learner.audit_actions[:, 2, learner.t-1] = result[0]
    return result


def traced_three(learner, y, myopic):
    result = BASE_THREE(learner, y, myopic)
    # Replace the nested own-history C2 diagnostic with the final C3 action.
    learner.audit_actions[:, 2, learner.t-1] = result[0]
    return result


def task_terms(actions, myopic, u, warnings, truth, q):
    counts, sums = A.task_terms(actions, u, warnings, truth, q)
    p = A.physical_probabilities(q, warnings)[..., None, :]
    posterior = np.where((warnings[..., None, :] & 2) != 0, 1-u, u)
    physical_myopic = np.where(myopic == 2, .1, np.where(myopic == 0, p, 1-p))
    subjective_myopic = np.where(myopic == 2, .1, np.where(myopic == 0, posterior, 1-posterior))
    extra = ((actions == 2) & (myopic != 2)).astype(np.int16)
    counts = np.concatenate((counts, extra[..., None]), axis=-1)
    sums = np.concatenate((sums, physical_myopic[..., None], subjective_myopic[..., None]), axis=-1)
    check('risk', 'cost/headroom/residual identity', np.allclose(
        counts[..., 1]+counts[..., 2]/10-.1,
        sums[..., 2:5].sum(axis=-1)-(.1-sums[..., 1])
        +counts[..., 1]+counts[..., 2]/10-sums[..., 0], atol=2e-15, rtol=0))
    return counts, sums


def replay(meta, indices, prefix, bridge):
    start, cpu = perf_counter(), process_time()
    check('trace', 'clean wrappers', M.Filter is BASE_FILTER and B.choose_future is BASE_FUTURE
          and T.choose_three is BASE_THREE and not TracedFilter.instances)
    try:
        M.Filter, B.choose_future, T.choose_three = TracedFilter, traced_future, traced_three
        original, _ = T.run_batch(meta, indices, prefix)
        traces = TracedFilter.instances[:]
    finally:
        M.Filter, B.choose_future, T.choose_three = BASE_FILTER, BASE_FUTURE, BASE_THREE
        TracedFilter.instances.clear()
    original_fingerprint = M.fingerprint(original)
    if bridge:
        path = PREVIOUS/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with np.load(path, allow_pickle=False) as saved:
            check('bridge', 'original fields', set(saved.files) == set(original))
            for key, array in original.items():
                check('bridge', key, array.dtype == saved[key].dtype and np.array_equal(array, saved[key]))
            check('bridge', 'original byte fingerprint', M.fingerprint({k: saved[k] for k in saved.files}) == original_fingerprint)
    b = len(indices)
    check('trace', 'three filter instances', len(traces) == 3)
    def combine(field):
        arrays = [getattr(traces[0], field)]+[getattr(f, field)[:, 2:3] for f in traces[1:]]
        return np.concatenate(arrays, axis=1).reshape(b, 10, 7, 100)
    actions, myopic, u = (combine(k) for k in ('audit_actions', 'audit_myopic', 'audit_u'))
    check('trace', 'only additional purchases', np.all((actions == myopic) | ((actions == 2) & (myopic != 2))))
    check('trace', 'old controls unchanged myopic', np.array_equal(actions[:, :, :5], myopic[:, :, :5]))
    c, warnings, truth, q = A.physical_trace(meta, indices, prefix)
    check('bridge', 'calibration', np.array_equal(c, original['calibration']))
    counts, sums = task_terms(actions, myopic, u, warnings, truth, q)
    check('trace', 'subjective immediate premium nonnegative', np.all(sums[..., 5]-sums[..., 7] >= -2e-12))
    check('bridge', 'chosen actions reproduce costs', np.array_equal(counts[..., 1].sum(axis=-1), original['wrong'])
          and np.array_equal(counts[..., 2].sum(axis=-1), original['references']))
    check('bridge', 'C2 extra actions', np.array_equal(counts[:, :, 5, :, 3].sum(axis=-1), original['c2_extra_references'][..., 0]))
    check('bridge', 'C3 extra actions', np.array_equal(counts[:, :, 6, :, 3].sum(axis=-1), original['extra_references'][..., 0]))
    pc = np.empty((b, 12, 7, 3, 4), dtype=np.int16)
    ps = np.empty((b, 12, 7, 3, 8))
    first = np.empty((b, 12, 7), dtype=np.int16)
    for j, (condition, tau) in enumerate(ANCHORS):
        first[:, j], masks = A.phase_masks(actions[:, condition], tau)
        pc[:, j] = np.einsum('bapt,batm->bapm', masks.astype(np.int16), counts[:, condition])
        ps[:, j] = np.einsum('bapt,batm->bapm', masks.astype(float), sums[:, condition])
        check('partition', 'counts close', np.array_equal(pc[:, j].sum(axis=-2), counts[:, condition, :, tau-1:].sum(axis=-2)))
        check('partition', 'fixed exposure', np.all(pc[:, j, :, :, 0].sum(axis=-1) == 101-tau))
        check('partition', 'first-answer timing', np.all(pc[:, j, :, 1, 1] == 0)
              and np.array_equal(pc[:, j, :, 1, 0], pc[:, j, :, 1, 2])
              and np.array_equal(pc[:, j, :, 0, 0], first[:, j]-tau))
        wi = M.BOUNDARIES.index(tau)
        units = (10*pc[:, j, :, :, 1]+pc[:, j, :, :, 2]).sum(axis=-1)
        old = 10*original['window_wrong'][:, condition, :, wi:]+original['window_references'][:, condition, :, wi:]
        check('bridge', 'window/phase units', np.array_equal(units, old.sum(axis=-1)))
        if condition:
            check('bridge', 'first post-change purchase', np.array_equal(first[:, j], original['first_post_reference'][:, condition]))
            for ai, key in ((5, 'c2_extra_references'), (6, 'extra_references')):
                check('bridge', 'post/after extra purchases '+key,
                      np.array_equal(pc[:, j, ai, :, 3].sum(axis=-1), original[key][:, condition, 1])
                      and np.array_equal(pc[:, j, ai, 2, 3], original[key][:, condition, 2]))
    check('risk', 'phase regret identity', np.allclose(ps[..., 0]-ps[..., 1], ps[..., 2:5].sum(axis=-1), atol=5e-13, rtol=0))
    check('risk', 'same total floor for every arm', np.allclose(ps[..., 1].sum(axis=-1), ps[..., 1].sum(axis=-1)[:, :, :1], atol=5e-13, rtol=0))
    arrays = dict(indices=np.array(indices, dtype=np.int16), first_query=first, phase_counts=pc, phase_sums=ps,
                  whole_units=(10*original['wrong']+original['references']).astype(np.int16))
    return arrays, dict(original_fingerprint=original_fingerprint, original_arrays=len(original),
        wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu, checks=dict(CHECKS), cpus=sorted(os.sched_getaffinity(0)))


def worker(job):
    meta, indices, prefix, output, bridge = job
    arrays, record = replay(meta, indices, prefix, bridge)
    record.update(label=meta['label'], first=indices[0], last=indices[-1], fingerprint=M.fingerprint(arrays))
    if output:
        path = Path(output)/'blocks'/f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record['record'] = M.identity(path)
    return record


def ci(values):
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[None, :]
    check('aggregation', 'stratified matrix', values.ndim == 2 and values.shape[1] > 1)
    bases, n = values.shape
    mean = float(values.mean())
    se = float(np.sqrt(values.var(axis=1, ddof=1).sum()/(bases*bases*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def stats_int(num, den, offset=0):
    result = ci(num/den)
    mean = int(num.sum())/(num.size*den)+offset
    result.update(mean=mean, lower95=mean-1.96*result['mc_se'], upper95=mean+1.96*result['mc_se'])
    return result


def arm_summary(num, den, offset=0):
    return dict(arms={arm: stats_int(num[:, :, j], den, offset) for j, arm in enumerate(ARMS)},
        contrasts={'C3_minus_'+arm: stats_int(num[:, :, 6]-num[:, :, j], den) for j, arm in enumerate(ARMS[:6])},
        C3_minus_always=stats_int(num[:, :, 6], den, offset-.1))


def same_tree(value, reference):
    if isinstance(reference, dict):
        check('bridge', 'tree keys', value.keys() == reference.keys())
        for key in reference:
            same_tree(value[key], reference[key])
    elif isinstance(reference, float):
        check('bridge', 'original aggregate', abs(value-reference) < 2e-13)
    else:
        check('bridge', 'original value', value == reference)


def metric_arrays(counts, sums):
    c = np.concatenate((counts, counts.sum(axis=-2, keepdims=True)), axis=-2)
    s = np.concatenate((sums, sums.sum(axis=-2, keepdims=True)), axis=-2)
    length = np.array([101-t for _, t in ANCHORS])[None, None, :, None, None]
    exposure, wrong, references, extra = (c[..., i]/length for i in range(4))
    cost = wrong+references/10
    for name, value in [('exposure', exposure), ('wrong_cost', wrong), ('reference_cost', references/10),
                        ('extra_reference_rate', extra), ('cost', cost), ('excess_always', cost-.1*exposure)]:
        yield name, value
    for i, name in enumerate(SUMS):
        yield name, s[..., i]/length
    yield 'conditional_regret', s[..., 2:5].sum(axis=-1)/length
    yield 'realization_residual', cost-s[..., 0]/length
    yield 'risk_underestimate', (s[..., 0]-s[..., 5])/length
    yield 'available_headroom', .1*exposure-s[..., 1]/length
    yield 'planning_immediate_effect', (s[..., 0]-s[..., 6])/length
    yield 'subjective_immediate_premium', (s[..., 5]-s[..., 7])/length


def analyze(rows, pop, prior=None):
    c, s = rows['phase_counts'], rows['phase_sums']
    weights = A.weights()
    groups = {g: dict(arms={arm: {phase: {} for phase in PHASES} for arm in ARMS},
        contrasts={'C3_minus_'+arm: {phase: {} for phase in PHASES} for arm in ARMS[:6]},
        query={arm: {} for arm in ARMS}) for g in weights}
    conditions = {f'{m["label"]}__{name}': dict(base=m['label'], anchor=name, analysis_tau=ANCHORS[j][1],
        original_condition=M.CONDITIONS[ANCHORS[j][0]], arms={arm: {phase: {} for phase in PHASES} for arm in ARMS},
        query={arm: {} for arm in ARMS}) for m in pop for j, name in enumerate(A.ANCHOR_NAMES)}
    for metric, values in metric_arrays(c, s):
        for g, w in weights.items():
            v = np.einsum('k,brkap->brap', w, values)
            for ai, arm in enumerate(ARMS):
                for pi, phase in enumerate(PHASES):
                    groups[g]['arms'][arm][phase][metric] = ci(v[:, :, ai, pi])
                    if ai < 6:
                        groups[g]['contrasts']['C3_minus_'+arm][phase][metric] = ci(v[:, :, 6, pi]-v[:, :, ai, pi])
        for bi, meta in enumerate(pop):
            for j, name in enumerate(A.ANCHOR_NAMES):
                row = conditions[f'{meta["label"]}__{name}']
                for ai, arm in enumerate(ARMS):
                    for pi, phase in enumerate(PHASES):
                        row['arms'][arm][phase][metric] = ci(values[bi, :, j, ai, pi])
    query = dict(purchase_probability=(rows['first_query'] < 101).astype(float), waiting_tasks=c[:, :, :, :, 0, 0].astype(float))
    for name, values in query.items():
        for g, w in weights.items():
            v = np.einsum('k,brka->bra', w, values)
            for ai, arm in enumerate(ARMS):
                groups[g]['query'][arm][name] = ci(v[:, :, ai])
        for bi, meta in enumerate(pop):
            for j, anchor in enumerate(A.ANCHOR_NAMES):
                for ai, arm in enumerate(ARMS):
                    conditions[f'{meta["label"]}__{anchor}']['query'][arm][name] = ci(values[bi, :, j, ai])
    # Independent known-law expectation, without using sampled warning counts.
    floors = []
    for meta in pop:
        values = []
        for j, (condition, tau) in enumerate(ANCHORS):
            family = M.CONDITIONS[condition][0]
            q = tuple(map(F, meta['laws'][{'stable': 0, 'A_loss': 1, 'B_loss': 2, 'reverse': 3}[family]]))
            floor = sum(min(q[y]/2, q[y ^ 3]/2, (q[y]+q[y ^ 3])/20) for y in range(4))
            check('floor', 'within always-check floor', 0 <= floor <= F(1, 10))
            values.append(floor)
            conditions[f'{meta["label"]}__{A.ANCHOR_NAMES[j]}']['analytic_floor'] = dict(
                rational=str(floor), mean=float(floor), headroom=float(F(1, 10)-floor), positive_headroom=floor < F(1, 10))
        floors.append(values)
    analytic = {}
    for group, w in weights.items():
        exact = sum(F(float(wj)).limit_denominator(18)*floors[b][j] for b in range(len(pop)) for j, wj in enumerate(w))/len(pop)
        selected = [floors[b][j] for b in range(len(pop)) for j, wj in enumerate(w) if wj]
        analytic[group] = dict(rational_floor=str(exact), floor=float(exact), headroom=float(F(1, 10)-exact),
            analysis_rows=len(selected), positive_headroom_rows=sum(v < F(1, 10) for v in selected), zero_headroom_rows=sum(v == F(1, 10) for v in selected))
    units = rows['whole_units'].astype(np.int64)
    pc = c[:, :, 3:].sum(axis=-2).astype(np.int64)
    post = np.concatenate((np.zeros_like(units[:, :, :1]), 10*pc[..., 1]+pc[..., 2]), axis=2)
    episode, post_groups = {}, {}
    for g, w in zip(M.PROFILE_GROUPS, M.group_weights()):
        co = np.rint(18*w).astype(np.int64)
        episode[g] = arm_summary(np.einsum('k,brka->bra', co, units), 18000, .00064)
        if g not in ('full', 'stable'):
            post_groups[g] = arm_summary(np.einsum('k,brka->bra', co*np.array([0]+[2, 3, 6]*3), post), 27000)
            for arm in ARMS:
                same_tree(groups[g]['arms'][arm]['total']['cost'], post_groups[g]['arms'][arm])
    criteria = dict(economical_recovery=post_groups['changed']['C3_minus_always']['upper95'] < 0,
        overall_useful_function=episode['full']['C3_minus_always']['upper95'] < 0,
        value_of_longer_horizon=post_groups['changed']['contrasts']['C3_minus_C2']['upper95'] < 0)
    signs = {}
    for endpoint, data in (('episode', units), ('post_change', post)):
        signs[endpoint] = {}
        for ai, arm in enumerate(ARMS[:6]):
            all_ci = []
            for bi in range(len(pop)):
                for j, (family, tau) in enumerate(M.CONDITIONS):
                    if endpoint == 'post_change' and family == 'stable':
                        continue
                    den = 1000 if endpoint == 'episode' else 10*(101-tau)
                    all_ci.append(stats_int(data[bi, :, j, 6]-data[bi, :, j, ai], den))
            signs[endpoint][arm] = dict(point_lower=sum(v['mean'] < 0 for v in all_ci), point_equal=sum(v['mean'] == 0 for v in all_ci),
                point_higher=sum(v['mean'] > 0 for v in all_ci), upper_below_zero=sum(v['upper95'] < 0 for v in all_ci), lower_above_zero=sum(v['lower95'] > 0 for v in all_ci))
    if prior is not None:
        for current, original in ((episode, prior['episode']), (post_groups, prior['post_change']), (criteria, prior['criteria']), (signs, prior['condition_counts'])):
            same_tree(current, original)
    return dict(summary=dict(independent_blocks=units.shape[0]*units.shape[1], original_physical_conditions=len(pop)*10,
        analysis_rows=len(pop)*12, arms=list(ARMS), new_samples=0, new_policies=0,
        interpretation='retrospective unchanged-policy explanation; endogenous phases; immediate contrasts are not total causal effects',
        phases=list(PHASES), count_fields=list(COUNTS), sum_fields=list(SUMS), bayesian_reference='shared mathematical foundation and verification; distinctive advantage not required'),
        original_criteria=criteria, original_episode=episode, original_post_change=post_groups, original_condition_counts=signs,
        groups=groups, analytic_known_law=analytic, conditions=conditions)


def aggregate(output, pop):
    rows = {k: [] for k in FIELDS}
    for meta in pop:
        parts = []
        for first in range(0, 1024, 128):
            path = output/'blocks'/f'{meta["label"]}_{first:04d}_{first+127:04d}.npz'
            with np.load(path, allow_pickle=False) as d:
                check('aggregation', 'complete indices', np.array_equal(d['indices'], np.arange(first, first+128)))
                parts.append({k: d[k] for k in FIELDS})
        for key in FIELDS:
            rows[key].append(np.concatenate([p[key] for p in parts], axis=0))
    rows = {k: np.stack(v) for k, v in rows.items()}
    check('aggregation', 'full original cohort', rows['whole_units'].shape == (27, 1024, 10, 7))
    return analyze(rows, pop, json.loads((PREVIOUS/'RESULTS.json').read_text()))


def qualify(cpus):
    start = perf_counter()
    for tau in (1, 2, 4):
        for pattern in range(16):
            actions = np.array([2 if pattern & (1 << i) else 0 for i in range(4)])
            k, masks = A.phase_masks(actions, tau)
            expected_k = next((t for t in range(tau, 5) if actions[t-1] == 2), 5)
            expected = np.zeros((3, 4), dtype=bool)
            for t in range(tau, 5):
                expected[0 if t < expected_k else 1 if t == expected_k else 2, t-1] = True
            check('qualification', 'independent scalar partition', k == expected_k and np.array_equal(masks, expected))
    # Enumerate target/error paths with rational probabilities, independently
    # of the evaluator's warning-index formula, including both residual signs.
    for q in ((F(1, 4),)*4, tuple(F(x, 20) for x in (14, 2, 1, 3)),
              tuple(F(x, 20) for x in (1, 1, 1, 17)), tuple(F(x, 20) for x in (9, 9, 1, 1))):
        integrated = F(0)
        for y in range(4):
            den = sum(q[e]/2 for w in (0, 1) for e in range(4) if e ^ (3*w) == y)
            p = sum(q[e]/2 for e in range(4) if e ^ 3 == y)/den
            integrated += den*min(p, 1-p, F(1, 10))
            for action in range(3):
                for myopic in range(3):
                    for target in (0, 1):
                        a, m = np.array([[[action]]]), np.array([[[myopic]]])
                        c, s = task_terms(a, m, np.array([[[.3]]]), np.array([[y]]),
                            np.array([[target]]), np.array([[[float(x) for x in q]]]))
                        cost = F(1, 10) if action == 2 else p if action == 0 else 1-p
                        mc = F(1, 10) if myopic == 2 else p if myopic == 0 else 1-p
                        posterior = F(7, 10) if y >> 1 else F(3, 10)
                        sc = F(1, 10) if action == 2 else posterior if action == 0 else 1-posterior
                        sm = F(1, 10) if myopic == 2 else posterior if myopic == 0 else 1-posterior
                        check('qualification', 'rational physical and myopic risks', abs(s[0, 0, 0, 0]-float(cost)) < 2e-15 and abs(s[0, 0, 0, 6]-float(mc)) < 2e-15)
                        check('qualification', 'prelabel subjective orientation', abs(s[0, 0, 0, 5]-float(sc)) < 2e-15 and abs(s[0, 0, 0, 7]-float(sm)) < 2e-15)
                        check('qualification', 'rational floor and regret', abs(s[0, 0, 0, 1]-float(min(p, 1-p, F(1, 10)))) < 2e-15
                              and abs(s[0, 0, 0, 2:5].sum()-float(cost-min(p, 1-p, F(1, 10)))) < 2e-15)
                        check('qualification', 'integer events', c[0, 0, 0, 1] == (action != 2 and action != target)
                              and c[0, 0, 0, 3] == (action == 2 and myopic != 2))
        check('qualification', 'analytic integrated known-law floor', integrated == M.floor(q))
    meta, indices = A.synthetic(), list(range(8))
    prefix = 'qualification-fep-c3-recovery-audit-v1'
    original, _ = T.run_batch(meta, indices, prefix)
    arrays, record = replay(meta, indices, prefix, False)
    check('qualification', 'complete trace invariance', record['original_fingerprint'] == M.fingerprint(original))
    check('qualification', 'all wrappers restored', M.Filter is BASE_FILTER and B.choose_future is BASE_FUTURE
          and T.choose_three is BASE_THREE and not TracedFilter.instances)
    synthetic_result = analyze({k: arrays[k][None] for k in FIELDS}, [meta])
    check('qualification', 'complete synthetic aggregate schema', len(synthetic_result['conditions']) == 12
          and synthetic_result['summary']['independent_blocks'] == 8 and len(synthetic_result['groups']) == 12)
    check('qualification', 'myopic control planning effects zero', all(
        synthetic_result['groups'][g]['arms'][a]['total']['planning_immediate_effect']['mean'] == 0
        for g in synthetic_result['groups'] for a in ARMS[:5]))
    x = np.arange(1024, dtype=float)[None, :]+np.arange(27)[:, None]
    check('qualification', 'paired SE', ci((x+2)-x)['mc_se'] == 0 and ci((x+2)-x)['mean'] == 2)
    check('qualification', 'stratified SE', abs(ci(x)['mc_se']-np.sqrt(np.var(np.arange(1024), ddof=1)/(27*1024))) < 1e-14)
    check('qualification', 'integer mean ties', stats_int(np.array([3, -3]), 10)['mean'] == 0)
    jobs = [(meta, list(range(2*i, 2*i+2)), prefix, None, False) for i in range(4)]
    one = [worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        four = list(pool.map(worker, jobs))
    for a, b in zip(one, four):
        check('qualification', 'one/four worker equality', a['fingerprint'] == b['fingerprint'] and a['original_fingerprint'] == b['original_fingerprint'])
    return dict(status='PASS', assertions=sum(CHECKS.values()), checks=dict(CHECKS), wall_seconds=perf_counter()-start,
        synthetic_only=True, original_arrays=len(original), one_four_worker_chunks=4,
        inherited_policy_qualification='C3 frozen 7031 assertions; not rerun or counted as new audit checks',
        numerical_reference='independent rational/scalar routes by the same author')


def mount_check(output):
    item = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('storage', 'external FEP mount', item['target'] == '/mnt/bioIce1' and item['source'] == '/dev/sdc1'
          and item['fstype'] == 'ext4' and output.parent == ROOT)
    s = os.statvfs('/mnt/bioIce1')
    free = s.f_bavail*s.f_frsize
    check('storage', 'adequate space', free > 2_000_000_000)
    return dict(mount=item, free_bytes=free)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output, 'PREPARE: one explanatory C3 audit; unchanged cohort and policies')
    check('integrity', 'original manifest', M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity', 'completed C3 report', M.identity(SOURCE/'FEP_THREE_DECISION_CHECKING_V1_REPORT.md')['sha256'] == REPORT_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = {r['path']: r for group in ('inputs', 'outputs', 'preserved') for r in prior[group]}
    extras = [PREVIOUS/'MANIFEST.json', SOURCE/'FEP_THREE_DECISION_CHECKING_V1_REPORT.md',
        SOURCE/'FEP_THREE_DECISION_CHECKING_V1_CHECKPOINT.md', SOURCE/'readback_fep_three_decision_checking.py',
        T.ROOT/'readback-2026-10-08/READBACK.json', T.ROOT/'readback-2026-10-08/VERIFIER.py']
    for path in extras:
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = [M.identity(SOURCE/name) for name in ('FEP_C3_RECOVERY_AUDIT_V1.md', 'check_fep_c3_recovery_audit.py')]
    for record in inputs:
        shutil.copyfile(record['path'], output/'inputs'/Path(record['path']).name)
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity', 'source snapshot match', sorted(r['sha256'] for r in inputs) == sorted(r['sha256'] for r in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources', 'four CPUs available', len(cpus) == 4)
    M.write(output/'PREPARATION.json', dict(started_utc=M.now(), inputs=inputs, source_snapshots=snapshots,
        preserved=list(preserved.values()), cpus=cpus, storage=storage, python=platform.python_version(), numpy=np.__version__,
        source_manifest=M.identity(PREVIOUS/'MANIFEST.json'), source_seeds=M.identity(PREVIOUS/'SEEDS.json'),
        source_population=M.identity(PREVIOUS/'POPULATION.json'), source_prefix=T.PREFIX, new_seeds=False,
        anchors=ANCHORS, phases=PHASES, count_fields=COUNTS, sum_fields=SUMS))
    M.logline(output, 'FROZEN: specification, wrapper, original seeds/population and inherited identities')
    M.pin_cpus(cpus)
    qualification = qualify(cpus)
    M.write(output/'QUALIFICATION.json', qualification)
    M.logline(output, f'QUALIFIED: {qualification["assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(A.synthetic(), list(range(i*32, (i+1)*32)), 'benchmark-fep-c3-recovery-audit-v1', None, False) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        records = list(pool.map(worker, jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*27648/128
    M.write(output/'BENCHMARK.json', dict(wall_seconds=elapsed, forecast_seconds=forecast, requires_detached=forecast > 600,
        workers=4, synthetic_blocks=128, records=records, rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output, f'PREPARED: forecast {forecast:.3f}s; detached={forecast > 600}; no main attribution outcomes')
    print(json.dumps(dict(qualification=qualification['assertions'], qualification_seconds=qualification['wall_seconds'],
        benchmark_seconds=elapsed, forecast_seconds=forecast, requires_detached=forecast > 600,
        preserved_identities=len(preserved))))


def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution', 'qualified', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'not previously started', not (output/'EXECUTION_STARTED.json').exists())
    check('execution', 'detachment rule', detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json', dict(started_utc=M.now(), pid=os.getpid(), detached=detached,
        cpus=prep['cpus'], workers=4, benchmark=M.identity(output/'BENCHMARK.json')))
    M.logline(output, 'AUDIT STARTED: 216 original chunks; every original array must match')
    pop = json.loads((PREVIOUS/'POPULATION.json').read_text())['bases']
    jobs = [(meta, list(range(i, i+128)), T.PREFIX, str(output), True) for meta in pop for i in range(0, 1024, 128)]
    records = []
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(prep['cpus'],)) as pool:
        for i, record in enumerate(pool.map(worker, jobs), 1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output, f'REPLAYED AND BRIDGED {i}/216 chunks; {record["label"]}')
    M.write(output/'WORKERS.json', records)
    M.logline(output, 'REPLAY COMPLETE: original arrays identical; aggregate all signed outcomes')
    results = aggregate(output, pop)
    M.write(output/'RESULTS.json', results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    M.verify([r['record'] for r in records])
    M.logline(output, f'COMPLETE: {perf_counter()-start:.3f}s; original criteria preserved; no new sample or policy')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json', dict(status='COMPLETE', started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
        finished_utc=M.now(), wall_seconds=perf_counter()-start, parent_cpu_seconds=process_time()-cpu,
        worker_cpu_seconds=sum(r['cpu_seconds'] for r in records), workers=4, cpus=prep['cpus'],
        python=platform.python_version(), numpy=np.__version__, inputs=prep['inputs'], preserved=prep['preserved'],
        outputs=outputs, summary=results['summary'], original_criteria=results['original_criteria'],
        checks=dict(CHECKS), identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch', 'prepared', (output/'BENCHMARK.json').is_file())
    check('launch', 'not launched', not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'execute', '--output', str(output), '--detached'],
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, cwd=SOURCE,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    record = dict(pid=child.pid, launched_utc=M.now(), automatic_polling=False, benchmark=M.identity(output/'BENCHMARK.json'))
    M.write(output/'LAUNCH.json', record)
    print(json.dumps(record))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'execute', 'launch'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    check('scope', 'new audit namespace', args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        if args.phase == 'prepare':
            prepare(args.output)
        elif args.phase == 'execute':
            execute(args.output, args.detached)
        else:
            launch(args.output)
    except Exception:
        if args.output.is_dir():
            failure = args.output/f'FAILURE_{args.phase}.json'
            if not failure.exists():
                M.write(failure, dict(phase=args.phase, utc=M.now(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
            M.logline(args.output, f'FAILED {args.phase}; preserve attempt; no automatic scientific rerun')
        raise


if __name__ == '__main__':
    main()
