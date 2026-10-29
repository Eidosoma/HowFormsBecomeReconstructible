"""LR004's tissue: LR003's (DL002's preparation and DL001's body, unchanged and imported; the relational record's bonds
held as edges with lr001.sim's helpers; LR003's gates, unchanged), with a second relational record for the pair and vote
teachers and positional anchors as arbiters.

A run advances one body under every condition as branches (condition-major: index = condition x cases + case). Every
branch reads the case's body, record and bond noise streams; branches with a second record also read that record's own
record and bond noise streams, so the two records' errors are independent. The body reads the first record only. One
update, in order: the body reads the record (dl001.sim.body); bond noise; the records step through their bonds
(msegrid.record_step, k_c 0); relearning; parity. For record+parity, body and site the arithmetic is
lr003.sim.relations's, in its order (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import bond_err, cut_for, edges_from, halves, parity_repair
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr003.sim import gates
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, bonds, record_step

from . import design as D


def anchors(cases, density, tag=D.TAG):
    """The anchored cells: a random 1/density of the sheet per case, drawn without replacement."""
    n = D.SIDE * D.SIDE
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        out[j].flat[address(tag, *c.key(), "anchors", density).permutation(n)[: n // density]] = True
    return out


def params(conds, cases, tag=D.TAG):
    """Per-branch noise cut, source and parity, each (n, 1, 1), condition-major; the branches with a second record;
    the anchored cells."""
    k = len(cases)

    def rep(f):
        return np.repeat([f(c) for c in conds], k)[:, None, None]
    P = {"cut": rep(lambda c: cut_for(c.rate)), "src": rep(lambda c: D.SOURCES[c.source]), "par": rep(lambda c: c.parity)}
    P["two_idx"] = np.nonzero(np.repeat([c.two for c in conds], k))[0]
    P["cut_two"] = P["cut"][P["two_idx"]]
    P["vote_two"] = P["src"][P["two_idx"]] == D.SOURCES["vote"]
    amask = np.zeros((len(conds) * k, D.SIDE, D.SIDE), bool)
    for ci, c in enumerate(conds):
        if c.density:
            amask[ci * k:(ci + 1) * k] = anchors(cases, c.density, tag)
    P["amask"] = amask
    return P


def signs(x):
    """The sign of each bond's relation, x_i x_j, for the right (H) and lower (W) bonds, as +-1."""
    p = x > 0
    return np.where(p == np.roll(p, -1, -1), 1.0, -1.0), np.where(p == np.roll(p, -1, -2), 1.0, -1.0)


