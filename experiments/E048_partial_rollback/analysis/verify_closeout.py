"""Verify completed artifacts and operational receipts without new trajectories."""
import argparse
import json
from pathlib import Path
import shutil
import sys
HERE = Path(__file__).resolve().parents[1]; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import check_inputs, dump, sha, utc
from E015_functional_inheritance.audit import verify
from E048_partial_rollback.run import input_paths


def load(p): return json.loads(p.read_text())


def main():
    p = argparse.ArgumentParser(); p.add_argument('--figure-inspected', action='store_true', required=True); p.parse_args()
    dest = HERE/'analysis/closeout_v1.json'; assert not dest.exists()
    check_inputs(HERE/'analysis/freeze_v1')
    technical, forecast, pre = [load(HERE/'analysis'/name) for name in
        ('technical_v1.json', 'forecast_v1.json', 'prelaunch_scientific_v1.json')]
    inputs = {str(p.relative_to(ROOT)):sha(p) for p in input_paths()}
    assert len(inputs) == 17 and inputs == technical['inputs_sha256'] == forecast['inputs_sha256'] == pre['inputs_sha256']
    assert technical['status'] == pre['status'] == 'PASS' and technical['tests'] == 12
    assert technical['runner_sha256'] == sha(HERE/'analysis/run_technical.py')
    assert pre['launcher_sha256'] == sha(HERE/'analysis/launch_scientific.py')
    assert pre['fixtures_and_benchmark_figures_inspected']
    assert pre['forecast_sha256'] == sha(HERE/'analysis/forecast_v1.json')
    assert pre['technical_receipt_sha256'] == forecast['technical_receipt_sha256'] == sha(HERE/'analysis/technical_v1.json')
    for name, stage in technical['stages'].items():
        assert stage['returncode'] == 0 and stage['log_sha256'] == sha(HERE/'analysis'/f'{name}_v1.log')
    for rel, digest in pre['evidence_sha256'].items(): assert sha(ROOT/rel) == digest
    sources = load(HERE/'SOURCE_DATA.json')
    for rel, digest in sources['sha256'].items(): assert sha(ROOT/rel) == digest
    for rel in set(sources['sources'].values()) | set(sources['reference'].values()) | {p for p in sources['chronology'].values() if p}: verify(ROOT/rel)
    runs = {}
    for name, blocks, count, observations in (('fixture_v1', [900041], 25, 48),
        ('benchmark_v1', [900041], 25, 24), ('partial_v1', list(range(32000, 32032)), 180, 1806)):
        run = HERE/'runs'/name; m = verify(run); c, a, s = [load(run/f) for f in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json')]
        assert m['inputs_sha256'] == inputs and m['contract']['blocks'] == s['blocks'] == blocks
        assert len(c['outputs_sha256']) == count
        assert a['status'] == 'PASS' and a['complete_sha256'] == sha(run/'COMPLETE.json')
        assert a['audit_code_sha256'] == sha(HERE/'audit.py') and a['summaries_checked'] == 40
        assert a['original_and_full_match_e047_byte_exactly']
        assert a['individual_observations'] == s['individual_observations'] == observations
        assert a['cohort'] == s['cohort']
        assert all(v for v in a.values() if isinstance(v, bool))
        for pattern in ('selection_*.npz', 'read_*.npz', 'cases_*.npz', 'worker_*.json', 'worker_*.log'):
            assert len(list(run.glob(pattern))) == len(blocks)
        assert not s['multi_generation_policy_tested'] and s['prior_cases_reused'] and not s['selection_uses_future_outcomes']
        fig = HERE/'figures'/name; provenance = load(fig/'provenance.json')
        for key, file in (('complete_sha256', 'COMPLETE.json'), ('audit_sha256', 'INDEPENDENT_AUDIT.json'), ('summary_sha256', 'summary.json')):
            assert provenance[key] == sha(run/file)
        assert provenance['plot_code_sha256'] == sha(HERE/'plot.py')
        for file, digest in provenance['outputs_sha256'].items(): assert sha(fig/file) == digest
        workflow_seconds = None
        if name != 'fixture_v1':
            check_inputs(HERE/'jobs'/name); status = load(HERE/'jobs'/name/'status.json')
            assert status['status'] == 'COMPLETE' and not status['automatic_successor_started']
            assert status['complete_sha256'] == sha(run/'COMPLETE.json') and status['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
            assert status['figure_provenance_sha256'] == sha(fig/'provenance.json'); workflow_seconds = status['seconds']
        runs[name] = dict(original_outputs_verified=count, blocks=len(blocks), individual_observations=observations,
            workflow_seconds=workflow_seconds, audit_finished_utc=a['utc'], scientific_status=s['status'],
            retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            summary_sha256=sha(run/'summary.json'), figure_provenance_sha256=sha(fig/'provenance.json'))
    assert runs['partial_v1']['retained_bytes'] < forecast['storage_with_reserve_bytes']
    assert forecast['benchmark_complete_sha256'] == runs['benchmark_v1']['complete_sha256']
    assert forecast['benchmark_audit_sha256'] == runs['benchmark_v1']['audit_sha256']
    s = load(HERE/'runs/partial_v1/summary.json'); assert s['cohort']['eligible'] == 301 and s['cohort']['total_lineages'] == 512
    assert sum(s['groups']['original']['both_cues']['block_numerators']) == 174
    assert sum(s['groups']['full_rollback']['both_cues']['block_numerators']) == 193
    for group in s['transitions'].values(): assert sum(group['counts'].values()) == 301
    assert s['selection']['affected_cases']+s['selection']['zero_edit_cases'] == 301
    active = [str(p.relative_to(ROOT)) for p in ROOT.glob('E*/jobs/*/status.json') if load(p).get('status') in ('RUNNING', 'PREPARED')]
    assert not active, active
    result = dict(status='PASS', utc=utc(), verification_code_sha256=sha(__file__), runs=runs,
        frozen_inputs_verified=17, source_and_all_original_output_hashes_verified=True, operational_receipts_verified=True,
        figures_visually_inspected=True, source_sha256=sources['sha256'], original_and_full_match_e047_byte_exactly=True,
        scientific_log_sha256=sha(HERE/'analysis/scientific_v1.log'), forecast_seconds=forecast['forecast_seconds'],
        actual_minus_forecast_seconds=runs['partial_v1']['workflow_seconds']-forecast['forecast_seconds'],
        storage_forecast_including_reserve_bytes=forecast['storage_with_reserve_bytes'], available_bytes=shutil.disk_usage(HERE).free,
        active_jobs=active, subsequent_experiment_started=False)
    dump(dest, result)
    print(json.dumps({k:result[k] for k in ('status', 'utc', 'runs', 'actual_minus_forecast_seconds', 'available_bytes')}, indent=2))


if __name__ == '__main__': main()
