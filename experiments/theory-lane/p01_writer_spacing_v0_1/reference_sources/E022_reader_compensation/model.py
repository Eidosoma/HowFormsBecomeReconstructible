"""One damaged renewal boundary with three fixed local reading rules."""
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E015_functional_inheritance import model as base
from E016_teaching_consistency import model as acquisition
from E017_reader_timing.model import unamplified
import numpy as np

CFG = base.CFG
PORTS, RULES, CUES = base.PORTS.copy(), base.RULES.copy(), base.CUES.copy()
ARMS, DAMAGE = base.ARMS, base.DAMAGE
CONDITIONS = ("baseline", "degree_compensated", "strength_compensated", "intact_renewed",
              "protected_copy", "masked_copy", "read_blocked", "write_blocked")
ACTIVE = (0, 1, 2, 3, 6, 7)
READER_MODES = ("fixed_four", "physical_degree", "local_strength", "fixed_four", "local_strength", "local_strength")
PANELS = ((0, "initial"),) + tuple((1, condition) for condition in CONDITIONS)


@dataclass(frozen=True)
class Cycle:
    read_steps: int = 2048
    settling_steps: int = 256
    write_steps: int = 128
    generations: int = 1


CYCLE = Cycle()


def surviving_edges(masks):
    alive = ~masks
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def incident_sum(weights):
    h, v = weights[..., 0, :, :], weights[..., 1, :, :]
    return h + np.roll(h, 1, -1) + v + np.roll(v, 1, -2)


def reading_denominators(weights, masks):
    result = np.full(masks.shape, 4.)
    result[1] = incident_sum(surviving_edges(masks[1]).astype(float))
    for branch in (2, 4, 5):
        result[branch] = incident_sum(np.abs(weights[branch]))
    return result


def compensated_step(v, weights, denominator, noise, cfg=CFG, amplification=True):
    incoming = base.neighbor_sum(v, weights)
    local = np.divide(incoming, denominator, out=np.zeros_like(incoming), where=denominator > 0)
    drift = (v-v**3 if amplification else -v**3) + 2.*(local-v)
    return np.clip(v+cfg.dt*drift+cfg.noise*noise, -2., 2.)


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
        v = compensated_step(v, weights, denominator[:, :, :, None], noise, cfg,
                             amplification=t >= cycle.settling_steps)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(birth=birth, read_denominators=denominator, developed_end=v, developed_late_ports=np.stack(trace))


def capture_from_activity(body, cfg=CFG):
    """Unchanged E019/E020 snapshot; neither mask nor incoming record enters."""
    return base.encode(base.correlations(body, cfg.writer_beta).mean(axis=3))


def write_from_activity(body, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Capture once, then keep the same cells absent throughout the holding window."""
    assert body.shape == (6, 4, cfg.recipients, 2, 16, 16)
    assert masks.shape == (6, 4, cfg.recipients, 16, 16)
    stream = rng("E022", block, "write", generation)
    v = body.copy()
    computed = capture_from_activity(v, cfg)
    active = (~masks)[:, :, :, None]
    scaffold = surviving_edges(masks)[:, :, :, None].astype(float)
    states = []
    cue = CUES.reshape(1, 1, 1, 2, 1)
    for _ in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue
        states.append(v.copy())
    return dict(write_states=np.stack(states), write_end=v, computed_packets=computed)


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (8, 4, cfg.recipients, 4096)
    assert generation == cycle.generations == 1
    renewal_mask = base.damage_masks(block, f"E022_renewal_g{generation}", cfg)[:, :, 1]
    masks = np.repeat(renewal_mask[None], 6, axis=0)
    masks[3] = False  # Paired intact renewal reference.
    read_packets = base.encode(base.decode(incoming[list(ACTIVE)])*surviving_edges(masks))
    read_packets[4] = 0  # Disable incoming-record reading, not subsequent writing.
    effective_saved = read_packets.copy()
    developed = develop(read_packets, masks, block, generation, cfg, cycle)
    read_packets.fill(0)  # No incoming weights are available to the new writer.
    written = write_from_activity(developed["developed_end"], masks, block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written["computed_packets"]
    outgoing[5] = base.encode(base.decode(incoming[5])*surviving_edges(renewal_mask))
    outgoing[7] = 0  # Write-disabled transmission; calculation retained for audit.
    return dict(incoming=incoming.copy(), read_packets=effective_saved,
                erased_packets=read_packets, outgoing=outgoing, renewal_mask=renewal_mask,
                body_masks=masks, **developed, **written)


def assay_packets(records, block, horizon):
    # N,F,R,bytes -> N,F,R,A,bytes. Foreign swaps matched opposite-rule founders.
    own = base.decode(records)
    weights = np.repeat(own[:, :, :, None], len(ARMS), axis=3)
    weights[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    permutations = np.stack([rng("E022", block, "shuffle", horizon, f).permutation(512) for f in range(4)])
    for n in range(len(records)):
        for f in range(4):
            weights[n, f, :, 2] = own[n, f].reshape(-1, 512)[:, permutations[f]].reshape(-1, 2, 16, 16)
    weights[:, :, :, 3] = 0.
    weights[:, :, :, 4] = 1.
    return base.encode(weights), permutations


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    packets, permutations = assay_packets(records, block, horizon)
    masks = base.damage_masks(block, f"E022_h{horizon}", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E022", block, "assay", horizon)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None, :, None], (len(records), 4, cfg.recipients, 2, 3, 7, 16, 16)).copy()
    active = (~masks)[None, :, :, None, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1, 1, 1)
    v *= active
    v[..., PORTS[0]] = cue
    late = np.zeros_like(v)
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))[None, :, :, None, :, None]
        v = unamplified(v, weights, noise, cfg) if t < cycle.settling_steps else base.step(v, weights, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            late += v
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(packets=packets, permutations=permutations, masks=masks, birth=birth,
                end=v, late_mean=late/cfg.observe_steps, late_ports=np.stack(trace))


def score(trace, cfg=CFG):
    values = trace.mean(axis=0)
    desired = RULES.reshape(1, 4, 1, 1, 1, 1)*CUES.reshape(1, 1, 1, 2, 1, 1)
    a, b = desired*values[..., 0], -desired*values[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), values
