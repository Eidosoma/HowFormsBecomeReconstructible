"""AR002's arms: AR001's (ar001.sim.run, imported unchanged) and the controller driven by a detector inside the tissue
(run_det).

run_det is ar001.sim.run's loop for BE006's signal arms only (the body reads the first record; bond noise; the record
steps through its bonds; the trusted targets by be006.sim.sig_targets' arithmetic; the pull toward committed signs;
Hebbian relearning at the clock's rate), with the signal set per case by a detector instead of a declared window:
  each update, after the record's step and before the targets, the arm's detector reads that update's body, record and
  anchors (detect); the first time a window's criterion has held for DWELL consecutive updates it fires, once per case,
  and the dial opens over its zone dilated by SIG['d'] (2) for SIG['duration'] (1,000) updates from that update on.
Before its onset (and if it never fires) a det arm is rest; with an oracle that fires at update 1 over the patch it is
AR001's dial (checks Q3, bit for bit). Every branch reads the case's body, record and bond-noise streams, so a det arm
is paired with AR001's arms run separately on the same case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.sparse.linalg import splu

from ar001 import design as A
from ar001 import sim as A1S
from be002 import sim as B2S
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, record_step

from . import design as D

prepare, event = A1S.prepare, A1S.event
ENDS = A1S.ENDS
SCALARS = A1S.SCALARS
DET_SCALARS = ("det_on", "det_zone", "det_fp", "det_zone_in", "det_fp_in", "det_windows", "det_by")


# the detector -----------------------------------------------------------------------------------------------------

def wsum(x, b):
    """(k, n, n) counts over the b x b window whose top-left corner is each cell (periodic)."""
    y = x
    for d in range(1, b):
        y = y + np.roll(x, -d, -1)
    z = y
    for d in range(1, b):
        z = z + np.roll(y, -d, -2)
    return z


def cover(f, b):
    """Every cell of the b x b windows whose top-left corners are f (periodic)."""
    y = f
    for d in range(1, b):
        y = y | np.roll(f, d, -1)
    z = y
    for d in range(1, b):
        z = z | np.roll(y, d, -2)
    return z


def channel_windows(V, r, P, ch, kind):
    """(k, n, n) bool: the windows (by top-left corner) whose criterion holds on this state, for one channel.
    cue: the live anchors (anchor present, record confident) that disagree with the record, at least ch['n'] of them
    and at least a fraction ch['q'] of the live ones, with at most ch['ring_max'] disagreeing live anchors in the ring
    of width ch['ring'] around the window (no ring at width 0). body: the confident body and record disagreeing in at
    least ch['n'] cells and a fraction ch['q'] of the cells where both are confident."""
    b = ch["box"]
    sr = L5S.vote_sign(r)
    if kind == "cue":
        ca = np.where(P["am"], P["aval"], 0.0)
        live = (ca != 0) & (sr != 0)
        dis = (live & (ca != sr)).astype(np.int16)
        nd, nl = wsum(dis, b), wsum(live.astype(np.int16), b)
        f = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
        g = ch.get("ring", 0)
        if g:
            outer = np.roll(wsum(dis, b + 2 * g), (g, g), (-2, -1))
            f &= (outer - nd) <= ch["ring_max"]
        return f
    sv = L5S.vote_sign(V)
    both = (sv != 0) & (sr != 0)
    mis = both & (sv != sr)
    nm, nb = wsum(mis.astype(np.int16), b), wsum(both.astype(np.int16), b)
    return (nm >= ch["n"]) & (nm >= ch["q"] * nb)


def integral(x, lo, hi):
    """The integral image of x (k, n, n) wrap-padded to rows and columns -lo .. n + hi - 1: S[:, i, j] is the sum of x
    over rows -lo .. i - lo - 1 and columns -lo .. j - lo - 1 (periodic), in int32 (exact)."""
    n = x.shape[-1]
    idx = np.arange(-lo, n + hi) % n
    S = np.zeros((x.shape[0], n + lo + hi + 1, n + lo + hi + 1), np.int32)
    S[:, 1:, 1:] = x[:, idx][:, :, idx].astype(np.int32).cumsum(1).cumsum(2)
    return S


def window_sums(S, lo, b, off, n):
    """(k, n, n): the sums over the b x b windows whose top-left corners are (i + off, j + off), from S = integral(x, lo,
    hi) (lo >= -off, hi >= off + b - 1). With off 0 they equal wsum(x, b) exactly."""
    a, c = off + lo, off + lo + b
    return S[:, c:c + n, c:c + n] - S[:, a:a + n, c:c + n] - S[:, c:c + n, a:a + n] + S[:, a:a + n, a:a + n]


def cue_windows_multi(r, P, ch):
    """{box: (k, n, n) bool}: the cue channel's windows at every box in ch['boxes'], each with channel_windows'
    criterion at that box (n, q, ring, ring_max), by integral images: the counts are integers, so each box's windows
    equal channel_windows' at that box exactly."""
    n = r.shape[-1]
    sr = L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    g = ch.get("ring", 0)
    lo, hi = g, max(ch["boxes"]) + g
    Sd, Sl = integral(dis, lo, hi), integral(live, lo, hi)
    out = {}
    for b in ch["boxes"]:
        nd, nl = window_sums(Sd, lo, b, 0, n), window_sums(Sl, lo, b, 0, n)
        f = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
        if g:
            f &= (window_sums(Sd, lo, b + 2 * g, -g, n) - nd) <= ch["ring_max"]
        out[b] = f
    return out


