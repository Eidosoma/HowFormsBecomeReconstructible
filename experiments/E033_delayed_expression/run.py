"""All-case receiving intervention on saved E031 packets."""
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
from E033_delayed_expression import model
import numpy as np

CONTRASTS = (('delayed_same_duration', 'original'), ('extra_time', 'original'),
             ('delayed_extra_time', 'original'), ('delayed_extra_time', 'extra_time'),
             ('delayed_extra_time', 'delayed_same_duration'))


def input_paths():
    names = ('common.py', 'run_python.sh', 'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E023_receiver_compensation/model.py', 'E023_receiver_compensation/audit.py',
        'E031_renewal_durability/audit.py', 'E031_renewal_durability/evidence.py')
    return [ROOT/p for p in names]+[HERE/p for p in ('model.py', 'run.py', 'audit.py', 'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def source_config(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest, rel
    source = ROOT/index[dict(fixture='fixture_run', benchmark='benchmark_run', scientific='source_run')[mode]]
    manifest = verify(source)
    cfg, cycle = model.base.Config(**manifest['contract']['config']), model.Cycle(**manifest['contract']['cycle'])
    ids = manifest['contract']['blocks']
    assert ids == (list(range(27000, 27032)) if mode == 'scientific' else [900031])
    assert manifest['contract']['conditions'][0] == 'maturing'
    return source, ids, cfg, cycle


def load(path):
    with np.load(path, allow_pickle=False) as handle: return {k:handle[k] for k in handle.files}


def save_block(output, source, block, cfg, cycle, factor):
    started = time.monotonic(); cap_cpus(8)
    correct, margin, ports = [], [], []
    for h in model.HORIZONS:
        record = load(source/f'boundary_{block:06d}_g{h}.npz')['outgoing'][0]
        original = load(source/f'assay_{block:06d}_h{h}.npz')
        for i, timing in enumerate(model.schedules(cycle, factor)):
            raw = model.assay(record, block, h, cfg, timing)
            if i == 0:
                for k in ('masks', 'permutations'): np.testing.assert_array_equal(raw[k], original[k])
                np.testing.assert_array_equal(raw['late_ports'].mean(axis=0), original['mean_ports'][[0, 10]])
            model.evidence.save(output/f'assay_{block:06d}_h{h}_t{i}.npz', raw, 'assay')
            a, b, c = model.score(raw['late_ports'].mean(axis=0), cfg)
            correct.append(a); margin.append(b); ports.append(c)
    cases = dict(correct=np.concatenate(correct), margin=np.concatenate(margin), ports=np.concatenate(ports))
    np.savez_compressed(output/f'cases_{block:06d}.npz', **cases)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started, original_schedules_match_e031=True))


def statistics(x):
    x = np.asarray(x, float)
    draw = rng('E033', 'bootstrap', 'delayed_expression').integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draw].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def primary_values(both):
    assert both.shape[1:] == (16, 3, 7)
    hi = model.PANELS.index((16, 'delayed_extra_time', 'local_strength'))
    lo = model.PANELS.index((16, 'extra_time', 'local_strength'))
    return both[:, hi, 1, 0]-both[:, lo, 1, 0]


