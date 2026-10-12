"""Bind completed TT015 receipts to frozen evidence without rerunning dynamics."""
from datetime import datetime
import json

import numpy as np

import dynamics as dyn
import intake
import scoring
import support as s


def archive(folder, complete):
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p.name not in ('STATUS.json', 'COMPLETE.json')}
    s.require(actual == set(complete['outputs_sha256']), 'Complete archive membership')
    for rel, digest in complete['outputs_sha256'].items():
        s.require(s.sha(folder / rel) == digest, 'Committed output ' + rel)
    return len(actual)


def flag_endpoints(d):
    good, other = d['both_pass'], d['opposite_pass']
    s.require(good.dtype == other.dtype == np.dtype(bool) and not (good & other).any(),
              'Exclusive Boolean task flags')
    prefix = np.logical_and.accumulate(good, axis=0)
    return dict(uninterrupted=good.all(axis=0), terminal=good[-1],
                ever_recovered=(good[1:] & ~prefix[:-1]).any(axis=0),
                terminal_after_failure=good[-1] & ~prefix[-2],
                mean_cycle_success=good.mean(axis=0), initial_success_run=prefix.sum(axis=0),
                ever_opposite=other.any(axis=0), terminal_opposite=other[-1])


def analysis_check(label, cfg, endpoints, analysis):
    summary = scoring.Summaries(cfg)
    counts = {}
    for vi, variant in enumerate(cfg['variants']):
        counts[variant] = {}
        for metric in scoring.METRICS:
            values = [float(endpoints[b][metric][vi].mean()) for b in cfg['blocks']]
            scoring.same_tree(analysis['rates'][variant][metric], summary(values),
                              label + '/' + variant + '/' + metric)
            if metric in ('uninterrupted', 'terminal'):
                counts[variant][metric] = sum(int(endpoints[b][metric][vi].sum()) for b in cfg['blocks'])
    coefficients = cfg.get('contrasts', dict(
        repeated_minus_baseline=[-1, 0, 1, 0], one_time_minus_baseline=[-1, 1, 0, 0],
        repeated_minus_one_time=[0, -1, 1, 0], repeated_minus_shuffled=[0, 0, 1, -1]))
    for name, coefs in coefficients.items():
        for metric in ('uninterrupted', 'terminal'):
            values = [sum(coef * int(endpoints[b][metric][vi].sum()) for vi, coef in enumerate(coefs)) / 16
                      for b in cfg['blocks']]
            scoring.same_tree(analysis['contrasts'][name][metric], summary(values), label + '/' + name)
    def pairs(left, right):
        return {k: scoring.paired([endpoints[b][k][left] for b in cfg['blocks']],
                                 [endpoints[b][k][right] for b in cfg['blocks']])
                for k in ('uninterrupted', 'terminal')}
    expected = (pairs(2, 0) if label == 'serial' else
                {name: pairs(2*i+1, 2*i) for i, name in enumerate(cfg['noise_regimes'])})
    s.require(expected == analysis['paired_counts'], 'All paired counts ' + label)
    for h, name in enumerate(cfg['histories']):
        for vi, variant in enumerate(cfg['variants']):
            for metric in ('uninterrupted', 'terminal'):
                total = sum(int(endpoints[b][metric][vi].sum()) for b in cfg['blocks']
                            if cfg['history_by_block'][str(b)] == h)
                s.require(analysis['history_summaries'][name][variant][metric] == total / 64,
                          'History rates ' + label)
    primary = cfg.get('primary_contrast', 'repeated_minus_baseline')
    s.require(analysis['primary_name'] == primary and analysis['source_agreement'] and
              not analysis['new_scientific_cohort'] and analysis['blocks'] == 16 and
              analysis['records'] == 256 and analysis['fitted_parameters'] == 0,
              'Unchanged development target ' + label)
    effect = analysis['contrasts'][primary]['uninterrupted']
    decision = scoring.classification(effect)
    s.require(analysis['scientific_verdict'] == decision and
              analysis['primary_direction_observed'] == (effect['mean'] > 0), 'Primary decision ' + label)
    return counts, effect, decision


