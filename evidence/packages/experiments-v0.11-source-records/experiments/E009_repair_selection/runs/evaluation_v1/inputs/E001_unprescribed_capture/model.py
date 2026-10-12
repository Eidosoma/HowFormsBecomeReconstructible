"""Target-free tissue dynamics and explicit record-only replacement boundaries."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
import numpy as np

TAG = "forms-e001-unprescribed-v1"
ARMS = ("rewrite", "foreign", "shuffled", "erased", "held", "read_off",
        "write_off", "copy", "background", "challenged")


@dataclass(frozen=True)
class Config:
    founders: int = 4
    recipients: int = 2
    side: int = 16
    formation: int = 1000
    capture: int = 1000
    read: int = 300
    write: int = 1000
    generations: int = 3
    observation_window: int = 100
    challenge_time: int = 150
    dt: float = .2
    sigma: float = .3
    norm: float = .3
    rho: float = .002
    lam: float = .001
    gain: float = .2


CFG = Config()


def centered(x):
    return x - x.mean(axis=(-2, -1), keepdims=True)


def project(x, norm=.3):
    x = centered(x)
    return x * (norm / np.maximum(x.std(axis=(-2, -1), keepdims=True), 1e-9))


def step(v, ema, ref, field, noise, *, gain=0., writing=False, cfg=CFG):
    neighbors = (np.roll(v, 1, -2) + np.roll(v, -1, -2)
                 + np.roll(v, 1, -1) + np.roll(v, -1, -1)) / 4.
    drift = centered(v - v**3 + field + (neighbors-v))
    v = np.clip(v + cfg.dt*drift + centered(cfg.sigma*noise), -2., 2.)
    ema = .9*ema + .1*v
    if gain > 0:
        v = np.clip(v + cfg.dt*centered(gain*(ref-v)), -2., 2.)
    ref = ref + cfg.rho*(v-ref)
    if np.any(writing):
        proposed = project((1-cfg.lam)*field + cfg.lam*np.tanh(ref), cfg.norm)
        field = np.where(writing, proposed, field)
    return v, ema, ref, field


def pack(field, factor=1):
    if factor not in (1, 2, 4):
        raise ValueError("Declared spatial factors are 1, 2, 4")
    field = np.asarray(field)
    if field.dtype != np.float64 or field.shape[-2:] != (16, 16) or not np.isfinite(field).all():
        raise ValueError("Finite float64 16x16 fields required")
    low = field.reshape(*field.shape[:-2], 16//factor, factor, 16//factor, factor).mean(axis=(-3, -1))
    # Preserve the full field bytes exactly when there is no bottleneck.
    if factor == 1:
        low = field
    return np.ascontiguousarray(low, dtype="<f8").view(np.uint8).reshape(*field.shape[:-2], -1).copy()


def unpack(packets, factor=1):
    packets = np.asarray(packets)
    if factor not in (1, 2, 4) or packets.dtype != np.uint8 or packets.shape[-1] != 2048//factor**2:
        raise ValueError("Invalid packet dtype or byte count")
    low = np.frombuffer(packets.tobytes(order="C"), dtype="<f8").reshape(*packets.shape[:-1], 16//factor, 16//factor)
    if not np.isfinite(low).all():
        raise ValueError("Nonfinite record")
    return np.repeat(np.repeat(low, factor, axis=-2), factor, axis=-1).copy()


def formation(block, background, cfg=CFG):
    f, s = cfg.founders, cfg.side
    bias = np.zeros((s, s))
    if background == "heterogeneous":
        bias = project(rng(TAG, block, "background").standard_normal((s, s)), cfg.norm)
    elif background != "homogeneous":
        raise ValueError("Unknown formation background")
    v = .2*centered(rng(TAG, block, "founder_birth").standard_normal((f, s, s)))
    birth = v.copy()
    ema, ref = v.copy(), v.copy()
    random = rng(TAG, block, "founder_formation")
    late = []
    for t in range(1, cfg.formation+1):
        v, ema, ref, _ = step(v, ema, ref, bias, random.standard_normal(v.shape), cfg=cfg)
        if t > cfg.formation-cfg.observation_window:
            late.append(v.copy())
    late = np.stack(late)
    return dict(background=bias, founder_birth=birth, founder_state=np.stack((v, ema, ref), axis=1),
                prototype=late.mean(axis=0),
                prototype_halves=np.stack([x.mean(axis=0) for x in np.array_split(late, 2)]),
                formation_late=late)


def capture(state, block, cfg=CFG):
    # Only body state enters. The offline founder prototype is not an argument.
    v, ema, ref = [np.repeat(state[:, i, None], 2, axis=1) for i in range(3)]
    field = np.zeros_like(v)
    random = rng(TAG, block, "capture")
    writing = np.array([True, False])[None, :, None, None]
    first = None
    for t in range(1, cfg.capture+1):
        noise = random.standard_normal((cfg.founders, 1, cfg.side, cfg.side))
        v, ema, ref, field = step(v, ema, ref, field, noise, gain=cfg.gain, writing=writing, cfg=cfg)
        if t == 1:
            first = np.stack((v, ema, ref, field), axis=2)
    return pack(field), np.stack((v, ema, ref, field), axis=2), first


def initial_packets(acquired, background, block, cfg=CFG):
    written = unpack(acquired[:, 0])
    held = unpack(acquired[:, 1])
    fields = np.repeat(written[:, None], len(ARMS), axis=1)
    fields[:, ARMS.index("foreign")] = np.roll(written, -1, axis=0)
    permutations = np.stack([rng(TAG, block, i, "shuffle").permutation(256) for i in range(cfg.founders)])
    fields[:, ARMS.index("shuffled")] = np.stack([x.ravel()[p].reshape(16,16) for x,p in zip(written, permutations)])
    fields[:, ARMS.index("erased")] = 0.
    fields[:, ARMS.index("held")] = held
    fields[:, ARMS.index("background")] = background
    packets = pack(np.repeat(fields[:, None], cfg.recipients, axis=1))
    return packets, permutations


def read_packets(packets, block, phase, *, factor=1, arms=ARMS, disable_read=False, cfg=CFG):
    """Only packet bytes plus public RNG coordinates/configuration enter."""
    field = unpack(packets, factor)
    if field.shape != (cfg.founders, cfg.recipients, len(arms), cfg.side, cfg.side):
        raise ValueError("Complete declared packet panel required")
    birth_shape = (cfg.founders, cfg.recipients, 1, cfg.side, cfg.side)
    birth = .2*centered(rng(TAG, block, phase, "birth").standard_normal(birth_shape))
    v = np.repeat(birth, len(arms), axis=2)
    ema, ref = v.copy(), v.copy()
    applied = field.copy()
    if disable_read and "read_off" in arms:
        applied[:, :, arms.index("read_off")] = 0.
    random = rng(TAG, block, phase, "read")
    # Outcome-independent challenge: exactly 64 sites per recipient.
    ranks = rng(TAG, block, phase, "challenge").random((cfg.founders, cfg.recipients, 256))
    mask = np.argsort(np.argsort(ranks, axis=-1), axis=-1) < 64
    mask = mask.reshape(cfg.founders, cfg.recipients, cfg.side, cfg.side)
    for t in range(1, cfg.read+1):
        v, ema, ref, _ = step(v, ema, ref, applied, random.standard_normal(birth_shape), cfg=cfg)
        if t == cfg.challenge_time and "challenged" in arms:
            j = arms.index("challenged")
            v[:, :, j] = np.where(mask, -v[:, :, j], v[:, :, j])
    return np.stack((v, ema, ref), axis=3), birth, mask


def generation(packets, block, number, cfg=CFG):
    state, birth, mask = read_packets(packets, block, f"g{number}", disable_read=True, cfg=cfg)
    v, ema, ref = [state[:, :, :, i].copy() for i in range(3)]
    field = np.zeros_like(v)
    field[:, :, ARMS.index("copy")] = unpack(packets)[:, :, ARMS.index("copy")]
    write_birth = np.stack((v, ema, ref, field), axis=3)
    writing = np.array([a not in ("copy", "write_off") for a in ARMS])[None, None, :, None, None]
    random = rng(TAG, block, f"g{number}", "write")
    for _ in range(cfg.write):
        noise = random.standard_normal((cfg.founders, cfg.recipients, 1, cfg.side, cfg.side))
        v, ema, ref, field = step(v, ema, ref, field, noise, gain=cfg.gain, writing=writing, cfg=cfg)
    final = np.stack((v, ema, ref, field), axis=3)
    return pack(field), dict(read=state, birth=birth, mask=mask, write_birth=write_birth, written=final)


def simulate(block, background, cfg=CFG):
    raw = formation(block, background, cfg)
    acquired, end, first = capture(raw["founder_state"], block, cfg)
    raw.update(acquired=acquired, capture_end=end, capture_first=first)
    packets, permutations = initial_packets(acquired, raw["background"], block, cfg)
    raw["permutations"] = permutations
    incoming, outgoing, histories = [], [], []
    for g in range(1, cfg.generations+1):
        incoming.append(packets)
        packets, states = generation(packets, block, g, cfg)
        outgoing.append(packets)
        histories.append(states)
    raw["incoming"], raw["outgoing"] = np.stack(incoming), np.stack(outgoing)
    for k in histories[0]:
        raw["generation_"+k] = np.stack([h[k] for h in histories])
    terminal, birth, mask = read_packets(packets, block, "terminal", cfg=cfg)
    raw.update(terminal=terminal, terminal_birth=birth, terminal_mask=mask)
    budget_states = []
    for factor in (1, 2, 4):
        written = unpack(acquired[:, 0])
        fields = np.stack((written, np.roll(written, -1, axis=0), np.zeros_like(written)), axis=1)
        payload = pack(np.repeat(fields[:, None], cfg.recipients, axis=1), factor)
        states, _, _ = read_packets(payload, block, "budget", factor=factor, arms=("own", "foreign", "zero"), cfg=cfg)
        raw[f"budget_payload_{factor}"] = payload
        budget_states.append(states)
    raw["budget_terminal"] = np.stack(budget_states)
    return raw


def checks(raw):
    copy = ARMS.index("copy")
    assert np.array_equal(raw["incoming"][:, :, :, copy], raw["outgoing"][:, :, :, copy])
    assert np.array_equal(raw["outgoing"][:-1], raw["incoming"][1:])
    assert np.array_equal(raw["acquired"][:, 1], np.zeros_like(raw["acquired"][:, 1]))
    assert np.array_equal(raw["terminal"][:, :, ARMS.index("held")], raw["terminal"][:, :, ARMS.index("erased")])
    zero_arms = [i for i,a in enumerate(ARMS) if a != "copy"]
    assert not np.any(raw["generation_write_birth"][:, :, :, zero_arms, 3])
    assert not np.any(raw["outgoing"][:, :, :, ARMS.index("write_off")])
    for name, value in raw.items():
        if np.issubdtype(value.dtype, np.floating):
            assert np.isfinite(value).all(), name
    return dict(copy_exact=True, lineage_packets_exact=True, held_erased_alias=True,
                erased_write_births=True, write_off_zero=True, finite=True,
                changed_primary_packets=int(np.any(raw["incoming"][:,:,:,0] != raw["outgoing"][:,:,:,0], axis=-1).sum()))