def relations(A, B, xi, z, xiB, zB, V, P, aval, eta=D.ETA):
    """One update of the records of relations after the body's step. A = (H, W, Hb, Wb, r) for every branch; B the same
    for the branches with a second record (or None). Returns A, B and the share of bonds (or anchored cells) where the
    body or the third copy decided."""
    H, W, Hb, Wb, r = A
    hh, hw = z > P["cut"], z < -P["cut"]
    H, W = np.where(hh, -H, H), np.where(hw, -W, W)
    Hb, Wb = np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
    r = record_step(r, xi, D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
    idx = P["two_idx"]
    if len(idx):
        HB, WB, HbB, WbB, rB = B
        hh2, hw2 = zB > P["cut_two"], zB < -P["cut_two"]
        HB, WB = np.where(hh2, -HB, HB), np.where(hw2, -WB, WB)
        HbB, WbB = np.where(hh2, -HbB, HbB), np.where(hw2, -WbB, WbB)
        rB = record_step(rB, xiB, D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(HB, WB))
    src = P["src"]
    learn = src > 0
    opened = np.zeros(len(r))
    lh = lw = learn
    if learn.any():
        xh = r * np.roll(r, -1, -1) / R_STAR ** 2
        xw = r * np.roll(r, -1, -2) / R_STAR ** 2
        useh, usew = gates(H, W, r, V, src)
        if useh.any() or usew.any():
            xh = np.where(useh, V * np.roll(V, -1, -1), xh)
            xw = np.where(usew, V * np.roll(V, -1, -2), xw)
            opened = (np.broadcast_to(useh, H.shape).mean((-2, -1)) + np.broadcast_to(usew, W.shape).mean((-2, -1))) / 2
        anc = src == D.SOURCES["anchors"]
        if anc.any():
            sv, sr = np.where(V > 0, 1.0, -1.0), np.where(r > 0, 1.0, -1.0)
            dis = sv != sr
            t = np.where(dis, np.where(P["amask"], aval, sr), sv)        # the trusted sign at each cell
            xh = np.where(anc, t * np.roll(t, -1, -1), xh)
            xw = np.where(anc, t * np.roll(t, -1, -2), xw)
            opened = np.where(anc[:, 0, 0], (dis & P["amask"]).mean((-2, -1)), opened)
        if len(idx):
            sVh, sVw = signs(V[idx])
            sAh, sAw = signs(r[idx])
            sBh, sBw = signs(rB)
            vote = P["vote_two"]
            mh = np.where(vote, np.sign(sVh + sAh + sBh), sAh)
            mw = np.where(vote, np.sign(sVw + sAw + sBw), sAw)
            kh = vote | (sAh == sBh)                                     # pair: learn only where the records agree
            kw = vote | (sAw == sBw)
            xh, xw = xh.copy(), xw.copy()
            xh[idx], xw[idx] = mh, mw
            lh, lw = np.broadcast_to(learn, H.shape).copy(), np.broadcast_to(learn, W.shape).copy()
            lh[idx], lw[idx] = kh, kw
            opened[idx] = ((sAh != sBh).mean((-2, -1)) + (sAw != sBw).mean((-2, -1))) / 2
            HnB = HbB + eta * (mh - HbB)
            WnB = WbB + eta * (mw - WbB)
            HbB, WbB = np.where(kh, HnB, HbB), np.where(kw, WnB, WbB)
            HB = np.where(kh & (HbB != 0), np.sign(HbB), HB)
            WB = np.where(kw & (WbB != 0), np.sign(WbB), WB)
        Hn = Hb + eta * (np.clip(xh, -1, 1) - Hb)
        Wn = Wb + eta * (np.clip(xw, -1, 1) - Wb)
        Hb, Wb = np.where(lh, Hn, Hb), np.where(lw, Wn, Wb)
        H = np.where(lh & (Hb != 0), np.sign(Hb), H)
        W = np.where(lw & (Wb != 0), np.sign(Wb), W)
    if P["par"].any():
        H2, W2 = parity_repair(H, W)
        H, W = np.where(P["par"], H2, H), np.where(P["par"], W2, W)
        Hb = np.where(P["par"] & (np.sign(Hb) * H < 0), -Hb, Hb)
        Wb = np.where(P["par"] & (np.sign(Wb) * W < 0), -Wb, Wb)
    return (H, W, Hb, Wb, r), ((HB, WB, HbB, WbB, rB) if len(idx) else None), opened


def run(body, conds, cases, V0, ema0, R0, th, T, theta, reads, tag=D.TAG, window=D.WINDOW):
    """Advance one body under every condition for `window` updates. Endpoints per read: the body's sign, the first
    record's sign, body-record agreement and the first record's bond error against the taught bonds; the realised flip
    rate and the mean share of bonds (or anchored cells) where the body or the third copy decided; finals."""
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
    P = params(conds, cases, tag)
    aval = np.where(R0[idx] > 0, 1.0, -1.0)
    two = P["two_idx"]
    B = None
    if len(two):
        B = (H0[two].copy(), W0[two].copy(), D.STRENGTH0 * H0[two], D.STRENGTH0 * W0[two], R0[idx][two].copy())
        xsB, zsB = (Stream(tag, cases, s, "B", side=D.SIDE) for s in ("record-noise", "bond-noise"))
        ctwo = idx[two]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ("sign", "r_sign", "agree", "bond_err")}
    flips, opened = np.zeros(nb * k), np.zeros(nb * k)
    buf = xbuf = zbuf = xbB = zbB = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if B is not None:
                xbB, zbB = xsB.take(D.CHUNK), zsB.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, D.GAIN, alpha, G)
        z = zbuf[i][idx]
        flips += (z > P["cut"]).sum((-2, -1)) + (z < -P["cut"]).sum((-2, -1))
        A, B, op = relations((H, W, Hb, Wb, r), B, xbuf[i][idx], z, None if B is None else xbB[i][ctwo],
                             None if B is None else zbB[i][ctwo], V, P, aval)
        H, W, Hb, Wb, r = A
        opened += op
        if t in reads:
            out["sign"].append(S.sign(V, Tb))
            out["r_sign"].append(S.sign(r, Tb))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
            out["bond_err"].append(bond_err(H, W, H0, W0))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(flip_rate=flips / (window * 2 * D.SIDE * D.SIDE), opened=opened / window, V=V, r=r, H=H, W=W)
    return res
