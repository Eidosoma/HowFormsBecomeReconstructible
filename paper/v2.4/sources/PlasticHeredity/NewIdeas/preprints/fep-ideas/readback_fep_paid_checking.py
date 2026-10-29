#!/usr/bin/env python3
"""Independent saved-trace accounting and scalar-loop intervals; no policy runs."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import json
import math
from pathlib import Path
from time import perf_counter
import traceback
import numpy as np
import run_fep_paid_checking as P

C = P.C
CHECKS = {}


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def close(name, left, right, atol=3e-12):
    check(name, np.shape(left) == np.shape(right) and np.allclose(left, right, atol=atol, rtol=0))


def rebuild(raw, meta):
    b, nc, na, nt = raw['actions'].shape
    check('trace_dimensions', (nc, na, nt) == (25, 2, 100))
    shape = (b, nc, 2)
    out = dict(counts=np.zeros(shape+(2, 3), dtype=np.int64), sums=np.zeros(shape+(2, 6)),
               phase_counts=np.zeros(shape+(3, 3), dtype=np.int64), phase_sums=np.zeros(shape+(3, 6)),
               first=np.full(shape, 101, dtype=np.int64), confident_agreement=np.zeros(shape+(2, 3), dtype=np.int64),
               extra_counts=np.zeros(shape+(2,), dtype=np.int64), alarm=np.zeros(shape+(3,)),
               posterior_final=np.zeros(shape+(2,)), audit_counts=np.zeros(shape+(2, 3), dtype=np.int64),
               predictive=np.zeros(shape+(3, 4)))
    times = np.arange(1, 101)
    check('same_physical_truth', np.all(raw['truth'] == raw['truth'][:, 0:1]))
    check('finite_traces', all(np.all(np.isfinite(v)) for v in raw.values()))
    check('calibration_size', np.all(raw['calibration'].sum(axis=-1) == 64) and np.all(raw['calibration'] >= 0))
    for j, (family, onset) in enumerate(P.CONDITIONS):
        oldq = np.array([float(C.F(x)) for x in meta['laws'][0]])
        newq = oldq if family == 'stable' else np.array([float(C.F(x)) for x in meta['laws'][1+C.U.FAMILIES.index(family)]])
        laws = np.array([newq if t >= onset else oldq for t in times])
        for block in range(b):
            warning, target = raw['warnings'][block, j], raw['truth'][block, j]
            check('physical_range', np.all((warning >= 0) & (warning <= 3)) and np.all((target >= 0) & (target <= 1)))
            for arm in range(2):
                index = (block, j, arm)
                action, proposed, u = raw['actions'][index], raw['planned_actions'][index], raw['subjective_u'][index]
                paid = action == 2
                wrong = (action != target) & ~paid
                extra = raw['extra'][index]
                check('action_range', np.all((action >= 0) & (action <= 2)) and np.all((proposed >= 0) & (proposed <= 2)))
                check('feedback_exact_mask', np.array_equal(raw['labels'][index],
                      [int(target[t]) if paid[t] else -1 for t in range(100)]))
                check('belief_range', np.all((u >= -1e-13) & (u <= 1+1e-13)))
                check('extra_ct4_is_planned_purchase', np.all(~extra | (proposed == 2)))
                check('information_sign_terminal', np.all(raw['information'][index] >= -2e-12) and raw['information'][index][-1] == 0)
                last, expected_gap, expected_due, expected_forced, expected_action = 0, [], [], [], []
                for t, plan in enumerate(proposed, 1):
                    gap = t-last
                    due = arm == 1 and gap >= 2
                    forced = due and plan != 2
                    actual = 2 if due else int(plan)
                    expected_gap.append(gap); expected_due.append(due)
                    expected_forced.append(forced); expected_action.append(actual)
                    if actual == 2:
                        last = t
                    check('feedback_gap_bound', arm == 0 or t-last <= 1)
                for key, value in (('gap_before', expected_gap), ('due', expected_due),
                                   ('forced', expected_forced), ('actions', expected_action)):
                    close('independent_clock_'+key, raw[key][index], value, 0)
                due, forced = np.array(expected_due), np.array(expected_forced)
                check('no_double_purchase', np.all(~due | paid) and not np.any(forced & extra))
                confident = np.array([yy in (0, 3) and min(p, 1-p) < .1 for yy, p in zip(warning, u)])
                probability = np.array([[q[yy], q[yy ^ 3]] for q, yy in zip(laws, warning)])
                probability /= probability.sum(axis=1, keepdims=True)
                best = probability.min(axis=1)
                conditional = np.array([.1 if a == 2 else p[1-a] for a, p in zip(action, probability)])
                floor = np.minimum(best, .1)
                insufficient = np.array([0. if a == 2 else max(e-.1, 0.) for a, e in zip(action, best)])
                direction = np.array([0. if a == 2 else p[1-a]-e for a, p, e in zip(action, probability, best)])
                excess = np.array([max(.1-e, 0.) if a == 2 else 0. for a, e in zip(action, best)])
                subjective = np.array([.1 if a == 2 else (p if a == yy >> 1 else 1-p) for a, p, yy in zip(action, u, warning)])
                close('independent_regret_identity', conditional-floor, insufficient+direction+excess, 2e-15)
                metrics = np.column_stack((conditional, floor, insufficient, direction, excess, subjective))
                prediction = np.array([1-p if yy >> 1 else p for yy, p in zip(warning, u)])
                preferred = np.array([(yy >> 1) ^ (p > .5) for yy, p in zip(warning, u)])
                preferred_regret = np.array([p[1-a]-e for p, a, e in zip(probability, preferred, best)])
                pred = np.column_stack((np.ones(100), np.abs(prediction-probability[:, 1]),
                                        preferred_regret > 1e-14, preferred_regret))
                post = times >= onset
                purchased = times[post & paid]
                first = int(purchased[0]) if len(purchased) else 101
                out['first'][index] = first
                check('first_purchase_bound', arm == 0 or j == 0 or onset <= first <= onset+1)
                for segment, keep in enumerate((np.ones(100, dtype=bool), post)):
                    out['counts'][index+(segment,)] = (sum(keep), sum(wrong & keep), sum(paid & keep))
                    out['sums'][index+(segment,)] = metrics[keep].sum(axis=0)
                    out['confident_agreement'][index+(segment,)] = (sum(confident & keep), sum(confident & paid & keep), sum(confident & wrong & keep))
                    out['extra_counts'][index+(segment,)] = sum(extra & keep)
                    out['audit_counts'][index+(segment,)] = (sum(due & keep), sum(forced & keep), sum(forced & confident & keep))
                for phase, keep in enumerate((post & (times < first), post & (times == first), post & (times > first))):
                    out['phase_counts'][index+(phase,)] = (sum(keep), sum(wrong & keep), sum(paid & keep))
                    out['phase_sums'][index+(phase,)] = metrics[keep].sum(axis=0)
                    out['predictive'][index+(phase,)] = pred[keep].sum(axis=0)
                posterior = raw['posterior'][index]
                check('posterior_ranges', np.all(posterior >= -2e-13) and np.all(posterior <= 1+2e-13)
                      and np.all(posterior[:, 1] <= posterior[:, 0]+1e-13))
                alarm = times[posterior[:, 0] > .5]
                out['alarm'][index] = (len(alarm), int(alarm[0]) if len(alarm) else 101, sum(posterior[:, 0]))
                out['posterior_final'][index] = posterior[-1]
    return out


def stats(saved, rows):
    b, n = len(rows), len(rows[0])
    check('scalar_rows_rectangular', n > 1 and all(len(row) == n for row in rows))
    means = [math.fsum(map(float, row))/n for row in rows]
    mean = math.fsum(means)/b
    variances = [math.fsum((float(v)-mu)**2 for v in row)/(n-1) for row, mu in zip(rows, means)]
    se = math.sqrt(math.fsum(variances)/(b*b*n))
    expected = dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)
    check('interval_fields', set(saved) == set(expected))
    for key, value in expected.items():
        close('scalar_interval_'+key, saved[key], value)


def rows(data, selected, function):
    """Explicit base, block and condition loops; no NumPy advanced indexing."""
    b, n = data['counts'].shape[:2]
    return [[math.fsum(float(function(bi, i, j)) for j in selected)/len(selected)
             for i in range(n)] for bi in range(b)]


def cost_rows(data, selected, segment):
    counts = data['counts']
    b, n = counts.shape[:2]
    return [[[math.fsum((int(counts[bi, i, j, a, segment, 1])+
                        int(counts[bi, i, j, a, segment, 2])/10)/
                        int(counts[bi, i, j, a, segment, 0]) for j in selected)/len(selected)
              for a in range(2)] for i in range(n)] for bi in range(b)]


def cost_panel(saved, value):
    for a, arm in enumerate(P.ARMS):
        stats(saved['arms'][arm], [[v[a] for v in row] for row in value])
        stats(saved['against_always'][arm], [[v[a]-.1 for v in row] for row in value])
    stats(saved['gap1_minus_baseline'], [[v[1]-v[0] for v in row] for row in value])


def total(data, key, selected, suffix):
    b, n = data['counts'].shape[:2]
    return math.fsum(float(data[key][(bi, i, j)+suffix])
                     for bi in range(b) for i in range(n) for j in selected)


def verify_results(saved, data, pop):
    b, n = data['counts'].shape[:2]
    check('result_sample', (saved['blocks_per_base'], saved['independent_blocks'], saved['physical_episodes'],
                          saved['policy_decisions']) == (n, b*n, b*n*25, b*n*25*200))
    check('result_arms', tuple(saved['arms']) == P.ARMS)
    groups = {f: [j for j, (family, _) in enumerate(P.CONDITIONS) if family == f]
              for f in ('stable',)+C.U.FAMILIES}
    groups.update(core=sum([groups[f] for f in ('A_loss', 'B_loss', 'reverse')], []),
                  transfer=sum([groups[f] for f in ('A_partial', 'B_partial', 'both_partial')], []),
                  non_reversal=[j for j, (f, _) in enumerate(P.CONDITIONS) if f not in ('stable', 'reverse')],
                  all_changes=list(range(1, 25)))
    check('complete_groups', set(saved['panels']) == set(groups) == set(saved['diagnostics']))
    for name, selected in groups.items():
        for s, segment in enumerate(('episode', 'post_change')):
            if name == 'stable' and s:
                continue
            cost_panel(saved['panels'][name][segment], cost_rows(data, selected, s))
            for a, arm in enumerate(P.ARMS):
                d = saved['diagnostics'][name][arm][segment]
                for k, metric in enumerate(C.SUMS):
                    stats(d[metric], rows(data, selected, lambda bi, i, j:
                          data['sums'][bi, i, j, a, s, k]/data['counts'][bi, i, j, a, s, 0]))
                for metric, entry, factor in (('error_cost', 1, 1), ('purchase_cost', 2, .1)):
                    stats(d[metric], rows(data, selected, lambda bi, i, j:
                          factor*data['counts'][bi, i, j, a, s, entry]/data['counts'][bi, i, j, a, s, 0]))
                stats(d['forced_purchase_fraction'], rows(data, selected, lambda bi, i, j:
                      data['audit_counts'][bi, i, j, a, s, 1]/data['counts'][bi, i, j, a, s, 0]))
                for name_saved, field in (('count_totals', 'counts'), ('audit_totals', 'audit_counts'),
                                          ('confident_agreement_totals', 'confident_agreement')):
                    close('diagnostic_'+name_saved, d[name_saved],
                          [total(data, field, selected, (a, s, k)) for k in range(3)], 0)
                check('extra_ct4_purchase_total', d['extra_ct4_purchases'] == total(data, 'extra_counts', selected, (a, s)))
        for a, arm in enumerate(P.ARMS):
            d = saved['diagnostics'][name][arm]
            stats(d['alarm_episode_fraction'], rows(data, selected, lambda bi, i, j: data['alarm'][bi, i, j, a, 0] > 0))
            stats(d['alarm_tasks'], rows(data, selected, lambda bi, i, j: data['alarm'][bi, i, j, a, 0]))
            for k, key in enumerate(('final_change_mass', 'final_reversal_mass')):
                stats(d[key], rows(data, selected, lambda bi, i, j: data['posterior_final'][bi, i, j, a, k]))
            if name == 'stable':
                continue
            stats(d['no_post_purchase_fraction'], rows(data, selected, lambda bi, i, j: data['first'][bi, i, j, a] == 101))
            stats(d['capped_first_purchase_delay'], rows(data, selected, lambda bi, i, j:
                  data['first'][bi, i, j, a]-P.CONDITIONS[j][1]))
            for p, phase in enumerate(('before_first', 'at_first', 'after_first')):
                pd = d['phases'][phase]
                close('phase_count_totals', pd['count_totals'],
                      [total(data, 'phase_counts', selected, (a, p, k)) for k in range(3)], 0)
                for k, metric in enumerate(C.SUMS):
                    stats(pd[metric], rows(data, selected, lambda bi, i, j:
                          data['phase_sums'][bi, i, j, a, p, k]/(101-P.CONDITIONS[j][1])))
                def phase_cost(bi, i, j, subtract_exposure):
                    exposure, wrong, paid = map(int, data['phase_counts'][bi, i, j, a, p])
                    return (wrong+paid/10-(exposure/10 if subtract_exposure else 0))/(101-P.CONDITIONS[j][1])
                stats(pd['realized_cost_contribution'], rows(data, selected, lambda bi, i, j: phase_cost(bi, i, j, False)))
                stats(pd['excess_over_always'], rows(data, selected, lambda bi, i, j: phase_cost(bi, i, j, True)))
                pt = [total(data, 'predictive', selected, (a, p, k)) for k in range(4)]
                close('predictive_totals', pd['predictive_totals'], pt, 1e-8)
                if pt[0]:
                    close('predictive_means', pd['predictive_task_means'], [v/pt[0] for v in pt[1:]])
                else:
                    check('no_undefined_predictive_mean', pd['predictive_task_means'] is None)
    check('condition_count', len(saved['conditions']) == b*25)
    for bi, meta in enumerate(pop):
        for j, (family, onset) in enumerate(P.CONDITIONS):
            r = saved['conditions'][bi*25+j]
            check('condition_identity', (r['base'], r['family'], r['onset']) == (meta['label'], family, onset))
            subset = {'counts': data['counts'][bi:bi+1]}
            cost_panel(r['episode'], cost_rows(subset, [j], 0))
            if j:
                cost_panel(r['post_change'], cost_rows(subset, [j], 1))
            # Pair 00/11 and 01/10 directly, independently of the runner's warning sum.
            law = 0 if not j else 1+C.U.FAMILIES.index(family)
            q = [C.F(x) for x in meta['laws'][law]]
            floor = sum(min(C.F(1, 10)*(q[y]+q[y ^ 3]), q[y], q[y ^ 3]) for y in (0, 1))
            close('known_law_floor', r['known_law_floor'], float(floor))
            check('known_law_floor_exact', r['known_law_floor_exact'] == str(floor))
            check('zero_headroom_retained', r['zero_headroom'] == (floor == C.F(1, 10)))
    for name in ('reverse', 'core'):
        p = saved['panels'][name]['post_change']
        relative = p['gap1_minus_baseline']['upper95'] < 0
        absolute = p['against_always'][P.ARMS[1]]['upper95'] < 0
        check('frozen_gates', saved['criteria'][name] ==
              dict(better_than_baseline=relative, below_always=absolute, both=relative and absolute))
    for t in C.U.UNEXPECTED:
        cost_panel(saved['reversal_onsets'][str(t)], cost_rows(data, [P.CONDITIONS.index(('reverse', t))], 1))
    for segment in ('episode', 'post_change'):
        valid = [r for r in saved['conditions'] if segment in r]
        harms = [dict(base=r['base'], family=r['family'], onset=r['onset'], **r[segment]['gap1_minus_baseline'])
                 for r in valid if r[segment]['gap1_minus_baseline']['mean'] > 0]
        check('signed_harms_retained', saved['harms'][segment]['point_higher'] == harms)
        for key, field, pred in (('point_equal', 'mean', lambda x: x == 0), ('point_lower', 'mean', lambda x: x < 0),
                                 ('interval_lower_above_zero', 'lower95', lambda x: x > 0)):
            check('harm_count_'+key, saved['harms'][segment][key] ==
                  sum(pred(r[segment]['gap1_minus_baseline'][field]) for r in valid))


def qualify_axes():
    fixture = np.zeros((3, 5, 4, 2, 2, 3), dtype=np.int64)
    for b in range(3):
        for n in range(5):
            for j in range(4):
                for a in range(2):
                    for s in range(2):
                        fixture[b, n, j, a, s] = [100-7*s, b+n+j+a*(n % 2)+s, 7+j+a+2*s]
    selected = [1, 3]
    for segment in range(2):
        x = P.cost_values(fixture, selected, segment)
        reference = cost_rows({'counts': fixture}, selected, segment)
        close('unequal_axes_scalar_selection', x, reference)
        cost_panel(P.panel(x), reference)
        # Distinct block permutations within strata preserve the proper uncertainty.
        permuted = fixture.copy()
        for b in range(3):
            permuted[b] = fixture[b, np.roll(np.arange(5), b+1)]
        y = P.cost_values(permuted, selected, segment)
        for a in range(2):
            close('per_stratum_block_permutation', list(P.ci(x[..., a]).values()), list(P.ci(y[..., a]).values()))
        rates = (10*fixture[..., 1]+fixture[..., 2])/(10*fixture[..., 0])
        bad = rates[:, :, selected, :, segment].mean(axis=2)
        check('old_axis_defect_detected', bad.shape == (2, 3, 2) and bad.shape != x.shape)
        check('old_variance_defect_detected', abs(P.ci(bad[..., 1])['mc_se']-P.ci(x[..., 1])['mc_se']) > 1e-6)
    analytic = np.array([[0., 1., 2.], [2., 4., 6.]])
    stats(P.ci(analytic), analytic.tolist())
    close('analytic_stratified_variance', P.ci(analytic)['mc_se'], math.sqrt(5/12))


def readback(output):
    tick = perf_counter()
    P.resources()
    frozen = P.check_inputs(output)
    manifest = json.loads((output/'MANIFEST.json').read_text())
    check('completed_manifest', manifest['status'] == 'COMPLETE')
    for name, expected in manifest['outputs'].items():
        check('output_hash', P.digest(output/name) == expected)
    started = json.loads((output/'STARTED.json').read_text())
    for name, key in (('FREEZE.json', 'freeze_sha256'), ('QUALIFICATION.json', 'qualification_sha256'),
                      ('BENCHMARK.json', 'benchmark_sha256')):
        check('launch_input_identity', P.digest(output/name) == started[key])
    check('four_cpu_limit', len(started['cpus']) <= 4 and started['workers'] == 4 and started['nice'] >= 10)
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    seeds = json.loads((output/'SEEDS.json').read_text())
    collected = {key: [] for key in P.FIELDS}
    workers = json.loads((output/'WORKERS.json').read_text())
    check('complete_worker_set', len(workers) == 216 and len({r['file'] for r in workers}) == 216)
    indexed = {r['file']: r for r in workers}
    fallbacks = np.zeros(2, dtype=np.int64)
    for meta in pop:
        parts = {key: [] for key in P.FIELDS}
        for first in range(0, 32, 4):
            indices = list(range(first, first+4))
            for i in indices:
                for key, suffix in (('blocks', ''), ('flip_blocks', '-transfer-flips')):
                    check('saved_seed_identity', seeds[key][meta['label']][i] == str(C.M.seed_for(meta['label'], i, P.PREFIX+suffix)))
            name = f'blocks/{meta["label"]}_{first:04d}_{first+3:04d}.npz'
            with np.load(output/name, allow_pickle=False) as source:
                raw = {key: source[key] for key in source.files}
            record = indexed[name]
            check('worker_identity', record['sha256'] == P.digest(output/name) and record['indices'] == indices and record['label'] == meta['label'])
            check('worker_resources', len(record['affinity']) <= 4 and record['nice'] >= 10 and record['threads'] == 1)
            check('chunk_fingerprint', C.M.fingerprint(raw) == record['fingerprint'])
            check('saved_indices', np.array_equal(raw['indices'], indices))
            cal, warning, truth, _ = C.physical(meta, indices, P.PREFIX)
            for key, expected in (('calibration', cal), ('warnings', warning), ('truth', truth)):
                check('regenerated_physical_'+key, np.array_equal(raw[key], expected))
            rebuilt = rebuild(raw, meta)
            for key in P.FIELDS:
                close('saved_'+key, raw[key], rebuilt[key])
                parts[key].append(rebuilt[key])
            fallbacks += raw['fallbacks']
            check('worker_fallbacks', record['fallback'] == raw['fallbacks'].tolist())
        for key in P.FIELDS:
            collected[key].append(np.concatenate(parts[key]))
    data = {key: np.stack(value) for key, value in collected.items()}
    check('main_sample_shape', data['counts'].shape == (27, 32, 25, 2, 2, 3))
    saved = json.loads((output/'RESULTS.json').read_text())
    qualify_axes()
    verify_results(saved, data, pop)
    check('fallback_totals', saved['fallbacks'] == fallbacks.tolist())
    P.write(output/'READBACK.json', dict(passed=True, completed=P.utc(), seconds=perf_counter()-tick,
                                        checks=dict(CHECKS), total_checks=sum(CHECKS.values()),
                                        manifest_sha256=P.digest(output/'MANIFEST.json'),
                                        readback_source_sha256=P.digest(Path(__file__).resolve()),
                                        frozen_inputs=len(frozen['inputs']), reconstructed_chunks=216,
                                        policy_episodes_rerun=0, criteria=saved['criteria']))
    print(json.dumps(dict(passed=True, checks=sum(CHECKS.values()), seconds=perf_counter()-tick)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=P.ROOT/'attempt-01')
    args = parser.parse_args()
    try:
        readback(args.output)
    except BaseException:
        path = args.output/'FAILURE-readback.json'
        if not path.exists():
            P.write(path, dict(utc=P.utc(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
        raise


if __name__ == '__main__':
    main()
