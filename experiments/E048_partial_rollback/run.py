"""Existing E041 first-failure cohort, paired next-body intervention."""
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
from E048_partial_rollback import model
import numpy as np

PAIRS = ((1, 0), (2, 0), (1, 2))
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='partial_v1')


def input_paths():
    external = ('common.py', 'run_python.sh', 'E015_functional_inheritance/model.py',
        'E015_functional_inheritance/audit.py', 'E016_teaching_consistency/model.py',
        'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py')
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
    assert prior['experiment'] == 'E047' and prior['mode'] == mode
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


def save_block(output, source, chronology, reference, block, cfg, cycle):
    started = time.monotonic(); cap_cpus(8)
    original = load(source/f'cases_{block:06d}.npz')
    first, index = model.first_failures(original['body_correct'][:, 3])
    if chronology is not None:
        witness = load(chronology/f'measurements_{block:06d}.npz')
        np.testing.assert_array_equal(first, witness['events'][..., 0])
    incoming, outgoing, dead, next_dead, expected_ports = gather(source, block, index)
    selection = model.construct(incoming, outgoing, dead, index, block)
    raw = model.read(selection['packets'], index, block, cfg, cycle)
    np.testing.assert_array_equal(raw['masks'], next_dead)
    np.testing.assert_array_equal(raw['mean_ports'][0], expected_ports)
    cases = model.score(raw['mean_ports'], index, cfg)
    f, r, g = index.T
    for k, name in (('ports', 'body_ports'), ('correct', 'body_correct'), ('margin', 'body_margin')):
        np.testing.assert_array_equal(cases[k][0], original[name][g, 3, f, r])
    next_available = model.renewal.surviving_edges(next_dead)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & next_available).sum(axis=(-3, -2, -1)) for k in ('half_changed', 'full_changed')], axis=-1))
    prior_selection = load(reference/f'selection_{block:06d}.npz')
    for k in ('index', 'first_failure', 'incoming', 'outgoing', 'renewal_mask', 'available', 'target'):
        assert selection[k].dtype == prior_selection[k].dtype
        assert selection[k].shape == prior_selection[k].shape
        assert selection[k].tobytes() == prior_selection[k].tobytes(), k
    np.testing.assert_array_equal(selection['packets'][[0, 2]], prior_selection['packets'][[0, 1]])
    prior_read = load(reference/f'read_{block:06d}.npz')
    for k, value in raw.items():
        current = value if k in ('masks', 'birth') else value[:, [0, 2]] if k == 'late_ports' else value[[0, 2]]
        prior = prior_read[k] if k in ('masks', 'birth') else prior_read[k][:, [0, 1]] if k == 'late_ports' else prior_read[k][[0, 1]]
        assert current.dtype == prior.dtype and current.shape == prior.shape and current.tobytes() == prior.tobytes(), k
    prior_cases = load(reference/f'cases_{block:06d}.npz')
    for k, value in cases.items(): assert value[[0, 2]].tobytes() == prior_cases[k][[0, 1]].tobytes(), k
    save(output/f'selection_{block:06d}.npz', selection)
    save(output/f'read_{block:06d}.npz', raw)
    save(output/f'cases_{block:06d}.npz', cases)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        eligible_cases=len(index), original_next_body_matches_e041_exactly=True, original_and_full_match_e047_byte_exactly=True))


@lru_cache(maxsize=None)
def draws(n):
    return rng('E048', 'bootstrap', 'partial_rollback').integers(0, n, (10000, n))


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


