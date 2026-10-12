"""Rule-blind pulse, passive capture, and a packet-only fresh reader."""
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
from E022_reader_compensation import model as reader
from E054_record_interventions.model import coupling, graph_batch
from E055_stress_capture_recovery.plan import ARMS
import numpy as np

base = reader.base
P = base.PORTS


def state_hash(v):
    return np.frombuffer(hashlib.sha256(np.ascontiguousarray(v, dtype='<f8').tobytes()).digest(), np.uint8)


def pulse_field(mask, block, sites):
    R = mask.shape[1]
    field = np.zeros((2, R, 16, 16))
    selected = np.zeros_like(field, bool)
    for f, r in np.ndindex(2, R):
        stream = rng('E055', block, 'pulse_field', f, r)
        eligible = np.flatnonzero((~mask[2*f, r] & ~P.any(axis=0)).ravel())
        ids = stream.choice(eligible, sites, replace=False)
        selected[f, r].ravel()[ids] = True
        field[f, r].ravel()[ids] = stream.choice(np.array([-1., 1.]), sites)
    return base.paired_founders(field), base.paired_founders(selected)


def develop(records, block, cfg):
    H, F, R = records.shape[:3]
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    masks = base.damage_masks(block, 'E055_current_body', config)[:, :, 1]
    available = reader.surviving_edges(masks)
    effective = records * available
    d, k = coupling(effective)
    field, selected = pulse_field(masks, block, cfg['pulse_sites'])
    stream = rng('E055', block, 'current_body')
    birth = cfg['birth_sd'] * base.paired_founders(stream.standard_normal((2, R, 16, 16)))
    v = np.broadcast_to(birth[None, None, :, :, None], (H, 2, F, R, 2, 16, 16)).copy()
    live = (~masks)[None, None, :, :, None]
    cue = base.CUES.reshape(1, 1, 1, 1, 2, 1)
    v *= live
    v[..., P[0]] = cue
    initial = v.copy()
    before = cfg['body_pre_steps']
    early = before + cfg['pulse_steps']
    late = early + cfg['recovery_steps']
    boundaries = (before, early, late)
    windows = [[], [], []]
    states = []
    hashes = []
    requested = np.zeros((H, F, R, 2))
    delivered = np.zeros_like(requested)
    clipped = np.zeros(requested.shape, np.int64)
    for t in range(late):
        noise = base.paired_founders(stream.standard_normal((2, R, 2, 16, 16)))[None, None]
        v = reader.compensated_step(v, effective[:, None, :, :, None],
            d[:, None, :, :, None], noise, config, t >= cfg['body_settling_steps'])
        if before <= t < early:
            increment = cfg['dt'] * cfg['pulse_amplitude'] * field[None, :, :, None]
            proposed = v[:, 1] + increment
            actual = np.clip(proposed, -2., 2.)
            requested += np.broadcast_to(increment * increment, v[:, 1].shape).sum(axis=(-2, -1))
            delivered += ((actual - v[:, 1])**2).sum(axis=(-2, -1))
            clipped += (abs(proposed) > 2.).sum(axis=(-2, -1))
            v[:, 1] = actual
        v *= live
        v[..., P[0]] = cue
        hashes.append(state_hash(v))
        for j, boundary in enumerate(boundaries):
            if boundary - cfg['observe_steps'] <= t < boundary:
                windows[j].append(np.stack([v[..., P[q]].mean(axis=-1) for q in (1, 2)], axis=-1))
            if t + 1 == boundary:
                states.append(v.copy())
    windows = np.stack([np.stack(w, axis=2) for w in windows], axis=2)
    return dict(masks=masks, available=available, effective=effective, denominator=d,
        coupling=k, birth=birth, initial=initial, pulse_field=field, pulse_sites=selected,
        requested_squared=requested, delivered_squared=delivered, clipping_count=clipped,
        states=np.stack(states, axis=2), port_windows=windows, mean_ports=windows.mean(axis=3),
        state_hashes=np.stack(hashes))


def capture(state, available, beta):
    """State ends F,R,C,Y,X; no incoming record or task targets enter."""
    x = np.tanh(beta * state)
    difference = (x[..., 0, :, :] - x[..., 1, :, :]) / 2
    contrast = np.stack((difference*np.roll(difference, -1, -1),
                         difference*np.roll(difference, -1, -2)), axis=-3)
    ordinary = base.correlations(state, beta).mean(axis=-4)
    fallback = contrast == 0.
    outgoing = np.where(available, np.where(fallback, ordinary, contrast), 0.)
    return outgoing, ordinary, contrast, fallback & available


def transmit(body, cfg):
    H, F, R = body['effective'].shape[:3]
    weights = np.zeros((H, len(ARMS), F, R, 2, 16, 16))
    ordinary = np.zeros_like(weights[:, :4])
    contrast = np.zeros_like(ordinary)
    fallback = np.zeros(ordinary.shape, bool)
    for a, (p, t) in enumerate(((0, 1), (1, 1), (0, 2), (1, 2))):
        weights[:, a], ordinary[:, a], contrast[:, a], fallback[:, a] = capture(
            body['states'][:, p, t], body['available'], cfg['writer_beta'])
    weights[:, 4] = body['effective']
    weights[:, 5] = body['effective']
    return dict(packets=base.encode(weights), ordinary=ordinary, contrast=contrast,
                fallback=fallback)


