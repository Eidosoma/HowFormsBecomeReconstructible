"""Resource-amended continuation of the same frozen fresh-founder replication."""
import time
BOOT_MONOTONIC=time.monotonic()
BOOT_EPOCH=time.time()
import argparse
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import traceback

from sr_common import ROOT,P,read,write,sha,stamp,binding,verify_snapshot,status,check_disk,tree_bytes
import sr_source
import sr_acquire
import sr_analysis
import sr_verification
import sr_reuse
import sr_scheduler

CHILDREN={}
CAPACITY_GATE=None


def stop_children():
    for proc,log in list(CHILDREN.values()):
        if proc.poll() is None:
            try:proc.terminate()
            except ProcessLookupError:pass
    for proc,log in list(CHILDREN.values()):
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        log.close()
    CHILDREN.clear()


def admission(path):
    ref=ROOT/'native/inherited/reference';sys.path.insert(0,str(ref))
    spec=importlib.util.spec_from_file_location('replication_cpu_preflight',ref/'cpu_preflight.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if CAPACITY_GATE is None:raise RuntimeError('CPU gate has no fixed deadline')
    def waiting(receipt,delay):
        status(path.parent.parent,status='WAITING_FOR_CPU',active_pid=os.getpid(),next_batch=path.stem,
               capacity_wait_seconds=CAPACITY_GATE.wait_seconds,next_wait_seconds=delay,
               other_threads=receipt['other_active_or_recently_busy_threads'])
    CAPACITY_GATE.admit(path,module.collect,waiting)


def wave(run,tasks,deadline,label,index):
    started=time.monotonic()
    if time.time()>=deadline:raise TimeoutError('Stage deadline reached')
    if not 1<=len(tasks)<=P['resource']['workers'] or CHILDREN:raise ValueError('At most4 new workers; no overlapping batches')
    folder=run/'tasks';folder.mkdir(exist_ok=True)
    admission(folder/f'{label}_wave_{index}_ADMISSION.json')
    check_disk(run)
    if tree_bytes(run)>P['resource']['max_saved_bytes']:raise OSError('Saved-data cap')
    for i,source in enumerate(tasks):
        task=dict(source,deadline=deadline,parent_pid=os.getpid(),binding=binding(),run=str(run))
        path=folder/f'{label}_wave_{index}_unit_{i}.json';write(path,task)
        log=path.with_suffix('.log').open('xb')
        proc=subprocess.Popen([sys.executable,str(ROOT/'sr_worker.py'),str(path)],stdin=subprocess.DEVNULL,
                              stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
        CHILDREN[proc.pid]=(proc,log)
    write(folder/f'{label}_wave_{index}_STARTED.json',dict(utc=stamp(),workers=sorted(CHILDREN),units=len(tasks),deadline=deadline))
    status(run,status='WORKERS_RUNNING',phase=label,active_pid=os.getpid(),units=len(tasks),capacity_wait_seconds=CAPACITY_GATE.wait_seconds)
    while CHILDREN:
        pid,waitstatus=os.wait()
        if pid not in CHILDREN:raise RuntimeError('Unexpected child completion')
        proc,log=CHILDREN.pop(pid);proc.returncode=os.waitstatus_to_exitcode(waitstatus);log.close()
        if proc.returncode:raise RuntimeError(f'Worker {pid} failed with code {proc.returncode}; see saved unit log')
    elapsed=time.monotonic()-started
    write(folder/f'{label}_wave_{index}_COMPLETE.json',dict(utc=stamp(),units=len(tasks),wall_seconds=elapsed))
    return elapsed


def policy_seal(run,stage,blocks):
    path=run/(stage+'_SEAL.json')
    if (run/stage).exists():raise ValueError('Future directory exists before policy/cohort seal')
    rows=[]
    for block in blocks:
        one,_=sr_source.load(stage,block,run);rows.extend(one)
    extra={'cohort_sha256':sha(run/'COHORT.json')} if stage=='scientific' else {}
    write(path,dict(utc=stamp(),binding=binding(),stage=stage,blocks=blocks,rows=rows,policies=P['policies'],
                   generations=P['generations'],primary_generations=P['primary_generations'],
                   protocol_sha256=sha(ROOT/'protocol.json'),repeat=0,all_conditions_bound_before_futures=True,**extra))
    return path,sha(path)


def future_tasks(run,stage,units,seal_path,seal_hash):
    return [dict(kind='future',stage=stage,block=b,injury=n,seal_path=str(seal_path),seal_sha256=seal_hash,
                 output=str(run/stage/f'n{n}_b{b}')) for b,n in units]


def acquisition_stats(run,stage,blocks,legacy_block=None):
    values=[];attempts={}
    for block in blocks:
        parent='qualification_acquisition' if stage=='qualification' else 'acquisition'
        rows,receipt=sr_acquire.verify(run/parent/f'b{block}',stage,block,block==legacy_block)
        attempts[block]=rows;values.append(receipt)
    return attempts,dict(status='PASS',units=len(values),native_reads=sum(v['native_reads'] for v in values),
        flat_reads=sum(v['flat_native_reads'] for v in values),teaching_episodes=2*len(values),
        maximum_unit_seconds=max(v['wall_seconds'] for v in values),worker_cpu_seconds=sum(v['cpu_seconds'] for v in values))


def timing_gate(acquisition_seconds,continuation_seconds,elapsed):
    r=P['resource'];a=max(r['historical_acquisition_floor'],acquisition_seconds);f=max(r['historical_continuation_floor'],continuation_seconds)
    groups=sr_scheduler.remaining_groups(sr_reuse.REUSE['imported_acquisition_blocks'])
    acquisition_batches=sum(len(sr_scheduler.batches(g)) for g in groups)
    future_batches=len(sr_scheduler.batches(list(range(P['cohort']['eligible_blocks']))))
    forecast=r['overhead']+r['multiplier']*(acquisition_batches*a+future_batches*f)
    required=elapsed+forecast+r['completion_reserve']+r['capacity_wait_seconds']
    charged=sr_reuse.REUSE['prior_charged_wall_seconds']+r['target_seconds']
    fits=required<=r['target_seconds'] and charged<=r['combined_seconds']
    return dict(status='PASS' if fits else 'FAILED',guarded_acquisition_unit_seconds=a,
        guarded_continuation_unit_seconds=f,remaining_acquisition_worker_batches=acquisition_batches,
        continuation_worker_batches=future_batches,resume_forecast_seconds=forecast,
        startup_and_reuse_seconds=elapsed,completion_reserve_seconds=r['completion_reserve'],
        capacity_wait_reserve_seconds=r['capacity_wait_seconds'],required_resumed_seconds=required,
        resumed_hard_seconds=r['target_seconds'],prior_charged_seconds=sr_reuse.REUSE['prior_charged_wall_seconds'],
        charged_total_hard_seconds=charged,total_study_cap_seconds=r['combined_seconds'])


def run(output):
    global CAPACITY_GATE
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False)
    resource=P['resource'];cohort=P['cohort'];nblocks=cohort['eligible_blocks']
    deadline=BOOT_EPOCH+resource['target_seconds'];CAPACITY_GATE=sr_scheduler.CapacityGate(deadline)
    def expired(*args):raise TimeoutError('Fixed amended deadline or termination; no extension')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
    write(root/'START.json',dict(utc=stamp(),pid=os.getpid(),binding=binding(),deadline_epoch=deadline,
          prior_charged_seconds=sr_reuse.REUSE['prior_charged_wall_seconds'],total_study_cap_seconds=resource['combined_seconds'],
          native_qualification_reused=True,automatic_polling=False))
    status(root,status='REUSE_VALIDATION_RUNNING',active_pid=os.getpid())
    try:
        verified_inputs=verify_snapshot();software=read(ROOT/'SOFTWARE_QUALIFICATION.json')
        if software['status']!='PASS' or software['tests_passed']!=P['software_test_count']:raise ValueError('Software qualification missing')
        for rel,digest in software['implementation_sha256'].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Implementation changed after qualification')
        # Charged grace permits the one-off startup checker to exit.
        time.sleep(4.)
        check_disk(root);reuse=sr_reuse.install(root)
        q=read(root/'QUALIFICATION.json');qacq=q['acquisition'];qfuture=q['continuation']
        elapsed=time.monotonic()-BOOT_MONOTONIC
        timing=timing_gate(qacq['maximum_unit_seconds'],qfuture['maximum_unit_wall_seconds'],elapsed)
        timing.update(binding=binding(),qualification_reuse_sha256=sha(root/'QUALIFICATION_REUSE.json'))
        write(root/'REMAINING_COST_GATE.json',timing)
        if timing['status']!='PASS':raise RuntimeError('Remaining work does not fit the amended charged budget')
        verify_snapshot();target_start=time.monotonic()
        write(root/'ACQUISITION_RELEASE.json',dict(utc=stamp(),binding=binding(),qualification_sha256=sha(root/'QUALIFICATION.json'),
              qualification_reuse_sha256=sha(root/'QUALIFICATION_REUSE.json'),target_deadline_epoch=deadline,
              attempt_cap=cohort['maximum_attempts'],selected_blocks=nblocks,imported_attempts=14))
        attempted=list(sr_reuse.REUSE['imported_acquisition_blocks'])
        attempts,astats=acquisition_stats(root,'scientific',attempted)
        first_group=len(attempted)//cohort['wave_size']
        for group_index,blocks in enumerate(sr_scheduler.remaining_groups(attempted),start=first_group):
            status(root,status='ACQUISITION_RUNNING',active_pid=os.getpid(),completed_attempts=len(attempted),attempt_cap=cohort['maximum_attempts'])
            tasks=[dict(kind='acquire',stage='scientific',block=b,legacy=False,output=str(root/'acquisition'/f'b{b}')) for b in blocks]
            for physical_index,part in enumerate(sr_scheduler.batches(tasks)):
                wave(root,part,deadline,f'acquisition_group_{group_index}',physical_index)
            # The original logical seven-block selection barrier is unchanged.
            attempted.extend(blocks)
            attempts,astats=acquisition_stats(root,'scientific',attempted)
            candidate=sr_source.select_panel(attempts);sr_source.verify_selection(attempts,candidate)
            if candidate['complete']:break
        panel=sr_source.seal_panel(root,attempted)
        seal,seal_hash=policy_seal(root,'scientific',panel['blocks'])
        write(root/'FUTURE_RELEASE.json',dict(utc=stamp(),qualification_sha256=sha(root/'QUALIFICATION.json'),
              qualification_reuse_sha256=sha(root/'QUALIFICATION_REUSE.json'),cohort_sha256=sha(root/'COHORT.json'),
              policy_seal_sha256=seal_hash,target_deadline_epoch=deadline))
        units=[(b,n) for b in panel['blocks'] for n in P['injury_levels']]
        tasks=future_tasks(root,'scientific',units,seal,seal_hash)
        for index,part in enumerate(sr_scheduler.batches(tasks)):
            status(root,status='ALLOCATION_REPLICATION_RUNNING',active_pid=os.getpid(),completed_units=resource['workers']*index,
                   total_units=len(tasks),selected_blocks=nblocks,acquisition_attempts=len(attempted),policy_seal_sha256=seal_hash)
            wave(root,part,deadline,'scientific',index)
        outcomes,verification=sr_verification.verify_stage(root,'scientific',units,seal_hash)
        if set(verification['base_forcing_hashes'])&set(qfuture['base_forcing_hashes']):raise ArithmeticError('Qualification/future streams overlap')
        write(root/'OUTCOMES.json',outcomes);write(root/'VERIFICATION.json',verification)
        analysis=sr_analysis.summarize(outcomes,panel['blocks']);audit=sr_analysis.audit_analysis(outcomes,analysis)
        recovery=sr_analysis.audit_recovery(outcomes,analysis)
        write(root/'ANALYSIS.json',analysis);write(root/'ANALYSIS_AUDIT.json',audit);write(root/'RECOVERY_AUDIT.json',recovery)
        report=sr_analysis.report(analysis,verification,astats)
        report+='\nResource amendment2: four workers; fourteen prior acquisitions and the passed native qualification reused under original hash bindings. Logical acquisition groups of seven, scientific fields, selection and namespace unchanged. Prior659.8173002619296 seconds is charged once. CPU admission waiting is bounded to180 seconds and included in the fixed resumed deadline.\n'
        with (root/'REPORT.txt').open('x') as f:f.write(report)
        verify_snapshot()
        if time.time()>=deadline:raise TimeoutError('Amended closeout deadline exceeded')
        if tree_bytes(root)>resource['max_saved_bytes']:raise OSError('Saved-data cap exceeded')
        entries={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        write(root/'OUTPUTS.json',dict(utc=stamp(),sha256=entries))
        resumed=time.monotonic()-BOOT_MONOTONIC;prior=sr_reuse.REUSE['prior_charged_wall_seconds']
        complete=dict(status='COMPLETE_AUDITED',utc=stamp(),decision=analysis['decision'],
            inputs_sha256=sha(ROOT/'INPUTS.json'),output_manifest_sha256=sha(root/'OUTPUTS.json'),policy_seal_sha256=seal_hash,
            qualification_sha256=sha(root/'QUALIFICATION.json'),qualification_reuse_sha256=sha(root/'QUALIFICATION_REUSE.json'),cohort_sha256=sha(root/'COHORT.json'),
            wall_seconds=prior+resumed,prior_charged_wall_seconds=prior,resumed_wall_seconds=resumed,
            target_wall_seconds=time.monotonic()-target_start,capacity_wait_seconds=CAPACITY_GATE.wait_seconds,
            selected_blocks=nblocks,source_packets=len(panel['rows']),acquisition_attempts=len(attempted),
            imported_acquisition_attempts=14,new_acquisition_attempts=len(attempted)-14,terminal_policy_outcomes=len(outcomes),
            acquisition=astats,target_continuation=verification,qualification_acquisition=qacq,qualification_continuation=qfuture,
            independent_analysis_audit=audit,recovery_audit=recovery,software_tests=P['software_test_count'],input_files_verified=verified_inputs,
            qualification_reused=True,new_estimation_probes=0,new_fits=0,automatic_successor=False,automatic_retry=False)
        write(root/'COMPLETE.json',complete)
        status(root,status='COMPLETE_AUDITED',active_pid=None,decision=analysis['decision'],complete_sha256=sha(root/'COMPLETE.json'))
        write(root/'HANDOFF.json',dict(utc=stamp(),status='COMPLETE_AUDITED',active_pid=None,active_run=None,
              report=str(root/'REPORT.txt'),complete=str(root/'COMPLETE.json'),decision=analysis['decision'],
              next_action='Audit the unchanged primary, all reused/new acquisition bindings, controls, charged costs and separate recovery/uninterrupted endpoints. No automatic successor.',protected_sources=P['protected_sources']))
        print({k:complete[k] for k in ['status','decision','wall_seconds','selected_blocks','terminal_policy_outcomes']},flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0);stop_children()
        failure=dict(utc=stamp(),status='FAILED',traceback=traceback.format_exc(),resumed_wall_seconds=time.monotonic()-BOOT_MONOTONIC,
                     prior_charged_wall_seconds=sr_reuse.REUSE['prior_charged_wall_seconds'],capacity_wait_seconds=CAPACITY_GATE.wait_seconds,
                     acquisition_started=(root/'ACQUISITION_RELEASE.json').exists(),scientific_futures_started=(root/'FUTURE_RELEASE.json').exists(),
                     automatic_retry=False,automatic_resume=False)
        write(root/'FAILED.json',failure);status(root,status='FAILED',active_pid=None,reason=failure['traceback'].splitlines()[-1]);raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);stop_children()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();run(args.output)
