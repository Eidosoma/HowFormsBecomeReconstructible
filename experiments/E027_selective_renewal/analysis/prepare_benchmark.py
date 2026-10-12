"""Verify short evidence and freeze a measured, conservative benchmark forecast."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, sha, utc
from E027_selective_renewal.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    analysis = HERE/'analysis'
    forecast_path = analysis/'benchmark_forecast_v1.json'
    verification_path = analysis/'prebenchmark_verification_v1.json'
    assert not forecast_path.exists() and not verification_path.exists()
    fixtures()
    receipt = load(analysis/'fixtures_v1.json')
    assert receipt['invocation_sha256'] == sha(analysis/'fixture_invocation_v1.json')
    assert receipt['inputs_sha256'] == load(analysis/'fixture_invocation_v1.json')['inputs_sha256']
    fixture = analysis/'fixture_attempt1'
    prior = ROOT/'E024_serial_compensation/runs/benchmark_v1'
    evidence = {}
    for label, run, terminal, body, files in (('fixture', fixture, 11424, 288, 35), ('runtime_source', prior, 5712, 144, 34)):
        check_inputs(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == files
        for rel, digest in complete['outputs_sha256'].items():
            assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py' if label == 'fixture' else prior.parents[1]/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, (label, key)
        for name, expected in (('observations.csv', terminal), ('body_observations.csv', body)):
            with (run/name).open(newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == expected
        evidence[label] = dict(original_outputs_verified=files, individual_observations=terminal,
            body_individual_observations=body, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), manifest_sha256=sha(run/'manifest.json'))
    summary = load(fixture/'summary.json')
    assert summary['status'] == 'TECHNICAL_ONLY'
    for flag in ('qualification_requirements_pass', 'full_selective_renewal_qualified'):
        assert summary[flag] is None
    assert summary['primary']['lower_bound_above_zero'] is None
    assert load(fixture/'manifest.json')['inputs_sha256'] == receipt['inputs_sha256']
    assert len(receipt['inputs_sha256']) == 22 and len(summary['qualification_gates']) == 13
    figure = HERE/'figures/fixture_attempt1'
    provenance = load(figure/'provenance.json')
    assert provenance['complete_sha256'] == evidence['fixture']['complete_sha256']
    assert provenance['audit_sha256'] == evidence['fixture']['audit_sha256']
    assert provenance['summary_sha256'] == sha(fixture/'summary.json')
    assert provenance['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in provenance['outputs_sha256'].items():
        assert sha(figure/rel) == digest
    predecessor = ROOT/'E026_restoration_intervention/analysis/closeout_v1.json'
    closeout = load(predecessor)
    assert closeout['status'] == 'PASS'
    assert closeout['verification_code_sha256'] == sha(predecessor.parent/'verify_closeout.py')
    predecessors = closeout['predecessor_frozen_inputs_unchanged']+['E026_restoration_intervention/runs/restoration_v1']
    for rel in predecessors+closeout['predecessor_diagnosis_inputs_unchanged']:
        check_inputs(ROOT/rel)
    reserved = set(range(24000, 24032)) | {900027}
    for path in ROOT.glob('E*/**/manifest.json'):
        if path.is_relative_to(HERE) or 'inputs' in path.parts:
            continue
        blocks = load(path).get('contract', {}).get('blocks', [])
        assert not (isinstance(blocks, list) and reserved.intersection(blocks)), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for path in (HERE/'jobs/benchmark_v1', HERE/'runs/benchmark_v1'):
        assert not path.exists()
    worker, audit = load(prior/'worker_900024.json'), load(prior/'INDEPENDENT_AUDIT.json')
    seconds = 1.5*(worker['seconds']+audit['seconds'])+60
    prior_bytes = sum(p.stat().st_size for p in prior.rglob('*') if p.is_file())
    storage = math.ceil(1.5*prior_bytes)+1024**3
    available = shutil.disk_usage(HERE).free
    assert available > storage
    forecast = dict(created_utc=utc(), workers=1, cpu_affinity=cap_cpus(), numerical_threads=1,
        formula='1.5*(E024_benchmark_worker_seconds+E024_benchmark_audit_seconds)+60',
        forecast_seconds=seconds, detached_required=seconds > 600,
        source_worker_seconds=worker['seconds'], source_audit_seconds=audit['seconds'],
        source_benchmark_worker_sha256=sha(prior/'worker_900024.json'),
        source_benchmark_audit_sha256=evidence['runtime_source']['audit_sha256'],
        source_benchmark_bytes=prior_bytes, storage_with_reserve_bytes=storage, available_bytes=available,
        fixture_receipt_sha256=sha(analysis/'fixtures_v1.json'), inputs_sha256=receipt['inputs_sha256'])
    with forecast_path.open('x') as handle:
        json.dump(forecast, handle, indent=2, allow_nan=False)
    verification = dict(status='PASS', utc=utc(), tests=7, scientific_inputs=22, evidence=evidence,
        fixture_figure_visually_inspected=True, figure_provenance_sha256=sha(figure/'provenance.json'),
        forecast_sha256=sha(forecast_path), forecast_seconds=seconds, storage_with_reserve_bytes=storage,
        available_bytes=available, fixture_receipt_sha256=sha(analysis/'fixtures_v1.json'),
        fresh_scientific_blocks=list(range(24000, 24032)), benchmark_id_previously_unused=900027,
        predecessor_closeout_sha256=sha(predecessor), predecessor_inputs_unchanged=predecessors,
        predecessor_diagnoses_unchanged=closeout['predecessor_diagnosis_inputs_unchanged'], prior_active_jobs=active,
        operational_launcher_sha256=sha(analysis/'launch_benchmark.py'), verification_code_sha256=sha(Path(__file__)))
    with verification_path.open('x') as handle:
        json.dump(verification, handle, indent=2, allow_nan=False)
    print(json.dumps({key: verification[key] for key in ('status', 'utc', 'evidence', 'forecast_seconds',
        'storage_with_reserve_bytes', 'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
