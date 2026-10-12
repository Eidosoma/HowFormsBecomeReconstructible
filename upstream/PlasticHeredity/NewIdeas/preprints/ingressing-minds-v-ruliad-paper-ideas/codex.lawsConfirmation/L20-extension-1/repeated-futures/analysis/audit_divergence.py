"""Independent saved-only FFT/sums-of-squares audit; no extraction imports."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np

BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
SOURCE = BASE/'outputs/l20_extension1_repeated_futures_v1_attempt1'
DEST = BASE/'analyses/d142_saved_divergence_v1'
SOURCE_COMPLETE = BASE/'runs/l20_extension1_repeated_futures_v1_attempt1/COMPLETE.json'
SOURCE_SHA = 'a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72'
GROUPS = ('A_translated', 'A_aligned', 'B_translated', 'B_aligned')
METRICS = ('read_preference', 'read_shape', 'write_preference', 'write_shape',
           'terminal_preference', 'terminal_shape', 'phase_shape', 'guide_family')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while data := f.read(1048576):
            h.update(data)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def targets(role):
    return np.array([[1. if (i < 8 if role == 0 else j % 8 < 4) else -1.
                      for j in range(16)] for i in range(16)])


def pref(v, role):
    v = np.asarray(v)
    assert v.shape[-2:] == (16, 16) and np.isfinite(v).all() and role in (0, 1)
    own = ((v > 0) == (targets(role) > 0)).astype(np.int64)
    alternative = ((v > 0) == (targets(1-role) > 0)).astype(np.int64)
    return np.where(abs(v) > .2, own-alternative, 0).sum(axis=(-2, -1))/256


def best(v, role):
    v = np.asarray(v)
    assert v.shape[-2:] == (16, 16) and np.isfinite(v).all() and role in (0, 1)
    z = v-v.mean(axis=(-2, -1), keepdims=True)
    denominator = 16*np.linalg.norm(z, axis=(-2, -1))
    correlations = np.fft.ifft2(np.fft.fft2(z)*np.conjugate(np.fft.fft2(targets(role)))).real
    return np.divide(correlations.max(axis=(-2, -1)), denominator,
                     out=np.zeros_like(denominator), where=denominator != 0)


def unpack(b):
    assert b.dtype == np.uint8 and b.shape[-1] == 2048
    # Decode each packet explicitly rather than using the producer's array view.
    return np.array([np.frombuffer(a.tobytes(), dtype='<f8').reshape(16, 16)
                     for a in b.reshape(-1, 2048)]).reshape(*b.shape[:-1], 16, 16)


def reconstruct(raw, meta):
    out = {}
    for phase in ('read', 'write', 'terminal'):
        states = raw[phase+'_states']
        pref_rows, ref_rows = [], []
        for ci in range(4):
            pref_rows.append(pref(states[:, :, ci, ..., 0, :, :], ci//2))
            ref_rows.append(best(states[:, :, ci, ..., 2, :, :], ci//2))
        out[phase+'_preference'] = np.stack(pref_rows, axis=2)
        out[phase+'_shape'] = np.stack(ref_rows, axis=2)
    traces = []
    for ci in range(4):
        traces.append(np.stack((best(unpack(raw['incoming'][:, :, ci]), ci//2),
            best(unpack(raw['routed'][:, :, ci]), ci//2), out['read_shape'][:, :, ci, :, -1],
            out['write_shape'][:, :, ci, :, -1], best(unpack(raw['outgoing'][:, :, ci]), ci//2)), axis=-1))
    out['phase_shape'] = np.stack(traces, axis=2)
    labels = np.zeros((4, 4, 4, 4), dtype=np.int64)
    for life in range(4):
        for future in range(4):
            entry = meta['lives'][life][future]
            assert entry['index'] == meta['index'] and entry['life'] == life and entry['future'] == future
            for ci, path in enumerate(entry['paths']):
                choices = [p['selector']['inferred_family'] for p in path['generations']]+[path['terminal']['selector']['inferred_family']]
                labels[life, future, ci] = [-1 if c is None else c for c in choices]
    out['guide_family'] = labels
    return out


def check_block(raw, meta, measured):
    other = reconstruct(raw, meta)
    assert set(measured) == set(METRICS)
    worst = 0.
    for k in METRICS:
        assert measured[k].shape == other[k].shape and np.isfinite(measured[k]).all()
        if k.endswith('shape'):
            err = float(np.max(abs(other[k]-measured[k])))
            assert err < 1e-12; worst = max(worst, err)
        else:
            np.testing.assert_array_equal(measured[k], other[k])
    for a, b in (('read_preference', 'values'), ('terminal_preference', 'terminal_values')):
        np.testing.assert_array_equal(other[a], raw[b][..., 0]-raw[b][..., 1])
    np.testing.assert_array_equal(raw['write_states'][..., 0, :3, :, :], raw['read_states'][..., -1, :, :, :])
    assert not raw['write_states'][..., 0, 3, :, :].any()
    for role in range(2):
        ordinary, aligned = 2*role, 2*role+1
        np.testing.assert_array_equal(raw['read_states'][:, :, ordinary, 0], raw['read_states'][:, :, aligned, 0])
        np.testing.assert_array_equal(raw['write_states'][:, :, ordinary, 0, :2], raw['write_states'][:, :, aligned, 0, :2])
        for ci in (ordinary, aligned):
            np.testing.assert_array_equal(raw['incoming'][:, :, ci, 0], raw['founder_packets'][:, :, role])
    np.testing.assert_array_equal(raw['incoming'][..., 1:, :], raw['outgoing'][..., :-1, :])
    np.testing.assert_array_equal(raw['terminal_input'], raw['outgoing'][..., -1, :])
    return dict(passes=True, body_preference_checks=1984, independent_fft_shape_checks=2560,
                max_shape_error=worst, new_dynamics=0)


def local_moments(y):
    assert y.shape[:3] == (16, 4, 4) and np.isfinite(y).all()
    mean = np.add.reduce(y, axis=2)/4
    # Pairwise differences are an independent expression of divisor-three variance.
    variance = sum((y[:, :, i]-y[:, :, j])**2 for i in range(4) for j in range(i+1, 4))/12
    return mean, variance


def profile(y, counts=False):
    means, variances = local_moments(y)
    result = dict(mean=(means.sum(axis=(0, 1))/64).tolist(),
        within_pair_variance=(variances.sum(axis=(0, 1))/64).tolist(),
        block_mean=(means.sum(axis=1)/4).tolist(), block_within_pair_variance=(variances.sum(axis=1)/4).tolist())
    if counts:
        result['negative_count'] = np.count_nonzero(y < 0, axis=(0, 1, 2)).tolist()
        result['zero_count'] = np.count_nonzero(y == 0, axis=(0, 1, 2)).tolist()
    return result


def phase_stats(y):
    before, after = y[..., :4], y[..., 1:]
    delta = after-before
    _, a = local_moments(before); _, b = local_moments(after); _, c = local_moments(delta)
    # Paired products reconstruct unbiased within-case covariance independently.
    two_cov = sum((before[:, :, i]-before[:, :, j])*(delta[:, :, i]-delta[:, :, j])
                 for i in range(4) for j in range(i+1, 4))/6
    avg = lambda v: (v.sum(axis=(0, 1))/64).tolist()
    assert np.max(abs((b-a)-(c+two_cov))) < 1e-12
    return dict(mean_change=(delta.sum(axis=(0, 1, 2))/256).tolist(),
        within_before=avg(a), within_after=avg(b), within_change=avg(b-a),
        within_increment=avg(c), twice_covariance=avg(two_cov),
        pairs_spread_decreased=(b-a < -1e-12).sum(axis=(0, 1)).tolist(),
        futures_fidelity_decreased=(delta < -1e-12).sum(axis=(0, 1, 2)).tolist())


def equal(a, b):
    if isinstance(b, dict):
        assert isinstance(a, dict) and set(a) == set(b)
        for k in b:
            equal(a[k], b[k])
    elif isinstance(b, list):
        assert isinstance(a, list) and len(a) == len(b)
        for x, y in zip(a, b):
            equal(x, y)
    elif isinstance(b, float):
        assert np.isfinite(a) and abs(a-b) < 1e-12
    else:
        assert a == b


def check_summary(data, summary, moments):
    assert set(data) == set(METRICS) and all(v.shape[:4] == (16, 4, 4, 4) for v in data.values())
    equal({k: v for k, v in summary.items() if k not in ('groups', 'matched_writers')}, dict(
        schema='d142_saved_divergence_v1', scientific_status='POST_RESULT_EXPLORATORY_DESCRIPTION',
        independent_blocks=16, cases=256, futures=1024, new_dynamics=0, refitted_models=0,
        excluded_cases=0, read_times=[0, 1, 100, 101, 300], write_times=[0, 1, 300, 1000], terminal_times=[0, 1, 100, 300],
        phases=['incoming', 'routed', 'read_end_R', 'write_end_R', 'outgoing'],
        segments=['routing', 'reading_reference', 'writing_reference', 'record_construction'],
        no_new_intervals=True, no_causal_phase_allocation=True, primary_results_unchanged=True))
    assert set(summary['groups']) == set(GROUPS)
    moment_keys = set()
    for ci, name in enumerate(GROUPS):
        panel = {k: a[:, :, :, ci] for k, a in data.items()}
        panel['reader_endpoints'] = np.stack([panel['read_preference'][..., g, -1] for g in range(3)]+
                                           [panel['terminal_preference'][..., -1]], axis=-1)
        panel['record_endpoints'] = np.stack([panel['phase_shape'][..., 0, 0]]+
                                           [panel['phase_shape'][..., g, 4] for g in range(3)], axis=-1)
        panel['read_endpoint_increments'] = panel['reader_endpoints'][..., 1:]-panel['reader_endpoints'][..., :-1]
        group = summary['groups'][name]
        assert set(group) == {'metrics', 'phase_decomposition', 'non_own_guide_counts'}
        assert set(group['metrics']) == set(panel)-{'guide_family'}
        for key, values in panel.items():
            if key == 'guide_family':
                assert group['non_own_guide_counts'] == np.count_nonzero(values != ci//2, axis=(0, 1, 2)).tolist()
                continue
            counts = 'preference' in key or key in ('reader_endpoints', 'read_endpoint_increments')
            equal(group['metrics'][key], profile(values, counts))
            for label, wanted in zip(('mean', 'variance'), local_moments(values)):
                k = f'{name}__{key}__{label}'; moment_keys.add(k)
                np.testing.assert_allclose(moments[k], wanted, atol=1e-12, rtol=0)
        phases = group['phase_decomposition']
        assert 0 <= phases['max_identity_error'] < 1e-12
        equal({k: v for k, v in phases.items() if k != 'max_identity_error'}, phase_stats(panel['phase_shape']))
    assert set(moments) == moment_keys and set(summary['matched_writers']) == {'A', 'B'}
    for role in range(2):
        expected = {}
        for key in METRICS[:-1]:
            x, y = data[key][:, :, :, 2*role], data[key][:, :, :, 2*role+1]
            expected[key] = dict(mean_aligned_minus_ordinary=((y-x).sum(axis=(0, 1, 2))/256).tolist(),
                within_variance_aligned_minus_ordinary=((local_moments(y)[1]-local_moments(x)[1]).sum(axis=(0, 1))/64).tolist())
        equal(summary['matched_writers']['AB'[role]], expected)
    return True


def verify_artifacts(destination):
    destination = Path(destination)
    receipt = read(destination/'COMPLETE.json')
    assert receipt['status'] == 'COMPLETE' and receipt['source_complete_sha256'] == SOURCE_SHA
    names = {'FREEZE.json', 'benchmark.json', 'STARTED.json', 'measurements.npz', 'pair_moments.npz', 'summary.json', 'verification.json'}
    assert set(receipt['output_sha256']) == names
    assert {p.name for p in destination.iterdir()} == names|{'COMPLETE.json'}
    for name, expected in receipt['output_sha256'].items():
        assert sha(destination/name) == expected, f'analysis output hash: {name}'
    assert receipt['output_bytes'] == sum((destination/n).stat().st_size for n in names)
    return receipt


def main():
    receipt = verify_artifacts(DEST)
    freeze = read(DEST/'FREEZE.json')
    assert sha(SOURCE_COMPLETE) == SOURCE_SHA == freeze['source']['source_complete_sha256']
    source_receipt = read(SOURCE_COMPLETE)
    assert freeze['source']['source_output_sha256'] == source_receipt['output_sha256']
    assert sha(SOURCE/'output_hashes.sha256') == source_receipt['hash_file_sha256']
    for name, wanted in source_receipt['output_sha256'].items():
        assert Path(name).parent == SOURCE and sha(name) == wanted
    source_inputs = (SOURCE/'input_hashes.sha256').read_text().splitlines()
    assert len(source_inputs) == 1265
    for line in source_inputs:
        wanted, name = line.split(maxsplit=1)
        assert sha(name.lstrip('*')) == wanted
    for name, wanted in freeze['analysis_inputs'].items():
        assert sha(name) == wanted
    assert sha(freeze['qualification_report']) == freeze['qualification_sha256']
    with np.load(DEST/'measurements.npz', allow_pickle=False) as f:
        data = {k: f[k] for k in f.files}
    with np.load(DEST/'pair_moments.npz', allow_pickle=False) as f:
        moments = {k: f[k] for k in f.files}
    proofs = []
    for bi, index in enumerate(range(90000, 90016)):
        with np.load(SOURCE/f'block_{index}.npz', allow_pickle=False) as f:
            raw = {k: f[k] for k in f.files}
        meta = read(SOURCE/f'block_{index}.json')
        assert meta['index'] == index
        proofs.append(dict(block=index, **check_block(raw, meta, {k: v[bi] for k, v in data.items()})))
    summary = read(DEST/'summary.json')
    check_summary(data, summary, moments)
    proof = read(DEST/'verification.json')
    equal(proof, dict(passes=True, blocks=proofs, new_dynamics=0, independent_statistics=True,
                      endpoints_match_D142=True, source_verified_before_after=True))
    previous = read(SOURCE/'summary.json')
    for name, g in summary['groups'].items():
        prior = previous['groups'][name]; m = g['metrics']
        equal(m['reader_endpoints']['mean'], prior['mean_preference_G1_G4'])
        equal(m['reader_endpoints']['negative_count'], prior['negative_preference_G1_G4'])
        equal(g['non_own_guide_counts'], prior['non_own_guide_G1_G4'])
        equal(m['record_endpoints']['mean'], prior['mean_record_best_F0_F3'])
        equal(m['reader_endpoints']['within_pair_variance'][-1], prior['primary']['within_future_variance']['estimate'])
    assert receipt == verify_artifacts(DEST)
    print(json.dumps(dict(passes=True, independent_blocks=16, cases=256, futures=1024,
        body_preferences=sum(p['body_preference_checks'] for p in proofs),
        independent_fft_shapes=sum(p['independent_fft_shape_checks'] for p in proofs),
        source_inputs=1265, source_outputs=36, analysis_outputs=7, new_dynamics=0,
        max_shape_error=max(p['max_shape_error'] for p in proofs), primary_results_unchanged=True), indent=2))


if __name__ == '__main__':
    main()
