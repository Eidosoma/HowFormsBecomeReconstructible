"""Frozen, detached, all-record fresh acquisition and budgeted policy comparison."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import time
import traceback
from common import ROOT,read,write,sha,save_arrays,status,stamp,validate
import acquire
import cohort
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
        for name in ('COMPLETE.json','TEACHING_COMPLETE.json'):
            for path,digest in read(ROOT/'sources'/name)['sources_sha256'].items():assert sha(path)==digest,path
        model=read(ROOT/'development/MODEL.json')
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),
            ready_inputs_verified=True,persistent_host_process=True,executes_frozen_copy=True))
        status(folder,status='RUNNING',phase='startup_verified')
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        receipts=[]
        for b in cfg['blocks']:
            started=time.perf_counter();check_inputs(manifest)
            status(folder,status='RUNNING',phase='fresh_acquisition_and_history',block=b)
            teaching=acquire.teach(cohort.seed_identity(b,cfg),cfg['development_config'])
            acquisition_hash=save_arrays(folder/f'acquisition_{b:06d}.npz',teaching)
            lineage=cohort.develop(teaching,b,cfg)
            lineage_hash=save_arrays(folder/f'lineage_{b:06d}.npz',lineage)
            status(folder,status='RUNNING',phase='budgeted_policy_continuation',block=b)
            d=continue_block(lineage['outgoing'][-1],lineage['masks'][-1],b,cfg,model)
            digest=save_arrays(folder/f'continuation_{b:06d}.npz',d)
            receipt=dict(status='COMPLETE',block=b,records=16,history=cfg['history_by_block'][str(b)],
                seconds=time.perf_counter()-started,acquisition_sha256=acquisition_hash,lineage_sha256=lineage_hash,
                continuation_sha256=digest,independent_optimizer_checks=int(d['independent_optimizer_checks'].sum()),
                selected_on_outcome=False,generations=cfg['generations'],branches=4,simulated_branches=4,reused_branches=0)
            assert receipt['independent_optimizer_checks']==720
            write(folder/f'worker_{b:06d}.json',receipt);receipts.append(receipt)
            print(f'Block {b} complete; all records and all four policies retained through generation 32.',flush=True)
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
            cpu_seconds=time.process_time()-cpu,scientific_status='PROSPECTIVE_SEED_HOLDOUT_EXPOSED_POLICY_HYPOTHESIS',
            blocks_completed=cfg['blocks'],records=256,scientific_read_contexts=18432,acquisition_lineage_read_contexts=3584,
            independent_verification_passed=True,receipts=receipts,outputs_sha256=outputs,automatic_successor=False))
        print('COMPLETE: fresh histories, budgeted policies, costs, independent checks and report saved.',flush=True)
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
