"""One admitted, bounded read-only development calculation including its checks."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import signal
import sys
import time
import traceback
import unittest

ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'protocol.json').read_text())


def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    frozen=json.loads((ROOT/'INPUTS.json').read_text())
    assert all(sha(ROOT/name)==digest for name,digest in frozen['sha256'].items())


def main():
    started,cpu=time.monotonic(),time.process_time()
    assert not (ROOT/'results_v1').exists() and not (ROOT/'checks/START.json').exists()
    def expired(*_):raise TimeoutError('Fixed 600-second read-only diagnostic cap; no automatic retry')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,P['resources']['hard_wall_seconds'])
    write(ROOT/'checks/START.json',dict(utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),hard_seconds=600,input_manifest_sha256=sha(ROOT/'INPUTS.json')))
    try:
        verify()
        source_package=Path(P['source']).parents[1]
        path=source_package/'jobs/qualification_v2/inputs/parent/qualified/native/inherited/reference/cpu_preflight.py'
        sys.path.insert(0,str(path.parent))
        spec=importlib.util.spec_from_file_location('cpu_preflight',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        receipt=module.collect()
        receipt.update(planned_threads=1,purpose='Read-only saved-data recovery diagnostic')
        receipt['within_limit']=receipt['other_active_or_recently_busy_threads']+1<=12
        write(ROOT/'checks/CPU_ADMISSION.json',receipt)
        assert receipt['within_limit'], 'Shared CPU budget unavailable'
        suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_diagnostic.py')
        with (ROOT/'checks/tests.log').open('x') as f:
            tested=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        assert tested.testsRun==9 and tested.wasSuccessful()
        write(ROOT/'checks/TESTS.json',dict(status='PASS',tests=tested.testsRun,failures=len(tested.failures),errors=len(tested.errors)))
        import analyze
        count=analyze.analyze()
        import audit
        audit_result=audit.audit()
        verify()
        output=ROOT/'results_v1'
        files={str(p.relative_to(output)):sha(p) for p in sorted(output.iterdir()) if p.is_file()}
        write(output/'OUTPUTS.json',dict(sha256=files))
        done=dict(status='COMPLETE',utc=datetime.now(timezone.utc).isoformat(),
            input_manifest_sha256=sha(ROOT/'INPUTS.json'),output_manifest_sha256=sha(output/'OUTPUTS.json'),
            tests_passed=9,independent_scalar_audit=audit_result['status'],probe_cases=count[0],trajectories=count[1],source_files=count[2],
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
            new_native_reads=0,new_native_simulations=0,new_outcomes=0,new_model_fits=0,
            development_analysis=True,automatic_successor=False,automatic_retry=False)
        write(output/'COMPLETE.json',done)
        print(done,flush=True)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL,0)
        write(ROOT/'checks/FAILED.json',dict(utc=datetime.now(timezone.utc).isoformat(),traceback=traceback.format_exc(),automatic_retry=False))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
