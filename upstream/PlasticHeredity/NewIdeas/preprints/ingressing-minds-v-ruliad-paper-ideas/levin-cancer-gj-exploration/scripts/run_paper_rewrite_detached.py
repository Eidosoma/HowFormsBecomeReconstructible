"""Detached P6 supervisor: bounded rewrite panel, audit, no follow-on."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import paper_rewrite_design as d
from run_rewrite_tradeoff_detached import now, run_child, status, write_status

ROOT=d.ROOT
JOBS=ROOT/'runs/jobs'
RUNNER=ROOT/'scripts/run_paper_rewrite.py'
ANALYZER=ROOT/'scripts/analyze_paper_rewrite.py'
CONFIG=ROOT/'configs/paper_rewrite_v1.json'


def discover_run(job):
    log=job/'runner.log'
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            if line.startswith('Run artifacts: '):
                run=Path(line.removeprefix('Run artifacts: ')).resolve()
                if run.parent!=ROOT/'runs' or not run.name.startswith('paper-rewrite-'):
                    raise ValueError('Unexpected P6 output directory')
                return run
    return None


def launch():
    d.validate_config(json.loads(CONFIG.read_text()))
    JOBS.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'runs/paper-rewrite.lock').open('a+')
    try:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('P6 already supervised; poll instead of duplicating')
        if shutil.disk_usage(ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
        hashes=d.execution_manifest()
        input_hashes={str(p):d.digest(p) for p in d.input_paths().values()}
        job=Path(tempfile.mkdtemp(prefix='paper-rewrite-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=JOBS))
        (job/'frozen').mkdir(); frozen={}
        for p in d.LOCAL_FILES:
            if p.name in frozen: raise ValueError('Frozen filename collision')
            shutil.copyfile(p,job/'frozen'/p.name); frozen[p.name]=hashes[str(p.relative_to(ROOT))]
            if d.digest(job/'frozen'/p.name)!=frozen[p.name]: raise RuntimeError('Changed execution source')
        write_status(job/'launch.json',dict(launched_utc=now(),hashes_sha256=hashes,
            frozen_hashes_sha256=frozen,input_hashes_sha256=input_hashes,
            runner_watchdog_seconds=29100,audit_watchdog_seconds=1800,total_watchdog_seconds=31500,
            automatic_retry=False,downstream_launch=False))
        write_status(job/'status.json',dict(job=str(job),phase='launching',launched_utc=now(),
            heartbeat_utc=now(),heartbeat_epoch=time.time(),completed_cases=0,valid_cases=0,
            planned_cases=62,planned_continuation_rounds=336,completed_writing_stages=0))
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--supervise',str(job),'--lock-fd',str(lock.fileno())]
        with (job/'supervisor.log').open('x') as output:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,
                stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
    finally:
        lock.close()
    print(json.dumps(dict(job=str(job),supervisor_pid=process.pid,
        status_command=f'.venv/bin/python -B scripts/run_paper_rewrite_detached.py --status {job.relative_to(ROOT)}',
        note='A later advancing heartbeat, not just launcher success, confirms detached execution'),indent=2),flush=True)
    return 0


def supervise(job,lock_fd):
    launch_record=json.loads((job/'launch.json').read_text())
    meta=json.loads((job/'status.json').read_text())
    meta.update(supervisor_pid=os.getpid(),supervisor_session=os.getsid(0))
    deadline=time.monotonic()+31500
    def update(pid=None):
        meta.update(heartbeat_utc=now(),heartbeat_epoch=time.time())
        if pid is not None: meta['child_pid']=pid
        run=discover_run(job)
        if run is not None:
            meta['run']=str(run)
            if (run/'summary.json').exists():
                summary=json.loads((run/'summary.json').read_text())
                meta.update(completed_cases=len(summary['cases']),valid_cases=sum(bool(r['execution_pass']) for r in summary['cases']),
                    predecessor_gate=summary.get('predecessor_gate',False),
                    gate_pass=(summary.get('gate') or {}).get('quality_gate'))
                completed_rounds=0; writes=0
                for case in summary.get('registered_cases',[]):
                    if case['kind']!='rewrite': continue
                    try:
                        progress=json.loads((run/case['id']/'progress.json').read_text())
                        completed_rounds+=sum(p['phase'].startswith('r') and p['phase'].endswith('_isolated_2') for p in progress)
                        writes+=sum(p['phase']=='writing_isolated_2' for p in progress)
                    except (OSError,json.JSONDecodeError): pass
                meta.update(completed_continuation_rounds=completed_rounds,completed_writing_stages=writes)
                if meta['phase'] not in ('complete','failed','independent_audit'):
                    meta['phase']=summary.get('stage','preflight')
        write_status(job/'status.json',meta)
    def child(command,name,cap):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('Overall P6 limit')
        return run_child(command,job/name,min(cap,left),update)
    def interrupted(signum,frame): raise KeyboardInterrupt(f'Signal {signum}')
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    code=1
    try:
        if lock_fd is None: raise ValueError('Exclusive inherited lock required')
        os.fstat(lock_fd)
        if not all(d.digest(ROOT/p)==h for p,h in launch_record['hashes_sha256'].items()):
            raise RuntimeError('Execution files changed after launch')
        if not all(d.digest(job/'frozen'/p)==h for p,h in launch_record['frozen_hashes_sha256'].items()):
            raise RuntimeError('Frozen launch files changed')
        if not all(d.digest(Path(p))==h for p,h in launch_record['input_hashes_sha256'].items()):
            raise RuntimeError('P5 inputs changed after launch')
        if shutil.disk_usage(ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
        meta['phase']='preflight'; update()
        rc=child([sys.executable,'-B',str(RUNNER),'--config',str(CONFIG)],'runner.log',29100)
        meta['runner_exit_code']=rc
        if rc: raise RuntimeError(f'Runner exited {rc}; no retry or downstream launch')
        run=discover_run(job)
        if run is None: raise RuntimeError('No output identified')
        meta['phase']='independent_audit'; update()
        rc=child([sys.executable,'-B',str(ANALYZER),str(run),'--save','--compact'],'audit.log',1800)
        meta['audit_exit_code']=rc
        if rc: raise RuntimeError(f'Independent audit exited {rc}')
        audit=json.loads((run/'independent_audit.json').read_text())
        if not audit['quality_gate']: raise RuntimeError('Quality gate failed')
        meta.update(phase='complete',quality_gate=True,ready_for_interpretation=True,
            independent_checks=audit['independent_check_count'],gate_pass=audit['gate']['quality_gate'],
            selected_fine_agreement=audit['all_selected_fine_agree'],
            next_action='Review rewrite versus transmission, sham and capacity controls; no return-to-E, stress or follow-on launch')
        code=0
    except BaseException as error:
        meta.update(phase='failed',error=f'{type(error).__name__}: {error}')
        print(meta['error'],file=sys.stderr,flush=True)
    finally:
        meta.update(exit_code=code,finished_utc=now()); update()
        if lock_fd is not None: os.close(lock_fd)
    return code


def main():
    p=argparse.ArgumentParser(description=__doc__); group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--launch',action='store_true'); group.add_argument('--status',type=Path)
    group.add_argument('--supervise',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--lock-fd',type=int,help=argparse.SUPPRESS); args=p.parse_args()
    if args.status: print(json.dumps(status(args.status.resolve()),indent=2)); return 0
    if args.supervise:
        job=args.supervise.resolve()
        if job.parent!=JOBS: raise ValueError('Supervisor outside runs/jobs')
        return supervise(job,args.lock_fd)
    return launch()


if __name__=='__main__': raise SystemExit(main())
