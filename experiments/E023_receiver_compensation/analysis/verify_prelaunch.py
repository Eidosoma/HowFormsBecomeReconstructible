"""Verify completed technical evidence before launching any scientific block."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E023_receiver_compensation.workflow import fixtures
from E023_receiver_compensation.run import BLOCKS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    destination = HERE/'analysis/prelaunch_verification_v1.json'
    assert not destination.exists()
    load = lambda p: json.loads(p.read_text())
    fixtures()
    receipt = load(HERE/'analysis/fixtures_v1.json')
    assert sha(ROOT/receipt['source_log']) == receipt['log_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 6048, 96, 28),
        ('benchmark', HERE/'runs/benchmark_v1', 3024, 48, 29)):
        check_inputs(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists() and len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        assert audit['teaching_sign_symmetry_max_error'] < 1e-10
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        evidence[label] = dict(original_outputs_verified=nfiles, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), terminal_observations=terminal, body_observations=body)
    check_inputs(HERE/'jobs/benchmark_v1')
    status = load(HERE/'jobs/benchmark_v1/status.json')
    figure = HERE/'figures/benchmark_v1'; prov = load(figure/'provenance.json')
    assert status['status'] == 'COMPLETE'
    assert status['scientific_complete_sha256'] == prov['complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert status['audit_sha256'] == prov['audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert status['figure_provenance_sha256'] == sha(figure/'provenance.json')
    assert prov['summary_sha256'] == sha(HERE/'runs/benchmark_v1/summary.json')
    assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
    forecast_path = HERE/'analysis/forecast_v1.json'; forecast = load(forecast_path)
    assert forecast['fixture_receipt_sha256'] == sha(HERE/'analysis/fixtures_v1.json')
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark']['audit_sha256']
    for rel, digest in forecast['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    predecessors = load(ROOT/'E022_reader_compensation/analysis/closeout_v1.json')['predecessor_frozen_inputs_unchanged']
    predecessors += ['E022_reader_compensation/runs/compensation_v1']
    for rel in predecessors: check_inputs(ROOT/rel)
    check_inputs(ROOT/'E022_reader_compensation/analysis/transmission_diagnosis_v1')
    for path in ROOT.glob('E*/runs/*/manifest.json'):
        assert not set(BLOCKS).intersection(load(path).get('contract', {}).get('blocks', [])), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('jobs/receiver_v1', 'runs/receiver_v1'): assert not (HERE/rel).exists()
    result = dict(status='PASS', utc=utc(), evidence=evidence, benchmark_figure_visually_inspected=True,
        figure_provenance_sha256=sha(figure/'provenance.json'), forecast_sha256=sha(forecast_path),
        forecast_seconds=forecast['forecast_seconds'], workers=forecast['workers'], numerical_threads=1,
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        cohort_ids_previously_unused=list(BLOCKS), predecessor_inputs_unchanged=predecessors,
        predecessor_diagnosis_inputs_unchanged=True, prior_active_jobs=active,
        launch_command='bash run_python.sh E023_receiver_compensation/analysis/launch_verified.py',
        operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'), verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
