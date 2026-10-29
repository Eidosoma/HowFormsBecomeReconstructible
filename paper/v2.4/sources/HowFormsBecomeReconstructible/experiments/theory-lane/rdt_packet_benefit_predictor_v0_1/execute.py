"""One short qualification and development job; never launches new futures."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from core import ROOT, require
from data import ev, read


def sources():
    values = list(ROOT.glob('*.py'))
    values += [ROOT / n for n in ('protocol.json', 'SOURCE_BINDINGS.json', 'PROTOCOL.md')]
    for directory in ('support', 'context'):
        values += [p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return sorted(values)


def main(name):
    job = ROOT / 'jobs' / name
    job.mkdir(parents=True, exist_ok=False)
    inputs = job / 'inputs'; inputs.mkdir()
    initial = {str(p.relative_to(ROOT)): ev.sha(p) for p in sources()}
    for p in sources():
        target = inputs / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    entries = {str(p.relative_to(inputs)): ev.sha(p) for p in sorted(inputs.rglob('*')) if p.is_file()}
    ev.write(inputs / 'INPUTS.json', dict(utc=ev.utc(), sha256=entries))
    sys.path.insert(0, str(ROOT / 'support/inherited/reference'))
    import cpu_preflight
    admitted = cpu_preflight.collect()
    ev.write(job / 'CPU_ADMISSION.json', admitted)
    require(admitted['within_limit'], 'Shared CPU budget unavailable; no retry')
    env = os.environ.copy()
    tmp = job / 'tmp'; tmp.mkdir()
    env.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(tmp))
    tests = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp', str(job / 'pytest_tmp'), str(inputs / 'test_predictor.py')]
    output = ROOT / 'runs' / name
    command = [sys.executable, str(inputs / 'run.py'), '--output', str(output)]
    ev.write(job / 'JOB.json', dict(utc=ev.utc(), tests=tests, command=command,
        source_sha256=initial, input_manifest_sha256=ev.sha(inputs / 'INPUTS.json'),
        development_wall_cap_seconds=300, new_scientific_futures=0, automatic_successor=False))
    start = time.monotonic()
    try:
        with (job / 'pytest.log').open('xb') as log:
            result = subprocess.run(tests, cwd=inputs, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, timeout=120, check=False)
        require(result.returncode == 0, 'Qualification failed; preserve pytest.log')
        ev.write(job / 'QUALIFICATION.json', dict(utc=ev.utc(), status='PASS', log_sha256=ev.sha(job / 'pytest.log'),
            scope='Fixed shrinkage, whole-block exclusion, scalar audit, no-effect counterexample and dry-run costs.'))
        with (job / 'worker.log').open('xb') as log:
            result = subprocess.run(command, cwd=inputs, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, timeout=320, check=False)
        require(result.returncode == 0, 'Development job failed; preserve evidence')
        require(initial == {str(p.relative_to(ROOT)): ev.sha(p) for p in sources()}, 'Source changed during calculation')
        complete = read(output / 'COMPLETE.json')
        print(dict(status='COMPLETE', decision=complete['decision'], total_wall_seconds=time.monotonic() - start,
            development_wall_seconds=complete['wall_seconds']), flush=True)
    except BaseException as error:
        ev.write(job / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    name = parser.parse_args().name
    require(name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name), 'Simple unique job name required')
    main(name)
