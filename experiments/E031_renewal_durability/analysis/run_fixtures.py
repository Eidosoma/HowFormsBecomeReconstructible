"""Freeze the complete source before the disposable nine-test suite."""
import json
from pathlib import Path
import subprocess
import sys
import time
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, sha, utc
from E031_renewal_durability.run import input_paths


def main():
    cap_cpus(8)
    analysis = HERE/'analysis'
    log, receipt = analysis/'fixtures_v1.log', analysis/'fixtures_v1.json'
    assert not log.exists() and not receipt.exists()
    suite = new_run(analysis/'fixture_suite_v1', input_paths(), dict(experiment='E031', mode='technical_fixture_suite', estimated_seconds=180, tests=9))
    inputs = json.loads((suite/'manifest.json').read_text())['inputs_sha256']
    started = time.monotonic()
    with log.open('x') as handle:
        result = subprocess.run([sys.executable, '-B', str(HERE/'tests.py')], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT)
    unchanged = all(sha(ROOT/rel) == digest for rel, digest in inputs.items())
    passed = result.returncode == 0 and unchanged and 'Ran 9 tests' in log.read_text()
    evidence = dict(status='PASS' if passed else 'FAIL', tests=9, utc=utc(), seconds=time.monotonic()-started,
        returncode=result.returncode, log_sha256=sha(log), inputs_sha256=inputs,
        frozen_inputs_unchanged=unchanged, suite_manifest_sha256=sha(suite/'manifest.json'),
        fixture_artifacts_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(analysis.glob('*_fixture.npz'))},
        runner_sha256=sha(__file__))
    dump(receipt, evidence)
    if passed: finish(suite, started, dict(fixture_receipt_sha256=sha(receipt)))
    else: dump(suite/'FAILED.json', evidence)
    print(log.read_text(), flush=True)
    print(json.dumps(evidence, indent=2), flush=True)
    if not passed: raise SystemExit(1)


if __name__ == '__main__': main()
