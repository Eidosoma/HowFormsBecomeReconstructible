"""Bounded D195 four-block workflow qualification, never a scientific launch."""

import argparse
from pathlib import Path
import subprocess
import sys
import time
import traceback

from laws_confirmation import l22_recipient_pulse_panel as run


def paths(): return run.imported_paths() | {run.WS/n for n in run.SCIENCE} | {Path(__file__).resolve()}


def qualify(attempt):
    assert attempt.startswith('workflow_attempt') and attempt.removeprefix('workflow_attempt').isdigit()
    limits = run.resources(run.BOUND+run.QUAL_BOUND)
    directory = run.ROOT/'qualification'/attempt
    assert not directory.exists(), 'retain all previous qualification attempts'
    inputs = run.benchmark_evidence() | run.block.baseline_evidence() | {str(p): run.sha256_file(p) for p in paths()}
    command = [sys.executable, '-m', 'pytest', *run.TESTS, '-q',
        '--basetemp='+str(directory/'fixtures'), '--junitxml='+str(directory/'tests.xml'),
        '-o', 'cache_dir='+str(directory/'cache')]
    run.write(directory/'MANIFEST.json', dict(started_utc=run.utc_now(), inputs=inputs, command=command,
        resources=limits, scope='panel_workflow_qualification_only', scientific_execution_frozen=False,
        main_cohort_started=False, automatic_polling=False, automatic_retry=False, automatic_successor=False))
    started = time.monotonic()
    try:
        with run.target(directory/'tests.log').open('x') as log:
            completed = subprocess.run(command, cwd=run.WS, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=540)
        assert completed.returncode == 0, f'pytest exit status {completed.returncode}'
        run.verify(inputs); tests = run.test_receipt(directory/'tests.xml')
        result = dict(status='COMPLETE', completed_utc=run.utc_now(), seconds=time.monotonic()-started,
            tests=tests, manifest_sha256=run.sha256_file(directory/'MANIFEST.json'), inputs_unchanged=True,
            artifacts={str(p): run.sha256_file(p) for p in sorted(directory.rglob('*')) if p.is_file()},
            resources=run.resources(run.BOUND), main_cohort_started=False, scientific_execution_frozen=False,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        run.write(directory/'COMPLETE.json', result)
        return {k: v for k, v in result.items() if k != 'artifacts'}
    except Exception as exc:
        run.write(directory/'FAILED.json', dict(status='FAILED', failed_utc=run.utc_now(), error=str(exc),
            traceback=traceback.format_exc(), retained=True, main_cohort_started=False,
            scientific_execution_frozen=False, automatic_retry=False, automatic_successor=False))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--attempt', required=True)
    args = p.parse_args()
    print(__import__('json').dumps(qualify(args.attempt), sort_keys=True), flush=True)
