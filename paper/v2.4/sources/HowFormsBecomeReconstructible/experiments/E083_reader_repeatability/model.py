"""Unchanged reader equations, with fresh E083 streams."""
import hashlib
import numpy as np
from common import rng
from E022_reader_compensation import model as reader
base=reader.base
P=base.PORTS


def fraction(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b > 0)


def directed(e):
    h, v = e[..., 0, :, :], e[..., 1, :, :]
    return np.stack((h, np.roll(h, 1, -1), v, np.roll(v, 1, -2)), axis=-3)


def digest(v):
    return np.frombuffer(hashlib.sha256(np.ascontiguousarray(v, dtype='<f8').tobytes()).digest(), np.uint8)


def masks(block, R, phase, generation=0, stream_tag='E083'):
    stream = rng(stream_tag, block, phase, generation)
    eligible = np.flatnonzero(~P.any(axis=0).ravel())
    m = np.zeros((2, R, 16, 16), bool)
    for f, r in np.ndindex(2, R):
        m[f, r].ravel()[stream.choice(eligible, 24, replace=False)] = True
    return base.paired_founders(m)


def coupling(w):
    h, v = w[..., 0, :, :], w[..., 1, :, :]
    raw = np.stack((h, np.roll(h, 1, -1), v, np.roll(v, 1, -2)), axis=-3)
    d = reader.incident_sum(abs(w))
    k = np.zeros_like(raw)
    np.divide(raw, d[..., None, :, :], out=k, where=d[..., None, :, :] > 0)
    return d, k


def develop(packets, block, cfg, steps, phase, generation=0, stream_tag='E083'):
    w = base.decode(packets)
    A, F, R = w.shape[:3]
    mask = masks(block, R, phase + '_injury', generation, stream_tag)
    available = reader.surviving_edges(mask)
    effective = w * available
    d, k = coupling(effective)
    stream = rng(stream_tag, block, phase, generation)
    shape = (2, R, 16, 16)
    birth = cfg['birth_sd'] * base.paired_founders(stream.standard_normal(shape))
    v = np.broadcast_to(birth[None, :, :, None], (A, F, R, 2, 16, 16)).copy()
    live = (~mask)[None, :, :, None]
    cue = base.CUES.reshape(1, 1, 1, 2, 1)
    v *= live
    v[..., P[0]] = cue
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    trace, hashes = [], []
    boundary = np.zeros((A, F, R), np.int64)
    observed = ((~mask) & ~P.any(axis=0))[None, :, :, None]
    for t in range(steps['read_steps']):
        eta = base.paired_founders(stream.standard_normal(shape))[None, :, :, None]
        v = reader.compensated_step(v, effective[:, :, :, None], d[:, :, :, None],
                                   eta, config, t >= steps['settling_steps'])
        v *= live
        v[..., P[0]] = cue
        hashes.append(digest(v))
        boundary += ((abs(v) == 2.) & observed).sum(axis=(-3, -2, -1))
        if t >= steps['read_steps'] - cfg['observe_steps']:
            trace.append(np.stack([v[..., P[p]].mean(axis=-1) for p in (1, 2)], axis=-1))
    trace = np.stack(trace)
    return dict(masks=mask, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.stack(hashes),
        boundary_counts=boundary)


def score(v, margin):
    desired = base.RULES.reshape(1, 4, 1, 1) * base.CUES
    a, b = desired * v[..., 0], -desired * v[..., 1]
    m = np.minimum(a, b)
    transfer = ((v[..., 0, 0] - v[..., 1, 0]) - (v[..., 0, 1] - v[..., 1, 1])) / 4
    success = (m > margin).all(axis=-1)
    wrong = (m < 0).any(axis=-1)
    return dict(margin=m, minimum_margin=m.min(axis=-1), both=success,
        transfer=transfer, aligned_transfer=transfer * base.RULES.reshape(1, 4, 1),
        correct_signs_below_threshold=(m > 0).all(axis=-1) & ~success,
        zero_without_wrong_sign=(m == 0).any(axis=-1) & ~wrong,
        any_wrong_sign=wrong, opposite_rule_success=(np.minimum(-a, -b) > margin).all(axis=-1))


def diagnostics(packets, eligible, fresh, cfg):
    from E083_reader_repeatability.plan import REFERENCE
    w=base.decode(packets);d,k=coupling(w)
    e=np.zeros_like(w,dtype=bool)
    for start in (0,4,9,13,18,22):e[start:start+4]=eligible
    axes=(-3,-2,-1);out=score(fresh['mean_ports'],cfg['margin'])
    out.update(selected_mass=np.where(e,abs(w),0.).sum(axis=axes),
        postinjury_selected_mass=np.where(e,abs(fresh['effective']),0.).sum(axis=axes),
        selected_present=((w!=0)&e).sum(axis=axes),eligible_edges=e.sum(axis=axes),
        max_absolute_weight=abs(w).max(axis=axes),weights_above_one=(abs(w)>1.).sum(axis=axes))
    for prefix,dd,kk in (('',d,k),('postinjury_',fresh['denominator'],fresh['coupling'])):
        out[prefix+'selected_coupling_share']=fraction((abs(kk)*directed(e)).sum(axis=axes),abs(kk).sum(axis=axes))
        out[prefix+'coupling_l1']=abs(kk-kk[REFERENCE]).sum(axis=axes)/256
        out[prefix+'denominator_mean']=dd.mean(axis=(-2,-1))
        out[prefix+'isolated_fraction']=(dd==0).mean(axis=(-2,-1))
    observed=((~fresh['masks'])&~P.any(axis=0)).sum(axis=(-2,-1))
    out['boundary_fraction']=fresh['boundary_counts']/(2*cfg['read_steps']*observed[None])
    return out,dict(packets=packets.copy(),denominator=d,coupling=k)
