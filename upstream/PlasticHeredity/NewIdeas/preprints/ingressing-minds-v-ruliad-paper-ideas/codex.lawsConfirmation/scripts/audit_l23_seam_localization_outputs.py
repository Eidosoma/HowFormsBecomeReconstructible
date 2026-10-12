"""Independent saved-field D083 geometry, error and aggregation checks."""

from collections import deque

import numpy as np

PAIRS = ('AB', 'AC', 'AD', 'BA', 'BC', 'BD', 'CA', 'CB', 'CD', 'DA', 'DB', 'DC')


def geometry(canonical_forms, g):
    forms = np.empty_like(canonical_forms)
    labels = np.zeros((16, 16), dtype=bool)
    distance = np.empty((16, 16), dtype=np.int64)
    for r in range(16):
        for c in range(16):
            if g == 0:
                sr, sc = r, c
                d = min(c % 8, 7-c % 8)
            elif g == 1:
                sr, sc = 15-c, r
                d = min(r % 8, 7-r % 8)
            elif g == 2:
                sr, sc = r, 4*(2*((r//4+c//4) % 2)+(c//4)//2)+c % 4
                d = min(r % 4, 3-r % 4, c % 4, 3-c % 4)
            else:
                raise ValueError('unknown layout')
            forms[:, r, c] = canonical_forms[:, sr, sc]
            labels[r, c] = sc < 8
            distance[r, c] = d
    # An independent graph traversal checks even the closed-form distances.
    found = np.full((16, 16), -1, dtype=int)
    queue = deque()
    for r in range(16):
        for c in range(16):
            if any(labels[r, c] != labels[rr % 16, cc % 16]
                   for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1))):
                found[r, c] = 0
                queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
            rr, cc = rr % 16, cc % 16
            if labels[rr, cc] == labels[r, c] and found[rr, cc] < 0:
                found[rr, cc] = found[r, c]+1
                queue.append((rr, cc))
    np.testing.assert_array_equal(distance, found)
    bands = np.stack((np.ones((16, 16), bool), distance == 0, distance > 0,
                     *(distance == k for k in range(4))))
    counts = np.array([[np.count_nonzero(b & region) for b in bands]
                       for region in (labels, ~labels)])
    return forms, labels, distance, bands, counts


def recompute(v, canonical_forms, g):
    assert v.ndim == 6 and v.shape[:3] == (12, 3, 7) and v.shape[-2:] == (16, 16)
    forms, labels, distance, bands, counts = geometry(canonical_forms, g)
    shape = (12, 3, 8, v.shape[3], 2)
    result = np.zeros((*shape, 7, 4))
    active = np.zeros((*shape, 2), dtype=np.uint8)
    for p, pair in enumerate(PAIRS):
        for h, region in enumerate((labels, ~labels)):
            indices = np.flatnonzero(region.ravel())
            x = v[p].reshape(3, 7, v.shape[3], 256)[..., indices]
            f = forms[ord(pair[h])-65].ravel()[indices]
            cx, cf = x-x.sum(axis=-1, keepdims=True)/128, f-f.sum()/128
            sx = np.sqrt(np.square(cx).sum(axis=-1)/128)
            sf = np.sqrt(np.square(cf).sum()/128)
            zx = np.divide(cx, sx[..., None], out=np.zeros_like(cx), where=sx[..., None] > 0)
            zf = cf/sf if sf > 0 else np.zeros_like(cf)
            fields = (.5*np.square(zx-zf), 1-zx*zf, np.square(x-f), (x > 0) != (f > 0))
            active[p, :, :7, :, h, 0] = sx > 0
            active[p, :, :7, :, h, 1] = sf > 0
            for b, band in enumerate(bands):
                take = band.ravel()[indices]
                if take.any():
                    for m, values in enumerate(fields):
                        result[p, :, :7, :, h, b, m] = values[..., take].sum(axis=-1)/take.sum()
    for h, reader in ((0, 2), (1, 3)):
        result[:, :, 7, :, h] = result[:, :, reader, :, h]
        active[:, :, 7, :, h] = active[:, :, reader, :, h]
    return dict(values=result, active=active, distance=distance, counts=counts)


def check_snapshot(v, canonical_forms, g, saved):
    expected = recompute(v, canonical_forms, g)
    assert set(saved) == set(expected)
    for key in ('active', 'distance', 'counts'):
        np.testing.assert_array_equal(saved[key], expected[key])
    np.testing.assert_allclose(saved['values'], expected['values'], rtol=0, atol=1e-12)
    value, active, counts = saved['values'], saved['active'], saved['counts']
    assert np.isfinite(value).all()
    assert (value[..., [0, 2, 3]] >= 0).all()
    # Whole = area-weighted seam/interior; never average empty shells as data.
    weighted = (value[..., 1, :]*counts[:, 1, None]+value[..., 2, :]*counts[:, 2, None])/128
    np.testing.assert_allclose(value[..., 0, :], weighted, rtol=0, atol=1e-12)
    shells = (value[..., 3:, :]*counts[:, 3:, None]).sum(axis=-2)/128
    np.testing.assert_allclose(value[..., 0, :], shells, rtol=0, atol=1e-12)
    np.testing.assert_allclose(value[..., 0, 0], value[..., 0, 1]-1+.5*active.sum(axis=-1), rtol=0, atol=1e-12)
    return True


def check_endpoint(values, old_metrics):
    # values pair,budget,reader,start,half,band,metric; old pair,budget,reader,start,metric.
    for new, old in ((1, 5), (3, 2)):
        np.testing.assert_allclose(values[..., 0, new].mean(axis=-1), 1-old_metrics[..., old], rtol=0, atol=1e-12)
    return True


def check_block(values, active, counts):
    assert values.shape[:4] == (3, 2, 5, 12)
    # Identical birth actions/states and target observers make composition excess zero.
    np.testing.assert_array_equal(values[:, :, 0, :, :, 1], values[:, :, 0, :, :, 7])
    np.testing.assert_array_equal(values[:, 0, :, :, :, 6], values[:, 1, :, :, :, 6])
    for p in (0, 3):
        np.testing.assert_array_equal(values[:, :, :, p, 0], values[:, :, :, p, 1])
        np.testing.assert_array_equal(values[:, :, :, p, 0], values[:, :, :, p, 2])
    np.testing.assert_array_equal(active[0], active[1])
    np.testing.assert_array_equal(counts[0], counts[1])
    np.testing.assert_array_equal(values[0, ..., 3], values[1, ..., 3])
    delta = float(np.max(np.abs(values[0]-values[1])))
    assert delta <= 1e-10
    return delta


def check_summary(blocks, summary, focal):
    # Explicit summation avoids calling the production pooling code.
    expected = np.zeros_like(np.take(blocks[0], 0, axis=6))
    for x in blocks:
        for start in range(x.shape[6]):
            expected += np.take(x, start, axis=6)/(len(blocks)*x.shape[6])
    np.testing.assert_allclose(summary['means'], expected, rtol=0, atol=1e-12)
    excess = []
    for x in blocks:
        difference = np.zeros(x.shape[:5]+x.shape[-2:])
        for start in range(x.shape[6]):
            for half in range(2):
                difference += (x[:, :, :, :, :, 1, start, half]
                               -x[:, :, :, :, :, 7, start, half])/(2*x.shape[6])
        excess.append(difference)
    excess = np.array(excess)
    np.testing.assert_allclose(summary['composition_block_means'], excess, rtol=0, atol=1e-12)
    assert len(focal) == 8
    for i, row in enumerate(focal):
        n, kind = divmod(i, 4)
        all_draws = []
        for x in blocks:
            # layout,pair,start,half,band after fixed norm/time/budget/observer.
            y = x[:, n, 4, :, 1, 1, :, :, :, 0]-x[:, n, 4, :, 1, 7, :, :, :, 0]
            y = y.mean(axis=3)
            target = y[2]-y[0] if kind >= 2 else y[2]
            all_draws.append(target[..., 1]-target[..., 2] if kind % 2 else target[..., 0])
        all_draws = np.array(all_draws)
        means = all_draws.mean(axis=(1, 2))
        assert row['norm'] == (.15, .30)[n] and row['kind'] == kind
        assert row['label'] == ('checker_whole_excess', 'checker_seam_minus_interior',
                               'layout_change_whole_excess', 'layout_change_seam_minus_interior')[kind]
        for key, want in [('mean', means.mean()), ('minimum', means.min()), ('maximum', means.max())]:
            np.testing.assert_allclose(row[key], want, rtol=0, atol=1e-12)
        np.testing.assert_allclose(row['block_means'], means, rtol=0, atol=1e-12)
        np.testing.assert_allclose(row['pair_means'], all_draws.mean(axis=(0, 2)), rtol=0, atol=1e-12)
        for prefix, data in [('', means), ('paired_', all_draws)]:
            for label, test in [('positive', data > 1e-12), ('tied', abs(data) <= 1e-12), ('negative', data < -1e-12)]:
                assert row[prefix+label] == int(test.sum())
    return True
