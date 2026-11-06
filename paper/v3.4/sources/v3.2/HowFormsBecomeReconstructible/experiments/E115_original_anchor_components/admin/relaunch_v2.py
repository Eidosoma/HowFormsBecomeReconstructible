"""One reviewed resource resubmission; execute the unchanged frozen E115 engine."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import check_inputs, dump, new_run, sha, utc
from E084_magnitude_placement.workflow import inventory
from E115_original_anchor_components.plan import HERE, ROOT, settings
from E115_original_anchor_components.run import inputs, qualification


def main():
    name='anchor_v2';workers=3;qualification()
    reviewed=HERE/'analysis/resource_recovery_v1.json'
    review=json.loads(reviewed.read_text());assert review['status']=='REVIEWED'
    for p,h in review['evidence'].items():assert sha(ROOT/p)==h,p
    check_inputs(HERE/'runs/anchor_v1');check_inputs(HERE/'jobs/anchor_v1')
    forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text())
    assert workers==forecast['workers'] and forecast['detach_required']
    resources=inventory(workers);assert resources['free_bytes']>forecast['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes']
                   if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda cpu:(burden[cpu],cpu))[:workers])
    assert len(selected)==workers;os.sched_setaffinity(0,selected);resources['selected_affinity']=selected
    scientific=inputs('scientific')
    job=new_run(HERE/'jobs'/name,scientific+[Path(__file__).resolve(),reviewed],
                dict(**settings('scientific'),workers=workers,reviewed_resubmission_of='anchor_v1',
                     scientific_inputs_unchanged=True))
    try:
        with (job/'run.log').open('xb') as log:
            proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'execute',
                '--mode','scientific','--name',name,'--workers',str(workers)],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,detached=True,workers=workers,resources=resources,
            forecast=forecast,reviewed_resubmission_of='anchor_v1',scientific_inputs_unchanged=True,
            administrative_launcher_sha256=sha(Path(__file__)),automatic_restart=False,automatic_successor=False))
        deadline=time.monotonic()+60;last=None
        while time.monotonic()<deadline:
            run=HERE/'runs'/name
            try:last=json.loads((run/'STATUS.json').read_text())
            except (FileNotFoundError,json.JSONDecodeError):last=None
            if last and last['status']=='FAILED':raise RuntimeError(last)
            if last and last['status']=='RUNNING' and last['stage']=='anchored_readers_and_independent_replay':
                check_inputs(job);check_inputs(run)
                observed=json.loads((run/'resources.json').read_text())
                assert workers+observed['other_busy_capacity']<=12
                assert proc.poll() is None and os.getsid(proc.pid)==proc.pid
                assert os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
                assert json.loads((run/'manifest.json').read_text())['inputs_sha256']=={
                    str(p.relative_to(ROOT)):sha(p) for p in scientific}
                dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=workers,
                    verified_stage=last['stage'],execution_resource_gate_passed=True,
                    source_verification_and_archived_copies_passed=True,
                    scientific_inputs_unchanged=True,execution_resources=observed,
                    automatic_polling=False,automatic_restart=False))
                print(json.dumps(dict(status='RUNNING',pid=proc.pid,workers=workers,
                    verified_stage=last['stage'],expected_seconds=forecast['expected_seconds'],
                    conservative_seconds=forecast['conservative_seconds'])),flush=True)
                return
            if proc.poll() is not None:raise RuntimeError(f'Process exited before verified reader stage: {proc.returncode}')
            time.sleep(.25)
        raise TimeoutError(f'Reader-stage startup not verified within 60 seconds: {last}')
    except BaseException:
        dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),traceback=traceback.format_exc(),
             automatic_restart=False,process_not_automatically_terminated=True))
        raise


if __name__=='__main__':main()
