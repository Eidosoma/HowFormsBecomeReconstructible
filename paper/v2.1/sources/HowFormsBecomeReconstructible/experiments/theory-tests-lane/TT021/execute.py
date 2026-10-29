"""Bounded two-worker execution, immutable registration, detached startup."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import multiprocessing
import os
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
import run
from design import WORKERS

QUALIFICATION='qualification_v1'
BENCHMARK='benchmark_v1'
PANEL='confirmation_v1'
RUN_LIMIT=3*1024**3
RESERVE=1024**3


def environment():
    return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
        numerical_threads={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})


def worker(directory,index,cfg,rcfg,cpu,role):
    os.sched_setaffinity(0,{cpu});os.nice(10)
    assert set(environment()['numerical_threads'].values())=={'1'}
    output=Path(directory)/f'tissue_{index}'
    write_json(Path(directory)/f'worker_{index}.json',dict(started_utc=now(),pid=os.getpid(),
        affinity=sorted(os.sched_getaffinity(0)),numerical_threads=1,tissue=index))
    proof=run.run_block(output,index,cfg,rcfg,role)
    return dict(proof=proof,saved=read_json(output/'SAVED_CHECK.json'),
        retained_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)


def paired_batch(directory,indices,cfg,rcfg,cpus,role):
    pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
    try:
        futures={pool.submit(worker,str(directory),index,cfg,rcfg,cpus[offset],role):index for offset,index in enumerate(indices)}
        result={futures[f]:f.result() for f in as_completed(futures)}
        pool.shutdown(wait=True)
        return result
    except BaseException:
        for process in list((pool._processes or {}).values()): process.terminate()
        pool.shutdown(wait=True,cancel_futures=True)
        raise


def execute(mode):
    source_check();inputs=runtime_hashes();cpus=sorted(os.sched_getaffinity(0))[-2:]
    assert len(cpus)==2 and set(environment()['numerical_threads'].values())=={'1'}
    if mode=='confirmation':
        registration=read_json(ROOT/'REGISTRATION.json')
        assert registration['inputs']==inputs and registration['environment']==environment()
        verify(registration['inputs']);verify(registration['evidence'])
        assert registration['blocks']==list(BLOCKS)
        assert registration['cpus']==cpus
        cfg,rcfg=model.CONFIG,model.READOUT
        indices=BLOCKS;deadline=registration['deadline_seconds'];name=PANEL
    else:
        registration=None
        cfg=replace(model.CONFIG,sweeps=100,times=(0,1,5,25,50,100))
        rcfg=replace(model.READOUT,sweeps=100,times=(0,1,100))
        indices=DISPOSABLE;deadline=600;name=BENCHMARK
    directory=ROOT/'runs'/name;directory.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError(f'TT021 {deadline}-second deadline')
    signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
    write_json(directory/'RUNNING.json',dict(status='RUNNING',mode=mode,pid=os.getpid(),started_utc=now(),
        inputs=inputs,registration_sha256=sha(ROOT/'REGISTRATION.json') if registration else None,
        workers=2,numerical_threads=1,cpus=cpus,deadline_seconds=deadline,automatic_polling=False))
    fd=os.environ.pop('TT021_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        results={}
        for offset in range(0,len(indices),2):
            retained=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
            assert retained<RUN_LIMIT and shutil.disk_usage(ROOT).free>RESERVE+256*1024**2,'storage reserve'
            results.update(paired_batch(directory,indices[offset:offset+2],cfg,rcfg,cpus,
                'prospective confirmation' if registration else 'excluded disposable benchmark'))
            print(json.dumps(dict(stage='batch_verified',completed_blocks=len(results),total_blocks=len(indices))),flush=True)
        if registration:
            summary=analysis.summary(directory);write_json(directory/'SUMMARY.json',summary)
            with (directory/'REPORT.md').open('x') as f:f.write(analysis.report(summary))
            assert serialized(analysis.summary(directory))==(directory/'SUMMARY.json').read_bytes()
            assert analysis.report(read_json(directory/'SUMMARY.json'))==(directory/'REPORT.md').read_text()
        for index in indices:
            assert run.saved_check(directory/f'tissue_{index}',cfg,rcfg)==results[index]['saved']
        verify(inputs)
        if registration:verify(registration['evidence'])
        files={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        retained=sum(Path(p).stat().st_size for p in files)
        assert retained<RUN_LIMIT and shutil.disk_usage(ROOT).free>=RESERVE
        fields=('records','repair_paths','logical_assays','unique_assays','native_arrays','exact_alias_checks')
        checked={k:sum(v['proof'][k] for v in results.values()) for k in fields}
        checked.update(max_native_error=0.,max_average_error=max(v['proof']['max_average_error'] for v in results.values()))
        saved={k:sum(v['saved'][k] for v in results.values()) for k in ('array_receipts','scalar_record_rows','packet_routes')}
        complete=dict(status='COMPLETE',mode=mode,started_utc=read_json(directory/'RUNNING.json')['started_utc'],
            completed_utc=now(),seconds=time.monotonic()-tick,blocks=list(indices),inputs=inputs,outputs=files,
            environment=environment(),workers=2,numerical_threads=1,cpus=cpus,
            retained_bytes=retained,peak_worker_rss_bytes=max(v['peak_rss_bytes'] for v in results.values()),
            verification=checked,saved_verification=saved,reused_scientific_trajectories=0,
            registration_sha256=sha(ROOT/'REGISTRATION.json') if registration else None,
            primary=summary['primary'] if registration else None,automatic_polling=False,automatic_successor=False)
        write_json(directory/'COMPLETE.json',complete);signal.alarm(0)
        return {k:v for k,v in complete.items() if k not in ('inputs','outputs')}
    except BaseException as error:
        write_json(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),
            traceback=traceback.format_exc(),automatic_retry=False));raise


def launch():
    registration=read_json(ROOT/'REGISTRATION.json')
    verify(registration['inputs']);verify(registration['evidence'])
    assert registration['inputs']==runtime_hashes() and registration['environment']==environment()
    assert not (ROOT/'runs'/PANEL).exists() and not (ROOT/'LAUNCH.json').exists()
    assert shutil.disk_usage(ROOT).free>=RUN_LIMIT+RESERVE,'full output allowance plus reserve'
    readfd,writefd=os.pipe();env=dict(os.environ,TT021_READY_FD=str(writefd));log=ROOT/(PANEL+'.log')
    with log.open('xb') as stream:
        process=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'execute.py'),'--execute','confirmation'],
            cwd=LANE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,
            start_new_session=True,pass_fds=(writefd,))
    os.close(writefd);ready=select.select([readfd],[],[],30)[0]
    message=os.read(readfd,64) if ready else b'';os.close(readfd)
    receipt=dict(status='DETACHED_STARTED' if message==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid,acknowledged_utc=now(),log=str(log),registration_sha256=sha(ROOT/'REGISTRATION.json'),
        forecast_seconds=registration['forecast_seconds'],deadline_seconds=registration['deadline_seconds'],
        workers=2,numerical_threads=1,cpus=registration['cpus'],automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write_json(ROOT/'LAUNCH.json',receipt);assert message==b'READY\n',receipt
    return receipt


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',choices=('benchmark','confirmation'));group.add_argument('--launch',action='store_true')
    args=parser.parse_args()
    print(json.dumps(execute(args.execute) if args.execute else launch(),sort_keys=True),flush=True)


if __name__=='__main__':main()
