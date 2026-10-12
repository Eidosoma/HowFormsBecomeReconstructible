"""Verify completed artifacts and provenance without running new trajectories."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, dump, sha, utc
from E015_functional_inheritance.audit import verify


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    analysis = HERE/'analysis'
    destination = analysis/'closeout_v1.json'
    assert not destination.exists()
    technical = load(analysis/'technical_v1.json')
    assert technical['status'] == 'PASS' and technical['tests'] == 8
    assert technical['runner_sha256'] == sha(analysis/'run_technical.py')
    for stage, record in technical['stages'].items():
        assert record['returncode'] == 0 and record['log_sha256'] == sha(analysis/f'{stage}_v1.log')
    check_inputs(analysis/'freeze_v1')
    runs = {}
    for name, outputs, terminal, body in (('fixture_v1', 33, 4032, 32),
                                         ('benchmark_v1', 33, 2016, 16),
                                         ('capture_v1', 188, 258048, 2048)):
        run = HERE/'runs'/name
        manifest = verify(run)
        complete, audit, summary = [load(run/p) for p in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json')]
        assert len(complete['outputs_sha256']) == outputs
        assert manifest['inputs_sha256'] == technical['inputs_sha256'] and len(manifest['inputs_sha256']) == 25
        assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == summary['individual_observations'] == terminal
        assert audit['source_body_observations_replayed'] == summary['source_body_observations_replayed'] == body
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, key
        if name != 'capture_v1':
            assert summary['status'] == 'TECHNICAL_ONLY' and summary['primary']['lower_above_005'] is None
            assert summary['absolute_reliability_lower_above_075'] is None
        figure = HERE/'figures'/name
        provenance = load(figure/'provenance.json')
        for key, file in (('complete_sha256', 'COMPLETE.json'), ('audit_sha256', 'INDEPENDENT_AUDIT.json'), ('summary_sha256', 'summary.json')):
            assert provenance[key] == sha(run/file)
        assert provenance['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in provenance['outputs_sha256'].items():
            assert sha(figure/rel) == digest
        runs[name] = dict(original_outputs_verified=outputs, terminal_observations=terminal,
            source_body_observations_replayed=body, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), summary_sha256=sha(run/'summary.json'),
            figure_provenance_sha256=sha(figure/'provenance.json'), simulation_seconds=complete['seconds'],
            audit_seconds=audit['seconds'], retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
    assert technical['fixture_complete_sha256'] == runs['fixture_v1']['complete_sha256']
    assert technical['fixture_audit_sha256'] == runs['fixture_v1']['audit_sha256']
    for name in ('benchmark_v1', 'capture_v1'):
        job = HERE/'jobs'/name
        check_inputs(job)
        status = load(job/'status.json')
        assert status['status'] == 'COMPLETE' and not status['automatic_successor_started']
        for key in ('complete_sha256', 'audit_sha256', 'figure_provenance_sha256'):
            assert status[key] == runs[name][key]
        runs[name].update(workflow_seconds=status['seconds'], finished_utc=status['utc'])
    preflight = load(analysis/'prelaunch_scientific_v1.json')
    launch = load(analysis/'scientific_launch_verification_v1.json')
    forecast = load(analysis/'forecast_v1.json')
    assert launch['status'] == preflight['status'] == 'PASS'
    assert launch['preflight_sha256'] == sha(analysis/'prelaunch_scientific_v1.json')
    assert launch['launcher_sha256'] == preflight['launcher_sha256'] == sha(analysis/'launch_scientific.py')
    start = load(HERE/'jobs/capture_v1/launch.json')
    assert launch['pid'] == start['pid'] and launch['launch_utc'] == start['utc']
    assert preflight['forecast_sha256'] == sha(analysis/'forecast_v1.json')
    assert preflight['technical_receipt_sha256'] == forecast['technical_receipt_sha256'] == sha(analysis/'technical_v1.json')
    assert forecast['inputs_sha256'] == preflight['inputs_sha256'] == technical['inputs_sha256']
    assert forecast['benchmark_complete_sha256'] == runs['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == runs['benchmark_v1']['audit_sha256']
    assert forecast['benchmark_run_bytes'] == runs['benchmark_v1']['retained_bytes']
    source = load(HERE/'SOURCE_DATA.json')
    for rel, digest in {**preflight['inputs_sha256'], **preflight['evidence_sha256'], **source['sha256']}.items():
        assert sha(ROOT/rel) == digest, rel
    verify(ROOT/source['source_run'])
    run = HERE/'runs/capture_v1'
    contract = load(run/'manifest.json')['contract']
    summary = load(run/'summary.json')
    assert contract['blocks'] == summary['blocks'] == list(range(27000, 27032))
    assert summary['lineages'] == 512 and contract['generation'] == summary['generation'] == 9
    assert len(list(run.glob('construction_*.npz'))) == 32 and len(list(run.glob('assay_*.npz'))) == 32
    assert len(list(run.glob('cases_*.npz'))) == 32 and len(list(run.glob('worker_*.json'))) == 32
    assert summary['primary']['statistics'] == summary['contrasts']['local_strength']['contrast_rewrite_minus_standard_preserve']['both_cues']['scattered']
    assert summary['primary']['margin'] == .05
    passed = summary['primary']['statistics']['ci95'][0] > .05
    assert summary['primary']['lower_above_005'] == passed
    assert summary['status'] == ('CUE_SELECTIVE_CAPTURE_BENEFIT_ESTABLISHED' if passed else 'CUE_SELECTIVE_CAPTURE_BENEFIT_NOT_ESTABLISHED')
    absolute = summary['groups']['local_strength']['contrast_rewrite']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert summary['absolute_reliability_lower_above_075'] == absolute
    assert summary['prior_cases_reused'] and not summary['source_bodies_changed'] and not summary['new_serial_history']
    assert summary['baseline_endpoints_match_e034'] and summary['all_source_boundary_commitments_match']
    assert summary['matched_magnitudes_support_and_denominators_verified']
    for policy in ('preserve', 'rewrite'):
        comparison = summary['contrasts']['local_strength'][f'matched_{policy}_minus_standard_{policy}']['both_cues']['scattered']
        assert summary['matched_sign_control_lower_above_zero'][policy] == (comparison['ci95'][0] > 0)
    assert len(contract['panels']) == 12 and contract['factor'] == 4
    verify(ROOT/contract['parent_source'])
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', utc=utc(), verification_code_sha256=sha(__file__),
        scientific_status=summary['status'], primary=summary['primary'], absolute_reliability_passed=absolute,
        runs=runs, frozen_inputs_verified=25, scientific_figure_visually_inspected=True,
        all_original_outputs_and_source_provenance_verified=True, operational_receipts_verified=True,
        new_trajectories_run=False, forecast_seconds=forecast['forecast_seconds'],
        actual_minus_forecast_seconds=runs['capture_v1']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'],
        available_bytes=shutil.disk_usage(HERE).free, active_jobs=active, subsequent_experiment_started=False)
    dump(destination, result)
    print(json.dumps({k:result[k] for k in ('status', 'utc', 'scientific_status', 'runs', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2))


if __name__ == '__main__':
    main()
