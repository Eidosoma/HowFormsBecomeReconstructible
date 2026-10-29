#!/usr/bin/env python3
"""Fresh-cohort confirmation; imports every policy unchanged from its freeze."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
from time import perf_counter, process_time
import traceback

SOURCE = Path(__file__).resolve().parent
EXPECTED = {
    'check_fep_calibrated_change.py': 'e35042ba9fecb2dea137d67b1ecca9b97a657ec336fb9a60fc693a10efadb004',
    'qualify_fep_calibrated_change.py': '03e006607dbfe57f8c16185254d57403eda682d79bcf543861d837c13b59470a',
    'FEP_CALIBRATED_CHANGE_V1.md': 'f6d357321240dab27c244d5bcb711a0247398eac6cab8ef624f5dbbaa1691e31',
    'FEP_CALIBRATED_CHANGE_V1_REPORT.md': 'db405bdbdf78f512c34ed6d000cd6b61a0dd7c57a307c3d2d888fdcdcfae8537',
    'FEP_CALIBRATED_CHANGE_V1_CHECKPOINT.md': '5f4e576b0c36d5d16e56be471f9ac1b5c6d86c7e8ea221a22f06c7e5429e9a24',
    'readback_fep_calibrated_change.py': '727c1a3d4323f4cecefcaecac3078a1de030d3f89bea09f68f34b9b22766ab01',
}
for _name, _digest in EXPECTED.items():
    assert sha256((SOURCE/_name).read_bytes()).hexdigest() == _digest, _name
import check_fep_calibrated_change as S
import qualify_fep_calibrated_change as Q
import numpy as np

M = S.M
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-weak-prior-confirmation-v1')
PREVIOUS = S.ROOT/'attempt-02'
PREVIOUS_SHA = 'c1f79140937a721fe9ea0109afe081356fd8cbe4285a8d6f6b74aac077dedcac'
PREFIX = 'fep-weak-prior-confirmation-v1'
PRIMARY = 'CT3-flat'
PRIMARY_INDEX = S.ARMS.index(PRIMARY)
FIELDS = ('wrong', 'references', 'post_wrong', 'post_references', 'window_wrong', 'window_references',
          'first_post_reference', 'phase_counts', 'phase_sums', 'candidate_extra_references', 'candidate_values', 'diagnosis')
FALLBACKS = ('planner_fallbacks', 'control_fallback', 'c2_inference_fallback', 'c3_inference_fallback', 'candidate_fallback')
CHECKS = {}


def check(group, name, ok):
    if not bool(ok):
        raise AssertionError(group+': '+name)
    CHECKS[group] = CHECKS.get(group, 0)+1


def primary_stats(num, den, offset=0.):
    own = num[..., PRIMARY_INDEX]
    return dict(cost=S.stats_int(own, den, offset),
                minus_always=S.stats_int(own, den, offset-.1),
                contrasts={PRIMARY+'_minus_'+arm: S.stats_int(own-num[..., i], den)
                           for i, arm in enumerate(S.ARMS) if i != PRIMARY_INDEX})


def verdicts(primary):
    return dict(economical_core_recovery=primary['post_change']['core_changed']['minus_always']['upper95'] < 0,
                better_than_C3_recovery=primary['post_change']['core_changed']['contrasts']['CT3-flat_minus_C3']['upper95'] < 0,
                better_than_C3_full_core=primary['episode']['core_full']['contrasts']['CT3-flat_minus_C3']['upper95'] < 0)


def analyze_primary(rows, pop):
    units = 10*rows['wrong'].astype(np.int64)+rows['references']
    post = 10*rows['post_wrong'].astype(np.int64)+rows['post_references']
    windows = 10*rows['window_wrong'].astype(np.int64)+rows['window_references']
    multipliers = np.array([0]+[150//(101-t) for _, t in S.CONDITIONS[1:]])
    result = dict(episode={}, post_change={}, conditions={}, first_25_task_mean_cost={}, condition_counts={})
    for group, weights in S.coefficients().items():
        result['episode'][group] = primary_stats(np.einsum('k,brka->bra', weights, units), 18000, .00064)
        if group != 'stable' and not group.endswith('_full'):
            result['post_change'][group] = primary_stats(np.einsum('k,brka->bra', weights*multipliers, post), 27000)
    for wi, tau in enumerate(M.BOUNDARIES):
        out = dict(stable=primary_stats(windows[:, :, 0, :, wi], 250))
        for panel, indices in (('core', range(1, 10)), ('transfer', range(10, 19))):
            chosen = [j for j in indices if S.CONDITIONS[j][1] == tau]
            out[panel] = primary_stats(np.take(windows, chosen, axis=2)[..., wi].sum(axis=2), 750)
        result['first_25_task_mean_cost'][str(tau)] = out
    for bi, meta in enumerate(pop):
        for j, (family, tau) in enumerate(S.CONDITIONS):
            result['conditions'][f'{meta["label"]}__{family}_{tau}'] = dict(
                episode=primary_stats(units[bi:bi+1, :, j], 1000, .00064),
                post_change=None if not j else primary_stats(post[bi:bi+1, :, j], 10*(101-tau)))
    for panel, indices in (('core', range(10)), ('transfer', range(10, 19)), ('all', range(19))):
        panel_counts = {}
        for endpoint, data in (('episode', units), ('post_change', post)):
            arm_counts = {}
            for ai, arm in enumerate(S.ARMS):
                if ai == PRIMARY_INDEX:
                    continue
                count = dict(point_lower=0, point_equal=0, point_higher=0, upper_below_zero=0, lower_above_zero=0)
                for bi in range(len(pop)):
                    for j in indices:
                        if j == 0 and endpoint == 'post_change':
                            continue
                        d = data[bi, :, j, PRIMARY_INDEX]-data[bi, :, j, ai]
                        den = 1000 if endpoint == 'episode' else 10*(101-S.CONDITIONS[j][1])
                        interval = S.stats_int(d, den)
                        total = int(d.sum())
                        for k, value in (('point_lower', total < 0), ('point_equal', total == 0), ('point_higher', total > 0),
                                         ('upper_below_zero', interval['upper95'] < 0), ('lower_above_zero', interval['lower95'] > 0)):
                            count[k] += int(value)
                arm_counts[arm] = count
            panel_counts[endpoint] = arm_counts
        result['condition_counts'][panel] = panel_counts
    return result


def aggregate(output, pop):
    rows = {k: [] for k in FIELDS}
    fallbacks = {k: 0 for k in FALLBACKS}
    for meta in pop:
        parts = {k: [] for k in FIELDS}
        for first in range(0, 1024, 128):
            with np.load(output/'blocks'/f'{meta["label"]}_{first:04d}_{first+127:04d}.npz', allow_pickle=False) as saved:
                check('aggregation', 'complete chunk indices', np.array_equal(saved['indices'], np.arange(first, first+128)))
                for key in FIELDS:
                    parts[key].append(saved[key])
                for key in FALLBACKS:
                    fallbacks[key] += saved[key]
        for key in FIELDS:
            rows[key].append(np.concatenate(parts[key], axis=0))
    rows = {k: np.stack(v) for k, v in rows.items()}
    reference = S.analyze(rows, pop)
    reference['summary'].update(seed_prefix=PREFIX, new_policies=0,
                                role='CT3-centered descriptive reference on the new cohort; not confirmation decision rules')
    primary = analyze_primary(rows, pop)
    for section in ('episode', 'post_change'):
        for group, value in primary[section].items():
            check('aggregation', 'unchanged primary arm summary', value['cost'] == reference[section][group]['arms'][PRIMARY])
    criteria = verdicts(primary)
    summary = dict(reference['summary'], primary=PRIMARY, role='fresh prospective confirmation of a previously selected control',
                   primary_endpoint='economical_core_recovery', old_cohort_pooled=False,
                   imported_policy_sha256=EXPECTED['check_fep_calibrated_change.py'])
    return dict(summary=summary, criteria=criteria, core_lead_confirmed=all(criteria.values()),
                primary=primary, reference_CT3=reference, fallbacks={k: v.tolist() for k, v in fallbacks.items()})


def qualify(cpus):
    started = perf_counter()
    inherited = Q.qualify(S, cpus)
    meta = S.extend_meta(S.A.synthetic())
    prefix = 'qualification-'+PREFIX
    arrays, _ = S.run_batch(meta, [0, 1, 2, 3], prefix)
    rows = {k: arrays[k][None, ...] for k in FIELDS}
    result = analyze_primary(rows, [meta])
    count = len(arrays['indices'])

    def scalar_ci(saved, values):
        mean = statistics.mean(values)
        se = (statistics.variance(values)/len(values))**.5
        expected = [mean, se, mean-1.96*se, mean+1.96*se]
        actual = [saved[k] for k in ('mean', 'mc_se', 'lower95', 'upper95')]
        check('qualification', 'independent scalar mean and uncertainty', max(abs(a-b) for a, b in zip(expected, actual)) < 3e-13)

    def compare_endpoint(saved, values):
        own = [v[PRIMARY_INDEX] for v in values]
        scalar_ci(saved['cost'], own)
        scalar_ci(saved['minus_always'], [v-.1 for v in own])
        for ai, arm in enumerate(S.ARMS):
            if ai != PRIMARY_INDEX:
                scalar_ci(saved['contrasts'][PRIMARY+'_minus_'+arm], [v[PRIMARY_INDEX]-v[ai] for v in values])

    for group, weights in S.coefficients().items():
        episode, post = [], []
        for b in range(count):
            episode.append([sum(int(w)*(int(arrays['wrong'][b, j, ai])+int(arrays['references'][b, j, ai])/10)/100/18
                                for j, w in enumerate(weights))+.00064 for ai in range(9)])
            if group != 'stable' and not group.endswith('_full'):
                post.append([sum(int(w)*(int(arrays['post_wrong'][b, j, ai])+int(arrays['post_references'][b, j, ai])/10)/(101-t)/18
                                 for j, (w, (_, t)) in enumerate(zip(weights, S.CONDITIONS)) if t != 101) for ai in range(9)])
        compare_endpoint(result['episode'][group], episode)
        if post:
            compare_endpoint(result['post_change'][group], post)
    for wi, tau in enumerate(M.BOUNDARIES):
        for panel, indices in (('stable', [0]), ('core', range(1, 10)), ('transfer', range(10, 19))):
            selected = [j for j in indices if panel == 'stable' or S.CONDITIONS[j][1] == tau]
            values = [[sum((int(arrays['window_wrong'][b, j, ai, wi])+int(arrays['window_references'][b, j, ai, wi])/10)/25
                           for j in selected)/len(selected) for ai in range(9)] for b in range(count)]
            compare_endpoint(result['first_25_task_mean_cost'][str(tau)][panel], values)
    for j, (family, tau) in enumerate(S.CONDITIONS):
        saved = result['conditions'][f'{meta["label"]}__{family}_{tau}']
        for endpoint, wk, rk, den, offset in (('episode', 'wrong', 'references', 100, .00064),
                                             ('post_change', 'post_wrong', 'post_references', 101-tau, 0)):
            if endpoint == 'post_change' and j == 0:
                check('qualification', 'stable recovery absent', saved[endpoint] is None)
                continue
            values = [[(int(arrays[wk][b, j, ai])+int(arrays[rk][b, j, ai])/10)/den+offset for ai in range(9)] for b in range(count)]
            compare_endpoint(saved[endpoint], values)
    for panel, indices in (('core', range(10)), ('transfer', range(10, 19)), ('all', range(19))):
        for endpoint, wk, rk in (('episode', 'wrong', 'references'), ('post_change', 'post_wrong', 'post_references')):
            for ai, arm in enumerate(S.ARMS):
                if ai == PRIMARY_INDEX:
                    continue
                tally = dict(point_lower=0, point_equal=0, point_higher=0, upper_below_zero=0, lower_above_zero=0)
                for j in indices:
                    if endpoint == 'post_change' and j == 0:
                        continue
                    den = 1000 if endpoint == 'episode' else 10*(101-S.CONDITIONS[j][1])
                    diffs = [10*(int(arrays[wk][b, j, PRIMARY_INDEX])-int(arrays[wk][b, j, ai]))+
                             int(arrays[rk][b, j, PRIMARY_INDEX])-int(arrays[rk][b, j, ai]) for b in range(count)]
                    mean = statistics.mean(diffs)/den
                    se = (statistics.variance(diffs)/count)**.5/den
                    for k, yes in (('point_lower', sum(diffs) < 0), ('point_equal', sum(diffs) == 0), ('point_higher', sum(diffs) > 0),
                                   ('upper_below_zero', mean+1.96*se < 0), ('lower_above_zero', mean-1.96*se > 0)):
                        tally[k] += int(yes)
                check('qualification', 'scalar condition signs', tally == result['condition_counts'][panel][endpoint][arm])
    # Exercise each strict gate independently; equality is a failure.
    for bad in (None, 0, 1, 2):
        for boundary in (0., .01):
            uppers = [-.01]*3
            if bad is not None:
                uppers[bad] = boundary
            fixture = dict(post_change=dict(core_changed=dict(minus_always=dict(upper95=uppers[0]),
                           contrasts={'CT3-flat_minus_C3': dict(upper95=uppers[1])})),
                           episode=dict(core_full=dict(contrasts={'CT3-flat_minus_C3': dict(upper95=uppers[2])})))
            check('qualification', 'strict frozen criterion decisions', list(verdicts(fixture).values()) == [x < 0 for x in uppers])
    # Unequal strata fixture detects treating conditions/strata as independent samples.
    values = np.array([[0., 2., 4., 6.], [7., 9., 11., 13.]])
    interval = S.ci(values)
    expected_se = (sum(statistics.variance(list(row)) for row in values)/(2*2*4))**.5
    check('qualification', 'stratified primary uncertainty', abs(interval['mc_se']-expected_se) < 1e-15)
    # The wrapper passes its fresh prefix into the unchanged worker and stream.
    jobs = [(meta, [i], 'parallel-'+PREFIX, None) for i in range(4)]
    serial = [S.worker(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        parallel = list(pool.map(S.worker, jobs))
    for a, b in zip(serial, parallel):
        check('qualification', 'fresh-prefix one/four-worker fingerprint', a['fingerprint'] == b['fingerprint'])
        check('qualification', 'worker CPU ceiling', b['cpus'] == cpus)
    fresh = S.physical_trace(meta, [0, 1], prefix)
    other = S.physical_trace(meta, [0, 1], 'qualification-'+S.PREFIX)
    check('qualification', 'distinct namespace changes physical stream', any(not np.array_equal(a, b) for a, b in zip(fresh[:3], other[:3])))
    return dict(status='PASS', wall_seconds=perf_counter()-started, wrapper_assertions=sum(CHECKS.values()),
                wrapper_checks=dict(CHECKS), shared_checks=dict(S.CHECKS), inherited_qualification=inherited,
                inherited_qualification_reexecuted=True, new_policy_implementations=0,
                scalar_confirmation_blocks=4, fresh_one_four_worker_chunks=4, synthetic_only=True,
                references='separate scalar accounting and existing rational/latent-path qualification; same author')


def mount_check(output):
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check('storage', 'verified FEP destination', mount == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4') and output.parent == ROOT)
    stat = os.statvfs('/mnt/bioIce1')
    free = stat.f_bavail*stat.f_frsize
    check('storage', 'space available', free > 2_000_000_000)
    return dict(mount=mount, free_bytes=free)


def prepare(output):
    storage = mount_check(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    (output/'blocks').mkdir()
    M.logline(output, 'PREPARE: frozen unchanged CT3-flat confirmation; fresh seeds, all nine policies')
    check('integrity', 'completed selection-cohort manifest', M.identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    prior = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    check('integrity', 'previous study complete', prior['status'] == 'COMPLETE')
    preserved = {r['path']: r for group in ('inputs', 'outputs', 'preserved') for r in prior[group]}
    paths = [PREVIOUS/'MANIFEST.json']+[SOURCE/name for name in EXPECTED]
    paths += sorted((S.ROOT/'readback-2026-10-08').iterdir())
    for attempt in sorted(ROOT.glob('attempt-*')):
        if attempt != output:
            paths += sorted(p for p in attempt.rglob('*') if p.is_file())
    for path in paths:
        preserved[str(path)] = M.identity(path)
    M.verify(list(preserved.values()))
    inputs = []
    for name in ('FEP_WEAK_PRIOR_CONFIRMATION_V1.md', Path(__file__).name):
        inputs.append(M.identity(SOURCE/name))
        shutil.copyfile(SOURCE/name, output/'inputs'/name)
    shutil.copyfile(PREVIOUS/'POPULATION.json', output/'POPULATION.json')
    population = json.loads((output/'POPULATION.json').read_text())
    pop = population['bases']
    check('population', 'unchanged entire panel', population == dict(bases=S.population(), conditions=[list(x) for x in S.CONDITIONS],
          arms=list(S.ARMS), coefficients={k: v.tolist() for k, v in S.coefficients().items()}, coefficient_denominator=18))
    seeds = {m['label']: [str(M.seed_for(m['label'], i, PREFIX)) for i in range(1024)] for m in pop}
    flips = {m['label']: [str(M.seed_for(m['label'], i, PREFIX+'-transfer-flips')) for i in range(1024)] for m in pop}
    fresh = {x for values in (seeds, flips) for row in values.values() for x in row}
    check('seeds', 'unique core/flip seeds', len(fresh) == 55296)
    seed_sources = [PREVIOUS/'SEEDS.json']+[ROOT.parent/study/'attempt-01/SEEDS.json' for study in
                  ('fep-changing-world-v1', 'fep-future-aware-checking-v1', 'fep-three-decision-checking-v1')]
    for path in seed_sources:
        old = json.loads(path.read_text())
        previous = {x for group in ('blocks', 'flip_blocks') for row in old.get(group, {}).values() for x in row}
        check('seeds', 'separation from '+str(path), not fresh.intersection(previous))
    for study_prefix in (PREFIX, S.PREFIX, S.T.PREFIX, S.B.PREFIX, 'fep-changing-world-v1'):
        for purpose in ('qualification-', 'parallel-', 'benchmark-'):
            prefix = purpose+study_prefix
            synthetic = {str(M.seed_for(S.A.synthetic()['label'], i, p)) for i in range(128)
                         for p in (prefix, prefix+'-transfer-flips')}
            check('seeds', 'synthetic separation '+prefix, not fresh.intersection(synthetic))
    M.write(output/'SEEDS.json', dict(root=20260924, main_prefix=PREFIX, flip_prefix=PREFIX+'-transfer-flips',
            rng='Python random.Random MT19937', python=platform.python_version(), core_draw_order=M.streams.__doc__,
            flip_draw_order='two random() values per task; each flip iff value < 1/4',
            blocks=seeds, flip_blocks=flips, overlap_with_previous=0, selected_after_previous_results=True))
    inputs += [M.identity(output/'POPULATION.json'), M.identity(output/'SEEDS.json')]
    snapshots = [M.identity(p) for p in sorted((output/'inputs').iterdir())]
    check('integrity', 'source snapshot identity', sorted(x['sha256'] for x in inputs[:2]) == sorted(x['sha256'] for x in snapshots))
    cpus = sorted(os.sched_getaffinity(0))[:4]
    check('resources', 'four CPUs available', len(cpus) == 4)
    M.write(output/'PREPARATION.json', dict(started_utc=M.now(), inputs=inputs, source_snapshots=snapshots,
            preserved=list(preserved.values()), storage=storage, cpus=cpus, python=platform.python_version(), numpy=np.__version__,
            imported_policy=M.identity(SOURCE/'check_fep_calibrated_change.py'), source_manifest=M.identity(PREVIOUS/'MANIFEST.json'),
            primary=PRIMARY, new_policy_implementations=0, new_seeds=True, old_cohort_pooled=False))
    M.logline(output, 'FROZEN: design, wrapper, identical population, both seed sets and all inherited evidence')
    M.pin_cpus(cpus)
    qualification = qualify(cpus)
    M.write(output/'QUALIFICATION.json', qualification)
    M.logline(output, f'QUALIFIED: wrapper {qualification["wrapper_assertions"]} assertions; {qualification["wall_seconds"]:.3f}s')
    jobs = [(S.extend_meta(S.A.synthetic()), list(range(i*32, (i+1)*32)), 'benchmark-'+PREFIX, None) for i in range(4)]
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(cpus,)) as pool:
        records = list(pool.map(S.worker, jobs))
    elapsed = perf_counter()-start
    forecast = 120+3*elapsed*27648/128
    M.write(output/'BENCHMARK.json', dict(wall_seconds=elapsed, forecast_seconds=forecast, requires_detached=forecast > 600,
            workers=4, synthetic_blocks=128, conditions_per_block=19, arms=9, records=records,
            rule='120 + 3 * four-worker wall * 27648 / 128; no outcome selection'))
    M.verify(inputs+snapshots+list(preserved.values()))
    M.logline(output, f'PREPARED: forecast {forecast:.3f}s; detached={forecast > 600}; main outcomes unread')
    print(json.dumps(dict(qualification=qualification, benchmark_seconds=elapsed, forecast_seconds=forecast,
                         requires_detached=forecast > 600, preserved_identities=len(preserved))))


def execute(output, detached):
    start, cpu = perf_counter(), process_time()
    prep = json.loads((output/'PREPARATION.json').read_text())
    bench = json.loads((output/'BENCHMARK.json').read_text())
    check('execution', 'not started', not (output/'EXECUTION_STARTED.json').exists())
    check('execution', 'qualified', json.loads((output/'QUALIFICATION.json').read_text())['status'] == 'PASS')
    check('execution', 'detachment rule', detached or not bench['requires_detached'])
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved'])
    mount_check(output)
    M.pin_cpus(prep['cpus'])
    M.write(output/'EXECUTION_STARTED.json', dict(started_utc=M.now(), pid=os.getpid(), detached=detached,
            workers=4, cpus=prep['cpus'], benchmark=M.identity(output/'BENCHMARK.json'), primary=PRIMARY))
    M.logline(output, 'MAIN STARTED: 216 fixed chunks, 27648 fresh blocks, 513 conditions, nine unchanged arms')
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    jobs = [(meta, list(range(i, i+128)), PREFIX, str(output)) for meta in pop for i in range(0, 1024, 128)]
    records = []
    with ProcessPoolExecutor(max_workers=4, initializer=M.pin_cpus, initargs=(prep['cpus'],)) as pool:
        for i, record in enumerate(pool.map(S.worker, jobs), 1):
            records.append(record)
            if i % 8 == 0:
                M.logline(output, f'COMPLETED {i}/216 chunks; {record["label"]}')
    M.write(output/'WORKERS.json', records)
    results = aggregate(output, pop)
    M.write(output/'RESULTS.json', results)
    M.verify(prep['inputs']+prep['source_snapshots']+prep['preserved']+[r['record'] for r in records])
    M.logline(output, f'COMPLETE: {perf_counter()-start:.3f}s; three frozen criteria and all signed results retained')
    outputs = [M.identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
    M.write(output/'MANIFEST.json', dict(status='COMPLETE', started_utc=json.loads((output/'EXECUTION_STARTED.json').read_text())['started_utc'],
            finished_utc=M.now(), wall_seconds=perf_counter()-start, parent_cpu_seconds=process_time()-cpu,
            worker_cpu_seconds=sum(r['cpu_seconds'] for r in records), workers=4, cpus=prep['cpus'],
            python=platform.python_version(), numpy=np.__version__, inputs=prep['inputs'], preserved=prep['preserved'], outputs=outputs,
            summary=results['summary'], criteria=results['criteria'], core_lead_confirmed=results['core_lead_confirmed'],
            checks=dict(CHECKS), shared_checks=dict(S.CHECKS), identity_checks=dict(M.CHECKS)))


def launch(output):
    check('launch', 'prepared', (output/'BENCHMARK.json').is_file())
    check('launch', 'not launched', not (output/'EXECUTION_STARTED.json').exists() and not (output/'LAUNCH.json').exists())
    with (output/'DETACHED_STDOUT.log').open('xb') as stream:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'execute', '--output', str(output), '--detached'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                cwd=SOURCE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    receipt = dict(pid=child.pid, launched_utc=M.now(), automatic_polling=False, benchmark=M.identity(output/'BENCHMARK.json'))
    M.write(output/'LAUNCH.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'execute', 'launch'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    check('scope', 'dedicated attempt directory', args.output.parent == ROOT and args.output.name.startswith('attempt-'))
    try:
        {'prepare': lambda: prepare(args.output), 'execute': lambda: execute(args.output, args.detached), 'launch': lambda: launch(args.output)}[args.phase]()
    except Exception:
        if args.output.is_dir():
            path = args.output/f'FAILURE_{args.phase}.json'
            if not path.exists():
                M.write(path, dict(phase=args.phase, utc=M.now(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
            M.logline(args.output, f'FAILED {args.phase}; preserve attempt')
        raise
