"""Fixed timing intervention on unchanged E016 acquisition and record controls."""
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E016_teaching_consistency import model as acquisition
from E015_functional_inheritance import model as base
import numpy as np

CFG = base.CFG
RULES = base.RULES.copy()
CUES = base.CUES.copy()
PORTS = base.PORTS.copy()
ARMS = base.ARMS
DAMAGE = base.DAMAGE
REGIMES = ("consistent", "engineered")
CONDITIONS = ("baseline", "extended", "staged")
GAIN = 2.


@dataclass(frozen=True)
class Timing:
    baseline_steps: int = 512
    total_steps: int = 2048
    settling_steps: int = 256


TIMING = Timing()


def initial_packets(source, block, cfg=CFG):
    packets, permutations = acquisition.initial_packets(source["acquired"], block, cfg)
    return packets[[1, 2]].copy(), permutations


def unamplified(v, weights, noise, cfg=CFG):
    drift = -v**3 + GAIN*(base.neighbor_sum(v, weights)/4. - v)
    return np.clip(v + cfg.dt*drift + cfg.noise*noise, -2., 2.)


def read(packets, block, cfg=CFG, timing=TIMING):
    assert packets.shape == (2, 4, cfg.recipients, 7, 4096)
    assert cfg.observe_steps <= timing.baseline_steps < timing.total_steps
    assert 0 < timing.settling_steps < timing.total_steps
    masks = base.damage_masks(block, "E017", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E017", block, "reader")
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
    # B,M,F,R,C,D,A,H,W: two actual branches, three scored conditions.
    v = np.broadcast_to(birth[None, None, :, :, None, :, None],
                        (2, 2, 4, cfg.recipients, 2, 3, 7, 16, 16)).copy()
    active = (~masks)[None, None, :, :, None, :, None]
    cue = CUES[None, None, None, None, :, None, None, None]
    v *= active
    v[..., PORTS[0]] = cue
    trace = []
    endpoints = np.empty((3, *v.shape[1:]))
    late = np.zeros_like(endpoints)
    windows = ((0, timing.baseline_steps), (0, timing.total_steps), (1, timing.total_steps))
    for t in range(timing.total_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
        expanded = noise[None, :, :, None, :, None]
        if t < timing.settling_steps:
            v[0] = base.step(v[0], weights, GAIN, expanded, cfg)
            v[1] = unamplified(v[1], weights, expanded, cfg)
        else:
            v = base.step(v, weights[None], GAIN, expanded[None], cfg)
        v *= active
        v[..., PORTS[0]] = cue
        trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
        for k, (branch, stop) in enumerate(windows):
            if stop-cfg.observe_steps <= t < stop: late[k] += v[branch]
            if t == stop-1: endpoints[k] = v[branch]
    return dict(packets=packets, masks=masks, birth=birth, endpoints=endpoints,
                late_mean=late/cfg.observe_steps, port_trace=np.stack(trace))


def score(trace, cfg=CFG, timing=TIMING):
    values = np.stack([trace[stop-cfg.observe_steps:stop, branch].mean(axis=0)
                       for branch, stop in ((0, timing.baseline_steps), (0, timing.total_steps), (1, timing.total_steps))])
    target = RULES[None, None, :, None, None, None, None]*CUES[None, None, None, None, :, None, None]
    a = target*values[..., 0]
    b = -target*values[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), values
