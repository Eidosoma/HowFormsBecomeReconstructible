"""Frozen audit launcher. Detached full jobs have no polling or retry loop."""
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
import support as s

PLAN=s.read(s.HERE/'plan.json')
THREADS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
OWN=('support.py','prepare.py','native.py','intake.py','scoring.py','checks.py','engine.py','report.py','run.py',
     'plan.json','PROTOCOL.md','DRAFT_PROTOCOL.md','SOURCE_RECEIPT.json','PLANNING_CONTEXT.json')


def hashes():return {name:s.sha(s.HERE/name) for name in sorted([*OWN,*s.verify_sources()['files_sha256']])}


def preflight(mode,benchmark):
    inputs=hashes();forecast=None;qualification={};storage=PLAN['storage_reserve_bytes']+2*sum((s.HERE/rel).stat().st_size for rel in inputs)
    if mode=='audit':
        run=s.HERE/'runs'/benchmark;complete=s.read(run/'COMPLETE.json');manifest=s.read(run/'manifest.json');bench=s.read(run/'benchmark.json')
        s.require(complete['status']=='COMPLETE' and complete['audit_status']=='PASS' and manifest['mode']=='benchmark','Benchmark complete and qualified')
        s.require(manifest['inputs_sha256']==inputs,'Benchmark input identity')
        for rel,digest in complete['outputs_sha256'].items():s.require(s.sha(run/rel)==digest,'Benchmark output identity')
        forecast=bench['forecast_seconds'];storage=max(storage,bench['storage_required_bytes'])
        s.require(bench['runtime_capacity_pass'] and forecast<PLAN['maximum_forecast_seconds'],'Benchmark runtime ceiling')
        qualification=dict(run=str(run),complete_sha256=s.sha(run/'COMPLETE.json'))
    free=shutil.disk_usage(s.HERE).free;s.require(free>=storage,'Storage reserve')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,storage_required_bytes=storage,free_bytes_at_preflight=free,qualification=qualification,
                workers=1,numerical_threads=1,automatic_polling=False)


def status(output,state,**fields):
    temp=output/f'.status_{os.getpid()}.tmp';s.dump(temp,dict(status=state,utc=s.utc(),pid=os.getpid(),**fields));os.replace(temp,output/'STATUS.json')


def execute(job_path):
    job=s.read(job_path/'job.json');output=Path(job['output']);output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});s.require(all(os.environ.get(k)=='1' for k in THREADS),'One numerical thread')
        s.require(s.HERE==job_path/'inputs/TT009' and hashes()==job['inputs_sha256'],'Unchanged frozen inputs')
        s.dump(output/'manifest.json',dict(study='TT009',mode=job['mode'],started_utc=s.utc(),pid=os.getpid(),job=str(job_path),job_sha256=s.sha(job_path/'job.json'),
            inputs_sha256=job['inputs_sha256'],python=sys.version,executable=sys.executable,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in THREADS},detached=job['detached'],forecast_seconds=job['forecast_seconds'],
            qualification=job['qualification'],classification=PLAN['classification'] if job['mode']=='audit' else 'EXCLUDED_TECHNICAL_QUALIFICATION'))
        s.dump(output/'RUNNING.json',dict(status='RUNNING',started_utc=s.utc(),pid=os.getpid(),note='Historical startup; consult STATUS, COMPLETE or FAILED for current state.'))
        def progress(phase,**fields):
            s.require(time.monotonic()-started<PLAN['maximum_forecast_seconds'],'Actual runtime ceiling')
            s.require(shutil.disk_usage(output).free>PLAN['storage_reserve_bytes'],'Storage floor')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-started,**fields)
        import checks
        import intake
        import engine
        progress('technical_checks');s.dump(output/'technical_checks.json',checks.run())
        progress('source_provenance_and_diagnostics');s.dump(output/'PROVENANCE_AUDIT.json',intake.run())
        if job['mode']=='benchmark':result=engine.benchmark(output,progress)
        else:
            result=engine.audit(output,progress);s.dump(output/'NATIVE_AUDIT.json',result)
            import scoring
            for kind in ['fixed','transfer']:progress('scoring_'+kind);scoring.analyze(kind,output)
            import report
            progress('report');result['scientific_verdict']=report.run(output)['scientific_verdict']
        progress('final_input_verification');s.require(hashes()==job['inputs_sha256'],'Inputs changed during execution')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        done=dict(status='COMPLETE',utc=s.utc(),seconds=time.monotonic()-started,audit_status=result['status'],outputs_sha256=outputs,
            scientific_verdict=result.get('scientific_verdict'),blocks_completed=result.get('blocks_completed',[]),new_scientific_outcomes=False,automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done);status(output,'COMPLETE',seconds=done['seconds'],scientific_verdict=done['scientific_verdict'])
        print(json.dumps(dict(status='COMPLETE',mode=job['mode'],seconds=done['seconds'],output=str(output))),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),traceback=traceback.format_exc()));status(output,'FAILED');raise


def launch(mode,name,benchmark,host_launch):
    s.require(name and name.replace('_','').isalnum(),'Simple unique run name');pre=preflight(mode,benchmark);inputs=pre['inputs_sha256']
    detached=mode=='audit';s.require(not detached or host_launch,'Full audit requires persistent host execution')
    output=(s.HERE/'runs'/name).resolve();job=(s.HERE/'jobs'/name).resolve();s.require(not output.exists(),'Run already exists');job.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        target=job/'inputs/TT009'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,target);s.require(s.sha(target)==digest,'Frozen copy identity')
    s.require(hashes()==inputs,'Inputs changed during freezing')
    command=[sys.executable,'-B',str(job/'inputs/TT009/run.py'),'--execute',str(job)]
    s.dump(job/'job.json',dict(study='TT009',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,detached=detached,
        host_launch_requested=host_launch,status_policy='One startup persistence check, then no automatic polling.',**pre))
    env=os.environ.copy();env.update({k:'1' for k in THREADS});env['PYTHONDONTWRITEBYTECODE']='1'
    if detached:
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT009_EXPOSED_P03_AUDIT_LAUNCH',recorded_utc=s.utc(),study='TT009',
            job=str(job),run=str(output),job_sha256=s.sha(job/'job.json'),new_scientific_outcomes=False,automatic_polling=False))+'\n')
    with (job/'console.log').open('xb') as log:process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=process.pid,utc=s.utc(),detached=detached,launcher_pid=os.getpid()))
    if detached:print(json.dumps(dict(status='SPAWNED',pid=process.pid,forecast_seconds=pre['forecast_seconds'],job=str(job),output=str(output),persistence_check_pending=True,automatic_polling=False)),flush=True)
    else:
        code=process.wait()
        if code:raise subprocess.CalledProcessError(code,command)
        print(json.dumps(s.read(output/'COMPLETE.json')),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['benchmark','audit']);parser.add_argument('--name');parser.add_argument('--benchmark',default='benchmark_v1')
    parser.add_argument('--host-launch',action='store_true');parser.add_argument('--preflight-only',action='store_true');parser.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.preflight_only:print(json.dumps({k:v for k,v in preflight(args.mode,args.benchmark).items() if k!='inputs_sha256'},indent=2))
    else:
        if not args.mode or not args.name:parser.error('--mode and --name required')
        launch(args.mode,args.name,args.benchmark,args.host_launch)


if __name__=='__main__':main()
