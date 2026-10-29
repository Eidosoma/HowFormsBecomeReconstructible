"""Bounded two-worker execution and detached startup acknowledgment."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing
import os
from pathlib import Path
import resource
import select
import shutil
import signal
import subprocess
import sys
import time
import traceback
import scipy
from common import *
import analysis
import design
import run

BENCHMARK='benchmark_v1'
PANEL='serial_v1'
RUN_LIMIT=2*1024**3
RESERVE=2*1024**3

def environment():
    return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
        numerical_threads={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})

def snapshot_code(directory):
    destination=directory/'input_code';destination.mkdir()
    for path in sorted(ROOT.iterdir()):
        if path.suffix=='.py' or path.name in ('PROTOCOL.md','SOURCE_MANIFEST.json','BASELINE_MANIFEST.json'):
            shutil.copyfile(path,destination/path.name)

def worker(directory,index,role,cpu):
    os.sched_setaffinity(0,{cpu});os.nice(10)
    write_json(Path(directory)/f'worker_{index}.json',dict(started_utc=now(),pid=os.getpid(),cpu=cpu,numerical_threads=1))
    path=Path(directory)/f'tissue_{index}';proof=run.run_block(path,index,role)
    return dict(proof=proof,saved=read_json(path/'SAVED_CHECK.json'),peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)

def batch(directory,indices,role,cpus):
    pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
    try:
        pending={pool.submit(worker,str(directory),i,role,cpus[n]):i for n,i in enumerate(indices)}
        result={pending[f]:f.result() for f in as_completed(pending)}
        pool.shutdown(wait=True);return result
    except BaseException:
        for process in list((pool._processes or {}).values()):process.terminate()
        pool.shutdown(wait=True,cancel_futures=True);raise

def execute(role):
    assert role in ('benchmark','development')
    source_check();baseline_check();inputs=runtime_hashes()
    cpus=sorted(os.sched_getaffinity(0))[-2:]
    assert len(cpus)==2 and set(environment()['numerical_threads'].values())=={'1'}
    frozen=read_json(ROOT/'FREEZE.json') if role=='development' else None
    if frozen:
        assert frozen['inputs']==inputs and frozen['environment']==environment() and frozen['cpus']==cpus
        verify(frozen['evidence'])
    indices=BLOCKS if frozen else DISPOSABLE;deadline=frozen['deadline_seconds'] if frozen else 600
    output=ROOT/'runs'/(PANEL if frozen else BENCHMARK);output.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError(f'TT024 {deadline}-second limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
    write_json(output/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=inputs,
        workers=2,numerical_threads=1,cpus=cpus,deadline_seconds=deadline,automatic_polling=False,
        freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None))
    fd=os.environ.pop('TT024_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        snapshot_code(output);result={}
        for offset in range(0,len(indices),2):
            assert shutil.disk_usage(ROOT).free>=RESERVE and sum(p.stat().st_size for p in output.rglob('*') if p.is_file())<RUN_LIMIT
            result.update(batch(output,indices[offset:offset+2],role,cpus))
            print(json.dumps(dict(stage='blocks_verified',completed_blocks=len(result),total_blocks=len(indices))),flush=True)
        for index in indices:assert run.saved_check(output/f'tissue_{index}')==result[index]['saved']
        summary=analysis.summary(output,role);write_json(output/'SUMMARY.json',summary)
        with (output/'REPORT.md').open('x') as stream:stream.write(analysis.report(summary))
        assert serialized(analysis.summary(output,role))==(output/'SUMMARY.json').read_bytes()
        assert analysis.report(read_json(output/'SUMMARY.json'))==(output/'REPORT.md').read_text()
        verify(inputs);baseline_check()
        if frozen:verify(frozen['evidence'])
        outputs={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        retained=sum(Path(p).stat().st_size for p in outputs)
        assert retained<RUN_LIMIT and shutil.disk_usage(ROOT).free>=RESERVE
        fields=('arm_batches','new_repairs','new_reads','retained_repairs','reused_read_slots','native_arrays')
        proof={k:sum(v['proof'][k] for v in result.values()) for k in fields};proof['max_native_error']=0.
        assert proof==design.expected(role,len(indices))
        saved={k:sum(v['saved'][k] for v in result.values()) for k in ('arrays','records','packet_handoffs','new_dynamics')}
        receipt=dict(status='COMPLETE',role=role,started_utc=read_json(output/'RUNNING.json')['started_utc'],completed_utc=now(),
            seconds=time.monotonic()-tick,blocks=list(indices),inputs=inputs,outputs=outputs,retained_bytes=retained,
            environment=environment(),workers=2,numerical_threads=1,cpus=cpus,verification=proof,saved_verification=saved,
            peak_worker_rss_bytes=max(v['peak_rss_bytes'] for v in result.values()),
            freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None,
            exposed_case_development=True,fresh_population_confirmation=False,additional_injury_mask=True,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write_json(output/'COMPLETE.json',receipt);signal.alarm(0)
        return {k:v for k,v in receipt.items() if k not in ('inputs','outputs')}
    except BaseException as error:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False));raise

def launch():
    frozen=read_json(ROOT/'FREEZE.json');verify(frozen['inputs']);verify(frozen['evidence'])
    assert runtime_hashes()==frozen['inputs'] and environment()==frozen['environment']
    assert not (ROOT/'runs'/PANEL).exists() and shutil.disk_usage(ROOT).free>=RUN_LIMIT+RESERVE
    rd,wr=os.pipe();log=ROOT/(PANEL+'.log')
    with log.open('xb') as stream:
        process=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'execute.py'),'--execute','development'],
            cwd=LANE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,TT024_READY_FD=str(wr)),pass_fds=(wr,))
    os.close(wr);ready=select.select([rd],[],[],30)[0];message=os.read(rd,64) if ready else b'';os.close(rd)
    result=dict(status='DETACHED_STARTED' if message==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=process.pid,
        acknowledged_utc=now(),log=str(log),freeze_sha256=sha(ROOT/'FREEZE.json'),workers=2,numerical_threads=1,
        cpus=frozen['cpus'],forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write_json(ROOT/'LAUNCH.json',result);assert message==b'READY\n',result
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',choices=('benchmark','development'));group.add_argument('--launch',action='store_true')
    args=parser.parse_args();print(json.dumps(execute(args.execute) if args.execute else launch(),sort_keys=True),flush=True)
