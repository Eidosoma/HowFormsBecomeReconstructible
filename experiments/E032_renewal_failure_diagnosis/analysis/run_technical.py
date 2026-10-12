"""Retain the short-test and excluded-benchmark invocations and outputs."""
import json
from pathlib import Path
import subprocess
import sys
import time
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, sha, utc


def main():
    cap_cpus(8); check_inputs(HERE/'analysis/freeze_v1')
    assert not (HERE/'analysis/technical_v1.json').exists()
    started = time.monotonic()
    commands = [('tests', [sys.executable, '-B', str(HERE/'tests.py')]),
                ('benchmark', [sys.executable, '-B', str(HERE/'run.py'), '--mode', 'benchmark'])]
    results = {}
    for stage, command in commands:
        log = HERE/'analysis'/f'{stage}_v1.log'
        t = time.monotonic()
        with log.open('x') as handle:
            process = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT)
        results[stage] = dict(returncode=process.returncode, seconds=time.monotonic()-t, log_sha256=sha(log), command=command)
        print(log.read_text(), flush=True)
        if process.returncode:
            dump(HERE/'analysis/technical_v1.json', dict(status='FAIL', utc=utc(), stages=results))
            raise SystemExit(process.returncode)
    check_inputs(HERE/'analysis/freeze_v1')
    dump(HERE/'analysis/technical_v1.json', dict(status='PASS', utc=utc(), tests=5,
        seconds=time.monotonic()-started, stages=results, freeze_manifest_sha256=sha(HERE/'analysis/freeze_v1/manifest.json'),
        runner_sha256=sha(__file__), inputs_unchanged=True))
    print((HERE/'analysis/forecast_v1.json').read_text(), flush=True)


if __name__ == '__main__': main()
