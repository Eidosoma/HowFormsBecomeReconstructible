"""Frozen, resource-qualified benchmark and detached audit; no scientific polling."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import traceback
import numpy as np
import scipy
import capacity
import support as s

OWN=['PROTOCOL.md','DRAFT_PROTOCOL.md','plan.json','PLANNING_CONTEXT.json','SOURCE_IDENTITY_CHECK.json',
     'SOURCE_RECEIPT.json','IMPLEMENTATION_REUSE.json','IMPLEMENTATION_CONTEXT.json',
     'prepare.py','support.py','native.py','core.py','optimizer.py','repair.py','capacity.py',
     'provenance.py','intake.py','dynamics.py','scoring.py','checks.py','engine.py','report.py','run.py']

def hashes():
    receipt=s.verify_sources()
    return {rel:s.sha(s.HERE/rel) for rel in sorted(set(OWN)|set(receipt['files_sha256']))}

def status(output,state,**details):
    p=output/'STATUS.tmp';s.dump(p,dict(status=state,utc=s.utc(),pid=os.getpid(),**details));p.replace(output/'STATUS.json')

def preflight(mode,benchmark):
    cfg=s.config();inputs=hashes();forecast=None;qualification={}
    if mode=='audit':
        base=s.HERE/'runs'/benchmark;done=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json')
        s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and done['mode']=='benchmark','Successful qualification')
        s.require(manifest['inputs_sha256']==inputs,'Identical qualification and audit inputs')
        for rel,digest in done['outputs_sha256'].items():s.require(s.sha(base/rel)==digest,'Qualification output '+rel)
        b=s.read(base/'benchmark.json');forecast=b['forecast_seconds']
        s.require(b['capacity_pass'] and forecast<cfg['maximum_forecast_seconds'],'Full-work forecast ceiling')
        qualification=dict(run=str(base),complete_sha256=s.sha(base/'COMPLETE.json'))
    needed=cfg['storage_reserve_bytes']+cfg['audit_output_reserve_bytes']+2*sum((s.HERE/p).stat().st_size for p in inputs)
    s.require(shutil.disk_usage(s.HERE).free>=needed,'Immutable copies plus output and free-space reserves')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,qualification=qualification,required_free_bytes=needed,
                maximum_seconds=cfg['maximum_forecast_seconds'],workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False)

def execute(job):
    meta=s.read(job/'job.json');output=Path(meta['output']);output.mkdir(parents=True,exist_ok=False);cfg=s.config();launched=time.monotonic()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        s.require(s.HERE==job/'inputs/TT015' and hashes()==meta['inputs_sha256'],'Unchanged frozen execution')
        s.require(all(os.environ.get(k)=='1' for k in capacity.THREADS),'Single numerical thread')
        allowed=os.sched_getaffinity(0);os.sched_setaffinity(0,{7 if 7 in allowed else min(allowed)})
        snapshots=0
        while True:
            cpu=capacity.snapshot();snapshots+=1
            if cpu['available']>=1:break
            s.require(meta['mode']=='audit','No CPU slot for foreground qualification')
            status(output,'WAITING_CAPACITY',other_numerical_slots=cpu['numerical_slots'],queue_seconds=time.monotonic()-launched)
            s.require(time.monotonic()-launched<86400,'CPU admission timeout; no work discarded')
            time.sleep(60)
        start=time.monotonic()
        s.dump(output/'CPU_ADMISSION.json',dict(status='PASS',utc=s.utc(),capacity_checks=snapshots,queue_seconds=start-launched,**cpu))
        s.dump(output/'manifest.json',dict(study='TT015',mode=meta['mode'],started_utc=s.utc(),pid=os.getpid(),job_sha256=s.sha(job/'job.json'),
            inputs_sha256=meta['inputs_sha256'],executable=sys.executable,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
            platform=platform.platform(),cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in capacity.THREADS},
            detached=meta['detached'],forecast_seconds=meta['forecast_seconds'],qualification=meta['qualification'],new_scientific_cohort=False))
        def progress(phase,**details):
            limit=cfg['benchmark_ceiling_seconds'] if meta['mode']=='benchmark' else cfg['maximum_forecast_seconds']
            s.require(time.monotonic()-start<limit,'Declared runtime ceiling')
            s.require(shutil.disk_usage(output).free>=cfg['storage_reserve_bytes'],'Storage floor')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-start,**details)
        import engine
        if meta['mode']=='benchmark':result=engine.benchmark(output,cfg,progress)
        else:
            base=Path(meta['qualification']['run']);done=s.read(base/'COMPLETE.json')
            s.require(s.sha(base/'COMPLETE.json')==meta['qualification']['complete_sha256'],'Qualification identity at execution')
            for name,digest in done['outputs_sha256'].items():s.require(s.sha(base/name)==digest,'Qualification remains immutable')
            result=engine.audit(output,cfg,progress,base)
        progress('final_input_verification');s.require(hashes()==meta['inputs_sha256'],'Inputs unchanged after execution')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        complete=dict(status='COMPLETE',mode=meta['mode'],audit_status='PASS',utc=s.utc(),seconds=time.monotonic()-start,
                      total_seconds=time.monotonic()-launched,outputs_sha256=outputs,
                      full_native_replay_performed=meta['mode']=='audit',new_scientific_cohort=False,
                      scientific_verdict=result.get('scientific_verdict'),automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',complete);status(output,'COMPLETE',seconds=complete['seconds'],scientific_verdict=complete['scientific_verdict'])
        print(json.dumps({k:v for k,v in complete.items() if k!='outputs_sha256'}),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),seconds=time.monotonic()-launched,traceback=traceback.format_exc()))
        status(output,'FAILED');raise

def launch(mode,name,benchmark,host):
    s.require(mode in ('benchmark','audit') and name and name.replace('_','').isalnum(),'Valid mode and unique name')
    s.require(host,'Use persistent host execution and shared CPU accounting')
    pre=preflight(mode,benchmark);detached=mode=='audit' and pre['forecast_seconds']>600
    job=s.HERE/'jobs'/name;output=s.HERE/'runs'/name;s.require(not job.exists() and not output.exists(),'Never overwrite a run')
    job.mkdir(parents=True)
    for rel,digest in pre['inputs_sha256'].items():
        target=job/'inputs/TT015'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write((s.HERE/rel).read_bytes())
        s.require(s.sha(target)==digest,'Frozen copy identity')
    s.require(hashes()==pre['inputs_sha256'],'No input mutation during freeze')
    command=[sys.executable,'-B',str(job/'inputs/TT015/run.py'),'--execute',str(job)]
    s.dump(job/'job.json',dict(study='TT015',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,
        detached=detached,status_policy='One startup check, then status at user request. CPU capacity checks alone allowed while awaiting admission.',**pre))
    env=os.environ.copy();env.update({k:'1' for k in capacity.THREADS});env['PYTHONDONTWRITEBYTECODE']='1'
    with (job/'console.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=child.pid,launcher_pid=os.getpid(),created_utc=s.utc(),detached=detached))
    if not detached:s.require(child.wait()==0,'Worker failed; preserve FAILED.json and frozen inputs')
    else:
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT015_FROZEN_FULL_AUDIT_LAUNCH',
            recorded_utc=s.utc(),job_sha256=s.sha(job/'job.json'),job=str(job),pid=child.pid,new_scientific_cohort=False,automatic_polling=False))+'\n')
    print(json.dumps(dict(status='SPAWNED' if detached else 'COMPLETE',job=str(job),run=str(output),pid=child.pid,detached=detached,
                         forecast_seconds=pre['forecast_seconds'],automatic_polling=False,persistence_check_pending=detached),indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['benchmark','audit']);p.add_argument('--name');p.add_argument('--benchmark',default='benchmark_v1')
    p.add_argument('--host-launch',action='store_true');p.add_argument('--execute',type=Path);a=p.parse_args()
    if a.execute:execute(a.execute.resolve())
    else:launch(a.mode,a.name,a.benchmark,a.host_launch)
