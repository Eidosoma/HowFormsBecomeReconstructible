"""Post-result saved-state description only; no simulator or predictor imports."""
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
RUN = 'l20_extension1_heldout_v1_attempt1'
SOURCE = ROOT / 'outputs' / RUN
COMPLETE = ROOT / 'runs' / RUN / 'COMPLETE.json'
COMPLETE_SHA = '818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918'
DESTINATION = ROOT / 'analyses' / 'd141_heldout_late_loss_v1'
BLOCKS = tuple(range(90000, 90016))
CASES = tuple((r, m) for r in (0, 1) for m in ('translated', 'aligned'))
MODELS = ('starting_only', 'passive', 'challenge')
YY, XX = np.indices((16, 16))
TARGETS = np.stack((np.where(YY < 8, 1., -1.), np.where(XX % 8 < 4, 1., -1.)))
BANK = np.stack([[np.roll(t, divmod(i, 16), (0, 1)) for i in range(256)] for t in TARGETS])
TARGET_FFT = np.fft.fft2(TARGETS)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(part)
    return hasher.hexdigest()


def read_json(path):
    with Path(path).open() as stream:
        return json.load(stream)


def verify_sources():
    if digest(COMPLETE) != COMPLETE_SHA:
        raise ValueError('source COMPLETE differs from independently audited result')
    receipt = read_json(COMPLETE)
    assert receipt['status'] == 'COMPLETE'
    assert receipt['run_id'] == RUN
    assert len(receipt['output_sha256']) == 102
    assert digest(SOURCE / 'output_hashes.sha256') == receipt['hash_file_sha256']
    for name, expected in receipt['output_sha256'].items():
        path = Path(name)
        assert path.parent.resolve() == SOURCE.resolve()
        if digest(path) != expected:
            raise ValueError(f'sealed output changed: {path.name}')
    return receipt


def field(value):
    a = np.asarray(value)
    if a.shape != (16, 16) or not np.isfinite(a).all():
        raise ValueError('finite 16-by-16 field required')
    return a


def decode(packet):
    packet = np.asarray(packet)
    if packet.dtype != np.uint8 or packet.shape != (2048,):
        raise ValueError('2048-byte ordinary record required')
    return field(np.frombuffer(packet.tobytes(), dtype='<f8').reshape(16, 16))


def preference(v, role):
    if role not in (0, 1):
        raise ValueError('declared target family required')
    v = field(v)
    own = (v > 0) == (TARGETS[role] > 0)
    other = (v > 0) == (TARGETS[1-role] > 0)
    active = np.abs(v) > .2
    return float((np.count_nonzero(own & active) - np.count_nonzero(other & active)) / 256)


def shape(value, role):
    if role not in (0, 1):
        raise ValueError('declared target family required')
    a = field(value)
    z = a - a.mean()
    scale = float(np.sqrt(np.mean(z*z)))
    if scale:
        direct = np.einsum('rsij,ij->rs', BANK, z, optimize=False) / (256 * scale)
        fft = np.fft.ifft2(np.fft.fft2(z)[None] * np.conjugate(TARGET_FFT)).real / (256 * scale)
        best = direct.max(axis=1)
        difference = float(np.max(np.abs(best - fft.max(axis=(1, 2)))))
        if difference > 1e-12:
            raise ValueError('direct/FFT shape disagreement')
        canonical = np.mean(TARGETS * z, axis=(1, 2)) / scale
    else:
        best, canonical, difference = np.zeros(2), np.zeros(2), 0.
    return dict(own_best=float(best[role]), alternative_best=float(best[1-role]),
                best_margin=float(best[role] - best[1-role]),
                own_canonical=float(canonical[role]),
                canonical_margin=float(canonical[role] - canonical[1-role]),
                rms=float(np.sqrt(np.mean(a*a))), direct_fft_max_error=difference)


def first_negative(values):
    return next((i + 1 for i, v in enumerate(values) if v < 0), None)