def new_det(k):
    z = np.zeros((k, D.SIDE, D.SIDE))
    zb = np.zeros((k, D.SIDE, D.SIDE), bool)
    return {"v": z.copy(), "s": z.copy(), "sgn": z.copy(), "kernel": A1S.cable_kernel(D.SIG["lam_rest"]),
            "lus": [None] * k, "fp": zb.copy(), "zone": zb.copy(), "count": {},
            "t_on": np.zeros(k, int), "windows": np.zeros(k), "by": np.zeros(k), "onset": np.full(k, -1.0),
            "hit": zb.copy()}


def fire(state, j, zone, t, nwin, by=0):
    """Fire case j's detector at update t over zone: its footprint, conductances and sparse LU (be002's)."""
    fp = B2S.footprint(zone[None], D.SIG["d"])[0]
    gH, gW = B2S.conductances(fp[None], D.SIG["lam_rest"], D.SIG["lam_sig"])
    state["t_on"][j], state["zone"][j], state["fp"][j], state["windows"][j], state["by"][j] = t, zone, fp, nwin, by
    state["lus"][j] = splu(B2S.cable_matrix(gH[0], gW[0]))


def detect(state, V, r, P, cfg, t, m=None):
    """One update of an arm's detector, before the targets. A channel's window (at its box, or at each of its boxes)
    that has held its criterion for the channel's dwell (consecutive updates, counted per box) fires the detector, once
    per case; the zone is every cell of the windows held at that update, in either channel and at any box. by records
    the channels that fired (1 cue, 2 body, 3 both). m is read by the oracle only (a check's arm, never a registered
    one)."""
    waiting = state["t_on"] == 0
    if not waiting.any():
        return
    if cfg.get("oracle"):
        if t == 1 + cfg.get("delay", 0):
            for j in np.flatnonzero(waiting):
                fire(state, j, m[j], t, 0)
        return
    if cfg.get("never"):
        return
    held = []
    for bit, c in ((1, "cue"), (2, "body")):
        ch = cfg.get(c)
        if not ch:
            continue
        fs = cue_windows_multi(r, P, ch) if "boxes" in ch else {ch["box"]: channel_windows(V, r, P, ch, c)}
        for b, f in fs.items():
            cnt = state["count"].get((c, b))
            cnt = np.where(f, (np.zeros(f.shape, np.int32) if cnt is None else cnt) + 1, 0)
            state["count"][(c, b)] = cnt
            held.append((bit, b, cnt >= ch["dwell"]))
    by = np.zeros(len(V), int)
    nwin = np.zeros(len(V), int)
    for bit, b, ready in held:
        by |= np.where(ready.any((-2, -1)), bit, 0)
        nwin += ready.sum((-2, -1))
    new = (by > 0) & waiting
    if new.any():
        zone = np.zeros(V.shape, bool)
        for bit, b, ready in held:
            zone |= cover(ready, b)
        for j in np.flatnonzero(new):
            fire(state, j, zone[j], t, int(nwin[j]), int(by[j]))


def sig_targets_cases(prm, V, r, P, state, on, onset, m):
    """be006.sim.sig_targets' arithmetic (tau_v = 1; the slow state decaying by exp(-1 / tau_c)) with the signal on per
    case: on (k,) bool. The cable equation is solved by each case's own sparse LU where on, by the FFT at rest
    elsewhere; at a case's onset its patch's trigger fraction is recorded (be006's onset_m, a diagnostic)."""
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    current = A.KAPPA * ca * sr
    n = current.shape[-1]
    if on.all():
        v = np.stack([state["lus"][j].solve(current[j].ravel()).reshape(n, n) for j in range(len(on))])
    else:
        v = np.real(np.fft.ifft2(np.fft.fft2(current) / state["kernel"]))
        for j in np.flatnonzero(on):
            v[j] = state["lus"][j].solve(current[j].ravel()).reshape(n, n)
    for j in np.flatnonzero(onset):
        hit = (v[j] < -A.SIG["theta"]) & (sr[j] != 0) & m[j]
        state["onset"][j] = hit.sum((-2, -1)) / m[j].sum((-2, -1))
    state["v"] = v
    trig = (v < -A.SIG["theta"]) & (sr != 0)
    state["hit"] |= trig
    was = state["s"] >= A.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / prm["tau_c"]))
    committed = state["s"] >= A.S_MIN
    t = np.where(committed, state["sgn"], t)
    fix = ~agree & (ca != 0) & ~committed
    return *L5S.rel(t), (committed, t), fix


