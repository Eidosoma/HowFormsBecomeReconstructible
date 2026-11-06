from io_utils import *
import time

def sample():
    out={}
    for p in Path('/proc').glob('[0-9]*'):
        if int(p.name)==os.getpid():continue
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if not argv or 'python' not in Path(argv[0].decode(errors='replace')).name:continue
            if '/home/robert/Random-Replications' not in str((p/'cwd').resolve()):continue
            for t in (p/'task').iterdir():
                f=(t/'stat').read_text().rsplit(')',1)[1].split();out[t.name]=(f[0],int(f[11])+int(f[12]))
        except (OSError,ValueError):pass
    return out

def admit(path):
    assert len(list(Path('/proc').glob('[0-9]*')))>16
    a=sample();time.sleep(1);b=sample()
    active={k for k,v in a.items() if v[0]=='R'}|{k for k,v in b.items() if v[0]=='R' or k in a and v[1]>a[k][1]}
    result=dict(utc=now(),active_project_threads=len(active),planned_threads=1,ceiling=12,cpu=5,
        pass_admission=len(active)+1<=12 and 5 in os.sched_getaffinity(0))
    write(path,result);assert result['pass_admission'];os.sched_setaffinity(0,{5});return result

