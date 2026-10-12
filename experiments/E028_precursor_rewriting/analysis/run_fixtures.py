"""Retain the invocation, frozen inputs, log and result of the short fixture suite."""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import sha, utc
from E028_precursor_rewriting.run import input_paths


def main():
    analysis = HERE/'analysis'
    log = analysis/'fixtures_v1.log'
    receipt = analysis/'fixtures_v1.json'
    invocation = analysis/'fixture_invocation_v1.json'
    assert not any(p.exists() for p in (log, receipt, invocation))
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in input_paths()}
    with invocation.open('x') as handle:
        json.dump(dict(utc=utc(), estimated_seconds=120, inputs_sha256=inputs,
            command=[sys.executable, '-B', str(HERE/'tests.py')]), handle, indent=2)
    started = time.monotonic()
    with log.open('x') as handle:
        result = subprocess.run([sys.executable, '-B', str(HERE/'tests.py')], cwd=ROOT,
            stdout=handle, stderr=subprocess.STDOUT)
    unchanged = all(sha(ROOT/rel) == digest for rel, digest in inputs.items())
    passed = result.returncode == 0 and unchanged and 'Ran 7 tests' in log.read_text()
    evidence = dict(status='PASS' if passed else 'FAIL', tests=7, utc=utc(),
        seconds=time.monotonic()-started, returncode=result.returncode,
        source_log=str(log.relative_to(ROOT)), log_sha256=sha(log), inputs_sha256=inputs,
        frozen_inputs_unchanged=unchanged, invocation_sha256=sha(invocation))
    with receipt.open('x') as handle:
        json.dump(evidence, handle, indent=2)
    print(log.read_text(), flush=True)
    print(json.dumps(evidence, indent=2), flush=True)
    if not passed: raise SystemExit(1)


if __name__ == '__main__':
    main()
