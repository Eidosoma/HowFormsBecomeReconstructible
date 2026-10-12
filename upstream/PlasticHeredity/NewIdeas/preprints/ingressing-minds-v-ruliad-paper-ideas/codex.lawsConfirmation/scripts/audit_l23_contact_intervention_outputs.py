"""Independent D084 weighted-graph dynamics, source bridge and pooling checks."""

import json

import numpy as np

from laws_confirmation import l23_seam_localization as previous
from laws_confirmation.io import canonical_digest

seam_check = previous.checker()
layout_check = previous.source.checker()
KINDS = ('normalized_rescue', 'composition_rescue', 'contact_specificity',
         'record_specificity_off', 'record_specificity_scrambled')


def selected_edges(g, internal):
    # Independent coordinate construction: no production edge masks or shifts.
    edges = np.zeros((2, 16, 16), dtype=bool)
    for r in range(16):
        for c in range(16):
            if g == 0:
                edges[1, r, c] = c % 8 == (3 if internal else 7)
            elif g == 1:
                edges[0, r, c] = r % 8 == (3 if internal else 7)
            elif g == 2:
                edges[0, r, c] = r % 4 == (1 if internal else 3)
                edges[1, r, c] = c % 4 == (1 if internal else 3)
            else:
                raise ValueError('unknown geometry')
    return edges


def weighted_laplacian(v, weights):
    # Direct conservative edge flux, not the production full-lattice-minus-lesion expression.
    fluxes = []
    for a in (0, 1):
        outgoing = weights[a]*(np.roll(v, -1, a-2)-v)
        fluxes.append(outgoing-np.roll(outgoing, 1, a-2))
    return (fluxes[0]+fluxes[1])*.25


