"""Use audited full-cohort measurements to forecast and run an unchanged repeat."""
import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
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
from E030_maturing_confirmation.run import input_paths
from E030_maturing_confirmation import model

FORECAST = HERE/'analysis/forecast_v1.json'
FIXTURES = HERE/'analysis/fixtures_v1.json'
SOURCE = HERE/'SOURCE_EVIDENCE.json'


def fixtures():
    receipt = json.loads(FIXTURES.read_text())
    assert receipt['status'] == 'PASS' and receipt['tests'] == 9
    for rel, digest in receipt['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    assert receipt['log_sha256'] == sha(HERE/'analysis/fixtures_v1.log')


def source_evidence():
    reference = json.loads(SOURCE.read_text())
    for rel, digest in reference['provenance_sha256'].items(): assert sha(ROOT/rel) == digest
    check_inputs(ROOT/reference['source_run'])
    check_inputs(ROOT/reference['source_job'])
    assert reference['source_model_sha256'] == sha(HERE/'model.py') == sha(ROOT/'E029_maturing_renewal/model.py')
    assert reference['source_protocol_sha256'] == sha(ROOT/'E029_maturing_renewal/PROTOCOL.md')
    assert reference['config'] == asdict(model.CFG) and reference['cycle'] == asdict(model.CYCLE)
    assert reference['conditions'] == list(model.CONDITIONS)
    assert reference['panels'] == [list(p) for p in model.PANELS]
    assert reference['prior_measurements_reused_for_forecast_only'] and not reference['prior_cases_pooled']
    return reference


def forecast():
    fixtures()
    reference = source_evidence()
    affinity = cap_cpus(8)
    workers = min(8, len(affinity) or (os.cpu_count() or 1))
    rounds_ratio = math.ceil(32/workers)/math.ceil(32/reference['source_workers'])
    seconds = 1.25*reference['workflow_seconds']*rounds_ratio+90
    storage = reference['cohort_bytes']+1024**3
    available = shutil.disk_usage(HERE).free
    if storage > available: raise RuntimeError(f'Need {storage} bytes including reserve; {available} available')
    result = dict(created_utc=utc(), blocks=32, workers=workers, cpu_affinity=affinity, numerical_threads=1,
        source_experiment='E029', source_run=reference['source_run'], source_workers=reference['source_workers'],
        source_workflow_seconds=reference['workflow_seconds'], source_cohort_bytes=reference['cohort_bytes'],
        formula='1.25*E029_full_workflow_seconds*ceil(32/workers)/ceil(32/E029_workers)+90',
        forecast_seconds=seconds, detached_required=seconds > 600,
        storage_formula='E029_full_cohort_bytes+1GiB', storage_with_reserve_bytes=storage, available_bytes=available,
        identical_numerical_model=True, prior_full_run_measurement_reused=True, new_throughput_benchmark_run=False,
        fixture_receipt_sha256=sha(FIXTURES), source_evidence_sha256=sha(SOURCE),
        inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in input_paths()})
    assert not FORECAST.exists()
    dump(FORECAST, result)
    print(json.dumps(result, indent=2), flush=True)


def execute(job, output):
    started = time.monotonic()
    check_inputs(job)
    dump(job/'pid.json', dict(pid=os.getpid(), recorded_utc=utc()))
    workers = str(json.loads((job/'manifest.json').read_text())['contract']['workers'])
    try:
        commands = (('simulation', ['run.py', '--output', str(output), '--workers', workers]),
                    ('audit', ['audit.py', str(output), '--workers', workers]),
                    ('figures', ['plot.py', str(output)]))
        for stage, command in commands:
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
    cap_cpus(8)
    if args.forecast:
        forecast()
        return
    if not re.fullmatch(r'[a-z0-9_]+', args.run_name): raise ValueError('Invalid run name')
    output, job = HERE/'runs'/args.run_name, HERE/'jobs'/args.run_name
    fixtures()
    source_evidence()
    estimate = json.loads(FORECAST.read_text())
    for rel, digest in estimate['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    assert estimate['fixture_receipt_sha256'] == sha(FIXTURES)
    assert estimate['source_evidence_sha256'] == sha(SOURCE)
    assert cap_cpus(8) == estimate['cpu_affinity'], 'CPU affinity differs from forecast'
    if args.child:
        execute(job, output)
        return
    if estimate['detached_required'] and not args.detach: raise ValueError('Forecast exceeds 600 seconds; detach required')
    if shutil.disk_usage(HERE).free < estimate['storage_with_reserve_bytes']: raise RuntimeError('Storage reserve unavailable')
    if output.exists(): raise FileExistsError(output)
    new_run(job, input_paths()+[FIXTURES, FORECAST], dict(experiment='E030', detached=args.detach,
        run_name=args.run_name, workers=estimate['workers'], forecast_seconds=estimate['forecast_seconds'],
        confirmation_of='E029', prior_cases_pooled=False))
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
