"""Independent source/selection/graph/dynamics replay; no production imports."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from E015_functional_inheritance.audit import random, pair, unpack, ports
from E022_reader_compensation.audit import advance_compensated
from E054_record_interventions.plan import HISTORIES, ARMS, SOURCE_INDICES
import numpy as np

P = ports()
ENDS = [(y*16+x, y*16+(x+1)%16) for y in range(16) for x in range(16)]
ENDS += [(y*16+x, ((y+1)%16)*16+x) for y in range(16) for x in range(16)]


def equal(a, b):
    a, b = np.asarray(a), np.asarray(b)
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), (a.shape, b.shape)


def source(run, block):
    def read(name):
        with np.load(run/name, allow_pickle=False) as f: return {k:f[k] for k in f.files}
    a = read(f'source_{block:06d}.npz')['acquired'][1]
    prev = read(f'boundary_{block:06d}_g31.npz'); cur = read(f'boundary_{block:06d}_g32.npz')
    R = cur['outgoing'].shape[2]
    records = np.empty((5, 4, R, 2, 16, 16)); records[0] = unpack(a)[:, None]
    for h, n in enumerate(SOURCE_INDICES, 1): records[h] = unpack(cur['outgoing'][n])
    tags = np.zeros_like(records, bool)
    for h, n in enumerate(SOURCE_INDICES, 1):
        before = unpack(prev['outgoing'][n]).reshape(4, R, 512)
        now = records[h].reshape(4, R, 512)
        for f, r in np.ndindex(4, R):
            oldmask = prev['masks'][f, r].ravel(); mask = cur['masks'][f, r].ravel()
            for e, (u, v) in enumerate(ENDS):
                available = not (mask[u] or mask[v])
                returning = (oldmask[u] and not mask[u]) or (oldmask[v] and not mask[v])
                tags[h, f, r].ravel()[e] = available and returning and before[f, r, e] == 0 and now[f, r, e] != 0
    return dict(records=records, repair=tags)


def graph(w):
    """Build explicit forest then assign node parity; independent of signed DSU."""
    labels = list(range(256)); adjacency = [[] for _ in range(256)]; chords = []
    flat = w.ravel(); count = 0
    for e, (u, v) in enumerate(ENDS):
        if flat[e] == 0: continue
        count += 1; bit = bool(flat[e] < 0)
        if labels[u] == labels[v]: chords.append((u, v, bit))
        else:
            old, new = labels[v], labels[u]
            labels = [new if x == old else x for x in labels]
            adjacency[u].append((v, bit)); adjacency[v].append((u, bit))
    parity = {}; seen = set()
    for i in range(256):
        if i in seen: continue
        stack = [i]; parity[i] = False; seen.add(i)
        while stack:
            u = stack.pop()
            for v, bit in adjacency[u]:
                if v not in seen:
                    seen.add(v); parity[v] = parity[u] ^ bit; stack.append(v)
    neg = sum(parity[u] ^ parity[v] ^ bit for u, v, bit in chords)
    input_labels = {labels[i] for i in np.flatnonzero(P[0])}
    reach = np.array([x in input_labels for x in labels])
    return np.array((count, len(set(labels)), len(chords), neg, sum(reach),
        sum(reach[P[1].ravel()]), sum(reach[P[2].ravel()])), np.int64)


def graph_batch(w):
    return np.array([graph(x) for x in w.reshape(-1, 2, 16, 16)]).reshape(*w.shape[:-3], 7)


def interventions(saved, records, repair, block):
    out = saved['weights']; H, A, F, R = out.shape[:4]
    allport = P.any(axis=0).ravel()
    for h, f, r in np.ndindex(H, F, R):
        w = records[h, f, r].ravel(); result = out[h, :, f, r].reshape(A, 512)
        key = ('E054', block, HISTORIES[h], f//2, r)
        s = np.ones(256); s[random(*key, 'cells').choice(np.flatnonzero(~allport), 8, replace=False)] = -1
        equal(s.reshape(16, 16), saved['cell_signs'][h, f, r])
        factor = np.array([s[u]*s[v] for u, v in ENDS]); cut = (factor < 0) & (w != 0)
        order = sorted(np.flatnonzero(w), key=lambda i:(abs(w[i]), i))
        bins = np.full(512, -1, np.int16)
        for k, e in enumerate(order): bins[e] = k*8//len(order)
        equal(bins, saved['bins'][h, f, r])
        perm = np.arange(512)
        for sign in (-1, 1):
            ids = np.flatnonzero(np.sign(w) == sign)
            perm[ids] = random(*key, 'magnitudes', sign).permutation(ids)
        equal(perm, saved['permutations'][h, f, r])
        iso = np.zeros(512, bool); candidate = []; other_pools = []
        for b in range(8):
            ids = np.flatnonzero(bins == b); count = int(sum(cut[ids]))
            iso[random(*key, 'isolated', b).choice(ids, count, replace=False)] = True
            tagged = repair[h, f, r].ravel()[ids]
            yes, no = ids[tagged], ids[~tagged]
            candidate += random(*key, 'repair_candidates', b).permutation(yes)[:min(len(yes), len(no))].tolist()
            other_pools.append(no)
        selected = random(*key, 'repair_subset').permutation(candidate)[:int(sum(cut))].astype(int)
        target = np.zeros(512, bool); target[selected] = True; other = np.zeros(512, bool)
        for b in range(8):
            k = int(sum(bins[selected] == b))
            other[random(*key, 'other', b).choice(other_pools[b], k, replace=False)] = True
        for name, value in (('isolated', iso), ('delete_returning', target), ('delete_other', other)):
            equal(value, saved[name][h, f, r])
        expected = np.repeat(w[None], A, axis=0)
        expected[1] = w*.5; expected[2] = np.sign(w)*abs(w[perm])
        expected[3] = np.sign(w)*(abs(w[w != 0]).mean() if (w != 0).any() else 0.)
        expected[4] = w*factor; expected[5, iso] *= -1
        expected[6, iso] = 0.; expected[8, target] = 0.; expected[9, other] = 0.; expected[10] = 0.
        equal(expected, result)
        assert np.array_equal(result[1] != 0, w != 0)
        for a in (2, 3, 4, 5): assert np.array_equal(result[a] != 0, w != 0)
        for a in (4, 5): equal(abs(result[a]), abs(w))
        expected_noise = np.ones((A, 16, 16)); expected_noise[4] = s.reshape(16, 16)
        equal(expected_noise, saved['noise_signs'][h, :, f, r])
        for a in range(A):
            changed = result[a] != w
            incident = np.array([allport[u] or allport[v] for u, v in ENDS])
            x = np.array([sum(changed), sum(abs(w)*changed), sum(changed & incident),
                          repair[h, f, r].sum(), sum(target)], float)
            np.testing.assert_allclose(x, saved['exposure'][h, a, f, r], rtol=1e-14, atol=1e-14)
    equal(graph_batch(out), saved['graph_before'])


def masks(block, R):
    eligible = np.flatnonzero(~P.any(axis=0).ravel()); squares = []
    for y, x in np.ndindex(16, 16):
        a = np.zeros((16, 16), bool)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1): a[(y+dy)%16, (x+dx)%16] = True
        if not (a & P.any(axis=0)).any(): squares.append(a)
    stream = random('E015', block, 'E054_fresh_reader', 'damage')
    out = np.zeros((2, R, 3, 16, 16), bool)
    for f, r in np.ndindex(2, R):
        out[f, r, 1].ravel()[stream.choice(eligible, 24, replace=False)] = True
        out[f, r, 2] = squares[int(stream.integers(len(squares)))]
    return pair(out)


def coupling(w):
    d = np.empty(w.shape[:-3]+(16, 16)); k = np.zeros(w.shape[:-3]+(4, 16, 16))
    for y, x in np.ndindex(16, 16):
        values = (w[..., 0, y, x], w[..., 0, y, (x-1)%16],
                  w[..., 1, y, x], w[..., 1, (y-1)%16, x])
        total = abs(values[0])+abs(values[1])+abs(values[2])+abs(values[3]); d[..., y, x] = total
        for i, a in enumerate(values): np.divide(a, total, out=k[..., i, y, x], where=total > 0)
    return d, k


def replay(inter, block, cfg):
    H, A, F, R = inter['weights'].shape[:4]; N = H*A
    mask = masks(block, R); w = inter['weights'].reshape(N, F, R, 2, 16, 16)
    effective = np.empty((N, F, R, 3, 2, 16, 16))
    for e, (u, v) in enumerate(ENDS):
        alive = (~mask.reshape(F, R, 3, 256)[..., u]) & (~mask.reshape(F, R, 3, 256)[..., v])
        effective.reshape(N, F, R, 3, 512)[..., e] = w.reshape(N, F, R, 512)[..., e, None]*alive
    d, k = coupling(effective); s = inter['noise_signs'].reshape(N, F, R, 1, 1, 16, 16)
    stream = random('E054', block, 'fresh_reader')
    birth = cfg['birth_sd']*pair(stream.standard_normal((2, R, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (N, F, R, 2, 3, 16, 16)).copy()*s
    live = (~mask)[None, :, :, None]; cue = np.array([1., -1.]).reshape(1, 1, 1, 2, 1, 1)
    v *= live; v[..., P[0]] = cue; trace = []
    for t in range(cfg['read_steps']):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]*s
        v = advance_compensated(v, effective[:, :, :, None], d[:, :, :, None], noise, cfg,
                                t >= cfg['settling_steps'])
        v *= live; v[..., P[0]] = cue
        if t >= cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[..., P[1]].mean(axis=-1), v[..., P[2]].mean(axis=-1)), axis=-1))
    trace = np.array(trace)
    return dict(masks=mask, effective=effective, denominator=d, coupling=k, birth=birth,
                end=v, late_ports=trace, mean_ports=trace.mean(axis=0), graph_after=graph_batch(effective))


def scores(raw):
    v = raw['mean_ports'].reshape(5, 11, *raw['mean_ports'].shape[1:])
    margin = np.empty(v.shape[:-1]); transfer = np.empty(v.shape[:4]+(3,))
    for f, rule in enumerate((1., -1., 1., -1.)):
        for c, cue in enumerate((1., -1.)):
            y = v[:, :, f, :, c]
            margin[:, :, f, :, c] = np.minimum(rule*cue*y[..., 0], -rule*cue*y[..., 1])
        y = v[:, :, f]
        transfer[:, :, f] = ((y[:, :, :, 0, :, 0]-y[:, :, :, 1, :, 0])-
                              (y[:, :, :, 0, :, 1]-y[:, :, :, 1, :, 1]))/4
    return dict(margin=margin, both=(margin > .25).all(axis=4), transfer=transfer,
                aligned_transfer=transfer*np.array([1., -1., 1., -1.])[None, None, :, None, None])
