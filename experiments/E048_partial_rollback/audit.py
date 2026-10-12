"""Independent cohort, coordinate edits, trajectory replay and ratio inference."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, random, EXPECTED, pack, unpack, ports
from E022_reader_compensation.audit import masks_for, advance_compensated
import numpy as np

VARIANTS = ('original', 'half_rollback', 'full_rollback')
FIELDS = ('target_edges', 'half_changed_edges', 'full_changed_edges',
          'half_sign_changes', 'full_sign_changes', 'half_absolute_gain',
          'full_absolute_gain', 'half_l1_change', 'full_l1_change')
RULES, CUES = np.array([1., -1., 1., -1.]), np.array([1., -1.])


def load(path):
    with np.load(path, allow_pickle=False) as h: return {k:h[k] for k in h.files}


def equal_dict(a, b):
    assert set(a) == set(b)
    for k in a:
        assert a[k].dtype == b[k].dtype and a[k].shape == b[k].shape, k
        np.testing.assert_array_equal(a[k], b[k], err_msg=k)
        assert a[k].tobytes() == b[k].tobytes(), k


def edges(dead):
    result = np.empty(dead.shape[:-2]+(2, 16, 16), bool)
    for y in range(16):
        for x in range(16):
            result[..., 0, y, x] = ~(dead[..., y, x] | dead[..., y, (x+1) % 16])
            result[..., 1, y, x] = ~(dead[..., y, x] | dead[..., (y+1) % 16, x])
    return result


def reconstruct(incoming, outgoing, dead, index, block):
    old, new = unpack(incoming), unpack(outgoing)
    available = edges(dead)
    target = np.zeros_like(available)
    changed = np.stack([new.copy() for _ in range(3)])
    for c, (f, r, g) in enumerate(index.tolist()):
        for j in range(512):
            if not available[c].flat[j]: assert new[c].flat[j] == 0
            elif abs(old[c].flat[j]) > .5:
                target[c].flat[j] = abs(new[c].flat[j]) <= .5
        for j in np.flatnonzero(target[c]):
            changed[1, c].flat[j] = new[c].flat[j]+.5*(old[c].flat[j]-new[c].flat[j])
            changed[2, c].flat[j] = old[c].flat[j]
    half_changed, full_changed = changed[1] != new, changed[2] != new
    counts = np.stack([m.sum(axis=(-3, -2, -1)) for m in
        (target, half_changed, full_changed, np.sign(changed[1]) != np.sign(new), np.sign(changed[2]) != np.sign(new))]
        + [a.sum(axis=(-3, -2, -1)) for a in
           (abs(changed[1])-abs(new), abs(changed[2])-abs(new), abs(changed[1]-new), abs(changed[2]-new))], axis=-1)
    return dict(incoming=incoming, outgoing=outgoing, renewal_mask=dead, index=index,
        available=available, target=target, half_changed=half_changed, full_changed=full_changed, packets=pack(changed), counts=counts)


def replay(packet, index, block, cfg, cycle):
    """Incremental full-size noise draws, unlike production's concatenated draws."""
    C, R, p = len(index), cfg['recipients'], ports()
    grouped = {}
    masks = np.empty((C, 16, 16), bool)
    for i, (f, r, g) in enumerate(index.tolist()): grouped.setdefault(g+1, []).append((i, f, r))
    streams = {g:random('E022', block, 'develop', g) for g in grouped}
    for g, cases in grouped.items():
        full = masks_for(block, g, R, renewal=True)
        for i, f, r in cases: masks[i] = full[f, r, 1]
    assert np.all(masks.sum(axis=(-2, -1)) == 24) and not (masks & p.any(axis=0)).any()
    def draw():
        result = np.empty((C, 16, 16))
        for g, cases in grouped.items():
            full = streams[g].standard_normal((2, R, 16, 16))
            for i, f, r in cases: result[i] = full[f//2, r]
        return result
    w = unpack(packet)*edges(masks)[None]
    h, vertical = abs(w[..., 0, :, :]), abs(w[..., 1, :, :])
    denominator = h+np.roll(h, 1, -1)+vertical+np.roll(vertical, 1, -2)
    birth = cfg['birth_sd']*draw()
    v = np.empty((3, C, 2, 16, 16))
    for a in range(3):
        for cue in range(2): v[a, :, cue] = birth
    live = (~masks)[None, :, None]
    cues = CUES.reshape(1, 1, 2, 1)
    v *= live; v[..., p[0]] = cues
    trace = []
    for t in range(cycle['read_steps']):
        v = advance_compensated(v, w[:, :, None], denominator[:, :, None],
            draw()[None, :, None], cfg, t >= cycle['settling_steps'])
        v *= live; v[..., p[0]] = cues
        if t >= cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    trace = np.asarray(trace)
    return dict(masks=masks, effective_packets=pack(w), denominator=denominator, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0))


