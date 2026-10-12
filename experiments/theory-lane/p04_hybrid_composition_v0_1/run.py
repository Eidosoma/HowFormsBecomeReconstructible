"""Detached frozen worker with automatic scientific checks and no successor."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import time
import traceback
import numpy as np

from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,status,validate,write
from reader import generators,read_fixed,scores
from compute import experiment


def check_code(manifest):
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,'Frozen input changed: '+name


def interrupted(signum,frame):
    raise RuntimeError('Worker received '+signal.Signals(signum).name)


def main(folder,ready_fd):
    begin=time.perf_counter();lock=(folder/'worker.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        manifest=read(folder/'manifest.json');cfg=manifest['config'];validate(cfg);check_code(manifest)
        assert ROOT==folder/'inputs','Run must execute the frozen copy'
        assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
        prepared=read(ROOT/'prepared/COMPLETE.json')
        for path,digest in prepared['sources_sha256'].items():assert sha(path)==digest,'Bound source changed: '+path
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),ready_inputs_verified=True,
            persistent_host_process=True,executes_frozen_copy=True))
        status(folder,status='RUNNING',phase='startup_verified')
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        receipts=[]
        for block in cfg['blocks']:
            started=time.perf_counter();check_code(manifest)
            name=f'cases_{block:06d}.npz';data=arrays(ROOT/'prepared'/name,prepared['outputs_sha256'][name])
            status(folder,status='RUNNING',phase='known_original_replay',block=block)
            known=read_fixed(data['packets'][:,0:1],data['original_masks'],data['founders'],data['recipients'],
                generators(cfg,block,[0],original=True),cfg['reader'],[2048],cfg['settling_steps'])
            equal(known['birth'][:,0],data['original_birth'],'original reset')
            equal(known['end'][0,:,0,0],data['original_end'],'original body')
            equal(known['mean_ports'][0,:,0,0],data['original_mean_ports'],'original mean ports')
            assert not scores(known['mean_ports'],data['founders'],.25)['both_pass'].any()
            status(folder,status='RUNNING',phase='paired_injury_reads',block=block)
            raw=experiment(data,block,cfg)
            equal(raw['birth'][0],raw['birth'][1],'paired injury reset')
            equal(raw['end'][0,:,0],raw['end'][0,:,2],'original erasure identity')
            equal(raw['port_windows'][0,:,:,0],raw['port_windows'][0,:,:,2],'original erasure window identity')
            for vi in (3,4):
                equal(raw['end'][0,:,1],raw['end'][0,:,vi],'original masked backup identity')
                equal(raw['port_windows'][0,:,:,1],raw['port_windows'][0,:,:,vi],'original masked backup windows')
            equal(raw['mean_ports'][:,:,5,:,0],raw['mean_ports'][:,:,5,:,1],'erased cue identity')
            assert not raw['both_pass'][:,:,5].any()
            digest=save_arrays(folder/f'reads_{block:06d}.npz',dict(**data,**raw))
            receipt=dict(status='COMPLETE',block=block,cases=len(data['founders']),seconds=time.perf_counter()-started,
                original_native_replay_byte_equal=True,erasure_identity_passed=True,masked_backup_identity_passed=True,erased_control_passed=True,
                input_sha256=prepared['outputs_sha256'][name],output_sha256=digest)
            write(folder/f'worker_{block:06d}.json',receipt);receipts.append(receipt)
            print(f'Completed block {block}; known replay, erasure and backup controls passed.',flush=True)
        status(folder,status='RUNNING',phase='analysis')
        from analyze import analyze,render
        analyze(folder,cfg)
        status(folder,status='RUNNING',phase='independent_verification')
        from verify import verify
        assert verify(folder,cfg)['status']=='PASS'
        status(folder,status='RUNNING',phase='report_and_figures')
        render(folder,cfg)
        from plot import plot
        plot(folder,cfg);check_code(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        excluded={'console.log','PID','LAUNCH.json','worker.lock'}
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in excluded}
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),seconds=time.perf_counter()-begin,
            scientific_status='DEVELOPMENT_HYBRID_COMPOSITION_NOT_CONFIRMATORY',blocks_completed=cfg['blocks'],cases=64,
            trajectories=12288,native_replay_passed=True,independent_verification_passed=True,
            receipts=receipts,outputs_sha256=outputs,automatic_successor=False,figure_visual_review_pending=True))
        print('COMPLETE: raw evidence, verification, report and figures saved.',flush=True)
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
