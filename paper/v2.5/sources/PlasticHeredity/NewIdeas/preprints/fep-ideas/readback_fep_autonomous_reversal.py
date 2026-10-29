#!/usr/bin/env python3
"""Saved-action reconstruction only: never run a policy or new scientific episode."""
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
import run_fep_autonomous_reversal as C

CHECKS = {}


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def close(name, left, right, tolerance=3e-12):
    check(name, np.shape(left) == np.shape(right) and np.allclose(left, right, atol=tolerance, rtol=0))


def rebuild(raw, meta):
    """Independent episode-wise reconstruction from primitive action traces."""
    b, nc, na, nt = raw['actions'].shape
    check('trace_dimensions', (nc, na, nt) == (25, 2, 100))
    shape = (b, nc, 2)
    out = dict(counts=np.zeros(shape+(2, 3), dtype=np.int64), sums=np.zeros(shape+(2, 6)),
               phase_counts=np.zeros(shape+(3, 3), dtype=np.int64), phase_sums=np.zeros(shape+(3, 6)),
               first=np.full(shape, 101, dtype=np.int64), confident_agreement=np.zeros(shape+(2, 3), dtype=np.int64),
               extra_counts=np.zeros(shape+(2,), dtype=np.int64), alarm=np.zeros(shape+(3,)),
               posterior_final=np.zeros(shape+(2,)))
    times = np.arange(1, 101)
    check('same_physical_truth', np.all(raw['truth'] == raw['truth'][:, 0:1]))
    check('finite_traces', all(np.all(np.isfinite(v)) for v in raw.values()))
    check('calibration_size', np.all(raw['calibration'].sum(axis=-1) == 64) and np.all(raw['calibration'] >= 0))
    for j, (family, onset) in enumerate(C.CONDITIONS):
        oldq = np.array([float(C.F(x)) for x in meta['laws'][0]])
        newq = oldq if family == 'stable' else np.array([float(C.F(x)) for x in meta['laws'][1+C.U.FAMILIES.index(family)]])
        laws = np.array([newq if t >= onset else oldq for t in times])
        for block in range(b):
            warning, target = raw['warnings'][block, j], raw['truth'][block, j]
            check('physical_range', np.all((warning >= 0) & (warning <= 3)) and np.all((target >= 0) & (target <= 1)))
            for arm in range(2):
                index = (block, j, arm)
                action, u = raw['actions'][index], raw['subjective_u'][index]
                paid = action == 2
                wrong = (action != target) & ~paid
                labels = raw['labels'][index]
                extra = raw['extra'][index]
                check('action_range', np.all((action >= 0) & (action <= 2)))
                check('feedback_exact_mask', np.array_equal(labels, [int(target[t]) if paid[t] else -1 for t in range(100)]))
                check('belief_range', np.all((u >= -1e-13) & (u <= 1+1e-13)))
                check('extra_paid', np.all(~extra | paid))
                check('information_sign_terminal', np.all(raw['information'][index] >= -2e-12) and raw['information'][index][-1] == 0)
                confident = np.array([yy in (0, 3) and min(p, 1-p) < .1 for yy, p in zip(warning, u)])
                # Physical target probabilities given the warning, without learner beliefs.
                target_prob = np.array([[q[yy], q[yy ^ 3]] for q, yy in zip(laws, warning)])
                target_prob /= target_prob.sum(axis=1, keepdims=True)
                error_best = target_prob.min(axis=1)
                conditional = np.array([.1 if a == 2 else p[1-a] for a, p in zip(action, target_prob)])
                floor = np.minimum(error_best, .1)
                insufficient = np.array([0. if a == 2 else max(e-.1, 0.) for a, e in zip(action, error_best)])
                direction = np.array([0. if a == 2 else p[1-a]-e for a, p, e in zip(action, target_prob, error_best)])
                excess = np.array([max(.1-e, 0.) if a == 2 else 0. for a, e in zip(action, error_best)])
                subjective = np.array([.1 if a == 2 else (p if a == yy >> 1 else 1-p) for a, p, yy in zip(action, u, warning)])
                close('independent_regret_identity', conditional-floor, insufficient+direction+excess, 2e-15)
                metrics = np.column_stack((conditional, floor, insufficient, direction, excess, subjective))
                post = times >= onset
                purchased = times[post & paid]
                first = int(purchased[0]) if len(purchased) else 101
                out['first'][index] = first
                for segment, keep in enumerate((np.ones(100, dtype=bool), post)):
                    out['counts'][index+(segment,)] = (sum(keep), sum(wrong & keep), sum(paid & keep))
                    out['sums'][index+(segment,)] = metrics[keep].sum(axis=0)
                    out['confident_agreement'][index+(segment,)] = (sum(confident & keep), sum(confident & paid & keep), sum(confident & wrong & keep))
                    out['extra_counts'][index+(segment,)] = sum(extra & keep)
                for phase, keep in enumerate((post & (times < first), post & (times == first), post & (times > first))):
                    out['phase_counts'][index+(phase,)] = (sum(keep), sum(wrong & keep), sum(paid & keep))
                    out['phase_sums'][index+(phase,)] = metrics[keep].sum(axis=0)
                posterior = raw['posterior'][index]
                check('posterior_ranges', np.all(posterior >= -2e-13) and np.all(posterior <= 1+2e-13) and np.all(posterior[:, 1] <= posterior[:, 0]+1e-13))
                if arm == 0:
                    check('baseline_no_reversal_component', np.all(posterior[:, 1] == 0))
                alarm = times[posterior[:, 0] > .5]
                out['alarm'][index] = (len(alarm), int(alarm[0]) if len(alarm) else 101, sum(posterior[:, 0]))
                out['posterior_final'][index] = posterior[-1]
    return out


