"""Budget-only continuation of the unchanged, fully qualified replication."""
import time
BOOT_MONOTONIC=time.monotonic()
BOOT_EPOCH=time.time()
import argparse
import os
from pathlib import Path
import signal
import traceback
from sr_common import ROOT,P,read,write,sha,stamp,binding,verify_snapshot,status,tree_bytes
import sr_source
import sr_analysis
import sr_verification
from sr_schedule import stop_children,wave,acquisition_stats,policy_seal,future_tasks
from sr_reuse import timing_gate,verify_reuse


def run(output):
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False)
    def expired(*args):raise TimeoutError('Fixed3200-second target cap or termination; no extension')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,BOOT_EPOCH+3200-time.time()))
    write(root/'START.json',dict(utc=stamp(),pid=os.getpid(),binding=binding(),deadline_epoch=BOOT_EPOCH+3200,
                              prior_execution_charged=True,qualification_reused=True,automatic_polling=False))
    status(root,status='VERIFYING_REUSED_QUALIFICATION',active_pid=os.getpid())
    try:
        verified_inputs=verify_snapshot();software=read(ROOT/'SOFTWARE_QUALIFICATION.json')
        if software['status']!='PASS' or software['tests_passed']!=P['software_test_count']:raise ValueError('Software qualification missing')
        for rel,digest in software['implementation_sha256'].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Source changed after software qualification')
        timing,qacq,qfuture,proof=verify_reuse();spent=proof['charged_prior_execution_seconds']
        write(root/'QUALIFICATION_REUSE_AUDIT.json',proof)
        timing.update(binding=binding(),qualification_reused=True,original_qualification_status='FAILED_TIME_GATE_ONLY',
                      acquisition=qacq,continuation=qfuture,reuse_audit_sha256=sha(root/'QUALIFICATION_REUSE_AUDIT.json'),
                      native_reads=qacq['native_reads']+qfuture['native_reads'],flat_reads=qacq['flat_reads']+qfuture['flat_reads'])
        write(root/'QUALIFICATION.json',timing)
        verify_snapshot();target_start=BOOT_MONOTONIC;deadline=BOOT_EPOCH+3200
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
        write(root/'ACQUISITION_RELEASE.json',dict(utc=stamp(),binding=binding(),qualification_sha256=sha(root/'QUALIFICATION.json'),
                                                   target_deadline_epoch=deadline,attempt_cap=24,selected_blocks=16))
        attempted=[]
        for index in range(3):
            blocks=list(range(8*index,8*index+8))
            status(root,status='ACQUISITION_RUNNING',active_pid=os.getpid(),completed_attempts=len(attempted),attempt_cap=24)
            tasks=[dict(kind='acquire',stage='scientific',block=b,legacy=False,output=str(root/'acquisition'/f'b{b}')) for b in blocks]
            wave(root,tasks,deadline,'acquisition',index);attempted.extend(blocks)
            attempts,astats=acquisition_stats(root,'scientific',attempted)
            candidate=sr_source.select_panel(attempts)
            sr_source.verify_selection(attempts,candidate)
            if candidate['complete']:break
        panel=sr_source.seal_panel(root,attempted)
        seal,seal_hash=policy_seal(root,'scientific',panel['blocks'])
        write(root/'FUTURE_RELEASE.json',dict(utc=stamp(),qualification_sha256=sha(root/'QUALIFICATION.json'),
              cohort_sha256=sha(root/'COHORT.json'),policy_seal_sha256=seal_hash,target_deadline_epoch=deadline))
        units=[(b,n) for b in panel['blocks'] for n in P['injury_levels']]
        tasks=future_tasks(root,'scientific',units,seal,seal_hash)
        for index in range(4):
            status(root,status='REPLICATION_RUNNING',active_pid=os.getpid(),completed_units=8*index,total_units=32,
                   selected_blocks=16,acquisition_attempts=len(attempted),policy_seal_sha256=seal_hash)
            wave(root,tasks[8*index:8*index+8],deadline,'scientific',index)
        outcomes,verification=sr_verification.verify_stage(root,'scientific',units,seal_hash)
        if set(verification['base_forcing_hashes'])&set(qfuture['base_forcing_hashes']):raise ArithmeticError('Qualification/future streams overlap')
        write(root/'OUTCOMES.json',outcomes);write(root/'VERIFICATION.json',verification)
        analysis=sr_analysis.summarize(outcomes,panel['blocks']);audit=sr_analysis.audit_analysis(outcomes,analysis)
        write(root/'ANALYSIS.json',analysis);write(root/'ANALYSIS_AUDIT.json',audit)
        with (root/'REPORT.txt').open('x') as f:f.write(sr_analysis.report(analysis,verification,astats))
        verify_snapshot()
        if time.time()>=deadline:raise TimeoutError('Target closeout exceeded frozen cap')
        if tree_bytes(root)>P['resource']['max_saved_bytes']:raise OSError('Saved-data cap exceeded')
        entries={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        write(root/'OUTPUTS.json',dict(utc=stamp(),sha256=entries))
        complete=dict(status='COMPLETE_AUDITED',utc=stamp(),decision=analysis['decision'],all_six_point_directions_positive=analysis['all_six_point_directions_positive'],
            inputs_sha256=sha(ROOT/'INPUTS.json'),output_manifest_sha256=sha(root/'OUTPUTS.json'),policy_seal_sha256=seal_hash,
            qualification_sha256=sha(root/'QUALIFICATION.json'),cohort_sha256=sha(root/'COHORT.json'),
            wall_seconds=time.monotonic()-BOOT_MONOTONIC,target_wall_seconds=time.monotonic()-target_start,
            charged_prior_execution_seconds=spent,charged_total_compute_wall_seconds=spent+time.monotonic()-BOOT_MONOTONIC,qualification_reused=True,
            selected_blocks=16,source_packets=64,acquisition_attempts=len(attempted),terminal_policy_outcomes=len(outcomes),
            acquisition=astats,target_continuation=verification,qualification_acquisition=qacq,qualification_continuation=qfuture,
            independent_analysis_audit=audit,software_tests=P['software_test_count'],input_files_verified=verified_inputs,
            new_estimation_probes=0,new_fits=0,automatic_successor=False,automatic_retry=False)
        write(root/'COMPLETE.json',complete)
        status(root,status='COMPLETE_AUDITED',active_pid=None,decision=analysis['decision'],complete_sha256=sha(root/'COMPLETE.json'))
        write(root/'HANDOFF.json',dict(utc=stamp(),status='COMPLETE_AUDITED',active_pid=None,active_run=None,
              report=str(root/'REPORT.txt'),complete=str(root/'COMPLETE.json'),decision=analysis['decision'],
              next_action='Review the full six-comparison replication and ordinary controls; no automatic successor.',protected_sources=P['protected_sources']))
        print({k:complete[k] for k in ['status','decision','wall_seconds','selected_blocks','terminal_policy_outcomes']},flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0);stop_children()
        failure=dict(utc=stamp(),status='FAILED',traceback=traceback.format_exc(),wall_seconds=time.monotonic()-BOOT_MONOTONIC,
                     acquisition_started=(root/'ACQUISITION_RELEASE.json').exists(),scientific_futures_started=(root/'FUTURE_RELEASE.json').exists(),
                     automatic_retry=False,automatic_resume=False)
        write(root/'FAILED.json',failure);status(root,status='FAILED',active_pid=None,reason=failure['traceback'].splitlines()[-1])
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);stop_children()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();run(args.output)
