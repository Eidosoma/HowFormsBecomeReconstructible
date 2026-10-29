"""One short resource-only admission sample; no other scientific files read."""
import argparse
import os
from pathlib import Path
import shutil
import time
from common import ROOT,now,write_json,sha

def sample():
    result={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if not argv or 'python' not in Path(argv[0].decode(errors='replace')).name:continue
            if '/home/robert/Random-Replications' not in str((p/'cwd').resolve()):continue
            script=next((Path(x.decode()).name for x in argv[1:] if x.endswith(b'.py')),'python')
            for task in (p/'task').iterdir():
                fields=(task/'stat').read_text().rsplit(')',1)[1].split()
                result[task.name]=dict(pid=int(p.name),script=script,state=fields[0],ticks=int(fields[11])+int(fields[12]))
        except (OSError,ValueError):pass
    return result

def main(name):
    first=sample();tick=time.monotonic();time.sleep(1);second=sample()
    active={k for k,v in second.items() if v['state']=='R' or (k in first and v['ticks']>first[k]['ticks'])}
    active|={k for k,v in first.items() if v['state']=='R'}
    value=dict(recorded_utc=now(),planned_workers=2,numerical_threads=1,cpus=sorted(os.sched_getaffinity(0))[-2:],
        observed_project_threads_including_sleeping=len(second),active_or_cpu_consuming_threads=len(active),
        active_threads=[dict(tid=int(k),**second.get(k,first.get(k))) for k in sorted(active,key=int)],
        sample_seconds=time.monotonic()-tick,free_bytes=shutil.disk_usage(ROOT).free,ceiling=12,
        admission_pass=len(active)+2<=12 and shutil.disk_usage(ROOT).free>=3*1024**3,
        scientific_outputs_inspected=False,resource_script_sha256=sha(__file__),automatic_polling=False)
    write_json(ROOT/name,value)
    print({k:value[k] for k in ('recorded_utc','active_or_cpu_consuming_threads','planned_workers','admission_pass','free_bytes')},flush=True)
    assert value['admission_pass'],'shared-resource admission'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);main(parser.parse_args().name)