def run_det(body, situation, sigma, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=A.GAIN, tag=D.TAG,
            window=A.WINDOW, size=A.SIZE, clock=None, detectors=None, observe=None, pre=None):
    """One run of detector-driven controller arms: the event (ar001.sim.event), then every arm for `window` updates.
    arms: names in detectors (default D.DETECTORS); 'rest' is allowed (a detector that never fires). observe(t, V, r, H,
    W, states) runs at the end of an update; pre(t, V, r, P, m) after the record's step, on the state the detectors read
    (probes and checks only)."""
    clock = A.CLOCK if clock is None else clock
    detectors = D.DETECTORS if detectors is None else detectors
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    G = S.ghat(A.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    cfgs = [{"never": True} if a == "rest" else detectors[a] for a in arms]
    ev = event(situation, size, sigma, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fp2 = B2S.footprint(m, A.SIG["d"])
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb, fpb = ev["target"][idx], (th * theta)[idx], m[idx], fp2[idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    s_post = r > 0
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(clock["rate"])
    p = replace(NATIVE, sigma=A.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=A.SIDE) for s in ("future", "record-noise", "bond-noise"))
    states = [new_det(k) for _ in range(na)]
    prm = {"tau_c": clock["tau_c"]}
    out = {key: [] for key in ENDS}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    signal_updates = {a: 0 for a in arms}
    for t in range(1, window + 1):
        i = (t - 1) % A.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(A.CHUNK), xs.take(A.CHUNK), zs.take(A.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(H, W))
        if pre is not None:
            pre(t, V, r, P, m)
        for ai in range(na):
            sl = slice(ai * k, (ai + 1) * k)
            sta = states[ai]
            detect(sta, V[sl], r[sl], P, cfgs[ai], t, m)
            t_on = sta["t_on"]
            on = (t_on > 0) & (t >= t_on) & (t < t_on + A.SIG["duration"])
            onset = (t_on > 0) & (t == t_on)
            signal_updates[arms[ai]] += int(on.sum())
            xh, xw, extra, _fix = sig_targets_cases(prm, V[sl], r[sl], P, sta, on, onset, m)
            zone, tt = extra
            opened[sl] += zone.mean((-2, -1))
            opened_out[sl] += (zone & ~fp2).mean((-2, -1))
            r[sl] = np.where(zone, r[sl] + A.EPS * A.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + eta * (xh - Hb[sl]), Wb[sl] + eta * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if observe is not None:
            observe(t, V, r, H, W, states)
        if t % A.TRACE == 0:
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
    onset_ = np.concatenate([s_["onset"] for s_ in states])
    hit = np.concatenate([(s_["hit"] & m).sum((-2, -1)) / m.sum((-2, -1)) for s_ in states])
    det_on = np.concatenate([np.where(s_["t_on"] > 0, s_["t_on"], -1).astype(float) for s_ in states])
    zone_ = np.concatenate([s_["zone"] for s_ in states])
    fp_ = np.concatenate([s_["fp"] for s_ in states])
    res.update(trace=np.array(trace), opened=opened / window, opened_out=opened_out / window, onset=onset_, hit=hit,
               det_on=det_on, det_zone=zone_.sum((-2, -1)).astype(float), det_fp=fp_.sum((-2, -1)).astype(float),
               det_zone_in=(zone_ & mb).sum((-2, -1)) / mb.sum((-2, -1)),
               det_fp_in=(fp_ & mb).sum((-2, -1)) / mb.sum((-2, -1)),
               det_windows=np.concatenate([s_["windows"] for s_ in states]),
               det_by=np.concatenate([s_["by"] for s_ in states]),
               n_anc=(m & ev["am"]).sum((-2, -1)).astype(float), n_mis=ev["mis"].sum((-2, -1)).astype(float),
               signal_updates=signal_updates, V=V, r=r, H=H, W=W, zone=zone_, fp=fp_)
    return res
