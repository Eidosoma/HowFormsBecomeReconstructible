"""Launch only the excluded benchmark; bounded startup verification, no polling."""
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
from common import cap_cpus, check_inputs, dump, sha, utc
from E031_renewal_durability.workflow import fixtures
from E015_functional_inheritance.audit import verify


def main():
    affinity = cap_cpus(8); fixtures()
    analysis = HERE/'analysis'
    fixture = analysis/'fixture_attempt1'
    verify(fixture)
    audited = json.loads((fixture/'INDEPENDENT_AUDIT.json').read_text())
    assert audited['status'] == 'PASS'
    assert audited['complete_sha256'] == sha(fixture/'COMPLETE.json')
    assert audited['individual_observations'] == 27552 and audited['body_individual_observations'] == 2048
    figures = HERE/'figures/fixture_attempt1/provenance.json'
    picture = json.loads(figures.read_text())
    assert picture['audit_sha256'] == sha(fixture/'INDEPENDENT_AUDIT.json')
    for name, digest in picture['outputs_sha256'].items(): assert sha(figures.parent/name) == digest
    source = json.loads((analysis/'fixtures_v1.json').read_text())
    for rel, digest in source['fixture_artifacts_sha256'].items(): assert sha(ROOT/rel) == digest
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if json.loads(p.read_text()).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    assert shutil.disk_usage(HERE).free > 128*1024**2
    name = 'benchmark_v1'
    job, run = HERE/'jobs'/name, HERE/'runs'/name
    assert not job.exists() and not run.exists()
    assert not (analysis/'launch_verification_v1.json').exists()
    preflight = dict(status='PASS', utc=utc(), mode='technical_benchmark', block=900031,
        expected_seconds_upper_bound=900, fixture_receipt_sha256=sha(analysis/'fixtures_v1.json'),
        fixture_audit_sha256=sha(fixture/'INDEPENDENT_AUDIT.json'), fixture_figures_sha256=sha(figures),
        frozen_inputs=len(source['inputs_sha256']), cpu_affinity=affinity, workers=1, numerical_threads=1,
        available_bytes=shutil.disk_usage(HERE).free, launcher_sha256=sha(__file__),
        no_experiment_jobs_active=True, automatic_successor=False)
    path = analysis/'prelaunch_benchmark_v1.json'
    assert not path.exists(); dump(path, preflight)
    subprocess.run([sys.executable, '-B', str(HERE/'workflow.py'), '--mode', 'benchmark', '--detach'], cwd=ROOT, check=True)
    launch = json.loads((job/'launch.json').read_text())
    try:
        deadline = time.monotonic()+15
        while True:
            os.kill(launch['pid'], 0)
            try: status = json.loads((job/'status.json').read_text())
            except (FileNotFoundError, json.JSONDecodeError): status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            if status.get('stage') == 'simulation' and (run/'manifest.json').exists() and (run/'worker_900031.log').exists(): break
            if time.monotonic() > deadline: raise TimeoutError('Startup not verified within 15 seconds')
            time.sleep(.5)
        check_inputs(job); check_inputs(run)
        manifest = json.loads((run/'manifest.json').read_text())
        c = manifest['contract']
        assert c['blocks'] == [900031] and c['mode'] == 'technical_benchmark' and c['workers'] == 1
        assert c['cycle'] == dict(generations=16, read_steps=256, settling_steps=32, write_steps=128)
        assert c['config']['recipients'] == 1 and c['config']['teach_steps'] == 512
        assert c['config']['capture_steps'] == 128 and c['config']['observe_steps'] == 32
        assert len(c['conditions']) == 10 and len(c['panels']) == 82
        assert manifest['cpu_affinity'] == affinity and manifest['numerical_threads'] == 1
        assert len(manifest['inputs_sha256']) == len(source['inputs_sha256'])
        assert os.getsid(launch['pid']) == launch['pid']
        proc = Path('/proc')/str(launch['pid'])
        command = (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()
        assert str(HERE/'workflow.py') in command and '--child' in command and 'benchmark' in command
        evidence = dict(status='PASS', verified_utc=utc(), launch_utc=launch['utc'], pid=launch['pid'],
            job_status=status, process_command=command, cpu_affinity=affinity, workers=1,
            frozen_job_and_run_inputs_verified=True, forecast_upper_bound_seconds=900,
            estimated_completion_upper_bound_utc=(datetime.fromisoformat(launch['utc'])+timedelta(seconds=900)).isoformat(),
            preflight_sha256=sha(path), launcher_sha256=sha(__file__), automatic_polling_started=False,
            automatic_successor_started=False, scientific_outcomes_inspected=False)
        dump(analysis/'launch_verification_v1.json', evidence)
        print(json.dumps(evidence, indent=2), flush=True)
    except BaseException:
        dump(analysis/'startup_check_failure_v1.json', dict(utc=utc(), launch=launch,
            traceback=traceback.format_exc(), note='No automatic restart.'))
        raise


if __name__ == '__main__': main()
