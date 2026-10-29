"""Fresh reconstruction and selected patterns at the filtered absolute total."""
import hashlib
import numpy as np
from common import rng
from E022_reader_compensation import model as reader

base = reader.base
P = base.PORTS


def intervene(source):
    before, after = base.decode(source['incoming']), base.decode(source['outgoing'])
    eligible = (before[:4] == 0) & (after[:4] != 0) & source['fallback'][:4]
    pruned = after[:4].copy()
    pruned[eligible] = 0.
    return dict(packets=base.encode(np.concatenate((after[:4], pruned, after[4:5]))),
                eligible=eligible)


def fraction(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b > 0)


def directed(e):
    h, v = e[..., 0, :, :], e[..., 1, :, :]
    return np.stack((h, np.roll(h, 1, -1), v, np.roll(v, 1, -2)), axis=-3)


def diagnostics(packets, inter, fresh, renewal, cfg):
    from E081_fresh_strength_pattern.plan import REFERENCE, BASELINE
    w = base.decode(packets)
    d, k = coupling(w)
    e9 = np.concatenate((inter['eligible'], inter['eligible'], np.zeros_like(inter['eligible'][:1])))
    e = np.concatenate((e9, e9, inter['eligible'], inter['eligible']))
    axes = (-3, -2, -1)
    ec = e.sum(axis=axes)
    present = ((w != 0) & e).sum(axis=axes)
    shared = (w != 0) & (w[REFERENCE] != 0)
    cases = score(fresh['mean_ports'], cfg['margin'])
    cases.update(edges=(w != 0).sum(axis=axes), weight_mass=abs(w).sum(axis=axes),
        eligible_edges=ec, no_eligible_edges=ec == 0,
        selected_present=present, selected_present_fraction=fraction(present, ec),
        sign_changes=(shared & ((w < 0) != (w[REFERENCE] < 0))).sum(axis=axes),
        support_gained=((w != 0) & (w[REFERENCE] == 0)).sum(axis=axes),
        support_lost=((w == 0) & (w[REFERENCE] != 0)).sum(axis=axes),
        gained_success=cases['both'] & ~cases['both'][REFERENCE],
        lost_success=~cases['both'] & cases['both'][REFERENCE],
        temporal_gained_success=cases['both'] & ~cases['both'][BASELINE],
        temporal_lost_success=~cases['both'] & cases['both'][BASELINE])
    cases.update(selected_mass=np.where(e,abs(w),0.).sum(axis=axes),
        postinjury_selected_mass=np.where(e,abs(fresh['effective']),0.).sum(axis=axes),
        max_absolute_weight=abs(w).max(axis=axes),weights_above_one=(abs(w)>1.).sum(axis=axes))
    for prefix, dd, kk in (('', d, k), ('postinjury_', fresh['denominator'], fresh['coupling'])):
        cases[prefix+'selected_coupling_share'] = fraction((abs(kk)*directed(e)).sum(axis=axes), abs(kk).sum(axis=axes))
        cases[prefix+'coupling_l1'] = abs(kk-kk[REFERENCE]).sum(axis=axes)/256
        cases[prefix+'unsigned_coupling_l1'] = abs(abs(kk)-abs(kk[REFERENCE])).sum(axis=axes)/256
        cases[prefix+'temporal_coupling_l1'] = abs(kk-kk[BASELINE]).sum(axis=axes)/256
        cases[prefix+'isolated_fraction'] = (dd == 0).mean(axis=(-2, -1))
        cases[prefix+'denominator_mean'] = dd.mean(axis=(-2, -1))
    observed = ((~fresh['masks']) & ~P.any(axis=0)).sum(axis=(-2, -1))
    cases['boundary_fraction'] = fresh['boundary_counts'] / (2*cfg['read_steps']*observed[None])
    available = e9 & reader.surviving_edges(renewal['masks'])
    out = base.decode(renewal['outgoing'])
    active = (out != 0) & e9
    available_count = available.sum(axis=axes)
    rewritten = active.sum(axis=axes)
    transition = dict(eligible_edges=e9.sum(axis=axes), available_selected=available_count,
        no_available_selected=available_count == 0, rewritten_selected=rewritten,
        rewritten_fraction=fraction(rewritten, available_count),
        fallback_selected=(active & renewal['fallback']).sum(axis=axes),
        contrast_selected=(active & ~renewal['fallback']).sum(axis=axes))
    return cases, dict(packets=packets.copy(), denominator=d, coupling=k), transition


def digest(v):
    return np.frombuffer(hashlib.sha256(np.ascontiguousarray(v, dtype='<f8').tobytes()).digest(), np.uint8)


