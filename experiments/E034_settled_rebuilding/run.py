"""One matched rebuilding boundary on every saved E031 h8 candidate packet."""
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
from E034_settled_rebuilding import model
import numpy as np


def input_paths():
    names = ('common.py', 'run_python.sh', 'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E023_receiver_compensation/model.py', 'E023_receiver_compensation/audit.py',
        'E024_serial_compensation/model.py', 'E031_renewal_durability/model.py',
        'E031_renewal_durability/audit.py', 'E031_renewal_durability/evidence.py')
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
    ids = contract['blocks']
    assert ids == (list(range(27000, 27032)) if mode == 'scientific' else [900031])
    assert contract['conditions'][0] == 'maturing'
    return source, ids, model.base.Config(**contract['config']), model.Cycle(**contract['cycle'])


def save_block(output, source, block, cfg, cycle, factor):
    started = time.monotonic()
    cap_cpus(8)
    incoming = load(source/f'boundary_{block:06d}_g8.npz')['outgoing'][0]
    raw = model.boundary(incoming, block, cfg, cycle, factor)
    model.check_original(raw, load(source/f'boundary_{block:06d}_g9.npz'))
    model.evidence.save(output/f'boundary_{block:06d}.npz', raw, 'boundary')
    bc, bm, bv = model.body_score(raw['developed_late_ports'].mean(axis=0), cfg)
    cs, ms, vs = [], [], []
    for i, clock in enumerate(model.schedules(cycle, factor)):
        measured = model.assay(raw['outgoing'], block, cfg, clock)
        model.evidence.save(output/f'assay_{block:06d}_t{i}.npz', measured, 'assay')
        c, m, v = model.score(measured['late_ports'].mean(axis=0), cfg)
        cs.append(c); ms.append(m); vs.append(v)
    np.savez_compressed(output/f'cases_{block:06d}.npz', correct=np.concatenate(cs), margin=np.concatenate(ms),
                        ports=np.concatenate(vs), body_correct=bc, body_margin=bm, body_ports=bv)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started, original_boundary_matches_e031=True))


def statistics(x):
    x = np.asarray(x, float)
    draw = rng('E034', 'bootstrap', 'settled_rebuilding').integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draw].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def primary_values(both):
    assert both.shape[1:] == (8, 3, 7)
    a = model.PANELS.index(('delayed', 'local_strength', 'delayed'))
    b = model.PANELS.index(('delayed', 'local_strength', 'original'))
    return both[:, a, 1, 0]-both[:, b, 1, 0]


