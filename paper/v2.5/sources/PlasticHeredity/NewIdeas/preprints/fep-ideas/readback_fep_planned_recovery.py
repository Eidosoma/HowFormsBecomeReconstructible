#!/usr/bin/env python3
"""Independent trace accounting and reused scalar intervals; no policy episodes rerun."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path
from time import perf_counter
import traceback
import numpy as np
import run_fep_planned_recovery as P
import readback_fep_paid_checking as Q

C = P.C
CHECKS = {}
qualify_axes = Q.qualify_axes



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
               predictive=np.zeros(shape+(3, 4)), proposal_sums=np.zeros(shape+(2, 2)))
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
                check('extra_is_proposed_purchase', np.all(~extra | (proposed == 2)))
                check('information_sign_terminal', np.all(raw['information'][index] >= -2e-12) and raw['information'][index][-1] == 0)
                clock = raw['clock_benefit'][index]
                check('clock_sign_terminal', np.all(clock >= -2e-12) and clock[-1] == 0)
                if arm == 0:
                    check('hybrid_proposal_clock_zero', np.all(clock == 0))
                else:
                    answer, purchase = raw['clock_scores'][block, j].T
                    fallback = raw['clock_fallback'][block, j]
                    check('fallback_mask_boolean', fallback.dtype == bool)
                    risk = np.minimum(u, 1-u)
                    close('planned_score_decomposition', answer-purchase, risk-.1+clock+raw['information'][index])
                    check('planned_optional_choice', np.array_equal(proposed[~fallback] == 2, (purchase <= answer)[~fallback]))
                    chosen = np.where(proposed == 2, purchase, answer)
                    check('fallback_score_consistency', np.all(chosen <= np.minimum(answer, purchase)+3e-12))
                    check('planned_answer_prediction', np.all((proposed == 2) | (proposed == ((warning >> 1) ^ (u > .5)))))
                    h = np.minimum(4, 101-times)
                    check('planned_finite_horizon_bounds', np.all(answer >= risk-3e-12) and
                          np.all(purchase >= .1-3e-12) and np.all(purchase <= .1*h+3e-12))
                last, expected_gap, expected_due, expected_forced, expected_action = 0, [], [], [], []
                for t, plan in enumerate(proposed, 1):
                    gap = t-last
                    due = gap >= 2
                    forced = due and plan != 2
                    actual = 2 if due else int(plan)
                    expected_gap.append(gap); expected_due.append(due)
                    expected_forced.append(forced); expected_action.append(actual)
                    if actual == 2:
                        last = t
                    check('feedback_gap_bound', t-last <= 1)
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
                check('first_purchase_bound', j == 0 or onset <= first <= onset+1)
                for segment, keep in enumerate((np.ones(100, dtype=bool), post)):
                    out['counts'][index+(segment,)] = (sum(keep), sum(wrong & keep), sum(paid & keep))
                    out['sums'][index+(segment,)] = metrics[keep].sum(axis=0)
                    out['confident_agreement'][index+(segment,)] = (sum(confident & keep), sum(confident & paid & keep), sum(confident & wrong & keep))
                    out['extra_counts'][index+(segment,)] = sum(extra & keep)
                    out['proposal_sums'][index+(segment,)] = (raw['information'][index][keep].sum(), raw['clock_benefit'][index][keep].sum())
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
    check('planned_fallback_count', int(raw['clock_fallback'].sum()) == int(raw['fallbacks'][1]))
    return out


def verify_results(saved, data, pop):
    # Only schema labels change; the previously independent scalar verifier
    # receives the same arm-indexed numerical data through the inverse mapping.
    previous_schema = P.relabel(saved, inverse=True)
    check('schema_round_trip', P.relabel(previous_schema) == saved)
    Q.verify_results(previous_schema, data, pop)
    check('proposal_panel_names', set(saved['proposal_values']) == set(saved['panels']))
    groups = {f: [j for j, (family, _) in enumerate(P.CONDITIONS) if family == f]
              for f in ('stable',)+C.U.FAMILIES}
    groups.update(core=sum([groups[f] for f in ('A_loss', 'B_loss', 'reverse')], []),
                  transfer=sum([groups[f] for f in ('A_partial', 'B_partial', 'both_partial')], []),
                  non_reversal=[j for j, (f, _) in enumerate(P.CONDITIONS) if f not in ('stable', 'reverse')],
                  all_changes=list(range(1, 25)))
    for name, selected in groups.items():
        expected_segments = {'episode'} if name == 'stable' else {'episode', 'post_change'}
        check('proposal_segments', set(saved['proposal_values'][name]) == expected_segments)
        for s, segment in enumerate(('episode', 'post_change')):
            if segment not in expected_segments:
                continue
            panel = saved['proposal_values'][name][segment]
            check('proposal_arms', set(panel) == set(P.ARMS))
            for a, arm in enumerate(P.ARMS):
                check('proposal_terms', set(panel[arm]) == {'task_information', 'clock_benefit'})
                for k, key in enumerate(('task_information', 'clock_benefit')):
                    values = Q.rows(data, selected, lambda bi, i, j:
                                    data['proposal_sums'][bi, i, j, a, s, k]/data['counts'][bi, i, j, a, s, 0])
                    Q.stats(panel[arm][key], values)


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
                                        checks=dict(CHECKS), interval_checks=dict(Q.CHECKS), total_checks=sum(CHECKS.values())+sum(Q.CHECKS.values()),
                                        manifest_sha256=P.digest(output/'MANIFEST.json'),
                                        readback_source_sha256=P.digest(Path(__file__).resolve()),
                                        frozen_inputs=len(frozen['inputs']), reconstructed_chunks=216,
                                        policy_episodes_rerun=0, criteria=saved['criteria']))
    print(json.dumps(dict(passed=True, checks=sum(CHECKS.values())+sum(Q.CHECKS.values()), seconds=perf_counter()-tick)), flush=True)


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
