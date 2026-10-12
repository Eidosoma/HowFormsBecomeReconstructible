"""Capacity/evidence preflight, one launch and one bounded startup check."""
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
HERE=Path(__file__).resolve().parents[1]; ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,sha,utc
from E015_functional_inheritance.audit import verify
from E053_combined_numerical_confirmation.workflow import technical


def read(path): return json.loads(path.read_text())


def prepare():
    affinity=cap_cpus(8); t=technical(); f=read(HERE/'analysis/forecast_v1.json')
    assert f['capacity_pass'] and f['cpu_affinity']==affinity and f['inputs_sha256']==t['inputs_sha256']
    assert len(t['inputs_sha256'])==25 and t['tests']==22 and t['ten_single_stress_histories_byte_exact']
    assert t['runner_sha256']==sha(HERE/'analysis/run_technical.py')
    assert not (HERE/'runs/robustness_v1').exists() and not (HERE/'jobs/robustness_v1').exists()
    active=[str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if read(p).get('status') in ('RUNNING','PREPARED')]
    assert not active,active
    check_inputs(HERE/'analysis/freeze_v1'); receipts={}
    for name in ('fixture_v1','benchmark_v1'):
        run=HERE/'runs'/name; manifest=verify(run); a=read(run/'INDEPENDENT_AUDIT.json'); s=read(run/'summary.json')
        assert manifest['inputs_sha256']==t['inputs_sha256']
        assert a['status']=='PASS' and a['complete_sha256']==sha(run/'COMPLETE.json') and a['audit_code_sha256']==sha(HERE/'audit.py')
        assert a['all_dynamics_channels_and_assays_replayed'] and a['all_mechanism_diagnostics_replayed']
        assert a['ten_single_stress_histories_byte_exact'] and a['summaries_checked']==len(s['statistics'])
        assert s['status']=='TECHNICAL_ONLY' and s['primary_decision'] is None
        picture=HERE/'figures'/name/'provenance.json'; fig=read(picture)
        assert fig['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json') and fig['summary_sha256']==sha(run/'summary.json')
        assert fig['plot_code_sha256']==sha(HERE/'plot.py')
        for rel,digest in fig['outputs_sha256'].items(): assert sha(picture.parent/rel)==digest
        for p in (run/'COMPLETE.json',run/'INDEPENDENT_AUDIT.json',picture): receipts[str(p.relative_to(ROOT))]=sha(p)
    b=HERE/'runs/benchmark_v1'
    assert read(HERE/'jobs/benchmark_v1/status.json')['status']=='COMPLETE'; check_inputs(HERE/'jobs/benchmark_v1')
    assert f['benchmark_run_bytes']==sum(p.stat().st_size for p in b.rglob('*') if p.is_file())
    assert f['benchmark_complete_sha256']==sha(b/'COMPLETE.json') and f['benchmark_audit_sha256']==sha(b/'INDEPENDENT_AUDIT.json')
    assert f['simulation_worker_seconds']==read(b/'worker_900041.json')['seconds']
    assert f['audit_worker_seconds']==read(b/'INDEPENDENT_AUDIT.json')['worker_seconds'][0]
    assert f['forecast_seconds']==3*(f['simulation_worker_seconds']+f['audit_worker_seconds'])*16*4*math.ceil(32/f['workers'])+120
    assert f['storage_with_reserve_bytes']==math.ceil(1.5*f['benchmark_run_bytes']*4*32)+128*1024**2
    free=shutil.disk_usage(HERE).free; assert free>f['storage_with_reserve_bytes']
    receipt=dict(status='PASS',utc=utc(),launcher_sha256=sha(__file__),inputs_sha256=t['inputs_sha256'],
        evidence_sha256=receipts,technical_receipt_sha256=sha(HERE/'analysis/technical_v1.json'),
        forecast_sha256=sha(HERE/'analysis/forecast_v1.json'),forecast_seconds=f['forecast_seconds'],
        detached_required=f['detached_required'],workers=f['workers'],cpu_affinity=affinity,numerical_threads=1,
        storage_with_reserve_bytes=f['storage_with_reserve_bytes'],available_bytes=free,
        fixtures_and_benchmark_figures_inspected=True,scientific_cases_not_yet_run=True)
    p=HERE/'analysis/prelaunch_scientific_v1.json'; assert not p.exists(); dump(p,receipt)
    print(json.dumps({k:receipt[k] for k in ('status','forecast_seconds','storage_with_reserve_bytes','available_bytes')},indent=2),flush=True)


