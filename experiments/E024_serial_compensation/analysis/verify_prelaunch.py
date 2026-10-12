"""Verify the completed technical evidence and measured forecast before the cohort."""
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
from E024_serial_compensation.workflow import fixtures
from E024_serial_compensation.run import BLOCKS


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    destination = HERE/'analysis/prelaunch_verification_v1.json'
    assert not destination.exists()
    fixtures()
    receipt_path = HERE/'analysis/fixtures_v1.json'
    receipt = load(receipt_path)
    assert sha(ROOT/receipt['source_log']) == receipt['log_sha256']
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 11424, 288, 33),
        ('benchmark', HERE/'runs/benchmark_v1', 5712, 144, 34)):
        check_inputs(run)
        manifest = load(run/'manifest.json')
        assert len(manifest['inputs_sha256']) == 20
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items():
            assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        assert audit['teaching_sign_symmetry_max_error'] < 1e-10
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        for name, count in (('observations.csv', terminal), ('body_observations.csv', body)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count
        summary = load(run/'summary.json')
        assert summary['status'] == 'TECHNICAL_ONLY'
        assert summary['primary']['lower_bound_above_075'] is None
        assert summary['full_compensation_qualified'] is None
        assert manifest['contract']['cycle']['generations'] == 3 and len(summary['panels']) == 34
        evidence[label] = dict(original_outputs_verified=nfiles, input_count=20,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            terminal_observations=terminal, body_observations=body,
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'])
    check_inputs(HERE/'jobs/benchmark_v1')
    status = load(HERE/'jobs/benchmark_v1/status.json')
    figure = HERE/'figures/benchmark_v1'
    prov = load(figure/'provenance.json')
    assert status['status'] == 'COMPLETE'
    assert status['scientific_complete_sha256'] == prov['complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert status['audit_sha256'] == prov['audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert status['figure_provenance_sha256'] == sha(figure/'provenance.json')
    assert prov['summary_sha256'] == sha(HERE/'runs/benchmark_v1/summary.json')
    assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
    forecast_path = HERE/'analysis/forecast_v1.json'
    forecast = load(forecast_path)
    assert forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark']['audit_sha256']
    for rel, digest in forecast['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    prebenchmark_path = HERE/'analysis/prebenchmark_verification_v1.json'
    prebenchmark = load(prebenchmark_path)
    launch = load(HERE/'analysis/benchmark_launch_verification_v1.json')
    assert prebenchmark['status'] == launch['status'] == 'PASS'
    assert prebenchmark['fixture_receipt_sha256'] == sha(receipt_path)
    assert prebenchmark['fixture_complete_sha256'] == evidence['fixture']['complete_sha256']
    assert prebenchmark['fixture_audit_sha256'] == evidence['fixture']['audit_sha256']
    assert launch['preflight_sha256'] == sha(prebenchmark_path)
    assert launch['forecast_sha256'] == prebenchmark['forecast_sha256'] == sha(HERE/'analysis/benchmark_forecast_v1.json')
    assert launch['operational_launcher_sha256'] == prebenchmark['operational_launcher_sha256'] == sha(HERE/'analysis/launch_verified.py')
    assert prebenchmark['verification_code_sha256'] == sha(HERE/'analysis/verify_prebenchmark.py')
    predecessors = prebenchmark['predecessor_inputs_unchanged']
    for rel in predecessors: check_inputs(ROOT/rel)
    check_inputs(ROOT/'E022_reader_compensation/analysis/transmission_diagnosis_v1')
    for path in ROOT.glob('E*/runs/*/manifest.json'):
        assert not set(BLOCKS).intersection(load(path).get('contract', {}).get('blocks', [])), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('jobs/serial_v1', 'runs/serial_v1'): assert not (HERE/rel).exists()
    result = dict(status='PASS', utc=utc(), evidence=evidence,
        benchmark_completed_utc=status['utc'], benchmark_workflow_seconds=status['seconds'],
        benchmark_minus_forecast_seconds=status['seconds']-load(HERE/'analysis/benchmark_forecast_v1.json')['forecast_seconds'],
        benchmark_figure_visually_inspected=True, csv_row_counts_verified=True,
        benchmark_operational_receipts_verified=True,
        figure_provenance_sha256=sha(figure/'provenance.json'), forecast_sha256=sha(forecast_path),
        forecast_seconds=forecast['forecast_seconds'], workers=forecast['workers'], numerical_threads=1,
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        cohort_ids_previously_unused=list(BLOCKS), predecessor_inputs_unchanged=predecessors,
        predecessor_diagnosis_inputs_unchanged=True, prior_active_jobs=active,
        scientific_outcomes_inspected=False,
        launch_command='bash run_python.sh E024_serial_compensation/analysis/launch_verified.py',
        operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'), verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
