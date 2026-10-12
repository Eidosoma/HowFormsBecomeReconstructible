"""Verify fresh fixtures, unchanged model, prior timing evidence and capacity."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E015_functional_inheritance.audit import verify
from E030_maturing_confirmation.workflow import fixtures, source_evidence


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    analysis = HERE/'analysis'
    destination = analysis/'prelaunch_verification_v1.json'
    assert not destination.exists()
    fixtures()
    source = source_evidence()
    frozen = load(analysis/'freeze_v1.json')
    receipt_path = analysis/'fixtures_v1.json'
    receipt = load(receipt_path)
    invocation = analysis/'fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256'] == frozen['inputs_sha256']
    assert frozen['source_evidence_sha256'] == sha(HERE/'SOURCE_EVIDENCE.json')
    run = analysis/'fixture_attempt1'
    manifest = verify(run)
    assert len(manifest['inputs_sha256']) == 26 and manifest['inputs_sha256'] == receipt['inputs_sha256']
    complete, audit, summary = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json'), load(run/'summary.json')
    assert len(complete['outputs_sha256']) == 39
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
    assert audit['individual_observations'] == 14112 and audit['body_individual_observations'] == 384
    for key, value in audit.items():
        if isinstance(value, bool): assert value, key
    for name, count in (('observations.csv', 14112), ('body_observations.csv', 384)):
        with (run/name).open(newline='') as handle:
            assert sum(1 for _ in csv.DictReader(handle)) == count
    assert summary['status'] == 'TECHNICAL_ONLY' and summary['confirmation_of'] == 'E029'
    assert not summary['prior_cases_pooled'] and summary['strength_threshold'] == .5
    assert summary['primary']['lower_bound_above_010'] is None
    assert summary['noninferiority']['lower_bound_above_minus_005'] is None
    assert summary['qualification_requirements_pass'] is summary['full_maturing_renewal_qualified'] is None
    assert len(summary['panels']) == 42 and len(summary['qualification_gates']) == 14
    figure = HERE/'figures/fixture_attempt1'
    prov = load(figure/'provenance.json')
    assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
    assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
    assert prov['summary_sha256'] == sha(run/'summary.json')
    assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
    forecast_path = analysis/'forecast_v1.json'
    forecast = load(forecast_path)
    assert forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert forecast['source_evidence_sha256'] == sha(HERE/'SOURCE_EVIDENCE.json')
    assert forecast['prior_full_run_measurement_reused'] and not forecast['new_throughput_benchmark_run']
    assert forecast['source_workflow_seconds'] == source['workflow_seconds']
    assert forecast['source_cohort_bytes'] == source['cohort_bytes']
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    ids = set(range(26000, 26032))
    for p in ROOT.glob('E*/**/manifest.json'):
        assert not ids.intersection(load(p).get('contract', {}).get('blocks', [])), str(p)
    assert frozen['unused_blocks'] == sorted(ids)
    for rel in source['predecessor_frozen_inputs_unchanged']+source['predecessor_diagnosis_inputs_unchanged']:
        check_inputs(ROOT/rel)
    assert source['original_outputs_verified'] == 316
    # The source index and E029 closeout bind the already-verified old raw outputs.
    # The forecast cannot incorporate any newly acquired scientific cases.
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
        if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('runs/confirmation_v1', 'jobs/confirmation_v1'): assert not (HERE/rel).exists()
    evidence = dict(original_outputs_verified=39, individual_observations=14112, body_individual_observations=384,
        complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'],
        figure_provenance_sha256=sha(figure/'provenance.json'))
    result = dict(status='PASS', utc=utc(), tests=9, scientific_inputs=26, fixture=evidence,
        source_run=source['source_run'], prior_original_outputs_verified=316,
        fixture_receipt_sha256=sha(receipt_path), fixture_figure_visually_inspected=True,
        source_evidence_sha256=sha(HERE/'SOURCE_EVIDENCE.json'), model_byte_identical_to_e029=True,
        freeze_sha256=sha(analysis/'freeze_v1.json'), forecast_sha256=sha(forecast_path),
        forecast_seconds=forecast['forecast_seconds'], workers=forecast['workers'],
        cpu_affinity=forecast['cpu_affinity'], numerical_threads=1,
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        unused_scientific_blocks=sorted(ids), prior_active_jobs=active,
        predecessor_inputs_unchanged=source['predecessor_frozen_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=source['predecessor_diagnosis_inputs_unchanged'],
        new_scientific_cohort_outcomes_inspected=False, prior_cases_pooled=False, threshold_search=False,
        operational_launcher_sha256=sha(analysis/'launch_verified.py'),
        verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps({k: result[k] for k in ('status', 'utc', 'fixture', 'source_run', 'prior_original_outputs_verified',
        'forecast_seconds', 'workers', 'storage_with_reserve_bytes', 'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
