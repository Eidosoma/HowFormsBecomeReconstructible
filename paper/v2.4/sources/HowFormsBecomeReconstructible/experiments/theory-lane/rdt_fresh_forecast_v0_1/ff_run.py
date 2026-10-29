"""Finite waves, a global forecast barrier, four futures, then complete inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
import traceback

from ff_common import (ROOT,C,P,REGIMES,ev,read,require,ledger,configure,specification,identity,
    binding,verify_snapshot,environment,admission,Guard,completed_outputs,verify_completed)
import ff_selection
import ff_evidence
import ff_analysis
import ff_audit


def stop_workers(processes):
    for p in processes:
        if p.poll() is None:p.terminate()
    deadline=time.monotonic()+3.
    for p in processes:
        try:p.wait(timeout=max(.001,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:p.kill()
    for p in processes:p.wait()


def await_workers(local,deadline):
    """Blocking process waits, not scientific status polling; clean up before pool exit."""
    with ThreadPoolExecutor(max_workers=len(local)) as pool:
        pending={pool.submit(p.wait):(name,p) for name,p in local}
        try:
            for completed in as_completed(pending,timeout=max(.001,deadline-time.time())):
                name,p=pending[completed]
                require(completed.result()==0, 'Worker failed: '+name+'; no retry or partial analysis')
        except BaseException:
            stop_workers([p for _,p in local]);raise


def tasks_in_waves(root,tasks,deadline,processes,guard):
    refs=[]
    for begin in range(0,len(tasks),C['resources']['workers']):
        guard.check();group=tasks[begin:begin+C['resources']['workers']];local=[];logs=[]
        try:
            for task in group:
                name=task['kind']
                if 'block' in task:name+=f"_b{task['block']}"
                if 'replicate' in task:name+=f"_r{task['replicate']}"
                task=dict(**task,run=str(root),binding=binding(),deadline=deadline)
                path=root/'tasks'/f'{name}.json';ledger.atomic_json(path,task)
                stream=(root/'logs'/f'{name}.log').open('xb');logs.append(stream)
                p=subprocess.Popen([sys.executable,str(ROOT/'ff_worker.py'),'--task',str(path)],
                    cwd=ROOT,env=environment(root/'tmp'),stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
                local.append((name,p));processes.append(p)
            ledger.atomic_json(root/'tasks'/f'{local[0][0]}_WAVE.json',dict(utc=ev.utc(),workers=[dict(name=n,pid=p.pid) for n,p in local]))
            await_workers(local,deadline)
            for task in group:
                folder=ledger.child(root,task['output']);ledger.verify(folder)
                refs.append(ledger.reference(root,folder))
            guard.account()
        except BaseException:
            stop_workers([p for _,p in local]);raise
        finally:
            for stream in logs:stream.close()
    return refs


def collect_cohort(root,spec,submit):
    refs=[];attempts={}
    for offset in range(0,spec['maximum_attempts'],spec['wave_size']):
        ids=range(spec['first_block']+offset,spec['first_block']+offset+spec['wave_size'])
        group=[dict(kind='acquire',spec=spec,block=b,output=f'units/acquire/b{b}') for b in ids]
        batch=submit(group);refs.extend(batch)
        # Completion order is deliberately ignored by cohort().
        attempts.update(ff_evidence.attempt_rows(root,batch,spec))
        chosen=ff_selection.cohort(attempts,spec)
        ev.status(root,status='RUNNING',scope=spec['scope'],stage='acquisition',attempts=len(attempts),
            eligible_blocks=len(chosen['eligible_blocks']),target_blocks=spec['eligible_blocks'],scientific_futures_started=False)
        if chosen['complete']:break
    ledger.atomic_json(root/'ACQUISITION_ATTEMPTS.json',dict(references=refs,selection=chosen))
    if not chosen['complete']:return None,refs
    return ff_evidence.seal_selection(root,refs,spec),refs


def forcing_checks(root,measurement_refs,future_refs,rows,spec):
    """Check distinct forcing streams and paired injuries across both regimes."""
    future_noise=set();probe_noise=set();entries=0;paired=0
    for ref in measurement_refs:
        folder=root/ref['path']
        for path in folder.glob('case_*/probe.json'):
            receipt=read(path)
            for f in receipt['forcing']:
                for value in f['purposes'].values():probe_noise.add(value['noise'])
    import numpy as np
    for ref in future_refs:
        folder=root/ref['path'];matched=read(folder/'matched/future.json');independent=read(folder/'independent/future.json')
        require(len(matched['forcing'])==len(independent['forcing']), 'Paired forcing sizes differ')
        for a,b in zip(matched['forcing'],independent['forcing'],strict=True):
            require((a['key'],a['generation'],a['purpose'])==(b['key'],b['generation'],b['purpose']), 'Paired forcing identities differ')
            require(a['sha256']['mask']==b['sha256']['mask'], 'Regimes lost paired injuries')
            for f in (a,b):
                noise=f['sha256']['noise']
                require(noise not in future_noise and noise not in probe_noise, 'Repeated or reused future forcing')
                future_noise.add(noise);entries+=1
        a=ev.load(folder/'matched/future.npz',matched['raw_sha256'])['birth']
        b=ev.load(folder/'independent/future.npz',independent['raw_sha256'])['birth']
        require(np.array_equal(a[:,:,0],b[:,:,0]) and np.array_equal(a[:,:,0],a[:,:,1]), 'Base birth draws or matched cues differ')
        paired+=len(matched['forcing'])
    require(entries==len(rows)*len(REGIMES)*len(spec['repeats'])*19, 'Forcing coverage incomplete')
    return dict(status='PASS',future_forcing_entries=entries,distinct_future_noise_hashes=len(future_noise),
        disjoint_from_probe_noise=True,paired_injury_and_cue0_birth_checks=paired)


def costs(root,refs,spec,rows,attempt_count):
    primary=flat=0;cpu=0.
    for ref in refs:
        folder,value=ledger.referenced(root,ref)
        primary+=value['payload']['native_reads'];flat+=value['payload']['flat_native_reads']
        cpu+=read(folder/'RESOURCES.json')['cpu_seconds']
    acq=attempt_count if spec['scope']=='scientific' else 0
    legacy=int(spec['scope']=='qualification')
    expected_primary=896*(acq+legacy)+len(rows)*(2*72+2*4*19)
    expected_flat=12*(acq+legacy)+len(rows)*2*3+spec['eligible_blocks']*2*4*19
    require((primary,flat)==(expected_primary,expected_flat), 'Total native read budget differs')
    return dict(primary_native_reads=primary,flat_native_reads=flat,worker_cpu_seconds=cpu,
        acquisition_attempts=attempt_count,legacy_replays=legacy,selected_packets=len(rows),
        forecast_native_reads_per_packet_regime=dict(candidate=64,direct_rival=8,tt008=0),
        scientific_outcomes=0 if spec['scope']=='qualification' else len(rows)*2*4)


def pipeline_run(root,spec,submit,guard):
    legacy_refs=[]
    if spec['scope']=='qualification':
        legacy_refs=submit([dict(kind='legacy',spec=spec,output='units/legacy')])
    selection_ref,acquisition_refs=collect_cohort(root,spec,submit)
    if selection_ref is None:
        return dict(decision='EXECUTION_INCOMPLETE_ACQUISITION_CAP',inferential_verdict=None,
                    scientific_future_outcomes=0,automatic_extension=False)
    plan=ff_evidence.selection(root,selection_ref,spec);rows=plan['rows']
    ev.status(root,status='RUNNING',scope=spec['scope'],stage='measurement',blocks=len(plan['blocks']),packets=len(rows),scientific_futures_started=False)
    measurements=submit([dict(kind='measure',spec=spec,block=b,selection=selection_ref,
        output=f'units/measure/b{b}') for b in plan['blocks']])
    guard.check();seal_ref=ff_evidence.seal_forecasts(root,spec,selection_ref,measurements)
    ev.status(root,status='RUNNING',scope=spec['scope'],stage='sealed_futures',forecast_seal_sha256=seal_ref['sha256'],
        scientific_futures_started=spec['scope']=='scientific',future_repeats=spec['repeats'])
    future_refs=submit([dict(kind='future',spec=spec,block=b,replicate=r,seal=seal_ref,
        output=f'units/future/b{b}_r{r}') for b in plan['blocks'] for r in spec['repeats']])
    guard.check();_,seal=ff_evidence.check_seal(root,seal_ref,spec)
    labels=[]
    expected=[(b,r) for b in plan['blocks'] for r in spec['repeats']]
    require(len(future_refs)==len(expected), 'Complete future cohort required before any scoring')
    for ref,(b,r) in zip(future_refs,expected,strict=True):
        labels.extend(ff_evidence.verify_future(root,ref,[x for x in rows if x['block']==b],r,spec,seal_ref))
    # Recheck forecasts after all futures; no scores or selective early stopping above.
    for ref,b in zip(measurements,plan['blocks'],strict=True):
        forecasts=ff_evidence.verify_measurement(root,ref,[x for x in rows if x['block']==b],spec)
        require(forecasts==[f for f in seal['forecasts'] if f['block']==b], 'Sealed predictions changed')
    forcing=forcing_checks(root,measurements,future_refs,rows,spec)
    read_costs=costs(root,legacy_refs+acquisition_refs+measurements+future_refs,spec,rows,len(plan['attempted_blocks']))
    guard.check()
    result=ff_analysis.analyze(rows,seal['forecasts'],labels,spec)
    audit=ff_audit.evaluate(rows,seal['forecasts'],labels,result,spec['repeats'])
    for name,value in [('OUTCOMES',labels),('ANALYSIS',result),('VERIFICATION',audit),
            ('FORCING_AUDIT',forcing),('RESOURCES',read_costs),('FUTURE_REFERENCES',future_refs)]:
        ledger.atomic_json(root/(name+'.json'),value)
    with (root/'REPORT.md').open('x') as f:f.write(ff_analysis.report(result,read_costs))
    return dict(decision='RUNNER_QUALIFICATION_PASS' if spec['scope']=='qualification' else result['decision'],
        inferential_verdict=None if spec['scope']=='qualification' else result['decision'],
        selected_blocks=len(plan['blocks']),selected_packets=len(rows),forecast_seal_sha256=seal_ref['sha256'],
        synthetic_outcomes=len(labels) if spec['scope']=='qualification' else 0,
        scientific_future_outcomes=read_costs['scientific_outcomes'],independent_scalar_audit=True,
        primary_native_reads=read_costs['primary_native_reads'],flat_native_reads=read_costs['flat_native_reads'])


def check_qualification(path):
    result=verify_completed(path)
    require(result['scope']=='qualification' and result['decision']=='RUNNER_QUALIFICATION_PASS' and
            result['input_manifest_sha256']==binding()['input_manifest_sha256'], 'Matching successful frozen runner qualification required')
    require(result['scientific_future_outcomes']==0, 'Qualification touched scientific outcomes')
    return dict(path=str(Path(path).resolve()),complete_sha256=ev.sha(Path(path)/'COMPLETE.json'))


def test_workspace(root):
    """Keep pytest's mutable fixture aliases outside the committed run evidence."""
    root=Path(root).resolve()
    workspace=root.parent/(root.name+'_pytest_workspace')
    workspace.mkdir(exist_ok=False)
    ledger.atomic_json(root/'TEST_WORKSPACE.json',dict(path=str(workspace),
        role='Temporary pytest fixtures; test source, stdout and JUnit report remain bound in the run evidence.',
        outside_committed_evidence=True))
    return workspace


