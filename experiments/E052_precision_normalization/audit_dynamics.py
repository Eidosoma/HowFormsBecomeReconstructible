"""Independent E052 numerical replay; imports auditors, never production dynamics."""
import hashlib
import numpy as np
from E015_functional_inheritance.audit import pair, pack, unpack, ports, random, advance
from E022_reader_compensation.audit import masks_for, source_record, advance_compensated
from E051_cue_pairing_robustness.audit import edges, mechanism, equal, equal_dict, load
from E052_precision_normalization.design import REGIMES, PAIRINGS, CONDITIONS, READERS

P = ports()
CUES = np.array([1., -1.])
N = 33


def layout(h):
    entries = []; mapped = []
    for n, name in enumerate(CONDITIONS):
        regime = REGIMES[n % 11]
        reader = READERS.index((regime['arithmetic'], regime['denominator_floor']))
        for role, r in [('native', reader), ('common', 0)]:
            if (n, r) not in entries: entries.append((n, r))
            mapped.append((name, role, entries.index((n, r))))
    entries.extend([(-1, k) for k in range(5)])
    if h == 0: entries.append((-2, 0))
    return tuple(entries), tuple(mapped)


def strength(w):
    a = abs(w); result = np.empty(w.shape[:-3] + (16, 16), dtype=w.dtype)
    for y, x in np.ndindex(16, 16):
        result[..., y, x] = ((a[..., 0, y, x] + a[..., 0, y, (x-1) % 16])
                            + a[..., 1, y, x]) + a[..., 1, (y-1) % 16, x]
    return result


def step(v, weights, d, noise, cfg, amplify, eps):
    t = v.dtype.type
    assert v.dtype == weights.dtype == d.dtype == noise.dtype
    divisor = np.maximum(d, np.asarray(eps, dtype=v.dtype))
    divisor = np.where(d == 0, t(0), divisor)
    if v.dtype == np.float64:
        return advance_compensated(v, weights, divisor, noise, cfg, amplify)
    h, vertical = weights[..., 0, :, :], weights[..., 1, :, :]
    incoming = h * np.roll(v, -1, -1)
    incoming = incoming + np.roll(h, 1, -1) * np.roll(v, 1, -1)
    incoming = incoming + vertical * np.roll(v, -1, -2)
    incoming = incoming + np.roll(vertical, 1, -2) * np.roll(v, 1, -2)
    u = np.zeros_like(v); np.divide(incoming, divisor, out=u, where=d != 0)
    local = v - v**3 if amplify else -v**3
    drift = local + t(2) * (u - v)
    result = np.clip(v + t(cfg['dt']) * drift + t(cfg['noise']) * noise, t(-2), t(2))
    assert result.dtype == v.dtype
    return result


def capture(v, beta):
    t = v.dtype.type; x = np.tanh(t(beta) * v); difference = (x[:, :, :, 0] - x[:, :, :, 1]) / t(2)
    shape = v.shape[:3] + (2, 16, 16)
    q, c = np.empty(shape, dtype=v.dtype), np.empty(shape, dtype=v.dtype)
    underflow = np.zeros(shape, bool)
    for direction, y, xx in np.ndindex(2, 16, 16):
        yy, nx = (y, (xx+1) % 16) if direction == 0 else ((y+1) % 16, xx)
        a, b = difference[..., y, xx], difference[..., yy, nx]
        q[..., direction, y, xx] = a * b
        total = np.zeros(v.shape[:3], dtype=v.dtype)
        total += x[:, :, :, 0, y, xx] * x[:, :, :, 0, yy, nx]
        total += x[:, :, :, 1, y, xx] * x[:, :, :, 1, yy, nx]
        total /= t(2)
        c[..., direction, y, xx] = total
        underflow[..., direction, y, xx] = (a != 0) & (b != 0) & (a * b == 0)
    use = q == 0; chosen = q.copy(); chosen[use] = c[use]
    tiny = np.finfo(v.dtype).tiny
    edge_count = lambda a: a.sum(axis=(-3, -2, -1), dtype=np.int64)
    counts = np.stack((edge_count(q != 0), edge_count(underflow),
        ((abs(x) > 0) & (abs(x) < tiny)).sum(axis=(-3, -2, -1), dtype=np.int64),
        edge_count((abs(q) > 0) & (abs(q) < tiny)),
        edge_count((abs(chosen) > 0) & (abs(chosen) < tiny))), axis=-1)
    return chosen, q, use, counts


