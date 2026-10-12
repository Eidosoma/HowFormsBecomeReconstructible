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
    assert technical['status'] == 'PASS' and technical['tests'] == 12
    assert technical['runner_sha256'] == sha(analysis/'run_technical.py')
    for stage, record in technical['stages'].items():
        assert record['returncode'] == 0 and record['log_sha256'] == sha(analysis/f'{stage}_v1.log')
    check_inputs(analysis/'freeze_v1')
    runs = {}
    for name, outputs, terminal, body in (('fixture_v1', 76, 36960, 3584),
                                         ('benchmark_v1', 76, 18480, 1792),
                                         ('serial_v1', 1409, 2365440, 229376)):
        run = HERE/'runs'/name
        manifest = verify(run)
        complete, audit, summary = [load(run/p) for p in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json')]
        assert len(complete['outputs_sha256']) == outputs
        assert manifest['inputs_sha256'] == technical['inputs_sha256'] and len(manifest['inputs_sha256']) == 30
        assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == summary['individual_observations'] == terminal
        assert audit['body_individual_observations'] == summary['body_individual_observations'] == body
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, key
        if name != 'serial_v1':
            assert summary['status'] == 'TECHNICAL_ONLY' and summary['primary']['lower_above_005'] is None
            assert summary['primary_status'] == 'TECHNICAL_ONLY' and summary['full_qualification'] is None
            assert summary['full_durability_qualified'] is None and summary['durability_status'] == 'TECHNICAL_ONLY'
        figure = HERE/'figures'/name
        provenance = load(figure/'provenance.json')
        for key, file in (('complete_sha256', 'COMPLETE.json'), ('audit_sha256', 'INDEPENDENT_AUDIT.json'), ('summary_sha256', 'summary.json')):
            assert provenance[key] == sha(run/file)
        assert provenance['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in provenance['outputs_sha256'].items():
            assert sha(figure/rel) == digest
        runs[name] = dict(original_outputs_verified=outputs, terminal_observations=terminal,
            body_individual_observations=body, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), summary_sha256=sha(run/'summary.json'),
            figure_provenance_sha256=sha(figure/'provenance.json'), simulation_seconds=complete['seconds'],
            audit_seconds=audit['seconds'], retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
    assert technical['fixture_complete_sha256'] == runs['fixture_v1']['complete_sha256']
    assert technical['fixture_audit_sha256'] == runs['fixture_v1']['audit_sha256']
    for name in ('benchmark_v1', 'serial_v1'):
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
    start = load(HERE/'jobs/serial_v1/launch.json')
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
    assert preflight['available_bytes'] > forecast['storage_with_reserve_bytes']
    assert load(ROOT/'E037_repair_support_diagnosis/analysis/closeout_v1.json')['status'] == 'PASS'
    assert load(ROOT/'E037_repair_support_diagnosis/analysis/recovery_failure_v1.json')['status'] == 'FAILED'
    assert load(ROOT/'E036_serial_cue_capture/analysis/technical_v1.json')['status'] == 'FAIL'
    run = HERE/'runs/serial_v1'
    contract = load(run/'manifest.json')['contract']
    summary = load(run/'summary.json')
    assert contract['blocks'] == summary['blocks'] == list(range(31000, 31032))
    assert summary['lineages'] == 512 and contract['generations'] == summary['cycle']['generations'] == 32
    assert len(list(run.glob('source_*.npz'))) == 32
    assert len(list(run.glob('boundary_*.npz'))) == 1024 and len(list(run.glob('assay_*.npz'))) == 224
    assert len(list(run.glob('cases_*.npz'))) == 32 and len(list(run.glob('worker_*.json'))) == 32
    assert summary['primary']['statistics'] == summary['contrasts']['32']['local_strength']['bridge_preserve_minus_standard_preserve']['both_cues']['scattered']
    rescue = summary['contrasts']['32']['local_strength']['bridge_preserve_minus_contrast_preserve']['both_cues']['scattered']
    assert summary['repair_rescue']['statistics'] == rescue
    assert summary['repair_rescue']['lower_above_010'] == (rescue['ci95'][0] > .10)
    assert summary['primary']['margin'] == .05
    passed = summary['primary']['statistics']['ci95'][0] > .05
    assert summary['primary']['lower_above_005'] == passed
    assert summary['primary_status'] == ('LONG_RENEWAL_BENEFIT_ESTABLISHED' if passed else 'LONG_RENEWAL_BENEFIT_NOT_ESTABLISHED')
    gates = {}
    for h in (8, 16, 24, 32):
        candidate = summary['groups'][str(h)]['local_strength']['bridge_preserve']
        for damage in ('intact', 'scattered'):
            gates[f'h{h}_{damage}_both_cue_lower_above_075'] = candidate['both_cues'][damage]['own']['ci95'][0] > .75
        gates[f'h{h}_original_24_gates'] = candidate['all_original_gates_pass']
    for h in (16, 32):
        for control in ('bridge_read_blocked', 'bridge_write_blocked'):
            gates[f'h{h}_above_{control}_by_010'] = summary['contrasts'][str(h)]['local_strength']['bridge_preserve_minus_'+control]['both_cues']['scattered']['ci95'][0] > .10
    gates['initial_normalized_original_24_gates'] = summary['groups']['0']['local_strength']['initial']['all_original_gates_pass']
    assert len(gates) == 17 and summary['durability_requirements'] == gates
    durable = all(gates.values())
    assert summary['full_durability_qualified'] == durable
    assert summary['full_qualification'] == (passed and durable)
    assert summary['status'] == ('LONG_RENEWAL_QUALIFIED' if passed and durable else 'LONG_RENEWAL_NOT_QUALIFIED')
    assert summary['durability_status'] == ('DURABLE_THROUGH_32_RENEWALS' if durable else 'DURABILITY_NOT_ESTABLISHED')
    assert not summary['prior_cases_pooled'] and summary['independent_serial_histories'] and summary['setting_selected'] is None
    assert len(contract['panels']) == 110 and contract['cycle'] == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=32)
    assert summary['terminal_cycle'] == dict(contract['cycle'], settling_steps=1024)
    assert summary['primary']['endpoint'] == 'h32 normalized scattered own both-cue success: bridge_preserve minus standard_preserve'
    assert summary['repair_rescue']['endpoint'] == 'h32 bridge_preserve minus contrast_preserve'
    assert summary['model_is_horizon_only_extension_of_e039'] is True
    reference = (ROOT/'E039_weak_bridge_confirmation/model.py').read_text()
    expected = reference.replace('CFG, Cycle, CYCLE = previous.CFG, previous.Cycle, previous.CYCLE\n',
        'CFG, Cycle, CYCLE = previous.CFG, previous.Cycle, previous.CYCLE\nCYCLE = replace(CYCLE, generations=32)\n')
    expected = expected.replace('HORIZONS = (0, 1, 3, 8, 16)', 'HORIZONS = (0, 1, 3, 8, 16, 24, 32)')
    expected = expected.replace('cycle.generations == 16', 'cycle.generations == 32')
    assert (HERE/'model.py').read_text() == expected
    for prior in ('E038_weak_bridge_capture', 'E039_weak_bridge_confirmation'):
        assert load(ROOT/prior/'analysis/closeout_v1.json')['status'] == 'PASS'
    assert runs['serial_v1']['retained_bytes'] <= forecast['storage_with_reserve_bytes']
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', utc=utc(), verification_code_sha256=sha(__file__),
        scientific_status=summary['status'], primary_status=summary['primary_status'], primary=summary['primary'], durability_status=summary['durability_status'], full_durability_qualified=durable, full_qualification=summary['full_qualification'], durability_requirements=gates, model_is_horizon_only_extension_of_e039=True,
        runs=runs, frozen_inputs_verified=30, scientific_figure_visually_inspected=True,
        all_original_outputs_and_source_provenance_verified=True, operational_receipts_verified=True, preserved_prior_failures_verified=True, capacity_verified=True,
        new_trajectories_run=False, forecast_seconds=forecast['forecast_seconds'],
        actual_minus_forecast_seconds=runs['serial_v1']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'],
        available_bytes=shutil.disk_usage(HERE).free, active_jobs=active, subsequent_experiment_started=False)
    dump(destination, result)
    print(json.dumps({k:result[k] for k in ('status', 'utc', 'scientific_status', 'runs', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2))


if __name__ == '__main__':
    main()
