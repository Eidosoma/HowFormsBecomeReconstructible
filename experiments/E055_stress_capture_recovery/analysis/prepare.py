"""Freeze, technical qualification, forecast, and scientific artifact closeout."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E015_functional_inheritance.audit import verify
from E055_stress_capture_recovery.plan import HERE, ROOT, settings
from E055_stress_capture_recovery.run import input_paths
from E055_stress_capture_recovery.workflow import predecessor_gate


def checked_run(name):
    run = HERE/'runs'/name; m = verify(run)
    frozen = json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
    assert m['inputs_sha256'] == frozen
    read = lambda p: json.loads(p.read_text())
    c = read(run/'COMPLETE.json'); a = read(run/'INDEPENDENT_AUDIT.json'); s = read(run/'summary.json')
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(run/'COMPLETE.json')
    assert a['audit_code_sha256'] == sha(HERE/'audit.py')
    assert a['all_sources_pulses_states_writes_assays_diagnostics_replayed'] and a['every_step_state_hashes_replayed']
    assert a['controls_pass'] and s['controls_pass'] and a['transfer_protection'] == s['transfer_protection']
    assert a['summaries_checked'] == len(s['statistics'])
    assert c['blocks_completed'] == len(m['contract']['blocks']) == s['independent_blocks']
    job = HERE/'jobs'/name; check_inputs(job); status = read(job/'status.json')
    assert status['status'] == 'COMPLETE'
    assert status['complete_sha256'] == sha(run/'COMPLETE.json') and status['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json')
    fig = HERE/'figures'/name/'provenance.json'; meta = read(fig)
    assert meta['audit_sha256'] == sha(run/'INDEPENDENT_AUDIT.json') and meta['summary_sha256'] == sha(run/'summary.json')
    assert meta['plot_code_sha256'] == sha(HERE/'plot.py')
    for rel, digest in meta['outputs_sha256'].items(): assert sha(fig.parent/rel) == digest
    evidence = {str(p.relative_to(ROOT)):sha(p) for p in
                (run/'COMPLETE.json', run/'INDEPENDENT_AUDIT.json', run/'summary.json', fig, job/'status.json')}
    return m, c, a, s, evidence


def main(action, inspected):
    cap_cpus(1)
    if action == 'freeze':
        predecessor_gate()
        new_run(HERE/'analysis/freeze_v1', input_paths(), dict(experiment='E055', stage='freeze', scientific_outcomes_seen=False))
        print('Frozen', len(input_paths()), 'inputs'); return
    assert inspected, 'Inspect applicable figures before qualification/closeout'
    check_inputs(HERE/'analysis/freeze_v1'); predecessor = predecessor_gate()
    evidence = {}; results = {}
    for name in ('fixture_v1', 'benchmark_v1') + (('capture_v1',) if action == 'closeout' else ()):
        m, c, a, s, ev = checked_run(name); evidence.update(ev)
        if name != 'capture_v1':
            assert s['status'] == 'TECHNICAL_ONLY' and s['transfer_protection'] is None
            assert all(x is None for x in s['primary_gates'].values())
        else: assert m['contract']['blocks'] == list(range(34000, 34032))
        results[name] = dict(outputs_verified=len(c['outputs_sha256']), summaries_checked=a['summaries_checked'],
            terminal_cue_observations=a['terminal_cue_observations'], status=s['status'])
    tests = HERE/'analysis/tests_v1.log'; text = tests.read_text()
    assert '\nOK\n' in text and 'Ran 20 tests' in text
    evidence[str(tests.relative_to(ROOT))] = sha(tests)
    if action == 'ready':
        bench = HERE/'runs/benchmark_v1'
        sim = json.loads((bench/'worker_900041.json').read_text())['seconds']
        aud = json.loads((bench/'INDEPENDENT_AUDIT.json').read_text())['worker_seconds'][0]
        cfg = settings('scientific'); b = settings('benchmark')
        ratio = max((cfg['body_pre_steps']+cfg['pulse_steps']+cfg['recovery_steps']) /
                    (b['body_pre_steps']+b['pulse_steps']+b['recovery_steps']), cfg['read_steps']/b['read_steps'])
        seconds = 3*(sim+aud)*ratio*4*4+120
        size = sum(p.stat().st_size for p in bench.rglob('*') if p.is_file())
        storage = math.ceil(1.5*size*4*32)+128*1024**2
        forecast = dict(utc=utc(), workers=8, forecast_seconds=seconds, benchmark_simulation_seconds=sim,
            benchmark_audit_seconds=aud, benchmark_bytes=size, storage_with_reserve_bytes=storage,
            free_bytes=shutil.disk_usage(HERE).free, detached_required=seconds > 600,
            source_records_reused=True, basis='3x(sim+audit) x max(body/read step ratio) x4 recipients x4 waves +120s')
        assert forecast['free_bytes'] > storage
        path = HERE/'analysis/forecast_v1.json'; assert not path.exists(); dump(path, forecast)
        evidence[str(path.relative_to(ROOT))] = sha(path)
        result = dict(status='PASS', utc=utc(), tests=20, figures_inspected=True,
            scientific_run_started=False, automatic_successor_started=False, evidence_sha256=evidence,
            inputs_sha256=json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256'])
        path = HERE/'analysis/technical_v1.json'
    else:
        ready = json.loads((HERE/'analysis/technical_v1.json').read_text())
        for rel, digest in ready['evidence_sha256'].items(): assert sha(ROOT/rel) == digest
        result = dict(status='PASS', utc=utc(), figure_inspected=True, runs=results,
            evidence_sha256=evidence, predecessor_evidence=predecessor, code_sha256=sha(__file__),
            controls_pass=True, transfer_protection=s['transfer_protection'],
            joint_body_and_transfer_recovery=s['joint_body_and_transfer_recovery'],
            scientific_retained_bytes=sum(p.stat().st_size for p in (HERE/'runs/capture_v1').rglob('*') if p.is_file()),
            automatic_successor_started=False)
        path = HERE/'analysis/closeout_v1.json'
    assert not path.exists(); dump(path, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--action', required=True, choices=('freeze', 'ready', 'closeout'))
    p.add_argument('--figures-inspected', action='store_true'); args = p.parse_args()
    main(args.action, args.figures_inspected)
