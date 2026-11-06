"""BE006's tissue: BE005's (BE004's events, footprint and dial, LR004's arbiter, the arbiter's own relearning rate),
with three clocks set per arm: the arbiter's rate eta_a (BE005's), every other bond's Hebbian rate eta with its
bond-noise rate p_b, and the commitment's decay time tau_c.

Branches are arm-major (index = arm x cases + case). One update, in order, as in be005.sim.run: the body reads the
record; bond noise (each arm at its own p_b, from the same standard normal per bond, so a slower arm's flips are a subset
of a faster arm's); the record steps through its bonds; the trusted targets (be005.sim.sig_targets' arithmetic with
tau_v = 1 and no flicker, the slow state decaying by exp(-1 / tau_c)); the pull toward committed signs; Hebbian
relearning (the bonds touching an arbiter cell at eta_a, every other bond at eta). Every arm is a signal arm (the dial,
or 'never': the same tissue with the signal never on).

With an arm at eta_a = eta = 0.01, p_b = 1e-3 and tau_c = 300 (clock F), a run equals be005.sim.run's dial-e0.01 and
never-e0.01 bit for bit, and with eta = 0.01, p_b = 1e-3, tau_c = 300 and any eta_a it equals be005.sim.run's dial-e and
never-e arms at that eta_a (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be002 import sim as B2S
from be005.sim import ENDS, event, footprint, new_state, patch, prepare  # noqa: F401  (BE005's, unchanged)
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, record_step

from . import design as D


def sig_targets(prm, V, r, P, state, on, onset_m=None):
    """Trusted signs for one signal arm's branches; updates state in place (be005.sim.sig_targets' arithmetic at tau_v = 1
    with a scalar `on`, the slow state decaying by exp(-1 / tau_c)). Returns the bond targets, (committed, targets) and
    the arbiter cells."""
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    current = D.KAPPA * ca * sr
    if on:
        if state["lus"] is None:
            state["lus"] = B2S.factor(*state["g"])
        v = B2S.solve(state["lus"], current)
    else:
        v = np.real(np.fft.ifft2(np.fft.fft2(current) / state["kernel"]))
    v_on = v if on else None
    if onset_m is not None:
        if v_on is None:
            if state["lus"] is None:
                state["lus"] = B2S.factor(*state["g"])
            v_on = B2S.solve(state["lus"], current)
        hit = (v_on < -D.SIG["theta"]) & (sr != 0) & onset_m
        state["onset"] = hit.sum((-2, -1)) / onset_m.sum((-2, -1))
    state["v"] = v
    trig = (v < -D.SIG["theta"]) & (sr != 0)
    state["hit"] |= trig
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / prm["tau_c"]))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    fix = ~agree & (ca != 0) & ~committed
    return *L5S.rel(t), (committed, t), fix


def run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, tag=D.TAG,
        window=None, on_window=None, params=None, observe=None):
    """One run: the event, then every arm for `window` updates with the signal on at (first, last) = on_window or
    D.on_window (delay + 1 to delay + 1,000), 'never' arms never. params: arm -> {eta_a, eta, rate, tau_c, never}
    (default D.SIGNAL_ARMS). observe(t, states, fix_by_arm, committed_by_arm, V, r): an optional hook for probes."""
    params = D.SIGNAL_ARMS if params is None else params
    first, last = on_window if on_window is not None else D.on_window(situation, size, delay)
    window = D.run_window(situation, size, delay, arms) if window is None else window
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    prms = [params[a] for a in arms]
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fps = {d: B2S.footprint(m, d) for d in (0, 2, 4, 8)}
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], m[idx]
    ab = (m & ev["am"])[idx]
    fpb = {d: f[idx] for d, f in fps.items()}
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cuts = [cut_for(q["rate"]) for q in prms]
    cut = cuts[0] if len(set(cuts)) == 1 else np.repeat(np.array(cuts), k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ENDS}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    anc_on = np.full(na * k, -1.0)
    states = {ai: new_state(k, m) for ai in range(na)}
    outside = {ai: ~states[ai]["fp"] for ai in range(na)}
    signal_updates = {a: 0 for a in arms}
    for t in range(1, window + 1):
        win = first <= t <= last
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        fixes, comms = {}, {}
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            prm = prms[ai]
            if t == first:
                anc_on[sl] = (((r[sl] > 0) == (Tb[sl] > 0)) & ab[sl]).sum((-2, -1)).astype(float)
            on = win and not prm["never"]
            signal_updates[arm] += int(on) * k
            onset_m = m if (t == first and not prm["never"]) else None
            xh, xw, extra, fix = sig_targets(prm, V[sl], r[sl], P, states[ai], on, onset_m)
            if observe is not None:
                fixes[arm], comms[arm] = fix, extra[0]
            if prm["eta_a"] == prm["eta"]:
                fix = None
            zone, tt = extra
            opened[sl] += zone.mean((-2, -1))
            opened_out[sl] += (zone & outside[ai]).mean((-2, -1))
            r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            eta = prm["eta"]
            if fix is None:
                Hn, Wn = Hb[sl] + eta * (xh - Hb[sl]), Wb[sl] + eta * (xw - Wb[sl])
            else:
                ea = prm["eta_a"]
                eh = np.where(fix | np.roll(fix, -1, -1), ea, eta)
                ew = np.where(fix | np.roll(fix, -1, -2), ea, eta)
                Hn, Wn = Hb[sl] + eh * (xh - Hb[sl]), Wb[sl] + ew * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if observe is not None:
            observe(t, states, fixes, comms, V, r)
        if t % D.TRACE == 0:
            trace.append(L5S.inside(r, Tb, mb))
        if t in reads:
            out["r_all"].append(S.sign(r, Tb))
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            out["n_anc_ok"].append((((r > 0) == (Tb > 0)) & ab).sum((-2, -1)).astype(float))
            for dd in (0, 2, 4, 8):
                out[f"r_fp{dd}"].append(L5S.inside(r, Tb, fpb[dd]))
            out["r_out8"].append(L5S.inside(r, Tb, ~fpb[8]))
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    onset, hit = np.full(na * k, -1.0), np.full(na * k, -1.0)
    for ai, arm in enumerate(arms):
        sl = slice(ai * k, (ai + 1) * k)
        onset[sl] = states[ai]["onset"]
        hit[sl] = (states[ai]["hit"] & m).sum((-2, -1)) / m.sum((-2, -1))
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset, hit=hit,
               anc_on=anc_on, n_anc=(m & ev["am"]).sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W)
    return res
