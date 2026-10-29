"""Bounded two-worker execution and durable host-detached launch."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os
import resource
import select
import shutil
import signal
import subprocess
import time
import traceback
import scipy
from common import *
import analysis
import design
import run

BENCHMARK='benchmark_v2'
PANEL='reset_v1'
RUN_LIMIT=48*1024**3
RESERVE=8*1024**3
def environment():
    return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
        numerical_threads={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
def worker(directory,index,role,cpu,final=False):
    os.sched_setaffinity(0,{cpu});assert os.getpriority(os.PRIO_PROCESS,0)==0;directory=Path(directory)
    if not final:
        write_json(directory/f'worker_{index}.json',dict(started_utc=now(),pid=os.getpid(),cpu=cpu,numerical_threads=1,nice=os.getpriority(os.PRIO_PROCESS,0)))
        proof=run.block(directory/f'tissue_{index}',index,role)
        return dict(proof=proof,timing=read_json(directory/f'tissue_{index}'/'BLOCK_TIMING.json'),
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    path=directory/f'tissue_{index}';proof=run.saved(path)
    assert read_json(path/'SAVED_CHECK.json')==dict(status='PASS',verification=proof,new_dynamics=0)
    assert serialized(analysis.block(path))==(path/'SUMMARY.json').read_bytes()
    return proof
def batch(directory,indices,role,cpus,final=False):
    pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
    try:
        pending={pool.submit(worker,str(directory),i,role,cpus[n],final):i for n,i in enumerate(indices)}
        result={pending[f]:f.result() for f in as_completed(pending)}
        pool.shutdown(wait=True);return result
    except BaseException:
        for p in list((pool._processes or {}).values()):p.terminate()
        pool.shutdown(wait=True,cancel_futures=True);raise
def execute(role):
    assert role in ('benchmark','development')
    source_check();inputs=runtime_hashes();cpus=sorted(os.sched_getaffinity(0))[-2:]
    assert len(cpus)==2 and set(environment()['numerical_threads'].values())=={'1'}
    frozen=read_json(ROOT/'FREEZE.json') if role=='development' else None
    resource_check=read_json(ROOT/('PRELAUNCH_RESOURCE_CHECK.json' if frozen else 'BENCHMARK_V2_RESOURCE_CHECK.json'))
    assert resource_check['admission_pass'] and resource_check['planned_workers']==2
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resource_check['recorded_utc'])).total_seconds()<180
    if frozen:assert os.environ.get('TT032_DETACHED')=='1','host-detached production required'
    if frozen:
        assert frozen['inputs']==inputs and frozen['environment']==environment() and frozen['cpus']==cpus
        verify(frozen['evidence'])
    directory=ROOT/'runs'/(PANEL if frozen else BENCHMARK);directory.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();deadline=frozen['deadline_seconds'] if frozen else 600
    def expire(*_):raise TimeoutError(f'TT032 {deadline}-second limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
    write_json(directory/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=inputs,
        workers=2,numerical_threads=1,cpus=cpus,deadline_seconds=deadline,automatic_polling=False,
        freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None))
    fd=os.environ.pop('TT032_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        snapshot=directory/'input_code';snapshot.mkdir()
        for p in ROOT.iterdir():
            if p.suffix=='.py' or p.name in ('PROTOCOL.md','SOURCE_MANIFEST.json','INPUT_MANIFEST.json','RANDOMNESS.json'):
                shutil.copyfile(p,snapshot/p.name)
        indices=design.indices(role);result={}
        for offset in range(0,len(indices),2):
            assert shutil.disk_usage(ROOT).free>=RESERVE
            assert sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())<RUN_LIMIT
            result.update(batch(directory,indices[offset:offset+2],role,cpus))
            print(json.dumps(dict(stage='blocks_verified',completed_blocks=len(result),total_blocks=len(indices))),flush=True)
        t=time.monotonic()
        for offset in range(0,len(indices),2):
            checked=batch(directory,indices[offset:offset+2],role,cpus,True)
            for i,p in checked.items():assert p==result[i]['proof']
        final_verification_seconds=time.monotonic()-t;t=time.monotonic()
        summary=analysis.summary(directory,role);write_json(directory/'SUMMARY.json',summary)
        with (directory/'REPORT.md').open('x') as f:f.write(analysis.report(summary))
        assert analysis.report(read_json(directory/'SUMMARY.json'))==(directory/'REPORT.md').read_text()
        final_analysis_seconds=time.monotonic()-t;t=time.monotonic()
        verify(inputs)
        source_manifest=read_json(ROOT/'INPUT_MANIFEST.json')
        verify(source_manifest['production' if frozen else 'benchmark']);verify(source_manifest['evidence'])
        if frozen:verify(frozen['evidence'])
        outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        retained=sum(Path(p).stat().st_size for p in outputs)
        assert retained<RUN_LIMIT and shutil.disk_usage(ROOT).free>=RESERVE
        planned=design.expected(role,len(indices));proof={}
        for key in next(iter(result.values()))['proof']:
            proof[key]=0. if key=='max_native_error' else sum(v['proof'][key] for v in result.values())
        assert all(proof[k]==v for k,v in planned.items()) and summary['verification']==proof
        upper=design.upper(role,len(indices))
        assert proof['repair_batches']<=upper['repair_batches'] and proof['reader_batches']<=upper['reader_batches']
        receipt=dict(status='COMPLETE',role=role,started_utc=read_json(directory/'RUNNING.json')['started_utc'],
            completed_utc=now(),seconds=time.monotonic()-tick,blocks=list(indices),inputs=inputs,outputs=outputs,
            retained_bytes=retained,environment=environment(),workers=2,numerical_threads=1,cpus=cpus,
            verification=proof,component_timings={str(i):v['timing'] for i,v in result.items()},
            final_verification_seconds=final_verification_seconds,final_analysis_seconds=final_analysis_seconds,
            final_manifest_seconds=time.monotonic()-t,peak_worker_rss_bytes=max(v['peak_rss_bytes'] for v in result.values()),
            freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None,exposed_case_development=True,
            fresh_population_confirmation=False,record_bytes=2048,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write_json(directory/'COMPLETE.json',receipt);signal.alarm(0)
        return {k:v for k,v in receipt.items() if k not in ('inputs','outputs','component_timings')}
    except BaseException as error:
        write_json(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False))
        raise
def launch():
    resources=read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
    assert resources['admission_pass'] and resources['planned_workers']==2
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resources['recorded_utc'])).total_seconds()<180
    assert len(list(Path('/proc').glob('[0-9]*')))>16,'host launch required'
    frozen=read_json(ROOT/'FREEZE.json');verify(frozen['inputs']);verify(frozen['evidence'])
    assert runtime_hashes()==frozen['inputs'] and environment()==frozen['environment']
    os.sched_setaffinity(0,set(frozen['cpus']))
    assert not (ROOT/'runs'/PANEL).exists() and shutil.disk_usage(ROOT).free>=RUN_LIMIT+RESERVE
    rd,wr=os.pipe();log=ROOT/(PANEL+'.log')
    with log.open('xb') as f:
        process=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'execute.py'),'--execute','development'],
            cwd=LANE,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,TT032_READY_FD=str(wr),TT032_DETACHED='1'),pass_fds=(wr,))
    os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
    value=dict(status='DETACHED_STARTED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=process.pid,
        acknowledged_utc=now(),log=str(log),freeze_sha256=sha(ROOT/'FREEZE.json'),workers=2,numerical_threads=1,
        cpus=frozen['cpus'],forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write_json(ROOT/'LAUNCH.json',value);assert msg==b'READY\n',value
    return value
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',choices=('benchmark','development'));g.add_argument('--launch',action='store_true')
    a=p.parse_args();print(json.dumps(execute(a.execute) if a.execute else launch(),sort_keys=True),flush=True)
