"""Single host persistence check; never inspect scientific results."""
import sys,os,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
def main():
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 assert not (ROOT/'STARTUP_PERSISTENCE_CHECK.json').exists()
 launch=read(ROOT/'QUEUE_LAUNCH.json');age=(datetime.now(timezone.utc)-datetime.fromisoformat(launch['acknowledged_utc'])).total_seconds()
 if age<15:time.sleep(15-age)
 pid=launch['pid'];proc=Path('/proc')/str(pid);stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
 assert stat[0] not in ('Z','X') and os.getpgid(pid)==pid and os.sched_getaffinity(pid)=={6,7}
 assert not (ROOT/'QUEUE_FAILED.json').exists()
 current=read(ROOT/'QUEUE_STATUS.json');assert current['phase']=='QUALIFICATION_RUNNING'
 workers=[]
 for p in sorted((ROOT/'runs/qualification_v1').glob('worker_*.json')):
  w=read(p);wp=Path('/proc')/str(w['pid']);s=(wp/'stat').read_text().rsplit(')',1)[1].split()
  assert s[0] not in ('Z','X') and os.sched_getaffinity(w['pid'])=={w['cpu']} and os.getpriority(os.PRIO_PROCESS,w['pid'])==0
  workers.append(w)
 assert len(workers)==2 and {w['cpu'] for w in workers}=={6,7}
 value=dict(status='PASS',recorded_utc=now(),pid=pid,phase_at_observation=current['phase'],workers=workers,
  one_persistence_check=True,scientific_results_inspected=False,post_startup_result_polling=False,
  current_dynamic_status='TT043/QUEUE_STATUS.json')
 write(ROOT/'STARTUP_PERSISTENCE_CHECK.json',value);print(json.dumps(value),flush=True)
if __name__=='__main__':main()
