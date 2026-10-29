"""D196 synthetic qualification and complete family extraction cost measurement."""

import argparse
import importlib.util
import subprocess
import sys
import time
import traceback

import numpy as np

from laws_confirmation import l22_pulse_mechanism as run


def qualify(attempt):
    assert attempt.startswith('workflow_attempt') and attempt.removeprefix('workflow_attempt').isdigit()
    limits = run.resources(run.OUTPUT+run.QUAL)
    directory = run.ROOT/'qualification'/attempt
    assert not directory.exists(), 'retain previous attempts'
    inputs = {str(run.WS/p): run.digest(run.WS/p) for p in run.SCIENCE}
    command = [sys.executable, '-m', 'pytest', 'tests/test_l22_pulse_mechanism.py', '-q',
        '--basetemp='+str(directory/'fixtures'), '--junitxml='+str(directory/'tests.xml'),
        '-o', 'cache_dir='+str(directory/'cache')]
    run.write(directory/'MANIFEST.json', dict(started_utc=run.utc(), inputs=inputs, resources=limits,
        command=command, scope='synthetic_qualification_only', study_metrics_extracted=False,
        new_dynamics=0, automatic_retry=False, automatic_successor=False))
    start = time.monotonic()
    try:
        with run.target(directory/'tests.log').open('x') as log:
            result = subprocess.run(command, cwd=run.WS, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=550)
        assert result.returncode == 0, f'pytest failed: {result.returncode}'
        tests = run.test_receipt(directory/'tests.xml')
        # Full-size synthetic arrays only; no D195 study files are loaded.
        spec=importlib.util.spec_from_file_location('d196_synthetic',run.WS/'tests/test_l22_pulse_mechanism.py')
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        bundle=fixture.make_bundle(parents=4,draws=4)
        tick=time.monotonic();values,proof=run.metrics.extract(bundle,'common')
        seconds=time.monotonic()-tick
        assert proof['passes'] and proof['new_dynamics']==0
        run.write(directory/'BENCHMARK.json',dict(passes=True,families=1,records=16,
            seconds=seconds,proof=proof,new_dynamics=0,budget=run.budget(seconds)))
        del bundle,values
        run.verify(inputs)
        done = dict(status='COMPLETE', completed_utc=run.utc(), seconds=time.monotonic()-start,
            inputs_unchanged=True, manifest_sha256=run.digest(directory/'MANIFEST.json'), tests=tests,
            artifacts={str(p): run.digest(p) for p in directory.rglob('*') if p.is_file()},
            resources=run.resources(run.OUTPUT), study_metrics_extracted=False, new_dynamics=0,
            automatic_retry=False, automatic_successor=False)
        run.write(directory/'COMPLETE.json', done)
        return {k: v for k, v in done.items() if k != 'artifacts'} | {'budget': run.budget(seconds)}
    except Exception:
        run.write(directory/'FAILED.json', dict(status='FAILED', failed_utc=run.utc(), traceback=traceback.format_exc(),
            retained=True, study_metrics_extracted=False, new_dynamics=0, automatic_retry=False, automatic_successor=False))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--attempt', required=True)
    a = p.parse_args(); print(__import__('json').dumps(qualify(a.attempt), sort_keys=True), flush=True)
