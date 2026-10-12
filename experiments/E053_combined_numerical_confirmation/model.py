"""Typed rebuilding, one transmission channel per generation, dual readers."""
from pathlib import Path
import hashlib
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E051_cue_pairing_robustness import model as legacy
from E053_combined_numerical_confirmation.design import *
import numpy as np

base, acquisition, renewal, Cycle = legacy.base, legacy.acquisition, legacy.renewal, legacy.Cycle
N = len(CONDITIONS)
GROUPS = tuple((dtype, np.array([n for n in range(N) if
    REGIMES[n % len(REGIMES)]['arithmetic'] == dtype], dtype=int)) for dtype in ('float64', 'float32'))


def typed_step(v, w, denominator, noise, cfg, amplification, floor):
    dtype = v.dtype.type
    assert w.dtype == denominator.dtype == noise.dtype == v.dtype
    effective_d = np.where(denominator > 0, np.maximum(denominator, np.asarray(floor, dtype=v.dtype)), dtype(0))
    if v.dtype == np.float64:
        return renewal.compensated_step(v, w, effective_d, noise, cfg, amplification)
    incoming = base.neighbor_sum(v, w)
    local = np.divide(incoming, effective_d, out=np.zeros_like(incoming), where=denominator > 0)
    drift = (v - v**3 if amplification else -v**3) + dtype(2) * (local - v)
    out = np.clip(v + dtype(cfg.dt) * drift + dtype(cfg.noise) * noise, dtype(-2), dtype(2))
    assert out.dtype == v.dtype
    return out


def capture(v, beta):
    dtype = v.dtype.type
    x = np.tanh(dtype(beta) * v)
    d = (x[:, :, :, 0] - x[:, :, :, 1]) / dtype(2)
    q = np.stack((d * np.roll(d, -1, -1), d * np.roll(d, -1, -2)), axis=-3)
    c = np.stack((x * np.roll(x, -1, -1), x * np.roll(x, -1, -2)), axis=-3).mean(axis=3)
    used = q == dtype(0)
    chosen = np.where(used, c, q)
    underflow = np.stack(((d != 0) & (np.roll(d, -1, -1) != 0),
                          (d != 0) & (np.roll(d, -1, -2) != 0)), axis=-3) & used
    tiny = np.finfo(v.dtype).tiny
    edges = lambda a: a.sum(axis=(-3, -2, -1), dtype=np.int64)
    fields = (edges(q != 0), edges(underflow),
              ((abs(x) > 0) & (abs(x) < tiny)).sum(axis=(-3, -2, -1), dtype=np.int64),
              edges((abs(q) > 0) & (abs(q) < tiny)),
              edges((abs(chosen) > 0) & (abs(chosen) < tiny)))
    assert chosen.dtype == q.dtype == v.dtype
    return chosen, q, used, np.stack(fields, axis=-1)


