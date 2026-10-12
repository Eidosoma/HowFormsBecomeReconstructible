"""CPU admission only; after starting the scientific worker, exit without polling."""
import argparse
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import traceback
from common import ROOT,read,write,sha,status,stamp
from cpu_preflight import collect


def await_capacity(folder,on_wait,sampler=collect,sleeper=time.sleep):
    attempts=folder/'admission_checks';attempts.mkdir(exist_ok=False)
    hashes={};attempt=0
    while True:
        attempt+=1;receipt=sampler()
        assert receipt['shared_limit']==12 and receipt['planned_threads']==1
        assert receipt['within_limit']==(receipt['other_active_or_recently_busy_threads']+1<=12)
        path=attempts/f'attempt_{attempt:06d}.json';write(path,receipt)
        hashes[str(path.relative_to(folder))]=sha(path)
        if receipt['within_limit']:
            write(folder/'CPU_ADMISSION.json',receipt)
            return hashes
        status(folder,status='WAITING_FOR_CPU',phase='capacity_wait',capacity_checks=attempt)
        if attempt==1:on_wait()
        sleeper(60)


def main(folder,ready_fd):
    def acknowledge(message):
        nonlocal ready_fd
        if ready_fd is not None:
            os.write(ready_fd,message);os.close(ready_fd);ready_fd=None
    try:
        manifest=read(folder/'manifest.json')
        assert ROOT==folder/'inputs' and sys.executable==manifest['executable']
        for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name
        write(folder/'ADMISSION_STARTED.json',dict(status='CAPACITY_CHECK',at_utc=stamp(),pid=os.getpid(),
            persistent_host_process=True,scientific_run_polling=False,capacity_interval_seconds=60))
        checks=await_capacity(folder,lambda:acknowledge(b'QUEUED\n'))
        for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name
        receive,send=os.pipe()
        with (folder/'console.log').open('xb') as log:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'run.py'),'--run',str(folder),'--ready-fd',str(send)],
                cwd=ROOT,env=os.environ.copy(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=True,close_fds=True,pass_fds=(send,))
        os.close(send);ready,_,_=select.select([receive],[],[],20.)
        ack=os.read(receive,64) if ready else b'';os.close(receive)
        assert ack==b'READY\n','Worker startup not acknowledged; preserve evidence.'
        started=read(folder/'WORKER_STARTED.json');assert started['pid']==child.pid and started['ready_inputs_verified']
        receipt=dict(status='LAUNCHED',at_utc=stamp(),pid=child.pid,run=str(folder),detached=True,
            persistent_host_process=True,polling=False,startup_acknowledged=True,
            forecast_cpu_minutes=manifest['forecast_cpu_seconds']/60,workers=1,numerical_threads=1,
            blocks=16,records=256,variants=4,generations=list(range(15,33)),scientific_read_contexts=18432,acquisition_lineage_read_contexts=3584,simulated_read_contexts=18432,reused_control_contexts=0,
            completion_marker=str(folder/'COMPLETE.json'),completion_report=str(folder/'REPORT.md'))
        write(folder/'LAUNCH.json',receipt)
        with (folder/'PID').open('x') as f:f.write(str(child.pid)+'\n')
        write(folder/'ADMISSION_COMPLETE.json',dict(status='STARTED_ONCE',at_utc=stamp(),
            worker_pid=child.pid,capacity_checks_sha256=checks,scientific_run_polled=False))
        acknowledge(b'RUNNING\n')
        print('Authorized worker started; admission process exits without polling.',flush=True)
    except BaseException:
        failure=dict(status='ADMISSION_FAILED',at_utc=stamp(),traceback=traceback.format_exc())
        if not (folder/'ADMISSION_FAILED.json').exists():write(folder/'ADMISSION_FAILED.json',failure)
        status(folder,status='FAILED',phase='admission_failed');raise
    finally:
        if ready_fd is not None:os.close(ready_fd)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--ready-fd',type=int,required=True);a=p.parse_args()
    main(a.run.resolve(),a.ready_fd)
