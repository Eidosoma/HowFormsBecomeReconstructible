"""HS002's fit and readings (PLAN_HS002.md, fixed before any value past rewrite 256).

HS001's procedure (hs001.fit) with the checkpoints as an argument: M1 c + a rho^(n-1) (a free in sign) and M0 (c = 0)
by profile least squares on 400 log-spaced half-lives with a golden-section refinement; M2 (two timescales and a
plateau) on a 60 x 60 grid with two local refinements. On HS001's sixteen checkpoints it reproduces hs001.fit exactly
(Q7).

The readings are rule AH, the lead's ruling on Q7 (1 November 2026; PLAN_HS002.md's amendment), for any curve X read,
in order:
1. a slow drift: X(1024) - X(512)'s 95% interval lies entirely below zero;
2. a plateau within 1,024 rewrites: M1 identified (h's 95% upper bound <= 256) with its c interval above zero; M2's
   c interval above zero wherever M2's slow timescale is identified (h2's 95% upper bound <= 256), not counted where
   it is not; and the level holds through the horizon: with LB the 95% lower bound of X(1024) - X(512) and X(512) the
   full-sample value at 512, LB >= 0, or X(512) + LB > 0 and 512 ln 2 / ln(X(512) / (X(512) + LB)) >= 1,024;
3. decay to zero or below within 1,024 rewrites: M1 identified, its c interval not above zero;
4. neither resolved, with its reasons named.
The drift bound and the reading by the rule as first declared (`reading_declared`) are reported beside every reading.
"""
from __future__ import annotations

import numpy as np

from . import design as D

LN2 = np.log(2.0)


def basis(h, N):
    h = np.asarray(h, float)[..., None]
    return np.exp(-LN2 * (N - 1.0) / h)


def _ls(Y, X):
    XtX = np.einsum("bkp,bkq->bpq", X, X)
    XtY = np.einsum("bkp,bk->bp", X, Y)
    coef = np.linalg.solve(XtX + 1e-12 * np.eye(X.shape[-1]), XtY[..., None])[..., 0]
    R = Y - np.einsum("bkp,bp->bk", X, coef)
    return coef, (R ** 2).sum(-1)


def _design(h, plateau, N):
    e = basis(h, N)
    return np.stack([np.ones_like(e), e], -1) if plateau else e[..., None]


def fit1(Y, N, plateau=True):
    Y = np.atleast_2d(np.asarray(Y, float))
    N = np.asarray(N, float)
    B = Y.shape[0]
    grid = np.geomspace(*D.H_GRID[:2], D.H_GRID[2])
    sse = np.empty((B, grid.size))
    for i, h in enumerate(grid):
        X = np.broadcast_to(_design(np.array([h]), plateau, N)[0], (B, N.size, 2 if plateau else 1))
        sse[:, i] = _ls(Y, X)[1]
    best = sse.argmin(1)
    lo = np.log(grid[np.maximum(best - 1, 0)])
    hi = np.log(grid[np.minimum(best + 1, grid.size - 1)])
    f = lambda lh: _ls(Y, _design(np.exp(lh), plateau, N))[1]
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
    coef, s = _ls(Y, _design(h, plateau, N))
    c = coef[:, 0] if plateau else np.zeros(B)
    a = coef[:, 1] if plateau else coef[:, 0]
    return {"c": c, "a": a, "h": h, "sse": s, "at_edge": (best == 0) | (best == grid.size - 1)}


def fit2(Y, N):
    Y = np.atleast_2d(np.asarray(Y, float))
    N = np.asarray(N, float)
    B = Y.shape[0]
    g = np.log(np.geomspace(*D.H2_GRID[:2], D.H2_GRID[2]))
    pairs = np.array([(i, j) for i in range(g.size) for j in range(i + 1, g.size)])

    def sse_at(l1, l2):
        X = np.stack([np.ones((l1.size, N.size)), basis(np.exp(l1), N), basis(np.exp(l2), N)], -1)
        return _ls(Y, X)

    sse = np.empty((B, len(pairs)))
    for k, (i, j) in enumerate(pairs):
        X = np.broadcast_to(np.stack([np.ones(N.size), basis(np.exp(g[i]), N), basis(np.exp(g[j]), N)], -1), (B, N.size, 3))
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


