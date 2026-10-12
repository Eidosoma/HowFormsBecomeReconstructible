"""One onset intervention followed through three complete rebuilding bodies."""
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
from E049_rollback_persistence import model
import numpy as np

PAIRS = ((1, 0), (2, 0), (1, 2))
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='persistence_v1')


def input_paths():
    external = ('common.py', 'run_python.sh', 'E015_functional_inheritance/model.py',
        'E015_functional_inheritance/audit.py', 'E016_teaching_consistency/model.py',
        'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E048_partial_rollback/model.py', 'E048_partial_rollback/audit.py')
    return [ROOT/p for p in external]+[HERE/p for p in
        ('model.py', 'run.py', 'audit.py', 'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def source_config(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest, rel
    source = ROOT/index['sources'][mode]
    contract = verify(source)['contract']
    assert contract['experiment'] == 'E041' and contract['mode'] == mode
    ids = contract['blocks']
    assert ids == (list(range(32000, 32032)) if mode == 'scientific' else [900041])
    cfg = model.base.Config(**contract['config'])
    cycle = replace(model.Cycle(**contract['cycle']), settling_steps=4*contract['cycle']['settling_steps'])
    assert 2*cycle.settling_steps == cycle.read_steps and cycle.generations == 32
    chronology = index['chronology'][mode]
    if chronology is not None:
        chronology = ROOT/chronology
        verify(chronology)
    reference = ROOT/index['reference'][mode]
    prior = verify(reference)['contract']
    assert prior['experiment'] == 'E048' and prior['mode'] == mode
    assert prior['blocks'] == ids and prior['config'] == asdict(cfg) and prior['cycle'] == asdict(cycle)
    return source, chronology, reference, ids, cfg, cycle


def load(path):
    with np.load(path, allow_pickle=False) as h: return {k:h[k] for k in h.files}


def save(path, values):
    with path.open('xb') as handle: np.savez_compressed(handle, **values)


def gather(source, block, index):
    """Accept explicit addresses also for excluded mixed-generation technical tests."""
    n = len(index)
    incoming = np.empty((n, 4096), np.uint8); outgoing = incoming.copy()
    dead = np.empty((n, 16, 16), bool); next_dead = dead.copy()
    ports = np.empty((n, 2, 2))
    cache = {}
    def boundary(g):
        if g not in cache: cache[g] = load(source/f'boundary_{block:06d}_g{g}.npz')
        return cache[g]
    acquired = load(source/f'source_{block:06d}.npz')['acquired'][1] if np.any(index[:, 2] == 1) else None
    for c, (f, r, g) in enumerate(index.tolist()):
        incoming[c] = acquired[f] if g == 1 else boundary(g-1)['outgoing'][3, f, r]
        outgoing[c] = boundary(g)['outgoing'][3, f, r]
        dead[c] = boundary(g)['renewal_mask'][f, r]
        next_dead[c] = boundary(g+1)['renewal_mask'][f, r]
        ports[c] = boundary(g+1)['developed_mean_ports'][3, f, r]
    return incoming, outgoing, dead, next_dead, ports


def equal(a, b, label=''):
    assert a.shape == b.shape and a.dtype == b.dtype, label
    assert a.tobytes() == b.tobytes(), label


def select_reference_read(raw, positions):
    return {k:v[positions] if k in ('masks', 'birth') else v[:, :, positions] if k == 'late_ports' else v[:, positions]
        for k, v in raw.items()}


def save_block(output, source, chronology, reference, block, cfg, cycle):
    started = time.monotonic(); cap_cpus(8)
    original = load(source/f'cases_{block:06d}.npz')
    first, index = model.first_failures(original['body_correct'][:, 3])
    if chronology is not None:
        witness = load(chronology/f'measurements_{block:06d}.npz')
        np.testing.assert_array_equal(first, witness['events'][..., 0])
        np.testing.assert_array_equal((first > 0) & (first <= 29), witness['lineage'][..., 4].astype(bool))
    incoming, outgoing, dead, next_dead, expected_ports = gather(source, block, index)
    selection = model.construct(incoming, outgoing, dead, index, block)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & model.renewal.surviving_edges(next_dead)).sum(axis=(-3, -2, -1))
        for k in ('half_changed', 'full_changed')], axis=-1))
    prior_selection = load(reference/f'selection_{block:06d}.npz')
    positions = np.flatnonzero(prior_selection['index'][:, 2] <= 29)
    for k, value in selection.items():
        expected = prior_selection[k] if k == 'first_failure' else prior_selection[k][:, positions] if k == 'packets' else prior_selection[k][positions]
        equal(value, expected, k)
    selection['reference_positions'] = positions
    prior_read = select_reference_read(load(reference/f'read_{block:06d}.npz'), positions)
    prior_cases = load(reference/f'cases_{block:06d}.npz')
    result = dict(correct=[], margin=[], ports=[])
    boundary_cache = {}
    records = selection['packets'].copy()
    for offset in model.OFFSETS:
        raw = model.rebuild(records, index, offset, block, cfg, cycle)
        equal(raw['incoming'], records, 'chain')
        cases = model.score(raw['mean_ports'], index, cfg)
        if offset == 1:
            for k in model.READ_KEYS: equal(raw[k], prior_read[k], k)
            for k, value in cases.items(): equal(value, prior_cases[k][:, positions], k)
        f, r, g = index.T
        for k, name in (('ports', 'body_ports'), ('correct', 'body_correct'), ('margin', 'body_margin')):
            equal(cases[k][0], original[name][g+offset-1, 3, f, r], k)
            result[k].append(cases[k])
        for j, (f, r, g) in enumerate(index.tolist()):
            if g+offset not in boundary_cache:
                boundary_cache[g+offset] = load(source/f'boundary_{block:06d}_g{g+offset}.npz')
            boundary = boundary_cache[g+offset]
            equal(raw['outgoing'][0, j], boundary['outgoing'][3, f, r], 'original outgoing')
            equal(raw['masks'][j], boundary['renewal_mask'][f, r], 'renewal mask')
        save(output/f'boundary_{block:06d}_d{offset}.npz', raw)
        records = raw['outgoing'].copy()
    cases = {k:np.stack(v) for k, v in result.items()}
    if chronology is not None:
        f, r, _ = index.T
        np.testing.assert_array_equal(cases['correct'][:, 0].all(axis=-1).any(axis=0), witness['lineage'][f, r, 5].astype(bool))
    save(output/f'selection_{block:06d}.npz', selection)
    save(output/f'cases_{block:06d}.npz', cases)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        eligible_cases=len(index), first_body_matches_e048_byte_exactly=True,
        original_three_bodies_and_outgoing_match_e041_byte_exactly=True, rollback_applied_once=True))


