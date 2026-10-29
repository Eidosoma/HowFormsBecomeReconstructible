"""Motile tissue: Kawasaki swap dynamics on the frozen identity sheet.

Cells (lattice sites carrying their V as cargo) swap with neighbors under
Metropolis acceptance on:  J * d(sign-mismatch)  [rung G, differential
adhesion — like prefers like]  +  chi * d(|E - V|)  [rung H, chemotaxis
toward the organizer's expectation].  Swaps exchange whole cells, so total
V is conserved EXACTLY by construction. The motility phase uses a
DEDICATED rng; switching it off skips the phase and consumes nothing —
the lesion is stream-exact on the identity dynamics (the E39 pattern).

Identity layer: `ladder_web.engine.ladder_step` at rung "D", verbatim."""

from __future__ import annotations

import numpy as np

from ladder_web.config import LadderConfig
from ladder_web.engine import ladder_step

from .config import GrowConfig


def _pair_delta(V, E, axis, parity, config: GrowConfig, rung: str):
    """Energy change for swapping each disjoint neighbor pair along `axis`
    (left slot at parity indices; partner = next index, torus wrap).
    Returns (delta, pair_mask) in the left-slot frame."""
    other = -2 if axis == -1 else -1
    n = V.shape[axis]
    index = np.arange(n)
    pair_mask = np.zeros(V.shape, dtype=bool)
    sel = (index % 2) == parity
    if axis == -1:
        pair_mask[..., sel] = True
    else:
        pair_mask[..., sel, :] = True

    def unlike(p, q):
        return np.abs(np.sign(p) - np.sign(q)) / 2.0

    s = V
    sR = np.roll(V, -1, axis)          # partner value, left frame
    a_nbs = (np.roll(s, 1, axis), np.roll(s, 1, other), np.roll(s, -1, other))
    b_nbs = (
        np.roll(s, -2, axis),
        np.roll(np.roll(s, -1, axis), 1, other),
        np.roll(np.roll(s, -1, axis), -1, other),
    )
    before = sum(unlike(s, nb) for nb in a_nbs) + sum(unlike(sR, nb) for nb in b_nbs)
    after = sum(unlike(sR, nb) for nb in a_nbs) + sum(unlike(s, nb) for nb in b_nbs)
    delta = config.adhesion_j * (after - before)
    if rung == "H" and E is not None:
        # Chemotaxis round 2 (recorded): the interpolated expectation's
        # magnitudes (~0.15) made the chemotactic energy 20x weaker than
        # adhesion — cells must read the field's DIRECTION, not its
        # magnitude (saturated receptors): chemotax on sign(E).
        E_sign = np.sign(E[None] if E.ndim == 2 else E)
        E_right = np.roll(E_sign, -1, axis)
        d_before = np.abs(E_sign - np.sign(s)) + np.abs(E_right - np.sign(sR))
        d_after = np.abs(E_sign - np.sign(sR)) + np.abs(E_right - np.sign(s))
        delta = delta + config.chemotaxis_chi * (d_after - d_before)
    return delta, pair_mask


def motility_phase(V, E, config: GrowConfig, rung: str, mrng):
    """One Kawasaki phase along a random axis/parity; returns swapped V."""
    axis = -1 if mrng.random() < 0.5 else -2
    parity = int(mrng.integers(0, 2))
    delta, pair_mask = _pair_delta(V, E, axis, parity, config, rung)
    proposed = pair_mask & (mrng.random(V.shape) < config.proposal_fraction)
    accept = (delta <= 0) | (
        mrng.random(V.shape) < np.exp(-np.clip(delta, 0, 50) / config.temperature)
    )
    do_swap = proposed & accept
    partner = np.roll(V, -1, axis)
    swapped_left = np.where(do_swap, partner, V)
    receive = np.roll(do_swap, 1, axis)
    original_left = np.roll(V, 1, axis)
    V_new = np.where(receive, original_left, swapped_left)
    return V_new


def growing_step(V, ema, theta, tissue, ladder: LadderConfig,
                 config: GrowConfig, rung: str, rng, mrng, fields,
                 clamp=None, motility_on=True):
    V, ema, S = ladder_step(V, ema, theta, tissue, ladder, "D", rng, fields, clamp)
    if rung != "D" and motility_on:
        E = fields[3] if (fields is not None and len(fields) > 3) else None
        for _ in range(config.phases_per_sweep):
            V = motility_phase(V, E, config, rung, mrng)
    return V, ema, S


def interface_length(V) -> np.ndarray:
    """Unlike-neighbor bond count per future (the Steinberg metric)."""
    s = np.sign(V)
    total = np.zeros(V.shape[0])
    for ax in (-1, -2):
        total += (np.abs(s - np.roll(s, 1, ax)) / 2.0).sum(axis=(-2, -1))
    return total
