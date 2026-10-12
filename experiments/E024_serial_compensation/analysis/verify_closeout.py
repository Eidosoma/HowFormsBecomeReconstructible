"""Verify completed artifacts without rerunning or modifying scientific outputs."""
import argparse
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E024_serial_compensation.workflow import fixtures


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
    assert sha(ROOT/receipt['source_log']) == receipt['log_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 11424, 288, 33),
        ('benchmark_v1', HERE/'runs/benchmark_v1', 5712, 144, 34),
        ('serial_v1', HERE/'runs/serial_v1', 731136, 18432, 313)):
        check_inputs(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items():
            assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal
        assert audit['body_individual_observations'] == body
        assert audit['teaching_sign_symmetry_max_error'] < 1e-10
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, key
        for name, count in [('observations.csv', terminal), ('body_observations.csv', body)]:
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count
        evidence[label] = dict(original_outputs_verified=nfiles,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            individual_observations=terminal, body_individual_observations=body,
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'])
        if label == 'fixture':
            continue
        check_inputs(HERE/'jobs'/label)
        status = load(HERE/'jobs'/label/'status.json')
        figure = HERE/'figures'/label
        prov = load(figure/'provenance.json')
        assert status['status'] == 'COMPLETE'
        assert status['scientific_complete_sha256'] == prov['complete_sha256'] == evidence[label]['complete_sha256']
        assert status['audit_sha256'] == prov['audit_sha256'] == evidence[label]['audit_sha256']
        assert status['figure_provenance_sha256'] == sha(figure/'provenance.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items():
            assert sha(figure/rel) == digest
        evidence[label].update(completed_utc=status['utc'], workflow_seconds=status['seconds'],
            figure_provenance_sha256=sha(figure/'provenance.json'))
    forecast = load(HERE/'analysis/forecast_v1.json')
    assert forecast['fixture_receipt_sha256'] == sha(HERE/'analysis/fixtures_v1.json')
    for name in ['complete', 'audit']:
        assert forecast[f'benchmark_{name}_sha256'] == evidence['benchmark_v1'][f'{name}_sha256']
    for rel, digest in forecast['inputs_sha256'].items():
        assert sha(ROOT/rel) == digest
    prelaunch = load(HERE/'analysis/prelaunch_verification_v1.json')
    launch = load(HERE/'analysis/launch_verification_v1.json')
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(HERE/'analysis/forecast_v1.json')
    assert launch['preflight_sha256'] == sha(HERE/'analysis/prelaunch_verification_v1.json')
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(HERE/'analysis/launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(HERE/'analysis/verify_prelaunch.py')
    prebenchmark_path = HERE/'analysis/prebenchmark_verification_v1.json'
    prebenchmark = load(prebenchmark_path)
    benchmark_launch = load(HERE/'analysis/benchmark_launch_verification_v1.json')
    assert prebenchmark['status'] == benchmark_launch['status'] == 'PASS'
    assert prebenchmark['fixture_complete_sha256'] == evidence['fixture']['complete_sha256']
    assert prebenchmark['fixture_audit_sha256'] == evidence['fixture']['audit_sha256']
    assert prebenchmark['fixture_receipt_sha256'] == sha(HERE/'analysis/fixtures_v1.json')
    assert benchmark_launch['preflight_sha256'] == sha(prebenchmark_path)
    assert benchmark_launch['forecast_sha256'] == prebenchmark['forecast_sha256'] == sha(HERE/'analysis/benchmark_forecast_v1.json')
    assert benchmark_launch['operational_launcher_sha256'] == prebenchmark['operational_launcher_sha256'] == sha(HERE/'analysis/launch_verified.py')
    assert prebenchmark['verification_code_sha256'] == sha(HERE/'analysis/verify_prebenchmark.py')
    assert receipt['invocation_sha256'] == sha(HERE/'analysis/fixture_invocation_v1.json')
    for rel in prelaunch['predecessor_inputs_unchanged']:
        check_inputs(ROOT/rel)
    check_inputs(ROOT/'E022_reader_compensation/analysis/transmission_diagnosis_v1')
    run = HERE/'runs/serial_v1'
    manifest = load(run/'manifest.json')
    summary = load(run/'summary.json')
    blocks = list(range(22000, 22032))
    assert manifest['contract']['blocks'] == summary['blocks'] == prelaunch['cohort_ids_previously_unused'] == blocks
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    assert len(manifest['inputs_sha256']) == 20 and manifest['numerical_threads'] == 1
    assert manifest['contract']['cycle']['generations'] == 3
    assert manifest['contract']['workers'] == 8
    assert len(manifest['contract']['receivers']) == 2 and len(manifest['contract']['panels']) == 34
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['status'] == 'SERIAL_COMPENSATION_QUALIFIED'
    assert summary['full_compensation_qualified'] and summary['primary']['lower_bound_above_075']
    assert all(summary['qualification_gates'].values()) and all(summary['boundary_gates'].values())
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], full_compensation_qualified=summary['full_compensation_qualified'],
        primary=summary['primary'], qualification_gates=summary['qualification_gates'],
        boundary_gates_passed=sum(summary['boundary_gates'].values()),
        original_gates_passed={h: {reader: {condition: sum(group['gates'].values())
            for condition, group in conditions.items()} for reader, conditions in summary['groups'][h].items()}
            for h in ('1', '3')},
        runs=evidence, forecast_seconds=forecast['forecast_seconds'],
        actual_workflow_seconds=evidence['serial_v1']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['serial_v1']['workflow_seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        fixture_receipt_and_evidence_verified=True, workflow_and_figure_references_verified=True,
        launch_receipts_and_operational_launcher_verified=True, scientific_figure_visually_inspected=True,
        predecessor_frozen_inputs_unchanged=prelaunch['predecessor_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=True, active_experiment_jobs=active,
        subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
