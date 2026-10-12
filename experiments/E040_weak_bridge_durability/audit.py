"""Independent teaching, serial dynamics, scalar capture and full inference replay."""
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
from E031_renewal_durability.audit import CompactEvidence, load_compact, require, coverage, replay_assay
import numpy as np

CONDITIONS = ('standard_preserve', 'standard_rewrite', 'bridge_preserve', 'bridge_rewrite',
              'contrast_preserve', 'bridge_read_blocked', 'bridge_write_blocked', 'protected_copy', 'masked_copy')
ACTIVE = tuple(range(7)); HORIZONS = (0, 1, 3, 8, 16, 24, 32)
RECEIVERS = ('fixed_four', 'local_strength')
ARMS = ('own', 'foreign', 'shuffled', 'erased', 'untrained', 'communication_off', 'source_cut')
DAMAGE = ('intact', 'scattered', 'square')
PANELS = tuple((h, c, r) for h in HORIZONS for r in RECEIVERS for c in (('initial',) if h == 0 else CONDITIONS))
PAIRS = tuple(('bridge_preserve', c) for c in CONDITIONS if c != 'bridge_preserve')+(
    ('standard_rewrite', 'standard_preserve'), ('bridge_rewrite', 'standard_rewrite'),
    ('bridge_rewrite', 'bridge_preserve'), ('contrast_preserve', 'standard_preserve'))
RULES, CUES = np.array([1., -1., 1., -1.]), np.array([1., -1.])


def load(path):
    with np.load(path, allow_pickle=False) as h:
        return {k:h[k] for k in h.files}


def load_source(path):
    saved = load(path); index = saved.pop('__index__')
    assert index.dtype == np.uint8 and index.ndim == 1
    meta = json.loads(index.tobytes())
    names = {'ports', 'rules', 'cues', 'teach_birth', 'teach_end', 'capture_states',
             'episode_weights', 'weights', 'acquired', 'engineered_signs'}
    assert set(meta) == {'format', 'kind', 'arrays', 'retained', 'nonretained_arrays_require_replay'}
    assert meta['format'] == 'E040_source_v1' and meta['kind'] == 'source'
    assert meta['nonretained_arrays_require_replay'] is True
    assert set(meta['arrays']) == names and set(saved) == names-{'capture_states'}
    assert meta['retained'] == sorted(saved)
    raw = CompactEvidence(saved); raw.descriptors, raw.checked = meta['arrays'], set()
    for key, value in raw.items():
        assert np.isfinite(value).all()
        require(raw, key, value)
    raw.checked.clear()
    return raw


def replay_source(raw, block, cfg):
    p = ports()
    for key, value in (('ports', p), ('rules', RULES), ('cues', CUES)): require(raw, key, value)
    records, pieces, births, ends, captured = [], [], [], [], []
    for mode in range(2):
        total = np.zeros((4, 2, 16, 16)); episodes, bb, ee, cc = [], [], [], []
        for c, cue in enumerate(CUES):
            stream = random('E016', block, 'teach', 0 if mode == 1 else c)
            sign = -1. if mode == 1 and c == 1 else 1.
            v = sign*cfg['birth_sd']*pair(stream.standard_normal((2, 16, 16)))
            bb.append(v.copy())
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
    for key, value in (('teach_birth', births), ('teach_end', ends), ('capture_states', captured), ('episode_weights', pieces)):
        require(raw, key, value)
    captured = np.asarray(captured)
    np.testing.assert_array_equal(captured[0, 0], captured[1, 0])
    assert np.max(abs(captured[1, 0]+captured[1, 1])) <= 1e-10
    signs = np.ones((4, 16, 16)); signs[:, p[1]], signs[:, p[2]] = RULES[:, None], -RULES[:, None]
    require(raw, 'engineered_signs', signs)
    edges = np.empty((4, 2, 16, 16))
    for y in range(16):
        for x in range(16):
            edges[:, 0, y, x] = signs[:, y, x]*signs[:, y, (x+1)%16]
            edges[:, 1, y, x] = signs[:, y, x]*signs[:, (y+1)%16, x]
    records.append(edges); weights = np.stack(records)
    require(raw, 'weights', weights); require(raw, 'acquired', pack(weights)); coverage(raw)
    assert np.max(abs(weights)) <= 1.
    return pack(weights)[1]