def inspect(task):
    run, source, chronology, reference, block, cfg, cycle = task
    started = time.monotonic(); cap_cpus(8)
    original = load(source/f'cases_{block:06d}.npz')
    original_ports = original['body_ports'][:, 3]
    target = RULES[None, :, None, None]*CUES[None, None, None, :]
    a, b = target*original_ports[..., 0], -target*original_ports[..., 1]
    correct = (a > cfg['margin']) & (b > cfg['margin'])
    np.testing.assert_array_equal(correct, original['body_correct'][:, 3])
    np.testing.assert_array_equal(np.minimum(a, b), original['body_margin'][:, 3])
    first = np.zeros((4, cfg['recipients']), np.int64); rows = []
    for f in range(4):
        for r in range(cfg['recipients']):
            for g in range(32):
                if not correct[g, f, r].all():
                    first[f, r] = g+1
                    if g < 31: rows.append((f, r, g+1))
                    break
    index = np.asarray(rows, dtype=np.int64).reshape(-1, 3)
    if chronology is not None:
        witness = load(chronology/f'measurements_{block:06d}.npz')
        np.testing.assert_array_equal(first, witness['events'][..., 0])
        for f, r, g in rows:
            assert witness['lineage'][f, r, 2] == 1
            assert witness['lineage'][f, r, 3] == correct[g, f, r].all()
    n = len(index); old = np.empty((n, 4096), np.uint8); outgoing = old.copy()
    dead = np.empty((n, 16, 16), bool); next_dead = dead.copy()
    expected = np.empty((n, 2, 2)); cache = {}
    def boundary(g):
        if g not in cache: cache[g] = load(source/f'boundary_{block:06d}_g{g}.npz')
        return cache[g]
    acquired = load(source/f'source_{block:06d}.npz')['acquired'][1] if any(g == 1 for _, _, g in rows) else None
    for i, (f, r, g) in enumerate(rows):
        old[i] = acquired[f] if g == 1 else boundary(g-1)['outgoing'][3, f, r]
        outgoing[i] = boundary(g)['outgoing'][3, f, r]
        dead[i] = boundary(g)['renewal_mask'][f, r]
        next_dead[i] = boundary(g+1)['renewal_mask'][f, r]
        expected[i] = boundary(g+1)['developed_mean_ports'][3, f, r]
    selection = reconstruct(old, outgoing, dead, index, block)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & edges(next_dead)).sum(axis=(-3, -2, -1)) for k in ('half_changed', 'full_changed')], axis=-1))
    equal_dict(selection, load(run/f'selection_{block:06d}.npz'))
    raw = replay(selection['packets'], index, block, cfg, cycle)
    equal_dict(raw, load(run/f'read_{block:06d}.npz'))
    np.testing.assert_array_equal(raw['masks'], next_dead)
    np.testing.assert_array_equal(raw['mean_ports'][0], expected)
    target = RULES[index[:, 0]][None, :, None]*CUES[None, None, :]
    a, b = raw['mean_ports'][..., 0]*target, -raw['mean_ports'][..., 1]*target
    cases = dict(correct=(a > cfg['margin']) & (b > cfg['margin']), margin=np.minimum(a, b), ports=raw['mean_ports'])
    equal_dict(cases, load(run/f'cases_{block:06d}.npz'))
    prior_selection = load(reference/f'selection_{block:06d}.npz')
    for k in ('index', 'first_failure', 'incoming', 'outgoing', 'renewal_mask', 'available', 'target'):
        equal_dict({k:selection[k]}, {k:prior_selection[k]})
    equal_dict({'packets':selection['packets'][[0, 2]]}, {'packets':prior_selection['packets'][[0, 1]]})
    prior_raw = load(reference/f'read_{block:06d}.npz')
    def controls(x, indices):
        return {k:v if k in ('masks', 'birth') else np.take(v, indices, axis=1 if k == 'late_ports' else 0) for k, v in x.items()}
    equal_dict(controls(raw, [0, 2]), controls(prior_raw, [0, 1]))
    prior_cases = load(reference/f'cases_{block:06d}.npz')
    equal_dict({k:v[[0, 2]] for k, v in cases.items()}, {k:v[[0, 1]] for k, v in prior_cases.items()})
    for i, (f, r, g) in enumerate(rows):
        for k, name in (('correct', 'body_correct'), ('margin', 'body_margin'), ('ports', 'body_ports')):
            np.testing.assert_array_equal(cases[k][0, i], original[name][g, 3, f, r])
    worker = json.loads((run/f'worker_{block}.json').read_text())
    assert worker['block'] == block and worker['eligible_cases'] == n and worker['original_next_body_matches_e041_exactly']
    assert worker['original_and_full_match_e047_byte_exactly']
    return dict(cases=cases, selection=selection, seconds=time.monotonic()-started)


