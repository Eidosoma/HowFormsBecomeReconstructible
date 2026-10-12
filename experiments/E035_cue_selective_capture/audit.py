"""Independent source replay, scalar capture, terminal replay and inference."""
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
from E023_receiver_compensation.audit import receiver_denominators
from E031_renewal_durability.audit import load_compact, require, coverage, replay_assay
from E034_settled_rebuilding.audit import body_scores
import numpy as np

CONDITIONS = ('standard_preserve', 'standard_rewrite', 'contrast_preserve', 'contrast_rewrite', 'matched_preserve', 'matched_rewrite')
RECEIVERS = ('fixed_four', 'local_strength')
ARMS = ('own', 'foreign', 'shuffled', 'erased', 'untrained', 'communication_off', 'source_cut')
DAMAGE = ('intact', 'scattered', 'square')
PANELS = tuple((r, c) for r in RECEIVERS for c in CONDITIONS)
PAIRS = (('standard_rewrite', 'standard_preserve'), ('contrast_preserve', 'standard_preserve'),
         ('contrast_rewrite', 'standard_rewrite'), ('contrast_rewrite', 'contrast_preserve'),
         ('contrast_rewrite', 'standard_preserve'), ('matched_preserve', 'standard_preserve'),
         ('matched_rewrite', 'standard_rewrite'), ('matched_rewrite', 'matched_preserve'),
         ('contrast_preserve', 'matched_preserve'), ('contrast_rewrite', 'matched_rewrite'))


def load(path):
    with np.load(path, allow_pickle=False) as h:
        return {k:h[k] for k in h.files}


# Source-boundary replay is inserted from the frozen E034 independent auditor,
# with only a copy of the pre-holding state added to the returned evidence.


def replay_source(raw, incoming, block, cfg, cycle, factor, reference):
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
    developed_end = v.copy()
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
    return outgoing, mean, developed_end


def construction(body, incoming, available, cfg):
    x = np.tanh(cfg['writer_beta']*body)
    mean = (x[:, :, 0]+x[:, :, 1])/2
    cue = (x[:, :, 0]-x[:, :, 1])/2
    old = unpack(incoming)
    retained = np.zeros_like(available)
    standard, contrast, matched = [np.zeros_like(old) for _ in range(3)]
    weights = np.zeros((6, *old.shape))
    for f, r, axis, y, xx in np.ndindex(old.shape):
        yy, nx = (y, (xx+1)%16) if axis == 0 else ((y+1)%16, xx)
        index = (f, r, axis, y, xx)
        standard[index] = (x[f, r, 0, y, xx]*x[f, r, 0, yy, nx]+x[f, r, 1, y, xx]*x[f, r, 1, yy, nx])/2
        contrast[index] = cue[f, r, y, xx]*cue[f, r, yy, nx]
        if contrast[index] > 0:
            matched[index] = abs(standard[index])
        elif contrast[index] < 0:
            matched[index] = -abs(standard[index])
        else:
            matched[index] = standard[index]
        if not available[index]:
            assert standard[index] == contrast[index] == matched[index] == 0
            continue
        retained[index] = abs(old[index]) > .5
        for i, field in enumerate((standard, contrast, matched)):
            weights[(2*i, *index)] = old[index] if retained[index] else field[index]
            weights[(2*i+1, *index)] = field[index]
    mean_products = np.stack((mean*np.roll(mean, -1, -1), mean*np.roll(mean, -1, -2)), axis=-3)
    np.testing.assert_allclose(standard, mean_products+contrast, rtol=0, atol=5e-16)
    for a, b in ((0, 4), (1, 5)):
        np.testing.assert_array_equal(abs(weights[a]), abs(weights[b]))
        np.testing.assert_array_equal(weights[a] != 0, weights[b] != 0)
    return dict(body=body.copy(), incoming=incoming.copy(), available=available.copy(), retained=retained,
                mean_component=mean, cue_component=cue, standard=standard, contrast=contrast,
                matched=matched, records=pack(weights))


