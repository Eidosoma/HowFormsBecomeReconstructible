"""Launch one approved stage with a bounded host startup check; no ongoing polling."""
from datetime import datetime, timedelta
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E029_maturing_renewal.workflow import fixtures


def main():
    fixtures()
    analysis = HERE/'analysis'
    preflight_path = analysis/'prelaunch_verification_v1.json'
    forecast_path = analysis/'forecast_v1.json'
    preflight = json.loads(preflight_path.read_text())
    forecast = json.loads(forecast_path.read_text())
    assert preflight['status'] == 'PASS'
    assert preflight['operational_launcher_sha256'] == sha(__file__)
    assert preflight['forecast_sha256'] == sha(forecast_path)
    assert preflight['verification_code_sha256'] == sha(analysis/'verify_prelaunch.py')
    assert shutil.disk_usage(HERE).free > forecast['storage_with_reserve_bytes']
    for rel, digest in forecast['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if json.loads(p.read_text()).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    name = 'maturing_v1'
    job, run = HERE/'jobs'/name, HERE/'runs'/name
    assert not job.exists() and not run.exists()
    command = [sys.executable, '-B', str(HERE/'workflow.py'), '--detach', '--run-name', name]
    subprocess.run(command, cwd=ROOT, check=True)
    launch = json.loads((job/'launch.json').read_text())
    try:
        deadline = time.monotonic()+15
        while True:
            os.kill(launch['pid'], 0)
            try: status = json.loads((job/'status.json').read_text())
            except (FileNotFoundError, json.JSONDecodeError): status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            logs = list(run.glob('worker_*.log'))
            if status.get('status') == 'RUNNING' and status.get('stage') == 'simulation' and (run/'manifest.json').exists() and len(logs) >= forecast['workers']:
                break
            if time.monotonic() > deadline: raise TimeoutError('Startup not verified within 15 seconds')
            time.sleep(.5)
        check_inputs(job); check_inputs(run)
        manifest = json.loads((run/'manifest.json').read_text())
        assert manifest['contract']['blocks'] == list(range(25000, 25032))
        assert manifest['contract']['mode'] == 'prospective_maturing_renewal'
        assert manifest['contract']['workers'] == forecast['workers']
        assert manifest['numerical_threads'] == 1
        assert manifest['cpu_affinity'] == forecast['cpu_affinity']
        assert len(manifest['inputs_sha256']) == 23
        assert manifest['contract']['cycle'] == dict(generations=3, read_steps=2048, settling_steps=256, write_steps=128)
        assert manifest['contract']['config']['recipients'] == 4
        assert len(manifest['contract']['conditions']) == 10
        assert manifest['contract']['receivers'] == ['fixed_four', 'local_strength']
        assert len(manifest['contract']['panels']) == 42
        assert not (run/'FAILED.json').exists()
        proc = Path('/proc')/str(launch['pid'])
        process_command = (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()
        assert str(HERE/'workflow.py') in process_command and '--child' in process_command
        assert os.getsid(launch['pid']) == launch['pid']
        fields = dict(line.split(':', 1) for line in (proc/'status').read_text().splitlines())
        host_process = {key: fields[key].strip() for key in ('Name', 'State', 'Pid', 'PPid', 'Threads', 'Cpus_allowed_list')}
        estimate = datetime.fromisoformat(launch['utc'])+timedelta(seconds=forecast['forecast_seconds'])
        evidence = dict(status='PASS', verified_utc=utc(), launch_utc=launch['utc'], pid=launch['pid'],
            host_process=host_process, process_command=process_command, job_status=status,
            declared_blocks=len(manifest['contract']['blocks']),
            started_worker_logs=len(logs), workers=forecast['workers'], numerical_threads=1,
            cpu_affinity=manifest['cpu_affinity'], frozen_job_and_run_inputs_verified=True,
            forecast_seconds=forecast['forecast_seconds'], estimated_completion_utc=estimate.isoformat(),
            forecast_sha256=sha(forecast_path), preflight_sha256=sha(preflight_path),
            operational_launcher_sha256=sha(__file__), automatic_polling_started=False,
            automatic_successor_started=False, scientific_outcomes_inspected=False)
        with (analysis/'launch_verification_v1.json').open('x') as handle:
            json.dump(evidence, handle, indent=2)
        print(json.dumps(evidence, indent=2), flush=True)
    except BaseException:
        with (analysis/'startup_check_failure_v1.json').open('x') as handle:
            json.dump(dict(utc=utc(), launch=launch, traceback=traceback.format_exc(),
                note='Startup checker failed; no automatic restart or scientific-status change.'), handle, indent=2)
        raise


if __name__ == '__main__':
    main()
