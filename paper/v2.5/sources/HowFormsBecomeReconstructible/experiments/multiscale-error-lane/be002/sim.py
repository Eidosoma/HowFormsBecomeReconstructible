"""BE002's tissue (DRAFT): BE001's, with a regime signal that changes the coupling or permits commitment.

Branches are arm-major (index = arm x cases + case). One update, in order, as in be001.sim.run: the body reads the first
record (dl001.sim.body); bond noise; the record steps through its bonds (msegrid.record_step, k_c 0); the trusted targets
(the cue arm by lr005.sim.targets, BE001's arms by be001.sim.bio_targets, both unchanged; the signal arms by
sig_targets); the pull toward committed signs; Hebbian relearning. BE001's arms never read the signal: in every run they
equal be001.sim.run bit for bit (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from be001 import design as B1
from be001 import sim as B1S
from be001.sim import cable_kernel, event, patch, prepare  # noqa: F401  (BE001's, unchanged)
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, record_step

from . import design as D


def footprint(m, d=D.SIG["d"]):
    """The signal's footprint: the patch dilated by d sites on the torus (square dilation)."""
    out = m.copy()
    for dy in range(-d, d + 1):
        for dx in range(-d, d + 1):
            out |= np.roll(m, (dy, dx), (-2, -1))
    return out


def conductances(fp, lam_rest=D.SIG["lam_rest"], lam_sig=D.SIG["lam_sig"]):
    """Junction conductances (right, lower) with the junctions that touch the footprint closed to lam_sig^2."""
    gH = np.where(fp | np.roll(fp, -1, -1), lam_sig ** 2, lam_rest ** 2)
    gW = np.where(fp | np.roll(fp, -1, -2), lam_sig ** 2, lam_rest ** 2)
    return gH, gW


def cable_matrix(gH, gW):
    """g_l I + the weighted graph Laplacian of one periodic sheet (gH[i, j] couples (i, j)-(i, j + 1), gW (i, j)-(i + 1, j)),
    as a sparse CSC matrix."""
    n = gH.shape[-1]
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    a = (ii * n + jj).ravel()
    bh, bw = (ii * n + (jj + 1) % n).ravel(), (((ii + 1) % n) * n + jj).ravel()
    gh, gw = gH.ravel(), gW.ravel()
    diag = D.G_LEAK + gh + gw + np.roll(gH, 1, -1).ravel() + np.roll(gW, 1, -2).ravel()
    rows = np.concatenate([a, bh, a, bw, a])
    cols = np.concatenate([bh, a, bw, a, a])
    vals = np.concatenate([-gh, -gh, -gw, -gw, diag])
    return coo_matrix((vals, (rows, cols)), shape=(n * n, n * n)).tocsc()


def factor(gH, gW):
    """One sparse LU factorisation per branch."""
    return [splu(cable_matrix(gH[j], gW[j])) for j in range(gH.shape[0])]


def solve(lus, current):
    n = current.shape[-1]
    return np.stack([lu.solve(current[j].ravel()).reshape(n, n) for j, lu in enumerate(lus)])


def new_state(arm, k, fp):
    z = np.zeros((k, D.SIDE, D.SIDE))
    kind = D.SIGNAL_ARMS[arm]["kind"]
    st = {"v": z.copy(), "s": z.copy(), "sgn": z.copy(), "lus": None, "fp": fp,
          "kernel": cable_kernel(D.SIG["lam_permit"] if kind == "permit" else D.SIG["lam_rest"])}
    if kind == "global":
        st["kernel_on"] = cable_kernel(D.SIG["lam_sig"])
    return st


def sig_targets(arm, V, r, P, state, on):
    """Trusted signs for one signal arm's branches while the signal is on (on = True) or off; updates state in place.
    The arithmetic outside the signal is be001.sim.bio_targets' for an ungated, noiseless arm."""
    prm = D.SIGNAL_ARMS[arm]
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    current = D.KAPPA * ca * sr
    if prm["kind"] == "local" and on:
        if state["lus"] is None:
            state["lus"] = factor(*conductances(state["fp"]))
        v = solve(state["lus"], current)
    else:
        kern = state["kernel_on"] if (prm["kind"] == "global" and on) else state["kernel"]
        v = np.real(np.fft.ifft2(np.fft.fft2(current) / kern))
    state["v"] = v
    trig = (v < -prm["theta"]) & (sr != 0)
    if prm["kind"] == "permit":
        trig = trig & state["fp"] & on
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t)


def run(body, situation, size, signal, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE, tag=D.TAG,
        window=D.WINDOW, arms=D.ARMS, on_window=None):
    """signal: a key of design.SIGNALS ('' none, 'sig', 'late'); on_window = (first, last) update overrides it (tests)."""
    first, last = on_window if on_window is not None else (D.SIGNALS[signal] or (0, -1))
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    fp = footprint(ev["m"])
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb, fpb = ev["target"][idx], (th * theta)[idx], ev["m"][idx], fp[idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    bio = [a for a in arms if a in B1.BIO]
    vs = Stream(tag, cases, "voltage-noise", side=D.SIDE) if bio else None
    out = {key: [] for key in ("r_all", "r_in", "v_all", "v_in", "r_fp", "r_out", "r_in_old", "v_in_old")}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": cable_kernel(B1.BIO[a]["lam"])}
              for ai, a in enumerate(arms) if a in B1.BIO}
    states.update({ai: new_state(a, k, fp) for ai, a in enumerate(arms) if a in D.SIGNAL_ARMS})
    vbuf = None
    for t in range(1, window + 1):
        on = first <= t <= last
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
            if arm in D.SIGNAL_ARMS:
                xh, xw, extra = sig_targets(arm, V[sl], r[sl], P, states[ai], on)
            elif arm in B1.BIO:
                xh, xw, extra = B1S.bio_targets(arm, V[sl], r[sl], P, states[ai], vbuf[i])
            else:
                xh, xw, extra = L5S.targets(arm, V[sl], r[sl], None, P, None)
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                opened_out[sl] += (zone & ~fp).mean((-2, -1))
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
            out["r_fp"].append(L5S.inside(r, Tb, fpb))
            out["r_out"].append(L5S.inside(r, Tb, ~fpb))
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
                out["v_in_old"].append(L5S.inside(V, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, V=V, r=r, H=H, W=W)
    return res
