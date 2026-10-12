"""Verify completed evidence without rerunning or changing scientific outputs."""
import argparse
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E027_selective_renewal.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    destination = HERE/'analysis/closeout_v1.json'
    assert not destination.exists()
    fixtures()
    receipt = load(HERE/'analysis/fixtures_v1.json')
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 11424, 288, 35),
        ('benchmark_v1', HERE/'runs/benchmark_v1', 5712, 144, 36),
        ('selective_v1', HERE/'runs/selective_v1', 731136, 18432, 315)):
        check_inputs(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        assert audit['teaching_sign_symmetry_max_error'] < 1e-10
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        for name, count in (('observations.csv', terminal), ('body_observations.csv', body)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count
        manifest = load(run/'manifest.json')
        assert len(manifest['inputs_sha256']) == 22
        assert manifest['inputs_sha256'] == receipt['inputs_sha256']
        figure = HERE/'figures'/('fixture_attempt1' if label == 'fixture' else label)
        prov = load(figure/'provenance.json')
        assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
        assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
        evidence[label] = dict(original_outputs_verified=nfiles,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            manifest_sha256=sha(run/'manifest.json'),
            individual_observations=terminal, body_individual_observations=body,
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'],
            figure_provenance_sha256=sha(figure/'provenance.json'))
        if label != 'selective_v1':
            summary = load(run/'summary.json')
            assert summary['status'] == 'TECHNICAL_ONLY'
            assert summary['primary']['lower_bound_above_zero'] is None
            assert summary['qualification_requirements_pass'] is summary['full_selective_renewal_qualified'] is None
        if label == 'fixture':
            continue
        job = HERE/'jobs'/label
        check_inputs(job)
        status = load(job/'status.json')
        assert status['status'] == 'COMPLETE'
        assert status['scientific_complete_sha256'] == evidence[label]['complete_sha256']
        assert status['audit_sha256'] == evidence[label]['audit_sha256']
        assert status['figure_provenance_sha256'] == evidence[label]['figure_provenance_sha256']
        evidence[label].update(completed_utc=status['utc'], workflow_seconds=status['seconds'])
    forecast_path = HERE/'analysis/forecast_v1.json'
    forecast = load(forecast_path)
    prelaunch_path = HERE/'analysis/prelaunch_verification_v1.json'
    prelaunch = load(prelaunch_path)
    launch = load(HERE/'analysis/launch_verification_v1.json')
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(forecast_path)
    assert launch['preflight_sha256'] == sha(prelaunch_path)
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(HERE/'analysis/launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(HERE/'analysis/verify_prelaunch.py')
    assert forecast['fixture_receipt_sha256'] == prelaunch['fixture_receipt_sha256'] == sha(HERE/'analysis/fixtures_v1.json')
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    for old, new in (('fixture', 'fixture'), ('benchmark', 'benchmark_v1')):
        for key, value in prelaunch['evidence'][old].items():
            assert evidence[new][key] == value, (old, key)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark_v1']['audit_sha256']
    bench_preflight_path = HERE/'analysis/prebenchmark_verification_v1.json'
    bench_launch_path = HERE/'analysis/benchmark_launch_verification_v1.json'
    bench_forecast_path = HERE/'analysis/benchmark_forecast_v1.json'
    bench_preflight, bench_launch, bench_forecast = [load(path) for path in (bench_preflight_path, bench_launch_path, bench_forecast_path)]
    assert prelaunch['benchmark_preflight_sha256'] == sha(bench_preflight_path)
    assert prelaunch['benchmark_launch_receipt_sha256'] == sha(bench_launch_path)
    assert prelaunch['benchmark_forecast_sha256'] == sha(bench_forecast_path)
    assert bench_preflight['status'] == bench_launch['status'] == 'PASS'
    assert bench_launch['preflight_sha256'] == sha(bench_preflight_path)
    assert bench_launch['forecast_sha256'] == bench_preflight['forecast_sha256'] == sha(bench_forecast_path)
    assert bench_preflight['verification_code_sha256'] == sha(HERE/'analysis/prepare_benchmark.py')
    assert bench_launch['operational_launcher_sha256'] == bench_preflight['operational_launcher_sha256'] == sha(HERE/'analysis/launch_benchmark.py')
    assert bench_forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert bench_forecast['fixture_receipt_sha256'] == sha(HERE/'analysis/fixtures_v1.json')
    assert prelaunch['benchmark_completed_utc'] == evidence['benchmark_v1']['completed_utc']
    assert prelaunch['benchmark_workflow_seconds'] == evidence['benchmark_v1']['workflow_seconds']
    prior_closeout = ROOT/'E026_restoration_intervention/analysis/closeout_v1.json'
    assert prelaunch['predecessor_closeout_sha256'] == bench_preflight['predecessor_closeout_sha256'] == sha(prior_closeout)
    old = load(prior_closeout)
    assert old['status'] == 'PASS' and old['verification_code_sha256'] == sha(prior_closeout.parent/'verify_closeout.py')
    for rel in prelaunch['predecessor_inputs_unchanged']+prelaunch['predecessor_diagnoses_unchanged']:
        check_inputs(ROOT/rel)
    run = HERE/'runs/selective_v1'
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    blocks = list(range(24000, 24032))
    assert manifest['contract']['blocks'] == summary['blocks'] == prelaunch['scientific_ids_previously_unused'] == blocks
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == forecast['cpu_affinity']
    assert manifest['contract']['workers'] == forecast['workers'] == 8
    assert manifest['contract']['cycle']['generations'] == 3
    assert len(manifest['contract']['receivers']) == 2 and len(manifest['contract']['panels']) == 34
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['primary']['lower_bound_above_zero'] == (summary['primary']['statistics']['ci95'][0] > 0.)
    assert len(summary['qualification_gates']) == 13 and len(summary['boundary_gates']) == 12
    assert summary['qualification_requirements_pass'] == all(summary['qualification_gates'].values())
    assert summary['full_selective_renewal_qualified'] == (summary['primary']['lower_bound_above_zero'] and summary['qualification_requirements_pass'])
    expected = 'SELECTIVE_RENEWAL_QUALIFIED' if summary['full_selective_renewal_qualified'] else 'SELECTIVE_RENEWAL_NOT_ESTABLISHED'
    assert summary['status'] == expected
    assert summary['evidence_status'] == manifest['contract']['mode'] == 'prospective_selective_renewal'
    assert manifest['contract']['config']['recipients'] == 4
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], evidence_status=summary['evidence_status'], primary=summary['primary'],
        qualification_requirements_pass=summary['qualification_requirements_pass'],
        full_selective_renewal_qualified=summary['full_selective_renewal_qualified'],
        qualification_gates=summary['qualification_gates'], boundary_gates_passed=sum(summary['boundary_gates'].values()),
        original_gates_passed={h: {reader: {condition: sum(group['gates'].values())
            for condition, group in conditions.items()} for reader, conditions in summary['groups'][h].items()}
            for h in ('1', '3')}, runs=evidence, forecast_seconds=forecast['forecast_seconds'],
        actual_workflow_seconds=evidence['selective_v1']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['selective_v1']['workflow_seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        fixture_receipt_and_evidence_verified=True, workflow_and_figure_references_verified=True,
        launch_receipts_and_operational_launcher_verified=True, benchmark_runtime_references_verified=True,
        scientific_figure_visually_inspected=True,
        predecessor_frozen_inputs_unchanged=prelaunch['predecessor_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=prelaunch['predecessor_diagnoses_unchanged'], active_experiment_jobs=active,
        new_trajectories_run_during_closeout=False,
        subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps({k:result[k] for k in ('status', 'scientific_status', 'qualification_requirements_pass',
        'full_selective_renewal_qualified', 'runs', 'actual_workflow_seconds', 'actual_minus_forecast_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
