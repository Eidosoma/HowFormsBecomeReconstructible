"""Verify completed technical evidence and freeze the authorized cohort forecast."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, sha, utc
from E027_selective_renewal.workflow import fixtures
import numpy as np


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    analysis = HERE/'analysis'
    destination = analysis/'prelaunch_verification_v1.json'
    forecast_path = analysis/'forecast_v1.json'
    assert not destination.exists() and not forecast_path.exists()
    fixtures()
    receipt_path = analysis/'fixtures_v1.json'
    receipt = load(receipt_path)
    assert receipt['invocation_sha256'] == sha(analysis/'fixture_invocation_v1.json')
    assert receipt['inputs_sha256'] == load(analysis/'fixture_invocation_v1.json')['inputs_sha256']
    prebenchmark_path = analysis/'prebenchmark_verification_v1.json'
    prebenchmark = load(prebenchmark_path)
    launch_path = analysis/'benchmark_launch_verification_v1.json'
    launch = load(launch_path)
    benchmark_forecast_path = analysis/'benchmark_forecast_v1.json'
    benchmark_forecast = load(benchmark_forecast_path)
    assert prebenchmark['status'] == launch['status'] == 'PASS'
    assert prebenchmark['forecast_sha256'] == launch['forecast_sha256'] == sha(benchmark_forecast_path)
    assert launch['preflight_sha256'] == sha(prebenchmark_path)
    assert prebenchmark['verification_code_sha256'] == sha(analysis/'prepare_benchmark.py')
    assert prebenchmark['operational_launcher_sha256'] == launch['operational_launcher_sha256'] == sha(analysis/'launch_benchmark.py')
    assert prebenchmark['fixture_receipt_sha256'] == benchmark_forecast['fixture_receipt_sha256'] == sha(receipt_path)
    evidence = {}
    for label, run, terminal, body, files in (
        ('fixture', analysis/'fixture_attempt1', 11424, 288, 35),
        ('benchmark', HERE/'runs/benchmark_v1', 5712, 144, 36)):
        check_inputs(run)
        manifest = load(run/'manifest.json')
        assert len(manifest['inputs_sha256']) == 22 and manifest['inputs_sha256'] == receipt['inputs_sha256']
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists() and len(complete['outputs_sha256']) == files
        for rel, digest in complete['outputs_sha256'].items():
            assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        assert audit['teaching_sign_symmetry_max_error'] < 1e-10
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, (label, key)
        for name, expected in (('observations.csv', terminal), ('body_observations.csv', body)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == expected
        summary = load(run/'summary.json')
        assert summary['status'] == 'TECHNICAL_ONLY' and summary['evidence_status'] == 'technical'
        assert summary['primary']['lower_bound_above_zero'] is None
        assert summary['qualification_requirements_pass'] is summary['full_selective_renewal_qualified'] is None
        assert len(summary['qualification_gates']) == 13 and len(summary['boundary_gates']) == 12
        assert len(summary['panels']) == 34 and summary['blocks'] == [900027]
        figure = HERE/'figures'/run.name
        prov = load(figure/'provenance.json')
        assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
        assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items():
            assert sha(figure/rel) == digest
        evidence[label] = dict(original_outputs_verified=files, individual_observations=terminal,
            body_individual_observations=body, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), manifest_sha256=sha(run/'manifest.json'),
            figure_provenance_sha256=sha(figure/'provenance.json'),
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'])
        if label == 'benchmark':
            assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == cap_cpus()
            assert manifest['python'] == sys.version and manifest['executable'] == sys.executable
            assert manifest['numpy'] == np.__version__
            assert manifest['contract']['config']['recipients'] == 1
            assert manifest['contract']['cycle']['generations'] == 3
    for key, value in prebenchmark['evidence']['fixture'].items():
        assert evidence['fixture'][key] == value
    assert prebenchmark['figure_provenance_sha256'] == evidence['fixture']['figure_provenance_sha256']
    job = HERE/'jobs/benchmark_v1'
    check_inputs(job)
    status = load(job/'status.json')
    assert status['status'] == 'COMPLETE'
    assert status['scientific_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert status['audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert status['figure_provenance_sha256'] == evidence['benchmark']['figure_provenance_sha256']
    predecessor = ROOT/'E026_restoration_intervention/analysis/closeout_v1.json'
    assert prebenchmark['predecessor_closeout_sha256'] == sha(predecessor)
    assert load(predecessor)['status'] == 'PASS'
    assert load(predecessor)['verification_code_sha256'] == sha(predecessor.parent/'verify_closeout.py')
    for rel in prebenchmark['predecessor_inputs_unchanged']+prebenchmark['predecessor_diagnoses_unchanged']:
        check_inputs(ROOT/rel)
    blocks = list(range(24000, 24032))
    assert blocks == prebenchmark['fresh_scientific_blocks']
    for path in ROOT.glob('E*/**/manifest.json'):
        if 'inputs' in path.parts:
            continue
        old = load(path).get('contract', {}).get('blocks', [])
        assert not (isinstance(old, list) and set(blocks).intersection(old)), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for path in (HERE/'runs/selective_v1', HERE/'jobs/selective_v1'):
        assert not path.exists()
    # This command only freezes the measured runtime; it launches no trajectories.
    subprocess.run([sys.executable, '-B', str(HERE/'workflow.py'), '--forecast'], cwd=ROOT,
                   stdout=subprocess.DEVNULL, check=True)
    forecast = load(forecast_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert forecast['detached_required'] and forecast['workers'] <= 12 and forecast['numerical_threads'] == 1
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    result = dict(status='PASS', utc=utc(), tests=7, scientific_inputs=22, evidence=evidence,
        benchmark_completed_utc=status['utc'], benchmark_workflow_seconds=status['seconds'],
        benchmark_minus_forecast_seconds=status['seconds']-benchmark_forecast['forecast_seconds'],
        benchmark_figure_visually_inspected=True, fixture_receipt_sha256=sha(receipt_path),
        benchmark_preflight_sha256=sha(prebenchmark_path), benchmark_launch_receipt_sha256=sha(launch_path),
        benchmark_forecast_sha256=sha(benchmark_forecast_path), forecast_sha256=sha(forecast_path),
        forecast_seconds=forecast['forecast_seconds'], workers=forecast['workers'],
        cpu_affinity=forecast['cpu_affinity'], numerical_threads=1,
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        scientific_ids_previously_unused=blocks, prior_active_jobs=active,
        predecessor_closeout_sha256=sha(predecessor),
        predecessor_inputs_unchanged=prebenchmark['predecessor_inputs_unchanged'],
        predecessor_diagnoses_unchanged=prebenchmark['predecessor_diagnoses_unchanged'],
        benchmark_environment_matches_current=True, no_design_retuning_from_technical_outcomes=True,
        operational_launcher_sha256=sha(analysis/'launch_verified.py'), verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps({key: result[key] for key in ('status', 'utc', 'evidence', 'benchmark_workflow_seconds',
        'benchmark_minus_forecast_seconds', 'forecast_seconds', 'workers', 'storage_with_reserve_bytes',
        'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
