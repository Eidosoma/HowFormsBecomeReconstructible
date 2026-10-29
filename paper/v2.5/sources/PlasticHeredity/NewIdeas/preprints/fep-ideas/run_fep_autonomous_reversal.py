#!/usr/bin/env python3
"""One frozen autonomous comparison; imported policies are never modified."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
import json
from pathlib import Path
import platform
import shutil
import subprocess
from time import perf_counter, process_time
import traceback
import numpy as np
import fep_structured_reversal as R

OLD, A, Q = R.OLD, R.A, R.Q
U, S, M, H = A.U, A.S, A.M, OLD.H
SOURCE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1')
PREVIOUS = ROOT.parent/'fep-structured-reversal-v1/attempt-01'
POP_SOURCE = H.ROOT/'attempt-01/POPULATION.json'
SPEC = SOURCE/'FEP_AUTONOMOUS_REVERSAL_V1.md'
READBACK = SOURCE/'readback_fep_autonomous_reversal.py'
PREFIX = 'fep-autonomous-reversal-v1'
ARMS = ('CT4-anytime', 'CT4-structured')
CONDITIONS = (('stable', 101),)+tuple((f, t) for f in U.FAMILIES for t in U.UNEXPECTED)
SELECT = [U.CONDITIONS.index(c) for c in CONDITIONS]
BLOCKS, CHUNK, MAX_FORECAST = 32, 4, 7*86400
TAU = np.array([t for _, t in CONDITIONS])
TIMES = np.arange(1, 101)
SUMS = ('conditional_cost', 'known_law_floor', 'insufficient_checking',
        'wrong_direction', 'excess_checking', 'subjective_cost')
FIELDS = ('counts', 'sums', 'phase_counts', 'phase_sums', 'first',
          'confident_agreement', 'extra_counts', 'alarm', 'posterior_final')
CHECKS = {}
write, digest, utc = OLD.write, OLD.digest, OLD.utc
FROZEN = {
    SOURCE/'fep_structured_reversal.py': '9ae8f36d2730d6885a5558cc0069fe6f2b614e279985831105233ec437a63f3b',
    SOURCE/'check_fep_structured_reversal.py': '000ef88a118c6e373fc41685ddf9ef2acf799ef3f10be9f14eb60886322b4852',
    SOURCE/'FEP_STRUCTURED_REVERSAL_V1.md': '8ba918cf2af2a796777608f6cc351c57e65f1bcb915c00a16d8ab63efc7e5003',
    SOURCE/'FEP_STRUCTURED_REVERSAL_V1_REPORT.md': '86c1e183f3d3a973fefe6177d3ce1d5b73ec5d979887f19594b576cec9cb74e7',
    PREVIOUS/'MANIFEST.json': 'bf218c3411a9b0a8926704dbe057c6eff4594a3b1db654593f370bbc6c2bec05',
    PREVIOUS/'READBACK.json': '8389366c8cce2961d63d68f1766df10ad2ac173d77a3082e8acbd722bff3032a',
    PREVIOUS/'QUALIFICATION.json': '0ccb4ef6e84b925db0c1c20e409988372b873f018f8a79eeec98cf0db43e120d',
    POP_SOURCE: 'd255f20a82057d11900ed7e2531e6c326b8b6eb3cfc75c90934c0e1cbfb3eb23',
}


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def log(output, message):
    line = utc()+' '+message
    with (output/'RUN_LOG.txt').open('a') as stream:
        stream.write(line+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(line, flush=True)


def resources():
    OLD.constrain()
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        os.nice(10-os.getpriority(os.PRIO_PROCESS, 0))
    return sorted(os.sched_getaffinity(0))


def mount_check(output):
    mounted = json.loads(subprocess.check_output(
        ['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('external_mount', mounted == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'))
    check('output_namespace', output.resolve().parent == ROOT and output.name.startswith('attempt-'))
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('external_space', free > 2_000_000_000)
    return dict(mount=mounted, free_bytes=free)


def physical(meta, indices, prefix):
    cal, warning, target, law = U.physical_trace(meta, indices, prefix)
    return cal, warning[:, SELECT], target[:, SELECT], law[SELECT]


def simulate(meta, indices, prefix, steps=100):
    """The learner receives only calibration, warnings and its paid targets."""
    cal, y, truth, laws = physical(meta, indices, prefix)
    b, nc = len(indices), len(CONDITIONS)
    yy, targets = y.reshape(-1, 100), truth.reshape(-1, 100)
    shape = (b*nc, 2, steps)
    out = dict(calibration=cal, warnings=y, truth=truth, indices=np.array(indices))
    out.update(actions=np.empty(shape, dtype=np.int8), labels=np.empty(shape, dtype=np.int8),
               subjective_u=np.empty(shape), information=np.empty(shape),
               extra=np.empty(shape, dtype=bool), posterior=np.empty(shape+(2,)))
    fallbacks = []
    for arm, cls in enumerate((A.Filter, R.Filter)):
        learner = cls(np.repeat(cal, nc, axis=0))
        for t in range(1, steps+1):
            learner.start(t)
            u = learner.warning(yy[:, t-1])
            action, value, _, extra = learner.choose(steps=4)
            labels = np.where(action == 2, targets[:, t-1], -1).astype(np.int8)
            learner.retain(labels)
            check('only_paid_labels_retained', np.array_equal(learner.labels[:, t-1], labels))
            check('posterior_normalized', np.allclose(learner.w.sum(axis=1), 1, atol=2e-13, rtol=0))
            check('finite_state', np.all(np.isfinite(learner.w)) and np.all(np.isfinite(u)))
            check('information_nonnegative', np.all(value >= -2e-12))
            completed = learner.times <= t
            mass = learner.w[:, completed].sum(axis=1)
            reversal = learner.w[:, completed & (learner.kinds == 3)].sum(axis=1)
            for key, array in (('actions', action), ('labels', labels), ('subjective_u', u),
                               ('information', value), ('extra', extra)):
                out[key][:, arm, t-1] = array
            out['posterior'][:, arm, t-1] = np.column_stack((mass, reversal))
            if t == 100:
                check('terminal_information_zero', np.all(value == 0))
        fallbacks.append(learner.fallback)
    for key in ('actions', 'labels', 'subjective_u', 'information', 'extra', 'posterior'):
        out[key] = out[key].reshape((b, nc)+out[key].shape[1:])
    out['fallbacks'] = np.array(fallbacks, dtype=np.int64)
    if steps == 100:
        out.update(account(out, laws))
    return out


def account(raw, laws):
    action = raw['actions']
    ask = action == 2
    wrong = (action != raw['truth'][:, :, None, :]) & ~ask
    y = raw['warnings']
    q = np.broadcast_to(laws, y.shape+(4,))
    qy = np.take_along_axis(q, y[..., None], axis=-1)[..., 0]
    qop = np.take_along_axis(q, (y ^ 3)[..., None], axis=-1)[..., 0]
    p1 = (qop/(qy+qop))[:, :, None, :]
    risk = np.where(action == 0, p1, 1-p1)
    best = np.minimum(p1, 1-p1)
    subject = np.where((y[:, :, None, :] >> 1) != 0, 1-raw['subjective_u'], raw['subjective_u'])
    sums = np.stack((np.where(ask, .1, risk), np.broadcast_to(np.minimum(best, .1), ask.shape),
                     np.where(ask, 0, np.maximum(best-.1, 0)), np.where(ask, 0, risk-best),
                     np.where(ask, np.maximum(.1-best, 0), 0),
                     np.where(ask, .1, np.where(action == 0, subject, 1-subject))), axis=-1)
    check('regret_closure', np.allclose(sums[..., 0]-sums[..., 1], sums[..., 2:5].sum(axis=-1), atol=2e-15, rtol=0))
    post = np.broadcast_to((TIMES[None, :] >= TAU[:, None])[:, None, :], action.shape)
    first = np.where(ask & post, TIMES, 101).min(axis=-1)
    confident = np.isin(y[:, :, None, :], [0, 3]) & (np.minimum(raw['subjective_u'], 1-raw['subjective_u']) < .1)
    counts = np.stack((np.ones_like(action), wrong, ask), axis=-1)
    conf = np.stack((confident, confident & ask, confident & wrong), axis=-1)
    masks = (np.ones_like(ask), post)
    out = dict(counts=np.stack([(counts*m[..., None]).sum(axis=-2) for m in masks], axis=-2),
               sums=np.stack([(sums*m[..., None]).sum(axis=-2) for m in masks], axis=-2),
               confident_agreement=np.stack([(conf*m[..., None]).sum(axis=-2) for m in masks], axis=-2),
               extra_counts=np.stack([(raw['extra']*m).sum(axis=-1) for m in masks], axis=-1), first=first)
    phases = (post & (TIMES < first[..., None]), post & (TIMES == first[..., None]),
              post & (TIMES > first[..., None]))
    out['phase_counts'] = np.stack([(counts*m[..., None]).sum(axis=-2) for m in phases], axis=-2)
    out['phase_sums'] = np.stack([(sums*m[..., None]).sum(axis=-2) for m in phases], axis=-2)
    mass = raw['posterior'][..., 0]
    out['alarm'] = np.stack(((mass > .5).sum(axis=-1), np.where(mass > .5, TIMES, 101).min(axis=-1), mass.sum(axis=-1)), axis=-1)
    out['posterior_final'] = raw['posterior'][..., -1, :]
    check('phase_count_closure', np.array_equal(out['phase_counts'].sum(axis=-2), out['counts'][..., 1, :]))
    check('phase_sum_closure', np.allclose(out['phase_sums'].sum(axis=-2), out['sums'][..., 1, :], atol=2e-12, rtol=0))
    check('paid_label_mask', np.array_equal(raw['labels'], np.where(ask, raw['truth'][:, :, None, :], -1)))
    check('count_bounds', np.all(out['counts'][..., 1:].sum(axis=-1) <= out['counts'][..., 0]))
    return out


def worker(job):
    meta, indices, prefix, output, steps = job
    resources()
    CHECKS.clear()
    tick, cpu = perf_counter(), process_time()
    arrays = simulate(meta, indices, prefix, steps)
    record = dict(label=meta['label'], indices=indices, fingerprint=M.fingerprint(arrays),
                  wall_seconds=perf_counter()-tick, cpu_seconds=process_time()-cpu,
                  affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                  fallback=arrays['fallbacks'].tolist(), checks=dict(CHECKS))
    if output:
        name = f'{meta["label"]}_{indices[0]:04d}_{indices[-1]:04d}.npz'
        path = Path(output)/'blocks'/name
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        record.update(file='blocks/'+name, sha256=digest(path), bytes=path.stat().st_size)
    return record


def ci(x):
    check('independent_strata_blocks', x.ndim == 2 and x.shape[1] > 1)
    b, n = x.shape
    mean = float(x.mean())
    se = float(np.sqrt(x.var(axis=1, ddof=1).sum()/(b*b*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def panel(x):
    return dict(arms={arm: ci(x[..., a]) for a, arm in enumerate(ARMS)},
                structured_minus_anytime=ci(x[..., 1]-x[..., 0]),
                against_always={arm: ci(x[..., a]-.1) for a, arm in enumerate(ARMS)})


def panels():
    result = dict(stable=[0])
    result.update({f: [j for j, (family, _) in enumerate(CONDITIONS) if family == f] for f in U.FAMILIES})
    result.update(core=[j for j, (f, _) in enumerate(CONDITIONS) if f in U.FAMILIES[:3]],
                  non_reversal=[j for j, (f, _) in enumerate(CONDITIONS) if f not in ('stable', 'reverse')],
                  transfer=[j for j, (f, _) in enumerate(CONDITIONS) if f in U.FAMILIES[3:]],
                  all_changes=list(range(1, len(CONDITIONS))))
    return result


def analyze(data, pop):
    counts = data['counts']
    units = 10*counts[..., 1]+counts[..., 2]
    rate = units/(10*np.maximum(1, counts[..., 0]))
    result = dict(arms=list(ARMS), blocks_per_base=BLOCKS, independent_blocks=27*BLOCKS,
                  physical_episodes=27*BLOCKS*len(CONDITIONS), policy_decisions=27*BLOCKS*len(CONDITIONS)*2*100,
                  panels={}, conditions=[], diagnostics={})
    for name, selected in panels().items():
        result['panels'][name] = dict(episode=panel(rate[:, :, selected, :, 0].mean(axis=2)))
        if name != 'stable':
            result['panels'][name]['post_change'] = panel(rate[:, :, selected, :, 1].mean(axis=2))
        diag = {}
        for a, arm in enumerate(ARMS):
            d = {}
            for seg, segment in enumerate(('episode', 'post_change')):
                if name == 'stable' and seg:
                    continue
                exposure = counts[:, :, selected, a, seg, 0]
                d[segment] = {key: ci((data['sums'][:, :, selected, a, seg, k]/exposure).mean(axis=2)) for k, key in enumerate(SUMS)}
                d[segment]['confident_agreement_totals'] = data['confident_agreement'][:, :, selected, a, seg].sum(axis=(0, 1, 2)).tolist()
                d[segment]['extra_purchases'] = int(data['extra_counts'][:, :, selected, a, seg].sum())
            d['alarm_episode_fraction'] = ci((data['alarm'][:, :, selected, a, 0] > 0).mean(axis=2))
            d['alarm_tasks'] = ci(data['alarm'][:, :, selected, a, 0].mean(axis=2))
            d['final_change_mass'] = ci(data['posterior_final'][:, :, selected, a, 0].mean(axis=2))
            d['final_reversal_mass'] = ci(data['posterior_final'][:, :, selected, a, 1].mean(axis=2))
            if name != 'stable':
                first = data['first'][:, :, selected, a]
                d['no_post_purchase_fraction'] = ci((first == 101).mean(axis=2))
                d['capped_first_purchase_delay'] = ci((first-TAU[selected]).mean(axis=2))
                d['phase_count_totals'] = data['phase_counts'][:, :, selected, a].sum(axis=(0, 1, 2)).tolist()
                den = (101-TAU[selected])[None, None, :, None, None]
                ps = data['phase_sums'][:, :, selected, a]/den
                d['phase_contributions_per_post_task'] = {
                    phase: {key: ci(ps[:, :, :, j, k].mean(axis=2)) for k, key in enumerate(SUMS)}
                    for j, phase in enumerate(('before_first', 'at_first', 'after_first'))}
            diag[arm] = d
        result['diagnostics'][name] = diag
    for bi, meta in enumerate(pop):
        for j, (family, onset) in enumerate(CONDITIONS):
            row = dict(base=meta['label'], family=family, onset=onset,
                       episode=panel(rate[bi:bi+1, :, j, :, 0]))
            if j:
                row['post_change'] = panel(rate[bi:bi+1, :, j, :, 1])
            result['conditions'].append(row)
    result['criteria'] = {}
    for name in ('reverse', 'core'):
        p = result['panels'][name]['post_change']
        gates = dict(better_than_anytime=p['structured_minus_anytime']['upper95'] < 0,
                     below_always=p['against_always'][ARMS[1]]['upper95'] < 0)
        result['criteria'][name] = dict(gates, both=all(gates.values()))
    result['harms'] = {}
    for segment in ('episode', 'post_change'):
        valid = [r for r in result['conditions'] if segment in r]
        result['harms'][segment] = {
            'point_higher': [dict(base=r['base'], family=r['family'], onset=r['onset'],
                                  **r[segment]['structured_minus_anytime']) for r in valid
                             if r[segment]['structured_minus_anytime']['mean'] > 0],
            'interval_lower_above_zero': sum(r[segment]['structured_minus_anytime']['lower95'] > 0 for r in valid),
            'point_equal': sum(r[segment]['structured_minus_anytime']['mean'] == 0 for r in valid),
            'point_lower': sum(r[segment]['structured_minus_anytime']['mean'] < 0 for r in valid)}
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
    tick = perf_counter()
    CHECKS.clear()
    check('previous_model_qualified', json.loads((PREVIOUS/'QUALIFICATION.json').read_text())['passed'])
    # Full-support batch/scalar equivalence, including endogenous label masks.
    counts = np.array([[58, 3, 3, 0], [20, 4, 8, 32], [16, 16, 16, 16]])
    for cls in (A.Filter, R.Filter):
        batch = cls(counts)
        scalar = [cls(c[None, :]) for c in counts]
        for t in range(1, 13):
            y = np.array([(t+2*i) % 4 for i in range(3)], dtype=np.int8)
            batch.start(t); ub = batch.warning(y)
            action, value, _, extra = batch.choose(steps=4)
            target = np.array([(t+i) % 2 for i in range(3)])
            for i, f in enumerate(scalar):
                f.start(t); u = f.warning(y[i:i+1])
                aa, vv, _, ee = f.choose(steps=4)
                check('batch_scalar_decisions', aa[0] == action[i] and ee[0] == extra[i])
                check('batch_scalar_predictions', abs(u[0]-ub[i]) < 2e-14 and abs(vv[0]-value[i]) < 2e-13)
                f.retain(np.array([target[i] if aa[0] == 2 else -1]))
            batch.retain(np.where(action == 2, target, -1))
            for i, f in enumerate(scalar):
                check('batch_scalar_beliefs', np.allclose(batch.w[i], f.w[0], atol=2e-14, rtol=0) and np.array_equal(batch.p[i], f.p[0]))
        # Replay to terminal without extra planning, then check truncation exactly.
        for t in range(13, 101):
            batch.start(t); batch.warning(np.full(3, t % 4, dtype=np.int8))
            if t < 100:
                batch.retain(np.full(3, -1, dtype=np.int8))
        four = batch.choose(steps=4)
        one = batch.choose(steps=1)
        check('terminal_truncation', np.array_equal(four[0], one[0]) and np.all(four[1] == 0))
    # Rational scores on a separate short-support history; the main models stay full-support.
    history = [(0, None), (3, 0), (1, None)]
    ref = R.Reference(counts[1], (1, 2, 4))
    w, p = ref.state(history, 2)
    f = R.Filter(counts[1:2], (1, 2, 4))
    for t, (y, label) in enumerate(history, 1):
        f.start(t); f.warning(np.array([y])); f.retain(np.array([-1 if label is None else label]))
    f.start(4); f.warning(np.array([2]))
    exact = ref.scores(w, p, 2, 4, 4)
    scores = f.scores(f.w, f.p, f.z, 4, 4)
    check('rational_scores', max(abs(a[0]-float(b)) for a, b in zip(scores, exact[:3])) < 2e-13)
    check('rational_action', f.choose(4)[0][0] == Q.exact_action(exact[0], exact[1], exact[3], 2))
    # Full synthetic episode: independently reproduce baseline evaluator and readback.
    synthetic = S.extend_meta(S.A.synthetic())
    raw = simulate(synthetic, [0], 'qualification-'+PREFIX)
    previous = H.new_batch(synthetic, [0], 'qualification-'+PREFIX, 4)
    for field, segment, entry in (('wrong', 0, 1), ('references', 0, 2), ('post_wrong', 1, 1), ('post_references', 1, 2)):
        check('prior_evaluator_'+field, np.array_equal(raw['counts'][:, :, 0, segment, entry], previous[field][:, SELECT, 0]))
    check('prior_evaluator_regret', np.allclose(raw['sums'][:, :, 0, 0], previous['anytime_episode_sums'][:, SELECT], atol=2e-12, rtol=0))
    check('prior_evaluator_first', np.array_equal(raw['first'][:, :, 0], previous['first_post_reference'][:, SELECT, 0]))
    with (output/'QUALIFICATION_TRACES.npz').open('xb') as stream:
        np.savez_compressed(stream, **raw)
    import readback_fep_autonomous_reversal as V
    rebuilt = V.rebuild(raw, synthetic)
    for key in FIELDS:
        check('independent_synthetic_accounting_'+key, np.allclose(raw[key], rebuilt[key], atol=2e-12, rtol=0))
    # Exercise the entire reporting path before main outcomes. Repeated synthetic
    # data are a software fixture only, never a scientific sample or estimate.
    fixture = {key: np.broadcast_to(value[0], (27, BLOCKS)+value.shape[1:]).copy()
               for key, value in rebuilt.items()}
    fixture_population = [dict(synthetic, label='synthetic-fixture-'+str(i)) for i in range(27)]
    V.verify_results(analyze(fixture, fixture_population), fixture, fixture_population)
    variance_fixture = np.array([[0., 1., 2.], [2., 4., 6.]])
    interval = ci(variance_fixture)
    check('analytic_stratified_variance', abs(interval['mean']-2.5) < 1e-15 and
          abs(interval['mc_se']-np.sqrt(5/12)) < 1e-15)
    V.stats(interval, variance_fixture)
    # Small full-support autonomous traces establish process and batching determinism.
    jobs = [(synthetic, [i], 'parallel-'+PREFIX, None, 8) for i in range(4)]
    accumulated_checks = dict(CHECKS)
    serial = [worker(j) for j in jobs]
    CHECKS.clear()
    CHECKS.update(accumulated_checks)
    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(worker, jobs))
    for left, right in zip(serial, parallel):
        check('serial_four_worker_fingerprint', left['fingerprint'] == right['fingerprint'])
    return dict(passed=True, seconds=perf_counter()-tick, checks=dict(CHECKS),
                previous_qualification_sha256=digest(PREVIOUS/'QUALIFICATION.json'),
                independent_readback_checks=dict(V.CHECKS), parallel_records=parallel)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir(); (output/'blocks').mkdir()
    log(output, 'PREPARE: frozen CT4 policies, autonomous paid labels, 864 fresh paired blocks')
    for path, expected in FROZEN.items():
        check('previous_frozen_input', digest(path) == expected)
    identities = OLD.inputs()
    prior = json.loads((PREVIOUS/'FREEZE.json').read_text())
    for path, expected in prior['inputs'].items():
        check('previous_structured_dependencies', digest(path) == expected)
        identities[path] = expected
    for path in (SPEC, Path(__file__).resolve(), READBACK, *FROZEN):
        identities[str(path)] = digest(path)
    pop = json.loads(POP_SOURCE.read_text())['bases']
    check('unchanged_population', pop == S.population() and len(pop) == 27)
    write(output/'POPULATION.json', dict(bases=pop, conditions=CONDITIONS, arms=ARMS, blocks_per_base=BLOCKS,
                                        chunk=CHUNK, policy_horizon=4, total_policy_decisions=4320000))
    seeds = {m['label']: [str(M.seed_for(m['label'], i, PREFIX)) for i in range(BLOCKS)] for m in pop}
    flips = {m['label']: [str(M.seed_for(m['label'], i, PREFIX+'-transfer-flips')) for i in range(BLOCKS)] for m in pop}
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
    synthetic = S.A.synthetic()['label']
    test_seeds = {str(M.seed_for(synthetic, i, purpose+PREFIX+suffix)) for purpose in ('qualification-', 'parallel-', 'benchmark-')
                  for i in range(16) for suffix in ('', '-transfer-flips')}
    check('separate_synthetic_seeds', not fresh.intersection(test_seeds) and len(test_seeds) == 96)
    write(output/'SEEDS.json', dict(root=M.ROOT_SEED, main_prefix=PREFIX, blocks=seeds, flip_blocks=flips,
                                   rng='Python random.Random MT19937', core_draw_order=M.streams.__doc__,
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
    log(output, 'FROZEN: sources, models, population, seeds, endpoints and sample size')
    qualification = qualify(output)
    write(output/'QUALIFICATION.json', qualification)
    log(output, f'QUALIFIED: {qualification["seconds"]:.2f}s; batched, scalar, rational, legacy and saved-trace checks passed')
    synthetic = S.extend_meta(S.A.synthetic())
    jobs = [(synthetic, list(range(i*4, (i+1)*4)), 'benchmark-'+PREFIX, None, 100) for i in range(4)]
    tick = perf_counter()
    log(output, 'BENCHMARK: four workers, four synthetic blocks each, both fixed CT4 policies')
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
    jobs = [(m, list(range(i, i+CHUNK)), PREFIX, str(output), 100) for m in pop for i in range(0, BLOCKS, CHUNK)]
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
    log(output, 'MAIN COMPLETE: all fixed chunks saved; separate readback follows')
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
    parser.add_argument('mode', choices=('prepare', 'run', 'campaign'))
    parser.add_argument('--output', type=Path, default=ROOT/'attempt-01')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    resources()
    if args.mode in ('prepare', 'campaign') and args.output.exists():
        raise FileExistsError('Preserve the existing attempt; do not overwrite it.')
    try:
        if args.mode in ('prepare', 'campaign'):
            prepare(args.output)
        if args.mode in ('run', 'campaign'):
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
