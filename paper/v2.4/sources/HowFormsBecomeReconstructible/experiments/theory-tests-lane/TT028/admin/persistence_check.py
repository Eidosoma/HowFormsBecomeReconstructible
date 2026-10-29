"""One host-level startup check after the detached launcher has returned."""
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import common as c

def process(pid):
    path=Path('/proc')/str(pid)
    fields=(path/'stat').read_text().rsplit(')',1)[1].split()
    assert fields[0] not in ('Z','X')
    return dict(pid=pid,state=fields[0],parent_pid=int(fields[1]),cpu_ticks=int(fields[11])+int(fields[12]),
        start_ticks=int(fields[19]),cpus=sorted(os.sched_getaffinity(pid)),threads=len(list((path/'task').iterdir())))

def main():
    launch=c.read_json(ROOT/'LAUNCH.json');frozen=c.read_json(ROOT/'FREEZE.json')
    assert launch['status']=='DETACHED_STARTED'
    directory=ROOT/'runs/confirmation_v1'
    assert not (directory/'FAILED.json').exists()
    running=c.read_json(directory/'RUNNING.json')
    assert running['inputs']==frozen['inputs'] and running['freeze_sha256']==c.sha(ROOT/'FREEZE.json')
    assert running['pid']==launch['pid'] and running['workers']==2
    main_process=process(launch['pid'])
    argv=(Path('/proc')/str(launch['pid'])/'cmdline').read_bytes().split(b'\0')
    assert str(ROOT/'execute.py').encode() in argv and b'--execute' in argv
    assert main_process['cpus']==frozen['cpus']
    workers=[]
    deadline=time.monotonic()+15
    while not all((directory/f'worker_{index}.json').exists() for index in frozen['blocks'][:2]):
        assert time.monotonic()<deadline,'worker startup receipts missing'
        time.sleep(.05)
    for index in frozen['blocks'][:2]:
        receipt=c.read_json(directory/f'worker_{index}.json');observed=process(receipt['pid'])
        assert receipt['numerical_threads']==1 and observed['threads']==1
        assert observed['parent_pid']==launch['pid'] and observed['cpus']==[receipt['cpu']]
        workers.append(dict(block=index,receipt_sha256=c.sha(directory/f'worker_{index}.json'),**observed))
    assert {v['cpus'][0] for v in workers}==set(frozen['cpus'])
    value=dict(status='PASS',recorded_utc=c.now(),main_pid=launch['pid'],main=main_process,workers=workers,
        checked_after_launching_command_returned=True,namespace=str(Path('/proc/self/ns/pid').resolve()),
        startup_check_only=True,scientific_effects_inspected=False,completed_batch_counts_inspected=False,
        automatic_followup_polling=False,code_sha256=c.sha(__file__),launch_sha256=c.sha(ROOT/'LAUNCH.json'))
    c.write_json(ROOT/'STARTUP_PERSISTENCE_CHECK.json',value)
    print({k:v for k,v in value.items() if k not in ('namespace',)},flush=True)
if __name__=='__main__':main()
