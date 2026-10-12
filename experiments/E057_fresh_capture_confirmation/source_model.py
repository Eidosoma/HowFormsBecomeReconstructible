"""The two E051 exact-writer chains needed for a fresh E055/E056 confirmation."""
import numpy as np
from common import rng
from E022_reader_compensation import model as renewal
from E055_stress_capture_recovery.model import capture
from E056_sign_magnitude_substitution.model import digest

base = renewal.base
acquisition = renewal.acquisition


def rebuild(incoming, block, generation, cfg, cycle):
    R = cfg.recipients
    assert incoming.shape == (2, 4, R, 4096)
    masks = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    available = renewal.surviving_edges(masks)
    effective = base.decode(incoming) * available
    denominator = renewal.incident_sum(abs(effective))
    stream = rng('E022', block, 'develop', generation)
    innovation = rng('E051', block, 'innovation', generation)
    shape = (2, R, 16, 16)
    z = stream.standard_normal(shape)
    innovation.standard_normal(shape)  # E051 consumes this draw for its shared births.
    birth = cfg.birth_sd * np.stack([np.stack((base.paired_founders(z), base.paired_founders(z)), axis=2)]*2)
    v = birth.copy()
    live = (~masks)[None, :, :, None]
    cue = base.CUES.reshape(1, 1, 1, 2, 1)
    v *= live; v[..., base.PORTS[0]] = cue
    trace = []; hashes = []; moments = np.zeros((2, 6))
    for t in range(cycle['read_steps']):
        z, e = stream.standard_normal(shape), innovation.standard_normal(shape)
        first = base.paired_founders(z)
        noise = np.stack((np.stack((first, first), axis=2),
                          np.stack((first, base.paired_founders(0.*z+np.sqrt(1.)*e)), axis=2)))
        a, b = noise[:, :, :, 0], noise[:, :, :, 1]
        for k, term in enumerate((a, b, a*a, b*b, a*b)):
            moments[:, k] += term.sum(axis=(1, 2, 3, 4))
        moments[:, 5] += a[0].size
        v = renewal.compensated_step(v, effective[:, :, :, None], denominator[:, :, :, None],
                                    noise, cfg, t >= cycle['settling_steps'])
        v *= live; v[..., base.PORTS[0]] = cue
        hashes.append(np.stack([digest(x) for x in v]))
        if t >= cycle['read_steps']-cfg.observe_steps:
            trace.append(np.stack([v[..., base.PORTS[p]].mean(axis=-1) for p in (1, 2)], axis=-1))
    end = v.copy(); trace = np.stack(trace)
    outgoing, ordinary, contrast, fallback = capture(end, available, cfg.writer_beta)
    stream = rng('E022', block, 'write', generation)
    scaffold = available[None, :, :, None].astype(float)
    write_hashes = []
    for _ in range(cycle['write_steps']):
        noise = base.paired_founders(stream.standard_normal(shape))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= live; v[..., base.PORTS[0]] = cue
        write_hashes.append(np.stack([digest(x) for x in v]))
    return dict(incoming=incoming.copy(), masks=masks, effective_packets=base.encode(effective),
        denominator=denominator, birth=birth, end=end, late_ports=trace, mean_ports=trace.mean(axis=0),
        ordinary=ordinary, contrast=contrast, fallback=fallback, outgoing=base.encode(outgoing),
        noise_moments=moments, read_state_hashes=np.stack(hashes), write_end=v,
        write_state_hashes=np.stack(write_hashes))
