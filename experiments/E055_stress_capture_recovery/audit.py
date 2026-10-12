"""Independent replay, packet-boundary checks and whole-block inference audit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, dump, utc
from E015_functional_inheritance.audit import verify, random, sha
from E055_stress_capture_recovery import audit_model as replay
from E055_stress_capture_recovery.data import load, receipt
from E055_stress_capture_recovery.plan import HERE, ROOT, NAMES, HISTORIES, ARMS, TIMES, INJURIES, GRAPH_FIELDS, settings
import numpy as np


def compare(expected, saved):
    assert set(expected) == set(saved)
    for k in expected: replay.equal(expected[k], saved[k])


def worker(run, b, cfg):
    start = time.monotonic(); source_run, index = receipt(cfg['mode'])
    for name in (f'source_{b:06d}.npz', f'boundary_{b:06d}_g32.npz'):
        assert sha(source_run/name) == index['files'][name]
    source = replay.source(source_run, b); compare(source, load(run/f'source_{b:06d}.npz'))
    body = replay.develop(source['records'], b, cfg); compare(body, load(run/f'body_{b:06d}.npz'))
    outgoing = replay.transmit(body, cfg); compare(outgoing, load(run/f'outgoing_{b:06d}.npz'))
    fresh = replay.assay(outgoing['packets'], b, cfg); compare(fresh, load(run/f'assay_{b:06d}.npz'))
    cases, controls = replay.diagnostics(body, outgoing, fresh, cfg)
    compare(cases, load(run/f'cases_{b:06d}.npz'))
    assert controls == json.loads((run/f'worker_{b}.json').read_text())['controls']
    dump(run/f'audit_worker_{b}.json', dict(status='PASS', block=b, seconds=time.monotonic()-start, controls=controls))


def independent_values(cases):
    values = {}
    for metric in ('both', 'transfer', 'aligned_transfer', 'minimum_margin'):
        for h, history in enumerate(HISTORIES):
            for a, arm in enumerate(ARMS):
                for j, injury in enumerate(INJURIES):
                    values[f'fresh/{metric}/{history}/{arm}/{injury}'] = np.array([c['fresh_'+metric][h, a, j].mean() for c in cases])
            for p, label in enumerate(('sham', 'pulse')):
                for t, name in enumerate(TIMES):
                    values[f'body/{metric}/{history}/{label}/{name}'] = np.array([c['body_'+metric][h, p, t].mean() for c in cases])
    for metric in ('both', 'aligned_transfer', 'minimum_margin'):
        for history in HISTORIES:
            for injury in INJURIES:
                def score(arm): return values[f'fresh/{metric}/{history}/{arm}/{injury}']
                effects = dict(early=score('pulse_early')-score('sham_early'),
                    late=score('pulse_late')-score('sham_late'),
                    protected=score('protected_pulse')-score('protected_sham'))
                effects['interaction'] = effects['late']-effects['early']
                for key, v in effects.items(): values[f'fresh_effect/{metric}/{history}/{key}/{injury}'] = v
            for t in TIMES:
                values[f'body_effect/{metric}/{history}/{t}'] = (
                    values[f'body/{metric}/{history}/pulse/{t}']-values[f'body/{metric}/{history}/sham/{t}'])
            values[f'body_effect/{metric}/{history}/interaction'] = (
                values[f'body_effect/{metric}/{history}/late']-values[f'body_effect/{metric}/{history}/early'])
        for history in HISTORIES[1:]:
            for injury in INJURIES:
                for key in ('early', 'late', 'interaction'):
                    values[f'history_interaction/{metric}/{history}/{key}/{injury}'] = (
                        values[f'fresh_effect/{metric}/{history}/{key}/{injury}']-
                        values[f'fresh_effect/{metric}/acquired/{key}/{injury}'])
    for h, history in enumerate(HISTORIES):
        for a, arm in enumerate(ARMS):
            for metric in ('shared_support', 'sign_disagreements', 'support_gained', 'support_lost', 'coupling_l1', 'denominator_l1'):
                values[f'record/{metric}/{history}/{arm}'] = np.array([c[metric][h, a].mean() for c in cases])
            for g, field in enumerate(GRAPH_FIELDS):
                values[f'graph/{field}/{history}/{arm}'] = np.array([c['graph'][h, a, ..., g].mean() for c in cases])
            if a < 4:
                values[f'record/fallback/{history}/{arm}'] = np.array([c['fallback_count'][h, a].mean() for c in cases])
        for t, name in enumerate(TIMES):
            values[f'body_distance/{history}/{name}'] = np.array([c['body_state_distance'][h, t].mean() for c in cases])
        for metric in ('requested_squared', 'delivered_squared', 'clipping_count'):
            values[f'pulse/{metric}/{history}'] = np.array([c['pulse_'+metric][h].mean() for c in cases])
    return values


def check_summary(summary, cases, controls, mode):
    v = independent_values(cases); s = summary['statistics']; assert set(s) == set(v)
    draws = random('E055', 'bootstrap', 'capture').integers(0, len(cases), (10000, len(cases)))
    for key, x in v.items():
        expected = dict(mean=float(x.mean()), interval=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(),
                        confidence=.95, block_means=x.tolist())
        for field in expected:
            np.testing.assert_allclose(expected[field], s[key][field], rtol=1e-13, atol=1e-13)
    ok = all(c['pass'] for c in controls); enabled = mode == 'scientific' and ok
    assert summary['controls_pass'] == ok and summary['controls_by_block'] == controls
    assert summary['primary_history'] == 'independent_rewrite' and summary['primary_injury'] == 'scattered'
    assert summary['independent_blocks'] == len(cases) and summary['cohort_reused']
    b = lambda k: s[k]['interval']
    prefix = 'fresh_effect/both/independent_rewrite/'
    p = dict(early_transferred_loss_exceeds_five=b(prefix+'early/scattered')[1] < -.05,
        delay_interaction_exceeds_five=b(prefix+'interaction/scattered')[0] > .05,
        late_loss_bounded_within_five=b(prefix+'late/scattered')[0] > -.05,
        late_fresh_success_above_75=b('fresh/both/independent_rewrite/pulse_late/scattered')[0] > .75)
    body = dict(early_body_loss_exceeds_five=b('body_effect/both/independent_rewrite/early')[1] < -.05,
        late_body_loss_bounded_within_five=b('body_effect/both/independent_rewrite/late')[0] > -.05,
        late_body_success_above_75=b('body/both/independent_rewrite/pulse/late')[0] > .75)
    p = {k: bool(x) if enabled else None for k, x in p.items()}
    body = {k: bool(x) if enabled else None for k, x in body.items()}
    assert summary['primary_gates'] == p and summary['body_recovery_gates'] == body
    decision = all(p.values()) if enabled else None
    assert summary['transfer_protection'] == decision
    assert summary['joint_body_and_transfer_recovery'] == (decision and all(body.values()) if enabled else None)
    expected_status = ('TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else
                       'TRANSFER_PROTECTION_ESTABLISHED' if decision else 'TRANSFER_PROTECTION_NOT_ESTABLISHED')
    assert summary['status'] == expected_status
    return len(v)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--workers', type=int, default=1); p.add_argument('--worker', type=int)
    a = p.parse_args(); assert 1 <= a.workers <= 8; cap_cpus(a.workers)
    run = HERE/'runs'/NAMES[a.mode]; cfg = settings(a.mode)
    if a.worker is not None:
        assert a.worker in cfg['blocks']; worker(run, a.worker, cfg); return
    started = time.monotonic(); m = verify(run)
    assert m['contract']['blocks'] == cfg['blocks']
    assert not (run/'INDEPENDENT_AUDIT.json').exists()
    def launch(b):
        with (run/f'audit_worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'audit.py'), '--mode', a.mode,
                '--workers', str(a.workers), '--worker', str(b)], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for b in pool.map(launch, cfg['blocks']): print('Independently replayed block', b, flush=True)
    controls = [json.loads((run/f'audit_worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
    summary = json.loads((run/'summary.json').read_text())
    checked = check_summary(summary, [load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']], controls, a.mode)
    verify(run)
    dump(run/'INDEPENDENT_AUDIT.json', dict(status='PASS', utc=utc(), seconds=time.monotonic()-started,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), summaries_checked=checked,
        all_sources_pulses_states_writes_assays_diagnostics_replayed=True, every_step_state_hashes_replayed=True,
        worker_seconds=[json.loads((run/f'audit_worker_{b}.json').read_text())['seconds'] for b in cfg['blocks']],
        controls_pass=summary['controls_pass'], transfer_protection=summary['transfer_protection'],
        terminal_cue_observations=len(cfg['blocks'])*21*4*cfg['recipients']*2*3,
        body_boundary_cue_observations=len(cfg['blocks'])*3*2*4*cfg['recipients']*2*3))


if __name__ == '__main__': main()
