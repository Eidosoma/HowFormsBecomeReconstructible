"""E077 writer with one controlled change: second-cue read noise."""
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff import model as old

base, reader, P = old.base, old.reader, old.P
AXES = (-3, -2, -1)


def rebuild(packets, block, cfg, cycle):
    assert packets.shape[0] == 9
    incoming = np.concatenate((packets, packets))
    w = base.decode(incoming)
    A, F, R = w.shape[:3]
    mask = old.masks(block, R, 'develop_injury', 1)
    physical = reader.surviving_edges(mask)
    effective = w * physical
    denominator, coupling = old.coupling(effective)
    common = rng('E077', block, 'develop', 1)
    innovation = rng('E098', block, 'writer_second_cue', 1)
    shape = (2, R, 16, 16)
    birth = cfg['birth_sd'] * base.paired_founders(common.standard_normal(shape))
    v = np.broadcast_to(birth[None, :, :, None], (A, F, R, 2, 16, 16)).copy()
    live = (~mask)[None, :, :, None]
    cue = base.CUES.reshape(1, 1, 1, 2, 1)
    v *= live; v[..., P[0]] = cue
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    trace, hashes, paired_hashes, common_hashes, innovation_hashes = [], [], [], [], []
    boundary = np.zeros((A, F, R), np.int64)
    observed = ((~mask) & ~P.any(axis=0))[None, :, :, None]
    for t in range(cycle['read_steps']):
        z = base.paired_founders(common.standard_normal(shape))
        z2 = base.paired_founders(innovation.standard_normal(shape))
        eta = np.broadcast_to(z[None, :, :, None], v.shape).copy()
        eta[9:, :, :, 1] = z2
        v = reader.compensated_step(v, effective[:, :, :, None], denominator[:, :, :, None],
                                    eta, config, t >= cycle['settling_steps'])
        v *= live; v[..., P[0]] = cue
        hashes.append(old.digest(v)); paired_hashes.append(old.digest(v[:9]))
        common_hashes.append(old.digest(z)); innovation_hashes.append(old.digest(z2))
        boundary += ((abs(v) == 2.) & observed).sum(axis=AXES)
        if t >= cycle['read_steps'] - cfg['observe_steps']:
            trace.append(np.stack([v[..., P[p]].mean(axis=-1) for p in (1, 2)], axis=-1))
    trace = np.stack(trace)
    out, ordinary, contrast, fallback = old.capture(v, physical, cfg['writer_beta'])
    x = np.tanh(cfg['writer_beta'] * v)
    m = (x[..., 0, :, :] + x[..., 1, :, :]) / 2
    cue_independent = np.stack((m*np.roll(m, -1, -1), m*np.roll(m, -1, -2)), axis=-3)
    body = dict(masks=mask, effective=effective, denominator=denominator, coupling=coupling, birth=birth,
        end=v.copy(), late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.stack(hashes),
        paired_state_hashes=np.stack(paired_hashes), common_noise_hashes=np.stack(common_hashes),
        innovation_noise_hashes=np.stack(innovation_hashes), boundary_counts=boundary)
    holding = rng('E077', block, 'write', 1)
    scaffold = physical[None, :, :, None].astype(float)
    hashes, paired_hashes = [], []
    for _ in range(cycle['write_steps']):
        eta = base.paired_founders(holding.standard_normal(shape))[None, :, :, None]
        v = base.step(v, scaffold, 2., eta, config)
        v *= live; v[..., P[0]] = cue
        hashes.append(old.digest(v)); paired_hashes.append(old.digest(v[:9]))
    return dict(**body, incoming=incoming, outgoing=base.encode(out), ordinary=ordinary,
        contrast=contrast, cue_independent=cue_independent, fallback=fallback, write_end=v,
        write_state_hashes=np.stack(hashes), paired_write_state_hashes=np.stack(paired_hashes))


def legacy_projection(writer):
    shared = ('masks', 'birth')
    first_axis = ('effective', 'denominator', 'coupling', 'end', 'mean_ports', 'boundary_counts',
                  'incoming', 'outgoing', 'ordinary', 'contrast', 'fallback', 'write_end')
    return dict(**{k:writer[k] for k in shared}, **{k:writer[k][:9] for k in first_axis},
        late_ports=writer['late_ports'][:, :9], state_hashes=writer['paired_state_hashes'],
        write_state_hashes=writer['paired_write_state_hashes'])


def selected_masks(selected, groups):
    e9 = np.concatenate((selected, selected, np.zeros_like(selected[:1])))
    return np.concatenate([e9]*groups)


def coupling_diagnostics(packets, selected, fresh):
    w = base.decode(packets); e = selected_masks(selected, len(w)//9)
    d, k = old.coupling(w)
    active = (w != 0) & e
    result = dict(eligible_edges=e.sum(axis=AXES), no_eligible_edges=e.sum(axis=AXES) == 0,
        selected_present=active.sum(axis=AXES), selected_weight_mass=(abs(w)*e).sum(axis=AXES),
        edges=(w != 0).sum(axis=AXES), weight_mass=abs(w).sum(axis=AXES))
    for prefix, dd, kk in (('', d, k), ('postinjury_', fresh['denominator'], fresh['coupling'])):
        result[prefix+'selected_coupling_share'] = old.fraction((abs(kk)*old.directed(e)).sum(axis=AXES), abs(kk).sum(axis=AXES))
        result[prefix+'coupling_mass'] = abs(kk).sum(axis=AXES)
        result[prefix+'denominator_mean'] = dd.mean(axis=(-2,-1))
        result[prefix+'isolated_fraction'] = (dd == 0).mean(axis=(-2,-1))
    return result, dict(packets=packets.copy(), denominator=d, coupling=k)


def writer_diagnostics(writer, selected):
    e = selected_masks(selected, 2)
    available = e & reader.surviving_edges(writer['masks'])
    w = base.decode(writer['outgoing']); before = base.decode(writer['incoming'])
    active = (w != 0) & available
    count = available.sum(axis=AXES)
    shared = available & (w != 0) & (before != 0)
    result = dict(eligible_edges=e.sum(axis=AXES), available_selected=count, no_available_selected=count == 0,
        rewritten_selected=active.sum(axis=AXES), rewritten_fraction=old.fraction(active.sum(axis=AXES), count),
        fallback_available=(available & writer['fallback']).sum(axis=AXES),
        contrast_available=(available & ~writer['fallback']).sum(axis=AXES),
        fallback_selected=(active & writer['fallback']).sum(axis=AXES),
        contrast_selected=(active & ~writer['fallback']).sum(axis=AXES),
        restored_selected=(active & (before == 0)).sum(axis=AXES),
        sign_changes=(shared & (np.signbit(w) != np.signbit(before))).sum(axis=AXES),
        selected_weight_mass=(abs(w)*available).sum(axis=AXES))
    for key in ('ordinary', 'contrast', 'cue_independent'):
        result[key+'_absolute_sum'] = (abs(writer[key])*available).sum(axis=AXES)
        result[key+'_signed_sum'] = (writer[key]*available).sum(axis=AXES)
    np.testing.assert_allclose(writer['ordinary'], writer['cue_independent']+writer['contrast'], rtol=0, atol=5e-16)
    return result


def end_ports(writer):
    return np.stack([writer['end'][..., P[p]].mean(axis=-1) for p in (1,2)], axis=-1)