def capture(body, beta):
    x = np.tanh(beta*body); values = np.zeros((7, *body.shape[1:3], 2, 16, 16))
    for n, f, r, axis, y, xx in np.ndindex(values.shape):
        yy, nx = (y, (xx+1)%16) if axis == 0 else ((y+1)%16, xx)
        a, b = x[n, f, r, :, y, xx], x[n, f, r, :, yy, nx]
        difference = ((a[0]-a[1])/2)*((b[0]-b[1])/2)
        # Match NumPy mean's positive-zero reduction, including signed zero.
        ordinary = np.float64(0.)
        ordinary += a[0]*b[0]
        ordinary += a[1]*b[1]
        ordinary /= 2
        if n == 4: value = difference
        elif n in (2, 3, 5, 6) and difference != 0: value = difference
        else: value = ordinary
        values[n, f, r, axis, y, xx] = value
    return pack(values)


def replay_boundary(raw, incoming, block, generation, cfg, cycle):
    p, R = ports(), cfg['recipients']; require(raw, 'incoming', incoming)
    mask = masks_for(block, generation, R, renewal=True)[:, :, 1]
    require(raw, 'renewal_mask', mask)
    assert (mask.sum(axis=(-2, -1)) == 24).all() and not (mask & p.any(axis=0)).any()
    masks = np.stack([mask]*7); alive = ~masks; require(raw, 'body_masks', masks)
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    physical = pack(unpack(incoming[:7])*edges); require(raw, 'retained_packets', physical)
    reading = physical.copy(); reading[5] = 0; require(raw, 'read_packets', reading)
    inherited = unpack(reading); denominator = np.zeros((7, 4, R, 16, 16)); w = abs(inherited)
    for y in range(16):
        for x in range(16):
            denominator[..., y, x] = w[..., 0, y, x]+w[..., 0, y, (x-1)%16]+w[..., 1, y, x]+w[..., 1, (y-1)%16, x]
    require(raw, 'read_denominators', denominator); assert not denominator[5].any()
    stream = random('E022', block, 'develop', generation)
    birth = cfg['birth_sd']*pair(stream.standard_normal((2, R, 16, 16))); require(raw, 'birth', birth)
    v = np.broadcast_to(birth[None, :, :, None], (7, 4, R, 2, 16, 16)).copy()
    active = alive[:, :, :, None]; cue = CUES.reshape(1, 1, 1, 2, 1)
    v *= active; v[..., p[0]] = cue; late = []
    for t in range(cycle['read_steps']):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[:, :, None]
        for n in ACTIVE:
            settling = cycle['settling_steps']*4
            v[n] = advance_compensated(v[n], inherited[n, :, :, None], denominator[n, :, :, None], noise, cfg, t >= settling)
        v *= active; v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        np.testing.assert_array_equal(v[5, :, :, 0][..., ~p[0]], v[5, :, :, 1][..., ~p[0]])
        if t >= cycle['read_steps']-cfg['observe_steps']:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    require(raw, 'developed_end', v); require(raw, 'developed_late_ports', late)
    reading.fill(0); require(raw, 'erased_packets', reading)
    computed = capture(v, cfg['writer_beta']); require(raw, 'computed_packets', computed)
    assert not (unpack(computed)*(~edges)).any()
    stream = random('E022', block, 'write', generation)
    hashes = np.empty((cycle['write_steps'], 7, 32), np.uint8)
    for t in range(cycle['write_steps']):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, edges[:, :, :, None].astype(float), 2., noise, cfg)
        v *= active; v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        for n in ACTIVE:
            hashes[t, n] = np.frombuffer(hashlib.sha256(np.asarray(v[n], dtype='<f8', order='C').tobytes()).digest(), np.uint8)
    require(raw, 'write_state_hashes', hashes); require(raw, 'write_end', v)
    old, fresh = unpack(physical), unpack(computed)
    retained = np.zeros_like(edges); eligible = np.zeros_like(edges); chosen = np.zeros_like(old)
    for index in np.ndindex(old.shape):
        if edges[index]:
            if index[0] in (0, 2, 4, 5, 6) and abs(old[index]) > .5:
                retained[index] = True; chosen[index] = old[index]
            else:
                eligible[index] = True; chosen[index] = fresh[index]
    require(raw, 'retained_edges', retained); require(raw, 'eligible_edges', eligible)
    np.testing.assert_array_equal(retained | eligible, edges)
    outgoing = incoming.copy(); outgoing[:7] = pack(chosen); outgoing[6] = 0
    outgoing[8] = pack(unpack(incoming[8])*edges[0])
    require(raw, 'outgoing', outgoing)
    np.testing.assert_array_equal(outgoing[7], incoming[7]); assert not outgoing[6].any()
    mean = np.asarray(late).mean(axis=0); require(raw, 'developed_mean_ports', mean); coverage(raw)
    return outgoing, mean