def run():
    output = s.HERE / 'runs/audit_v1'
    jobdir = s.HERE / 'jobs/audit_v1'
    benchmark = s.HERE / 'runs/benchmark_v1'
    complete = s.read(output / 'COMPLETE.json')
    job = s.read(jobdir / 'job.json')
    manifest = s.read(output / 'manifest.json')
    startup = s.read(s.HERE / 'STARTUP_CHECK.json')
    bench_done = s.read(benchmark / 'COMPLETE.json')
    bench_manifest = s.read(benchmark / 'manifest.json')
    plan = s.config()
    s.require(complete['status'] == 'COMPLETE' and complete['audit_status'] == 'PASS' and
              complete['mode'] == 'audit' and complete['full_native_replay_performed'] and
              not complete['new_scientific_cohort'], 'Complete full independent development audit')
    s.require(not (output / 'FAILED.json').exists() and not (benchmark / 'FAILED.json').exists(),
              'No failed final or qualification run')
    s.require(s.sha(jobdir / 'job.json') == manifest['job_sha256'] == startup['job_sha256'],
              'Job and startup identity')
    s.require(bench_done['status'] == 'COMPLETE' and bench_done['audit_status'] == 'PASS' and
              bench_done['mode'] == 'benchmark', 'Successful qualification')
    bench_hash = s.sha(benchmark / 'COMPLETE.json')
    s.require(bench_hash == job['qualification']['complete_sha256'] ==
              manifest['qualification']['complete_sha256'] == startup['benchmark_complete_sha256'],
              'Qualification identity')
    s.require(job['inputs_sha256'] == manifest['inputs_sha256'] == bench_manifest['inputs_sha256'],
              'Identical qualification and full audit inputs')
    s.require(len(job['inputs_sha256']) == 314, 'Full frozen input scope')
    for rel, digest in job['inputs_sha256'].items():
        for root in (s.HERE, jobdir / 'inputs/TT015', s.HERE / 'jobs/benchmark_v1/inputs/TT015'):
            s.require(s.sha(root / rel) == digest, 'Frozen input ' + str(root / rel))
    s.require(datetime.fromisoformat(bench_done['utc']) < datetime.fromisoformat(job['created_utc']) <
              datetime.fromisoformat(manifest['started_utc']) < datetime.fromisoformat(complete['utc']),
              'Qualified inputs precede full replay')
    outputs = archive(output, complete)
    benchmark_outputs = archive(benchmark, bench_done)
    s.require(outputs == 26 and benchmark_outputs == 8, 'Expected archive scope')
    for name in ('TECHNICAL_CHECKS.json', 'PROVENANCE_AUDIT.json', 'SCORING_AUDIT.json',
                 'serial_analysis.json', 'noise_analysis.json'):
        s.require(s.sha(output / name) == s.sha(benchmark / name), 'Identical qualified evidence ' + name)
    native = s.read(output / 'NATIVE_AUDIT.json')
    score = s.read(output / 'SCORING_AUDIT.json')
    for name in ('NATIVE_AUDIT.json', 'SCORING_AUDIT.json', 'TECHNICAL_CHECKS.json', 'PROVENANCE_AUDIT.json'):
        s.require(s.read(output / name)['status'] == 'PASS', 'Audit stage ' + name)
    cfgs = {label: intake.config(label) for label in ('serial', 'noise')}
    s.require(plan['blocks'] == list(range(81000, 81016)) and plan['generations'] == list(range(15, 33)),
              'Frozen cohort and horizon')
    for cfg in cfgs.values():
        s.require(cfg['blocks'] == plan['blocks'] and cfg['generations'] == plan['generations'],
                  'Complete source cohort and horizon')
    boundary = intake.boundaries()
    endpoints = {label: {} for label in cfgs}
    totals = dict(optimizer_checks=0, constructed_records=0, unique_contexts=0, source_contexts=0,
                  matched_overlap=0, native_array_comparisons=0)
    noise_contexts = 0
    for bi, block in enumerate(plan['blocks']):
        a, b = intake.load('serial', block), intake.load('noise', block)
        receipt = s.read(output / f'replay_{block:06d}.json')
        s.require(receipt['status'] == 'PASS' and receipt['block'] == block and
                  receipt['optimizer_checks'] == 1456 and receipt['constructed_records'] == 2880,
                  'Complete block reconstruction receipt')
        s.require(receipt['structural'] == dict(status='PASS', capture_contexts=2880,
                  matched_contexts=576, noise_writer_contexts=1728), 'Structural verification scope')
        for label, raw in [('serial', a), ('noise', b)]:
            intake.continuity(raw, boundary['initial_packets'][bi], block, cfgs[label])
            endpoints[label][block] = flag_endpoints(raw)
        intake.overlap(a, b)
        s.require(len(receipt['receipts']) == 18, 'All generations have independent replay')
        for gi, replay in enumerate(receipt['receipts']):
            generation = gi + 15
            s.require(replay['status'] == 'PASS' and replay['generation'] == generation and
                      replay['label'] == f'{block}/g{generation}/all_eight_distinct_arms' and
                      (replay['unique_contexts'], replay['source_contexts'], replay['matched_overlap']) == (128, 160, 32),
                      'Generation replay identity and scope')
            s.require(replay['arrays'] == 6 and set(replay['sha256']) == set(dyn.FIELDS),
                      'Every native array checked')
            values = dyn.union(a, b, gi)
            for key in dyn.FIELDS:
                s.require(s.descriptor(values[key])['sha256'] == replay['sha256'][key],
                          'Native receipt binds to retained array ' + key)
            s.require(replay['noise_moment_max_error'] == 0 and
                      s.descriptor(b['noise_moments'][gi])['sha256'] == replay['noise_moments_sha256'],
                      'Exact independent forcing moments')
            for key in ('unique_contexts', 'source_contexts', 'matched_overlap'):
                totals[key] += replay[key]
            totals['native_array_comparisons'] += replay['arrays']
            noise_contexts += 1
        for key in ('optimizer_checks', 'constructed_records'):
            totals[key] += receipt[key]
    expected = dict(optimizer_checks=23296, constructed_records=46080, unique_contexts=36864,
                    source_contexts=46080, matched_overlap=9216, native_array_comparisons=1728)
    s.require(totals == expected and all(native[k] == v for k, v in expected.items()), 'Complete native coverage')
    s.require(noise_contexts == native['noise_contexts'] == 288 and native['max_noise_moment_error'] == 0 and
              native['all_native_states_byte_exact'] and native['full_native_replay_performed'] and
              not native['source_functions_executed'] and not native['new_scientific_cohort'], 'Full independent native audit')
    s.require(score['raw_endpoints'] == 46080 and score['dual_task_flags'] == 92160 and
              score['duplicated_matched_endpoints'] == 9216 and score['independent_blocks'] == 16 and
              not score['new_scientific_cohort'], 'Complete source scoring and overlap')
    for label, contexts in [('serial', 18432), ('noise', 27648)]:
        row = score['studies'][label]
        s.require(row['raw_endpoints'] == contexts and row['dual_task_flags'] == contexts * 2 and
                  row['descriptive_whole_block_inference'] and row['independent_bootstrap_multiplicity_check'] and
                  row['scalar_window_max_error'] < 1e-12 < row['nearest_threshold'], 'Scoring precision and scope ' + label)
    analyses = {label: s.read(output / (label + '_analysis.json')) for label in cfgs}
    counts, primary, decisions = {}, {}, {}
    for label in cfgs:
        counts[label], primary[label], decisions[label] = analysis_check(
            label, cfgs[label], endpoints[label], analyses[label])
    verdict = s.read(output / 'SCIENTIFIC_VERDICT.json')
    s.require(primary == verdict['primary'] and decisions == verdict['scientific_verdict'] ==
              complete['scientific_verdict'], 'Published scientific decisions reproduce')
    s.require(verdict['audit_status'] == 'PASS' and verdict['full_native_replay_performed'] and
              verdict['independent_blocks'] == 16 and not verdict['new_scientific_cohort'] and
              not verdict['source_scientific_functions_executed'], 'Scientific interpretation scope')
    s.require(not any(x['automatic_successor'] for x in (plan, job, complete, verdict)) and
              not any(x['automatic_polling'] for x in (plan, job, complete)), 'No automatic polling or successor')
    result = dict(status='PASS', recorded_utc=s.utc(), closeout_code_sha256=s.sha(s.HERE / 'closeout.py'),
                  completion_utc=complete['utc'], completion_sha256=s.sha(output / 'COMPLETE.json'),
                  job_sha256=s.sha(jobdir / 'job.json'), benchmark_completion_sha256=bench_hash,
                  seconds=complete['seconds'], frozen_inputs_verified=314, frozen_copies_per_input=3,
                  outputs_verified=outputs, benchmark_outputs_verified=benchmark_outputs,
                  exact_enrollment_and_lineage_continuity=True, matched_overlap_verified=True,
                  native_array_receipts_verified=1728, native_coverage=totals, noise_generation_checks=288,
                  raw_endpoints=46080, dual_task_flags=92160, independent_blocks=16, records=256,
                  generations=plan['generations'], counts=counts, primary_effects=primary,
                  all_endpoint_summaries_and_contrast_intervals_rechecked=True,
                  paired_counts={k: v['paired_counts'] for k, v in analyses.items()},
                  contrasts={k: v['contrasts'] for k, v in analyses.items()}, scientific_verdict=decisions,
                  unchanged_scientific_criteria=True, evidence_class=plan['classification'],
                  new_scientific_cohort=False, full_native_replay_complete=True,
                  source_scientific_functions_executed=False, trajectories_rerun_at_closeout=False,
                  within_apparatus_only=True, automatic_polling=False, automatic_successor=False)
    s.dump(s.HERE / 'CLOSEOUT.json', result)
    return {k: result[k] for k in ('status', 'completion_utc', 'seconds', 'frozen_inputs_verified',
                                  'outputs_verified', 'native_array_receipts_verified', 'scientific_verdict')}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
