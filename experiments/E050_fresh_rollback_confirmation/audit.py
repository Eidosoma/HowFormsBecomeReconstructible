"""Independent teaching, 32 unchanged bodies, rollback chains and inference."""
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
from E015_functional_inheritance.audit import verify, random, EXPECTED, pack, unpack, ports, advance, pair
from E022_reader_compensation.audit import masks_for, advance_compensated, correlations
from E049_rollback_persistence import audit as branch
import numpy as np

VARIANTS, FIELDS, EPISODES = branch.VARIANTS, branch.FIELDS, branch.EPISODES
RULES, CUES = np.array([1., -1., 1., -1.]), np.array([1., -1.])
load, equal_dict, edges, reconstruct = branch.load, branch.equal_dict, branch.edges, branch.reconstruct


def teaching(block, cfg):
    p = ports(); records, pieces, births, ends, captured = [], [], [], [], []
    for mode in range(2):
        total = np.zeros((4, 2, 16, 16)); episodes, bb, ee, cc = [], [], [], []
        for c, cue in enumerate(CUES):
            stream = random('E016', block, 'teach', 0 if mode == 1 else c)
            sign = -1. if mode == 1 and c == 1 else 1.
            v = sign*cfg['birth_sd']*pair(stream.standard_normal((2, 16, 16))); bb.append(v.copy())
            target = np.column_stack((np.full(4, cue), RULES*cue, -RULES*cue))
            for q in range(3): v[:, p[q]] = target[:, q, None]
            piece = np.zeros_like(total); states = []
            for t in range(cfg['teach_steps']):
                noise = sign*pair(stream.standard_normal((2, 16, 16)))
                v = advance(v, np.ones((2, 16, 16)), cfg['teacher_gain'], noise, cfg)
                for q in range(3): v[:, p[q]] = target[:, q, None]
                if t >= cfg['teach_steps']-cfg['capture_steps']:
                    states.append(v.copy()); corr = correlations(v, cfg['writer_beta'])
                    piece += corr; total += corr
            ee.append(v.copy()); cc.append(np.stack(states)); episodes.append(piece/cfg['capture_steps'])
        pieces.append(np.stack(episodes)); records.append(total/(2*cfg['capture_steps']))
        births.append(bb); ends.append(ee); captured.append(cc)
    captured = np.asarray(captured)
    assert np.max(abs(captured[1, 0]+captured[1, 1])) <= 1e-10
    signs = np.ones((4, 16, 16)); signs[:, p[1]], signs[:, p[2]] = RULES[:, None], -RULES[:, None]
    engineered = np.empty((4, 2, 16, 16))
    for y, x in np.ndindex(16, 16):
        engineered[:, 0, y, x] = signs[:, y, x]*signs[:, y, (x+1)%16]
        engineered[:, 1, y, x] = signs[:, y, x]*signs[:, (y+1)%16, x]
    records.append(engineered); weights = np.stack(records)
    return dict(ports=p, rules=RULES.copy(), cues=CUES.copy(), teach_birth=np.array(births),
        teach_end=np.array(ends), capture_states=captured, episode_weights=np.stack(pieces),
        weights=weights, acquired=pack(weights), engineered_signs=signs)


def baseline_capture(body, beta):
    x = np.tanh(beta*body); fresh = np.empty((4, body.shape[1], 2, 16, 16))
    for f, r, direction, y, xx in np.ndindex(fresh.shape):
        yy, nx = (y, (xx+1)%16) if direction == 0 else ((y+1)%16, xx)
        a, b = x[f, r, :, y, xx], x[f, r, :, yy, nx]
        contrast = ((a[0]-a[1])/2)*((b[0]-b[1])/2)
        ordinary = np.float64(0.); ordinary += a[0]*b[0]; ordinary += a[1]*b[1]; ordinary /= 2
        fresh[f, r, direction, y, xx] = contrast if contrast != 0 else ordinary
    return pack(fresh)