def masks(block, R, phase, generation=0):
    stream = rng('E081', block, phase, generation)
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




def develop(packets, block, cfg, steps, phase, generation=0):
    w = base.decode(packets)
    A, F, R = w.shape[:3]
    mask = masks(block, R, phase + '_injury', generation)
    available = reader.surviving_edges(mask)
    effective = w * available
    d, k = coupling(effective)
    stream = rng('E081', block, phase, generation)
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


def capture(state, available, beta):
    x = np.tanh(beta * state)
    difference = (x[..., 0, :, :] - x[..., 1, :, :]) / 2
    contrast = np.stack((difference * np.roll(difference, -1, -1),
                         difference * np.roll(difference, -1, -2)), axis=-3)
    ordinary = base.correlations(state, beta).mean(axis=-4)
    fallback = (contrast == 0.) & available
    outgoing = np.where(available, np.where(fallback, ordinary, contrast), 0.)
    return outgoing, ordinary, contrast, fallback


def rebuild(incoming, block, generation, cfg, cycle):
    body = develop(incoming, block, cfg, cycle, 'develop', generation)
    available = reader.surviving_edges(body['masks'])
    out, ordinary, contrast, fallback = capture(body['end'], available, cfg['writer_beta'])
    v = body['end'].copy()
    R = cfg['recipients']
    stream = rng('E081', block, 'write', generation)
    live = (~body['masks'])[None, :, :, None]
    scaffold = available[None, :, :, None].astype(float)
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    hashes = []
    for _ in range(cycle['write_steps']):
        eta = base.paired_founders(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., eta, config)
        v *= live
        v[..., P[0]] = base.CUES.reshape(1, 1, 1, 2, 1)
        hashes.append(digest(v))
    return dict(**body, incoming=incoming.copy(), outgoing=base.encode(out), ordinary=ordinary,
        contrast=contrast, fallback=fallback, write_end=v, write_state_hashes=np.stack(hashes))




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


def allocate(ordinary, filtered, eligible, cfg):
    assert np.isfinite(ordinary).all() and np.isfinite(filtered).all(), 'Nonfinite donor'
    assert np.array_equal((ordinary!=0)[eligible],(filtered!=0)[eligible]), 'Selected support mismatch'
    t0=np.where(eligible,abs(ordinary),0.).sum(axis=(-3,-2,-1))
    tf=np.where(eligible,abs(filtered),0.).sum(axis=(-3,-2,-1))
    assert np.isfinite(t0).all() and np.isfinite(tf).all(), 'Nonfinite total'
    assert np.array_equal(t0==0,tf==0), 'Empty total mismatch'
    scale=np.ones_like(t0)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        np.divide(tf,t0,out=scale,where=t0>0)
        mag=abs(ordinary[eligible])*np.broadcast_to(scale[...,None,None,None],ordinary.shape)[eligible]
    assert np.isfinite(scale).all() and (scale>0).all(), 'Invalid scale'
    of=ordinary.copy();of[eligible]=np.copysign(mag,ordinary[eligible])
    ff=ordinary.copy();ff[eligible]=np.copysign(abs(filtered[eligible]),ordinary[eligible])
    for group in (of,ff):
        assert np.isfinite(group).all(), 'Nonfinite scaled weights'
        assert np.array_equal(group!=0,ordinary!=0), 'Scaled support mismatch'
        actual=np.where(eligible,abs(group),0.).sum(axis=(-3,-2,-1))
        assert np.allclose(actual,tf,rtol=cfg['total_relative_tolerance'],atol=cfg['total_absolute_tolerance']), 'Total mismatch'
    return dict(weights=np.concatenate((of,ff)),ordinary_total=t0,filtered_total=tf,
        scales=np.concatenate((scale,np.ones_like(scale))),target_totals=np.concatenate((tf,tf)))


def components(raw, eligible, cfg):
    w=base.decode(raw['outgoing'])
    ordinary=np.where(reader.surviving_edges(raw['masks']),raw['ordinary'][:4],0.)
    assert np.array_equal((w[:4]!=0)[eligible],(w[4:8]!=0)[eligible]), 'Selected support mismatch'
    o=w[4:8].copy();o[eligible]=ordinary[eligible]
    f=o.copy();f[eligible]=np.copysign(abs(w[:4][eligible]),o[eligible])
    result=allocate(o,f,eligible,cfg)
    return dict(packets=base.encode(result.pop('weights')),eligible=np.concatenate((eligible,eligible)),
        ordinary_packets=base.encode(o),filtered_packets=base.encode(f),**result)



