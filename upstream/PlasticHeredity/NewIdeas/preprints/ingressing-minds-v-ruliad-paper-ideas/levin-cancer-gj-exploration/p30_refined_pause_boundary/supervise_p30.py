"""Bounded detached P30 verification, preflight, execution and final audit."""
import argparse
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import p30_design as d
from run_rewrite_tradeoff_detached import terminate_owned

def now(): return datetime.now(timezone.utc).isoformat()
def child_env(job):
    cache=job/'cache'; temporary=job/'tmp'
    cache.mkdir(exist_ok=True); temporary.mkdir(exist_ok=True)
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(cache/'matplotlib'),XDG_CACHE_HOME=str(cache),TMPDIR=str(temporary),
        P30_TEST_ROOT=str(temporary),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    return env

def discover_run(job):
    path=job/'runner.log'
    if path.exists():
        for line in path.read_text(errors='replace').splitlines():
            if line.startswith('Run artifacts: '):
                run=Path(line.removeprefix('Run artifacts: ')); d.check_run_path(run); return run
    return None

def run_child(command,job,name,timeout,update):
    with (job/name).open('x') as output:
        process=subprocess.Popen(command,cwd=d.ROOT,env=child_env(job),stdin=subprocess.DEVNULL,
            stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+timeout
        try:
            while process.poll() is None:
                update(process.pid)
                if time.monotonic()>=deadline: return 124
                time.sleep(min(5,max(.001,deadline-time.monotonic())))
            return process.returncode
        finally: terminate_owned(process)

def supervise(job,lock_fd):
    meta=d.read(job/'status.json'); meta.update(supervisor_pid=os.getpid(),supervisor_session=os.getsid(0))
    deadline=time.monotonic()+d.FIXED['overall_timeout_seconds']
    def update(pid=None):
        meta.update(heartbeat_utc=now(),heartbeat_epoch=time.time(),external_free_gib=shutil.disk_usage(job).free/1024**3)
        if pid is not None: meta['child_pid']=pid
        run=discover_run(job)
        if run is not None and (run/'summary.json').exists():
            summary=d.read(run/'summary.json'); rows=summary['cases']
            meta.update(run=str(run),completed_cases=len(rows),valid_cases=sum(bool(r['execution_pass']) for r in rows),
                completed_integrations=sum(len(r.get('result',{}).get('phases',[])) for r in rows),
                stage_gates={s:g['quality_gate'] for s,g in summary['gates'].items()},predecessor_gate=summary['predecessor_gate'])
            if meta['phase'] not in ('complete','failed','software_verification','independent_audit'):
                meta['phase']=summary['stage']
        d.write_json(job/'status.json',meta)
    def child(args,name,cap):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('Overall P30 watchdog')
        return run_child([sys.executable,'-B',*args],job,name,min(cap,left),update)
    def interrupted(signum,frame): raise KeyboardInterrupt('Signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    code=1
    try:
        if lock_fd is None: raise ValueError('Exclusive inherited P30 lock required')
        os.fstat(lock_fd); d.verify_launch(job)
        if not d.space_available(job): raise RuntimeError('Require five GiB external reserve')
        meta['phase']='software_verification'; update()
        rc=child(['-m','unittest','discover','-s',str(d.HERE),'-p','test_p30.py'],
            'verification.log',d.FIXED['verification_timeout_seconds'])
        meta['verification_exit_code']=rc; update()
        if rc: raise RuntimeError('P30 software verification failed; no science launch')
        content=(job/'verification.log').read_text(); match=re.search(r'Ran (\d+) tests in ([0-9.]+)s\s+OK\s*$',content)
        if not match or int(match[1])!=d.FIXED['software_tests']: raise RuntimeError('Missing complete P30 verification evidence')
        meta.update(verification_log_sha256=d.digest(job/'verification.log'),verification_tests=int(match[1]),
            verification_seconds=float(match[2]))
        d.verify_launch(job); meta['phase']='preflight'; update()
        rc=child([str(d.HERE/'run_p30.py'),'--run',str(job)],'runner.log',d.FIXED['total_budget_seconds'])
        meta['runner_exit_code']=rc
        if rc: raise RuntimeError('P30 runner failed; no retry')
        run=discover_run(job)
        if run is None: raise RuntimeError('Missing P30 output')
        meta['phase']='independent_audit'; update()
        rc=child([str(d.HERE/'analyze_p30.py'),str(run)],'audit.log',d.FIXED['audit_timeout_seconds'])
        meta['audit_exit_code']=rc
        if rc: raise RuntimeError('P30 final independent audit failed')
        report=d.read(run/'independent_audit.json')
        if not report['quality_gate']: raise RuntimeError('P30 quality gate failed')
        meta.update(phase='complete',quality_gate=True,ready_for_interpretation=True,
            independent_checks=report['independent_check_count'],all_numerical_agree=report['all_numerical_agree'],source_precision_agrees=report['all_source_comparisons_agree'],
            qualified_pause_schedules=[x['condition'] for x in report['across_backgrounds'] if x['qualified_across_all_backgrounds']],
            next_action='Review the refined boundary and transmission results; P27 remains stopped; no downstream launch')
        code=0
    except BaseException as error:
        meta.update(phase='failed',error=type(error).__name__+': '+str(error)); print(meta['error'],file=sys.stderr,flush=True)
    finally:
        meta.update(finished_utc=now(),exit_code=code); update()
        if lock_fd is not None: os.close(lock_fd)
    return code

def launch():
    if (d.ROOT/'storage/p30-active.json').exists(): raise RuntimeError('P30 already registered as launched; inspect status instead of retrying')
    pre=d.read(d.ROOT/'storage/p30-prelaunch-verification.json')
    if not (pre.get('passed') is True and pre.get('exit_code')==0 and pre.get('tests')==d.FIXED['software_tests']
        and pre.get('hashes_sha256')==d.manifest() and d.digest(Path(pre['log']))==pre.get('log_sha256')):
        raise RuntimeError('Complete unchanged P30 prelaunch verification required')
    d.validate_config(d.read(d.HERE/'config.json')); d.source_check(); evidence=d.completed_evidence()
    if d.read(d.STORE/'workspace.json')['root']!=str(d.ROOT): raise ValueError('Foreign external store')
    if not d.space_available(d.STORE): raise RuntimeError('Require five GiB external reserve')
    lock=(d.ROOT/'runs/p30-refined-pause-boundary.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        d.JOBS.mkdir(parents=True,exist_ok=True); d.RUNS.mkdir(parents=True,exist_ok=True)
        job=Path(tempfile.mkdtemp(prefix='p30-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.JOBS))
        hashes=d.freeze(job); d.write_json(job/'input_manifest.json',d.input_manifest())
        d.write_json(job/'launch.json',dict(launched_utc=now(),hashes_sha256=hashes,inherited_verification=evidence,
            prelaunch_verification_sha256=d.digest(d.ROOT/'storage/p30-prelaunch-verification.json'),prelaunch_log_sha256=pre['log_sha256'],
            input_manifest_sha256=d.digest(job/'input_manifest.json'),planned_cases=856,planned_integrations=7352,
            numerical_pairs=428,source_pairs=214,automatic_retry=False,downstream_launch=False,output_reserve_gib=5,
            verification_watchdog_seconds=7200,runner_watchdog_seconds=1209600,audit_watchdog_seconds=43200,
            overall_watchdog_seconds=1296000))
        d.write_json(job/'status.json',dict(job=str(job),phase='launching',launched_utc=now(),heartbeat_utc=now(),
            heartbeat_epoch=time.time(),planned_cases=856,planned_integrations=7352,completed_cases=0,completed_integrations=0))
        with (job/'supervisor.log').open('x') as output:
            process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--supervise',str(job),
                '--lock-fd',str(lock.fileno())],cwd=d.ROOT,env=child_env(job),stdin=subprocess.DEVNULL,
                stdout=output,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
        pointer=dict(job=str(job),supervisor_pid=process.pid,launched_utc=now(),external_outputs=True)
        d.write_json(d.ROOT/'storage/p30-active.json',pointer)
    finally: lock.close()
    print(__import__('json').dumps(pointer,indent=2),flush=True); return 0

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--launch',action='store_true'); g.add_argument('--supervise',type=Path); g.add_argument('--status',type=Path)
    p.add_argument('--lock-fd',type=int); args=p.parse_args()
    if args.status:
        value=d.read(args.status/'status.json'); value['heartbeat_age_seconds']=time.time()-value['heartbeat_epoch']
        print(__import__('json').dumps(value,indent=2)); return 0
    if args.supervise:
        job=args.supervise.absolute()
        if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P30 job directory')
        return supervise(job,args.lock_fd)
    return launch()

if __name__=='__main__': raise SystemExit(main())
