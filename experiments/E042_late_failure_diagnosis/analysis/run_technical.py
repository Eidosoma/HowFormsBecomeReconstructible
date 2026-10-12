"""Freeze and validate the saved-record diagnosis on synthetic/excluded cases."""
import ast,json,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent;sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E042_late_failure_diagnosis.run import inputs


def main():
    cap_cpus(8);analysis=HERE/'analysis'
    for p in HERE.glob('*.py'):ast.parse(p.read_text())
    new_run(analysis/'freeze_v1',inputs(),dict(experiment='E042',purpose='Before tests or new per-record measurements'))
    results={};started=time.monotonic()
    for stage,args in [('tests',['tests.py']),('benchmark',['run.py','--mode','benchmark'])]:
        command=[sys.executable,'-B',str(HERE/args[0]),*args[1:]];log=analysis/f'{stage}_v1.log';t=time.monotonic()
        with log.open('x') as handle:p=subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT)
        results[stage]=dict(returncode=p.returncode,seconds=time.monotonic()-t,log_sha256=sha(log),command=command)
        print(log.read_text(),flush=True)
        if p.returncode:
            dump(analysis/'technical_v1.json',dict(status='FAIL',utc=utc(),stages=results));raise SystemExit(p.returncode)
    check_inputs(analysis/'freeze_v1')
    dump(analysis/'technical_v1.json',dict(status='PASS',utc=utc(),tests=8,seconds=time.monotonic()-started,
        stages=results,freeze_manifest_sha256=sha(analysis/'freeze_v1/manifest.json'),runner_sha256=sha(__file__),inputs_unchanged=True))
    print((analysis/'forecast_v1.json').read_text(),flush=True)


if __name__=='__main__':main()