def channel(pre, available, block, generation):
    """One shared independent draw per reciprocal edge; no change on identity arms."""
    assert pre.shape[0] == N and 0 <= generation <= 32
    old = base.decode(pre)
    z = base.paired_founders(rng('E052', block, 'record_noise', generation)
                            .standard_normal((2, old.shape[2], 2, 16, 16)))
    out = old.copy(); noise_stage = old.copy(); grid_stage = old.copy(); counts = []; sums = []
    av = np.broadcast_to(available, old.shape[1:])
    for n in range(N):
        r = REGIMES[n % len(REGIMES)]; w = old[n]; new = w.copy(); clipped = np.zeros_like(av)
        if r['record_noise_sd']:
            selected = av & ((w != 0) if r['record_noise_support'] == 'nonzero_available' else True)
            candidate = w + r['record_noise_sd'] * z
            clipped = selected & ((candidate < -1.) | (candidate > 1.))
            new[selected] = np.clip(candidate[selected], -1., 1.)
        noise_stage[n] = new
        if r['grid_step']:
            delta = r['grid_step']; new = delta * np.rint(new / delta)
        grid_stage[n] = new
        if r['record_precision'] == 'float32':
            new = new.astype(np.float32).astype(np.float64)
        # Identity branch preserves the bytes of the already-masked pre-channel packet.
        assert not w[~av].any()
        new[~av] = 0.
        if not (r['record_precision'] == 'float32' or r['grid_step'] or r['record_noise_sd']):
            new = w.copy()
        out[n] = new
        tiny = np.finfo(r['record_precision']).tiny
        fields = (av, av & (w != 0), av & (new != 0), av & (w != 0) & (new == 0),
                  av & (w == 0) & (new != 0), av & (w != 0) & (new != 0) & (np.signbit(w) != np.signbit(new)), clipped,
                  av & (abs(w) > 0) & (abs(w) < tiny), av & (abs(new) > 0) & (abs(new) < tiny),
                  av & (noise_stage[n] != 0) & (grid_stage[n] == 0), av & (grid_stage[n] != 0) & (new == 0))
        counts.append(np.stack([a.sum(axis=(-3, -2, -1), dtype=np.int64) for a in fields], axis=-1))
        err = new - w
        sums.append(np.stack((abs(err).sum(axis=(-3, -2, -1)), (err * err).sum(axis=(-3, -2, -1)),
                              abs(err).max(axis=(-3, -2, -1))), axis=-1))
    return dict(pre_channel=pre.copy(), outgoing=base.encode(out), channel_noise=z,
                channel_counts=np.stack(counts), channel_sums=np.stack(sums),
                after_noise=base.encode(noise_stage), after_grid=base.encode(grid_stage))


def initial(acquired, block, cfg):
    packets = np.repeat(np.repeat(acquired[:, None], cfg.recipients, axis=1)[None], N, axis=0)
    return channel(packets, np.ones((4, cfg.recipients, 2, 16, 16), bool), block, 0)


def observations(v):
    return np.stack((v[..., base.PORTS[1]].mean(axis=-1, dtype=np.float64),
                     v[..., base.PORTS[2]].mean(axis=-1, dtype=np.float64)), axis=-1)


def numerical_diagnostics(old, denominator, mask, previous_tags):
    live = np.broadcast_to((~mask & ~base.PORTS[0])[None], denominator.shape)
    eps = np.array([REGIMES[n % len(REGIMES)]['denominator_floor'] for n in range(N)])[:, None, None, None, None]
    tiny = np.array([np.finfo(REGIMES[n % len(REGIMES)]['arithmetic']).tiny for n in range(N)])[:, None, None, None, None]
    positive = live & (denominator > 0)
    attenuation = np.divide(denominator, np.maximum(denominator, eps),
                            out=np.zeros_like(denominator), where=denominator > 0)
    count = lambda x: x.sum(axis=(-2, -1), dtype=np.int64)
    dcounts = np.stack([count(x) for x in (live, live & (denominator == 0), positive,
        positive & (denominator < eps), positive & (denominator < tiny))], axis=-1)
    dsums = np.stack((np.where(positive, denominator, 0).sum(axis=(-2, -1)),
                      np.where(positive, attenuation, 0).sum(axis=(-2, -1))), axis=-1)
    hist = np.stack([count(positive & (denominator > low) & (denominator <= high))
                    for low, high in zip(DENOM_BINS[:-1], DENOM_BINS[1:])], axis=-1)
    available = renewal.surviving_edges(mask)[None]
    surviving = previous_tags & available
    nonzero = surviving & (old != 0)
    exposed = (renewal.incident_sum(surviving.astype(np.int64)) > 0) & live
    tagged_strength = renewal.incident_sum(abs(old) * surviving)
    # Offline diagnostic uses a float64 strength sum, independently of typed dynamics.
    strength64 = renewal.incident_sum(abs(old))
    fraction = np.divide(tagged_strength, strength64, out=np.zeros_like(strength64), where=strength64 > 0)
    edges = lambda x: x.sum(axis=(-3, -2, -1), dtype=np.int64)
    rcounts = np.stack((edges(previous_tags), edges(surviving), edges(nonzero),
                       count(exposed & (strength64 > 0)), count(exposed & (strength64 == 0))), axis=-1)
    rsums = np.stack(((abs(old) * surviving).sum(axis=(-3, -2, -1)),
                      np.where(exposed, fraction, 0).sum(axis=(-2, -1))), axis=-1)
    return dict(attenuation=attenuation, denom_counts=dcounts, denom_sums=dsums, denom_hist=hist,
                repair_counts=rcounts, repair_sums=rsums, repair_fraction=fraction)


