"""Detached fixed fresh cohort with per-block internal audits and no interim decision."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import time
import traceback
import acquire
import cohort
from audit_cohort import check_lineage
from audit_serial import audit_block
from serial import continue_block
from common import ROOT,read,write,sha,stamp,status,save_arrays,validate


def check_inputs(manifest):
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name


def interrupted(signum,frame):raise RuntimeError('Worker received '+signal.Signals(signum).name)


def main(folder,ready_fd):
    begin=time.perf_counter();cpu=time.process_time();lock=(folder/'worker.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        manifest=read(folder/'manifest.json');cfg=manifest['config'];validate(cfg);check_inputs(manifest)
        assert ROOT==folder/'inputs'
        assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1' and all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
        q=read(ROOT/'qualification_v2/COMPLETE.json');assert q['status']=='PASS' and q['new_test_outcomes']==0
        assert sha(ROOT/'qualification_v2/COMPLETE.json')==manifest['qualification_sha256']
        for path,digest in read(ROOT/'sources/COMPLETE.json')['sources_sha256'].items():assert sha(path)==digest,path
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),ready_inputs_verified=True,persistent_host_process=True,executes_frozen_copy=True))
        status(folder,status='RUNNING',phase='startup_verified',blocks_completed=[])
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        write(folder/'TEST_COHORT_STARTED.json',dict(status='RUNNING',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json'),qualification_sha256=manifest['qualification_sha256'],outcome_based_selection=False))
        receipts=[]
        for b in cfg['blocks']:
            started=time.perf_counter();check_inputs(manifest);done=[r['block'] for r in receipts]
            status(folder,status='RUNNING',phase='fresh_acquisition_and_history',block=b,blocks_completed=done)
            teaching=acquire.teach(cohort.seed_identity(b,cfg),cfg['development_config'])
            acquisition_hash=save_arrays(folder/f'acquisition_{b:06d}.npz',teaching)
            lineage=cohort.develop(teaching,b,cfg);lineage_hash=save_arrays(folder/f'lineage_{b:06d}.npz',lineage)
            check_lineage(teaching,lineage,b,cfg)
            status(folder,status='RUNNING',phase='repair_efficiency_continuation',block=b,blocks_completed=done)
            d=continue_block(lineage['outgoing'][-1],lineage['masks'][-1],b,cfg)
            digest=save_arrays(folder/f'continuation_{b:06d}.npz',d)
            status(folder,status='RUNNING',phase='block_internal_verification',block=b,blocks_completed=done)
            checks=audit_block(d,lineage['outgoing'][-1],lineage['masks'][-1],b,cfg)
            audit=dict(status='COMPLETE',at_utc=stamp(),block=b,acquisition_sha256=acquisition_hash,lineage_sha256=lineage_hash,
                continuation_sha256=digest,acquisition_and_history_audit_passed=True,continuation_checks=checks)
            write(folder/f'audit_{b:06d}.json',audit)
            receipt=dict(status='COMPLETE',block=b,records=16,history=cfg['history_by_block'][str(b)],seconds=time.perf_counter()-started,
                acquisition_sha256=acquisition_hash,lineage_sha256=lineage_hash,continuation_sha256=digest,audit_sha256=sha(folder/f'audit_{b:06d}.json'),
                independent_optimizer_checks=int(d['independent_optimizer_checks'].sum()),selected_on_outcome=False,generations=cfg['generations'],branches=3,simulated_branches=3,reused_branches=0)
            assert receipt['independent_optimizer_checks']==400;write(folder/f'worker_{b:06d}.json',receipt);receipts.append(receipt)
            print(f'Block {b} complete and audited; all records and three schedules retained through generation 32.',flush=True)
        status(folder,status='RUNNING',phase='analysis',blocks_completed=cfg['blocks'])
        from analyze import analyze,render
        analyze(folder,cfg)
        status(folder,status='RUNNING',phase='independent_analysis_verification',blocks_completed=cfg['blocks'])
        from verify import verify
        assert verify(folder,cfg)['status']=='PASS';render(folder,cfg);check_inputs(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        excluded={'console.log','PID','LAUNCH.json','worker.lock'}
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in excluded}
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),seconds=time.perf_counter()-begin,cpu_seconds=time.process_time()-cpu,
            scientific_status='PROSPECTIVE_SEED_HOLDOUT_EXPOSED_SCHEDULE_HYPOTHESIS',blocks_completed=cfg['blocks'],records=cfg['cohort_size'],
            scientific_read_contexts=cfg['scientific_read_contexts'],acquisition_lineage_read_contexts=cfg['acquisition_lineage_read_contexts'],
            independent_verification_passed=True,primary_verdict=read(folder/'analysis.json')['primary']['verdict'],receipts=receipts,outputs_sha256=outputs,automatic_successor=False))
        print('COMPLETE: all fresh blocks, fixed efficiency test, resource accounting and internal checks saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-begin,traceback=traceback.format_exc())
        if not (folder/'FAILED.json').exists():write(folder/'FAILED.json',failure)
        status(folder,status='FAILED',phase='failed');raise
    finally:
        if ready_fd is not None:os.close(ready_fd)
        lock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--ready-fd',type=int,required=True)
    args=p.parse_args();main(args.run.resolve(),args.ready_fd)
