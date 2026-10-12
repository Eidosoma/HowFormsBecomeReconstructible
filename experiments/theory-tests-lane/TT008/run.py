"""Frozen qualification and persistent phased study, with no polling loop."""
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
OWN=('support.py','prepare.py','forecast.py','calibrate.py','check_forecasts.py','auditor.py','native.py','measure.py','check_native.py','check_known.py','engine.py','score.py','check_scoring.py','check_scoring_flow.py','report.py','run.py','finalize.py',
    'selection.json','plan.json','PROTOCOL.md','SOURCE_RECEIPT.json','QUALIFICATION_SOURCE.json','HOLDOUT_RESERVATION.json','FROZEN_MODELS.json','REGISTRATION.json','DEVELOPMENT_BENCHMARK.json')


def sources():
    result=s.verify_sources()
    for rel,digest in s.read(s.HERE/'QUALIFICATION_SOURCE.json')['files_sha256'].items():s.require(s.sha(s.HERE/rel)==digest,'Known trajectory source changed');result[rel]=digest
    complete=s.read(s.HERE/'runs/calibration_v1/COMPLETE.json')
    result['runs/calibration_v1/COMPLETE.json']=s.sha(s.HERE/'runs/calibration_v1/COMPLETE.json')
    for rel,digest in complete['outputs_sha256'].items():
        name='runs/calibration_v1/'+rel;s.require(s.sha(s.HERE/name)==digest,'Calibration changed');result[name]=digest
    return result


def hashes():return {name:s.sha(s.HERE/name) for name in sorted([*OWN,*sources()])}


def registered():
    r=s.read(s.HERE/'REGISTRATION.json')
    bindings={'models_sha256':'FROZEN_MODELS.json','plan_sha256':'plan.json','selection_sha256':'selection.json','source_receipt_sha256':'SOURCE_RECEIPT.json',
        'qualification_source_sha256':'QUALIFICATION_SOURCE.json','holdout_reservation_sha256':'HOLDOUT_RESERVATION.json','protocol_sha256':'PROTOCOL.md',
        'calibration_complete_sha256':'runs/calibration_v1/COMPLETE.json','calibration_selection_sha256':'runs/calibration_v1/selection_result.json'}
    for field,name in bindings.items():s.require(s.sha(s.HERE/name)==r[field],'Registration binding '+field)
    s.require(r['blocks']==list(range(8800000,8800064)) and r['planned_records']==4096,'Registration cohort')
    return r


def preflight(mode,benchmark):
    registered();inputs=hashes();forecast=None;qualification={};storage=PLAN['storage_reserve_bytes']
    if mode=='scientific':
        run=s.HERE/'runs'/benchmark;complete=s.read(run/'COMPLETE.json');manifest=s.read(run/'manifest.json');bench=s.read(run/'benchmark.json')
        s.require(complete['status']=='COMPLETE' and complete['audit_status']=='PASS' and manifest['mode']=='benchmark','Benchmark incomplete')
        s.require(manifest['inputs_sha256']==inputs,'Benchmark inputs differ')
        for rel,digest in complete['outputs_sha256'].items():s.require(s.sha(run/rel)==digest,'Benchmark artifact changed')
        forecast=bench['forecast_seconds'];storage=bench['storage_required_bytes'];s.require(bench['runtime_capacity_pass'] and forecast<=PLAN['maximum_forecast_seconds'],'Runtime ceiling exceeded')
        qualification=dict(run=str(run),complete_sha256=s.sha(run/'COMPLETE.json'))
    free=shutil.disk_usage(s.HERE).free;s.require(free>=storage,'Storage reserve insufficient')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,storage_required_bytes=storage,free_bytes_at_preflight=free,qualification=qualification,
        workers=1,numerical_threads=1,automatic_polling=False)


def status(output,state,**fields):
    temporary=output/f'.status_{os.getpid()}.tmp';s.dump(temporary,dict(status=state,utc=s.utc(),pid=os.getpid(),**fields));os.replace(temporary,output/'STATUS.json')


