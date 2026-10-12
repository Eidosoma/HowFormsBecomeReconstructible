"""Freeze and execute short uncertainty calculations; preserve every attempt."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import scipy
import study as s

OWN=('PROTOCOL.md','plan.json','source_manifest.json','prepare.py','core.py','study.py','checks.py','audit.py','report.py','run.py')


def hashes():
    source=json.loads((s.HERE/'source_manifest.json').read_text())['files']
    return {rel:s.sha(s.HERE/rel) for rel in sorted([*OWN,*source])}


def state(output,status,**fields):
    temporary=output/'.status.tmp'
    s.dump(temporary,dict(status=status,utc=s.utc(),pid=os.getpid(),**fields))
    os.replace(temporary,output/'STATUS.json')


def execute(output):
    started=time.monotonic();manifest=json.loads((output/'manifest.json').read_text())
    try:
        if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{max(os.sched_getaffinity(0))})
        if s.HERE!=output/'inputs' or hashes()!=manifest['inputs_sha256']:raise ValueError('Frozen execution required')
        if any(os.environ.get(k)!='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')):
            raise ValueError('One numerical thread required')
        s.verify_sources();state(output,'RUNNING',phase='checks')
        with (output/'technical_checks.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(s.HERE/'checks.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
        state(output,'RUNNING',phase='calculation')
        result=s.run(output,benchmark=manifest['mode']=='benchmark')
        state(output,'RUNNING',phase='audit')
        import audit
        audited=audit.audit(output)
        state(output,'RUNNING',phase='report')
        import report
        report.render(output,result,audited)
        if hashes()!=manifest['inputs_sha256']:raise ValueError('Inputs changed during run')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*'))
                 if p.is_file() and p.name not in ('STATUS.json','console.log')}
        elapsed=time.monotonic()-started
        s.dump(output/'COMPLETE.json',dict(status='COMPLETE',utc=s.utc(),seconds=elapsed,
            audit_status=audited['status'],outputs_sha256=outputs,rdt_verdict=s.PLAN['rdt_verdict']))
        state(output,'COMPLETE',seconds=elapsed)
        print(json.dumps(dict(status='COMPLETE',mode=manifest['mode'],seconds=elapsed,output=str(output))),flush=True)
    except BaseException:
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),traceback=traceback.format_exc()))
        state(output,'FAILED');raise


def launch(mode,name,benchmark):
    if not name.replace('_','').isalnum():raise ValueError('Use a unique simple name')
    s.verify_sources();inputs=hashes();forecast=None;qualification=None
    if mode=='development':
        bench=s.HERE/'runs'/benchmark
        complete=json.loads((bench/'COMPLETE.json').read_text());m=json.loads((bench/'manifest.json').read_text())
        if complete['status']!='COMPLETE' or m['mode']!='benchmark' or m['inputs_sha256']!=inputs:
            raise ValueError('Need a successful benchmark with identical inputs')
        for rel,digest in complete['outputs_sha256'].items():
            if s.sha(bench/rel)!=digest:raise ValueError('Benchmark evidence changed')
        forecast=3*complete['seconds']+30
        if forecast>s.PLAN['foreground_limit_seconds']:
            raise RuntimeError('Forecast exceeds 600 seconds; use a persistent detached host job before scientific execution')
        qualification=dict(run=str(bench),complete_sha256=s.sha(bench/'COMPLETE.json'))
    if shutil.disk_usage(s.HERE).free<s.PLAN['storage_reserve_bytes']:raise ValueError('Insufficient free storage')
    output=(s.HERE/'runs'/name).resolve();output.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        destination=output/'inputs'/rel;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(s.HERE/rel,destination)
        if s.sha(destination)!=digest:raise ValueError('Snapshot mismatch')
    s.dump(output/'manifest.json',dict(study='TT004',mode=mode,created_utc=s.utc(),inputs_sha256=inputs,
        forecast_seconds=forecast,benchmark=qualification,python=sys.version,executable=sys.executable,
        platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,workers=1,numerical_threads=1,
        native_trajectories_generated=0,rdt_verdict=s.PLAN['rdt_verdict']))
    if mode=='development':
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:
            f.write(json.dumps(dict(event='UNCERTAINTY_DEVELOPMENT_STARTED',recorded_utc=s.utc(),study='TT004',
                run=str(output),classification='DEVELOPMENT',native_trajectories_generated=0))+'\n')
    command=[sys.executable,'-B',str(output/'inputs/run.py'),'--execute',str(output)]
    with (output/'console.log').open('x') as log:
        subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    complete=json.loads((output/'COMPLETE.json').read_text())
    print(json.dumps(dict(status='COMPLETE',mode=mode,seconds=complete['seconds'],forecast_seconds=forecast,output=str(output))),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['benchmark','development'])
    parser.add_argument('--name');parser.add_argument('--benchmark',default='benchmark_v1');parser.add_argument('--execute',type=Path)
    args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.mode and args.name:launch(args.mode,args.name,args.benchmark)
    else:parser.error('Supply --mode and --name')


if __name__=='__main__':main()
