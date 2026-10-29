"""Posthoc H079 closeout and endpoint diagnosis; sealed arrays only, no trajectories."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = '6d733b3d9421c12f4b522cf3b6be58be91bad46cc74e711b3a5014a9d7234a1f'
FREEZE = 'c79dbab939e9ec87501ce445ceec462a1d78549f15c8d944296df1339ecac013'
SCHEDULES = ('on', 'delayed', 'off')
NETWORKS = 192


def read(path):
    return json.loads(path.read_text())


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def verify(run):
    assert checksum(run / 'checksums.json') == MANIFEST
    assert checksum(run / 'freeze.json') == FREEZE
    sealed, frozen = (read(run / name) for name in ('checksums.json', 'freeze.json'))
    for manifest in (sealed, frozen):
        for name, digest in manifest.items():
            assert checksum(run / name) == digest, name
    sources = {k[7:]: v for k, v in frozen.items() if k.startswith('source/')}
    for name, digest in sources.items():
        assert checksum(ROOT / name) == digest, name
    complete = read(run / 'COMPLETE.json')
    assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
    assert not Path('/proc', str(complete['pid'])).exists()
    assert not list(run.rglob('*FAILED*'))
    assert not run.with_name(run.name + '_postseal_failure.json').exists()
    config = read(run / 'config.json')
    parent = Path(config['context_parent'])
    assert checksum(parent / 'checksums.json') == config['context_parent_manifest']
    for name, digest in config['bound_context_artifacts'].items():
        assert checksum(parent / name) == digest, name
    assert read(run / 'historical_verdicts.json') == dict(read(parent / 'historical_verdicts.json'),
        h078_capability=read(parent / 'main/summary.json')['capability_screen'])
    receipt = read(Path(config['closeout_receipt']))
    assert receipt['passed'] and receipt['manifest_sha256'] == MANIFEST
    return dict(sealed_files=len(sealed), frozen_files=len(frozen),
                current_source_context_files=len(sources), controller_exited=True,
                controller_pid=complete['pid'], historical_verdicts_unchanged=True)


def fixed(state, fields, conditional=False):
    proposed = np.where(fields > 1e-12, 1, np.where(fields < -1e-12, -1, state))
    same = proposed == state
    return same[..., np.r_[0:32, 80:128]].all(-1) if conditional else same.all(-1)


def scores(state, target):
    hits = (state[..., 80:] == target[:, None]).sum(-1)
    good = hits >= 44
    return dict(task_correct=int(good.all(0).sum()), query_correct=int(good.sum()),
                bit_correct=int(hits.sum()), exact_correct=int((hits == 48).sum()))



def verify_qualification(run, counts):
    """Rebuild planned means/bounds and gates from independently recounted raw states."""
    primary=[]; comparisons={k:[] for k in ('delayed_minus_on','delayed_minus_off','delayed_eight_minus_one')}
    network_rows=[]; gates={k:[] for k in ('complete_tasks','eight_minus_query_one','eight_minus_query_off',
        'own_minus_context_swap','own_minus_context_absent','own_minus_foreign','own_minus_erased')}
    thresholds=dict(zip(gates,(.75,.10,.25,.50,.50,.50,.50)))
    for block in range(NETWORKS):
        def rate(schedule='delayed',scenario='own',method='query_eight'):
            return counts[block,schedule,4,scenario,method]['task_correct']/4
        value=rate();primary.append(value)
        differences=dict(delayed_minus_on=value-rate('on'),delayed_minus_off=value-rate('off'),
                         delayed_eight_minus_one=value-rate(method='query_one'))
        network_rows.append(dict(block=block,delayed_task_rate=value,**differences))
        for key,v in differences.items():comparisons[key].append(v)
        gates['complete_tasks'].append(value)
        for method in ('query_one','query_off'):gates['eight_minus_'+method].append(value-rate(method=method))
        for condition in ('context_swap','context_absent','foreign','erased'):
            gates['own_minus_'+condition].append(value-rate(scenario=condition))
    archived=read(run/'main/replication.json');summary=read(run/'main/summary.json')
    assert archived['network_values']==network_rows
    mean=math.fsum(primary)/NETWORKS
    radius=math.sqrt(math.log(40)/(2*NETWORKS))
    absolute=dict(mean=mean,lower=max(0.,mean-radius),upper=min(1.,mean+radius),radius=radius)
    for key,value in absolute.items():assert abs(value-archived['absolute_delayed_task_rate'][key])<1e-15
    contrasts={}
    for name,values in comparisons.items():
        mean_difference=math.fsum(values)/NETWORKS
        radius_difference=math.sqrt(2*math.log(60)/NETWORKS)
        contrasts[name]=dict(mean=mean_difference,lower=max(-1.,mean_difference-radius_difference))
        for key,value in contrasts[name].items():
            assert abs(value-archived['simultaneous_task_contrasts'][name][key])<1e-15
    expected_gates={key:dict(value=math.fsum(values)/NETWORKS,threshold=thresholds[key],
                           passed=math.fsum(values)/NETWORKS>=thresholds[key]) for key,values in gates.items()}
    assert expected_gates==summary['schedule_decisions']['delayed']['capability_gates']
    capability='ITERATIVE_READER_CAPABILITY_SCREEN_PASSED' if all(r['passed'] for r in expected_gates.values()) else 'ITERATIVE_READER_CAPABILITY_SCREEN_FAILED'
    timing='TIMING_AND_ITERATION_BENEFIT_REPLICATED' if all(r['lower']>0 for r in contrasts.values()) else 'NO_QUALIFIED_TIMING_AND_ITERATION_REPLICATION'
    assert capability==summary['capability_screen']
    assert timing==summary['timing_iteration_verdict']==archived['timing_iteration_verdict']
    return dict(passed=True,independent_networks=NETWORKS,absolute_task_interval=absolute,
        simultaneous_task_contrasts=contrasts,capability_gates=expected_gates,
        capability_screen=capability,timing_iteration_verdict=timing,
        network_task_count_histogram=dict(sorted(Counter(int(4*v) for v in primary).items())))


def review(run, out):
    assert run.is_relative_to(ROOT) and out.is_relative_to(ROOT) and not out.exists()
    integrity = verify(run)
    score_rows = list(csv.DictReader((run / 'main/scores.csv').open()))
    index = {(int(r['block']), r['schedule'], int(r['gap']), r['scenario'], r['method']): r
             for r in score_rows}
    rows, checkpoints, sources = [], [], {}
    score_checks = common_checks = 0
    identities = Counter()
    checked_scores, task_limits = {}, []
    for block in range(NETWORKS):
        path = run / 'main/raw' / f'block_{block:03d}.npz'
        sources[str(path.relative_to(run))] = checksum(path)
        with np.load(path, allow_pickle=False) as loaded:
            raw = {k: loaded[k] for k in loaded.files}
        x, y = raw['training_inputs'], raw['responses']
        patterns = np.concatenate((x, y), axis=1)
        nominal = raw['source_J_projection'][0].astype(np.longdouble)
        target_energy = -np.sum(patterns * (patterns.astype(np.longdouble) @ nominal.T), axis=-1) / 2
        rank = int(raw['source_projector_rank'][0])
        np.testing.assert_allclose(target_energy, -(128 - rank) / 2, rtol=0, atol=2e-11)
        for (b, schedule, gap, scenario, method), row in index.items():
            if b != block:
                continue
            if method.startswith('query_'):
                horizon = {'query_off': 0, 'query_one': 1, 'query_eight': 8}[method]
                state = raw[f'{schedule}_d{gap}_{scenario}_read{horizon}_final']
                actual = scores(state, y)
            else:
                output = raw[f'baseline_{scenario}_{method}_final']
                hits = (output == y[:, None]).sum(-1)
                actual = dict(task_correct=int((hits >= 44).all(0).sum()),
                              query_correct=int((hits >= 44).sum()),
                              bit_correct=int(hits.sum()), exact_correct=int((hits == 48).sum()))
            assert all(actual[k] == int(row[k]) for k in actual), (b, schedule, gap, scenario, method)
            score_checks += 1
            checked_scores[b, schedule, gap, scenario, method] = actual
        for gap in (0, 4):
            before = raw[f'd{gap}_own_gap_final']
            off_first = raw[f'off_d{gap}_own_read8_trace'][1]
            delayed_first = raw[f'delayed_d{gap}_own_read8_trace'][1]
            identities['delayed_and_off_first_state_equal'] += int(np.array_equal(off_first, delayed_first))
            identities['off_final_equals_delayed_first_state'] += int(
                np.array_equal(raw[f'off_d{gap}_own_read8_final'], delayed_first))
            for schedule in SCHEDULES:
                prefix = f'{schedule}_d{gap}_own_read8_'
                state, trace = raw[prefix + 'final'], raw[prefix + 'trace']
                assert np.array_equal(before, raw[prefix + 'initial'])
                assert np.array_equal(raw[f'{schedule}_d{gap}_own_read0_final'],
                                      raw[f'on_d{gap}_own_read0_final'])
                assert np.array_equal(trace[1], raw[f'{schedule}_d{gap}_own_read1_final'])
                common_checks += 3
                current = nominal.copy()
                if schedule == 'off':
                    current[80:, 80:] = 0
                nominal_fields = state.astype(np.longdouble) @ nominal.T
                current_fields = state.astype(np.longdouble) @ current.T
                nominal_flags, current_flags = fixed(state, nominal_fields), fixed(state, current_fields)
                assert np.array_equal(nominal_flags, raw[prefix + 'nominal_full_fixed'])
                assert np.array_equal(current_flags, raw[prefix + 'full_fixed'])
                nominal_conditional = fixed(state, nominal_fields, conditional=True)
                current_conditional = fixed(state, current_fields, conditional=True)
                assert np.array_equal(nominal_conditional, raw[prefix + 'nominal_conditional_fixed'])
                assert np.array_equal(current_conditional, raw[prefix + 'conditional_fixed'])
                np.testing.assert_allclose(nominal_fields, raw[prefix + 'nominal_fields_final'], rtol=0, atol=2e-11)
                np.testing.assert_allclose(current_fields, raw[prefix + 'fields_final'], rtol=0, atol=2e-11)
                nominal_energy = -np.sum(state * nominal_fields, axis=-1) / 2
                hits = (state[..., 80:] == y[:, None]).sum(-1)
                good = hits >= 44
                blocked = ((~good) & current_conditional).any(0)
                task_limits.append(dict(block=block, gap=gap, schedule=schedule,
                    complete_tasks=int(good.all(0).sum()), tasks=4,
                    tasks_blocked_by_fixed_wrong_query=int(blocked.sum()),
                    optimistic_complete_task_bound_unchanged_conditions=int((~blocked).sum()),
                    failed_nonfixed_queries=int(((~good) & ~current_conditional).sum())))
                for sweep, checkpoint in enumerate(trace):
                    checkpoints.append(dict(block=block, gap=gap, schedule=schedule,
                                            sweep=sweep, **scores(checkpoint, y)))
                for association in range(8):
                    for birth in range(4):
                        final, first, old = state[association, birth], trace[1, association, birth], before[association, birth]
                        response = final[80:]
                        changes = raw[prefix + 'changes'][:, association, birth]
                        active = np.flatnonzero(changes)
                        rows.append(dict(block=block, gap=gap, schedule=schedule,
                            association=association, birth=birth, success=bool(hits[association, birth] >= 44),
                            correct_bits=int(hits[association, birth]),
                            first_sweep_correct_bits=int((first[80:] == y[association]).sum()),
                            context_before_exact=bool((old[:32] == x[association, :32]).all()),
                            context_final_exact=bool((final[:32] == x[association, :32]).all()),
                            query_final_exact=bool((final[32:80] == x[association, 32:]).all()),
                            full_fixed_current=bool(current_flags[association, birth]),
                            full_fixed_nominal=bool(nominal_flags[association, birth]),
                            conditional_fixed_current=bool(current_conditional[association, birth]),
                            conditional_fixed_nominal=bool(nominal_conditional[association, birth]),
                            response_equals_prequery=bool((response == old[80:]).all()),
                            exact_response_matches=np.flatnonzero((response[None] == y).all(-1)).tolist(),
                            prequery_exact_pattern_matches=np.flatnonzero((old[None] == patterns).all(-1)).tolist(),
                            prequery_query_matches=bool((old[32:80] == x[association, 32:]).all()),
                            prequery_query_opposes=bool((old[32:80] == -x[association, 32:]).all()),
                            nominal_energy_above_target=float(nominal_energy[association, birth] - target_energy[association]),
                            last_sweep_with_flips=int(active[-1] + 1) if len(active) else 0))
        if (block + 1) % 16 == 0:
            print(json.dumps(dict(reviewed_networks=block + 1, total_networks=NETWORKS)), flush=True)
    qualification = verify_qualification(run, checked_scores)
    summaries = []
    for gap in (0, 4):
        for schedule in SCHEDULES:
            selected = [r for r in rows if r['gap'] == gap and r['schedule'] == schedule]
            failures = [r for r in selected if not r['success']]
            summary = dict(gap=gap, schedule=schedule, queries=len(selected),
                           successful_queries=sum(r['success'] for r in selected),
                           failed_queries=len(failures),
                           failures_by_network=dict(sorted(Counter(r['block'] for r in failures).items())),
                           failed_exact_taught_response=sum(bool(r['exact_response_matches']) for r in failures),
                           failed_response_unchanged=sum(r['response_equals_prequery'] for r in failures))
            for key in ('context_before_exact', 'context_final_exact', 'query_final_exact',
                        'full_fixed_current', 'full_fixed_nominal',
                        'conditional_fixed_current', 'conditional_fixed_nominal'):
                summary[key] = sum(r[key] for r in selected)
                summary['failed_' + key] = sum(r[key] for r in failures)
            gaps = [r['nominal_energy_above_target'] for r in failures]
            summary['failed_nominal_energy_above_target'] = dict(min=min(gaps), max=max(gaps), mean=float(np.mean(gaps))) if gaps else None
            task_rows = [r for r in task_limits if r['gap'] == gap and r['schedule'] == schedule]
            summary['task_completion_limits_unchanged_conditions'] = {
                key: sum(r[key] for r in task_rows) for key in ('complete_tasks', 'tasks',
                    'tasks_blocked_by_fixed_wrong_query', 'optimistic_complete_task_bound_unchanged_conditions',
                    'failed_nonfixed_queries')}
            summary['failed_correct_bits_histogram'] = dict(sorted(Counter(r['correct_bits'] for r in failures).items()))
            summary['failed_first_sweep_correct_bits_histogram'] = dict(sorted(Counter(r['first_sweep_correct_bits'] for r in failures).items()))
            summaries.append(summary)
    checkpoint_totals = []
    for gap in (0, 4):
        for schedule in SCHEDULES:
            for sweep in range(9):
                selected = [r for r in checkpoints if (r['gap'], r['schedule'], r['sweep']) == (gap, schedule, sweep)]
                checkpoint_totals.append(dict(gap=gap, schedule=schedule, sweep=sweep,
                    **{k: sum(r[k] for r in selected) for k in ('task_correct', 'query_correct', 'bit_correct', 'exact_correct')}))
    assert verify(run) == integrity
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'findings.json', dict(posthoc_saved_data_only=True, target_aware_diagnosis=True,
        source_run=str(run.relative_to(ROOT)), source_manifest_sha256=MANIFEST,
        source_raw_hashes=sources, trajectories_generated=0, models_fitted=0,
        summary=summaries, own_state_identities=dict(identities), own_network_gap_pairs=NETWORKS * 2,
        independently_verified_qualification=qualification, task_completion_limits=task_limits,
        checkpoints=checkpoint_totals, network_checkpoints=checkpoints, queries=rows,
        limitations=['192 independent replication networks; births and queries are related.',
                    'Endpoint fields are posthoc target-aware diagnostics, not forecasts.',
                    'A lower-energy stable target does not guarantee access.',
                    'Timing superiority over constant schedules does not establish inheritance or comparator superiority.'],
        next_campaign_launched=False))
    save(out / 'integrity.json', dict(passed=True, reviewed_utc=datetime.now(timezone.utc).isoformat(),
        **integrity, completed_manifest_sha256=MANIFEST, freeze_sha256=FREEZE,
        review_source_sha256=checksum(Path(__file__).resolve()), independently_checked_score_rows=score_checks,
        common_state_checks=common_checks, endpoint_checks=len(rows), target_energy_checks=8 * NETWORKS,
        primary_bound_and_gate_verification=True,
        next_campaign_launched=False))
    save(out / 'checksums.json', {p.name: checksum(p) for p in sorted(out.iterdir())})
    print(json.dumps(dict(summary=[{k:v for k,v in r.items() if k != 'failures_by_network'} for r in summaries],
                          qualification=qualification, state_identities=dict(identities),
                          integrity=integrity, score_checks=score_checks), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    review(args.run.resolve(), args.out.resolve())