def run(root,scope,qualification=None):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    spec=specification(scope);limit=C['resources']['hard_wall_seconds'] if scope=='scientific' else C['qualification']['hard_wall_seconds']
    start=time.monotonic();deadline=time.time()+limit;processes=[]
    def expired(*_):raise TimeoutError('Fixed job wall limit or termination; no extension, resume or partial inference')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,limit)
    try:
        for name in ('tasks','logs','tmp'): (root/name).mkdir()
        ledger.atomic_json(root/'START.json',dict(utc=ev.utc(),pid=os.getpid(),scope=scope,spec=spec,
            binding=binding(),deadline_epoch=deadline,hard_wall_seconds=limit,automatic_retry=False,automatic_successor=False))
        ev.status(root,status='RUNNING',scope=scope,stage='verification_and_admission')
        verify_snapshot();changes=configure(scope)
        ledger.atomic_json(root/'NAMESPACE_ADAPTER.json',changes)
        if scope=='scientific':
            require(qualification is not None, 'Scientific launch needs a qualified identical runner')
            ledger.atomic_json(root/'QUALIFICATION_BINDING.json',check_qualification(qualification))
        cpu=admission();ledger.atomic_json(root/'CPU_ADMISSION.json',cpu)
        require(cpu['within_limit'], 'Shared12-thread budget unavailable; no automatic retry')
        guard=Guard(root,deadline);guard.check()
        if scope=='qualification':
            workspace=test_workspace(root)
            with (root/'tests.log').open('xb') as stream:
                command=[sys.executable,'-m','pytest',str(ROOT/'test_fresh_runner.py'),'-q','-p','no:cacheprovider',
                    '--basetemp',str(workspace),'--junitxml',str(root/'tests.xml')]
                p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT,env=environment(root/'tmp'))
                processes.append(p);await_workers([('frozen_tests',p)],deadline)
        submit=lambda tasks:tasks_in_waves(root,tasks,deadline,processes,guard)
        result=pipeline_run(root,spec,submit,guard)
        verify_snapshot();guard.account()
        completed_outputs(root,dict(status='COMPLETE',scope=scope,wall_seconds=time.monotonic()-start,
            automatic_successor=False,automatic_retry=False,new_model_fits=0,**result))
        print(read(root/'COMPLETE.json'),flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0);stop_workers(processes)
        ledger.atomic_json(root/'FAILED.json',dict(utc=ev.utc(),scope=scope,error=repr(error),traceback=traceback.format_exc(),
            decision='EXECUTION_INCOMPLETE',inferential_verdict=None,automatic_retry=False,automatic_extension=False))
        ev.status(root,status='FAILED',scope=scope,stage='execution_incomplete');raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);stop_workers(processes)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['qualification','scientific'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--qualification',type=Path)
    args=p.parse_args();run(args.output,args.scope,args.qualification)
