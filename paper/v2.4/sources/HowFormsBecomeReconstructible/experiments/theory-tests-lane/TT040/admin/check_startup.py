"""One host persistence observation of the TT040 queue; no scientific results."""
from pathlib import Path
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
launch=read(ROOT/'QUEUE_LAUNCH.json');pid=launch['pid'];p=Path(f'/proc/{pid}')
stat=(p/'stat').read_text().rsplit(')',1)[1].split()
assert stat[0] not in ('Z','X') and os.getpgid(pid)==pid
assert os.getpriority(os.PRIO_PROCESS,pid)==0 and os.sched_getaffinity(pid)=={6,7}
assert (p/'cwd').resolve()==LANE and (p/'fd/0').resolve()==Path('/dev/null')
assert (p/'fd/1').resolve()==ROOT/'queue.log'
argv=(p/'cmdline').read_bytes().split(b'\0')
assert b'--run' in argv and any(b'TT040/admin/controller.py' in s for s in argv)
status=read(ROOT/'QUEUE_STATUS.json')
write(ROOT/'QUEUE_STARTUP_CHECK.json',dict(status='PASS',recorded_utc=now(),pid=pid,process_state=stat[0],
    nice=0,cpus=[6,7],phase_at_single_startup_check=status['phase'],latest_queue_state=status,
    detached_after_launcher_return=True,science_results_inspected=False,automatic_result_polling=False))
print(dict(status='PASS',pid=pid,phase=status['phase'],science_results_inspected=False))
