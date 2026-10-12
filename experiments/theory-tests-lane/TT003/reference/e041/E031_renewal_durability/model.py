"""Preserve available weights above 0.5; refresh weaker coordinates from activity."""
import hashlib
from dataclasses import replace
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
CYCLE = replace(CYCLE, generations=16)
PORTS, RULES, CUES = predecessor.PORTS.copy(), predecessor.RULES.copy(), predecessor.CUES.copy()
ARMS, DAMAGE = predecessor.ARMS, predecessor.DAMAGE
CONDITIONS = ('maturing', 'maturing_read_blocked', 'strength_compensated', 'intact_renewed',
              'protected_copy', 'masked_copy', 'read_blocked', 'write_blocked',
              'selective', 'maturing_refresh_blocked')
ACTIVE = (0, 1, 2, 3, 6, 7, 8, 9)
READER_MODES = ('local_strength', 'local_strength', 'local_strength', 'fixed_four',
                'local_strength', 'local_strength', 'local_strength', 'local_strength')
SELECTORS = (0, 1, 6, 7)  # Positions within ACTIVE, not condition indices.
THRESHOLDS = (.5, .5, 0., .5)
REFRESH = (True, True, True, False)
RECEIVERS, HORIZONS = predecessor.RECEIVERS, (0, 1, 3, 8, 16)
PANELS = tuple((h, c, r) for h in HORIZONS for r in RECEIVERS for c in (('initial',) if h == 0 else CONDITIONS))
assay, score = predecessor.assay, predecessor.score
receiver_denominators = predecessor.receiver_denominators


def selective_packet(inherited, computed, available, threshold=.5, refresh=True):
    """A fixed strength proxy; no ancestry labels, outcomes or donor packet."""
    old, fresh = base.decode(inherited), base.decode(computed)
    retained = available & (np.abs(old) > threshold)
    eligible = available & ~retained
    outgoing = np.where(retained, old, np.where(eligible & refresh, fresh, 0.))
    return base.encode(outgoing), retained, eligible


def reading_denominators(weights, masks):
    result = renewal.incident_sum(np.abs(weights))
    result[3] = 4.
    return result


def develop(packets, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Read eight matched branches; the denominator is local to this body."""
    assert packets.shape == (8, 4, cfg.recipients, 4096)
    assert masks.shape == (8, 4, cfg.recipients, 16, 16)
    decoded = base.decode(packets)
    denominator = reading_denominators(decoded, masks)
    weights = decoded[:, :, :, None]
    stream = rng("E022", block, "develop", generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (8, 4, cfg.recipients, 2, 16, 16)).copy()
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


def write_from_activity(body, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Unchanged capture/holding dynamics; retain exact per-branch state digests."""
    assert body.shape == (8, 4, cfg.recipients, 2, 16, 16)
    assert masks.shape == (8, 4, cfg.recipients, 16, 16)
    stream = rng('E022', block, 'write', generation)
    v = body.copy()
    computed = renewal.capture_from_activity(v, cfg)
    active = (~masks)[:, :, :, None]
    scaffold = renewal.surviving_edges(masks)[:, :, :, None].astype(float)
    hashes = np.empty((cycle.write_steps, 8, 32), dtype=np.uint8)
    cue = CUES.reshape(1, 1, 1, 2, 1)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue
        for a in range(8):
            digest = hashlib.sha256(np.ascontiguousarray(v[a], dtype='<f8').tobytes()).digest()
            hashes[t, a] = np.frombuffer(digest, dtype=np.uint8)
    return dict(write_state_hashes=hashes, write_end=v, computed_packets=computed)


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (10, 4, cfg.recipients, 4096)
    assert cycle.generations in (3, 16) and 1 <= generation <= cycle.generations
    renewal_mask = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    masks = np.repeat(renewal_mask[None], 8, axis=0)
    masks[3] = False
    available = renewal.surviving_edges(masks)
    physical_packets = base.encode(base.decode(incoming[list(ACTIVE)])*available)
    # Selective chains explicitly retain inherited values for the copying component.
    retained_packets = physical_packets[list(SELECTORS)].copy()
    read_packets = physical_packets.copy()
    read_packets[[1, 4]] = 0
    effective_saved = read_packets.copy()
    developed = develop(read_packets, masks, block, generation, cfg, cycle)
    read_packets.fill(0)
    written = write_from_activity(developed['developed_end'], masks, block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written['computed_packets']
    retained, eligible = [], []
    for i, (a, cutoff, refresh) in enumerate(zip(SELECTORS, THRESHOLDS, REFRESH)):
        packet, kept, weak = selective_packet(retained_packets[i], written['computed_packets'][a], available[a], cutoff, refresh)
        outgoing[ACTIVE[a]] = packet
        retained.append(kept)
        eligible.append(weak)
    outgoing[5] = base.encode(base.decode(incoming[5])*available[0])
    outgoing[7] = 0
    return dict(incoming=incoming.copy(), read_packets=effective_saved, erased_packets=read_packets,
                retained_packets=retained_packets, retained_edges=np.stack(retained), eligible_edges=np.stack(eligible),
                outgoing=outgoing, renewal_mask=renewal_mask, body_masks=masks, **developed, **written)
