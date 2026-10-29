"""Freeze inputs, qualify excluded runs, and verify completed scientific artifacts."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import check_inputs,dump,new_run,sha,utc
from E068_fresh_recovery_confirmation.plan import HERE,ROOT,settings
from E068_fresh_recovery_confirmation.run import input_paths
from E068_fresh_recovery_confirmation.data import verify_receipts


def checked(name):
    run=HERE/'runs'/name;check_inputs(run)
    c=json.loads((run/'COMPLETE.json').read_text());a=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass'] and a['status']=='PASS' and a['controls_pass']
    assert a['complete_sha256']==sha(run/'COMPLETE.json')
    assert a['audit_model_sha256']==sha(HERE/'audit_model.py') and a['inference_sha256']==sha(HERE/'inference.py')
    for rel,digest in c['outputs_sha256'].items():assert sha(run/rel)==digest,rel
    manifest=json.loads((run/'manifest.json').read_text());frozen=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())
    assert manifest['inputs_sha256']==frozen['inputs_sha256']
    job=HERE/'jobs'/name;check_inputs(job);status=json.loads((job/'status.json').read_text())
    assert status['status']=='COMPLETE' and status['complete_sha256']==sha(run/'COMPLETE.json')
    assert status['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json')
    s=json.loads((run/'summary.json').read_text())
    assert s['primary_effects']==a['primary_effects'] and s['recovery_supported']==a['recovery_supported']
    return run,c,a,manifest,status


def qualify():
    evidence={};runs={}
    for name in ('fixture_v1','benchmark_v1'):
        run,c,a,m,status=checked(name)
        worker=json.loads((run/'worker_900041.json').read_text());assert worker['legacy_writer_and_alias_projections_verified'] and worker['source_projection_verified']
        assert worker['ancestry_boundaries_replayed']==32 and worker['source_continuation_boundaries_replayed']==3 and worker['recovery_boundaries_replayed']==3
        assert a['recovery_supported'] is None and all(v is None for v in a['primary_effects'].values())
        for file in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json','rebuilding.png'):
            evidence[str((run/file).relative_to(ROOT))]=sha(run/file)
        runs[name]=dict(seconds=status['seconds'],outputs_verified=len(c['outputs_sha256']),summaries_checked=a['summaries_checked'])
    bench=HERE/'runs/benchmark_v1';c=json.loads((bench/'COMPLETE.json').read_text())
    target,small=settings('scientific'),settings('benchmark')
    ratio=target['recipients']/small['recipients'];scaled={};scales={}
    for key,values in c['phase_block_seconds'].items():
        if key.endswith('_acquisition'):scale=target['source_config']['teach_steps']/small['source_config']['teach_steps']
        elif key.endswith('_pulse'):
            scale=ratio*(target['body']['body_pre_steps']+target['body']['pulse_steps'])/(small['body']['body_pre_steps']+small['body']['pulse_steps'])
        elif '_ancestry_' in key or '_source_continuation_' in key:
            stage='source_cycle' if '_ancestry_' in key else 'source_continuation';kind=key.rsplit('_',1)[1]
            scale=ratio*(target[stage][kind+'_steps']/small[stage][kind+'_steps'] if kind in ('read','write') else 1)
        elif key.endswith('_terminal_read'):scale=ratio*target['reader']['read_steps']/small['reader']['read_steps']
        elif key.endswith('_rebuild'):
            scale=ratio*max(target['cycle'][k]/small['cycle'][k] for k in ('read_steps','write_steps'))
        else:scale=ratio
        scales[key]=scale;scaled[key]=values[0]*scale
    seconds={str(w):3*sum(scaled.values())*math.ceil(32/w)+120 for w in range(1,9)}
    arrays=0
    for path in bench.glob('*.npz'):
        with np.load(path,allow_pickle=False) as z:
            for key in z.files:
                scale=ratio
                if path.name.startswith('acquisition_'):scale=1
                elif path.name.startswith(('source_boundary_','source_continuation_','boundary_')):
                    stage='source_cycle' if path.name.startswith('source_boundary_') else 'source_continuation' if path.name.startswith('source_continuation_') else 'cycle'
                    if key in ('read_state_hashes','state_hashes','write_state_hashes'):
                        kind='write' if key.startswith('write') else 'read'
                        scale=target[stage][kind+'_steps']/small[stage][kind+'_steps']
                    elif key=='late_ports':scale*=target['config']['observe_steps']/small['config']['observe_steps']
                elif path.name.startswith('body_'):
                    if key=='state_hashes':scale=(target['body']['body_pre_steps']+target['body']['pulse_steps'])/(small['body']['body_pre_steps']+small['body']['pulse_steps'])
                    elif key=='port_windows':scale*=target['body']['observe_steps']/small['body']['observe_steps']
                elif path.name.startswith('assay_'):
                    if key=='state_hashes':scale=target['reader']['read_steps']/small['reader']['read_steps']
                    elif key=='late_ports':scale*=target['reader']['observe_steps']/small['reader']['observe_steps']
                arrays+=z[key].nbytes*scale
    forecast=dict(utc=utc(),scaled_seconds_per_scientific_block=scaled,phase_scale_factors=scales,
        timing_margin=3,seconds_by_workers=seconds,
        unpadded_seconds_by_workers={str(w):sum(scaled.values())*math.ceil(32/w)+120 for w in range(1,9)},
        recovery_rebuild_scale_uses_maximum_read_or_holding_ratio=True,
        storage_with_reserve_bytes=math.ceil(1.5*arrays*32)+256*1024**2,
        benchmark_complete_sha256=sha(bench/'COMPLETE.json'))
    assert not (HERE/'analysis/forecast_v1.json').exists();dump(HERE/'analysis/forecast_v1.json',forecast)
    assert not (HERE/'analysis/technical_v1.json').exists()
    dump(HERE/'analysis/technical_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,runs=runs,
        inputs_sha256=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256'],
        evidence_sha256=evidence,scientific_outcomes_seen=False))
    print(json.dumps(dict(runs=runs,forecast=forecast),indent=2))


def closeout():
    assert not (HERE/'analysis/closeout_v1.json').exists()
    run,c,a,m,status=checked('confirmation_v1');verify_receipts('scientific');assert a['blocks_checked']==32
    dump(HERE/'analysis/closeout_v1.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),original_outputs_verified=len(c['outputs_sha256']),
        frozen_inputs_verified=len(m['inputs_sha256']),summaries_checked=a['summaries_checked'],
        primary_effects=a['primary_effects'],recovery_supported=a['recovery_supported'],figure_inspected=True,
        figure_sha256=sha(run/'rebuilding.png'),seconds=status['seconds'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor_started=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('freeze','qualify','closeout'))
    p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    if a.action=='freeze':
        for mode in ('fixture','benchmark','scientific'):verify_receipts(mode)
        new_run(HERE/'analysis/freeze_v1',input_paths(),dict(experiment='E068',scientific_outcomes_seen=False))
    else:
        assert a.figures_inspected
        qualify() if a.action=='qualify' else closeout()
