"""Freeze, qualify, launch or explicitly resume; never automatically poll a run."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from bridge import ROOT, P, ev, read
import ledger


def sources():
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.c')]
    paths += [ROOT/name for name in ('protocol.json', 'FROZEN_MODELS.json', 'BUILD.json',
                                    'SOURCE_MANIFEST.json', 'EXPOSURE_AND_DECISIONS.json')]
    for name in ('context', 'inherited', 'build'):
        paths += [p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    if any(p.is_symlink() for p in paths):
        raise ValueError('Frozen source symlinks are not permitted')
    return sorted(set(paths))


def source_hashes():
    return {str(p.relative_to(ROOT)): ev.sha(p) for p in sources()}


def verify_receipt(path):
    receipt = read(path)
    if receipt['status'] != 'PASS' or receipt['source_sha256'] != source_hashes():
        raise ValueError('Qualification missing, failed or stale: '+str(path))
    return receipt


def snapshot(folder, extra=()):
    folder.mkdir(parents=True, exist_ok=False)
    for source in sources()+[ROOT/name for name in extra]:
        target = folder/source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    hashes = {str(p.relative_to(folder)): ev.sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    ledger.atomic_json(folder/'INPUTS.json', dict(utc=ev.utc(), sha256=hashes))


def environment(temporary):
    temporary.mkdir(parents=True, exist_ok=True)
    result = os.environ.copy()
    result.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  MKL_NUM_THREADS='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(temporary))
    return result


def validate_name(name):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name):
        raise ValueError('Use a unique lowercase alphanumeric/underscore job name')


def qualify(name):
    validate_name(name)
    job = ROOT/'jobs'/name
    job.mkdir(parents=True, exist_ok=False)
    run = ROOT/'runs'/name
    run.mkdir(parents=True, exist_ok=False)
    initial = source_hashes()
    snapshot(job/'inputs')
    started = time.monotonic()
    try:
        sys.path.insert(0, str(ROOT/'inherited/reference'))
        import cpu_preflight
        admission = cpu_preflight.collect()
        ledger.atomic_json(run/'CPU_ADMISSION.json', admission)
        if not admission['within_limit']:
            raise RuntimeError('Shared CPU budget has no free slot')
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--basetemp', str(run/'pytest_tmp'), str(job/'inputs/test_outcome.py')]
        ledger.atomic_json(job/'JOB.json', dict(utc=ev.utc(), mode='lightweight_qualification',
            command=command, input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),
            wall_ceiling_seconds=P['resources']['qualification_wall_ceiling_seconds']))
        ev.status(run, status='RUNNING', stage='lightweight_qualification')
        with (run/'pytest.log').open('xb') as log:
            result = subprocess.run(command, cwd=job/'inputs', env=environment(run/'tmp'),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                timeout=P['resources']['qualification_wall_ceiling_seconds'], check=False)
        if result.returncode:
            raise RuntimeError('Lightweight qualification failed; inspect the preserved pytest.log')
        if source_hashes() != initial:
            raise ValueError('Working source changed during qualification')
        complete = dict(utc=ev.utc(), status='PASS', source_sha256=initial,
            input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),
            log_sha256=ev.sha(run/'pytest.log'), wall_seconds=time.monotonic()-started,
            scope='Reduced-step synthetic fixtures and failure injection; native qualification still required.',
            new_scientific_outcomes=0)
        ledger.atomic_json(run/'COMPLETE.json', complete)
        ledger.atomic_json(ROOT/'QUALIFICATION.json', complete)
        ev.status(run, status='COMPLETE', stage='lightweight_qualification')
        print(dict(status='PASS', job=name, wall_seconds=complete['wall_seconds']), flush=True)
        return complete
    except BaseException as error:
        ledger.atomic_json(run/'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__,
            message=str(error), traceback=traceback.format_exc()))
        ev.status(run, status='FAILED', stage='lightweight_qualification')
        raise


def launch(mode, name, resume_job=None):
    validate_name(name)
    job = ROOT/'jobs'/name
    job.mkdir(parents=True, exist_ok=False)
    if resume_job:
        validate_name(resume_job)
        previous = read(ROOT/'jobs'/resume_job/'JOB.json')
        if previous['mode'] != mode:
            raise ValueError('Resume mode differs')
        inputs = Path(previous['inputs'])
        run = Path(previous['output'])
        if ev.sha(inputs/'INPUTS.json') != previous['input_manifest_sha256']:
            raise ValueError('Original input manifest changed')
        if (run/'COMPLETE.json').exists():
            raise ValueError('The run has already completed')
        extras = ['--resume']
    else:
        verify_receipt(ROOT/'QUALIFICATION.json')
        extra = ['QUALIFICATION.json']
        if mode == 'outcome':
            verify_receipt(ROOT/'NATIVE_QUALIFICATION.json')
            extra.append('NATIVE_QUALIFICATION.json')
        inputs = job/'inputs'
        snapshot(inputs, extra)
        run = ROOT/'runs'/name
        if run.exists():
            raise FileExistsError(run)
        extras = []
    command = [sys.executable, str(inputs/'execute.py'), '--mode', mode, '--output', str(run), *extras]
    configuration = dict(utc=ev.utc(), mode=mode, command=command, inputs=str(inputs), output=str(run),
        input_manifest_sha256=ev.sha(inputs/'INPUTS.json'), resume_of=resume_job,
        forecast_seconds=P['resources']['native_qualification_forecast_seconds' if mode == 'native_qualification' else 'measured_forecast_outcome_seconds'],
        automatic_polling=False, automatic_retry=False, automatic_successor=False,
        workers=1, numerical_threads=1)
    ledger.atomic_json(job/'JOB.json', configuration)
    with (job/'worker.log').open('xb') as log:
        process = subprocess.Popen(command, cwd=inputs, env=environment(job/'tmp'),
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    ledger.atomic_json(job/'PID.json', dict(utc=ev.utc(), pid=process.pid))
    time.sleep(3.)  # Exactly one startup check, never a progress poll.
    exitcode = process.poll()
    status = read(run/'STATUS.json') if (run/'STATUS.json').exists() else None
    startup = dict(utc=ev.utc(), pid=process.pid, exitcode=exitcode,
                   session_leader=os.getsid(process.pid) == process.pid if exitcode is None else None,
                   durable_status=status, subsequent_automatic_polling=False)
    ledger.atomic_json(job/'STARTUP.json', startup)
    print(dict(job=name, mode=mode, pid=process.pid, exitcode=exitcode,
               status=status, forecast_seconds=configuration['forecast_seconds']), flush=True)
    if exitcode is not None and exitcode != 0:
        raise RuntimeError('Detached process failed its single startup check; no retry')


def close_native(name):
    """Called only after the user requests a status/closeout, never by launch."""
    validate_name(name)
    job = read(ROOT/'jobs'/name/'JOB.json')
    if job['mode'] != 'native_qualification':
        raise ValueError('Native qualification job required')
    inputs, run = Path(job['inputs']), Path(job['output'])
    complete = read(run/'COMPLETE.json')
    manifest = read(inputs/'INPUTS.json')
    for relative, digest in manifest['sha256'].items():
        if ev.sha(ledger.child(inputs, relative)) != digest:
            raise ValueError('Qualified input changed')
    current = source_hashes()
    if any(manifest['sha256'].get(name) != digest for name, digest in current.items()):
        raise ValueError('Current source differs from completed native qualification')
    if (complete['status'] != 'COMPLETE' or complete['mode'] != 'native_qualification'
        or complete['scientific_future_outcomes'] != 0 or complete['legacy']['status'] != 'PASS'
        or complete['result']['case_regimes'] != 8 or not complete['result']['independent_analysis_verified']
        or complete['binding'] != ev.sha(inputs/'INPUTS.json')):
        raise ValueError('Native completion requirements not met')
    for path in (run/'units').rglob('COMMIT.json'):
        ledger.verify(path.parent)
    ledger.referenced(run, complete['result']['final_reference'])
    ledger.referenced(run, complete['legacy']['reference'])
    receipt = dict(utc=ev.utc(), status='PASS', source_sha256=current,
        job=name, complete_sha256=ev.sha(run/'COMPLETE.json'),
        input_manifest_sha256=ev.sha(inputs/'INPUTS.json'),
        wall_seconds=complete['wall_seconds'], new_scientific_outcomes=0,
        scope='Full native orchestration on four synthetic packets, plus exact legacy g14 replay; engineering qualification only.')
    ledger.atomic_json(ROOT/'NATIVE_QUALIFICATION.json', receipt)
    print(dict(status='PASS', job=name, scientific_outcome_job_started=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['qualify', 'launch-native', 'close-native', 'launch-outcome', 'resume'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--resume-job')
    arguments = parser.parse_args()
    if arguments.action == 'qualify':
        qualify(arguments.name)
    elif arguments.action == 'close-native':
        close_native(arguments.name)
    elif arguments.action == 'resume':
        if not arguments.resume_job:
            parser.error('--resume-job is required')
        saved_job = read(ROOT/'jobs'/arguments.resume_job/'JOB.json')
        launch(saved_job['mode'], arguments.name, arguments.resume_job)
    else:
        launch('native_qualification' if arguments.action == 'launch-native' else 'outcome', arguments.name)
