"""Independent source, pulse, dynamics, writer, diagnostics and score replay."""
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from E015_functional_inheritance.audit import random, pair, unpack, pack, ports
from E022_reader_compensation.audit import advance_compensated
from E054_record_interventions.audit_model import coupling, graph_batch, equal
import numpy as np

P = ports()


def source(run, block):
    with np.load(run/f'source_{block:06d}.npz', allow_pickle=False) as f:
        acquired = unpack(f['acquired'][1])
    with np.load(run/f'boundary_{block:06d}_g32.npz', allow_pickle=False) as f:
        last = f['outgoing']; masks = f['masks']
    R = last.shape[2]
    records = np.empty((3, 4, R, 2, 16, 16))
    records[0] = acquired[:, None]
    records[1] = unpack(last[0])
    records[2] = unpack(last[20])
    return dict(records=records, source_last_masks=masks)


def masks(block, R, phase):
    eligible = np.flatnonzero(~P.any(axis=0).ravel())
    squares = []
    for y, x in np.ndindex(16, 16):
        a = np.zeros((16, 16), bool)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1): a[(y+dy)%16, (x+dx)%16] = True
        if not (a & P.any(axis=0)).any(): squares.append(a)
    stream = random('E015', block, phase, 'damage')
    out = np.zeros((2, R, 3, 16, 16), bool)
    for f, r in np.ndindex(2, R):
        out[f, r, 1].ravel()[stream.choice(eligible, 24, replace=False)] = True
        out[f, r, 2] = squares[int(stream.integers(len(squares)))]
    return pair(out)


def alive_edges(mask):
    out = np.empty(mask.shape[:-2]+(2, 16, 16), bool)
    for y, x in np.ndindex(16, 16):
        out[..., 0, y, x] = ~mask[..., y, x] & ~mask[..., y, (x+1)%16]
        out[..., 1, y, x] = ~mask[..., y, x] & ~mask[..., (y+1)%16, x]
    return out


def digest(x):
    return np.frombuffer(hashlib.sha256(np.asarray(x, dtype='<f8').tobytes(order='C')).digest(), dtype=np.uint8)


def develop(records, block, cfg):
    H, F, R = records.shape[:3]
    mask = masks(block, R, 'E055_current_body')[:, :, 1]
    available = alive_edges(mask)
    weights = records * available
    denominator, k = coupling(weights)
    pulse = np.zeros((F, R, 16, 16)); selected = np.zeros(pulse.shape, bool)
    for f, r in np.ndindex(2, R):
        g = random('E055', block, 'pulse_field', f, r)
        choices = np.array([i for i in range(256) if not mask[2*f, r].ravel()[i]
                            and not P.any(axis=0).ravel()[i]])
        ids = g.choice(choices, cfg['pulse_sites'], replace=False)
        values = g.choice(np.array([-1., 1.]), cfg['pulse_sites'])
        for member in (2*f, 2*f+1):
            pulse[member, r].ravel()[ids] = values
            selected[member, r].ravel()[ids] = True
    g = random('E055', block, 'current_body')
    birth = cfg['birth_sd'] * pair(g.standard_normal((2, R, 16, 16)))
    v = np.broadcast_to(birth[None, None, :, :, None], (H, 2, F, R, 2, 16, 16)).copy()
    live = (~mask)[None, None, :, :, None]
    cues = np.array([1., -1.]).reshape(1, 1, 1, 1, 2, 1)
    v *= live; v[..., P[0]] = cues; initial = v.copy()
    first = cfg['body_pre_steps']; second = first + cfg['pulse_steps']
    last = second + cfg['recovery_steps']; endpoints = (first, second, last)
    traces = [[], [], []]; snapshots = []; state_hashes = []
    requested = np.zeros((H, F, R, 2)); delivered = np.zeros_like(requested)
    clipped = np.zeros(requested.shape, np.int64)
    for t in range(last):
        eta = pair(g.standard_normal((2, R, 2, 16, 16)))[None, None]
        v = advance_compensated(v, weights[:, None, :, :, None], denominator[:, None, :, :, None],
                               eta, cfg, t >= cfg['body_settling_steps'])
        if first <= t < second:
            force = cfg['dt'] * cfg['pulse_amplitude'] * pulse[None, :, :, None]
            proposal = v[:, 1] + force
            updated = np.minimum(2., np.maximum(-2., proposal))
            requested += np.broadcast_to(force**2, v[:, 1].shape).sum(axis=(-2, -1))
            delivered += ((updated-v[:, 1])**2).sum(axis=(-2, -1))
            clipped += ((proposal < -2.) | (proposal > 2.)).sum(axis=(-2, -1))
            v[:, 1] = updated
        v *= live; v[..., P[0]] = cues
        state_hashes.append(digest(v))
        for j, end in enumerate(endpoints):
            if end-cfg['observe_steps'] <= t < end:
                traces[j].append(np.stack((v[..., P[1]].mean(axis=-1), v[..., P[2]].mean(axis=-1)), axis=-1))
            if t == end-1: snapshots.append(v.copy())
    traces = np.stack([np.stack(x, axis=2) for x in traces], axis=2)
    return dict(masks=mask, available=available, effective=weights, denominator=denominator,
        coupling=k, birth=birth, initial=initial, pulse_field=pulse, pulse_sites=selected,
        requested_squared=requested, delivered_squared=delivered, clipping_count=clipped,
        states=np.stack(snapshots, axis=2), port_windows=traces, mean_ports=traces.mean(axis=3),
        state_hashes=np.array(state_hashes))


