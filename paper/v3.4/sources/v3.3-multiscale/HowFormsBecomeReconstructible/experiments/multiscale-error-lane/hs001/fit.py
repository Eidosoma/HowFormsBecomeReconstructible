"""The asymptote's fit (PLAN_HS001.md's rule, fixed before any long-horizon value).

On a curve y(n) over the sixteen checkpoints, equal weights:
- M1, a decay or a rise to a plateau (a free in sign; the lead's ruling 6): y = c + a rho^(n-1), the half-life
  h = ln 2 / (-ln rho). Profile least squares: on 400
  half-lives log-spaced from 0.25 to 1e5 rewrites, (c, a) are solved linearly; the grid minimum is refined by a bounded
  (golden-section) search in log h between its grid neighbours.
- M0, pure decay to zero: c = 0, fitted the same way.
- M2, two timescales plus plateau: y = c + a1 rho1^(n-1) + a2 rho2^(n-1), h1 < h2, on a 60 x 60 grid of half-life
  pairs with (c, a1, a2) linear, refined by two rounds of a local 11 x 11 sub-grid in (log h1, log h2).
Every function works on a batch of curves at once (the observed curve and its whole-block bootstrap resamples).
"""
from __future__ import annotations

import numpy as np

from . import design as D

N = np.asarray(D.CHECKPOINTS, float)
LN2 = np.log(2.0)


def basis(h):
    """rho^(n-1) for half-lives h (any shape): (..., 16)."""
    h = np.asarray(h, float)[..., None]
    return np.exp(-LN2 * (N - 1.0) / h)


def _ls(Y, X):
    """Least squares of curves Y (B, K) on per-curve designs X (B, K, p): coefficients (B, p) and SSE (B,)."""
    XtX = np.einsum("bkp,bkq->bpq", X, X)
    XtY = np.einsum("bkp,bk->bp", X, Y)
    coef = np.linalg.solve(XtX + 1e-12 * np.eye(X.shape[-1]), XtY[..., None])[..., 0]
    R = Y - np.einsum("bkp,bp->bk", X, coef)
    return coef, (R ** 2).sum(-1)


def _design(h, plateau):
    """Per-curve design for M1 (plateau) or M0: (B, 16, 2) or (B, 16, 1)."""
    e = basis(h)
    return np.stack([np.ones_like(e), e], -1) if plateau else e[..., None]


def fit1(Y, plateau=True):
    """M1 (plateau True) or M0 on curves Y (B, 16). Returns dict of (B,) arrays: c, a, h, sse, at_edge."""
    Y = np.atleast_2d(np.asarray(Y, float))
    B = Y.shape[0]
    grid = np.geomspace(*D.H_GRID[:2], D.H_GRID[2])
    sse = np.empty((B, grid.size))
    for i, h in enumerate(grid):
        X = np.broadcast_to(_design(np.array([h]), plateau)[0], (B, N.size, 2 if plateau else 1))
        sse[:, i] = _ls(Y, X)[1]
    best = sse.argmin(1)
    lo = np.log(grid[np.maximum(best - 1, 0)])
    hi = np.log(grid[np.minimum(best + 1, grid.size - 1)])
    f = lambda lh: _ls(Y, _design(np.exp(lh), plateau))[1]
    g = (np.sqrt(5.0) - 1) / 2
    a_, b_ = lo.copy(), hi.copy()
    x1, x2 = b_ - g * (b_ - a_), a_ + g * (b_ - a_)
    f1, f2 = f(x1), f(x2)
    for _ in range(60):
        left = f1 < f2
        b_ = np.where(left, x2, b_)
        a_ = np.where(left, a_, x1)
        x2n = np.where(left, x1, a_ + g * (b_ - a_))
        x1n = np.where(left, b_ - g * (b_ - a_), x2)
        x1, x2 = x1n, x2n
        f1, f2 = f(x1), f(x2)
    lh = (a_ + b_) / 2
    cand = np.stack([lh, np.log(grid[best])], 1)
    fc = np.stack([f(cand[:, 0]), f(cand[:, 1])], 1)
    lh = np.where(fc[:, 0] <= fc[:, 1], cand[:, 0], cand[:, 1])
    h = np.exp(lh)
    coef, s = _ls(Y, _design(h, plateau))
    c = coef[:, 0] if plateau else np.zeros(B)
    a = coef[:, 1] if plateau else coef[:, 0]
    return {"c": c, "a": a, "h": h, "sse": s, "at_edge": (best == 0) | (best == grid.size - 1)}


