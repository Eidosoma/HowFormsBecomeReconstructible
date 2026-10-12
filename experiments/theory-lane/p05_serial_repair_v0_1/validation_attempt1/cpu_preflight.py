"""One bounded host CPU snapshot for shared-budget admission; not run polling."""
import argparse
import os
from pathlib import Path
import time
from common import ROOT,write,stamp


def sample():
    result={}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit() or int(directory.name)==os.getpid():continue
        try:
            command=(directory/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            executable=(directory/'exe').resolve().name
            if not executable.startswith('python'):continue
            cwd=str((directory/'cwd').resolve())
            if '/Random-Replications/' not in command and '/Random-Replications/' not in cwd:continue
            ticks={}
            for task in (directory/'task').iterdir():
                parts=(task/'stat').read_text().rsplit(')',1)[1].split()
                ticks[int(task.name)]=int(parts[11])+int(parts[12])
            stat=(directory/'stat').read_text().rsplit(')',1)[1].split()
            result[int(directory.name)]=dict(ticks=ticks,start=int(stat[19]))
        except (OSError,ValueError):continue
    return result


def main(name):
    first=sample();time.sleep(1.);second=sample()
    uptime=float(Path('/proc/uptime').read_text().split()[0]);hz=os.sysconf('SC_CLK_TCK')
    rows=[];active=0
    for pid,current in second.items():
        previous=first.get(pid,{}).get('ticks',{})
        delta={tid:max(0,ticks-previous.get(tid,ticks)) for tid,ticks in current['ticks'].items()}
        busy=sum(t>0 for t in delta.values())
        lifetime=max(1.,uptime-current['start']/hz)
        percent=100*sum(current['ticks'].values())/hz/lifetime
        # A recently busy one-thread worker can fall between scheduler slices.
        reserved=max(busy,1 if percent>=5. else 0)
        active+=reserved
        rows.append(dict(pid=pid,threads=len(current['ticks']),sampled_busy_threads=busy,
                         sampled_ticks=sum(delta.values()),lifetime_cpu_percent=percent,counted_threads=reserved))
    receipt=dict(at_utc=stamp(),processes=rows,other_active_or_recently_busy_threads=active,
                 planned_threads=1,shared_limit=12,within_limit=active+1<=12,
                 method='One-second project Python task tick sample, with one-thread reserve for lifetime CPU >=5%; no scientific run polling.')
    write(ROOT/name,receipt)
    assert receipt['within_limit'],f'No CPU slot: {active} other busy project threads'
    print(f'Shared CPU admission: {active} other active/reserved threads + 1 planned <= 12.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    main(p.parse_args().output)
