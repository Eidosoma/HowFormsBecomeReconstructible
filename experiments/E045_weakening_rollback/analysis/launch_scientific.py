"""Verify completed technical evidence and launch one frozen comparison."""
import argparse
from datetime import datetime,timedelta
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,sha,utc
from E015_functional_inheritance.audit import verify
from E045_weakening_rollback.workflow import technical


def load(path):return json.loads(path.read_text())


def inactive():
    active=[str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('RUNNING','PREPARED')]
    assert not active,active
    assert not (HERE/'jobs/rollback_v1').exists() and not (HERE/'runs/rollback_v1').exists()


def prepare():
    affinity=cap_cpus(8); receipt=technical();inactive(); check_inputs(HERE/'analysis/freeze_v1')
    f=load(HERE/'analysis/forecast_v1.json'); assert f['capacity_pass'] and f['workers']==8 and f['cpu_affinity']==affinity
    assert f['inputs_sha256']==receipt['inputs_sha256'] and len(f['inputs_sha256'])==21
    evidence={}
    for name,count in (('fixture_v1',4032),('benchmark_v1',2016)):
        r=HERE/'runs'/name; verify(r)
        a=load(r/'INDEPENDENT_AUDIT.json'); assert a['status']=='PASS' and a['individual_observations']==count
        assert a['complete_sha256']==sha(r/'COMPLETE.json') and a['audit_code_sha256']==sha(HERE/'audit.py')
        p=HERE/'figures'/name/'provenance.json'; picture=load(p)
        assert picture['audit_sha256']==sha(r/'INDEPENDENT_AUDIT.json') and picture['summary_sha256']==sha(r/'summary.json')
        for rel,digest in picture['outputs_sha256'].items():assert sha(p.parent/rel)==digest
        for path in (r/'COMPLETE.json',r/'INDEPENDENT_AUDIT.json',p):evidence[str(path.relative_to(ROOT))]=sha(path)
    b=HERE/'runs/benchmark_v1'; status=load(HERE/'jobs/benchmark_v1/status.json')
    check_inputs(HERE/'jobs/benchmark_v1'); assert status['status']=='COMPLETE'
    assert f['benchmark_complete_sha256']==sha(b/'COMPLETE.json') and f['benchmark_audit_sha256']==sha(b/'INDEPENDENT_AUDIT.json')
    assert f['benchmark_run_bytes']==sum(p.stat().st_size for p in b.rglob('*') if p.is_file())
    assert f['forecast_seconds']==2.0*f['benchmark_seconds']*16*4*math.ceil(32/f['workers'])+120
    assert f['storage_with_reserve_bytes']==math.ceil(1.5*f['benchmark_run_bytes']*4*32)+128*1024**2
    available=shutil.disk_usage(HERE).free; assert available>f['storage_with_reserve_bytes']
    for rel,digest in load(HERE/'SOURCE_DATA.json')['sha256'].items():assert sha(ROOT/rel)==digest
    result=dict(status='PASS',utc=utc(),launcher_sha256=sha(__file__),inputs_sha256=f['inputs_sha256'],
        forecast_sha256=sha(HERE/'analysis/forecast_v1.json'),technical_receipt_sha256=sha(HERE/'analysis/technical_v1.json'),
        evidence_sha256=evidence,forecast_seconds=f['forecast_seconds'],storage_with_reserve_bytes=f['storage_with_reserve_bytes'],
        available_bytes=available,workers=8,cpu_affinity=affinity,numerical_threads=1,scientific_cases_not_yet_run=True,
        original_endpoints_match_e041_exactly=True,fixtures_and_benchmark_figures_inspected=True)
    p=HERE/'analysis/prelaunch_scientific_v1.json';assert not p.exists();dump(p,result)
    print(json.dumps({k:result[k] for k in ('status','utc','forecast_seconds','storage_with_reserve_bytes','available_bytes')},indent=2),flush=True)


def launch():
    cap_cpus(8); technical();inactive()
    p=HERE/'analysis/prelaunch_scientific_v1.json'; pre=load(p)
    assert pre['status']=='PASS' and pre['launcher_sha256']==sha(__file__)
    assert pre['forecast_sha256']==sha(HERE/'analysis/forecast_v1.json')
    assert pre['technical_receipt_sha256']==sha(HERE/'analysis/technical_v1.json')
    for rel,digest in {**pre['inputs_sha256'],**pre['evidence_sha256']}.items():assert sha(ROOT/rel)==digest
    assert shutil.disk_usage(HERE).free>pre['storage_with_reserve_bytes']
    subprocess.run([sys.executable,'-B',str(HERE/'workflow.py'),'--mode','scientific','--detach'],cwd=ROOT,check=True)
    job,run=HERE/'jobs/rollback_v1',HERE/'runs/rollback_v1';start=load(job/'launch.json')
    try:
        deadline=time.monotonic()+15
        while True:
            os.kill(start['pid'],0)
            try:status=load(job/'status.json')
            except(FileNotFoundError,json.JSONDecodeError):status={}
            if status.get('status')=='FAILED':raise RuntimeError(status)
            logs=list(run.glob('worker_*.log'))
            if status.get('stage')=='simulation' and (run/'manifest.json').exists() and len(logs)>=8:break
            if time.monotonic()>deadline:raise TimeoutError('Startup check exceeded 15 seconds')
            time.sleep(.5)
        check_inputs(job);check_inputs(run);m=load(run/'manifest.json');c=m['contract']
        assert c['mode']=='scientific' and c['blocks']==list(range(32000,32032)) and c['workers']==8 and c['variants']==['original','targeted_rollback','random_rollback']
        assert c['cycle']==dict(read_steps=2048,settling_steps=1024,write_steps=128,generations=32)
        assert c['config']['recipients']==4 and len(c['panels'])==12
        assert m['inputs_sha256']==pre['inputs_sha256'] and m['cpu_affinity']==pre['cpu_affinity'] and m['numerical_threads']==1
        assert c['source']=='E041_full_rewrite_confirmation/runs/serial_v1'
        assert os.getsid(start['pid'])==start['pid'] and not (run/'FAILED.json').exists()
        proc=Path('/proc')/str(start['pid']);command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
        assert str(HERE/'workflow.py') in command and '--child' in command
        result=dict(status='PASS',utc=utc(),launch_utc=start['utc'],pid=start['pid'],job_status=status,process_command=command,
            workers=8,numerical_threads=1,cpu_affinity=m['cpu_affinity'],started_worker_logs=len(logs),blocks=32,lineages=512,
            frozen_inputs_verified=21,forecast_seconds=pre['forecast_seconds'],
            estimated_completion_utc=(datetime.fromisoformat(start['utc'])+timedelta(seconds=pre['forecast_seconds'])).isoformat(),
            preflight_sha256=sha(p),launcher_sha256=sha(__file__),automatic_polling_started=False,automatic_successor_started=False)
        dest=HERE/'analysis/scientific_launch_verification_v1.json';assert not dest.exists();dump(dest,result)
        print(json.dumps(result,indent=2),flush=True)
    except BaseException:
        dump(HERE/'analysis/scientific_startup_failure_v1.json',dict(utc=utc(),launch=start,traceback=traceback.format_exc(),automatic_restart=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:launch()
