"""Paired receiving readers for unchanged E022 packets on fresh blocks."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E022_reader_compensation import model as renewal
import numpy as np

base, acquisition = renewal.base, renewal.acquisition
CFG, Cycle, CYCLE = renewal.CFG, renewal.Cycle, renewal.CYCLE
PORTS, RULES, CUES = renewal.PORTS.copy(), renewal.RULES.copy(), renewal.CUES.copy()
ARMS, DAMAGE = renewal.ARMS, renewal.DAMAGE
CONDITIONS, ACTIVE, READER_MODES = renewal.CONDITIONS, renewal.ACTIVE, renewal.READER_MODES
RECEIVERS = ('fixed_four', 'local_strength')
PANELS = tuple((h, condition, receiver) for h in (0, 1) for receiver in RECEIVERS
               for condition in (('initial',) if h == 0 else CONDITIONS))
# Reuse the already audited acquisition/renewal machinery and its RNG namespaces.
# Fresh block IDs make the cohort independent of E022.
replace_record = renewal.replace_record
score = renewal.score


def receiver_denominators(effective_weights):
    """Local strength is measured AFTER injury and record/communication controls."""
    strength = renewal.incident_sum(np.abs(effective_weights))
    return np.concatenate((np.full_like(strength, 4.), strength), axis=0)


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    """First N output panels fixed-four, next N normalized; all randomness paired."""
    packets, permutations = renewal.assay_packets(records, block, horizon)
    masks = base.damage_masks(block, f'E022_h{horizon}', cfg)
    effective = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    denominator = receiver_denominators(effective)
    weights = np.concatenate((effective, effective), axis=0)
    stream = rng('E022', block, 'assay', horizon)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None, :, None], (2*len(records), 4, cfg.recipients, 2, 3, 7, 16, 16)).copy()
    active = (~masks)[None, :, :, None, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1, 1, 1)
    v *= active
    v[..., PORTS[0]] = cue
    late = np.zeros_like(v); trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))[None, :, :, None, :, None]
        v = renewal.compensated_step(v, weights, denominator, noise, cfg,
                                     amplification=t >= cycle.settling_steps)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            late += v
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(packets=packets, permutations=permutations, masks=masks, birth=birth,
                receiver_denominators=denominator, end=v, late_mean=late/cfg.observe_steps,
                late_ports=np.stack(trace))