def transmit(packets, available, block, g):
    raw = unpack(packets); out = raw.copy()
    noise = pair(random('E052', block, 'record_noise', g).standard_normal((2, raw.shape[2], 2, 16, 16)))
    av = np.broadcast_to(available, raw.shape[1:]); count = []; sums = []
    for n, name in enumerate(CONDITIONS):
        r = REGIMES[n % 11]; old = raw[n]; modified = old.copy(); clipped = np.zeros_like(av)
        if r['record_precision'] == 'float32': modified = np.asarray(old, np.float32).astype(np.float64)
        elif r['grid_step'] > 0:
            modified = np.rint(old / r['grid_step']) * r['grid_step']
        elif r['record_noise_sd'] > 0:
            eligible = av.copy()
            if r['record_noise_support'] == 'nonzero_available': eligible &= old != 0
            candidate = old + r['record_noise_sd'] * noise
            clipped = eligible & ((candidate > 1) | (candidate < -1))
            modified[eligible] = np.maximum(-1., np.minimum(1., candidate[eligible]))
        assert not old[~av].any()
        if r['record_precision'] == 'float32' or r['grid_step'] or r['record_noise_sd']:
            modified[~av] = 0.
        out[n] = modified
        tiny = np.finfo(r['record_precision']).tiny
        fields = (av, av & (old != 0), av & (modified != 0), av & (old != 0) & (modified == 0),
                  av & (old == 0) & (modified != 0),
                  av & (old != 0) & (modified != 0) & (np.signbit(old) != np.signbit(modified)), clipped,
                  av & (abs(old) > 0) & (abs(old) < tiny), av & (abs(modified) > 0) & (abs(modified) < tiny))
        count.append(np.stack([v.sum(axis=(-3, -2, -1), dtype=np.int64) for v in fields], axis=-1))
        error = modified - old
        sums.append(np.stack((np.abs(error).sum(axis=(-3, -2, -1)), (error**2).sum(axis=(-3, -2, -1)),
                               np.abs(error).max(axis=(-3, -2, -1))), axis=-1))
    return dict(pre_channel=packets.copy(), outgoing=pack(out), channel_noise=noise,
                channel_counts=np.array(count), channel_sums=np.array(sums))


def initialization(acquired, block, cfg):
    originals = acquired[:, None].repeat(cfg['recipients'], axis=1)
    packets = originals[None].repeat(N, axis=0)
    return transmit(packets, np.ones((4, cfg['recipients'], 2, 16, 16), bool), block, 0)


def observe(v):
    # Means use the common scoring type even for float32 body arrays.
    one = np.mean(v[..., P[1]], axis=-1, dtype=np.float64)
    two = np.mean(v[..., P[2]], axis=-1, dtype=np.float64)
    return np.stack((one, two), axis=-1)


def numerics(old, d, mask, tags):
    valid = np.broadcast_to((~mask & ~P[0])[None], d.shape)
    eps = np.array([REGIMES[n % 11]['denominator_floor'] for n in range(N)])[:, None, None, None, None]
    tiny = np.array([np.finfo(REGIMES[n % 11]['arithmetic']).tiny for n in range(N)])[:, None, None, None, None]
    positive = valid & (d > 0)
    attenuation = np.zeros_like(d); np.divide(d, np.maximum(d, eps), out=attenuation, where=d > 0)
    count = lambda x: x.sum(axis=(-2, -1), dtype=np.int64)
    counts = np.stack([count(x) for x in (valid, valid & (d == 0), positive,
                       positive & (d < eps), positive & (d < tiny))], axis=-1)
    sums = np.stack((np.where(positive, d, 0.).sum(axis=(-2, -1)),
                     np.where(positive, attenuation, 0.).sum(axis=(-2, -1))), axis=-1)
    bins = (0., 1e-8, 1e-6, 1e-4, 1e-2, 1., np.inf)
    hist = np.stack([count(positive & (d > low) & (d <= high)) for low, high in zip(bins[:-1], bins[1:])], axis=-1)
    alive_edges = edges(mask)[None]; surviving = tags & alive_edges
    # strength() sums magnitudes; bool-to-float exposure is only a diagnostic.
    exposed = (strength(surviving.astype(float)) > 0) & valid
    numerator = strength(abs(old) * surviving); denominator = strength(old)
    fractions = np.zeros_like(denominator)
    np.divide(numerator, denominator, out=fractions, where=denominator > 0)
    edge_count = lambda a: a.sum(axis=(-3, -2, -1), dtype=np.int64)
    rc = np.stack((edge_count(tags), edge_count(surviving), edge_count(surviving & (old != 0)),
                   count(exposed & (denominator > 0)), count(exposed & (denominator == 0))), axis=-1)
    rs = np.stack(((abs(old) * surviving).sum(axis=(-3, -2, -1)),
                   np.where(exposed, fractions, 0.).sum(axis=(-2, -1))), axis=-1)
    return dict(attenuation=attenuation, denom_counts=counts, denom_sums=sums, denom_hist=hist,
                repair_counts=rc, repair_sums=rs, repair_fraction=fractions)