def check_replay(raw, inst, ctx, g, n, arm, digest):
    cfg = ctx['config']
    assert arm in range(5)
    expected_keys = {'theta', 'offsets', 'case_ids', 'birth_noise', 'max_mean_drift', 'max_clip_fraction'}
    expected_keys |= {f's{t}_{field}' for t in cfg.times for field in ('V', 'ema', 'R')}
    assert set(raw) == expected_keys
    ids = np.array([(p, b, r) for p in range(12) for b in range(3) for r in range(7)])
    mapping = layout_check.expected_maps()[g]
    theta = layout_check.remap(inst['packets'][n, ids[:, 0], ids[:, 2]], mapping)
    offsets = np.array([inst['target_means'][p]*[0, 1, -1][b] for p, b, _ in ids])
    for key, value in (('theta', theta), ('offsets', offsets), ('case_ids', ids)):
        np.testing.assert_array_equal(raw[key], value)
    generator = layout_check.rng(ctx['index'], 'expression')
    z = .2*generator.standard_normal((cfg.draws, 16, 16))
    z -= z.mean(axis=(-2, -1), keepdims=True)
    z = layout_check.remap(z, mapping)
    np.testing.assert_array_equal(raw['birth_noise'], z)
    v = z[None]+offsets[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    start = v.mean(axis=(-2, -1))
    max_drift, max_clip = np.zeros_like(start), np.zeros_like(start)
    weights = np.ones((2, 16, 16))
    weights[selected_edges(g, arm in (2, 4))] -= (0., .5, .5, 1., 1.)[arm]
    maximum = 0.
    for t in range(cfg.sweeps+1):
        if t:
            drift = v-v**3+ctx['tissue'].well_asym+theta[:, None]+ctx['tissue'].coupling*weighted_laplacian(v, weights)
            drift -= drift.mean(axis=(-2, -1), keepdims=True)
            noise = ctx['tissue'].sigma*np.broadcast_to(
                layout_check.remap(generator.standard_normal((cfg.draws, 16, 16)), mapping), v.shape)
            noise -= noise.mean(axis=(-2, -1), keepdims=True)
            v = np.clip(v+ctx['tissue'].dt*drift+noise, -2., 2.)
            ema = (1.-ctx['ladder'].ema_rate)*ema+ctx['ladder'].ema_rate*v
            ref = ref+ctx['bp'].rho*(v-ref)
        max_drift = np.maximum(max_drift, abs(v.mean(axis=(-2, -1))-start))
        max_clip = np.maximum(max_clip, (abs(v) == 2.).mean(axis=(-2, -1)))
        if t in cfg.times:
            for key, value in (('V', v), ('ema', ema), ('R', ref)):
                actual = raw[f's{t}_{key}']
                assert actual.shape == (252, cfg.draws, 16, 16) and actual.dtype == np.float64
                assert np.isfinite(actual).all()
                np.testing.assert_allclose(actual, value, rtol=0, atol=1e-10)
                maximum = max(maximum, float(np.max(abs(actual-value))))
            # Labels must agree exactly even though independent arithmetic need not.
            np.testing.assert_array_equal(raw[f's{t}_V'] > 0, v > 0)
    np.testing.assert_allclose(raw['max_mean_drift'], max_drift, rtol=0, atol=1e-10)
    np.testing.assert_array_equal(raw['max_clip_fraction'], max_clip)
    assert digest == canonical_digest(generator.bit_generator.state)
    return maximum


def check_metrics(v, canonical_forms, g, metrics):
    forms, labels, *_ = seam_check.geometry(canonical_forms, g)
    scores, probabilities = layout_check.scores_of(v, forms, labels)
    alignment = layout_check.alignment_of(v, forms, labels)
    s = scores.reshape(12, 3, 7, v.shape[1], 2, 4)
    p = probabilities.reshape(s.shape)
    a = alignment.reshape(s.shape)
    expected = np.empty((12, 3, 8, v.shape[1], 6))
    for j, pair in enumerate(layout_check.PAIRS):
        for b in range(3):
            for reader in range(8):
                ss = s[j, b, reader] if reader < 7 else np.stack((s[j, b, 2, :, 0], s[j, b, 3, :, 1]), axis=1)
                pp = p[j, b, reader] if reader < 7 else np.stack((p[j, b, 2, :, 0], p[j, b, 3, :, 1]), axis=1)
                aa = a[j, b, reader] if reader < 7 else np.stack((a[j, b, 2, :, 0], a[j, b, 3, :, 1]), axis=1)
                expected[j, b, reader] = layout_check.paired_metrics(ss, pp, aa, pair)
    np.testing.assert_allclose(metrics, expected, rtol=0, atol=1e-12)
    return True


def check_source_bridge(raw, observed, root, index, g, n):
    directory = root/'outputs'/previous.source.RUN_ID/f'tissue_{index}'
    with np.load(directory/f'panel_{g}_{n}.npz', allow_pickle=False) as saved:
        keys = ('theta', 'case_ids', 'offsets', 'birth_noise')
        keys += tuple(f's{t}_{field}' for t in previous.TIMES for field in ('V', 'ema', 'R'))
        for key in keys:
            np.testing.assert_array_equal(raw[key], saved[key])
        mean = saved['mean']
        np.testing.assert_array_equal(raw['max_mean_drift'], abs(mean-mean[0]).max(axis=0))
        np.testing.assert_array_equal(raw['max_clip_fraction'], saved['boundary_fraction'].max(axis=0))
    with np.load(root/'outputs'/previous.RUN_ID/f'tissue_{index}.npz', allow_pickle=False) as saved:
        np.testing.assert_array_equal(observed['values'], saved['values'][g, n, ..., :3, :])
        np.testing.assert_array_equal(observed['active'], saved['active'][g, n])
    previous_metrics = json.loads((directory/'panel.json').read_text())['metrics']
    np.testing.assert_array_equal(observed['metrics'], np.array(previous_metrics)[g, n])
    return True


def check_block(payload):
    values, active, metrics = (payload[k] for k in ('values', 'active', 'metrics'))
    assert values.shape[:7] == (3, 2, 5, 5, 12, 3, 8)
    assert active.shape == values.shape[:-2]+(2,)
    assert metrics.shape == values.shape[:3]+values.shape[4:8]+(6,)
    assert payload['final_V'].shape == (3, 2, 4, 252, values.shape[7], 16, 16)
    assert payload['diagnostics'].shape == (3, 2, 5, 252, values.shape[7], 2)
    assert all(np.isfinite(x).all() for x in payload.values())
    for g in range(3):
        for k in range(2):
            np.testing.assert_array_equal(payload['edges'][g, k], selected_edges(g, bool(k)))
        _, _, distance, _, counts = seam_check.geometry(np.zeros((4, 16, 16)), g)
        np.testing.assert_array_equal(payload['counts'][g], counts[:, :3])
        np.testing.assert_array_equal(payload['distance'][g], distance)
    # Birth identical across all interventions, instructions and virtual isolation.
    for arm in range(1, 5):
        np.testing.assert_array_equal(values[:, :, arm, 0], values[:, :, 0, 0])
    np.testing.assert_array_equal(values[:, :, :, 0, :, :, 1], values[:, :, :, 0, :, :, 7])
    np.testing.assert_array_equal(values[:, 0, :, :, :, :, 6], values[:, 1, :, :, :, :, 6])
    np.testing.assert_array_equal(metrics[:, 0, :, :, :, 6], metrics[:, 1, :, :, :, 6])
    for p in (0, 3):
        for b in (1, 2):
            np.testing.assert_array_equal(values[:, :, :, :, p, 0], values[:, :, :, :, p, b])
            np.testing.assert_array_equal(metrics[:, :, :, p, 0], metrics[:, :, :, p, b])
    # Original full-sheet standardization and virtual donor selection remain unchanged.
    for h, reader in ((0, 2), (1, 3)):
        np.testing.assert_array_equal(values[..., 7, :, h, :, :], values[..., reader, :, h, :, :])
    np.testing.assert_array_equal(values[0, ..., 3], values[1, ..., 3])
    np.testing.assert_array_equal(active[0], active[1])
    np.testing.assert_array_equal(metrics[0, ..., :5], metrics[1, ..., :5])
    maximum = float(np.max(abs(values[0]-values[1])))
    assert maximum <= 1e-10
    np.testing.assert_allclose(metrics[0], metrics[1], rtol=0, atol=1e-10)
    rotation = np.rot90(payload['final_V'][0], -1, axes=(-2, -1))
    np.testing.assert_allclose(rotation, payload['final_V'][1], rtol=0, atol=1e-10)
    np.testing.assert_array_equal(rotation > 0, payload['final_V'][1] > 0)
    np.testing.assert_allclose(payload['diagnostics'][0], payload['diagnostics'][1], rtol=0, atol=1e-10)
    return max(maximum, float(np.max(abs(rotation-payload['final_V'][1]))))


def check_summary(blocks, metrics, summary, focal):
    assert set(summary) == {'means', 'composition_block_means', 'metric_means'}
    expected = np.zeros_like(np.take(blocks[0], 0, axis=7))
    met = np.zeros_like(np.take(metrics[0], 0, axis=6))
    excess = []
    for x, m in zip(blocks, metrics):
        delta = np.zeros(x.shape[:6]+x.shape[-2:])
        for start in range(x.shape[7]):
            expected += np.take(x, start, axis=7)/(len(blocks)*x.shape[7])
            met += np.take(m, start, axis=6)/(len(blocks)*x.shape[7])
            for region in range(2):
                delta += (x[..., 1, start, region, :, :]-x[..., 7, start, region, :, :])/(2*x.shape[7])
        excess.append(delta)
    np.testing.assert_allclose(summary['means'], expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(summary['metric_means'], met, rtol=0, atol=1e-12)
    np.testing.assert_allclose(summary['composition_block_means'], np.array(excess), rtol=0, atol=1e-12)
    assert len(focal) == 20
    for i, row in enumerate(focal):
        n, rem_kind = divmod(i, 10)
        level, kind = divmod(rem_kind, 5)
        join, internal = (1, 2) if level == 0 else (3, 4)
        all_draws = np.empty((len(blocks), 12, blocks[0].shape[7]))
        for j, x in enumerate(blocks):
            for p in range(12):
                # Keep start and region explicitly to avoid a plausible pooled-axis alias.
                e = x[2, n, :, -1, p, 1, :, :, :, 0, 0]
                for start in range(x.shape[7]):
                    v = e[:, :, start].sum(axis=-1)/2
                    gain = v[0, 1]-v[join, 1]
                    cost0, costj, costi = (v[a, 1]-v[a, 7] for a in (0, join, internal))
                    wanted = (gain, cost0-costj, costi-costj,
                              gain-v[0, 6]+v[join, 6], gain-v[0, 4]+v[join, 4])
                    all_draws[j, p, start] = wanted[kind]
        means = all_draws.mean(axis=(1, 2))
        assert row['norm'] == (.15, .30)[n] and row['removal'] == (.5, 1.)[level]
        assert row['kind'] == kind and row['label'] == KINDS[kind]
        for key, want in (('mean', means.mean()), ('minimum', means.min()), ('maximum', means.max()),
                          ('block_means', means), ('pair_means', all_draws.mean(axis=(0, 2)))):
            np.testing.assert_allclose(row[key], want, rtol=0, atol=1e-12)
        for prefix, v in (('', means), ('paired_', all_draws)):
            for label, mask in (('positive', v > 1e-12), ('tied', abs(v) <= 1e-12), ('negative', v < -1e-12)):
                assert row[prefix+label] == int(mask.sum())
    return True
