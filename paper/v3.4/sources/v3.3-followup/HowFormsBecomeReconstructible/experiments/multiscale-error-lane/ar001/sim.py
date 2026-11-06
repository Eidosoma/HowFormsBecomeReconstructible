"""AR001's tissue: BE006's at clock SL, with every fixed policy and the controller as arms of one run.

Branches are arm-major (index = arm x cases + case); every branch reads the case's body, record and bond-noise streams
(the vote's second record its own "B" streams, as in lr005.sim.run), so the arms are paired. One update, in order, as in
lr005.sim.run and be006.sim.run: the body reads the first record (dl001.sim.body); bond noise (one rate for every arm);
the records step through their bonds (msegrid.record_step); the trusted targets (lr005.sim.targets for record, body,
vote and arbiter; the latch by latch_targets, lr005's community arithmetic with its hold a parameter; rest and dial by
be006.sim.sig_targets, unchanged); the pull toward committed or latched signs; Hebbian relearning at the clock's rate;
parity (record only). The inactive arm computes no target and never learns.

Bridges (checks Q3): with arms rest and dial at sigma 0 and BE006's tag, a run equals be006.sim.run's never-SL and
dial-SL bit for bit; at the lane's clock on an 8 x 8 patch with LR005's tag and the latch's hold 300, the record, body,
vote, arbiter and latch arms equal lr005.sim.run's record+parity, body, vote2r, cue and community-s bit for bit.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001 import sim as B1S
from be001.sim import cable_kernel, prepare  # noqa: F401  (DL002's preparation via lr002.sim, unchanged)
from be002 import sim as B2S
from be006 import sim as B6S
from dl001 import design as DL
from dl001 import sim as S
from gc001 import sim as GCS
from lr001.sim import cut_for, edges_from, halves, parity_repair
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, bonds, record_step

from . import design as D

ENDS = ("r_in", "r_in_old", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
SCALARS = ("opened", "opened_out", "onset", "hit")
LR5_NAME = {"record": "record+parity", "body": "body", "vote": "vote2r", "arbiter": "cue"}


def event(situation, size, sigma, cases, V0, ema0, R0, T, tag=D.TAG):
    """be001.sim.event (unchanged) for none, memory, shared, cue and change; body adds lr005's body flip to none, and
    correlated adds it to memory (the body and the record agree on the error). Then, at sigma > 0, the anchors read
    the event's cue field at GC001's quenched noisy position (gc001.sim.read_at, unit_normals under this tag)."""
    base = {"body": "none", "correlated": "memory"}.get(situation, situation)
    ev = B1S.event(base, size, cases, V0, ema0, R0, T, tag)
    if situation in ("body", "correlated"):
        ev["V"] = np.where(ev["m"], -ev["V"], ev["V"])
    exact = ev["aval"]
    if sigma:
        ev["aval"] = GCS.read_at(exact, GCS.unit_normals(cases, tag), sigma)
    ev["mis"] = (ev["aval"] != exact) & ev["am"]
    return ev


def footprint(m, d, shift):
    """The arm's footprint: the patch dilated by d on the torus (be002.sim.footprint), shifted by `shift` along the rows."""
    fp = B2S.footprint(m, d)
    return np.roll(fp, shift, -1) if shift else fp


def new_state(k, m, d=D.SIG["d"], shift=0):
    """be005.sim.new_state's fields with the arm's footprint (equal to it at d = 2, shift 0)."""
    fp = footprint(m, d, shift)
    z = np.zeros((k, D.SIDE, D.SIDE))
    return {"v": z.copy(), "s": z.copy(), "sgn": z.copy(), "lus": None, "fp": fp,
            "g": B2S.conductances(fp, D.SIG["lam_rest"], D.SIG["lam_sig"]), "kernel": cable_kernel(D.SIG["lam_rest"]),
            "onset": np.full(k, -1.0), "hit": np.zeros((k, D.SIDE, D.SIDE), bool)}


def latch_targets(V, r, P, latch, hold, q=D.Q_LATCH):
    """lr005.sim.targets' community arithmetic (unchanged) with the latch's hold as a parameter."""
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    n_live, n_dis = L5S.box(live.astype(float), D.RHO), L5S.box(dis.astype(float), D.RHO)
    zone = (n_live >= D.MIN_ANCHORS) & (n_dis >= q * n_live) & (sr != 0)
    age, sgn = latch
    sgn[:] = np.where(zone & (age == 0), -sr, sgn)
    age[:] = np.where(zone, hold, np.maximum(age - 1, 0))
    zone = age > 0
    t = np.where(zone, sgn, t)
    return *L5S.rel(t), (zone, t)


