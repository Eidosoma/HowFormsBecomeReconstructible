"""Detached P19 supervisor: software verification, equal-time preparation, onward panel and final audit."""
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

import paper_preparation_support_design as d
from run_rewrite_tradeoff_detached import now, run_child, status, write_status

ROOT=d.ROOT
JOBS=ROOT/'runs/jobs'
RUNNER=ROOT/'scripts/run_paper_preparation_support.py'
ANALYZER=ROOT/'scripts/analyze_paper_preparation_support.py'
CONFIG=ROOT/'configs/paper_preparation_support_v1.json'

def space_available():
    return all(shutil.disk_usage(p).free>=5*1024**3 for p in (ROOT,d.STORE))

def watcher_health(job,pid):
    value=json.loads((job/'storage-watcher-status.json').read_text())
    from datetime import datetime,timezone
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(value['heartbeat_utc'])).total_seconds()
    if value.get('job')!=str(job) or value.get('pid')!=pid or value.get('phase')!='watching' or not 0<=age<120:
        raise RuntimeError('Storage watcher failed or heartbeat stale')
    return value

def start_storage_watcher(job):
    result=subprocess.run([sys.executable,'-B',str(ROOT/'storage/artifact_storage_v2.py'),'--start-watch',str(job)],
        cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
    if result.returncode: raise RuntimeError('Storage watcher start failed: '+result.stderr[-2000:])
    launch=json.loads(result.stdout); pid=launch['pid']; deadline=time.monotonic()+10
    while not (job/'storage-watcher-status.json').exists() and time.monotonic()<deadline: time.sleep(.1)
    watcher_health(job,pid)
    return pid


def verification_manifest():
    paths=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'configs').glob('*.json'))
    return {str(p.relative_to(ROOT)):d.digest(p) for p in sorted(paths)}


def discover_run(job):
    log=job/'runner.log'
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            if line.startswith('Run artifacts: '):
                run=Path(line.removeprefix('Run artifacts: ')).resolve()
                if run.parent!=ROOT/'runs' or not run.name.startswith('paper-preparation-support-'):
                    raise ValueError('Unexpected P19 output directory')
                return run
    return None


