"""One host CPU/storage admission sample, without inspecting running results."""
from common import *
import argparse,os,shutil,time

def sample():
    result={}
    for p in Path('/proc').glob('[0-9]*'):
        if int(p.name)==os.getpid():continue
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if not argv or 'python' not in Path(argv[0].decode(errors='replace')).name:continue
            if '/home/robert/Random-Replications' not in str((p/'cwd').resolve()):continue
            for task in (p/'task').iterdir():
                fields=(task/'stat').read_text().rsplit(')',1)[1].split()
                result[task.name]=dict(pid=int(p.name),state=fields[0],ticks=int(fields[11])+int(fields[12]))
        except (OSError,ValueError):pass
    return result
def main(name):
    assert len(list(Path('/proc').glob('[0-9]*')))>16,'host namespace required'
    a=sample();time.sleep(1);b=sample()
    active={k for k,v in b.items() if v['state']=='R' or (k in a and v['ticks']>a[k]['ticks'])}
    active|={k for k,v in a.items() if v['state']=='R'}
    free=shutil.disk_usage(ROOT).free;cpus=sorted(os.sched_getaffinity(0))[-2:]
    value=dict(recorded_utc=now(),active_project_threads=len(active),planned_workers=2,numerical_threads=1,
        ceiling=12,cpus=cpus,free_bytes=free,admission_pass=len(active)+2<=12 and free>=8*1024**3 and len(cpus)==2,
        no_scientific_outputs_inspected=True)
    write(ROOT/name,value);print(value,flush=True);assert value['admission_pass']
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);main(p.parse_args().name)
