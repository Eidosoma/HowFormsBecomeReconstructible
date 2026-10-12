"""Verify saved durability artifacts and provenance without new trajectories."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E015_functional_inheritance.audit import verify
from E031_renewal_durability.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    analysis = HERE/'analysis'
    destination = analysis/'closeout_v1.json'
    assert not destination.exists()
    fixtures()
    receipt = load(analysis/'fixtures_v1.json')
    suite = analysis/'fixture_suite_v1'
    verify(suite)
    assert receipt['suite_manifest_sha256'] == sha(suite/'manifest.json')
    assert receipt['runner_sha256'] == sha(analysis/'run_fixtures.py')
    for rel, digest in receipt['fixture_artifacts_sha256'].items(): assert sha(ROOT/rel) == digest
    evidence = {}
    for name, run, nfiles, terminal, body, mode in (
        ('fixture', analysis/'fixture_attempt1', 55, 27552, 2048, 'technical_fixture'),
        ('benchmark', HERE/'runs/benchmark_v1', 56, 13776, 1024, 'technical_benchmark'),
        ('scientific', HERE/'runs/durability_v1', 800, 1763328, 131072, 'prospective_renewal_durability')):
        manifest = verify(run)
        complete, audited = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert len(complete['outputs_sha256']) == nfiles
        assert len(manifest['inputs_sha256']) == 27 and manifest['inputs_sha256'] == receipt['inputs_sha256']
        assert manifest['contract']['mode'] == mode
        assert audited['status'] == 'PASS' and audited['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audited['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audited['individual_observations'] == terminal and audited['body_individual_observations'] == body
        for key, value in audited.items():
            if isinstance(value, bool): assert value, key
        for file, count in (('observations.csv.gz', terminal), ('body_observations.csv.gz', body)):
            with gzip.open(run/file, 'rt', newline='') as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == count, file
        summary = load(run/'summary.json')
        assert summary['individual_observations'] == terminal and summary['body_individual_observations'] == body
        assert summary['policy_from'] == 'E030' and not summary['prior_cases_pooled']
        if name != 'scientific':
            assert summary['status'] == 'TECHNICAL_ONLY'
            assert summary['primary']['lower_bound_above_075'] is None
            assert summary['noninferiority']['lower_bound_above_minus_005'] is None
            assert summary['qualification_requirements_pass'] is summary['full_durability_qualified'] is None
        figure = HERE/'figures'/run.name
        prov = load(figure/'provenance.json')
        for key, file in (('complete_sha256', 'COMPLETE.json'), ('audit_sha256', 'INDEPENDENT_AUDIT.json'), ('summary_sha256', 'summary.json')):
            assert prov[key] == sha(run/file)
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
        evidence[name] = dict(original_outputs_verified=nfiles, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), manifest_sha256=sha(run/'manifest.json'),
            summary_sha256=sha(run/'summary.json'), figure_provenance_sha256=sha(figure/'provenance.json'),
            individual_observations=terminal, body_individual_observations=body,
            simulation_seconds=complete['seconds'], audit_seconds=audited['seconds'],
            retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
    forecast_path = analysis/'forecast_v1.json'
    forecast = load(forecast_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    assert forecast['fixture_receipt_sha256'] == sha(analysis/'fixtures_v1.json')
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark']['audit_sha256']
    assert forecast['benchmark_total_bytes'] == evidence['benchmark']['retained_bytes']
    for name, kind, launch_file, preflight_file, launcher_file in (
        ('benchmark_v1', 'benchmark', 'launch_verification_v1.json', 'prelaunch_benchmark_v1.json', 'launch_benchmark.py'),
        ('durability_v1', 'scientific', 'scientific_launch_verification_v1.json', 'prelaunch_scientific_v1.json', 'launch_scientific.py')):
        job = HERE/'jobs'/name
        check_inputs(job)
        status, start = load(job/'status.json'), load(job/'launch.json')
        assert status['status'] == 'COMPLETE' and status['mode'] == kind
        assert status['forecast_sha256'] == sha(forecast_path) and not status['automatic_successor_started']
        for key, expected in (('scientific_complete_sha256', 'complete_sha256'), ('audit_sha256', 'audit_sha256'), ('figure_provenance_sha256', 'figure_provenance_sha256')):
            assert status[key] == evidence[kind][expected]
        launch, preflight = load(analysis/launch_file), load(analysis/preflight_file)
        assert launch['status'] == preflight['status'] == 'PASS'
        assert launch['preflight_sha256'] == sha(analysis/preflight_file)
        assert launch['launcher_sha256'] == preflight['launcher_sha256'] == sha(analysis/launcher_file)
        assert launch['pid'] == start['pid'] and launch['launch_utc'] == start['utc']
        evidence[kind].update(completed_utc=status['utc'], workflow_seconds=status['seconds'])
    preflight = load(analysis/'prelaunch_scientific_v1.json')
    for rel, digest in {**preflight['inputs_sha256'], **preflight['receipts_sha256']}.items(): assert sha(ROOT/rel) == digest, rel
    run = HERE/'runs/durability_v1'
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    contract = manifest['contract']
    assert contract['blocks'] == summary['blocks'] == preflight['blocks'] == list(range(27000, 27032))
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == contract['blocks']
    assert len(list(run.glob('source_*.npz'))) == 32
    assert len(list(run.glob('boundary_*.npz'))) == 512 and len(list(run.glob('assay_*.npz'))) == 160
    assert manifest['cpu_affinity'] == forecast['cpu_affinity'] and manifest['numerical_threads'] == 1
    assert contract['workers'] == forecast['workers'] == 8
    assert contract['config'] == preflight['config'] == summary['cfg']
    assert contract['cycle'] == preflight['cycle'] == summary['cycle'] == dict(generations=16, read_steps=2048, settling_steps=256, write_steps=128)
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['strength_threshold'] == .5 and not summary['transmitted_ancestry_metadata']
    assert summary['raw_evidence'] == 'E031_compact_v1' and summary['evidence_status'] == contract['mode']
    primary, ni = summary['primary'], summary['noninferiority']
    assert primary['statistics'] == summary['groups']['16']['local_strength']['maturing']['both_cues']['scattered']['own']
    assert ni['statistics'] == summary['packet_contrasts']['16']['local_strength']['maturing_minus_strength_compensated']['both_cues']['scattered']
    assert primary['margin'] == .75 and ni['margin'] == -.05
    assert primary['lower_bound_above_075'] == (primary['statistics']['ci95'][0] > .75)
    assert ni['lower_bound_above_minus_005'] == (ni['statistics']['ci95'][0] > -.05)
    assert len(summary['qualification_gates']) == 23 and len(summary['boundary_gates']) == 12
    assert summary['qualification_requirements_pass'] == all(summary['qualification_gates'].values())
    full = primary['lower_bound_above_075'] and ni['lower_bound_above_minus_005'] and summary['qualification_requirements_pass']
    assert summary['full_durability_qualified'] == full
    assert summary['status'] == ('DURABLE_THROUGH_16_RENEWALS' if full else 'DURABILITY_NOT_ESTABLISHED')
    source = load(HERE/'SOURCE_EVIDENCE.json')
    for rel, digest in source['provenance_sha256'].items(): assert sha(ROOT/rel) == digest
    check_inputs(ROOT/'E030_maturing_confirmation/runs/confirmation_v1')
    previous = load(ROOT/'E030_maturing_confirmation/analysis/closeout_v1.json')
    assert previous['status'] == 'PASS'
    assert previous['verification_code_sha256'] == sha(ROOT/'E030_maturing_confirmation/analysis/verify_closeout.py')
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(__file__),
        scientific_status=summary['status'], primary=primary, noninferiority=ni,
        qualification_gates=summary['qualification_gates'], runs=evidence,
        frozen_inputs_verified=27, all_original_outputs_and_compressed_csv_counts_verified=True,
        source_provenance_unchanged=True, fixtures_forecast_launch_and_figure_receipts_verified=True,
        scientific_figure_visually_inspected=True, new_trajectories_run=False,
        forecast_seconds=forecast['forecast_seconds'], actual_workflow_seconds=evidence['scientific']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['scientific']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'],
        available_bytes=shutil.disk_usage(HERE).free, active_experiment_jobs=active, subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps({k:result[k] for k in ('status', 'verified_utc', 'scientific_status', 'runs',
        'actual_workflow_seconds', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2), flush=True)


if __name__ == '__main__': main()
