"""Independent writer updates, slot construction and edge diagnostics."""
import numpy as np
from E077_fresh_reconstruction_tradeoff import audit_model as old

P = old.P
AXES = (-3, -2, -1)


def rebuild(packets, block, cfg, cycle):
    assert len(packets) == 9
    incoming = np.empty((18, *packets.shape[1:]), dtype=packets.dtype)
    for slot in range(18): incoming[slot] = packets[slot % 9]
    weights = old.unpack(incoming)
    N, F, R = weights.shape[:3]
    mask = old.masks(block, R, 'develop_injury', 1)
    physical = old.alive(mask)
    effective = weights * physical
    d, k = old.coupling(effective)
    stream = old.random('E077', block, 'develop', 1)
    second = old.random('E098', block, 'writer_second_cue', 1)
    birth = cfg['birth_sd'] * old.pair(stream.standard_normal((2, R, 16, 16)))
    v = np.empty((N, F, R, 2, 16, 16))
    for n, cue in np.ndindex(N, 2): v[n, :, :, cue] = birth
    live = (~mask)[None, :, :, None]
    cues = np.array([1., -1.]).reshape(1, 1, 1, 2, 1)
    v *= live; v[..., P[0]] = cues
    trace, hashes, paired_hashes, common_hashes, innovation_hashes = [], [], [], [], []
    counts = np.zeros((N, F, R), np.int64)
    free = ((~mask) & ~P.any(axis=0))[None, :, :, None]
    h, ve = effective[:, :, :, None, 0], effective[:, :, :, None, 1]
    for t in range(cycle['read_steps']):
        z = old.pair(stream.standard_normal((2, R, 16, 16)))
        z2 = old.pair(second.standard_normal((2, R, 16, 16)))
        eta = np.empty(v.shape)
        for slot, cue in np.ndindex(N, 2):
            eta[slot, :, :, cue] = z2 if slot >= 9 and cue == 1 else z
        incoming_drive = h * np.roll(v, -1, -1)
        incoming_drive = incoming_drive + np.roll(h, 1, -1) * np.roll(v, 1, -1)
        incoming_drive = incoming_drive + ve * np.roll(v, -1, -2)
        incoming_drive = incoming_drive + np.roll(ve, 1, -2) * np.roll(v, 1, -2)
        u = np.zeros_like(incoming_drive)
        np.divide(incoming_drive, d[:, :, :, None], out=u, where=d[:, :, :, None] > 0)
        drift = (v-v**3 if t >= cycle['settling_steps'] else -v**3) + 2.*(u-v)
        v = np.clip(v + cfg['dt']*drift + cfg['noise']*eta, -2., 2.)
        v *= live; v[..., P[0]] = cues
        hashes.append(old.digest(v)); paired_hashes.append(old.digest(v[:9]))
        common_hashes.append(old.digest(z)); innovation_hashes.append(old.digest(z2))
        counts += ((abs(v) == 2.) & free).sum(axis=AXES)
        if t >= cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[..., P[1]].mean(axis=-1), v[..., P[2]].mean(axis=-1)), axis=-1))
    trace = np.array(trace)
    out, ordinary, contrast, fallback = old.capture(v, physical, cfg['writer_beta'])
    x = np.tanh(cfg['writer_beta']*v)
    cue_independent = np.empty_like(ordinary)
    for direction, y, col in np.ndindex(2, 16, 16):
        yy, xx = (y, (col+1)%16) if direction == 0 else ((y+1)%16, col)
        a, b = x[..., y, col], x[..., yy, xx]
        cue_independent[..., direction, y, col] = ((a[...,0]+a[...,1])/2)*((b[...,0]+b[...,1])/2)
    body = dict(masks=mask, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v.copy(), late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.array(hashes),
        paired_state_hashes=np.array(paired_hashes), common_noise_hashes=np.array(common_hashes),
        innovation_noise_hashes=np.array(innovation_hashes), boundary_counts=counts)
    stream = old.random('E077', block, 'write', 1)
    scaffold = physical[None, :, :, None].astype(float)
    hashes, paired_hashes = [], []
    for _ in range(cycle['write_steps']):
        eta = old.pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = old.advance(v, scaffold, 2., eta, cfg)
        v *= live; v[..., P[0]] = cues
        hashes.append(old.digest(v)); paired_hashes.append(old.digest(v[:9]))
    return dict(**body, incoming=incoming, outgoing=old.pack(out), ordinary=ordinary,
        contrast=contrast, cue_independent=cue_independent, fallback=fallback, write_end=v,
        write_state_hashes=np.array(hashes), paired_write_state_hashes=np.array(paired_hashes))


