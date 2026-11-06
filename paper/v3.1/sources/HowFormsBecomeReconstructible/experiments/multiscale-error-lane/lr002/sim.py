"""LR002's tissue: DL002's (dl002.sim.prepare and dl001.sim.body, unchanged and imported) with the relational record's
bonds held as edges (lr001.sim's helpers, unchanged) under bond-sign noise and repairs.

A run advances one body under every condition as branches (condition-major: index = condition x cases + case), all
reading the case's three noise streams (the body's, the record's and the bonds'), so bodies, rates and repairs are
paired within a case. One update, in order: the body reads the record (dl001.sim.body); bond noise; the record step
through the bonds (msegrid.record_step); Hebbian relearning, from the record or from the body; plaquette parity.
With no bond noise and no repair, DL002's coarse code and DL002's tag, a branch is DL002's rel branch bit for bit; the
relations' update is lr001.sim.simulate_E's arithmetic (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from dl002.sim import prepare, template  # noqa: F401  (unchanged)
from lr001.sim import bond_err, cut_for, edges_from, halves, parity_repair
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, bonds, bproj, record_step

from . import design as D


def params(conds, k):
    """Per-branch noise cut, learning sources and parity, each (n, 1, 1), condition-major."""
    def rep(f):
        return np.repeat([f(c) for c in conds], k)[:, None, None]
    return {"cut": rep(lambda c: cut_for(c.rate)), "learn_r": rep(lambda c: c.learn == "record"),
            "learn_v": rep(lambda c: c.learn == "body"), "par": rep(lambda c: c.parity)}


def relations(H, W, Hb, Wb, r, xi, z, V, P, kc=D.KC, B=None, eta=D.ETA):
    """One update of the record of relations after the body's step: bond noise, the record step through the bonds,
    Hebbian relearning (the record's co-activity r_i r_j / R*^2, or the body's V_i V_j where P['learn_v']), parity.
    For record relearning and parity this is lr001.sim.simulate_E's arithmetic, in its order."""
    hh, hw = z > P["cut"], z < -P["cut"]
    H, W = np.where(hh, -H, H), np.where(hw, -W, W)
    Hb, Wb = np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
    r = record_step(r, xi, D.EPS, D.KR, D.SIGMA_R, kc, B, halves(H, W))
    learn = P["learn_r"] | P["learn_v"]
    if learn.any():
        xh = r * np.roll(r, -1, -1) / R_STAR ** 2
        xw = r * np.roll(r, -1, -2) / R_STAR ** 2
        if P["learn_v"].any():
            xh = np.where(P["learn_v"], V * np.roll(V, -1, -1), xh)
            xw = np.where(P["learn_v"], V * np.roll(V, -1, -2), xw)
        Hn = Hb + eta * (np.clip(xh, -1, 1) - Hb)
        Wn = Wb + eta * (np.clip(xw, -1, 1) - Wb)
        Hb, Wb = np.where(learn, Hn, Hb), np.where(learn, Wn, Wb)
        H = np.where(learn & (Hb != 0), np.sign(Hb), H)
        W = np.where(learn & (Wb != 0), np.sign(Wb), W)
    if P["par"].any():
        H2, W2 = parity_repair(H, W)
        H, W = np.where(P["par"], H2, H), np.where(P["par"], W2, W)
        Hb = np.where(P["par"] & (np.sign(Hb) * H < 0), -Hb, Hb)
        Wb = np.where(P["par"] & (np.sign(Wb) * W < 0), -Wb, Wb)
    return H, W, Hb, Wb, r


def run(body, conds, cases, V0, ema0, R0, th, T, theta, reads, tag=D.TAG, kc=D.KC, window=D.WINDOW):
    """Advance one body under every condition for `window` updates. Endpoints per read: the body's sign, the
    record's sign, body-record agreement and bond error against the taught bonds; the realised flip rate; finals."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(conds)
    idx = np.tile(np.arange(k), nb)
    V, E, r = V0[idx].copy(), ema0[idx].copy(), R0[idx].copy()
    Tb, thb = T[idx], (th * theta)[idx]
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    P = params(conds, k)
    B = bproj(R0, 4)[idx] if kc else None
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ("sign", "r_sign", "agree", "bond_err")}
    flips = np.zeros(nb * k)
    buf = xbuf = zbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, D.GAIN, alpha, G)
        z = zbuf[i][idx]
        flips += (z > P["cut"]).sum((-2, -1)) + (z < -P["cut"]).sum((-2, -1))
        H, W, Hb, Wb, r = relations(H, W, Hb, Wb, r, xbuf[i][idx], z, V, P, kc, B)
        if t in reads:
            out["sign"].append(S.sign(V, Tb))
            out["r_sign"].append(S.sign(r, Tb))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
            out["bond_err"].append(bond_err(H, W, H0, W0))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(flip_rate=flips / (window * 2 * D.SIDE * D.SIDE), V=V, r=r, H=H, W=W)
    return res
