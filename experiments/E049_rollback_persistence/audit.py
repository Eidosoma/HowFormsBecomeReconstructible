"""Independent capture, serial replay, source controls and third-body inference."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, random, EXPECTED, pack, unpack, ports, advance
from E048_partial_rollback import audit as reader
import numpy as np

VARIANTS = ('original', 'half_rollback', 'full_rollback')
FIELDS = reader.FIELDS
RULES, CUES = np.array([1., -1., 1., -1.]), np.array([1., -1.])
load, equal_dict, edges, reconstruct = reader.load, reader.equal_dict, reader.edges, reader.reconstruct
READ_KEYS = ('masks', 'effective_packets', 'denominator', 'birth', 'end', 'late_ports', 'mean_ports')
EPISODES = ('sustained', 'any_recovery', 'relapse_after_first')


def capture(body, beta):
    """Scalar coordinate capture with the E041 positive-zero mean reduction."""
    x = np.tanh(beta*body)
    fresh = np.empty((3, body.shape[1], 2, 16, 16))
    for v, c, direction, y, xx in np.ndindex(fresh.shape):
        yy, nx = (y, (xx+1) % 16) if direction == 0 else ((y+1) % 16, xx)
        a, b = x[v, c, :, y, xx], x[v, c, :, yy, nx]
        difference = ((a[0]-a[1])/2)*((b[0]-b[1])/2)
        ordinary = np.float64(0.)
        ordinary += a[0]*b[0]; ordinary += a[1]*b[1]; ordinary /= 2
        fresh[v, c, direction, y, xx] = difference if difference != 0 else ordinary
    return pack(fresh)


def replay(packets, index, offset, block, cfg, cycle):
    assert offset in (1, 2, 3) and np.all((index[:, 2] >= 1) & (index[:, 2] <= 29))
    shifted = index.copy(); shifted[:, 2] += offset-1
    raw = reader.replay(packets, shifted, block, cfg, cycle)
    computed = capture(raw['end'], cfg['writer_beta'])
    available = edges(raw['masks'])
    assert not (unpack(computed)*(~available)[None]).any()
    groups = {}
    for j, (f, r, g) in enumerate(index.tolist()): groups.setdefault(g+offset, []).append((j, f, r))
    streams = {g:random('E022', block, 'write', g) for g in groups}
    v = raw['end'].copy(); p = ports(); live = (~raw['masks'])[None, :, None]
    cue = CUES.reshape(1, 1, 2, 1); scaffold = available[None, :, None].astype(float)
    hashes = np.empty((cycle['write_steps'], 3, len(index), 32), np.uint8)
    for t in range(cycle['write_steps']):
        noise = np.empty((len(index), 16, 16))
        for g, cases in groups.items():
            full = streams[g].standard_normal((2, cfg['recipients'], 16, 16))
            for j, f, r in cases: noise[j] = full[f//2, r]
        v = advance(v, scaffold, 2., noise[None, :, None], cfg)
        v *= live; v[..., p[0]] = cue
        for variant in range(3):
            for j in range(len(index)):
                hashes[t, variant, j] = np.frombuffer(hashlib.sha256(v[variant, j].astype('<f8').tobytes(order='C')).digest(), np.uint8)
    fresh = unpack(computed); chosen = np.zeros_like(fresh)
    for j in range(len(index)):
        for variant in range(3): chosen[variant, j][available[j]] = fresh[variant, j][available[j]]
    raw.update(incoming=packets.copy(), computed_packets=computed, outgoing=pack(chosen), write_end=v, write_state_hashes=hashes)
    return raw


def inspect(task):
    run, source, chronology, reference, block, cfg, cycle = task
    started = time.monotonic(); cap_cpus(8)
    original = load(source/f'cases_{block:06d}.npz'); original_ports = original['body_ports'][:, 3]
    target = RULES[None, :, None, None]*CUES[None, None, None, :]
    a, b = target*original_ports[..., 0], -target*original_ports[..., 1]
    correct = (a > cfg['margin']) & (b > cfg['margin'])
    equal_dict({'correct':correct, 'margin':np.minimum(a, b)},
        {'correct':original['body_correct'][:, 3], 'margin':original['body_margin'][:, 3]})
    first = np.zeros((4, cfg['recipients']), np.int64); rows = []
    for f in range(4):
        for r in range(cfg['recipients']):
            for g in range(32):
                if not correct[g, f, r].all():
                    first[f, r] = g+1
                    if g < 29: rows.append((f, r, g+1))
                    break
    index = np.asarray(rows, np.int64).reshape(-1, 3)
    if chronology is not None:
        witness = load(chronology/f'measurements_{block:06d}.npz')
        np.testing.assert_array_equal(first, witness['events'][..., 0])
        np.testing.assert_array_equal((first > 0) & (first <= 29), witness['lineage'][..., 4].astype(bool))
    n = len(index); old = np.empty((n, 4096), np.uint8); outgoing = old.copy()
    dead = np.empty((n, 16, 16), bool); next_dead = dead.copy(); cache = {}
    def boundary(g):
        if g not in cache: cache[g] = load(source/f'boundary_{block:06d}_g{g}.npz')
        return cache[g]
    acquired = load(source/f'source_{block:06d}.npz')['acquired'][1] if any(g == 1 for _, _, g in rows) else None
    for j, (f, r, g) in enumerate(rows):
        old[j] = acquired[f] if g == 1 else boundary(g-1)['outgoing'][3, f, r]
        outgoing[j] = boundary(g)['outgoing'][3, f, r]
        dead[j] = boundary(g)['renewal_mask'][f, r]; next_dead[j] = boundary(g+1)['renewal_mask'][f, r]
    selection = reconstruct(old, outgoing, dead, index, block)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & edges(next_dead)).sum(axis=(-3, -2, -1)) for k in ('half_changed', 'full_changed')], axis=-1))
    prior_selection = load(reference/f'selection_{block:06d}.npz')
    lookup = {tuple(row):j for j, row in enumerate(prior_selection['index'].tolist())}
    positions = np.array([lookup[tuple(row)] for row in rows], np.int64)
    for k, value in selection.items():
        expected = prior_selection[k] if k == 'first_failure' else prior_selection[k][:, positions] if k == 'packets' else prior_selection[k][positions]
        equal_dict({k:value}, {k:expected})
    selection['reference_positions'] = positions
    equal_dict(selection, load(run/f'selection_{block:06d}.npz'))
    previous = selection['packets'].copy(); results = dict(correct=[], margin=[], ports=[])
    prior_read = load(reference/f'read_{block:06d}.npz'); prior_cases = load(reference/f'cases_{block:06d}.npz')
    for offset in (1, 2, 3):
        raw = replay(previous, index, offset, block, cfg, cycle)
        equal_dict(raw, load(run/f'boundary_{block:06d}_d{offset}.npz'))
        target = RULES[index[:, 0]][None, :, None]*CUES[None, None, :]
        a, b = raw['mean_ports'][..., 0]*target, -raw['mean_ports'][..., 1]*target
        scores = dict(correct=(a > cfg['margin']) & (b > cfg['margin']), margin=np.minimum(a, b), ports=raw['mean_ports'])
        if offset == 1:
            for k in READ_KEYS:
                expected = prior_read[k][positions] if k in ('masks', 'birth') else np.take(prior_read[k], positions, axis=2 if k == 'late_ports' else 1)
                equal_dict({k:raw[k]}, {k:expected})
            for k in scores: equal_dict({k:scores[k]}, {k:prior_cases[k][:, positions]})
        for j, (f, r, g) in enumerate(rows):
            src = boundary(g+offset)
            equal_dict({'outgoing':raw['outgoing'][0, j], 'mask':raw['masks'][j]},
                {'outgoing':src['outgoing'][3, f, r], 'mask':src['renewal_mask'][f, r]})
            for k, name in (('correct', 'body_correct'), ('margin', 'body_margin'), ('ports', 'body_ports')):
                equal_dict({k:scores[k][0, j]}, {k:original[name][g+offset-1, 3, f, r]})
        for k in results: results[k].append(scores[k])
        previous = raw['outgoing'].copy()
    cases = {k:np.stack(v) for k, v in results.items()}
    equal_dict(cases, load(run/f'cases_{block:06d}.npz'))
    if chronology is not None:
        for j, (f, r, _) in enumerate(rows): assert cases['correct'][:, 0, j].all(axis=-1).any() == witness['lineage'][f, r, 5]
    worker = json.loads((run/f'worker_{block}.json').read_text())
    assert worker['block'] == block and worker['eligible_cases'] == n
    assert worker['first_body_matches_e048_byte_exactly'] and worker['original_three_bodies_and_outgoing_match_e041_byte_exactly'] and worker['rollback_applied_once']
    return dict(cases=cases, selection=selection, seconds=time.monotonic()-started)


def audit(run, workers):
    started = time.monotonic(); cap_cpus(8)
    m = verify(run); c = m['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, mode = (c[k] for k in ('config', 'cycle', 'blocks', 'mode'))
    source, reference = ROOT/c['source'], ROOT/c['reference']; chronology = ROOT/c['chronology'] if c['chronology'] else None
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    assert c['source'] == index['sources'][mode] and c['reference'] == index['reference'][mode] and c['chronology'] == index['chronology'][mode]
    original, prior = verify(source)['contract'], verify(reference)['contract']
    if chronology is not None: verify(chronology)
    assert original['experiment'] == 'E041' and prior['experiment'] == 'E048' and original['mode'] == prior['mode'] == mode
    assert cfg == original['config'] == prior['config'] and cycle == prior['cycle'] == dict(original['cycle'], settling_steps=4*original['cycle']['settling_steps'])
    assert original['blocks'] == prior['blocks'] == ids == ([900041] if mode != 'scientific' else list(range(32000, 32032)))
    assert c['variants'] == s['variants'] == list(VARIANTS) and s['dose_fractions'] == c['dose_fractions'] == [0., .5, 1.]
    assert c['body_offsets'] == s['body_offsets'] == [1, 2, 3] and c['primary_body_offset'] == s['primary_body_offset'] == 3
    assert c['rollback_applied_once'] and s['rollback_applied_once'] and s['ordinary_rewriting_after_rollback']
    assert c['source_policy'] == s['source_policy'] == 'bridge_rewrite' and c['source_policy_index'] == s['source_policy_index'] == 3
    assert s['experiment'] == c['experiment'] == 'E049' and s['mode'] == mode
    assert s['blocks'] == ids and s['cfg'] == cfg and s['cycle'] == cycle
    assert s['prior_cases_reused'] and not s['indefinite_or_fresh_policy_qualified'] and not s['selection_uses_future_outcomes']
    assert s['first_body_matches_e048_byte_exactly'] and s['original_three_bodies_and_outgoing_match_e041_byte_exactly']
    if mode == 'scientific': assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect, [(run, source, chronology, reference, b, cfg, cycle) for b in ids]))
    cases, selections = [x['cases'] for x in results], [x['selection'] for x in results]
    den = np.array([len(x['index']) for x in selections], float)
    draw = random('E049', 'bootstrap', 'rollback_persistence').integers(0, len(ids), (10000, len(ids)))
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
    third = None
    for d in range(3):
        key = str(d+1)
        nums = dict(both_cues=np.array([x['correct'][d].all(axis=-1).sum(axis=1) for x in cases]),
            accuracy=np.array([x['correct'][d].sum(axis=(1, 2))/2 for x in cases]),
            margin=np.array([x['margin'][d].sum(axis=(1, 2))/2 for x in cases]))
        for j, v in enumerate(VARIANTS):
            for metric, values in nums.items(): check(values[:, j], den, s['groups'][key][v][metric])
        for hi, lo in ((1, 0), (2, 0), (1, 2)):
            name = VARIANTS[hi]+'_minus_'+VARIANTS[lo]
            for metric, values in nums.items(): check(values[:, hi]-values[:, lo], den, s['contrasts'][key][name][metric])
            tr = s['transitions'][key][name]; paired = [x['correct'][d].all(axis=-1) for x in cases]
            for label, op in (('both_fail', lambda a,b:~a & ~b), ('rescued', lambda a,b:~a & b),
                ('lost', lambda a,b:a & ~b), ('both_succeed', lambda a,b:a & b)):
                counts = [int(op(x[lo], x[hi]).sum()) for x in paired]
                assert tr['by_block'][label] == counts and tr['counts'][label] == sum(counts)
            assert tr['total'] == int(den.sum()) == sum(tr['counts'].values())
        for rule in (1, -1):
            masks = [RULES[x['index'][:, 0]] == rule for x in selections]
            rd = [mask.sum() for mask in masks]
            for j, v in enumerate(VARIANTS): check([x['correct'][d, j, mask].all(axis=-1).sum() for x, mask in zip(cases, masks)], rd, s['per_rule'][key][str(rule)][v])
        losses = np.array([[int((x['correct'][d, 0].all(axis=-1) & ~x['correct'][d, j].all(axis=-1)).sum()) for j in (1, 2)] for x in cases])
        for j, name in enumerate(('half_rollback', 'full_rollback')): check(losses[:, j], den, s['loss_rates'][key][name])
        check(losses[:, 1]-losses[:, 0], den, s['loss_reduction'][key])
        if d == 2: third = nums, losses
    nums, losses = third
    for lo in (0, 2): check(nums['both_cues'][:, 1]-nums['both_cues'][:, lo], den, s['primary'][VARIANTS[lo]])
    check(losses[:, 1]-losses[:, 0], den, s['primary']['loss_reduction'])
    episode_values = []
    for x in cases:
        b = x['correct'].all(axis=-1)
        episode_values.append(dict(sustained=b[0] & b[1] & b[2], any_recovery=b[0] | b[1] | b[2], relapse_after_first=b[0] & (~b[1] | ~b[2])))
    for name in EPISODES:
        for j, v in enumerate(VARIANTS): check([x[name][j].sum() for x in episode_values], den, s['episode'][name][v])
        for hi, lo in ((1, 0), (2, 0), (1, 2)):
            check([x[name][hi].sum()-x[name][lo].sum() for x in episode_values], den, s['episode_contrasts'][name][VARIANTS[hi]+'_minus_'+VARIANTS[lo]])
    for j, v in enumerate(VARIANTS):
        pattern = s['patterns'][v]
        assert set(pattern['by_block']) == {'FFF', 'FFS', 'FSF', 'FSS', 'SFF', 'SFS', 'SSF', 'SSS'}
        for label in pattern['by_block']:
            counts = []
            target = np.array([z == 'S' for z in label])[:, None]
            for x in cases: counts.append(int((x['correct'][:, j].all(axis=-1) == target).all(axis=0).sum()))
            assert counts == pattern['by_block'][label] and pattern['counts'][label] == sum(counts)
        assert sum(pattern['counts'].values()) == int(den.sum())
    st = s['selection']; totals = np.array([x['counts'].sum(axis=0) for x in selections])
    for j, name in enumerate(FIELDS):
        check(totals[:, j], den, st['mean_per_eligible_case'][name]); assert st['totals'][name] == float(totals[:, j].sum())
    visible = np.array([x['next_visible_counts'].sum(axis=0) for x in selections])
    assert st['next_visible_totals'] == visible.sum(axis=0).tolist()
    for j, name in enumerate(('half', 'full')): check(visible[:, j], den, st['next_visible_means'][name])
    affected = sum(int((x['counts'][:, 0] > 0).sum()) for x in selections)
    assert st['affected_cases'] == affected and st['zero_edit_cases'] == int(den.sum())-affected
    first = np.stack([x['first_failure'] for x in selections])
    cohort = dict(total_lineages=int(first.size), ever_failed=int((first > 0).sum()), never_failed=int((first == 0).sum()),
        first_failure_without_three=int((first > 29).sum()), eligible=int(den.sum()), eligible_by_block=den.astype(int).tolist())
    assert cohort == s['cohort'] and s['individual_observations'] == 18*int(den.sum())
    if mode == 'scientific':
        assert (cohort['total_lineages'], cohort['ever_failed'], cohort['eligible'], cohort['first_failure_without_three']) == (512, 307, 281, 26)
        assert sum(x['any_recovery'][0].sum() for x in episode_values) == 243
    thresholds = dict(original=.05, full_rollback=0., loss_reduction=0.)
    assert set(s['primary']) == set(thresholds)
    passed = all(s['primary'][k]['ci95'][0] is not None and s['primary'][k]['ci95'][0] > t for k, t in thresholds.items())
    assert s['primary_decision'] == (passed if mode == 'scientific' else None)
    status = 'THIRD_BODY_JOINT_BENEFIT_ESTABLISHED' if passed else 'THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED'
    assert s['status'] == (status if mode == 'scientific' else 'TECHNICAL_ONLY')
    verify(run); verify(source); verify(reference)
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, worker_seconds=[x['seconds'] for x in results],
        blocks=len(ids), cohort=cohort, summaries_checked=checked, individual_observations=s['individual_observations'],
        all_returned_arrays_and_write_state_commitments_replayed=True, cohort_and_every_initial_edit_independently_reconstructed=True,
        first_body_matches_e048_byte_exactly=True, original_three_bodies_and_outgoing_match_e041_byte_exactly=True,
        serial_packet_chain_verified=True, rollback_applied_once=True, source_packets_unchanged=True,
        all_scores_statistics_patterns_and_decisions_verified=True, all_paired_rescue_and_loss_counts_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    dest = run/'INDEPENDENT_AUDIT.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
