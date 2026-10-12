"""Freeze scientific inputs, retain tests and run the excluded end-to-end fixture."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E045_weakening_rollback.run import input_paths


def main():
    cap_cpus(8); analysis=HERE/'analysis'
    for p in HERE.glob('*.py'): ast.parse(p.read_text())
    new_run(analysis/'freeze_v1',input_paths(),dict(experiment='E045',purpose='Before tests or receiving interventions'))
    inputs=json.loads((analysis/'freeze_v1/manifest.json').read_text())['inputs_sha256']
    stages=(('tests',['tests.py']),('fixture',['run.py','--mode','fixture','--workers','1']),
            ('fixture_audit',['audit.py',str(HERE/'runs/fixture_v1'),'--workers','1']),
            ('fixture_plot',['plot.py',str(HERE/'runs/fixture_v1')]))
    results={}; started=time.monotonic()
    for name, args in stages:
        command=[sys.executable,'-B',str(HERE/args[0]),*args[1:]]
        log=analysis/f'{name}_v1.log'; t=time.monotonic()
        with log.open('x') as handle:
            p=subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT)
        results[name]=dict(returncode=p.returncode,seconds=time.monotonic()-t,log_sha256=sha(log))
        print(log.read_text(),flush=True)
        if p.returncode:
            dump(analysis/'technical_v1.json',dict(status='FAIL',utc=utc(),stages=results,inputs_sha256=inputs))
            raise SystemExit(p.returncode)
    check_inputs(analysis/'freeze_v1')
    audit=json.loads((HERE/'runs/fixture_v1/INDEPENDENT_AUDIT.json').read_text())
    assert audit['status']=='PASS' and audit['individual_observations']==4032
    s=json.loads((HERE/'runs/fixture_v1/summary.json').read_text())
    assert s['status']=='TECHNICAL_ONLY' and s['primary']['joint_pass'] is None
    dump(analysis/'technical_v1.json',dict(status='PASS',utc=utc(),tests=12,end_to_end_fixture_passed=True,
        seconds=time.monotonic()-started,stages=results,inputs_sha256=inputs,inputs_unchanged=True,
        fixture_complete_sha256=sha(HERE/'runs/fixture_v1/COMPLETE.json'),
        fixture_audit_sha256=sha(HERE/'runs/fixture_v1/INDEPENDENT_AUDIT.json'),runner_sha256=sha(__file__)))
    print('Technical validation PASS; twelve checks and complete independent fixture.',flush=True)


if __name__=='__main__':main()
