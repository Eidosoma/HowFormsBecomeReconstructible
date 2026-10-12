"""Immediate capture through three damaged bodies, with paired serial controls."""
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
CONDITIONS = ("renewed", "intact_renewed", "protected_copy", "masked_copy", "read_blocked", "write_blocked")
ACTIVE = (0, 1, 4, 5)
PANELS = ((0, "initial"),) + tuple((h, condition) for h in (1, 3) for condition in CONDITIONS)


@dataclass(frozen=True)
class Cycle:
    read_steps: int = 2048
    settling_steps: int = 256
    write_steps: int = 128
    generations: int = 3


CYCLE = Cycle()


def surviving_edges(masks):
    alive = ~masks
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def develop(packets, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Read four chains with absent cells fixed at zero; only input is clamped."""
    assert packets.shape == (4, 4, cfg.recipients, 4096)
    assert masks.shape == (4, 4, cfg.recipients, 16, 16)
    weights = base.decode(packets)[:, :, :, None]
    stream = rng("E021", block, "develop", generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (4, 4, cfg.recipients, 2, 16, 16)).copy()
    active = (~masks)[:, :, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., PORTS[0]] = cue
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = unamplified(v, weights, noise, cfg) if t < cycle.settling_steps else base.step(v, weights, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(birth=birth, developed_end=v, developed_late_ports=np.stack(trace))


def capture_from_activity(body, cfg=CFG):
    """Unchanged E019/E020 snapshot; neither mask nor incoming record enters."""
    return base.encode(base.correlations(body, cfg.writer_beta).mean(axis=3))


def write_from_activity(body, masks, block, generation, cfg=CFG, cycle=CYCLE):
    """Capture once, then keep the same cells absent throughout the holding window."""
    assert body.shape == (4, 4, cfg.recipients, 2, 16, 16)
    assert masks.shape == (4, 4, cfg.recipients, 16, 16)
    stream = rng("E021", block, "write", generation)
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
    assert incoming.shape == (6, 4, cfg.recipients, 4096)
    renewal_mask = base.damage_masks(block, f"E021_renewal_g{generation}", cfg)[:, :, 1]
    masks = np.repeat(renewal_mask[None], 4, axis=0)
    masks[1] = False  # Paired intact renewal reference.
    read_packets = base.encode(base.decode(incoming[list(ACTIVE)])*surviving_edges(masks))
    read_packets[2] = 0  # Disable incoming-record reading, not subsequent writing.
    effective_saved = read_packets.copy()
    developed = develop(read_packets, masks, block, generation, cfg, cycle)
    read_packets.fill(0)  # No incoming weights are available to the new writer.
    written = write_from_activity(developed["developed_end"], masks, block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written["computed_packets"]
    outgoing[3] = base.encode(base.decode(incoming[3])*surviving_edges(renewal_mask))
    outgoing[5] = 0  # Write-disabled transmission; calculation retained for audit.
    return dict(incoming=incoming.copy(), read_packets=effective_saved,
                erased_packets=read_packets, outgoing=outgoing, renewal_mask=renewal_mask,
                body_masks=masks, **developed, **written)


def assay_packets(records, block, horizon):
    # N,F,R,bytes -> N,F,R,A,bytes. Foreign swaps matched opposite-rule founders.
    own = base.decode(records)
    weights = np.repeat(own[:, :, :, None], len(ARMS), axis=3)
    weights[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    permutations = np.stack([rng("E021", block, "shuffle", horizon, f).permutation(512) for f in range(4)])
    for n in range(len(records)):
        for f in range(4):
            weights[n, f, :, 2] = own[n, f].reshape(-1, 512)[:, permutations[f]].reshape(-1, 2, 16, 16)
    weights[:, :, :, 3] = 0.
    weights[:, :, :, 4] = 1.
    return base.encode(weights), permutations


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    packets, permutations = assay_packets(records, block, horizon)
    masks = base.damage_masks(block, f"E021_h{horizon}", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E021", block, "assay", horizon)
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
