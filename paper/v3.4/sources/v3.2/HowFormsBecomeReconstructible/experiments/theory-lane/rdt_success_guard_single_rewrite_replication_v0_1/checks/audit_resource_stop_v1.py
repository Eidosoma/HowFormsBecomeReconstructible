"""Seal an interrupted run without aggregating its partial scientific results."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CHECKS = BASE / 'checks'
RUN = BASE / 'runs/replication_v1'
INPUTS = BASE / 'jobs/replication_v1/inputs'
sys.path.insert(0, str(INPUTS))
import sr_common as common
import sr_acquire
import sr_source


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def inventory():
    return {str(p.relative_to(RUN)): sha(p)
            for p in sorted(RUN.rglob('*')) if p.is_file()}


def main():
    started = time.monotonic()
    host = read(CHECKS / 'RESOURCE_STOP_HOST_PROCESS_CHECK.json')
    assert host['status'] == 'NO_REPLICATION_PROCESSES' and not host['matches']
    frozen_hash = '13c38438056b96bb18d4b57edc1296bbbd82ddf626942853bcb983d5f4f6c60c'
    assert sha(INPUTS / 'INPUTS.json') == frozen_hash
    assert common.verify_snapshot() == 76
    before = inventory()
    failure = read(RUN / 'FAILED.json')
    assert failure['traceback'].splitlines()[-1] == 'OSError: Required free disk reserve unavailable'
    assert read(RUN / 'STATUS.json')['status'] == 'FAILED'
    assert failure['scientific_futures_started'] and not failure['automatic_resume']
    assert not any((RUN / n).exists() for n in ['COMPLETE.json', 'ANALYSIS.json', 'OUTCOMES.json'])
    qualification = read(RUN / 'QUALIFICATION.json')
    assert qualification['status'] == 'PASS' and qualification['binding'] == common.binding()
    cohort = read(RUN / 'COHORT.json')
    assert cohort['complete'] and cohort['blocks'] == list(range(16))
    assert cohort['attempted_blocks'] == list(range(16)) and len(cohort['rows']) == 64
    attempts, acquisitions = {}, []
    for stage, blocks, parent in [('scientific', range(16), 'acquisition'),
                                  ('qualification', [34000, -2], 'qualification_acquisition')]:
        for block in blocks:
            folder = RUN / parent / f'b{block}'
            rows, payload = sr_acquire.verify(folder, stage, block, block == 34000)
            if stage == 'scientific':
                attempts[block] = rows
                reference = next(r for r in cohort['acquisitions'] if r['block'] == block)
                assert reference['commit_sha256'] == sha(folder / 'COMMIT.json')
            acquisitions.append(dict(stage=stage, block=block, commit_sha256=sha(folder/'COMMIT.json'),
                native_reads=payload['native_reads'], flat_reads=payload['flat_native_reads']))
    selection = sr_source.verify_selection(attempts, cohort)
    seal = read(RUN / 'scientific_SEAL.json')
    release = read(RUN / 'FUTURE_RELEASE.json')
    assert seal['rows'] == cohort['rows'] and seal['blocks'] == cohort['blocks']
    assert seal['policies'] == common.P['policies'] and seal['binding'] == common.binding()
    assert seal['cohort_sha256'] == release['cohort_sha256'] == sha(RUN / 'COHORT.json')
    assert release['policy_seal_sha256'] == sha(RUN / 'scientific_SEAL.json')
    assert release['qualification_sha256'] == sha(RUN / 'QUALIFICATION.json')
    assert cohort['utc'] <= seal['utc'] <= release['utc']
    units = []
    for stage, blocks in [('qualification', [-2, -1]), ('scientific', list(range(4)))]:
        folders = list((RUN / stage).iterdir())
        assert {p.name for p in folders} == {f'n24_b{b}' for b in blocks}
        seal_hash = sha(RUN / f'{stage}_SEAL.json')
        for block in blocks:
            folder = RUN / stage / f'n24_b{block}'
            commit = read(folder / 'COMPLETE.json')
            assert commit['status'] == 'COMPLETE_AUDITED'
            assert (commit['stage'], commit['block'], commit['injury']) == (stage, block, 24)
            assert commit['binding'] == common.binding() and commit['policy_seal_sha256'] == seal_hash
            assert commit['native_reads'] == commit['flat_native_reads'] == 380
            assert commit['outcomes'] == 20
            for relative, expected in commit['sha256'].items():
                assert sha(folder / relative) == expected
            audit = read(folder / 'independent_AUDIT.json')
            assert audit['status'] == 'PASS' and audit['native_readouts_independently_scored'] == 380
            assert audit['flat_reads'] == 380 and audit['full_horizon_flat_policy_chains'] == 20
            if stage == 'scientific':
                assert release['utc'] <= read(folder / 'START.json')['utc'] < commit['utc'] < failure['utc']
            units.append(dict(stage=stage, block=block, complete_sha256=sha(folder/'COMPLETE.json'),
                native_reads=380, flat_reads=380, outcomes=20, wall_seconds=commit['wall_seconds']))
    tasks = RUN / 'tasks'
    completed_waves = sorted(p.name for p in tasks.glob('*_COMPLETE.json'))
    assert len(completed_waves) == 6
    assert (tasks / 'scientific_wave_0_COMPLETE.json').is_file()
    assert (tasks / 'scientific_wave_1_ADMISSION.json').is_file()
    assert not list(tasks.glob('scientific_wave_1_unit_*'))
    assert not (tasks / 'scientific_wave_1_STARTED.json').exists()
    assert read(tasks / 'scientific_wave_1_ADMISSION.json')['within_limit']
    assert inventory() == before
    manifest = CHECKS / 'STOPPED_RUN_MANIFEST.json'
    write(manifest, dict(utc=stamp(), run=str(RUN), sha256=before))
    q_reads = qualification['native_reads'] + qualification['flat_reads']
    acq_reads = sum(r['native_reads'] + r['flat_reads'] for r in acquisitions if r['stage'] == 'scientific')
    future_reads = sum(r['native_reads'] + r['flat_reads'] for r in units if r['stage'] == 'scientific')
    assert (q_reads, acq_reads, future_reads) == (3336, 14528, 3040)
    free = shutil.disk_usage(BASE).free
    report = BASE / 'RESOURCE_STOP_REPORT.txt'
    report_text = (
        'The fresh-founder repeated-rewrite replication stopped for disk reserve on 2026-10-29 at 14:01:42 UTC.\n'
        'Native qualification passed. All 16 eligible acquisition blocks (64 selected packets) were sealed before any scientific continuation.\n'
        'Continuation blocks 0 through 3 completed; blocks 4 through 15 were not started. There is no full-cohort scientific verdict.\n'
        'The stop occurred before wave 1 workers were launched: CPU admission passed, then free disk space was below the frozen 4,000,000,000-byte reserve. The exact free bytes at the stop were not logged.\n'
        f'Charged run wall time: {failure["wall_seconds"]:.6f} seconds (18m50s). Unused portion of the original 3600-second compute allowance: {3600-failure["wall_seconds"]:.6f} seconds. Its original absolute wall-clock deadline has expired.\n'
        f'Current free disk at closeout: {free} bytes. The completed acquisition and continuation files occupy {sum((RUN/r).stat().st_size for r in before)} bytes.\n'
        'Checkpoint audit: all 76 frozen inputs and every saved acquisition/continuation commitment verified; source cohort selection independently reconstructed; cohort-before-future order verified; no live replication processes.\n'
        'Native costs already incurred: 3336 qualification + 14528 scientific acquisition + 3040 scientific continuation = 20904 full readers. Software qualification separately used 56 full readers and 760 short 32-step readers.\n'
        'Partial outcome files were hashed for integrity, without calculating an effect, confidence interval or hypothesis verdict. Per-unit audit metadata, including block 0 action counts, was inspected; this was not a fully blinded status review. Saved native/flat audit receipts passed; no new dynamics were run and no independent partial endpoint reanalysis was performed during this closeout.\n'
        'Next step: prepare a documented resource-only resume, retaining all 16 original blocks, all 4 completed continuations, original seeds, five policies, endpoint and rejection rule. Complete the remaining 12 continuation blocks, charge prior run time against the one-hour compute allowance, and verify storage and CPU availability. Preserve this failed run and its expired deadline; do not overwrite it or silently restart the clock.\n'
        'No automatic resume, retry, sample change, successor or RDT-specific conclusion.\n'
    )
    with report.open('x') as stream:
        stream.write(report_text)
    closeout = dict(utc=stamp(), status='STOPPED_DISK_RESERVE_CHECKPOINTS_VERIFIED',
        scientific_decision='INCOMPLETE_NO_FULL_COHORT_VERDICT', active_pid=None, active_run=None,
        stopped_run=str(RUN), failed_sha256=sha(RUN/'FAILED.json'), frozen_input_sha256=frozen_hash,
        input_files_verified=76, stopped_run_manifest_sha256=sha(manifest), stopped_run_files=len(before),
        qualification_status='PASS', qualification_sha256=sha(RUN/'QUALIFICATION.json'),
        cohort_sha256=sha(RUN/'COHORT.json'), policy_seal_sha256=sha(RUN/'scientific_SEAL.json'),
        selection_audit=selection, acquisition_commitments=acquisitions, completed_continuations=units,
        completed_scientific_blocks=list(range(4)), remaining_scientific_blocks=list(range(4,16)),
        saved_scientific_policy_outcomes=80, target_policy_outcomes=320,
        wall_seconds=failure['wall_seconds'], original_combined_seconds=3600,
        unused_compute_allowance_seconds=3600-failure['wall_seconds'], original_deadline_expired=True,
        free_bytes_at_closeout=free, free_reserve_bytes=4000000000, free_bytes_at_failure=None,
        full_native_readers_total=20904, software_full_readers_separate=56, software_short32_readers_separate=760,
        run_bytes=sum((RUN/r).stat().st_size for r in before), partial_effects_evaluated=False,
        exposure='Hashes, acquisition boundary/cohort data, resource and unit audit metadata; block0 action counts visible. No scientific success aggregates or primary contrasts computed or displayed.',
        saved_unit_audit_receipts_verified=True, independent_partial_endpoint_reanalysis=False,
        host_process_check_sha256=sha(CHECKS/'RESOURCE_STOP_HOST_PROCESS_CHECK.json'),
        report=str(report), report_sha256=sha(report), audit_script_sha256=sha(Path(__file__)),
        new_native_dynamics_for_closeout=0, closeout_wall_seconds=time.monotonic()-started,
        automatic_retry=False, automatic_resume=False, automatic_successor=False,
        protected_sources=['TT018','rdt_packet_continuation_v0_1'])
    destination = CHECKS / 'RESOURCE_STOP_CLOSEOUT.json'
    write(destination, closeout)
    handoff = CHECKS / 'HANDOFF.json'
    with (CHECKS / 'HANDOFF_BEFORE_RESOURCE_STOP.json').open('xb') as stream:
        stream.write(handoff.read_bytes())
    new = dict(utc=stamp(), status=closeout['status'], active_pid=None, active_run=None,
        stopped_run=str(RUN), scientific_decision=closeout['scientific_decision'], closeout=str(destination),
        closeout_sha256=sha(destination), report=str(report),
        next_action='Document a resource-only resume of the remaining12 original continuation blocks, preserving seeds, completed units, the full16-block test and prior charged time. Do not resume automatically.',
        automatic_polling=False, automatic_resume=False, protected_sources=closeout['protected_sources'])
    temporary = CHECKS / 'HANDOFF_AFTER_RESOURCE_STOP.tmp'
    write(temporary, new)
    os.replace(temporary, handoff)
    assert inventory() == before and common.verify_snapshot() == 76
    print(json.dumps({k:closeout[k] for k in ['status','scientific_decision','stopped_run_files',
        'completed_scientific_blocks','remaining_scientific_blocks','full_native_readers_total',
        'free_bytes_at_closeout','closeout_wall_seconds']}))


if __name__ == '__main__':
    main()
