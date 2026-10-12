"""Verify completed artifacts and provenance without running new trajectories."""
import argparse
import csv
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E015_functional_inheritance.audit import verify
from E028_precursor_rewriting.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true', required=True)
    parser.parse_args()
    destination = HERE/'analysis/closeout_v1.json'
    assert not destination.exists()
    fixtures()
    receipt_path = HERE/'analysis/fixtures_v1.json'
    receipt = load(receipt_path)
    invocation = HERE/'analysis/fixture_invocation_v1.json'
    assert receipt['invocation_sha256'] == sha(invocation)
    assert receipt['inputs_sha256'] == load(invocation)['inputs_sha256']
    evidence = {}
    for label, run, terminal, body, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 2688, 32, 30),
        ('benchmark_v1', HERE/'runs/benchmark_v1', 1344, 16, 31),
        ('precursor_v1', HERE/'runs/precursor_v1', 172032, 2048, 155)):
        manifest = verify(run)
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert len(complete['outputs_sha256']) == nfiles
        assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == terminal and audit['body_individual_observations'] == body
        for key, value in audit.items():
            if isinstance(value, bool): assert value, key
        for name, count in (('observations.csv', terminal), ('body_observations.csv', body), ('target_strength.csv', body//4)):
            with (run/name).open(newline='') as handle: assert sum(1 for _ in csv.DictReader(handle)) == count
        assert len(manifest['inputs_sha256']) == 21
        assert manifest['inputs_sha256'] == receipt['inputs_sha256']
        figure = HERE/'figures'/('fixture_attempt1' if label == 'fixture' else label)
        prov = load(figure/'provenance.json')
        assert prov['complete_sha256'] == sha(run/'COMPLETE.json')
        assert prov['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
        assert prov['summary_sha256'] == sha(run/'summary.json') and prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items(): assert sha(figure/rel) == digest
        evidence[label] = dict(original_outputs_verified=nfiles, complete_sha256=sha(run/'COMPLETE.json'),
            audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), manifest_sha256=sha(run/'manifest.json'),
            individual_observations=terminal, body_individual_observations=body, target_strength_rows=body//4,
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'],
            figure_provenance_sha256=sha(figure/'provenance.json'))
        if label != 'precursor_v1':
            summary = load(run/'summary.json')
            assert summary['status'] == 'TECHNICAL_ONLY'
            for item in summary['focal'].values():
                assert item['lower_bound_above_zero'] is item['lower_bound_above_010'] is None
        if label == 'fixture': continue
        job = HERE/'jobs'/label
        check_inputs(job)
        status = load(job/'status.json')
        assert status['status'] == 'COMPLETE'
        assert status['scientific_complete_sha256'] == evidence[label]['complete_sha256']
        assert status['audit_sha256'] == evidence[label]['audit_sha256']
        assert status['figure_provenance_sha256'] == evidence[label]['figure_provenance_sha256']
        evidence[label].update(completed_utc=status['utc'], workflow_seconds=status['seconds'])
    analysis = HERE/'analysis'
    forecast_path, prelaunch_path = analysis/'forecast_v1.json', analysis/'prelaunch_verification_v1.json'
    forecast, prelaunch = load(forecast_path), load(prelaunch_path)
    launch = load(analysis/'launch_verification_v1.json')
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(forecast_path)
    assert launch['preflight_sha256'] == sha(prelaunch_path)
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(analysis/'launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(analysis/'verify_prelaunch.py')
    assert forecast['fixture_receipt_sha256'] == prelaunch['fixture_receipt_sha256'] == sha(receipt_path)
    assert forecast['inputs_sha256'] == receipt['inputs_sha256']
    for old, new in (('fixture', 'fixture'), ('benchmark', 'benchmark_v1')):
        for key, value in prelaunch['evidence'][old].items(): assert evidence[new][key] == value, (old, key)
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark_v1']['audit_sha256']
    bench_preflight_path, bench_forecast_path = analysis/'prebenchmark_verification_v1.json', analysis/'benchmark_forecast_v1.json'
    bench_preflight, bench_forecast = load(bench_preflight_path), load(bench_forecast_path)
    assert bench_preflight['status'] == 'PASS'
    assert bench_preflight['benchmark_forecast_sha256'] == prelaunch['benchmark_forecast_sha256'] == sha(bench_forecast_path)
    assert bench_preflight['fixture_receipt_sha256'] == bench_forecast['fixture_receipt_sha256'] == sha(receipt_path)
    assert bench_preflight['fixture_figure_provenance_sha256'] == evidence['fixture']['figure_provenance_sha256']
    assert bench_forecast['inputs_sha256'] == receipt['inputs_sha256'] and not bench_forecast['detached_required']
    prior_benchmark = ROOT/'E026_restoration_intervention/runs/benchmark_v1'
    verify(prior_benchmark)
    prior_audit = load(prior_benchmark/'INDEPENDENT_AUDIT.json')
    assert prior_audit['status'] == 'PASS' and prior_audit['complete_sha256'] == sha(prior_benchmark/'COMPLETE.json')
    assert bench_forecast['source_benchmark_worker_sha256'] == sha(prior_benchmark/'worker_900024.json')
    assert bench_forecast['source_benchmark_audit_sha256'] == sha(prior_benchmark/'INDEPENDENT_AUDIT.json')
    assert prelaunch['benchmark_completed_utc'] == evidence['benchmark_v1']['completed_utc']
    assert prelaunch['benchmark_workflow_seconds'] == evidence['benchmark_v1']['workflow_seconds']
    assert prelaunch['source_data_index_sha256'] == sha(HERE/'SOURCE_DATA.json')
    sources = {}
    for label, spec in load(HERE/'SOURCE_DATA.json').items():
        source = ROOT/spec['path']; check_inputs(source)
        for rel, digest in spec['provenance_sha256'].items(): assert sha(source/rel) == digest
        complete, audit = load(source/'COMPLETE.json'), load(source/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS' and audit['complete_sha256'] == sha(source/'COMPLETE.json')
        for files in spec['files'].values():
            for rel, digest in files.items(): assert sha(source/rel) == digest == complete['outputs_sha256'][rel]
        sources[label] = dict(path=spec['path'], blocks=spec['blocks'], raw_files_verified=sum(map(len, spec['files'].values())),
            complete_sha256=sha(source/'COMPLETE.json'), audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'))
        assert sources[label] == prelaunch['source_evidence'][label]
    prior_closeout = ROOT/'E027_selective_renewal/analysis/closeout_v1.json'
    assert prelaunch['predecessor_closeout_sha256'] == sha(prior_closeout)
    old = load(prior_closeout)
    assert old['status'] == 'PASS' and old['verification_code_sha256'] == sha(prior_closeout.parent/'verify_closeout.py')
    diagnoses = old['predecessor_diagnosis_inputs_unchanged']
    for rel in prelaunch['predecessor_inputs_unchanged']+diagnoses: check_inputs(ROOT/rel)
    run = HERE/'runs/precursor_v1'
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    blocks = list(range(24000, 24032))
    assert manifest['contract']['blocks'] == summary['blocks'] == sources['cohort']['blocks'] == blocks
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    assert manifest['numerical_threads'] == 1 and manifest['cpu_affinity'] == forecast['cpu_affinity']
    assert manifest['contract']['workers'] == forecast['workers'] == 8
    assert manifest['contract']['cycle']['generations'] == 3 and manifest['contract']['config']['recipients'] == 4
    assert len(manifest['contract']['receivers']) == 2 and len(manifest['contract']['panels']) == 8
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['status'] == 'PRECURSOR_DIAGNOSTIC_COMPLETE'
    assert summary['evidence_status'] == 'post_hoc_saved_cohort_intervention' and manifest['contract']['mode'] == 'post_hoc_intervention'
    assert not summary['new_independent_cohort'] and not summary['new_teaching']
    assert summary['new_generation_three_read_variants'] == 2 and summary['original_endpoint_replay_exact']
    assert set(summary['focal']) == {'rewrite_with_precursors', 'precursors_with_rewriting'}
    for name, item in summary['focal'].items():
        assert item['statistics'] == summary['contrasts']['local_strength'][name]['both_cues']['scattered']
        assert item['lower_bound_above_zero'] == (item['statistics']['ci95'][0] > 0.)
        assert item['lower_bound_above_010'] == (item['statistics']['ci95'][0] > .10)
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('PREPARED', 'RUNNING')]
    assert not active, active
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], evidence_status=summary['evidence_status'], focal=summary['focal'],
        original_gates_passed={reader: {condition: sum(group['gates'].values()) for condition, group in conditions.items()}
            for reader, conditions in summary['groups'].items()}, runs=evidence, sources=sources,
        forecast_seconds=forecast['forecast_seconds'], actual_workflow_seconds=evidence['precursor_v1']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['precursor_v1']['workflow_seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        source_provenance_and_indexed_files_verified=True, fixture_receipt_and_evidence_verified=True,
        workflow_and_figure_references_verified=True, launch_receipts_and_operational_launcher_verified=True,
        benchmark_runtime_references_verified=True, scientific_figure_visually_inspected=True,
        predecessor_frozen_inputs_unchanged=prelaunch['predecessor_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=diagnoses, active_experiment_jobs=active,
        new_trajectories_run_during_closeout=False, subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps({k:result[k] for k in ('status', 'verified_utc', 'scientific_status', 'runs',
        'actual_workflow_seconds', 'actual_minus_forecast_seconds')}, indent=2), flush=True)


if __name__ == '__main__': main()
