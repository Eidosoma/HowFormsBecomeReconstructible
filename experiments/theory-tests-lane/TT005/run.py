"""Freeze, qualify and execute TT005. Scientific jobs have no polling loop."""
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

THREAD_KEYS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
OWN_INPUTS=('support.py','engine.py','auditor.py','analyze.py','analysis_audit.py','checks.py','run.py',
    'prepare_source.py','PROTOCOL.md','plan.json','source_manifest.json','source_packets.npz',
    'native_checks.npz','reference_manifest.json')


def hashes():
    refs=json.loads((s.HERE/'reference_manifest.json').read_text())['files_sha256']
    return {name:s.sha(s.HERE/name) for name in sorted([*OWN_INPUTS,*refs])}


def status(output,state,**fields):
    temporary=output/f'.status_{os.getpid()}.tmp'
    s.dump(temporary,dict(status=state,utc=s.utc(),pid=os.getpid(),**fields))
    os.replace(temporary,output/'STATUS.json')


def qualified(name,mode,expected):
    output=s.HERE/'runs'/name
    complete=json.loads((output/'COMPLETE.json').read_text());manifest=json.loads((output/'manifest.json').read_text())
    if complete['status']!='COMPLETE' or manifest['mode']!=mode or manifest['inputs_sha256']!=expected:
        raise ValueError('Qualification absent or inputs changed: '+name)
    if complete['dynamics_audit_status']!='PASS' or complete['analysis_audit_status']!='PASS':raise ValueError('Qualification audit failed')
    for rel,digest in complete['outputs_sha256'].items():
        if s.sha(output/rel)!=digest:raise ValueError('Qualification evidence changed: '+rel)
    return complete,dict(run=str(output),complete_sha256=s.sha(output/'COMPLETE.json'))


def preflight(mode,fixture,benchmark):
    s.verify_inputs();inputs=hashes();qualification={};forecast=None
    reserve=s.PLAN['minimum_storage_reserve_bytes']
    if mode=='pilot':
        _,qualification['fixture']=qualified(fixture,'fixture',inputs)
        bench,qualification['benchmark']=qualified(benchmark,'benchmark',inputs)
        contexts,_=s.cases('pilot');technical,_=s.cases('benchmark');factor=len(contexts)/len(technical)
        t=bench['timings']
        forecast=s.PLAN['forecast_safety_factor']*(t['simulation_seconds']+t['audit_seconds'])*factor+2*t['technical_checks_seconds']+factor*t['analysis_seconds']+60
        if forecast>s.PLAN['pilot_forecast_ceiling_seconds']:
            raise ValueError(f'Forecast {forecast:.2f}s exceeds fixed {s.PLAN["pilot_forecast_ceiling_seconds"]}s ceiling; revise before scientific assays.')
        reserve=max(reserve,int(2*factor*bench['output_bytes']))
    free=shutil.disk_usage(s.HERE).free
    if free<reserve:raise ValueError('Insufficient storage reserve')
    return dict(inputs_sha256=inputs,forecast_seconds=forecast,minimum_free_bytes=reserve,free_bytes_at_preflight=free,
        qualification=qualification,workers=1,numerical_threads=1,automatic_polling=False)


def execute(job_path):
    job=json.loads((job_path/'job.json').read_text());output=Path(job['output']);output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_frame):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
        if any(os.environ.get(k)!='1' for k in THREAD_KEYS):raise ValueError('Numerical threads must be one')
        if s.HERE!=job_path/'inputs/TT005' or hashes()!=job['inputs_sha256']:raise ValueError('Worker must use frozen inputs')
        s.verify_inputs()
        s.dump(output/'manifest.json',dict(study='TT005',mode=job['mode'],started_utc=s.utc(),pid=os.getpid(),
            job=str(job_path),job_sha256=s.sha(job_path/'job.json'),inputs_sha256=hashes(),
            python=sys.version,executable=sys.executable,numpy=np.__version__,platform=platform.platform(),
            threads={k:os.environ[k] for k in THREAD_KEYS},cpu_affinity=sorted(os.sched_getaffinity(0)),
            detached=job['detached'],forecast_seconds=job['forecast_seconds'],qualification=job['qualification'],
            rdt_verdict='NOT_A_CONFIRMATORY_TEST'))
        s.dump(output/'RUNNING.json',dict(status='RUNNING',started_utc=s.utc(),pid=os.getpid(),
            note='Historical launch record; STATUS.json and COMPLETE/FAILED.json determine current state.'))
        status(output,'RUNNING',phase='technical_checks');began=time.monotonic()
        with (output/'technical_checks.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(s.HERE/'checks.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
        checks_seconds=time.monotonic()-began
        import engine
        import auditor
        import analyze
        import analysis_audit
        status(output,'RUNNING',phase='simulation');simulation_seconds=engine.run_events(output,job['mode'])
        status(output,'RUNNING',phase='dynamics_audit');audit=auditor.audit(output)
        status(output,'RUNNING',phase='analysis');began=time.monotonic();summary=analyze.run(output)
        analysis=analysis_audit.audit(output);analysis_seconds=time.monotonic()-began
        if hashes()!=job['inputs_sha256']:raise ValueError('Inputs changed during execution')
        s.verify_inputs()
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        complete=dict(status='COMPLETE',utc=s.utc(),seconds=time.monotonic()-started,
            timings=dict(technical_checks_seconds=checks_seconds,simulation_seconds=simulation_seconds,audit_seconds=audit['seconds'],analysis_seconds=analysis_seconds),
            dynamics_audit_status=audit['status'],analysis_audit_status=analysis['status'],contexts_replayed=audit['contexts_replayed'],
            paired_cue_assays=summary['paired_cue_assays'],native_rebuilds=0,output_bytes=sum((output/p).stat().st_size for p in outputs),
            outputs_sha256=outputs,rdt_verdict='NOT_A_CONFIRMATORY_TEST')
        s.dump(output/'COMPLETE.json',complete);status(output,'COMPLETE',seconds=complete['seconds'])
        print(json.dumps(dict(status='COMPLETE',mode=job['mode'],seconds=complete['seconds'],output=str(output))),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),traceback=traceback.format_exc()))
        status(output,'FAILED');raise


