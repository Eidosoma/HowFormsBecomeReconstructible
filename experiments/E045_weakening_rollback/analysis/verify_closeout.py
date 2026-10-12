"""Verify the completed receiving experiment and its retained provenance; no dynamics."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, sha, utc
from E015_functional_inheritance.audit import verify


def load(path):
    return json.loads(path.read_text())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--figure-inspected', action='store_true', required=True)
    p.parse_args(); cap_cpus(1)
    analysis = HERE/'analysis'; dest = analysis/'closeout_v1.json'
    assert not dest.exists()
    check_inputs(analysis/'freeze_v1')
    technical = load(analysis/'technical_v1.json')
    assert technical['status'] == 'PASS' and technical['tests'] == 12
    assert technical['runner_sha256'] == sha(analysis/'run_technical.py')
    assert technical['inputs_sha256'] == load(analysis/'freeze_v1/manifest.json')['inputs_sha256']
    for stage, receipt in technical['stages'].items():
        assert receipt['returncode'] == 0 and receipt['log_sha256'] == sha(analysis/f'{stage}_v1.log')
    runs = {}
    for name, blocks, outputs, scores in (('fixture_v1', [900041], 31, 4032),
                                         ('benchmark_v1', [900041], 31, 2016),
                                         ('rollback_v1', list(range(32000, 32032)), 248, 258048)):
        r = HERE/'runs'/name; m = verify(r)
        complete, audit, s = [load(r/f) for f in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json')]
        assert len(complete['outputs_sha256']) == outputs
        assert m['inputs_sha256'] == technical['inputs_sha256'] and len(m['inputs_sha256']) == 21
        assert m['contract']['blocks'] == s['blocks'] == blocks
        assert len(list(r.glob('assay_*.npz'))) == 2*len(blocks)
        assert len(list(r.glob('intervention_*.npz'))) == 2*len(blocks)
        assert len(list(r.glob('cases_*.npz'))) == len(list(r.glob('worker_*.json'))) == len(blocks)
        assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(r/'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE/'audit.py')
        assert audit['individual_observations'] == s['individual_observations'] == scores
        assert all(v for v in audit.values() if isinstance(v, bool))
        assert s['prior_cases_reused'] and s['packets_changed'] and not s['renewal_policy_changed']
        assert s['source_policy'] == 'bridge_rewrite' and s['source_policy_index'] == 3
        if name != 'rollback_v1':
            assert s['status'] == 'TECHNICAL_ONLY' and s['primary']['joint_pass'] is None
            assert s['absolute_h32_targeted_reliability_lower_above_075'] is None
        fig = HERE/'figures'/name; prov = load(fig/'provenance.json')
        for key, file in (('complete_sha256', 'COMPLETE.json'), ('audit_sha256', 'INDEPENDENT_AUDIT.json'), ('summary_sha256', 'summary.json')):
            assert prov[key] == sha(r/file)
        assert prov['plot_code_sha256'] == sha(HERE/'plot.py')
        for file, digest in prov['outputs_sha256'].items(): assert sha(fig/file) == digest
        runs[name] = dict(original_outputs_verified=outputs, blocks=len(blocks), individual_cue_scores=scores,
            complete_sha256=sha(r/'COMPLETE.json'), audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'),
            summary_sha256=sha(r/'summary.json'), figure_provenance_sha256=sha(fig/'provenance.json'),
            simulation_seconds=complete['seconds'], audit_seconds=audit['seconds'],
            retained_bytes=sum(f.stat().st_size for f in r.rglob('*') if f.is_file()))
    assert technical['fixture_complete_sha256'] == runs['fixture_v1']['complete_sha256']
    assert technical['fixture_audit_sha256'] == runs['fixture_v1']['audit_sha256']
    for name in ('benchmark_v1', 'rollback_v1'):
        job = HERE/'jobs'/name; check_inputs(job); status = load(job/'status.json')
        assert status['status'] == 'COMPLETE' and not status['automatic_successor_started']
        for key in ('complete_sha256', 'audit_sha256', 'figure_provenance_sha256'):
            assert status[key] == runs[name][key]
        runs[name].update(workflow_seconds=status['seconds'], finished_utc=status['utc'])
    pre = load(analysis/'prelaunch_scientific_v1.json'); launch = load(analysis/'scientific_launch_verification_v1.json')
    forecast = load(analysis/'forecast_v1.json'); start = load(HERE/'jobs/rollback_v1/launch.json')
    assert pre['status'] == launch['status'] == 'PASS'
    assert pre['launcher_sha256'] == launch['launcher_sha256'] == sha(analysis/'launch_scientific.py')
    assert launch['preflight_sha256'] == sha(analysis/'prelaunch_scientific_v1.json')
    assert launch['pid'] == start['pid'] and launch['launch_utc'] == start['utc']
    assert pre['forecast_sha256'] == sha(analysis/'forecast_v1.json')
    assert pre['technical_receipt_sha256'] == forecast['technical_receipt_sha256'] == sha(analysis/'technical_v1.json')
    assert pre['inputs_sha256'] == forecast['inputs_sha256'] == technical['inputs_sha256']
    assert forecast['benchmark_complete_sha256'] == runs['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == runs['benchmark_v1']['audit_sha256']
    assert forecast['benchmark_run_bytes'] == runs['benchmark_v1']['retained_bytes']
    assert forecast['forecast_seconds'] == 2.0*forecast['benchmark_seconds']*16*4*math.ceil(32/forecast['workers'])+120
    assert forecast['storage_with_reserve_bytes'] == math.ceil(1.5*forecast['benchmark_run_bytes']*4*32)+128*1024**2
    source = load(HERE/'SOURCE_DATA.json')
    for rel, digest in {**pre['inputs_sha256'], **pre['evidence_sha256'], **source['sha256']}.items():
        assert sha(ROOT/rel) == digest, rel
    for key in ('source_run', 'fixture_run', 'benchmark_run'): verify(ROOT/source[key])
    run = HERE/'runs/rollback_v1'; s = load(run/'summary.json')
    assert s['lineages'] == 512 and len(s['panels']) == 12
    passes = []
    for low, threshold in (('original', .05), ('random_rollback', 0.)):
        comparison = s['primary']['comparisons'][low]
        assert comparison['statistics'] == s['contrasts']['32']['local_strength']['targeted_rollback_minus_'+low]['both_cues']['scattered']
        assert comparison['margin'] == threshold
        passed = comparison['statistics']['ci95'][0] > threshold
        assert comparison['lower_above_margin'] == passed
        passes.append(passed)
    passed = all(passes)
    assert s['primary']['joint_pass'] == passed
    assert s['status'] == ('TARGETED_ROLLBACK_BENEFIT_ESTABLISHED' if passed else 'TARGETED_ROLLBACK_BENEFIT_NOT_ESTABLISHED')
    absolute = s['groups']['32']['local_strength']['targeted_rollback']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert s['absolute_h32_targeted_reliability_lower_above_075'] == absolute
    assert s['selection_uses_terminal_outcomes'] is False
    for h in ('24', '32'):
        counts = s['selection'][h]['totals']
        assert counts['target_edges'] == counts['random_edges']
        assert 0 <= counts['overlap_edges'] <= counts['target_edges'] <= counts['pool_edges']
    assert runs['rollback_v1']['retained_bytes'] < forecast['storage_with_reserve_bytes']
    active = [str(f.relative_to(ROOT)) for f in ROOT.glob('E*/jobs/*/status.json') if load(f).get('status') in ('RUNNING', 'PREPARED')]
    assert not active, active
    result = dict(status='PASS', utc=utc(), verification_code_sha256=sha(__file__),
        scientific_status=s['status'], primary=s['primary'], absolute_reliability_passed=absolute, runs=runs,
        frozen_inputs_verified=21, all_original_outputs_and_source_provenance_verified=True,
        operational_receipts_verified=True, scientific_figure_visually_inspected=True,
        forecast_seconds=forecast['forecast_seconds'],
        actual_minus_forecast_seconds=runs['rollback_v1']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'],
        available_bytes=shutil.disk_usage(HERE).free, active_jobs=active,
        new_trajectories_run=False, subsequent_experiment_started=False)
    dump(dest, result)
    print(json.dumps({k:result[k] for k in ('status', 'utc', 'scientific_status', 'runs', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2))


if __name__ == '__main__': main()
