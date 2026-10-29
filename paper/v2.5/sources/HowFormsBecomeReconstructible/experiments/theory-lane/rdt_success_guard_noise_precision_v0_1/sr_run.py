"""Bounded native qualification, fresh cohort barrier and fixed injury24 precision job."""
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

CHILDREN={}


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
    receipt=module.collect();planned=P['resource']['workers']+P['resource']['parent_reserve'];receipt['planned_threads']=planned
    receipt['within_limit']=receipt['other_active_or_recently_busy_threads']+planned<=P['resource']['shared_limit']
    write(path,receipt)
    if not receipt['within_limit']:raise RuntimeError('Shared CPU capacity unavailable; no automatic retry')


def wave(run,tasks,deadline,label,index):
    started=time.monotonic()
    if time.time()>=deadline:raise TimeoutError('Stage deadline reached')
    if not 1<=len(tasks)<=P['resource']['workers'] or CHILDREN:raise ValueError('At most8 new workers; no overlapping waves')
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
    r=P['resource']
    a=max(r['historical_acquisition_floor'],acquisition_seconds)
    f=max(r['historical_continuation_floor'],continuation_seconds)
    forecast=r['overhead']+r['multiplier']*(r['acquisition_waves_cap']*a+r['continuation_waves']*f)
    fits=(forecast+r['completion_reserve']<=r['target_seconds']
          and elapsed<r['qualification_seconds'] and elapsed+r['target_seconds']<=r['combined_seconds'])
    return dict(status='PASS' if fits else 'FAILED',guarded_acquisition_unit_seconds=a,
        guarded_continuation_unit_seconds=f,target_forecast_seconds=forecast,
        target_completion_reserve_seconds=r['completion_reserve'],target_hard_seconds=r['target_seconds'],
        combined_hard_seconds=r['combined_seconds'],qualification_elapsed_seconds=elapsed,
        charged_acquisition_waves=r['acquisition_waves_cap'],charged_continuation_waves=r['continuation_waves'])


