"""Record interventions and one fixed-record, common normalized reader."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
from E022_reader_compensation import model as reader
from E054_record_interventions.plan import (ARMS, HISTORIES, SELECTED_CELLS, BINS,
                                            GRAPH_FIELDS, EXPOSURE_FIELDS)
import numpy as np

base = reader.base
P = base.PORTS
U = np.tile(np.arange(256), 2)
V = np.concatenate((np.roll(np.arange(256).reshape(16, 16), -1, 1).ravel(),
                    np.roll(np.arange(256).reshape(16, 16), -1, 0).ravel()))


def graph(w):
    """Ordered-edge spanning forest; signed union-find counts chord parity."""
    parent = np.arange(256); parity = np.zeros(256, bool)
    def root(x):
        bit = False
        while parent[x] != x:
            bit ^= bool(parity[x]); x = parent[x]
        return x, bit
    occupied = np.flatnonzero(w.ravel() != 0); neg = 0; rank = 0
    for e in occupied:
        a, sa = root(int(U[e])); b, sb = root(int(V[e])); flip = w.ravel()[e] < 0
        if a == b:
            rank += 1; neg += bool(sa ^ sb ^ flip)
        else:
            parent[b] = a; parity[b] = sa ^ sb ^ flip
    roots = np.array([root(i)[0] for i in range(256)])
    reach = np.isin(roots, roots[P[0].ravel()])
    return np.array((len(occupied), len(set(roots)), rank, neg, reach.sum(),
                     (reach & P[1].ravel()).sum(), (reach & P[2].ravel()).sum()), np.int64)


def graph_batch(w):
    return np.stack([graph(x) for x in w.reshape(-1, 2, 16, 16)]).reshape(*w.shape[:-3], len(GRAPH_FIELDS))


def strata(w):
    ids = np.flatnonzero(w.ravel() != 0)
    order = ids[np.argsort(abs(w.ravel()[ids]), kind='stable')]
    bins = np.full(512, -1, np.int16)
    if len(order): bins[order] = np.arange(len(order))*BINS//len(order)
    return bins


def intervene(records, repair, block):
    H, F, R = records.shape[:3]
    assert (H, F) == (5, 4) and records.shape[-3:] == (2, 16, 16)
    out = np.repeat(records[:, None], len(ARMS), axis=1)
    signs = np.ones((H, F, R, 16, 16))
    iso = np.zeros((H, F, R, 512), bool); target = iso.copy(); other = iso.copy()
    permutations = np.broadcast_to(np.arange(512), (H, F, R, 512)).copy()
    bins = np.empty((H, F, R, 512), np.int16)
    eligible_cells = np.flatnonzero(~P.any(axis=0).ravel())
    for h, f, r in np.ndindex(H, F, R):
        w = records[h, f, r].ravel(); bin_id = strata(records[h, f, r]); bins[h, f, r] = bin_id
        key = ('E054', block, HISTORIES[h], f//2, r)
        picked = rng(*key, 'cells').choice(eligible_cells, SELECTED_CELLS, replace=False)
        s = signs[h, f, r].ravel(); s[picked] = -1
        cut = (s[U]*s[V] == -1) & (w != 0)
        out[h, 1, f, r] *= .5
        for sign in (-1, 1):
            ids = np.flatnonzero(np.sign(w) == sign)
            permutations[h, f, r, ids] = rng(*key, 'magnitudes', sign).permutation(ids)
        out[h, 2, f, r] = (np.sign(w)*abs(w[permutations[h, f, r]])).reshape(2, 16, 16)
        occupied = w != 0
        mean = abs(w[occupied]).mean() if occupied.any() else 0.
        out[h, 3, f, r] = (np.sign(w)*mean).reshape(2, 16, 16)
        out[h, 4, f, r] = (w*s[U]*s[V]).reshape(2, 16, 16)
        candidates = []; pool_by_bin = {}
        for b in range(BINS):
            ids = np.flatnonzero(bin_id == b)
            count = int((cut & (bin_id == b)).sum())
            iso[h, f, r, rng(*key, 'isolated', b).choice(ids, count, replace=False)] = True
            yes = ids[repair[h, f, r].ravel()[ids]]
            no = ids[~repair[h, f, r].ravel()[ids]]
            yes = rng(*key, 'repair_candidates', b).permutation(yes)[:min(len(yes), len(no))]
            candidates.extend(yes.tolist()); pool_by_bin[b] = no
        selected = rng(*key, 'repair_subset').permutation(candidates)[:int(cut.sum())].astype(int)
        target[h, f, r, selected] = True
        for b in range(BINS):
            count = int((bin_id[selected] == b).sum())
            chosen = rng(*key, 'other', b).choice(pool_by_bin[b], count, replace=False)
            other[h, f, r, chosen] = True
        for a, mask in ((5, iso[h, f, r]), (6, iso[h, f, r]),
                        (8, target[h, f, r]), (9, other[h, f, r])):
            flat = out[h, a, f, r].ravel()
            flat[mask] = -flat[mask] if a == 5 else 0.
        restored = out[h, 7, f, r].ravel(); restored[iso[h, f, r]] = 0.
        restored[iso[h, f, r]] = w[iso[h, f, r]]
    out[:, 10] = 0.
    assert np.array_equal(out[:, 1] != 0, records != 0), 'Scaling changed support'
    noise_signs = np.ones(out.shape[:4]+(16, 16)); noise_signs[:, 4] = signs
    changed = out != records[:, None]
    port_edges = (P.any(axis=0).ravel()[U] | P.any(axis=0).ravel()[V]).reshape(2, 16, 16)
    exposure = np.stack((changed.sum(axis=(-3, -2, -1)),
        (abs(records[:, None])*changed).sum(axis=(-3, -2, -1)),
        (changed & port_edges).sum(axis=(-3, -2, -1)),
        np.broadcast_to(repair.sum(axis=(-3, -2, -1))[:, None], out.shape[:4]),
        np.broadcast_to(target.sum(axis=-1)[:, None], out.shape[:4])), axis=-1)
    return dict(weights=out, noise_signs=noise_signs, cell_signs=signs,
        isolated=iso, delete_returning=target, delete_other=other, bins=bins,
        permutations=permutations, exposure=exposure, graph_before=graph_batch(out))


def coupling(w):
    d = reader.incident_sum(abs(w)); h, v = w[..., 0, :, :], w[..., 1, :, :]
    raw = np.stack((h, np.roll(h, 1, -1), v, np.roll(v, 1, -2)), axis=-3)
    k = np.zeros_like(raw); np.divide(raw, d[..., None, :, :], out=k, where=d[..., None, :, :] > 0)
    return d, k


def assay(interventions, block, cfg):
    H, A, F, R = interventions['weights'].shape[:4]; N = H*A
    records = interventions['weights'].reshape(N, F, R, 2, 16, 16)
    signs = interventions['noise_signs'].reshape(N, F, R, 16, 16)
    config = base.Config(recipients=R, observe_steps=cfg['observe_steps'])
    masks = base.damage_masks(block, 'E054_fresh_reader', config)
    effective = records[:, :, :, None]*reader.surviving_edges(masks)[None]
    d, k = coupling(effective)
    stream = rng('E054', block, 'fresh_reader')
    birth = cfg['birth_sd']*base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))
    signed = signs[:, :, :, None, None]
    v = np.broadcast_to(birth[None, :, :, None], (N, F, R, 2, 3, 16, 16)).copy()*signed
    alive = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1, 1, 1, 2, 1, 1)
    v *= alive; v[..., P[0]] = cue
    trace = []
    for t in range(cfg['read_steps']):
        noise = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]*signed
        v = reader.compensated_step(v, effective[:, :, :, None], d[:, :, :, None], noise,
                                   config, amplification=t >= cfg['settling_steps'])
        v *= alive; v[..., P[0]] = cue
        if t >= cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack([v[..., P[j]].mean(axis=-1) for j in (1, 2)], axis=-1))
    trace = np.stack(trace)
    return dict(masks=masks, effective=effective, denominator=d, coupling=k,
        birth=birth, end=v, late_ports=trace, mean_ports=trace.mean(axis=0),
        graph_after=graph_batch(effective))


def scores(raw):
    v = raw['mean_ports'].reshape(5, len(ARMS), *raw['mean_ports'].shape[1:])
    target = base.RULES.reshape(1, 1, 4, 1, 1, 1)*base.CUES.reshape(1, 1, 1, 1, 2, 1)
    margin = np.minimum(target*v[..., 0], -target*v[..., 1])
    transfer = ((v[:, :, :, :, 0, :, 0]-v[:, :, :, :, 1, :, 0])-
                (v[:, :, :, :, 0, :, 1]-v[:, :, :, :, 1, :, 1]))/4
    return dict(margin=margin, both=(margin > .25).all(axis=4), transfer=transfer,
                aligned_transfer=transfer*base.RULES.reshape(1, 1, 4, 1, 1))
