"""Detached full qualification, then resource-conditional fixed development."""
from study import *
import signal, subprocess, time, traceback
import analysis, resources

LIVE=[]
def status(phase,**extra):
    data=dict(study='TT050',status=phase,updated_utc=now(),controller_pid=os.getpid(),
        priority='causal re-isolation',automatic_polling=False,automatic_retry=False,
        automatic_extension=False,automatic_successor=False,**extra)
    replace(ROOT/'CURRENT_EXECUTION.json',data)
    print(json.dumps(data),flush=True)

def stop_live():
    for p,_,_,_ in LIVE:
        if p.poll() is None:p.terminate()
    for p,_,_,_ in LIVE:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()

def phase(name,blocks,technical,limit):
    run=ROOT/'runs'/name;run.mkdir()
    resources.admission(run/'RESOURCES.json',2);verify_inputs();begin=time.monotonic();queue=list(blocks)
    elapsed=[];available=[6,7]
    write(run/'CONTRACT.json',dict(utc=now(),blocks=blocks,technical=technical,cpus=[6,7],
        limit_seconds=limit,inputs_sha256=sha(ROOT/'FROZEN.json')))
    signal.setitimer(signal.ITIMER_REAL,limit)
    try:
        while queue or LIVE:
            assert time.monotonic()-begin<limit,f'{name} hard deadline'
            guard()
            while queue and available:
                b=queue.pop(0);cpu=available.pop(0);log=(run/f'block_{b}.log').open('xb')
                cmd=['taskset','-c',str(cpu),sys.executable,'-B',str(ROOT/'engine.py'),str(run/f'block_{b}'),str(b)]
                if technical:cmd.append('--technical')
                p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=LANE)
                LIVE.append((p,b,cpu,log));write(run/f'block_{b}_PID.json',dict(pid=p.pid,cpu=cpu,block=b,utc=now()))
            for item in list(LIVE):
                p,b,cpu,log=item;code=p.poll()
                if code is None:continue
                log.close();LIVE.remove(item);available.append(cpu)
                assert code==0,f'{name} block {b} failed, exit {code}; see retained log'
                done=read(run/f'block_{b}/COMPLETE.json');assert done['status']=='COMPLETE';elapsed.append(done['seconds'])
            if queue or LIVE:time.sleep(2)
        wall=time.monotonic()-begin
        summary=analysis.analyze(run,blocks,technical=technical)
        verify_inputs();guard()
        complete=dict(status='COMPLETE',utc=now(),seconds=time.monotonic()-begin,worker_wave_seconds=wall,
            block_seconds=elapsed,summary=summary,blocks=blocks,technical=technical,bytes=size(run),
            inputs_sha256=sha(ROOT/'FROZEN.json'),outputs={str(p.relative_to(run)):sha(p)
                for p in run.rglob('*') if p.is_file() and not p.name.endswith('.log') and p.name!='STATUS.json'})
        write(run/'COMPLETE.json',complete);return complete
    except BaseException:
        stop_live();write(run/'FAILED.json',dict(status='FAILED',utc=now(),traceback=traceback.format_exc()));raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def main():
    def terminate(signum,frame):raise RuntimeError(f'Controller signal {signum}')
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);signal.signal(signal.SIGALRM,terminate)
    try:
        verify_inputs();status('QUALIFICATION_RUNNING',started_utc=now())
        q=phase('qualification_v1',[50999990,50999991],True,3600)
        forecast=1.5*4*q['worker_wave_seconds']+120
        write(ROOT/'FORECAST.json',dict(utc=now(),qualification_wave_seconds=q['worker_wave_seconds'],
            development_seconds=forecast,development_deadline_seconds=2*forecast,
            maximum_admitted_seconds=28800,admitted=forecast<=28800,
            estimated_development_bytes=4*q['bytes'],study_ceiling_bytes=STUDY_LIMIT))
        assert forecast<=28800,'Development runtime admission exceeds eight hours'
        assert size(ROOT)+4*q['bytes']<STUDY_LIMIT,'Development storage forecast exceeds two GiB'
        status('DEVELOPMENT_RUNNING',forecast_seconds=forecast,started_utc=now(),development_blocks=BLOCKS)
        p=phase('development_v1',BLOCKS,False,2*forecast)
        status('COMPLETE_AWAITING_REVIEW',development_seconds=p['seconds'],development_blocks=BLOCKS,
            report='TT050/runs/development_v1/analysis/REPORT.md',no_active_workers=True)
    except BaseException:
        stop_live();status('FAILED_PRESERVED',traceback=traceback.format_exc(),no_automatic_retry=True)
        raise

if __name__=='__main__':main()