def stats(saved, data):
    """Two-pass stratified variance, independent of the runner's CI helper."""
    b, n = data.shape
    row_means = [math.fsum(map(float, row))/n for row in data]
    mean = math.fsum(row_means)/b
    variances = [math.fsum((float(v)-m)**2 for v in row)/(n-1) for row, m in zip(data, row_means)]
    se = math.sqrt(math.fsum(variances)/(b*b*n))
    expected = dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)
    check('interval_fields', set(saved) == set(expected))
    for key, value in expected.items():
        check('saved_interval_'+key, abs(saved[key]-value) < 3e-12)


def cost_panel(saved, value):
    for a, arm in enumerate(C.ARMS):
        stats(saved['arms'][arm], value[..., a])
        stats(saved['against_always'][arm], value[..., a]-.1)
    stats(saved['structured_minus_anytime'], value[..., 1]-value[..., 0])


def verify_results(saved, data, population):
    counts = data['counts']
    cost = (counts[..., 1]+counts[..., 2]/10)/np.maximum(counts[..., 0], 1)
    check('result_sample', (saved['blocks_per_base'], saved['independent_blocks'], saved['physical_episodes'], saved['policy_decisions']) == (32, 864, 21600, 4320000))
    family_indices = {f: [j for j, (family, _) in enumerate(C.CONDITIONS) if family == f] for f in ('stable',)+C.U.FAMILIES}
    family_indices.update(core=sum([family_indices[f] for f in ('A_loss', 'B_loss', 'reverse')], []),
                          transfer=sum([family_indices[f] for f in ('A_partial', 'B_partial', 'both_partial')], []),
                          non_reversal=[j for j, (f, _) in enumerate(C.CONDITIONS) if f not in ('stable', 'reverse')],
                          all_changes=list(range(1, 25)))
    check('all_panels_present', set(saved['panels']) == set(family_indices))
    for name, selected in family_indices.items():
        cost_panel(saved['panels'][name]['episode'], np.mean(cost[:, :, selected, :, 0], axis=2))
        if name != 'stable':
            cost_panel(saved['panels'][name]['post_change'], np.mean(cost[:, :, selected, :, 1], axis=2))
        for a, arm in enumerate(C.ARMS):
            diagnostic = saved['diagnostics'][name][arm]
            for segment, seg in enumerate(('episode', 'post_change')):
                if name == 'stable' and segment:
                    continue
                for k, key in enumerate(C.SUMS):
                    v = data['sums'][:, :, selected, a, segment, k]/counts[:, :, selected, a, segment, 0]
                    stats(diagnostic[seg][key], v.mean(axis=2))
                close('confident_agreement_total', diagnostic[seg]['confident_agreement_totals'], data['confident_agreement'][:, :, selected, a, segment].sum(axis=(0, 1, 2)), 0)
                check('extra_purchase_total', diagnostic[seg]['extra_purchases'] == int(data['extra_counts'][:, :, selected, a, segment].sum()))
            stats(diagnostic['alarm_episode_fraction'], (data['alarm'][:, :, selected, a, 0] != 0).mean(axis=2))
            stats(diagnostic['alarm_tasks'], data['alarm'][:, :, selected, a, 0].mean(axis=2))
            stats(diagnostic['final_change_mass'], data['posterior_final'][:, :, selected, a, 0].mean(axis=2))
            stats(diagnostic['final_reversal_mass'], data['posterior_final'][:, :, selected, a, 1].mean(axis=2))
            if name != 'stable':
                first = data['first'][:, :, selected, a]
                stats(diagnostic['no_post_purchase_fraction'], (first == 101).mean(axis=2))
                onsets = np.array([C.CONDITIONS[j][1] for j in selected])
                stats(diagnostic['capped_first_purchase_delay'], (first-onsets).mean(axis=2))
                close('phase_count_totals', diagnostic['phase_count_totals'], data['phase_counts'][:, :, selected, a].sum(axis=(0, 1, 2)), 0)
                for phase, phase_name in enumerate(('before_first', 'at_first', 'after_first')):
                    for k, key in enumerate(C.SUMS):
                        contributions = data['phase_sums'][:, :, selected, a, phase, k]/(101-onsets)
                        stats(diagnostic['phase_contributions_per_post_task'][phase_name][key], contributions.mean(axis=2))
    check('condition_panel_count', len(saved['conditions']) == 675)
    for bi, meta in enumerate(population):
        for j, (family, onset) in enumerate(C.CONDITIONS):
            row = saved['conditions'][bi*25+j]
            check('condition_identity', (row['base'], row['family'], row['onset']) == (meta['label'], family, onset))
            cost_panel(row['episode'], cost[bi:bi+1, :, j, :, 0])
            if j:
                cost_panel(row['post_change'], cost[bi:bi+1, :, j, :, 1])
    for name in ('reverse', 'core'):
        panel = saved['panels'][name]['post_change']
        relative = panel['structured_minus_anytime']['upper95'] < 0
        absolute = panel['against_always'][C.ARMS[1]]['upper95'] < 0
        check('predeclared_gates', saved['criteria'][name] == dict(better_than_anytime=relative, below_always=absolute, both=relative and absolute))
    for segment in ('episode', 'post_change'):
        rows = [r for r in saved['conditions'] if segment in r]
        bad = [dict(base=r['base'], family=r['family'], onset=r['onset'], **r[segment]['structured_minus_anytime'])
               for r in rows if r[segment]['structured_minus_anytime']['mean'] > 0]
        check('all_signed_harms', saved['harms'][segment]['point_higher'] == bad)
        for key, field, predicate in (('point_equal', 'mean', lambda x: x == 0), ('point_lower', 'mean', lambda x: x < 0),
                                       ('interval_lower_above_zero', 'lower95', lambda x: x > 0)):
            check('harm_count_'+key, saved['harms'][segment][key] == sum(predicate(r[segment]['structured_minus_anytime'][field]) for r in rows))


