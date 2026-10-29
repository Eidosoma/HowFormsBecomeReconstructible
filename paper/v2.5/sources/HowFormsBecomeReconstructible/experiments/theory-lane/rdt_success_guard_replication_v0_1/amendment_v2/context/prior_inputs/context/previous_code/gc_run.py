"""One detached qualification-and-target job, hard capped at one hour."""
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

from gc_common import ROOT,P,read,write,sha,stamp,binding,verify_snapshot,status,check_disk,tree_bytes
import gc_source
import gc_analysis

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
    ref=ROOT/'native/inherited/reference'
    sys.path.insert(0,str(ref))
    spec=importlib.util.spec_from_file_location('guard_cpu_preflight',ref/'cpu_preflight.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    receipt=module.collect()
    receipt['planned_threads']=5
    receipt['within_limit']=receipt['other_active_or_recently_busy_threads']+5<=12
    receipt['purpose']='Admit four one-thread native workers and one parent reserve; not scientific status polling'
    write(path,receipt)
    if not receipt['within_limit']:raise RuntimeError('Shared CPU capacity unavailable; no automatic retry')


def seal(run,stage,blocks):
    rows=[]
    for block in blocks:
        one,packets=gc_source.load(stage,block);rows.extend(one)
    path=run/(stage+'_SEAL.json')
    if (run/stage).exists():raise RuntimeError('Future directory exists before seal')
    write(path,dict(utc=stamp(),binding=binding(),stage=stage,rows=rows,policies=P['policies'],
                   generations=P['generations'],primary_generations=P['primary_generations'],
                   protocol_sha256=sha(ROOT/'protocol.json'),repeat=0,all_conditions_bound_before_futures=True))
    return path,sha(path)


def wave(run,stage,units,deadline,seal_path,seal_hash,index):
    wave_start=time.monotonic()
    if time.time()>=deadline:raise TimeoutError('No remaining stage time')
    tasks=run/'tasks';tasks.mkdir(exist_ok=True)
    admission(tasks/f'{stage}_wave_{index}_ADMISSION.json')
    if tree_bytes(run)>P['resource']['max_saved_bytes']:raise OSError('Saved-data cap')
    check_disk(run)
    for block,injury in units:
        task=dict(stage=stage,block=block,injury=injury,deadline=deadline,parent_pid=os.getpid(),
                  binding=binding(),seal_path=str(seal_path),seal_sha256=seal_hash,
                  output=str(run/stage/f'n{injury}_b{block}'))
        task_path=tasks/f'{stage}_n{injury}_b{block}.json';write(task_path,task)
        log=(tasks/f'{stage}_n{injury}_b{block}.log').open('xb')
        proc=subprocess.Popen([sys.executable,str(ROOT/'gc_worker.py'),str(task_path)],stdin=subprocess.DEVNULL,
                              stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
        CHILDREN[proc.pid]=(proc,log)
    write(tasks/f'{stage}_wave_{index}_STARTED.json',dict(utc=stamp(),workers=sorted(CHILDREN),units=units,deadline=deadline))
    # Blocking wait for any child completion, not a polling loop.
    while CHILDREN:
        pid,waitstatus=os.wait()
        if pid not in CHILDREN:raise RuntimeError('Unexpected child completion')
        proc,log=CHILDREN.pop(pid)
        proc.returncode=os.waitstatus_to_exitcode(waitstatus)
        log.close()
        if proc.returncode:raise RuntimeError(f'Worker {pid} failed with code {proc.returncode}; see committed worker log')
    elapsed=time.monotonic()-wave_start
    write(tasks/f'{stage}_wave_{index}_COMPLETE.json',dict(utc=stamp(),units=units,wall_seconds=elapsed))
    return elapsed


def run(output):
    run=Path(output).resolve();run.mkdir(parents=True,exist_ok=False)
    global_deadline=BOOT_EPOCH+3600
    def expired(*args):raise TimeoutError('Combined hard deadline or termination; no extension')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,BOOT_EPOCH+600-time.time()))
    write(run/'START.json',dict(utc=stamp(),pid=os.getpid(),binding=binding(),deadline_epoch=global_deadline,
                              qualification_deadline_epoch=BOOT_EPOCH+600,automatic_polling=False))
    status(run,status='QUALIFICATION_RUNNING',active_pid=os.getpid(),binding=binding())
    try:
        verified=verify_snapshot()
        software=read(ROOT/'SOFTWARE_QUALIFICATION.json')
        if software['status']!='PASS' or software['tests_passed']!=14:raise RuntimeError('Software qualification missing')
        for rel,digest in software['implementation_sha256'].items():
            if sha(ROOT/rel)!=digest:raise RuntimeError('Implementation changed since software qualification')
        q_path,q_hash=seal(run,'qualification',P['qualification_blocks'])
        q_units=[(b,n) for b in P['qualification_blocks'] for n in P['injury_levels']]
        q_wave=wave(run,'qualification',q_units,BOOT_EPOCH+600,q_path,q_hash,0)
        _,qualified=gc_analysis.verify_stage(run,'qualification',q_units,q_hash)
        if not all(v>0 for v in qualified['policy_branch_coverage'].values()):
            raise RuntimeError('Disposable qualification did not exercise every guarded promotion/retention branch')
        elapsed=time.monotonic()-BOOT_MONOTONIC
        if elapsed>=600:raise TimeoutError('Qualification exceeded its fixed cap')
        measured=max(q_wave,qualified['maximum_unit_wall_seconds'])
        unit_bound=max(4*P['resource']['historical_unit_floor'],measured)
        target_forecast=120+1.5*4*unit_bound
        gate=(target_forecast+120<=3000 and elapsed+3000<=3600)
        timing=dict(status='PASS' if gate else 'FAILED',qualification_elapsed_seconds=elapsed,
                    measured_full_wave_seconds=q_wave,maximum_full_unit_seconds=qualified['maximum_unit_wall_seconds'],
                    retained_four_policy_historical_floor=4*P['resource']['historical_unit_floor'],
                    guarded_unit_seconds=unit_bound,target_forecast_seconds=target_forecast,
                    completion_reserve_seconds=120,target_hard_seconds=3000,combined_hard_seconds=3600,
                    qualification_native_reads=qualified['native_reads'],qualification_flat_reads=qualified['flat_reads'],
                    counts_and_coupling_audit=qualified,implementation_binding=binding())
        write(run/'QUALIFICATION.json',timing)
        if not gate:raise RuntimeError('Measured runtime fails the one-hour fixed design; no scientific outcomes launched')
        verify_snapshot()
        target_start=time.time();target_monotonic=time.monotonic()
        target_deadline=min(global_deadline,target_start+3000)
        signal.setitimer(signal.ITIMER_REAL,max(.001,target_deadline-time.time()))
        p_path,p_hash=seal(run,'development',P['blocks'])
        write(run/'DEVELOPMENT_RELEASE.json',dict(utc=stamp(),qualification_sha256=sha(run/'QUALIFICATION.json'),
              policy_seal_sha256=p_hash,target_deadline_epoch=target_deadline,combined_deadline_epoch=global_deadline))
        status(run,status='DEVELOPMENT_RUNNING',active_pid=os.getpid(),qualification_sha256=sha(run/'QUALIFICATION.json'),
               policy_seal_sha256=p_hash,completed_units=0,total_units=16)
        # Each wave contains both injury levels for two whole founders.
        units=[(b,n) for b in P['blocks'] for n in P['injury_levels']]
        for index in range(4):
            wave(run,'development',units[4*index:4*index+4],target_deadline,p_path,p_hash,index)
            status(run,status='DEVELOPMENT_RUNNING',active_pid=os.getpid(),completed_units=4*(index+1),total_units=16,
                   policy_seal_sha256=p_hash)
        outcomes,verification=gc_analysis.verify_stage(run,'development',units,p_hash)
        if set(verification['base_forcing_hashes'])&set(qualified['base_forcing_hashes']):
            raise ArithmeticError('Scientific streams overlap disposable qualification')
        write(run/'OUTCOMES.json',outcomes);write(run/'VERIFICATION.json',verification)
        analysis=gc_analysis.summarize(outcomes)
        audit=gc_analysis.audit_analysis(outcomes,analysis)
        write(run/'ANALYSIS.json',analysis);write(run/'ANALYSIS_AUDIT.json',audit)
        report=gc_analysis.report(analysis,verification,{})
        with (run/'REPORT.txt').open('x') as f:f.write(report)
        verify_snapshot()
        if time.time()>=target_deadline:raise TimeoutError('Target completion exceeded frozen stage cap')
        if tree_bytes(run)>P['resource']['max_saved_bytes']:raise OSError('Completed output exceeds storage cap')
        files={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        write(run/'OUTPUTS.json',dict(utc=stamp(),sha256=files))
        done=dict(status='COMPLETE_AUDITED',utc=stamp(),decision=analysis['decision'],secondary_boundary_all_four=analysis['secondary_boundary_all_four'],
            inputs_sha256=sha(ROOT/'INPUTS.json'),output_manifest_sha256=sha(run/'OUTPUTS.json'),
            policy_seal_sha256=p_hash,qualification_sha256=sha(run/'QUALIFICATION.json'),
            wall_seconds=time.monotonic()-BOOT_MONOTONIC,target_wall_seconds=time.monotonic()-target_monotonic,
            target_worker_cpu_seconds=verification['worker_cpu_seconds'],qualification_worker_cpu_seconds=qualified['worker_cpu_seconds'],
            primary_native_reads=verification['native_reads'],flat_native_reads=verification['flat_reads'],
            qualification_native_reads=qualified['native_reads'],qualification_flat_reads=qualified['flat_reads'],
            terminal_policy_outcomes=len(outcomes),founder_blocks=8,source_packets=32,software_tests=14,
            input_files_verified=verified,independent_analysis_audit=audit,new_acquisition_reads=0,new_estimation_probes=0,new_fits=0,
            automatic_successor=False,automatic_retry=False)
        write(run/'COMPLETE.json',done)
        status(run,status='COMPLETE_AUDITED',active_pid=None,decision=analysis['decision'],complete_sha256=sha(run/'COMPLETE.json'))
        write(run/'HANDOFF.json',dict(utc=stamp(),status='COMPLETE_AUDITED',active_run=None,active_pid=None,
              report=str(run/'REPORT.txt'),complete=str(run/'COMPLETE.json'),decision=analysis['decision'],
              next_action='Review the complete audited result; no automatic successor.',protected_sources=P['protected_sources']))
        print(done,flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0)
        stop_children()
        failure=dict(utc=stamp(),status='FAILED',traceback=traceback.format_exc(),wall_seconds=time.monotonic()-BOOT_MONOTONIC,
                     scientific_started=(run/'DEVELOPMENT_RELEASE.json').exists(),automatic_retry=False,automatic_resume=False)
        write(run/'FAILED.json',failure)
        status(run,status='FAILED',active_pid=None,reason=failure['traceback'].splitlines()[-1])
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);stop_children()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();run(args.output)
