"""BE001's tissue (DRAFT): LR005's, with the community rule's detector and commitment made bioelectric.

Branches are arm-major (index = arm x cases + case). One update, in order, as in lr005.sim.run: the body reads the first
record (dl001.sim.body); bond noise; the record steps through its bonds (msegrid.record_step, k_c 0); the trusted targets
(cue and community arms by lr005.sim.targets, unchanged; bioelectric arms by bio_targets); the pull toward committed
signs; Hebbian relearning. With only the cue and community arms and a patch of side 8, a run equals lr005.sim.run bit
for bit (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, edges_from, halves
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr005 import sim as L5S
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, bonds, kill_bonds, record_step

from . import design as D


def patch(cases, size, tag=D.TAG):
    """LR005's patch draw (the same corner per case), at any side."""
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        a, b = address(tag, *c.key(), "patch").integers(0, D.SIDE, 2)
        out[j][np.ix_(np.arange(a, a + size) % D.SIDE, np.arange(b, b + size) % D.SIDE)] = True
    return out


def event(situation, size, cases, V0, ema0, R0, T, tag=D.TAG):
    """lr005.sim.event on a patch of the given side (identical arithmetic)."""
    m = patch(cases, size, tag)
    am = L5S.anchor_mask(cases, tag)
    V, E, r = V0.copy(), ema0.copy(), R0.copy()
    H, W = edges_from(bonds(R0, True))
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    aval = np.where(R0 > 0, 1.0, -1.0)
    target, old = T, None
    if situation == "none":
        pass
    elif situation == "memory":
        r = np.where(m, -r, r)
        H, W = edges_from(bonds(r, True))
        Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    elif situation == "shared":
        nb = L5S.newborn(cases, tag)
        V, E, r = np.where(m, nb, V), np.where(m, nb, E), np.where(m, 0.0, r)
        H, W = edges_from(kill_bonds(halves(H, W), m, False))
        dh, dw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
        Hb, Wb = np.where(dh, 0.0, Hb), np.where(dw, 0.0, Wb)
        am = am & ~m
    elif situation == "cue":
        aval = np.where(L5S.scattered(cases, am, tag), -aval, aval)
    elif situation == "change":
        aval = np.where(m, -aval, aval)
        target, old = np.where(m, -T, T), T
    else:
        raise ValueError(situation)
    return dict(V=V, E=E, r=r, H=H, W=W, Hb=Hb, Wb=Wb, aval=aval, am=am, m=m, target=target, old=old)


def cable_kernel(lam, n=D.SIDE):
    """The Fourier symbol of g_l + lam^2 (4 - shifts) on the periodic sheet."""
    k = 2 * np.pi * np.fft.fftfreq(n)
    kx, ky = np.meshgrid(k, k, indexing="ij")
    return D.G_LEAK + lam ** 2 * (4 - 2 * np.cos(kx) - 2 * np.cos(ky))


def gates(v, lam):
    """Junction conductances (right, lower) from the voltages across them (connexin-like Boltzmann gating)."""
    g = D.GATE

    def f(dv):
        return lam ** 2 * (g["g_min"] + (1 - g["g_min"]) / (1 + np.exp((np.abs(dv) - g["d0"]) / g["w"])))
    return f(v - np.roll(v, -1, -1)), f(v - np.roll(v, -1, -2))


def apply_A(x, gH, gW):
    return (D.G_LEAK * x + gH * (x - np.roll(x, -1, -1)) + np.roll(gH, 1, -1) * (x - np.roll(x, 1, -1))
            + gW * (x - np.roll(x, -1, -2)) + np.roll(gW, 1, -2) * (x - np.roll(x, 1, -2)))


def cable_cg(I, gH, gW, x0):
    """Solve A v = I (A symmetric positive definite) by Jacobi-preconditioned conjugate gradients, per branch."""
    diag = D.G_LEAK + gH + np.roll(gH, 1, -1) + gW + np.roll(gW, 1, -2)
    x = x0.copy()
    res = I - apply_A(x, gH, gW)
    z = res / diag
    p = z.copy()
    rz = (res * z).sum((-2, -1), keepdims=True)
    norm = np.sqrt((I * I).sum((-2, -1), keepdims=True)) + 1e-300
    for _ in range(D.CG_MAXIT):
        if (np.sqrt((res * res).sum((-2, -1), keepdims=True)) <= D.CG_TOL * norm).all():
            break
        Ap = apply_A(p, gH, gW)
        alpha = rz / (p * Ap).sum((-2, -1), keepdims=True)
        x, res = x + alpha * p, res - alpha * Ap
        z = res / diag
        rz_new = (res * z).sum((-2, -1), keepdims=True)
        p, rz = z + (rz_new / rz) * p, rz_new
    return x


def bio_targets(arm, V, r, P, state, vnoise):
    """Trusted signs for one bioelectric arm's branches; updates state = {v, s, sgn} in place. Returns the bond targets
    and (committed, trusted signs)."""
    prm = D.BIO[arm]
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    current = D.KAPPA * ca * sr
    if prm["gate"]:
        gH, gW = gates(state["v"], prm["lam"])
        v = cable_cg(current, gH, gW, state["v"])
    else:
        v = np.real(np.fft.ifft2(np.fft.fft2(current) / state["kernel"]))
    state["v"] = v
    vo = v + prm["noise"] * vnoise if prm["noise"] else v
    trig = (vo < -prm["theta"]) & (sr != 0)
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t)


def run(body, situation, size, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE, tag=D.TAG,
        window=D.WINDOW, arms=D.ARMS):
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], ev["m"][idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    bio = [a for a in arms if a in D.BIO]
    vs = Stream(tag, cases, "voltage-noise", side=D.SIDE) if bio else None
    out = {key: [] for key in ("r_all", "r_in", "v_all", "v_in", "r_in_old", "v_in_old")}
    trace = []
    opened = np.zeros(na * k)
    latches = {ai: (np.zeros((k, D.SIDE, D.SIDE), int), np.zeros((k, D.SIDE, D.SIDE))) for ai, a in enumerate(arms)
               if a.startswith("community")}
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": cable_kernel(D.BIO[a]["lam"])}
              for ai, a in enumerate(arms) if a in D.BIO}
    vbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if vs is not None:
                vbuf = vs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            if arm in D.BIO:
                xh, xw, extra = bio_targets(arm, V[sl], r[sl], P, states[ai], vbuf[i])
            else:
                xh, xw, extra = L5S.targets(arm, V[sl], r[sl], None, P, latches.get(ai))
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + D.ETA * (xh - Hb[sl]), Wb[sl] + D.ETA * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if t % D.TRACE == 0:
            trace.append(L5S.inside(r, Tb, mb))
        if t in reads:
            out["r_all"].append(S.sign(r, Tb))
            out["v_all"].append(S.sign(V, Tb))
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
                out["v_in_old"].append(L5S.inside(V, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace), opened=opened / window, V=V, r=r, H=H, W=W)
    return res
