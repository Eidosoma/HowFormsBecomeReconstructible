"""One detached, bounded job: disposable cost gate, then the declared study."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
import traceback
import numpy as np
from rr_common import (ROOT,C,ev,read,require,ledger,inherited,actions,fixtures,
    admission,verify_snapshot,manifest,check_manifest,Guard,numerical_environment)
import rr_analysis
import rr_audit


def stop_workers(processes):
    for p in processes:
        if p.poll() is None: p.terminate()
    stop=time.monotonic()+5.
    for p in processes:
        try: p.wait(timeout=max(.001,stop-time.monotonic()))
        except subprocess.TimeoutExpired: p.kill()
    for p in processes: p.wait()


def seal_panel(folder,stage,rows,forecasts,packets):
    folder.mkdir(parents=True,exist_ok=False)
    initial,receipts,details=actions.prepare(rows,packets)
    if stage=='pilot':
        old=read(ROOT/'context/02_PANEL_SEAL.json')
        old_arrays=ev.load(ROOT/'context/00_ACTIONS.npz',old['action_arrays_sha256'])
        require(old['rows']==rows and old['forecasts']==forecasts,'Original cohort or forecasts changed')
        require(initial.dtype==old_arrays['initial_packets'].dtype and initial.shape==old_arrays['initial_packets'].shape and initial.tobytes()==old_arrays['initial_packets'].tobytes(),'Repair differs from previous pre-future action')
    action_sha=ev.save(folder/'ACTIONS.npz',dict(initial_packets=initial,**details))
    ev.write(folder/'ACTIONS.json',receipts)
    seal=folder/'PANEL_SEAL.json'
    ev.write(seal,dict(utc=ev.utc(),stage=stage,replicates=C['cohort']['new_replicates'],
        input_manifest_sha256=ev.sha(ROOT/'INPUTS.json'),future_namespace=C['future']['namespace'],
        rows=rows,forecasts=forecasts,actions_sha256=action_sha,action_receipts_sha256=ev.sha(folder/'ACTIONS.json'),
        branch_sha256=[[inherited.digest(a) for a in pair] for pair in initial],all_actions_checked_before_any_future=True))
    return seal


def concurrent_replicates(folder,seal,stage,deadline,processes):
    seal_sha=ev.sha(seal)
    logs=[]
    try:
        local=[]
        for rep in C['cohort']['new_replicates']:
            target=folder/f'replicate_{rep}'
            command=[sys.executable,str(ROOT/'rr_worker.py'),'--output',str(target),'--seal',str(seal),
                '--seal-sha',seal_sha,'--replicate',str(rep),'--stage',stage,'--deadline',str(deadline)]
            log=(folder/f'replicate_{rep}.log').open('xb');logs.append(log)
            process=subprocess.Popen(command,cwd=ROOT,env=numerical_environment(folder/'tmp'),
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            processes.append(process);local.append((rep,target,process))
        ev.write(folder/'WORKERS.json',dict(utc=ev.utc(),stage=stage,workers=[dict(replicate=r,pid=p.pid,output=str(d)) for r,d,p in local]))
        with ThreadPoolExecutor(max_workers=len(local)) as pool:
            pending={pool.submit(p.wait):(rep,target,p) for rep,target,p in local}
            try:
                for future in as_completed(pending,timeout=max(.001,deadline-time.time())):
                    rep,target,process=pending[future]
                    require(future.result()==0,f'Replicate {rep} failed; no reduced-sample analysis')
            except BaseException:
                stop_workers([p for _,_,p in local])
                raise
        outcomes=[];receipts=[]
        for rep,target,_ in local:
            complete=read(target/'COMPLETE.json')
            require(complete['status']=='COMPLETE' and complete['replicate']==rep and complete['stage']==stage and complete['seal_sha256']==seal_sha,'Wrong replicate completion')
            entries=read(target/'OUTPUTS.json')['sha256']
            require(set(manifest(target,('OUTPUTS.json',)))==set(entries),'Replicate output coverage')
            check_manifest(target,entries)
            outcomes.extend(read(target/'OUTCOMES.json'));receipts.append(complete)
        require(ev.sha(seal)==seal_sha,'Whole-panel seal changed')
        return outcomes,receipts
    finally:
        for log in logs: log.close()


def price(receipts,remaining):
    require(len(receipts)==4 and all(r['stage']=='benchmark' and r['records']==4 and r['batches']==2 for r in receipts),'Full concurrent benchmark required')
    slowest=max(r['wall_seconds'] for r in receipts)
    forecast=16*slowest*C['resources']['forecast_factor']+C['resources']['fixed_overhead_seconds']
    return dict(utc=ev.utc(),forecast_seconds=forecast,remaining_job_seconds=remaining,
                passed=forecast<remaining,slowest_concurrent_benchmark_worker_seconds=slowest,
                rule='16 blocks times slowest concurrent full worker time times 1.5 plus 120 seconds; must fit remaining one-hour job budget.',
                primary_disposable_reads=sum(r['primary_native_reads'] for r in receipts),
                flat_disposable_reads=sum(r['flat_native_reads'] for r in receipts),new_scientific_outcomes=0)


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();deadline=time.time()+C['resources']['hard_wall_seconds']
    processes=[]
    def expired(*_): raise TimeoutError('One-hour job deadline; no automatic extension')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,C['resources']['hard_wall_seconds'])
    try:
        ev.write(output/'START.json',dict(utc=ev.utc(),pid=os.getpid(),hard_wall_seconds=3600,deadline_epoch=deadline,input_manifest_sha256=ev.sha(ROOT/'INPUTS.json')))
        ev.status(output,status='RUNNING',stage='verification_and_admission')
        verified=verify_snapshot()
        require(read(ROOT/'QUALIFICATION.json')['status']=='PASS','Passing frozen tests required')
        cpu=admission();ev.write(output/'CPU_ADMISSION.json',cpu)
        require(cpu['within_limit'],'Four CPU slots unavailable; no retry')
        guard=Guard(output,deadline);guard.check()
        rows,forecasts,_,packets=fixtures.panel()
        rows,packets=rows[-4:],packets[-4:]
        forecasts=[f for f in forecasts if f['block']==rows[0]['block']]
        seal=seal_panel(output/'benchmark','benchmark',rows,forecasts,packets)
        ev.status(output,status='RUNNING',stage='concurrent_disposable_benchmark',scientific_futures_started=False)
        _,bench=concurrent_replicates(output/'benchmark',seal,'benchmark',min(deadline,time.time()+C['resources']['benchmark_wall_seconds']),processes)
        gate=price(bench,deadline-time.time());ev.write(output/'COST_GATE.json',gate)
        if not gate['passed']:
            result=dict(status='COMPLETE',decision='BUDGET_GATE_NOT_MET',new_scientific_outcomes=0,automatic_retry=False,automatic_successor=False)
            with (output/'REPORT.md').open('x') as f:
                f.write('**Repeatability study not launched.**\n\nThe concurrent disposable benchmark forecast '+f"{gate['forecast_seconds']:.1f}"+' seconds against '+f"{gate['remaining_job_seconds']:.1f}"+' seconds remaining in the one-hour job budget. The fixed cost gate failed. No scientific future was generated and no smaller sample was substituted.\n')
        else:
            guard.check()
            cpu=admission();ev.write(output/'SCIENCE_CPU_ADMISSION.json',cpu)
            require(cpu['within_limit'],'Four CPU slots no longer available; no retry')
            ev.status(output,status='RUNNING',stage='panel_verification_and_action_seal',scientific_futures_started=False,forecast_seconds=gate['forecast_seconds'])
            rows,forecasts,packets=inherited.cached_runner.check_cache()
            require(len(rows)==63 and len({r['block'] for r in rows})==16,'Full original panel required')
            seal=seal_panel(output/'study','pilot',rows,forecasts,packets)
            guard.check()
            require(gate['forecast_seconds']<deadline-time.time(),'Preparation consumed forecast reserve; do not launch')
            ev.status(output,status='RUNNING',stage='four_replicates',scientific_futures_started=True,forecast_seconds=gate['forecast_seconds'],deadline_epoch=deadline)
            outcomes,receipts=concurrent_replicates(output/'study',seal,'pilot',deadline,processes)
            guard.check()
            require(sum(r['primary_native_reads'] for r in receipts)==C['costs']['primary_native_reads'] and sum(r['flat_native_reads'] for r in receipts)==C['costs']['flat_native_reads'],'Read budget changed')
            analysis=rr_analysis.analyze(rows,forecasts,outcomes)
            verification=rr_audit.evaluate(rows,forecasts,outcomes,analysis)
            ev.write(output/'OUTCOMES.json',outcomes);ev.write(output/'ANALYSIS.json',analysis)
            ev.write(output/'VERIFICATION.json',verification);ev.write(output/'RESOURCES.json',dict(**C['costs'],worker_cpu_seconds=sum(r['cpu_seconds'] for r in receipts)))
            with (output/'REPORT.md').open('x') as f: f.write(rr_analysis.report(analysis,C['costs']))
            result=dict(status='COMPLETE',decision=analysis['signal'],new_scientific_outcomes=len(outcomes),primary_native_reads=C['costs']['primary_native_reads'],flat_native_reads=C['costs']['flat_native_reads'],independent_scalar_audit=True,automatic_successor=False)
        verify_snapshot();guard.check()
        ev.write(output/'OUTPUTS.json',dict(sha256=manifest(output)))
        result.update(utc=ev.utc(),wall_seconds=time.monotonic()-start,input_files_verified=verified,input_manifest_sha256=ev.sha(ROOT/'INPUTS.json'),output_manifest_sha256=ev.sha(output/'OUTPUTS.json'))
        ev.write(output/'COMPLETE.json',result);ev.status(output,status='COMPLETE',stage='complete',decision=result['decision'])
        print(result,flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        stop_workers(processes)
        ev.write(output/'FAILED.json',dict(utc=ev.utc(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),automatic_retry=False))
        ev.status(output,status='FAILED',stage='failed');raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        stop_workers(processes)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
