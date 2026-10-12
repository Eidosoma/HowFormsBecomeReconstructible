"""Three record regimes; the E015 local cell reader is unchanged."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E015_functional_inheritance import model as base
import numpy as np

CFG = base.CFG
RULES = base.RULES.copy()
CUES = base.CUES.copy()
PORTS = base.PORTS.copy()
ARMS = base.ARMS
DAMAGE = base.DAMAGE
REGIMES = ("ordinary", "consistent", "engineered")
GAIN = 2.


def episode(block, cue_index, stream_index, polarity, cfg=CFG):
    stream = rng("E016", block, "teach", stream_index)
    birth = polarity * cfg.birth_sd * base.paired_founders(stream.standard_normal((2, 16, 16)))
    v = birth.copy()
    cue = CUES[cue_index]
    targets = np.stack((np.full(4, cue), RULES * cue, -RULES * cue), axis=1)
    for p in range(3):
        v[:, PORTS[p]] = targets[:, p, None]
    states = []
    for t in range(cfg.teach_steps):
        noise = polarity * base.paired_founders(stream.standard_normal((2, 16, 16)))
        v = base.step(v, np.ones((2, 16, 16)), cfg.teacher_gain, noise, cfg)
        for p in range(3):
            v[:, PORTS[p]] = targets[:, p, None]
        if t >= cfg.teach_steps - cfg.capture_steps:
            states.append(v.copy())
    return birth, v, np.stack(states)


def teach(block, cfg=CFG):
    positive = episode(block, 0, 0, 1., cfg)
    negative = episode(block, 1, 1, 1., cfg)
    coordinated = episode(block, 1, 0, -1., cfg)
    births, ends, captured = [np.array([[positive[k], negative[k]],
                                       [positive[k], coordinated[k]]]) for k in range(3)]
    weights = []
    per_episode = []
    for regime in captured:
        total = np.zeros((4, 2, 16, 16))
        pieces = []
        for cue_states in regime:
            piece = np.zeros_like(total)
            for state in cue_states:
                corr = base.correlations(state, cfg.writer_beta)
                piece += corr
                total += corr
            pieces.append(piece / cfg.capture_steps)
        weights.append(total / (2 * cfg.capture_steps))
        per_episode.append(np.stack(pieces))
    signs = np.ones((4, 16, 16))
    signs[:, PORTS[1]] = RULES[:, None]
    signs[:, PORTS[2]] = -RULES[:, None]
    weights.append(np.stack((signs * np.roll(signs, -1, -1),
                             signs * np.roll(signs, -1, -2)), axis=-3))
    weights = np.stack(weights)
    return dict(ports=PORTS, rules=RULES, cues=CUES, teach_birth=births,
                teach_end=ends, capture_states=captured, episode_weights=np.stack(per_episode),
                weights=weights, acquired=base.encode(weights), engineered_signs=signs)


def initial_packets(acquired, block, cfg=CFG):
    own = base.decode(acquired)  # M,F,E,H,W
    weights = np.repeat(own[:, :, None], len(ARMS), axis=2)
    weights[:, :, 1] = own[:, np.arange(4) ^ 1]
    permutations = np.stack([rng("E016", block, f, "shuffle").permutation(512) for f in range(4)])
    for m in range(3):
        for f in range(4):
            weights[m, f, 2] = own[m, f].ravel()[permutations[f]].reshape(2, 16, 16)
    weights[:, :, 3] = 0.
    weights[:, :, 4] = 1.
    return base.encode(np.repeat(weights[:, :, None], cfg.recipients, axis=2)), permutations


def read(packets, block, cfg=CFG):
    assert packets.shape == (3, 4, cfg.recipients, 7, 4096)
    masks = base.damage_masks(block, "E016", cfg)
    weights = np.concatenate([base.effective_weights(panel, masks) for panel in packets], axis=0)
    stream = rng("E016", block, "reader")
    birth = cfg.birth_sd * base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None, :, None],
                        (3, 4, cfg.recipients, 2, 3, 7, 16, 16)).copy()
    alive = (~masks)[None, :, :, None, :, None]
    v *= alive
    cue_values = CUES[None, None, None, :, None, None, None]
    v[..., PORTS[0]] = cue_values
    trace = []
    late = np.zeros_like(v)
    for t in range(cfg.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 3, 16, 16)))
        v = base.step(v, weights, GAIN, noise[None, :, :, None, :, None], cfg)
        v *= alive
        v[..., PORTS[0]] = cue_values
        trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
        if t >= cfg.read_steps - cfg.observe_steps:
            late += v
    return dict(packets=packets, masks=masks, birth=birth, end=v,
                late_mean=late / cfg.observe_steps, port_trace=np.stack(trace))


def score(trace, cfg=CFG):
    values = trace[-cfg.observe_steps:].mean(axis=0)
    target = RULES[None, :, None, None, None, None] * CUES[None, None, None, :, None, None]
    a = target * values[..., 0]
    b = -target * values[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), values
