"""Verify completed evidence and provenance without running new trajectories."""
import argparse
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E015_functional_inheritance.audit import verify
from E029_maturing_renewal.workflow import fixtures


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
    receipt_path = analysis/'fixtures_v1.json'
    receipt = load(receipt_path)
    invocation = analysis/'fixture_invocation_v1.json'
    frozen = load(analysis/'freeze_v1.json')
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256'] == frozen['inputs_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', analysis/'fixture_attempt1', 14112, 384, 36),
        ('benchmark_v1', HERE/'runs/benchmark_v1', 7056, 192, 37),
        ('maturing_v1', HERE/'runs/maturing_v1', 903168, 24576, 316)):
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
        assert len(manifest['inputs_sha256']) == 23
        assert manifest['inputs_sha256'] == receipt['inputs_sha256']
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
        s = load(run/'summary.json')
        if label != 'maturing_v1':
            assert s['status'] == 'TECHNICAL_ONLY'
            assert s['primary']['lower_bound_above_010'] is None
            assert s['noninferiority']['lower_bound_above_minus_005'] is None
            assert s['qualification_requirements_pass'] is s['full_maturing_renewal_qualified'] is None
        if label == 'fixture': continue
        job = HERE/'jobs'/label
        check_inputs(job)
        status = load(job/'status.json')
        assert status['status'] == 'COMPLETE'
        assert status['scientific_complete_sha256'] == evidence[label]['complete_sha256']
        assert status['audit_sha256'] == evidence[label]['audit_sha256']
        assert status['figure_provenance_sha256'] == evidence[label]['figure_provenance_sha256']
        evidence[label].update(completed_utc=status['utc'], workflow_seconds=status['seconds'])
    forecast_path, prelaunch_path = analysis/'forecast_v1.json', analysis/'prelaunch_verification_v1.json'
    forecast, prelaunch = load(forecast_path), load(prelaunch_path)
    launch_path = analysis/'launch_verification_v1.json'
    launch = load(launch_path)
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(forecast_path)
    assert launch['preflight_sha256'] == sha(prelaunch_path)
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(analysis/'launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(analysis/'verify_prelaunch.py')
    assert forecast['fixture_receipt_sha256'] == prelaunch['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert prelaunch['freeze_sha256'] == sha(analysis/'freeze_v1.json')
    for old, new in (('fixture', 'fixture'), ('benchmark', 'benchmark_v1')):
        for key, value in prelaunch['evidence'][old].items(): assert evidence[new][key] == value, (old, key)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark_v1']['audit_sha256']
    bench_forecast_path = analysis/'benchmark_forecast_v1.json'
    bench_forecast = load(bench_forecast_path)
    assert prelaunch['benchmark_forecast_sha256'] == sha(bench_forecast_path)
    assert bench_forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert bench_forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert not bench_forecast['detached_required'] and bench_forecast['excluded_throughput_only']
    prior_benchmark = ROOT/'E027_selective_renewal/runs/benchmark_v1'
    verify(prior_benchmark)
    assert bench_forecast['source_complete_sha256'] == sha(prior_benchmark/'COMPLETE.json')
    assert bench_forecast['source_audit_sha256'] == sha(prior_benchmark/'INDEPENDENT_AUDIT.json')
    assert prelaunch['benchmark_completed_utc'] == evidence['benchmark_v1']['completed_utc']
    assert prelaunch['benchmark_workflow_seconds'] == evidence['benchmark_v1']['workflow_seconds']
    prior_closeout = ROOT/'E028_precursor_rewriting/analysis/closeout_v1.json'
    assert frozen['predecessor_closeout_sha256'] == sha(prior_closeout)
    old = load(prior_closeout)
    assert old['status'] == 'PASS' and old['verification_code_sha256'] == sha(prior_closeout.parent/'verify_closeout.py')
    diagnoses = old['predecessor_diagnosis_inputs_unchanged']
    assert prelaunch['predecessor_inputs_unchanged'] == frozen['predecessor_frozen_inputs_unchanged']
    for rel in prelaunch['predecessor_inputs_unchanged']+diagnoses: check_inputs(ROOT/rel)
    run = HERE/'runs/maturing_v1'
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    blocks = list(range(25000, 25032))
    assert manifest['contract']['blocks'] == summary['blocks'] == blocks
    assert prelaunch['unused_scientific_blocks'] == frozen['unused_blocks'] == blocks
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == forecast['cpu_affinity']
    assert manifest['contract']['workers'] == forecast['workers'] == 8
    assert manifest['contract']['cycle'] == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=3)
    assert manifest['contract']['config']['recipients'] == 4
    assert len(manifest['contract']['panels']) == 42 and len(manifest['contract']['conditions']) == 10
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['evidence_status'] == manifest['contract']['mode'] == 'prospective_maturing_renewal'
    assert summary['strength_threshold'] == .5 and not summary['transmitted_ancestry_metadata']
    primary, ni = summary['primary'], summary['noninferiority']
    paired = summary['packet_contrasts']['3']['local_strength']
    assert primary['statistics'] == paired['maturing_minus_selective']['both_cues']['scattered']
    assert ni['statistics'] == paired['maturing_minus_strength_compensated']['both_cues']['scattered']
    assert primary['margin'] == .10 and ni['margin'] == -.05
    assert primary['lower_bound_above_010'] == (primary['statistics']['ci95'][0] > .10)
    assert ni['lower_bound_above_minus_005'] == (ni['statistics']['ci95'][0] > -.05)
    assert len(summary['qualification_gates']) == 14 and len(summary['boundary_gates']) == 12
    assert summary['qualification_requirements_pass'] == all(summary['qualification_gates'].values())
    qualified = primary['lower_bound_above_010'] and ni['lower_bound_above_minus_005'] and summary['qualification_requirements_pass']
    assert summary['full_maturing_renewal_qualified'] == qualified
    assert summary['status'] == ('MATURING_RENEWAL_QUALIFIED' if qualified else 'MATURING_RENEWAL_NOT_ESTABLISHED')
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
        if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], evidence_status=summary['evidence_status'],
        primary=primary, noninferiority=ni, qualification_gates=summary['qualification_gates'], runs=evidence,
        forecast_seconds=forecast['forecast_seconds'], actual_workflow_seconds=evidence['maturing_v1']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['maturing_v1']['workflow_seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        fixture_receipt_and_evidence_verified=True, workflow_and_figure_references_verified=True,
        launch_receipts_and_operational_launcher_verified=True, benchmark_runtime_references_verified=True,
        scientific_figure_visually_inspected=True, freeze_and_unused_id_receipts_verified=True,
        predecessor_frozen_inputs_unchanged=prelaunch['predecessor_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=diagnoses, active_experiment_jobs=active,
        new_trajectories_run_during_closeout=False, subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'verified_utc', 'scientific_status', 'runs',
        'actual_workflow_seconds', 'actual_minus_forecast_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