def execute(job_path):
    job=s.read(job_path/'job.json');output=Path(job['output']);output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});s.require(all(os.environ.get(k)=='1' for k in THREADS),'Single numerical thread')
        s.require(s.HERE==job_path/'inputs/TT008' and hashes()==job['inputs_sha256'],'Unchanged frozen worker inputs');registered()
        s.dump(output/'manifest.json',dict(study='TT008',mode=job['mode'],started_utc=s.utc(),pid=os.getpid(),job=str(job_path),job_sha256=s.sha(job_path/'job.json'),
            inputs_sha256=hashes(),python=sys.version,executable=sys.executable,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in THREADS},detached=job['detached'],forecast_seconds=job['forecast_seconds'],
            qualification=job['qualification'],registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),classification=PLAN['classification'] if job['mode']=='scientific' else 'EXCLUDED_TECHNICAL_QUALIFICATION'))
        s.dump(output/'RUNNING.json',dict(status='RUNNING',started_utc=s.utc(),pid=os.getpid(),note='Historical startup; STATUS/COMPLETE/FAILED give current state.'))
        def progress(phase,**fields):
            s.require(time.monotonic()-started<PLAN['maximum_forecast_seconds'],'Actual runtime ceiling reached')
            s.require(shutil.disk_usage(output).free>PLAN['storage_reserve_bytes'],'Storage floor reached')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-started,**fields)
        progress('technical_checks')
        import check_forecasts
        import check_scoring
        import check_scoring_flow
        import check_native
        import check_known
        checks=dict(forecasts=check_forecasts.run(),scoring=check_scoring.run(),scoring_flow=check_scoring_flow.run(output),known_schema=check_known.run());s.dump(output/'technical_checks.json',checks)
        check_native.run(output)
        import engine
        if job['mode']=='benchmark':result=engine.benchmark(output,progress)
        else:
            result=engine.scientific(output,progress);s.dump(output/'NATIVE_AUDIT.json',result)
            progress('scoring')
            import score
            analysis=score.run(output)
            progress('report')
            import report
            report.run(output)
            result.update(scientific_verdict=analysis['scientific_verdict'])
        s.require(hashes()==job['inputs_sha256'],'Frozen inputs changed during run')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        done=dict(status='COMPLETE',utc=s.utc(),seconds=time.monotonic()-started,audit_status=result['status'],outputs_sha256=outputs,
            scientific_verdict=result.get('scientific_verdict'),blocks_completed=result.get('blocks_completed',[]),
            native_test_outcomes_generated=job['mode']=='scientific',automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done);status(output,'COMPLETE',seconds=done['seconds'],scientific_verdict=done['scientific_verdict'])
        print(json.dumps(dict(status='COMPLETE',mode=job['mode'],seconds=done['seconds'],output=str(output))),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),traceback=traceback.format_exc()));status(output,'FAILED');raise


def launch(mode,name,benchmark,host_launch=False):
    s.require(name and name.replace('_','').isalnum(),'Unique simple run name');pre=preflight(mode,benchmark);inputs=pre['inputs_sha256']
    detached=mode=='scientific';s.require(not detached or host_launch,'Scientific run requires persistent host execution')
    output=(s.HERE/'runs'/name).resolve();job=(s.HERE/'jobs'/name).resolve();s.require(not output.exists(),'Run already exists');job.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        target=job/'inputs/TT008'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,target);s.require(s.sha(target)==digest,'Copy changed')
    s.require(hashes()==inputs,'Inputs changed during freezing')
    command=[sys.executable,'-B',str(job/'inputs/TT008/run.py'),'--execute',str(job)]
    s.dump(job/'job.json',dict(study='TT008',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,detached=detached,
        host_launch_requested=host_launch,status_policy='One startup persistence check; no automatic polling.',**pre))
    env=os.environ.copy();env.update({k:'1' for k in THREADS});env['PYTHONDONTWRITEBYTECODE']='1';env['TT008_LANE']=str(s.HERE.parent)
    if mode=='scientific':
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as ledger:ledger.write(json.dumps(dict(event='TT008_REGISTERED_PROSPECTIVE_LAUNCH',recorded_utc=s.utc(),study='TT008',
            registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),job=str(job),run=str(output),job_sha256=s.sha(job/'job.json'),
            blocks=list(range(8800000,8800064)),new_test_outcomes_generated=False,automatic_polling=False))+'\n')
    with (job/'console.log').open('xb') as log:process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=process.pid,utc=s.utc(),detached=detached,launcher_pid=os.getpid()))
    if detached:print(json.dumps(dict(status='SPAWNED',pid=process.pid,forecast_seconds=pre['forecast_seconds'],job=str(job),output=str(output),persistence_check_pending=True,automatic_polling=False)),flush=True)
    else:
        code=process.wait()
        if code:raise subprocess.CalledProcessError(code,command)
        done=s.read(output/'COMPLETE.json');print(json.dumps(dict(status='COMPLETE',mode=mode,seconds=done['seconds'],output=str(output))),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['benchmark','scientific']);parser.add_argument('--name');parser.add_argument('--benchmark',default='benchmark_v1')
    parser.add_argument('--host-launch',action='store_true');parser.add_argument('--preflight-only',action='store_true');parser.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.preflight_only:print(json.dumps({k:v for k,v in preflight(args.mode,args.benchmark).items() if k!='inputs_sha256'},indent=2))
    else:
        if not args.mode or not args.name:parser.error('--mode and --name required')
        launch(args.mode,args.name,args.benchmark,args.host_launch)


if __name__=='__main__':main()