def selected_masks(selected, groups):
    e = np.zeros((9*groups, *selected.shape[1:]), bool)
    for g, arm in np.ndindex(groups, 4):
        e[g*9+arm] = selected[arm]; e[g*9+4+arm] = selected[arm]
    return e


def coupling_diagnostics(packets, selected, fresh):
    w = old.unpack(packets); e = selected_masks(selected, len(w)//9)
    d, k = old.coupling(w)
    result = dict(eligible_edges=np.count_nonzero(e, axis=AXES),
        no_eligible_edges=np.count_nonzero(e, axis=AXES) == 0,
        selected_present=np.count_nonzero((w != 0) & e, axis=AXES),
        selected_weight_mass=np.where(e, np.abs(w), 0).sum(axis=AXES),
        edges=np.count_nonzero(w, axis=AXES), weight_mass=np.abs(w).sum(axis=AXES))
    for prefix, dd, kk in (('', d, k), ('postinjury_', fresh['denominator'], fresh['coupling'])):
        selected_mass = np.where(old.directions(e), np.abs(kk), 0).sum(axis=AXES)
        result[prefix+'selected_coupling_share'] = old.divide(selected_mass, np.abs(kk).sum(axis=AXES))
        result[prefix+'coupling_mass'] = np.abs(kk).sum(axis=AXES)
        result[prefix+'denominator_mean'] = dd.mean(axis=(-2,-1))
        result[prefix+'isolated_fraction'] = np.mean(dd == 0, axis=(-2,-1))
    return result, dict(packets=packets.copy(), denominator=d, coupling=k)


def writer_diagnostics(writer, selected):
    e = selected_masks(selected, 2)
    available = e & old.alive(writer['masks'])
    w, before = old.unpack(writer['outgoing']), old.unpack(writer['incoming'])
    active = available & (w != 0)
    count = np.count_nonzero(available, axis=AXES)
    shared = available & (w != 0) & (before != 0)
    result = dict(eligible_edges=np.count_nonzero(e, axis=AXES), available_selected=count,
        no_available_selected=count == 0, rewritten_selected=np.count_nonzero(active, axis=AXES),
        rewritten_fraction=old.divide(np.count_nonzero(active, axis=AXES), count),
        fallback_available=np.count_nonzero(available & writer['fallback'], axis=AXES),
        contrast_available=np.count_nonzero(available & ~writer['fallback'], axis=AXES),
        fallback_selected=np.count_nonzero(active & writer['fallback'], axis=AXES),
        contrast_selected=np.count_nonzero(active & ~writer['fallback'], axis=AXES),
        restored_selected=np.count_nonzero(active & (before == 0), axis=AXES),
        sign_changes=np.count_nonzero(shared & (np.signbit(w) != np.signbit(before)), axis=AXES),
        selected_weight_mass=np.where(available, np.abs(w), 0).sum(axis=AXES))
    for key in ('ordinary', 'contrast', 'cue_independent'):
        result[key+'_absolute_sum'] = np.where(available, np.abs(writer[key]), 0).sum(axis=AXES)
        # Multiplication, rather than masking to +0, retains signed-zero summation.
        result[key+'_signed_sum'] = (writer[key]*available).sum(axis=AXES)
    assert np.max(np.abs(writer['ordinary']-writer['cue_independent']-writer['contrast'])) <= 5e-16
    return result


def end_ports(writer):
    v = writer['end']; out = np.empty((*v.shape[:-2], 2))
    for slot in range(len(v)):
        for port in (1,2): out[slot,...,port-1] = v[slot][...,P[port]].mean(axis=-1)
    return out
