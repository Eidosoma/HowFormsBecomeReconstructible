"""Independent development, capture, holding, terminal and statistics replay."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, random, EXPECTED, ports, pair, pack, unpack, advance
from E022_reader_compensation.audit import masks_for, advance_compensated, correlations
from E031_renewal_durability.audit import load_compact, require, coverage, replay_assay
import numpy as np

TIMINGS = CONDITIONS = ('original', 'delayed')
RECEIVERS = ('fixed_four', 'local_strength')
ARMS = ('own', 'foreign', 'shuffled', 'erased', 'untrained', 'communication_off', 'source_cut')
DAMAGE = ('intact', 'scattered', 'square')
PANELS = tuple((t, r, c) for t in TIMINGS for r in RECEIVERS for c in CONDITIONS)


def load(path):
    with np.load(path, allow_pickle=False) as h:
        return {k:h[k] for k in h.files}


def clocks(cycle, factor):
    return [dict(cycle), dict(cycle, settling_steps=cycle['settling_steps']*factor)]


def body_scores(value):
    signed_a = value[..., 0]*np.array([1., -1., 1., -1.])[None, :, None, None]*np.array([1., -1.])[None, None, None, :]
    signed_b = -value[..., 1]*np.array([1., -1., 1., -1.])[None, :, None, None]*np.array([1., -1.])[None, None, None, :]
    return (signed_a > .25) & (signed_b > .25), np.minimum(signed_a, signed_b), value


def replay_boundary(raw, incoming, block, cfg, cycle, factor, reference):
    p, R = ports(), cfg['recipients']
    require(raw, 'incoming', incoming)
    mask = masks_for(block, 9, R, renewal=True)[:, :, 1]
    require(raw, 'renewal_mask', mask)
    assert (mask.sum(axis=(-2, -1)) == 24).all() and not (mask & p.any(axis=0)).any()
    masks = np.stack((mask, mask)); alive = ~masks
    require(raw, 'body_masks', masks)
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    effective = pack(unpack(incoming)[None]*edges)
    require(raw, 'retained_packets', effective)
    require(raw, 'read_packets', effective)
    inherited = unpack(effective)
    denominator = np.zeros((2, 4, R, 16, 16))
    for y in range(16):
        for x in range(16):
            w = abs(inherited)
            denominator[..., y, x] = w[..., 0, y, x]+w[..., 0, y, (x-1)%16]+w[..., 1, y, x]+w[..., 1, (y-1)%16, x]
    require(raw, 'read_denominators', denominator)
    stream = random('E022', block, 'develop', 9)
    birth = cfg['birth_sd']*pair(stream.standard_normal((2, R, 16, 16)))
    require(raw, 'birth', birth)
    v = np.broadcast_to(birth[None, :, :, None], (2, 4, R, 2, 16, 16)).copy()
    active = alive[:, :, :, None]; cue = np.array([1., -1.]).reshape(1, 1, 1, 2, 1)
    v *= active; v[..., p[0]] = cue
    late = []
    for t in range(cycle['read_steps']):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[:, :, None]
        for branch, settling in enumerate((cycle['settling_steps'], cycle['settling_steps']*factor)):
            v[branch] = advance_compensated(v[branch], inherited[branch, :, :, None], denominator[branch, :, :, None], noise, cfg, t >= settling)
        v *= active; v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        if t >= cycle['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    require(raw, 'developed_end', v)
    require(raw, 'developed_late_ports', late)
    effective.fill(0); require(raw, 'erased_packets', effective)
    computed = pack(correlations(v, cfg['writer_beta']).mean(axis=3))
    require(raw, 'computed_packets', computed)
    assert not (unpack(computed)*(~edges)).any()
    stream = random('E022', block, 'write', 9)
    hashes = np.empty((cycle['write_steps'], 2, 32), dtype=np.uint8)
    for t in range(cycle['write_steps']):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, edges[:, :, :, None].astype(float), 2., noise, cfg)
        v *= active; v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        for b in range(2):
            hashes[t, b] = np.frombuffer(hashlib.sha256(np.asarray(v[b], dtype='<f8', order='C').tobytes()).digest(), np.uint8)
    require(raw, 'write_state_hashes', hashes)
    require(raw, 'write_end', v)
    selected = np.zeros_like(inherited); retained = np.zeros_like(edges); eligible = np.zeros_like(edges)
    fresh = unpack(computed)
    for index in np.ndindex(selected.shape):
        if edges[index]:
            if abs(inherited[index]) > .5:
                selected[index] = inherited[index]; retained[index] = True
            else:
                selected[index] = fresh[index]; eligible[index] = True
    outgoing = pack(selected)
    require(raw, 'retained_edges', retained); require(raw, 'eligible_edges', eligible)
    require(raw, 'outgoing', outgoing)
    mean = np.asarray(late).mean(axis=0)
    require(raw, 'developed_mean_ports', mean); coverage(raw)
    np.testing.assert_array_equal(retained | eligible, edges)
    np.testing.assert_array_equal(selected[retained], inherited[retained])
    np.testing.assert_array_equal(mask, reference['renewal_mask'])
    for key in ('outgoing', 'retained_edges', 'eligible_edges', 'developed_mean_ports'):
        np.testing.assert_array_equal(raw[key][0], reference[key][0])
    np.testing.assert_array_equal(hashes[:, 0], reference['write_state_hashes'][:, 0])
    return outgoing, mean


def inspect(task):
    run, source, block, cfg, cycle, factor = task
    incoming = load_compact(source/f'boundary_{block:06d}_g8.npz', 'boundary')['outgoing'][0]
    reference = load_compact(source/f'boundary_{block:06d}_g9.npz', 'boundary')
    raw = load_compact(run/f'boundary_{block:06d}.npz', 'boundary')
    records, mean = replay_boundary(raw, incoming, block, cfg, cycle, factor, reference)
    bc, bm, bv = body_scores(mean)
    cs, ms, vs = [], [], []
    for i, clock in enumerate(clocks(cycle, factor)):
        raw = load_compact(run/f'assay_{block:06d}_t{i}.npz', 'assay')
        c, m, v = replay_assay(raw, records, block, 9, cfg, clock)
        cs.append(c); ms.append(m); vs.append(v)
    actual = dict(correct=np.concatenate(cs), margin=np.concatenate(ms), ports=np.concatenate(vs),
                  body_correct=bc, body_margin=bm, body_ports=bv)
    retained = load(run/f'cases_{block:06d}.npz')
    assert set(retained) == set(actual)
    for key in actual:
        np.testing.assert_array_equal(actual[key], retained[key])
    return actual


def audit(run, workers=8):
    started = time.monotonic(); cap_cpus(8)
    contract = verify(run)['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, factor = (contract[k] for k in ('config', 'cycle', 'blocks', 'factor'))
    technical = contract['mode'] != 'scientific'; source = ROOT/contract['source']
    src = verify(source)['contract']
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    assert cfg == src['config'] and cycle == src['cycle'] and ids == src['blocks']
    assert ids == ([900031] if technical else list(range(27000, 27032)))
    assert factor == (2 if contract['mode'] == 'fixture' else 4)
    if not technical:
        assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=16)
    assert contract['generation'] == s['generation'] == 9
    assert contract['panels'] == s['panels'] == [list(p) for p in PANELS]
    assert s['schedules'] == dict(zip(TIMINGS, clocks(cycle, factor)))
    assert s['cfg'] == cfg and s['base_cycle'] == cycle and s['blocks'] == ids
    assert s['prior_cases_reused'] and s['original_boundary_matches_e031']
    assert not s['writing_rule_changed'] and not s['total_read_steps_changed']
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        cases = list(pool.map(inspect, [(run, source, b, cfg, cycle, factor) for b in ids]))
    correct = np.stack([x['correct'] for x in cases]); margin = np.stack([x['margin'] for x in cases])
    values = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    draw = random('E034', 'bootstrap', 'settled_rebuilding').integers(0, len(ids), (10000, len(ids)))
    def check(x, st):
        np.testing.assert_array_equal(x, st['block_means'])
        assert float(x.mean()) == st['mean']
        np.testing.assert_array_equal(np.quantile(x[draw].mean(axis=1), [.025, .975]), st['ci95'])
    for i, (timing, receiver, condition) in enumerate(PANELS):
        g = s['groups'][timing][receiver][condition]; gates = {}
        for d, injury in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for m, x in values.items(): check(x[:, i, d, a], g[m][injury][arm])
                if a:
                    st = g['own_minus_control'][injury][arm]
                    check(values['accuracy'][:, i, d, 0]-values['accuracy'][:, i, d, a], st)
                    gates[f'advantage_{injury}_{arm}'] = st['ci95'][0] > .10
            for f, rule in enumerate((1, -1)):
                x = correct[:, i][:, [f, f+2]][:, :, :, :, d, 0].mean(axis=(1, 2, 3))
                st = g['own_accuracy_by_rule'][str(rule)][injury]; check(x, st)
                gates[f'accuracy_rule_{rule}_{injury}'] = st['ci95'][0] > .75
        assert g['gates'] == gates and g['all_original_gates_pass'] == all(gates.values())
    def check_difference(high, low, stats):
        a, b = PANELS.index(high), PANELS.index(low)
        for m, x in values.items():
            for d, injury in enumerate(DAMAGE): check(x[:, a, d, 0]-x[:, b, d, 0], stats[m][injury])
    for t in TIMINGS:
        for r in RECEIVERS:
            check_difference((t, r, 'delayed'), (t, r, 'original'), s['rebuilding_contrasts'][t][r])
    for c in CONDITIONS:
        for r in RECEIVERS:
            check_difference(('delayed', r, c), ('original', r, c), s['receiving_contrasts'][c][r])
    for r in RECEIVERS:
        indexes = [PANELS.index(p) for p in (('delayed', r, 'delayed'), ('delayed', r, 'original'), ('original', r, 'delayed'), ('original', r, 'original'))]
        for m, x in values.items():
            a, b, c, d = indexes
            for j, injury in enumerate(DAMAGE):
                check((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]), s['interactions'][r][m][injury])
    bc = np.stack([x['body_correct'] for x in cases]); bm = np.stack([x['body_margin'] for x in cases])
    body = dict(accuracy=bc.mean(axis=(2, 3, 4)), both_cues=bc.all(axis=4).mean(axis=(2, 3)), margin=bm.mean(axis=(2, 3, 4)))
    for m, x in body.items():
        for i, c in enumerate(CONDITIONS): check(x[:, i], s['body'][c][m])
        check(x[:, 1]-x[:, 0], s['body']['delayed_minus_original'][m])
    check(values['both_cues'][:, 7, 1, 0]-values['both_cues'][:, 6, 1, 0], s['primary']['statistics'])
    passed = s['primary']['statistics']['ci95'][0] > .05
    assert s['primary']['margin'] == .05 and s['primary']['lower_above_005'] == (None if technical else passed)
    assert s['status'] == ('TECHNICAL_ONLY' if technical else 'SETTLED_REBUILDING_BENEFIT_ESTABLISHED' if passed else 'SETTLED_REBUILDING_BENEFIT_NOT_ESTABLISHED')
    absolute = s['groups']['delayed']['local_strength']['delayed']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert s['absolute_reliability_lower_above_075'] == (None if technical else absolute)
    assert s['individual_observations'] == correct.size == len(ids)*8*4*cfg['recipients']*2*3*7
    assert s['body_individual_observations'] == bc.size == len(ids)*2*4*cfg['recipients']*2
    assert s['lineages'] == len(ids)*4*cfg['recipients']
    verify(run); verify(source)
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, blocks=len(ids),
        individual_observations=int(correct.size), body_individual_observations=int(bc.size),
        all_development_capture_holding_terminal_updates_and_commitments_replayed=True,
        all_cases_statistics_gates_and_focal_contrast_verified=True, original_boundary_matches_e031_exactly=True,
        unchanged_source_packets_and_strong_copy_rule_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    p = run/'INDEPENDENT_AUDIT.json'; assert not p.exists(); dump(p, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