def analyze(output, ids, cfg, cycle, factor, mode):
    data = [load(output/f'cases_{b:06d}.npz') for b in ids]
    correct = np.stack([d['correct'] for d in data])
    margin = np.stack([d['margin'] for d in data])
    values = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    groups = {}
    for i, (timing, receiver, condition) in enumerate(model.PANELS):
        g = {metric:{d:{arm:statistics(x[:, i, j, a]) for a, arm in enumerate(model.ARMS)}
                     for j, d in enumerate(model.DAMAGE)} for metric, x in values.items()}
        g['own_accuracy_by_rule'] = {str(rule):{d:statistics(correct[:, i][:, [f, f+2]][:, :, :, :, j, 0].mean(axis=(1, 2, 3)))
            for j, d in enumerate(model.DAMAGE)} for f, rule in enumerate((1, -1))}
        g['own_minus_control'] = {d:{a:statistics(values['accuracy'][:, i, j, 0]-values['accuracy'][:, i, j, k])
            for k, a in enumerate(model.ARMS) if k} for j, d in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{d}':g['own_accuracy_by_rule'][str(rule)][d]['ci95'][0] > .75 for rule in (1, -1) for d in model.DAMAGE}
        gates.update({f'advantage_{d}_{a}':g['own_minus_control'][d][a]['ci95'][0] > .10 for d in model.DAMAGE for a in model.ARMS[1:]})
        g.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(timing, {}).setdefault(receiver, {})[condition] = g
    def difference(high, low):
        a, b = model.PANELS.index(high), model.PANELS.index(low)
        return {m:{d:statistics(x[:, a, j, 0]-x[:, b, j, 0]) for j, d in enumerate(model.DAMAGE)} for m, x in values.items()}
    rebuilding = {t:{r:difference((t, r, 'delayed'), (t, r, 'original')) for r in model.RECEIVERS} for t in model.TIMINGS}
    receiving = {c:{r:difference(('delayed', r, c), ('original', r, c)) for r in model.RECEIVERS} for c in model.CONDITIONS}
    interactions = {}
    for r in model.RECEIVERS:
        a, b, c, d = [model.PANELS.index(p) for p in (('delayed', r, 'delayed'), ('delayed', r, 'original'), ('original', r, 'delayed'), ('original', r, 'original'))]
        interactions[r] = {m:{injury:statistics((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]))
                             for j, injury in enumerate(model.DAMAGE)} for m, x in values.items()}
    bc = np.stack([d['body_correct'] for d in data]); bm = np.stack([d['body_margin'] for d in data])
    body_values = dict(accuracy=bc.mean(axis=(2, 3, 4)), both_cues=bc.all(axis=4).mean(axis=(2, 3)), margin=bm.mean(axis=(2, 3, 4)))
    body = {c:{m:statistics(x[:, i]) for m, x in body_values.items()} for i, c in enumerate(model.CONDITIONS)}
    body['delayed_minus_original'] = {m:statistics(x[:, 1]-x[:, 0]) for m, x in body_values.items()}
    primary = statistics(primary_values(values['both_cues']))
    technical = mode != 'scientific'; passed = primary['ci95'][0] > .05
    absolute = groups['delayed']['local_strength']['delayed']['both_cues']['scattered']['own']['ci95'][0] > .75
    s = dict(experiment='E034', mode=mode, status='TECHNICAL_ONLY' if technical else 'SETTLED_REBUILDING_BENEFIT_ESTABLISHED' if passed else 'SETTLED_REBUILDING_BENEFIT_NOT_ESTABLISHED',
        blocks=ids, lineages=len(ids)*4*cfg.recipients, cfg=asdict(cfg), base_cycle=asdict(cycle), generation=9,
        schedules={t:asdict(c) for t, c in zip(model.TIMINGS, model.schedules(cycle, factor))}, panels=model.PANELS,
        arms=model.ARMS, damage=model.DAMAGE, conditions=model.CONDITIONS, timings=model.TIMINGS, receivers=model.RECEIVERS,
        groups=groups, rebuilding_contrasts=rebuilding, receiving_contrasts=receiving, interactions=interactions, body=body,
        prior_cases_reused=True, original_boundary_matches_e031=True, writing_rule_changed=False, total_read_steps_changed=False,
        individual_observations=int(correct.size), body_individual_observations=int(bc.size),
        primary=dict(endpoint='h9 scattered own both-cue success under delayed normalized terminal receiving: delayed minus original renewal',
            margin=.05, statistics=primary, lower_above_005=None if technical else passed),
        absolute_reliability_lower_above_075=None if technical else absolute,
        interval_scope='One focal contrast; all secondary intervals and context gates pointwise')
    dump(output/'summary.json', s)
    def fmt(x):
        return f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E034 longer settling during one rebuilding step', '', '**'+s['status']+'**', '',
        f'{len(ids)} existing E031 blocks; {s["lineages"]} lineages. Generation 8 to 9; writer and total step count unchanged.', '',
        'Focal rebuilding benefit with a common delayed normalized receiver: **'+fmt(primary)+' percentage points**.', '',
        '| Terminal timing | Reader | Renewal timing | Intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- | --- |']
    for t, r, c in model.PANELS:
        g = groups[t][r][c]
        lines.append(f'| {t} | {r} | {c} | '+' | '.join(fmt(g['both_cues'][d]['own']) for d in model.DAMAGE)+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', 'Current-body both-cue success: original '+fmt(body['original']['both_cues'])+', delayed '+fmt(body['delayed']['both_cues'])+'.', '',
        'Post hoc one-boundary intervention, not fresh replication or long-term serial maintenance. The focal lower bound must exceed five points. Absolute reliability is reported separately. Every terminal comparison uses common receiving settings; all cases retained. Omitted raw arrays require independent replay against saved commitments.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return s


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('fixture', 'benchmark', 'scientific'), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    a = p.parse_args(); cap_cpus(8); assert 1 <= a.workers <= 8
    output = HERE/'runs'/dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='rebuilding_v1')[a.mode]
    if a.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']; assert a.worker in c['blocks']
        save_block(output, ROOT/c['source'], a.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle']), c['factor']); return
    source, ids, cfg, cycle = source_config(a.mode); factor = 2 if a.mode == 'fixture' else 4
    started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E034', mode=a.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        factor=factor, source=str(source.relative_to(ROOT)), workers=a.workers, generation=9, panels=model.PANELS))
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
        finish(output, started, dict(experiment='E034', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__':
    main()
