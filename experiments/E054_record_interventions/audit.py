"""Independent replay of every case and block-bootstrap summary."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, dump, utc
from E015_functional_inheritance.audit import verify, sha, random
from E054_record_interventions import audit_model as audit
from E054_record_interventions.data import load, receipt
from E054_record_interventions.plan import HERE, ROOT, ARMS, HISTORIES, INJURIES, NAMES, settings
import numpy as np


def independent_diagnostics(inter, raw):
    H, A, F, R = inter['weights'].shape[:4]
    k = raw['coupling'].reshape(H, A, F, R, 3, 4, 16, 16)
    d = raw['denominator'].reshape(H, A, F, R, 3, 16, 16)
    aligned = k.copy(); s = inter['cell_signs']
    for y, x in np.ndindex(16, 16):
        for direction, (ny, nx) in enumerate(((y, (x+1)%16), (y, (x-1)%16), ((y+1)%16, x), ((y-1)%16, x))):
            aligned[:, 4, :, :, :, direction, y, x] *= (s[..., y, x]*s[..., ny, nx])[..., None]
    ports = raw['mean_ports'].reshape(H, A, F, R, 2, 3, 2)
    end = raw['end'].reshape(H, A, F, R, 2, 3, 16, 16)
    graph = raw['graph_after'].reshape(H, A, F, R, 3, 7)
    c = dict(scale_k_error=float(np.max(np.abs(k[:, 1]-k[:, 0]))),
        switch_aligned_k_error=float(np.max(np.abs(aligned[:, 4]-k[:, 0]))),
        scale_output_error=float(np.max(np.abs(ports[:, 1]-ports[:, 0]))),
        switch_output_error=float(np.max(np.abs(ports[:, 4]-ports[:, 0]))),
        restoration_exact=bool(np.array_equal(end[:, 0], end[:, 7])),
        cycle_parity_preserved=bool(np.array_equal(inter['graph_before'][:, 0], inter['graph_before'][:, 4]) and np.array_equal(graph[:, 0], graph[:, 4])),
        scale_support_preserved=bool(np.array_equal(inter['weights'][:, 0] != 0, inter['weights'][:, 1] != 0)))
    c['pass'] = bool(c['restoration_exact'] and c['cycle_parity_preserved'] and c['scale_support_preserved'] and
        max(c['scale_k_error'], c['switch_aligned_k_error']) <= 1e-12 and max(c['scale_output_error'], c['switch_output_error']) <= 1e-8)
    values = dict(coupling_l1=np.abs(k-k[:, :1]).sum(axis=(-3, -2, -1))/256,
        aligned_coupling_l1=np.abs(aligned-k[:, :1]).sum(axis=(-3, -2, -1))/256,
        denominator_l1=np.abs(d-d[:, :1]).sum(axis=(-2, -1))/256)
    return values, c


def worker(run, b, cfg):
    started = time.monotonic(); src_run, entry = receipt(cfg['mode'])
    for name in (f'source_{b:06d}.npz', f'boundary_{b:06d}_g31.npz', f'boundary_{b:06d}_g32.npz'):
        assert sha(src_run/name) == entry['files'][name]
    original = audit.source(src_run, b); saved = load(run/f'source_{b:06d}.npz')
    for k, x in original.items(): audit.equal(x, saved[k])
    inter = load(run/f'interventions_{b:06d}.npz')
    audit.interventions(inter, **original, block=b)
    replay = audit.replay(inter, b, cfg); actual = load(run/f'assay_{b:06d}.npz')
    assert set(replay) == set(actual)
    for k, x in replay.items(): audit.equal(x, actual[k])
    measures, controls = independent_diagnostics(inter, replay)
    expected = dict(**audit.scores(replay), **measures, exposure=inter['exposure'],
                    graph_before=inter['graph_before'], graph_after=replay['graph_after'])
    cases = load(run/f'cases_{b:06d}.npz'); assert set(cases) == set(expected)
    for k, x in expected.items(): audit.equal(x, cases[k])
    assert controls == json.loads((run/f'worker_{b}.json').read_text())['controls']
    dump(run/f'audit_worker_{b}.json', dict(block=b, seconds=time.monotonic()-started, controls=controls, status='PASS'))


def independent_values(cases):
    out = {}
    for metric in ('both', 'transfer', 'aligned_transfer', 'coupling_l1', 'aligned_coupling_l1', 'denominator_l1', 'margin'):
        for h, history in enumerate(HISTORIES):
            for a, arm in enumerate(ARMS):
                for j, injury in enumerate(INJURIES):
                    out[f'{metric}/{history}/{arm}/{injury}'] = np.array([c[metric][h, a, ..., j].mean() for c in cases])
    for metric in ('both', 'aligned_transfer'):
        for history in HISTORIES:
            for injury in INJURIES:
                get = lambda arm:out[f'{metric}/{history}/{arm}/{injury}']
                for arm in ARMS[1:]: out[f'effect/{metric}/{history}/{arm}/{injury}'] = get(arm)-get('untouched')
                out[f'sign_contrast/{metric}/{history}/{injury}'] = get('sign_isolated')-get('sign_switch')
                if history != 'acquired': out[f'repair_contrast/{metric}/{history}/{injury}'] = get('delete_returning')-get('delete_other')
        for pairing in ('paired', 'independent'):
            for arm in ARMS[1:]:
                for injury in INJURIES:
                    out[f'policy_interaction/{metric}/{pairing}/{arm}/{injury}'] = (
                        out[f'effect/{metric}/{pairing}_rewrite/{arm}/{injury}']-out[f'effect/{metric}/{pairing}_preserve/{arm}/{injury}'])
    for a, reference in (('magnitude_permute', 'untouched'), ('sign_isolated', 'sign_switch'), ('delete_isolated', 'untouched')):
        out['primary/'+a] = out[f'both/paired_rewrite/{a}/scattered']-out[f'both/paired_rewrite/{reference}/scattered']
    return out


def check_summary(summary, cases, controls, mode):
    vals = independent_values(cases); assert set(vals) == set(summary['statistics'])
    samples = random('E054', 'bootstrap', 'record_interventions').integers(0, len(cases), (10000, len(cases)))
    for name, x in vals.items():
        s = summary['statistics'][name]; alpha = 1/120 if name.startswith('primary/') else .025
        np.testing.assert_allclose(s['block_means'], x, rtol=1e-13, atol=1e-13)
        np.testing.assert_allclose(s['mean'], x.mean(), rtol=1e-13, atol=1e-13)
        np.testing.assert_allclose(s['interval'], np.quantile(x[samples].mean(axis=1), [alpha, 1-alpha]), rtol=1e-13, atol=1e-13)
        assert s['confidence'] == 1-2*alpha
    ok = all(x['pass'] for x in controls)
    assert summary['controls_by_block'] == controls and summary['controls_pass'] == ok
    assert summary['cohort_reused'] and summary['independent_blocks'] == len(cases)
    assert summary['status'] == ('TECHNICAL_ONLY' if mode != 'scientific' else 'MECHANISTIC_FOLLOWUP' if ok else 'NUMERICAL_CONTROL_FAILURE')
    assert set(summary['primary_classifications']) == {'magnitude_permute', 'sign_isolated', 'delete_isolated'}
    for arm, value in summary['primary_classifications'].items():
        lo, hi = summary['statistics']['primary/'+arm]['interval']
        expected = None if mode != 'scientific' or not ok else 'LOSS_EXCEEDS_FIVE_POINTS' if hi < -.05 else 'LOSS_BOUNDED_WITHIN_FIVE_POINTS' if lo > -.05 else 'UNRESOLVED'
        assert value == expected
    return len(vals)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--workers', type=int, default=1); p.add_argument('--worker', type=int)
    a = p.parse_args(); assert 1 <= a.workers <= 8; cap_cpus(a.workers)
    run = HERE/'runs'/NAMES[a.mode]; cfg = settings(a.mode)
    if a.worker is not None:
        assert a.worker in cfg['blocks']; worker(run, a.worker, cfg); return
    started = time.monotonic(); manifest = verify(run)
    assert manifest['contract']['blocks'] == cfg['blocks']
    assert not (run/'INDEPENDENT_AUDIT.json').exists()
    def launch(b):
        with (run/f'audit_worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'audit.py'), '--mode', a.mode, '--worker', str(b),
                            '--workers', str(a.workers)], cwd=ROOT, stdin=subprocess.DEVNULL,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for b in pool.map(launch, cfg['blocks']): print('Independently replayed block', b, flush=True)
    controls = [json.loads((run/f'audit_worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
    summary = json.loads((run/'summary.json').read_text())
    n = check_summary(summary, [load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']], controls, a.mode)
    verify(run)
    dump(run/'INDEPENDENT_AUDIT.json', dict(status='PASS', utc=utc(), seconds=time.monotonic()-started,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), summaries_checked=n,
        all_source_interventions_graphs_couplings_trajectories_scores_replayed=True,
        worker_seconds=[json.loads((run/f'audit_worker_{b}.json').read_text())['seconds'] for b in cfg['blocks']],
        controls_pass=summary['controls_pass'], terminal_cue_observations=len(cfg['blocks'])*55*4*cfg['recipients']*2*3))


if __name__ == '__main__': main()