def launch():
    cap_cpus(8); technical(); pre=read(HERE/'analysis/prelaunch_scientific_v1.json')
    assert pre['status']=='PASS' and pre['launcher_sha256']==sha(__file__)
    assert pre['forecast_sha256']==sha(HERE/'analysis/forecast_v1.json')
    assert pre['technical_receipt_sha256']==sha(HERE/'analysis/technical_v1.json')
    for rel,digest in {**pre['inputs_sha256'],**pre['evidence_sha256']}.items(): assert sha(ROOT/rel)==digest
    assert shutil.disk_usage(HERE).free>pre['storage_with_reserve_bytes']
    command=[sys.executable,'-B',str(HERE/'workflow.py'),'--mode','scientific']
    if pre['detached_required']: command.append('--detach')
    with (HERE/'analysis/scientific_v1.log').open('x') as log:
        subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    job,run=HERE/'jobs/robustness_v1',HERE/'runs/robustness_v1'
    if not pre['detached_required']:
        assert read(job/'status.json')['status']=='COMPLETE'; print('Scientific workflow complete',flush=True); return
    start=read(job/'launch.json'); deadline=time.monotonic()+15
    while True:
        os.kill(start['pid'],0)
        try: status=read(job/'status.json')
        except (FileNotFoundError,json.JSONDecodeError): status={}
        if status.get('status')=='FAILED': raise RuntimeError(status)
        logs=list(run.glob('worker_*.log'))
        if status.get('stage')=='simulation' and (run/'manifest.json').exists() and len(logs)>=pre['workers']: break
        if time.monotonic()>deadline: raise TimeoutError('Bounded startup check exceeded15seconds; no automatic restart')
        time.sleep(.5)
    check_inputs(job); check_inputs(run); m=read(run/'manifest.json'); c=m['contract']
    assert c['blocks']==list(range(36000,36032)) and c['mode']=='scientific' and len(c['conditions'])==20
    assert c['config']['recipients']==4 and c['channel_applications']==33
    assert c['cycle']==dict(read_steps=2048,settling_steps=1024,write_steps=128,generations=32)
    assert c['workers']==pre['workers'] and m['inputs_sha256']==pre['inputs_sha256']
    assert m['cpu_affinity']==pre['cpu_affinity'] and m['numerical_threads']==1
    assert os.getsid(start['pid'])==start['pid'] and os.readlink(Path('/proc')/str(start['pid'])/'fd/0')=='/dev/null'
    result=dict(status='PASS',utc=utc(),launch_utc=start['utc'],pid=start['pid'],job_status=status,
        workers=pre['workers'],cpu_affinity=m['cpu_affinity'],numerical_threads=1,started_worker_logs=len(logs),
        blocks=32,lineages_per_condition=512,conditions=20,frozen_inputs_verified=len(pre['inputs_sha256']),
        forecast_seconds=pre['forecast_seconds'],estimated_completion_utc=(datetime.fromisoformat(start['utc'])+timedelta(seconds=pre['forecast_seconds'])).isoformat(),
        preflight_sha256=sha(HERE/'analysis/prelaunch_scientific_v1.json'),launcher_sha256=sha(__file__),
        automatic_polling_started=False,automatic_successor_started=False)
    dest=HERE/'analysis/scientific_launch_verification_v1.json'; assert not dest.exists(); dump(dest,result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--prepare',action='store_true'); p.add_argument('--figures-inspected',action='store_true')
    a=p.parse_args()
    if a.prepare: assert a.figures_inspected; prepare()
    else: launch()
