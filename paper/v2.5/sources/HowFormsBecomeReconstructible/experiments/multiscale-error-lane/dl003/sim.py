"""DL003's tissue: DL001's body (dl001.sim.body, unchanged) reading positional information at 64 cells, laid out as a
boundary, scattered cells or a cluster, on a 32-site sheet of stripes of period 8 (S4).

A run advances every arm of one body as branches (arm-major: index = arm x cases + case), all reading the case's noise
stream, so arms and bodies are paired within a case. In panel B the sheet starts from newborn noise; an arm with a
front activates cells by their distance from its boundary, one line per `front` updates: cells ahead of the front are
held at 0 (V and its moving average) and start from their newborn values when the front reaches them. The record is
the acquired one, read only at the arm's cells; the body never reads the template.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from mse.assay import enrol
from mse.native import NATIVE, address
from msegrid.core import Stream, acquire, birth

from . import design as D


def prepare(block, purpose):
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = np.stack([D.AMPLITUDE * S.template("S4", c.message, D.SIDE, block) for c in cases])
    V, ema, R0, th = acquire(D.TAG, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), D.SIDE,
                             settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T


def ring_dist(lines):
    """Distance of every index on the periodic ring from the nearest of the given lines."""
    ar = np.arange(D.SIDE)
    return (np.abs((ar[:, None] - np.asarray(lines)[None, :] + D.SIDE // 2) % D.SIDE - D.SIDE // 2)).min(1)


def geometry(cases):
    """Per case: the 64-cell masks of each geometry, and distance maps from the par and perp boundaries (distance
    across the boundary, 0 on it) and from the cluster (Chebyshev). Kinds 0 and 2 change sign across columns."""
    n, k = D.SIDE, len(cases)
    masks = {g: np.zeros((k, n, n), bool) for g in D.GEOMETRIES}
    dist = {g: np.zeros((k, n, n), int) for g in ("par", "perp", "cluster")}
    for j, c in enumerate(cases):
        g = address(D.TAG, *c.key(), "geometry")
        masks["scatter"][j].flat[g.permutation(n * n)[:D.N_ANCHOR]] = True
        w = int(g.integers(0, n // 4))                          # the pattern's walls lie between 4w - 1 and 4w
        wall = [(4 * w - 1) % n, (4 * w) % n]
        o = int(g.integers(0, n))
        across = [o, (o + 1) % n]
        dw, da = ring_dist(wall), ring_dist(across)
        if c.message % 2 == 0:
            masks["par"][j][:, wall] = True
            dist["par"][j] = np.broadcast_to(dw[None, :], (n, n))
            masks["perp"][j][across, :] = True
            dist["perp"][j] = np.broadcast_to(da[:, None], (n, n))
        else:
            masks["par"][j][wall, :] = True
            dist["par"][j] = np.broadcast_to(dw[:, None], (n, n))
            masks["perp"][j][:, across] = True
            dist["perp"][j] = np.broadcast_to(da[None, :], (n, n))
        a, b = (int(x) for x in g.integers(0, n, 2))
        ri, ci = np.arange(a, a + 8) % n, np.arange(b, b + 8) % n
        masks["cluster"][j][np.ix_(ri, ci)] = True
        dist["cluster"][j] = np.maximum(ring_dist(ri)[:, None], ring_dist(ci)[None, :])
    return masks, dist


def newborn(cases):
    return birth(D.TAG, cases, "newborn-sheet", side=D.SIDE)


def branches(arms, cases, V0, ema0, panel):
    """Initial V and moving average, per-site gain, and front distance (-1 where no front) for every arm."""
    k, nb, n = len(cases), len(arms), D.SIDE
    masks, dist = geometry(cases)
    if panel == "B":
        nbv = newborn(cases)
        V, E = np.tile(nbv, (nb, 1, 1)), np.tile(nbv, (nb, 1, 1))
    else:
        V, E = np.tile(V0, (nb, 1, 1)), np.tile(ema0, (nb, 1, 1))
    gain = np.zeros((nb * k, n, n))
    fdist = np.full((nb * k, n, n), -1)
    every = np.zeros(nb * k)
    for i, arm in enumerate(arms):
        sl = slice(i * k, (i + 1) * k)
        if arm.geo == "full":
            gain[sl] = D.G_FULL
        elif arm.geo in masks:
            gain[sl] = D.G_ANCHOR * masks[arm.geo]
        if arm.front:
            fdist[sl] = dist[arm.origin or arm.geo]
            every[sl] = arm.front
    live = (fdist < 0) | (fdist == 0)
    return np.where(live, V, 0.0), np.where(live, E, 0.0), gain, fdist, every, masks, dist


def profile(ok, dmap, dmax):
    """Mean agreement at each distance 0..dmax, per branch."""
    return np.stack([(ok & (dmap == d)).sum((-2, -1)) / np.maximum((dmap == d).sum((-2, -1)), 1)
                     for d in range(dmax + 1)], -1)


def run(body, arms, cases, V0, ema0, R0, th, T, theta, panel, snaps, window=None):
    """Advance one body under every arm for D.WINDOW updates (or `window`, for the checks); endpoints per snapshot,
    distance profiles and work at the end, and the final V and moving average."""
    window = window or D.WINDOW
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(arms)
    idx = np.tile(np.arange(k), nb)
    V, E, gain, fdist, every, masks, dist = branches(arms, cases, V0, ema0, panel)
    frontal = fdist >= 0
    live = ~frontal | (fdist == 0)
    nbv = np.tile(newborn(cases), (nb, 1, 1)) if frontal.any() else None
    r = np.tile(R0, (nb, 1, 1))
    Tb, thb = np.tile(T, (nb, 1, 1)), (th * theta)[idx]
    p = replace(NATIVE, sigma=D.SIGMA)
    st = Stream(D.TAG, cases, "future", panel, side=D.SIDE)
    out = {"sign": [], "shift": [], "spacing": []}
    wc, nwork, buf = np.zeros(nb * k), 0, None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        if nbv is not None:
            now = ~frontal | (fdist * every[:, None, None] <= t)
            born = now & ~live
            V = np.where(born, nbv, np.where(now, V, 0.0))
            E = np.where(born, nbv, np.where(now, E, 0.0))
            live = now
        if t > window // 2:
            wc += np.abs(p.dt * d).mean((-2, -1))
            nwork += 1
        if t in snaps:
            out["sign"].append(S.sign(V, Tb))
            out["shift"].append(S.best_shift(V, Tb))
            out["spacing"].append(S.spacing(V))
    res = {key: np.array(v) for key, v in out.items()}
    ok = (V > 0) == (Tb > 0)
    for g, dmax in D.DMAX.items():
        res[f"prof_{g}"] = profile(ok, np.tile(dist[g], (nb, 1, 1)), dmax)
    res.update(w_corr=wc / max(nwork, 1), qual=S.qual(V, Tb), final=V, final_ema=E)
    return res
