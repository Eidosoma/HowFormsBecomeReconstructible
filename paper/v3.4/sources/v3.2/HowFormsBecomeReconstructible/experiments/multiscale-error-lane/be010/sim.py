"""BE010's tissue: BE007's (be007.sim's arithmetic for clock C12, unchanged: BE006's clock SL, BE005's events, footprint and
dial, LR004's arbiter, the commit form), with a second event per arm at the start of update T_W + 1 and re-execution.

Branches are arm-major (index = arm x cases + case). One update, in order, as in be007.sim.run: the body reads the
record; bond noise; the record steps through its bonds; the trusted targets (be007.sim.sig_targets, unchanged); the pull
toward committed signs; Hebbian relearning. The additions, each off for reset None:

second event  at the start of update T_W + 1, in the arm's branches:
              wound       in the patch m: body and moving average <- the lane's newborn values (lr005.sim.newborn:
                          KILL_SD x N(0, 1), stream 'newborn'), record 0, decision state 0, trusted sign 0, every
                          contact touching m untrained (sign 0, strength 0; cellpop.core.touching); the anchors stay
              wound-kept  the same, but only contacts with both ends in m untrained
              decommit    everywhere: decision state 0 and trusted sign 0; nothing else
re-execution  for rexec arms, C12's commit again at T_W + tau_x (be007.sim.sig_targets called with tau_x moved there
              after T_W; the share of the patch that executed then is 'executed2')

With reset None every arm is be007.sim.run's arm of the same clock bit for bit (checks Q3); before T_W + 1 every arm of a
run equals its reset-None arm bit for bit (checks Q5).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be002 import sim as B2S
from be005.sim import ENDS, event, new_state, patch, prepare  # noqa: F401  (BE005's, unchanged)
from be007.sim import sig_targets  # noqa: F401  (BE007's, unchanged)
from cellpop.core import touching
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, record_step

from . import design as D


def second_event(kind, m, k, V, E, r, H, W, Hb, Wb, state, nb):
    """Apply one arm's second event to its branches (arrays (k, side, side), changed in place); m: the patch (k, side,
    side); nb: the newborn values (k, side, side). The wounds clear the decision state in the patch, the drug everywhere."""
    if kind in ("wound", "wound-kept"):
        V[:], E[:], r[:] = np.where(m, nb, V), np.where(m, nb, E), np.where(m, 0.0, r)
        if kind == "wound":
            th, tw = touching(m)
        else:
            th, tw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
        H[:], Hb[:] = np.where(th, 0.0, H), np.where(th, 0.0, Hb)
        W[:], Wb[:] = np.where(tw, 0.0, W), np.where(tw, 0.0, Wb)
    elif kind != "decommit":
        raise ValueError(kind)
    clear = m if kind != "decommit" else np.ones_like(m)
    state["s"] = np.where(clear, 0.0, state["s"])
    state["sgn"] = np.where(clear, 0.0, state["sgn"])


def run(body, situation, size, d, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, tag=D.TAG,
        window=None, on_window=None, params=None, observe=None, t_w=D.T_W):
    """One run: the event, then every arm for `window` updates with the signal on at (first, last) = on_window or
    D.on_window (T_W + d + 1 to T_W + d + 1,000), 'never' arms never, and each arm's second event at t_w + 1.
    params: arm -> {eta_a, eta, rate, tau_c, form, tau_x, never, reset, rexec} (default D.SIGNAL_ARMS).
    observe(t, states, V, r): an optional hook for probes."""
    params = D.SIGNAL_ARMS if params is None else params
    first, last = on_window if on_window is not None else D.on_window(situation, size, d)
    window = D.run_window(situation, size, d, arms) if window is None else window
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    prms = [params[a] for a in arms]
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fps = {dd: B2S.footprint(m, dd) for dd in (0, 2, 4, 8)}
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], m[idx]
    ab = (m & ev["am"])[idx]
    fpb = {dd: f[idx] for dd, f in fps.items()}
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cuts = [cut_for(q["rate"]) for q in prms]
    cut = cuts[0] if len(set(cuts)) == 1 else np.repeat(np.array(cuts), k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    nb = L5S.newborn(cases, tag) if any(q.get("reset") in ("wound", "wound-kept") for q in prms) else None
    out = {key: [] for key in ENDS}
    out["committed_in"], out["conf_in"] = [], []
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    anc_on = np.full(na * k, -1.0)
    executed, executed2 = np.full(na * k, -1.0), np.full(na * k, -1.0)
    states = {ai: new_state(k, m) for ai in range(na)}
    outside = {ai: ~states[ai]["fp"] for ai in range(na)}
    later = [dict(q, tau_x=t_w + q["tau_x"]) if q.get("rexec") else q for q in prms]
    signal_updates = {a: 0 for a in arms}
    comm = np.zeros((na * k, D.SIDE, D.SIDE), bool)
    for t in range(1, window + 1):
        if t == t_w + 1:
            for ai in range(na):
                if prms[ai].get("reset") is not None:
                    sl = slice(ai * k, (ai + 1) * k)
                    second_event(prms[ai]["reset"], m, k, V[sl], E[sl], r[sl], H[sl], W[sl], Hb[sl], Wb[sl],
                                 states[ai], nb)
        win = first <= t <= last
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, dv = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            prm = prms[ai] if t <= t_w else later[ai]
            if t == first:
                anc_on[sl] = (((r[sl] > 0) == (Tb[sl] > 0)) & ab[sl]).sum((-2, -1)).astype(float)
            on = win and not prm["never"]
            signal_updates[arm] += int(on) * k
            onset_m = m if (t == first and not prm["never"]) else None
            xh, xw, extra, fix = sig_targets(prm, V[sl], r[sl], P, states[ai], on, t, onset_m)
            if prm["form"] == "commit" and t == prm["tau_x"]:
                share = (states[ai]["executed"] & m).sum((-2, -1)) / m.sum((-2, -1))
                if t <= t_w:
                    executed[sl] = share
                else:
                    executed2[sl] = share
            if prm["eta_a"] == prm["eta"]:
                fix = None
            zone, tt = extra
            comm[sl] = zone
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
            observe(t, states, V, r)
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
            out["committed_in"].append((comm & mb).sum((-2, -1)) / mb.sum((-2, -1)))
            out["conf_in"].append(((np.abs(r) >= D.VMIN) & mb).sum((-2, -1)) / mb.sum((-2, -1)))
    res = {key: np.array(v) for key, v in out.items() if v}
    onset, hit = np.full(na * k, -1.0), np.full(na * k, -1.0)
    for ai, arm in enumerate(arms):
        sl = slice(ai * k, (ai + 1) * k)
        onset[sl] = states[ai]["onset"]
        hit[sl] = (states[ai]["hit"] & m).sum((-2, -1)) / m.sum((-2, -1))
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset, hit=hit,
               anc_on=anc_on, executed=executed, executed2=executed2, n_anc=(m & ev["am"]).sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W)
    return res