def reading_declared(rep, h_max=D.IDENTIFIED_H_MAX):
    """The readings as first declared in PLAN_HS002.md (reported beside rule AH): (reading, reasons)."""
    if "d1024_minus_d512_ci95" in rep and rep["d1024_minus_d512_ci95"][1] < 0:
        return "a slow drift", []
    ident = rep["M1"]["h_ci95"][1] <= h_max
    if ident and rep["M1"]["c_ci95"][0] > 0 and rep["M2"]["c_ci95"][0] > 0:
        return "a plateau within 1,024 rewrites", []
    if ident and rep["M1"]["c_ci95"][0] <= 0:
        return "decay to zero or below within 1,024 rewrites", []
    return "neither resolved", [r for r, bad in (("M1 not identified", not ident),
                                                 ("M2's c not above zero", rep["M2"]["c_ci95"][0] <= 0)) if bad]


def drift_bound(x512, lb):
    """(half-life or None, text): the slowest decay toward zero that X(1024) - X(512)'s 95% lower bound leaves possible."""
    if lb >= 0:
        return None, "none needed"
    if x512 + lb <= 0:
        return None, "a decay to zero within the second half is not excluded"
    h = 512 * LN2 / np.log(x512 / (x512 + lb))
    return float(h), f"a decay toward zero needs a half-life of at least {h:.0f} rewrites"


def level_holds(x512, lb):
    return bool(lb >= 0 or (x512 + lb > 0 and 512 * LN2 / np.log(x512 / (x512 + lb)) >= D.HORIZON))


def reading(rep, x512, h_max=D.IDENTIFIED_H_MAX):
    """Rule AH (the lead's ruling on Q7): (reading, reasons)."""
    if rep["d1024_minus_d512_ci95"][1] < 0:
        return "a slow drift", []
    ident = rep["M1"]["h_ci95"][1] <= h_max
    m2_identified = rep["M2"]["h2_ci95"][1] <= h_max
    m2_ok = rep["M2"]["c_ci95"][0] > 0 if m2_identified else True
    held = level_holds(x512, rep["d1024_minus_d512_ci95"][0])
    if ident and rep["M1"]["c_ci95"][0] > 0 and m2_ok and held:
        return "a plateau within 1,024 rewrites", []
    if ident and rep["M1"]["c_ci95"][0] <= 0:
        return "decay to zero or below within 1,024 rewrites", []
    return "neither resolved", [r for r, bad in (("M1 not identified", not ident), ("M2's identified c not above zero", not m2_ok),
                                                 ("the level not shown to hold", not held)) if bad]


def summarise(curve, boot, checkpoints=D.CHECKPOINTS, h_max=D.IDENTIFIED_H_MAX, late=D.LATE, horizon=D.HORIZON):
    """The rule's report for one curve over `checkpoints` and its bootstrap curves (BOOT, K)."""
    N = np.asarray(checkpoints, float)
    allc = np.vstack([np.asarray(curve, float)[None], np.asarray(boot, float)])
    m1, m0, m2 = fit1(allc, N, True), fit1(allc, N, False), fit2(allc, N)
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
    rem = m1["a"] * np.exp(-LN2 * (horizon - 1) / m1["h"])
    rep["M1"]["remaining_at_horizon"], rep["M1"]["remaining_at_horizon_ci95"] = float(rem[0]), q(rem)
    rep["sse_M0_minus_M1"], rep["sse_M0_minus_M1_ci95"] = float(m0["sse"][0] - m1["sse"][0]), q(m0["sse"] - m1["sse"])
    rep["sse_M1_minus_M2"], rep["sse_M1_minus_M2_ci95"] = float(m1["sse"][0] - m2["sse"][0]), q(m1["sse"] - m2["sse"])
    ck = list(checkpoints)
    li = [ck.index(n) for n in late if n in ck]
    lm = allc[:, li].mean(1)
    rep["late_mean"], rep["late_mean_ci95"] = float(lm[0]), q(lm)
    for a, b in ((1024, 512), (1024, 256)):
        if a in ck and b in ck:
            x = allc[:, ck.index(a)] - allc[:, ck.index(b)]
            rep[f"d{a}_minus_d{b}"], rep[f"d{a}_minus_d{b}_ci95"] = float(x[0]), q(x)
    rep["identified"] = bool(rep["M1"]["h_ci95"][1] <= h_max)
    if 512 in ck and 1024 in ck:
        rep["x512"] = float(allc[0, ck.index(512)])
        rep["drift_bound"], rep["drift_bound_text"] = drift_bound(rep["x512"], rep["d1024_minus_d512_ci95"][0])
        rep["level_holds"] = level_holds(rep["x512"], rep["d1024_minus_d512_ci95"][0])
        rep["reading"], rep["reasons"] = reading(rep, rep["x512"], h_max)
    rep["reading_declared"], rep["reasons_declared"] = reading_declared(rep, h_max)
    return rep
