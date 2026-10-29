"""Freeze, qualify excluded runs, and close out immutable scientific evidence."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import check_inputs,dump,new_run,sha,utc
from E083_reader_repeatability.plan import HERE,ROOT
from E083_reader_repeatability.run import input_paths
from E083_reader_repeatability.data import verify_receipts


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
    assert status['status']=='COMPLETE' and status['complete_sha256']==sha(run/'COMPLETE.json') and status['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json')
    s=json.loads((run/'summary.json').read_text())
    assert s['primary_effects']==a['primary_effects'] and s['alignment_at_both_cohorts']==a['alignment_at_both_cohorts']
    return run,c,a,manifest,status


def qualify():
    evidence={};runs={}
    test=HERE/'analysis/development_tests_v1.json';tr=json.loads(test.read_text())
    assert tr['status']=='PASS' and tr['tests_sha256']==sha(HERE/'tests.py')
    evidence[str(test.relative_to(ROOT))]=sha(test)
    for name in ('fixture_v1','benchmark_v1'):
        run,c,a,m,status=checked(name)
        assert a['alignment_at_both_cohorts'] is None and all(v is None for v in a['primary_effects'].values())
        assert a['blocks_checked']==2
        for file in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json','repeatability.png'):
            evidence[str((run/file).relative_to(ROOT))]=sha(run/file)
        runs[name]=dict(seconds=status['seconds'],outputs_verified=len(c['outputs_sha256']),summaries_checked=a['summaries_checked'])
    bench=HERE/'runs/benchmark_v1';c=json.loads((bench/'COMPLETE.json').read_text());scaled={}
    for phase in ('production','audit'):
        scaled[phase+'_reader_seconds']=max(c[phase+'_reader_block_seconds'])*16
        scaled[phase+'_static_seconds']=max(c[phase+'_static_block_seconds'])*4
    seconds={str(w):3*sum(scaled.values())*math.ceil(64/w)+120 for w in range(1,9)}
    arrays=0
    for path in bench.glob('*.npz'):
        with np.load(path,allow_pickle=False) as z:arrays+=sum(z[k].nbytes for k in z.files)
    forecast=dict(utc=utc(),scaled_seconds_per_scientific_block=scaled,recipient_scale=4,read_step_scale=4,
        timing_margin=3,uses_slower_of_two_benchmark_cohorts=True,seconds_by_workers=seconds,
        unpadded_seconds_by_workers={str(w):sum(scaled.values())*math.ceil(64/w)+120 for w in range(1,9)},
        storage_with_reserve_bytes=math.ceil(1.5*arrays/2*4*64)+256*1024**2,
        benchmark_complete_sha256=sha(bench/'COMPLETE.json'))
    assert not (HERE/'analysis/forecast_v1.json').exists();dump(HERE/'analysis/forecast_v1.json',forecast)
    assert not (HERE/'analysis/technical_v1.json').exists()
    dump(HERE/'analysis/technical_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,runs=runs,
        inputs_sha256=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256'],evidence_sha256=evidence,scientific_outcomes_seen=False))
    print(json.dumps(dict(runs=runs,forecast=forecast),indent=2))


def closeout():
    assert not (HERE/'analysis/closeout_v1.json').exists()
    run,c,a,m,status=checked('repeatability_v1');verify_receipts('scientific');assert a['blocks_checked']==64
    dump(HERE/'analysis/closeout_v1.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),original_outputs_verified=len(c['outputs_sha256']),
        frozen_inputs_verified=len(m['inputs_sha256']),summaries_checked=a['summaries_checked'],primary_effects=a['primary_effects'],
        alignment_at_both_cohorts=a['alignment_at_both_cohorts'],figure_inspected=True,figure_sha256=sha(run/'repeatability.png'),
        seconds=status['seconds'],retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor_started=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('freeze','qualify','closeout'));p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    if a.action=='freeze':
        for mode in ('fixture','benchmark','scientific'):verify_receipts(mode)
        test=json.loads((HERE/'analysis/development_tests_v1.json').read_text());assert test['status']=='PASS' and test['tests_sha256']==sha(HERE/'tests.py')
        new_run(HERE/'analysis/freeze_v1',input_paths(),dict(experiment='E083',scientific_outcomes_seen=False))
    else:
        assert a.figures_inspected
        qualify() if a.action=='qualify' else closeout()
