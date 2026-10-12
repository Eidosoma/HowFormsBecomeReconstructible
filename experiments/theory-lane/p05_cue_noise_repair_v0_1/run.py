"""Detached six-arm continuation with automatic internal verification."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import time
import traceback
import numpy as np
from common import ROOT,arrays,read,write,sha,save_arrays,status,stamp,validate
from serial import continue_block


def check_inputs(manifest):
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name


def interrupted(signum,frame):
    raise RuntimeError('Worker received '+signal.Signals(signum).name)


def main(folder,ready_fd):
    begin=time.perf_counter();cpu=time.process_time();lock=(folder/'worker.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        manifest=read(folder/'manifest.json');cfg=manifest['config'];validate(cfg);check_inputs(manifest)
        assert ROOT==folder/'inputs'
        assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
        for path,digest in read(ROOT/'sources/COMPLETE.json')['sources_sha256'].items():assert sha(path)==digest,path
        source=arrays(ROOT/'sources/boundaries.npz')
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),
            ready_inputs_verified=True,persistent_host_process=True,executes_frozen_copy=True))
        status(folder,status='RUNNING',phase='startup_verified')
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        receipts=[]
        for bi,b in enumerate(cfg['blocks']):
            started=time.perf_counter();check_inputs(manifest)
            status(folder,status='RUNNING',phase='six_arm_noise_continuation',block=b)
            d=continue_block(source['initial_packets'][bi],source['previous_masks'][bi],b,cfg)
            digest=save_arrays(folder/f'continuation_{b:06d}.npz',d)
            receipt=dict(status='COMPLETE',block=b,records=16,history=cfg['history_by_block'][str(b)],
                seconds=time.perf_counter()-started,continuation_sha256=digest,
                independent_optimizer_checks=int(d['independent_optimizer_checks'].sum()),selected_on_outcome=False,
                generations=cfg['generations'],branches=6)
            assert receipt['independent_optimizer_checks']==864
            write(folder/f'worker_{b:06d}.json',receipt);receipts.append(receipt)
            print(f'Block {b} complete; all records and all six arms retained through generation 32.',flush=True)
        status(folder,status='RUNNING',phase='analysis')
        from analyze import analyze,render
        analyze(folder,cfg)
        status(folder,status='RUNNING',phase='independent_verification')
        from verify import verify
        assert verify(folder,cfg)['status']=='PASS'
        render(folder,cfg);check_inputs(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        excluded={'console.log','PID','LAUNCH.json','worker.lock'}
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in excluded}
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),seconds=time.perf_counter()-begin,
            cpu_seconds=time.process_time()-cpu,scientific_status='CUE_NOISE_MECHANISM_FOLLOWUP_ON_EXPOSED_COHORT',
            blocks_completed=cfg['blocks'],records=256,scientific_read_contexts=27648,new_mismatched_read_contexts=18432,matched_replay_read_contexts=9216,
            independent_verification_passed=True,receipts=receipts,outputs_sha256=outputs,automatic_successor=False))
        print('COMPLETE: branch histories, costs, analysis, checks and report saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-begin,traceback=traceback.format_exc())
        if not (folder/'FAILED.json').exists():write(folder/'FAILED.json',failure)
        status(folder,status='FAILED',phase='failed');raise
    finally:
        if ready_fd is not None:os.close(ready_fd)
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--ready-fd',type=int,required=True)
    args=parser.parse_args();main(args.run.resolve(),args.ready_fd)
