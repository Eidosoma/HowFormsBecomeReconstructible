"""All-case packet intervention with fixed capture and copying alternatives."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, rng, sha, utc
from E015_functional_inheritance.audit import verify
from E035_cue_selective_capture import model
import numpy as np


def input_paths():
    names = ('common.py', 'run_python.sh', 'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E023_receiver_compensation/model.py', 'E023_receiver_compensation/audit.py',
        'E024_serial_compensation/model.py', 'E031_renewal_durability/model.py',
        'E031_renewal_durability/audit.py', 'E031_renewal_durability/evidence.py',
        'E034_settled_rebuilding/model.py', 'E034_settled_rebuilding/audit.py')
    return [ROOT/p for p in names]+[HERE/p for p in ('model.py', 'run.py', 'audit.py', 'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def load(path):
    with np.load(path, allow_pickle=False) as h:
        return {k:h[k] for k in h.files}


def source_config(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items():
        assert sha(ROOT/rel) == digest, rel
    source = ROOT/index[dict(fixture='fixture_run', benchmark='benchmark_run', scientific='source_run')[mode]]
    contract = verify(source)['contract']
    parent = ROOT/contract['source']; parent_contract = verify(parent)['contract']
    assert contract['config'] == parent_contract['config'] and contract['cycle'] == parent_contract['cycle']
    ids = contract['blocks']
    assert ids == (list(range(27000, 27032)) if mode == 'scientific' else [900031])
    assert contract['generation'] == 9 and contract['factor'] == (2 if mode == 'fixture' else 4)
    return source, parent, ids, model.base.Config(**contract['config']), model.Cycle(**contract['cycle']), contract['factor']


def save_block(output, source, parent, block, cfg, cycle, factor):
    started = time.monotonic(); cap_cpus(8)
    incoming = load(parent/f'boundary_{block:06d}_g8.npz')['outgoing'][0]
    data, body_ports = model.reconstruct(incoming, block, cfg, cycle, factor, load(source/f'boundary_{block:06d}.npz'))
    np.savez_compressed(output/f'construction_{block:06d}.npz', **data)
    bc, bm, bv = model.history.body_score(body_ports, cfg)
    old_cases = load(source/f'cases_{block:06d}.npz')
    for key, value in (('body_correct', bc), ('body_margin', bm), ('body_ports', bv)):
        np.testing.assert_array_equal(value, old_cases[key])
    raw = model.assay(data['records'], block, cfg, model.terminal_cycle(cycle, factor))
    model.check_baseline(raw, load(source/f'assay_{block:06d}_t1.npz'))
    model.evidence.save(output/f'assay_{block:06d}.npz', raw, 'assay')
    c, m, v = model.score(raw['late_ports'].mean(axis=0), cfg)
    np.savez_compressed(output/f'cases_{block:06d}.npz', correct=c, margin=m, ports=v,
                        body_correct=bc, body_margin=bm, body_ports=bv)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        all_source_boundary_commitments_match=True, baseline_endpoints_match_e034=True))


def statistics(x):
    x = np.asarray(x, float)
    draw = rng('E035', 'bootstrap', 'cue_selective_capture').integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draw].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def primary_values(both):
    assert both.shape[1:] == (12, 3, 7)
    hi = model.PANELS.index(('local_strength', 'contrast_rewrite'))
    lo = model.PANELS.index(('local_strength', 'standard_preserve'))
    return both[:, hi, 1, 0]-both[:, lo, 1, 0]


def analyze(output, ids, cfg, cycle, factor, mode):
    data = [load(output/f'cases_{b:06d}.npz') for b in ids]
    correct = np.stack([d['correct'] for d in data]); margin = np.stack([d['margin'] for d in data])
    arrays = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    groups = {}
    for i, (receiver, condition) in enumerate(model.PANELS):
        g = {metric:{d:{arm:statistics(x[:, i, j, a]) for a, arm in enumerate(model.ARMS)}
                     for j, d in enumerate(model.DAMAGE)} for metric, x in arrays.items()}
        g['own_accuracy_by_rule'] = {str(rule):{d:statistics(correct[:, i][:, [f, f+2]][:, :, :, :, j, 0].mean(axis=(1, 2, 3)))
            for j, d in enumerate(model.DAMAGE)} for f, rule in enumerate((1, -1))}
        g['own_minus_control'] = {d:{a:statistics(arrays['accuracy'][:, i, j, 0]-arrays['accuracy'][:, i, j, k])
            for k, a in enumerate(model.ARMS) if k} for j, d in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{d}':g['own_accuracy_by_rule'][str(rule)][d]['ci95'][0] > .75 for rule in (1, -1) for d in model.DAMAGE}
        gates.update({f'advantage_{d}_{a}':g['own_minus_control'][d][a]['ci95'][0] > .10 for d in model.DAMAGE for a in model.ARMS[1:]})
        g.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(receiver, {})[condition] = g
    contrasts, interactions = {}, {}
    for r in model.RECEIVERS:
        contrasts[r] = {}
        for hi, lo in model.PAIRS:
            a, b = model.PANELS.index((r, hi)), model.PANELS.index((r, lo))
            contrasts[r][hi+'_minus_'+lo] = {m:{d:statistics(x[:, a, j, 0]-x[:, b, j, 0])
                for j, d in enumerate(model.DAMAGE)} for m, x in arrays.items()}
        a, b, c, d = [model.PANELS.index((r, name)) for name in ('contrast_rewrite', 'standard_rewrite', 'contrast_preserve', 'standard_preserve')]
        interactions[r] = {m:{injury:statistics((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]))
                             for j, injury in enumerate(model.DAMAGE)} for m, x in arrays.items()}
    primary = statistics(primary_values(arrays['both_cues']))
    technical = mode != 'scientific'; passed = primary['ci95'][0] > .05
    absolute = groups['local_strength']['contrast_rewrite']['both_cues']['scattered']['own']['ci95'][0] > .75
    matched_flags = {c:None if technical else contrasts['local_strength'][f'matched_{c}_minus_standard_{c}']['both_cues']['scattered']['ci95'][0] > 0
                     for c in ('preserve', 'rewrite')}
    body = np.stack([d['body_correct'] for d in data])
    s = dict(experiment='E035', mode=mode,
        status='TECHNICAL_ONLY' if technical else 'CUE_SELECTIVE_CAPTURE_BENEFIT_ESTABLISHED' if passed else 'CUE_SELECTIVE_CAPTURE_BENEFIT_NOT_ESTABLISHED',
        blocks=ids, lineages=len(ids)*4*cfg.recipients, cfg=asdict(cfg), base_cycle=asdict(cycle), generation=9,
        terminal_cycle=asdict(model.terminal_cycle(cycle, factor)), panels=model.PANELS,
        conditions=model.CONDITIONS, receivers=model.RECEIVERS, arms=model.ARMS, damage=model.DAMAGE,
        groups=groups, contrasts=contrasts, interaction=interactions,
        prior_cases_reused=True, source_bodies_changed=False, new_serial_history=False,
        all_source_boundary_commitments_match=True, baseline_endpoints_match_e034=True,
        matched_magnitudes_support_and_denominators_verified=True,
        individual_observations=int(correct.size), source_body_observations_replayed=int(body.size),
        primary=dict(endpoint='h9 normalized scattered own both-cue success: contrast_rewrite minus standard_preserve',
                     margin=.05, statistics=primary, lower_above_005=None if technical else passed),
        absolute_reliability_lower_above_075=None if technical else absolute,
        matched_sign_control_lower_above_zero=matched_flags,
        interval_scope='One primary; all secondary intervals and gates pointwise')
    dump(output/'summary.json', s)
    def fmt(x):
        return f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E035 cue-sensitive capture and strong-copy release', '', '**'+s['status']+'**', '',
        f'{len(ids)} existing E034 blocks; {s["lineages"]} lineages; same delayed-renewal bodies and terminal timing.', '',
        'Primary contrast_rewrite minus standard_preserve: **'+fmt(primary)+' percentage points**.', '',
        '| Reader | Construction | Intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- |']
    for r, c in model.PANELS:
        g = groups[r][c]
        lines.append(f'| {r} | {c} | '+' | '.join(fmt(g['both_cues'][d]['own']) for d in model.DAMAGE)+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', 'Matched-sign control minus standard, normalized scattered both-cue success:']
    for c in ('preserve', 'rewrite'):
        lines.append('- '+c+': '+fmt(contrasts['local_strength'][f'matched_{c}_minus_standard_{c}']['both_cues']['scattered'])+' points.')
    lines += ['', 'Existing-cohort packet intervention, not new serial maintenance or fresh replication. The primary lower bound must exceed five points; absolute reliability is separate. Matched controls keep absolute weights and receiving denominators exact, using standard signs for zero contrast. Secondary contrasts are pointwise; a favorable alternative cannot replace the primary.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return s


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('fixture', 'benchmark', 'scientific'), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    a = p.parse_args(); cap_cpus(8); assert 1 <= a.workers <= 8
    output = HERE/'runs'/dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='capture_v1')[a.mode]
    if a.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']; assert a.worker in c['blocks']
        save_block(output, ROOT/c['source'], ROOT/c['parent_source'], a.worker,
                   model.base.Config(**c['config']), model.Cycle(**c['cycle']), c['factor']); return
    source, parent, ids, cfg, cycle, factor = source_config(a.mode)
    started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E035', mode=a.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        factor=factor, source=str(source.relative_to(ROOT)), parent_source=str(parent.relative_to(ROOT)),
        workers=a.workers, generation=9, panels=model.PANELS))
    def launch(block):
        with (output/f'worker_{block}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(block)],
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return block
    try:
        with ThreadPoolExecutor(max_workers=min(a.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]):
                print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, factor, a.mode)
        finish(output, started, dict(experiment='E035', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__':
    main()
