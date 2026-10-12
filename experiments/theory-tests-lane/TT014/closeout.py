"""Verify completed TT014 evidence without generating or rerunning trajectories."""
from datetime import datetime
import json
import math

import numpy as np

import statistics_block as st
import support as s


def archive(folder, complete):
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p.name not in ('STATUS.json', 'COMPLETE.json')}
    s.require(actual == set(complete['outputs_sha256']), 'Complete output membership')
    for rel, digest in complete['outputs_sha256'].items():
        s.require(s.sha(folder / rel) == digest, 'Output identity ' + rel)
    return len(actual)


def receipt_arrays(receipt, values, fields):
    s.require(receipt['status'] == 'PASS', 'Independent replay passed')
    s.require(set(receipt['sha256']) == set(fields) and receipt['arrays'] == len(fields),
              'Complete replay array scope')
    for key in fields:
        s.require(s.descriptor(values[key])['sha256'] == receipt['sha256'][key],
                  'Replay array identity ' + key)
    return len(fields)


def run():
    output = s.HERE / 'runs/validation_v1'
    jobdir = s.HERE / 'jobs/validation_v1'
    benchmark = s.HERE / 'runs/benchmark_v1'
    complete = s.read(output / 'COMPLETE.json')
    job = s.read(jobdir / 'job.json')
    manifest = s.read(output / 'manifest.json')
    startup = s.read(s.HERE / 'STARTUP_CHECK.json')
    bench_done = s.read(benchmark / 'COMPLETE.json')
    bench_manifest = s.read(benchmark / 'manifest.json')
    cfg = s.config()
    registration = s.read(s.HERE / 'REGISTRATION.json')
    reg_sha = s.sha(s.HERE / 'REGISTRATION.json')
    started = s.read(output / 'TEST_START.json')
    s.require(complete['status'] == 'COMPLETE' and complete['audit_status'] == 'PASS'
              and complete['mode'] == 'validation' and complete['new_scientific_cohort'],
              'Completed prospective validation')
    s.require(not (output / 'FAILED.json').exists(), 'No failed final run')
    s.require(s.sha(jobdir / 'job.json') == manifest['job_sha256'] == startup['job_sha256'],
              'Job and startup identity')
    s.require(bench_done['status'] == 'COMPLETE' and bench_done['audit_status'] == 'PASS'
              and bench_done['mode'] == 'benchmark', 'Successful qualification')
    s.require(s.sha(benchmark / 'COMPLETE.json') == job['qualification']['complete_sha256']
              == started['benchmark_complete_sha256'], 'Benchmark identity')
    s.require(job['inputs_sha256'] == manifest['inputs_sha256'] == bench_manifest['inputs_sha256'],
              'Identical qualification and validation inputs')
    s.require(len(job['inputs_sha256']) == 47, 'Complete frozen input scope')
    for rel, digest in job['inputs_sha256'].items():
        for root in (s.HERE, jobdir / 'inputs/TT014',
                     s.HERE / 'jobs/benchmark_v1/inputs/TT014'):
            s.require(s.sha(root / rel) == digest, 'Frozen input ' + str(root / rel))
    s.require(registration['design_inputs_sha256'] ==
              {k: v for k, v in job['inputs_sha256'].items() if k != 'REGISTRATION.json'},
              'Registered executable inputs')
    s.require(reg_sha == manifest['registration_sha256'] == started['registration_sha256'],
              'Registration identity')
    s.require(registration['plan_sha256'] == s.sha(s.HERE / 'plan.json') and
              registration['protocol_sha256'] == s.sha(s.HERE / 'PROTOCOL.md'), 'Registered design')
    s.require(datetime.fromisoformat(registration['registered_utc']) <
              datetime.fromisoformat(bench_done['utc']) <
              datetime.fromisoformat(job['created_utc']) <
              datetime.fromisoformat(started['utc']) < datetime.fromisoformat(complete['utc']),
              'Registration and qualification precede test generation')
    s.require(startup['test_start'] == started and not started['generated_before_registration'],
              'Unchanged test-start record')
    s.require(cfg['blocks'] == registration['blocks'] == started['planned_blocks'] ==
              list(range(14000000, 14000064)), 'Exact registered cohort')
    s.require(cfg['primary_margins'] == registration['margins'] ==
              dict(recipient_minus_outgoing=.02, recipient_minus_shuffled=.05), 'Unchanged margins')
    benchmark_outputs = archive(benchmark, bench_done)
    outputs = archive(output, complete)
    s.require({p.name for p in (output / 'blocks').iterdir()} ==
              {str(b) for b in cfg['blocks']}, 'No additional or omitted blocks')
    native = s.read(output / 'NATIVE_AUDIT.json')
    scoring = s.read(output / 'SCORING_AUDIT.json')
    technical = s.read(output / 'TECHNICAL_CHECKS.json')
    s.require(all(x['status'] == 'PASS' for x in (native, scoring, technical)), 'All audit stages')
    s.require(s.sha(output / 'TECHNICAL_CHECKS.json') == s.sha(benchmark / 'TECHNICAL_CHECKS.json'),
              'Qualified fixture checks retained unchanged')

    array_receipts = 0
    panel = {}
    counts = {'recipient_minus_outgoing': [[] for _ in range(4)],
              'recipient_minus_shuffled': [[] for _ in range(4)]}
    initial_counts = {False: 0, True: 0}
    for block in cfg['blocks']:
        folder = output / 'blocks' / str(block)
        h = (block - 14000000) % 4
        s.require(cfg['history_by_block'][str(block)] == h, 'Balanced history identity')
        r = s.read(folder / 'REPLAY_AUDIT.json')
        s.require(r['status'] == 'PASS' and r['block'] == block and r['history'] == h,
                  'Block replay identity')
        s.require((r['optimizer_checks'], r['records'], r['rebuild_contexts'], r['assessment_contexts'])
                  == (16, 64, 224, 512), 'Block scope')
        teach = s.arrays(folder / 'teaching.npz')
        array_receipts += receipt_arrays(r['teaching'], teach,
                                        ('acquired', 'birth', 'captured', 'end', 'weights'))
        previous = np.repeat(teach['acquired'][:, None], 4, axis=1)[None]
        s.require(len(r['rebuilds']) == 14, 'Every generation replayed')
        for generation, replay in enumerate(r['rebuilds'], 1):
            name = f'generation_{generation:02d}.npz'
            raw = s.arrays(folder / name)
            s.require(replay['file'] == name and replay['file_sha256'] == s.sha(folder / name),
                      'Retained rebuild identity')
            s.require(replay['generation'] == int(raw['generation']) == generation and
                      int(raw['history']) == h and
                      replay['writer_code'] == int(generation in cfg['tolerance_generations'][h]),
                      'Registered writer schedule')
            s.equal(previous, raw['incoming'], 'Complete generation continuity')
            array_receipts += receipt_arrays(replay, raw,
                                            ('birth', 'end', 'masks', 'mean_ports', 'outgoing'))
            previous = raw['outgoing']
        boundary = raw
        prepared = s.arrays(folder / 'prepared.npz')
        seal = s.read(folder / 'ENROLLMENT_SEAL.json')
        assessment_start = s.read(folder / 'ASSESSMENT_STARTED.json')
        s.require(seal['block'] == assessment_start['block'] == block and
                  seal['history'] == h and seal['records'] == 16 and
                  seal['registration_sha256'] == reg_sha, 'All-record enrollment')
        s.require(seal['boundary_sha256'] == s.sha(folder / 'generation_14.npz') and
                  seal['prepared_sha256'] == s.sha(folder / 'prepared.npz') and
                  assessment_start['seal_sha256'] == s.sha(folder / 'ENROLLMENT_SEAL.json'),
                  'Enrollment commitment links')
        s.require(datetime.fromisoformat(started['utc']) < datetime.fromisoformat(seal['utc']) <
                  datetime.fromisoformat(assessment_start['utc']) < datetime.fromisoformat(complete['utc']),
                  'Each enrolled packet sealed before assessment')
        outgoing = previous.reshape(16, 4096)
        s.equal(outgoing, prepared['packets'][:, 0], 'Every outgoing record enrolled')
        s.require(seal['outgoing_sha256'] == s.descriptor(outgoing)['sha256'], 'Outgoing commitment')
        s.equal(prepared['founders'], np.repeat(np.arange(4), 4), 'All founders')
        s.equal(prepared['recipients'], np.tile(np.arange(4), 4), 'All recipients')
        means = boundary['mean_ports'].reshape(16, 2, 2)
        initial = []
        for case, ports in enumerate(means):
            rule = 1 if (case // 4) % 2 == 0 else -1
            initial.append(min(rule*ports[0, 0], -rule*ports[0, 1],
                               -rule*ports[1, 0], rule*ports[1, 1]) > .25)
        s.equal(np.array(initial), prepared['initial_pass'], 'Descriptive pre-repair labels')
        for flag in initial:
            initial_counts[bool(flag)] += 1
        assessment = s.arrays(folder / 'assessment.npz')
        array_receipts += receipt_arrays(r['assessment'], assessment,
                                        ('birth', 'budgets', 'end', 'mean_ports', 'port_windows'))
        s.require(r['assessment']['contexts'] == 512 and
                  assessment['both_pass'].shape == assessment['opposite_pass'].shape == (1, 16, 4, 8),
                  'Complete assessment panel')
        panel[block] = {key: assessment[field][0] for key, field in
                        [('intended', 'both_pass'), ('opposite', 'opposite_pass')]}
        panel[block]['initial'] = np.array(initial)
        for name, right in [('recipient_minus_outgoing', 0), ('recipient_minus_shuffled', 2)]:
            passed = panel[block]['intended']
            counts[name][h].append(int(passed[:, 1].sum()) - int(passed[:, right].sum()))

    s.require(array_receipts == 5120, 'All native replay array commitments')
    for key, value in dict(blocks=64, teaching_replays=64, rebuild_contexts=14336,
                           assessment_contexts=32768, optimizer_checks=1024,
                           constructed_records=4096, all_native_states_byte_exact=True).items():
        s.require(native[key] == value, 'Native scope ' + key)
    s.require(scoring['raw_endpoints'] == 32768 and scoring['dual_task_flags'] == 65536 and
              scoring['all_enrollment_seals_precede_assessments'] and
              scoring['independent_integer_interval_audit'], 'Scoring and interval audit scope')
    s.require(scoring['scalar_window_max_error'] < 1e-12 < scoring['nearest_threshold_distance'],
              'Scores resolved away from strict threshold')
    s.require(counts == s.read(output / 'block_contrast_counts.json'), 'Raw flag contrast counts')
    analysis = s.read(output / 'analysis.json')
    verdict = s.read(output / 'SCIENTIFIC_VERDICT.json')
    for vi, variant in enumerate(cfg['variants']):
        for task in ('intended', 'opposite'):
            successes = sum(int(panel[b][task][:, vi].sum()) for b in cfg['blocks'])
            row = analysis['rate_summaries'][variant][task]
            s.require(row['successes'] == successes and row['reads'] == 8192 and
                      row['mean'] == successes / 8192, 'Complete success rate ' + variant)
            for h, history in enumerate(cfg['histories']):
                total = sum(int(panel[b][task][:, vi].sum()) for b in cfg['blocks'] if (b-14000000) % 4 == h)
                s.require(row['by_history'][history] == total / 2048, 'History success rate')
    for flag, name in [(False, 'initially_failing'), (True, 'initially_passing')]:
        group = analysis['pre_repair_subgroups'][name]
        records = initial_counts[flag]
        s.require(group['records'] == records and group['reads_per_variant'] == records * 8,
                  'Descriptive subgroup denominator')
        for vi, variant in enumerate(cfg['variants']):
            for task in ('intended', 'opposite'):
                total = sum(int(p[task][p['initial'] == flag, vi].sum()) for p in panel.values())
                s.require(group['rates'][variant][task] == total and
                          group['rates'][variant][task + '_rate'] == total / (records * 8),
                          'Descriptive subgroup rate')
    for name, rows in counts.items():
        effect = analysis['primary_effects'][name]
        st.audit_bounds(rows, cfg['primary_margins'][name], effect)
        st.audit_bootstrap(rows, cfg, effect['descriptive_stratified_bootstrap95'])
        expected_blocks = {str(b): rows[(b-14000000) % 4][(b-14000000) // 4] / 128
                           for b in cfg['blocks']}
        s.require(effect['by_block'] == expected_blocks, 'Every reported block contrast')
        for label, check in [('positive_blocks', lambda x: x > 0), ('tied_blocks', lambda x: x == 0),
                             ('negative_blocks', lambda x: x < 0)]:
            s.require(effect[label] == sum(check(x) for x in expected_blocks.values()), 'Block directions')
        right = 0 if name == 'recipient_minus_outgoing' else 2
        pairs = dict(left_only=0, right_only=0, both=0, neither=0, reads=8192)
        for p in panel.values():
            x, y = p['intended'][:, 1], p['intended'][:, right]
            for key, values in [('left_only', x & ~y), ('right_only', y & ~x),
                                ('both', x & y), ('neither', ~(x | y))]:
                pairs[key] += int(values.sum())
        s.require(pairs == analysis['paired_counts'][name], 'Paired success accounting')
    passed = all(e['lower_one_sided95'] > cfg['primary_margins'][name]
                 for name, e in analysis['primary_effects'].items())
    decision = ('PRACTICAL_SUPERIORITY_PASS' if passed else 'PRACTICAL_SUPERIORITY_UNSUPPORTED'
                if any(e['upper_one_sided95'] < cfg['primary_margins'][name]
                       for name, e in analysis['primary_effects'].items())
                else 'PRACTICAL_SUPERIORITY_INCONCLUSIVE')
    s.require(verdict['primary_effects'] == analysis['primary_effects'] and
              verdict['conjunction_pass'] == analysis['conjunction_pass'] == passed and
              verdict['scientific_verdict'] == analysis['scientific_verdict'] ==
              complete['scientific_verdict'] == decision, 'Unchanged scientific conjunction')
    s.require(verdict['within_apparatus_only'] and verdict['new_scientific_cohort'] and
              analysis['new_cohort'] and analysis['fitted_models'] == 0 and
              not analysis['subgroup_rescue_permitted'], 'Prospective interpretation boundaries')
    s.require(not any(x['automatic_successor'] for x in (cfg, job, complete, verdict)),
              'No automatic successor')
    result = dict(status='PASS', recorded_utc=s.utc(), closeout_code_sha256=s.sha(s.HERE/'closeout.py'),
                  completion_utc=complete['utc'], completion_sha256=s.sha(output/'COMPLETE.json'),
                  registration_sha256=reg_sha, job_sha256=s.sha(jobdir/'job.json'),
                  benchmark_completion_sha256=s.sha(benchmark/'COMPLETE.json'),
                  seconds=complete['seconds'], frozen_inputs_verified=47,
                  outputs_verified=outputs, benchmark_outputs_verified=benchmark_outputs,
                  registration_before_test=True, enrollment_seals_verified=64,
                  exact_cohort_and_lineage_continuity=True, native_array_receipts_verified=array_receipts,
                  teaching_replays=64, rebuild_contexts=14336, assessment_contexts=32768,
                  optimizer_checks=1024, constructed_records=4096, dual_task_flags=65536,
                  primary_effects=analysis['primary_effects'], rate_summaries=analysis['rate_summaries'],
                  paired_counts=analysis['paired_counts'], pre_repair_subgroups=analysis['pre_repair_subgroups'],
                  scientific_verdict=decision, conjunction_pass=passed,
                  independent_integer_intervals_rechecked=True, unchanged_scientific_criteria=True,
                  new_scientific_cohort=True, test_blocks_now_exposed=cfg['blocks'],
                  within_apparatus_only=True, trajectories_rerun_at_closeout=False,
                  automatic_polling=False, automatic_successor=False)
    s.dump(s.HERE/'CLOSEOUT.json', result)
    return {k: result[k] for k in ('status', 'completion_utc', 'seconds', 'frozen_inputs_verified',
                                  'outputs_verified', 'native_array_receipts_verified', 'scientific_verdict')}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
