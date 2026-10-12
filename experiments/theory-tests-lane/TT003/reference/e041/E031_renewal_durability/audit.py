"""Independent receiving-reader replay; imports auditors, never production code."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from E015_functional_inheritance.audit import advance, pair, pack, unpack, ports, random, read_json, sha, verify, EXPECTED
from E022_reader_compensation.audit import source_record, masks_for, advance_compensated, load_arrays, equal, correlations
import numpy as np
CONDITIONS = ("maturing", "maturing_read_blocked", "strength_compensated", "intact_renewed",
              "protected_copy", "masked_copy", "read_blocked", "write_blocked",
              "selective", "maturing_refresh_blocked")
ACTIVE = (0, 1, 2, 3, 6, 7, 8, 9)
READER_MODES = ("local_strength", "local_strength", "local_strength", "fixed_four", "local_strength", "local_strength", "local_strength", "local_strength")
RECEIVERS = ("fixed_four", "local_strength")
PANELS = tuple((h, name, receiver) for h in (0, 1, 3, 8, 16) for receiver in RECEIVERS
               for name in (("initial",) if h == 0 else CONDITIONS))
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
CYCLE = dict(read_steps=2048, settling_steps=256, write_steps=128, generations=16)


from E023_receiver_compensation.audit import receiver_denominators


BOUNDARY_NAMES = frozenset(('incoming', 'read_packets', 'erased_packets', 'retained_packets',
    'retained_edges', 'eligible_edges', 'outgoing', 'renewal_mask', 'body_masks', 'birth',
    'read_denominators', 'developed_end', 'developed_late_ports', 'write_state_hashes',
    'write_end', 'computed_packets', 'developed_mean_ports'))
ASSAY_NAMES = frozenset(('packets', 'permutations', 'masks', 'birth', 'receiver_denominators',
                        'end', 'late_mean', 'late_ports', 'mean_ports'))


class CompactEvidence(dict):
    pass


def load_compact(path, kind):
    with np.load(path, allow_pickle=False) as saved:
        assert saved['__index__'].dtype == np.uint8 and saved['__index__'].ndim == 1
        meta = json.loads(saved['__index__'].tobytes())
        retained = {'boundary': {'outgoing', 'renewal_mask', 'retained_edges', 'eligible_edges', 'write_state_hashes', 'developed_mean_ports'},
                    'assay': {'masks', 'permutations', 'mean_ports'}}[kind]
        assert set(saved.files) == retained | {'__index__'}
        raw = CompactEvidence({name: saved[name] for name in retained})
    assert set(meta) == {'format', 'kind', 'arrays', 'retained', 'nonretained_arrays_require_replay'}
    assert meta['format'] == 'E031_compact_v1' and meta['kind'] == kind
    assert meta['retained'] == sorted(retained) and meta['nonretained_arrays_require_replay'] is True
    assert set(meta['arrays']) == (BOUNDARY_NAMES if kind == 'boundary' else ASSAY_NAMES)
    raw.descriptors, raw.checked = meta['arrays'], set()
    for name, value in raw.items():
        assert np.isfinite(value).all(), name
        descriptor = raw.descriptors[name]
        assert descriptor == dict(shape=list(value.shape), dtype=value.dtype.str,
            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest()), ('retained evidence', name)
    return raw


def require(raw, key, expected):
    value = np.asarray(expected)
    if isinstance(raw, CompactEvidence):
        actual = dict(shape=list(value.shape), dtype=value.dtype.str,
            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())
        assert actual == raw.descriptors[key], ('array commitment', key)
        if key in raw: equal(raw[key], value)
        raw.checked.add(key)
    else:
        equal(raw[key], value)


def coverage(raw):
    if isinstance(raw, CompactEvidence):
        assert raw.checked == set(raw.descriptors), ('unreplayed arrays', set(raw.descriptors)-raw.checked)


def local_denominators(weights, physical_edges):
    result = np.full((*weights.shape[:-3], 16, 16), 4.)
    for branch in (0, 1, 2, 4, 5, 6, 7):
        w = abs(weights[branch])
        for y in range(16):
            for x in range(16):
                result[branch, ..., y, x] = w[..., 0, y, x]+w[..., 0, y, (x-1)%16]+w[..., 1, y, x]+w[..., 1, (y-1)%16, x]
    return result


def replay_boundary(raw, incoming, block, generation, cfg, cycle):
    p, R = ports(), cfg["recipients"]
    require(raw, "incoming", incoming)
    mask = masks_for(block, generation, R, renewal=True)[:, :, 1]
    require(raw, "renewal_mask", mask)
    assert np.all(mask.sum(axis=(-2, -1)) == 24) and not (mask & p.any(axis=0)).any()
    masks = np.stack((mask, mask, mask, np.zeros_like(mask), mask, mask, mask, mask))
    require(raw, "body_masks", masks)
    alive = ~masks
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    effective = pack(unpack(incoming[list(ACTIVE)])*edges)
    retained_packets = effective[[0, 1, 6, 7]].copy()
    require(raw, "retained_packets", retained_packets)
    effective[[1, 4]] = 0
    require(raw, "read_packets", effective)
    weights = unpack(effective)[:, :, :, None]
    denominator = local_denominators(unpack(effective), edges)
    require(raw, "read_denominators", denominator)
    assert not denominator[[1, 4]].any() and np.isfinite(denominator).all()
    stream = random("E022", block, "develop", generation)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 16, 16)))
    require(raw, "birth", birth)
    v = np.broadcast_to(birth[None, :, :, None], (8, 4, R, 2, 16, 16)).copy()
    active = alive[:, :, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., p[0]] = cue
    late = []
    for t in range(cycle["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance_compensated(v, weights, denominator[:, :, :, None], noise, cfg, t >= cycle["settling_steps"])
        v *= active
        v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        for branch in (1, 4):
            equal(v[branch, :, :, 0][..., ~p[0]], v[branch, :, :, 1][..., ~p[0]])
        if t >= cycle["read_steps"]-cfg["observe_steps"]:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    require(raw, "developed_end", v)
    require(raw, "developed_late_ports", late)
    # Activity-only capture follows read erasure; selective copying uses its explicit retained packet.
    effective.fill(0)
    weights = edges[:, :, :, None].astype(float)
    require(raw, "erased_packets", effective)
    computed = pack(correlations(v, cfg["writer_beta"]).mean(axis=3))
    stream = random("E022", block, "write", generation)
    assert not (unpack(computed)*(~edges)).any()
    assert raw["write_state_hashes"].shape == (cycle["write_steps"], 8, 32)
    assert raw["write_state_hashes"].dtype == np.uint8
    expected_hashes = np.empty((cycle["write_steps"], 8, 32), dtype=np.uint8)
    for t in range(cycle["write_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, weights, 2., noise, cfg)
        v *= active
        v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        for a in range(8):
            digest = hashlib.sha256(np.asarray(v[a], dtype="<f8", order="C").tobytes(order="C")).digest()
            assert raw["write_state_hashes"][t, a].tobytes() == digest, ("holding digest", t, a)
            expected_hashes[t, a] = np.frombuffer(digest, dtype=np.uint8)
    require(raw, "write_state_hashes", expected_hashes)
    require(raw, "write_end", v)
    require(raw, "computed_packets", computed)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = computed
    retained = np.zeros((4, 4, R, 2, 16, 16), dtype=bool)
    eligible = np.zeros_like(retained)
    selected = np.zeros((4, 4, R, 2, 16, 16))
    old, fresh = unpack(retained_packets), unpack(computed[[0, 1, 6, 7]])
    for branch, active_index in enumerate((0, 1, 6, 7)):
        cutoff = 0. if branch == 2 else .5
        for founder in range(4):
            for lineage in range(R):
                for axis in range(2):
                    for y in range(16):
                        for x in range(16):
                            k = (branch, founder, lineage, axis, y, x)
                            if not edges[(active_index, founder, lineage, axis, y, x)]:
                                continue
                            if abs(old[k]) > cutoff:
                                retained[k] = True
                                selected[k] = old[k]
                            else:
                                eligible[k] = True
                                selected[k] = fresh[k] if branch != 3 else 0.
    require(raw, 'retained_edges', retained)
    require(raw, 'eligible_edges', eligible)
    equal(retained | eligible, edges[[0, 1, 6, 7]])
    assert not (retained & eligible).any()
    outgoing[[0, 1, 8, 9]] = pack(selected)
    outgoing[5] = pack(unpack(incoming[5])*edges[0])
    outgoing[7] = 0
    require(raw, "outgoing", outgoing)
    equal(outgoing[4], incoming[4])
    assert not outgoing[7].any() and np.max(abs(unpack(outgoing))) <= 1.
    mean_ports = np.asarray(late).mean(axis=0)
    if isinstance(raw, CompactEvidence): require(raw, "developed_mean_ports", mean_ports)
    coverage(raw)
    return outgoing, mean_ports



def replay_assay(raw, records, block, horizon, cfg, cycle):
    N, R, p = len(records), cfg["recipients"], ports()
    own = unpack(records)
    panel = own[:, :, :, None].repeat(7, axis=3)
    panel[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    permutations = []
    for f in range(4):
        permutation = random("E022", block, "shuffle", horizon, f).permutation(512)
        permutations.append(permutation)
        for n in range(N):
            for r in range(R): panel[n, f, r, 2] = own[n, f, r].ravel()[permutation].reshape(2, 16, 16)
    panel[:, :, :, 3], panel[:, :, :, 4] = 0., 1.
    require(raw, "permutations", np.stack(permutations))
    packet = pack(panel)
    require(raw, "packets", packet)
    masks = masks_for(block, horizon, R)
    require(raw, "masks", masks)
    equal(masks.sum(axis=(-2, -1)), np.broadcast_to([0, 24, 9], (4, R, 3)))
    assert not (masks & p.any(axis=0)).any()
    alive = ~masks
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    weights = unpack(packet)[:, :, :, None, None]*edges[None, :, :, None, :, None]
    weights[..., 5, :, :, :] = 0.
    cut = np.stack((p[0] | np.roll(p[0], -1, -1), p[0] | np.roll(p[0], -1, -2)))
    weights[..., 6, :, :, :] *= ~cut
    denominator = receiver_denominators(weights)
    require(raw, "receiver_denominators", denominator)
    assert not denominator[N:, ..., [3, 5], :, :].any()
    weights = np.concatenate((weights, weights), axis=0)
    stream = random("E022", block, "assay", horizon)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 3, 16, 16)))
    require(raw, "birth", birth)
    v = np.broadcast_to(birth[None, :, :, None, :, None], (2*N, 4, R, 2, 3, 7, 16, 16)).copy()
    active = alive[None, :, :, None, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1, 1, 1)
    v *= active
    v[..., p[0]] = cue
    late = np.zeros_like(v)
    traces = []
    for t in range(cycle["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None, :, None]
        v = advance_compensated(v, weights, denominator, noise, cfg, t >= cycle["settling_steps"])
        v *= active
        v[..., p[0]] = cue
        assert not (v*masks[None, :, :, None, :, None]).any()
        for a in (5, 6): equal(v[:, :, :, 0, :, a][..., ~p[0]], v[:, :, :, 1, :, a][..., ~p[0]])
        if t >= cycle["read_steps"]-cfg["observe_steps"]:
            late += v
            traces.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    require(raw, "end", v)
    require(raw, "late_mean", late/cfg["observe_steps"])
    require(raw, "late_ports", traces)
    output = np.asarray(traces).mean(axis=0)
    requested = RULES.reshape(1, 4, 1, 1, 1, 1)*CUES.reshape(1, 1, 1, 2, 1, 1)
    a, b = requested*output[..., 0], -requested*output[..., 1]
    correct = (a > cfg["margin"]) & (b > cfg["margin"])
    assert not correct.all(axis=3)[..., 5:7].any()
    if isinstance(raw, CompactEvidence): require(raw, "mean_ports", output)
    coverage(raw)
    return correct, np.minimum(a, b), output


def inspect_block(task):
    run, block, cfg, cycle = task
    source_path = run/f"source_{block:06d}.npz"
    source = load_arrays(source_path)
    meta = read_json(run/f"worker_{block}.json")
    assert (ROOT/meta["source_file"]).resolve() == source_path and meta["source_sha256"] == sha(source_path)
    packet, symmetry = source_record(source, block, cfg)
    records = packet[:, None].repeat(cfg["recipients"], axis=1)
    correct, margin, output = [], [], []
    def assay(h, records):
        c, m, v = replay_assay(load_compact(run/f"assay_{block:06d}_h{h}.npz", "assay"), records, block, h, cfg, cycle)
        correct.append(c); margin.append(m); output.append(v)
    assay(0, records[None])
    incoming = records[None].repeat(10, axis=0)
    body_values = []
    cumulative_edges = np.ones((4, cfg['recipients'], 2, 16, 16), bool)
    for g in range(1, 17):
        raw = load_compact(run/f"boundary_{block:06d}_g{g}.npz", "boundary")
        incoming, values = replay_boundary(raw, incoming, block, g, cfg, cycle)
        body_values.append(values)
        equal(incoming[4], records)
        alive = ~raw['renewal_mask']
        cumulative_edges &= np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
        equal(incoming[5], pack(unpack(records)*cumulative_edges))
        del raw
        if g in (1, 3, 8, 16): assay(g, incoming)
    c, m, v = [np.concatenate(x) for x in (correct, margin, output)]
    body_values = np.asarray(body_values)
    target = RULES[None, None, :, None, None]*CUES[None, None, None, None, :]
    bm = np.minimum(target*body_values[..., 0], -target*body_values[..., 1])
    bc = bm > cfg["margin"]
    return dict(correct=c, margin=m, output=v, accuracy=c.mean(axis=(1, 2, 3)),
        both_cues=c.all(axis=3).mean(axis=(1, 2)), mean_margin=m.mean(axis=(1, 2, 3)), symmetry=symmetry,
        body_correct=bc, body_margin=bm, body_output=body_values, body_accuracy=bc.mean(axis=(2, 3, 4)),
        body_both_cues=bc.all(axis=4).mean(axis=(2, 3)), body_mean_margin=bm.mean(axis=(2, 3, 4)),
        rules=np.stack([c[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))





def audit(run, workers=8):
    started = time.monotonic()
    if hasattr(os, 'sched_getaffinity'): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:8])
    manifest = verify(run); contract = manifest['contract']
    cfg, cycle, ids = contract['config'], contract['cycle'], contract['blocks']
    assert contract['mode'] in ('technical_fixture', 'technical_benchmark', 'prospective_renewal_durability')
    technical = contract['mode'] in ('technical_fixture', 'technical_benchmark')
    assert ids == ([900031] if technical else list(range(27000, 27032)))
    if contract['mode'] != 'technical_fixture':
        assert cfg == (dict(EXPECTED, recipients=1) if technical else EXPECTED)
        assert cycle == (dict(CYCLE, read_steps=256, settling_steps=32) if technical else CYCLE)
    assert cycle['generations'] == 16 and 0 < cycle['settling_steps'] < cycle['read_steps']
    assert 0 < cfg['observe_steps'] <= cycle['read_steps'] and cycle['write_steps'] > 0
    assert contract['gain'] == 2. and contract['conditions'] == list(CONDITIONS)
    assert contract['panels'] == [list(x) for x in PANELS] and contract['receivers'] == list(RECEIVERS)
    summary = read_json(run/'summary.json')
    assert summary['evidence_status'] == ('technical' if technical else 'prospective_renewal_durability')
    for key, value in (('experiment', 'E031'), ('policy_from', 'E030'), ('prior_cases_pooled', False), ('blocks', ids), ('conditions', list(CONDITIONS)),
        ('panels', [list(x) for x in PANELS]), ('receivers', list(RECEIVERS)), ('arms', list(ARMS)),
        ('damage', list(DAMAGE)), ('cfg', cfg), ('cycle', cycle), ('gain', 2.), ('packet_bytes', 4096),
        ('founders', 4*len(ids)), ('lineages', 4*cfg['recipients']*len(ids)), ('reader_modes', list(READER_MODES)),
        ('receiving_apparatus_changed', False), ('boundary_policy', 'preserve_abs_above_05_refresh_available_weak'), ('terminal_rule_unchanged_from', 'E023'), ('full_rebuilding_unchanged_from', 'E024'), ('strength_threshold', .5), ('exact_zero_reference_included', True), ('holding_evidence', 'per_step_per_branch_sha256_little_endian_float64'), ('raw_evidence', 'E031_compact_v1'), ('transmitted_ancestry_metadata', False)):
        assert summary[key] == value, key
    assert summary['damage_during_renewal'] and summary['setting_selected'] is None
    assert summary['renewal_damage'] == dict(kind='scattered', cells=24, applied_at_birth=True, generations=16)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, cycle) for block in ids]))
    arrays = {key: np.array([r[raw] for r in results]) for key, raw in
        (('accuracy', 'accuracy'), ('both_cues', 'both_cues'), ('margin', 'mean_margin'))}
    rules = np.array([r['rules'] for r in results])
    draws = random('E031', 'bootstrap', 'maturing').integers(0, len(ids), (10000, len(ids)))

    def check(x, st):
        equal(x, st['block_means'])
        assert float(x.mean()) == st['mean']
        equal(np.quantile(x[draws].mean(axis=1), [.025, .975]), st['ci95'])

    for k, (h, condition, receiver) in enumerate(PANELS):
        group = summary['groups'][str(h)][receiver][condition]; gates = {}
        for d, damage in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for metric, arr in arrays.items(): check(arr[:, k, d, a], group[metric][damage][arm])
                if a:
                    st = group['own_minus_control'][damage][arm]
                    check(arrays['accuracy'][:, k, d, 0]-arrays['accuracy'][:, k, d, a], st)
                    gates[f'advantage_{damage}_{arm}'] = st['ci95'][0] > .10
            for r, rule in enumerate((1, -1)):
                st = group['own_accuracy_by_rule'][str(rule)][damage]
                check(rules[:, k, r, d], st); gates[f'accuracy_rule_{rule}_{damage}'] = st['ci95'][0] > .75
        assert group['gates'] == gates and group['all_original_gates_pass'] == all(gates.values())
    for h in (0, 1, 3, 8, 16):
        for condition in (('initial',) if h == 0 else CONDITIONS):
            hi, lo = (PANELS.index((h, condition, receiver)) for receiver in ('local_strength', 'fixed_four'))
            contrast = summary['receiver_contrasts'][str(h)][condition]
            for metric, arr in arrays.items():
                for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
    for h in (1, 3, 8, 16):
        for receiver in RECEIVERS:
            for candidate in ('maturing', 'strength_compensated'):
                hi = PANELS.index((h, candidate, receiver))
                for condition in CONDITIONS:
                    if condition == candidate: continue
                    lo = PANELS.index((h, condition, receiver))
                    contrast = summary['packet_contrasts'][str(h)][receiver][f'{candidate}_minus_{condition}']
                    for metric, arr in arrays.items():
                        for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
        cn, cf, mn, mf = [PANELS.index((h, condition, receiver)) for condition, receiver in
            (('maturing', 'local_strength'), ('maturing', 'fixed_four'), ('masked_copy', 'local_strength'), ('masked_copy', 'fixed_four'))]
        for metric, arr in arrays.items():
            for d, damage in enumerate(DAMAGE):
                check((arr[:, cn, d, 0]-arr[:, cf, d, 0])-(arr[:, mn, d, 0]-arr[:, mf, d, 0]),
                      summary['receiver_benefit_candidate_minus_masked_copy'][str(h)][metric][damage])
    for h in (3, 8, 16):
        for receiver in RECEIVERS:
            for condition in CONDITIONS:
                hi, lo = (PANELS.index((x, condition, receiver)) for x in (h, 1))
                for metric, arr in arrays.items():
                    for d, damage in enumerate(DAMAGE):
                        check(arr[:, hi, d, 0]-arr[:, lo, d, 0], summary['generation_changes'][str(h)][receiver][condition][metric][damage])
    boundary_gates = {f'h{h}_normalized_{condition}_{damage}':
        summary['packet_contrasts'][str(h)]['local_strength'][f'strength_compensated_minus_{condition}']['accuracy'][damage]['ci95'][0] > .10
        for h in (8, 16) for condition in ('read_blocked', 'write_blocked') for damage in DAMAGE}
    assert boundary_gates == summary['boundary_gates']
    primary = summary['primary']['statistics']
    candidate_index = PANELS.index((16, 'maturing', 'local_strength'))
    check(arrays['both_cues'][:, candidate_index, 1, 0], primary)
    noninferiority = summary['noninferiority']['statistics']
    check(arrays['both_cues'][:, candidate_index, 1, 0]-
          arrays['both_cues'][:, PANELS.index((16, 'strength_compensated', 'local_strength')), 1, 0], noninferiority)
    assert summary['primary']['margin'] == .75 and summary['noninferiority']['margin'] == -.05
    qualification = {}
    for h in (8, 16):
        candidate = summary['groups'][str(h)]['local_strength']['maturing']
        for damage in (('intact', 'scattered') if h == 8 else ('intact',)):
            qualification[f'h{h}_maturing_{damage}_both_cue_lower_above_075'] = candidate['both_cues'][damage]['own']['ci95'][0] > .75
        qualification[f'h{h}_maturing_original_24_gates'] = candidate['all_original_gates_pass']
        contrasts = summary['packet_contrasts'][str(h)]['local_strength']
        for other, cutoff in (('selective', .10), ('masked_copy', .10), ('maturing_read_blocked', 0.), ('maturing_refresh_blocked', 0.)):
            qualification[f'h{h}_maturing_minus_{other}_scattered_both_cue'] = contrasts[f'maturing_minus_{other}']['both_cues']['scattered']['ci95'][0] > cutoff
    qualification['h8_maturing_noninferior_to_full_rewriting'] = summary['packet_contrasts']['8']['local_strength']['maturing_minus_strength_compensated']['both_cues']['scattered']['ci95'][0] > -.05
    for h in (1, 3, 8, 16):
        for receiver in RECEIVERS:
            qualification[f'h{h}_{receiver}_intact_reference_original_24_gates'] = summary['groups'][str(h)][receiver]['intact_renewed']['all_original_gates_pass']
    qualification['full_rebuilding_reading_writing_12_gates'] = all(boundary_gates.values())
    assert len(qualification) == 23 and qualification == summary['qualification_gates']
    for g in range(1, 17):
        for a, n in enumerate(ACTIVE):
            for metric, raw in (('accuracy', 'body_accuracy'), ('both_cues', 'body_both_cues'), ('margin', 'body_mean_margin')):
                check(np.array([r[raw][g-1, a] for r in results]), summary['body_reading'][str(g)][CONDITIONS[n]][metric])
    passed = primary['ci95'][0] > .75
    noninferior = noninferiority['ci95'][0] > -.05
    reliability = all(qualification.values()); full = passed and noninferior and reliability
    assert summary['primary']['lower_bound_above_075'] == (None if technical else passed)
    assert summary['noninferiority']['lower_bound_above_minus_005'] == (None if technical else noninferior)
    assert summary['qualification_requirements_pass'] == (None if technical else reliability)
    assert summary['full_durability_qualified'] == (None if technical else full)
    assert summary['status'] == ('TECHNICAL_ONLY' if technical else 'DURABLE_THROUGH_16_RENEWALS' if full else 'DURABILITY_NOT_ESTABLISHED')
    count = 0
    with gzip.open(run/"observations.csv.gz", "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for k, (h, condition, receiver) in enumerate(PANELS):
                for f in range(4):
                    for r in range(cfg["recipients"]):
                        for c, cue in enumerate(CUES):
                            for d, damage in enumerate(DAMAGE):
                                for a, arm in enumerate(ARMS):
                                    row = next(reader); count += 1
                                    assert (int(row["block"]), int(row["horizon"]), row["condition"], row["receiver"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"]), row["damage"], row["arm"]) == (block, h, condition, receiver, f, int(RULES[f]), r, int(cue), damage, arm)
                                    index = (k, f, r, c, d, a)
                                    assert int(row["success"]) == result["correct"][index]
                                    assert float(row["margin"]) == result["margin"][index]
                                    assert float(row["output_A"]) == result["output"][index+(0,)]
                                    assert float(row["output_B"]) == result["output"][index+(1,)]
        assert next(reader, None) is None
    assert count == summary["individual_observations"] == len(ids)*82*4*cfg["recipients"]*2*3*7
    body_count = 0
    with gzip.open(run/"body_observations.csv.gz", "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for g in range(1, 17):
                for a, n in enumerate(ACTIVE):
                    for f in range(4):
                        for r in range(cfg["recipients"]):
                            for c, cue in enumerate(CUES):
                                row = next(reader); body_count += 1
                                assert (int(row["block"]), int(row["generation"]), row["condition"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"])) == (block, g, CONDITIONS[n], f, int(RULES[f]), r, int(cue))
                                index = (g-1, a, f, r, c)
                                assert int(row["success"]) == result["body_correct"][index]
                                assert float(row["margin"]) == result["body_margin"][index]
                                assert float(row["output_A"]) == result["body_output"][index+(0,)]
                                assert float(row["output_B"]) == result["body_output"][index+(1,)]
        assert next(reader, None) is None
    assert body_count == summary["body_individual_observations"] == len(ids)*16*8*4*cfg["recipients"]*2
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(), blocks=len(ids),
        individual_observations=count, all_teaching_renewal_and_assay_updates_replayed_exactly=True,
        record_erasure_copying_and_disrupted_boundaries_verified=True, source_isolation_exact_at_every_update=True,
        immediate_capture_and_sixteen_packet_boundaries_verified=True,
        paired_receivers_denominators_after_controls_and_zero_strength_verified=True,
        fixed_threshold_old_zero_reference_and_copied_values_verified=True,
        activity_only_refresh_and_explicit_retained_packet_verified=True,
        body_individual_observations=body_count,
        renewal_masks_dead_cells_and_incident_edges_verified=True,
        masked_copy_erasure_at_every_generation_verified=True,
        own_chain_serial_handoffs_and_cumulative_masked_copy_verified=True,
        teaching_sign_symmetry_max_error=max(r["symmetry"] for r in results),
        all_scores_intervals_and_gates_reproduced=True,
        declared_primary_noninferiority_and_durability_qualification_verified=True,
        every_holding_state_sha256_verified=True, every_raw_array_commitment_replayed=True, complete_descriptor_coverage_verified=True, complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__), workers=workers, seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as handle: json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E031 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
