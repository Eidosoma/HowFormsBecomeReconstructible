"""Fresh independent baseline histories and fixed three-body rollback confirmation."""
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
from E015_functional_inheritance.audit import verify
from E050_fresh_rollback_confirmation import model
import numpy as np


PAIRS = ((1, 0), (2, 0), (1, 2))
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='confirmation_v1')


def input_paths():
    external = ('common.py', 'run_python.sh', 'SOURCE_SNAPSHOT.json', 'SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E048_partial_rollback/model.py', 'E048_partial_rollback/audit.py',
        'E049_rollback_persistence/model.py', 'E049_rollback_persistence/audit.py')
    return [ROOT/p for p in external]+[HERE/p for p in
        ('model.py', 'run.py', 'audit.py', 'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def load(path):
    with np.load(path, allow_pickle=False) as h: return {k:h[k] for k in h.files}


def save(path, values):
    with path.open('xb') as handle: np.savez_compressed(handle, **values)


def equal(a, b, label=''):
    assert a.shape == b.shape and a.dtype == b.dtype, label
    assert a.tobytes() == b.tobytes(), label


def configuration(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in {**index['sha256'], **index['prior_manifest_sha256']}.items(): assert sha(ROOT/rel) == digest, rel
    prior = set()
    for rel in index['prior_manifest_sha256']:
        prior.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(prior) == index['prior_block_ids'] and not prior.intersection(index['blocks'])
    assert index['blocks'] == list(range(33000, 33032)) and index['excluded_block'] == 900041
    cfg = model.base.Config(); cycle = model.Cycle(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    if mode == 'fixture':
        cfg = replace(cfg, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cycle = replace(cycle, read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark':
        cfg = replace(cfg, recipients=1); cycle = replace(cycle, read_steps=128, settling_steps=64)
    else: assert mode == 'scientific'
    if mode != 'scientific':
        baseline = verify(ROOT/index['baseline_reference'][mode])['contract']
        branch = verify(ROOT/index['branch_reference'][mode])['contract']
        assert baseline['experiment'] == 'E041' and branch['experiment'] == 'E049'
        assert baseline['blocks'] == branch['blocks'] == [900041]
        assert baseline['config'] == branch['config'] == asdict(cfg)
        assert dict(baseline['cycle'], settling_steps=4*baseline['cycle']['settling_steps']) == branch['cycle'] == asdict(cycle)
    return index['blocks'] if mode == 'scientific' else [index['excluded_block']], cfg, cycle


def gather(output, block, index, acquired):
    n = len(index); old = np.empty((n, 4096), np.uint8); new = old.copy()
    dead = np.empty((n, 16, 16), bool); next_dead = dead.copy(); cache = {}
    def boundary(g):
        if g not in cache:
            with np.load(output/f'baseline_{block:06d}_g{g}.npz', allow_pickle=False) as h:
                cache[g] = {k:h[k] for k in ('outgoing', 'masks')}
        return cache[g]
    for j, (f, r, g) in enumerate(index.tolist()):
        old[j] = acquired[f] if g == 1 else boundary(g-1)['outgoing'][f, r]
        new[j] = boundary(g)['outgoing'][f, r]; dead[j] = boundary(g)['masks'][f, r]
        next_dead[j] = boundary(g+1)['masks'][f, r]
    return old, new, dead, next_dead


def save_block(output, block, cfg, cycle, mode):
    started = time.monotonic(); cap_cpus(8); index_data = json.loads((HERE/'SOURCE_DATA.json').read_text())
    source = model.acquisition.teach(block, cfg); save(output/f'source_{block:06d}.npz', source)
    reference = ROOT/index_data['baseline_reference'][mode] if mode != 'scientific' else None
    if reference is not None:
        expected = load(reference/f'source_{block:06d}.npz')
        for k, v in source.items():
            if k != 'capture_states': equal(v, expected[k], k)
        import hashlib
        meta = json.loads(expected['__index__'].tobytes())
        assert hashlib.sha256(source['capture_states'].tobytes()).hexdigest() == meta['arrays']['capture_states']['sha256']
        prior_cases = load(reference/f'cases_{block:06d}.npz')
    packet = np.repeat(source['acquired'][1, :, None], cfg.recipients, axis=1)
    observations = dict(correct=[], margin=[], ports=[])
    for g in range(1, 33):
        raw = model.baseline(packet, block, g, cfg, cycle)
        cases = model.baseline_score(raw['mean_ports'], cfg)
        if reference is not None:
            expected = load(reference/f'boundary_{block:06d}_g{g}.npz')
            equal(raw['outgoing'], expected['outgoing'][3], 'baseline reference outgoing')
            equal(raw['masks'], expected['renewal_mask'], 'baseline reference mask')
            for k in cases: equal(cases[k], prior_cases['body_'+k][g-1, 3], k)
        save(output/f'baseline_{block:06d}_g{g}.npz', raw)
        packet = raw['outgoing'].copy()
        for k in cases: observations[k].append(cases[k])
    baseline = {k:np.stack(v) for k, v in observations.items()}
    save(output/f'baseline_cases_{block:06d}.npz', baseline)
    first, index = model.first_failures(baseline['correct'])
    old, outgoing, dead, next_dead = gather(output, block, index, source['acquired'][1])
    selection = model.construct(old, outgoing, dead, index, block)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & model.renewal.surviving_edges(next_dead)).sum(axis=(-3, -2, -1))
        for k in ('half_changed', 'full_changed')], axis=-1))
    branch_reference = ROOT/index_data['branch_reference'][mode] if mode != 'scientific' else None
    if branch_reference is not None:
        prior_selection = load(branch_reference/f'selection_{block:06d}.npz')
        for k in selection: equal(selection[k], prior_selection[k], k)
    records = selection['packets'].copy(); result = dict(correct=[], margin=[], ports=[])
    cache = {}
    for offset in model.OFFSETS:
        raw = model.rebuild(records, index, offset, block, cfg, cycle)
        equal(raw['incoming'], records, 'serial packet chain')
        cases = model.score(raw['mean_ports'], index, cfg)
        f, r, g = index.T
        for k in cases:
            equal(cases[k][0], baseline[k][g+offset-1, f, r], 'original branch '+k)
            result[k].append(cases[k])
        for j, (f, r, g) in enumerate(index.tolist()):
            if g+offset not in cache:
                with np.load(output/f'baseline_{block:06d}_g{g+offset}.npz', allow_pickle=False) as h:
                    cache[g+offset] = {k:h[k] for k in ('outgoing', 'masks')}
            expected = cache[g+offset]
            equal(raw['outgoing'][0, j], expected['outgoing'][f, r], 'original outgoing')
            equal(raw['masks'][j], expected['masks'][f, r], 'matched damage')
        if branch_reference is not None:
            expected = load(branch_reference/f'boundary_{block:06d}_d{offset}.npz')
            assert set(expected) == set(raw)
            for k in raw: equal(raw[k], expected[k], 'technical E049 '+k)
        save(output/f'boundary_{block:06d}_d{offset}.npz', raw); records = raw['outgoing'].copy()
    cases = {k:np.stack(v) for k, v in result.items()}
    if branch_reference is not None:
        expected = load(branch_reference/f'cases_{block:06d}.npz')
        for k in cases: equal(cases[k], expected[k], k)
    save(output/f'selection_{block:06d}.npz', selection); save(output/f'cases_{block:06d}.npz', cases)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started, generations=32,
        eligible_cases=len(index), source_sha256=sha(output/f'source_{block:06d}.npz'),
        original_three_bodies_match_own_baseline_byte_exactly=True, rollback_applied_once=True,
        technical_baseline_and_branch_reference_match=(reference is not None)))
