"""Immutable benchmark/audit jobs with detached, unpolled long execution."""
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
import support as s

OWN=['PROTOCOL.md','DRAFT_PROTOCOL.md','PLANNING_CONTEXT.json','PLANNING_REVIEW.json','IMPLEMENTATION_REUSE.json',
    'SOURCE_RECEIPT.json','support.py','native.py','arithmetic.py','prepare.py','optimizer.py','repair.py','boundary.py',
    'intake.py','scoring.py','engine.py','checks.py','report.py','run.py']
THREADS=['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']
CEILING=10800
RESERVE=1073741824


def hashes():
    return {name:s.sha(s.HERE/name) for name in sorted(OWN+list(s.verify_sources()['files_sha256']))}


def status(output,state,**detail):
    temp=output/'STATUS.tmp';s.dump(temp,dict(status=state,utc=s.utc(),pid=os.getpid(),**detail));temp.replace(output/'STATUS.json')


def preflight(mode,benchmark):
    inputs=hashes();forecast=None;qualification={}
    if mode=='audit':
        base=s.HERE/'runs'/benchmark;done=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json')
        s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and manifest['mode']=='benchmark','Successful benchmark')
        s.require(manifest['inputs_sha256']==inputs,'Benchmark and audit have identical frozen inputs')
        for rel,digest in done['outputs_sha256'].items():s.require(s.sha(base/rel)==digest,'Benchmark output identity')
        b=s.read(base/'benchmark.json');forecast=b['forecast_seconds'];s.require(b['capacity_pass'] and forecast<CEILING,'Runtime forecast ceiling')
        qualification=dict(run=str(base),complete_sha256=s.sha(base/'COMPLETE.json'))
    storage=RESERVE+2*sum((s.HERE/rel).stat().st_size for rel in inputs)
    s.require(shutil.disk_usage(s.HERE).free>=storage,'Free storage including immutable copy')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,qualification=qualification,required_free_bytes=storage,
        maximum_seconds=CEILING,automatic_polling=False,automatic_successor=False,workers=1,numerical_threads=1)


def execute(job):
    meta=s.read(job/'job.json');output=Path(meta['output']);output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupt(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    try:
        s.require(s.HERE==job/'inputs/TT013' and hashes()==meta['inputs_sha256'],'Execute unchanged frozen inputs')
        allowed=os.sched_getaffinity(0);cpu=7 if 7 in allowed else min(allowed);os.sched_setaffinity(0,{cpu})
        s.require(all(os.environ.get(k)=='1' for k in THREADS),'One numerical thread')
        s.dump(output/'manifest.json',dict(study='TT013',mode=meta['mode'],started_utc=s.utc(),pid=os.getpid(),job_sha256=s.sha(job/'job.json'),
            inputs_sha256=meta['inputs_sha256'],executable=sys.executable,python=sys.version,numpy=np.__version__,platform=platform.platform(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in THREADS},forecast_seconds=meta['forecast_seconds'],
            detached=meta['detached'],qualification=meta['qualification'],new_scientific_outcomes=False))
        def progress(phase,**detail):
            s.require(time.monotonic()-start<CEILING,'Runtime ceiling')
            s.require(shutil.disk_usage(output).free>=RESERVE,'Storage floor')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-start,**detail)
        import checks
        import intake
        import engine
        progress('technical_checks');t=time.monotonic();checks.run(output);check_seconds=time.monotonic()-t
        progress('source_provenance');s.dump(output/'PROVENANCE_AUDIT.json',intake.provenance())
        t=time.monotonic();panel,intake_result=intake.run(output,[34006] if meta['mode']=='benchmark' else None,progress);prep_seconds=time.monotonic()-t
        if meta['mode']=='benchmark':result=engine.benchmark(output,prep_seconds,check_seconds,progress)
        else:
            engine.audit(output,progress)
            import scoring
            import report
            progress('all_raw_window_scoring_and_summaries');scoring.run(panel,output)
            progress('bounded_report');result=report.run(output)
        progress('final_input_verification');s.require(hashes()==meta['inputs_sha256'],'Inputs unchanged after execution')
        committed={str(path.relative_to(output)):s.sha(path) for path in sorted(output.rglob('*')) if path.is_file() and path.name!='STATUS.json'}
        done=dict(status='COMPLETE',audit_status='PASS',mode=meta['mode'],utc=s.utc(),seconds=time.monotonic()-start,
            outputs_sha256=committed,full_native_replay_performed=meta['mode']=='audit',new_scientific_outcomes=False,
            automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done);status(output,'COMPLETE',seconds=done['seconds'],mode=meta['mode'])
        print(json.dumps({k:v for k,v in done.items() if k!='outputs_sha256'}),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=s.utc(),seconds=time.monotonic()-start,traceback=traceback.format_exc())
        s.dump(output/'FAILED.json',failure);status(output,'FAILED');raise


def launch(mode,name,benchmark,host_launch):
    s.require(name and name.replace('_','').isalnum(),'Simple unique job name');pre=preflight(mode,benchmark)
    detached=mode=='audit' and pre['forecast_seconds']>600
    s.require(not detached or host_launch,'Detached job requires persistent host execution')
    job=s.HERE/'jobs'/name;output=s.HERE/'runs'/name
    s.require(not job.exists() and not output.exists(),'Never overwrite a job or run');job.mkdir(parents=True)
    for rel,digest in pre['inputs_sha256'].items():
        target=job/'inputs/TT013'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write((s.HERE/rel).read_bytes())
        s.require(s.sha(target)==digest,'Frozen copy identity')
    s.require(hashes()==pre['inputs_sha256'],'No mutation during freeze')
    command=[sys.executable,'-B',str(job/'inputs/TT013/run.py'),'--execute',str(job)]
    meta=dict(study='TT013',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,detached=detached,
        host_launch_requested=host_launch,status_policy='One startup persistence check, then no automatic polling.',**pre)
    s.dump(job/'job.json',meta)
    env=os.environ.copy();env.update({k:'1' for k in THREADS});env['PYTHONDONTWRITEBYTECODE']='1'
    with (job/'console.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=child.pid,launcher_pid=os.getpid(),created_utc=s.utc(),detached=detached))
    if not detached:
        code=child.wait()
        s.require(code==0,'Worker failed; retained FAILED.json and frozen source describe this attempt')
    else:
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT013_RECIPIENT_ONLY_COMPLETION_AUDIT_LAUNCH',recorded_utc=s.utc(),
            job_sha256=s.sha(job/'job.json'),job=str(job),pid=child.pid,new_scientific_outcomes=False,automatic_polling=False))+'\n')
    print(json.dumps(dict(status='SPAWNED' if detached else 'COMPLETE',job=str(job),run=str(output),pid=child.pid,
        detached=detached,forecast_seconds=pre['forecast_seconds'],automatic_polling=False,persistence_check_pending=detached),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['benchmark','audit']);parser.add_argument('--name');parser.add_argument('--benchmark',default='benchmark_v1')
    parser.add_argument('--host-launch',action='store_true');parser.add_argument('--preflight-only',action='store_true');parser.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.preflight_only:print(json.dumps({k:v for k,v in preflight(args.mode,args.benchmark).items() if k!='inputs_sha256'},indent=2))
    else:launch(args.mode,args.name,args.benchmark,args.host_launch)
