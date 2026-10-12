"""Local tissue with activity-written reciprocal edges and explicit task ports."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
import numpy as np

TAG = "E015"
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
GAINS = (1., 2.)
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")


@dataclass(frozen=True)
class Config:
    side: int = 16
    founders: int = 4
    recipients: int = 4
    teach_steps: int = 512
    capture_steps: int = 128
    read_steps: int = 512
    observe_steps: int = 32
    dt: float = .2
    noise: float = .02
    birth_sd: float = .05
    writer_beta: float = 3.
    teacher_gain: float = 2.
    margin: float = .25


CFG = Config()


def ports():
    result = np.zeros((3, 16, 16), dtype=bool)
    for p, (row, column) in enumerate(((7, 1), (3, 10), (11, 10))):
        result[p, row:row+2, column:column+2] = True
    return result


PORTS = ports()


def encode(weights):
    x = np.asarray(weights, dtype="<f8")
    assert x.shape[-3:] == (2, 16, 16) and np.isfinite(x).all()
    return np.ascontiguousarray(x).view(np.uint8).reshape(*x.shape[:-3], 4096).copy()


def decode(packets):
    assert packets.dtype == np.uint8 and packets.shape[-1] == 4096
    result = np.frombuffer(packets.tobytes(), dtype="<f8").reshape(*packets.shape[:-1], 2, 16, 16).copy()
    assert np.isfinite(result).all()
    return result


def correlations(v, beta=3.):
    x = np.tanh(beta * v)
    return np.stack((x * np.roll(x, -1, -1), x * np.roll(x, -1, -2)), axis=-3)


def neighbor_sum(v, weights):
    horizontal, vertical = weights[..., 0, :, :], weights[..., 1, :, :]
    return (horizontal * np.roll(v, -1, -1) + np.roll(horizontal, 1, -1) * np.roll(v, 1, -1)
            + vertical * np.roll(v, -1, -2) + np.roll(vertical, 1, -2) * np.roll(v, 1, -2))


def step(v, weights, gain, noise, cfg=CFG):
    # Every state-dependent interaction is on an explicit nearest-neighbor edge.
    drift = v - v**3 + gain * (neighbor_sum(v, weights) / 4. - v)
    return np.clip(v + cfg.dt * drift + cfg.noise * noise, -2., 2.)


def paired_founders(values):
    return np.repeat(values, 2, axis=0)


def teach(block, cfg=CFG):
    captured, births, ends = [], [], []
    total = np.zeros((4, 2, 16, 16))
    for c, cue in enumerate(CUES):
        random = rng(TAG, block, "teach", c)
        birth = cfg.birth_sd * paired_founders(random.standard_normal((2, 16, 16)))
        v = birth.copy(); births.append(birth)
        targets = np.stack((np.full(4, cue), RULES * cue, -RULES * cue), axis=1)
        for p in range(3): v[:, PORTS[p]] = targets[:, p, None]
        states = []
        for t in range(cfg.teach_steps):
            noise = paired_founders(random.standard_normal((2, 16, 16)))
            v = step(v, np.ones((2, 16, 16)), cfg.teacher_gain, noise, cfg)
            for p in range(3): v[:, PORTS[p]] = targets[:, p, None]
            if t >= cfg.teach_steps - cfg.capture_steps:
                states.append(v.copy())
                total += correlations(v, cfg.writer_beta)
        captured.append(np.stack(states)); ends.append(v)
    weights = total / (len(CUES) * cfg.capture_steps)
    return dict(ports=PORTS.copy(), rules=RULES.copy(), cues=CUES.copy(),
                teach_birth=np.stack(births), teach_end=np.stack(ends),
                capture_states=np.stack(captured), weights=weights, acquired=encode(weights))


def initial_packets(acquired, block, cfg=CFG):
    own = decode(acquired)
    weights = np.repeat(own[:, None], len(ARMS), axis=1)
    weights[:, 1] = own[np.arange(4) ^ 1]
    permutations = np.stack([rng(TAG, block, f, "shuffle").permutation(512) for f in range(4)])
    for f in range(4): weights[f, 2] = own[f].ravel()[permutations[f]].reshape(2, 16, 16)
    weights[:, 3] = 0.; weights[:, 4] = 1.
    return encode(np.repeat(weights[:, None], cfg.recipients, axis=1)), permutations


def damage_masks(block, phase, cfg=CFG):
    """Paired between counterfactual rules; no outcome/connectivity rejection."""
    available = np.flatnonzero(~PORTS.any(axis=0).ravel())
    squares = []
    for row in range(16):
        for column in range(16):
            mask = np.zeros((16, 16), dtype=bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): mask[(row+dy) % 16, (column+dx) % 16] = True
            if not (mask & PORTS.any(axis=0)).any(): squares.append(mask)
    random = rng(TAG, block, phase, "damage")
    masks = np.zeros((2, cfg.recipients, 3, 16, 16), dtype=bool)
    for f in range(2):
        for r in range(cfg.recipients):
            masks[f, r, 1].ravel()[random.choice(available, 24, replace=False)] = True
            masks[f, r, 2] = squares[int(random.integers(len(squares)))]
    return paired_founders(masks)


def effective_weights(packets, masks, arms=ARMS):
    # F,R,A,E,H,W -> 1,F,R,1,D,A,E,H,W, with reciprocal edge deletions.
    weights = decode(packets)[None, :, :, None, None].copy()
    alive = ~masks
    edge_alive = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    weights = weights * edge_alive[None, :, :, None, :, None]
    if "communication_off" in arms: weights[..., arms.index("communication_off"), :, :, :] = 0.
    if "source_cut" in arms:
        source_edges = np.stack((PORTS[0] | np.roll(PORTS[0], -1, -1),
                                 PORTS[0] | np.roll(PORTS[0], -1, -2)))
        weights[..., arms.index("source_cut"), :, :, :] *= ~source_edges
    return weights


def read(packets, block, phase, gains=GAINS, arms=ARMS, cfg=CFG, masks=None):
    """Only packets/public conditions enter. No rule, teaching output or prototype."""
    assert packets.shape == (4, cfg.recipients, len(arms), 4096)
    masks = damage_masks(block, phase, cfg) if masks is None else masks
    weights = effective_weights(packets, masks, arms)
    random = rng(TAG, block, phase, "reader")
    birth = cfg.birth_sd * paired_founders(random.standard_normal((2, cfg.recipients, 3, 16, 16)))
    shape = (len(gains), 4, cfg.recipients, 2, 3, len(arms), 16, 16)
    v = np.broadcast_to(birth[None, :, :, None, :, None], shape).copy()
    alive = (~masks)[None, :, :, None, :, None]
    v *= alive
    cue_values = CUES[None, None, None, :, None, None, None]
    v[..., PORTS[0]] = cue_values
    gain = np.asarray(gains).reshape(-1, 1, 1, 1, 1, 1, 1, 1)
    trace = []; late = np.zeros_like(v)
    for t in range(cfg.read_steps):
        noise = paired_founders(random.standard_normal((2, cfg.recipients, 3, 16, 16)))
        v = step(v, weights, gain, noise[None, :, :, None, :, None], cfg)
        v *= alive
        v[..., PORTS[0]] = cue_values
        trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
        if t >= cfg.read_steps - cfg.observe_steps: late += v
    return dict(packets=packets.copy(), masks=masks.copy(), birth=birth,
                end=v, late_mean=late / cfg.observe_steps, port_trace=np.stack(trace), gains=np.array(gains))


def score(port_trace, cfg=CFG):
    outputs = port_trace[-cfg.observe_steps:].mean(axis=0)
    desired = RULES[None, :, None, None, None, None] * CUES[None, None, None, :, None, None]
    success = (desired * outputs[..., 0] > cfg.margin) & (desired * outputs[..., 1] < -cfg.margin)
    margin = np.minimum(desired * outputs[..., 0], -desired * outputs[..., 1])
    return success, margin, outputs
