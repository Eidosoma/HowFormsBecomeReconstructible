"""Resume missing blocks with unchanged scientific code and persistent supervision."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import sys
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,status,validate,write
from reader import generators,read_fixed,scores
from run import check_code


def interrupted(signum,frame):
    raise RuntimeError(f'Recovery worker received signal {signal.Signals(signum).name}')


def main(folder,ready_fd):
    started=time.perf_counter()
    lock=(ROOT/'recovery_v0_1/worker.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        manifest=read(folder/'manifest.json')
        cfg=manifest['config'];validate(cfg);check_code(manifest)
        assert sha(ROOT/'prepared/COMPLETE.json')==manifest['prepared_complete_sha256']
        prepared=read(ROOT/'prepared/COMPLETE.json')
        for path,digest in prepared['sources_sha256'].items():
            assert sha(Path(path))==digest,'Source changed: '+path
        receipts=[]
        reused=set(manifest['resumption']['reused_blocks'])
        assert reused=={34000}
        for block in reused:
            expected=manifest['resumption']['checkpoint_sha256'][str(block)]
            path=folder/f'reads_{block:06d}.npz'
            receipt_path=folder/f'worker_{block:06d}.json'
            assert sha(path)==expected['data'] and sha(receipt_path)==expected['receipt']
            receipt=read(receipt_path)
            assert receipt['status']=='COMPLETE' and receipt['original_native_replay_byte_equal']
            assert sha(path)==receipt['output_sha256']
            arrays(path,expected['data'])
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),
            persistent_host_process=True,reused_blocks=sorted(reused),ready_inputs_verified=True))
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        for block in cfg['blocks']:
            check_code(manifest)
            if block in reused:
                receipts.append(read(folder/f'worker_{block:06d}.json'))
                print(f'Reused verified block {block}; no recomputation.',flush=True)
                continue
            before=time.perf_counter()
            name=f'cases_{block:06d}.npz'
            source=arrays(ROOT/'prepared'/name,prepared['outputs_sha256'][name])
            status(folder,status='RUNNING',phase='original_native_replay',block=block,reused_blocks=sorted(reused))
            original=read_fixed(source['packets'][:,0:1],source['masks'],source['founders'],source['recipients'],
                generators(cfg,block,[0],original=True),cfg['reader'],[2048],cfg['settling_steps'])
            equal(original['birth'][:,0],source['original_birth'],'selected original birth')
            equal(original['end'][0,:,0,0],source['original_end'],'selected original body')
            equal(original['mean_ports'][0,:,0,0],source['original_mean_ports'],'selected original output')
            assert not scores(original['mean_ports'],source['founders'],.25)['both_pass'].any()
            status(folder,status='RUNNING',phase='fresh_fixed_injury_reads',block=block,reused_blocks=sorted(reused))
            raw=read_fixed(source['packets'],source['masks'],source['founders'],source['recipients'],
                generators(cfg,block,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])
            scored=scores(raw['mean_ports'],source['founders'],cfg['reader']['margin'])
            equal(raw['mean_ports'][:,:,2,:,0],raw['mean_ports'][:,:,2,:,1],'erased cue equality')
            assert not scored['both_pass'][:,:,2].any()
            output=save_arrays(folder/f'reads_{block:06d}.npz',dict(**source,**raw,**scored,replicates=np.array(cfg['replicates'])))
            receipt=dict(status='COMPLETE',block=block,cases=len(source['founders']),seconds=time.perf_counter()-before,
                original_native_replay_byte_equal=True,erased_control_passed=True,
                input_sha256=prepared['outputs_sha256'][name],output_sha256=output)
            write(folder/f'worker_{block:06d}.json',receipt);receipts.append(receipt)
            print(f'Completed block {block}; known replay and erased checks passed.',flush=True)
        check_code(manifest)
        status(folder,status='RUNNING',phase='analysis')
        from analyze import analyze,render
        analyze(folder,cfg)
        status(folder,status='RUNNING',phase='independent_verification')
        from verify import verify
        assert verify(folder,cfg)['status']=='PASS'
        status(folder,status='RUNNING',phase='report_and_figures')
        render(folder,cfg)
        from plot import plot
        plot(folder,cfg)
        check_code(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in ('console.log','PID','LAUNCH.json')}
        write(folder/'COMPLETE.json',dict(status='COMPLETE',completed_at_utc=stamp(),seconds=time.perf_counter()-started,
            scientific_status='DEVELOPMENT_FIXED_INJURY_PROBE_NOT_CONFIRMATORY',blocks_completed=cfg['blocks'],
            cases=64,trajectories=3072,endpoint_read_scores=9216,native_replay_passed=True,independent_verification_passed=True,
            receipts=receipts,outputs_sha256=outputs,reused_blocks=sorted(reused),new_blocks=[b for b in cfg['blocks'] if b not in reused],
            original_interruption=str(ROOT/'runs/pilot_v1/INTERRUPTED.json'),
            scientific_protocol_unchanged=True,automatic_successor=False,figure_visual_review_pending=True))
        print('COMPLETE: report, raw evidence and independent verification saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-started,traceback=traceback.format_exc())
        write(folder/'FAILED.json',failure);status(folder,status='FAILED',phase='failed')
        raise
    finally:
        if ready_fd is not None:
            os.close(ready_fd)
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--ready-fd',type=int,required=True)
    args=parser.parse_args();main(args.run.resolve(),args.ready_fd)