def run(body, situation, sigma, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, tag=D.TAG,
        window=D.WINDOW, size=D.SIZE, clock=None, hold=None, observe=None):
    """One run: the event, then every arm for `window` updates. clock: {eta, rate, tau_c} (default D.CLOCK); hold: the
    latch's hold (default the clock's tau_c). observe(t, V, r, H, W): an optional hook for checks."""
    clock = D.CLOCK if clock is None else clock
    hold = int(clock["tau_c"]) if hold is None else hold
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    specs = [D.ARM[a] for a in arms]
    kinds = [s["kind"] for s in specs]
    assert kinds.count("vote") <= 1
    ev = event(situation, size, sigma, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fp2 = B2S.footprint(m, D.SIG["d"])
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb, fpb = ev["target"][idx], (th * theta)[idx], m[idx], fp2[idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    s_post = r > 0                                               # the post-event record's signs (the dose's origin)
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(clock["rate"])
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    vi = kinds.index("vote") if "vote" in kinds else None
    if vi is not None:
        tb = np.arange(vi * k, (vi + 1) * k)
        HB, WB, HbB, WbB, rB = H[tb].copy(), W[tb].copy(), Hb[tb].copy(), Wb[tb].copy(), r[tb].copy()
        if situation in ("memory", "correlated"):                # the event hit the first record only
            H0, W0 = edges_from(bonds(R0, True))
            rB, HB, WB = R0.copy(), H0.copy(), W0.copy()
            HbB, WbB = D.STRENGTH0 * HB, D.STRENGTH0 * WB
        xsB, zsB = (Stream(tag, cases, s, "B", side=D.SIDE) for s in ("record-noise", "bond-noise"))
    states = {ai: new_state(k, m, specs[ai]["d"], specs[ai]["shift"]) for ai in range(na) if kinds[ai] in ("rest", "dial")}
    latches = {ai: (np.zeros((k, D.SIDE, D.SIDE), int), np.zeros((k, D.SIDE, D.SIDE))) for ai in range(na)
               if kinds[ai] == "latch"}
    windows = {ai: (specs[ai]["delay"] + 1, specs[ai]["delay"] + D.SIG["duration"]) for ai in range(na)
               if kinds[ai] == "dial"}
    prm = {"tau_c": clock["tau_c"]}
    out = {key: [] for key in ENDS}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    signal_updates = {a: 0 for a in arms}
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if vi is not None:
                xbB, zbB = xsB.take(D.CHUNK), zsB.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        if vi is not None:
            zB = zbB[i]
            h2, w2 = zB > cut, zB < -cut
            HB, WB, HbB, WbB = np.where(h2, -HB, HB), np.where(w2, -WB, WB), np.where(h2, -HbB, HbB), np.where(w2, -WbB, WbB)
            rB = record_step(rB, xbB[i], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(HB, WB))
        for ai, kind in enumerate(kinds):
            if kind == "inactive":
                continue
            sl = slice(ai * k, (ai + 1) * k)
            if kind in ("rest", "dial"):
                on = kind == "dial" and windows[ai][0] <= t <= windows[ai][1]
                signal_updates[arms[ai]] += int(on) * k
                onset_m = m if (kind == "dial" and t == windows[ai][0]) else None
                xh, xw, extra, _fix = B6S.sig_targets(prm, V[sl], r[sl], P, states[ai], on, onset_m)
            elif kind == "latch":
                xh, xw, extra = latch_targets(V[sl], r[sl], P, latches[ai], hold)
            else:
                xh, xw, extra = L5S.targets(LR5_NAME[kind], V[sl], r[sl], rB if kind == "vote" else None, P, None)
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                opened_out[sl] += (zone & ~fp2).mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + eta * (xh - Hb[sl]), Wb[sl] + eta * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
            if kind == "vote":
                HbB, WbB = np.where(lh, HbB + eta * (xh - HbB), HbB), np.where(lw, WbB + eta * (xw - WbB), WbB)
                HB = np.where(lh & (HbB != 0), np.sign(HbB), HB)
                WB = np.where(lw & (WbB != 0), np.sign(WbB), WB)
            if kind == "record":
                H2, W2 = parity_repair(H[sl], W[sl])
                Hb[sl] = np.where(np.sign(Hb[sl]) * H2 < 0, -Hb[sl], Hb[sl])
                Wb[sl] = np.where(np.sign(Wb[sl]) * W2 < 0, -Wb[sl], Wb[sl])
                H[sl], W[sl] = H2, W2
        if observe is not None:
            observe(t, V, r, H, W)
        if t % D.TRACE == 0:
            trace.append(L5S.inside(r, Tb, mb))
        if t in reads:
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["r_all"].append(S.sign(r, Tb))
            out["r_fp"].append(L5S.inside(r, Tb, fpb))
            out["r_out"].append(L5S.inside(r, Tb, ~fpb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            out["v_all"].append(S.sign(V, Tb))
            out["r_dose"].append(((r > 0) != s_post).mean((-2, -1)))
            out["r_dose_in"].append((((r > 0) != s_post) & mb).sum((-2, -1)) / mb.sum((-2, -1)))
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    onset, hit = np.full(na * k, -1.0), np.full(na * k, -1.0)
    for ai in states:
        sl = slice(ai * k, (ai + 1) * k)
        onset[sl] = states[ai]["onset"]
        hit[sl] = (states[ai]["hit"] & m).sum((-2, -1)) / m.sum((-2, -1))
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset, hit=hit,
               n_anc=(m & ev["am"]).sum((-2, -1)).astype(float), n_mis=ev["mis"].sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W)
    if vi is not None:
        res.update(rB=rB, HB=HB, WB=WB)
    return res
