"""Post-hoc D145 saved-field review. No simulator imports or dynamics calls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN_ID = 'l20_extension1_serial_compatible_feedback_v1_attempt1'
REVIEW_ID = RUN_ID + '_saved_review_v1_attempt1'
COMPLETE_SHA = 'adf150141ae7c5b200de105f480ce6544edc9bdcb9a5d3fb8e56477efaa03d88'
BLOCKS = tuple(range(92000, 92016))
KINDS = ('zero', 'q4', 'q-4', 'copy', 'read_off', 'write_off', 'q4_read_off', 'q4_write_off')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
TIMES = {'read': [0, 1, 100, 101, 300], 'write': [0, 1, 300, 1000], 'terminal': [0, 1, 100, 300]}
SEED = 14520260918


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def targets():
    y, x = np.indices((16, 16))
    return np.stack((np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.)))


TARGETS = targets()
# Unique translations are sufficient for the maximum, independently of the
# production implementation's 256-entry banks.
BANKS = (np.stack([np.roll(TARGETS[0], i, axis=0) for i in range(16)]),
         np.stack([np.roll(TARGETS[1], i, axis=1) for i in range(8)]))


def field(value):
    value = np.asarray(value)
    if value.shape != (16, 16) or not np.isfinite(value).all():
        raise ValueError('finite 16-by-16 field required')
    return value


def decode(packet):
    if np.asarray(packet).shape != (2048,) or np.asarray(packet).dtype != np.uint8:
        raise ValueError('original 2048-byte record required')
    return field(np.frombuffer(np.asarray(packet).tobytes(), dtype='<f8').reshape(16, 16))


def shape(value, role):
    if role not in (0, 1):
        raise ValueError('two target families only')
    z = field(value) - np.mean(value)
    scale = np.sqrt(np.mean(z * z))
    return float(np.max(np.mean(BANKS[role] * z, axis=(1, 2))) / scale) if scale else 0.


def canonical(value, role):
    z = field(value) - np.mean(value)
    scale = np.sqrt(np.mean(z * z))
    return float(np.mean(TARGETS[role] * z) / scale) if scale else 0.


def self_overlap(value, shift):
    if len(shift) != 2:
        raise ValueError('two-dimensional address required')
    z = field(value) - np.mean(value)
    power = np.mean(z * z)
    return float(np.mean(z * np.roll(z, tuple(shift), (0, 1))) / power) if power else 0.


def contributions(v, role):
    active = np.abs(field(v)) > .2
    own = ((v > 0) == (TARGETS[role] > 0)).astype(np.int64)
    other = ((v > 0) == (TARGETS[1 - role] > 0)).astype(np.int64)
    return (own - other) * active


def preference(v, role):
    return float(contributions(v, role).sum() / 256)


def preference_parts(q, z, role):
    """An exact identity for the unchanged endpoint, not a threshold sweep."""
    cq, cz = contributions(q, role), contributions(z, role)
    aq, az = np.abs(q) > .2, np.abs(z) > .2
    delta = cq - cz
    parts = {
        'both_active_sign_net_units': int(delta[aq & az].sum()),
        'compatible_only_active_net_units': int(delta[aq & ~az].sum()),
        'zero_only_active_net_units': int(delta[~aq & az].sum()),
        'net_units': int(delta.sum()),
        'changed_contribution_cells': int(np.count_nonzero(delta)),
        'both_active_sign_changed_cells': int(np.count_nonzero((delta != 0) & aq & az)),
        'compatible_only_active_cells': int(np.count_nonzero(aq & ~az)),
        'zero_only_active_cells': int(np.count_nonzero(~aq & az)),
    }
    assert sum(parts[k] for k in ('both_active_sign_net_units',
        'compatible_only_active_net_units', 'zero_only_active_net_units')) == parts['net_units']
    assert parts['net_units'] / 256 == preference(q, role) - preference(z, role)
    return parts


def signs(x):
    x = np.asarray(x)
    if not np.isfinite(x).all():
        raise ValueError('no nonfinite values or exclusions')
    return dict(positive=int(np.count_nonzero(x > 0)), negative=int(np.count_nonzero(x < 0)),
                zero=int(np.count_nonzero(x == 0)), count=int(x.size))


def describe(x):
    x = np.asarray(x, float)
    if not x.size or not np.isfinite(x).all():
        raise ValueError('nonempty finite complete values required')
    return dict(mean=float(x.mean()), min=float(x.min()), max=float(x.max()),
                quartiles=np.quantile(x, [.25, .5, .75]).tolist(), **signs(x))


def sibling_signs(x):
    x = np.asarray(x)
    if x.shape != (16, 4, 2):
        raise ValueError('all sixteen blocks, four lives and two replicas required')
    count = (x < 0).sum(axis=-1)
    return dict(both_negative=int(np.count_nonzero(count == 2)),
                exactly_one_negative=int(np.count_nonzero(count == 1)),
                neither_negative=int(np.count_nonzero(count == 0)),
                record_host_pairs=64, address_and_noise_both_change=True)


def block_stats(x):
    x = np.asarray(x)
    if x.shape != (16, 4, 2) or not np.isfinite(x).all():
        raise ValueError('complete block panel required')
    means = x.mean(axis=(1, 2))
    draws = np.random.default_rng(SEED).integers(0, 16, (10000, 16))
    ci = np.quantile(means[draws].mean(axis=1), [.025, .975])
    omitted_means = (means.sum() - means) / 15
    return dict(mean=float(means.mean()), block_means=means.tolist(),
                original_block_bootstrap_95=ci.tolist(),
                leave_one_block_out_mean_range=[float(omitted_means.min()), float(omitted_means.max())],
                leave_one_block_out_is_new_test=False)


def check_saved_sources():
    run, out = ROOT / 'runs' / RUN_ID, ROOT / 'outputs' / RUN_ID
    assert sha(run / 'COMPLETE.json') == COMPLETE_SHA
    complete, manifest = read_json(run / 'COMPLETE.json'), read_json(run / 'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and read_json(run / 'STATUS.json') == complete
    assert not (run / 'FAILED.json').exists()
    assert sha(run / 'MANIFEST.json') == complete['manifest_sha256']
    hashes = manifest['input_sha256'] | complete['output_sha256']
    assert len(manifest['input_sha256']) == 1456 and len(complete['output_sha256']) == 37
    for path, expected in hashes.items():
        assert sha(path) == expected, path
    assert sha(out / 'output_hashes.sha256') == complete['hash_file_sha256']
    return out, hashes, complete


def extract_block(out, index, original_summary):
    meta = read_json(out / f'block_{index}.json')
    with np.load(out / f'block_{index}.npz', allow_pickle=False) as archive:
        keys = ('incoming', 'routed', 'outgoing', 'terminal_packet', 'read_states', 'write_states',
                'terminal_states', 'shift', 'scores', 'read_values', 'write_values', 'terminal_values',
                'record_values', 'founder_packets')
        raw = {k: archive[k] for k in keys}
    assert meta['index'] == index and len(meta['lives']) == 4
    rows = []
    for life in range(4):
        for noise in range(2):
            for role in (0, 1):
                paths = {}
                for kind in ('zero', 'q4'):
                    ci = CASES.index((role, kind))
                    f0 = decode(raw['founder_packets'][life, role])
                    generations = []
                    for gi in range(3):
                        slot = (life, noise, ci, gi)
                        entry = meta['lives'][life]['trials'][noise]['paths'][ci]['generations'][gi]
                        assert (entry['role'], entry['kind'], entry['generation']) == (role, kind, gi + 1)
                        incoming, outgoing, routed, terminal_packet = [decode(raw[k][slot]) for k in
                            ('incoming', 'outgoing', 'routed', 'terminal_packet')]
                        shift = raw['shift'][slot].tolist()
                        assert self_overlap(TARGETS[role], shift) == 1.
                        profiles = {}
                        for phase in TIMES:
                            states = raw[phase + '_states'][slot]
                            profile = np.array([[preference(s[0], role), shape(s[2], role)] for s in states])
                            np.testing.assert_allclose(profile, raw[phase + '_values'][slot], atol=2e-14, rtol=0)
                            profiles[phase] = dict(times=TIMES[phase], preference=profile[:, 0].tolist(),
                                reference_shape=profile[:, 1].tolist())
                        record_shapes = [shape(incoming, role), shape(outgoing, role)]
                        np.testing.assert_allclose(record_shapes, raw['record_values'][slot], atol=2e-14, rtol=0)
                        group = next(g for g in original_summary['groups'] if
                            (g['role'], g['condition'], g['generation']) == (role, kind, gi + 1))
                        expected = group['metrics']['outgoing_shape']['life_noise_values'][index - BLOCKS[0]][life][noise]
                        np.testing.assert_allclose(record_shapes[1], expected, atol=2e-14, rtol=0)
                        score = raw['scores'][slot]
                        final_v = raw['terminal_states'][slot][-1, 0]
                        generations.append(dict(generation=gi + 1, shift=shift, profiles=profiles,
                            incoming_shape=record_shapes[0], outgoing_shape=record_shapes[1],
                            terminal_preference=profiles['terminal']['preference'][-1],
                            terminal_reference_shape=profiles['terminal']['reference_shape'][-1],
                            write_end_shape=profiles['write']['reference_shape'][-1],
                            read_end_shape=profiles['read']['reference_shape'][-1],
                            write_shape_change=profiles['write']['reference_shape'][-1]-profiles['read']['reference_shape'][-1],
                            terminal_reference_canonical=canonical(raw['terminal_states'][slot][-1, 2], role),
                            outgoing_rms=float(np.sqrt(np.mean(outgoing ** 2))), outgoing_mean=float(outgoing.mean()),
                            routed_canonical=canonical(routed, role), terminal_packet_canonical=canonical(terminal_packet, role),
                            actual_incoming_self_overlap=self_overlap(incoming, shift),
                            actual_read_end_self_overlap=self_overlap(raw['read_states'][slot][-1, 2], shift),
                            guide_in_family=entry['selector']['inferred_family'],
                            guide_out_family=entry['terminal_selector']['inferred_family'],
                            guide_in_margin=float(score[0, role].max()-score[0, 1-role].max()),
                            guide_out_margin=float(score[1, role].max()-score[1, 1-role].max()),
                            guide_in_shift=entry['selector']['chosen_forward_shift'],
                            guide_out_shift=entry['terminal_selector']['chosen_forward_shift'],
                            terminal_active_cells=int(np.count_nonzero(np.abs(final_v) > .2))))
                    paths[kind] = dict(f0_shape=shape(f0, role), f0_alternative_shape=shape(f0, 1-role),
                        f0_rms=float(np.sqrt(np.mean(f0 ** 2))), generations=generations)
                differences = []
                for gi in range(3):
                    q, z = paths['q4']['generations'][gi], paths['zero']['generations'][gi]
                    qi, zi = CASES.index((role, 'q4')), CASES.index((role, 'zero'))
                    parts = preference_parts(raw['terminal_states'][life, noise, qi, gi, -1, 0],
                                             raw['terminal_states'][life, noise, zi, gi, -1, 0], role)
                    differences.append(dict(generation=gi + 1,
                        **{k: q[k]-z[k] for k in ('terminal_preference', 'outgoing_shape',
                            'write_end_shape', 'terminal_reference_shape', 'read_end_shape')},
                        terminal_preference_parts=parts))
                rows.append(dict(block=index, life=life, noise=noise, role=role, paths=paths,
                    paired=differences, host=meta['lives'][life]['host']['tissue']))
    return rows


def corr(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(np.corrcoef(a, b)[0, 1]) if a.std() and b.std() else None


def summarize(rows, original):
    assert len(rows) == 256 and len({(r['block'], r['life'], r['noise'], r['role']) for r in rows}) == 256
    result = {}
    for role in (0, 1):
        rr = sorted((r for r in rows if r['role'] == role), key=lambda r: (r['block'], r['life'], r['noise']))
        paired = np.array([r['paired'][-1]['terminal_preference'] for r in rr]).reshape(16, 4, 2)
        original_metric = next(c['metrics']['terminal_preference'] for c in original['contrasts']
            if (c['role'], c['condition'], c['generation']) == (role, 'q4', 3))
        assert paired.tolist() == original_metric['life_noise_values']
        assert block_stats(paired)['original_block_bootstrap_95'] == original_metric['pointwise_block_bootstrap_95']
        serial = np.array([r['paths']['q4']['generations'][2]['outgoing_shape']-
            r['paths']['q4']['generations'][0]['outgoing_shape'] for r in rr]).reshape(16, 4, 2)
        original_serial = next(c['metrics']['outgoing_shape'] for c in original['serial_changes']
            if (c['role'], c['condition']) == (role, 'q4'))
        np.testing.assert_allclose(serial, original_serial['life_noise_values'], atol=2e-14, rtol=0)
        np.testing.assert_allclose(block_stats(serial)['original_block_bootstrap_95'],
                                  original_serial['pointwise_block_bootstrap_95'], atol=2e-14, rtol=0)
        subsets = {}
        for name, keep in (('all', np.ones(128, bool)), ('negative', paired.ravel() < 0),
                           ('positive', paired.ravel() > 0), ('zero', paired.ravel() == 0)):
            chosen = [r for r, yes in zip(rr, keep) if yes]
            if not chosen:
                subsets[name] = dict(count=0)
                continue
            items = dict(count=len(chosen), independent_blocks=len({r['block'] for r in chosen}),
                distinct_record_host_pairs=len({(r['block'], r['life']) for r in chosen}),
                f0_shape=describe([r['paths']['q4']['f0_shape'] for r in chosen]),
                generation_metrics=[], paired_generation_metrics=[],
                preference_parts={k: describe([r['paired'][-1]['terminal_preference_parts'][k] for r in chosen])
                                  for k in chosen[0]['paired'][-1]['terminal_preference_parts']})
            for gi in range(3):
                items['paired_generation_metrics'].append({k: describe([r['paired'][gi][k] for r in chosen])
                    for k in ('terminal_preference', 'outgoing_shape', 'read_end_shape',
                              'write_end_shape', 'terminal_reference_shape')})
                items['generation_metrics'].append({kind: {k: describe([r['paths'][kind]['generations'][gi][k]
                    for r in chosen]) for k in ('outgoing_shape', 'terminal_preference', 'write_shape_change',
                        'routed_canonical', 'terminal_packet_canonical', 'actual_incoming_self_overlap',
                        'actual_read_end_self_overlap', 'guide_out_margin', 'terminal_active_cells',
                        'outgoing_rms', 'outgoing_mean')} for kind in ('zero', 'q4')})
            subsets[name] = items
        def brief(r):
            return dict(block=r['block'], life=r['life'], noise=r['noise'],
                f0_shape=r['paths']['q4']['f0_shape'], paired=r['paired'],
                q_shapes=[g['outgoing_shape'] for g in r['paths']['q4']['generations']],
                zero_shapes=[g['outgoing_shape'] for g in r['paths']['zero']['generations']],
                q_preferences=[g['terminal_preference'] for g in r['paths']['q4']['generations']],
                q_shifts=[g['shift'] for g in r['paths']['q4']['generations']])
        result[str(role)] = dict(subsets=subsets, primary_reproduction=block_stats(paired),
            preference_sibling_recurrence=sibling_signs(paired),
            all_negative_preference_cases=[brief(r) for r, v in zip(rr, paired.ravel()) if v < 0],
            serial_shape=dict(descriptive=describe(serial), original_inference_reproduced=block_stats(serial),
                positive_contribution_to_full_mean=float(np.maximum(serial, 0).sum()/128),
                negative_contribution_to_full_mean=float(np.minimum(serial, 0).sum()/128),
                sibling_recurrence=sibling_signs(serial),
                all_negative_change_cases=[brief(r) for r, v in zip(rr, serial.ravel()) if v < 0],
                correlations_descriptive_only=dict(
                    f0_shape_vs_change=corr([r['paths']['q4']['f0_shape'] for r in rr], serial.ravel()),
                    g1_shape_vs_change_mathematically_coupled=corr(
                        [r['paths']['q4']['generations'][0]['outgoing_shape'] for r in rr], serial.ravel()),
                    late_shape_change_vs_final_preference_difference=corr(serial.ravel(), paired.ravel()))))
    return dict(schema='d145_saved_state_review_v1', post_hoc=True, prospective_evidence=False,
        new_dynamics=0, refits=0, outcome_exclusions=0, new_thresholds=0, rows=256,
        original_primary_unchanged=True, families=result)


def execute():
    started = time.monotonic()
    if len(os.sched_getaffinity(0)) > 6:
        raise RuntimeError('at most six CPUs required')
    if any(os.environ.get(k) != '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')):
        raise RuntimeError('numerical threads must be one')
    destination = ROOT / 'outputs' / REVIEW_ID
    if destination.exists():
        raise FileExistsError('single-use review directory already exists')
    out, inputs, complete = check_saved_sources()
    original = read_json(out / 'summary.json')
    rows = []
    for index in BLOCKS:
        rows.extend(extract_block(out, index, original))
    summary = summarize(rows, original)
    # Recheck the actual consumed D145 artifacts after computation; never write
    # to their directory, receipt, summary or scientific sources.
    for path, expected in complete['output_sha256'].items():
        assert sha(path) == expected, path
    destination.mkdir()
    write_json(destination / 'rows.json', rows)
    write_json(destination / 'summary.json', summary)
    ws = Path(__file__).resolve().parents[2]
    own = [Path(__file__).resolve(), ws/'tests/test_serial_compat_review.py',
           ws/'serial-compatible-feedback/SAVED_STATE_REVIEW_PLAN_V1.md']
    receipt = dict(status='COMPLETE', completed_utc=datetime.now(timezone.utc).isoformat(),
        review_id=REVIEW_ID, source_complete_sha256=COMPLETE_SHA,
        original_input_hashes_verified=1456, original_outputs_verified=37,
        consumed_inputs={k: v for k, v in inputs.items() if Path(k).parent == out},
        review_code_and_plan_sha256={str(p): sha(p) for p in own},
        output_sha256={str(p): sha(p) for p in destination.iterdir()},
        wall_seconds=time.monotonic()-started, affinity=sorted(os.sched_getaffinity(0)),
        new_dynamics=0, original_primary_unchanged=True, all_256_main_rule_pairs_retained=True,
        independent_recomputed_preference_and_shape=True, post_hoc=True,
        output_bytes_before_receipt=sum(p.stat().st_size for p in destination.iterdir()))
    write_json(destination / 'COMPLETE.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', required=True)
    parser.parse_args()
    execute()