def fit2(Y):
    """M2 on curves Y (B, 16). Returns dict of (B,) arrays: c, a1, h1, a2, h2, sse."""
    Y = np.atleast_2d(np.asarray(Y, float))
    B = Y.shape[0]
    g = np.log(np.geomspace(*D.H2_GRID[:2], D.H2_GRID[2]))
    pairs = np.array([(i, j) for i in range(g.size) for j in range(i + 1, g.size)])

    def sse_at(l1, l2):
        X = np.stack([np.ones((l1.size, N.size)), basis(np.exp(l1)), basis(np.exp(l2))], -1)
        return _ls(Y, X)

    sse = np.empty((B, len(pairs)))
    for k, (i, j) in enumerate(pairs):
        X = np.broadcast_to(np.stack([np.ones(N.size), basis(np.exp(g[i])), basis(np.exp(g[j]))], -1), (B, N.size, 3))
        sse[:, k] = _ls(Y, X)[1]
    b = sse.argmin(1)
    l1, l2 = g[pairs[b, 0]], g[pairs[b, 1]]
    step = g[1] - g[0]
    for _ in range(2):
        offs = np.linspace(-step, step, 11)
        best_s = np.full(B, np.inf)
        bl1, bl2 = l1.copy(), l2.copy()
        for d1 in offs:
            for d2 in offs:
                t1, t2 = l1 + d1, l2 + d2
                ok = t1 < t2
                s = np.where(ok, sse_at(np.where(ok, t1, l1), np.where(ok, t2, l2))[1], np.inf)
                better = s < best_s
                best_s = np.where(better, s, best_s)
                bl1, bl2 = np.where(better, t1, bl1), np.where(better, t2, bl2)
        l1, l2 = bl1, bl2
        step = step / 5
    coef, s = sse_at(l1, l2)
    return {"c": coef[:, 0], "a1": coef[:, 1], "h1": np.exp(l1), "a2": coef[:, 2], "h2": np.exp(l2), "sse": s}


def summarise(curves, boot_curves):
    """The rule's report for one curve (16,) and its bootstrap curves (BOOT, 16)."""
    allc = np.vstack([curves[None], boot_curves])
    m1, m0, m2 = fit1(allc, True), fit1(allc, False), fit2(allc)
    q = lambda x: [float(np.quantile(x[1:], 0.025)), float(np.quantile(x[1:], 0.975))]
    rep = {"M1": {k: float(m1[k][0]) for k in ("c", "a", "h", "sse")} | {"at_edge": bool(m1["at_edge"][0])},
           "M0": {k: float(m0[k][0]) for k in ("a", "h", "sse")} | {"at_edge": bool(m0["at_edge"][0])},
           "M2": {k: float(m2[k][0]) for k in ("c", "a1", "h1", "a2", "h2", "sse")}}
    for k in ("c", "a", "h"):
        rep["M1"][k + "_ci95"] = q(m1[k])
    for k in ("a", "h"):
        rep["M0"][k + "_ci95"] = q(m0[k])
    for k in ("c", "a1", "h1", "a2", "h2"):
        rep["M2"][k + "_ci95"] = q(m2[k])
    rem = m1["a"] * np.exp(-LN2 * (D.HORIZON - 1) / m1["h"])
    rep["M1"]["remaining_at_horizon"] = float(rem[0])
    rep["M1"]["remaining_at_horizon_ci95"] = q(rem)
    rep["sse_M0_minus_M1"] = float(m0["sse"][0] - m1["sse"][0])
    rep["sse_M0_minus_M1_ci95"] = q(m0["sse"] - m1["sse"])
    rep["sse_M1_minus_M2"] = float(m1["sse"][0] - m2["sse"][0])
    rep["sse_M1_minus_M2_ci95"] = q(m1["sse"] - m2["sse"])
    li = [D.CHECKPOINTS.index(n) for n in D.LATE]
    late = allc[:, li].mean(1)
    slope = allc[:, D.CHECKPOINTS.index(256)] - allc[:, D.CHECKPOINTS.index(128)]
    rep["late_mean"], rep["late_mean_ci95"] = float(late[0]), q(late)
    rep["late_slope"], rep["late_slope_ci95"] = float(slope[0]), q(slope)
    identified = rep["M1"]["h_ci95"][1] <= D.IDENTIFIED_H_MAX
    above = identified and rep["M1"]["c_ci95"][0] > 0
    below = identified and rep["M1"]["c_ci95"][1] < 0
    m2_zero = rep["M2"]["c_ci95"][0] <= 0 <= rep["M2"]["c_ci95"][1]
    rep["identified"] = bool(identified)
    rep["reading"] = ("a plateau is not identified within 256 rewrites" if not identified else
                      "a plateau above zero" + (" (M2 absorbs it into a slow second timescale)" if m2_zero else "")
                      if above else "a plateau below zero" if below else "a plateau indistinguishable from zero")
    return rep