def launch():
    d.validate_config(json.loads(CONFIG.read_text()))
    JOBS.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'runs/paper-preparation-support.lock').open('a+')
    try:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('P19 already supervised; poll instead of duplicating')
        if not space_available(): raise RuntimeError('Require 5 GiB free on both filesystems')
        hashes=d.execution_manifest()
        input_hashes={str(p):d.digest(p) for p in d.input_paths().values()}
        job=Path(tempfile.mkdtemp(prefix='paper-preparation-support-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=JOBS))
        (job/'frozen').mkdir(); frozen={}
        for p in d.LOCAL_FILES:
            if p.name in frozen: raise ValueError('Frozen filename collision')
            shutil.copyfile(p,job/'frozen'/p.name); frozen[p.name]=hashes[str(p.relative_to(ROOT))]
            if d.digest(job/'frozen'/p.name)!=frozen[p.name]: raise RuntimeError('Changed execution source')
        write_status(job/'launch.json',dict(launched_utc=now(),hashes_sha256=hashes,
            frozen_hashes_sha256=frozen,input_hashes_sha256=input_hashes,
            verification_hashes_sha256=verification_manifest(),verification_watchdog_seconds=7200,
            runner_watchdog_seconds=108300,audit_watchdog_seconds=21600,total_watchdog_seconds=144000,
            automatic_retry=False,downstream_launch=False))
        write_status(job/'status.json',dict(job=str(job),phase='launching',launched_utc=now(),
            heartbeat_utc=now(),heartbeat_epoch=time.time(),completed_cases=0,valid_cases=0,
            planned_cases=192,case_ceiling=192,minimum_cases=192,completed_replacements=0,stage_gates={}))
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--supervise',str(job),'--lock-fd',str(lock.fileno())]
        with (job/'supervisor.log').open('x') as output:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,
                stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
    finally:
        lock.close()
    print(json.dumps(dict(job=str(job),supervisor_pid=process.pid,
        status_command=f'.venv/bin/python -B scripts/run_paper_preparation_support_detached.py --status {job.relative_to(ROOT)}',
        note='A later advancing heartbeat, not just launcher success, confirms detached execution'),indent=2),flush=True)
    return 0


def supervise(job,lock_fd):
    launch_record=json.loads((job/'launch.json').read_text())
    meta=json.loads((job/'status.json').read_text())
    meta.update(supervisor_pid=os.getpid(),supervisor_session=os.getsid(0))
    deadline=time.monotonic()+144000
    def update(pid=None):
        meta.update(heartbeat_utc=now(),heartbeat_epoch=time.time())
        if pid is not None: meta['child_pid']=pid
        if meta.get('storage_watcher_pid') and meta['phase'] not in ('complete','failed'):
            health=watcher_health(job,meta['storage_watcher_pid'])
            meta['storage_watcher_heartbeat']=health['heartbeat_utc']
            meta['large_files_relocated']=health['files_moved']
        run=discover_run(job)
        if run is not None:
            meta['run']=str(run)
            if (run/'summary.json').exists():
                summary=json.loads((run/'summary.json').read_text())
                meta.update(completed_cases=len(summary['cases']),valid_cases=sum(bool(r['execution_pass']) for r in summary['cases']),
                    predecessor_gate=summary.get('predecessor_gate',False),registered_cases=len(summary['registered_cases']))
                meta['stage_gates']={k:dict(quality_gate=v['quality_gate'],eligible=v['eligible']) for k,v in summary.get('gates',{}).items()}
                if summary.get('stage')=='finished':
                    meta['planned_cases']=len(summary['cases'])
                    meta['completion_reason']=summary.get('completion_reason')
                meta['completed_replacements']=0
                for case in summary['registered_cases']:
                    path=run/case['id']/'turnover_progress.json'
                    if path.exists(): meta['completed_replacements']+=len(json.loads(path.read_text())['replacements'])
                if meta['phase'] not in ('complete','failed','independent_audit','software_verification'):
                    meta['phase']=summary.get('stage','preflight')
        write_status(job/'status.json',meta)
    def child(command,name,cap):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('Overall P19 limit')
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
            raise RuntimeError('Historical inputs changed after launch')
        if not space_available(): raise RuntimeError('Require 5 GiB free on both filesystems')
        if launch_record.get('verification_hashes_sha256',{})!=verification_manifest():
            raise RuntimeError('Verification sources changed after launch')
        meta['storage_watcher_pid']=start_storage_watcher(job)
        meta['phase']='software_verification'; update()
        rc=child([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'scripts'),'-p','test_*.py'],
                 'verification.log',7200)
        meta['verification_exit_code']=rc
        if rc: raise RuntimeError(f'Software verification exited {rc}; no biological runner launch')
        meta['verification_log_sha256']=d.digest(job/'verification.log')
        if launch_record.get('verification_hashes_sha256',{})!=verification_manifest():
            raise RuntimeError('Verification sources changed during tests')
        if not all(d.digest(ROOT/p)==h for p,h in launch_record['hashes_sha256'].items()):
            raise RuntimeError('Execution files changed during tests')
        meta['phase']='preflight'; update()
        rc=child([sys.executable,'-B',str(RUNNER),'--config',str(CONFIG)],'runner.log',108300)
        meta['runner_exit_code']=rc
        if rc: raise RuntimeError(f'Runner exited {rc}; no retry or downstream launch')
        run=discover_run(job)
        if run is None: raise RuntimeError('No output identified')
        meta['phase']='independent_audit'; update()
        rc=child([sys.executable,'-B',str(ANALYZER),str(run),'--save','--compact'],'audit.log',21600)
        meta['audit_exit_code']=rc
        if rc: raise RuntimeError(f'Independent audit exited {rc}')
        audit=json.loads((run/'independent_audit.json').read_text())
        if not audit['quality_gate']: raise RuntimeError('Quality gate failed')
        meta.update(phase='complete',quality_gate=True,ready_for_interpretation=True,
            independent_checks=audit['independent_check_count'],
            selected_fine_agreement=audit['all_fine_agree'],readout_capacity=audit['readout_capacity'],
            mode_contrasts=audit['mode_contrasts'],benchmark_consistency=audit['benchmark_consistency'],chain_outcomes=audit['chain_outcomes'],
            next_action='Review equal-time preparation modes, benchmark consistency and actual-cell onward transmission; no follow-on launch')
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
