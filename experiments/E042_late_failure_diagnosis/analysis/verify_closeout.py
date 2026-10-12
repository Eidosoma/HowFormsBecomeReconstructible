"""Close the completed diagnosis without new measurements or dynamics."""
import argparse,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent;sys.path.insert(0,str(ROOT))
from common import check_inputs,dump,sha,utc
from E015_functional_inheritance.audit import verify
from E042_late_failure_diagnosis.run import inputs,source_check


def load(p):return json.loads(p.read_text())


def main():
    p=argparse.ArgumentParser();p.add_argument('--figure-inspected',action='store_true',required=True);p.parse_args()
    analysis=HERE/'analysis';dest=analysis/'closeout_v1.json';assert not dest.exists()
    source=source_check();check_inputs(analysis/'freeze_v1')
    technical=load(analysis/'technical_v1.json');forecast=load(analysis/'forecast_v1.json')
    assert technical['status']=='PASS' and technical['tests']==8
    assert technical['freeze_manifest_sha256']==sha(analysis/'freeze_v1/manifest.json')
    assert technical['runner_sha256']==sha(analysis/'run_technical.py')
    for stage,item in technical['stages'].items():
        assert item['returncode']==0 and item['log_sha256']==sha(analysis/f'{stage}_v1.log')
    assert forecast['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs()}
    runs={}
    for name,blocks,count in (('benchmark_v1',[900041],17),('diagnosis_v1',list(range(32000,32032)),79)):
        r=HERE/'runs'/name;manifest=verify(r);check_inputs(HERE/'jobs'/name)
        complete,audit,s=map(load,(r/'COMPLETE.json',r/'INDEPENDENT_AUDIT.json',r/'summary.json'))
        assert manifest['inputs_sha256']==forecast['inputs_sha256'] and len(manifest['inputs_sha256'])==12
        assert manifest['contract']['blocks']==s['blocks']==blocks
        assert len(complete['outputs_sha256'])==count
        assert len(list(r.glob('measurements_*.npz')))==len(list(r.glob('worker_*.json')))==len(blocks)
        assert audit['status']=='PASS' and audit['audit_code_sha256']==sha(HERE/'audit.py')
        assert audit['complete_sha256']==sha(r/'COMPLETE.json')
        assert all(v for v in audit.values() if isinstance(v,bool))
        assert s['no_new_trajectories'] and s['prior_cases_reused'] and not s['causal_claim_established']
        assert s['status']==('TECHNICAL_ONLY' if name=='benchmark_v1' else 'EXPLORATORY_DIAGNOSIS_COMPLETE')
        assert len(s['series'])==len(s['definitions'])==13483
        assert s['lineages']==(8 if name=='benchmark_v1' else 512)
        status=load(HERE/'jobs'/name/'status.json');assert status['status']=='COMPLETE' and not status['automatic_successor_started']
        fig=HERE/'figures'/name;provenance=load(fig/'provenance.json')
        for key,file in (('complete_sha256','COMPLETE.json'),('audit_sha256','INDEPENDENT_AUDIT.json'),('summary_sha256','summary.json')):
            assert provenance[key]==sha(r/file)
            if key!='summary_sha256':assert status[key]==provenance[key]
        assert provenance['plot_code_sha256']==sha(HERE/'plot.py')
        for file,digest in provenance['outputs_sha256'].items():assert sha(fig/file)==digest
        assert status['figure_provenance_sha256']==sha(fig/'provenance.json')
        runs[name]=dict(original_outputs_verified=count,blocks=len(blocks),summaries=13483,workflow_seconds=status['seconds'],
            finished_utc=status['utc'],retained_bytes=sum(p.stat().st_size for p in r.rglob('*') if p.is_file()),
            complete_sha256=sha(r/'COMPLETE.json'),audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'),summary_sha256=sha(r/'summary.json'),figure_provenance_sha256=sha(fig/'provenance.json'))
    assert forecast['benchmark_complete_sha256']==runs['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256']==runs['benchmark_v1']['audit_sha256']
    assert runs['diagnosis_v1']['retained_bytes']<forecast['storage_with_reserve_bytes']
    s=load(HERE/'runs/diagnosis_v1/summary.json')['series']
    totals=lambda key:(sum(s[key]['block_numerators']),sum(s[key]['block_denominators']))
    assert totals('terminal.g32.bridge_rewrite.scattered.both_correct')==(428,512)
    assert totals('joint.g32.bridge_rewrite.scattered_failure_other_terminal_success|scattered_failure')==(30,84)
    assert totals('joint.g32.bridge_rewrite.all_terminal_failed|scattered_failure')==(54,84)
    assert s['joint.g32.bridge_rewrite.next_body_success_given_scattered_failure']['mean'] is None
    assert totals('graph.g32.bridge_rewrite.scattered.nonzero_all_outputs|scattered_failure')==(84,84)
    active=[str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('RUNNING','PREPARED')]
    assert not active,active
    result=dict(status='PASS',utc=utc(),verification_code_sha256=sha(__file__),runs=runs,frozen_inputs_verified=12,
        all_original_outputs_and_source_provenance_verified=True,operational_receipts_verified=True,
        figures_visually_inspected=True,scientific_log_sha256=sha(analysis/'scientific_v1.log'),source_sha256=source['sha256'],
        forecast_seconds=forecast['forecast_seconds'],actual_minus_forecast_seconds=runs['diagnosis_v1']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'],available_bytes=shutil.disk_usage(HERE).free,
        active_jobs=active,new_trajectories_run=False,subsequent_experiment_started=False)
    dump(dest,result)
    print(json.dumps({k:result[k] for k in ('status','utc','runs','actual_minus_forecast_seconds','available_bytes')},indent=2))


if __name__=='__main__':main()
