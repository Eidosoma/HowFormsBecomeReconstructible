#!/usr/bin/env python3
"""A fixed paid-checking intervention; imported inference/planning stay frozen."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter, process_time
import traceback
import numpy as np
import run_fep_autonomous_reversal as C

SOURCE = Path(__file__).resolve().parent
ROOT = C.ROOT.parent/'fep-paid-checking-v1'
PREVIOUS = C.ROOT/'attempt-01'
SPEC = SOURCE/'FEP_PAID_CHECKING_V1.md'
READBACK = SOURCE/'readback_fep_paid_checking.py'
PREFIX = 'fep-paid-checking-v1'
ARMS = ('CT4-structured', 'CT4-structured-gap1')
BLOCKS, CHUNK, MAX_FORECAST = 32, 4, 7*86400
CONDITIONS, TAU, TIMES = C.CONDITIONS, C.TAU, C.TIMES
FIELDS = C.FIELDS+('audit_counts', 'predictive')
CHECKS = {}
write, digest, utc, resources = C.write, C.digest, C.utc, C.resources
FROZEN = {
    SOURCE/'fep_structured_reversal.py': '9ae8f36d2730d6885a5558cc0069fe6f2b614e279985831105233ec437a63f3b',
    SOURCE/'run_fep_autonomous_reversal.py': 'ca265d3d3392656165eedd410599d167ace16b588a52d5d3a2bc31f779be10e2',
    PREVIOUS/'FREEZE.json': 'baf6df858bb4688c04b86285a79de8238901a91100099fe50c0f4551c96aa216',
    PREVIOUS/'MANIFEST.json': '92ae729ed63faa44a5296e7525357feb9ccbf83936334d04bcb03058e45324f5',
    C.ROOT/'reporting-2026-10-17/CORRECTED_RESULTS.json': 'dc6d44925a905c43dc6e3212378fc9b489aa6abe11e507294103bb0ae9b07202',
    C.ROOT/'reporting-2026-10-17/ANALYSIS_READBACK.json': 'bb4aa132f9c2370416fc6a63dcfd786739e89ad34c21b53dc8a7bf91a04bdd9a',
    SOURCE/'FEP_AUTONOMOUS_REVERSAL_V1_REPORT.md': 'abb9b8f42854e6cf3282c5cc26025cd482362adaa4605dcc4c0ea768050eb83c',
    SOURCE/'FEP_AUTONOMOUS_REVERSAL_V1_CORRECTION.md': 'babf1c7c9d4ce7344ab8cfed582e746d9c3628ce3b50cf10f9a5f95dfd72e41b',
}


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def close(name, left, right, atol=3e-12):
    check(name, np.shape(left) == np.shape(right) and np.allclose(left, right, atol=atol, rtol=0))


def log(output, message):
    line = utc()+' '+message
    with (output/'RUN_LOG.txt').open('a') as stream:
        stream.write(line+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(line, flush=True)


def mount_check(output):
    mounted = json.loads(subprocess.check_output(
        ['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('external_mount', mounted == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'))
    check('output_namespace', output.resolve().parent == ROOT and output.name.startswith('attempt-'))
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('external_space', free > 2_000_000_000)
    return dict(mount=mounted, free_bytes=free)


def apply_rule(proposed, gap, enabled):
    """No warning, hidden target, law, onset or future observation enters this rule."""
    due = (gap >= 2) & enabled
    forced = due & (proposed != 2)
    return np.where(due, 2, proposed).astype(np.int8), due, forced


def simulate(meta, indices, prefix, steps=100, enabled=(False, True)):
    cal, y, truth, laws = C.physical(meta, indices, prefix)
    b, nc = len(indices), len(CONDITIONS)
    yy, targets = y.reshape(-1, 100), truth.reshape(-1, 100)
    shape = (b*nc, 2, steps)
    out = dict(calibration=cal, warnings=y, truth=truth, indices=np.array(indices))
    for key in ('actions', 'planned_actions', 'labels', 'gap_before'):
        out[key] = np.empty(shape, dtype=np.int16)
    for key in ('subjective_u', 'information'):
        out[key] = np.empty(shape)
    for key in ('extra', 'due', 'forced'):
        out[key] = np.empty(shape, dtype=bool)
    out['posterior'] = np.empty(shape+(2,))
    fallbacks = []
    for arm, use_rule in enumerate(enabled):
        learner = C.R.Filter(np.repeat(cal, nc, axis=0))
        last_paid = np.zeros(b*nc, dtype=np.int16)
        for t in range(1, steps+1):
            learner.start(t)
            u = learner.warning(yy[:, t-1])
            proposed, value, _, extra = learner.choose(steps=4)
            gap = t-last_paid
            action, due, forced = apply_rule(proposed, gap, use_rule)
            labels = np.where(action == 2, targets[:, t-1], -1).astype(np.int8)
            learner.retain(labels)
            last_paid = np.where(action == 2, t, last_paid)
            check('only_paid_labels_retained', np.array_equal(learner.labels[:, t-1], labels))
            close('posterior_normalized', learner.w.sum(axis=1), np.ones(len(last_paid)), 2e-13)
            check('finite_state', np.all(np.isfinite(learner.w)) and np.all(np.isfinite(u)))
            check('rule_gap_bound', not use_rule or np.all(t-last_paid <= 1))
            check('planned_extra_and_forced_disjoint', not np.any(extra & forced))
            check('information_nonnegative', np.all(value >= -2e-12))
            done = learner.times <= t
            posterior = np.column_stack((learner.w[:, done].sum(axis=1),
                                         learner.w[:, done & (learner.kinds == 3)].sum(axis=1)))
            values = dict(actions=action, planned_actions=proposed, labels=labels,
                          gap_before=gap, subjective_u=u, information=value, extra=extra,
                          due=due, forced=forced, posterior=posterior)
            for key, value in values.items():
                out[key][:, arm, t-1] = value
            if t == 100:
                check('terminal_information_zero', np.all(out['information'][:, arm, -1] == 0))
        fallbacks.append(learner.fallback)
    for key in ('actions', 'planned_actions', 'labels', 'gap_before', 'subjective_u',
                'information', 'extra', 'due', 'forced', 'posterior'):
        out[key] = out[key].reshape((b, nc)+out[key].shape[1:])
    out['fallbacks'] = np.array(fallbacks, dtype=np.int64)
    if steps == 100:
        out.update(account(out, laws))
    return out


def account(raw, laws):
    # Reuse only the qualified per-episode accounting, never the old pooled analyzer.
    out = C.account(raw, laws)
    y, u = raw['warnings'][:, :, None, :], raw['subjective_u']
    confident = np.isin(y, [0, 3]) & (np.minimum(u, 1-u) < .1)
    post = np.broadcast_to((TIMES[None, :] >= TAU[:, None])[:, None, :], u.shape)
    masks = (np.ones_like(post), post)
    audits = np.stack((raw['due'], raw['forced'], raw['forced'] & confident), axis=-1)
    out['audit_counts'] = np.stack([(audits*m[..., None]).sum(axis=-2) for m in masks], axis=-2)
    q = np.broadcast_to(laws, raw['warnings'].shape+(4,))
    qy = np.take_along_axis(q, raw['warnings'][..., None], axis=-1)[..., 0]
    qo = np.take_along_axis(q, (raw['warnings'] ^ 3)[..., None], axis=-1)[..., 0]
    p1 = (qo/(qy+qo))[:, :, None, :]
    predicted = np.where((y >> 1) != 0, 1-u, u)
    answer = (y >> 1) ^ (u > .5)
    direction = np.where(answer == 0, p1, 1-p1)-np.minimum(p1, 1-p1)
    pred = np.stack((np.ones_like(u), np.abs(predicted-p1), (direction > 1e-14), direction), axis=-1)
    first = out['first'][..., None]
    phases = (post & (TIMES < first), post & (TIMES == first), post & (TIMES > first))
    out['predictive'] = np.stack([(pred*m[..., None]).sum(axis=-2) for m in phases], axis=-2)
    close('predictive_phase_exposure', out['predictive'][..., 0], out['phase_counts'][..., 0], 0)
    return out


def worker(job):
    meta, indices, prefix, output, steps = job
    resources()
    CHECKS.clear(); C.CHECKS.clear()
    tick, cpu = perf_counter(), process_time()
    arrays = simulate(meta, indices, prefix, steps)
    record = dict(label=meta['label'], indices=indices, fingerprint=C.M.fingerprint(arrays),
                  wall_seconds=perf_counter()-tick, cpu_seconds=process_time()-cpu,
                  affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                  threads=len(list(Path('/proc/self/task').iterdir())),
                  fallback=arrays['fallbacks'].tolist(), checks=dict(CHECKS), accounting_checks=dict(C.CHECKS))
    check('single_worker_thread', record['threads'] == 1)
    if output:
        name = f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        path = Path(output)/'blocks'/name
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record.update(file='blocks/'+name, sha256=digest(path), bytes=path.stat().st_size)
    return record


def ci(x):
    check('interval_base_block_axes', x.ndim == 2 and x.shape[1] > 1)
    b, n = x.shape
    mean = float(x.mean())
    se = float(np.sqrt(x.var(axis=1, ddof=1).sum()/(b*b*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def panel(x):
    check('panel_base_block_arm_axes', x.ndim == 3 and x.shape[2] == 2)
    return dict(arms={arm: ci(x[..., a]) for a, arm in enumerate(ARMS)},
                gap1_minus_baseline=ci(x[..., 1]-x[..., 0]),
                against_always={arm: ci(x[..., a]-.1) for a, arm in enumerate(ARMS)})


def cost_values(counts, selected, segment):
    c = np.take(np.take(counts, segment, axis=4), selected, axis=2)
    b, n = counts.shape[:2]
    check('selected_count_axes', c.shape == (b, n, len(selected), 2, 3))
    check('positive_selected_exposure', np.all(c[..., 0] > 0))
    x = ((10*c[..., 1]+c[..., 2])/(10*c[..., 0])).mean(axis=2)
    check('averaged_cost_axes', x.shape == (b, n, 2))
    return x


def floor(q):
    q = [C.F(x) for x in q]
    return sum((q[y]+q[y ^ 3])/2 * min(C.F(1, 10), q[y]/(q[y]+q[y ^ 3]),
                                         q[y ^ 3]/(q[y]+q[y ^ 3])) for y in range(4))


def analyze(data, pop):
    counts = data['counts']
    b, n = counts.shape[:2]
    check('aggregate_axes', counts.shape == (len(pop), n, 25, 2, 2, 3))
    result = dict(arms=ARMS, blocks_per_base=n, independent_blocks=b*n,
                  physical_episodes=b*n*25, policy_decisions=b*n*25*2*100,
                  panels={}, diagnostics={}, conditions=[], harms={}, criteria={})
    for name, selected in C.panels().items():
        result['panels'][name] = {}
        taken = {k: np.take(data[k], selected, axis=2) for k in FIELDS}
        c = taken['counts']
        diag = {arm: {} for arm in ARMS}
        for seg, segment in enumerate(('episode', 'post_change')):
            if name == 'stable' and seg:
                continue
            rates = cost_values(counts, selected, seg)
            result['panels'][name][segment] = panel(rates)
            for a, arm in enumerate(ARMS):
                exposure = c[..., a, seg, 0]
                errors = (c[..., a, seg, 1]/exposure).mean(axis=2)
                paid = (c[..., a, seg, 2]/(10*exposure)).mean(axis=2)
                close('cost_components_close', errors+paid, rates[..., a])
                covariance = ((errors-errors.mean(axis=1)[:, None])*(paid-paid.mean(axis=1)[:, None])).sum(axis=1)/(n-1)
                close('cost_variance_closure', rates[..., a].var(axis=1, ddof=1),
                      errors.var(axis=1, ddof=1)+paid.var(axis=1, ddof=1)+2*covariance)
                d = dict(error_cost=ci(errors), purchase_cost=ci(paid),
                         count_totals=c[..., a, seg, :].sum(axis=(0, 1, 2)).tolist(),
                         audit_totals=taken['audit_counts'][..., a, seg, :].sum(axis=(0, 1, 2)).tolist(),
                         confident_agreement_totals=taken['confident_agreement'][..., a, seg, :].sum(axis=(0, 1, 2)).tolist(),
                         extra_ct4_purchases=int(taken['extra_counts'][..., a, seg].sum()))
                for k, metric in enumerate(C.SUMS):
                    d[metric] = ci((taken['sums'][..., a, seg, k]/exposure).mean(axis=2))
                d['forced_purchase_fraction'] = ci((taken['audit_counts'][..., a, seg, 1]/exposure).mean(axis=2))
                diag[arm][segment] = d
        for a, arm in enumerate(ARMS):
            d = diag[arm]
            d['alarm_episode_fraction'] = ci((taken['alarm'][..., a, 0] > 0).mean(axis=2))
            d['alarm_tasks'] = ci(taken['alarm'][..., a, 0].mean(axis=2))
            for k, key in enumerate(('final_change_mass', 'final_reversal_mass')):
                d[key] = ci(taken['posterior_final'][..., a, k].mean(axis=2))
            if name == 'stable':
                continue
            onsets = np.take(TAU, selected)
            lengths = 101-onsets
            first = taken['first'][..., a]
            d['no_post_purchase_fraction'] = ci((first == 101).mean(axis=2))
            d['capped_first_purchase_delay'] = ci((first-onsets).mean(axis=2))
            d['phases'] = {}
            for p, phase in enumerate(('before_first', 'at_first', 'after_first')):
                pc = taken['phase_counts'][..., a, p, :]
                cost = ((10*pc[..., 1]+pc[..., 2])/(10*lengths)).mean(axis=2)
                excess = ((10*pc[..., 1]+pc[..., 2]-pc[..., 0])/(10*lengths)).mean(axis=2)
                pd = dict(count_totals=pc.sum(axis=(0, 1, 2)).tolist(),
                          realized_cost_contribution=ci(cost), excess_over_always=ci(excess))
                for k, metric in enumerate(C.SUMS):
                    pd[metric] = ci((taken['phase_sums'][..., a, p, k]/lengths).mean(axis=2))
                pr = taken['predictive'][..., a, p, :].sum(axis=(0, 1, 2))
                pd['predictive_totals'] = pr.tolist()
                pd['predictive_task_means'] = (pr[1:]/pr[0]).tolist() if pr[0] else None
                d['phases'][phase] = pd
            close('phase_cost_mean_closure', sum(p['realized_cost_contribution']['mean'] for p in d['phases'].values()),
                  result['panels'][name]['post_change']['arms'][arm]['mean'])
        result['diagnostics'][name] = diag
    for bi, meta in enumerate(pop):
        for j, (family, onset) in enumerate(CONDITIONS):
            row = dict(base=meta['label'], family=family, onset=onset,
                       episode=panel(cost_values(counts[bi:bi+1], [j], 0)))
            law = 0 if not j else 1+C.U.FAMILIES.index(family)
            f = floor(meta['laws'][law])
            row.update(known_law_floor=float(f), known_law_floor_exact=str(f), zero_headroom=f == C.F(1, 10))
            if j:
                row['post_change'] = panel(cost_values(counts[bi:bi+1], [j], 1))
            result['conditions'].append(row)
    for name in ('reverse', 'core'):
        p = result['panels'][name]['post_change']
        relative = p['gap1_minus_baseline']['upper95'] < 0
        absolute = p['against_always'][ARMS[1]]['upper95'] < 0
        result['criteria'][name] = dict(better_than_baseline=relative, below_always=absolute, both=relative and absolute)
    result['reversal_onsets'] = {str(t): panel(cost_values(counts, [CONDITIONS.index(('reverse', t))], 1))
                                 for t in C.U.UNEXPECTED}
    for segment in ('episode', 'post_change'):
        rows = [r for r in result['conditions'] if segment in r]
        result['harms'][segment] = {
            'point_higher': [dict(base=r['base'], family=r['family'], onset=r['onset'], **r[segment]['gap1_minus_baseline'])
                             for r in rows if r[segment]['gap1_minus_baseline']['mean'] > 0],
            'point_lower': sum(r[segment]['gap1_minus_baseline']['mean'] < 0 for r in rows),
            'point_equal': sum(r[segment]['gap1_minus_baseline']['mean'] == 0 for r in rows),
            'interval_lower_above_zero': sum(r[segment]['gap1_minus_baseline']['lower95'] > 0 for r in rows)}
    return result


def load_counts(output, pop):
    rows = {k: [] for k in FIELDS}
    for meta in pop:
        parts = {k: [] for k in FIELDS}
        for first in range(0, BLOCKS, CHUNK):
            path = output/'blocks'/f'{meta["label"]}_{first:04d}_{first+CHUNK-1:04d}.npz'
            with np.load(path, allow_pickle=False) as saved:
                check('chunk_indices', np.array_equal(saved['indices'], np.arange(first, first+CHUNK)))
                for key in FIELDS:
                    parts[key].append(saved[key])
        for key in FIELDS:
            rows[key].append(np.concatenate(parts[key]))
    return {k: np.stack(v) for k, v in rows.items()}


def check_inputs(output):
    frozen = json.loads((output/'FREEZE.json').read_text())
    for path, expected in frozen['inputs'].items():
        check('frozen_input', digest(path) == expected)
    for name, expected in frozen['snapshots'].items():
        check('source_snapshot', digest(output/'inputs'/name) == expected)
    return frozen


def qualify(output):
    import readback_fep_paid_checking as V
    tick = perf_counter()
    CHECKS.clear(); V.CHECKS.clear()
    check('previous_exact_model_qualified', json.loads((C.PREVIOUS/'QUALIFICATION.json').read_text())['passed'])
    proposed = np.array([0, 1, 2, 0, 1, 2])
    gaps = np.array([1, 1, 1, 2, 2, 2])
    actual, due, forced = apply_rule(proposed, gaps, True)
    close('rule_truth_table_actions', actual, [0, 1, 2, 2, 2, 2], 0)
    close('rule_truth_table_due', due, [0, 0, 0, 1, 1, 1], 0)
    close('rule_truth_table_forced', forced, [0, 0, 0, 1, 1, 0], 0)
    close('disabled_rule_identity', apply_rule(proposed, gaps, False)[0], proposed, 0)
    last = 0
    sequence = []
    for t in range(1, 101):
        a, _, _ = apply_rule(np.array([0]), np.array([t-last]), True)
        if a[0] == 2:
            last = t
        sequence.append(int(a[0]))
    check('clock_initialization_and_terminal', sequence == [0, 2]*50)
    # Batched versus individually maintained histories, including actual overrides.
    counts = np.array([[58, 3, 3, 0], [20, 4, 8, 32], [16, 16, 16, 16]])
    for enabled in (False, True):
        batch = C.R.Filter(counts)
        scalar = [C.R.Filter(c[None, :]) for c in counts]
        last = np.zeros(3, dtype=int)
        slast = [0, 0, 0]
        for t in range(1, 13):
            y = np.array([(t+2*i) % 4 for i in range(3)], dtype=np.int8)
            target = np.array([(t+i) % 2 for i in range(3)])
            batch.start(t); u = batch.warning(y)
            p, value, _, extra = batch.choose(4)
            a, _, _ = apply_rule(p, t-last, enabled)
            for i, f in enumerate(scalar):
                f.start(t); su = f.warning(y[i:i+1])
                sp, sv, _, se = f.choose(4)
                # Independently coded scalar rule.
                sa = 2 if enabled and t-slast[i] >= 2 else int(sp[0])
                check('scalar_actions', sa == a[i] and sp[0] == p[i] and se[0] == extra[i])
                close('scalar_predictions', [su[0], sv[0]], [u[i], value[i]], 2e-13)
                f.retain(np.array([target[i] if sa == 2 else -1]))
                if sa == 2:
                    slast[i] = t
            batch.retain(np.where(a == 2, target, -1))
            last = np.where(a == 2, t, last)
            for i, f in enumerate(scalar):
                close('scalar_beliefs', batch.w[i], f.w[0], 2e-14)
                close('scalar_sufficient_statistics', batch.p[i], f.p[0], 0)
        for t in range(13, 101):
            batch.start(t); batch.warning(np.full(3, t % 4, dtype=np.int8))
            if t < 100:
                batch.retain(np.full(3, -1, dtype=np.int8))
        four, one = batch.choose(4), batch.choose(1)
        close('terminal_ct4_truncation', four[0], one[0], 0)
        check('terminal_information_zero', np.all(four[1] == 0))
    synthetic = C.S.extend_meta(C.S.A.synthetic())
    raw = simulate(synthetic, [0, 1], 'qualification-'+PREFIX)
    prior = C.simulate(synthetic, [0, 1], 'qualification-'+PREFIX, steps=8)
    for key in ('actions', 'labels', 'subjective_u', 'information', 'extra', 'posterior'):
        close('unchanged_structured_evaluator_'+key, raw[key][:, :, 0, :8], prior[key][:, :, 1], 2e-13)
    off = simulate(synthetic, [2], 'qualification-'+PREFIX, steps=8, enabled=(False, False))
    for key in ('actions', 'planned_actions', 'labels', 'subjective_u', 'posterior', 'information', 'gap_before'):
        close('disabled_rule_two_arm_identity_'+key, off[key][:, :, 0], off[key][:, :, 1], 0)
    with (output/'QUALIFICATION_TRACES.npz').open('xb') as stream:
        np.savez_compressed(stream, **raw)
    rebuilt = V.rebuild(raw, synthetic)
    for key in FIELDS:
        close('independent_synthetic_accounting_'+key, raw[key], rebuilt[key])
    # Complete report exercise on synthetic blocks; no main observations.
    fixture = {key: np.stack([value]*3) for key, value in rebuilt.items()}
    fixture_pop = [dict(synthetic, label='synthetic-fixture-'+str(i)) for i in range(3)]
    V.verify_results(analyze(fixture, fixture_pop), fixture, fixture_pop)
    V.qualify_axes()
    jobs = [(synthetic, [i], 'parallel-'+PREFIX, None, 8) for i in range(4)]
    accumulated, accounting = dict(CHECKS), dict(C.CHECKS)
    serial = [worker(j) for j in jobs]
    CHECKS.clear(); CHECKS.update(accumulated)
    C.CHECKS.clear(); C.CHECKS.update(accounting)
    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(worker, jobs))
    for left, right in zip(serial, parallel):
        check('serial_four_worker_fingerprint', left['fingerprint'] == right['fingerprint'])
    return dict(passed=True, seconds=perf_counter()-tick, checks=dict(CHECKS),
                accounting_checks=dict(C.CHECKS), independent_readback_checks=dict(V.CHECKS),
                previous_model_qualification_sha256=digest(C.PREVIOUS/'QUALIFICATION.json'),
                parallel_records=parallel)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir(); (output/'blocks').mkdir()
    log(output, 'PREPARE: fixed structured model; one paid gap rule; 864 fresh paired blocks')
    for path, expected in FROZEN.items():
        check('previous_frozen_input', digest(path) == expected)
    prior = json.loads((PREVIOUS/'FREEZE.json').read_text())
    identities = dict(prior['inputs'])
    for path, expected in identities.items():
        check('previous_frozen_dependency', digest(path) == expected)
    for path in (SPEC, Path(__file__).resolve(), READBACK, *FROZEN):
        identities[str(path)] = digest(path)
    pop = json.loads(C.POP_SOURCE.read_text())['bases']
    check('unchanged_population', pop == C.S.population() and len(pop) == 27)
    write(output/'POPULATION.json', dict(bases=pop, conditions=CONDITIONS, arms=ARMS, blocks_per_base=BLOCKS,
                                        chunk=CHUNK, policy_horizon=4, maximum_unlabelled_gap=1,
                                        total_policy_decisions=4320000))
    seeds = {m['label']: [str(C.M.seed_for(m['label'], i, PREFIX)) for i in range(BLOCKS)] for m in pop}
    flips = {m['label']: [str(C.M.seed_for(m['label'], i, PREFIX+'-transfer-flips')) for i in range(BLOCKS)] for m in pop}
    fresh = {x for group in (seeds, flips) for row in group.values() for x in row}
    check('unique_main_seeds', len(fresh) == 2*27*BLOCKS)
    seed_paths = sorted(ROOT.parent.glob('*/attempt-*/SEEDS.json'))
    for path in seed_paths:
        if path.parent == output:
            continue
        old = json.loads(path.read_text())
        earlier = {str(x) for group in ('blocks', 'flip_blocks') for row in old.get(group, {}).values() for x in row}
        check('separate_prior_seeds', not fresh.intersection(earlier))
        identities[str(path)] = digest(path)
    synthetic = C.S.A.synthetic()['label']
    test_seeds = {str(C.M.seed_for(synthetic, i, purpose+PREFIX+suffix))
                  for purpose in ('qualification-', 'parallel-', 'benchmark-')
                  for i in range(16) for suffix in ('', '-transfer-flips')}
    check('separate_synthetic_seeds', not fresh.intersection(test_seeds) and len(test_seeds) == 96)
    write(output/'SEEDS.json', dict(root=C.M.ROOT_SEED, main_prefix=PREFIX, blocks=seeds, flip_blocks=flips,
                                   rng='Python random.Random MT19937', core_draw_order=C.M.streams.__doc__,
                                   flip_draw_order='two random() per task, independent flips at probability .25',
                                   qualification_prefix='qualification-'+PREFIX, parallel_prefix='parallel-'+PREFIX,
                                   benchmark_prefix='benchmark-'+PREFIX, previous_seed_manifests=len(seed_paths),
                                   no_old_outcomes_pooled=True))
    for name in ('POPULATION.json', 'SEEDS.json'):
        identities[str(output/name)] = digest(output/name)
    snapshots = {}
    for path in (SPEC, Path(__file__).resolve(), READBACK):
        shutil.copyfile(path, output/'inputs'/path.name)
        snapshots[path.name] = digest(path)
    write(output/'FREEZE.json', dict(created=utc(), inputs=identities, snapshots=snapshots,
                                     cpus=sorted(os.sched_getaffinity(0)), storage=storage,
                                     python=platform.python_version(), numpy=np.__version__,
                                     blocks=27*BLOCKS, main_prefix=PREFIX, no_main_outcomes_generated=True))
    log(output, 'FROZEN: source identities, gap=1, population, seeds, endpoints and sample size')
    qualification = qualify(output)
    write(output/'QUALIFICATION.json', qualification)
    log(output, f'QUALIFIED: {qualification["seconds"]:.2f}s; policy, masks, accounting and scalar interval checks passed')
    synthetic = C.S.extend_meta(C.S.A.synthetic())
    jobs = [(synthetic, list(range(i*4, (i+1)*4)), 'benchmark-'+PREFIX, None, 100) for i in range(4)]
    tick = perf_counter()
    log(output, 'BENCHMARK: four workers, four synthetic blocks each, two structured policies')
    with ProcessPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(worker, jobs))
    elapsed = perf_counter()-tick
    forecast = 120+3*elapsed*(27*BLOCKS)/16
    write(output/'BENCHMARK.json', dict(wall_seconds=elapsed, forecast_seconds=forecast,
                                       requires_detached=forecast > 600, within_compute_bound=forecast <= MAX_FORECAST,
                                       maximum_forecast_seconds=MAX_FORECAST, rule='120 + 3 * wall * 864 / 16', records=records))
    check_inputs(output)
    log(output, f'PREPARED: conservative forecast {forecast:.2f}s; bound passes={forecast <= MAX_FORECAST}; no main outcomes')


def execute(output, detached):
    frozen = check_inputs(output)
    mount_check(output)
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('qualified', qual['passed'])
    check('compute_bound', bench['within_compute_bound'])
    check('detachment_rule', detached or not bench['requires_detached'])
    check('not_started', not (output/'STARTED.json').exists())
    tick = perf_counter()
    write(output/'STARTED.json', dict(started=utc(), pid=os.getpid(), process_group=os.getpgrp(),
                                      detached=detached, workers=4, cpus=sorted(os.sched_getaffinity(0)),
                                      nice=os.getpriority(os.PRIO_PROCESS, 0), freeze_sha256=digest(output/'FREEZE.json'),
                                      qualification_sha256=digest(output/'QUALIFICATION.json'),
                                      benchmark_sha256=digest(output/'BENCHMARK.json')))
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(m, list(range(i, i+CHUNK)), PREFIX, str(output), 100)
            for m in pop for i in range(0, BLOCKS, CHUNK)]
    log(output, f'MAIN STARTED: {len(jobs)} fixed chunks; 21600 paired episodes; no automatic extension')
    records = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        pending = [pool.submit(worker, job) for job in jobs]
        for future in as_completed(pending):
            record = future.result()
            records.append(record)
            log(output, f'COMPLETED {len(records)}/{len(jobs)}: {record["file"]}; {record["wall_seconds"]:.2f}s')
    records.sort(key=lambda r: (r['label'], r['indices'][0]))
    write(output/'WORKERS.json', records)
    result = analyze(load_counts(output, pop), pop)
    result['fallbacks'] = np.sum([r['fallback'] for r in records], axis=0).tolist()
    write(output/'RESULTS.json', result)
    check_inputs(output)
    for r in records:
        check('saved_chunk_hash', digest(output/r['file']) == r['sha256'])
    log(output, 'MAIN COMPLETE: all fixed chunks saved; independent saved-data readback follows')
    outputs = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write(output/'MANIFEST.json', dict(status='COMPLETE', finished=utc(), wall_seconds=perf_counter()-tick,
                                       worker_cpu_seconds=sum(r['cpu_seconds'] for r in records),
                                       workers=4, cpus=frozen['cpus'], checks=dict(CHECKS), outputs=outputs))
    with (output/'READBACK_STDOUT.log').open('xb') as stream:
        subprocess.run([sys.executable, '-B', str(READBACK), '--output', str(output)],
                       cwd=SOURCE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, check=True)
    print('SAVED-DATA READBACK PASSED; study complete, no successor launched.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, default=ROOT/'attempt-01')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    resources()
    if args.mode == 'prepare' and args.output.exists():
        raise FileExistsError('Preserve the existing attempt; do not overwrite it.')
    try:
        if args.mode == 'prepare':
            prepare(args.output)
        else:
            bench = json.loads((args.output/'BENCHMARK.json').read_text())
            if not bench['within_compute_bound']:
                write(args.output/'FEASIBILITY_STOP.json', dict(utc=utc(), status='STOPPED_BEFORE_MAIN', benchmark=bench))
                return
            execute(args.output, args.detached)
    except BaseException:
        if args.output.exists():
            failure = args.output/('FAILURE-'+args.mode+'.json')
            if not failure.exists():
                write(failure, dict(utc=utc(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
        raise


if __name__ == '__main__':
    main()
