"""Host launch with a single bounded startup acknowledgment; no runtime polling."""
import os
from pathlib import Path
import select
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import ROOT,read,sha,stamp,write


def main():
    folder=ROOT/'runs/pilot_v1_resume1'
    manifest=read(folder/'manifest.json')
    assert not (folder/'LAUNCH.json').exists() and not (folder/'FAILED.json').exists()
    for name,digest in manifest['code_sha256'].items():
        assert sha(ROOT/name)==digest,name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    # The original host worker was confirmed absent. Reject any duplicate resume.
    target=str(ROOT/'recovery_v0_1/runner.py')
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            argv=[a.decode(errors='replace') for a in (path/'cmdline').read_bytes().split(b'\0') if a]
            assert target not in argv,'Recovery worker already exists: '+path.name
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    receive,send=os.pipe()
    with (folder/'console.log').open('xb') as log:
        child=subprocess.Popen([sys.executable,'-B',target,'--run',str(folder),'--ready-fd',str(send)],
            cwd=ROOT,env=os.environ.copy(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,close_fds=True,pass_fds=(send,))
    os.close(send)
    ready,_,_=select.select([receive],[],[],20.)
    acknowledgment=os.read(receive,64) if ready else b''
    os.close(receive)
    assert acknowledgment==b'READY\n','No successful startup acknowledgment; inspect preserved run evidence.'
    started=read(folder/'WORKER_STARTED.json')
    assert started['pid']==child.pid and started['ready_inputs_verified']
    receipt=dict(status='LAUNCHED',launched_at_utc=stamp(),pid=child.pid,run=str(folder),
        detached=True,persistent_host_process=True,polling=False,startup_acknowledged=True,
        reused_blocks=[34000],remaining_blocks=list(range(34001,34008)),
        forecast_minutes=manifest['forecast_cpu_seconds']/60,scientific_protocol_unchanged=True,
        completion_marker=str(folder/'COMPLETE.json'),completion_report=str(folder/'REPORT.md'))
    write(folder/'LAUNCH.json',receipt)
    with (folder/'PID').open('x') as f:f.write(str(child.pid)+'\n')
    print(__import__('json').dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    main()