def launch(mode,name,fixture,benchmark,host_launch=False):
    if not name or not name.replace('_','').isalnum():raise ValueError('Use a simple unique run name')
    if mode=='pilot' and not host_launch:raise ValueError('Pilot requires explicit host launch, not a sandbox child process')
    check=preflight(mode,fixture,benchmark);inputs=check['inputs_sha256']
    output=(s.HERE/'runs'/name).resolve();job_path=(s.HERE/'jobs'/name).resolve()
    if output.exists():raise FileExistsError(output)
    job_path.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        dest=job_path/'inputs/TT005'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,dest)
        if s.sha(dest)!=digest:raise ValueError('Snapshot copy changed')
    if hashes()!=inputs:raise ValueError('Inputs changed during freezing')
    detached=mode=='pilot'
    command=[sys.executable,'-B',str(job_path/'inputs/TT005/run.py'),'--execute',str(job_path)]
    job=dict(study='TT005',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,detached=detached,
        host_launch_requested=host_launch,status_policy='One post-launch persistence check; later status only on user request.',**check)
    s.dump(job_path/'job.json',job)
    env=os.environ.copy();env.update({k:'1' for k in THREAD_KEYS});env['PYTHONDONTWRITEBYTECODE']='1'
    if mode=='pilot':
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as ledger:
            ledger.write(json.dumps(dict(event='NATIVE_READOUT_DEVELOPMENT_LAUNCH',recorded_utc=s.utc(),study='TT005',classification='DEVELOPMENT',
                job=str(job_path),run=str(output),job_sha256=s.sha(job_path/'job.json'),planned_paired_cue_assays=2816,automatic_polling=False))+'\n')
    with (job_path/'console.log').open('xb') as log:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            cwd=s.HERE.parent,env=env,start_new_session=detached)
    s.dump(job_path/'PID.json',dict(pid=process.pid,utc=s.utc(),detached=detached,launcher_pid=os.getpid()))
    if detached:
        # Persistence is checked once from a subsequent host command, after this
        # launcher exits. No process polling or monitoring loop lives here.
        print(json.dumps(dict(status='SPAWNED',pid=process.pid,forecast_seconds=check['forecast_seconds'],job=str(job_path),
            output=str(output),automatic_polling=False,persistence_check_pending=True)),flush=True)
    else:
        code=process.wait()
        if code:raise subprocess.CalledProcessError(code,command)
        done=json.loads((output/'COMPLETE.json').read_text())
        print(json.dumps(dict(status='COMPLETE',mode=mode,output=str(output),seconds=done['seconds'],timings=done['timings'])),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['fixture','benchmark','pilot']);p.add_argument('--name')
    p.add_argument('--fixture',default='fixture_v1');p.add_argument('--benchmark',default='benchmark_v1')
    p.add_argument('--execute',type=Path);p.add_argument('--host-launch',action='store_true');p.add_argument('--preflight-only',action='store_true')
    args=p.parse_args()
    if args.execute:
        if args.mode or args.name or args.host_launch or args.preflight_only:p.error('--execute is internal')
        execute(args.execute.resolve())
    elif args.preflight_only:
        if args.mode!='pilot':p.error('Preflight is for the pilot')
        check=preflight(args.mode,args.fixture,args.benchmark)
        print(json.dumps({k:v for k,v in check.items() if k!='inputs_sha256'},indent=2))
    else:
        if not args.mode or not args.name:p.error('--mode and --name required')
        launch(args.mode,args.name,args.fixture,args.benchmark,args.host_launch)


if __name__=='__main__':main()
