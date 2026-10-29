"""BE005's tissue: BE004's (the dial's footprint and closure unchanged), with the arbiter's own relearning rate and a
membrane time constant per signal arm.

Branches are arm-major (index = arm x cases + case). One update, in order, as in be004.sim.run: the body reads the
record; bond noise; the record steps through its bonds; the trusted targets (the cue arm by lr005.sim.targets and BE001's
arms by be001.sim.bio_targets, unchanged; the signal arms by sig_targets, be004.sim.sig_targets' arithmetic with no hold);
the pull toward committed signs; Hebbian relearning. Two additions, each off at its default:

eta_a   a signal arm's bonds that touch an "arbiter cell" (an anchored cell whose body and record disagree and which is
        not committed, so that its target is the cue) relearn at eta_a; every other bond at ETA. At eta_a = ETA the
        arithmetic is be004's (a scalar rate).
tau_v   a signal arm's potentials relax toward the cable equation's steady state: v <- v + (v* - v) / tau_v, from the
        pre-event steady state (every anchor agreeing: the acquired record's own currents at lam 3). At tau_v = 1, v = v*
        (be004's arithmetic).

With every arm at its defaults (eta_a = ETA, tau_v = 1, no hold, the dial's footprint and closure) a run equals
be004.sim.run bit for bit (checks Q3); a 'never' arm (the signal never on) equals bio-3 bit for bit at the defaults.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001 import design as B1
from be001 import sim as B1S
from be002 import sim as B2S
from be002.sim import cable_kernel, event, patch, prepare  # noqa: F401  (BE001's, unchanged)
from be004 import sim as B4S
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, record_step

from . import design as D

ENDS = ("r_all", "r_in", "v_in", "n_anc_ok", "r_fp0", "r_fp2", "r_fp4", "r_fp8", "r_out8", "r_in_old")


def footprint(m):
    """BE002's footprint: the patch dilated by 2 on the torus (every BE005 signal arm's)."""
    return B2S.footprint(m, D.SIG["d"])


def pre_event_potential(R0, am):
    """The steady potentials before the event: the acquired record's own currents (every anchor agreeing) at lam 3."""
    aval = np.where(R0 > 0, 1.0, -1.0)
    cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(R0)
    return np.real(np.fft.ifft2(np.fft.fft2(cur) / cable_kernel(D.SIG["lam_rest"])))


def new_state(k, m, v0=None):
    fp = footprint(m)
    return {"v": np.zeros((k, D.SIDE, D.SIDE)) if v0 is None else v0.copy(), "s": np.zeros((k, D.SIDE, D.SIDE)),
            "sgn": np.zeros((k, D.SIDE, D.SIDE)), "lus": None, "fp": fp,
            "g": B2S.conductances(fp, D.SIG["lam_rest"], D.SIG["lam_sig"]), "kernel": cable_kernel(D.SIG["lam_rest"]),
            "onset": np.full(k, -1.0), "hit": np.zeros((k, D.SIDE, D.SIDE), bool)}


def sig_targets(arm, V, r, P, state, on, onset_m=None):
    """Trusted signs for one signal arm's branches; updates state in place. on: a bool or a (k,) bool array (flicker);
    onset_m: the patch at the signal's first update (records the share of the patch below -theta under the footprint's
    steady potentials). Returns the bond targets, (committed, targets) and the arbiter cells. With tau_v = 1 the
    arithmetic is be004.sim.sig_targets' for the dial with no hold."""
    tau_v = D.SIGNAL_ARMS[arm]["tau_v"]
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
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
    if tau_v != 1:
        v = state["v"] + (v - state["v"]) / tau_v
    state["v"] = v
    trig = (v < -D.SIG["theta"]) & (sr != 0)
    state["hit"] |= trig
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    fix = ~agree & (ca != 0) & ~committed
    return *L5S.rel(t), (committed, t), fix


def flicker(cases, window, tag=D.TAG):
    return B4S.flicker(cases, window, tag)


def run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE,
        tag=D.TAG, window=D.WINDOW, on_window=None):
    """One run: the event, then every arm for `window` updates with the signal on at (first, last) = on_window or
    D.on_window (delay + 1 to delay + 1,000), an arm's duration, flicker and 'never' acting inside it."""
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
    anc_on = np.full(na * k, -1.0)
    v_pre = pre_event_potential(R0, ev["am"]) if any(D.SIGNAL_ARMS.get(a, {}).get("tau_v", 1) != 1 for a in arms) else None
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": cable_kernel(B1.BIO[a]["lam"])}
              for ai, a in enumerate(arms) if a in B1.BIO}
    states.update({ai: new_state(k, m, v_pre if D.SIGNAL_ARMS[a]["tau_v"] != 1 else None)
                   for ai, a in enumerate(arms) if a in D.SIGNAL_ARMS})
    outside = {ai: ~(states[ai]["fp"] if a in D.SIGNAL_ARMS else fps[D.SIG["d"]]) for ai, a in enumerate(arms)}
    signal_updates = {a: 0 for a in arms if a in D.SIGNAL_ARMS}
    vbuf = None
    for t in range(1, window + 1):
        win = first <= t <= last
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
            fix = None
            if arm in D.SIGNAL_ARMS:
                prm = D.SIGNAL_ARMS[arm]
                if t == first:
                    anc_on[sl] = (((r[sl] > 0) == (Tb[sl] > 0)) & ab[sl]).sum((-2, -1)).astype(float)
                on = win and t < first + prm["dur"] and not prm["never"]
                on = on if prm["p_on"] >= 1.0 else (on & (flick[:, t - 1] < prm["p_on"]))
                signal_updates[arm] += int(np.sum(on)) if np.ndim(on) else int(on) * k
                onset_m = m if (t == first and not prm["never"]) else None
                xh, xw, extra, fix = sig_targets(arm, V[sl], r[sl], P, states[ai], on, onset_m)
                if prm["eta_a"] == D.ETA:
                    fix = None
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
            if fix is None:
                Hn, Wn = Hb[sl] + D.ETA * (xh - Hb[sl]), Wb[sl] + D.ETA * (xw - Wb[sl])
            else:
                ea = D.SIGNAL_ARMS[arm]["eta_a"]
                eh = np.where(fix | np.roll(fix, -1, -1), ea, D.ETA)
                ew = np.where(fix | np.roll(fix, -1, -2), ea, D.ETA)
                Hn, Wn = Hb[sl] + eh * (xh - Hb[sl]), Wb[sl] + ew * (xw - Wb[sl])
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
    onset, hit = np.full(na * k, -1.0), np.full(na * k, -1.0)
    for ai, arm in enumerate(arms):
        if arm in D.SIGNAL_ARMS:
            sl = slice(ai * k, (ai + 1) * k)
            onset[sl] = states[ai]["onset"]
            hit[sl] = (states[ai]["hit"] & m).sum((-2, -1)) / m.sum((-2, -1))
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset, hit=hit,
               anc_on=anc_on, n_anc=(m & ev["am"]).sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W)
    return res
