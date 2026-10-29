#!/usr/bin/env python3
"""Fresh paired recovery comparison: previous hybrid versus planned checking."""
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
import run_fep_paid_checking as P
import fep_planned_recovery_policy as K
import fep_planned_checking as A

C = P.C
SOURCE = Path(__file__).resolve().parent
ROOT = P.ROOT.parent/'fep-planned-recovery-v1'
PREVIOUS = ROOT.parent/'fep-planned-checking-v1/attempt-01'
SPEC = SOURCE/'FEP_PLANNED_RECOVERY_V1.md'
POLICY = SOURCE/'fep_planned_recovery_policy.py'
READBACK = SOURCE/'readback_fep_planned_recovery.py'
PREFIX = 'fep-planned-recovery-v1'
ARMS = ('CT4-structured-gap1', 'CT4-structured-planned-gap1')
BLOCKS, CHUNK, MAX_FORECAST = 32, 4, 7*86400
CONDITIONS, TAU, TIMES = P.CONDITIONS, P.TAU, P.TIMES
FIELDS = P.FIELDS+('proposal_sums',)
CHECKS = {}
write, digest, utc, resources = P.write, P.digest, P.utc, P.resources
FROZEN = {
    SOURCE/'fep_structured_reversal.py': '9ae8f36d2730d6885a5558cc0069fe6f2b614e279985831105233ec437a63f3b',
    SOURCE/'run_fep_paid_checking.py': '0b6fc6d0de2b2023780350a48e7b55e22aaf34d706f8192379bd2128d1cb0d79',
    SOURCE/'readback_fep_paid_checking.py': '7b622a7913c2c6b50c8df70b059ed64ab9230092797d1ed1233efd90783fdb75',
    SOURCE/'FEP_PLANNED_CHECKING_V1_REPORT.md': 'd6545d33961c843688cc7c8e60bbaceaebeab22a0c1fba892109c3080cef26fa',
    PREVIOUS/'FREEZE.json': '13c7e7467a32731108e68a8c6a48594302465699ee33f04b737b692aca634140',
    PREVIOUS/'QUALIFICATION.json': '35a290a302e48ac7961f1e7591f298efd5b2a841cb38288099cbf3a954252afe',
    PREVIOUS/'MANIFEST.json': '246d47000e32d78cf3323d825cbad683384a456889bd6361114f6bc3c994ddab',
    PREVIOUS/'READBACK.json': '2821c924c99eb6095e1f2a6762d2e8aa2164aa6693f31e37ce0a270c46be759e',
    PREVIOUS.parent/'reporting-2026-10-18/REPORT_PROVENANCE.json': '3b5db3c5ef13c73205d96d7feb628b41570fcd958527ff17525d79283ad5ccc6',
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


def worker(job):
    meta, indices, prefix, output, steps = job
    resources()
    CHECKS.clear(); C.CHECKS.clear(); P.CHECKS.clear()
    tick, cpu = perf_counter(), process_time()
    arrays = simulate(meta, indices, prefix, steps)
    record = dict(label=meta['label'], indices=indices, fingerprint=C.M.fingerprint(arrays),
                  wall_seconds=perf_counter()-tick, cpu_seconds=process_time()-cpu,
                  affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                  threads=len(list(Path('/proc/self/task').iterdir())),
                  fallback=arrays['fallbacks'].tolist(), checks=dict(CHECKS), accounting_checks=dict(C.CHECKS), reused_checks=dict(P.CHECKS))
    check('single_worker_thread', record['threads'] == 1)
    if output:
        name = f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        path = Path(output)/'blocks'/name
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record.update(file='blocks/'+name, sha256=digest(path), bytes=path.stat().st_size)
    return record


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


def relabel(value, inverse=False):
    """Bijective schema adapter around the qualified paid-checking statistics."""
    names = {P.ARMS[0]: ARMS[0], P.ARMS[1]: ARMS[1],
             'gap1_minus_baseline': 'planned_minus_hybrid',
             'extra_ct4_purchases': 'extra_proposed_purchases',
             'better_than_baseline': 'better_than_hybrid'}
    if inverse:
        names = {v: k for k, v in names.items()}
    if isinstance(value, dict):
        return {names.get(k, k): relabel(v, inverse) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [relabel(v, inverse) for v in value]
    return names.get(value, value) if isinstance(value, str) else value


def simulate(meta, indices, prefix, steps=100):
    cal, y, truth, laws = C.physical(meta, indices, prefix)
    b, nc = len(indices), len(CONDITIONS)
    yy, targets = y.reshape(-1, 100), truth.reshape(-1, 100)
    shape = (b*nc, 2, steps)
    out = dict(calibration=cal, warnings=y, truth=truth, indices=np.array(indices),
               clock_scores=np.zeros((b*nc, steps, 2)), clock_fallback=np.zeros((b*nc, steps), dtype=bool))
    for key in ('actions', 'planned_actions', 'labels', 'gap_before'):
        out[key] = np.empty(shape, dtype=np.int16)
    for key in ('subjective_u', 'information', 'clock_benefit'):
        out[key] = np.empty(shape)
    for key in ('extra', 'due', 'forced'):
        out[key] = np.empty(shape, dtype=bool)
    out['posterior'] = np.empty(shape+(2,))
    fallbacks = []
    for arm, cls in enumerate((C.R.Filter, K.Clock)):
        learner = cls(np.repeat(cal, nc, axis=0))
        last_paid = np.zeros(b*nc, dtype=np.int16)
        for t in range(1, steps+1):
            learner.start(t)
            u = learner.warning(yy[:, t-1])
            if arm:
                planned = learner.choose_clock(steps=4)
                proposed, value, clock, extra = (planned[k] for k in ('proposed', 'information', 'clock_benefit', 'extra'))
                out['clock_scores'][:, t-1] = planned['scores']
                out['clock_fallback'][:, t-1] = planned['fallback_mask']
            else:
                proposed, value, _, extra = learner.choose(steps=4)
                clock = np.zeros(b*nc)
            gap = t-last_paid
            action, due, forced = P.apply_rule(proposed, gap, True)
            labels = np.where(action == 2, targets[:, t-1], -1).astype(np.int8)
            learner.retain(labels)
            last_paid = np.where(action == 2, t, last_paid)
            check('only_paid_labels_retained', np.array_equal(learner.labels[:, t-1], labels))
            close('posterior_normalized', learner.w.sum(axis=1), np.ones(len(last_paid)), 2e-13)
            check('finite_state', np.all(np.isfinite(learner.w)) and np.all(np.isfinite(u)))
            check('both_rule_gap_bounds', np.all(t-last_paid <= 1))
            check('planned_extra_and_binding_disjoint', not np.any(extra & forced))
            check('future_values_nonnegative', np.all(value >= -2e-12) and np.all(clock >= -2e-12))
            done = learner.times <= t
            posterior = np.column_stack((learner.w[:, done].sum(axis=1),
                                         learner.w[:, done & (learner.kinds == 3)].sum(axis=1)))
            values = dict(actions=action, planned_actions=proposed, labels=labels, gap_before=gap,
                          subjective_u=u, information=value, clock_benefit=clock, extra=extra,
                          due=due, forced=forced, posterior=posterior)
            for key, value in values.items():
                out[key][:, arm, t-1] = value
            if t == 100:
                check('terminal_information_zero', np.all(out['information'][:, arm, -1] == 0))
                check('terminal_clock_zero', np.all(out['clock_benefit'][:, arm, -1] == 0))
        fallbacks.append(learner.fallback)
    for key in ('actions', 'planned_actions', 'labels', 'gap_before', 'subjective_u',
                'information', 'clock_benefit', 'extra', 'due', 'forced', 'posterior'):
        out[key] = out[key].reshape((b, nc)+out[key].shape[1:])
    out['clock_scores'] = out['clock_scores'].reshape(b, nc, steps, 2)
    out['clock_fallback'] = out['clock_fallback'].reshape(b, nc, steps)
    out['fallbacks'] = np.array(fallbacks, dtype=np.int64)
    check('planned_fallback_record', int(out['clock_fallback'].sum()) == fallbacks[1])
    if steps == 100:
        out.update(P.account(out, laws))
        post = np.broadcast_to((TIMES[None, :] >= TAU[:, None])[:, None, :], out['actions'].shape)
        proposal = np.stack((out['information'], out['clock_benefit']), axis=-1)
        out['proposal_sums'] = np.stack([(proposal*m[..., None]).sum(axis=-2)
                                         for m in (np.ones_like(post), post)], axis=-2)
    return out


def analyze(data, pop):
    result = relabel(P.analyze(data, pop))
    result['proposal_values'] = {}
    for name, selected in C.panels().items():
        result['proposal_values'][name] = {}
        counts = np.take(data['counts'], selected, axis=2)
        values = np.take(data['proposal_sums'], selected, axis=2)
        for s, segment in enumerate(('episode', 'post_change')):
            if name == 'stable' and s:
                continue
            result['proposal_values'][name][segment] = {
                arm: {key: P.ci((values[..., a, s, k]/counts[..., a, s, 0]).mean(axis=2))
                      for k, key in enumerate(('task_information', 'clock_benefit'))}
                for a, arm in enumerate(ARMS)}
    return result


def qualify(output):
    import readback_fep_planned_recovery as V
    import readback_fep_paid_checking as Q
    tick = perf_counter()
    for checks in (CHECKS, C.CHECKS, P.CHECKS, V.CHECKS, Q.CHECKS):
        checks.clear()
    check('previous_analytic_qualified', json.loads((PREVIOUS/'QUALIFICATION.json').read_text())['passed'])
    check('previous_analytic_verified', json.loads((PREVIOUS/'READBACK.json').read_text())['passed'])
    check('schema_bijection', relabel(relabel({'arms': list(P.ARMS), 'gap1_minus_baseline': {'extra_ct4_purchases': 2}}), True) ==
          {'arms': list(P.ARMS), 'gap1_minus_baseline': {'extra_ct4_purchases': 2}})
    check('new_arm_names', relabel(list(P.ARMS)) == list(ARMS))
    exact_cases = []
    for counts, hist, y in (((20, 4, 8, 32), [(0, None), (3, 0), (1, None)], 0),
                            ((58, 3, 3, 0), [(0, 0), (3, None)], 1)):
        f = K.Clock(np.array([counts]), (1, 2, 4))
        for t, (yy, label) in enumerate(hist, 1):
            f.start(t); f.warning(np.array([yy])); f.retain(np.array([-1 if label is None else label]))
        f.start(len(hist)+1); f.warning(np.array([y]))
        before = C.M.fingerprint({k: getattr(f, k) for k in ('w', 'p', 'ys', 'labels', 'u', 'z')})
        ref = A.Reference(counts, (1, 2, 4))
        for h in range(1, 5):
            for retain in (True, False):
                scores = f.clock_scores(f.w, f.p, f.z, f.t, h, retain)
                for d in (0, 1):
                    vector, clock, information = A.Vector(f).inspect(h, d, retain)
                    exact, ec, ei = ref.inspect(hist, y, h, d, retain)
                    for got, saved, rational in (
                        (scores[0][0], vector['clock']['answer'][0], exact['clock']['answer']),
                        (scores[1][0], vector['clock']['purchase'][0], exact['clock']['purchase']),
                        (scores[2][0], clock[0], ec), (scores[3][0], information[0], ei)):
                        close('optimized_vector_equivalence', got, saved, 3e-12)
                        close('optimized_rational_equivalence', got, float(rational), 3e-12)
                    actual = scores[1][0] if d else min(scores[0][0], scores[1][0])
                    close('both_clock_values', actual, float(exact['clock']['value']), 3e-12)
                    exact_cases.append(dict(counts=counts, history=hist, warning=y, horizon=h, clock=d,
                                            retained=retain, cost=str(exact['clock']['value']), clock_benefit=str(ec), information=str(ei)))
        forced = f.choose_clock(4, force_exact=True)
        check('rational_fallback_exercised', forced['fallback_mask'][0] and f.fallback >= 1)
        exact, ec, ei = ref.inspect(hist, y, 4, 0)
        check('fallback_exact_purchase_choice', (forced['proposed'][0] == 2) == exact['clock']['buy'])
        close('fallback_diagnostics', [forced['clock_benefit'][0], forced['information'][0]], [float(ec), float(ei)], 0)
        check('proposal_purity', before == C.M.fingerprint({k: getattr(f, k) for k in ('w', 'p', 'ys', 'labels', 'u', 'z')}))
    counts = np.array([[58, 3, 3, 0], [20, 4, 8, 32], [16, 16, 16, 16]])
    batch = K.Clock(counts)
    scalar = [K.Clock(c[None, :]) for c in counts]
    last = np.zeros(3, dtype=int); slast = [0]*3
    for t in range(1, 9):
        y = np.array([(t+2*i) % 4 for i in range(3)], dtype=np.int8)
        target = np.array([(t+i) % 2 for i in range(3)])
        batch.start(t); batch.warning(y); plan = batch.choose_clock()
        action, _, _ = P.apply_rule(plan['proposed'], t-last, True)
        for i, f in enumerate(scalar):
            f.start(t); f.warning(y[i:i+1]); single = f.choose_clock()
            a = 2 if t-slast[i] >= 2 else int(single['proposed'][0])
            check('independent_scalar_clock', a == action[i])
            for key in plan:
                close('scalar_proposal_'+key, plan[key][i], single[key][0], 3e-12)
            f.retain(np.array([target[i] if a == 2 else -1]))
            if a == 2:
                slast[i] = t
        batch.retain(np.where(action == 2, target, -1)); last = np.where(action == 2, t, last)
        for i, f in enumerate(scalar):
            close('scalar_beliefs', batch.w[i], f.w[0], 2e-14)
            close('scalar_sufficient_statistics', batch.p[i], f.p[0], 0)
    for t in range(9, 101):
        batch.start(t); batch.warning(np.full(3, t % 4, dtype=np.int8))
        if t < 100:
            batch.retain(np.full(3, -1, dtype=np.int8))
    four, one = batch.choose_clock(4), batch.choose_clock(1)
    for key in four:
        close('terminal_truncation_'+key, four[key], one[key], 0)
    check('terminal_both_future_values_zero', np.all(four['information'] == 0) and np.all(four['clock_benefit'] == 0))
    twin = K.Clock(np.repeat(counts[:1], 2, axis=0))
    for t in range(1, 5):
        twin.start(t); twin.warning(np.array([t % 4, (t % 4) ^ 3]))
        p = twin.choose_clock()
        for key in ('information', 'clock_benefit', 'scores', 'extra'):
            close('flip_symmetry_'+key, p[key][0], p[key][1], 0)
        check('flip_action', p['proposed'][1] == (2 if p['proposed'][0] == 2 else 1-p['proposed'][0]))
        twin.retain(np.array([0, 1]) if t % 2 == 0 else np.array([-1, -1]))
    full = K.Clock(counts[1:2])
    history = [(0, None), (3, 1)]
    for t, (y, label) in enumerate(history, 1):
        full.start(t); full.warning(np.array([y])); full.retain(np.array([-1 if label is None else label]))
    full.start(3); full.warning(np.array([1]))
    reference = A.Reference(tuple(map(int, counts[1])))
    for retain in (True, False):
        scores = full.clock_scores(full.w, full.p, full.z, 3, 2, retain)
        exact, ec, ei = reference.inspect(history, 1, 2, 0, retain)
        close('full_support_rational_scores', [v[0] for v in scores],
              [float(exact['clock']['answer']), float(exact['clock']['purchase']), float(ec), float(ei)], 3e-12)
    synthetic = C.S.extend_meta(C.S.A.synthetic())
    raw = simulate(synthetic, [0, 1], 'qualification-'+PREFIX)
    prior = P.simulate(synthetic, [0, 1], 'qualification-'+PREFIX, steps=8, enabled=(True, True))
    for key in ('actions', 'planned_actions', 'labels', 'subjective_u', 'information', 'extra', 'posterior',
                'gap_before', 'due', 'forced'):
        close('previous_hybrid_unchanged_'+key, raw[key][:, :, 0, :8], prior[key][:, :, 1], 2e-13)
    for key in ('calibration', 'warnings', 'truth'):
        close('physical_reproducibility_'+key, raw[key], prior[key], 0)
    with (output/'QUALIFICATION_TRACES.npz').open('xb') as stream:
        np.savez_compressed(stream, **raw)
    rebuilt = V.rebuild(raw, synthetic)
    for key in FIELDS:
        close('independent_synthetic_accounting_'+key, raw[key], rebuilt[key])
    fixture = {key: np.stack([value]*3) for key, value in rebuilt.items()}
    fixture_pop = [dict(synthetic, label='synthetic-fixture-'+str(i)) for i in range(3)]
    V.verify_results(analyze(fixture, fixture_pop), fixture, fixture_pop)
    Q.qualify_axes()
    jobs = [(synthetic, [i], 'parallel-'+PREFIX, None, 8) for i in range(4)]
    accumulated = [dict(d) for d in (CHECKS, C.CHECKS, P.CHECKS)]
    serial = [worker(j) for j in jobs]
    for dest, saved in zip((CHECKS, C.CHECKS, P.CHECKS), accumulated):
        dest.clear(); dest.update(saved)
    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(worker, jobs))
    for left, right in zip(serial, parallel):
        check('serial_four_worker_fingerprint', left['fingerprint'] == right['fingerprint'])
    return dict(passed=True, seconds=perf_counter()-tick, checks=dict(CHECKS),
                reused_checks=dict(P.CHECKS), accounting_checks=dict(C.CHECKS),
                independent_readback_checks=dict(V.CHECKS), independent_interval_checks=dict(Q.CHECKS),
                exact_cases=exact_cases, parallel_records=parallel)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir(); (output/'blocks').mkdir()
    log(output, 'PREPARE: fixed structured model and gap; planned versus hybrid; 864 fresh paired blocks')
    for path, expected in FROZEN.items():
        check('previous_frozen_input', digest(path) == expected)
    prior = json.loads((PREVIOUS/'FREEZE.json').read_text())
    identities = dict(prior['inputs'])
    for path, expected in identities.items():
        check('previous_frozen_dependency', digest(path) == expected)
    for path in (SPEC, POLICY, Path(__file__).resolve(), READBACK, *FROZEN):
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
    for path in (SPEC, POLICY, Path(__file__).resolve(), READBACK):
        shutil.copyfile(path, output/'inputs'/path.name)
        snapshots[path.name] = digest(path)
    write(output/'FREEZE.json', dict(created=utc(), inputs=identities, snapshots=snapshots,
                                     cpus=sorted(os.sched_getaffinity(0)), storage=storage,
                                     python=platform.python_version(), numpy=np.__version__,
                                     blocks=27*BLOCKS, main_prefix=PREFIX, no_main_outcomes_generated=True))
    log(output, 'FROZEN: source identities, gap=1, coherent planning, population, seeds, endpoints and sample size')
    qualification = qualify(output)
    write(output/'QUALIFICATION.json', qualification)
    log(output, f'QUALIFIED: {qualification["seconds"]:.2f}s; policy, masks, accounting and scalar interval checks passed')
    synthetic = C.S.extend_meta(C.S.A.synthetic())
    jobs = [(synthetic, list(range(i*4, (i+1)*4)), 'benchmark-'+PREFIX, None, 100) for i in range(4)]
    tick = perf_counter()
    log(output, 'BENCHMARK: four workers, four synthetic blocks each, hybrid and planned policies')
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
                                       workers=4, cpus=frozen['cpus'], checks=dict(CHECKS),
                                       reused_checks=dict(P.CHECKS), outputs=outputs))
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