def check_matched_controls(raw, records):
    own = unpack(records)
    weights = own[:, :, :, None].repeat(7, axis=3)
    weights[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    for n in range(6):
        for f in range(4):
            for r in range(own.shape[2]):
                weights[n, f, r, 2] = own[n, f, r].ravel()[raw['permutations'][f]].reshape(2, 16, 16)
    weights[:, :, :, 3], weights[:, :, :, 4] = 0., 1.
    alive = ~raw['masks']; p = ports()
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    weights = weights[:, :, :, None, None]*edges[None, :, :, None, :, None]
    weights[..., 5, :, :, :] = 0.
    cut = np.stack((p[0] | np.roll(p[0], -1, -1), p[0] | np.roll(p[0], -1, -2)))
    weights[..., 6, :, :, :] *= ~cut
    denominator = receiver_denominators(weights)
    require(raw, 'receiver_denominators', denominator)
    for a, b in ((0, 4), (1, 5)):
        np.testing.assert_array_equal(abs(weights[a]), abs(weights[b]))
        for offset in (0, 6):
            np.testing.assert_array_equal(denominator[offset+a], denominator[offset+b])


def inspect(task):
    run, source, parent, block, cfg, cycle, factor = task
    incoming = load_compact(parent/f'boundary_{block:06d}_g8.npz', 'boundary')['outgoing'][0]
    reference = load_compact(parent/f'boundary_{block:06d}_g9.npz', 'boundary')
    source_raw = load_compact(source/f'boundary_{block:06d}.npz', 'boundary')
    outgoing, body_mean, developed_end = replay_source(source_raw, incoming, block, cfg, cycle, factor, reference)
    alive = ~source_raw['renewal_mask']
    available = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    data = construction(developed_end[1], incoming, available, cfg)
    saved = load(run/f'construction_{block:06d}.npz')
    assert set(saved) == set(data)
    for key in data:
        np.testing.assert_array_equal(saved[key], data[key])
    np.testing.assert_array_equal(data['records'][0], outgoing[1])
    bc, bm, bv = body_scores(body_mean)
    source_cases = load(source/f'cases_{block:06d}.npz')
    for key, value in (('body_correct', bc), ('body_margin', bm), ('body_ports', bv)):
        np.testing.assert_array_equal(value, source_cases[key])
    terminal = dict(cycle, settling_steps=cycle['settling_steps']*factor)
    raw = load_compact(run/f'assay_{block:06d}.npz', 'assay')
    c, m, v = replay_assay(raw, data['records'], block, 9, cfg, terminal)
    check_matched_controls(raw, data['records'])
    original = load_compact(source/f'assay_{block:06d}_t1.npz', 'assay')
    np.testing.assert_array_equal(v[[0, 6]], original['mean_ports'][[1, 3]])
    for key in ('masks', 'permutations'):
        np.testing.assert_array_equal(raw[key], original[key])
    actual = dict(correct=c, margin=m, ports=v, body_correct=bc, body_margin=bm, body_ports=bv)
    retained = load(run/f'cases_{block:06d}.npz')
    assert set(retained) == set(actual)
    for key in actual:
        np.testing.assert_array_equal(actual[key], retained[key])
    return actual


def audit(run, workers=8):
    started = time.monotonic(); cap_cpus(8)
    contract = verify(run)['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, factor = (contract[k] for k in ('config', 'cycle', 'blocks', 'factor'))
    technical = contract['mode'] != 'scientific'
    source, parent = ROOT/contract['source'], ROOT/contract['parent_source']
    src = verify(source)['contract']; earlier = verify(parent)['contract']
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    assert cfg == src['config'] == earlier['config'] and cycle == src['cycle'] == earlier['cycle']
    assert ids == src['blocks'] == earlier['blocks'] and src['source'] == contract['parent_source']
    assert ids == ([900031] if technical else list(range(27000, 27032)))
    assert factor == src['factor'] == (2 if contract['mode'] == 'fixture' else 4)
    if not technical:
        assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=16)
    assert contract['generation'] == s['generation'] == 9
    assert contract['panels'] == s['panels'] == [list(p) for p in PANELS]
    assert s['terminal_cycle'] == dict(cycle, settling_steps=cycle['settling_steps']*factor)
    assert s['cfg'] == cfg and s['base_cycle'] == cycle and s['blocks'] == ids
    assert s['prior_cases_reused'] and not s['source_bodies_changed'] and not s['new_serial_history']
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        cases = list(pool.map(inspect, [(run, source, parent, b, cfg, cycle, factor) for b in ids]))
    correct = np.stack([x['correct'] for x in cases]); margin = np.stack([x['margin'] for x in cases])
    values = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    draw = random('E035', 'bootstrap', 'cue_selective_capture').integers(0, len(ids), (10000, len(ids)))
    def check(x, st):
        np.testing.assert_array_equal(x, st['block_means'])
        assert float(x.mean()) == st['mean']
        np.testing.assert_array_equal(np.quantile(x[draw].mean(axis=1), [.025, .975]), st['ci95'])
    for i, (r, c) in enumerate(PANELS):
        g = s['groups'][r][c]; gates = {}
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
    for r in RECEIVERS:
        for hi, lo in PAIRS:
            a, b = PANELS.index((r, hi)), PANELS.index((r, lo))
            for m, x in values.items():
                for d, injury in enumerate(DAMAGE):
                    check(x[:, a, d, 0]-x[:, b, d, 0], s['contrasts'][r][hi+'_minus_'+lo][m][injury])
        a, b, c, d = [PANELS.index((r, name)) for name in ('contrast_rewrite', 'standard_rewrite', 'contrast_preserve', 'standard_preserve')]
        for m, x in values.items():
            for j, injury in enumerate(DAMAGE):
                check((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]), s['interaction'][r][m][injury])
    check(values['both_cues'][:, 9, 1, 0]-values['both_cues'][:, 6, 1, 0], s['primary']['statistics'])
    passed = s['primary']['statistics']['ci95'][0] > .05
    assert s['primary']['margin'] == .05 and s['primary']['lower_above_005'] == (None if technical else passed)
    assert s['status'] == ('TECHNICAL_ONLY' if technical else 'CUE_SELECTIVE_CAPTURE_BENEFIT_ESTABLISHED' if passed else 'CUE_SELECTIVE_CAPTURE_BENEFIT_NOT_ESTABLISHED')
    absolute = s['groups']['local_strength']['contrast_rewrite']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert s['absolute_reliability_lower_above_075'] == (None if technical else absolute)
    for c in ('preserve', 'rewrite'):
        flag = s['contrasts']['local_strength'][f'matched_{c}_minus_standard_{c}']['both_cues']['scattered']['ci95'][0] > 0
        assert s['matched_sign_control_lower_above_zero'][c] == (None if technical else flag)
    assert s['individual_observations'] == correct.size == len(ids)*12*4*cfg['recipients']*2*3*7
    assert s['source_body_observations_replayed'] == len(ids)*2*4*cfg['recipients']*2
    assert s['lineages'] == len(ids)*4*cfg['recipients']
    assert s['all_source_boundary_commitments_match'] and s['baseline_endpoints_match_e034'] and s['matched_magnitudes_support_and_denominators_verified']
    verify(run); verify(source); verify(parent)
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, blocks=len(ids),
        individual_observations=int(correct.size), source_body_observations_replayed=s['source_body_observations_replayed'],
        all_source_body_and_terminal_updates_and_commitments_replayed=True,
        all_construction_arrays_independently_rebuilt=True, exact_e034_baseline_verified=True,
        matched_magnitudes_support_and_all_terminal_denominators_verified=True,
        all_cases_statistics_gates_and_focal_contrast_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    p = run/'INDEPENDENT_AUDIT.json'; assert not p.exists(); dump(p, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
