"""Check the short fixture and audited predecessor runtime before fresh confirmation."""
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
from E025_rewriting_confirmation.workflow import fixtures
from E025_rewriting_confirmation.run import BLOCKS


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
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256']
    run = HERE/'analysis/fixture_attempt1'
    check_inputs(run)
    manifest = load(run/'manifest.json')
    assert len(manifest['inputs_sha256']) == 22
    assert manifest['inputs_sha256'] == receipt['inputs_sha256']
    assert manifest['contract']['mode'] == 'technical_fixture'
    complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert not (run/'FAILED.json').exists()
    assert len(complete['outputs_sha256']) == 35
    for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, rel
    assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
    assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
    assert audit['individual_observations'] == 11424 and audit['body_individual_observations'] == 288
    assert audit['teaching_sign_symmetry_max_error'] < 1e-10
    for key, value in audit.items():
        if isinstance(value, bool): assert value, key
    for name, count in (('observations.csv', 11424), ('body_observations.csv', 288)):
        with (run/name).open(newline='') as handle:
            assert sum(1 for _ in csv.DictReader(handle)) == count
    summary = load(run/'summary.json')
    assert summary['status'] == 'TECHNICAL_ONLY'
    assert summary['primary']['lower_bound_above_010'] is None
    assert summary['full_confirmation_qualified'] is summary['serial_reliability_qualified'] is None
    assert len(summary['qualification_gates']) == 11 and len(summary['boundary_gates']) == 12
    assert manifest['contract']['cycle']['generations'] == 3 and len(summary['panels']) == 34
    figure = HERE/'figures/fixture_attempt1'
    prov = load(figure/'provenance.json')
    assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
    assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
    assert prov['summary_sha256'] == sha(run/'summary.json')
    assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
    forecast_path = HERE/'analysis/forecast_v1.json'
    forecast = load(forecast_path)
    assert forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert forecast['numerical_contract_and_environment_match']
    assert not forecast['independent_new_long_benchmark_required']
    for rel, digest in forecast['inputs_sha256'].items(): assert sha(ROOT/rel) == digest
    prior = ROOT/'E024_serial_compensation'
    closeout_path = prior/'analysis/closeout_v1.json'
    assert forecast['predecessor_closeout_sha256'] == sha(closeout_path)
    closeout = load(closeout_path)
    assert closeout['status'] == 'PASS'
    assert closeout['verification_code_sha256'] == sha(prior/'analysis/verify_closeout.py')
    for label, evidence in forecast['predecessor'].items():
        old_run, job = prior/'runs'/label, prior/'jobs'/label
        check_inputs(old_run); check_inputs(job)
        for field, path in (
            ('status_sha256', job/'status.json'), ('complete_sha256', old_run/'COMPLETE.json'),
            ('audit_sha256', old_run/'INDEPENDENT_AUDIT.json'), ('manifest_sha256', old_run/'manifest.json')):
            assert evidence[field] == sha(path)
    assert forecast['benchmark_worker_sha256'] == sha(prior/'runs/benchmark_v1/worker_900024.json')
    predecessors = closeout['predecessor_frozen_inputs_unchanged']+['E024_serial_compensation/runs/serial_v1']
    for rel in predecessors: check_inputs(ROOT/rel)
    check_inputs(ROOT/'E022_reader_compensation/analysis/transmission_diagnosis_v1')
    for path in ROOT.glob('E*/runs/*/manifest.json'):
        assert not set(BLOCKS).intersection(load(path).get('contract', {}).get('blocks', [])), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('jobs/confirmation_v1', 'runs/confirmation_v1'): assert not (HERE/rel).exists()
    available = shutil.disk_usage(HERE).free
    assert available > forecast['storage_with_reserve_bytes']
    result = dict(status='PASS', utc=utc(), tests=7, fixture_original_outputs_verified=35,
        frozen_scientific_inputs=22, fixture_receipt_sha256=sha(receipt_path),
        fixture_complete_sha256=sha(run/'COMPLETE.json'), fixture_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        fixture_simulation_seconds=complete['seconds'], fixture_audit_seconds=audit['seconds'],
        terminal_observations=11424, body_observations=288, csv_row_counts_verified=True,
        fixture_figure_visually_inspected=True, figure_provenance_sha256=sha(figure/'provenance.json'),
        forecast_sha256=sha(forecast_path), forecast_seconds=forecast['forecast_seconds'],
        runtime_basis=forecast['runtime_basis'], predecessor_runtime_evidence=forecast['predecessor'],
        workers=forecast['workers'], numerical_threads=1, cpu_affinity=forecast['cpu_affinity'],
        storage_with_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=available,
        cohort_ids_previously_unused=list(BLOCKS), predecessor_inputs_unchanged=predecessors,
        predecessor_diagnosis_inputs_unchanged=True, prior_active_jobs=active,
        scientific_outcomes_inspected=False,
        launch_command='bash run_python.sh E025_rewriting_confirmation/analysis/launch_verified.py',
        operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'),
        verification_code_sha256=sha(Path(__file__)))
    with destination.open('x') as handle: json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