def assay(packets, block, cfg):
    """Only packet bytes and common public reader conditions enter."""
    H, A, F, R = packets.shape[:4]
    weights = base.decode(packets).reshape(H*A, F, R, 2, 16, 16)
    config = base.Config(recipients=R, dt=cfg['dt'], noise=cfg['noise'])
    masks = base.damage_masks(block, 'E055_fresh_reader', config)
    effective = weights[:, :, :, None] * reader.surviving_edges(masks)[None]
    d, k = coupling(effective)
    stream = rng('E055', block, 'fresh_reader')
    birth = cfg['birth_sd'] * base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (H*A, F, R, 2, 3, 16, 16)).copy()
    live = (~masks)[None, :, :, None]
    cue = base.CUES.reshape(1, 1, 1, 2, 1, 1)
    v *= live
    v[..., P[0]] = cue
    trace = []
    hashes = []
    for t in range(cfg['read_steps']):
        noise = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        v = reader.compensated_step(v, effective[:, :, :, None], d[:, :, :, None],
                                   noise, config, t >= cfg['settling_steps'])
        v *= live
        v[..., P[0]] = cue
        hashes.append(state_hash(v))
        if t >= cfg['read_steps'] - cfg['observe_steps']:
            trace.append(np.stack([v[..., P[q]].mean(axis=-1) for q in (1, 2)], axis=-1))
    trace = np.stack(trace)
    return dict(masks=masks, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.stack(hashes))


def score(v, margin):
    """Any panel prefix followed by F,R,C,output; targets enter scoring only."""
    target = base.RULES.reshape((1,)*(v.ndim-4)+(4, 1, 1)) * base.CUES
    m = np.minimum(target*v[..., 0], -target*v[..., 1])
    transfer = ((v[..., 0, 0]-v[..., 1, 0])-(v[..., 0, 1]-v[..., 1, 1]))/4
    return dict(margin=m, minimum_margin=m.min(axis=-1), both=(m > margin).all(axis=-1),
        transfer=transfer, aligned_transfer=transfer*base.RULES.reshape((1,)*(transfer.ndim-2)+(4, 1)))


def diagnostics(body, outgoing, fresh, cfg):
    weights = base.decode(outgoing['packets'])
    H, A, F, R = weights.shape[:4]
    d, k = coupling(weights)
    reference = np.array([0, 0, 2, 2, 4, 4, 6])
    w0 = weights[:, reference]
    common = (weights != 0) & (w0 != 0)
    edges = (-3, -2, -1)
    measure = dict(shared_support=common.sum(axis=edges),
        sign_disagreements=(common & (np.sign(weights) != np.sign(w0))).sum(axis=edges),
        support_gained=((weights != 0) & (w0 == 0)).sum(axis=edges),
        support_lost=((weights == 0) & (w0 != 0)).sum(axis=edges),
        coupling_l1=abs(k-k[:, reference]).sum(axis=edges)/256,
        denominator_l1=abs(d-d[:, reference]).sum(axis=(-2, -1))/256,
        graph=graph_batch(weights), denominator=d, coupling=k)
    ports = fresh['mean_ports'].reshape(H, A, F, R, 2, 3, 2)
    end = fresh['end'].reshape(H, A, F, R, 2, 3, 16, 16)
    windows = fresh['late_ports'].reshape(cfg['observe_steps'], H, A, F, R, 2, 3, 2)
    controls = dict(before_equal=bool(np.array_equal(body['states'][:, 0, 0], body['states'][:, 1, 0])),
        protected_packets_equal=bool(np.array_equal(outgoing['packets'][:, 4], outgoing['packets'][:, 5])),
        protected_end_equal=bool(np.array_equal(end[:, 4], end[:, 5])),
        protected_traces_equal=bool(np.array_equal(windows[:, :, 4], windows[:, :, 5])),
        pulse_excludes_ports=bool(not body['pulse_sites'][..., P.any(axis=0)].any()),
        pulse_excludes_absent=bool(not (body['pulse_sites'] & body['masks']).any()),
        pulse_site_count=bool((body['pulse_sites'].sum(axis=(-2, -1)) == cfg['pulse_sites']).all()))
    controls['pass'] = all(controls.values())
    fresh_scores = score(ports.transpose(0, 1, 5, 2, 3, 4, 6), cfg['margin'])
    body_scores = score(body['mean_ports'], cfg['margin'])
    cases = {f'fresh_{k}': v for k, v in fresh_scores.items()}
    cases.update({f'body_{k}': v for k, v in body_scores.items()})
    cases.update(measure)
    cases['fallback_count'] = outgoing['fallback'].sum(axis=edges)
    cases['body_state_distance'] = abs(body['states'][:, 1]-body['states'][:, 0]).mean(axis=(-3, -2, -1))
    for key in ('requested_squared', 'delivered_squared', 'clipping_count'):
        cases['pulse_'+key] = body[key].mean(axis=-1)
    return cases, controls
