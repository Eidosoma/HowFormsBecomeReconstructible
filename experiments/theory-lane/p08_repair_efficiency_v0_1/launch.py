"""Start a detached capacity waiter, which starts the authorized run once only."""
import os
import select
import subprocess
import sys
from common import ROOT,read,write,sha,stamp


def main():
    folder=ROOT/'runs/prospective_v1';manifest=read(folder/'manifest.json')
    assert not any((folder/n).exists() for n in ('QUEUE.json','ADMISSION_STARTED.json','LAUNCH.json','WORKER_STARTED.json','FAILED.json'))
    for name,digest in manifest['files_sha256'].items():
        assert sha(ROOT/name)==sha(folder/'inputs'/name)==digest,name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    assert sys.executable==manifest['executable']
    receive,send=os.pipe()
    with (folder/'admission.log').open('xb') as log:
        child=subprocess.Popen([sys.executable,'-B',str(folder/'inputs/admit.py'),'--run',str(folder),'--ready-fd',str(send)],
            cwd=folder/'inputs',env=os.environ.copy(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,close_fds=True,pass_fds=(send,))
    os.close(send);ready,_,_=select.select([receive],[],[],20.)
    ack=os.read(receive,64) if ready else b'';os.close(receive)
    assert ack in (b'QUEUED\n',b'RUNNING\n'),'Admission startup not acknowledged; preserve evidence.'
    receipt=dict(status='WAITING_FOR_CPU' if ack==b'QUEUED\n' else 'RUNNING',at_utc=stamp(),
        admission_pid=child.pid,run=str(folder),detached=True,persistent_host_process=True,
        startup_acknowledged=True,scientific_run_polling=False,cpu_admission_interval_seconds=60,
        forecast_cpu_minutes=manifest['forecast_cpu_seconds']/60,
            measured_benchmark_pending=False,qualified_before_freeze=True,workers=1,numerical_threads=1,
        blocks=132,records=2112,variants=3,generations=list(range(15,33)),scientific_read_contexts=114048,simulated_read_contexts=114048,reused_control_contexts=0,
        completion_marker=str(folder/'COMPLETE.json'),completion_report=str(folder/'REPORT.md'))
    write(folder/'QUEUE.json',receipt)
    with (folder/'ADMISSION_PID').open('x') as f:f.write(str(child.pid)+'\n')
    print(__import__('json').dumps(receipt,indent=2),flush=True)
    if ack==b'RUNNING\n':print(__import__('json').dumps(read(folder/'LAUNCH.json'),indent=2),flush=True)


if __name__=='__main__':main()
