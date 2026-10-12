"""Launch the frozen full cohort once, after benchmark verification."""
import argparse
from dataclasses import asdict
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

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, sha, utc
from E015_functional_inheritance.audit import verify
from E031_renewal_durability import model
from E031_renewal_durability.workflow import fixtures

ANALYSIS = HERE/'analysis'
PREFLIGHT = ANALYSIS/'prelaunch_scientific_v1.json'
FORECAST = ANALYSIS/'forecast_v1.json'
NAME = 'durability_v1'


def inactive():
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if json.loads(p.read_text()).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    assert not (HERE/'jobs'/NAME).exists() and not (HERE/'runs'/NAME).exists()


def prepare():
    assert not PREFLIGHT.exists()
    affinity = cap_cpus(8); fixtures(); inactive()
    estimate = json.loads(FORECAST.read_text())
    assert estimate['capacity_pass'] and estimate['workers'] == 8 and estimate['cpu_affinity'] == affinity
    inputs = estimate['inputs_sha256']
    assert len(inputs) == 27
    for rel, digest in inputs.items(): assert sha(ROOT/rel) == digest, rel
    indexed = [FORECAST, ANALYSIS/'fixtures_v1.json', ANALYSIS/'fixtures_v1.log',
               ANALYSIS/'launch_verification_v1.json', ANALYSIS/'prelaunch_benchmark_v1.json']
    output_counts = {}
    for run in (HERE/'analysis/fixture_attempt1', HERE/'runs/benchmark_v1'):
        manifest = verify(run)
        complete = json.loads((run/'COMPLETE.json').read_text())
        audited = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
        assert audited['status'] == 'PASS' and audited['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audited['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audited['every_raw_array_commitment_replayed'] and audited['complete_descriptor_coverage_verified']
        assert manifest['inputs_sha256'] == inputs
        assert (audited['individual_observations'], audited['body_individual_observations']) == (
            (27552, 2048) if run.name == 'fixture_attempt1' else (13776, 1024))
        output_counts[run.name] = len(complete['outputs_sha256'])
        figures = HERE/'figures'/run.name/'provenance.json'
        picture = json.loads(figures.read_text())
        assert picture['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert picture['complete_sha256'] == sha(run/'COMPLETE.json')
        assert picture['summary_sha256'] == sha(run/'summary.json')
        assert picture['plot_code_sha256'] == sha(HERE/'plot.py')
        for name, digest in picture['outputs_sha256'].items(): assert sha(figures.parent/name) == digest
        indexed += [run/'manifest.json', run/'COMPLETE.json', run/'INDEPENDENT_AUDIT.json', figures]
    check_inputs(HERE/'analysis/fixture_suite_v1'); check_inputs(HERE/'jobs/benchmark_v1')
    benchmark = HERE/'runs/benchmark_v1'
    status_path = HERE/'jobs/benchmark_v1/status.json'
    status = json.loads(status_path.read_text())
    assert status['status'] == 'COMPLETE' and status['forecast_sha256'] == sha(FORECAST)
    assert status['scientific_complete_sha256'] == estimate['benchmark_complete_sha256'] == sha(benchmark/'COMPLETE.json')
    assert status['audit_sha256'] == estimate['benchmark_audit_sha256'] == sha(benchmark/'INDEPENDENT_AUDIT.json')
    assert status['figure_provenance_sha256'] == sha(HERE/'figures/benchmark_v1/provenance.json')
    assert estimate['fixture_receipt_sha256'] == sha(ANALYSIS/'fixtures_v1.json')
    source_bytes = sum(p.stat().st_size for p in benchmark.glob('source_*.npz'))
    case_bytes = sum(p.stat().st_size for p in benchmark.glob('*.npz') if not p.name.startswith('source_'))
    case_bytes += sum(p.stat().st_size for p in benchmark.glob('*.csv.gz'))
    total = sum(p.stat().st_size for p in benchmark.rglob('*') if p.is_file())
    assert (source_bytes, case_bytes, total) == (estimate['source_bytes'], estimate['per_case_bytes'], estimate['benchmark_total_bytes'])
    assert estimate['overhead_bytes'] == total-source_bytes-case_bytes
    assert estimate['forecast_seconds'] == 1.5*estimate['benchmark_workflow_seconds']*4*8*math.ceil(32/8)+120
    assert estimate['storage_with_reserve_bytes'] == math.ceil(1.5*32*(source_bytes+4*case_bytes+estimate['overhead_bytes']))+256*1024**2
    free = shutil.disk_usage(HERE).free
    assert free > estimate['storage_with_reserve_bytes']
    receipt = json.loads((ANALYSIS/'fixtures_v1.json').read_text())
    for rel, digest in receipt['fixture_artifacts_sha256'].items(): assert sha(ROOT/rel) == digest
    indexed.append(status_path)
    record = dict(status='PASS', utc=utc(), mode='prospective_renewal_durability',
        blocks=list(range(27000, 27032)), founders=128, lineages=512, workers=8,
        cpu_affinity=affinity, numerical_threads=1, config=asdict(model.CFG), cycle=asdict(model.CYCLE),
        panels=82, terminal_observations=1763328, body_observations=131072,
        verified_original_outputs=output_counts, inputs_sha256=inputs,
        receipts_sha256={str(p.relative_to(ROOT)):sha(p) for p in indexed},
        forecast_seconds=estimate['forecast_seconds'], storage_with_reserve_bytes=estimate['storage_with_reserve_bytes'],
        available_bytes=free, launcher_sha256=sha(__file__),
        benchmark_values_not_used_to_select_settings=True, no_scientific_cases_yet=True)
    dump(PREFLIGHT, record)
    print(json.dumps({k:record[k] for k in ('status', 'utc', 'lineages', 'workers', 'verified_original_outputs',
        'forecast_seconds', 'storage_with_reserve_bytes', 'available_bytes', 'launcher_sha256')}, indent=2), flush=True)


def launch():
    affinity = cap_cpus(8); fixtures(); inactive()
    preflight = json.loads(PREFLIGHT.read_text())
    assert preflight['status'] == 'PASS' and preflight['launcher_sha256'] == sha(__file__)
    assert preflight['cpu_affinity'] == affinity
    for rel, digest in {**preflight['inputs_sha256'], **preflight['receipts_sha256']}.items(): assert sha(ROOT/rel) == digest, rel
    assert shutil.disk_usage(HERE).free > preflight['storage_with_reserve_bytes']
    job, run = HERE/'jobs'/NAME, HERE/'runs'/NAME
    subprocess.run([sys.executable, '-B', str(HERE/'workflow.py'), '--mode', 'scientific', '--detach'], cwd=ROOT, check=True)
    started = json.loads((job/'launch.json').read_text())
    try:
        deadline = time.monotonic()+15
        while True:
            os.kill(started['pid'], 0)
            try: status = json.loads((job/'status.json').read_text())
            except (FileNotFoundError, json.JSONDecodeError): status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            logs = list(run.glob('worker_*.log'))
            if status.get('status') == 'RUNNING' and status.get('stage') == 'simulation' and (run/'manifest.json').exists() and len(logs) >= 8: break
            if time.monotonic() > deadline: raise TimeoutError('Startup not verified within 15 seconds')
            time.sleep(.5)
        check_inputs(job); check_inputs(run)
        m = json.loads((run/'manifest.json').read_text()); c = m['contract']
        assert c['blocks'] == preflight['blocks'] and c['mode'] == 'prospective_renewal_durability' and c['workers'] == 8
        assert c['cycle'] == preflight['cycle'] == dict(generations=16, read_steps=2048, settling_steps=256, write_steps=128)
        assert c['config'] == preflight['config'] == asdict(model.CFG)
        assert c['config']['recipients'] == 4
        assert c['conditions'] == list(model.CONDITIONS) and c['panels'] == [list(x) for x in model.PANELS]
        assert c['receivers'] == ['fixed_four', 'local_strength'] and len(c['panels']) == 82
        assert m['cpu_affinity'] == affinity and m['numerical_threads'] == 1
        assert m['inputs_sha256'] == preflight['inputs_sha256']
        assert not (run/'FAILED.json').exists() and os.getsid(started['pid']) == started['pid']
        proc = Path('/proc')/str(started['pid'])
        command = (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()
        assert str(HERE/'workflow.py') in command and '--child' in command and 'scientific' in command
        fields = dict(line.split(':', 1) for line in (proc/'status').read_text().splitlines())
        record = dict(status='PASS', verified_utc=utc(), launch_utc=started['utc'], pid=started['pid'],
            job_status=status, process_command=command,
            host_process={key:fields[key].strip() for key in ('Name', 'State', 'Pid', 'PPid', 'Threads', 'Cpus_allowed_list')},
            cpu_affinity=affinity, workers=8, numerical_threads=1, declared_blocks=32,
            started_worker_logs=len(logs), lineages=512, frozen_inputs_verified=27,
            forecast_seconds=preflight['forecast_seconds'],
            estimated_completion_utc=(datetime.fromisoformat(started['utc'])+timedelta(seconds=preflight['forecast_seconds'])).isoformat(),
            preflight_sha256=sha(PREFLIGHT), launcher_sha256=sha(__file__),
            automatic_polling_started=False, automatic_successor_started=False, scientific_outcomes_inspected=False)
        path = ANALYSIS/'scientific_launch_verification_v1.json'
        assert not path.exists(); dump(path, record)
        print(json.dumps(record, indent=2), flush=True)
    except BaseException:
        dump(ANALYSIS/'scientific_startup_failure_v1.json', dict(utc=utc(), launch=started,
            traceback=traceback.format_exc(), note='No automatic restart.'))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--prepare', action='store_true')
    if parser.parse_args().prepare: prepare()
    else: launch()
