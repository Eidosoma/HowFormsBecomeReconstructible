"""Verify technical evidence, unused cohort identifiers and capacity before launch."""
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
from E029_maturing_renewal.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figures-inspected', action='store_true', required=True)
    parser.parse_args()
    destination = HERE/'analysis/prelaunch_verification_v1.json'
    assert not destination.exists()
    fixtures()
    receipt_path = HERE/'analysis/fixtures_v1.json'
    receipt = load(receipt_path)
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    frozen = load(HERE/'analysis/freeze_v1.json')
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256'] == frozen['inputs_sha256']
    evidence = {}
    for label, run, nfiles, nrows, nbody in (
        ('fixture', HERE/'analysis/fixture_attempt1', 36, 14112, 384),
        ('benchmark', HERE/'runs/benchmark_v1', 37, 7056, 192)):
        check_inputs(run)
        manifest = load(run/'manifest.json')
        assert len(manifest['inputs_sha256']) == 23
        assert manifest['inputs_sha256'] == receipt['inputs_sha256']
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        assert audit['individual_observations'] == nrows and audit['body_individual_observations'] == nbody
        for name, count in (('observations.csv', nrows), ('body_observations.csv', nbody)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count
        summary = load(run/'summary.json')
        assert summary['status'] == 'TECHNICAL_ONLY'
        assert summary['primary']['lower_bound_above_010'] is None
        assert summary['noninferiority']['lower_bound_above_minus_005'] is None
        assert summary['qualification_requirements_pass'] is summary['full_maturing_renewal_qualified'] is None
        assert len(summary['panels']) == 42 and len(summary['qualification_gates']) == 14
        assert summary['strength_threshold'] == .5
        figure = HERE/'figures'/run.name
        prov = load(figure/'provenance.json')
        assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
        assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
        evidence[label] = dict(original_outputs_verified=nfiles, individual_observations=nrows,
            body_individual_observations=nbody, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), simulation_seconds=complete['seconds'],
            audit_seconds=audit['seconds'], figure_provenance_sha256=sha(figure/'provenance.json'))
    check_inputs(HERE/'jobs/benchmark_v1')
    status = load(HERE/'jobs/benchmark_v1/status.json')
    assert status['status'] == 'COMPLETE'
    assert status['scientific_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert status['audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert status['figure_provenance_sha256'] == evidence['benchmark']['figure_provenance_sha256']
    forecast_path = HERE/'analysis/forecast_v1.json'
    forecast = load(forecast_path)
    assert forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    benchmark_forecast_path = HERE/'analysis/benchmark_forecast_v1.json'
    bench_forecast = load(benchmark_forecast_path)
    assert not bench_forecast['detached_required'] and bench_forecast['forecast_seconds'] <= 600
    assert bench_forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert bench_forecast['inputs_sha256'] == receipt['inputs_sha256']
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    # Only real run manifests have a contract; input snapshots do not consume seeds.
    ids = set(range(25000, 25032))
    for path in ROOT.glob('E*/**/manifest.json'):
        assert not ids.intersection(load(path).get('contract', {}).get('blocks', [])), str(path)
    for rel in frozen['predecessor_frozen_inputs_unchanged']: check_inputs(ROOT/rel)
    for rel in ('E022_reader_compensation/analysis/transmission_diagnosis_v1',
        'E025_rewriting_confirmation/analysis/rebuilding_leads_v1',
        'E025_rewriting_confirmation/analysis/rebuilding_link_scale_v1'): check_inputs(ROOT/rel)
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
        if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('runs/maturing_v1', 'jobs/maturing_v1'): assert not (HERE/rel).exists()
    result = dict(status='PASS', utc=utc(), tests=8, scientific_inputs=23, evidence=evidence,
        benchmark_completed_utc=status['utc'], benchmark_workflow_seconds=status['seconds'],
        benchmark_minus_forecast_seconds=status['seconds']-bench_forecast['forecast_seconds'],
        fixture_receipt_sha256=sha(receipt_path), benchmark_forecast_sha256=sha(benchmark_forecast_path),
        fixture_and_benchmark_figures_visually_inspected=True, forecast_sha256=sha(forecast_path),
        forecast_seconds=forecast['forecast_seconds'], workers=forecast['workers'],
        cpu_affinity=forecast['cpu_affinity'], numerical_threads=1,
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        unused_scientific_blocks=sorted(ids), freeze_sha256=sha(HERE/'analysis/freeze_v1.json'),
        predecessor_inputs_unchanged=frozen['predecessor_frozen_inputs_unchanged'],
        predecessor_diagnoses_inputs_unchanged=True, prior_active_jobs=active,
        new_scientific_cohort_outcomes_inspected=False, threshold_search=False,
        operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'),
        verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps({k: result[k] for k in ('status', 'utc', 'evidence', 'benchmark_workflow_seconds',
        'forecast_seconds', 'workers', 'storage_with_reserve_bytes', 'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