def analyze(output, ids, cfg, cycle, mode):
    cases = [load(output/f'cases_{b:06d}.npz') for b in ids]
    selections = [load(output/f'selection_{b:06d}.npz') for b in ids]
    den = np.array([len(x['index']) for x in selections])
    values = dict(both_cues=np.array([x['correct'].all(axis=-1).sum(axis=1) for x in cases]),
        accuracy=np.array([x['correct'].sum(axis=(1, 2))/2 for x in cases]),
        margin=np.array([x['margin'].sum(axis=(1, 2))/2 for x in cases]))
    groups = {v:{k:statistics(a[:, i], den) for k, a in values.items()} for i, v in enumerate(model.VARIANTS)}
    contrasts, transitions = {}, {}
    for a, b in PAIRS:
        key = model.VARIANTS[a]+'_minus_'+model.VARIANTS[b]
        contrasts[key] = {k:statistics(x[:, a]-x[:, b], den) for k, x in values.items()}
        codes = [2*x['correct'][b].all(axis=-1).astype(int)+x['correct'][a].all(axis=-1) for x in cases]
        by_block = {label:[int((code == i).sum()) for code in codes]
            for i, label in enumerate(('both_fail', 'rescued', 'lost', 'both_succeed'))}
        transitions[key] = dict(by_block=by_block, counts={k:sum(v) for k, v in by_block.items()}, total=int(den.sum()))
    primary = {v:contrasts['half_rollback_minus_'+v]['both_cues'] for v in ('original', 'full_rollback')}
    losses = np.array([loss_counts(x['correct']) for x in cases])
    primary['loss_reduction'] = statistics(losses[:, 1]-losses[:, 0], den)
    loss_rates = {name:statistics(losses[:, j], den) for j, name in enumerate(('half_rollback', 'full_rollback'))}
    per_rule = {}
    for rule in (1, -1):
        masks = [model.base.RULES[x['index'][:, 0]] == rule for x in selections]
        rd = [int(x.sum()) for x in masks]
        per_rule[str(rule)] = {v:statistics([x['correct'][j, mask].all(axis=-1).sum() for x, mask in zip(cases, masks)], rd)
            for j, v in enumerate(model.VARIANTS)}
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
        first_failure_without_next=int((first == 32).sum()), eligible=int(den.sum()), eligible_by_block=den.tolist())
    technical = mode != 'scientific'; result = decision(primary, technical)
    s = dict(experiment='E048', mode=mode, status='TECHNICAL_ONLY' if technical else 'HALF_ROLLBACK_JOINT_BENEFIT_ESTABLISHED' if result else 'HALF_ROLLBACK_JOINT_BENEFIT_NOT_ESTABLISHED',
        blocks=ids, cfg=asdict(cfg), cycle=asdict(cycle), variants=model.VARIANTS, cohort=cohort,
        groups=groups, contrasts=contrasts, transitions=transitions, per_rule=per_rule, selection=selection,
        primary=primary, primary_decision=result, loss_rates=loss_rates, original_next_body_matches_e041_exactly=True,
        original_and_full_match_e047_byte_exactly=True, dose_fractions=model.DOSES,
        individual_observations=6*int(den.sum()), prior_cases_reused=True, multi_generation_policy_tested=False,
        source_policy='bridge_rewrite', source_policy_index=3, selection_uses_future_outcomes=False,
        interpretation='Retrospective first-failure cohort; matched next-body intervention, not serial qualification.',
        interval_scope='Pointwise two-sided 95% whole-block bootstrap; pooled eligible-case ratios; all three primary requirements must pass.')
    if not technical:
        assert (cohort['total_lineages'], cohort['ever_failed'], cohort['eligible'], cohort['first_failure_without_next']) == (512, 307, 301, 6)
        assert int(values['both_cues'][:, 0].sum()) == 174
        assert int(values['both_cues'][:, 2].sum()) == 193
        assert transitions['full_rollback_minus_original']['counts']['rescued'] == 55
        assert transitions['full_rollback_minus_original']['counts']['lost'] == 36
    dump(output/'summary.json', s)
    fmt = lambda x: 'unobserved' if x['mean'] is None else f"{100*x['mean']:.2f} [{100*x['ci95'][0]:.2f}, {100*x['ci95'][1]:.2f}]"
    lines = ['# E048 half rollback after first failure', '', '**'+s['status']+'**', '',
        f"{cohort['eligible']} eligible onsets in {len(ids)} existing blocks; {cohort['never_failed']} never fail and {cohort['first_failure_without_next']} first fail without an observed next body.", '',
        '| Next-body packet | Both cues correct, % [95%] |', '| --- | --- |']
    lines += [f"| {v} | {fmt(groups[v]['both_cues'])} |" for v in model.VARIANTS]
    for v in ('original', 'full_rollback'):
        st = primary[v]
        tr = transitions['half_rollback_minus_'+v]['counts']
        lines += ['', f"Half minus {v}: {fmt(st)} percentage points; {tr['rescued']} rescues, {tr['lost']} losses."]
    lines += ['', 'Reduction in original-success losses, full minus half, per all eligible cases: '+fmt(primary['loss_reduction'])+' percentage points.',
        '', f"{selection['affected_cases']} cases have target edges; {selection['zero_edit_cases']} zero-edit cases retained. Half changes {int(selection['totals']['half_changed_edges'])} and full changes {int(selection['totals']['full_changed_edges'])} coordinates.", '',
        'Joint benefit requires lower bounds above +5 points for half minus original, above 0 for half minus full, AND above 0 for reduction in losses from original-success cases. Loss reduction uses all eligible cases as denominator; it does not select the cohort. Only a fixed half dose was tested. Signed-value interpolation is new + 0.5*(old-new), with current injury erasures and new weak repairs unchanged. Exact original and full endpoints reproduce E047, including packets and retained reader arrays. Secondary intervals are pointwise. Existing selected cases and one subsequent body do not qualify a serial rebuilding policy.']
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
    new_run(output, input_paths(), dict(experiment='E048', mode=a.mode, blocks=ids, config=asdict(cfg), cycle=asdict(cycle),
        variants=model.VARIANTS, source=str(source.relative_to(ROOT)), chronology=str(chronology.relative_to(ROOT)) if chronology else None,
        reference=str(reference.relative_to(ROOT)), dose_fractions=model.DOSES, source_policy='bridge_rewrite', source_policy_index=3, workers=a.workers))
    def launch(b):
        with (output/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'run.py'), '--mode', a.mode, '--worker', str(b)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=min(a.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]): print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, a.mode)
        finish(output, started, dict(experiment='E048', blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
