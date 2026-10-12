"""Append-only fresh cohort, full serial evidence and fixed inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from functools import lru_cache
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
from E041_full_rewrite_confirmation import model, evidence
import numpy as np

BLOCKS, FIXTURE = tuple(range(32000, 32032)), 900041


def input_paths():
    names = ('common.py', 'run_python.sh', 'SOURCE_SNAPSHOT.json', 'SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E023_receiver_compensation/model.py', 'E023_receiver_compensation/audit.py',
        'E024_serial_compensation/model.py', 'E031_renewal_durability/model.py',
        'E031_renewal_durability/audit.py', 'E031_renewal_durability/evidence.py',
        'E034_settled_rebuilding/model.py', 'E035_cue_selective_capture/model.py',
        'E040_weak_bridge_durability/model.py')
    return [ROOT/p for p in names]+[HERE/p for p in ('model.py', 'evidence.py', 'run.py', 'audit.py',
        'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def load(path):
    with np.load(path, allow_pickle=False) as h:
        return {k:h[k] for k in h.files}


def configuration(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items():
        assert sha(ROOT/rel) == digest, rel
    cfg, cycle = model.CFG, model.CYCLE
    if mode == 'fixture':
        cfg = replace(cfg, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cycle = replace(cycle, read_steps=24, settling_steps=3, write_steps=8)
    elif mode == 'benchmark':
        cfg = replace(cfg, recipients=1)
        cycle = replace(cycle, read_steps=128, settling_steps=16)
    else:
        assert mode == 'scientific'
    return list(BLOCKS) if mode == 'scientific' else [FIXTURE], cfg, cycle


def save_block(output, block, cfg, cycle):
    started = time.monotonic(); cap_cpus(8)
    source = model.acquisition.teach(block, cfg)
    evidence.save_source(output/f'source_{block:06d}.npz', source)
    records = np.repeat(source['acquired'][1, :, None], cfg.recipients, axis=1)
    incoming = np.repeat(records[None], len(model.CONDITIONS), axis=0)
    scores, margins, ports, bodies, body_margins, body_ports = [], [], [], [], [], []
    def assay(h, packets):
        raw = model.assay(packets, block, h, cfg, cycle)
        evidence.save(output/f'assay_{block:06d}_h{h}.npz', raw, 'assay')
        c, m, v = evidence.score_mean(raw['late_ports'].mean(axis=0), cfg, model.RULES, model.CUES)
        scores.append(c); margins.append(m); ports.append(v)
    assay(0, records[None])
    for g in range(1, 33):
        raw = model.replace_record(incoming, block, g, cfg, cycle)
        evidence.save(output/f'boundary_{block:06d}_g{g}.npz', raw, 'boundary')
        incoming = raw['outgoing'].copy()
        c, m, v = model.body_score(raw['developed_late_ports'].mean(axis=0), cfg)
        bodies.append(c); body_margins.append(m); body_ports.append(v)
        del raw
        if g in model.HORIZONS: assay(g, incoming)
    np.savez_compressed(output/f'cases_{block:06d}.npz', correct=np.concatenate(scores),
        margin=np.concatenate(margins), ports=np.concatenate(ports), body_correct=np.stack(bodies),
        body_margin=np.stack(body_margins), body_ports=np.stack(body_ports))
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        generations=32, terminal_panels=134, source_sha256=sha(output/f'source_{block:06d}.npz')))


@lru_cache(None)
def draws(n):
    return rng('E041', 'bootstrap', 'full_rewrite_confirmation').integers(0, n, (10000, n))


def statistics(x):
    x = np.asarray(x, float); assert x.ndim == 1 and np.isfinite(x).all()
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws(len(x))].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def primary_values(both):
    assert both.shape[1:] == (134, 3, 7)
    a = model.PANELS.index((32, 'bridge_rewrite', 'local_strength'))
    b = model.PANELS.index((32, 'bridge_preserve', 'local_strength'))
    return both[:, a, 1, 0]-both[:, b, 1, 0]


def durability_requirements(groups, contrasts):
    gates = {}
    for h in (8, 16, 24, 32):
        candidate = groups[str(h)]['local_strength']['bridge_rewrite']
        for damage in ('intact', 'scattered'):
            gates[f'h{h}_{damage}_both_cue_lower_above_075'] = candidate['both_cues'][damage]['own']['ci95'][0] > .75
        gates[f'h{h}_original_24_gates'] = candidate['all_original_gates_pass']
    for h in (16, 32):
        for control in ('bridge_rewrite_read_blocked', 'bridge_rewrite_write_blocked'):
            gates[f'h{h}_above_{control}_by_010'] = contrasts[str(h)]['local_strength']['bridge_rewrite_minus_'+control]['both_cues']['scattered']['ci95'][0] > .10
    gates['initial_normalized_original_24_gates'] = groups['0']['local_strength']['initial']['all_original_gates_pass']
    assert len(gates) == 17
    return gates


def decisions(primary, gates, technical):
    assert len(gates) == 17
    passed, durable = primary['ci95'][0] > .05, all(gates.values())
    return dict(primary=dict(endpoint='h32 normalized scattered own both-cue success: bridge_rewrite minus bridge_preserve',
            margin=.05, statistics=primary, lower_above_005=None if technical else passed),
        primary_status='TECHNICAL_ONLY' if technical else 'REWRITING_BENEFIT_ESTABLISHED' if passed else 'REWRITING_BENEFIT_NOT_ESTABLISHED',
        durability_requirements=gates, full_durability_qualified=None if technical else durable,
        durability_status='TECHNICAL_ONLY' if technical else 'DURABLE_THROUGH_32_RENEWALS' if durable else 'DURABILITY_NOT_ESTABLISHED',
        full_qualification=None if technical else passed and durable,
        status='TECHNICAL_ONLY' if technical else 'FULL_REWRITING_QUALIFIED' if passed and durable else 'FULL_REWRITING_NOT_QUALIFIED')


def analyze(output, ids, cfg, cycle, mode):
    data = [load(output/f'cases_{b:06d}.npz') for b in ids]
    correct = np.stack([d['correct'] for d in data]); margin = np.stack([d['margin'] for d in data])
    arrays = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    groups = {}
    for i, (h, condition, receiver) in enumerate(model.PANELS):
        g = {metric:{d:{arm:statistics(x[:, i, j, a]) for a, arm in enumerate(model.ARMS)}
                     for j, d in enumerate(model.DAMAGE)} for metric, x in arrays.items()}
        g['own_accuracy_by_rule'] = {str(rule):{d:statistics(correct[:, i][:, [f, f+2]][:, :, :, :, j, 0].mean(axis=(1, 2, 3)))
            for j, d in enumerate(model.DAMAGE)} for f, rule in enumerate((1, -1))}
        g['own_minus_control'] = {d:{a:statistics(arrays['accuracy'][:, i, j, 0]-arrays['accuracy'][:, i, j, k])
            for k, a in enumerate(model.ARMS) if k} for j, d in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{d}':g['own_accuracy_by_rule'][str(rule)][d]['ci95'][0] > .75 for rule in (1, -1) for d in model.DAMAGE}
        gates.update({f'advantage_{d}_{a}':g['own_minus_control'][d][a]['ci95'][0] > .10 for d in model.DAMAGE for a in model.ARMS[1:]})
        g.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(str(h), {}).setdefault(receiver, {})[condition] = g
    contrasts, interactions, changes = {}, {}, {}
    for h in model.HORIZONS[1:]:
        contrasts[str(h)], interactions[str(h)], changes[str(h)] = {}, {}, {}
        for r in model.RECEIVERS:
            contrasts[str(h)][r] = {}; changes[str(h)][r] = {}
            for hi, lo in model.PAIRS:
                a, b = model.PANELS.index((h, hi, r)), model.PANELS.index((h, lo, r))
                contrasts[str(h)][r][hi+'_minus_'+lo] = {m:{d:statistics(x[:, a, j, 0]-x[:, b, j, 0])
                    for j, d in enumerate(model.DAMAGE)} for m, x in arrays.items()}
            a, b, c, d = [model.PANELS.index((h, name, r)) for name in ('bridge_rewrite', 'standard_rewrite', 'bridge_preserve', 'standard_preserve')]
            interactions[str(h)][r] = {m:{injury:statistics((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]))
                for j, injury in enumerate(model.DAMAGE)} for m, x in arrays.items()}
            for name in model.CONDITIONS:
                a, b = model.PANELS.index((h, name, r)), model.PANELS.index((1, name, r))
                changes[str(h)][r][name] = {m:{d:statistics(x[:, a, j, 0]-x[:, b, j, 0]) for j, d in enumerate(model.DAMAGE)}
                                            for m, x in arrays.items()}
    body_c = np.stack([d['body_correct'] for d in data]); body_m = np.stack([d['body_margin'] for d in data])
    bvalues = dict(accuracy=body_c.mean(axis=(3, 4, 5)), both_cues=body_c.all(axis=5).mean(axis=(3, 4)), margin=body_m.mean(axis=(3, 4, 5)))
    body = {str(g+1):{model.CONDITIONS[n]:{m:statistics(x[:, g, j]) for m, x in bvalues.items()} for j, n in enumerate(model.ACTIVE)} for g in range(32)}
    gates = durability_requirements(groups, contrasts)
    primary = statistics(primary_values(arrays['both_cues']))
    technical = mode != 'scientific'
    decision = decisions(primary, gates, technical)
    rescue = contrasts['32']['local_strength']['bridge_preserve_minus_contrast_preserve']['both_cues']['scattered']
    summary = dict(experiment='E041', mode=mode, blocks=ids, founders=4*len(ids), lineages=len(ids)*4*cfg.recipients,
        cfg=asdict(cfg), cycle=asdict(cycle), terminal_cycle=asdict(model.terminal_cycle(cycle)),
        panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS, arms=model.ARMS, damage=model.DAMAGE,
        groups=groups, contrasts=contrasts, interaction=interactions, changes_from_h1=changes, body_reading=body,
        prior_cases_pooled=False, independent_serial_histories=True, setting_selected=None, source_capture_states_require_replay=True,
        individual_observations=int(correct.size), body_individual_observations=int(body_c.size),
        model_change_scope='E040 nine policies plus two matched bridge-rewrite ablations',
        active_conditions=[model.CONDITIONS[n] for n in model.ACTIVE],
        repair_rescue=dict(endpoint='h32 bridge_preserve minus contrast_preserve', statistics=rescue,
            lower_above_010=None if technical else rescue['ci95'][0] > .10, scope='prespecified secondary'),
        interval_scope='One relative primary plus separate absolute durability; full qualification requires both; all intervals and component gates pointwise',
        **decision)
    dump(output/'summary.json', summary)
    def fmt(st): return f"{100*st['mean']:.2f} [{100*st['ci95'][0]:.2f}, {100*st['ci95'][1]:.2f}]"
    lines = ['# E041 full rewriting through 32 damaged rebuilds', '', '**'+summary['status']+'**', '',
        '**Durability: '+summary['durability_status']+'**', '',
        '**Relative benefit: '+summary['primary_status']+'**', '',
        f'{len(ids)} blocks, {summary["lineages"]} lineages; thirty-two damaged replacements.', '',
        'Primary h32 gain: **'+fmt(primary)+' percentage points**; lower bound must exceed five.', '',
        'Full qualification requires this relative gain and all seventeen durability requirements.', '',
        '| Generation | Policy | Normalized intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- |']
    for h in model.HORIZONS:
        for c, g in groups[str(h)]['local_strength'].items():
            lines.append(f'| {h} | {c} | '+' | '.join(fmt(g['both_cues'][d]['own']) for d in model.DAMAGE)+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', 'Prespecified secondary repair rescue versus pure contrast: **'+fmt(rescue)+' percentage points**.',
        'Secondary lower bound above ten points: '+str(summary['repair_rescue']['lower_above_010'])+'.',
        '', 'Durability requirements:']+[f'- {k}: {v}' for k, v in gates.items()]
    lines += ['', 'Fresh independent histories; no earlier cases pooled. Full bridge rewriting is the frozen candidate, with matched reading-blocked and writing-blocked controls. E040 results motivated this fresh test; prior conclusions remain unchanged. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. Durability is required at h8/h16/h24/h32; this does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('fixture', 'benchmark', 'scientific'), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    a = p.parse_args(); cap_cpus(8); assert 1 <= a.workers <= 8
    output = HERE/'runs'/dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='serial_v1')[a.mode]
    if a.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']; assert a.worker in c['blocks']
        save_block(output, a.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle'])); return
    ids, cfg, cycle = configuration(a.mode); started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E041', mode=a.mode, blocks=ids, config=asdict(cfg),
        cycle=asdict(cycle), workers=a.workers, panels=model.PANELS, generations=32))
    def launch(block):
        with (output/f'worker_{block}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(block)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return block
    try:
        with ThreadPoolExecutor(max_workers=min(a.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]):
                print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, a.mode)
        finish(output, started, dict(experiment='E041', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
