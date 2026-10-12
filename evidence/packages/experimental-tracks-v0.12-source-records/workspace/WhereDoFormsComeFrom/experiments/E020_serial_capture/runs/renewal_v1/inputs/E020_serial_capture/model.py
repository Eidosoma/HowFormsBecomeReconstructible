"""Three staged readings and erased-record immediate captures, with fresh bodies."""
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
CONDITIONS = ("renewed", "protected_copy", "read_blocked", "write_blocked")
ACTIVE = (0, 2, 3)
PANELS = ((0, "initial"),) + tuple((h, condition) for h in (1, 3) for condition in CONDITIONS)


@dataclass(frozen=True)
class Cycle:
    read_steps: int = 2048
    settling_steps: int = 256
    write_steps: int = 128
    generations: int = 3


CYCLE = Cycle()


def develop(packets, block, generation, cfg=CFG, cycle=CYCLE):
    """Read three chains; only input is clamped. No rule/scorer/template input."""
    assert packets.shape == (3, 4, cfg.recipients, 4096)
    weights = base.decode(packets)[:, :, :, None]
    stream = rng("E020", block, "develop", generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (3, 4, cfg.recipients, 2, 16, 16)).copy()
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., PORTS[0]] = cue
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = unamplified(v, weights, noise, cfg) if t < cycle.settling_steps else base.step(v, weights, 2., noise, cfg)
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(birth=birth, developed_end=v, developed_late_ports=np.stack(trace))


def write_from_activity(body, block, generation, cfg=CFG, cycle=CYCLE):
    """E019 immediate estimator; protect its bytes through the same holding window."""
    assert body.shape == (3, 4, cfg.recipients, 2, 16, 16)
    stream = rng("E020", block, "write", generation)
    v = body.copy()
    computed = base.encode(base.correlations(v, cfg.writer_beta).mean(axis=3))
    states = []
    cue = CUES.reshape(1, 1, 1, 2, 1)
    for _ in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, np.ones((2, 16, 16)), 2., noise, cfg)
        v[..., PORTS[0]] = cue
        states.append(v.copy())
    return dict(write_states=np.stack(states), write_end=v, computed_packets=computed)


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (4, 4, cfg.recipients, 4096)
    read_packets = incoming[list(ACTIVE)].copy()
    read_packets[1] = 0  # Disable incoming-record reading, not subsequent writing.
    effective_saved = read_packets.copy()
    developed = develop(read_packets, block, generation, cfg, cycle)
    read_packets.fill(0)  # No incoming weights are available to the new writer.
    written = write_from_activity(developed["developed_end"], block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written["computed_packets"]
    outgoing[3] = 0  # Write-disabled transmission; calculation retained for audit.
    return dict(incoming=incoming.copy(), read_packets=effective_saved,
                erased_packets=read_packets, outgoing=outgoing, **developed, **written)


def assay_packets(records, block, horizon):
    # N,F,R,bytes -> N,F,R,A,bytes. Foreign swaps matched opposite-rule founders.
    own = base.decode(records)
    weights = np.repeat(own[:, :, :, None], len(ARMS), axis=3)
    weights[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    permutations = np.stack([rng("E020", block, "shuffle", horizon, f).permutation(512) for f in range(4)])
    for n in range(len(records)):
        for f in range(4):
            weights[n, f, :, 2] = own[n, f].reshape(-1, 512)[:, permutations[f]].reshape(-1, 2, 16, 16)
    weights[:, :, :, 3] = 0.
    weights[:, :, :, 4] = 1.
    return base.encode(weights), permutations


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    packets, permutations = assay_packets(records, block, horizon)
    masks = base.damage_masks(block, f"E020_h{horizon}", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E020", block, "assay", horizon)
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
