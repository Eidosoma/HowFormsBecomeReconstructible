"""One host-wide project thread snapshot; no scientific status/outcome access."""
from pc_common import *
import time


def sample():
    rows={}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:
            if not (entry/'exe').resolve().name.startswith('python'):continue
            command=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if '/Random-Replications/' not in command and '/Random-Replications/' not in str((entry/'cwd').resolve()):continue
            ticks={}
            for task in (entry/'task').iterdir():
                stat=(task/'stat').read_text().rsplit(')',1)[1].split()
                ticks[int(task.name)]=int(stat[11])+int(stat[12])
            stat=(entry/'stat').read_text().rsplit(')',1)[1].split()
            rows[int(entry.name)]=dict(ticks=ticks,start=int(stat[19]))
        except (OSError,ValueError):continue
    return rows


def admission():
    first=sample();time.sleep(1.);second=sample()
    uptime=float(Path('/proc/uptime').read_text().split()[0]);hz=os.sysconf('SC_CLK_TCK');rows=[]
    for pid,r in second.items():
        previous=first.get(pid,{}).get('ticks',{})
        busy=sum(v-previous.get(t,v)>0 for t,v in r['ticks'].items())
        percent=100*sum(r['ticks'].values())/hz/max(1,uptime-r['start']/hz)
        rows.append(dict(pid=pid,threads=len(r['ticks']),sampled_busy_threads=busy,
                         lifetime_cpu_percent=percent,counted_threads=max(busy,int(percent>=5))))
    active=sum(r['counted_threads'] for r in rows)
    return dict(utc=utc(),processes=rows,other_active_or_recently_busy_threads=active,
                shared_limit=12,available_worker_slots=max(0,11-active),parent_thread_reserved=True,
                method='One-second project Python task-tick sample plus recent-worker reserve; no scientific outcome access.')
