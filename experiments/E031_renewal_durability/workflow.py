"""Separate detached benchmark and scientific cohort, with no automatic transition."""
import argparse
from dataclasses import asdict
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
from E031_renewal_durability.run import input_paths

FIXTURES = HERE/'analysis/fixtures_v1.json'
FORECAST = HERE/'analysis/forecast_v1.json'
RESERVE = 256*1024**2


def fixtures():
    r = json.loads(FIXTURES.read_text())
    assert r['status'] == 'PASS' and r['tests'] == 9
    for rel, digest in r['inputs_sha256'].items(): assert sha(ROOT/rel) == digest, rel
    assert r['log_sha256'] == sha(HERE/'analysis/fixtures_v1.log')
    evidence = json.loads((HERE/'SOURCE_EVIDENCE.json').read_text())
    for rel, digest in evidence['provenance_sha256'].items(): assert sha(ROOT/rel) == digest, rel
    assert evidence['prior_cases_pooled'] is False


def forecast(run, seconds):
    """Partition source/overhead, which do not scale with recipient count."""
    assert not FORECAST.exists()
    receipt = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert receipt['status'] == 'PASS'
    source_bytes = sum(p.stat().st_size for p in run.glob('source_*.npz'))
    per_case_bytes = sum(p.stat().st_size for p in run.glob('*.npz') if not p.name.startswith('source_'))
    per_case_bytes += sum(p.stat().st_size for p in run.glob('*.csv.gz'))
    total_bytes = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
    overhead = total_bytes-source_bytes-per_case_bytes
    affinity = cap_cpus(8)
    workers = min(8, len(affinity) or 1)
    predicted = 1.5*seconds*4*8*math.ceil(32/workers)+120
    # Overhead *32 covers block means/report expansion without multiplying it by R.
    storage = math.ceil(1.5*32*(source_bytes+4*per_case_bytes+overhead))+RESERVE
    free = shutil.disk_usage(HERE).free
    result = dict(created_utc=utc(), benchmark=str(run.relative_to(ROOT)), benchmark_workflow_seconds=seconds,
        benchmark_complete_sha256=sha(run/'COMPLETE.json'), benchmark_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        benchmark_total_bytes=total_bytes, source_bytes=source_bytes, per_case_bytes=per_case_bytes, overhead_bytes=overhead,
        forecast_seconds=predicted, runtime_formula='1.5*benchmark_workflow_seconds*4*8*ceil(32/workers)+120',
        storage_with_reserve_bytes=storage, storage_formula='ceil(1.5*32*(source_bytes+4*per_case_bytes+overhead_bytes))+256MiB',
        reserve_bytes=RESERVE, available_bytes=free, capacity_pass=storage <= free,
        workers=workers, cpu_affinity=affinity, numerical_threads=1, detached_required=predicted > 600,
        fixture_receipt_sha256=sha(FIXTURES), inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in input_paths()},
        technical_results_not_used_to_select_scientific_settings=True, scientific_cohort_automatically_started=False)
    dump(FORECAST, result)
    return result


def execute(job, output, mode):
    started = time.monotonic(); check_inputs(job)
    dump(job/'pid.json', dict(pid=os.getpid(), recorded_utc=utc()))
    contract = json.loads((job/'manifest.json').read_text())['contract']
    try:
        sim = ['run.py', '--output', str(output), '--workers', str(contract['workers'])]
        if mode == 'benchmark': sim.append('--benchmark')
        commands = (('simulation', sim), ('audit', ['audit.py', str(output), '--workers', str(contract['workers'])]),
                    ('figures', ['plot.py', str(output)]))
        for stage, command in commands:
            dump(job/'status.json', dict(status='RUNNING', stage=stage, utc=utc(), pid=os.getpid()))
            print('Starting', stage, flush=True)
            with (job/'workflow.log').open('a') as log:
                subprocess.run([sys.executable, '-B', str(HERE/command[0]), *command[1:]], cwd=ROOT,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        elapsed = time.monotonic()-started
        if mode == 'benchmark': forecast(output, elapsed)
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-started, mode=mode,
            scientific_complete_sha256=sha(output/'COMPLETE.json'), audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'),
            figure_provenance_sha256=sha(HERE/'figures'/output.name/'provenance.json'),
            forecast_sha256=sha(FORECAST), automatic_successor_started=False))
        print('Complete:', output, flush=True)
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=('benchmark', 'scientific'))
    parser.add_argument('--detach', action='store_true')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args(); affinity = cap_cpus(8); fixtures()
    name = 'benchmark_v1' if args.mode == 'benchmark' else 'durability_v1'
    output, job = HERE/'runs'/name, HERE/'jobs'/name
    if args.child:
        execute(job, output, args.mode); return
    if not args.detach: raise ValueError('Both declared forecasts exceed 600 seconds; detach required')
    if args.mode == 'benchmark':
        estimate = dict(forecast_seconds=900, workers=1, storage_with_reserve_bytes=128*1024**2)
        extra = [FIXTURES]
    else:
        estimate = json.loads(FORECAST.read_text())
        assert estimate['capacity_pass']
        assert estimate['cpu_affinity'] == affinity
        for rel, digest in estimate['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
        assert estimate['fixture_receipt_sha256'] == sha(FIXTURES)
        benchmark = ROOT/estimate['benchmark']
        assert estimate['benchmark_complete_sha256'] == sha(benchmark/'COMPLETE.json')
        assert estimate['benchmark_audit_sha256'] == sha(benchmark/'INDEPENDENT_AUDIT.json')
        extra = [FIXTURES, FORECAST]
    if shutil.disk_usage(HERE).free < estimate['storage_with_reserve_bytes']: raise RuntimeError('Storage reserve unavailable')
    if output.exists(): raise FileExistsError(output)
    new_run(job, input_paths()+extra, dict(experiment='E031', mode=args.mode, detached=True,
        workers=estimate['workers'], forecast_seconds=estimate['forecast_seconds'], prior_cases_pooled=False))
    dump(job/'status.json', dict(status='PREPARED', utc=utc()))
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', '--mode', args.mode]
    with (job/'launcher.log').open('x') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    dump(job/'launch.json', dict(pid=process.pid, utc=utc(), command=command, job=str(job)))
    print('Detached PID', process.pid, 'status:', job/'status.json', flush=True)


if __name__ == '__main__': main()