def correlation(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.shape != y.shape or x.ndim != 1 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('paired finite vectors required')
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def body(v, role):
    return dict(preference=preference(v, role), active_fraction=float(np.mean(abs(v) > .2)),
                sign_preference=float(np.mean((v > 0) == (TARGETS[role] > 0)) -
                                      np.mean((v > 0) == (TARGETS[1-role] > 0))),
                **shape(v, role))


def family_choice(selector, role):
    maxima = selector['family_maxima']
    return dict(inferred_family=selector['inferred_family'], tie=selector['family_tie'],
                own_margin=float(maxima[role] - maxima[1-role]),
                shift=selector['chosen_forward_shift'])


def extract():
    forecasts = read_json(SOURCE / 'forecasts.json')
    keys = [(r['block'], r['life'], r['family'], r['writer']) for r in forecasts]
    expected = [(b, l, r, m) for b in BLOCKS for l in range(4) for r, m in CASES]
    assert keys == expected
    saved_summary = read_json(SOURCE / 'summary.json')
    rows = []
    for block in BLOCKS:
        lm = read_json(SOURCE / f'lineage_{block}.json')
        dm = read_json(SOURCE / f'diagnostic_{block}.json')
        assert lm['index'] == dm['index'] == block
        with np.load(SOURCE / f'lineage_{block}.npz', allow_pickle=False) as opened:
            raw = {k: opened[k] for k in ('targets', 'founder_packets', 'incoming', 'routed', 'outgoing',
                'generation_read_states', 'generation_write_states', 'terminal_inputs', 'terminal_packets',
                'terminal_states', 'values', 'terminal_values')}
        with np.load(SOURCE / f'diagnostic_{block}.npz', allow_pickle=False) as opened:
            diag = {k: opened[k] for k in ('founder_packets', 'initial_features', 'diagnostic_features',
                'terminal_states', 'changed_sites')}
        for life in range(4):
            np.testing.assert_array_equal(raw['targets'][life], TARGETS)
            np.testing.assert_array_equal(raw['founder_packets'][life], diag['founder_packets'][life])
            assert lm['lives'][life]['life'] == dm['lives'][life]['life'] == life
            cases = [tuple(c) for c in lm['lives'][life]['cases']]
            probes = [tuple(c) for c in lm['lives'][life]['probes']]
            assert [tuple(c) for c in dm['lives'][life]['cases']] == list(CASES)
            for ci, (role, writer) in enumerate(CASES):
                ki, pi = cases.index((role, writer)), probes.index((role, writer))
                forecast = forecasts[len(rows)]
                start = raw['founder_packets'][life, role]
                np.testing.assert_array_equal(raw['incoming'][life, ki, 0], start)
                record_fields = [decode(start)] + [decode(p) for p in raw['outgoing'][life, ki]]
                records = [shape(a, role) for a in record_fields]
                stages, segments = [], []
                for g in range(4):
                    if g < 3:
                        states = raw['generation_read_states'][life, ki, g]
                        routed = decode(raw['routed'][life, ki, g])
                        selector = lm['lives'][life]['generations'][ki][g]['selector']
                        saved = raw['values'][life, ki, g, -1]
                        np.testing.assert_array_equal(decode(raw['incoming'][life, ki, g]), record_fields[g])
                    else:
                        states = raw['terminal_states'][life, pi]
                        routed = decode(raw['terminal_packets'][life, pi])
                        selector = lm['lives'][life]['terminal'][pi]['selector']
                        saved = raw['terminal_values'][life, pi, -1]
                        np.testing.assert_array_equal(decode(raw['terminal_inputs'][life, pi]), record_fields[g])
                    values = body(states[-1, 0], role)
                    assert values['preference'] == saved[0] - saved[1]
                    assert values['sign_preference'] == saved[2] - saved[3]
                    assert values['active_fraction'] == saved[4]
                    route_shape, reference = shape(routed, role), shape(states[-1, 2], role)
                    assert abs(route_shape['own_best'] - records[g]['own_best']) < 1e-12
                    stages.append(dict(stage=g+1, body=values, reference=reference,
                        routed=route_shape, guide=family_choice(selector, role)))
                    if g < 3:
                        writes = raw['generation_write_states'][life, ki, g]
                        np.testing.assert_array_equal(writes[0, :3], states[-1])
                        assert not np.count_nonzero(writes[0, 3])
                        end_ref = shape(writes[-1, 2], role)
                        a, b, c, d, e = [x['own_best'] for x in
                            (records[g], route_shape, reference, end_ref, records[g+1])]
                        parts = [b-a, c-b, d-c, e-d]
                        assert abs(sum(parts) - (e-a)) < 1e-12
                        segments.append(dict(generation=g+1, routing=parts[0], reading_reference=parts[1],
                            writing_reference=parts[2], record_construction=parts[3], net=e-a, write_end_R=end_ref))
                dp = []
                for branch in range(3):
                    p = preference(diag['terminal_states'][life, ci, branch, -1, 0], role)
                    assert p == diag['diagnostic_features'][life, ci, branch, 4]
                    dp.append(p)
                start_features = diag['initial_features'][life, ci]
                cycle_features = diag['diagnostic_features'][life, ci]
                np.testing.assert_array_equal(start_features, forecast['features']['starting_only'])
                np.testing.assert_array_equal(np.r_[start_features, cycle_features[0], cycle_features[1]],
                                              forecast['features']['passive'])
                np.testing.assert_array_equal(np.r_[start_features, cycle_features[0], cycle_features[2]],
                                              forecast['features']['challenge'])
                assert abs(records[0]['own_best'] - start_features[0]) < 1e-12
                prefs = [s['body']['preference'] for s in stages]
                diagnostics = []
                for bi, name in enumerate(('U0', 'U1', 'C1')):
                    entry = dm['lives'][life]['cycles'][ci][bi]
                    diagnostics.append(dict(branch=name, features=cycle_features[bi].tolist(),
                        preference=dp[bi], input_guide=family_choice(entry['selector'], role),
                        output_guide=family_choice(entry['terminal_selector'], role)))
                rows.append(dict(block=block, life=life, family=role, writer=writer,
                    initial_features=start_features.tolist(), records=records, stages=stages,
                    preference=prefs, first_negative_stage=first_negative(prefs),
                    diagnostics=diagnostics, changed_sites=int(diag['changed_sites'][life, ci]),
                    phase_changes=segments, predictions=forecast['predictions'],
                    squared_error={k: (forecast['predictions'][k] - prefs[-1])**2 for k in MODELS}))
    assert len(rows) == 256
    for k in MODELS:
        assert abs(np.mean([r['squared_error'][k] for r in rows]) - saved_summary['secondary'][k]['mse']) < 1e-15
    return rows, saved_summary


def summarize(rows, saved_summary):
    groups = {}
    for role, writer in CASES:
        selected = [r for r in rows if (r['family'], r['writer']) == (role, writer)]
        assert len(selected) == 64 and len({r['block'] for r in selected}) == 16
        p = np.array([r['preference'] for r in selected])
        d = np.array([[b['preference'] for b in r['diagnostics']] for r in selected])
        guides = np.array([[s['guide']['inferred_family'] == role for s in r['stages']] for r in selected])
        own = np.array([[s['own_best'] for s in r['records']] for r in selected])
        margins = np.array([[s['best_margin'] for s in r['records']] for r in selected])
        negatives = p[:, -1] < 0
        group_error = {k: sum(r['squared_error'][k] for r in selected) for k in MODELS}
        phases = {k: np.array([[s[k] for s in r['phase_changes']] for r in selected])
                  for k in ('routing', 'reading_reference', 'writing_reference', 'record_construction', 'net')}
        first = [r['first_negative_stage'] for r in selected]
        diagnostics_wrong = {key: [sum(r['diagnostics'][bi][key]['inferred_family'] != role for r in selected)
                                  for bi in range(3)] for key in ('input_guide', 'output_guide')}
        block_rows = [dict(block=b, terminal_negative=sum(r['preference'][-1] < 0 for r in selected if r['block'] == b),
            record_shape_change_mean=float(np.mean([r['records'][-1]['own_best'] - r['records'][0]['own_best']
                                                    for r in selected if r['block'] == b]))) for b in BLOCKS]
        groups[f'{"AB"[role]}_{writer}'] = dict(
            cases=64, independent_blocks=16,
            mean_preference=p.mean(axis=0).tolist(), negative_preference_counts=(p < 0).sum(axis=0).tolist(),
            zero_preference_counts=(p == 0).sum(axis=0).tolist(),
            first_negative_stage_counts={str(k): first.count(k) for k in (1, 2, 3, 4, None)},
            guide_non_own_counts=(~guides).sum(axis=0).tolist(),
            guide_tie_counts=[sum(s['stages'][g]['guide']['tie'] for s in selected) for g in range(4)],
            negative_preference_despite_own_guide_counts=((p < 0) & guides).sum(axis=0).tolist(),
            negative_record_margin_counts=(margins < 0).sum(axis=0).tolist(),
            negative_record_margin_despite_own_guide_counts=((margins < 0) & guides).sum(axis=0).tolist(),
            mean_record_best=own.mean(axis=0).tolist(),
            total_record_shape_decline_cases=int(np.sum(own[:, -1] < own[:, 0])),
            total_record_shape_decline_blocks=sum(b['record_shape_change_mean'] < 0 for b in block_rows),
            mean_read_end_reference_best=np.mean([[s['reference']['own_best'] for s in r['stages']] for r in selected], axis=0).tolist(),
            mean_read_end_body_best=np.mean([[s['body']['own_best'] for s in r['stages']] for r in selected], axis=0).tolist(),
            mean_phase_changes={k: a.mean(axis=0).tolist() for k, a in phases.items()},
            negative_phase_change_counts={k: (a < -1e-12).sum(axis=0).tolist() for k, a in phases.items()},
            diagnostic_mean_preference=d.mean(axis=0).tolist(),
            diagnostic_negative_counts=(d < 0).sum(axis=0).tolist(),
            diagnostic_zero_counts=(d == 0).sum(axis=0).tolist(),
            diagnostic_non_own_guide_counts=diagnostics_wrong,
            challenge_minus_matched_intact_preference_mean=float(np.mean(d[:, 2]-d[:, 1])),
            challenge_minus_matched_intact_preference_negative_cases=int(np.sum(d[:, 2] < d[:, 1])),
            negative_terminal_with_all_three_diagnostics_positive=int(np.sum(negatives & (d > 0).all(axis=1))),
            negative_terminal_with_all_forecasts_positive=sum(r['preference'][-1] < 0 and all(x > 0 for x in r['predictions'].values()) for r in selected),
            exploratory_correlations=dict(
                U0_U1=correlation(d[:, 0], d[:, 1]),
                terminal_U0=correlation(p[:, -1], d[:, 0]),
                terminal_U1=correlation(p[:, -1], d[:, 1]),
                terminal_C1=correlation(p[:, -1], d[:, 2]),
                terminal_initial_shape=correlation(p[:, -1], own[:, 0]),
                terminal_matched_challenge_effect=correlation(p[:, -1], d[:, 2]-d[:, 1])),
            mean_squared_error={k: v/64 for k, v in group_error.items()},
            share_of_all_squared_error={k: v/sum(r['squared_error'][k] for r in rows) for k, v in group_error.items()},
            negative_terminal_share_of_group_passive_squared_error=float(sum(r['squared_error']['passive'] for r in selected if r['preference'][-1] < 0) / group_error['passive']),
            block_descriptions=block_rows,
            first_negative_terminal_example=next((r for r in selected if r['preference'][-1] < 0), None))
    pairs = {}
    for role in (0, 1):
        ordinary = [r for r in rows if (r['family'], r['writer']) == (role, 'translated')]
        aligned = [r for r in rows if (r['family'], r['writer']) == (role, 'aligned')]
        for a, b in zip(ordinary, aligned):
            assert (a['block'], a['life']) == (b['block'], b['life'])
            assert a['records'][0] == b['records'][0] and a['stages'][0] == b['stages'][0]
        pa, pb = (np.array([r['preference'] for r in group]) for group in (ordinary, aligned))
        pairs['AB'[role]] = dict(
            mean_aligned_minus_ordinary=(pb-pa).mean(axis=0).tolist(),
            ordinary_only_negative=((pa < 0) & (pb >= 0)).sum(axis=0).tolist(),
            aligned_only_negative=((pb < 0) & (pa >= 0)).sum(axis=0).tolist(),
            both_negative=((pa < 0) & (pb < 0)).sum(axis=0).tolist())
    # Every normalized shape calculation checks direct versus FFT maxima.
    def errors(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'direct_fft_max_error':
                    yield value
                else:
                    yield from errors(value)
        elif isinstance(node, list):
            for value in node:
                yield from errors(value)
    counts = [r['changed_sites'] for r in rows]
    return dict(schema='d141_saved_trajectory_review_v1', status='EXPLORATORY_SAVED_STATE_REVIEW',
        cases=256, independent_blocks=16, lives_per_block=4, new_dynamics=0, refitted_models=0,
        primary_result_unchanged=saved_summary['primary'],
        groups=groups, matched_writer_pairs=pairs,
        changed_sites=dict(min=min(counts), median=float(np.median(counts)), max=max(counts)),
        checks=dict(source_output_hashes=102, body_preferences_reconstructed=1024,
            diagnostic_preferences_reconstructed=768, forecast_features_matched=256,
            phase_telescope_rows=768, max_direct_fft_error=max(errors(rows))),
        limitation='One actual future per record/condition cannot separate stable vulnerability from lineage noise; replays use the same noise.',
        no_new_confidence_intervals=True, no_subgroup_success_claim=True)


def write_new(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', action='store_true', help='save write-once external analysis artifacts')
    args = parser.parse_args()
    began = time.monotonic()
    if args.save and DESTINATION.exists():
        raise FileExistsError(f'analysis already exists; no overwrite: {DESTINATION}')
    before = verify_sources()
    rows, saved = extract()
    summary = summarize(rows, saved)
    assert verify_sources() == before
    science = [Path(__file__), Path(__file__).with_name('test_review_saved_trajectories.py'),
               Path(__file__).with_name('REVIEW_SCOPE_V1.md')]
    provenance = dict(source_complete_sha256=COMPLETE_SHA, source_output_sha256=before['output_sha256'],
        source_hash_index_sha256=before['hash_file_sha256'],
        analysis_inputs={str(p.resolve()): digest(p) for p in science},
        source_verified_before_and_after=True, numerical_workers=1,
        scientific_status='post-result exploratory description, not another prediction test')
    if args.save:
        DESTINATION.mkdir(parents=True, exist_ok=False)
        for name, data in (('provenance.json', provenance), ('cases.json', rows), ('summary.json', summary)):
            write_new(DESTINATION / name, data)
        receipt = dict(status='COMPLETE', completed_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic()-began, new_dynamics=0,
            outputs={p.name: digest(p) for p in DESTINATION.iterdir()},
            output_bytes=sum(p.stat().st_size for p in DESTINATION.iterdir()))
        write_new(DESTINATION / 'COMPLETE.json', receipt)
        print(json.dumps(dict(destination=str(DESTINATION), **receipt), indent=2))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
