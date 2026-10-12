"""Independent D085 edge coordinates, flux replay, source anchors and pooling."""

import numpy as np

from laws_confirmation import l23_contact_intervention as frozen
from laws_confirmation.io import canonical_digest

previous = frozen.checker()
KINDS = ('absolute_join_advantage', 'composition_join_advantage')


def expected_edges(phase):
    assert phase in range(4)
    edges = np.zeros((2, 16, 16), dtype=bool)
    for r in range(16):
        for c in range(16):
            edges[0, r, c] = (r-phase) % 4 == 3
            edges[1, r, c] = (c-phase) % 4 == 3
    return edges


def check_replay(raw, inst, ctx, norm, phase, removal, digest):
    cfg = ctx['config']
    assert norm in (0, 1) and phase in range(4) and removal in (.5, 1.)
    keys = {'theta', 'offsets', 'case_ids', 'birth_noise', 'max_mean_drift', 'max_clip_fraction'}
    keys |= {f's{t}_{field}' for t in cfg.times for field in ('V', 'ema', 'R')}
    assert set(raw) == keys
    ids = np.array([(p, b, r) for p in range(12) for b in range(3) for r in range(7)])
    mapping = previous.layout_check.expected_maps()[2]
    theta = previous.layout_check.remap(inst['packets'][norm, ids[:, 0], ids[:, 2]], mapping)
    offsets = np.array([inst['target_means'][p]*(0, 1, -1)[b] for p, b, _ in ids])
    for key, value in (('theta', theta), ('offsets', offsets), ('case_ids', ids)):
        np.testing.assert_array_equal(raw[key], value)
    generator = previous.layout_check.rng(ctx['index'], 'expression')
    z = .2*generator.standard_normal((cfg.draws, 16, 16))
    z -= z.mean(axis=(-2, -1), keepdims=True)
    z = previous.layout_check.remap(z, mapping)
    np.testing.assert_array_equal(raw['birth_noise'], z)
    v = z[None]+offsets[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    initial = v.mean(axis=(-2, -1))
    max_drift, max_clip = np.zeros_like(initial), np.zeros_like(initial)
    weights = 1.-removal*expected_edges(phase)
    discrepancy = 0.
    for t in range(cfg.sweeps+1):
        if t:
            drift = v-v**3+ctx['tissue'].well_asym+theta[:, None]+ctx['tissue'].coupling*previous.weighted_laplacian(v, weights)
            drift -= drift.mean(axis=(-2, -1), keepdims=True)
            noise = ctx['tissue'].sigma*np.broadcast_to(previous.layout_check.remap(
                generator.standard_normal((cfg.draws, 16, 16)), mapping), v.shape)
            noise -= noise.mean(axis=(-2, -1), keepdims=True)
            v = np.clip(v+ctx['tissue'].dt*drift+noise, -2., 2.)
            ema = (1.-ctx['ladder'].ema_rate)*ema+ctx['ladder'].ema_rate*v
            ref += ctx['bp'].rho*(v-ref)
        max_drift = np.maximum(max_drift, abs(v.mean(axis=(-2, -1))-initial))
        max_clip = np.maximum(max_clip, (abs(v) == 2.).mean(axis=(-2, -1)))
        if t in cfg.times:
            for key, value in (('V', v), ('ema', ema), ('R', ref)):
                actual = raw[f's{t}_{key}']
                assert actual.shape == (252, cfg.draws, 16, 16) and actual.dtype == np.float64
                assert np.isfinite(actual).all()
                np.testing.assert_allclose(actual, value, rtol=0, atol=1e-10)
                discrepancy = max(discrepancy, float(np.max(abs(actual-value))))
            np.testing.assert_array_equal(raw[f's{t}_V'] > 0, v > 0)
    np.testing.assert_allclose(raw['max_mean_drift'], max_drift, rtol=0, atol=1e-10)
    np.testing.assert_array_equal(raw['max_clip_fraction'], max_clip)
    assert digest == canonical_digest(generator.bit_generator.state)
    return discrepancy


def check_source_record(record, index, cfg):
    assert record['tissue'] == index and record['passes']
    assert canonical_digest(record['config']) == canonical_digest(cfg)
    assert record['independently_checked_panels'] == 30 and record['source_bridge_panels'] == 6
    assert [(p['geometry'], p['norm'], p['arm']) for p in record['panels']] == [
        (g, n, a) for g in range(3) for n in range(2) for a in range(5)]
    assert len({p['rng_final'] for p in record['panels']}) == 1
    for p in record['panels']:
        assert 0 <= p['replay_max_abs'] <= 1e-10 and p['source_bridge'] is (p['arm'] == 0)
        assert set(p['state_sha256']) == {f's{t}_{k}' for t in cfg['times'] for k in ('V', 'ema', 'R')}
    return True


def check_anchor(row, compact, record, saved, source_record, source_arm):
    norm = record['norm']
    assert source_arm in (1, 4)
    assert (record['phase'], record['removal']) == ((0, .5) if source_arm == 1 else (2, 1.))
    source_panel = next(p for p in source_record['panels'] if (p['geometry'], p['norm'], p['arm']) == (2, norm, source_arm))
    assert record['state_sha256'] == source_panel['state_sha256']
    assert record['rng_final'] == source_panel['rng_final']
    for key in ('values', 'active', 'metrics'):
        np.testing.assert_array_equal(row[key], saved[key][norm, source_arm])
    np.testing.assert_array_equal(compact['diagnostics'], saved['diagnostics'][norm, source_arm])
    np.testing.assert_array_equal(row['counts'], saved['counts'])
    np.testing.assert_array_equal(row['distance'], saved['distance'])
    return True


def check_block(fresh, saved, combined):
    assert set(fresh) == {'values', 'active', 'metrics', 'diagnostics', 'final_V', 'edges', 'counts', 'distance'}
    x = fresh['values']
    assert x.shape[:6] == (2, 4, 5, 12, 3, 8) and x.shape[7:] == (2, 3, 4)
    draws = x.shape[6]
    assert fresh['active'].shape == x.shape[:-2]+(2,)
    assert fresh['metrics'].shape == (2, 4, 12, 3, 8, draws, 6)
    assert fresh['final_V'].shape == (2, 4, 252, draws, 16, 16)
    assert fresh['diagnostics'].shape == (2, 4, 252, draws, 2)
    assert all(np.isfinite(v).all() for v in fresh.values())
    for p in range(4):
        np.testing.assert_array_equal(fresh['edges'][p], expected_edges(p))
    _, _, distance, _, counts = previous.seam_check.geometry(np.zeros((4, 16, 16)), 2)
    np.testing.assert_array_equal(fresh['counts'], counts[:, :3])
    np.testing.assert_array_equal(fresh['distance'], distance)
    for key in ('values', 'active', 'metrics', 'diagnostics'):
        expected = np.stack((saved[key][:, 0], saved[key][:, 1], fresh[key][:, 0],
            saved[key][:, 2], fresh[key][:, 1], saved[key][:, 3], fresh[key][:, 2],
            saved[key][:, 4], fresh[key][:, 3]), axis=1)
        np.testing.assert_array_equal(combined[key], expected)
    v, m, a = combined['values'], combined['metrics'], combined['active']
    for arm in range(1, 9):
        np.testing.assert_array_equal(v[:, arm, 0], v[:, 0, 0])
        np.testing.assert_array_equal(a[:, arm, 0], a[:, 0, 0])
    np.testing.assert_array_equal(v[:, :, 0, :, :, 1], v[:, :, 0, :, :, 7])
    np.testing.assert_array_equal(v[0, :, :, :, :, 6], v[1, :, :, :, :, 6])
    np.testing.assert_array_equal(m[0, :, :, :, 6], m[1, :, :, :, 6])
    for pair in (0, 3):
        for budget in (1, 2):
            np.testing.assert_array_equal(v[:, :, :, pair, 0], v[:, :, :, pair, budget])
            np.testing.assert_array_equal(m[:, :, pair, 0], m[:, :, pair, budget])
    for region, reader in ((0, 2), (1, 3)):
        np.testing.assert_array_equal(v[..., 7, :, region, :, :], v[..., reader, :, region, :, :])
        np.testing.assert_array_equal(a[..., 7, :, region, :], a[..., reader, :, region, :])
    # Saved endpoints and all new fields retain paired budgets/off and birth-scale controls.
    final = fresh['final_V'].reshape(2, 4, 12, 3, 7, draws, 16, 16)
    np.testing.assert_array_equal(final[0, :, :, :, 6], final[1, :, :, :, 6])
    for pair in (0, 3):
        for budget in (1, 2):
            np.testing.assert_array_equal(final[:, :, pair, 0], final[:, :, pair, budget])
    return True


def check_summary(blocks, metrics, summary, focal):
    assert set(summary) == {'means', 'composition_block_means', 'metric_means'}
    assert len(blocks) == len(metrics)
    expected = np.zeros_like(np.take(blocks[0], 0, axis=6))
    met = np.zeros_like(np.take(metrics[0], 0, axis=5))
    cost = []
    for x, m in zip(blocks, metrics):
        delta = np.zeros(x.shape[:5]+x.shape[-2:])
        for start in range(x.shape[6]):
            expected += np.take(x, start, axis=6)/(len(blocks)*x.shape[6])
            met += np.take(m, start, axis=5)/(len(blocks)*x.shape[6])
            for half in range(2):
                delta += (x[:, :, :, :, :, 1, start, half]-x[:, :, :, :, :, 7, start, half])/(2*x.shape[6])
        cost.append(delta)
    np.testing.assert_allclose(summary['means'], expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(summary['metric_means'], met, rtol=0, atol=1e-12)
    np.testing.assert_allclose(summary['composition_block_means'], np.array(cost), rtol=0, atol=1e-12)
    assert len(focal) == 24
    for i, row in enumerate(focal):
        norm, local = divmod(i, 12)
        level, phase_kind = divmod(local, 6)
        phase_index, kind = divmod(phase_kind, 2)
        phase = phase_index+1
        join, internal = (1, 2+phase_index) if level == 0 else (5, 6+phase_index)
        draws = np.zeros((len(blocks), 12, blocks[0].shape[6]))
        for block, x in enumerate(blocks):
            for pair in range(12):
                for start in range(x.shape[6]):
                    for half in range(2):
                        v = x[norm, :, -1, pair, 1, :, start, half, 0, 0]
                        d = v[internal, 1]-v[join, 1]
                        if kind:
                            d -= v[internal, 7]-v[join, 7]
                        draws[block, pair, start] += d/2
        values = draws.mean(axis=(1, 2))
        assert row['norm'] == (.15, .30)[norm] and row['removal'] == (.5, 1.)[level]
        assert row['phase'] == phase and row['kind'] == kind and row['label'] == KINDS[kind]
        assert row['source_only'] is (phase == 2)
        for key, want in (('mean', values.mean()), ('minimum', values.min()), ('maximum', values.max()),
                          ('block_means', values), ('pair_means', draws.mean(axis=(0, 2)))):
            np.testing.assert_allclose(row[key], want, rtol=0, atol=1e-12)
        for prefix, v in (('', values), ('paired_', draws)):
            for name, selected in (('positive', v > 1e-12), ('tied', abs(v) <= 1e-12), ('negative', v < -1e-12)):
                assert row[prefix+name] == int(selected.sum())
    return True
