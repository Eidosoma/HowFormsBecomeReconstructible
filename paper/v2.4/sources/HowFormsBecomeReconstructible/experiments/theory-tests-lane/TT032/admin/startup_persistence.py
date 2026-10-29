"""One host process check after detached launch; do not inspect scientific outputs."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import os
import time


def process(pid):
    path=Path('/proc')/str(pid)
    fields=(path/'stat').read_text().rsplit(')',1)[1].split()
    assert fields[0] not in ('Z','X')
    return dict(pid=pid,state=fields[0],ppid=int(fields[1]),session=int(fields[3]),
        start_ticks=int(fields[19]),nice=os.getpriority(os.PRIO_PROCESS,pid),cpus=sorted(os.sched_getaffinity(pid)))


def main():
    assert len(list(Path('/proc').glob('[0-9]*')))>16,'host namespace required'
    launch=read_json(ROOT/'LAUNCH.json');frozen=read_json(ROOT/'FREEZE.json')
    assert launch['status']=='DETACHED_STARTED'
    time.sleep(3)
    parent=process(launch['pid']);assert parent['session']==parent['pid']
    assert parent['cpus']==frozen['cpus'] and parent['nice']==0
    directory=ROOT/'runs/reset_v1';assert not (directory/'FAILED.json').exists()
    workers=[]
    for index,cpu in zip(BLOCKS[:2],frozen['cpus']):
        receipt=read_json(directory/f'worker_{index}.json');p=process(receipt['pid'])
        assert p['ppid']==parent['pid'] and p['cpus']==[cpu] and p['nice']==0
        assert receipt['nice']==0 and receipt['numerical_threads']==1
        values={}
        for item in (Path('/proc')/str(p['pid'])/'environ').read_bytes().split(b'\0'):
            if b'=' not in item:continue
            key,value=item.split(b'=',1)
            if key.decode() in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
                values[key.decode()]=value.decode()
        assert len(values)==4 and set(values.values())=={'1'}
        p['numerical_thread_environment']=values;workers.append(p)
    value=dict(status='PASS',checked_utc=now(),parent=parent,workers=workers,live_workers=len(workers),
        freeze_sha256=sha(ROOT/'FREEZE.json'),host_launcher_returned=True,check_number=1,
        production_outcomes_inspected=False,automatic_polling=False)
    write_json(ROOT/'STARTUP_PERSISTENCE_CHECK.json',value)
    print(dict(status='PASS',parent_pid=parent['pid'],live_workers=len(workers),cpus=frozen['cpus'],automatic_polling=False))


if __name__=='__main__':main()
