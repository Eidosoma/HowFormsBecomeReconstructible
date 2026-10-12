"""Fresh unchanged histories, then the fixed E049 single-rollback continuation."""
import hashlib
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E049_rollback_persistence import model as previous
from E016_teaching_consistency import model as acquisition
import numpy as np

base, renewal, Cycle = previous.base, previous.renewal, previous.Cycle
VARIANTS, DOSES, FIELDS, OFFSETS = previous.VARIANTS, previous.DOSES, previous.FIELDS, previous.OFFSETS
construct, score, rebuild, first_failures = previous.construct, previous.score, previous.rebuild, previous.first_failures


def baseline(packets, block, generation, cfg, cycle):
    """One unchanged bridge-rewriting body; all founders and descendants together."""
    assert packets.shape == (4, cfg.recipients, 4096)
    assert 1 <= generation <= cycle.generations == 32 and 2*cycle.settling_steps == cycle.read_steps
    masks = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    available = renewal.surviving_edges(masks)
    effective = base.decode(packets)*available
    denominator = renewal.incident_sum(abs(effective))
    stream = rng('E022', block, 'develop', generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[:, :, None], (4, cfg.recipients, 2, 16, 16)).copy()
    live = (~masks)[:, :, None]; cues = base.CUES.reshape(1, 1, 2, 1)
    v *= live; v[..., base.PORTS[0]] = cues; late = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[:, :, None]
        v = renewal.compensated_step(v, effective[:, :, None], denominator[:, :, None], noise, cfg,
            amplification=t >= cycle.settling_steps)
        v *= live; v[..., base.PORTS[0]] = cues
        if t >= cycle.read_steps-cfg.observe_steps:
            late.append(np.stack([v[..., p].mean(axis=-1) for p in base.PORTS[1:]], axis=-1))
    end = v.copy(); late = np.stack(late)
    ordinary = base.correlations(end, cfg.writer_beta).mean(axis=2)
    x = np.tanh(cfg.writer_beta*end); difference = (x[:, :, 0]-x[:, :, 1])/2
    contrast = np.stack((difference*np.roll(difference, -1, -1), difference*np.roll(difference, -1, -2)), axis=-3)
    computed = base.encode(np.where(contrast != 0, contrast, ordinary))
    assert not (base.decode(computed)*(~available)).any()
    scaffold = available[:, :, None].astype(float); stream = rng('E022', block, 'write', generation)
    hashes = np.empty((cycle.write_steps, 4, cfg.recipients, 32), np.uint8)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[:, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= live; v[..., base.PORTS[0]] = cues
        for f, r in np.ndindex(4, cfg.recipients):
            hashes[t, f, r] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[f, r], dtype='<f8').tobytes()).digest(), np.uint8)
    return dict(incoming=packets.copy(), masks=masks, effective_packets=base.encode(effective),
        denominator=denominator, birth=birth, end=end, late_ports=late, mean_ports=late.mean(axis=0),
        computed_packets=computed, outgoing=base.encode(np.where(available, base.decode(computed), 0.)),
        write_end=v, write_state_hashes=hashes)


def baseline_score(values, cfg):
    target = base.RULES[:, None, None]*base.CUES[None, None, :]
    a, b = target*values[..., 0], -target*values[..., 1]
    return dict(correct=(a > cfg.margin) & (b > cfg.margin), margin=np.minimum(a, b), ports=values)
