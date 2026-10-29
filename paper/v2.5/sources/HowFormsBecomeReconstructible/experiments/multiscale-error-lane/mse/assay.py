"""Acquisition, damage and fresh-recipient reading with explicit RNG addresses.

Every stream is addressed by (tag, block, message, parent, phase, ...) and never by arm,
route or damage condition, so all arms of a case replay identical draws. Identity ranges
are reserved before sampling; engineering identities never enter development or
confirmation analyses.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .engine import ROUTES, Route, State, run
from .native import NATIVE, Params, address, center, half_plane, thresholds
from .ops import bands

TAG = "mse-v1"
RANGES = {"engineering": range(900000, 901000),
          "development": range(910000, 911000),
          "confirmation": range(920000, 930000)}
BIRTH_SCALE = 0.2
REFERENCE_BOUND = 2.0     # declared reference-domain rule: damaged R is clipped like V


@dataclass(frozen=True)
class Case:
    block: int
    message: int
    parent: int

    def key(self):
        return (self.block, self.message, self.parent)


def enrol(blocks, messages=(0, 1, 2, 3), parents=(0, 1), purpose="engineering"):
    allowed = RANGES[purpose]
    if any(b not in allowed for b in blocks):
        raise ValueError(f"Blocks outside the reserved {purpose} range")
    return [Case(b, m, r) for b in blocks for m in messages for r in parents]


class Noise:
    """Standard normals for each case's addressed stream, stacked on the batch axis."""

    def __init__(self, tag, cases, *stream, repeat=1, chunk=100):
        self.gens = [address(tag, *c.key(), *stream) for c in cases]
        self.repeat, self.chunk, self.buf = repeat, chunk, None

    def __call__(self, t):
        i = (t - 1) % self.chunk
        if i == 0:
            self.buf = np.stack([g.standard_normal((self.chunk, 16, 16)) for g in self.gens], 1)
        z = self.buf[i]
        return np.repeat(z, self.repeat, axis=0) if self.repeat > 1 else z


def spread(tag, block):
    """Per-tissue theta spread as in setpoint_rewrite.runner.tissue_config, U(0.15, 0.30).

    That function also draws a well asymmetry U(-0.05, 0.05); a uniform term cancels in
    the conserved drift (legacy check: |dV| <= 2.2e-15 after 1000 updates), so it is omitted.
    """
    return float(address(tag, "tissue", block).uniform(0.15, 0.30))


def theta(tag, cases, p: Params = NATIVE, per_tissue: bool = False):
    """The block's environmental field, recreated from the public block address only.

    per_tissue: draw each block's spread as the L15/L17 lineage did, instead of p's.
    """
    def field(b):
        q = replace(p, threshold_spread=spread(tag, b)) if per_tissue else p
        return thresholds(address(tag, "theta", b), q)
    fields = {b: field(b) for b in {c.block for c in cases}}
    return np.stack([fields[c.block] for c in cases])


def templates(cases, amplitude=1.2, shift=(0, 0)):
    """Taught fields; a shift moves every boundary off the aligned pooling grid."""
    return np.stack([np.roll(half_plane(c.message, amplitude), shift, axis=(0, 1)) for c in cases])


def birth(tag, cases, *stream):
    return np.stack([BIRTH_SCALE * center(address(tag, *c.key(), *stream).standard_normal((16, 16)))
                     for c in cases])


def acquire(tag, cases, settle=120, teach=1000, amplitude=1.2, p: Params = NATIVE, shift=(0, 0),
            per_tissue=False):
    """Native settling from a message-independent birth, then imposed-body teaching (L15)."""
    th = theta(tag, cases, p, per_tissue)
    V = birth(tag, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(tag, cases, "settle"), Route(capture=None), settle, p)
    s = run(s, th, Noise(tag, cases, "teach"), Route(capture=None), teach, p,
            imposed=templates(cases, amplitude, shift))
    return State(s.V, s.ema, s.R, np.zeros_like(V)), th


def band_damage(tag, cases, target, band, rms):
    """Independent Gaussian field projected into one band, scaled to pre-clipping RMS."""
    out = []
    for c in cases:
        x = bands(address(tag, *c.key(), "damage", target, band).standard_normal((16, 16)))[band]
        out.append(x * (rms / np.sqrt((x ** 2).mean())))
    return np.stack(out)


def injure(s: State, body=None, reference=None) -> State:
    V = s.V if body is None else np.clip(s.V + body, -NATIVE.bound, NATIVE.bound)
    R = s.R if reference is None else np.clip(s.R + reference, -REFERENCE_BOUND, REFERENCE_BOUND)
    return State(V, s.ema.copy(), R, s.Q.copy(), s.snapshot)


def read(tag, cases, packets, th, recipients=4, updates=1000, p: Params = NATIVE, every=0, record=None):
    """Fresh recipients hold the packet as their reference; only the packet is case-dependent.

    Returns final bodies shaped (cases, recipients, 16, 16).
    """
    n = len(cases)
    V = np.concatenate([birth(tag, cases, "recipient", r, "birth")[:, None] for r in range(recipients)], 1)
    V = V.reshape(n * recipients, 16, 16)
    R = np.repeat(np.asarray(packets), recipients, axis=0)
    noises = [Noise(tag, cases, "recipient", r, "read") for r in range(recipients)]
    noise = lambda t: np.stack([nz(t) for nz in noises], 1).reshape(n * recipients, 16, 16)
    s = State(V, V.copy(), R, np.zeros_like(V))
    s = run(s, np.repeat(th, recipients, axis=0), noise, Route(reference=None, capture=None),
            updates, p, every=every, record=record)
    return s.V.reshape(n, recipients, 16, 16)


__all__ = ["TAG", "RANGES", "Case", "enrol", "Noise", "theta", "templates", "birth",
           "acquire", "band_damage", "injure", "read", "ROUTES"]
