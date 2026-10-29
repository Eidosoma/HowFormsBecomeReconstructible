"""LR005's tissue (DRAFT): LR004's, with one event at t = 0 and three kinds of reference (body, record, cue).

Branches are arm-major (index = arm x cases + case). Every branch reads the case's body, record and bond noise streams;
vote2r's second record reads its own ("B") streams, as in LR004. One update, in order: the body reads the first record
(dl001.sim.body); bond noise; the records step through their bonds (msegrid.record_step, k_c 0); the trusted targets;
the community pull; Hebbian relearning; parity (record+parity only).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, edges_from, halves, parity_repair
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, bonds, kill_bonds, record_step

from . import design as D


def patch(cases, tag=D.TAG):
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        a, b = address(tag, *c.key(), "patch").integers(0, D.SIDE, 2)
        out[j][np.ix_(np.arange(a, a + D.PATCH) % D.SIDE, np.arange(b, b + D.PATCH) % D.SIDE)] = True
    return out


def anchor_mask(cases, tag=D.TAG):
    n = D.SIDE * D.SIDE
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        out[j].flat[address(tag, *c.key(), "anchors", D.DENSITY).permutation(n)[: n // D.DENSITY]] = True
    return out


def scattered(cases, amask, tag=D.TAG):
    """A random quarter of each case's anchors."""
    out = np.zeros_like(amask)
    for j, c in enumerate(cases):
        idx = np.flatnonzero(amask[j])
        pick = address(tag, *c.key(), "cue-damage").permutation(len(idx))[: len(idx) // 4]
        out[j].flat[idx[pick]] = True
    return out


def newborn(cases, tag=D.TAG):
    return np.stack([D.KILL_SD * address(tag, *c.key(), "newborn").standard_normal((D.SIDE, D.SIDE)) for c in cases])


def vote_sign(x):
    """+1, -1, or 0 for a value not confident enough to vote."""
    return np.where(x >= D.VMIN, 1.0, np.where(x <= -D.VMIN, -1.0, 0.0))


def rel(s):
    return s * np.roll(s, -1, -1), s * np.roll(s, -1, -2)


def box(x, rho):
    y = sum(np.roll(x, d, -1) for d in range(-rho, rho + 1))
    return sum(np.roll(y, d, -2) for d in range(-rho, rho + 1))


def event(situation, cases, V0, ema0, R0, T, tag=D.TAG):
    """The state after the event, per case: V, ema, r, H, W, strengths, anchor values, anchors present, the dead cells,
    the patch, and the correct target (and, for change, the old target too)."""
    m = patch(cases, tag)
    am = anchor_mask(cases, tag)
    V, E, r = V0.copy(), ema0.copy(), R0.copy()
    H, W = edges_from(bonds(R0, True))
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    aval = np.where(R0 > 0, 1.0, -1.0)
    dead = np.zeros_like(m)
    target, old = T, None
    if situation == "none":
        pass
    elif situation == "body":
        V = np.where(m, -V, V)
    elif situation == "memory":
        r = np.where(m, -r, r)
        H, W = edges_from(bonds(r, True))
        Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    elif situation == "shared":
        nb = newborn(cases, tag)
        V, E, r = np.where(m, nb, V), np.where(m, nb, E), np.where(m, 0.0, r)
        J = kill_bonds(halves(H, W), m, False)
        H, W = edges_from(J)
        dh, dw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
        Hb, Wb = np.where(dh, 0.0, Hb), np.where(dw, 0.0, Wb)
        am = am & ~m
        dead = m
    elif situation == "cue":
        aval = np.where(scattered(cases, am, tag), -aval, aval)
    elif situation == "change":
        aval = np.where(m, -aval, aval)
        target, old = np.where(m, -T, T), T
    else:
        raise ValueError(situation)
    return dict(V=V, E=E, r=r, H=H, W=W, Hb=Hb, Wb=Wb, aval=aval, am=am, dead=dead, m=m, target=target, old=old)


def targets(arm, V, r, rB, P, latch=None):
    """latch: (age, sign) arrays held across updates for a community arm."""
    """The bond targets (xh, xw) in [-1, 1] and the learning masks for one arm's branches; 0 targets do not learn."""
    if arm == "record+parity":
        xh, xw = r * np.roll(r, -1, -1) / R_STAR ** 2, r * np.roll(r, -1, -2) / R_STAR ** 2
        return np.clip(xh, -1, 1), np.clip(xw, -1, 1), None
    if arm == "body":
        return np.clip(V * np.roll(V, -1, -1), -1, 1), np.clip(V * np.roll(V, -1, -2), -1, 1), None
    sv, sr = vote_sign(V), vote_sign(r)
    if arm == "vote2r":
        a, b, c = rel(sv), rel(sr), rel(vote_sign(rB))
        return np.sign(a[0] + b[0] + c[0]), np.sign(a[1] + b[1] + c[1]), None
    ca = np.where(P["am"], P["aval"], 0.0)
    if arm == "vote3":
        tot = sv + sr + ca
        t = np.where(tot != 0, np.sign(tot), np.where(sr != 0, sr, sv))
        return *rel(t), None
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))
    if arm == "cue":
        return *rel(t), None
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    n_live, n_dis = box(live.astype(float), D.RHO), box(dis.astype(float), D.RHO)
    q, hold = D.COMMUNITY[arm]
    zone = (n_live >= D.MIN_ANCHORS) & (n_dis >= q * n_live) & (sr != 0)
    age, sgn = latch                                   # a slow state holds the decision and its sign for `hold` updates
    sgn[:] = np.where(zone & (age == 0), -sr, sgn)
    age[:] = np.where(zone, hold, np.maximum(age - 1, 0))
    zone = age > 0
    t = np.where(zone, sgn, t)
    return *rel(t), (zone, t)


