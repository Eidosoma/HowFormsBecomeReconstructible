"""Check retained fixtures and freeze the detached benchmark estimate."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E024_serial_compensation.run import BLOCKS, BENCHMARK, input_paths
from E024_serial_compensation.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    destination = HERE/'analysis/prebenchmark_verification_v1.json'
    forecast_path = HERE/'analysis/benchmark_forecast_v1.json'
    assert not destination.exists() and not forecast_path.exists()
    fixtures()
    receipt = load(HERE/'analysis/fixtures_v1.json')
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256']
    assert sha(ROOT/receipt['source_log']) == receipt['log_sha256']
    run = HERE/'analysis/fixture_attempt1'
    check_inputs(run)
    complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert not (run/'FAILED.json').exists()
    assert len(complete['outputs_sha256']) == 33
    for rel, digest in complete['outputs_sha256'].items():
        assert sha(run/rel) == digest, rel
    assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
    assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
    assert audit['individual_observations'] == 11424 and audit['body_individual_observations'] == 288
    assert audit['teaching_sign_symmetry_max_error'] < 1e-10
    for key, value in audit.items():
        if isinstance(value, bool): assert value, key
    predecessors = load(ROOT/'E023_receiver_compensation/analysis/closeout_v1.json')['predecessor_frozen_inputs_unchanged']
    predecessors += ['E023_receiver_compensation/runs/receiver_v1']
    for rel in predecessors: check_inputs(ROOT/rel)
    check_inputs(ROOT/'E022_reader_compensation/analysis/transmission_diagnosis_v1')
    for path in ROOT.glob('E*/runs/*/manifest.json'):
        assert not (set(BLOCKS)|{BENCHMARK}).intersection(load(path).get('contract', {}).get('blocks', [])), path
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    for rel in ('jobs/benchmark_v1', 'runs/benchmark_v1', 'jobs/serial_v1', 'runs/serial_v1'):
        assert not (HERE/rel).exists()
    prior_job = ROOT/'E023_receiver_compensation/jobs/benchmark_v1'
    prior_run = ROOT/'E023_receiver_compensation/runs/benchmark_v1'
    check_inputs(prior_job); check_inputs(prior_run)
    prior = load(prior_job/'status.json')
    assert prior['status'] == 'COMPLETE'
    assert prior['scientific_complete_sha256'] == sha(prior_run/'COMPLETE.json')
    assert prior['audit_sha256'] == sha(prior_run/'INDEPENDENT_AUDIT.json')
    seconds = 1.5*(34/18)*prior['seconds']
    prior_bytes = sum(p.stat().st_size for p in prior_run.rglob('*') if p.is_file())
    reserve = 3*prior_bytes+1024**3
    available = shutil.disk_usage(HERE).free
    assert available > reserve
    forecast = dict(created_utc=utc(), purpose='excluded_full_duration_benchmark',
        blocks=[BENCHMARK], workers=1, numerical_threads=1,
        formula='1.5*(34/18)*E023_benchmark_workflow_seconds',
        prior_workflow_seconds=prior['seconds'], prior_status_sha256=sha(prior_job/'status.json'),
        forecast_seconds=seconds, detached_required=seconds > 600,
        storage_formula='3*E023_benchmark_bytes+1_GiB', prior_benchmark_bytes=prior_bytes,
        storage_with_reserve_bytes=reserve, available_bytes=available,
        fixture_receipt_sha256=sha(HERE/'analysis/fixtures_v1.json'),
        inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in input_paths()})
    with forecast_path.open('x') as handle: json.dump(forecast, handle, indent=2)
    evidence = dict(status='PASS', utc=utc(), fixture_original_outputs_verified=33,
        fixture_complete_sha256=sha(run/'COMPLETE.json'), fixture_audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        fixture_receipt_sha256=sha(HERE/'analysis/fixtures_v1.json'), input_count=20,
        terminal_observations=11424, body_observations=288,
        forecast_seconds=seconds, forecast_sha256=sha(forecast_path),
        predecessor_inputs_unchanged=predecessors, predecessor_diagnosis_inputs_unchanged=True,
        cohort_ids_previously_unused=list(BLOCKS), benchmark_id_previously_unused=BENCHMARK,
        prior_active_jobs=active, operational_launcher_sha256=sha(HERE/'analysis/launch_verified.py'),
        verification_code_sha256=sha(Path(__file__)), scientific_outcomes_inspected=False)
    with destination.open('x') as handle: json.dump(evidence, handle, indent=2)
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == '__main__':
    main()
