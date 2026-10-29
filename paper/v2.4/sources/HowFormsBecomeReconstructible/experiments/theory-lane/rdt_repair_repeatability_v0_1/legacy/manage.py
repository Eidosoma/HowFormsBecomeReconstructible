"""Freeze, qualify, benchmark and explicitly launch a single bounded pilot."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from study import ROOT, C, ev, read, require, ledger, admission


def sources():
    files = list(ROOT.glob('*.py'))
    files += [ROOT / n for n in ('protocol.json', 'SOURCE_BINDINGS.json', 'PROTOCOL.md', 'EXPOSURE_AND_DECISIONS.json')]
    for directory in ('native', 'repair_source', 'context'):
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return sorted(files)


def hashes():
    return {str(p.relative_to(ROOT)): ev.sha(p) for p in sources()}


def snapshot(folder, extra=()):
    folder.mkdir(parents=True, exist_ok=False)
    for source in sources() + [ROOT / n for n in extra]:
        require(not source.is_symlink(), 'No snapshot symlinks')
        target = folder / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    entries = {str(p.relative_to(folder)): ev.sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    ev.write(folder / 'INPUTS.json', dict(utc=ev.utc(), sha256=entries))


def environment(tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(tmp))
    return env


def qualify(name):
    job = ROOT / 'jobs' / name
    job.mkdir(parents=True, exist_ok=False)
    output = ROOT / 'runs' / name
    output.mkdir(parents=True, exist_ok=False)
    frozen = hashes()
    snapshot(job / 'inputs')
    start = time.monotonic()
    ev.write(job / 'JOB.json', dict(utc=ev.utc(), mode='qualification_and_disposable_benchmark',
        input_manifest_sha256=ev.sha(job / 'inputs/INPUTS.json'), new_scientific_outcomes=0))
    try:
        admitted = admission()
        ev.write(output / 'CPU_ADMISSION.json', admitted)
        require(admitted['within_limit'], 'No shared CPU slot; no retry')
        ev.status(output, status='RUNNING', stage='qualification')
        tests = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'pytest_tmp'), str(job / 'inputs/test_study.py')]
        with (output / 'pytest.log').open('xb') as log:
            proc = subprocess.run(tests, cwd=job / 'inputs', env=environment(output / 'tmp'), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, timeout=C['resources']['qualification_wall_seconds'], check=False)
        require(proc.returncode == 0, 'Qualification failed; inspect preserved pytest.log')
        ev.status(output, status='RUNNING', stage='disposable_full_native_benchmark')
        command = [sys.executable, str(job / 'inputs/benchmark.py'), '--output', str(output / 'benchmark')]
        with (output / 'benchmark.log').open('xb') as log:
            proc = subprocess.run(command, cwd=job / 'inputs', env=environment(output / 'tmp'), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, timeout=C['resources']['benchmark_wall_seconds'], check=False)
        require(proc.returncode == 0, 'Benchmark failed; preserve attempt')
        benchmark = read(output / 'benchmark/COMPLETE.json')
        require(benchmark['forecast_seconds'] < C['resources']['hard_wall_seconds'], 'Measured pilot exceeds one-hour cap; do not launch')
        require(hashes() == frozen, 'Source changed during qualification')
        result = dict(utc=ev.utc(), status='PASS', source_sha256=frozen,
            wall_seconds=time.monotonic() - start, forecast_seconds=benchmark['forecast_seconds'],
            input_manifest_sha256=ev.sha(job / 'inputs/INPUTS.json'), pytest_log_sha256=ev.sha(output / 'pytest.log'),
            benchmark_complete_sha256=ev.sha(output / 'benchmark/COMPLETE.json'),
            new_scientific_outcomes=0, native_qualification='Both arms and both regimes over all nineteen reads on disposable inputs; separate flat dynamics and optimizer.')
        ledger.atomic_json(output / 'COMPLETE.json', result)
        ledger.atomic_json(ROOT / 'QUALIFICATION.json', result)
        ev.status(output, status='COMPLETE', stage='qualification')
        print(dict(status='PASS', forecast_seconds=result['forecast_seconds'], wall_seconds=result['wall_seconds']), flush=True)
    except BaseException as error:
        ev.write(output / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        ev.status(output, status='FAILED', stage='qualification')
        raise


def launch(name):
    qualification = read(ROOT / 'QUALIFICATION.json')
    require(qualification['status'] == 'PASS' and qualification['source_sha256'] == hashes(), 'Current passing qualification required')
    require(qualification['forecast_seconds'] < 3600 and C['resources']['hard_wall_seconds'] == 3600, 'One-hour cap required')
    require(shutil.disk_usage(ROOT).free > C['resources']['minimum_free_disk_bytes'], 'Insufficient disk')
    admitted = admission()
    require(admitted['within_limit'], 'No shared CPU slot; no retry')
    job = ROOT / 'jobs' / name
    job.mkdir(parents=True, exist_ok=False)
    snapshot(job / 'inputs', ['QUALIFICATION.json'])
    output = ROOT / 'runs' / name
    require(not output.exists(), 'Output attempt already exists')
    ev.write(job / 'CPU_ADMISSION.json', admitted)
    command = [sys.executable, str(job / 'inputs/run.py'), '--output', str(output)]
    ev.write(job / 'JOB.json', dict(utc=ev.utc(), command=command, output=str(output),
        input_manifest_sha256=ev.sha(job / 'inputs/INPUTS.json'), forecast_seconds=qualification['forecast_seconds'],
        hard_wall_seconds=3600, workers=1, numerical_threads=1, automatic_polling=False,
        automatic_retry=False, automatic_successor=False))
    with (job / 'worker.log').open('xb') as log:
        process = subprocess.Popen(command, cwd=job / 'inputs', env=environment(job / 'tmp'),
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    ev.write(job / 'PID.json', dict(utc=ev.utc(), pid=process.pid))
    time.sleep(10.)
    exitcode = process.poll()
    startup = dict(utc=ev.utc(), pid=process.pid, exitcode=exitcode,
        session_leader=os.getsid(process.pid) == process.pid if exitcode is None else None,
        status=read(output / 'STATUS.json') if (output / 'STATUS.json').exists() else None,
        subsequent_automatic_polling=False)
    ev.write(job / 'STARTUP.json', startup)
    print(startup, flush=True)
    require(exitcode is None or exitcode == 0, 'Pilot failed startup; no automatic retry')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('qualify', 'launch'))
    p.add_argument('--name', required=True)
    args = p.parse_args()
    require(args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in args.name), 'Simple unique attempt name required')
    (qualify if args.action == 'qualify' else launch)(args.name)
