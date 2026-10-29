"""Independent equations: construction, dynamics, writer, copying and scores."""
import hashlib
import numpy as np
from E015_functional_inheritance.audit import random, pair, unpack, pack, ports, advance

P = ports()


def intervene(source):
    before, after = unpack(source['incoming']), unpack(source['outgoing'])
    R = after.shape[2]
    eligible = np.zeros(after[:4].shape, bool)
    result = np.concatenate((after[:4], after[:4], after[4:5]))
    for arm, f, r, edge, y, x in np.ndindex(4, 4, R, 2, 16, 16):
        loc = arm, f, r, edge, y, x
        if before[loc] == 0 and after[loc] != 0 and source['fallback'][loc]:
            eligible[loc] = True
            result[arm+4, f, r, edge, y, x] = 0.
    return dict(packets=pack(result), eligible=eligible)


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


def diagnostics(packets, inter, fresh, renewal, cfg):
    w = unpack(packets)
    d, k = coupling(w)
    refs = [0, 1, 2, 3, 0, 1, 2, 3, 8, 9, 10, 11, 12, 9, 10, 11, 12, 17]
    initial = list(range(9))*2
    e = np.zeros(w.shape, bool)
    for start in (0, 4, 9, 13): e[start:start+4] = inter['eligible']
    axes = (-3, -2, -1)
    ec = np.count_nonzero(e, axis=axes)
    present = np.count_nonzero((w != 0) & e, axis=axes)
    shared = (w != 0) & (w[refs] != 0)
    out = score(fresh['mean_ports'], cfg['margin'])
    out.update(edges=np.count_nonzero(w, axis=axes), weight_mass=np.abs(w).sum(axis=axes),
        eligible_edges=ec, no_eligible_edges=ec == 0, selected_present=present,
        selected_present_fraction=divide(present, ec),
        sign_changes=np.count_nonzero(shared & ((w < 0) != (w[refs] < 0)), axis=axes),
        support_gained=np.count_nonzero((w != 0) & (w[refs] == 0), axis=axes),
        support_lost=np.count_nonzero((w == 0) & (w[refs] != 0), axis=axes),
        gained_success=out['both'] & ~out['both'][refs],
        lost_success=~out['both'] & out['both'][refs],
        temporal_gained_success=out['both'] & ~out['both'][initial],
        temporal_lost_success=~out['both'] & out['both'][initial])
    for prefix, dd, kk in (('', d, k), ('postinjury_', fresh['denominator'], fresh['coupling'])):
        out[prefix+'selected_coupling_share'] = divide((np.abs(kk)*directions(e)).sum(axis=axes), np.abs(kk).sum(axis=axes))
        out[prefix+'coupling_l1'] = np.abs(kk-kk[refs]).sum(axis=axes)/256
        out[prefix+'unsigned_coupling_l1'] = np.abs(np.abs(kk)-np.abs(kk[refs])).sum(axis=axes)/256
        out[prefix+'temporal_coupling_l1'] = np.abs(kk-kk[initial]).sum(axis=axes)/256
        out[prefix+'isolated_fraction'] = np.mean(dd == 0, axis=(-2, -1))
        out[prefix+'denominator_mean'] = np.mean(dd, axis=(-2, -1))
    observed = np.count_nonzero((~fresh['masks']) & ~P.any(axis=0), axis=(-2, -1))
    out['boundary_fraction'] = fresh['boundary_counts'] / (2*cfg['read_steps']*observed[None])
    available = np.count_nonzero(e[:9] & alive(renewal['masks']), axis=axes)
    active = (unpack(renewal['outgoing']) != 0) & e[:9]
    rewritten = np.count_nonzero(active, axis=axes)
    transition = dict(eligible_edges=np.count_nonzero(e[:9], axis=axes),
        available_selected=available, no_available_selected=available == 0,
        rewritten_selected=rewritten, rewritten_fraction=divide(rewritten, available),
        fallback_selected=np.count_nonzero(active & renewal['fallback'], axis=axes),
        contrast_selected=np.count_nonzero(active & ~renewal['fallback'], axis=axes))
    return out, dict(packets=packets.copy(), denominator=d, coupling=k), transition


def digest(v):
    return np.frombuffer(hashlib.sha256(np.asarray(v, dtype='<f8').tobytes()).digest(), dtype=np.uint8)


def masks(block, R, phase, generation=0):
    stream = random('E073', block, phase, generation)
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




def develop(packets, block, cfg, steps, phase, generation=0):
    weights = unpack(packets)
    N, F, R = weights.shape[:3]
    mask = masks(block, R, phase + '_injury', generation)
    effective = weights * alive(mask)
    d, k = coupling(effective)
    stream = random('E073', block, phase, generation)
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


def capture(state, physical, beta):
    x = np.tanh(beta * state)
    shape = (*state.shape[:-3], 2, 16, 16)
    ordinary, contrast = np.empty(shape), np.empty(shape)
    for direction, y, col in np.ndindex(2, 16, 16):
        yy, xx = (y, (col + 1) % 16) if direction == 0 else ((y + 1) % 16, col)
        a, b = x[..., y, col], x[..., yy, xx]
        contrast[..., direction, y, col] = ((a[..., 0] - a[..., 1]) / 2) * ((b[..., 0] - b[..., 1]) / 2)
        total = np.zeros(a.shape[:-1])
        total += a[..., 0] * b[..., 0]
        total += a[..., 1] * b[..., 1]
        total /= 2
        ordinary[..., direction, y, col] = total
    fallback = (contrast == 0) & physical
    outgoing = np.zeros_like(contrast)
    good = np.broadcast_to(physical, contrast.shape)
    outgoing[good] = contrast[good]
    outgoing[fallback] = ordinary[fallback]
    return outgoing, ordinary, contrast, fallback


def rebuild(incoming, block, generation, cfg, cycle):
    body = develop(incoming, block, cfg, cycle, 'develop', generation)
    physical = alive(body['masks'])
    out, ordinary, contrast, fallback = capture(body['end'], physical, cfg['writer_beta'])
    v = body['end'].copy()
    R = cfg['recipients']
    stream = random('E073', block, 'write', generation)
    scaffold = physical[None, :, :, None].astype(float)
    live = (~body['masks'])[None, :, :, None]
    hashes = []
    for _ in range(cycle['write_steps']):
        eta = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, scaffold, 2., eta, cfg)
        v *= live
        v[..., P[0]] = np.array([1., -1.]).reshape(1, 1, 1, 2, 1)
        hashes.append(digest(v))
    return dict(**body, incoming=incoming.copy(), outgoing=pack(out), ordinary=ordinary,
        contrast=contrast, fallback=fallback, write_end=v, write_state_hashes=np.array(hashes))




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


