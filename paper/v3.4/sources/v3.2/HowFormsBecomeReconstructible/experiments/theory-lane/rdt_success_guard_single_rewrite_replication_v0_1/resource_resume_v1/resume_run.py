"""Resume only twelve unstarted units with the original frozen science and capped time."""
import time
BOOT_MONOTONIC = time.monotonic()
BOOT_EPOCH = time.time()
import argparse
import os
from pathlib import Path
import signal
import traceback
from resume_common import (ROOT, PLAN, read, write, sha, stamp, need, science,
    verify_controller, verify_prior, import_sources, disk_check, report_budget_note,
    validate_complete_names)


def execute(output):
    run = Path(output).resolve()
    run.mkdir(parents=True, exist_ok=False)
    deadline = BOOT_EPOCH + PLAN['resume_hard_seconds']
    modules = None
    def expired(*args):
        raise TimeoutError('Fixed resumed deadline or termination; no extension')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.time()))
    def status(**values):
        modules['common'].status(run, **values)
    write(run/'START.json', dict(utc=stamp(), pid=os.getpid(), deadline_epoch=deadline,
        controller_input_sha256=sha(ROOT/'INPUTS.json'), scientific_input_sha256=PLAN['source_input_manifest_sha256'],
        original_absolute_deadline_expired=True, prior_wall_seconds=PLAN['prior_wall_seconds'],
        resume_hard_seconds=PLAN['resume_hard_seconds'], automatic_polling=False))
    try:
        controller_files = verify_controller()
        modules = science()
        driver = modules['run']
        driver.CAPACITY = modules['scheduler'].CapacityGate(deadline)
        status(status='VERIFYING_RESOURCE_RESUME', active_pid=os.getpid())
        prior = verify_prior()
        write(run/'PRIOR_VERIFICATION.json', prior)
        write(run/'DISK_ADMISSION.json', disk_check())
        imports = import_sources(run)
        write(run/'IMPORTED.json', imports)
        # Original scientific binding and future release remain byte-identical.
        # Only this resource release supplies the new, already charged deadline.
        write(run/'RESUME_RELEASE.json', dict(utc=stamp(), controller_input_sha256=sha(ROOT/'INPUTS.json'),
            original_binding=modules['common'].binding(), original_future_release_sha256=sha(run/'FUTURE_RELEASE.json'),
            original_cohort_sha256=sha(run/'COHORT.json'), original_policy_seal_sha256=sha(run/'scientific_SEAL.json'),
            imported_sha256=sha(run/'IMPORTED.json'), remaining_blocks=PLAN['remaining_scientific_blocks'],
            new_deadline_epoch=deadline, prior_wall_seconds=PLAN['prior_wall_seconds'],
            original_combined_seconds=3600, original_target_seconds=3400, resume_hard_seconds=PLAN['resume_hard_seconds']))
        seal = run/'scientific_SEAL.json'
        tasks = driver.future_tasks(run, 'scientific', [(b,24) for b in PLAN['remaining_scientific_blocks']], seal, sha(seal))
        need([t['block'] for t in tasks] == list(range(4,16)), 'Unexpected remaining task selection')
        # Charged startup grace permits the one-shot launcher check to finish.
        time.sleep(4.)
        for index in range(3):
            verify_controller()
            write(run/f'DISK_BEFORE_WAVE_{index+1}.json', disk_check(run))
            status(status='REPEATED_REWRITE_REPLICATION_RESUMED', active_pid=os.getpid(),
                   completed_units=4+4*index, total_units=16, imported_units=4)
            driver.wave(run, tasks[4*index:4*index+4], deadline, 'scientific', index+1)
        validate_complete_names(run/'scientific', PLAN['selected_blocks'])
        need(time.time() < deadline, 'Fixed resumed deadline reached before analysis')
        status(status='VERIFYING_COMPLETE_16_BLOCK_PANEL', active_pid=os.getpid())
        units = [(b,24) for b in PLAN['selected_blocks']]
        outcomes, verification = modules['verification'].verify_stage(run, 'scientific', units, sha(seal))
        qseal = run/'qualification_SEAL.json'
        _, qverification = modules['verification'].verify_stage(run, 'qualification', [(-2,24),(-1,24)], sha(qseal))
        need(not set(verification['base_forcing_hashes']) & set(qverification['base_forcing_hashes']),
             'Qualification and scientific streams overlap')
        _, acquisition = driver.acquisition_stats(run, 'scientific', PLAN['selected_blocks'])
        _, qacquisition = driver.acquisition_stats(run, 'qualification', [34000,-2], 34000)
        need(len(outcomes) == 320, 'Incomplete panel cannot be analyzed')
        result = modules['analysis'].summarize(outcomes, PLAN['selected_blocks'])
        audit = modules['analysis'].audit_analysis(outcomes, result)
        recovery = modules['analysis'].audit_recovery(outcomes, result)
        for name, value in [('OUTCOMES',outcomes),('VERIFICATION',verification),('ANALYSIS',result),
                            ('ANALYSIS_AUDIT',audit),('RECOVERY_AUDIT',recovery)]:
            write(run/(name+'.json'), value)
        text = modules['analysis'].report(result, verification, acquisition)
        with (run/'REPORT.txt').open('x') as stream:
            stream.write(report_budget_note(text, time.monotonic()-BOOT_MONOTONIC))
        write(run/'FINAL_SOURCE_VERIFICATION.json', verify_prior())
        verify_controller()
        write(run/'FINAL_DISK.json', disk_check(run))
        entries = {str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*'))
                   if p.is_file() and p.name != 'STATUS.json'}
        write(run/'OUTPUTS.json', dict(utc=stamp(), sha256=entries))
        elapsed = time.monotonic()-BOOT_MONOTONIC
        need(time.time() < deadline and elapsed <= PLAN['resume_hard_seconds'], 'Resume closeout exceeded fixed cap')
        need(PLAN['prior_wall_seconds']+elapsed <= 3600
             and PLAN['prior_target_wall_seconds']+elapsed <= 3400, 'Total charged allowance exceeded')
        complete = dict(status='COMPLETE_AUDITED', utc=stamp(), decision=result['decision'],
            scientific_input_manifest_sha256=PLAN['source_input_manifest_sha256'],
            controller_input_manifest_sha256=sha(ROOT/'INPUTS.json'), output_manifest_sha256=sha(run/'OUTPUTS.json'),
            cohort_sha256=sha(run/'COHORT.json'), policy_seal_sha256=sha(seal),
            qualification_sha256=sha(run/'QUALIFICATION.json'), selected_blocks=16, source_packets=64,
            terminal_policy_outcomes=320, imported_scientific_blocks=list(range(4)), new_scientific_blocks=list(range(4,16)),
            prior_wall_seconds=PLAN['prior_wall_seconds'], resumed_wall_seconds=elapsed,
            wall_seconds=PLAN['prior_wall_seconds']+elapsed, target_charged_seconds=PLAN['prior_target_wall_seconds']+elapsed,
            original_absolute_deadline_expired=True, clock_accounting='Explicit resource amendment; sum of job durations excludes calendar pause and preparation/closeout.',
            prior_full_native_reads=20904, newly_run_full_native_reads=9120, full_native_reads_total=30024,
            acquisition=acquisition, target_continuation=verification, qualification_acquisition=qacquisition,
            qualification_continuation=qverification, native_qualification_reused=True,
            source_software_checks=38, controller_software_checks=read(ROOT/'SOFTWARE_QUALIFICATION.json')['tests_passed'],
            controller_input_files=controller_files, capacity_wait_seconds=driver.CAPACITY.wait_seconds,
            independent_analysis_audit=audit, recovery_audit=recovery, automatic_successor=False, automatic_retry=False)
        write(run/'COMPLETE.json', complete)
        status(status='COMPLETE_AUDITED', active_pid=None, decision=result['decision'], complete_sha256=sha(run/'COMPLETE.json'))
        write(run/'HANDOFF.json', dict(utc=stamp(), status='COMPLETE_AUDITED', active_pid=None,
            report=str(run/'REPORT.txt'), complete=str(run/'COMPLETE.json'), decision=result['decision'],
            next_action='Independent closeout of the full16-block result, all ordinary controls and separate endpoints; no automatic successor.',
            protected_sources=PLAN['protected_sources'], automatic_polling=False))
        print({k:complete[k] for k in ['status','decision','resumed_wall_seconds','wall_seconds']}, flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if modules:
            modules['run'].stop_children()
        elapsed = time.monotonic()-BOOT_MONOTONIC
        failure = dict(utc=stamp(), status='FAILED', traceback=traceback.format_exc(), resumed_wall_seconds=elapsed,
            combined_charged_seconds=PLAN['prior_wall_seconds']+elapsed, automatic_retry=False, automatic_resume=False)
        write(run/'FAILED.json', failure)
        if modules:
            status(status='FAILED', active_pid=None, reason=failure['traceback'].splitlines()[-1])
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if modules:
            modules['run'].stop_children()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    execute(parser.parse_args().output)