def body_score(mean, cfg):
    target = np.array([1., -1., 1., -1.]).reshape(1, 4, 1, 1)*np.array([1., -1.]).reshape(1, 1, 1, 2)
    a, b = target*mean[..., 0], -target*mean[..., 1]
    return (a > cfg['margin']) & (b > cfg['margin']), np.minimum(a, b), mean


def inspect(task):
    run, block, cfg, cycle = task
    source = run/f'source_{block:06d}.npz'
    assert json.loads((run/f'worker_{block}.json').read_text())['source_sha256'] == sha(source)
    records = replay_source(load_source(source), block, cfg)[:, None].repeat(cfg['recipients'], axis=1)
    incoming = records[None].repeat(9, axis=0)
    correct, margin, values, bc, bm, bv = [], [], [], [], [], []
    terminal = dict(cycle, settling_steps=4*cycle['settling_steps'])
    def assay(h, packets):
        result = replay_assay(load_compact(run/f'assay_{block:06d}_h{h}.npz', 'assay'), packets, block, h, cfg, terminal)
        for dest, item in zip((correct, margin, values), result): dest.append(item)
    assay(0, records[None]); cumulative = np.ones((4, cfg['recipients'], 2, 16, 16), bool)
    for g in range(1, 33):
        raw = load_compact(run/f'boundary_{block:06d}_g{g}.npz', 'boundary')
        incoming, mean = replay_boundary(raw, incoming, block, g, cfg, cycle)
        for dest, item in zip((bc, bm, bv), body_score(mean, cfg)): dest.append(item)
        np.testing.assert_array_equal(incoming[7], records)
        alive = ~raw['renewal_mask']
        cumulative &= np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
        np.testing.assert_array_equal(incoming[8], pack(unpack(records)*cumulative))
        if g in HORIZONS: assay(g, incoming)
    actual = dict(correct=np.concatenate(correct), margin=np.concatenate(margin), ports=np.concatenate(values),
                  body_correct=np.stack(bc), body_margin=np.stack(bm), body_ports=np.stack(bv))
    saved = load(run/f'cases_{block:06d}.npz'); assert set(actual) == set(saved)
    for key in actual: np.testing.assert_array_equal(actual[key], saved[key])
    return actual


