"""Frozen benchmark and detached prospective validation; no scientific polling."""
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

OWN=['PROTOCOL.md','plan.json','RESERVATION.json','PLANNING_CONTEXT.json','SOURCE_RECEIPT.json','IMPLEMENTATION_REUSE.json',
    'REGISTRATION.json','POWER_SENSITIVITY.json','prepare.py','register.py','support.py','cohort.py','statistics_block.py','analysis.py','report.py',
    'engine.py','checks.py','capacity.py','run.py']

def hashes(exclude_registration=False):
    files=set(OWN)|set(s.verify_sources()['files_sha256'])
    if exclude_registration:files.discard('REGISTRATION.json')
    return {name:s.sha(s.HERE/name) for name in sorted(files)}


def preflight(mode,benchmark):
    cfg=s.config();inputs=hashes();reg=s.read(s.HERE/'REGISTRATION.json')
    s.require(reg['design_inputs_sha256']==hashes(True) and reg['plan_sha256']==s.sha(s.HERE/'plan.json'),'Frozen registration matches all code and source')
    forecast=None;qualification={};retained=0
    if mode=='validation':
        base=s.HERE/'runs'/benchmark;done=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json')
        s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and done['mode']=='benchmark','Successful benchmark')
        s.require(manifest['inputs_sha256']==inputs,'Benchmark and validation use identical frozen inputs')
        for name,digest in done['outputs_sha256'].items():s.require(s.sha(base/name)==digest,'Unchanged qualification '+name)
        b=s.read(base/'benchmark.json');s.require(b['capacity_pass'],'Benchmark capacity gate')
        forecast=b['forecast_seconds'];retained=b['retained_evidence_forecast_bytes']
        qualification=dict(run=str(base),complete_sha256=s.sha(base/'COMPLETE.json'))
    required=cfg['storage_reserve_bytes']+retained+2*sum((s.HERE/name).stat().st_size for name in inputs)
    s.require(shutil.disk_usage(s.HERE).free>=required,'Retained evidence plus storage reserve')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,required_free_bytes=required,retained_evidence_forecast_bytes=retained,
        qualification=qualification,maximum_seconds=cfg['maximum_forecast_seconds'],workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False)


def status(output,state,**detail):
    p=output/'STATUS.tmp';s.dump(p,dict(status=state,utc=s.utc(),pid=os.getpid(),**detail));p.replace(output/'STATUS.json')


