"""One admission sample; no scientific result polling."""
from common import *
import os,shutil,time,argparse
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
def main(name):
 assert len(list(Path('/proc').glob('[0-9]*')))>16,'host namespace required'
 a=sample();time.sleep(1);b=sample()
 active={k for k,v in b.items() if v[0]=='R' or k in a and v[1]>a[k][1]}|{k for k,v in a.items() if v[0]=='R'}
 free=shutil.disk_usage(ROOT).free;cpus=[6,7]
 value=dict(recorded_utc=now(),active_project_threads=len(active),planned_workers=2,numerical_threads=1,
  ceiling=12,cpus=cpus,free_bytes=free,admission_pass=len(active)+2<=12 and set(cpus)<=os.sched_getaffinity(0) and free>=LIMIT+RESERVE,
  no_scientific_outputs_inspected=True)
 write(ROOT/name,value);print(json.dumps(value),flush=True);assert value['admission_pass']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);main(p.parse_args().name)