def noises(z, e):
    a = pair(z); result = np.empty((3, *a.shape[:2], 2, 16, 16))
    for k, rho in enumerate((1., .999, 0.)):
        result[k, :, :, 0] = a
        result[k, :, :, 1] = a if rho == 1 else pair(rho*z + np.sqrt(1.-rho*rho)*e)
    return result


def replay(incoming, block, g, previous, tags, cfg, cycle):
    R = cfg['recipients']; mask = masks_for(block, g, R, renewal=True)[:, :, 1]
    av = edges(mask); old = unpack(incoming) * av
    stream, independent = random('E022', block, 'develop', g), random('E051', block, 'innovation', g)
    shape = (2, R, 16, 16); unit = pair(stream.standard_normal(shape)); independent.standard_normal(shape)
    live = (~mask)[None, :, :, None]; cues = CUES.reshape(1, 1, 1, 2, 1)
    birth = np.empty((N, 4, R, 2, 16, 16)); denom = np.empty((N, 4, R, 16, 16)); groups = []
    for kind in ('float64', 'float32'):
        ids = np.array([i for i in range(N) if REGIMES[i % 11]['arithmetic'] == kind]); t = np.dtype(kind).type
        w = old[ids].astype(t); d = strength(w)
        b = t(cfg['birth_sd']) * unit.astype(t)
        v = np.broadcast_to(b[None, :, :, None], (len(ids), 4, R, 2, 16, 16)).copy()
        birth[ids] = v; v *= live; v[..., P[0]] = cues.astype(t); denom[ids] = d
        eps = np.array([REGIMES[i % 11]['denominator_floor'] for i in ids], dtype=t)[:, None, None, None, None, None]
        groups.append([ids, v, w[:, :, :, None], d[:, :, :, None], eps])
    moments = np.zeros((3, 6)); traces = []
    for it in range(cycle['read_steps']):
        noise = noises(stream.standard_normal(shape), independent.standard_normal(shape))
        a, b = noise[:, :, :, 0], noise[:, :, :, 1]
        for k, x in enumerate((a, b, a*a, b*b, a*b)): moments[:, k] += x.sum(axis=(1, 2, 3, 4))
        moments[:, 5] += a[0].size
        observed = np.empty((N, 4, R, 2, 2)) if it >= cycle['read_steps'] - cfg['observe_steps'] else None
        for group in groups:
            ids, v, w, d, eps = group
            v = step(v, w, d, noise[ids // 11].astype(v.dtype), cfg, it >= cycle['settling_steps'], eps)
            v *= live; v[..., P[0]] = cues.astype(v.dtype); group[1] = v
            if observed is not None: observed[ids] = observe(v)
        if observed is not None: traces.append(observed)
    end = np.empty((N, 4, R, 2, 16, 16)); calculated = np.empty_like(old); q = np.empty_like(old)
    fallback = np.empty(old.shape, bool); cc = np.empty((N, 4, R, 5), np.int64); typed_old = np.empty_like(old)
    for ids, v, w, d, eps in groups:
        end[ids] = v; calculated[ids], q[ids], fallback[ids], cc[ids] = capture(v, cfg['writer_beta'])
        typed_old[ids] = w[:, :, :, 0]
    before = calculated.copy(); before *= av
    # Selection in the original writer explicitly produces +0 on unavailable edges.
    before[np.broadcast_to(~av, before.shape)] = 0.
    counts, sums = mechanism(typed_old, before, av, mask, previous, q, fallback)
    returning = previous & ~mask; incident = np.empty(av.shape, bool)
    for y, x in np.ndindex(16, 16):
        incident[..., 0, y, x] = av[..., 0, y, x] & (returning[..., y, x] | returning[..., y, (x+1) % 16])
        incident[..., 1, y, x] = av[..., 1, y, x] & (returning[..., y, x] | returning[..., (y+1) % 16, x])
    repair_tags = incident[None] & (typed_old == 0) & (before != 0)
    diagnostics = numerics(typed_old, denom, mask, tags)
    v = end.copy(); scaffold = av[None, :, :, None].astype(float); stream = random('E022', block, 'write', g)
    hashes = np.empty((cycle['write_steps'], N, 32), np.uint8)
    for it in range(cycle['write_steps']):
        v = advance(v, scaffold, 2., pair(stream.standard_normal(shape))[None, :, :, None], cfg)
        v *= live; v[..., P[0]] = cues
        for n in range(N): hashes[it, n] = np.frombuffer(hashlib.sha256(v[n].astype('<f8').tobytes()).digest(), np.uint8)
    trace = np.array(traces)
    return dict(incoming=incoming.copy(), masks=mask, effective_packets=pack(typed_old), denominator=denom,
        birth=birth, end=end, late_ports=trace, mean_ports=trace.mean(axis=0), computed_packets=pack(calculated),
        counts=counts, sums=sums, capture_counts=cc, repair_tags=repair_tags, noise_moments=moments,
        write_end=v, write_state_hashes=hashes, **diagnostics, **transmit(pack(before), av, block, g))


def assay(incoming, acquired, block, h, cfg, cycle):
    panels, mapping = layout(h); R = cfg['recipients']; count = len(panels)
    packets = np.array([incoming[n] if n >= 0 else np.zeros_like(incoming[0]) if n == -1 else acquired for n, r in panels])
    mask = masks_for(block, h, R); old = unpack(packets)[:, :, :, None] * edges(mask)[None]
    stream = random('E022', block, 'assay', h); unit = pair(stream.standard_normal((2, R, 3, 16, 16)))
    birth = np.empty((count, 4, R, 3, 16, 16)); dsave = np.empty_like(birth)
    live = (~mask)[None, :, :, None]; cue = CUES.reshape(1, 1, 1, 2, 1, 1); groups = []
    for kind in ('float64', 'float32'):
        ids = np.array([i for i, (n, r) in enumerate(panels) if READERS[r][0] == kind]); t = np.dtype(kind).type
        w = old[ids].astype(t); d = strength(w); b = t(cfg['birth_sd']) * unit.astype(t)
        v = np.broadcast_to(b[None, :, :, None], (len(ids), 4, R, 2, 3, 16, 16)).copy()
        v *= live; v[..., P[0]] = cue.astype(t); birth[ids] = b; dsave[ids] = d
        eps = np.array([READERS[panels[i][1]][1] for i in ids], dtype=t)[:, None, None, None, None, None, None]
        groups.append([ids, v, w[:, :, :, None], d[:, :, :, None], eps])
    traces = []
    for it in range(cycle['read_steps']):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None]
        observation = np.empty((count, 4, R, 2, 3, 2)) if it >= cycle['read_steps'] - cfg['observe_steps'] else None
        for group in groups:
            ids, v, w, d, eps = group
            v = step(v, w, d, noise.astype(v.dtype), cfg, it >= cycle['settling_steps'], eps)
            v *= live; v[..., P[0]] = cue.astype(v.dtype); group[1] = v
            if observation is not None: observation[ids] = observe(v)
        if observation is not None: traces.append(observation)
    end = np.empty((count, 4, R, 2, 3, 16, 16))
    for ids, v, w, d, eps in groups: end[ids] = v
    trace = np.array(traces)
    return dict(records=packets, panels=np.array(panels, np.int64), masks=mask, birth=birth,
                denominator=dsave, end=end, late_ports=trace, mean_ports=trace.mean(axis=0))


def score(values, cfg):
    rules = np.array([1., -1., 1., -1.]); extra = (1,) * (values.ndim - 5)
    target = rules.reshape(1, 4, 1, 1, *extra) * CUES.reshape(1, 1, 1, 2, *extra)
    margin = np.minimum(target * values[..., 0], -target * values[..., 1])
    return dict(correct=margin > cfg['margin'], margin=margin, ports=values)