def run(output):
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False)
    resource=P['resource'];cohort=P['cohort'];width=resource['workers'];nblocks=cohort['eligible_blocks']
    def expired(*args):raise TimeoutError('Fixed stage/job deadline or termination; no extension')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,BOOT_EPOCH+resource['qualification_seconds']-time.time()))
    write(root/'START.json',dict(utc=stamp(),pid=os.getpid(),binding=binding(),deadline_epoch=BOOT_EPOCH+resource['combined_seconds'],
                                qualification_deadline_epoch=BOOT_EPOCH+resource['qualification_seconds'],automatic_polling=False))
    status(root,status='QUALIFICATION_RUNNING',active_pid=os.getpid())
    try:
        verified_inputs=verify_snapshot();software=read(ROOT/'SOFTWARE_QUALIFICATION.json')
        if software['status']!='PASS' or software['tests_passed']!=P['software_test_count']:raise ValueError('Software qualification missing')
        for rel,digest in software['implementation_sha256'].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Implementation changed after software qualification')
        qseal,qhash=policy_seal(root,'qualification',P['qualification_blocks'])
        qunits=[(b,n) for b in P['qualification_blocks'] for n in P['injury_levels']]
        aqblocks=[P['legacy_block'],*P['qualification_acquisition_blocks']]
        qtasks=[dict(kind='acquire',stage='qualification',block=b,legacy=b==P['legacy_block'],
                     output=str(root/'qualification_acquisition'/f'b{b}')) for b in aqblocks]
        qtasks+=future_tasks(root,'qualification',qunits,qseal,qhash)
        qwall=wave(root,qtasks,BOOT_EPOCH+resource['qualification_seconds'],'qualification',0)
        _,qacq=acquisition_stats(root,'qualification',aqblocks,P['legacy_block'])
        _,qfuture=sr_verification.verify_stage(root,'qualification',qunits,qhash)
        if not all(v>0 for v in qfuture['policy_branch_coverage'].values()):raise ValueError('Guard branches not all exercised')
        elapsed=time.monotonic()-BOOT_MONOTONIC
        if elapsed>=resource['qualification_seconds']:raise TimeoutError('Qualification exceeded600seconds')
        timing=timing_gate(qacq['maximum_unit_seconds'],qfuture['maximum_unit_wall_seconds'],elapsed)
        timing.update(qualification_wave_seconds=qwall,acquisition=qacq,continuation=qfuture,binding=binding(),
                      native_reads=qacq['native_reads']+qfuture['native_reads'],flat_reads=qacq['flat_reads']+qfuture['flat_reads'])
        write(root/'QUALIFICATION.json',timing)
        if timing['status']!='PASS':raise RuntimeError('Full-cap forecast does not fit the frozen125-minute design')
        verify_snapshot();target_start=time.monotonic();deadline=min(BOOT_EPOCH+resource['combined_seconds'],time.time()+resource['target_seconds'])
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
        write(root/'ACQUISITION_RELEASE.json',dict(utc=stamp(),binding=binding(),qualification_sha256=sha(root/'QUALIFICATION.json'),
                                                   target_deadline_epoch=deadline,attempt_cap=cohort['maximum_attempts'],selected_blocks=nblocks))
        attempted=[]
        for index in range(resource['acquisition_waves_cap']):
            blocks=cohort['attempt_ids'][width*index:width*index+width]
            status(root,status='ACQUISITION_RUNNING',active_pid=os.getpid(),completed_attempts=len(attempted),attempt_cap=cohort['maximum_attempts'])
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
        for index in range(resource['continuation_waves']):
            status(root,status='NOISE_PRECISION_RUNNING',active_pid=os.getpid(),completed_units=width*index,total_units=len(tasks),
                   selected_blocks=nblocks,acquisition_attempts=len(attempted),policy_seal_sha256=seal_hash)
            wave(root,tasks[width*index:width*index+width],deadline,'scientific',index)
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
        complete=dict(status='COMPLETE_AUDITED',utc=stamp(),decision=analysis['decision'],all_three_point_directions_positive=analysis['all_three_point_directions_positive'],
            inputs_sha256=sha(ROOT/'INPUTS.json'),output_manifest_sha256=sha(root/'OUTPUTS.json'),policy_seal_sha256=seal_hash,
            qualification_sha256=sha(root/'QUALIFICATION.json'),cohort_sha256=sha(root/'COHORT.json'),
            wall_seconds=time.monotonic()-BOOT_MONOTONIC,target_wall_seconds=time.monotonic()-target_start,
            selected_blocks=nblocks,source_packets=len(panel['rows']),acquisition_attempts=len(attempted),terminal_policy_outcomes=len(outcomes),
            acquisition=astats,target_continuation=verification,qualification_acquisition=qacq,qualification_continuation=qfuture,
            independent_analysis_audit=audit,software_tests=P['software_test_count'],input_files_verified=verified_inputs,
            new_estimation_probes=0,new_fits=0,automatic_successor=False,automatic_retry=False)
        write(root/'COMPLETE.json',complete)
        status(root,status='COMPLETE_AUDITED',active_pid=None,decision=analysis['decision'],complete_sha256=sha(root/'COMPLETE.json'))
        write(root/'HANDOFF.json',dict(utc=stamp(),status='COMPLETE_AUDITED',active_pid=None,active_run=None,
              report=str(root/'REPORT.txt'),complete=str(root/'COMPLETE.json'),decision=analysis['decision'],
              next_action='Review all three fixed injury24 comparisons and ordinary controls. Prior six-test replication remains unresolved; no automatic successor.',protected_sources=P['protected_sources']))
        print({k:complete[k] for k in ['status','decision','wall_seconds','selected_blocks','terminal_policy_outcomes']},flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0);stop_children()
        failure=dict(utc=stamp(),status='FAILED',traceback=traceback.format_exc(),wall_seconds=time.monotonic()-BOOT_MONOTONIC,
                     acquisition_started=(root/'ACQUISITION_RELEASE.json').exists(),scientific_futures_started=(root/'FUTURE_RELEASE.json').exists(),
                     automatic_retry=False,automatic_resume=False)
        write(root/'FAILED.json',failure)
        status(root,status='FAILED',active_pid=None,reason=failure['traceback'].splitlines()[-1])
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);stop_children()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();run(args.output)
