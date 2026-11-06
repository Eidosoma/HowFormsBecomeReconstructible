"""One host admission per phase; numerical workers each use one CPU."""
from study import *
import time

def sample():
    result={}
    for p in Path('/proc').glob('[0-9]*'):
        if int(p.name)==os.getpid():continue
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if not argv or 'python' not in Path(argv[0].decode(errors='replace')).name:continue
            if '/home/robert/Random-Replications' not in str((p/'cwd').resolve()):continue
            for t in (p/'task').iterdir():
                stat=(t/'stat').read_text().rsplit(')',1)[1].split();result[t.name]=(stat[0],int(stat[11])+int(stat[12]))
        except (OSError,ValueError):pass
    return result

def admission(path,workers):
    assert len(list(Path('/proc').glob('[0-9]*')))>16,'Host process visibility is required'
    a=sample();time.sleep(1);b=sample()
    active={k for k,v in a.items() if v[0]=='R'}|{k for k,v in b.items() if v[0]=='R' or k in a and v[1]>a[k][1]}
    cpus=[6,7][:workers];free=shutil.disk_usage(ROOT).free
    decision=dict(utc=now(),planned_cpus=cpus,workers=workers,numerical_threads_per_worker=1,
        active_project_threads=len(active),ceiling=12,free_bytes=free,
        pass_admission=len(active)+workers<=12 and set(cpus)<=os.sched_getaffinity(0) and free>=RESERVE+STUDY_LIMIT)
    write(path,decision);assert decision['pass_admission'],'CPU/storage admission failed'
    return decision