def rebuild(incoming, block, generation, previous_mask, previous_tags, cfg, cycle):
    R = cfg.recipients
    masks = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    available = renewal.surviving_edges(masks)
    decoded = base.decode(incoming) * available
    stream, innovation = rng('E022', block, 'develop', generation), rng('E051', block, 'innovation', generation)
    shape = (2, R, 16, 16)
    z, e = stream.standard_normal(shape), innovation.standard_normal(shape)
    unit_birth = legacy.paired_draw(z, e, [1.] * len(PAIRINGS))
    groups = []
    denominator = np.empty((N, 4, R, 16, 16)); birth = np.empty((N, 4, R, 2, 16, 16))
    alive = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1, 1, 1, 2, 1)
    for kind, ids in GROUPS:
        dtype = np.dtype(kind).type
        w = decoded[ids].astype(dtype); d = renewal.incident_sum(abs(w))
        b = dtype(cfg.birth_sd) * unit_birth[ids // len(REGIMES)].astype(dtype)
        v = b.copy(); v *= alive; v[..., base.PORTS[0]] = cue.astype(dtype)
        floor = np.array([REGIMES[n % len(REGIMES)]['denominator_floor'] for n in ids], dtype=dtype)[:, None, None, None, None, None]
        groups.append(dict(ids=ids, v=v, w=w[:, :, :, None], d=d[:, :, :, None], floor=floor))
        denominator[ids] = d; birth[ids] = b
    trace = []; moments = np.zeros((len(PAIRINGS), 6))
    for t in range(cycle.read_steps):
        noise = legacy.paired_draw(stream.standard_normal(shape), innovation.standard_normal(shape), [p[1] for p in PAIRINGS])
        a, b = noise[:, :, :, 0], noise[:, :, :, 1]
        for k, term in enumerate((a, b, a * a, b * b, a * b)):
            moments[:, k] += term.sum(axis=(1, 2, 3, 4))
        moments[:, 5] += a[0].size
        obs = np.empty((N, 4, R, 2, 2)) if t >= cycle.read_steps - cfg.observe_steps else None
        for group in groups:
            ids, v = group['ids'], group['v']
            v = typed_step(v, group['w'], group['d'], noise[ids // len(REGIMES)].astype(v.dtype), cfg,
                           t >= cycle.settling_steps, group['floor'])
            v *= alive; v[..., base.PORTS[0]] = cue.astype(v.dtype); group['v'] = v
            if obs is not None: obs[ids] = observations(v)
        if obs is not None: trace.append(obs)
    end = np.empty((N, 4, R, 2, 16, 16)); computed = np.empty((N, 4, R, 2, 16, 16))
    contrast = np.empty_like(computed); used = np.empty(computed.shape, bool)
    cc = np.empty((N, 4, R, len(CAPTURE_COUNTS)), np.int64)
    effective = np.empty_like(decoded)
    for group in groups:
        ids, v = group['ids'], group['v']; end[ids] = v
        a, b, c, d = capture(v, cfg.writer_beta)
        computed[ids], contrast[ids], used[ids], cc[ids] = a, b, c, d
        effective[ids] = group['w'][:, :, :, 0]
    before = np.where(available, computed, 0.)
    counts, sums = legacy.diagnostics(effective, before, available, masks, previous_mask, contrast, used)
    returning = previous_mask & ~masks
    incident = np.stack((returning | np.roll(returning, -1, -1), returning | np.roll(returning, -1, -2)), axis=-3) & available
    repair_tags = incident[None] & (effective == 0) & (before != 0)
    diagnostics = numerical_diagnostics(effective, denominator, masks, previous_tags)
    v = end.copy(); stream = rng('E022', block, 'write', generation)
    scaffold = available[None, :, :, None].astype(float)
    hashes = np.empty((cycle.write_steps, N, 32), np.uint8)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal(shape))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg); v *= alive; v[..., base.PORTS[0]] = cue
        for n in range(N):
            hashes[t, n] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[n], dtype='<f8').tobytes()).digest(), np.uint8)
    transmitted = channel(base.encode(before), available, block, generation)
    trace = np.stack(trace)
    return dict(incoming=incoming.copy(), masks=masks, effective_packets=base.encode(effective),
                denominator=denominator, birth=birth, end=end, late_ports=trace, mean_ports=trace.mean(axis=0),
                computed_packets=base.encode(computed), counts=counts, sums=sums, capture_counts=cc,
                repair_tags=repair_tags, noise_moments=moments, write_end=v, write_state_hashes=hashes,
                **diagnostics, **transmitted)