@lru_cache(maxsize=None)
def draws(n):
    return rng('E049', 'bootstrap', 'rollback_persistence').integers(0, n, (10000, n))


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
    status = 'TECHNICAL_ONLY' if technical else 'THIRD_BODY_JOINT_BENEFIT_ESTABLISHED' if result else 'THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED'
    s = dict(experiment='E049', mode=mode, status=status, blocks=ids, cfg=asdict(cfg), cycle=asdict(cycle),
        variants=model.VARIANTS, dose_fractions=model.DOSES, body_offsets=model.OFFSETS, primary_body_offset=3, cohort=cohort,
        groups=groups, contrasts=contrasts, transitions=transitions, per_rule=per_rule, selection=selection,
        primary=primary, primary_decision=result, loss_rates=loss_rates, loss_reduction=loss_reduction,
        episode=episode, episode_contrasts=episode_contrasts, patterns=patterns,
        first_body_matches_e048_byte_exactly=True, original_three_bodies_and_outgoing_match_e041_byte_exactly=True,
        rollback_applied_once=True, ordinary_rewriting_after_rollback=True, indefinite_or_fresh_policy_qualified=False,
        individual_observations=18*int(den.sum()), prior_cases_reused=True, source_policy='bridge_rewrite',
        source_policy_index=3, selection_uses_future_outcomes=False,
        interval_scope='Pointwise two-sided 95% whole-block bootstrap; pooled eligible-case ratios; joint primary at third body only.')
    if not technical:
        assert (cohort['total_lineages'], cohort['ever_failed'], cohort['eligible'], cohort['first_failure_without_three']) == (512, 307, 281, 26)
        assert sum(episode['any_recovery']['original']['block_numerators']) == 243
    dump(output/'summary.json', s)
    fmt = lambda x: 'unobserved' if x['mean'] is None else f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E049 persistence after one onset rollback', '', '**'+status+'**', '',
        f"{cohort['eligible']} onsets with three observed next bodies in {len(ids)} existing blocks. Rollback once; full bridge rewriting afterward.", '',
        '| Body after onset | Original success % [95%] | Half rollback | Full rollback |', '| --- | --- | --- | --- |']
    for d in ('1', '2', '3'): lines.append('| '+d+' | '+' | '.join(fmt(groups[d][v]['both_cues']) for v in model.VARIANTS)+' |')
    for low in ('original', 'full_rollback'):
        tr = transitions['3']['half_rollback_minus_'+low]['counts']
        lines += ['', f"Third-body half minus {low}: {fmt(primary[low])} points; {tr['rescued']} rescues, {tr['lost']} losses."]
    lines += ['', 'Third-body reduction in original-success losses, full minus half: '+fmt(primary['loss_reduction'])+' points.', '',
        '| Three-body outcome | Original % [95%] | Half rollback | Full rollback |', '| --- | --- | --- | --- |']
    for name in episode: lines.append('| '+name+' | '+' | '.join(fmt(episode[name][v]) for v in model.VARIANTS)+' |')
    lines += ['', 'Joint benefit requires third-body lower bounds >5 points versus original, >0 versus full rollback, AND >0 for reduced original-success losses. All eligible cases remain in every denominator. Sustained means all three bodies succeed; any recovery means at least one does. Those secondary outcomes and the eight binary histories are descriptive. Initial rollback is never repeated; each later record is captured before the matched holding phase and passed to the next body. First-body arrays reproduce E048, and all three original body responses and outgoing packets reproduce E041 byte exactly. This tests finite persistence on selected existing cases, not a fresh deployable policy or indefinite heredity.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return s


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=tuple(NAMES), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    a = p.parse_args(); cap_cpus(8); assert 1 <= a.workers <= 8
    output = HERE/'runs'/NAMES[a.mode]
    if a.worker is not None:
        c = json.loads((output/'manifest.json').read_text())['contract']; assert a.worker in c['blocks']
        save_block(output, ROOT/c['source'], ROOT/c['chronology'] if c['chronology'] else None, ROOT/c['reference'],
            a.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle'])); return
    source, chronology, reference, ids, cfg, cycle = source_config(a.mode)
    started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E049', mode=a.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        variants=model.VARIANTS, source=str(source.relative_to(ROOT)), chronology=str(chronology.relative_to(ROOT)) if chronology else None,
        reference=str(reference.relative_to(ROOT)), dose_fractions=model.DOSES, body_offsets=model.OFFSETS, primary_body_offset=3, rollback_applied_once=True, source_policy='bridge_rewrite', source_policy_index=3, workers=a.workers))
    def launch(b):
        with (output/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(b)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=min(a.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]): print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, a.mode)
        finish(output, started, dict(experiment='E049', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
