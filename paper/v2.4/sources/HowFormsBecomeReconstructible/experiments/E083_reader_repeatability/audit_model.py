"""Independent replay of every E083 reader state."""
import hashlib
import numpy as np
from E015_functional_inheritance.audit import random, pair, unpack, ports
P=ports()


def divide(a, b):
    out = np.zeros(a.shape, float)
    np.divide(a, b, out=out, where=b != 0)
    return out


def directions(e):
    out = np.empty((*e.shape[:-3], 4, 16, 16), dtype=e.dtype)
    for y, x in np.ndindex(16, 16):
        out[..., 0, y, x] = e[..., 0, y, x]
        out[..., 1, y, x] = e[..., 0, y, (x-1)%16]
        out[..., 2, y, x] = e[..., 1, y, x]
        out[..., 3, y, x] = e[..., 1, (y-1)%16, x]
    return out


def digest(v):
    return np.frombuffer(hashlib.sha256(np.asarray(v, dtype='<f8').tobytes()).digest(), dtype=np.uint8)


def masks(block, R, phase, generation=0, stream_tag='E083'):
    stream = random(stream_tag, block, phase, generation)
    possible = [16 * y + x for y, x in np.ndindex(16, 16) if not P[:, y, x].any()]
    m = np.zeros((2, R, 16, 16), bool)
    for f in range(2):
        for r in range(R):
            chosen = stream.choice(possible, size=24, replace=False)
            for pos in chosen:
                m[f, r, pos // 16, pos % 16] = True
    return pair(m)


def alive(mask):
    out = np.empty((*mask.shape[:-2], 2, 16, 16), bool)
    for y, x in np.ndindex(16, 16):
        out[..., 0, y, x] = ~mask[..., y, x] & ~mask[..., y, (x + 1) % 16]
        out[..., 1, y, x] = ~mask[..., y, x] & ~mask[..., (y + 1) % 16, x]
    return out


def coupling(w):
    d = np.empty((*w.shape[:-3], 16, 16))
    raw = np.empty((*w.shape[:-3], 4, 16, 16))
    for y, x in np.ndindex(16, 16):
        a, b = w[..., 0, y, x], w[..., 0, y, (x - 1) % 16]
        c, e = w[..., 1, y, x], w[..., 1, (y - 1) % 16, x]
        d[..., y, x] = abs(a) + abs(b) + abs(c) + abs(e)
        for j, value in enumerate((a, b, c, e)):
            raw[..., j, y, x] = value
    k = np.zeros_like(raw)
    np.divide(raw, d[..., None, :, :], out=k, where=d[..., None, :, :] > 0)
    return d, k


def develop(packets, block, cfg, steps, phase, generation=0, stream_tag='E083'):
    weights = unpack(packets)
    N, F, R = weights.shape[:3]
    mask = masks(block, R, phase + '_injury', generation, stream_tag)
    effective = weights * alive(mask)
    d, k = coupling(effective)
    stream = random(stream_tag, block, phase, generation)
    birth = cfg['birth_sd'] * pair(stream.standard_normal((2, R, 16, 16)))
    v = np.empty((N, F, R, 2, 16, 16))
    for n, cue in np.ndindex(N, 2):
        v[n, :, :, cue] = birth
    live = (~mask)[None, :, :, None]
    cues = np.array([1., -1.]).reshape(1, 1, 1, 2, 1)
    v *= live
    v[..., P[0]] = cues
    trace, hashes = [], []
    counts = np.zeros((N, F, R), np.int64)
    free = ((~mask) & ~P.any(axis=0))[None, :, :, None]
    h = effective[:, :, :, None, 0]
    ve = effective[:, :, :, None, 1]
    for t in range(steps['read_steps']):
        eta = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        incoming = h * np.roll(v, -1, -1)
        incoming = incoming + np.roll(h, 1, -1) * np.roll(v, 1, -1)
        incoming = incoming + ve * np.roll(v, -1, -2)
        incoming = incoming + np.roll(ve, 1, -2) * np.roll(v, 1, -2)
        u = np.zeros_like(incoming)
        np.divide(incoming, d[:, :, :, None], out=u, where=d[:, :, :, None] > 0)
        drift = (v - v**3 if t >= steps['settling_steps'] else -v**3) + 2. * (u - v)
        v = np.clip(v + cfg['dt'] * drift + cfg['noise'] * eta, -2., 2.)
        v *= live
        v[..., P[0]] = cues
        hashes.append(digest(v))
        counts += ((abs(v) == 2.) & free).sum(axis=(-3, -2, -1))
        if t >= steps['read_steps'] - cfg['observe_steps']:
            trace.append(np.stack((v[..., P[1]].mean(axis=-1), v[..., P[2]].mean(axis=-1)), axis=-1))
    trace = np.array(trace)
    return dict(masks=mask, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.array(hashes),
        boundary_counts=counts)


def score(v, threshold):
    m = np.empty(v.shape[:-1])
    opposite_margin = np.empty_like(m)
    tr = np.empty(v.shape[:-2])
    for a, f, r in np.ndindex(v.shape[:3]):
        rule = (1., -1., 1., -1.)[f]
        for c, cue in enumerate((1., -1.)):
            x, y = rule * cue * v[a, f, r, c, 0], -rule * cue * v[a, f, r, c, 1]
            m[a, f, r, c] = x if x < y else y
            opposite_margin[a, f, r, c] = -x if -x < -y else -y
        tr[a, f, r] = ((v[a, f, r, 0, 0] - v[a, f, r, 1, 0]) -
                       (v[a, f, r, 0, 1] - v[a, f, r, 1, 1])) / 4
    both = (m > threshold).all(axis=-1)
    wrong = (m < 0).any(axis=-1)
    return dict(margin=m, minimum_margin=m.min(axis=-1), both=both, transfer=tr,
        aligned_transfer=tr * np.array([1., -1., 1., -1.])[None, :, None],
        correct_signs_below_threshold=(m > 0).all(axis=-1) & ~both,
        zero_without_wrong_sign=(m == 0).any(axis=-1) & ~wrong,
        any_wrong_sign=wrong, opposite_rule_success=(opposite_margin > threshold).all(axis=-1))


def diagnostics(packets, eligible, fresh, cfg):
    w=unpack(packets);d,k=coupling(w)
    e=np.zeros(w.shape,bool)
    for start in (0,4,9,13,18,22):e[start:start+4]=eligible
    refs=[0,1,2,3,0,1,2,3,8,9,10,11,12,9,10,11,12,17]+[18,19,20,21]*2
    axes=(-3,-2,-1);out=score(fresh['mean_ports'],cfg['margin'])
    out.update(selected_mass=np.where(e,np.abs(w),0.).sum(axis=axes),
        postinjury_selected_mass=np.where(e,np.abs(fresh['effective']),0.).sum(axis=axes),
        selected_present=np.count_nonzero((w!=0)&e,axis=axes),eligible_edges=np.count_nonzero(e,axis=axes),
        max_absolute_weight=np.abs(w).max(axis=axes),weights_above_one=np.count_nonzero(np.abs(w)>1.,axis=axes))
    for prefix,dd,kk in (('',d,k),('postinjury_',fresh['denominator'],fresh['coupling'])):
        out[prefix+'selected_coupling_share']=divide((np.abs(kk)*directions(e)).sum(axis=axes),np.abs(kk).sum(axis=axes))
        out[prefix+'coupling_l1']=np.abs(kk-kk[refs]).sum(axis=axes)/256
        out[prefix+'denominator_mean']=np.mean(dd,axis=(-2,-1))
        out[prefix+'isolated_fraction']=np.mean(dd==0,axis=(-2,-1))
    observed=np.count_nonzero((~fresh['masks'])&~P.any(axis=0),axis=(-2,-1))
    out['boundary_fraction']=fresh['boundary_counts']/(2*cfg['read_steps']*observed[None])
    return out,dict(packets=packets.copy(),denominator=d,coupling=k)
