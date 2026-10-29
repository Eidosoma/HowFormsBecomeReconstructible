"""Freeze inputs, qualify excluded runs, and verify completed scientific artifacts."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import check_inputs,dump,new_run,sha,utc
from E065_fresh_compatibility_confirmation.plan import HERE,ROOT,settings
from E065_fresh_compatibility_confirmation.run import input_paths
from E065_fresh_compatibility_confirmation.data import verify_receipts


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
    assert s['primary_effects']==a['primary_effects'] and s['primary_confirmed']==a['primary_confirmed']
    return run,c,a,manifest,status


def qualify():
    evidence={};runs={}
    for name in ('fixture_v1','benchmark_v1'):
        run,c,a,m,status=checked(name)
        worker=json.loads((run/'worker_900041.json').read_text())
        assert worker['reduced_legacy_projection_verified'] and worker['source_boundaries_replayed']==32 and worker['continuation_boundaries_replayed']==3
        assert a['primary_confirmed'] is None and all(v is None for v in a['primary_effects'].values())
        for file in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json','confirmation.png'):
            evidence[str((run/file).relative_to(ROOT))]=sha(run/file)
        runs[name]=dict(seconds=status['seconds'],outputs_verified=len(c['outputs_sha256']),summaries_checked=a['summaries_checked'])
    bench=HERE/'runs/benchmark_v1';c=json.loads((bench/'COMPLETE.json').read_text())
    target=settings('scientific');small=settings('benchmark');ratio=target['recipients']/small['recipients']
    scaled={};scales={}
    for key,values in c['phase_block_seconds'].items():
        if key.endswith('_acquisition'):scale=target['config']['teach_steps']/small['config']['teach_steps']
        elif key.endswith('_pulse'):
            scale=ratio*(target['body']['body_pre_steps']+target['body']['pulse_steps'])/(small['body']['body_pre_steps']+small['body']['pulse_steps'])
        elif '_source_' in key or '_continuation_' in key:
            stage='source_cycle' if '_source_' in key else 'continuation';kind=key.rsplit('_',1)[1]
            scale=ratio*(target[stage][kind+'_steps']/small[stage][kind+'_steps'] if kind in ('read','write') else 1)
        elif key.endswith('_terminal_read'):scale=ratio*target['reader']['read_steps']/small['reader']['read_steps']
        else:scale=ratio
        scales[key]=scale;scaled[key]=values[0]*scale
    seconds={str(w):3*sum(scaled.values())*math.ceil(32/w)+120 for w in range(1,9)}
    arrays=0
    for path in bench.glob('*.npz'):
        with np.load(path,allow_pickle=False) as z:
            for key in z.files:
                scale=ratio
                if path.name.startswith('acquisition_'):scale=1
                elif path.name.startswith(('source_boundary_','continuation_')):
                    stage='source_cycle' if path.name.startswith('source_boundary_') else 'continuation'
                    if key in ('read_state_hashes','write_state_hashes'):
                        kind=key.split('_')[0];scale=target[stage][kind+'_steps']/small[stage][kind+'_steps']
                    elif key=='late_ports':scale*=target['config']['observe_steps']/small['config']['observe_steps']
                elif path.name.startswith('body_'):
                    if key=='state_hashes':scale=(target['body']['body_pre_steps']+target['body']['pulse_steps'])/(small['body']['body_pre_steps']+small['body']['pulse_steps'])
                    elif key=='port_windows':scale*=target['body']['observe_steps']/small['body']['observe_steps']
                elif path.name.startswith('assay_'):
                    if key=='state_hashes':scale=target['reader']['read_steps']/small['reader']['read_steps']
                    elif key=='late_ports':scale*=target['reader']['observe_steps']/small['reader']['observe_steps']
                arrays+=z[key].nbytes*scale
    forecast=dict(utc=utc(),scaled_seconds_per_scientific_block=scaled,phase_scale_factors=scales,
        timing_margin=3,seconds_by_workers=seconds,storage_with_reserve_bytes=math.ceil(1.5*arrays*32)+256*1024**2,
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
        primary_effects=a['primary_effects'],primary_confirmed=a['primary_confirmed'],figure_inspected=True,
        figure_sha256=sha(run/'confirmation.png'),seconds=status['seconds'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor_started=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('freeze','qualify','closeout'))
    p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    if a.action=='freeze':
        for mode in ('fixture','benchmark','scientific'):verify_receipts(mode)
        new_run(HERE/'analysis/freeze_v1',input_paths(),dict(experiment='E065',scientific_outcomes_seen=False))
    else:
        assert a.figures_inspected
        qualify() if a.action=='qualify' else closeout()