def readback(output):
    tick = perf_counter()
    C.resources()
    frozen = C.check_inputs(output)
    manifest = json.loads((output/'MANIFEST.json').read_text())
    check('completed_manifest', manifest['status'] == 'COMPLETE')
    for name, expected in manifest['outputs'].items():
        check('output_hash', C.digest(output/name) == expected)
    started = json.loads((output/'STARTED.json').read_text())
    for name, key in (('FREEZE.json', 'freeze_sha256'), ('QUALIFICATION.json', 'qualification_sha256'), ('BENCHMARK.json', 'benchmark_sha256')):
        check('launch_input_identity', C.digest(output/name) == started[key])
    check('four_cpu_limit', len(started['cpus']) <= 4 and started['workers'] == 4 and started['nice'] >= 10)
    pop = json.loads((output/'POPULATION.json').read_text())['bases']
    seeds = json.loads((output/'SEEDS.json').read_text())
    rows = {key: [] for key in C.FIELDS}
    workers = json.loads((output/'WORKERS.json').read_text())
    check('complete_worker_set', len(workers) == 216 and len({r['file'] for r in workers}) == 216)
    indexed = {r['file']: r for r in workers}
    fallbacks = np.zeros(2, dtype=np.int64)
    for meta in pop:
        parts = {key: [] for key in C.FIELDS}
        for first in range(0, 32, 4):
            indices = list(range(first, first+4))
            for i in indices:
                for key, suffix in (('blocks', ''), ('flip_blocks', '-transfer-flips')):
                    check('saved_seed_identity', seeds[key][meta['label']][i] == str(C.M.seed_for(meta['label'], i, C.PREFIX+suffix)))
            name = f'blocks/{meta["label"]}_{first:04d}_{first+3:04d}.npz'
            with np.load(output/name, allow_pickle=False) as source:
                raw = {key: source[key] for key in source.files}
            record = indexed[name]
            check('worker_identity', record['sha256'] == C.digest(output/name) and record['indices'] == indices and record['label'] == meta['label'])
            check('worker_resources', len(record['affinity']) <= 4 and record['nice'] >= 10)
            check('chunk_fingerprint', C.M.fingerprint(raw) == record['fingerprint'])
            check('saved_indices', np.array_equal(raw['indices'], indices))
            cal, warning, truth, _ = C.physical(meta, indices, C.PREFIX)
            for key, expected in (('calibration', cal), ('warnings', warning), ('truth', truth)):
                check('regenerated_physical_'+key, np.array_equal(raw[key], expected))
            rebuilt = rebuild(raw, meta)
            for key in C.FIELDS:
                close('saved_'+key, raw[key], rebuilt[key])
                parts[key].append(rebuilt[key])
            fallbacks += raw['fallbacks']
            check('worker_fallbacks', record['fallback'] == raw['fallbacks'].tolist())
        for key in C.FIELDS:
            rows[key].append(np.concatenate(parts[key]))
    data = {key: np.stack(value) for key, value in rows.items()}
    saved = json.loads((output/'RESULTS.json').read_text())
    verify_results(saved, data, pop)
    check('fallback_totals', saved['fallbacks'] == fallbacks.tolist())
    C.write(output/'READBACK.json', dict(passed=True, completed=C.utc(), seconds=perf_counter()-tick,
                                        checks=dict(CHECKS), total_checks=sum(CHECKS.values()),
                                        manifest_sha256=C.digest(output/'MANIFEST.json'),
                                        readback_source_sha256=C.digest(Path(__file__).resolve()),
                                        frozen_inputs=len(frozen['inputs']), reconstructed_chunks=216,
                                        policy_episodes_rerun=0, criteria=saved['criteria']))
    print(json.dumps(dict(passed=True, checks=sum(CHECKS.values()), seconds=perf_counter()-tick)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=C.ROOT/'attempt-01')
    args = parser.parse_args()
    try:
        readback(args.output)
    except BaseException:
        path = args.output/'FAILURE-readback.json'
        if not path.exists():
            C.write(path, dict(utc=C.utc(), traceback=traceback.format_exc(), checks=dict(CHECKS)))
        raise


if __name__ == '__main__':
    main()
