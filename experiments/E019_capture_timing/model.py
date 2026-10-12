"""Matched snapshot timing and time-averaged capture at one erased-record boundary."""
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
WRITERS = ("immediate", "delayed", "averaged")
CONDITIONS = WRITERS + ("protected_copy",) + tuple(x+"_read_blocked" for x in WRITERS) + ("write_blocked",)
PANELS = ((0, "initial"),) + tuple((1, name) for name in CONDITIONS)


@dataclass(frozen=True)
class Cycle:
    read_steps: int = 2048
    settling_steps: int = 256
    write_steps: int = 128
    generations: int = 1


CYCLE = Cycle()


def develop(packets, block, cfg=CFG, cycle=CYCLE):
    """Normal and read-blocked bodies, paired across all candidate writers."""
    assert packets.shape == (2, 4, cfg.recipients, 4096)
    weights = base.decode(packets)[:, :, :, None]
    stream = rng("E019", block, "develop", 1)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (2, 4, cfg.recipients, 2, 16, 16)).copy()
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


def write_from_activity(body, block, cfg=CFG, cycle=CYCLE):
    """Only current body state enters; no record, rule, desired output or scorer."""
    assert body.shape == (2, 4, cfg.recipients, 2, 16, 16)
    v = body.copy()
    immediate = base.correlations(v, cfg.writer_beta).mean(axis=3)
    stream = rng("E019", block, "write", 1)
    total = np.zeros((*v.shape[:-2], 2, 16, 16))
    states = []
    cue = CUES.reshape(1, 1, 1, 2, 1)
    for _ in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, np.ones((2, 16, 16)), 2., noise, cfg)
        v[..., PORTS[0]] = cue
        states.append(v.copy())
        total += base.correlations(v, cfg.writer_beta)
    delayed = base.correlations(v, cfg.writer_beta).mean(axis=3)
    averaged = total.mean(axis=3)/cycle.write_steps
    computed = base.encode(np.stack((immediate, delayed, averaged)))
    return dict(write_states=np.stack(states), write_end=v, computed_packets=computed)


def replace_record(incoming, block, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (4, cfg.recipients, 4096)
    read_packets = np.repeat(incoming[None], 2, axis=0)
    read_packets[1] = 0
    effective_saved = read_packets.copy()
    developed = develop(read_packets, block, cfg, cycle)
    read_packets.fill(0)
    written = write_from_activity(developed["developed_end"], block, cfg, cycle)
    packets = written["computed_packets"]
    outgoing = np.stack([*packets[:, 0], incoming.copy(), *packets[:, 1], np.zeros_like(incoming)])
    return dict(incoming=incoming.copy(), read_packets=effective_saved, erased_packets=read_packets,
                outgoing=outgoing, **developed, **written)


def assay_packets(records, block, horizon):
    own = base.decode(records)
    weights = np.repeat(own[:, :, :, None], len(ARMS), axis=3)
    weights[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    permutations = np.stack([rng("E019", block, "shuffle", horizon, f).permutation(512) for f in range(4)])
    for n in range(len(records)):
        for f in range(4):
            weights[n, f, :, 2] = own[n, f].reshape(-1, 512)[:, permutations[f]].reshape(-1, 2, 16, 16)
    weights[:, :, :, 3] = 0.
    weights[:, :, :, 4] = 1.
    return base.encode(weights), permutations


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    packets, permutations = assay_packets(records, block, horizon)
    masks = base.damage_masks(block, f"E019_h{horizon}", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E019", block, "assay", horizon)
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