def audit(run, workers=8):
    started = time.monotonic(); cap_cpus(8)
    contract = verify(run)['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids = (contract[k] for k in ('config', 'cycle', 'blocks'))
    technical = contract['mode'] != 'scientific'
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    assert ids == ([900040] if technical else list(range(31000, 31032)))
    if not technical:
        assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=32)
    else:
        expected_cfg = dict(EXPECTED, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4) if contract['mode'] == 'fixture' else dict(EXPECTED, recipients=1)
        expected_cycle = dict(read_steps=24, settling_steps=3, write_steps=8, generations=32) if contract['mode'] == 'fixture' else dict(read_steps=128, settling_steps=16, write_steps=128, generations=32)
        assert cfg == expected_cfg and cycle == expected_cycle
    assert s['mode'] == contract['mode'] and s['cfg'] == cfg and s['cycle'] == cycle and s['blocks'] == ids
    assert s['terminal_cycle'] == dict(cycle, settling_steps=4*cycle['settling_steps'])
    assert contract['panels'] == s['panels'] == [list(p) for p in PANELS]
    assert not s['prior_cases_pooled'] and s['independent_serial_histories'] and s['setting_selected'] is None
    assert s['experiment'] == contract['experiment'] == 'E040'
    assert s['model_is_horizon_only_extension_of_e039'] is True
    reference = (ROOT/'E039_weak_bridge_confirmation/model.py').read_text()
    expected = reference.replace('CFG, Cycle, CYCLE = previous.CFG, previous.Cycle, previous.CYCLE\n',
        'CFG, Cycle, CYCLE = previous.CFG, previous.Cycle, previous.CYCLE\nCYCLE = replace(CYCLE, generations=32)\n')
    expected = expected.replace('HORIZONS = (0, 1, 3, 8, 16)', 'HORIZONS = (0, 1, 3, 8, 16, 24, 32)')
    expected = expected.replace('cycle.generations == 16', 'cycle.generations == 32')
    assert (HERE/'model.py').read_text() == expected
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        cases = list(pool.map(inspect, [(run, b, cfg, cycle) for b in ids]))
    correct = np.stack([x['correct'] for x in cases]); margin = np.stack([x['margin'] for x in cases])
    values = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    draw = random('E040', 'bootstrap', 'weak_bridge_durability').integers(0, len(ids), (10000, len(ids)))
    def check(x, st):
        np.testing.assert_array_equal(x, st['block_means']); assert float(x.mean()) == st['mean']
        np.testing.assert_array_equal(np.quantile(x[draw].mean(axis=1), [.025, .975]), st['ci95'])
    for i, (h, c, r) in enumerate(PANELS):
        g = s['groups'][str(h)][r][c]; gates = {}
        for d, injury in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for m, x in values.items(): check(x[:, i, d, a], g[m][injury][arm])
                if a:
                    st = g['own_minus_control'][injury][arm]
                    check(values['accuracy'][:, i, d, 0]-values['accuracy'][:, i, d, a], st)
                    gates[f'advantage_{injury}_{arm}'] = st['ci95'][0] > .10
            for f, rule in enumerate((1, -1)):
                st = g['own_accuracy_by_rule'][str(rule)][injury]
                check(correct[:, i][:, [f, f+2]][:, :, :, :, d, 0].mean(axis=(1, 2, 3)), st)
                gates[f'accuracy_rule_{rule}_{injury}'] = st['ci95'][0] > .75
        assert g['gates'] == gates and g['all_original_gates_pass'] == all(gates.values())
    for h in HORIZONS[1:]:
        for r in RECEIVERS:
            for hi, lo in PAIRS:
                a, b = PANELS.index((h, hi, r)), PANELS.index((h, lo, r))
                for m, x in values.items():
                    for d, injury in enumerate(DAMAGE):
                        check(x[:, a, d, 0]-x[:, b, d, 0], s['contrasts'][str(h)][r][hi+'_minus_'+lo][m][injury])
            a, b, c, d = [PANELS.index((h, name, r)) for name in ('bridge_rewrite', 'standard_rewrite', 'bridge_preserve', 'standard_preserve')]
            for m, x in values.items():
                for j, injury in enumerate(DAMAGE):
                    check((x[:, a, j, 0]-x[:, b, j, 0])-(x[:, c, j, 0]-x[:, d, j, 0]), s['interaction'][str(h)][r][m][injury])
            for c in CONDITIONS:
                a, b = PANELS.index((h, c, r)), PANELS.index((1, c, r))
                for m, x in values.items():
                    for j, injury in enumerate(DAMAGE):
                        check(x[:, a, j, 0]-x[:, b, j, 0], s['changes_from_h1'][str(h)][r][c][m][injury])
    bc = np.stack([x['body_correct'] for x in cases]); bm = np.stack([x['body_margin'] for x in cases])
    bvalues = dict(accuracy=bc.mean(axis=(3, 4, 5)), both_cues=bc.all(axis=5).mean(axis=(3, 4)), margin=bm.mean(axis=(3, 4, 5)))
    for g in range(32):
        for n in ACTIVE:
            for m, x in bvalues.items(): check(x[:, g, n], s['body_reading'][str(g+1)][CONDITIONS[n]][m])
    a, b = PANELS.index((32, 'bridge_preserve', 'local_strength')), PANELS.index((32, 'standard_preserve', 'local_strength'))
    check(values['both_cues'][:, a, 1, 0]-values['both_cues'][:, b, 1, 0], s['primary']['statistics'])
    assert s['primary']['endpoint'] == 'h32 normalized scattered own both-cue success: bridge_preserve minus standard_preserve'
    passed = s['primary']['statistics']['ci95'][0] > .05
    assert s['primary']['margin'] == .05 and s['primary']['lower_above_005'] == (None if technical else passed)
    assert s['primary_status'] == ('TECHNICAL_ONLY' if technical else 'LONG_RENEWAL_BENEFIT_ESTABLISHED' if passed else 'LONG_RENEWAL_BENEFIT_NOT_ESTABLISHED')
    gates = {}
    for h in (8, 16, 24, 32):
        candidate = s['groups'][str(h)]['local_strength']['bridge_preserve']
        for d in ('intact', 'scattered'):
            gates[f'h{h}_{d}_both_cue_lower_above_075'] = candidate['both_cues'][d]['own']['ci95'][0] > .75
        gates[f'h{h}_original_24_gates'] = candidate['all_original_gates_pass']
    for h in (16, 32):
        for c in ('bridge_read_blocked', 'bridge_write_blocked'):
            gates[f'h{h}_above_{c}_by_010'] = s['contrasts'][str(h)]['local_strength']['bridge_preserve_minus_'+c]['both_cues']['scattered']['ci95'][0] > .10
    gates['initial_normalized_original_24_gates'] = s['groups']['0']['local_strength']['initial']['all_original_gates_pass']
    rescue=s['contrasts']['32']['local_strength']['bridge_preserve_minus_contrast_preserve']['both_cues']['scattered']
    assert s['repair_rescue']['statistics']==rescue
    assert s['repair_rescue']['endpoint']=='h32 bridge_preserve minus contrast_preserve'
    assert s['repair_rescue']['scope']=='prespecified secondary'
    assert s['repair_rescue']['lower_above_010']==(None if technical else rescue['ci95'][0]>.10)
    assert s['durability_requirements'] == gates and len(gates) == 17
    assert s['full_durability_qualified'] == (None if technical else all(gates.values()))
    assert s['durability_status'] == ('TECHNICAL_ONLY' if technical else 'DURABLE_THROUGH_32_RENEWALS' if all(gates.values()) else 'DURABILITY_NOT_ESTABLISHED')
    qualified = passed and all(gates.values())
    assert s['full_qualification'] == (None if technical else qualified)
    assert s['status'] == ('TECHNICAL_ONLY' if technical else 'LONG_RENEWAL_QUALIFIED' if qualified else 'LONG_RENEWAL_NOT_QUALIFIED')
    assert s['interval_scope'] == 'One relative primary plus separate absolute durability; full qualification requires both; all intervals and component gates pointwise'
    assert s['individual_observations'] == correct.size == len(ids)*110*4*cfg['recipients']*2*3*7
    assert s['body_individual_observations'] == bc.size == len(ids)*32*7*4*cfg['recipients']*2
    assert s['lineages'] == len(ids)*4*cfg['recipients'] and s['founders'] == len(ids)*4
    verify(run)
    for rel, digest in index['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, blocks=len(ids),
        individual_observations=int(correct.size), body_individual_observations=int(bc.size),
        all_source_serial_holding_terminal_updates_replayed=True, every_array_commitment_verified=True,
        scalar_capture_and_copying_verified=True, independent_histories_and_copy_controls_verified=True,
        all_cases_statistics_and_decisions_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    p = run/'INDEPENDENT_AUDIT.json'; assert not p.exists(); dump(p, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
