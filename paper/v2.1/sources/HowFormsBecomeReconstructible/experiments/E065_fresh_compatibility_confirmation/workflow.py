"""Resource-bounded execution, detached when the forecast exceeds ten minutes."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E065_fresh_compatibility_confirmation.plan import HERE,ROOT,NAMES,settings
from E065_fresh_compatibility_confirmation.run import input_paths
from E065_fresh_compatibility_confirmation.data import verify_receipts


def inventory(workers=None):
    def sample():
        out={}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name)==os.getpid():continue
            try:
                args=(p/'cmdline').read_bytes().split(b'\0');name=Path(os.fsdecode(args[0])).name
                if not (name.startswith(('python','pytest')) or name in ('R','Rscript')):continue
                raw=(p/'stat').read_text();s=raw[raw.rfind(')')+2:].split()
                out[int(p.name)]=dict(ticks=int(s[11])+int(s[12]),threads=int(s[17]),affinity=sorted(os.sched_getaffinity(int(p.name))))
            except (OSError,ValueError,IndexError):pass
        return out
    before=sample();tick=time.monotonic();time.sleep(1);after=sample();elapsed=time.monotonic()-tick
    busy=[]
    for pid,row in after.items():
        use=(row['ticks']-before.get(pid,row)['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed
        if use>=.2:busy.append(dict(pid=pid,sampled_cpu_percent=100*use,**row))
    capacity=sum(min(x['threads'],len(x['affinity'])) for x in busy)
    assert workers is None or workers+capacity<=12
    return dict(utc=utc(),other_busy_processes=busy,other_busy_capacity=capacity,
                free_bytes=shutil.disk_usage(HERE).free,affinity=sorted(os.sched_getaffinity(0)),total_cpu_ceiling=12)


def execute(mode,workers):
    job=HERE/'jobs'/NAMES[mode];started=time.monotonic()
    try:
        check_inputs(job)
        for rel,digest in json.loads((job/'manifest.json').read_text())['contract']['evidence'].items():
            assert sha(ROOT/rel)==digest,rel
        dump(job/'status.json',dict(status='RUNNING',stage='source_and_reader_replay',utc=utc(),
            completed_blocks=[],total_blocks=len(settings(mode)['blocks']),workers=workers,pid=os.getpid()))
        with (job/'reader.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'run.py'),'--mode',mode,'--workers',str(workers)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        run=HERE/'runs'/NAMES[mode];check_inputs(job)
        audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
        assert audit['status']=='PASS' and audit['complete_sha256']==sha(run/'COMPLETE.json')
        dump(job/'status.json',dict(status='COMPLETE',utc=utc(),seconds=time.monotonic()-started,
            completed_blocks=settings(mode)['blocks'],total_blocks=len(settings(mode)['blocks']),workers=workers,
            complete_sha256=sha(run/'COMPLETE.json'),audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),automatic_successor_started=False))
    except BaseException:
        dump(job/'status.json',dict(status='FAILED',utc=utc(),traceback=traceback.format_exc(),automatic_restart=False));raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=NAMES,required=True)
    p.add_argument('--workers',type=int,default=0);p.add_argument('--detach',action='store_true');p.add_argument('--execute',action='store_true')
    a=p.parse_args();assert 0<=a.workers<=8
    if a.execute:cap_cpus(a.workers);execute(a.mode,a.workers);return
    check_inputs(HERE/'analysis/freeze_v1');verify_receipts(a.mode)
    evidence={};resources=inventory(None)
    if a.mode=='scientific':
        ready=HERE/'analysis/technical_v1.json';forecast_path=HERE/'analysis/forecast_v1.json'
        receipt=json.loads(ready.read_text());forecast=json.loads(forecast_path.read_text())
        assert receipt['status']=='PASS' and receipt['figures_inspected']
        assert receipt['inputs_sha256']==json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
        for rel,digest in receipt['evidence_sha256'].items():assert sha(ROOT/rel)==digest,rel
        for path in (ready,forecast_path):evidence[str(path.relative_to(ROOT))]=sha(path)
        assert resources['free_bytes']>forecast['storage_with_reserve_bytes']
        available=min(8,12-resources['other_busy_capacity'],max(1,len(resources['affinity'])-resources['other_busy_capacity']))
        a.workers=a.workers or available
        assert 1<=a.workers<=8 and a.workers+resources['other_busy_capacity']<=12
        resources['forecast_seconds']=forecast['seconds_by_workers'][str(a.workers)]
        assert a.detach or resources['forecast_seconds']<=600,'Forecast requires detached execution'
    else:
        a.workers=a.workers or 1;assert a.workers==1 and resources['other_busy_capacity']+1<=12
    # Choose from the existing affinity using measured competing load; scheduling
    # changes do not alter streams, cases, equations or inference.
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda cpu:(burden[cpu],cpu))[:a.workers])
    resources['selected_affinity']=selected;resources['estimated_cpu_burden']=burden
    os.sched_setaffinity(0,selected)
    cap_cpus(a.workers)
    job=new_run(HERE/'jobs'/NAMES[a.mode],input_paths(),dict(experiment='E065',**settings(a.mode),
        workers=a.workers,evidence=evidence,automatic_successor=False))
    dump(job/'resources.json',resources)
    dump(job/'status.json',dict(status='PREPARED',utc=utc(),stage='prepared'))
    if not a.detach:
        dump(job/'launch.json',dict(pid=os.getpid(),utc=utc(),detached=False,workers=a.workers))
        execute(a.mode,a.workers);return
    with (job/'workflow.log').open('x') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(HERE/'workflow.py'),'--mode',a.mode,
            '--workers',str(a.workers),'--execute'],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(pid=proc.pid,utc=utc(),detached=True,stdin='/dev/null',workers=a.workers,
        forecast_seconds=resources.get('forecast_seconds')))
    # A bounded launch check, not scientific progress polling.
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        os.kill(proc.pid,0)
        try:s=json.loads((job/'status.json').read_text())
        except json.JSONDecodeError:s={}
        if s.get('status')=='FAILED':raise RuntimeError(s)
        run=HERE/'runs'/NAMES[a.mode]
        if (run/'manifest.json').exists() and list(run.glob('worker_*.log')):
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,detached=True,
                stdin='/dev/null',automatic_polling_started=False,workers=a.workers))
            print(json.dumps(dict(status='STARTED',pid=proc.pid,workers=a.workers,
                forecast_seconds=resources.get('forecast_seconds'),job=str(job))));return
        time.sleep(.25)
    raise TimeoutError('Startup did not complete in 15 seconds; preserve logs, no automatic restart')


if __name__=='__main__':main()
