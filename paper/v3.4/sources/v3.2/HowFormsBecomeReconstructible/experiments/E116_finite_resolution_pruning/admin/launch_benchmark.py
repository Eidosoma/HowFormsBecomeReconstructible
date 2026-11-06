"""Detach the excluded full-width benchmark under its recorded timing allowance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import check_inputs,dump,new_run,utc
from E116_finite_resolution_pruning.run import inputs,inventory
from E116_finite_resolution_pruning.plan import HERE,ROOT,settings


def main():
    name='benchmark_v1';forecast_path=HERE/'analysis/benchmark_forecast_v1.json'
    forecast=json.loads(forecast_path.read_text());assert forecast['workers']==1
    resources=inventory(1)
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=[min(burden,key=lambda cpu:(burden[cpu],cpu))]
    os.sched_setaffinity(0,selected);resources['selected_affinity']=selected
    paths=inputs('benchmark')+[forecast_path,Path(__file__).resolve()]
    job=new_run(HERE/'jobs'/name,paths,dict(**settings('benchmark'),workers=1,scientific_launch=False))
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'execute',
            '--mode','benchmark','--name',name,'--workers','1'],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,detached=True,stdin='/dev/null',workers=1,
        forecast=forecast,resources=resources,automatic_restart=False,automatic_successor=False))
    deadline=time.monotonic()+45
    while time.monotonic()<deadline and proc.poll() is None:
        try:s=json.loads((HERE/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.25);continue
        if s['status']=='FAILED':raise RuntimeError(s)
        if s.get('stage')=='finite_readers_and_independent_replay':
            check_inputs(job);check_inputs(HERE/'runs'/name)
            assert (HERE/'runs'/name/'resources.json').exists()
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=1,
                stage=s['stage'],resource_gate_passed=True,automatic_polling=False,scientific_launch=False))
            print(json.dumps(dict(status='RUNNING',phase='excluded_benchmark',pid=proc.pid,
                expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'])));return
        time.sleep(.25)
    dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),automatic_restart=False))
    raise RuntimeError('Bounded benchmark startup failed; preserve evidence, no retry loop')


if __name__=='__main__':main()
