"""Explicit one-time completion of an interrupted launcher, never rerun simulation."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import cap_cpus,check_inputs,dump,sha,utc
from E015_functional_inheritance.audit import verify
from E056_sign_magnitude_substitution.plan import HERE,ROOT


def main():
    cap_cpus(1);job=HERE/'jobs/benchmark_v1';run=HERE/'runs/benchmark_v1'
    receipt=job/'interruption_v1.json'
    evidence=json.loads(receipt.read_text());assert evidence['observed_launcher_exit_code']==143
    check_inputs(job);verify(run)
    assert sha(run/'COMPLETE.json')==evidence['simulation_complete_sha256']
    assert not (run/'INDEPENDENT_AUDIT.json').exists()
    assert not (HERE/'figures/benchmark_v1').exists()
    start=time.monotonic()
    try:
        for stage,script in (('independent_audit','audit.py'),('figure','plot.py')):
            dump(job/'status.json',dict(status='RUNNING',stage=stage,utc=utc(),pid=os.getpid(),workers=1,
                explicit_completion_after_interruption=True))
            cmd=[sys.executable,'-B',str(HERE/script),'--mode','benchmark']
            if stage=='independent_audit':cmd+=['--workers','1']
            with (job/(stage+'.log')).open('x') as log:
                subprocess.run(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        check_inputs(job);verify(run)
        begun=datetime.fromisoformat(json.loads((job/'manifest.json').read_text())['started_utc'])
        dump(job/'status.json',dict(status='COMPLETE',utc=utc(),seconds=(datetime.fromisoformat(utc())-begun).total_seconds(),
            completion_phase_seconds=time.monotonic()-start,complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),interruption_sha256=sha(receipt),
            completion_code_sha256=sha(__file__),explicit_completion_after_interruption=True,
            simulation_repeated=False,automatic_successor_started=False))
    except BaseException:
        dump(job/'status.json',dict(status='FAILED',utc=utc(),traceback=traceback.format_exc(),automatic_restart=False))
        raise


if __name__=='__main__':main()
