"""Independent static reconstruction of D146 review fields and summaries."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_phase_budget_v1_attempt1'
REVIEW = RUN + '_saved_review_v1_attempt1'
COMPLETE = '3d057c9123cf3a10d6068c356dae6b4632834c9da4f87a88f431d8ce2f5789e0'
CONDITIONS = ('base', 'read', 'write', 'base_copy')
PAIRS = {'read_minus_write': ('read', 'write'), 'read_minus_base': ('read', 'base'), 'write_minus_base': ('write', 'base')}
MEASURES = ('terminal_preference', 'outgoing_shape', 'terminal_reference_shape', 'read_end_shape', 'write_end_shape')
y, x = np.indices((16, 16))
TARGET = np.stack((np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def same(actual, expected):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), (set(actual) - set(expected), set(expected) - set(actual))
        for key, value in expected.items():
            same(actual[key], value)
    elif isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            same(a, e)
    elif isinstance(expected, (float, np.floating)):
        assert np.isfinite(actual) and abs(actual - expected) <= 3e-14, (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def decode(value):
    assert value.shape == (2048,) and value.dtype == np.uint8
    result = np.frombuffer(value.tobytes(), '<f8').reshape(16, 16)
    assert np.isfinite(result).all()
    return result


def shape(value, role, translated=True):
    assert value.shape == (16, 16) and np.isfinite(value).all() and role in (0, 1)
    centered = value - value.sum() / 256
    norm = float(np.linalg.norm(centered) * 16)
    if norm == 0:
        return 0.
    candidates = range(16 if role == 0 else 8) if translated else (0,)
    return max(float(np.sum(np.roll(centered, -offset, axis=role) * TARGET[role]) / norm) for offset in candidates)


def score_map(value, role):
    own = np.logical_and(abs(value) > .2, (value > 0) == (TARGET[role] > 0))
    other = np.logical_and(abs(value) > .2, (value > 0) == (TARGET[1-role] > 0))
    return own.astype(int) - other.astype(int)


def decomposition(left, right, role):
    delta = score_map(left, role) - score_map(right, role)
    al, ar = abs(left) > .2, abs(right) > .2
    return dict(both_active_sign_net_units=int(delta[al & ar].sum()),
        left_only_active_net_units=int(delta[al & ~ar].sum()), right_only_active_net_units=int(delta[~al & ar].sum()),
        net_units=int(delta.sum()), changed_contribution_cells=int((delta != 0).sum()),
        both_active_sign_changed_cells=int(((delta != 0) & al & ar).sum()),
        left_only_active_cells=int((al & ~ar).sum()), right_only_active_cells=int((~al & ar).sum()))


def timestamps(kind, phase):
    if phase == 'terminal':
        return [0, 1, 100, 300]
    if phase == 'read':
        return [0, 1, 100, 101, 300, 600] if kind == 'read' else [0, 1, 100, 101, 200, 300]
    return [0, 1, 300, 1000, 1300] if kind == 'write' else [0, 1, 300, 500, 1000]


def trace(states, role, tt):
    return dict(times=tt, preference=[float(score_map(s[0], role).sum() / 256) for s in states],
        reference_shape=[shape(s[2], role) for s in states],
        reference_canonical=[shape(s[2], role, False) for s in states],
        body_shape=[shape(s[0], role) for s in states], body_canonical=[shape(s[0], role, False) for s in states])


def row_check(row, raw, meta):
    l, n, role = row['life'], row['noise'], row['role']
    assert row['block'] == meta['index']
    indices = {k: 12 * role + offset for k, offset in (('base', 0), ('read', 4), ('write', 8), ('base_copy', 1))}
    f0 = decode(raw['founder_packets'][l, role])
    expected = dict(block=meta['index'], life=l, noise=n, role=role,
        f0_shape=shape(f0, role), f0_alternative_shape=shape(f0, 1-role), f0_rms=float(np.linalg.norm(f0) / 16), paths={}, paired={})
    for k, ci in indices.items():
        gg = []
        for gi in range(3):
            slot = l, n, ci, gi
            entry = meta['lives'][l]['trials'][n]['paths'][ci]['generations'][gi]
            assert (entry['role'], entry['kind'], entry['generation']) == (role, k, gi + 1)
            assert entry['assay_steps'] == 300 and entry['assay_enters_lineage'] is False
            for phase in ('read', 'write'):
                assert entry[phase + '_times'] == timestamps(k, phase)
            profiles = {p: trace(raw[p + '_states'][slot], role, timestamps(k, p)) for p in ('read', 'write', 'terminal')}
            for phase, pp in profiles.items():
                np.testing.assert_allclose(np.stack((pp['preference'], pp['reference_shape']), axis=-1), raw[phase + '_values'][slot], atol=3e-14, rtol=0)
            source, output, routed, terminal = [decode(raw[name][slot]) for name in ('incoming', 'outgoing', 'routed', 'terminal_packet')]
            np.testing.assert_array_equal(raw['incoming'][slot], raw['founder_packets'][l, role] if gi == 0 else raw['outgoing'][l, n, ci, gi-1])
            if k == 'base_copy':
                np.testing.assert_array_equal(output, f0)
            guide = {}
            for name, j, key in (('in', 0, 'selector'), ('out', 1, 'terminal_selector')):
                maxima = [float(np.max(s)) for s in raw['scores'][slot][j]]
                family = -1 if abs(maxima[0] - maxima[1]) <= 1e-12 else int(maxima[1] > maxima[0])
                assert entry[key]['inferred_family'] == family
                np.testing.assert_allclose(entry[key]['family_maxima'], maxima, atol=3e-14, rtol=0)
                guide[name] = dict(family=family, margin=maxima[role] - maxima[1-role], shift=entry[key]['chosen_forward_shift'])
            a, b, c, d = shape(source, role), profiles['read']['reference_shape'][-1], profiles['write']['reference_shape'][-1], shape(output, role)
            np.testing.assert_allclose([a, d], raw['record_values'][slot], atol=3e-14, rtol=0)
            shift = raw['shift'][slot].tolist()
            assert np.array_equal(np.roll(TARGET[role], shift, (0, 1)), TARGET[role])
            r = raw['read_states'][slot][-1, 2].copy()
            r -= r.mean()
            overlap = float(np.sum(r * np.roll(r, shift, (0, 1))) / np.sum(r**2)) if np.any(r) else 0.
            v = raw['terminal_states'][slot][-1, 0]
            extended = None
            if k in ('read', 'write'):
                pp = profiles[k]
                begin, end = (300, 600) if k == 'read' else (1000, 1300)
                extended = dict(start=begin, end=end, **{name: values[pp['times'].index(end)] - values[pp['times'].index(begin)]
                    for name, values in pp.items() if name != 'times'})
            gg.append(dict(generation=gi + 1, profiles=profiles, guide=guide, shift=shift,
                incoming_shape=a, outgoing_shape=d, outgoing_alternative_shape=shape(output, 1-role),
                outgoing_rms=float(np.linalg.norm(output) / 16), outgoing_mean=float(output.sum() / 256),
                routed_canonical=shape(routed, role, False), terminal_packet_canonical=shape(terminal, role, False),
                terminal_packet_alternative_canonical=shape(terminal, 1-role, False),
                terminal_reference_alternative_canonical=shape(raw['terminal_states'][slot][-1, 2], 1-role, False),
                terminal_preference=float(score_map(v, role).sum() / 256), terminal_reference_shape=profiles['terminal']['reference_shape'][-1],
                read_end_shape=b, write_end_shape=c, terminal_active_cells=int(np.count_nonzero(abs(v) > .2)),
                terminal_own_matches=int(np.count_nonzero((abs(v) > .2) & ((v > 0) == (TARGET[role] > 0)))),
                terminal_alternative_matches=int(np.count_nonzero((abs(v) > .2) & ((v > 0) == (TARGET[1-role] > 0)))),
                actual_read_end_self_overlap=overlap, phase_changes=dict(incoming_to_read_R=b-a, read_R_to_write_R=c-b, write_R_to_packet=d-c, packet_net=d-a),
                extra_window=extended))
        expected['paths'][k] = gg
    for name, (a, b) in PAIRS.items():
        expected['paired'][name] = [dict(generation=g + 1,
            **{key: expected['paths'][a][g][key] - expected['paths'][b][g][key] for key in MEASURES},
            preference_parts=decomposition(raw['terminal_states'][l, n, indices[a], g, -1, 0], raw['terminal_states'][l, n, indices[b], g, -1, 0], role)) for g in range(3)]
    # Match timestamps explicitly; the final two read slots differ by condition.
    for kind, phase in (('read', 'read'), ('write', 'write')):
        for t in set(timestamps('base', phase)) & set(timestamps(kind, phase)):
            np.testing.assert_array_equal(raw[phase + '_states'][l, n, indices['base'], 0, timestamps('base', phase).index(t)],
                                          raw[phase + '_states'][l, n, indices[kind], 0, timestamps(kind, phase).index(t)])
    same(row, expected)


def describe(values):
    flat = np.array(values, float).ravel()
    assert len(flat) and np.isfinite(flat).all()
    return dict(mean=math.fsum(flat) / len(flat), min=float(min(flat)), max=float(max(flat)),
        quartiles=np.percentile(flat, [25, 50, 75]).tolist(), positive=int(sum(flat > 0)), negative=int(sum(flat < 0)), zero=int(sum(flat == 0)), count=len(flat))


def block_summary(values):
    flat = np.array(values, float).reshape(16, 8)
    means = np.array([math.fsum(block) / 8 for block in flat])
    draws = np.random.Generator(np.random.PCG64(14620260918)).integers(0, 16, (10000, 16))
    weights = np.stack([np.bincount(x, minlength=16) for x in draws])
    omitted = [math.fsum(means[j] for j in range(16) if j != i) / 15 for i in range(16)]
    return dict(mean=math.fsum(means) / 16, block_means=means.tolist(), original_block_bootstrap_95=np.percentile(weights @ means / 16, [2.5, 97.5]).tolist(),
        leave_one_block_out_mean_range=[min(omitted), max(omitted)],
        positive_contribution_to_full_mean=math.fsum(v for v in flat.flat if v > 0) / 128,
        negative_contribution_to_full_mean=math.fsum(v for v in flat.flat if v < 0) / 128, descriptive=describe(flat))


def key(row):
    return [row[k] for k in ('block', 'life', 'noise', 'role')]


def choose(rr):
    result = {k: [] for k in ('all', 'read_advantage', 'write_advantage', 'tie', 'any_negative', 'negative_base', 'negative_read', 'negative_write')}
    for r in rr:
        result['all'].append(r)
        delta = r['paths']['read'][2]['terminal_preference'] - r['paths']['write'][2]['terminal_preference']
        result['read_advantage' if delta > 0 else 'write_advantage' if delta < 0 else 'tie'].append(r)
        bad = [k for k in CONDITIONS[:3] if r['paths'][k][2]['terminal_preference'] < 0]
        if bad:
            result['any_negative'].append(r)
        for k in bad:
            result['negative_' + k].append(r)
    return result


def group_check(actual, rows):
    result = dict(count=len(rows), ids=[key(r) for r in rows], founder_blocks=len({r['block'] for r in rows}), record_host_pairs=len({(r['block'], r['life']) for r in rows}))
    if rows:
        result.update(f0_shape=describe([r['f0_shape'] for r in rows]), paths={}, paired={})
        for kind in CONDITIONS:
            result['paths'][kind] = []
            for gi in range(3):
                gg = [r['paths'][kind][gi] for r in rows]
                m = dict(generation=gi + 1, metrics={k: describe([g[k] for g in gg]) for k in (*MEASURES, 'incoming_shape', 'outgoing_alternative_shape', 'outgoing_rms', 'routed_canonical', 'terminal_packet_canonical', 'actual_read_end_self_overlap')},
                    wrong_in_guide=sum(g['guide']['in']['family'] != rows[0]['role'] for g in gg), wrong_out_guide=sum(g['guide']['out']['family'] != rows[0]['role'] for g in gg),
                    phase_changes={k: describe([g['phase_changes'][k] for g in gg]) for k in ('incoming_to_read_R', 'read_R_to_write_R', 'write_R_to_packet', 'packet_net')})
                if kind in ('read', 'write'):
                    m.update(extra_window={k: describe([g['extra_window'][k] for g in gg]) for k in ('preference', 'reference_shape', 'reference_canonical', 'body_shape', 'body_canonical')}, extra_window_times=[300, 600] if kind == 'read' else [1000, 1300])
                result['paths'][kind].append(m)
        for name in PAIRS:
            result['paired'][name] = [dict(generation=gi + 1, metrics={k: describe([r['paired'][name][gi][k] for r in rows]) for k in MEASURES},
                preference_parts_sum={k: sum(r['paired'][name][gi]['preference_parts'][k] for r in rows) for k in rows[0]['paired'][name][gi]['preference_parts']}) for gi in range(3)]
    same(actual, result)


def summary_check(rows, summary, original):
    expected_ids = {(b, l, n, r) for b in range(93000, 93016) for l in range(4) for n in (0, 1) for r in (0, 1)}
    assert len(rows) == 256 and {tuple(key(r)) for r in rows} == expected_ids
    header = dict(schema='d146_saved_state_review_v1', post_hoc=True, prospective_evidence=False, original_primary_unchanged=True,
        original_primary_classification=original['primary_interval_classification'], new_dynamics=0, refits=0, outcome_exclusions=0,
        new_thresholds=0, rows=256, generation_endpoints=3072, original_apparatus_checks=54,
        all_original_apparatus_checks_pass=all(g['passes'] for g in original['controls']))
    same({k: v for k, v in summary.items() if k != 'families'}, header)
    assert set(summary['families']) == {'0', '1'}
    for role in (0, 1):
        rr = sorted((r for r in rows if r['role'] == role), key=key)
        f = summary['families'][str(role)]
        assert set(f) == {'allocation_reproduction', 'absolute_reproduction', 'anchor_contrasts', 'negative_pattern_order', 'negative_patterns', 'negative_cases', 'zero_cases', 'negative_recurrence', 'strata'}
        assert set(f['absolute_reproduction']) == set(CONDITIONS)
        for kind in CONDITIONS:
            assert len(f['absolute_reproduction'][kind]) == 3
            for gi in range(3):
                source = next(g for g in original['groups'] if (g['role'], g['condition'], g['generation']) == (role, kind, gi + 1))
                assert set(f['absolute_reproduction'][kind][gi]) == {'terminal_preference', 'outgoing_shape', 'write_end_shape', 'terminal_reference_shape'}
                for m, value in f['absolute_reproduction'][kind][gi].items():
                    values = [r['paths'][kind][gi][m] for r in rr]
                    same(value, block_summary(values))
                    np.testing.assert_allclose(np.array(values).reshape(16, 4, 2), source['metrics'][m]['life_noise_values'], atol=3e-14, rtol=0)
                    same(value['original_block_bootstrap_95'], source['metrics'][m]['pointwise_block_bootstrap_95'])
        same(f['allocation_reproduction'], block_summary([r['paths']['read'][2]['terminal_preference'] - r['paths']['write'][2]['terminal_preference'] for r in rr]))
        assert set(f['anchor_contrasts']) == {'base_minus_copy', 'read_minus_copy', 'write_minus_copy', 'read_minus_base', 'write_minus_base'}
        for name, actual in f['anchor_contrasts'].items():
            left, right = name.split('_minus_')
            same(actual, block_summary([r['paths'][left][2]['terminal_preference'] - r['paths']['base_copy' if right == 'copy' else right][2]['terminal_preference'] for r in rr]))
        if role == 1:
            same(f['allocation_reproduction']['original_block_bootstrap_95'], original['primary']['pointwise_block_bootstrap_95'])
            same(f['allocation_reproduction']['mean'], original['primary']['mean'])
        patterns = {format(i, '03b'): 0 for i in range(8)}
        for r in rr:
            patterns[''.join('1' if r['paths'][k][2]['terminal_preference'] < 0 else '0' for k in CONDITIONS[:3])] += 1
        same(f['negative_pattern_order'], list(CONDITIONS[:3]))
        same(f['negative_patterns'], patterns)
        for name, check in (('negative_cases', lambda x: x < 0), ('zero_cases', lambda x: x == 0)):
            same(f[name], {k: [key(r) for r in rr if check(r['paths'][k][2]['terminal_preference'])] for k in CONDITIONS})
        assert set(f['negative_recurrence']) == set(CONDITIONS[:3])
        for kind in CONDITIONS[:3]:
            counts = [sum(r['paths'][kind][2]['terminal_preference'] < 0 for r in rr if (r['block'], r['life']) == (b, l)) for b in range(93000, 93016) for l in range(4)]
            same(f['negative_recurrence'][kind], dict(both_negative=counts.count(2), exactly_one_negative=counts.count(1), neither_negative=counts.count(0), record_host_pairs=64, address_and_noise_both_change=True))
        groups = choose(rr)
        assert set(f['strata']) == set(groups)
        for name, members in groups.items():
            group_check(f['strata'][name], members)


def main():
    began = time.monotonic()
    assert len(os.sched_getaffinity(0)) <= 6
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
    dest = ROOT / 'logs/d146_saved_review_audit_v1.json'
    if dest.exists():
        raise FileExistsError('single-use audit receipt')
    directory = ROOT / 'outputs' / REVIEW
    receipt = load(directory / 'COMPLETE.json')
    assert receipt['status'] == 'COMPLETE' and receipt['new_dynamics'] == 0 and receipt['source_complete_sha256'] == COMPLETE
    assert digest(ROOT / 'runs' / RUN / 'COMPLETE.json') == COMPLETE
    checked = {}
    for section in ('consumed_inputs', 'review_code_and_plan_sha256', 'output_sha256'):
        checked.update(receipt[section])
    for path, expected in checked.items():
        assert digest(path) == expected, path
    xml = ROOT / 'logs/d146_saved_review_qualification_b.xml'
    tree = ET.parse(xml).getroot()
    count = len(tree.findall('.//testcase'))
    assert count >= 20 and not any(tree.findall('.//' + k) for k in ('failure', 'error', 'skipped'))
    rows, summary = load(directory / 'rows.json'), load(directory / 'summary.json')
    source = ROOT / 'outputs' / RUN
    original = load(source / 'summary.json')
    for block in range(93000, 93016):
        meta = load(source / f'block_{block}.json')
        with np.load(source / f'block_{block}.npz', allow_pickle=False) as archive:
            raw = {k: archive[k] for k in ('founder_packets', 'incoming', 'routed', 'outgoing', 'terminal_packet',
                'scores', 'shift', 'read_states', 'write_states', 'terminal_states', 'read_values', 'write_values', 'terminal_values', 'record_values')}
        for row in rows:
            if row['block'] == block:
                row_check(row, raw, meta)
    summary_check(rows, summary, original)
    for path, expected in checked.items():
        assert digest(path) == expected, path
    result = dict(passes=True, completed_utc=datetime.now(timezone.utc).isoformat(), new_dynamics=0, post_hoc=True,
        review_complete_sha256=digest(directory / 'COMPLETE.json'), checker_sha256=digest(__file__), qualification_tests=count,
        qualification_sha256=digest(xml), rows_checked=256, generation_endpoints_checked=3072,
        all_profiles_and_extra_windows_checked=True, all_strata_and_negative_cases_checked=True,
        original_primary_unchanged=True, wall_seconds=time.monotonic() - began)
    with dest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
