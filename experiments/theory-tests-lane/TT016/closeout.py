"""Check completed TT016 commitments, continuity and decisions; no new trajectories."""
from datetime import datetime
import json
import numpy as np
import analysis
import statistics_block as st
import support as s

NATIVE = ('masks', 'birth', 'end', 'outgoing', 'port_windows', 'mean_ports', 'noise_moments',
          'available_edges', 'fallback_edges', 'returning_edges', 'returning_fallback_edges')


def archive(folder, complete):
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p.name not in ('STATUS.json', 'COMPLETE.json')}
    s.require(actual == set(complete['outputs_sha256']), 'Complete output membership')
    for rel, digest in complete['outputs_sha256'].items():
        s.require(s.sha(folder/rel) == digest, 'Committed output '+rel)
    return len(actual)


def arrays(receipt, values, fields):
    s.require(receipt['status'] == 'PASS' and receipt['arrays'] == len(fields) and
              set(receipt['sha256']) == set(fields), 'Complete independent array scope')
    for key in fields:
        s.require(s.descriptor(values[key])['sha256'] == receipt['sha256'][key], 'Replay commitment '+key)
    return len(fields)


def tree(actual, expected, label):
    if isinstance(expected, dict):
        s.require(isinstance(actual, dict) and set(actual) == set(expected), 'Summary schema '+label)
        for key, value in expected.items():
            tree(actual[key], value, label+'/'+key)
    elif isinstance(expected, list):
        s.require(isinstance(actual, list) and len(actual) == len(expected), 'Summary length '+label)
        for i, value in enumerate(expected):
            tree(actual[i], value, label+'/'+str(i))
    elif isinstance(expected, (str, bool)) or expected is None:
        s.require(actual == expected, 'Summary value '+label)
    else:
        s.close(actual, expected, 1e-12, 'Summary numeric '+label)