def audit(run, workers):
    started = time.monotonic(); cap_cpus(8)
    m = verify(run); c = m['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, mode = (c[k] for k in ('config', 'cycle', 'blocks', 'mode'))
    source = ROOT/c['source']; chronology = ROOT/c['chronology'] if c['chronology'] else None; reference = ROOT/c['reference']
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    assert c['source'] == index['sources'][mode] and c['chronology'] == index['chronology'][mode]
    assert c['reference'] == index['reference'][mode]
    prior = verify(reference)['contract']
    assert prior['experiment'] == 'E047' and prior['mode'] == mode and prior['blocks'] == ids
    assert prior['config'] == cfg and prior['cycle'] == cycle
    original = verify(source)['contract']
    if chronology is not None: verify(chronology)
    assert original['experiment'] == 'E041' and original['mode'] == mode
    assert original['blocks'] == ids == ([900041] if mode != 'scientific' else list(range(32000, 32032)))
    assert cfg == original['config'] and cycle == dict(original['cycle'], settling_steps=4*original['cycle']['settling_steps'])
    assert c['variants'] == s['variants'] == list(VARIANTS)
    assert c['source_policy'] == s['source_policy'] == 'bridge_rewrite' and c['source_policy_index'] == s['source_policy_index'] == 3
    assert s['experiment'] == c['experiment'] == 'E048' and s['mode'] == mode
    assert s['blocks'] == ids and s['cfg'] == cfg and s['cycle'] == cycle
    assert s['prior_cases_reused'] and not s['multi_generation_policy_tested'] and not s['selection_uses_future_outcomes']
    assert s['original_next_body_matches_e041_exactly']
    assert s['original_and_full_match_e047_byte_exactly'] and s['dose_fractions'] == c['dose_fractions'] == [0., .5, 1.]
    if mode == 'scientific': assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect, [(run, source, chronology, reference, b, cfg, cycle) for b in ids]))
    cases, selections = [x['cases'] for x in results], [x['selection'] for x in results]
    den = np.array([len(x['index']) for x in selections], float)
    draw = random('E048', 'bootstrap', 'partial_rollback').integers(0, len(ids), (10000, len(ids)))
    checked = 0
    def check(n, d, st):
        nonlocal checked
        n, d = np.asarray(n, float), np.asarray(d, float)
        np.testing.assert_array_equal(n, st['block_numerators']); np.testing.assert_array_equal(d, st['block_denominators'])
        assert st['mean'] == (float(n.sum()/d.sum()) if d.sum() else None)
        dd = d[draw].sum(axis=1); valid = dd > 0
        expected = np.quantile(n[draw].sum(axis=1)[valid]/dd[valid], [.025, .975]).tolist() if valid.any() else [None, None]
        assert st['ci95'] == expected and st['bootstrap_valid'] == int(valid.sum()) and st['bootstrap_total'] == 10000
        checked += 1
    nums = dict(both_cues=np.array([x['correct'].all(axis=-1).sum(axis=1) for x in cases]),
        accuracy=np.array([x['correct'].sum(axis=(1, 2))/2 for x in cases]),
        margin=np.array([x['margin'].sum(axis=(1, 2))/2 for x in cases]))
    for j, v in enumerate(VARIANTS):
        for key, values in nums.items(): check(values[:, j], den, s['groups'][v][key])
    for hi, lo in ((1, 0), (2, 0), (1, 2)):
        name = VARIANTS[hi]+'_minus_'+VARIANTS[lo]
        for key, values in nums.items(): check(values[:, hi]-values[:, lo], den, s['contrasts'][name][key])
        tr = s['transitions'][name]
        paired = [x['correct'].all(axis=-1) for x in cases]
        for label, op in (('both_fail', lambda a,b:~a & ~b), ('rescued', lambda a,b:~a & b),
                          ('lost', lambda a,b:a & ~b), ('both_succeed', lambda a,b:a & b)):
            counts = [int(op(x[lo], x[hi]).sum()) for x in paired]
            assert tr['by_block'][label] == counts and tr['counts'][label] == sum(counts)
        assert tr['total'] == int(den.sum()) == sum(tr['counts'].values())
    for rule in (1, -1):
        masks = [RULES[x['index'][:, 0]] == rule for x in selections]
        rd = [m.sum() for m in masks]
        for j, v in enumerate(VARIANTS):
            check([x['correct'][j, m].all(axis=-1).sum() for x, m in zip(cases, masks)], rd, s['per_rule'][str(rule)][v])
    st = s['selection']
    totals = np.array([x['counts'].sum(axis=0) for x in selections])
    for j, name in enumerate(FIELDS):
        check(totals[:, j], den, st['mean_per_eligible_case'][name]); assert st['totals'][name] == float(totals[:, j].sum())
    visible = np.array([x['next_visible_counts'].sum(axis=0) for x in selections])
    assert st['next_visible_totals'] == visible.sum(axis=0).tolist()
    for j, name in enumerate(('half', 'full')): check(visible[:, j], den, st['next_visible_means'][name])
    affected = sum(int((x['counts'][:, 0] > 0).sum()) for x in selections)
    assert st['affected_cases'] == affected and st['zero_edit_cases'] == int(den.sum())-affected
    first = np.stack([x['first_failure'] for x in selections])
    cohort = dict(total_lineages=int(first.size), ever_failed=int((first > 0).sum()), never_failed=int((first == 0).sum()),
        first_failure_without_next=int((first == 32).sum()), eligible=int(den.sum()), eligible_by_block=den.astype(int).tolist())
    assert cohort == s['cohort'] and s['individual_observations'] == 6*int(den.sum())
    if mode == 'scientific':
        assert (cohort['total_lineages'], cohort['ever_failed'], cohort['eligible'], cohort['first_failure_without_next']) == (512, 307, 301, 6)
        assert nums['both_cues'][:, 0].sum() == 174
        assert nums['both_cues'][:, 2].sum() == 193
        assert s['transitions']['full_rollback_minus_original']['counts']['rescued'] == 55
        assert s['transitions']['full_rollback_minus_original']['counts']['lost'] == 36
    for lo in (0, 2): check(nums['both_cues'][:, 1]-nums['both_cues'][:, lo], den, s['primary'][VARIANTS[lo]])
    losses = np.array([[int((x['correct'][0].all(axis=-1) & ~x['correct'][j].all(axis=-1)).sum()) for j in (1, 2)] for x in cases])
    for j, name in enumerate(('half_rollback', 'full_rollback')): check(losses[:, j], den, s['loss_rates'][name])
    check(losses[:, 1]-losses[:, 0], den, s['primary']['loss_reduction'])
    thresholds = dict(original=.05, full_rollback=0., loss_reduction=0.)
    assert set(s['primary']) == set(thresholds)
    passed = all(s['primary'][k]['ci95'][0] is not None and s['primary'][k]['ci95'][0] > threshold for k, threshold in thresholds.items())
    assert s['primary_decision'] == (passed if mode == 'scientific' else None)
    status = 'HALF_ROLLBACK_JOINT_BENEFIT_ESTABLISHED' if passed else 'HALF_ROLLBACK_JOINT_BENEFIT_NOT_ESTABLISHED'
    assert s['status'] == (status if mode == 'scientific' else 'TECHNICAL_ONLY')
    verify(run); verify(source); verify(reference)
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started,
        worker_seconds=[x['seconds'] for x in results], blocks=len(ids), cohort=cohort, summaries_checked=checked,
        individual_observations=s['individual_observations'], all_returned_read_arrays_replayed=True,
        cohort_and_every_edit_independently_reconstructed=True, original_next_body_matches_e041_exactly=True,
        original_and_full_match_e047_byte_exactly=True,
        source_packets_unchanged=True, all_scores_statistics_and_decisions_verified=True,
        all_paired_rescue_and_loss_counts_verified=True, complete_sha256=sha(run/'COMPLETE.json'),
        audit_code_sha256=sha(__file__), workers=workers)
    dest = run/'INDEPENDENT_AUDIT.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
