"""Check retained technical evidence and every source boundary before the diagnostic."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import check_inputs,sha,utc
from E026_restoration_intervention.workflow import fixtures


def load(path):return json.loads(path.read_text())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--figure-inspected',action='store_true',required=True);parser.parse_args()
    destination=HERE/'analysis/prelaunch_verification_v1.json';assert not destination.exists()
    fixtures();receipt_path=HERE/'analysis/fixtures_v1.json';receipt=load(receipt_path)
    invocation=HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256']==sha(invocation)
    assert receipt['inputs_sha256']==load(invocation)['inputs_sha256']
    evidence={}
    for label,run,count,nfiles in (
        ('fixture',HERE/'analysis/fixture_attempt1',2688,28),
        ('benchmark',HERE/'runs/benchmark_v1',1344,29)):
        check_inputs(run);manifest=load(run/'manifest.json')
        assert len(manifest['inputs_sha256'])==21 and manifest['inputs_sha256']==receipt['inputs_sha256']
        complete,audit=load(run/'COMPLETE.json'),load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status']=='COMPLETE' and audit['status']=='PASS' and not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256'])==nfiles
        for rel,digest in complete['outputs_sha256'].items():assert sha(run/rel)==digest,(label,rel)
        assert audit['complete_sha256']==sha(run/'COMPLETE.json') and audit['audit_code_sha256']==sha(HERE/'audit.py')
        assert audit['individual_observations']==count
        for key,value in audit.items():
            if isinstance(value,bool):assert value,key
        with (run/'observations.csv').open(newline='') as handle:assert sum(1 for _ in csv.DictReader(handle))==count
        summary=load(run/'summary.json');assert summary['status']=='TECHNICAL_ONLY'
        for item in summary['focal'].values():assert item['lower_bound_above_zero'] is item['lower_bound_above_010'] is None
        assert len(summary['panels'])==8 and not summary['new_independent_cohort']
        evidence[label]=dict(original_outputs_verified=nfiles,individual_observations=count,
            complete_sha256=sha(run/'COMPLETE.json'),audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            simulation_seconds=complete['seconds'],audit_seconds=audit['seconds'])
    check_inputs(HERE/'jobs/benchmark_v1')
    status=load(HERE/'jobs/benchmark_v1/status.json');figure=HERE/'figures/benchmark_v1';prov=load(figure/'provenance.json')
    assert status['status']=='COMPLETE'
    assert status['scientific_complete_sha256']==prov['complete_sha256']==evidence['benchmark']['complete_sha256']
    assert status['audit_sha256']==prov['audit_sha256']==evidence['benchmark']['audit_sha256']
    assert status['figure_provenance_sha256']==sha(figure/'provenance.json')
    assert prov['summary_sha256']==sha(HERE/'runs/benchmark_v1/summary.json') and prov['plot_code_sha256']==sha(HERE/'plot.py')
    for rel,digest in prov['outputs_sha256'].items():assert sha(figure/rel)==digest
    forecast_path=HERE/'analysis/forecast_v1.json';forecast=load(forecast_path)
    assert forecast['fixture_receipt_sha256']==sha(receipt_path)
    assert forecast['benchmark_complete_sha256']==evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256']==evidence['benchmark']['audit_sha256']
    assert forecast['inputs_sha256']==receipt['inputs_sha256']
    benchmark_forecast_path=HERE/'analysis/benchmark_forecast_v1.json';bench_forecast=load(benchmark_forecast_path)
    assert not bench_forecast['detached_required'] and bench_forecast['forecast_seconds']<=600
    assert bench_forecast['fixture_receipt_sha256']==sha(receipt_path)
    assert bench_forecast['inputs_sha256']==receipt['inputs_sha256']
    available=shutil.disk_usage(HERE).free;assert available>forecast['storage_with_reserve_bytes']
    source_evidence={}
    for label,spec in load(HERE/'SOURCE_DATA.json').items():
        source=ROOT/spec['path'];check_inputs(source)
        for rel,digest in spec['provenance_sha256'].items():assert sha(source/rel)==digest
        old_audit=load(source/'INDEPENDENT_AUDIT.json')
        assert old_audit['status']=='PASS' and old_audit['complete_sha256']==sha(source/'COMPLETE.json')
        nfiles=0
        for block,files in spec['files'].items():
            for name,digest in files.items():assert sha(source/name)==digest,(label,block,name);nfiles+=1
        source_evidence[label]=dict(path=spec['path'],blocks=spec['blocks'],raw_files_verified=nfiles,
            complete_sha256=sha(source/'COMPLETE.json'),audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'))
    assert source_evidence['cohort']['blocks']==list(range(23000,23032))
    closeout_path=ROOT/'E025_rewriting_confirmation/analysis/closeout_v1.json';closeout=load(closeout_path)
    assert closeout['status']=='PASS'
    assert closeout['verification_code_sha256']==sha(closeout_path.parent/'verify_closeout.py')
    predecessors=closeout['predecessor_frozen_inputs_unchanged']+['E025_rewriting_confirmation/runs/confirmation_v1']
    for rel in predecessors:check_inputs(ROOT/rel)
    for rel in ('E022_reader_compensation/analysis/transmission_diagnosis_v1',
        'E025_rewriting_confirmation/analysis/rebuilding_leads_v1','E025_rewriting_confirmation/analysis/rebuilding_link_scale_v1'):check_inputs(ROOT/rel)
    active=[str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('PREPARED','RUNNING')]
    assert not active,active
    for rel in ('runs/restoration_v1','jobs/restoration_v1'):assert not (HERE/rel).exists()
    result=dict(status='PASS',utc=utc(),tests=5,scientific_inputs=21,evidence=evidence,
        benchmark_completed_utc=status['utc'],benchmark_workflow_seconds=status['seconds'],
        benchmark_minus_forecast_seconds=status['seconds']-bench_forecast['forecast_seconds'],
        fixture_receipt_sha256=sha(receipt_path),benchmark_forecast_sha256=sha(benchmark_forecast_path),
        benchmark_figure_visually_inspected=True,figure_provenance_sha256=sha(figure/'provenance.json'),
        forecast_sha256=sha(forecast_path),forecast_seconds=forecast['forecast_seconds'],workers=forecast['workers'],
        cpu_affinity=forecast['cpu_affinity'],numerical_threads=1,storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'],
        available_bytes=available,source_data_index_sha256=sha(HERE/'SOURCE_DATA.json'),source_evidence=source_evidence,
        predecessor_closeout_sha256=sha(closeout_path),predecessor_inputs_unchanged=predecessors,
        predecessor_diagnoses_inputs_unchanged=True,prior_active_jobs=active,
        diagnostic_design='Four final-packet interventions on all existing E025 blocks; post hoc pointwise intervals',
        new_intervention_cohort_outcomes_inspected=False,
        operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'),verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({k:result[k] for k in ('status','utc','evidence','benchmark_workflow_seconds','forecast_seconds','workers',
        'storage_with_reserve_bytes','available_bytes','source_evidence')},indent=2),flush=True)


if __name__=='__main__':main()
