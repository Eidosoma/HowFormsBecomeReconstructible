"""Admit and detach saved-data verification; perform no scientific acquisition."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c
import execute
import resources


def launch():
    assert len(list(Path('/proc').glob('[0-9]*'))) > 16, 'host launch required'
    plan = c.read_json(ROOT/'SAVED_CLOSEOUT_PLAN.json')
    c.verify(plan['code_and_evidence'])
    frozen = c.read_json(ROOT/'FREEZE.json')
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    assert c.runtime_hashes() == frozen['inputs'] and execute.environment() == frozen['environment']
    first = resources.sample(); time.sleep(1); second = resources.sample()
    active = {k for k, v in second.items() if v['state'] == 'R' or
              (k in first and v['ticks'] > first[k]['ticks'])}
    active |= {k for k, v in first.items() if v['state'] == 'R'}
    resource_check = dict(recorded_utc=c.now(), planned_workers=2, numerical_threads=1,
        active_project_threads=len(active), active_threads=[dict(tid=int(k), **second.get(k, first.get(k)))
            for k in sorted(active, key=int)], ceiling=12, free_bytes=shutil.disk_usage(ROOT).free,
        cpus=plan['cpus'], scientific_outputs_inspected=False,
        admission_pass=len(active)+2 <= 12 and shutil.disk_usage(ROOT).free >= 8*1024**3)
    c.write_json(ROOT/'SAVED_CLOSEOUT_RESOURCE_CHECK.json', resource_check)
    assert resource_check['admission_pass'], 'shared resource admission'
    os.sched_setaffinity(0, set(plan['cpus']))
    assert not (ROOT/'checks/closeout_v1').exists()
    rd, wr = os.pipe()
    log = ROOT/'saved_closeout_v1.log'
    with log.open('xb') as stream:
        process = subprocess.Popen(['bash', str(c.LANE/'run_python.sh'), str(ROOT/'saved_closeout.py')],
            cwd=c.LANE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=True, pass_fds=(wr,),
            env=dict(os.environ, TT028_CLOSEOUT_READY_FD=str(wr)))
    os.close(wr)
    ready = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if ready else b''
    os.close(rd)
    ack = datetime.now(timezone.utc)
    receipt = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        acknowledged_utc=ack.isoformat(), pid=process.pid, log=str(log),
        plan_sha256=c.sha(ROOT/'SAVED_CLOSEOUT_PLAN.json'), workers=2, numerical_threads=1,
        cpus=plan['cpus'], forecast_seconds=plan['forecast_seconds'], deadline_seconds=plan['deadline_seconds'],
        forecast_completion_utc=(ack+timedelta(seconds=plan['forecast_seconds'])).isoformat(),
        deadline_utc=(ack+timedelta(seconds=plan['deadline_seconds'])).isoformat(),
        new_dynamics=0, new_receiving_assays=0, automatic_polling=False,
        automatic_retry=False, automatic_extension=False, automatic_successor=False)
    c.write_json(ROOT/'SAVED_CLOSEOUT_LAUNCH.json', receipt)
    assert message == b'READY\n', receipt
    print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == '__main__':
    launch()
