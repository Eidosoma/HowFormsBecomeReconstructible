"""Launch the verified benchmark and check startup once; no ongoing monitor."""
from datetime import datetime, timedelta
import json
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
from common import check_inputs, sha, utc
from E027_selective_renewal.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    fixtures()
    analysis = HERE/'analysis'
    forecast_path = analysis/'benchmark_forecast_v1.json'
    preflight_path = analysis/'prebenchmark_verification_v1.json'
    forecast, preflight = load(forecast_path), load(preflight_path)
    assert preflight['status'] == 'PASS'
    assert preflight['forecast_sha256'] == sha(forecast_path)
    assert preflight['operational_launcher_sha256'] == sha(Path(__file__))
    assert preflight['verification_code_sha256'] == sha(analysis/'prepare_benchmark.py')
    assert forecast['fixture_receipt_sha256'] == sha(analysis/'fixtures_v1.json')
    for rel, digest in forecast['inputs_sha256'].items():
        assert sha(ROOT/rel) == digest
    assert shutil.disk_usage(HERE).free > forecast['storage_with_reserve_bytes']
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    job, run = HERE/'jobs/benchmark_v1', HERE/'runs/benchmark_v1'
    assert not job.exists() and not run.exists()
    subprocess.run([sys.executable, '-B', str(HERE/'workflow.py'), '--benchmark', '--detach'], cwd=ROOT, check=True)
    launch = load(job/'launch.json')
    try:
        deadline = time.monotonic()+15
        while True:
            os.kill(launch['pid'], 0)
            try:
                status = load(job/'status.json')
            except (FileNotFoundError, json.JSONDecodeError):
                status = {}
            if status.get('status') == 'FAILED':
                raise RuntimeError(status)
            logs = list(run.glob('worker_*.log'))
            if status.get('status') == 'RUNNING' and status.get('stage') == 'simulation' and (run/'manifest.json').exists() and len(logs) == 1:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Startup not verified within 15 seconds')
            time.sleep(.5)
        check_inputs(job); check_inputs(run)
        manifest = load(run/'manifest.json')
        contract = manifest['contract']
        assert contract['mode'] == 'technical' and contract['blocks'] == [900027]
        assert contract['workers'] == 1 and contract['config']['recipients'] == 1
        assert contract['cycle']['generations'] == 3
        assert len(contract['panels']) == 34 and len(manifest['inputs_sha256']) == 22
        assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == forecast['cpu_affinity']
        assert not (run/'FAILED.json').exists()
        proc = Path('/proc')/str(launch['pid'])
        command = (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()
        assert str(HERE/'workflow.py') in command and '--child' in command
        assert os.getsid(launch['pid']) == launch['pid']
        fields = dict(line.split(':', 1) for line in (proc/'status').read_text().splitlines())
        evidence = dict(status='PASS', verified_utc=utc(), launch_utc=launch['utc'], pid=launch['pid'],
            host_process={key: fields[key].strip() for key in ('Name', 'State', 'Pid', 'PPid', 'Threads', 'Cpus_allowed_list')},
            process_command=command, job_status=status, workers=1, numerical_threads=1,
            cpu_affinity=manifest['cpu_affinity'], frozen_job_and_run_inputs_verified=True,
            declared_blocks=1, started_worker_logs=len(logs), panels=34,
            forecast_seconds=forecast['forecast_seconds'],
            estimated_completion_utc=(datetime.fromisoformat(launch['utc'])+timedelta(seconds=forecast['forecast_seconds'])).isoformat(),
            forecast_sha256=sha(forecast_path), preflight_sha256=sha(preflight_path),
            operational_launcher_sha256=sha(Path(__file__)), automatic_polling_started=False,
            scientific_cohort_started=False, automatic_successor_started=False)
        with (analysis/'benchmark_launch_verification_v1.json').open('x') as handle:
            json.dump(evidence, handle, indent=2, allow_nan=False)
        print(json.dumps(evidence, indent=2), flush=True)
    except BaseException:
        with (analysis/'benchmark_startup_failure_v1.json').open('x') as handle:
            json.dump(dict(utc=utc(), launch=launch, traceback=traceback.format_exc(),
                note='No automatic restart; preserve the existing job.'), handle, indent=2)
        raise


if __name__ == '__main__':
    main()
