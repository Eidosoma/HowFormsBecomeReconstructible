"""Fixed cue-correlation perturbations of E041 rebuilding and its writer."""
from pathlib import Path
import hashlib
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E022_reader_compensation import model as renewal
import numpy as np

base, acquisition, Cycle = renewal.base, renewal.acquisition, renewal.Cycle
PAIRINGS = (('paired', 1., 1.), ('noise_0999', 1., .999),
    ('noise_099', 1., .99), ('noise_09', 1., .9), ('noise_0', 1., 0.),
    ('reset_099', .99, 1.), ('reset_0', 0., 1.))
WRITERS = ('exact_rewrite', 'tolerance_rewrite', 'ordinary_rewrite',
    'contrast_rewrite', 'exact_preserve')
CONDITIONS = tuple(f'{p[0]}/{w}' for p in PAIRINGS for w in WRITERS)
HORIZONS = (8, 16, 24, 32)
TAU = 1e-4
COUNTS = ('available_edges', 'exact_zero_available', 'ordinary_selected_available',
    'returning_edges', 'exact_zero_returning', 'ordinary_selected_returning',
    'nonzero_outgoing_returning', 'strong_outgoing_returning',
    'zero_incoming_available', 'new_nonzero_available', 'returning_cells',
    'returning_reachable_before', 'returning_reachable_after')
SUMS = ('absolute_outgoing_returning', 'absolute_contrast_returning')


def paired_draw(z, e, rhos):
    """S,F,R,C,Y,X; rho1 takes the exact original branch, without arithmetic."""
    first = base.paired_founders(z)
    return np.stack([np.stack((first, first.copy() if rho == 1. else
        base.paired_founders(rho*z+np.sqrt(1.-rho*rho)*e)), axis=2) for rho in rhos])


def ordinary_mask(contrast, writer):
    if writer in ('exact_rewrite', 'exact_preserve'): return contrast == 0.
    if writer == 'tolerance_rewrite': return abs(contrast) <= TAU
    if writer == 'ordinary_rewrite': return np.ones(contrast.shape, bool)
    assert writer == 'contrast_rewrite'
    return np.zeros(contrast.shape, bool)


def capture(body, beta):
    ordinary = base.correlations(body, beta).mean(axis=3)
    x = np.tanh(beta*body); difference = (x[:, :, :, 0]-x[:, :, :, 1])/2
    contrast = np.stack((difference*np.roll(difference, -1, -1),
        difference*np.roll(difference, -1, -2)), axis=-3)
    selected = np.empty_like(contrast); use_ordinary = np.zeros(contrast.shape, bool)
    for n, name in enumerate(CONDITIONS):
        writer = name.split('/')[1]
        use_ordinary[n] = ordinary_mask(contrast[n], writer)
        selected[n] = np.where(use_ordinary[n], ordinary[n], contrast[n])
    return selected, contrast, use_ordinary


def select(incoming, computed, available):
    retain = np.zeros_like(computed, bool)
    for n, name in enumerate(CONDITIONS):
        if name.endswith('/exact_preserve'): retain[n] = available & (abs(incoming[n]) > .5)
    return np.where(available, np.where(retain, incoming, computed), 0.), retain


def reachable(weights):
    edges = weights != 0.; h, v = edges[..., 0, :, :], edges[..., 1, :, :]
    reached = np.broadcast_to(base.PORTS[0], weights.shape[:-3]+(16, 16)).copy()
    for _ in range(256):
        new = (reached | (h & np.roll(reached, -1, -1)) |
            (np.roll(h, 1, -1) & np.roll(reached, 1, -1)) |
            (v & np.roll(reached, -1, -2)) |
            (np.roll(v, 1, -2) & np.roll(reached, 1, -2)))
        if np.array_equal(new, reached): return reached
        reached = new
    raise AssertionError('Connectivity failed to converge')


def diagnostics(old, outgoing, available, mask, previous_mask, contrast, ordinary):
    returning = previous_mask & ~mask
    incident = np.stack((returning | np.roll(returning, -1, -1),
        returning | np.roll(returning, -1, -2)), axis=-3) & available
    shape = outgoing.shape
    av = np.broadcast_to(available, shape); rr = np.broadcast_to(incident, shape)
    rc = np.broadcast_to(returning, outgoing.shape[:-3]+(16, 16))
    count_edges = lambda x: x.sum(axis=(-3, -2, -1), dtype=np.int64)
    count_cells = lambda x: x.sum(axis=(-2, -1), dtype=np.int64)
    counts = np.stack((count_edges(av), count_edges(av & (contrast == 0)),
        count_edges(av & ordinary), count_edges(rr), count_edges(rr & (contrast == 0)),
        count_edges(rr & ordinary), count_edges(rr & (outgoing != 0)),
        count_edges(rr & (abs(outgoing) > .5)), count_edges(av & (old == 0)),
        count_edges(av & (old == 0) & (outgoing != 0)), count_cells(rc),
        count_cells(rc & reachable(old)), count_cells(rc & reachable(outgoing))), axis=-1)
    sums = np.stack(((abs(outgoing)*rr).sum(axis=(-3, -2, -1)),
        (abs(contrast)*rr).sum(axis=(-3, -2, -1))), axis=-1)
    return counts, sums