def analyze(output, ids, cfg, cycle, factor, mode):
    data = [load(output/f'cases_{b:06d}.npz') for b in ids]
    success = np.stack([d['correct'] for d in data])
    margins = np.stack([d['margin'] for d in data])
    values = dict(accuracy=success.mean(axis=(2, 3, 4)), both_cues=success.all(axis=4).mean(axis=(2, 3)), margin=margins.mean(axis=(2, 3, 4)))
    rules = np.stack([success[:, :, [r, r+2]][..., 0].mean(axis=(2, 3, 4)) for r in range(2)], axis=2)
    groups = {}
    for i, (h, t, receiver) in enumerate(model.PANELS):
        group = {metric: {d: {arm:statistics(array[:, i, j, a]) for a, arm in enumerate(model.ARMS)}
            for j, d in enumerate(model.DAMAGE)} for metric, array in values.items()}
        group['own_accuracy_by_rule'] = {str(rule):{d:statistics(rules[:, i, r, j]) for j, d in enumerate(model.DAMAGE)} for r, rule in enumerate((1, -1))}
        group['own_minus_control'] = {d:{arm:statistics(values['accuracy'][:, i, j, 0]-values['accuracy'][:, i, j, a])
            for a, arm in enumerate(model.ARMS) if a} for j, d in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{d}': group['own_accuracy_by_rule'][str(rule)][d]['ci95'][0] > .75 for rule in (1, -1) for d in model.DAMAGE}
        gates.update({f'advantage_{d}_{a}':group['own_minus_control'][d][a]['ci95'][0] > .10 for d in model.DAMAGE for a in model.ARMS[1:]})
        group.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(str(h), {}).setdefault(receiver, {})[t] = group
    contrasts = {}
    for h in model.HORIZONS:
        contrasts[str(h)] = {}
        for receiver in model.RECEIVERS:
            contrasts[str(h)][receiver] = {}
            for hi, lo in CONTRASTS:
                a, b = (model.PANELS.index((h, t, receiver)) for t in (hi, lo))
                contrasts[str(h)][receiver][hi+'_minus_'+lo] = {metric:{d:statistics(array[:, a, j, 0]-array[:, b, j, 0])
                    for j, d in enumerate(model.DAMAGE)} for metric, array in values.items()}
    primary = statistics(primary_values(values['both_cues']))
    technical = mode != 'scientific'; passed = primary['ci95'][0] > .10
    s = dict(experiment='E033', mode=mode, status='TECHNICAL_ONLY' if technical else 'DELAYED_EXPRESSION_BENEFIT_ESTABLISHED' if passed else 'DELAYED_EXPRESSION_BENEFIT_NOT_ESTABLISHED',
        blocks=ids, lineages=len(ids)*4*cfg.recipients, cfg=asdict(cfg), base_cycle=asdict(cycle),
        schedules={t:asdict(c) for t, c in zip(model.TIMINGS, model.schedules(cycle, factor))},
        panels=model.PANELS, arms=model.ARMS, damage=model.DAMAGE, timings=model.TIMINGS, receivers=model.RECEIVERS,
        groups=groups, contrasts=contrasts, prior_cases_reused=True, packets_changed=False, renewal_policy_changed=False,
        primary=dict(endpoint='h16 scattered normalized both-cue success: delayed_extra_time minus extra_time', margin=.10, statistics=primary, lower_above_010=None if technical else passed),
        original_schedules_match_e031=True, individual_observations=int(success.size), interval_scope='One focal contrast; secondary intervals and context gates pointwise',
        absolute_h16_delayed_extra_time_reliability_lower_above_075=None if technical else groups['16']['local_strength']['delayed_extra_time']['both_cues']['scattered']['own']['ci95'][0] > .75)
    dump(output/'summary.json', s)
    def fmt(x): return f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E033 delayed expression from unchanged saved records', '', '**'+s['status']+'**', '',
        f"{len(ids)} existing E031 blocks; {s['lineages']} lineages; all cases retained. No packet or renewal changes.", '',
        'Focal h16 time-matched delayed-minus-extra-time both-cue contrast: **'+fmt(primary)+' percentage points**.', '',
        '| Horizon | Schedule | Reader | Intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- | --- |']
    for h, t, receiver in model.PANELS:
        g = groups[str(h)][receiver][t]
        lines.append(f'| {h} | {t} | {receiver} | '+' | '.join(fmt(g['both_cues'][d]['own']) for d in model.DAMAGE)+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', 'This is a post hoc intervention on existing cases. The focal criterion is lower>10 points at fixed total duration. Receiver improvement cannot establish repaired serial inheritance. Absolute reliability, other contrasts and context gates are reported separately; secondary intervals are pointwise. All schedules share unchanged saved packets and paired random-stream prefixes. The original schedule matches E031 exactly. Full omitted arrays require replay against commitments.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return s


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--mode', choices=('fixture', 'benchmark', 'scientific'), required=True)
    parser.add_argument('--workers', type=int, default=8); parser.add_argument('--worker', type=int)
    args = parser.parse_args(); cap_cpus(8)
    assert 1 <= args.workers <= 8
    name = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='expression_v1')[args.mode]
    output = HERE/'runs'/name
    if args.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']
        assert args.worker in c['blocks']
        save_block(output, ROOT/c['source'], args.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle']), c['factor']); return
    source, ids, cfg, cycle = source_config(args.mode)
    factor = 2 if args.mode == 'fixture' else 4
    started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E033', mode=args.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        factor=factor, source=str(source.relative_to(ROOT)), workers=args.workers, panels=model.PANELS))
    def launch(block):
        with (output/f'worker_{block}.log').open('x') as handle:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', args.mode, '--worker', str(block)],
                stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT, check=True)
        return block
    try:
        with ThreadPoolExecutor(max_workers=min(args.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]): print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, factor, args.mode)
        finish(output, started, dict(experiment='E033', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
