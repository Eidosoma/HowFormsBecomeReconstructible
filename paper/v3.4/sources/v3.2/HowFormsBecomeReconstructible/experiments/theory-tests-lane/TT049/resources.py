"""One host CPU/storage admission per phase; no archive monitoring."""
from study import *
import os,time

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
def main(name,phase):
 assert phase in ('preflight','qualification','production') and len(list(Path('/proc').glob('[0-9]*')))>16
 a=sample();time.sleep(1);b=sample()
 active={k for k,v in b.items() if v[0]=='R' or k in a and v[1]>a[k][1]}|{k for k,v in a.items() if v[0]=='R'}
 cpus=[6] if phase=='preflight' else [6,7]
 bound=phase_bytes('qualification' if phase=='preflight' else phase);free=shutil.disk_usage(ROOT).free
 value=dict(recorded_utc=now(),phase=phase,cpus=cpus,planned_workers=len(cpus),numerical_threads=1,
  active_project_threads=len(active),ceiling=12,free_bytes=free,output_bound=bound,reserve_bytes=RESERVE,
  admission_pass=len(active)+len(cpus)<=12 and set(cpus)<=os.sched_getaffinity(0) and free>=RESERVE+bound)
 write(ROOT/name,value);assert value['admission_pass'];print(json.dumps(value),flush=True);return value

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('phase');a=p.parse_args();main(a.name,a.phase)