def replay_baseline(packet, block, generation, cfg, cycle):
    assert 1 <= generation <= 32 and packet.shape == (4, cfg['recipients'], 4096)
    masks = masks_for(block, generation, cfg['recipients'], renewal=True)[:, :, 1]
    p = ports(); assert np.all(masks.sum(axis=(-2, -1)) == 24) and not (masks & p.any(axis=0)).any()
    available = edges(masks); w = unpack(packet)*available
    denominator = np.empty((4, cfg['recipients'], 16, 16)); abs_w = abs(w)
    for y, x in np.ndindex(16, 16):
        denominator[:, :, y, x] = abs_w[:, :, 0, y, x]+abs_w[:, :, 0, y, (x-1)%16]+abs_w[:, :, 1, y, x]+abs_w[:, :, 1, (y-1)%16, x]
    stream = random('E022', block, 'develop', generation)
    birth = cfg['birth_sd']*pair(stream.standard_normal((2, cfg['recipients'], 16, 16)))
    v = np.empty((4, cfg['recipients'], 2, 16, 16))
    for cue in range(2): v[:, :, cue] = birth
    alive = (~masks)[:, :, None]; cue_values = CUES.reshape(1, 1, 2, 1)
    v *= alive; v[..., p[0]] = cue_values; late = []
    for t in range(cycle['read_steps']):
        noise = pair(stream.standard_normal((2, cfg['recipients'], 16, 16)))[:, :, None]
        v = advance_compensated(v, w[:, :, None], denominator[:, :, None], noise, cfg, t >= cycle['settling_steps'])
        v *= alive; v[..., p[0]] = cue_values
        if t >= cycle['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    end = v.copy(); late = np.array(late); computed = baseline_capture(end, cfg['writer_beta'])
    assert not (unpack(computed)*(~available)).any()
    scaffold = available[:, :, None].astype(float); stream = random('E022', block, 'write', generation)
    hashes = np.empty((cycle['write_steps'], 4, cfg['recipients'], 32), np.uint8)
    for t in range(cycle['write_steps']):
        noise = pair(stream.standard_normal((2, cfg['recipients'], 16, 16)))[:, :, None]
        v = advance(v, scaffold, 2., noise, cfg); v *= alive; v[..., p[0]] = cue_values
        for f in range(4):
            for r in range(cfg['recipients']):
                hashes[t, f, r] = np.frombuffer(hashlib.sha256(v[f, r].astype('<f8').tobytes(order='C')).digest(), np.uint8)
    fresh = unpack(computed); chosen = np.zeros_like(fresh)
    chosen[available] = fresh[available]
    return dict(incoming=packet.copy(), masks=masks, effective_packets=pack(w), denominator=denominator,
        birth=birth, end=end, late_ports=late, mean_ports=late.mean(axis=0), computed_packets=computed,
        outgoing=pack(chosen), write_end=v, write_state_hashes=hashes)


def baseline_score(values, cfg):
    target = RULES[:, None, None]*CUES[None, None, :]
    a, b = target*values[..., 0], -target*values[..., 1]
    return dict(correct=(a > cfg['margin']) & (b > cfg['margin']), margin=np.minimum(a, b), ports=values)


def inspect(task):
    run, block, cfg, cycle, mode = task; started = time.monotonic(); cap_cpus(8)
    spec = json.loads((HERE/'SOURCE_DATA.json').read_text())
    source = teaching(block, cfg); equal_dict(source, load(run/f'source_{block:06d}.npz'))
    reference = ROOT/spec['baseline_reference'][mode] if mode != 'scientific' else None
    if reference is not None:
        saved = load(reference/f'source_{block:06d}.npz'); meta = json.loads(saved.pop('__index__').tobytes())
        equal_dict({k:v for k,v in source.items() if k != 'capture_states'}, saved)
        assert hashlib.sha256(source['capture_states'].tobytes()).hexdigest() == meta['arrays']['capture_states']['sha256']
        reference_cases = load(reference/f'cases_{block:06d}.npz')
    packet = source['acquired'][1, :, None].repeat(cfg['recipients'], axis=1)
    baseline = dict(correct=[], margin=[], ports=[]); cache = {}
    for g in range(1, 33):
        raw = replay_baseline(packet, block, g, cfg, cycle)
        equal_dict(raw, load(run/f'baseline_{block:06d}_g{g}.npz'))
        scores = baseline_score(raw['mean_ports'], cfg)
        if reference is not None:
            prior = load(reference/f'boundary_{block:06d}_g{g}.npz')
            equal_dict({'packet':raw['outgoing'], 'mask':raw['masks']}, {'packet':prior['outgoing'][3], 'mask':prior['renewal_mask']})
            for k in scores: equal_dict({k:scores[k]}, {k:reference_cases['body_'+k][g-1, 3]})
        cache[g] = {k:raw[k] for k in ('incoming', 'outgoing', 'masks')}
        packet = raw['outgoing'].copy()
        for k in scores: baseline[k].append(scores[k])
    baseline = {k:np.stack(v) for k,v in baseline.items()}
    equal_dict(baseline, load(run/f'baseline_cases_{block:06d}.npz'))
    first = np.zeros((4, cfg['recipients']), np.int64); rows = []
    for f in range(4):
        for r in range(cfg['recipients']):
            for g in range(32):
                if not baseline['correct'][g, f, r].all():
                    first[f, r] = g+1
                    if g < 29: rows.append((f, r, g+1))
                    break
    index = np.asarray(rows, np.int64).reshape(-1, 3); n = len(rows)
    old = np.empty((n, 4096), np.uint8); new = old.copy()
    dead = np.empty((n, 16, 16), bool); next_dead = dead.copy()
    for j, (f, r, g) in enumerate(rows):
        old[j] = cache[g]['incoming'][f, r]; new[j] = cache[g]['outgoing'][f, r]
        dead[j] = cache[g]['masks'][f, r]; next_dead[j] = cache[g+1]['masks'][f, r]
    selection = reconstruct(old, new, dead, index, block)
    selection.update(first_failure=first, next_visible_counts=np.stack([
        (selection[k] & edges(next_dead)).sum(axis=(-3, -2, -1)) for k in ('half_changed', 'full_changed')], axis=-1))
    equal_dict(selection, load(run/f'selection_{block:06d}.npz'))
    branch_reference = ROOT/spec['branch_reference'][mode] if mode != 'scientific' else None
    if branch_reference is not None:
        expected = load(branch_reference/f'selection_{block:06d}.npz'); expected.pop('reference_positions')
        equal_dict(selection, expected)
    packets = selection['packets'].copy(); cases = dict(correct=[], margin=[], ports=[])
    for offset in (1, 2, 3):
        raw = branch.replay(packets, index, offset, block, cfg, cycle)
        equal_dict(raw, load(run/f'boundary_{block:06d}_d{offset}.npz'))
        if branch_reference is not None: equal_dict(raw, load(branch_reference/f'boundary_{block:06d}_d{offset}.npz'))
        target = RULES[index[:, 0]][None, :, None]*CUES[None, None, :]
        a, b = target*raw['mean_ports'][..., 0], -target*raw['mean_ports'][..., 1]
        scores = dict(correct=(a > cfg['margin']) & (b > cfg['margin']), margin=np.minimum(a, b), ports=raw['mean_ports'])
        for j, (f, r, g) in enumerate(rows):
            equal_dict({'outgoing':raw['outgoing'][0, j], 'mask':raw['masks'][j]},
                {'outgoing':cache[g+offset]['outgoing'][f, r], 'mask':cache[g+offset]['masks'][f, r]})
            for k in scores: equal_dict({k:scores[k][0, j]}, {k:baseline[k][g+offset-1, f, r]})
        packets = raw['outgoing'].copy()
        for k in scores: cases[k].append(scores[k])
    cases = {k:np.stack(v) for k,v in cases.items()}; equal_dict(cases, load(run/f'cases_{block:06d}.npz'))
    if branch_reference is not None: equal_dict(cases, load(branch_reference/f'cases_{block:06d}.npz'))
    worker = json.loads((run/f'worker_{block}.json').read_text())
    assert worker['block'] == block and worker['generations'] == 32 and worker['eligible_cases'] == n
    assert worker['source_sha256'] == sha(run/f'source_{block:06d}.npz')
    assert worker['original_three_bodies_match_own_baseline_byte_exactly'] and worker['rollback_applied_once']
    assert worker['technical_baseline_and_branch_reference_match'] == (mode != 'scientific')
    return dict(cases=cases, selection=selection, seconds=time.monotonic()-started)


def audit(run, workers):
    started = time.monotonic(); cap_cpus(8)
    m = verify(run); c = m['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, mode = (c[k] for k in ('config', 'cycle', 'blocks', 'mode'))
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    prior_ids = set()
    for rel, digest in index['prior_manifest_sha256'].items():
        assert sha(ROOT/rel) == digest; prior_ids.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(prior_ids) == index['prior_block_ids'] and not prior_ids.intersection(index['blocks'])
    assert index['blocks'] == list(range(33000, 33032)) and ids == (index['blocks'] if mode == 'scientific' else [900041])
    assert s['experiment'] == c['experiment'] == 'E050' and s['mode'] == mode and s['blocks'] == ids
    assert s['cfg'] == cfg and s['cycle'] == cycle
    expected_cfg = dict(EXPECTED); expected_cycle = dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    if mode == 'fixture':
        expected_cfg.update(recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        expected_cycle.update(read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark':
        expected_cfg.update(recipients=1); expected_cycle.update(read_steps=128, settling_steps=64)
    else: assert mode == 'scientific'
    assert cfg == expected_cfg and cycle == expected_cycle
    assert c['variants'] == s['variants'] == list(VARIANTS) and c['dose_fractions'] == s['dose_fractions'] == [0., .5, 1.]
    assert c['body_offsets'] == s['body_offsets'] == [1, 2, 3] and c['primary_body_offset'] == s['primary_body_offset'] == 3
    assert c['rollback_applied_once'] and s['rollback_applied_once'] and s['ordinary_rewriting_after_rollback']
    assert c['source_policy'] == s['source_policy'] == 'bridge_rewrite' and c['source_policy_index'] == s['source_policy_index'] == 3
    assert not c['prior_cases_pooled'] and not s['prior_cases_pooled'] and not s['prior_cases_reused']
    assert c['fresh_histories'] == s['independent_fresh_histories'] == (mode == 'scientific') and c['original_generations'] == 32
    assert not s['indefinite_or_deployable_policy_qualified'] and not s['selection_uses_future_outcomes']
    assert s['original_three_bodies_match_own_baseline_byte_exactly']
    assert s['technical_baseline_and_branch_reference_match'] == (True if mode != 'scientific' else None)
    if mode != 'scientific':
        for refs in ('baseline_reference', 'branch_reference'): verify(ROOT/index[refs][mode])
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect, [(run, b, cfg, cycle, mode) for b in ids]))
    cases, selections = [x['cases'] for x in results], [x['selection'] for x in results]
    den = np.array([len(x['index']) for x in selections], float)
    draw = random('E050', 'bootstrap', 'fresh_rollback_confirmation').integers(0, len(ids), (10000, len(ids)))
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
        assert cohort['total_lineages'] == 512
        assert cohort['eligible']+cohort['first_failure_without_three'] == cohort['ever_failed']
        assert cohort['ever_failed']+cohort['never_failed'] == 512
    thresholds = dict(original=.05, full_rollback=0., loss_reduction=0.)
    assert set(s['primary']) == set(thresholds)
    passed = all(s['primary'][k]['ci95'][0] is not None and s['primary'][k]['ci95'][0] > t for k, t in thresholds.items())
    assert s['primary_decision'] == (passed if mode == 'scientific' else None)
    status = 'FRESH_THIRD_BODY_JOINT_BENEFIT_ESTABLISHED' if passed else 'FRESH_THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED'
    assert s['status'] == (status if mode == 'scientific' else 'TECHNICAL_ONLY')
    assert s['baseline_individual_observations'] == 32*len(ids)*4*cfg['recipients']*2
    verify(run)
    for rel, digest in {**index['sha256'], **index['prior_manifest_sha256']}.items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, worker_seconds=[x['seconds'] for x in results],
        blocks=len(ids), cohort=cohort, summaries_checked=checked, individual_observations=s['individual_observations'],
        baseline_individual_observations=s['baseline_individual_observations'], all_teaching_and_32_baseline_bodies_replayed=True,
        all_returned_arrays_and_write_state_commitments_replayed=True, cohort_and_every_initial_edit_independently_reconstructed=True,
        original_three_bodies_match_own_baseline_byte_exactly=True,
        technical_baseline_and_branch_reference_match=(True if mode != 'scientific' else None), block_ids_and_nonpooling_verified=True,
        serial_packet_chain_verified=True, rollback_applied_once=True, source_packets_unchanged=True,
        all_scores_statistics_patterns_and_decisions_verified=True, all_paired_rescue_and_loss_counts_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    dest = run/'INDEPENDENT_AUDIT.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
