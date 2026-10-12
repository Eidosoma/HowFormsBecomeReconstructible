"""Schedule-only four-worker launch, retaining original six-worker receipts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E056_sign_magnitude_substitution.plan import HERE,ROOT,NAMES,settings
from E056_sign_magnitude_substitution.run import input_paths
from E056_sign_magnitude_substitution.workflow import predecessor_gate,inventory
from E056_sign_magnitude_substitution.data import receipt


def main():
    workers=4;cap_cpus(workers)
    check_inputs(HERE/'analysis/freeze_v1');previous=predecessor_gate();receipt('scientific')
    ready_path=HERE/'analysis/technical_v2.json';forecast_path=HERE/'analysis/forecast_v2.json'
    ready=json.loads(ready_path.read_text());forecast=json.loads(forecast_path.read_text())
    assert ready['status']=='PASS' and not ready['scientific_run_started']
    assert ready['inputs_sha256']==json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
    for rel,digest in ready['evidence_sha256'].items():assert sha(ROOT/rel)==digest,rel
    assert forecast['workers']==workers and shutil.disk_usage(HERE).free>forecast['storage_with_reserve_bytes']
    active=[str(p) for p in ROOT.glob('E*/jobs/*/status.json') if json.loads(p.read_text()).get('status') in ('RUNNING','PREPARED')]
    assert not active,active
    resources=inventory(workers)
    for p in (ready_path,forecast_path,Path(__file__).resolve()):previous[str(p.relative_to(ROOT))]=sha(p)
    run=HERE/'runs'/NAMES['scientific'];assert not run.exists()
    job=new_run(HERE/'jobs'/NAMES['scientific'],input_paths(),dict(experiment='E056',**settings('scientific'),
        workers=workers,predecessor_evidence=previous,automatic_successor=False,
        scheduling_revision='four_workers_v2',launch_controller_sha256=sha(__file__)))
    shutil.copyfile(__file__,job/'launch_controller_v2.py')
    dump(job/'resources.json',resources);dump(job/'status.json',dict(status='PREPARED',utc=utc(),stage='prepared'))
    # The frozen stage executor and all simulation/audit/plot code are unchanged.
    with (job/'workflow.log').open('x') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(HERE/'workflow.py'),'--mode','scientific',
            '--workers',str(workers),'--execute'],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(pid=proc.pid,utc=utc(),detached=True,stdin='/dev/null',workers=workers,
        launch_controller_sha256=sha(__file__),scheduling_revision='four_workers_v2'))
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        os.kill(proc.pid,0)
        try:status=json.loads((job/'status.json').read_text())
        except json.JSONDecodeError:status={}
        if status.get('status')=='FAILED':raise RuntimeError(status)
        if status.get('stage')=='simulation' and (run/'manifest.json').exists():
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,
                session_is_pid=os.getsid(proc.pid)==proc.pid,stdin=os.readlink(f'/proc/{proc.pid}/fd/0'),
                automatic_polling_started=False))
            print(json.dumps(dict(status='STARTED',pid=proc.pid,workers=workers,job=str(job))));return
        time.sleep(.25)
    raise TimeoutError('Startup exceeded 15 seconds; no automatic restart')


if __name__=='__main__':main()