def run():
    output = s.HERE/'runs/validation_v1'
    benchmark = s.HERE/'runs/benchmark_v1'
    jobdir = s.HERE/'jobs/validation_v1'
    complete, bench_done = s.read(output/'COMPLETE.json'), s.read(benchmark/'COMPLETE.json')
    job, manifest = s.read(jobdir/'job.json'), s.read(output/'manifest.json')
    startup, started = s.read(s.HERE/'STARTUP_CHECK.json'), s.read(output/'TEST_START.json')
    cfg, registration = s.config(), s.read(s.HERE/'REGISTRATION.json')
    reg_hash = s.sha(s.HERE/'REGISTRATION.json')
    s.require(complete['status'] == 'COMPLETE' and complete['audit_status'] == 'PASS' and
              complete['mode'] == 'validation' and complete['new_scientific_cohort'] and
              complete['full_native_replay_performed'], 'Completed prospective validation')
    s.require(not (output/'FAILED.json').exists() and not (benchmark/'FAILED.json').exists(), 'No failed final runs')
    s.require(bench_done['status'] == 'COMPLETE' and bench_done['audit_status'] == 'PASS' and
              bench_done['mode'] == 'benchmark' and not bench_done['new_scientific_cohort'], 'Qualification scope')
    s.require(s.sha(jobdir/'job.json') == manifest['job_sha256'] == startup['job_sha256'], 'Job identity')
    s.require(s.sha(benchmark/'COMPLETE.json') == job['qualification']['complete_sha256'] ==
              started['benchmark_complete_sha256'] == startup['benchmark_complete_sha256'], 'Benchmark identity')
    s.require(job['inputs_sha256'] == manifest['inputs_sha256'] == s.read(benchmark/'manifest.json')['inputs_sha256'] and
              len(job['inputs_sha256']) == 61, 'Identical complete frozen inputs')
    for rel, digest in job['inputs_sha256'].items():
        for root in (s.HERE, jobdir/'inputs/TT016', s.HERE/'jobs/benchmark_v1/inputs/TT016'):
            s.require(s.sha(root/rel) == digest, 'Frozen input '+str(root/rel))
    s.require(registration['design_inputs_sha256'] ==
              {k: v for k, v in job['inputs_sha256'].items() if k != 'REGISTRATION.json'}, 'Registered executable design')
    s.require(reg_hash == manifest['registration_sha256'] == started['registration_sha256'] ==
              startup['registration_sha256'], 'Unchanged registration')
    s.require(registration['plan_sha256'] == s.sha(s.HERE/'plan.json') and
              registration['protocol_sha256'] == s.sha(s.HERE/'PROTOCOL.md'), 'Frozen scientific criteria')
    s.require(datetime.fromisoformat(registration['registered_utc']) < datetime.fromisoformat(bench_done['utc']) <
              datetime.fromisoformat(job['created_utc']) < datetime.fromisoformat(started['utc']) <
              datetime.fromisoformat(complete['utc']), 'Registration and qualification before test generation')
    s.require(startup['test_start'] == started and not started['generated_before_registration'], 'Test-start commitment')
    s.require(cfg['blocks'] == registration['blocks'] == started['planned_blocks'] == list(range(16000000, 16000064)),
              'Exact registered new cohort')
    s.require(cfg['primary_margin'] == registration['practical_margin'] == .05 and
              cfg['primary_contrast'] == registration['primary_name'] == 'independent_repeated_minus_baseline' and
              cfg['generations'] == list(range(15, 33)) and registration['endpoint'] == 'uninterrupted', 'Unchanged primary')
    outputs, benchmark_outputs = archive(output, complete), archive(benchmark, bench_done)
    s.require(outputs == 2381 and benchmark_outputs == 13, 'Every expected committed file')
    s.require({p.name for p in (output/'blocks').iterdir()} == {str(b) for b in cfg['blocks']}, 'No block substitution')
    native, scoring = s.read(output/'NATIVE_AUDIT.json'), s.read(output/'SCORING_AUDIT.json')
    s.require(native['status'] == scoring['status'] == s.read(output/'TECHNICAL_CHECKS.json')['status'] == 'PASS', 'All audit stages')
    s.require(s.sha(output/'TECHNICAL_CHECKS.json') == s.sha(benchmark/'TECHNICAL_CHECKS.json'), 'Qualified fixtures unchanged')
    panel, array_count, optimizer_count, score_count, flag_count = {}, 0, 0, 0, 0
    max_error, nearest = 0., 1.
    for block in cfg['blocks']:
        folder = output/'blocks'/str(block)
        h = (block-16000000) % 4
        r = s.read(folder/'REPLAY_AUDIT.json')
        s.require(r['status'] == 'PASS' and r['block'] == block and r['history'] == h == cfg['history_by_block'][str(block)],
                  'Block/history identity')
        for key, value in dict(optimizer_checks=1184, constructed_records=2304, preliminary_contexts=224,
                               continuation_contexts=2304, native_array_comparisons=273).items():
            s.require(r[key] == value, 'Complete block scope '+key)
        teach = s.arrays(folder/'teaching.npz')
        array_count += arrays(r['teaching'], teach, ('acquired', 'birth', 'captured', 'end', 'weights'))
        previous = np.repeat(teach['acquired'][:, None], 4, axis=1)[None]
        s.require(len(r['preliminary']) == 14 and len(r['continuations']) == 18, 'Every registered generation')
        for g, replay in enumerate(r['preliminary'], 1):
            name = f'generation_{g:02d}.npz'
            raw = s.arrays(folder/name)
            s.require(replay['file'] == name and replay['file_sha256'] == s.sha(folder/name), 'Preliminary evidence identity')
            s.require(replay['generation'] == int(raw['generation']) == g and int(raw['history']) == h and
                      replay['writer_code'] == int(g in cfg['tolerance_generations'][h]) and replay['contexts'] == 16,
                      'Registered preliminary writer schedule')
            s.equal(previous, raw['incoming'], 'Every preliminary successor')
            array_count += arrays(replay, raw, ('birth', 'end', 'masks', 'mean_ports', 'outgoing'))
            previous = raw['outgoing']
        enrolled = s.arrays(folder/'enrollment.npz')
        seal, continued = s.read(folder/'ENROLLMENT_SEAL.json'), s.read(folder/'CONTINUATION_STARTED.json')
        s.require(seal['block'] == continued['block'] == int(enrolled['block']) == block and
                  seal['history'] == int(enrolled['history']) == h and seal['records'] == 16 and
                  seal['registration_sha256'] == reg_hash and continued['first_generation'] == 15, 'All-record enrollment')
        s.require(seal['boundary_sha256'] == s.sha(folder/'generation_14.npz') and
                  seal['enrollment_sha256'] == s.sha(folder/'enrollment.npz') and
                  continued['seal_sha256'] == s.sha(folder/'ENROLLMENT_SEAL.json'), 'Enrollment commitment links')
        s.require(datetime.fromisoformat(started['utc']) < datetime.fromisoformat(seal['utc']) <
                  datetime.fromisoformat(continued['utc']) < datetime.fromisoformat(complete['utc']), 'Enrollment precedes continuation')
        s.equal(previous.reshape(16, 4096), enrolled['initial_packets'], 'Every actual generation-14 outgoing record')
        s.equal(raw['masks'].reshape(16, 16, 16), enrolled['previous_mask'], 'Actual prior injury')
        s.require(s.descriptor(enrolled['initial_packets'])['sha256'] == seal['outgoing_sha256'], 'Enrolled outgoing hash')
        initial = []
        for case, ports in enumerate(raw['mean_ports'].reshape(16, 2, 2)):
            sign = 1 if (case//4) % 2 == 0 else -1
            initial.append(min(sign*ports[0, 0], -sign*ports[0, 1], -sign*ports[1, 0], sign*ports[1, 1]) > .25)
        s.equal(np.array(initial), enrolled['initial_pass'], 'Descriptive initial flags')
        previous = np.repeat(enrolled['initial_packets'][None], 8, axis=0)
        good, other = [], []
        for g, replay in zip(cfg['generations'], r['continuations']):
            name = f'continuation_{g:02d}.npz'
            raw = s.arrays(folder/name)
            s.require(replay['file'] == name and replay['file_sha256'] == s.sha(folder/name), 'Continuation evidence identity')
            s.require(replay['generation'] == int(raw['generation']) == g and int(raw['block']) == block and
                      int(raw['history']) == h and replay['contexts'] == replay['constructed_records'] == 128 and
                      replay['label'] == f"{cfg['continuation_namespace']}:{block}/g{g}/all_eight_policies" and
                      replay['noise_moments_byte_exact'], 'Complete continuation replay')
            s.equal(previous, raw['incoming'], 'Actual body-written successor on every branch')
            s.require(raw['incoming'].shape == raw['prepared'].shape == raw['outgoing'].shape == (8, 16, 4096), 'Complete branch records')
            array_count += arrays(replay, raw, NATIVE)
            active = np.repeat(np.array([False, g == 15, True, True]*2)[:, None], 16, axis=1)
            s.equal(active, raw['applied'], 'Fixed recurring and one-time schedules')
            calls = int(active.sum())
            s.require(int(raw['independent_optimizer_checks']) == replay['optimizer_checks'] == calls, 'Every scheduled optimizer slot')
            optimizer_count += calls
            for vi in range(8):
                if not active[vi, 0]:
                    s.equal(raw['prepared'][vi], raw['incoming'][vi], 'Inactive branch unchanged')
            incoming_weights = np.frombuffer(raw['incoming'].tobytes(), '<f8').reshape(8, 16, 512)
            prepared_weights = np.frombuffer(raw['prepared'].tobytes(), '<f8').reshape(8, 16, 512)
            observed = incoming_weights != 0
            s.equal(incoming_weights[observed], prepared_weights[observed], 'Every observed edge preserved')
            s.equal((~observed).sum(axis=-1), raw['missing_edges'], 'All missing-edge counts')
            s.equal(((prepared_weights != 0) & ~observed).sum(axis=-1), raw['added_edges'], 'All added-edge counts')
            if g == 15:
                for vi in range(4):
                    s.equal(raw['prepared'][vi], raw['prepared'][vi+4], 'Initial preparations paired across noise')
                for offset in (0, 4):
                    for key in ('prepared', 'end', 'outgoing', 'mean_ports', 'both_pass', 'opposite_pass'):
                        s.equal(raw[key][offset+1], raw[key][offset+2], 'First one-time/repeated identity')
                    s.equal(raw['port_windows'][:, offset+1], raw['port_windows'][:, offset+2], 'First paired windows')
            score = replay['scoring']
            s.require(score['status'] == 'PASS' and score['raw_endpoints'] == 128 and score['dual_task_flags'] == 256,
                      'Complete independently scored windows')
            score_count += score['raw_endpoints']; flag_count += score['dual_task_flags']
            max_error = max(max_error, score['scalar_window_max_error']); nearest = min(nearest, score['nearest_threshold'])
            good.append(raw['both_pass']); other.append(raw['opposite_pass']); previous = raw['outgoing']
        panel[block] = dict(intended=np.stack(good), opposite=np.stack(other), initial=np.array(initial))
    s.require(array_count == 17472 and optimizer_count == 75776 and score_count == 147456 and flag_count == 294912,
              'Full verified scope')
    for key, value in dict(blocks=64, teaching_replays=64, preliminary_contexts=14336, continuation_contexts=147456,
                           constructed_records=147456, optimizer_checks=75776, native_array_comparisons=17472,
                           noise_generation_checks=1152, all_native_states_byte_exact=True, noise_moments_byte_exact=True).items():
        s.require(native[key] == value, 'Native total '+key)
    s.require(scoring['raw_endpoints'] == score_count and scoring['dual_task_flags'] == flag_count and
              scoring['scalar_window_max_error'] == max_error and scoring['nearest_threshold'] == nearest and
              max_error < 1e-12 < nearest and scoring['independent_integer_interval_audit'] and
              scoring['independent_bootstrap_multiplicities'] and scoring['independent_blocks'] == 64, 'Scoring scope and precision')
    computed, rows, counts = analysis.summarize(panel, cfg)
    published = s.read(output/'analysis.json')
    for key, value in computed.items():
        tree(published[key], value, key)
    s.require(counts == s.read(output/'block_contrast_counts.json'), 'Raw integer primary contrasts')
    st.audit_bounds(counts, .05, published['primary_effect'])
    st.audit_bootstrap(counts, cfg, published['primary_effect']['descriptive_stratified_block_bootstrap95'])
    retained_rows = s.table(output/'block_summaries.csv')
    s.require(len(retained_rows) == len(rows) == 512, 'All block endpoint summaries')
    for actual, expected in zip(retained_rows, rows):
        s.require(actual == {k: str(v) for k, v in expected.items()}, 'Recomputed block summary row')
    verdict = s.read(output/'SCIENTIFIC_VERDICT.json')
    s.require(verdict['primary_effect'] == published['primary_effect'] and
              verdict['scientific_verdict'] == complete['scientific_verdict'] == computed['scientific_verdict'] and
              verdict['primary_name'] == cfg['primary_contrast'] and verdict['primary_endpoint'] == 'uninterrupted',
              'Unchanged primary classification')
    s.require(verdict['within_apparatus_only'] and verdict['new_scientific_cohort'] and
              verdict['full_native_replay_performed'] and not verdict['subgroup_rescue_permitted'], 'Interpretation boundaries')
    s.require(not any(x['automatic_successor'] for x in (cfg, job, complete, verdict)) and
              not any(x['automatic_polling'] for x in (cfg, job, complete)), 'No automatic polling or successor')
    result = dict(status='PASS', recorded_utc=s.utc(), closeout_code_sha256=s.sha(s.HERE/'closeout.py'),
        completion_utc=complete['utc'], completion_sha256=s.sha(output/'COMPLETE.json'), seconds=complete['seconds'],
        job_sha256=s.sha(jobdir/'job.json'), registration_sha256=reg_hash,
        benchmark_completion_sha256=s.sha(benchmark/'COMPLETE.json'), frozen_inputs_verified=61,
        frozen_copies_per_input=3, outputs_verified=outputs, benchmark_outputs_verified=benchmark_outputs,
        registration_before_test=True, enrollment_seals_verified=64, exact_cohort_and_lineage_continuity=True,
        native_array_receipts_verified=array_count, teaching_replays=64, preliminary_contexts=14336,
        continuation_contexts=147456, optimizer_checks=optimizer_count, constructed_records=147456,
        noise_generation_checks=1152, raw_endpoints=score_count, dual_task_flags=flag_count,
        endpoint_summaries_and_contrast_intervals_rechecked=True, primary_effect=published['primary_effect'],
        primary_counts=counts, rate_summaries=published['rates'], contrasts=published['contrasts'],
        paired_counts=published['paired_counts'], pre_repair_subgroups=published['pre_repair_subgroups'],
        scientific_verdict=computed['scientific_verdict'], independent_integer_intervals_rechecked=True,
        unchanged_scientific_criteria=True, new_scientific_cohort=True, test_blocks_now_exposed=cfg['blocks'],
        within_apparatus_only=True, trajectories_rerun_at_closeout=False, automatic_polling=False, automatic_successor=False)
    s.dump(s.HERE/'CLOSEOUT.json', result)
    return {k: result[k] for k in ('status', 'completion_utc', 'seconds', 'frozen_inputs_verified',
                                  'outputs_verified', 'native_array_receipts_verified', 'scientific_verdict')}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