@lru_cache(maxsize=None)
def draws(n):
    return rng('E050', 'bootstrap', 'fresh_rollback_confirmation').integers(0, n, (10000, n))


def statistics(numerators, denominators):
    num, den = np.asarray(numerators, float), np.asarray(denominators, float)
    assert num.shape == den.shape and num.ndim == 1
    assert np.isfinite(num).all() and np.isfinite(den).all() and np.all(den >= 0)
    d = draws(len(num)); sampled_den = den[d].sum(axis=1)
    valid = sampled_den > 0
    ratios = num[d].sum(axis=1)[valid]/sampled_den[valid]
    return dict(mean=float(num.sum()/den.sum()) if den.sum() else None,
        ci95=np.quantile(ratios, [.025, .975]).tolist() if len(ratios) else [None, None],
        block_numerators=num.tolist(), block_denominators=den.tolist(),
        bootstrap_valid=int(valid.sum()), bootstrap_total=10000)


def decision(primary, technical=False):
    if technical: return None
    return all(primary[k]['ci95'][0] is not None and primary[k]['ci95'][0] > threshold
        for k, threshold in (('original', .05), ('full_rollback', 0.), ('loss_reduction', 0.)))


def loss_counts(correct):
    assert correct.dtype == np.dtype(bool) and correct.ndim == 3 and correct.shape[0] == 3 and correct.shape[-1] == 2
    both = correct.all(axis=-1)
    return (both[0, None] & ~both[1:]).sum(axis=1)


