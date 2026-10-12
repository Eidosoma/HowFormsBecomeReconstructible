"""Verify completed confirmation artifacts without running new trajectories."""
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
    destination = analysis/'closeout_v1.json'
    assert not destination.exists()
    fixtures()
    source = source_evidence()
    receipt_path = analysis/'fixtures_v1.json'
    receipt = load(receipt_path)
    invocation = analysis/'fixture_invocation_v1.json'
    frozen = load(analysis/'freeze_v1.json')
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256'] == frozen['inputs_sha256']
    assert frozen['source_evidence_sha256'] == sha(HERE/'SOURCE_EVIDENCE.json')
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', analysis/'fixture_attempt1', 14112, 384, 39),
        ('confirmation_v1', HERE/'runs/confirmation_v1', 903168, 24576, 319)):
        manifest = verify(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert len(complete['outputs_sha256']) == nfiles
        assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        for name, count in (('observations.csv', terminal), ('body_observations.csv', body)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count
        assert len(manifest['inputs_sha256']) == 26 and manifest['inputs_sha256'] == receipt['inputs_sha256']
        figure = HERE/'figures'/run.name
        prov = load(figure/'provenance.json')
        assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
        assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
        evidence[label] = dict(original_outputs_verified=nfiles, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), manifest_sha256=sha(run/'manifest.json'),
            summary_sha256=sha(run/'summary.json'), individual_observations=terminal,
            body_individual_observations=body, simulation_seconds=complete['seconds'],
            audit_seconds=audit['seconds'], figure_provenance_sha256=sha(figure/'provenance.json'))
        summary = load(run/'summary.json')
        assert summary['confirmation_of'] == 'E029' and not summary['prior_cases_pooled']
        if label == 'fixture':
            assert summary['status'] == 'TECHNICAL_ONLY'
            assert summary['primary']['lower_bound_above_010'] is None
            assert summary['noninferiority']['lower_bound_above_minus_005'] is None
            assert summary['qualification_requirements_pass'] is summary['full_maturing_renewal_qualified'] is None
    run, job = HERE/'runs/confirmation_v1', HERE/'jobs/confirmation_v1'
    check_inputs(job)
    status = load(job/'status.json')
    assert status['status'] == 'COMPLETE'
    for key, expected in (('scientific_complete_sha256', 'complete_sha256'),
                          ('audit_sha256', 'audit_sha256'), ('figure_provenance_sha256', 'figure_provenance_sha256')):
        assert status[key] == evidence['confirmation_v1'][expected]
    evidence['confirmation_v1'].update(completed_utc=status['utc'], workflow_seconds=status['seconds'])
    forecast_path, prelaunch_path = analysis/'forecast_v1.json', analysis/'prelaunch_verification_v1.json'
    forecast, prelaunch = load(forecast_path), load(prelaunch_path)
    launch = load(analysis/'launch_verification_v1.json')
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(forecast_path)
    assert launch['preflight_sha256'] == sha(prelaunch_path)
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(analysis/'launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(analysis/'verify_prelaunch.py')
    assert forecast['fixture_receipt_sha256'] == prelaunch['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert prelaunch['freeze_sha256'] == sha(analysis/'freeze_v1.json')
    for key, value in prelaunch['fixture'].items(): assert evidence['fixture'][key] == value, key
    assert forecast['source_evidence_sha256'] == prelaunch['source_evidence_sha256'] == sha(HERE/'SOURCE_EVIDENCE.json')
    assert forecast['prior_full_run_measurement_reused'] and not forecast['new_throughput_benchmark_run']
    assert forecast['source_workflow_seconds'] == source['workflow_seconds']
    assert forecast['source_cohort_bytes'] == source['cohort_bytes']
    assert forecast['storage_with_reserve_bytes'] == source['cohort_bytes']+1024**3
    # The numerical model and all indexed old provenance must remain unchanged.
    prior = ROOT/source['source_run']
    verify(prior)
    assert len(load(prior/'COMPLETE.json')['outputs_sha256']) == source['original_outputs_verified'] == 316
    prior_closed = load(ROOT/'E029_maturing_renewal/analysis/closeout_v1.json')
    assert prior_closed['status'] == 'PASS'
    assert prior_closed['verification_code_sha256'] == sha(ROOT/'E029_maturing_renewal/analysis/verify_closeout.py')
    assert prelaunch['predecessor_inputs_unchanged'] == frozen['predecessor_frozen_inputs_unchanged'] == source['predecessor_frozen_inputs_unchanged']
    assert prelaunch['predecessor_diagnosis_inputs_unchanged'] == source['predecessor_diagnosis_inputs_unchanged']
    for rel in source['predecessor_frozen_inputs_unchanged']+source['predecessor_diagnosis_inputs_unchanged']:
        check_inputs(ROOT/rel)
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    contract = manifest['contract']
    blocks = list(range(26000, 26032))
    assert contract['blocks'] == summary['blocks'] == prelaunch['unused_scientific_blocks'] == frozen['unused_blocks'] == blocks
    assert not set(blocks).intersection(source['source_blocks'])
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == forecast['cpu_affinity']
    assert contract['workers'] == forecast['workers'] == 8
    for key, value in (('config', source['config']), ('cycle', source['cycle']), ('conditions', source['conditions']),
                       ('panels', source['panels']), ('receivers', source['receivers'])):
        assert contract[key] == value, key
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['evidence_status'] == contract['mode'] == 'prospective_maturing_confirmation'
    assert summary['strength_threshold'] == .5 and not summary['transmitted_ancestry_metadata']
    primary, ni = summary['primary'], summary['noninferiority']
    contrasts = summary['packet_contrasts']['3']['local_strength']
    assert primary['statistics'] == contrasts['maturing_minus_selective']['both_cues']['scattered']
    assert ni['statistics'] == contrasts['maturing_minus_strength_compensated']['both_cues']['scattered']
    assert primary['margin'] == .10 and ni['margin'] == -.05
    assert primary['lower_bound_above_010'] == (primary['statistics']['ci95'][0] > .10)
    assert ni['lower_bound_above_minus_005'] == (ni['statistics']['ci95'][0] > -.05)
    assert len(summary['qualification_gates']) == 14 and len(summary['boundary_gates']) == 12
    assert summary['qualification_requirements_pass'] == all(summary['qualification_gates'].values())
    qualified = primary['lower_bound_above_010'] and ni['lower_bound_above_minus_005'] and summary['qualification_requirements_pass']
    assert summary['full_maturing_renewal_qualified'] == qualified
    assert summary['status'] == ('MATURING_RENEWAL_CONFIRMED' if qualified else 'MATURING_RENEWAL_NOT_CONFIRMED')
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
        if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], evidence_status=summary['evidence_status'],
        confirmation_of='E029', prior_cases_pooled=False, model_byte_identical_to_e029=True,
        primary=primary, noninferiority=ni, qualification_gates=summary['qualification_gates'], runs=evidence,
        source_original_outputs_verified=316, source_evidence_sha256=sha(HERE/'SOURCE_EVIDENCE.json'),
        forecast_seconds=forecast['forecast_seconds'], actual_workflow_seconds=status['seconds'],
        actual_minus_forecast_seconds=status['seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        fixture_receipt_and_evidence_verified=True, workflow_and_figure_references_verified=True,
        launch_receipts_and_operational_launcher_verified=True, reused_runtime_references_verified=True,
        scientific_figure_visually_inspected=True, freeze_and_unused_id_receipts_verified=True,
        predecessor_frozen_inputs_unchanged=source['predecessor_frozen_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=source['predecessor_diagnosis_inputs_unchanged'],
        active_experiment_jobs=active, available_bytes=shutil.disk_usage(HERE).free,
        new_trajectories_run_during_closeout=False, subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'verified_utc', 'scientific_status', 'runs',
        'actual_workflow_seconds', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