def rebuild(incoming, block, generation, previous_mask, cfg, cycle):
    N, R = len(CONDITIONS), cfg.recipients
    assert incoming.shape == (N, 4, R, 4096) and 1 <= generation <= 32
    masks = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    available = renewal.surviving_edges(masks)
    effective = base.decode(incoming)*available
    denominator = renewal.incident_sum(abs(effective))
    stream, innovation = rng('E022', block, 'develop', generation), rng('E051', block, 'innovation', generation)
    shape = (2, R, 16, 16)
    birth = cfg.birth_sd*paired_draw(stream.standard_normal(shape), innovation.standard_normal(shape), [p[1] for p in PAIRINGS])
    v = np.repeat(birth, len(WRITERS), axis=0)
    alive = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1, 1, 1, 2, 1)
    v *= alive; v[..., base.PORTS[0]] = cue
    late = []; moments = np.zeros((len(PAIRINGS), 6))
    for t in range(cycle.read_steps):
        noise = paired_draw(stream.standard_normal(shape), innovation.standard_normal(shape), [p[2] for p in PAIRINGS])
        a, b = noise[:, :, :, 0], noise[:, :, :, 1]
        for k, value in enumerate((a, b, a*a, b*b, a*b)):
            moments[:, k] += value.sum(axis=(1, 2, 3, 4))
        moments[:, 5] += a[0].size
        v = renewal.compensated_step(v, effective[:, :, :, None], denominator[:, :, :, None],
            np.repeat(noise, len(WRITERS), axis=0), cfg, amplification=t >= cycle.settling_steps)
        v *= alive; v[..., base.PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            late.append(np.stack((v[..., base.PORTS[1]].mean(axis=-1), v[..., base.PORTS[2]].mean(axis=-1)), axis=-1))
    end = v.copy(); late = np.stack(late)
    computed, contrast, ordinary = capture(end, cfg.writer_beta)
    outgoing, retained = select(effective, computed, available)
    counts, sums = diagnostics(effective, outgoing, available, masks, previous_mask, contrast, ordinary)
    stream = rng('E022', block, 'write', generation)
    hashes = np.empty((cycle.write_steps, N, 32), np.uint8)
    scaffold = available[None, :, :, None].astype(float)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal(shape))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= alive; v[..., base.PORTS[0]] = cue
        for n in range(N):
            hashes[t, n] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[n], dtype='<f8').tobytes()).digest(), np.uint8)
    return dict(incoming=incoming.copy(), masks=masks, effective_packets=base.encode(effective),
        denominator=denominator, birth=birth, end=end, late_ports=late, mean_ports=late.mean(axis=0),
        computed_packets=base.encode(computed), outgoing=base.encode(outgoing), retained=retained,
        noise_moments=moments, counts=counts, sums=sums, write_end=v, write_state_hashes=hashes)


def assay(records, block, horizon, cfg, cycle):
    """Original normalized own-record assay, plus one shared erased packet."""
    records = np.concatenate((records, np.zeros_like(records[:1])), axis=0)
    N, R = len(records), cfg.recipients
    masks = base.damage_masks(block, f'E022_h{horizon}', cfg)
    available = renewal.surviving_edges(masks)
    effective = base.decode(records)[:, :, :, None]*available[None]
    denominator = renewal.incident_sum(abs(effective))
    stream = rng('E022', block, 'assay', horizon)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (N, 4, R, 2, 3, 16, 16)).copy()
    alive = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1, 1, 1, 2, 1, 1)
    v *= alive; v[..., base.PORTS[0]] = cue; late = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        v = renewal.compensated_step(v, effective[:, :, :, None], denominator[:, :, :, None], noise, cfg,
            amplification=t >= cycle.settling_steps)
        v *= alive; v[..., base.PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            late.append(np.stack((v[..., base.PORTS[1]].mean(axis=-1), v[..., base.PORTS[2]].mean(axis=-1)), axis=-1))
    late = np.stack(late)
    return dict(records=records, masks=masks, effective_packets=base.encode(effective),
        denominator=denominator, birth=birth, end=v, late_ports=late, mean_ports=late.mean(axis=0))


def score(values, cfg):
    assert values.shape[1] == 4 and values.shape[3] == 2 and values.shape[-1] == 2
    extra = (1,)*(values.ndim-5)
    target = base.RULES.reshape(1, 4, 1, 1, *extra)*base.CUES.reshape(1, 1, 1, 2, *extra)
    a, b = target*values[..., 0], -target*values[..., 1]
    return dict(correct=(a > cfg.margin) & (b > cfg.margin), margin=np.minimum(a, b), ports=values)