def episode_values(correct):
    assert correct.dtype == np.dtype(bool) and correct.ndim == 4 and correct.shape[:2] == (3, 3) and correct.shape[-1] == 2
    both = correct.all(axis=-1)
    return dict(sustained=both.all(axis=0), any_recovery=both.any(axis=0),
        relapse_after_first=both[0] & ~both[1:].all(axis=0)), 4*both[0].astype(np.int8)+2*both[1].astype(np.int8)+both[2]


def analyze(output, ids, cfg, cycle, mode):
    cases = [load(output/f'cases_{b:06d}.npz') for b in ids]
    selections = [load(output/f'selection_{b:06d}.npz') for b in ids]
    den = np.array([len(x['index']) for x in selections])
    groups, contrasts, transitions, per_rule, loss_rates, loss_reduction = {}, {}, {}, {}, {}, {}
    for d in range(3):
        key = str(d+1)
        values = dict(both_cues=np.array([x['correct'][d].all(axis=-1).sum(axis=1) for x in cases]),
            accuracy=np.array([x['correct'][d].sum(axis=(1, 2))/2 for x in cases]),
            margin=np.array([x['margin'][d].sum(axis=(1, 2))/2 for x in cases]))
        groups[key] = {v:{k:statistics(a[:, i], den) for k, a in values.items()} for i, v in enumerate(model.VARIANTS)}
        contrasts[key], transitions[key] = {}, {}
        for a, b in PAIRS:
            name = model.VARIANTS[a]+'_minus_'+model.VARIANTS[b]
            contrasts[key][name] = {k:statistics(x[:, a]-x[:, b], den) for k, x in values.items()}
            codes = [2*x['correct'][d, b].all(axis=-1).astype(int)+x['correct'][d, a].all(axis=-1) for x in cases]
            by_block = {label:[int((code == i).sum()) for code in codes]
                for i, label in enumerate(('both_fail', 'rescued', 'lost', 'both_succeed'))}
            transitions[key][name] = dict(by_block=by_block, counts={k:sum(v) for k, v in by_block.items()}, total=int(den.sum()))
        losses = np.array([loss_counts(x['correct'][d]) for x in cases])
        loss_rates[key] = {name:statistics(losses[:, j], den) for j, name in enumerate(('half_rollback', 'full_rollback'))}
        loss_reduction[key] = statistics(losses[:, 1]-losses[:, 0], den)
        per_rule[key] = {}
        for rule in (1, -1):
            masks = [model.base.RULES[x['index'][:, 0]] == rule for x in selections]
            rd = [int(x.sum()) for x in masks]
            per_rule[key][str(rule)] = {v:statistics([x['correct'][d, j, mask].all(axis=-1).sum() for x, mask in zip(cases, masks)], rd)
                for j, v in enumerate(model.VARIANTS)}
    primary = {v:contrasts['3']['half_rollback_minus_'+v]['both_cues'] for v in ('original', 'full_rollback')}
    primary['loss_reduction'] = loss_reduction['3']
    episodes = [episode_values(x['correct']) for x in cases]
    episode = {name:{v:statistics([x[0][name][j].sum() for x in episodes], den) for j, v in enumerate(model.VARIANTS)}
        for name in ('sustained', 'any_recovery', 'relapse_after_first')}
    episode_contrasts = {name:{model.VARIANTS[a]+'_minus_'+model.VARIANTS[b]:statistics(
        [x[0][name][a].sum()-x[0][name][b].sum() for x in episodes], den) for a, b in PAIRS} for name in episode}
    patterns = {}
    for j, v in enumerate(model.VARIANTS):
        by_block = {format(code, '03b').replace('0', 'F').replace('1', 'S'):[int((x[1][j] == code).sum()) for x in episodes] for code in range(8)}
        patterns[v] = dict(by_block=by_block, counts={k:sum(x) for k, x in by_block.items()})
    field_sums = np.array([x['counts'].sum(axis=0) for x in selections])
    visible = np.array([x['next_visible_counts'].sum(axis=0) for x in selections])
    selection = dict(mean_per_eligible_case={name:statistics(field_sums[:, i], den) for i, name in enumerate(model.FIELDS)},
        totals={name:float(field_sums[:, i].sum()) for i, name in enumerate(model.FIELDS)},
        affected_cases=sum(int((x['counts'][:, 0] > 0).sum()) for x in selections),
        zero_edit_cases=sum(int((x['counts'][:, 0] == 0).sum()) for x in selections),
        next_visible_totals=visible.sum(axis=0).tolist(),
        next_visible_means={name:statistics(visible[:, i], den) for i, name in enumerate(('half', 'full'))})
    first = np.stack([x['first_failure'] for x in selections])
    cohort = dict(total_lineages=int(first.size), ever_failed=int((first > 0).sum()), never_failed=int((first == 0).sum()),
        first_failure_without_three=int((first > 29).sum()), eligible=int(den.sum()), eligible_by_block=den.tolist())
    technical = mode != 'scientific'; result = decision(primary, technical)
    status = 'TECHNICAL_ONLY' if technical else 'FRESH_THIRD_BODY_JOINT_BENEFIT_ESTABLISHED' if result else 'FRESH_THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED'
    s = dict(experiment='E050', mode=mode, status=status, blocks=ids, cfg=asdict(cfg), cycle=asdict(cycle),
        variants=model.VARIANTS, dose_fractions=model.DOSES, body_offsets=model.OFFSETS, primary_body_offset=3, cohort=cohort,
        groups=groups, contrasts=contrasts, transitions=transitions, per_rule=per_rule, selection=selection,
        primary=primary, primary_decision=result, loss_rates=loss_rates, loss_reduction=loss_reduction,
        episode=episode, episode_contrasts=episode_contrasts, patterns=patterns,
        original_three_bodies_match_own_baseline_byte_exactly=True,
        technical_baseline_and_branch_reference_match=(True if technical else None),
        rollback_applied_once=True, ordinary_rewriting_after_rollback=True, indefinite_or_deployable_policy_qualified=False,
        individual_observations=18*int(den.sum()), baseline_individual_observations=32*len(ids)*4*cfg.recipients*2,
        prior_cases_reused=False, prior_cases_pooled=False, independent_fresh_histories=not technical, source_policy='bridge_rewrite',
        source_policy_index=3, selection_uses_future_outcomes=False,
        interval_scope='Pointwise two-sided 95% whole-block bootstrap; pooled eligible-case ratios; joint primary at third body only.')
    if not technical:
        assert cohort['total_lineages'] == 512
        assert cohort['eligible']+cohort['first_failure_without_three'] == cohort['ever_failed']
        assert cohort['ever_failed']+cohort['never_failed'] == 512
    dump(output/'summary.json', s)
    fmt = lambda x: 'unobserved' if x['mean'] is None else f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E050 fresh confirmation of one onset rollback', '', '**'+status+'**', '',
        f"{cohort['eligible']} onsets with three observed next bodies in {len(ids)} blocks; fresh histories for the scientific run. Rollback once; full bridge rewriting afterward.", '',
        '| Body after onset | Original success % [95%] | Half rollback | Full rollback |', '| --- | --- | --- | --- |']
    for d in ('1', '2', '3'): lines.append('| '+d+' | '+' | '.join(fmt(groups[d][v]['both_cues']) for v in model.VARIANTS)+' |')
    for low in ('original', 'full_rollback'):
        tr = transitions['3']['half_rollback_minus_'+low]['counts']
        lines += ['', f"Third-body half minus {low}: {fmt(primary[low])} points; {tr['rescued']} rescues, {tr['lost']} losses."]
    lines += ['', 'Third-body reduction in original-success losses, full minus half: '+fmt(primary['loss_reduction'])+' points.', '',
        '| Three-body outcome | Original % [95%] | Half rollback | Full rollback |', '| --- | --- | --- | --- |']
    for name in episode: lines.append('| '+name+' | '+' | '.join(fmt(episode[name][v]) for v in model.VARIANTS)+' |')
    lines += ['', 'Joint benefit requires third-body lower bounds >5 points versus original, >0 versus full rollback, AND >0 for reduced original-success losses. All eligible cases remain in every denominator. Sustained means all three bodies succeed; any recovery means at least one does. Those secondary outcomes and the eight binary histories are descriptive. Initial rollback is never repeated; each later record is captured before the matched holding phase and passed to the next body. The original branch reproduces its independently generated unchanged baseline byte exactly. Technical runs reproduce the excluded E041/E049 references. Scientific cases are fresh; earlier cases are not pooled. This tests finite first-failure persistence, not an autonomous deployable trigger or indefinite heredity.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return s

def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=tuple(NAMES), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    a = p.parse_args(); cap_cpus(8); assert 1 <= a.workers <= 8
    output = HERE/'runs'/NAMES[a.mode]
    if a.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']; assert a.worker in c['blocks']
        save_block(output, a.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle']), a.mode); return
    ids, cfg, cycle = configuration(a.mode); started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E050', mode=a.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        variants=model.VARIANTS, dose_fractions=model.DOSES, body_offsets=model.OFFSETS, primary_body_offset=3,
        rollback_applied_once=True, source_policy='bridge_rewrite', source_policy_index=3, workers=a.workers,
        prior_cases_pooled=False, fresh_histories=(a.mode == 'scientific'), original_generations=32))
    def launch(b):
        with (output/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(b)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=min(a.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]): print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, a.mode)
        finish(output, started, dict(experiment='E050', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
