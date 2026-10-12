"""Frozen detached generation, repair and assessment with automatic verification."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import time
import traceback
import numpy as np
import acquire
from cohort import develop,construct,seed_identity,body_pass
from reader import decode,read_fixed,generators,scores
from common import ROOT,arrays,equal,read,write,sha,save_arrays,status,stamp,validate


def check_inputs(manifest):
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name


def interrupted(signum,frame):raise RuntimeError('Worker received '+signal.Signals(signum).name)


def main(folder,ready_fd):
    begin=time.perf_counter();lock=(folder/'worker.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        manifest=read(folder/'manifest.json');cfg=manifest['config'];validate(cfg);check_inputs(manifest)
        assert ROOT==folder/'inputs'
        assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
        for path,digest in read(ROOT/'known/COMPLETE.json')['sources_sha256'].items():assert sha(path)==digest,path
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),ready_inputs_verified=True,persistent_host_process=True,executes_frozen_copy=True))
        status(folder,status='RUNNING',phase='startup_verified');os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        receipts=[]
        for b in cfg['blocks']:
            started=time.perf_counter();check_inputs(manifest)
            status(folder,status='RUNNING',phase='new_lineage_generation',block=b)
            acquisition=acquire.teach(seed_identity(b,cfg),cfg['development_config'])
            aq=save_arrays(folder/f'acquisition_{b:06d}.npz',acquisition)
            lineage=develop(acquisition,b,cfg);lh=save_arrays(folder/f'lineage_{b:06d}.npz',lineage)
            status(folder,status='RUNNING',phase='frozen_repair',block=b)
            data=construct(decode(lineage['outgoing'][-1]),b,cfg)
            data['pre_repair_pass']=body_pass(lineage['mean_ports'][-1])
            status(folder,status='RUNNING',phase='paired_assessment',block=b)
            raw=read_fixed(data['packets'],data['masks'],data['founders'],data['recipients'],generators(cfg,b,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])
            intended=scores(raw['mean_ports'],data['founders'],.25);opposite=scores(raw['mean_ports'],data['founders']^1,.25)
            assert not (intended['both_pass']&opposite['both_pass']).any()
            equal(raw['mean_ports'][0,:,3,:,0],raw['mean_ports'][0,:,3,:,1],'erased cue identity')
            assert not (intended['both_pass'][0,:,3]|opposite['both_pass'][0,:,3]).any()
            data.update(birth=raw['birth'],end=raw['end'][0],mean_ports=raw['mean_ports'][0],port_windows=raw['port_windows'][0],
                min_margin=intended['min_margin'][0],both_pass=intended['both_pass'][0],opposite_margin=opposite['min_margin'][0],opposite_pass=opposite['both_pass'][0])
            digest=save_arrays(folder/f'reads_{b:06d}.npz',data)
            receipt=dict(status='COMPLETE',block=b,records=16,history=cfg['history_by_block'][str(b)],seconds=time.perf_counter()-started,
                acquisition_sha256=aq,lineage_sha256=lh,reads_sha256=digest,independent_optimizer_checks=16,erased_control_passed=True,selected_on_outcome=False)
            write(folder/f'worker_{b:06d}.json',receipt);receipts.append(receipt)
            print(f'Block {b} complete; all 16 records retained, checked optimizer and erasure control.',flush=True)
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
            scientific_status='NEW_LINEAGE_VALIDATION_OF_FROZEN_CONVENTIONAL_REPAIR',blocks_completed=cfg['blocks'],records=256,
            scientific_read_contexts=8192,lineage_read_contexts=3584,independent_verification_passed=True,
            receipts=receipts,outputs_sha256=outputs,automatic_successor=False))
        print('COMPLETE: raw lineages, reads, independent checks and report saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-begin,traceback=traceback.format_exc())
        if not (folder/'FAILED.json').exists():write(folder/'FAILED.json',failure)
        status(folder,status='FAILED',phase='failed');raise
    finally:
        if ready_fd is not None:os.close(ready_fd)
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--ready-fd',type=int,required=True)
    args=parser.parse_args();main(args.run.resolve(),args.ready_fd)
