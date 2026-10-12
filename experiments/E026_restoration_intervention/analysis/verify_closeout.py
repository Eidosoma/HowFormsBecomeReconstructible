"""Verify retained diagnostic evidence without rerunning scientific trajectories."""
import argparse
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, sha, utc
from E026_restoration_intervention.workflow import fixtures


def load(path):
    return json.loads(path.read_text())


def compact(value):
    if isinstance(value, dict):
        return {key: compact(item) for key, item in value.items() if key != 'block_means'}
    return value


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
    for label, run, count, nfiles in (
        ('fixture', HERE/'analysis/fixture_attempt1', 2688, 28),
        ('benchmark_v1', HERE/'runs/benchmark_v1', 1344, 29),
        ('restoration_v1', HERE/'runs/restoration_v1', 172032, 153)):
        check_inputs(run)
        manifest = load(run/'manifest.json')
        assert len(manifest['inputs_sha256']) == 21
        assert manifest['inputs_sha256'] == receipt['inputs_sha256']
        complete, audit = load(run/'COMPLETE.json'), load(run/'INDEPENDENT_AUDIT.json')
        assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
        assert not (run/'FAILED.json').exists()
        assert len(complete['outputs_sha256']) == nfiles
        for rel, digest in complete['outputs_sha256'].items():
            assert sha(run/rel) == digest, (label, rel)
        assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == count
        for key, value in audit.items():
            if isinstance(value, bool):
                assert value, (label, key)
        with (run/'observations.csv').open(newline='') as handle:
            assert sum(1 for _ in csv.DictReader(handle)) == count
        summary = load(run/'summary.json')
        assert summary['individual_observations'] == count
        assert len(summary['panels']) == 8 and summary['original_endpoint_replay_exact']
        assert not summary['new_independent_cohort'] and not summary['new_teaching_or_renewal']
        if label != 'restoration_v1':
            assert summary['status'] == 'TECHNICAL_ONLY'
            for item in summary['focal'].values():
                assert item['lower_bound_above_zero'] is item['lower_bound_above_010'] is None
        evidence[label] = dict(original_outputs_verified=nfiles, individual_observations=count,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'])
        if label == 'fixture':
            continue
        job, figure = HERE/'jobs'/label, HERE/'figures'/label
        check_inputs(job)
        status, prov = load(job/'status.json'), load(figure/'provenance.json')
        assert status['status'] == 'COMPLETE' and not (job/'FAILED.json').exists()
        assert status['scientific_complete_sha256'] == prov['complete_sha256'] == evidence[label]['complete_sha256']
        assert status['audit_sha256'] == prov['audit_sha256'] == evidence[label]['audit_sha256']
        assert status['figure_provenance_sha256'] == sha(figure/'provenance.json')
        assert prov['summary_sha256'] == sha(run/'summary.json')
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for rel, digest in prov['outputs_sha256'].items():
            assert sha(figure/rel) == digest
        evidence[label].update(completed_utc=status['utc'], workflow_seconds=status['seconds'],
            figure_provenance_sha256=sha(figure/'provenance.json'))

    forecast_path = HERE/'analysis/forecast_v1.json'
    bench_forecast_path = HERE/'analysis/benchmark_forecast_v1.json'
    prelaunch_path = HERE/'analysis/prelaunch_verification_v1.json'
    forecast, bench_forecast = load(forecast_path), load(bench_forecast_path)
    prelaunch, launch = load(prelaunch_path), load(HERE/'analysis/launch_verification_v1.json')
    assert prelaunch['status'] == launch['status'] == 'PASS'
    assert launch['forecast_sha256'] == prelaunch['forecast_sha256'] == sha(forecast_path)
    assert prelaunch['benchmark_forecast_sha256'] == sha(bench_forecast_path)
    assert launch['preflight_sha256'] == sha(prelaunch_path)
    assert launch['operational_launcher_sha256'] == prelaunch['operational_launcher_sha256'] == sha(HERE/'analysis/launch_verified.py')
    assert prelaunch['verification_code_sha256'] == sha(HERE/'analysis/verify_prelaunch.py')
    assert prelaunch['fixture_receipt_sha256'] == sha(receipt_path)
    for item in (forecast, bench_forecast):
        assert item['fixture_receipt_sha256'] == sha(receipt_path)
        assert item['inputs_sha256'] == receipt['inputs_sha256']
    assert forecast['benchmark_complete_sha256'] == evidence['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == evidence['benchmark_v1']['audit_sha256']
    assert prelaunch['figure_provenance_sha256'] == evidence['benchmark_v1']['figure_provenance_sha256']
    for old, new in (('fixture', 'fixture'), ('benchmark', 'benchmark_v1')):
        for key, value in prelaunch['evidence'][old].items():
            assert evidence[new][key] == value
    assert not bench_forecast['detached_required'] and bench_forecast['forecast_seconds'] <= 600
    assert forecast['detached_required'] and forecast['forecast_seconds'] > 600

    assert prelaunch['source_data_index_sha256'] == sha(HERE/'SOURCE_DATA.json')
    source_evidence = {}
    sources = load(HERE/'SOURCE_DATA.json')
    for label, spec in sources.items():
        source = ROOT/spec['path']
        check_inputs(source)
        for rel, digest in spec['provenance_sha256'].items():
            assert sha(source/rel) == digest, (label, rel)
        old_audit = load(source/'INDEPENDENT_AUDIT.json')
        assert old_audit['status'] == 'PASS' and old_audit['complete_sha256'] == sha(source/'COMPLETE.json')
        nfiles = 0
        for block, files in spec['files'].items():
            for name, digest in files.items():
                assert sha(source/name) == digest, (label, block, name)
                nfiles += 1
        source_evidence[label] = dict(path=spec['path'], blocks=spec['blocks'], raw_files_verified=nfiles,
            complete_sha256=sha(source/'COMPLETE.json'), audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'))
    assert source_evidence == prelaunch['source_evidence']
    assert sum(item['raw_files_verified'] for item in source_evidence.values()) == 136
    prior_closeout = ROOT/'E025_rewriting_confirmation/analysis/closeout_v1.json'
    assert prelaunch['predecessor_closeout_sha256'] == sha(prior_closeout)
    assert load(prior_closeout)['status'] == 'PASS'
    assert load(prior_closeout)['verification_code_sha256'] == sha(prior_closeout.parent/'verify_closeout.py')
    for rel in prelaunch['predecessor_inputs_unchanged']:
        check_inputs(ROOT/rel)
    diagnoses = ('E022_reader_compensation/analysis/transmission_diagnosis_v1',
        'E025_rewriting_confirmation/analysis/rebuilding_leads_v1',
        'E025_rewriting_confirmation/analysis/rebuilding_link_scale_v1')
    for rel in diagnoses:
        check_inputs(ROOT/rel)

    run = HERE/'runs/restoration_v1'
    manifest, summary = load(run/'manifest.json'), load(run/'summary.json')
    contract = manifest['contract']
    blocks = list(range(23000, 23032))
    assert contract['blocks'] == summary['blocks'] == sources['cohort']['blocks'] == blocks
    assert sorted(int(p.stem.split('_')[1]) for p in run.glob('worker_*.json')) == blocks
    for block in blocks:
        worker = load(run/f'worker_{block}.json')
        assert worker['block'] == block and worker['source'] == 'cohort'
        assert worker['original_endpoint_packets_and_all_terminal_arrays_exact']
        assert worker['source_files_sha256'] == sources['cohort']['files'][str(block)]
    assert contract['mode'] == 'post_hoc_intervention' and contract['source'] == summary['source'] == 'cohort'
    assert manifest['numerical_threads'] == forecast['numerical_threads'] == 1
    assert manifest['cpu_affinity'] == forecast['cpu_affinity']
    assert contract['workers'] == forecast['workers'] == 8
    assert contract['cycle'] == summary['cycle'] and contract['cycle']['generations'] == 3
    assert contract['panels'] == summary['panels'] and len(contract['panels']) == 8
    assert summary['founders'] == 128 and summary['lineages'] == 512
    assert summary['status'] == 'RESTORATION_DIAGNOSTIC_COMPLETE'
    assert summary['evidence_status'] == 'post_hoc_saved_cohort_intervention'
    for item in summary['focal'].values():
        assert item['lower_bound_above_zero'] == (item['statistics']['ci95'][0] > 0)
        assert item['lower_bound_above_010'] == (item['statistics']['ci95'][0] > .10)
    old_summary = load(ROOT/sources['cohort']['path']/'summary.json')
    for receiver, conditions in summary['groups'].items():
        for group in conditions.values():
            assert len(group['gates']) == 24
            assert group['all_original_gates_pass'] == all(group['gates'].values())
        for new, old in (('copy', 'masked_copy'), ('rebuilt', 'strength_compensated')):
            for metric in ('accuracy', 'both_cues', 'margin'):
                for damage in summary['damage']:
                    for arm in summary['arms']:
                        new_stat = conditions[new][metric][damage][arm]
                        old_stat = old_summary['groups']['3'][receiver][old][metric][damage][arm]
                        for key in ('mean', 'block_means'):
                            assert new_stat[key] == old_stat[key], (receiver, new, metric, damage, arm, key)
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json')
              if load(p).get('status') in ('PREPARED', 'RUNNING')]
    result = dict(status='PASS', verified_utc=utc(), verification_code_sha256=sha(Path(__file__)),
        scientific_status=summary['status'], evidence_status=summary['evidence_status'],
        focal=compact(summary['focal']), runs=evidence, source_evidence=source_evidence,
        own_both_cues={receiver: {condition: {damage: compact(group['both_cues'][damage]['own'])
            for damage in summary['damage']} for condition, group in groups.items()}
            for receiver, groups in summary['groups'].items()},
        original_gates_passed={receiver: {condition: sum(group['gates'].values())
            for condition, group in groups.items()} for receiver, groups in summary['groups'].items()},
        forecast_seconds=forecast['forecast_seconds'],
        actual_workflow_seconds=evidence['restoration_v1']['workflow_seconds'],
        actual_minus_forecast_seconds=evidence['restoration_v1']['workflow_seconds']-forecast['forecast_seconds'],
        all_frozen_inputs_and_original_outputs_verified=True, csv_row_counts_verified=True,
        fixture_receipt_and_evidence_verified=True, workflow_and_figure_references_verified=True,
        launch_receipts_and_operational_launcher_verified=True, original_endpoint_block_statistics_unchanged=True,
        scientific_figure_visually_inspected=True, source_raw_files_and_audit_provenance_verified=True,
        predecessor_frozen_inputs_unchanged=prelaunch['predecessor_inputs_unchanged'],
        predecessor_diagnosis_inputs_unchanged=list(diagnoses), active_experiment_jobs=active,
        new_trajectories_run_during_closeout=False, subsequent_experiment_started=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'scientific_status', 'focal', 'runs',
        'actual_workflow_seconds', 'actual_minus_forecast_seconds', 'active_experiment_jobs')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
