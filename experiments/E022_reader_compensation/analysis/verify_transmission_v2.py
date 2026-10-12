"""Independent parity/closure and saved-state verification; no new dynamics."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, sha, utc
from E021_damaged_renewal.analysis.verify_boundary_diagnosis import reachable
import numpy as np

CONDITIONS = ('baseline', 'degree_compensated', 'strength_compensated', 'intact_renewed',
              'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked')
ACTIVE = (0, 1, 2, 3, 6, 7)
DAMAGE = ('intact', 'scattered', 'square')
PORTS = np.zeros((3, 16, 16), dtype=bool)
for p, (r, c) in enumerate(((7, 1), (3, 10), (11, 10))): PORTS[p, r:r+2, c:c+2] = True
TARGETS = PORTS[1] | PORTS[2]


def parity_constraints(weights, rule):
    """Parity union-find with a shared source anchor, independent of BFS labels."""
    parent = list(range(257)); parity = [0]*257; ranks = [0]*257; bad = [False]*257

    def find(u):
        if parent[u] != u:
            root, bit = find(parent[u])
            parity[u] ^= bit; parent[u] = root
        return parent[u], parity[u]

    def union(u, v, bit):
        a, x = find(u); b, y = find(v)
        if a == b:
            if (x ^ y) != bit: bad[a] = True
            return
        if ranks[a] < ranks[b]: a, b = b, a
        parent[b] = a; parity[b] = x ^ y ^ bit; bad[a] |= bad[b]
        if ranks[a] == ranks[b]: ranks[a] += 1

    for r in range(16):
        for c in range(16):
            for direction, v in ((0, 16*r+(c+1)%16), (1, 16*((r+1)%16)+c)):
                w = weights[direction, r, c]
                if w != 0: union(16*r+c, v, int(w < 0))
    for u in np.flatnonzero(PORTS[0]): union(256, int(u), 0)
    root, bit = find(256)
    aligned = not bad[root]
    for p, sign in ((1, rule), (2, -rule)):
        for u in np.flatnonzero(PORTS[p]):
            other, other_bit = find(int(u))
            aligned &= other == root and (other_bit ^ bit) == int(sign < 0)
    return bool(not bad[root]), bool(aligned)


def decode(packet):
    return np.frombuffer(packet.tobytes(), dtype='<f8').reshape(*packet.shape[:-1], 2, 16, 16)


def support(mask):
    # Explicit cell indexing, independent of rolled masks in the diagnostic.
    result = np.zeros((2, 16, 16), dtype=bool)
    for r in range(16):
        for c in range(16):
            result[0, r, c] = not (mask[r, c] or mask[r, (c+1)%16])
            result[1, r, c] = not (mask[r, c] or mask[(r+1)%16, c])
    return result


def number(value):
    if value == '': return None
    if value in ('True', 'False'): return value == 'True'
    try: return float(value)
    except ValueError: return value


def read_rows(path):
    with path.open(newline='') as handle:
        return [{k:number(v) for k, v in r.items()} for r in csv.DictReader(handle)]


def close(a, b):
    assert np.isclose(a, b, rtol=0, atol=1e-14), (a, b)


def check_aggregate(stats, rows):
    assert stats['lineages'] == len(rows)
    for k, v in stats.items():
        if not isinstance(v, dict) or 'mean' not in v: continue
        values = [r[k] for r in rows if r[k] is not None]
        close(v['mean'], np.mean(values)); close(v['minimum'], np.min(values)); close(v['maximum'], np.max(values))
        if 'count' in v: assert v['count'] == sum(values)


def check_transition(stats, before, after):
    assert len(before) == len(after)
    for x, y, key in ((True, True, 'success_success'), (True, False, 'success_failure'),
                      (False, True, 'failure_success'), (False, False, 'failure_failure')):
        assert stats[key] == sum(a == x and b == y for a, b in zip(before, after))


def classify(values, rule, cue):
    a, b = values
    if abs(a) <= .25 or abs(b) <= .25: return 'weak_output'
    if (a > 0) == (b > 0): return 'same_positive' if a > 0 else 'same_negative'
    return 'correct' if a*rule*cue > .25 else 'reversed'


def verify(analysis, destination):
    started = time.monotonic(); cap_cpus(1)
    assert analysis.is_relative_to(HERE) and destination.is_relative_to(HERE) and not destination.exists()
    check_inputs(analysis)
    completion = json.loads((analysis/'COMPLETE.json').read_text())
    assert completion['status'] == 'COMPLETE' and not (analysis/'FAILED.json').exists()
    for name, digest in completion['outputs_sha256'].items(): assert sha(analysis/name) == digest, name
    manifest = json.loads((analysis/'manifest.json').read_text())
    source = ROOT/manifest['contract']['source']; check_inputs(source)
    original = json.loads((source/'COMPLETE.json').read_text())
    provenance = json.loads((analysis/'provenance.json').read_text())
    assert provenance['source_complete_sha256'] == sha(source/'COMPLETE.json')
    assert provenance['source_audit_sha256'] == sha(source/'INDEPENDENT_AUDIT.json')
    for name, digest in provenance['consumed_source_outputs'].items():
        assert digest == original['outputs_sha256'][name] == sha(source/name), name
    s = json.loads((analysis/'summary.json').read_text())
    scientific = json.loads((source/'summary.json').read_text())
    boundaries, terminals = read_rows(analysis/'boundaries.csv'), read_rows(analysis/'terminal.csv')
    assert len(boundaries) == s['boundary_rows'] == scientific['lineages']*8
    assert len(terminals) == s['terminal_rows'] == scientific['lineages']*8*3
    index = lambda r: (int(r['block']), r['condition'], int(r['founder']), int(r['lineage']))
    bi = {index(r):r for r in boundaries}; ti = {index(r)+(r['damage'],):r for r in terminals}
    assert len(bi) == len(boundaries) and len(ti) == len(terminals)
    spin = np.ones((16, 16)); spin[PORTS[2]] = -1
    known = np.stack((spin*np.roll(spin, -1, 1), spin*np.roll(spin, -1, 0)))
    assert parity_constraints(known, 1) == (True, True)
    assert parity_constraints(known, -1) == (True, False)
    known[0, 0, 0] *= -1
    assert parity_constraints(known, 1) == (False, False)
    assert parity_constraints(np.zeros_like(known), 1) == (True, False)
    graphs = captures = 0
    for block in scientific['blocks']:
        with np.load(source/f'boundary_{block:06d}_g1.npz', allow_pickle=False) as raw:
            body, body_masks, window, computed, packet, masks, denominators = [raw[k] for k in
                ('developed_end', 'body_masks', 'developed_late_ports', 'computed_packets', 'outgoing', 'renewal_mask', 'read_denominators')]
        x = np.tanh(3*body); idx = list(range(1, 16))+[0]
        rebuilt = np.empty((*body.shape[:3], 2, 16, 16))
        for d, axis in ((0, -1), (1, -2)):
            neighbor = np.take(x, idx, axis=axis)
            # Preserve the positive-zero starting accumulator of the stored reduction.
            accumulator = np.zeros_like(x[:, :, :, 0])
            accumulator += x[:, :, :, 0]*neighbor[:, :, :, 0]
            accumulator += x[:, :, :, 1]*neighbor[:, :, :, 1]
            rebuilt[..., d, :, :] = accumulator/2
        assert np.array_equal(np.ascontiguousarray(rebuilt, dtype='<f8').view(np.uint8).reshape(computed.shape), computed)
        captures += 6*4*scientific['cfg']['recipients']
        weights = decode(packet); window = window.mean(axis=0)
        with np.load(source/f'source_{block:06d}.npz', allow_pickle=False) as raw: original_weights = decode(raw['acquired'][1])
        with np.load(source/f'assay_{block:06d}_h1.npz', allow_pickle=False) as raw:
            tm = raw['masks']; tv = raw['late_ports'].mean(axis=0); end = raw['end']
        for f in range(4):
            rule = 1 if f % 2 == 0 else -1
            for r in range(scientific['cfg']['recipients']):
                surviving = support(masks[f, r])
                terminal_support = [support(tm[f, r, d]) for d in range(3)]
                physical = [reachable(w.astype(float)) for w in terminal_support]
                for n, c in enumerate(CONDITIONS):
                    row = bi[(block, c, f, r)]; w = weights[n, f, r]; ref = original_weights[f]
                    alive_edges = np.ones_like(surviving) if n in (3, 4) else surviving
                    close(row['outgoing_mean_abs'], np.abs(w).mean())
                    assert row['outgoing_zero_edges'] == (w == 0).sum()
                    assert row['physically_deleted_edges'] == (~alive_edges).sum()
                    assert row['additional_zero_edges'] == ((w == 0) & alive_edges).sum()
                    close(row['surviving_mean_abs'], np.abs(w[alive_edges]).mean())
                    close(row['original_surviving_mean_abs'], np.abs(ref[alive_edges]).mean())
                    close(row['survivor_mean_abs_change'], np.abs(w[alive_edges]-ref[alive_edges]).mean())
                    common = (w != 0) & (ref != 0)
                    if common.any(): close(row['sign_change_fraction'], (np.sign(w[common]) != np.sign(ref[common])).mean())
                    else: assert row['sign_change_fraction'] is None
                    if n in ACTIVE:
                        a = ACTIVE.index(n); v = body[a, f, r]
                        pv = np.stack([v[:, p].mean(axis=1) for p in PORTS[1:]], axis=-1)
                        desired = rule*np.array([1, -1])
                        em = np.minimum(desired*pv[:, 0], -desired*pv[:, 1])
                        bm = np.minimum(desired*window[a, f, r, :, 0], -desired*window[a, f, r, :, 1])
                        assert row['body_end_both'] == bool((em > .25).all())
                        assert row['body_window_both'] == bool((bm > .25).all())
                        assert row['body_cue_score_disagreements'] == ((em > .25) != (bm > .25)).sum()
                        close(row['body_end_mean_margin'], em.mean()); close(row['body_window_mean_margin'], bm.mean())
                        alive = ~body_masks[a, f, r]
                        close(row['body_cue_opposition'], (v[0, alive]*v[1, alive] < 0).mean())
                        close(row['body_mean_abs_alive'], np.abs(v[:, alive]).mean())
                        close(row['reading_output_denominator_mean'], denominators[a, f, r][TARGETS].mean())
                        surviving_body = support(body_masks[a, f, r]); transformed = np.tanh(3*v)
                        conflicts = 0
                        for direction, axis in ((0, -1), (1, -2)):
                            product = transformed*np.take(transformed, idx, axis=axis)
                            conflicts += ((product[0]*product[1] < 0) & surviving_body[direction]).sum()
                        close(row['body_edge_cue_sign_conflict'], conflicts/surviving_body.sum())
                    for d, damage in enumerate(DAMAGE):
                        tr = ti[(block, c, f, r, damage)]; ew = w*terminal_support[d]
                        reached = reachable(ew)
                        assert tr['reachable_output_cells'] == reached[TARGETS].sum()
                        assert tr['source_component_cells'] == reached.sum()
                        assert tr['physical_reachable_output_cells'] == physical[d][TARGETS].sum()
                        assert tr['physical_source_component_cells'] == physical[d].sum()
                        capacity = tr['weakest_output_path_capacity']
                        if capacity > 0: assert reachable(ew, np.nextafter(capacity, -np.inf))[TARGETS].all()
                        assert not reachable(ew, capacity)[TARGETS].all()
                        consistent, aligned = parity_constraints(ew, rule)
                        assert tr['signed_source_consistent'] == consistent and tr['signed_all_outputs_aligned'] == aligned
                        assert tr['effective_nonzero_edges'] == (ew != 0).sum()
                        close(tr['effective_mean_abs'], np.abs(ew).mean())
                        strength = np.empty((16, 16))
                        for y in range(16):
                            for z in range(16):
                                strength[y, z] = abs(ew[0, y, z])+abs(ew[0, y, (z-1)%16])+abs(ew[1, y, z])+abs(ew[1, (y-1)%16, z])
                        close(tr['output_incident_mean'], strength[TARGETS].mean()); close(tr['output_incident_min'], strength[TARGETS].min())
                        values = tv[n, f, r, :, d, 0]
                        margins = [min(rule*cue*values[k, 0], -rule*cue*values[k, 1]) for k, cue in enumerate((1, -1))]
                        successes = [m > .25 for m in margins]
                        close(tr['mean_margin'], np.mean(margins))
                        assert tr['assay_both'] == all(successes)
                        ev = np.stack([end[n, f, r, :, d, 0][:, p].mean(axis=1) for p in PORTS[1:]], axis=-1)
                        assert tr['assay_end_both'] == all(min(rule*cue*ev[k, 0], -rule*cue*ev[k, 1]) > .25 for k, cue in enumerate((1, -1)))
                        supported = strength > 0
                        if supported.any():
                            endpoint = end[n, f, r, :, d, 0]
                            close(tr['end_cue_opposition_supported'], (endpoint[0, supported]*endpoint[1, supported] < 0).mean())
                        else: assert tr['end_cue_opposition_supported'] is None
                        for k, field in enumerate(('positive_cue_error', 'negative_cue_error')):
                            assert tr[field] == classify(values[k], rule, (1, -1)[k])
                        failure = 'success' if all(successes) else 'disconnected' if not reached[TARGETS].all() else 'signed_component_conflict' if not consistent else 'output_cell_sign_mismatch' if not aligned else 'compatible_graph_failed'
                        assert tr['failure_class'] == failure
                        graphs += 1
        print(f'Independently verified block {block}', flush=True)
    for c in CONDITIONS:
        group = s['groups'][c]; b = [r for r in boundaries if r['condition'] == c]
        check_aggregate(group['boundary'], b)
        if 'body_window_to_end' in group:
            check_transition(group['body_window_to_end'], [r['body_window_both'] for r in b], [r['body_end_both'] for r in b])
            assert group['body_individual_cue_disagreements'] == sum(r['body_cue_score_disagreements'] for r in b)
        intact = [r for r in terminals if r['condition'] == c and r['damage'] == 'intact']
        for damage in DAMAGE:
            t = [r for r in terminals if r['condition'] == c and r['damage'] == damage]; stats = group['terminal'][damage]
            check_aggregate(stats, t)
            check_aggregate(stats['success_descriptive'], [r for r in t if r['assay_both']])
            check_aggregate(stats['failure_descriptive'], [r for r in t if not r['assay_both']])
            assert stats['failure_classes'] == dict(Counter(r['failure_class'] for r in t))
            assert stats['individual_cue_errors'] == dict(Counter(r[k] for r in t for k in ('positive_cue_error', 'negative_cue_error')))
            check_transition(group['intact_to_terminal'][damage], [r['assay_both'] for r in intact], [r['assay_both'] for r in t])
            if damage in group['body_to_terminal']:
                check_transition(group['body_to_terminal'][damage], [r['body_end_both'] for r in b], [r['assay_both'] for r in t])
            expected = scientific['groups']['1'][c]['both_cues'][damage]['own']
            close(stats['assay_both']['mean'], expected['mean'])
            for i, block in enumerate(scientific['blocks']):
                close(np.mean([r['assay_both'] for r in t if r['block'] == block]), expected['block_means'][i])
    for other, comparisons in s['other_to_strength_transitions'].items():
        for damage, stats in comparisons.items():
            check_transition(stats,
                [r['assay_both'] for r in terminals if r['condition'] == other and r['damage'] == damage],
                [r['assay_both'] for r in terminals if r['condition'] == 'strength_compensated' and r['damage'] == damage])
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started,
        verification_code_sha256=sha(Path(__file__)), analysis_complete_sha256=sha(analysis/'COMPLETE.json'),
        analysis_original_outputs_verified=len(completion['outputs_sha256']),
        source_complete_sha256=sha(source/'COMPLETE.json'), source_audit_sha256=sha(source/'INDEPENDENT_AUDIT.json'),
        consumed_source_hashes_rechecked=len(provenance['consumed_source_outputs']),
        boundary_rows_verified=len(boundaries), terminal_rows_verified=len(terminals), independently_checked_graphs=graphs,
        independent_capture_packets_verified=captures, all_summary_counts_and_transitions_verified=True,
        unsigned_method='Explicit adjacency-matrix closure at zero, reported minimum bottleneck and preceding float.',
        signed_method='Parity union-find with a common source anchor; no diagnostic BFS imported.', new_simulation=False)
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False); handle.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        verify(args.analysis.resolve(), args.output.resolve())
    except BaseException:
        if args.output.resolve().is_relative_to(HERE) and not args.output.exists():
            with args.output.open('x') as handle:
                json.dump(dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()), handle, indent=2)
        raise
