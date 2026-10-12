"""Independent selected-condition replay of the frozen E051 native equations.

No production modules are imported. The arithmetic order follows their public
specification to permit exact replay. Native source snapshots are retained in
reference_sources. Holding states are discarded before renewal in that source.
"""
import hashlib
import json

import numpy as np

RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
PORTS = np.zeros((3, 16, 16), dtype=bool)
for p, (row, column) in enumerate(((7, 1), (3, 10), (11, 10))):
    PORTS[p, row:row+2, column:column+2] = True


def stream(tag, *parts):
    key = json.dumps([tag, *parts], separators=(',', ':')).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed))


def paired_founders(values):
    return np.repeat(values, 2, axis=0)


def matched_cues(values):
    first = paired_founders(values)
    return np.stack((first, first.copy()), axis=2)


def damage_masks(block, phase, recipients):
    available = np.flatnonzero(~PORTS.any(axis=0).ravel())
    squares = []
    for row in range(16):
        for column in range(16):
            mask = np.zeros((16, 16), dtype=bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    mask[(row+dy) % 16, (column+dx) % 16] = True
            if not (mask & PORTS.any(axis=0)).any():
                squares.append(mask)
    random = stream('E015', block, phase, 'damage')
    masks = np.zeros((2, recipients, 3, 16, 16), dtype=bool)
    for founder in range(2):
        for recipient in range(recipients):
            masks[founder, recipient, 1].ravel()[random.choice(available, 24, replace=False)] = True
            masks[founder, recipient, 2] = squares[int(random.integers(len(squares)))]
    return paired_founders(masks)


def available_edges(mask):
    alive = ~mask
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def encode(weights):
    weights = np.asarray(weights, dtype='<f8')
    assert weights.shape[-3:] == (2, 16, 16) and np.isfinite(weights).all()
    return np.ascontiguousarray(weights).view(np.uint8).reshape(*weights.shape[:-3], 4096).copy()


def decode(packets):
    assert packets.dtype == np.uint8 and packets.shape[-1] == 4096
    result = np.frombuffer(packets.tobytes(), dtype='<f8').reshape(*packets.shape[:-1], 2, 16, 16).copy()
    assert np.isfinite(result).all()
    return result


def incident(weights):
    h, v = weights[..., 0, :, :], weights[..., 1, :, :]
    return h + np.roll(h, 1, -1) + v + np.roll(v, 1, -2)


def neighbors(value, weights):
    h, v = weights[..., 0, :, :], weights[..., 1, :, :]
    return (h*np.roll(value, -1, -1) + np.roll(h, 1, -1)*np.roll(value, 1, -1)
            + v*np.roll(value, -1, -2) + np.roll(v, 1, -2)*np.roll(value, 1, -2))


def step(value, weights, denominator, noise, cfg, amplification):
    incoming = neighbors(value, weights)
    local = np.divide(incoming, denominator, out=np.zeros_like(incoming), where=denominator > 0)
    drift = (value-value**3 if amplification else -value**3) + 2.*(local-value)
    return np.clip(value+cfg['dt']*drift+cfg['noise']*noise, -2., 2.)


def writer_components(body, masks, beta, tolerance):
    x = np.tanh(beta*body)
    ordinary = np.stack((x*np.roll(x, -1, -1), x*np.roll(x, -1, -2)), axis=-3).mean(axis=3)
    difference = (x[:, :, :, 0]-x[:, :, :, 1])/2
    contrast = np.stack((difference*np.roll(difference, -1, -1),
                         difference*np.roll(difference, -1, -2)), axis=-3)
    available = available_edges(masks)
    original = np.where(available, np.where(contrast == 0., ordinary, contrast), 0.)
    threshold = np.where(available, np.where(abs(contrast) <= tolerance, ordinary, contrast), 0.)
    restored = np.sign(original)*np.abs(threshold)
    assert np.array_equal(np.abs(restored), np.abs(threshold)), 'Magnitude control failed'
    assert np.array_equal(restored != 0., threshold != 0.), 'Support control failed'
    counts = available.sum(axis=(-3, -2, -1))
    newly_substituted = available & (contrast != 0.) & (abs(contrast) <= tolerance)
    sign_flipped = available & (original*threshold < 0.)
    statistics = dict(available_edges=counts,
        newly_substituted_fraction=newly_substituted.sum(axis=(-3, -2, -1))/counts,
        sign_flip_fraction=sign_flipped.sum(axis=(-3, -2, -1))/counts)
    return dict(exact_rewrite=original, tolerance_rewrite=threshold, sign_restored=restored), statistics


def capture(body, masks, writers, cfg, tolerance):
    components, statistics = writer_components(body, masks, cfg['writer_beta'], tolerance)
    assert body.shape[0] == len(writers)
    weights = np.stack([components[name][i] for i, name in enumerate(writers)])
    return encode(weights), statistics


def read_ports(value):
    return np.stack((value[..., PORTS[1]].mean(axis=-1), value[..., PORTS[2]].mean(axis=-1)), axis=-1)


def rebuild(packets, block, generation, writers, cfg, cycle, tolerance):
    assert packets.shape == (len(writers), 4, cfg['recipients'], 4096)
    masks = damage_masks(block, f'E022_renewal_g{generation}', cfg['recipients'])[:, :, 1]
    effective = decode(packets)*available_edges(masks)
    denominator = incident(abs(effective))
    random = stream('E022', block, 'develop', generation)
    shape = (2, cfg['recipients'], 16, 16)
    birth = cfg['birth_sd']*matched_cues(random.standard_normal(shape))
    value = np.repeat(birth[None], len(writers), axis=0)
    alive = (~masks)[None, :, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1)
    value *= alive
    value[..., PORTS[0]] = cue
    late = []
    for t in range(cycle['read_steps']):
        noise = matched_cues(random.standard_normal(shape))[None]
        value = step(value, effective[:, :, :, None], denominator[:, :, :, None], noise, cfg,
                     amplification=t >= cycle['settling_steps'])
        value *= alive
        value[..., PORTS[0]] = cue
        if t >= cycle['read_steps']-cfg['observe_steps']:
            late.append(read_ports(value))
    outgoing, statistics = capture(value, masks, writers, cfg, tolerance)
    return dict(masks=masks, birth=birth, end=value, outgoing=outgoing,
                mean_ports=np.stack(late).mean(axis=0), **statistics)


def assay(packets, block, horizon, cfg, cycle):
    packets = np.concatenate((packets, np.zeros_like(packets[:1])), axis=0)
    masks = damage_masks(block, f'E022_h{horizon}', cfg['recipients'])
    effective = decode(packets)[:, :, :, None]*available_edges(masks)[None]
    denominator = incident(abs(effective))
    random = stream('E022', block, 'assay', horizon)
    shape = (2, cfg['recipients'], 3, 16, 16)
    birth = cfg['birth_sd']*paired_founders(random.standard_normal(shape))
    value = np.broadcast_to(birth[None, :, :, None], (len(packets), 4, cfg['recipients'], 2, 3, 16, 16)).copy()
    alive = (~masks)[None, :, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1, 1)
    value *= alive
    value[..., PORTS[0]] = cue
    late = []
    for t in range(cycle['read_steps']):
        noise = paired_founders(random.standard_normal(shape))[None, :, :, None]
        value = step(value, effective[:, :, :, None], denominator[:, :, :, None], noise, cfg,
                     amplification=t >= cycle['settling_steps'])
        value *= alive
        value[..., PORTS[0]] = cue
        if t >= cycle['read_steps']-cfg['observe_steps']:
            late.append(read_ports(value))
    return dict(masks=masks, birth=birth, end=value, mean_ports=np.stack(late).mean(axis=0))


def score(mean_ports, threshold):
    extra = (1,)*(mean_ports.ndim-5)
    target = RULES.reshape(1, 4, 1, 1, *extra)*CUES.reshape(1, 1, 1, 2, *extra)
    margins = np.minimum(target*mean_ports[..., 0], -target*mean_ports[..., 1])
    return dict(cue_margin=margins, cue_correct=margins > threshold,
                both_pass=(margins > threshold).all(axis=3), min_margin=margins.min(axis=3))
