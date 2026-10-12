"""Unpolled run with automatic replay, analysis, verification and report."""
import argparse
from pathlib import Path
import time
import traceback

import numpy as np

from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,status,validate,write
from reader import generators,read_fixed,scores


def check_code(manifest):
    for name,digest in manifest['code_sha256'].items():
        assert sha(ROOT/name)==digest,'Frozen input changed: '+name


def main(folder):
    started=time.perf_counter()
    try:
        manifest=read(folder/'manifest.json')
        cfg=manifest['config'];validate(cfg);check_code(manifest)
        prepared=read(ROOT/'prepared/COMPLETE.json')
        assert sha(ROOT/'prepared/COMPLETE.json')==manifest['prepared_complete_sha256']
        for path,digest in prepared['sources_sha256'].items():
            assert sha(Path(path))==digest,'External source changed: '+path
        receipts=[]
        for block in cfg['blocks']:
            before=time.perf_counter();check_code(manifest)
            name=f'cases_{block:06d}.npz'
            source=arrays(ROOT/'prepared'/name,prepared['outputs_sha256'][name])
            status(folder,status='RUNNING',phase='original_native_replay',block=block)
            original=read_fixed(source['packets'][:,0:1],source['masks'],source['founders'],source['recipients'],
                generators(cfg,block,[0],original=True),cfg['reader'],[2048],cfg['settling_steps'])
            equal(original['birth'][:,0],source['original_birth'],'selected original birth')
            equal(original['end'][0,:,0,0],source['original_end'],'selected original body')
            equal(original['mean_ports'][0,:,0,0],source['original_mean_ports'],'selected original output')
            assert not scores(original['mean_ports'],source['founders'],.25)['both_pass'].any()
            status(folder,status='RUNNING',phase='fresh_fixed_injury_reads',block=block)
            raw=read_fixed(source['packets'],source['masks'],source['founders'],source['recipients'],
                generators(cfg,block,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])
            scored=scores(raw['mean_ports'],source['founders'],cfg['reader']['margin'])
            equal(raw['mean_ports'][:,:,2,:,0],raw['mean_ports'][:,:,2,:,1],'erased cue equality')
            assert not scored['both_pass'][:,:,2].any(),'Erased record passed both cues'
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
        verification=verify(folder,cfg)
        assert verification['status']=='PASS'
        status(folder,status='RUNNING',phase='report_and_figures')
        render(folder,cfg)
        from plot import plot
        plot(folder,cfg)
        check_code(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in ('console.log','PID','LAUNCH.json')}
        write(folder/'COMPLETE.json',dict(status='COMPLETE',completed_at_utc=stamp(),seconds=time.perf_counter()-started,
            scientific_status='DEVELOPMENT_FIXED_INJURY_PROBE_NOT_CONFIRMATORY',blocks_completed=cfg['blocks'],
            cases=64,trajectories=3072,endpoint_read_scores=9216,native_replay_passed=True,
            independent_verification_passed=True,receipts=receipts,outputs_sha256=outputs,
            automatic_successor=False,figure_visual_review_pending=True))
        print('COMPLETE: report, raw evidence and independent verification saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-started,traceback=traceback.format_exc())
        write(folder/'FAILED.json',failure);status(folder,status='FAILED',phase='failed')
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    main(parser.parse_args().run.resolve())
