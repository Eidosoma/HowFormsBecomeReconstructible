"""Preserve nonzero inherited weights; fill available exact-zero coordinates locally."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E024_serial_compensation import model as predecessor
import numpy as np

renewal = predecessor.renewal
base, acquisition = predecessor.base, predecessor.acquisition
CFG, Cycle, CYCLE = predecessor.CFG, predecessor.Cycle, predecessor.CYCLE
PORTS, RULES, CUES = predecessor.PORTS.copy(), predecessor.RULES.copy(), predecessor.CUES.copy()
ARMS, DAMAGE = predecessor.ARMS, predecessor.DAMAGE
CONDITIONS = ('selective', 'selective_read_blocked', 'strength_compensated', 'intact_renewed',
              'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked')
ACTIVE = (0, 1, 2, 3, 6, 7)
READER_MODES = ('local_strength', 'local_strength', 'local_strength', 'fixed_four', 'local_strength', 'local_strength')
RECEIVERS, HORIZONS = predecessor.RECEIVERS, (0, 1, 3)
PANELS = tuple((h, c, r) for h in HORIZONS for r in RECEIVERS for c in (('initial',) if h == 0 else CONDITIONS))
assay, score = predecessor.assay, predecessor.score
receiver_denominators = predecessor.receiver_denominators


def selective_packet(inherited, computed, available):
    """Exact-zero infill; no threshold, ancestry labels or donor packet."""
    old, fresh = base.decode(inherited), base.decode(computed)
    retained = available & (old != 0.)
    eligible = available & ~retained
    outgoing = np.where(retained, old, np.where(eligible, fresh, 0.))
    return base.encode(outgoing), retained, eligible


def reading_denominators(weights, masks):
    result = renewal.incident_sum(np.abs(weights))
    result[3] = 4.
    return result


def develop(packets, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Read six matched branches; the denominator is local to this body."""
    assert packets.shape == (6, 4, cfg.recipients, 4096)
    assert masks.shape == (6, 4, cfg.recipients, 16, 16)
    decoded = base.decode(packets)
    denominator = reading_denominators(decoded, masks)
    weights = decoded[:, :, :, None]
    stream = rng("E022", block, "develop", generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (6, 4, cfg.recipients, 2, 16, 16)).copy()
    active = (~masks)[:, :, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., PORTS[0]] = cue
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = renewal.compensated_step(v, weights, denominator[:, :, :, None], noise, cfg,
                             amplification=t >= cycle.settling_steps)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(birth=birth, read_denominators=denominator, developed_end=v, developed_late_ports=np.stack(trace))


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (8, 4, cfg.recipients, 4096)
    assert cycle.generations == 3 and 1 <= generation <= 3
    renewal_mask = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    masks = np.repeat(renewal_mask[None], 6, axis=0)
    masks[3] = False
    available = renewal.surviving_edges(masks)
    physical_packets = base.encode(base.decode(incoming[list(ACTIVE)])*available)
    # Selective chains explicitly retain inherited values for the copying component.
    retained_packets = physical_packets[:2].copy()
    read_packets = physical_packets.copy()
    read_packets[[1, 4]] = 0
    effective_saved = read_packets.copy()
    developed = develop(read_packets, masks, block, generation, cfg, cycle)
    read_packets.fill(0)
    written = renewal.write_from_activity(developed['developed_end'], masks, block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written['computed_packets']
    selective, retained, eligible = selective_packet(retained_packets, written['computed_packets'][:2], available[:2])
    outgoing[:2] = selective
    outgoing[5] = base.encode(base.decode(incoming[5])*available[0])
    outgoing[7] = 0
    return dict(incoming=incoming.copy(), read_packets=effective_saved, erased_packets=read_packets,
                retained_packets=retained_packets, retained_edges=retained, eligible_edges=eligible,
                outgoing=outgoing, renewal_mask=renewal_mask, body_masks=masks, **developed, **written)
