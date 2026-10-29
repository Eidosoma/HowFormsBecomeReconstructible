"""Verify completed TT018 evidence, including the two-CPU handover.

Prepared after first completed-result inspection. Reuses frozen scoring checks,
adds provenance and retained-array checks, and generates no new trajectories.
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import traceback

STUDY = Path(__file__).resolve().parent
SOURCE = STUDY / 'jobs/validation_v1/inputs/TT018'
sys.path.insert(0, str(SOURCE))
import numpy as np
import scipy
import analysis
import capacity
import engine
import record_features
import report
import serial_audit
import support as s

CHECK = STUDY / 'closeout_checks/v1'


def archive(folder, complete):
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p.name not in ('STATUS.json', 'COMPLETE.json')}
    s.require(actual == set(complete['outputs_sha256']), 'Exact retained output membership ' + str(folder))
    for rel, digest in complete['outputs_sha256'].items():
        s.require(s.sha(folder / rel) == digest, 'Retained output commitment ' + rel)
    return len(actual)


def array_receipt(receipt, raw, fields):
    s.require(receipt['status'] == 'PASS' and receipt['arrays'] == len(fields)
              and set(receipt['sha256']) == set(fields), 'Full native array scope')
    for name in fields:
        s.require(s.descriptor(raw[name])['sha256'] == receipt['sha256'][name], 'Native replay array ' + name)
    return len(fields)


def forbid_trajectories(*args, **kwargs):
    raise ValueError('Closeout must not generate or replay trajectories')


def retained_environment(raw, record, futures, generation, cfg, terminal):
    expected = serial_audit.Draws(record, futures, generation, cfg['development_config'], terminal)
    s.equal(raw['masks'], expected.masks, 'Independently reconstructed injury')
    s.equal(raw['birth'], expected.birth, 'Independently reconstructed cue resets')
    s.require(not np.array_equal(raw['birth'][:, 0], raw['birth'][:, 1]), 'Separate cue resets')
    s.require(int(raw['forcing_steps']) == cfg['cycle']['read_steps'] == 2048, 'Every forcing update')
    s.equal(raw['noise_moments'][:, 5], np.full(len(futures), 2048 * 256, float), 'Complete forcing draw count')


def retained_repair(raw, generation):
    incoming = np.frombuffer(raw['incoming'].tobytes(), '<f8').reshape(3, -1, 512)
    prepared = np.frombuffer(raw['prepared'].tobytes(), '<f8').reshape(incoming.shape)
    observed = incoming != 0
    s.equal(incoming[observed], prepared[observed], 'Every surviving edge retained')
    s.equal((~observed).sum(axis=-1), raw['missing_edges'], 'Missing edge counts')
    s.equal(((prepared != 0) & ~observed).sum(axis=-1), raw['added_edges'], 'Added edge counts')
    expected_mass = np.where(~observed, np.abs(prepared), 0.).sum(axis=-1)
    s.close(expected_mass, raw['added_abs_weight'], 2e-12, 'Added weight totals')
    for policy in range(3):
        active = policy == 2 or (policy == 1 and generation == 15)
        if not active:
            s.equal(prepared[policy], incoming[policy], 'Untreated or inactive policy bytes')
            continue
        for future in range(incoming.shape[1]):
            w = incoming[policy, future]
            nonzero = np.abs(w[w != 0])
            magnitude = float(np.median(nonzero)) if len(nonzero) else 0.
            s.require(float(raw['magnitude'][policy, future]) == magnitude, 'Current-record magnitude only')
            nodes = raw['optimizer_signs'][policy, future].reshape(16, 16)
            signs = np.stack((nodes * np.roll(nodes, -1, -1), nodes * np.roll(nodes, -1, -2))).reshape(512)
            expected = w.copy()
            if magnitude > 0:
                expected[w == 0] = magnitude * signs[w == 0]
            s.equal(prepared[policy, future], expected, 'Saved optimizer signs construct exactly the prepared packet')


def fixtures(cfg):
    folder = STUDY / 'runs/native_v3/full_batch'
    # Use the excluded full-size fixture, never alter completed scientific data.
    candidates = sorted((STUDY / 'runs/native_v3').rglob('g15.npz'))
    s.require(bool(candidates), 'Excluded native fixture retained')
    path = next(p for p in candidates if '/full_batch/' in str(p)) if any('/full_batch/' in str(p) for p in candidates) else candidates[0]
    raw = s.arrays(path)
    retained_repair(raw, 15)
    rejected = []
    for field in ('prepared', 'added_edges', 'magnitude'):
        corrupt = {k: v.copy() for k, v in raw.items()}
        if field == 'prepared':
            corrupt[field].flat[0] ^= np.uint8(1)
        elif field == 'added_edges':
            corrupt[field].flat[0] += 1
        else:
            corrupt[field][2, 0] = np.nextafter(corrupt[field][2, 0], np.inf)
        try:
            retained_repair(corrupt, 15)
        except ValueError:
            rejected.append(field)
        else:
            raise ValueError('Accepted deliberately corrupted ' + field)
    return dict(status='PASS', fixture=str(path.relative_to(STUDY)), corruptions_rejected=rejected,
                prospective_outcomes_used_for_fixtures=False)


def run():
    began = time.monotonic()
    output = STUDY / 'runs/validation_two_cpu_v1'
    original_output = STUDY / 'runs/validation_v1'
    jobdir = STUDY / 'jobs/validation_two_cpu_v1'
    original_jobdir = STUDY / 'jobs/validation_v1'
    complete, manifest = s.read(output / 'COMPLETE.json'), s.read(output / 'manifest.json')
    job, original = s.read(jobdir / 'job.json'), s.read(original_jobdir / 'job.json')
    reg, cfg = s.read(STUDY / 'REGISTRATION.json'), s.config()
    qualification = STUDY / 'runs/native_v3'
    qdone = s.read(qualification / 'COMPLETE.json')
    controller_qual_path = Path(job['qualification'])
    controller_qual = s.read(controller_qual_path)
    started = s.read(output / 'TEST_START.json')
    amendment = s.read(STUDY / 'EXECUTION_TWO_CPU_AMENDMENT.json')
    checkpoint = s.read(jobdir / 'SOURCE_CHECKPOINT.json')
    migration = s.read(STUDY / 'two_cpu_v1/MIGRATION_COMPLETE.json')
    startup = s.read(jobdir / 'STARTUP_CHECK.json')
    s.require(complete['status'] == 'COMPLETE' and complete['audit_status'] == 'PASS'
              and complete['mode'] == 'validation' and complete['resumed_registered_cohort']
              and not complete['new_cohort_created_by_migration'], 'Completed same-cohort validation')
    s.require(not (output / 'FAILED.json').exists(), 'No failed final run')
    s.require(s.sha(jobdir / 'job.json') == manifest['job_sha256'], 'Completed controller identity')
    s.require(manifest['pid'] == startup['pid'] == migration['controller_pid'], 'Startup and handover controller')
    s.require(s.sha(STUDY / 'EXECUTION_TWO_CPU_AMENDMENT.json') == job['amendment_sha256'] == migration['amendment_sha256'], 'Execution amendment binding')
    s.require(s.sha(jobdir / 'SOURCE_CHECKPOINT.json') == migration['source_checkpoint_sha256'], 'Preserved checkpoint binding')
    s.require(s.sha(jobdir / 'STARTUP_CHECK.json') == migration['startup_check_sha256'] and startup['status'] == 'PASS', 'Verified delayed startup')
    s.require(s.sha(jobdir / 'STARTUP_RECOVERY.json') == migration['startup_recovery_sha256'], 'Disclosed startup recovery')
    s.require(amendment['authorized_workers'] == manifest['workers'] == 2 and manifest['numerical_threads_per_worker'] == 1, 'Explicit two-worker amendment')
    s.require(manifest['source_inputs_sha256'] == job['source_inputs_sha256'] == original['inputs_sha256'] == reg['runtime_inputs_sha256'], 'Unchanged scientific executable contract')
    s.require(len(original['inputs_sha256']) == 43 and len(original['extra_inputs_sha256']) == 6, 'Complete frozen input inventory')
    s.require(s.sha(STUDY / 'PROTOCOL.md') == reg['protocol_sha256'], 'Registered primary text unchanged')
    for rel, digest in original['inputs_sha256'].items():
        for root in (STUDY, SOURCE, STUDY / 'jobs/native_v3/inputs/TT018'):
            s.require(s.sha(root / rel) == digest, 'Original runtime input ' + str(root / rel))
    for rel, digest in original['extra_inputs_sha256'].items():
        for root in (STUDY, SOURCE):
            s.require(s.sha(root / rel) == digest, 'Original registration/context input ' + str(root / rel))
    for name, digest in job['controller_inputs_sha256'].items():
        for root in (jobdir / 'inputs', STUDY / 'two_cpu_v1', STUDY / 'two_cpu_v1/jobs/qualification_v2/inputs'):
            s.require(s.sha(root / name) == digest, 'Qualified controller input ' + str(root / name))
    s.require(job['controller_inputs_sha256'] == manifest['controller_inputs_sha256'] == controller_qual['controller_inputs_sha256'], 'Identical qualified controller')
    s.require(s.sha(controller_qual_path) == job['qualification_sha256'] == amendment['qualification_sha256'], 'Selected controller qualification')
    s.require(controller_qual['status'] == 'PASS' and controller_qual['byte_exact_array_comparisons'] == 1603, 'Complete controller qualification')
    s.require(s.sha(qualification / 'COMPLETE.json') == reg['qualification_complete_sha256'] == started['qualification_complete_sha256'], 'Original qualification binding')
    s.require(s.sha(STUDY / 'REGISTRATION.json') == started['registration_sha256'] == amendment['original_registration_sha256'], 'Original registration identity')
    s.require(manifest['python'] == sys.version and manifest['numpy'] == np.__version__ and manifest['scipy'] == scipy.__version__, 'Recorded numerical environment')
    parse = datetime.fromisoformat
    s.require(parse(qdone['utc']) < parse(reg['registered_utc']) < parse(original['created_utc']) < parse(started['utc']), 'Qualification and registration precede first acquisition')
    s.require(parse(controller_qual['utc']) < parse(amendment['utc']) <= parse(job['created_utc']) < parse(manifest['started_utc']), 'Amendment and qualification precede two-worker execution')
    s.require(parse(complete['utc']).timestamp() < job['absolute_deadline_epoch'] == parse(original['created_utc']).timestamp() + 172800, 'Original absolute deadline met')
    s.require(cfg['blocks'] == reg['blocks'] == started['blocks'] == list(range(18000000, 18000064)), 'Exact original cohort')
    s.require(cfg['primary_margin'] == reg['practical_margin'] == .02 and reg['primary_endpoint'] == 'fresh_terminal_recipient'
              and reg['primary_contrast'] == 'repeated_minus_untreated' and cfg['futures'] == 64, 'Unchanged registered inference')
    s.require(checkpoint['completed_acquisitions'] == 25 and checkpoint['completed_prefix_generations'] == 10, 'Retained handover scope')
    s.require(checkpoint['inherited_files_sha256'] == job['inherited_files_sha256'], 'Same inherited files')
    for rel, digest in checkpoint['source_files_sha256'].items():
        path = STUDY / 'two_cpu_v1/ORIGINAL_STATUS_AT_PAUSE.json' if rel == 'STATUS.json' else original_output / rel
        s.require(s.sha(path) == digest, 'Every original pre-handover file ' + rel)
    for rel, digest in checkpoint['inherited_files_sha256'].items():
        s.require(s.sha(output / rel) == digest, 'Inherited evidence unchanged through completion ' + rel)
    outputs = archive(output, complete)
    qualification_outputs = archive(qualification, qdone)
    for rel, digest in controller_qual['outputs_sha256'].items():
        s.require(s.sha(controller_qual_path.parent / rel) == digest, 'Controller qualification evidence')
    s.require(outputs == 6800 and qualification_outputs == 57, 'Complete output coverage')
    s.require({p.name for p in (output / 'records').iterdir()} == {str(b) for b in cfg['blocks']}, 'No cohort substitution')
    fixture = fixtures(cfg)
    s.dump(CHECK / 'FIXTURE_CHECK.json', fixture)

    counts = dict(acquisition_arrays=0, reconstructed_environments=0, retained_optimizer_constructions=0)
    for index, block in enumerate(cfg['blocks']):
        folder = output / 'records' / str(block)
        acquisition = s.read(folder / 'ACQUISITION_REPLAY.json')
        teach = s.arrays(folder / 'teaching.npz')
        counts['acquisition_arrays'] += array_receipt(acquisition['teaching'], teach, ('acquired', 'birth', 'captured', 'end', 'weights'))
        for generation, item in enumerate(acquisition['preliminary'], 1):
            raw = s.arrays(folder / f'g{generation:02d}.npz')
            counts['acquisition_arrays'] += array_receipt(item, raw, ('birth', 'end', 'masks', 'mean_ports', 'outgoing'))
        selected = s.arrays(folder / 'selected.npz')
        original_forecast = s.read(folder / 'FORECASTS.json')
        row, forecasts, diagnostics = record_features.boundary(selected['packet'], selected['mean_ports'], index % 4, index // 4, cfg, original_forecast['row']['record_id'])
        row.update(block=block, index=index, history_index=index % 4)
        s.require(row == original_forecast['row'] and forecasts == original_forecast['predictions'], 'Reconstructed boundary features and frozen forecasts')

    keys = set()
    original_verify = analysis.verify_batch
    def checked_batch(folder, packet, record, futures, rule, config):
        panel, totals = original_verify(folder, packet, record, futures, rule, config)
        receipt = s.read(folder / 'REPLAY.json')
        for position, item in enumerate(receipt['receipts']):
            terminal = position == 18
            generation = 32 if terminal else position + 15
            raw = s.arrays(folder / item['file'])
            s.require(item['arrays'] == len(item['sha256']) == (9 if terminal else 12), 'Full per-step independent replay scope')
            s.require(item['scoring']['status'] == 'PASS' and item['scoring']['contexts'] == 48 and item['scoring']['task_flags'] == 96, 'Full per-step scoring receipt')
            retained_environment(raw, record, list(futures), generation, config, terminal)
            incoming_keys = set(raw['seed_keys'].ravel().tolist())
            s.require(len(incoming_keys) == 80 and not (incoming_keys & keys), 'No random source identity reuse')
            keys.update(incoming_keys)
            counts['reconstructed_environments'] += len(futures)
            if not terminal:
                retained_repair(raw, generation)
                counts['retained_optimizer_constructions'] += int(raw['applied'].sum())
        return panel, totals
    analysis.verify_batch = checked_batch
    for name in ('teaching', 'preliminary', 'checked_read', 'acquire', 'batch'):
        setattr(engine, name, forbid_trajectories)
    regenerated = CHECK / 'recomputed'
    regenerated.mkdir()
    (regenerated / 'records').symlink_to(output / 'records', target_is_directory=True)
    for name in ('COHORT_SEAL.json', 'CONTINUATION_STARTED.json'):
        shutil.copy2(output / name, regenerated / name)
    result = analysis.run(regenerated, cfg, lambda *args, **kwargs: None)
    report.run(regenerated, result)
    derived = ('panels.npz', 'NATIVE_AUDIT.json', 'record_probabilities.csv', 'paired_state_effects.json',
               'sealed_forecasts.csv', 'analysis.json', 'REPORT.md')
    for name in derived:
        if name.endswith('.npz'):
            first, second = s.arrays(output / name), s.arrays(regenerated / name)
            s.require(set(first) == set(second), 'Recomputed array names')
            for key in first:
                s.equal(first[key], second[key], 'Recomputed study panel ' + key)
        else:
            s.require((output / name).read_bytes() == (regenerated / name).read_bytes(), 'Recomputed analysis/report bytes ' + name)
    s.require(counts == dict(acquisition_arrays=4800, reconstructed_environments=77824, retained_optimizer_constructions=77824), 'Complete additional closeout scope')
    s.require(len(keys) == 389120, 'Every separate source key retained')
    p = result['primary']
    s.require(complete['scientific_verdict'] == p['verdict'], 'Primary alone determines verdict')
    panels = s.arrays(output / 'panels.npz')
    endpoints = {'terminal_record':panels['terminal_success'], 'uninterrupted':panels['body_success'].all(axis=-1)}
    paired = {}
    for name, values in endpoints.items():
        treated, control = values[:, :, 2], values[:, :, 0]
        d = treated.mean(axis=1) - control.mean(axis=1)
        paired[name] = dict(treated_only=int((treated & ~control).sum()), control_only=int((control & ~treated).sum()),
            both=int((treated & control).sum()), neither=int((~treated & ~control).sum()),
            positive_records=int((d > 0).sum()), negative_records=int((d < 0).sum()), tied_records=int((d == 0).sum()))
    native = s.read(output / 'NATIVE_AUDIT.json')
    receipt = dict(status='PASS', utc=s.utc(), seconds=time.monotonic()-began,
        closeout_code_sha256=s.sha(Path(__file__)), closeout_prepared_after_completed_result_inspection=True,
        new_trajectories_generated=False, inference_and_scoring_reused_from_frozen_qualified_source=True,
        original_registration_sha256=s.sha(STUDY / 'REGISTRATION.json'), complete_sha256=s.sha(output / 'COMPLETE.json'),
        frozen_runtime_inputs=43, runtime_input_copies_verified=3, extra_context_inputs=6, controller_inputs=4,
        validation_outputs=outputs, native_qualification_outputs=qualification_outputs,
        controller_qualification_outputs=len(controller_qual['outputs_sha256']),
        source_checkpoint_files=516, inherited_checkpoint_files=513, original_status_archive_verified=True,
        complete_native_array_receipts=native['native_arrays']+counts['acquisition_arrays'],
        teaching_replays=64, preliminary_contexts=14336, continuation_contexts=221184, terminal_contexts=12288,
        dual_task_flags=2*(221184+12288), source_keys_verified=len(keys),
        **counts, regenerated_analysis_files=list(derived), paired_outcomes=paired,
        primary=p, scientific_verdict=p['verdict'], actual_wall_seconds=complete['seconds'],
        original_deadline_met=True, same_registered_cohort=True, no_new_cohort_on_migration=True,
        automatic_polling=False, automatic_successor=False)
    s.dump(CHECK / 'COMPLETE.json', receipt)
    s.dump(STUDY / 'CLOSEOUT.json', receipt)
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    CHECK.mkdir(parents=True, exist_ok=False)
    s.require(all(os.environ.get(name) == '1' for name in capacity.THREADS), 'One numerical thread')
    admission = capacity.snapshot()
    s.require(admission['available'] >= 1, 'Shared host CPU admission')
    s.dump(CHECK / 'CPU_ADMISSION.json', dict(status='PASS', utc=s.utc(), **admission))
    s.dump(CHECK / 'STARTED.json', dict(utc=s.utc(), pid=os.getpid(), maximum_seconds=600,
        code_sha256=s.sha(Path(__file__)), original_complete_sha256=s.sha(STUDY/'runs/validation_two_cpu_v1/COMPLETE.json')))
    def timeout(*args):
        raise TimeoutError('Ten-minute closeout ceiling')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        run()
    except BaseException:
        s.dump(CHECK / 'FAILED.json', dict(status='FAILED', utc=s.utc(), traceback=traceback.format_exc(),
            scientific_run_unchanged=True, no_automatic_scientific_retry=True))
        raise
    finally:
        signal.alarm(0)
