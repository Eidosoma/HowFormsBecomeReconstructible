"""BE004's tissue: BE002's, with the local dial's footprint, closure and reliability varied per arm, and a hold.

Branches are arm-major (index = arm x cases + case). One update, in order, as in be002.sim.run: the body reads the first
record (dl001.sim.body); bond noise; the record steps through its bonds (msegrid.record_step, k_c 0); the trusted targets
(the cue arm by lr005.sim.targets, BE001's arms by be001.sim.bio_targets, both unchanged; the signal arms by sig_targets,
be002.sim.sig_targets' arithmetic for a local dial); the pull toward committed signs; Hebbian relearning. With the base
dial's properties and BE002's signal window, a run equals be002.sim.run's dial-local bit for bit (checks Q3).

The hold: while the signal is pending (updates 1 to D, before it comes), at a cell inside the arm's footprint where body
and record disagree and the arbiter would take the cue (an anchored cell), the record's own sign is trusted instead (the
arbiter's fallback without a cue). Nothing else changes, and outside the wait the arm is the dial.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001 import design as B1
from be001 import sim as B1S
from be002 import sim as B2S
from be002.sim import cable_kernel, event, patch, prepare  # noqa: F401  (BE001's, unchanged)
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, record_step

from . import design as D

ENDS = ("r_all", "r_in", "v_in", "n_anc_ok", "r_fp0", "r_fp2", "r_fp4", "r_fp8", "r_out8", "r_in_old")


def arm_footprint(arm, m):
    """The arm's footprint: the patch dilated by its d on the torus, shifted by its offset along the rows."""
    prm = D.SIGNAL_ARMS[arm]
    fp = B2S.footprint(m, prm["d"])
    return np.roll(fp, prm["shift"], -1) if prm["shift"] else fp


def new_state(arm, k, m):
    prm = D.SIGNAL_ARMS[arm]
    fp = arm_footprint(arm, m)
    z = np.zeros((k, D.SIDE, D.SIDE))
    return {"v": z.copy(), "s": z.copy(), "sgn": z.copy(), "lus": None, "fp": fp,
            "g": B2S.conductances(fp, D.SIG["lam_rest"], prm["lam_sig"]), "kernel": cable_kernel(D.SIG["lam_rest"]),
            "onset": np.full(k, -1.0)}


def sig_targets(arm, V, r, P, state, on, pending=False, onset_m=None):
    """Trusted signs for one signal arm's branches; updates state in place. on: a bool (the window), or a (k,) bool array
    (a flickering signal); pending: inside the hold's wait; onset_m: the patch, at the signal's first update (records the
    share of the patch that triggers under the footprint's conductances). The arithmetic of a steady signal with no hold
    is be002.sim.sig_targets' for dial-local."""
    prm = D.SIGNAL_ARMS[arm]
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    if prm["hold"] and pending:
        t = np.where(state["fp"] & ~agree & (ca != 0), np.where(sr != 0, sr, sv), t)
    current = D.KAPPA * ca * sr
    if np.ndim(on) == 0:
        if on:
            if state["lus"] is None:
                state["lus"] = B2S.factor(*state["g"])
            v = B2S.solve(state["lus"], current)
        else:
            v = np.real(np.fft.ifft2(np.fft.fft2(current) / state["kernel"]))
        v_on = v if on else None
    else:
        v = np.real(np.fft.ifft2(np.fft.fft2(current) / state["kernel"]))
        v_on = None
        if on.any() or onset_m is not None:
            if state["lus"] is None:
                state["lus"] = B2S.factor(*state["g"])
            v_on = B2S.solve(state["lus"], current)
            v = np.where(on[:, None, None], v_on, v)
    if onset_m is not None:
        if v_on is None:
            if state["lus"] is None:
                state["lus"] = B2S.factor(*state["g"])
            v_on = B2S.solve(state["lus"], current)
        hit = (v_on < -D.SIG["theta"]) & (sr != 0) & onset_m
        state["onset"] = hit.sum((-2, -1)) / onset_m.sum((-2, -1))
    state["v"] = v
    trig = (v < -D.SIG["theta"]) & (sr != 0)
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t)


def flicker(cases, window, tag=D.TAG):
    """One uniform per case and update (k, window), shared by the flicker arms."""
    return np.stack([address(tag, *c.key(), "flicker").random(window) for c in cases])


def run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE,
        tag=D.TAG, window=D.WINDOW, on_window=None):
    """One run: the event, then every arm for `window` updates with the signal on at (first, last) = on_window or
    D.on_window (delay + 1 to delay + 1,000)."""
    first, last = on_window if on_window is not None else D.on_window(situation, size, delay)
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fps = {d: B2S.footprint(m, d) for d in D.FOOTPRINTS}
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], m[idx]
    ab = (m & ev["am"])[idx]
    fpb = {d: f[idx] for d, f in fps.items()}
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    bio = [a for a in arms if a in B1.BIO]
    vs = Stream(tag, cases, "voltage-noise", side=D.SIDE) if bio else None
    flick = flicker(cases, window, tag) if any(D.SIGNAL_ARMS.get(a, {}).get("p_on", 1.0) < 1.0 for a in arms) else None
    out = {key: [] for key in ENDS}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": cable_kernel(B1.BIO[a]["lam"])}
              for ai, a in enumerate(arms) if a in B1.BIO}
    states.update({ai: new_state(a, k, m) for ai, a in enumerate(arms) if a in D.SIGNAL_ARMS})
    outside = {ai: ~(states[ai]["fp"] if a in D.SIGNAL_ARMS else fps[D.SIG["d"]]) for ai, a in enumerate(arms)}
    signal_updates = {a: 0 for a in arms if a in D.SIGNAL_ARMS}
    vbuf = None
    for t in range(1, window + 1):
        win = first <= t <= last
        pending = t < first
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
                p_on, dur = D.SIGNAL_ARMS[arm]["p_on"], D.SIGNAL_ARMS[arm]["dur"]
                on = win and t < first + dur
                on = on if p_on >= 1.0 else (on & (flick[:, t - 1] < p_on))
                signal_updates[arm] += int(np.sum(on)) if np.ndim(on) else int(on) * k
                xh, xw, extra = sig_targets(arm, V[sl], r[sl], P, states[ai], on, pending, m if t == first else None)
            elif arm in B1.BIO:
                xh, xw, extra = B1S.bio_targets(arm, V[sl], r[sl], P, states[ai], vbuf[i])
            else:
                xh, xw, extra = L5S.targets(arm, V[sl], r[sl], None, P, None)
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                opened_out[sl] += (zone & outside[ai]).mean((-2, -1))
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
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            out["n_anc_ok"].append((((r > 0) == (Tb > 0)) & ab).sum((-2, -1)).astype(float))
            for dd in D.FOOTPRINTS:
                out[f"r_fp{dd}"].append(L5S.inside(r, Tb, fpb[dd]))
            out["r_out8"].append(L5S.inside(r, Tb, ~fpb[8]))
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    onset = np.full(na * k, -1.0)
    for ai, arm in enumerate(arms):
        if arm in D.SIGNAL_ARMS:
            onset[ai * k:(ai + 1) * k] = states[ai]["onset"]
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset,
               n_anc=(m & ev["am"]).sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W)
    return res
