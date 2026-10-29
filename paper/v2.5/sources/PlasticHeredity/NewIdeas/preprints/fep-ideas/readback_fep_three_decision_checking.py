#!/usr/bin/env python3
"""Read-only reconstruction of the sealed C3 study; no simulation or policy calls."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-three-decision-checking-v1')
RUN = ROOT/'attempt-01'
ARMS = ['F', 'S', 'C', 'R', 'C-Y', 'C2', 'C3']
CHECKS = 0


def require(condition, description):
    global CHECKS
    if not condition:
        raise AssertionError(description)
    CHECKS += 1


def identity(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def ci(numerator, denominator=1, offset=0):
    a = np.asarray(numerator)
    if a.ndim == 1:
        a = a[None, :]
    require(a.shape[1] == 1024, 'independent block count')
    values = a.astype(float)/denominator
    mean = (int(a.sum()) if a.dtype.kind in 'iu' else float(a.sum()))/a.size/denominator+offset
    se = float(np.sqrt(np.var(values, axis=1, ddof=1).sum()/(a.shape[0]**2*a.shape[1])))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def compare(actual, expected, description):
    require(set(actual) == set(expected), description+' keys')
    for key in actual:
        require(abs(actual[key]-expected[key]) < 3e-12, description+' '+key)


def compare_arms(num, den, offset, saved):
    for ai, arm in enumerate(ARMS):
        compare(ci(num[..., ai], den, offset), saved['arms'][arm], arm)
        if ai < 6:
            compare(ci(num[..., 6]-num[..., ai], den), saved['contrasts']['C3_minus_'+arm], 'paired '+arm)
    compare(ci(num[..., 6], den, offset-.1), saved['C3_minus_always'], 'always')


def verify():
    manifest = json.loads((RUN/'MANIFEST.json').read_text())
    require(manifest['status'] == 'COMPLETE', 'sealed completion')
    require(not list(RUN.glob('FAILURE*')), 'no saved execution failure')
    require(manifest['workers'] == 4 and manifest['cpus'] == [0, 1, 2, 3], 'main CPU ceiling')
    for group in ('inputs', 'outputs', 'preserved'):
        for record in manifest[group]:
            require(identity(record['path']) == record, 'identity '+record['path'])
    require({str(p) for p in RUN.rglob('*') if p.is_file() and p.name != 'MANIFEST.json'} ==
            {r['path'] for r in manifest['outputs']}, 'complete recorded output set')
    pop = json.loads((RUN/'POPULATION.json').read_text())
    require(pop['arms'] == ARMS and len(pop['bases']) == 27, 'population and arms')
    conditions = [('stable', 101)]+[(family, t) for family in ('A_loss', 'B_loss', 'reverse') for t in (26, 51, 76)]
    require(pop['conditions'] == [list(x) for x in conditions], 'condition order')
    seeds = json.loads((RUN/'SEEDS.json').read_text())
    new = set()
    for meta in pop['bases']:
        label = meta['label']
        expected = [str(int.from_bytes(sha256(f'fep-three-decision-checking-v1|20260924|{label}|{i}'.encode()).digest(), 'big')) for i in range(1024)]
        require(seeds['blocks'][label] == expected, 'seed derivation '+label)
        new.update(expected)
    require(len(new) == 27648, 'unique seeds')
    for previous in ('fep-changing-world-v1', 'fep-future-aware-checking-v1'):
        old = json.loads((ROOT.parent/previous/'attempt-01/SEEDS.json').read_text())['blocks']
        require(not new.intersection(x for row in old.values() for x in row), 'seed separation '+previous)
    workers = json.loads((RUN/'WORKERS.json').read_text())
    require(len(workers) == 216 and all(r['cpus'] == [0, 1, 2, 3] for r in workers), 'all worker records')
    records = {r['record']['path']: r for r in workers}
    fields = ['wrong', 'references', 'post_wrong', 'post_references', 'window_wrong', 'window_references',
              'extra_references', 'own_c2_disagreements', 'delta_sum', 'selected_gain_sum']
    rows = {k: [] for k in fields}
    fallbacks = {k: np.zeros(3, dtype=np.int64) for k in ('planner_fallbacks', 'control_fallback', 'c2_inference_fallback', 'c3_inference_fallback')}
    for meta in pop['bases']:
        parts = {k: [] for k in fields}
        for first in range(0, 1024, 128):
            path = RUN/'blocks'/f'{meta["label"]}_{first:04d}_{first+127:04d}.npz'
            with np.load(path, allow_pickle=False) as saved:
                arrays = {k: saved[k] for k in saved.files}
            require(np.array_equal(arrays['indices'], np.arange(first, first+128)), 'complete indices')
            digest = sha256()
            for key, a in sorted(arrays.items()):
                digest.update(key.encode()); digest.update(str(a.shape).encode())
                digest.update(a.dtype.str.encode()); digest.update(a.tobytes())
            require(digest.hexdigest() == records[str(path)]['fingerprint'], 'array fingerprint')
            for key in fields:
                require(np.isfinite(arrays[key]).all(), 'finite '+key)
                parts[key].append(arrays[key].astype(np.int64) if arrays[key].dtype.kind in 'iu' else arrays[key])
            for key in fallbacks:
                fallbacks[key] += arrays[key]
        for key in fields:
            rows[key].append(np.concatenate(parts[key], axis=0))
    rows = {k: np.stack(v) for k, v in rows.items()}
    r = json.loads((RUN/'RESULTS.json').read_text())
    require(r['summary'] == manifest['summary'], 'summary consistency')
    require({k: v.tolist() for k, v in fallbacks.items()} == r['fallbacks'], 'fallback totals')
    units = 10*rows['wrong']+rows['references']
    post = 10*rows['post_wrong']+rows['post_references']
    window = 10*rows['window_wrong']+rows['window_references']
    require(units.shape == (27, 1024, 10, 7), 'complete cohort shape')
    require(np.all(rows['wrong']+rows['references'] <= 100), 'episode accounting')
    require(not post[:, :, 0].any(), 'no stable post-change endpoint')
    for j, (_, t) in enumerate(conditions[1:], 1):
        require(np.array_equal(post[:, :, j], window[:, :, j, :, (t-26)//25:].sum(axis=-1)), 'post/window accounting')
        require(np.all(rows['post_wrong'][:, :, j]+rows['post_references'][:, :, j] <= 101-t), 'post count ceiling')
    groups = {'full': [9]+[1]*9, 'stable': [18]+[0]*9, 'changed': [0]+[2]*9}
    for family in ('A_loss', 'B_loss', 'reverse'):
        groups[family] = [6 if f == family else 0 for f, _ in conditions]
    for t in (26, 51, 76):
        groups['T'+str(t)] = [6 if tau == t else 0 for _, tau in conditions]
    require(np.allclose(np.array(list(groups.values()))/18, pop['group_weights'], rtol=0, atol=1e-15), 'frozen weights')
    weighted = lambda a, weights: sum(w*a[:, :, j] for j, w in enumerate(weights))
    components = {}
    for group, weights in groups.items():
        compare_arms(weighted(units, weights), 18000, .00064, r['episode'][group])
        if group not in ('full', 'stable'):
            pw = [0 if t == 101 else w*150//(101-t) for w, (_, t) in zip(weights, conditions)]
            compare_arms(weighted(post, pw), 27000, 0, r['post_change'][group])
        for field, names in [('extra_references', ['extra_references', 'post_extra_references', 'extras_after_first_post_answer']),
                             ('own_c2_disagreements', ['C3_buys_own_C2_reports', 'C3_reports_own_C2_buys'])]:
            values = weighted(rows[field], weights)
            for i, name in enumerate(names):
                compare(ci(values[..., i], 18), r['planning'][group][name], name)
        for field in ('delta_sum', 'selected_gain_sum'):
            compare(ci(weighted(rows[field], weights), 18), r['planning'][group][field], field)
    for endpoint, data in [('episode', units), ('post_change', post)]:
        counts = {arm: dict(point_lower=0, point_equal=0, point_higher=0, upper_below_zero=0, lower_above_zero=0) for arm in ARMS[:6]}
        for bi, meta in enumerate(pop['bases']):
            for j, (family, t) in enumerate(conditions):
                if endpoint == 'post_change' and family == 'stable':
                    continue
                saved = r['conditions'][f'{meta["label"]}__{family}_{t}']
                den, offset = (1000, .00064) if endpoint == 'episode' else (10*(101-t), 0)
                for ai, arm in enumerate(ARMS):
                    compare(ci(data[bi, :, j, ai], den, offset), saved['arms'][arm][endpoint], 'condition '+arm)
                    if ai < 6:
                        delta = data[bi, :, j, 6]-data[bi, :, j, ai]
                        value = ci(delta, den)
                        compare(value, saved['contrasts']['C3_minus_'+arm][endpoint], 'condition paired '+arm)
                        total = int(delta.sum())
                        for key, yes in [('point_lower', total < 0), ('point_equal', total == 0), ('point_higher', total > 0),
                                         ('upper_below_zero', value['upper95'] < 0), ('lower_above_zero', value['lower95'] > 0)]:
                            counts[arm][key] += int(yes)
        require(counts == r['condition_counts'][endpoint], 'all condition signs '+endpoint)
    for wi, t in enumerate((26, 51, 76)):
        selected = [j for j, (_, tau) in enumerate(conditions) if tau == t]
        compare_arms(sum(window[:, :, j, :, wi] for j in selected), 750, 0, r['first_25_task_mean_cost'][str(t)]['changed'])
        compare_arms(window[:, :, 0, :, wi], 250, 0, r['first_25_task_mean_cost'][str(t)]['stable'])
    expected_criteria = dict(economical_recovery=r['post_change']['changed']['C3_minus_always']['upper95'] < 0,
        overall_useful_function=r['episode']['full']['C3_minus_always']['upper95'] < 0,
        value_of_longer_horizon=r['post_change']['changed']['contrasts']['C3_minus_C2']['upper95'] < 0)
    require(expected_criteria == r['criteria'] == manifest['criteria'], 'three criteria')
    require(r['complete_proposed_improvement_supported'] == all(expected_criteria.values()), 'complete claim')
    for group in ('full', 'changed'):
        weights = groups[group]
        components[group] = {arm: dict(wrong_cost=float(weighted(rows['wrong'], weights)[..., ai].mean()/1800),
            reference_cost=float(weighted(rows['references'], weights)[..., ai].mean()/18000), calibration_cost=.00064)
            for ai, arm in enumerate(ARMS)}
    weights = [0]+[2]*9
    pw = [0 if t == 101 else w*150//(101-t) for w, (_, t) in zip(weights, conditions)]
    components['post_change'] = {arm: dict(wrong_cost=float(weighted(rows['post_wrong'], pw)[..., ai].mean()/2700),
        reference_cost=float(weighted(rows['post_references'], pw)[..., ai].mean()/27000)) for ai, arm in enumerate(ARMS)}
    return dict(status='PASS', verified_utc=datetime.now(timezone.utc).isoformat(), assertions=CHECKS,
        manifest=identity(RUN/'MANIFEST.json'), source=identity(__file__), identity_counts={k: len(manifest[k]) for k in ('inputs', 'outputs', 'preserved')},
        record_bytes=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()), chunks=216, seed_overlap=0,
        main_wall_seconds=manifest['wall_seconds'], worker_cpu_seconds=manifest['worker_cpu_seconds'], parent_cpu_seconds=manifest['parent_cpu_seconds'],
        criteria=expected_criteria, components=components, condition_counts=r['condition_counts'],
        episode=r['episode'], post_change=r['post_change'], windows=r['first_25_task_mean_cost'], planning=r['planning'],
        limitations='Independent aggregation code, same author; no scientific rerun and no causal attribution of individual checks.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        require(args.output.parent == ROOT and args.output.name.startswith('readback-'), 'separate readback destination')
        mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
        require(mount == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'), 'external mount')
        args.output.mkdir(exist_ok=False)
        (args.output/'VERIFIER.py').write_bytes(Path(__file__).read_bytes())
        with (args.output/'READBACK.json').open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'assertions', 'manifest', 'identity_counts', 'record_bytes', 'criteria')}, indent=2))
