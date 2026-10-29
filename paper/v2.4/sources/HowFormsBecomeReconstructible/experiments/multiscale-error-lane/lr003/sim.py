"""LR003's tissue: LR002's (DL002's preparation and DL001's body, unchanged and imported; the relational record's bonds
held as edges with lr001.sim's helpers, unchanged), with the bonds relearned from a source chosen per branch and, for the
gates, per bond.

A run advances one body under every condition as branches (condition-major: index = condition x cases + case), all
reading the case's three noise streams (the body's, the record's and the bonds'). One update, in order: the body reads
the record (dl001.sim.body); bond noise; the record step through the bonds (msegrid.record_step, k_c 0); relearning;
plaquette parity. A bond (i, j) is frustrated when J_ij s(r_i) s(r_j) < 0, s the sign of the record's current value:
the bond and the record's values disagree. For the record and body sources the arithmetic is lr002.sim.relations's,
in its order (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import bond_err, cut_for, edges_from, halves, parity_repair
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, bonds, record_step

from . import design as D


def params(conds, k):
    """Per-branch noise cut, learning source (design.SOURCES) and parity, each (n, 1, 1), condition-major."""
    def rep(f):
        return np.repeat([f(c) for c in conds], k)[:, None, None]
    return {"cut": rep(lambda c: cut_for(c.rate)), "src": rep(lambda c: D.SOURCES[c.source]), "par": rep(lambda c: c.parity)}


def gates(H, W, r, V, src):
    """Per bond: whether it learns from the body's co-activity. body: everywhere; agree: where the body and the record
    agree in sign at both ends; syndrome: where the bond is frustrated against the record's current values; site: every
    bond touching a site that has a frustrated bond."""
    useh = usew = src == D.SOURCES["body"]
    if (src == D.SOURCES["agree"]).any():
        ag = (V > 0) == (r > 0)
        a = src == D.SOURCES["agree"]
        useh = useh | (a & ag & np.roll(ag, -1, -1))
        usew = usew | (a & ag & np.roll(ag, -1, -2))
    if ((src == D.SOURCES["syndrome"]) | (src == D.SOURCES["site"])).any():
        s = np.where(r > 0, 1.0, -1.0)
        fh, fw = H * s * np.roll(s, -1, -1) < 0, W * s * np.roll(s, -1, -2) < 0
        g = src == D.SOURCES["syndrome"]
        useh = useh | (g & fh)
        usew = usew | (g & fw)
        alarm = fh | np.roll(fh, 1, -1) | fw | np.roll(fw, 1, -2)          # a site with any frustrated bond
        g = src == D.SOURCES["site"]
        useh = useh | (g & (alarm | np.roll(alarm, -1, -1)))
        usew = usew | (g & (alarm | np.roll(alarm, -1, -2)))
    return useh, usew


def relations(H, W, Hb, Wb, r, xi, z, V, P, eta=D.ETA):
    """One update of the record of relations after the body's step: bond noise, the record step through the bonds,
    relearning from the record's co-activity r_i r_j / R*^2 or, where the gate opens, the body's V_i V_j; parity.
    Returns the bonds, their strengths, the record and the share of bonds that learned from the body."""
    hh, hw = z > P["cut"], z < -P["cut"]
    H, W = np.where(hh, -H, H), np.where(hw, -W, W)
    Hb, Wb = np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
    r = record_step(r, xi, D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
    src = P["src"]
    learn = src > 0
    opened = np.zeros(len(r))
    if learn.any():
        xh = r * np.roll(r, -1, -1) / R_STAR ** 2
        xw = r * np.roll(r, -1, -2) / R_STAR ** 2
        useh, usew = gates(H, W, r, V, src)
        if useh.any() or usew.any():
            xh = np.where(useh, V * np.roll(V, -1, -1), xh)
            xw = np.where(usew, V * np.roll(V, -1, -2), xw)
            opened = (np.broadcast_to(useh, H.shape).mean((-2, -1)) + np.broadcast_to(usew, W.shape).mean((-2, -1))) / 2
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
    return H, W, Hb, Wb, r, opened


def run(body, conds, cases, V0, ema0, R0, th, T, theta, reads, tag=D.TAG, window=D.WINDOW):
    """Advance one body under every condition for `window` updates. Endpoints per read: the body's sign, the
    record's sign, body-record agreement and bond error against the taught bonds; the realised flip rate and the mean
    share of bonds taught by the body; finals."""
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
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ("sign", "r_sign", "agree", "bond_err")}
    flips, opened = np.zeros(nb * k), np.zeros(nb * k)
    buf = xbuf = zbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, D.GAIN, alpha, G)
        z = zbuf[i][idx]
        flips += (z > P["cut"]).sum((-2, -1)) + (z < -P["cut"]).sum((-2, -1))
        H, W, Hb, Wb, r, op = relations(H, W, Hb, Wb, r, xbuf[i][idx], z, V, P)
        opened += op
        if t in reads:
            out["sign"].append(S.sign(V, Tb))
            out["r_sign"].append(S.sign(r, Tb))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
            out["bond_err"].append(bond_err(H, W, H0, W0))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(flip_rate=flips / (window * 2 * D.SIDE * D.SIDE), opened=opened / window, V=V, r=r, H=H, W=W)
    return res