def transmit(body, cfg):
    H, F, R = body['effective'].shape[:3]
    outgoing = np.zeros((H, 7, F, R, 2, 16, 16))
    ordinary = np.empty((H, 4, F, R, 2, 16, 16))
    contrast = np.empty_like(ordinary); fallback = np.empty(ordinary.shape, bool)
    for a in range(4):
        state = body['states'][:, a % 2, 1+a//2]
        x = np.tanh(cfg['writer_beta']*state)
        d = (x[..., 0, :, :]-x[..., 1, :, :])/2
        for e, axis in enumerate((-1, -2)):
            ordinary[:, a, ..., e, :, :] = (x*np.roll(x, -1, axis)).mean(axis=-3)
            contrast[:, a, ..., e, :, :] = d*np.roll(d, -1, axis)
        zero = contrast[:, a] == 0.
        fallback[:, a] = zero & body['available']
        outgoing[:, a] = np.where(body['available'], np.where(zero, ordinary[:, a], contrast[:, a]), 0.)
    outgoing[:, 4] = body['effective']; outgoing[:, 5] = body['effective']
    return dict(packets=pack(outgoing), ordinary=ordinary, contrast=contrast, fallback=fallback)


def assay(packets, block, cfg):
    H, A, F, R = packets.shape[:4]
    w = unpack(packets).reshape(H*A, F, R, 2, 16, 16)
    mask = masks(block, R, 'E055_fresh_reader')
    effective = w[:, :, :, None] * alive_edges(mask)[None]
    d, k = coupling(effective)
    g = random('E055', block, 'fresh_reader')
    birth = cfg['birth_sd']*pair(g.standard_normal((2, R, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (H*A, F, R, 2, 3, 16, 16)).copy()
    live = (~mask)[None, :, :, None]
    cues = np.array([1., -1.]).reshape(1, 1, 1, 2, 1, 1)
    v *= live; v[..., P[0]] = cues
    trace = []; hashes = []
    for t in range(cfg['read_steps']):
        eta = pair(g.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        v = advance_compensated(v, effective[:, :, :, None], d[:, :, :, None], eta, cfg,
                                t >= cfg['settling_steps'])
        v *= live; v[..., P[0]] = cues
        hashes.append(digest(v))
        if t >= cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[..., P[1]].mean(axis=-1), v[..., P[2]].mean(axis=-1)), axis=-1))
    trace = np.array(trace)
    return dict(masks=mask, effective=effective, denominator=d, coupling=k, birth=birth,
        end=v, late_ports=trace, mean_ports=trace.mean(axis=0), state_hashes=np.array(hashes))


def score(v, margin):
    m = np.empty(v.shape[:-1]); transfer = np.empty(v.shape[:-2])
    rules = (1., -1., 1., -1.)
    for f, rule in enumerate(rules):
        for c, cue in enumerate((1., -1.)):
            m[..., f, :, c] = np.minimum(rule*cue*v[..., f, :, c, 0], -rule*cue*v[..., f, :, c, 1])
        transfer[..., f, :] = ((v[..., f, :, 0, 0]-v[..., f, :, 1, 0])-
                               (v[..., f, :, 0, 1]-v[..., f, :, 1, 1]))/4
    aligned = transfer.copy()
    for f, rule in enumerate(rules): aligned[..., f, :] *= rule
    return dict(margin=m, minimum_margin=m.min(axis=-1), both=(m > margin).all(axis=-1),
                transfer=transfer, aligned_transfer=aligned)


def diagnostics(body, outgoing, fresh, cfg):
    w = unpack(outgoing['packets']); H, A, F, R = w.shape[:4]
    d, k = coupling(w)
    ref = [0, 0, 2, 2, 4, 4, 6]; reference = w[:, ref]
    common = (w != 0) & (reference != 0)
    edges = (-3, -2, -1)
    measures = dict(shared_support=common.sum(axis=edges),
        sign_disagreements=(common & ((w < 0) != (reference < 0))).sum(axis=edges),
        support_gained=((w != 0) & (reference == 0)).sum(axis=edges),
        support_lost=((w == 0) & (reference != 0)).sum(axis=edges),
        coupling_l1=np.abs(k-k[:, ref]).sum(axis=edges)/256,
        denominator_l1=np.abs(d-d[:, ref]).sum(axis=(-2, -1))/256,
        graph=graph_batch(w), denominator=d, coupling=k)
    values = fresh['mean_ports'].reshape(H, A, F, R, 2, 3, 2)
    fields = fresh['end'].reshape(H, A, F, R, 2, 3, 16, 16)
    windows = fresh['late_ports'].reshape(cfg['observe_steps'], H, A, F, R, 2, 3, 2)
    checks = dict(before_equal=bool(np.array_equal(body['states'][:, 0, 0], body['states'][:, 1, 0])),
        protected_packets_equal=bool(np.array_equal(outgoing['packets'][:, 4], outgoing['packets'][:, 5])),
        protected_end_equal=bool(np.array_equal(fields[:, 4], fields[:, 5])),
        protected_traces_equal=bool(np.array_equal(windows[:, :, 4], windows[:, :, 5])),
        pulse_excludes_ports=bool(not body['pulse_sites'][..., P.any(axis=0)].any()),
        pulse_excludes_absent=bool(not (body['pulse_sites'] & body['masks']).any()),
        pulse_site_count=bool(np.all(body['pulse_sites'].sum(axis=(-2, -1)) == cfg['pulse_sites'])))
    checks['pass'] = all(checks.values())
    result = {f'fresh_{key}': a for key, a in score(values.transpose(0, 1, 5, 2, 3, 4, 6), cfg['margin']).items()}
    result.update({f'body_{key}': a for key, a in score(body['mean_ports'], cfg['margin']).items()})
    result.update(measures)
    result['fallback_count'] = outgoing['fallback'].sum(axis=edges)
    result['body_state_distance'] = np.abs(body['states'][:, 1]-body['states'][:, 0]).mean(axis=(-3, -2, -1))
    for name in ('requested_squared', 'delivered_squared', 'clipping_count'):
        result['pulse_'+name] = body[name].mean(axis=-1)
    return result, checks
