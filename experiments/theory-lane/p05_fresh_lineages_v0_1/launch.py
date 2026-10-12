"""Detached launch with bounded startup acknowledgment and no status polling."""
import os
import select
import subprocess
import sys
from common import ROOT,read,write,sha,stamp


def main():
    folder=ROOT/'runs/pilot_v1';manifest=read(folder/'manifest.json')
    assert not any((folder/name).exists() for name in ('LAUNCH.json','WORKER_STARTED.json','FAILED.json'))
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==sha(folder/'inputs'/name)==digest,name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    assert sys.executable==manifest['executable']
    receive,send=os.pipe()
    with (folder/'console.log').open('xb') as log:
        child=subprocess.Popen([sys.executable,'-B',str(folder/'inputs/run.py'),'--run',str(folder),'--ready-fd',str(send)],
            cwd=folder/'inputs',env=os.environ.copy(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,pass_fds=(send,))
    os.close(send);ready,_,_=select.select([receive],[],[],20.);ack=os.read(receive,64) if ready else b'';os.close(receive)
    assert ack==b'READY\n','Startup not acknowledged; preserve launch evidence.'
    started=read(folder/'WORKER_STARTED.json');assert started['pid']==child.pid and started['ready_inputs_verified']
    receipt=dict(status='LAUNCHED',at_utc=stamp(),pid=child.pid,run=str(folder),detached=True,persistent_host_process=True,polling=False,
        startup_acknowledged=True,forecast_minutes=manifest['forecast_cpu_seconds']/60,workers=1,numerical_threads=1,
        blocks=16,records=256,variants=4,fresh_paired_draws=8,scientific_read_contexts=8192,
        completion_marker=str(folder/'COMPLETE.json'),completion_report=str(folder/'REPORT.md'))
    write(folder/'LAUNCH.json',receipt)
    with (folder/'PID').open('x') as f:f.write(str(child.pid)+'\n')
    print(__import__('json').dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
