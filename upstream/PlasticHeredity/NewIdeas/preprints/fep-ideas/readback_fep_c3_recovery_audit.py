#!/usr/bin/env python3
"""Verify saved C3 attribution counts and sums without importing any policy code."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
import argparse
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from time import perf_counter
import traceback
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-c3-recovery-audit-v1')
RUN = ROOT/'attempt-01'
OLD = ROOT.parent/'fep-three-decision-checking-v1/attempt-01'
ARMS = ['F', 'S', 'C', 'R', 'C-Y', 'C2', 'C3']
CONDITIONS = [('stable', 101)]+[(f, t) for f in ('A_loss', 'B_loss', 'reverse') for t in (26, 51, 76)]
ANCHORS = [(0, 26), (0, 51), (0, 76)]+[(i, t) for i, (_, t) in enumerate(CONDITIONS) if i]
PHASES = ['before', 'first_answer', 'after', 'total']
SUMS = ['conditional_cost', 'known_Q_floor', 'insufficient_checking', 'wrong_direction',
        'excess_checking', 'subjective_cost', 'physical_myopic_cost', 'subjective_myopic_cost']
METRICS = ['exposure', 'wrong_cost', 'reference_cost', 'extra_reference_rate', 'cost', 'excess_always']+SUMS+[
    'conditional_regret', 'realization_residual', 'risk_underestimate', 'available_headroom',
    'planning_immediate_effect', 'subjective_immediate_premium']
CHECKS = 0
MAX_ERROR = 0.


def require(ok, description):
    global CHECKS
    if not bool(ok):
        raise AssertionError(description)
    CHECKS += 1


def near(actual, expected, description, tolerance=3e-12):
    global MAX_ERROR
    error = float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
    require(np.isfinite(error) and error <= tolerance, description+': '+str(error))
    MAX_ERROR = max(MAX_ERROR, error)


def identity(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def fingerprint(arrays):
    h = sha256()
    for key, value in sorted(arrays.items()):
        h.update(key.encode()); h.update(str(value.shape).encode())
        h.update(value.dtype.str.encode()); h.update(value.tobytes())
    return h.hexdigest()


def load_arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {k: saved[k] for k in saved.files}


def compare_ci(mean, variance_of_mean, saved, description):
    se = float(np.sqrt(variance_of_mean))
    values = [float(mean), se, float(mean)-1.96*se, float(mean)+1.96*se]
    require(set(saved) == {'mean', 'mc_se', 'lower95', 'upper95'}, description+' fields')
    near(values, [saved[k] for k in ('mean', 'mc_se', 'lower95', 'upper95')], description)


def compare_metric_cube(mean, variance, saved, description):
    # Both arrays have arm x phase x metric axes; variance is for the mean.
    for ai, arm in enumerate(saved):
        for pi, phase in enumerate(PHASES):
            require(set(saved[arm][phase]) == set(METRICS), 'all attribution metrics')
            for mi, metric in enumerate(METRICS):
                compare_ci(mean[ai, pi, mi], variance[ai, pi, mi], saved[arm][phase][metric],
                           description+' '+arm+' '+phase+' '+metric)


def compare_endpoint(values, saved, offset=0):
    # 27 independent strata, 1024 paired blocks in each.
    require(values.shape == (27, 1024, 7), 'original endpoint dimensions')
    for ai, arm in enumerate(ARMS):
        x = values[..., ai]
        compare_ci(x.mean()+offset, x.var(axis=1, ddof=1).sum()/(27**2*1024), saved['arms'][arm], arm)
        if ai < 6:
            d = values[..., 6]-x
            compare_ci(d.mean(), d.var(axis=1, ddof=1).sum()/(27**2*1024),
                       saved['contrasts']['C3_minus_'+arm], 'paired '+arm)
    x = values[..., 6]
    compare_ci(x.mean()+offset-.1, x.var(axis=1, ddof=1).sum()/(27**2*1024), saved['C3_minus_always'], 'always')


def verify():
    started = perf_counter()
    manifest = json.loads((RUN/'MANIFEST.json').read_text())
    prep = json.loads((RUN/'PREPARATION.json').read_text())
    result = json.loads((RUN/'RESULTS.json').read_text())
    prior = json.loads((OLD/'RESULTS.json').read_text())
    require(manifest['status'] == 'COMPLETE' and not list(RUN.rglob('FAILURE*')), 'complete without failure')
    require(manifest['workers'] == 4 and manifest['cpus'] == [0, 1, 2, 3], 'CPU limit')
    for group in ('inputs', 'outputs', 'preserved'):
        for record in manifest[group]:
            require(identity(record['path']) == record, 'identity '+record['path'])
    require({str(p) for p in RUN.rglob('*') if p.is_file() and p.name != 'MANIFEST.json'} ==
            {r['path'] for r in manifest['outputs']}, 'complete output set')
    for record in prep['source_snapshots']+[prep[k] for k in ('source_manifest', 'source_seeds', 'source_population')]:
        require(identity(record['path']) == record, 'source bridge identity')
    require(sorted(r['sha256'] for r in prep['source_snapshots']) == sorted(r['sha256'] for r in manifest['inputs']), 'snapshots')
    require(prep['source_prefix'] == 'fep-three-decision-checking-v1' and not prep['new_seeds'], 'same cohort')
    require(prep['anchors'] == [list(x) for x in ANCHORS] and prep['phases'] == PHASES, 'frozen phase definitions')
    require(prep['sum_fields'] == SUMS and prep['count_fields'] == ['tasks', 'wrong', 'references', 'extra_references'], 'field definitions')
    require(result['summary'] == manifest['summary'], 'manifest summary')
    population = json.loads((OLD/'POPULATION.json').read_text())
    pop = population['bases']
    require(population['arms'] == ARMS and len(pop) == 27, 'population')
    require(population['conditions'] == [list(x) for x in CONDITIONS], 'conditions')
    seeds = json.loads((OLD/'SEEDS.json').read_text())['blocks']
    all_seeds = set()
    for meta in pop:
        expected = [str(int.from_bytes(sha256(f'fep-three-decision-checking-v1|20260924|{meta["label"]}|{i}'.encode()).digest(), 'big')) for i in range(1024)]
        require(seeds[meta['label']] == expected, 'original seed derivation')
        all_seeds.update(expected)
    require(len(all_seeds) == 27648, 'unique blocks')
    records = json.loads((RUN/'WORKERS.json').read_text())
    old_records = {Path(r['record']['path']).name: r for r in json.loads((OLD/'WORKERS.json').read_text())}
    workers = {Path(r['record']['path']).name: r for r in records}
    require(len(records) == len(workers) == len(old_records) == 216, 'all chunks')
    require(all(r['cpus'] == [0, 1, 2, 3] and r['original_arrays'] == 20 for r in records), 'worker CPUs and original array count')
    stable = np.array([1/3]*3+[0]*9)
    changed = np.array([0]*3+[1/9]*9)
    weights = {'full_anchored': (stable+changed)/2, 'stable': stable, 'changed': changed}
    for family in ('A_loss', 'B_loss', 'reverse'):
        weights[family] = np.array([1/3 if CONDITIONS[c][0] == family else 0 for c, t in ANCHORS])
    for tau in (26, 51, 76):
        weights['T'+str(tau)] = np.array([1/3 if c and t == tau else 0 for c, t in ANCHORS])
        weights['stable_T'+str(tau)] = np.array([1 if not c and t == tau else 0 for c, t in ANCHORS])
    require(set(weights) == set(result['groups']) == set(result['analytic_known_law']), 'all groups')
    grouped = {g: [] for g in weights}
    floors, whole, post, condition_names = [], [], [], set()
    length = np.array([101-t for c, t in ANCHORS])
    for meta in pop:
        label = meta['label']
        parts = {k: [] for k in ('first_query', 'phase_counts', 'phase_sums', 'whole_units')}
        for first in range(0, 1024, 128):
            name = f'{label}_{first:04d}_{first+127:04d}.npz'
            arrays, old = load_arrays(RUN/'blocks'/name), load_arrays(OLD/'blocks'/name)
            record = workers[name]
            require((record['label'], record['first'], record['last']) == (label, first, first+127), 'chunk metadata')
            require(fingerprint(arrays) == record['fingerprint'], 'audit fingerprint')
            require(len(old) == 20 and fingerprint(old) == record['original_fingerprint'] == old_records[name]['fingerprint'], 'recorded original replay fingerprint')
            require(np.array_equal(arrays['indices'], np.arange(first, first+128)), 'block indices')
            require(set(arrays) == {'indices', *parts}, 'array fields')
            for key in parts:
                require(np.isfinite(arrays[key]).all(), 'finite '+key)
                parts[key].append(arrays[key])
            c, s, k = arrays['phase_counts'], arrays['phase_sums'], arrays['first_query']
            require(c.shape == (128, 12, 7, 3, 4) and s.shape == (128, 12, 7, 3, 8), 'trace shapes')
            require(c.dtype == np.int16 and k.dtype == np.int16 and s.dtype == np.float64, 'trace dtypes')
            require((c >= 0).all() and (c[..., 1]+c[..., 2] <= c[..., 0]).all() and (c[..., 3] <= c[..., 2]).all(), 'count bounds')
            require(not c[:, :, :5, :, 3].any(), 'old controls have no extra checks')
            require(not c[..., 0, 2].any() and not c[..., 1, 1].any(), 'before/first action accounting')
            require(np.array_equal(c[..., 1, 0], c[..., 1, 2]) and np.array_equal(c[..., 1, 0], k < 101), 'first check indicator')
            require(np.array_equal(arrays['whole_units'], 10*old['wrong']+old['references']), 'whole episode counts')
            near(s[..., 0]-s[..., 1], s[..., 2:5].sum(axis=-1), 'regret identity')
            near(s[..., 1].sum(axis=-1), np.broadcast_to(s[..., 1].sum(axis=-1)[:, :, :1], (128, 12, 7)), 'same task floor')
            near(s[:, :, :5, :, 0], s[:, :, :5, :, 6], 'myopic physical controls')
            near(s[:, :, :5, :, 5], s[:, :, :5, :, 7], 'myopic subjective controls')
            require((s[..., 5]-s[..., 7] >= -3e-12).all(), 'nonnegative subjective premium')
            for j, (condition, tau) in enumerate(ANCHORS):
                require(((k[:, j] >= tau) & (k[:, j] <= 101)).all(), 'query range')
                require(np.array_equal(c[:, j, :, 0, 0], k[:, j]-tau), 'waiting with censoring')
                require((c[:, j, :, :, 0].sum(axis=-1) == 101-tau).all(), 'fixed exposure')
                wi = (tau-26)//25
                for field, ci in [('window_wrong', 1), ('window_references', 2)]:
                    require(np.array_equal(c[:, j, :, :, ci].sum(axis=-1), old[field][:, condition, :, wi:].sum(axis=-1)), 'window bridge '+field)
                if condition:
                    require(np.array_equal(k[:, j], old['first_post_reference'][:, condition]), 'original first check')
                    require(np.array_equal(c[:, j, :, :, 1].sum(axis=-1), old['post_wrong'][:, condition]), 'post errors')
                    require(np.array_equal(c[:, j, :, :, 2].sum(axis=-1), old['post_references'][:, condition]), 'post checks')
                    for ai, field in [(5, 'c2_extra_references'), (6, 'extra_references')]:
                        require(np.array_equal(c[:, j, ai, :, 3].sum(axis=-1), old[field][:, condition, 1]), 'post extra checks')
                        require(np.array_equal(c[:, j, ai, 2, 3], old[field][:, condition, 2]), 'after extra checks')
        c = np.concatenate(parts['phase_counts']).astype(np.int64)
        s = np.concatenate(parts['phase_sums'])
        k = np.concatenate(parts['first_query'])
        whole.append(np.concatenate(parts['whole_units']).astype(np.int64))
        pc = c[:, 3:].sum(axis=-2)
        post.append(np.concatenate([np.zeros((1024, 1, 7), dtype=np.int64), 10*pc[..., 1]+pc[..., 2]], axis=1))
        c = np.concatenate([c, c.sum(axis=-2, keepdims=True)], axis=-2)
        s = np.concatenate([s, s.sum(axis=-2, keepdims=True)], axis=-2)
        n, wrong, references, extra = [c[..., i]/length[None, :, None, None] for i in range(4)]
        scaled = s/length[None, :, None, None, None]
        cost = wrong+.1*references
        metrics = [n, wrong, .1*references, extra, cost, cost-.1*n]+[scaled[..., i] for i in range(8)]+[
            scaled[..., 2:5].sum(axis=-1), cost-scaled[..., 0], scaled[..., 0]-scaled[..., 5],
            .1*n-scaled[..., 1], scaled[..., 0]-scaled[..., 6], scaled[..., 5]-scaled[..., 7]]
        values = np.stack(metrics, axis=-1)
        near(values[..., 5], values[..., 14]-values[..., 17]+values[..., 15], 'signed excess identity')
        near(values[..., :3, :].sum(axis=-2), values[..., 3, :], 'phase closure')
        query = np.stack([k < 101, c[..., 0, 0]], axis=-1).astype(float)
        means, variances = values.mean(axis=0), values.var(axis=0, ddof=1)/1024
        qm, qv = query.mean(axis=0), query.var(axis=0, ddof=1)/1024
        law_floors = []
        for j, (condition, tau) in enumerate(ANCHORS):
            family = CONDITIONS[condition][0]
            key = f'{label}__{family}_{tau}'
            condition_names.add(key)
            saved = result['conditions'][key]
            require(saved['base'] == label and saved['analysis_tau'] == tau and saved['original_condition'] == list(CONDITIONS[condition]), 'condition metadata')
            compare_metric_cube(means[j], variances[j], {arm: saved['arms'][arm] for arm in ARMS}, key)
            for ai, arm in enumerate(ARMS):
                for qi, name in enumerate(('purchase_probability', 'waiting_tasks')):
                    compare_ci(qm[j, ai, qi], qv[j, ai, qi], saved['query'][arm][name], 'condition query')
            q = list(map(Fraction, meta['laws'][('stable', 'A_loss', 'B_loss', 'reverse').index(family)]))
            joint = [[Fraction(0) for w in (0, 1)] for y in range(4)]
            for w in (0, 1):
                for error, probability in enumerate(q):
                    joint[(3*w) ^ error][w] += probability/2
            floor = sum(min(row[0], row[1], sum(row)/10) for row in joint)
            law_floors.append(floor)
            require(saved['analytic_floor'] == dict(rational=str(floor), mean=float(floor),
                headroom=float(Fraction(1, 10)-floor), positive_headroom=floor < Fraction(1, 10)), 'exact condition floor')
        floors.append(law_floors)
        for group, w in weights.items():
            v = np.tensordot(values, w, axes=(1, 0)).transpose(0, 1, 2, 3)
            # First average overlapping conditions/anchors within a block.
            d = v[:, 6:7]-v[:, :6]
            z = np.tensordot(query, w, axes=(1, 0))
            grouped[group].append((v.mean(axis=0), v.var(axis=0, ddof=1),
                                   d.mean(axis=0), d.var(axis=0, ddof=1), z.mean(axis=0), z.var(axis=0, ddof=1)))
    require(condition_names == set(result['conditions']), 'all 324 condition/anchor records')
    for group, rows in grouped.items():
        stat = [np.stack([row[i] for row in rows]) for i in range(6)]
        mean, variance, delta, delta_variance, query_mean, query_variance = [
            a.mean(axis=0) if i % 2 == 0 else a.sum(axis=0)/(27**2*1024) for i, a in enumerate(stat)]
        saved = result['groups'][group]
        compare_metric_cube(mean, variance, {a: saved['arms'][a] for a in ARMS}, group)
        compare_metric_cube(delta, delta_variance, {'C3_minus_'+a: saved['contrasts']['C3_minus_'+a] for a in ARMS[:6]}, group+' paired')
        for ai, arm in enumerate(ARMS):
            for qi, name in enumerate(('purchase_probability', 'waiting_tasks')):
                compare_ci(query_mean[ai, qi], query_variance[ai, qi], saved['query'][arm][name], group+' query')
        rational_weights = [Fraction(float(w)).limit_denominator(18) for w in weights[group]]
        floor = sum(w*floors[b][j] for b in range(27) for j, w in enumerate(rational_weights))/27
        selected = [floors[b][j] for b in range(27) for j, w in enumerate(rational_weights) if w]
        require(result['analytic_known_law'][group] == dict(rational_floor=str(floor), floor=float(floor),
            headroom=float(Fraction(1, 10)-floor), analysis_rows=len(selected),
            positive_headroom_rows=sum(f < Fraction(1, 10) for f in selected),
            zero_headroom_rows=sum(f == Fraction(1, 10) for f in selected)), 'exact group floor '+group)
    whole, post = np.stack(whole), np.stack(post)
    coefficients = {'full': [9]+[1]*9, 'stable': [18]+[0]*9, 'changed': [0]+[2]*9}
    for family in ('A_loss', 'B_loss', 'reverse'):
        coefficients[family] = [6 if f == family else 0 for f, t in CONDITIONS]
    for tau in (26, 51, 76):
        coefficients['T'+str(tau)] = [6 if t == tau else 0 for f, t in CONDITIONS]
    for group, co in coefficients.items():
        value = sum(weight*whole[:, :, j] for j, weight in enumerate(co))/18000
        compare_endpoint(value, result['original_episode'][group], .00064)
        compare_endpoint(value, prior['episode'][group], .00064)
        if group not in ('full', 'stable'):
            pc = [0 if t == 101 else weight*150//(101-t) for weight, (_, t) in zip(co, CONDITIONS)]
            value = sum(weight*post[:, :, j] for j, weight in enumerate(pc))/27000
            compare_endpoint(value, result['original_post_change'][group])
            compare_endpoint(value, prior['post_change'][group])
    for endpoint, data in [('episode', whole), ('post_change', post)]:
        counts = {}
        for ai, arm in enumerate(ARMS[:6]):
            tally = dict(point_lower=0, point_equal=0, point_higher=0, upper_below_zero=0, lower_above_zero=0)
            for bi in range(27):
                for j, (family, tau) in enumerate(CONDITIONS):
                    if endpoint == 'post_change' and not j:
                        continue
                    difference = data[bi, :, j, 6]-data[bi, :, j, ai]
                    den = 1000 if endpoint == 'episode' else 10*(101-tau)
                    total = int(difference.sum())
                    mean = total/1024/den
                    se = float(difference.std(ddof=1)/np.sqrt(1024)/den)
                    for key, yes in [('point_lower', total < 0), ('point_equal', total == 0), ('point_higher', total > 0),
                                     ('upper_below_zero', mean+1.96*se < 0), ('lower_above_zero', mean-1.96*se > 0)]:
                        tally[key] += int(yes)
            counts[arm] = tally
        require(counts == result['original_condition_counts'][endpoint] == prior['condition_counts'][endpoint], 'original condition signs '+endpoint)
    criteria = dict(economical_recovery=result['original_post_change']['changed']['C3_minus_always']['upper95'] < 0,
        overall_useful_function=result['original_episode']['full']['C3_minus_always']['upper95'] < 0,
        value_of_longer_horizon=result['original_post_change']['changed']['contrasts']['C3_minus_C2']['upper95'] < 0)
    require(criteria == result['original_criteria'] == manifest['original_criteria'] == prior['criteria'], 'original verdicts')
    c3 = result['groups']['changed']['arms']['C3']
    return dict(status='PASS', verified_utc=datetime.now(timezone.utc).isoformat(), assertions=CHECKS,
        max_absolute_comparison_error=MAX_ERROR, wall_seconds=perf_counter()-started,
        verifier=identity(__file__), manifest=identity(RUN/'MANIFEST.json'),
        identity_counts={g: len(manifest[g]) for g in ('inputs', 'outputs', 'preserved')},
        record_bytes=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()), chunks=216,
        original_array_comparisons_recorded=4320, independent_blocks=27648, original_criteria=criteria,
        phase_fraction_of_net_excess=c3['after']['excess_always']['mean']/c3['total']['excess_always']['mean'],
        analytic_known_law=result['analytic_known_law'], groups=result['groups'],
        original_condition_counts=result['original_condition_counts'],
        original_episode=result['original_episode'], original_post_change=result['original_post_change'],
        limitations='Independent aggregation by the same author, no new simulation. Original replay fingerprints and its 4320 recorded array comparisons verified against original chunks; original policies not rerun at readback. Endogenous phases and immediate contrasts do not identify total causal effects.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output
    require(output.parent == ROOT and output.name.startswith('readback-'), 'separate external destination')
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    require(mount == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'), 'verified external mount')
    output.mkdir(exist_ok=False)
    (output/'VERIFIER.py').write_bytes(Path(__file__).read_bytes())
    try:
        result = verify()
        (output/'READBACK.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
        brief = {k: result[k] for k in ('status', 'assertions', 'max_absolute_comparison_error', 'wall_seconds', 'manifest', 'identity_counts', 'record_bytes', 'original_criteria', 'phase_fraction_of_net_excess')}
        (output/'READBACK_LOG.txt').write_text(json.dumps(brief, indent=2)+'\n')
        print(json.dumps(brief, indent=2))
    except Exception:
        (output/'FAILURE.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), assertions=CHECKS, traceback=traceback.format_exc()), indent=2)+'\n')
        raise
