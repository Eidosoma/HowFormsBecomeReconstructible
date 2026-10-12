"""Verify excluded evidence, then run one comparison under the frozen forecast."""
import argparse
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
HERE = Path(__file__).resolve().parents[1]; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, sha, utc
from E015_functional_inheritance.audit import verify
from E048_partial_rollback.workflow import technical


def load(p): return json.loads(p.read_text())


def inactive():
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('RUNNING', 'PREPARED')]
    assert not active, active
    assert not (HERE/'jobs/partial_v1').exists() and not (HERE/'runs/partial_v1').exists()


def prepare():
    affinity = cap_cpus(8); receipt = technical(); inactive(); check_inputs(HERE/'analysis/freeze_v1')
    f = load(HERE/'analysis/forecast_v1.json')
    assert f['capacity_pass'] and f['cpu_affinity'] == affinity and 1 <= f['workers'] <= 8
    assert f['inputs_sha256'] == receipt['inputs_sha256'] and len(f['inputs_sha256']) == 17
    assert receipt['tests'] == 12 and receipt['runner_sha256'] == sha(HERE/'analysis/run_technical.py')
    evidence = {}
    for name, cases in (('fixture_v1', 8), ('benchmark_v1', 4)):
        r = HERE/'runs'/name; m = verify(r); a = load(r/'INDEPENDENT_AUDIT.json')
        assert a['status'] == 'PASS' and a['cohort']['eligible'] == cases and a['individual_observations'] == 6*cases
        assert a['original_and_full_match_e047_byte_exactly'] and a['summaries_checked'] == 40
        assert a['complete_sha256'] == sha(r/'COMPLETE.json') and a['audit_code_sha256'] == sha(HERE/'audit.py')
        assert m['inputs_sha256'] == receipt['inputs_sha256']
        assert load(r/'summary.json')['status'] == 'TECHNICAL_ONLY'
        p = HERE/'figures'/name/'provenance.json'; picture = load(p)
        assert picture['audit_sha256'] == sha(r/'INDEPENDENT_AUDIT.json') and picture['summary_sha256'] == sha(r/'summary.json')
        assert picture['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in picture['outputs_sha256'].items(): assert sha(p.parent/rel) == digest
        for path in (r/'COMPLETE.json', r/'INDEPENDENT_AUDIT.json', p): evidence[str(path.relative_to(ROOT))] = sha(path)
    b = HERE/'runs/benchmark_v1'; check_inputs(HERE/'jobs/benchmark_v1')
    assert load(HERE/'jobs/benchmark_v1/status.json')['status'] == 'COMPLETE'
    assert f['benchmark_complete_sha256'] == sha(b/'COMPLETE.json') and f['benchmark_audit_sha256'] == sha(b/'INDEPENDENT_AUDIT.json')
    assert f['benchmark_run_bytes'] == sum(p.stat().st_size for p in b.rglob('*') if p.is_file())
    assert f['simulation_worker_seconds'] == load(b/'worker_900041.json')['seconds']
    assert f['audit_worker_seconds'] == load(b/'INDEPENDENT_AUDIT.json')['worker_seconds'][0]
    assert f['forecast_seconds'] == 3*(f['simulation_worker_seconds']+f['audit_worker_seconds'])*16*4*math.ceil(32/f['workers'])+120
    assert f['detached_required'] == (f['forecast_seconds'] > 600)
    assert f['storage_with_reserve_bytes'] == math.ceil(1.5*f['benchmark_run_bytes']*4*32)+128*1024**2
    available = shutil.disk_usage(HERE).free; assert available > f['storage_with_reserve_bytes']
    for rel, digest in load(HERE/'SOURCE_DATA.json')['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), launcher_sha256=sha(__file__), inputs_sha256=f['inputs_sha256'],
        forecast_sha256=sha(HERE/'analysis/forecast_v1.json'), technical_receipt_sha256=sha(HERE/'analysis/technical_v1.json'),
        evidence_sha256=evidence, forecast_seconds=f['forecast_seconds'], detached_required=f['detached_required'],
        storage_with_reserve_bytes=f['storage_with_reserve_bytes'], available_bytes=available, workers=f['workers'],
        cpu_affinity=affinity, numerical_threads=1, scientific_cases_not_yet_run=True,
        original_next_body_matches_e041_exactly=True, fixtures_and_benchmark_figures_inspected=True)
    dest = HERE/'analysis/prelaunch_scientific_v1.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps({k:result[k] for k in ('status', 'utc', 'forecast_seconds', 'detached_required', 'storage_with_reserve_bytes', 'available_bytes')}, indent=2), flush=True)


def launch():
    cap_cpus(8); technical(); inactive()
    pre = load(HERE/'analysis/prelaunch_scientific_v1.json')
    assert pre['status'] == 'PASS' and pre['launcher_sha256'] == sha(__file__)
    assert pre['forecast_sha256'] == sha(HERE/'analysis/forecast_v1.json')
    assert pre['technical_receipt_sha256'] == sha(HERE/'analysis/technical_v1.json')
    for rel, digest in {**pre['inputs_sha256'], **pre['evidence_sha256']}.items(): assert sha(ROOT/rel) == digest
    assert shutil.disk_usage(HERE).free > pre['storage_with_reserve_bytes']
    command = [sys.executable, '-B', str(HERE/'workflow.py'), '--mode', 'scientific']
    if pre['detached_required']: command.append('--detach')
    with (HERE/'analysis/scientific_v1.log').open('x') as log:
        subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
    job, run = HERE/'jobs/partial_v1', HERE/'runs/partial_v1'
    if not pre['detached_required']:
        status = load(job/'status.json'); assert status['status'] == 'COMPLETE'
        print(json.dumps(status, indent=2), flush=True); return
    start = load(job/'launch.json')
    try:
        deadline = time.monotonic()+15
        while True:
            os.kill(start['pid'], 0)
            try: status = load(job/'status.json')
            except (FileNotFoundError, json.JSONDecodeError): status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            logs = list(run.glob('worker_*.log'))
            if status.get('stage') == 'simulation' and (run/'manifest.json').exists() and len(logs) >= pre['workers']: break
            if time.monotonic() > deadline: raise TimeoutError('Bounded startup check exceeded 15 seconds')
            time.sleep(.5)
        check_inputs(job); check_inputs(run); m = load(run/'manifest.json'); c = m['contract']
        assert c['mode'] == 'scientific' and c['blocks'] == list(range(32000, 32032)) and c['workers'] == pre['workers']
        assert c['cycle'] == dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
        assert c['config']['recipients'] == 4 and c['variants'] == ['original', 'half_rollback', 'full_rollback']
        assert m['inputs_sha256'] == pre['inputs_sha256'] and m['cpu_affinity'] == pre['cpu_affinity'] and m['numerical_threads'] == 1
        assert os.getsid(start['pid']) == start['pid'] and not (run/'FAILED.json').exists()
        process = Path('/proc')/str(start['pid'])
        assert os.readlink(process/'fd/0') == '/dev/null'
        result = dict(status='PASS', utc=utc(), launch_utc=start['utc'], pid=start['pid'], job_status=status,
            workers=pre['workers'], numerical_threads=1, cpu_affinity=m['cpu_affinity'], started_worker_logs=len(logs),
            blocks=32, original_lineages=512, expected_eligible_cases=301, frozen_inputs_verified=17,
            forecast_seconds=pre['forecast_seconds'], estimated_completion_utc=(datetime.fromisoformat(start['utc'])+timedelta(seconds=pre['forecast_seconds'])).isoformat(),
            preflight_sha256=sha(HERE/'analysis/prelaunch_scientific_v1.json'), launcher_sha256=sha(__file__),
            automatic_polling_started=False, automatic_successor_started=False)
        dest = HERE/'analysis/scientific_launch_verification_v1.json'; assert not dest.exists(); dump(dest, result)
        print(json.dumps(result, indent=2), flush=True)
    except BaseException:
        dump(HERE/'analysis/scientific_startup_failure_v1.json', dict(utc=utc(), launch=start, traceback=traceback.format_exc(), automatic_restart=False)); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--prepare', action='store_true')
    p.add_argument('--figures-inspected', action='store_true')
    args = p.parse_args()
    if args.prepare:
        assert args.figures_inspected; prepare()
    else: launch()