def execute(job):
    meta=s.read(job/'job.json');output=Path(meta['output']);output.mkdir(parents=True,exist_ok=False);launched=time.monotonic();cfg=s.config()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupt(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    try:
        s.require(s.HERE==job/'inputs/TT014' and hashes()==meta['inputs_sha256'],'Unchanged frozen execution')
        s.require(all(os.environ.get(k)=='1' for k in capacity.THREADS),'One numerical thread')
        allowed=os.sched_getaffinity(0);os.sched_setaffinity(0,{7 if 7 in allowed else min(allowed)})
        snapshots=0
        while True:
            cpu=capacity.snapshot();snapshots+=1
            if cpu['available']>=1:break
            s.require(meta['mode']=='validation','No CPU slot for foreground benchmark')
            status(output,'WAITING_CAPACITY',other_numerical_slots=cpu['numerical_slots'],queue_seconds=time.monotonic()-launched)
            s.require(time.monotonic()-launched<86400,'Capacity admission timeout; no test outcomes generated')
            time.sleep(60)
        s.dump(output/'CPU_ADMISSION.json',dict(status='PASS',utc=s.utc(),capacity_checks=snapshots,queue_seconds=time.monotonic()-launched,**cpu))
        start=time.monotonic()
        s.dump(output/'manifest.json',dict(study='TT014',mode=meta['mode'],started_utc=s.utc(),pid=os.getpid(),job_sha256=s.sha(job/'job.json'),
            registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),inputs_sha256=meta['inputs_sha256'],executable=sys.executable,
            python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in capacity.THREADS},forecast_seconds=meta['forecast_seconds'],
            detached=meta['detached'],qualification=meta['qualification'],new_scientific_cohort=meta['mode']=='validation'))
        def progress(phase,**detail):
            s.require(time.monotonic()-start<cfg['maximum_forecast_seconds'],'Runtime ceiling')
            s.require(shutil.disk_usage(output).free>=cfg['storage_reserve_bytes'],'Storage floor')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-start,**detail)
        import engine
        if meta['mode']=='benchmark':
            import checks
            progress('technical_qualification');checks.run(output);result=engine.benchmark(output,cfg,progress)
        else:
            base=Path(meta['qualification']['run']);done=s.read(base/'COMPLETE.json')
            s.require(s.sha(base/'COMPLETE.json')==meta['qualification']['complete_sha256'],'Successful benchmark identity before test generation')
            technical=base/'TECHNICAL_CHECKS.json';s.require(s.sha(technical)==done['outputs_sha256']['TECHNICAL_CHECKS.json'],'Reused qualification')
            with (output/'TECHNICAL_CHECKS.json').open('xb') as f:f.write(technical.read_bytes())
            s.dump(output/'TEST_START.json',dict(utc=s.utc(),registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),benchmark_complete_sha256=s.sha(base/'COMPLETE.json'),
                planned_blocks=cfg['blocks'],cohort_records=1024,generated_before_registration=False))
            result=engine.validate(output,cfg,progress)
        progress('final_input_verification');s.require(hashes()==meta['inputs_sha256'],'Frozen inputs unchanged after work')
        committed={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        done=dict(status='COMPLETE',audit_status='PASS',mode=meta['mode'],utc=s.utc(),seconds=time.monotonic()-start,total_seconds=time.monotonic()-launched,
            outputs_sha256=committed,new_scientific_cohort=meta['mode']=='validation',scientific_verdict=result.get('scientific_verdict'),
            automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done);status(output,'COMPLETE',seconds=done['seconds'],scientific_verdict=done['scientific_verdict'])
        print(json.dumps({k:v for k,v in done.items() if k!='outputs_sha256'}),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=s.utc(),total_seconds=time.monotonic()-launched,traceback=traceback.format_exc())
        s.dump(output/'FAILED.json',failure);status(output,'FAILED');raise


def launch(mode,name,benchmark,host_launch):
    s.require(name and name.replace('_','').isalnum(),'Unique simple run name');pre=preflight(mode,benchmark)
    s.require(host_launch,'Use host execution for shared CPU accounting and persistence')
    detached=mode=='validation' and pre['forecast_seconds']>600
    job=s.HERE/'jobs'/name;output=s.HERE/'runs'/name;s.require(not job.exists() and not output.exists(),'Never overwrite a run')
    job.mkdir(parents=True)
    for rel,digest in pre['inputs_sha256'].items():
        target=job/'inputs/TT014'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write((s.HERE/rel).read_bytes())
        s.require(s.sha(target)==digest,'Frozen copy identity')
    s.require(hashes()==pre['inputs_sha256'],'No input mutation during freeze')
    command=[sys.executable,'-B',str(job/'inputs/TT014/run.py'),'--execute',str(job)]
    meta=dict(study='TT014',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,detached=detached,
        status_policy='One startup check then status only at user request; admission observes CPU capacity only.',**pre)
    s.dump(job/'job.json',meta);env=os.environ.copy();env.update({k:'1' for k in capacity.THREADS});env['PYTHONDONTWRITEBYTECODE']='1'
    env['TT008_LANE']=str(s.HERE.parent)
    with (job/'console.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=child.pid,launcher_pid=os.getpid(),created_utc=s.utc(),detached=detached))
    if not detached:s.require(child.wait()==0,'Worker failed; retain frozen attempt and FAILED.json')
    else:
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT014_FROZEN_PROSPECTIVE_VALIDATION_LAUNCH',recorded_utc=s.utc(),
            job_sha256=s.sha(job/'job.json'),job=str(job),pid=child.pid,registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),automatic_polling=False))+'\n')
    print(json.dumps(dict(status='SPAWNED' if detached else 'COMPLETE',job=str(job),run=str(output),pid=child.pid,detached=detached,
        forecast_seconds=pre['forecast_seconds'],automatic_polling=False,persistence_check_pending=detached),indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['benchmark','validation']);p.add_argument('--name');p.add_argument('--benchmark',default='benchmark_v1')
    p.add_argument('--host-launch',action='store_true');p.add_argument('--execute',type=Path);a=p.parse_args()
    if a.execute:execute(a.execute.resolve())
    else:launch(a.mode,a.name,a.benchmark,a.host_launch)
