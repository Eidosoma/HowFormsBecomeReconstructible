"""Freeze, qualify and forecast, or verify completed immutable artifacts."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E015_functional_inheritance.audit import verify
from E057_fresh_capture_confirmation.plan import HERE,ROOT,settings
from E057_fresh_capture_confirmation.run import input_paths
from E057_fresh_capture_confirmation.workflow import predecessor_gate
from E057_fresh_capture_confirmation.data import receipt


def checked_run(name):
    run=HERE/'runs'/name;m=verify(run)
    frozen=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
    assert m['inputs_sha256']==frozen
    read=lambda p:json.loads(p.read_text())
    c=read(run/'COMPLETE.json');a=read(run/'INDEPENDENT_AUDIT.json');s=read(run/'summary.json')
    assert a['status']=='PASS' and a['complete_sha256']==sha(run/'COMPLETE.json')
    assert a['audit_code_sha256']==sha(HERE/'audit.py')
    assert a['all_acquisition_and_32_source_boundaries_replayed']
    assert a['all_sources_substitutions_assays_diagnostics_replayed'] and a['every_step_state_hashes_replayed']
    assert a['controls_pass'] and s['controls_pass'] and a['primary_effects']==s['primary_effects']
    assert a['primary_confirmed']==s['primary_confirmed']
    assert a['summaries_checked']==len(s['statistics'])
    assert c['blocks_completed']==len(m['contract']['blocks'])==s['independent_blocks']
    job=HERE/'jobs'/name;check_inputs(job);status=read(job/'status.json')
    assert status['status']=='COMPLETE'
    assert status['complete_sha256']==sha(run/'COMPLETE.json') and status['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json')
    for rel,digest in m['contract']['predecessor_evidence'].items():assert sha(ROOT/rel)==digest,rel
    fig=HERE/'figures'/name/'provenance.json';meta=read(fig)
    assert meta['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json') and meta['summary_sha256']==sha(run/'summary.json')
    assert meta['plot_code_sha256']==sha(HERE/'plot.py')
    for rel,digest in meta['outputs_sha256'].items():assert sha(fig.parent/rel)==digest
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'INDEPENDENT_AUDIT.json',
        run/'summary.json',fig,job/'status.json',job/'manifest.json',run/'manifest.json')}
    return m,c,a,s,evidence


def forecast():
    bench=HERE/'runs/benchmark_v1';sim=json.loads((bench/'worker_900041.json').read_text())
    audit=json.loads((bench/'audit_worker_900041.json').read_text())
    cfg=settings('scientific');b=settings('benchmark')
    R=cfg['config']['recipients']/b['config']['recipients']
    body_steps=lambda c:c['body']['body_pre_steps']+c['body']['pulse_steps']+c['body']['recovery_steps']
    ratios=dict(source=R*max(cfg['cycle']['read_steps']/b['cycle']['read_steps'],
                            cfg['cycle']['write_steps']/b['cycle']['write_steps']),
        perturb=R*body_steps(cfg)/body_steps(b),assay=R*cfg['reader']['read_steps']/b['reader']['read_steps'])
    block_seconds=sum((sim['stage_seconds'][k]+audit['stage_seconds'][k])*v for k,v in ratios.items())
    seconds={str(w):3*block_seconds*math.ceil(32/w)+180 for w in range(1,9)}
    size=sum(p.stat().st_size for p in bench.rglob('*') if p.is_file())
    # Reader/source arrays scale at most fourfold in R; hash lengths 16-fold,
    # and body window arrays fourfold in R and fourfold in observation length.
    storage=math.ceil(1.5*size*16*32)+256*1024**2
    assert shutil.disk_usage(HERE).free>storage
    return dict(utc=utc(),seconds_by_workers=seconds,scaled_block_seconds_including_audit=block_seconds,
        stage_scaling=ratios,benchmark_simulation_seconds=sim['seconds'],benchmark_audit_seconds=audit['seconds'],
        benchmark_stage_seconds=dict(simulation=sim['stage_seconds'],audit=audit['stage_seconds']),
        benchmark_bytes=size,storage_with_reserve_bytes=storage,free_bytes=shutil.disk_usage(HERE).free,
        detached_required=True,source_records_reused=False,
        basis='3x separately scaled source/body/assay benchmark seconds including replay, times worker waves, plus180s')


def main(action,inspected):
    cap_cpus(1)
    if action=='freeze':
        predecessor_gate();receipt('scientific')
        new_run(HERE/'analysis/freeze_v1',input_paths(),dict(experiment='E057',stage='freeze',
            fresh_source_outcomes_seen=False,prior_discovery_outcomes_seen=True))
        print('Frozen',len(input_paths()),'inputs');return
    assert inspected,'Inspect applicable figures before qualification/closeout'
    check_inputs(HERE/'analysis/freeze_v1');predecessor=predecessor_gate();evidence={};results={}
    for name in ('fixture_v1','benchmark_v1')+(('confirmation_v1',) if action=='closeout' else ()):
        m,c,a,s,ev=checked_run(name);evidence.update(ev)
        if name!='confirmation_v1':
            assert s['status']=='TECHNICAL_ONLY' and s['primary_confirmed'] is None
            assert all(x is None for x in s['primary_effects'].values())
        else:assert m['contract']['blocks']==list(range(38000,38032))
        results[name]=dict(outputs_verified=len(c['outputs_sha256']),summaries_checked=a['summaries_checked'],
            terminal_cue_observations=a['terminal_cue_observations'],status=s['status'])
    tests=HERE/'analysis/tests_v1.log';text=tests.read_text()
    assert '\nOK\n' in text and 'Ran 16 tests' in text
    evidence[str(tests.relative_to(ROOT))]=sha(tests)
    if action=='ready':
        estimate=forecast();path=HERE/'analysis/forecast_v1.json';assert not path.exists();dump(path,estimate)
        evidence[str(path.relative_to(ROOT))]=sha(path)
        result=dict(status='PASS',utc=utc(),tests=16,figures_inspected=True,scientific_run_started=False,
            automatic_successor_started=False,evidence_sha256=evidence,
            inputs_sha256=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256'])
        path=HERE/'analysis/technical_v1.json'
    else:
        ready=json.loads((HERE/'analysis/technical_v1.json').read_text())
        for rel,digest in ready['evidence_sha256'].items():assert sha(ROOT/rel)==digest
        result=dict(status='PASS',utc=utc(),figure_inspected=True,runs=results,evidence_sha256=evidence,
            predecessor_evidence=predecessor,code_sha256=sha(__file__),controls_pass=True,
            primary_effects=s['primary_effects'],primary_confirmed=s['primary_confirmed'],
            scientific_retained_bytes=sum(p.stat().st_size for p in (HERE/'runs/confirmation_v1').rglob('*') if p.is_file()),
            automatic_successor_started=False)
        path=HERE/'analysis/closeout_v1.json'
    assert not path.exists();dump(path,result);print(json.dumps(dict(path=str(path),status=result['status'],runs=results),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',required=True,choices=('freeze','ready','closeout'))
    p.add_argument('--figures-inspected',action='store_true');a=p.parse_args();main(a.action,a.figures_inspected)
