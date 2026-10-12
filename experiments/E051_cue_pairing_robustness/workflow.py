"""Benchmark and detached scientific workflow; no automatic successor."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E051_cue_pairing_robustness.run import input_paths


def technical():
    r = json.loads((HERE/'analysis/technical_v1.json').read_text())
    assert r['status'] == 'PASS'
    for rel, digest in r['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    return r


def execute(mode, workers):
    cap_cpus(8); started=time.monotonic()
    name = 'benchmark_v1' if mode == 'benchmark' else 'robustness_v1'
    job, run = HERE/'jobs'/name, HERE/'runs'/name
    if not job.exists(): new_run(job, input_paths(), dict(experiment='E051', mode=mode, workers=workers))
    check_inputs(job)
    dump(job/'pid.json', dict(pid=os.getpid(), utc=utc()))
    try:
        for stage, command in (('simulation', ['run.py', '--mode', mode, '--workers', str(workers)]),
            ('audit', ['audit.py', str(run), '--workers', str(workers)]), ('figures', ['plot.py', str(run)])):
            dump(job/'status.json', dict(status='RUNNING', stage=stage, utc=utc(), pid=os.getpid()))
            with (job/'workflow.log').open('a') as log:
                subprocess.run([sys.executable, '-B', str(HERE/command[0]), *command[1:]], cwd=ROOT,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job); elapsed=time.monotonic()-started
        if mode == 'benchmark':
            size = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
            workers_full = min(8, len(cap_cpus(8)) or 1)
            simulation_seconds=json.loads((run/'worker_900041.json').read_text())['seconds']
            audit_seconds=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())['worker_seconds'][0]
            seconds=3.0*(simulation_seconds+audit_seconds)*16*4*math.ceil(32/workers_full)+120
            required=math.ceil(1.5*size*4*32)+128*1024**2
            path=HERE/'analysis/forecast_v1.json'; assert not path.exists()
            dump(path, dict(utc=utc(), benchmark_seconds=elapsed, simulation_worker_seconds=simulation_seconds, audit_worker_seconds=audit_seconds, benchmark_run_bytes=size,
                benchmark_complete_sha256=sha(run/'COMPLETE.json'), benchmark_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
                forecast_seconds=seconds, workers=workers_full, cpu_affinity=cap_cpus(8), detached_required=seconds>600,
                storage_with_reserve_bytes=required, available_bytes=shutil.disk_usage(HERE).free,
                capacity_pass=required <= shutil.disk_usage(HERE).free,
                inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in input_paths()},
                technical_receipt_sha256=sha(HERE/'analysis/technical_v1.json'), automatic_successor_started=False))
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=elapsed,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            figure_provenance_sha256=sha(HERE/'figures'/name/'provenance.json'), automatic_successor_started=False))
        print(json.dumps(dict(status='COMPLETE', mode=mode, seconds=elapsed), indent=2), flush=True)
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc())); raise


def main():
    p=argparse.ArgumentParser(); p.add_argument('--mode', choices=('benchmark', 'scientific'), required=True)
    p.add_argument('--detach', action='store_true'); p.add_argument('--child', action='store_true')
    a=p.parse_args(); affinity=cap_cpus(8); technical()
    if a.mode == 'scientific':
        f=json.loads((HERE/'analysis/forecast_v1.json').read_text())
        for rel,digest in f['inputs_sha256'].items(): assert sha(ROOT/rel)==digest
        assert f['technical_receipt_sha256']==sha(HERE/'analysis/technical_v1.json')
        assert f['cpu_affinity']==affinity and f['capacity_pass']
        assert shutil.disk_usage(HERE).free>f['storage_with_reserve_bytes']
        if f['detached_required'] and not (a.detach or a.child): raise ValueError('Scientific forecast requires detached execution')
        workers=f['workers']
    else: workers=1
    if a.child: execute(a.mode, workers); return
    name='benchmark_v1' if a.mode=='benchmark' else 'robustness_v1'
    job, run = HERE/'jobs'/name,HERE/'runs'/name
    assert not job.exists() and not run.exists()
    extra=[HERE/'analysis/technical_v1.json']+([HERE/'analysis/forecast_v1.json'] if a.mode=='scientific' else [])
    new_run(job,input_paths()+extra,dict(experiment='E051',mode=a.mode,workers=workers,detached=a.detach))
    dump(job/'status.json',dict(status='PREPARED',utc=utc()))
    if a.detach:
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--mode',a.mode,'--child']
        with (job/'launcher.log').open('x') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(job/'launch.json',dict(utc=utc(),pid=process.pid,command=command));print('Detached PID',process.pid,flush=True)
    else: execute(a.mode,workers)


if __name__=='__main__': main()
