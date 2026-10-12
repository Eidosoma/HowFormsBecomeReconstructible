"""Measured predecessor forecast and durable detached confirmation workflow."""
import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E025_rewriting_confirmation import model
from E025_rewriting_confirmation.run import input_paths
import numpy as np

FORECAST = HERE/'analysis/forecast_v1.json'
FIXTURES = HERE/'analysis/fixtures_v1.json'
PRIOR = ROOT/'E024_serial_compensation'


def load(path):
    return json.loads(path.read_text())


def fixtures():
    receipt = load(FIXTURES)
    assert receipt['status'] == 'PASS' and receipt['tests'] == 7
    for rel, digest in receipt['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    assert receipt['log_sha256'] == sha(HERE/'analysis/fixtures_v1.log')


def forecast():
    assert not FORECAST.exists()
    fixtures()
    affinity = cap_cpus()
    evidence = {}
    for label, expected_blocks, recipients in (
        ('benchmark_v1', [900024], 1), ('serial_v1', list(range(22000, 22032)), 4)):
        run, job = PRIOR/'runs'/label, PRIOR/'jobs'/label
        check_inputs(run); check_inputs(job)
        manifest = load(run/'manifest.json')
        complete = load(run/'COMPLETE.json')
        audit = load(run/'INDEPENDENT_AUDIT.json')
        status = load(job/'status.json')
        assert complete['status'] == status['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert audit['audit_code_sha256'] == sha(PRIOR/'audit.py')
        assert audit['complete_sha256'] == status['scientific_complete_sha256'] == sha(run/'COMPLETE.json')
        assert status['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, (label, rel)
        expected_cfg = dict(asdict(model.CFG), recipients=recipients)
        assert manifest['contract']['config'] == expected_cfg
        assert manifest['contract']['cycle'] == asdict(model.CYCLE)
        assert manifest['contract']['blocks'] == expected_blocks
        assert manifest['contract']['panels'] == [list(p) for p in model.PANELS]
        assert manifest['contract']['conditions'] == list(model.CONDITIONS)
        assert manifest['contract']['receivers'] == list(model.RECEIVERS)
        assert manifest['numerical_threads'] == 1
        assert manifest['cpu_affinity'] == affinity
        assert manifest['python'] == sys.version and manifest['numpy'] == np.__version__
        assert manifest['executable'] == sys.executable and manifest['platform'] == platform.platform()
        evidence[label] = dict(workflow_seconds=status['seconds'], audit_seconds=audit['seconds'],
            workers=manifest['contract']['workers'], status_sha256=sha(job/'status.json'),
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            manifest_sha256=sha(run/'manifest.json'), original_outputs_verified=len(complete['outputs_sha256']),
            bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
    benchmark_worker = load(PRIOR/'runs/benchmark_v1/worker_900024.json')
    workers = min(12, len(affinity) or (os.cpu_count() or 1))
    batches = math.ceil(32/workers)
    benchmark_estimate = 2.5*(benchmark_worker['seconds']+evidence['benchmark_v1']['audit_seconds'])*4*batches+90
    cohort_estimate = 1.25*evidence['serial_v1']['workflow_seconds']*batches/math.ceil(32/evidence['serial_v1']['workers'])
    seconds = max(benchmark_estimate, cohort_estimate)
    storage = max(evidence['benchmark_v1']['bytes']*4*32, evidence['serial_v1']['bytes'])+1024**3
    available = shutil.disk_usage(HERE).free
    if storage > available: raise RuntimeError(f'Insufficient storage: need {storage}, available {available}')
    result = dict(created_utc=utc(), blocks=32, workers=workers, cpu_affinity=affinity, numerical_threads=1,
        runtime_basis='Unchanged E024 numerical workload; audited full-duration benchmark and completed full cohort',
        independent_new_long_benchmark_required=False, numerical_contract_and_environment_match=True,
        benchmark_formula='2.5*(E024_worker_seconds+E024_benchmark_audit_seconds)*4*ceil(32/workers)+90',
        cohort_formula='1.25*E024_cohort_workflow_seconds*ceil(32/workers)/ceil(32/E024_workers)',
        formula='max(benchmark_derived_seconds,cohort_derived_seconds)',
        benchmark_derived_seconds=benchmark_estimate, cohort_derived_seconds=cohort_estimate,
        forecast_seconds=seconds, detached_required=seconds > 600,
        storage_formula='max(E024_benchmark_bytes*4*32,E024_cohort_bytes)+1_GiB',
        storage_with_reserve_bytes=storage, available_bytes=available, predecessor=evidence,
        benchmark_worker_sha256=sha(PRIOR/'runs/benchmark_v1/worker_900024.json'),
        predecessor_closeout_sha256=sha(PRIOR/'analysis/closeout_v1.json'),
        fixture_receipt_sha256=sha(FIXTURES), inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in input_paths()})
    with FORECAST.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2), flush=True)


def execute(job, output):
    started = time.monotonic()
    check_inputs(job)
    dump(job/'pid.json', dict(pid=os.getpid(), recorded_utc=utc()))
    workers = str(load(job/'manifest.json')['contract']['workers'])
    try:
        for stage, command in (
            ('simulation', ['run.py', '--output', str(output), '--workers', workers]),
            ('audit', ['audit.py', str(output), '--workers', workers]),
            ('figures', ['plot.py', str(output)])):
            dump(job/'status.json', dict(status='RUNNING', stage=stage, utc=utc(), pid=os.getpid()))
            print('Starting', stage, flush=True)
            with (job/'workflow.log').open('a') as log:
                subprocess.run([sys.executable, '-B', str(HERE/command[0]), *command[1:]], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-started,
            scientific_complete_sha256=sha(output/'COMPLETE.json'), audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'),
            figure_provenance_sha256=sha(HERE/'figures'/output.name/'provenance.json')))
        print('Complete:', output, flush=True)
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--forecast', action='store_true')
    parser.add_argument('--run-name', default='confirmation_v1')
    parser.add_argument('--detach', action='store_true')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    cap_cpus()
    if args.forecast:
        forecast()
        return
    if not re.fullmatch(r'[a-z0-9_]+', args.run_name): raise ValueError('Invalid run name')
    output, job = HERE/'runs'/args.run_name, HERE/'jobs'/args.run_name
    fixtures()
    estimate = load(FORECAST)
    for rel, digest in estimate['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    assert cap_cpus() == estimate['cpu_affinity']
    if args.child:
        execute(job, output)
        return
    if estimate['detached_required'] and not args.detach: raise ValueError('Forecast exceeds 600 seconds; detached required')
    if shutil.disk_usage(HERE).free < estimate['storage_with_reserve_bytes']: raise RuntimeError('Storage reserve no longer available')
    if output.exists(): raise FileExistsError(output)
    new_run(job, input_paths()+[FIXTURES, FORECAST], dict(experiment='E025', detached=args.detach,
        run_name=args.run_name, workers=estimate['workers'], forecast_seconds=estimate['forecast_seconds']))
    dump(job/'status.json', dict(status='PREPARED', utc=utc()))
    if args.detach:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', '--run-name', args.run_name]
        with (job/'launcher.log').open('x') as log:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(job/'launch.json', dict(pid=process.pid, utc=utc(), command=command, job=str(job)))
        print('Detached PID', process.pid, 'status:', job/'status.json', flush=True)
    else:
        execute(job, output)


if __name__ == '__main__':
    main()