def run(body, situation, cases, V0, ema0, R0, th, T, theta, gain, reads, rate=D.RATE, tag=D.TAG, window=D.WINDOW,
        arms=D.ARMS):
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, cases, V0, ema0, R0, T, tag)
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], ev["m"][idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    arm_of = np.repeat(np.arange(na), k)
    two = [i for i, a in enumerate(arms) if a == "vote2r"]
    tb = np.flatnonzero(np.isin(arm_of, two))
    if len(tb):
        HB, WB, HbB, WbB, rB = H[tb].copy(), W[tb].copy(), Hb[tb].copy(), Wb[tb].copy(), r[tb].copy()
        if situation == "memory":                                 # the event hit the first record only
            H0, W0 = edges_from(bonds(R0, True))
            rB, HB, WB = R0[idx][tb].copy(), H0[idx][tb].copy(), W0[idx][tb].copy()
            HbB, WbB = D.STRENGTH0 * HB, D.STRENGTH0 * WB
        xsB, zsB = (Stream(tag, cases, s, "B", side=D.SIDE) for s in ("record-noise", "bond-noise"))
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ("r_all", "r_in", "v_all", "v_in", "r_in_old", "v_in_old")}
    trace = []
    opened = np.zeros(na * k)
    latches = {ai: (np.zeros((k, D.SIDE, D.SIDE), int), np.zeros((k, D.SIDE, D.SIDE))) for ai, a in enumerate(arms)
               if a.startswith("community")}
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if len(tb):
                xbB, zbB = xsB.take(D.CHUNK), zsB.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        if len(tb):
            zB = zbB[i][idx[tb]]
            h2, w2 = zB > cut, zB < -cut
            HB, WB, HbB, WbB = np.where(h2, -HB, HB), np.where(w2, -WB, WB), np.where(h2, -HbB, HbB), np.where(w2, -WbB, WbB)
            rB = record_step(rB, xbB[i][idx[tb]], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(HB, WB))
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            Pa = P
            xh, xw, extra = targets(arm, V[sl], r[sl], rB if arm == "vote2r" else None, Pa, latches.get(ai))
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + D.ETA * (xh - Hb[sl]), Wb[sl] + D.ETA * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
            if arm == "vote2r":
                HbB, WbB = np.where(lh, HbB + D.ETA * (xh - HbB), HbB), np.where(lw, WbB + D.ETA * (xw - WbB), WbB)
                HB = np.where(lh & (HbB != 0), np.sign(HbB), HB)
                WB = np.where(lw & (WbB != 0), np.sign(WbB), WB)
            if arm == "record+parity":
                H2, W2 = parity_repair(H[sl], W[sl])
                Hb[sl] = np.where(np.sign(Hb[sl]) * H2 < 0, -Hb[sl], Hb[sl])
                Wb[sl] = np.where(np.sign(Wb[sl]) * W2 < 0, -Wb[sl], Wb[sl])
                H[sl], W[sl] = H2, W2
        if t % D.TRACE == 0:
            trace.append(inside(r, Tb, mb))
        if t in reads:
            out["r_all"].append(S.sign(r, Tb))
            out["v_all"].append(S.sign(V, Tb))
            out["r_in"].append(inside(r, Tb, mb))
            out["v_in"].append(inside(V, Tb, mb))
            if oldb is not None:
                out["r_in_old"].append(inside(r, oldb, mb))
                out["v_in_old"].append(inside(V, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace), opened=opened / window, V=V, r=r, H=H, W=W)
    return res


def inside(x, T, m):
    return (((x > 0) == (T > 0)) & m).sum((-2, -1)) / m.sum((-2, -1))
