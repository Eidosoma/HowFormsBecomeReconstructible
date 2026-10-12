"""Immutable TT007 qualification/audit; detached only when forecast exceeds 600s."""
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

THREADS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
OWN=('support.py','prepare_native.py','geometry.py','models.py','analysis.py','checks.py','engine.py','report.py','run.py',
    'PROTOCOL.md','DRAFT_PROTOCOL.md','SOURCE_REVIEW.md','plan.json','SOURCE_RECEIPT.json','NATIVE_RECEIPT.json','PLANNING_CONTEXT.json')


def hashes():return {name:s.sha(s.HERE/name) for name in sorted([*OWN,*s.verify_sources()])}


def status(output,state,**fields):
    temporary=output/f'.status_{os.getpid()}.tmp';s.dump(temporary,dict(status=state,utc=s.utc(),pid=os.getpid(),**fields));os.replace(temporary,output/'STATUS.json')


def preflight(mode,qualification):
    inputs=hashes();forecast=None;receipt={}
    if mode=='audit':
        run=s.HERE/'runs'/qualification;complete=s.read(run/'COMPLETE.json');manifest=s.read(run/'manifest.json')
        s.require(complete['status']=='COMPLETE' and complete['audit_status']=='PASS' and manifest['mode']=='qualification','Qualification incomplete')
        s.require(manifest['inputs_sha256']==inputs,'Qualification inputs differ')
        for rel,digest in complete['outputs_sha256'].items():s.require(s.sha(run/rel)==digest,'Qualification output changed')
        q=s.read(run/'qualification.json');s.require(q['contexts']==64 and q['logistic_folds']==5,'Qualification scope')
        forecast=s.PLAN['forecast_safety_factor']*(8*q['compute_seconds']+complete['technical_checks_seconds'])+60
        s.require(forecast<=s.PLAN['forecast_ceiling_seconds'],'Runtime forecast exceeds ceiling; revise design')
        receipt=dict(run=str(run),complete_sha256=s.sha(run/'COMPLETE.json'))
    free=shutil.disk_usage(s.HERE).free;s.require(free>=s.PLAN['minimum_free_bytes'],'Insufficient free storage')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,qualification=receipt,free_bytes_at_preflight=free,
        minimum_free_bytes=s.PLAN['minimum_free_bytes'],workers=1,numerical_threads=1,automatic_polling=False)


def execute(job_path):
    job=s.read(job_path/'job.json');output=Path(job['output']);output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_frame):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
        s.require(all(os.environ.get(k)=='1' for k in THREADS),'One numerical thread required')
        s.require(s.HERE==job_path/'inputs/TT007' and hashes()==job['inputs_sha256'],'Worker must use unchanged frozen inputs')
        s.dump(output/'manifest.json',dict(study='TT007',mode=job['mode'],started_utc=s.utc(),pid=os.getpid(),
            job=str(job_path),job_sha256=s.sha(job_path/'job.json'),inputs_sha256=hashes(),python=sys.version,executable=sys.executable,
            numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),threads={k:os.environ[k] for k in THREADS},
            cpu_affinity=sorted(os.sched_getaffinity(0)),detached=job['detached'],forecast_seconds=job['forecast_seconds'],qualification=job['qualification'],
            classification=s.PLAN['classification'],prospective_confirmation=False))
        s.dump(output/'RUNNING.json',dict(status='RUNNING',utc=s.utc(),pid=os.getpid(),note='Historical startup record; STATUS/COMPLETE/FAILED give current state.'))
        status(output,'RUNNING',phase='synthetic_checks');os.environ['TT007_TMP']=str(output)
        import checks
        import engine
        checked=checks.run();s.dump(output/'technical_checks.json',checked)
        if job['mode']=='qualification':
            status(output,'RUNNING',phase='synthetic_benchmark');result=engine.qualification(output)
        else:
            result=engine.audit(output,lambda phase:status(output,'RUNNING',phase=phase))
            status(output,'RUNNING',phase='report')
            import report
            report.run(output)
        s.require(hashes()==job['inputs_sha256'],'Frozen inputs changed during execution')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        complete=dict(status='COMPLETE',utc=s.utc(),seconds=time.monotonic()-started,technical_checks_seconds=checked['seconds'],
            audit_status=result['status'],outputs_sha256=outputs,output_bytes=sum((output/p).stat().st_size for p in outputs),
            native_trajectories_generated=0,prospective_confirmation=False,automatic_polling=False)
        s.dump(output/'COMPLETE.json',complete);status(output,'COMPLETE',seconds=complete['seconds'])
        print(json.dumps(dict(status='COMPLETE',mode=job['mode'],seconds=complete['seconds'],output=str(output))),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),traceback=traceback.format_exc()));status(output,'FAILED');raise


def launch(mode,name,qualification,host_launch=False):
    s.require(bool(name) and name.replace('_','').isalnum(),'Unique simple run name required')
    pre=preflight(mode,qualification);inputs=pre['inputs_sha256'];detached=pre['forecast_seconds'] is not None and pre['forecast_seconds']>s.PLAN['foreground_limit_seconds']
    s.require(not detached or host_launch,'Long audit requires persistent host launch')
    output=(s.HERE/'runs'/name).resolve();job_path=(s.HERE/'jobs'/name).resolve();s.require(not output.exists(),'Output exists')
    job_path.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        target=job_path/'inputs/TT007'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,target);s.require(s.sha(target)==digest,'Snapshot copy changed')
    s.require(hashes()==inputs,'Inputs changed while freezing')
    command=[sys.executable,'-B',str(job_path/'inputs/TT007/run.py'),'--execute',str(job_path)]
    s.dump(job_path/'job.json',dict(study='TT007',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,
        detached=detached,host_launch_requested=host_launch,status_policy='One detached startup check; no automatic polling.',**pre))
    if mode=='audit':
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as ledger:
            ledger.write(json.dumps(dict(event='TT007_INDEPENDENT_P02_AUDIT_LAUNCH',recorded_utc=s.utc(),study='TT007',
                classification=s.PLAN['classification'],job=str(job_path),run=str(output),job_sha256=s.sha(job_path/'job.json'),
                native_trajectories_generated=0,prospective_confirmation=False,automatic_polling=False))+'\n')
    env=os.environ.copy();env.update({k:'1' for k in THREADS});env['PYTHONDONTWRITEBYTECODE']='1'
    with (job_path/'console.log').open('xb') as log:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job_path/'PID.json',dict(pid=process.pid,utc=s.utc(),detached=detached,launcher_pid=os.getpid()))
    if detached:print(json.dumps(dict(status='SPAWNED',pid=process.pid,forecast_seconds=pre['forecast_seconds'],job=str(job_path),output=str(output),persistence_check_pending=True,automatic_polling=False)),flush=True)
    else:
        code=process.wait()
        if code:raise subprocess.CalledProcessError(code,command)
        done=s.read(output/'COMPLETE.json');print(json.dumps(dict(status='COMPLETE',mode=mode,output=str(output),seconds=done['seconds'],forecast_seconds=pre['forecast_seconds'])),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['qualification','audit']);parser.add_argument('--name')
    parser.add_argument('--qualification',default='qualification_v1');parser.add_argument('--host-launch',action='store_true');parser.add_argument('--preflight-only',action='store_true');parser.add_argument('--execute',type=Path)
    args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.preflight_only:print(json.dumps({k:v for k,v in preflight(args.mode,args.qualification).items() if k!='inputs_sha256'},indent=2))
    else:
        if not args.mode or not args.name:parser.error('--mode and --name required')
        launch(args.mode,args.name,args.qualification,args.host_launch)


if __name__=='__main__':main()
