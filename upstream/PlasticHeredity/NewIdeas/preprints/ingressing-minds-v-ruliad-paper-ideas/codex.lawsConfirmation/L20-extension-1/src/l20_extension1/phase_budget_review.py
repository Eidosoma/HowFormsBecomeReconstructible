"""Post-hoc D146 saved-field review; no simulation, fitting or new thresholds."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

from . import serial_compat_review as metrics

ROOT = metrics.ROOT
RUN = 'l20_extension1_phase_budget_v1_attempt1'
REVIEW = RUN + '_saved_review_v1_attempt1'
COMPLETE_SHA = '3d057c9123cf3a10d6068c356dae6b4632834c9da4f87a88f431d8ce2f5789e0'
BLOCKS = tuple(range(93000, 93016))
KINDS = tuple(t + s for t in ('base', 'read', 'write')
              for s in ('', '_copy', '_read_off', '_write_off'))
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
SELECTED = ('base', 'read', 'write', 'base_copy')
INTACT = SELECTED[:3]
CONTRASTS = {'read_minus_write': ('read', 'write'),
             'read_minus_base': ('read', 'base'), 'write_minus_base': ('write', 'base')}
SEED = 14620260918
WS = Path(__file__).resolve().parents[2]
XML = ROOT / 'logs/d146_saved_review_qualification_b.xml'
CODE = (WS / 'src/l20_extension1/phase_budget_review.py',
        WS / 'src/l20_extension1/phase_budget_review_audit.py',
        WS / 'tests/test_phase_budget_review.py',
        WS / 'phase-budget/SAVED_STATE_REVIEW_PLAN_V1.md', WS / 'phase-budget/RESULTS.md')
VALUE_KEYS = ('terminal_preference', 'outgoing_shape', 'terminal_reference_shape',
              'read_end_shape', 'write_end_shape')


def times(kind, phase):
    if kind not in SELECTED or phase not in ('read', 'write', 'terminal'):
        raise ValueError('declared condition and phase required')
    if phase == 'terminal':
        return [0, 1, 100, 300]
    if phase == 'read':
        return [0, 1, 100, 101, 300, 600] if kind == 'read' else [0, 1, 100, 101, 200, 300]
    return [0, 1, 300, 1000, 1300] if kind == 'write' else [0, 1, 300, 500, 1000]


def profile(states, role, checkpoints):
    assert len(states) == len(checkpoints) and len(set(checkpoints)) == len(checkpoints)
    return dict(times=list(checkpoints),
        preference=[metrics.preference(s[0], role) for s in states],
        reference_shape=[metrics.shape(s[2], role) for s in states],
        reference_canonical=[metrics.canonical(s[2], role) for s in states],
        body_shape=[metrics.shape(s[0], role) for s in states],
        body_canonical=[metrics.canonical(s[0], role) for s in states])


def window(p, start, end):
    if start >= end or start not in p['times'] or end not in p['times']:
        raise ValueError('two distinct saved times required')
    a, b = p['times'].index(start), p['times'].index(end)
    return dict(start=start, end=end, **{k: p[k][b] - p[k][a]
        for k in ('preference', 'reference_shape', 'reference_canonical', 'body_shape', 'body_canonical')})


def parts(left, right, role):
    old = metrics.preference_parts(left, right, role)
    return {k.replace('compatible_only', 'left_only').replace('zero_only', 'right_only'): v
            for k, v in old.items()}


def phase_changes(incoming, read_end, write_end, outgoing):
    x = np.asarray([incoming, read_end, write_end, outgoing], float)
    if not np.isfinite(x).all():
        raise ValueError('finite phase endpoints required')
    d = np.diff(x)
    assert np.isclose(d.sum(), outgoing - incoming, atol=1e-14, rtol=0)
    return dict(incoming_to_read_R=float(d[0]), read_R_to_write_R=float(d[1]),
                write_R_to_packet=float(d[2]), packet_net=float(outgoing - incoming))


def block_stats(x):
    x = np.asarray(x, float)
    if x.shape != (16, 4, 2) or not np.isfinite(x).all():
        raise ValueError('all sixteen complete blocks required')
    means = x.mean(axis=(1, 2))
    draws = np.random.default_rng(SEED).integers(0, 16, (10000, 16))
    omitted = (means.sum() - means) / 15
    return dict(mean=float(means.mean()), block_means=means.tolist(),
        original_block_bootstrap_95=np.quantile(means[draws].mean(axis=1), [.025, .975]).tolist(),
        leave_one_block_out_mean_range=[float(omitted.min()), float(omitted.max())],
        positive_contribution_to_full_mean=float(np.maximum(x, 0).sum() / 128),
        negative_contribution_to_full_mean=float(np.minimum(x, 0).sum() / 128),
        descriptive=metrics.describe(x))


def prefixes(raw, life, noise, role):
    base = CASES.index((role, 'base'))
    for kind, phase in (('read', 'read'), ('write', 'write')):
        ci = CASES.index((role, kind))
        a, b = times('base', phase), times(kind, phase)
        for t in set(a) & set(b):
            np.testing.assert_array_equal(raw[phase + '_states'][life, noise, base, 0, a.index(t)],
                                          raw[phase + '_states'][life, noise, ci, 0, b.index(t)])


def load_block(out, index):
    meta = metrics.read_json(out / f'block_{index}.json')
    keys = ('incoming', 'routed', 'outgoing', 'terminal_packet', 'read_states', 'write_states',
            'terminal_states', 'shift', 'scores', 'read_values', 'write_values', 'terminal_values',
            'record_values', 'founder_packets')
    with np.load(out / f'block_{index}.npz', allow_pickle=False) as archive:
        raw = {k: archive[k] for k in keys}
    assert meta['index'] == index and len(meta['lives']) == 4
    return raw, meta


def extract(raw, meta):
    index = meta['index']
    rows = []
    for life in range(4):
        for noise in range(2):
            for role in (0, 1):
                prefixes(raw, life, noise, role)
                f0 = metrics.decode(raw['founder_packets'][life, role])
                paths = {}
                for kind in SELECTED:
                    ci = CASES.index((role, kind))
                    generations = []
                    for gi in range(3):
                        slot = (life, noise, ci, gi)
                        entry = meta['lives'][life]['trials'][noise]['paths'][ci]['generations'][gi]
                        assert (entry['role'], entry['kind'], entry['generation']) == (role, kind, gi + 1)
                        assert entry['read_times'] == times(kind, 'read') and entry['write_times'] == times(kind, 'write')
                        assert entry['assay_steps'] == 300 and not entry['assay_enters_lineage']
                        incoming, outgoing, routed, final_packet = [metrics.decode(raw[k][slot]) for k in
                            ('incoming', 'outgoing', 'routed', 'terminal_packet')]
                        np.testing.assert_array_equal(raw['incoming'][slot], raw['founder_packets'][life, role]
                            if gi == 0 else raw['outgoing'][life, noise, ci, gi - 1])
                        if kind == 'base_copy':
                            np.testing.assert_array_equal(outgoing, f0)
                        pp = {p: profile(raw[p + '_states'][slot], role, times(kind, p))
                              for p in ('read', 'write', 'terminal')}
                        for p, values in pp.items():
                            np.testing.assert_allclose(np.array([values['preference'], values['reference_shape']]).T,
                                raw[p + '_values'][slot], atol=2e-14, rtol=0)
                        si, so = metrics.shape(incoming, role), metrics.shape(outgoing, role)
                        np.testing.assert_allclose([si, so], raw['record_values'][slot], atol=2e-14, rtol=0)
                        guide = {}
                        for name, ordinal, key in (('in', 0, 'selector'), ('out', 1, 'terminal_selector')):
                            selected = entry[key]
                            maxima = raw['scores'][slot][ordinal].max(axis=(1, 2))
                            np.testing.assert_allclose(selected['family_maxima'], maxima, atol=2e-14, rtol=0)
                            family = -1 if abs(maxima[0] - maxima[1]) <= 1e-12 else int(np.argmax(maxima))
                            assert selected['inferred_family'] == family
                            guide[name] = dict(family=family, margin=float(maxima[role] - maxima[1-role]),
                                               shift=selected['chosen_forward_shift'])
                        shift = raw['shift'][slot].tolist()
                        assert metrics.self_overlap(metrics.TARGETS[role], shift) == 1
                        final_v = raw['terminal_states'][slot][-1, 0]
                        active = np.abs(final_v) > .2
                        extended = window(pp['read'], 300, 600) if kind == 'read' else (
                            window(pp['write'], 1000, 1300) if kind == 'write' else None)
                        generations.append(dict(generation=gi + 1, profiles=pp, guide=guide, shift=shift,
                            incoming_shape=si, outgoing_shape=so,
                            outgoing_alternative_shape=metrics.shape(outgoing, 1-role),
                            outgoing_rms=float(np.sqrt(np.mean(outgoing**2))), outgoing_mean=float(outgoing.mean()),
                            routed_canonical=metrics.canonical(routed, role),
                            terminal_packet_canonical=metrics.canonical(final_packet, role),
                            terminal_packet_alternative_canonical=metrics.canonical(final_packet, 1-role),
                            terminal_reference_alternative_canonical=metrics.canonical(raw['terminal_states'][slot][-1, 2], 1-role),
                            terminal_preference=pp['terminal']['preference'][-1],
                            terminal_reference_shape=pp['terminal']['reference_shape'][-1],
                            read_end_shape=pp['read']['reference_shape'][-1],
                            write_end_shape=pp['write']['reference_shape'][-1],
                            terminal_active_cells=int(active.sum()),
                            terminal_own_matches=int(np.count_nonzero(active & ((final_v > 0) == (metrics.TARGETS[role] > 0)))),
                            terminal_alternative_matches=int(np.count_nonzero(active & ((final_v > 0) == (metrics.TARGETS[1-role] > 0)))),
                            actual_read_end_self_overlap=metrics.self_overlap(raw['read_states'][slot][-1, 2], shift),
                            phase_changes=phase_changes(si, pp['read']['reference_shape'][-1], pp['write']['reference_shape'][-1], so),
                            extra_window=extended))
                    paths[kind] = generations
                paired = {}
                for name, (left, right) in CONTRASTS.items():
                    li, ri = CASES.index((role, left)), CASES.index((role, right))
                    paired[name] = [dict(generation=g + 1,
                        **{k: paths[left][g][k] - paths[right][g][k] for k in VALUE_KEYS},
                        preference_parts=parts(raw['terminal_states'][life, noise, li, g, -1, 0],
                                               raw['terminal_states'][life, noise, ri, g, -1, 0], role)) for g in range(3)]
                rows.append(dict(block=index, life=life, noise=noise, role=role,
                    f0_shape=metrics.shape(f0, role), f0_alternative_shape=metrics.shape(f0, 1-role),
                    f0_rms=float(np.sqrt(np.mean(f0**2))), paths=paths, paired=paired))
    return rows


def identity(row):
    return [row[k] for k in ('block', 'life', 'noise', 'role')]


def masks(rows):
    if len(rows) != 128:
        raise ValueError('complete family cohort required')
    delta = np.array([r['paired']['read_minus_write'][2]['terminal_preference'] for r in rows])
    negatives = {k: np.array([r['paths'][k][2]['terminal_preference'] < 0 for r in rows]) for k in INTACT}
    return dict(all=np.ones(128, bool), read_advantage=delta > 0, write_advantage=delta < 0, tie=delta == 0,
        any_negative=np.logical_or.reduce(list(negatives.values())),
        **{'negative_' + k: value for k, value in negatives.items()})


def stratum(rows):
    result = dict(count=len(rows), ids=[identity(r) for r in rows],
        founder_blocks=len({r['block'] for r in rows}), record_host_pairs=len({(r['block'], r['life']) for r in rows}))
    if not rows:
        return result
    result['f0_shape'] = metrics.describe([r['f0_shape'] for r in rows])
    paths, paired = {}, {}
    for kind in SELECTED:
        gg = []
        for gi in range(3):
            selected = [r['paths'][kind][gi] for r in rows]
            row = dict(generation=gi + 1, metrics={k: metrics.describe([g[k] for g in selected])
                for k in (*VALUE_KEYS, 'incoming_shape', 'outgoing_alternative_shape', 'outgoing_rms',
                    'routed_canonical', 'terminal_packet_canonical', 'actual_read_end_self_overlap')},
                wrong_in_guide=sum(g['guide']['in']['family'] != rows[0]['role'] for g in selected),
                wrong_out_guide=sum(g['guide']['out']['family'] != rows[0]['role'] for g in selected),
                phase_changes={k: metrics.describe([g['phase_changes'][k] for g in selected]) for k in selected[0]['phase_changes']})
            if selected[0]['extra_window'] is not None:
                row['extra_window'] = {k: metrics.describe([g['extra_window'][k] for g in selected])
                    for k in selected[0]['extra_window'] if k not in ('start', 'end')}
                row['extra_window_times'] = [selected[0]['extra_window'][k] for k in ('start', 'end')]
            gg.append(row)
        paths[kind] = gg
    for name in CONTRASTS:
        paired[name] = [dict(generation=gi + 1,
            metrics={k: metrics.describe([r['paired'][name][gi][k] for r in rows]) for k in VALUE_KEYS},
            preference_parts_sum={k: sum(r['paired'][name][gi]['preference_parts'][k] for r in rows)
                for k in rows[0]['paired'][name][gi]['preference_parts']}) for gi in range(3)]
    result.update(paths=paths, paired=paired)
    return result


def reproduce(values, expected):
    values = np.array(values).reshape(16, 4, 2)
    np.testing.assert_allclose(values, expected['life_noise_values'], atol=2e-14, rtol=0)
    result = block_stats(values)
    np.testing.assert_allclose(result['mean'], expected['mean'], atol=2e-14, rtol=0)
    np.testing.assert_allclose(result['block_means'], expected['block_means'], atol=2e-14, rtol=0)
    np.testing.assert_allclose(result['original_block_bootstrap_95'], expected['pointwise_block_bootstrap_95'], atol=2e-14, rtol=0)
    return result


def summarize(rows, original):
    expected = {(b, l, n, r) for b in BLOCKS for l in range(4) for n in (0, 1) for r in (0, 1)}
    assert len(rows) == 256 and {tuple(identity(r)) for r in rows} == expected
    families = {}
    for role in (0, 1):
        rr = sorted((r for r in rows if r['role'] == role), key=identity)
        anchors = {}
        for kind in SELECTED:
            anchors[kind] = []
            for gi in range(3):
                group = next(g for g in original['groups'] if (g['role'], g['condition'], g['generation']) == (role, kind, gi + 1))
                anchors[kind].append({k: reproduce([r['paths'][kind][gi][k] for r in rr], group['metrics'][k])
                    for k in ('terminal_preference', 'outgoing_shape', 'write_end_shape', 'terminal_reference_shape')})
        allocation = next(g for g in original['allocation_contrasts'] if (g['role'], g['generation']) == (role, 3))
        primary = reproduce([r['paired']['read_minus_write'][2]['terminal_preference'] for r in rr], allocation['metrics']['terminal_preference'])
        anchored = {}
        for kind in INTACT:
            expected_copy = next(g for g in original['copy_contrasts'] if (g['role'], g['condition'], g['generation']) == (role, kind, 3))
            anchored[kind + '_minus_copy'] = reproduce([r['paths'][kind][2]['terminal_preference'] - r['paths']['base_copy'][2]['terminal_preference'] for r in rr], expected_copy['metrics']['terminal_preference'])
            if kind != 'base':
                expected_base = next(g for g in original['contrasts'] if (g['role'], g['condition'], g['generation']) == (role, kind, 3))
                anchored[kind + '_minus_base'] = reproduce([r['paired'][kind + '_minus_base'][2]['terminal_preference'] for r in rr], expected_base['metrics']['terminal_preference'])
        patterns = {format(i, '03b'): 0 for i in range(8)}
        for r in rr:
            patterns[''.join(str(int(r['paths'][k][2]['terminal_preference'] < 0)) for k in INTACT)] += 1
        families[str(role)] = dict(allocation_reproduction=primary, absolute_reproduction=anchors, anchor_contrasts=anchored,
            negative_pattern_order=list(INTACT), negative_patterns=patterns,
            negative_cases={k: [identity(r) for r in rr if r['paths'][k][2]['terminal_preference'] < 0] for k in SELECTED},
            zero_cases={k: [identity(r) for r in rr if r['paths'][k][2]['terminal_preference'] == 0] for k in SELECTED},
            negative_recurrence={k: metrics.sibling_signs(np.array([r['paths'][k][2]['terminal_preference'] for r in rr]).reshape(16, 4, 2)) for k in INTACT},
            strata={name: stratum([r for r, yes in zip(rr, mask) if yes]) for name, mask in masks(rr).items()})
    assert original['primary'] == next(g['metrics']['terminal_preference'] for g in original['allocation_contrasts'] if (g['role'], g['generation']) == (1, 3))
    return dict(schema='d146_saved_state_review_v1', post_hoc=True, prospective_evidence=False,
        original_primary_unchanged=True, original_primary_classification=original['primary_interval_classification'],
        new_dynamics=0, refits=0, outcome_exclusions=0, new_thresholds=0, rows=256,
        generation_endpoints=3072, original_apparatus_checks=54,
        all_original_apparatus_checks_pass=all(g['passes'] for g in original['controls']), families=families)


def source_check():
    run, out = ROOT / 'runs' / RUN, ROOT / 'outputs' / RUN
    assert metrics.sha(run / 'COMPLETE.json') == COMPLETE_SHA
    complete, manifest = metrics.read_json(run / 'COMPLETE.json'), metrics.read_json(run / 'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and metrics.read_json(run / 'STATUS.json') == complete
    assert not (run / 'FAILED.json').exists()
    assert metrics.sha(run / 'MANIFEST.json') == complete['manifest_sha256']
    assert len(manifest['input_sha256']) == 1522 and len(complete['output_sha256']) == 37
    hashes = manifest['input_sha256'] | complete['output_sha256']
    for path, value in hashes.items():
        assert metrics.sha(path) == value, path
    assert metrics.sha(out / 'output_hashes.sha256') == complete['hash_file_sha256']
    return out, hashes, complete


def resources():
    if len(os.sched_getaffinity(0)) > 6 or any(os.environ.get(k) != '1' for k in
            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')):
        raise RuntimeError('at most six CPUs and single numerical threads required')


def execute():
    began = time.monotonic()
    resources()
    destination = ROOT / 'outputs' / REVIEW
    if destination.exists():
        raise FileExistsError('single-use review path exists')
    tree = ET.parse(XML).getroot()
    assert len(tree.findall('.//testcase')) >= 20 and not any(tree.findall('.//' + k) for k in ('failure', 'error', 'skipped'))
    own = {str(p): metrics.sha(p) for p in (*CODE, XML, Path(metrics.__file__))}
    out, inputs, complete = source_check()
    original = metrics.read_json(out / 'summary.json')
    rows = []
    for block in BLOCKS:
        raw, meta = load_block(out, block)
        rows.extend(extract(raw, meta))
    summary = summarize(rows, original)
    for path, value in complete['output_sha256'].items():
        assert metrics.sha(path) == value, path
    assert own == {p: metrics.sha(p) for p in own}
    destination.mkdir()
    metrics.write_json(destination / 'rows.json', rows)
    metrics.write_json(destination / 'summary.json', summary)
    receipt = dict(status='COMPLETE', completed_utc=datetime.now(timezone.utc).isoformat(),
        review_id=REVIEW, source_complete_sha256=COMPLETE_SHA,
        original_input_hashes_verified=1522, original_outputs_verified=37,
        consumed_inputs={p: value for p, value in inputs.items() if Path(p).parent == out},
        review_code_and_plan_sha256=own, output_sha256={str(p): metrics.sha(p) for p in destination.iterdir()},
        wall_seconds=time.monotonic() - began, affinity=sorted(os.sched_getaffinity(0)),
        new_dynamics=0, original_primary_unchanged=True, all_256_rows_retained=True, post_hoc=True,
        independent_recomputed_preference_and_shape=True,
        output_bytes_before_receipt=sum(p.stat().st_size for p in destination.iterdir()))
    metrics.write_json(destination / 'COMPLETE.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', required=True)
    parser.parse_args()
    execute()
