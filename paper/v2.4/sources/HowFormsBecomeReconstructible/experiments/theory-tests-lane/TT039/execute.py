"""Bounded stop-writing body intervention; detached above the 600-second forecast."""
from common import *
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing,os,resource,select,shutil,signal,subprocess,time,traceback
import argparse,scipy
import analysis,run

LIMIT=32*1024**3
RESERVE=8*1024**3
def environment():
    return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,numerical_threads={k:os.environ.get(k) for k in
        ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
def worker(directory,index,role,cpu):
    os.sched_setaffinity(0,{cpu});assert os.getpriority(os.PRIO_PROCESS,0)==0
    directory=Path(directory);write(directory/f'worker_{index}.json',dict(pid=os.getpid(),cpu=cpu,nice=0,started_utc=now()))
    result=run.block(directory/f'tissue_{index}',index,role)
    return dict(receipt=result,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
def batch(directory,indices,role,cpus):
    pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
    try:
        pending={pool.submit(worker,str(directory),i,role,cpus[n]):i for n,i in enumerate(indices)}
        result={pending[f]:f.result() for f in as_completed(pending)}
        pool.shutdown(wait=True);return result
    except BaseException:
        for p in list((pool._processes or {}).values()):p.terminate()
        pool.shutdown(wait=True,cancel_futures=True);raise
def execute(role,name,resource_name):
    assert role in ('benchmark','confirmation')
    code=inputs();cpus=sorted(os.sched_getaffinity(0))[-2:];env=environment()
    assert len(cpus)==2 and set(env['numerical_threads'].values())=={'1'}
    admission=read(ROOT/resource_name)
    assert admission['admission_pass'] and admission['cpus']==cpus
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    frozen=read(ROOT/'FREEZE.json') if role=='confirmation' else None
    manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence'])
    if frozen:
        assert frozen['inputs']==code and frozen['environment']==env and frozen['cpus']==cpus
        verify(frozen['evidence']);assert name==frozen['run_name']
        if frozen['forecast_seconds']>600:assert os.environ.get('TT039_DETACHED')=='1'
    directory=ROOT/'runs'/name;directory.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();deadline=frozen['deadline_seconds'] if frozen else 600
    def expire(*_):raise TimeoutError(f'TT039 {deadline}-second limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
    write(directory/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=code,
        workers=2,numerical_threads=1,cpus=cpus,deadline_seconds=deadline,automatic_polling=False,
        freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None))
    fd=os.environ.pop('TT039_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        snapshot=directory/'input_code';snapshot.mkdir()
        for p in ROOT.iterdir():
            if p.suffix=='.py' or p.name in ('PROTOCOL.md','SOURCE_MANIFEST.json','RESERVATION.json','RESERVATION_REVIEW.json','RANDOMNESS.json'):shutil.copyfile(p,snapshot/p.name)
        indices=selected(role);result={}
        for offset in range(0,len(indices),2):
            assert shutil.disk_usage(ROOT).free>=RESERVE
            assert sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())<LIMIT
            result.update(batch(directory,indices[offset:offset+2],role,cpus))
            print(json.dumps(dict(stage='saved_blocks_verified',completed_blocks=len(result),total_blocks=len(indices))),flush=True)
        t=time.monotonic();proof=analysis.summary(directory,role);summary_seconds=time.monotonic()-t
        t=time.monotonic();verify(code);verify(manifest['evidence'])
        for index in indices:verify(read(directory/f'tissue_{index}'/'USED_INPUTS.json'))
        if frozen:verify(frozen['evidence'])
        cc,dd,families=schedule(role)
        expected=dict(labelled_cases=len(indices)*cc*len(families)*4*3*16,
            paired_rows=len(indices)*cc*len(families)*4*3*16*dd,new_independent_receiving_draws=len(indices)*cc*dd)
        assert all(proof[k]==v for k,v in expected.items())
        output={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        retained=sum(Path(p).stat().st_size for p in output);assert retained<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE
        receipt=dict(status='COMPLETE',role=role,started_utc=read(directory/'RUNNING.json')['started_utc'],completed_utc=now(),
            seconds=time.monotonic()-tick,blocks=list(indices),inputs=code,outputs=output,retained_bytes=retained,
            verification=proof,environment=env,cpus=cpus,workers=2,numerical_threads=1,
            block_seconds={str(i):v['receipt']['seconds'] for i,v in result.items()},
            summary_seconds=summary_seconds,final_custody_seconds=time.monotonic()-t,
            peak_worker_rss_bytes=max(v['peak_rss_bytes'] for v in result.values()),
            freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write(directory/'COMPLETE.json',receipt);signal.alarm(0)
        return {k:v for k,v in receipt.items() if k not in ('inputs','outputs')}
    except BaseException as error:
        write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False))
        raise
def launch(resource_name):
    admission=read(ROOT/resource_name);frozen=read(ROOT/'FREEZE.json')
    assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    assert len(list(Path('/proc').glob('[0-9]*')))>16,'host launch required'
    verify(frozen['inputs']);verify(frozen['evidence']);assert inputs()==frozen['inputs'] and environment()==frozen['environment']
    os.sched_setaffinity(0,set(frozen['cpus']))
    assert not (ROOT/'runs'/frozen['run_name']).exists() and shutil.disk_usage(ROOT).free>=LIMIT+RESERVE
    rd,wr=os.pipe();log=ROOT/(frozen['run_name']+'.log')
    with log.open('xb') as f:
        process=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'execute.py'),'--execute','confirmation',
            '--name',frozen['run_name'],'--resource',resource_name],cwd=LANE,stdin=subprocess.DEVNULL,
            stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,TT039_READY_FD=str(wr),TT039_DETACHED='1'),pass_fds=(wr,))
    os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
    value=dict(status='DETACHED_STARTED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=process.pid,
        acknowledged_utc=now(),log=str(log),freeze_sha256=sha(ROOT/'FREEZE.json'),workers=2,numerical_threads=1,
        cpus=frozen['cpus'],forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'LAUNCH.json',value);assert msg==b'READY\n',value;return value
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',choices=('benchmark','confirmation'));g.add_argument('--launch',action='store_true')
    p.add_argument('--name');p.add_argument('--resource',required=True);a=p.parse_args()
    print(json.dumps(execute(a.execute,a.name,a.resource) if a.execute else launch(a.resource),sort_keys=True),flush=True)