def assay(records, acquired, block, horizon, cfg, cycle):
    panels, mapping = assay_layout(horizon)
    packets = np.stack([records[n] if n >= 0 else np.zeros_like(records[0]) if n == -1 else acquired
                        for n, reader in panels])
    P, R = len(panels), cfg.recipients
    masks = base.damage_masks(block, f'E022_h{horizon}', cfg)
    decoded = base.decode(packets)[:, :, :, None] * renewal.surviving_edges(masks)[None]
    stream = rng('E022', block, 'assay', horizon)
    unit = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))
    birth = np.empty((P, 4, R, 3, 16, 16)); denominator = np.empty((P, 4, R, 3, 16, 16))
    alive = (~masks)[None, :, :, None]; cue = base.CUES.reshape(1, 1, 1, 2, 1, 1)
    groups = []
    for kind in ('float64', 'float32'):
        ids = np.array([n for n, (_, r) in enumerate(panels) if READERS[r][0] == kind])
        dtype = np.dtype(kind).type; w = decoded[ids].astype(dtype); d = renewal.incident_sum(abs(w))
        b = dtype(cfg.birth_sd) * unit.astype(dtype)
        v = np.broadcast_to(b[None, :, :, None], (len(ids), 4, R, 2, 3, 16, 16)).copy()
        v *= alive; v[..., base.PORTS[0]] = cue.astype(dtype)
        floor = np.array([READERS[panels[n][1]][1] for n in ids], dtype=dtype)[:, None, None, None, None, None, None]
        groups.append(dict(ids=ids, v=v, w=w[:, :, :, None], d=d[:, :, :, None], floor=floor))
        birth[ids] = b; denominator[ids] = d
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        obs = np.empty((P, 4, R, 2, 3, 2)) if t >= cycle.read_steps - cfg.observe_steps else None
        for group in groups:
            ids, v = group['ids'], group['v']
            v = typed_step(v, group['w'], group['d'], noise.astype(v.dtype), cfg,
                           t >= cycle.settling_steps, group['floor'])
            v *= alive; v[..., base.PORTS[0]] = cue.astype(v.dtype); group['v'] = v
            if obs is not None: obs[ids] = observations(v)
        if obs is not None: trace.append(obs)
    end = np.empty((P, 4, R, 2, 3, 16, 16))
    for group in groups: end[group['ids']] = group['v']
    trace = np.stack(trace)
    return dict(records=packets, panels=np.array(panels, np.int64), masks=masks, birth=birth,
                denominator=denominator, end=end, late_ports=trace, mean_ports=trace.mean(axis=0))


score = legacy.score
