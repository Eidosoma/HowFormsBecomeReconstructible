"""AR003's controller whose default is the vote (run_vd), beside AR002's rest-default detector arms (ar002.sim.run_det)
and AR001's fixed policies (ar001.sim.run), both imported unchanged.

A vote-default arm is AR001's vote (LR004's vote2r: the record moved toward the majority of the body's and the two
records' relations; the second record with its own "B" noise streams; both records' bonds relearn toward the same
targets) until its detector fires, and wherever the detector has not committed a cell:
  - the detector is ar002.sim.detect, unchanged: each update, after the records' step and before the targets, it reads
    the arm's own body, first record and anchors; it fires once per case, and its zone dilated by SIG['d'] (2) is the
    footprint F, whose junctions close to coupling length 1 for SIG['duration'] (1,000) updates from the onset
    (ar002.sim.fire: be002's conductances and the case's sparse LU), as in AR002;
  - during that window the cable equation is solved for the case (BE006's currents, kappa ca sr), and a cell of F whose
    potential falls below -theta, with a confident record, commits to the opposite of its record's sign (BE006's slow
    state: s = 1 on a trigger, decaying by exp(-1 / tau_c) each update); outside F, and after the window, nothing
    triggers (the vote has no commitment of its own); a cell stays committed while s >= S_MIN, which at tau_c = 15,000
    is beyond the run's 8,000 updates;
  - every bond touching a committed cell takes AR002's target there (rel(t): t the committed sign at a committed cell
    and LR004's arbiter's sign at the other end, be006.sim.sig_targets' arithmetic), and the first record's committed
    cells are pulled toward their sign (AR002's pull); every other bond keeps the vote's target;
  - the second record learns the same bond targets as the first, everywhere (the vote's own rule: one target field for
    both copies), steps through its bonds with its own noise, and is never pulled and never read by the detector or the
    cable; inside the committed zone it therefore learns the re-specification, so that when the commitment lapses the
    vote's majority holds it rather than contesting it.
With a detector that never fires, a vote-default arm is AR001's vote bit for bit (checks Q3); with an oracle that fires
at update 1 over the patch it is the declared signal under the vote default (vdial). Every branch reads the case's
body, record and bond-noise streams and the vote's second-record streams, so the arms are paired with AR001's and
AR002's run separately on the same cases.

scan(): the tuning's passive evaluator (probes/p47a): on a never-firing vote-default branch, which is the vote, it
evaluates every candidate cue detector at every update, at the point where an arm's own detector reads the tissue, and
records each candidate's first firing per case, its zone, footprint and onset. A vote-default arm is the vote until
its onset, so this is exactly that arm's own firing.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from ar001 import design as A
from ar001 import sim as A1S
from ar002 import sim as A2S
from be002 import sim as B2S
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, edges_from, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, bonds, record_step

from . import design as D

ENDS = A1S.ENDS
SCALARS = A1S.SCALARS
DET_SCALARS = A2S.DET_SCALARS


def vd_targets(prm, V, r, rB, P, state, on, onset, m):
    """One vote-default arm's bond targets for its k branches; updates state in place.
    on (k,) bool: the case's dial window is open (the cable is solved and cells of F may commit); onset (k,) bool: the
    window opens at this update (the onset diagnostic, be006's onset_m). Returns xh, xw, (committed, t)."""
    xh, xw, _ = L5S.targets("vote2r", V, r, rB, P, None)
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    trig = np.zeros(V.shape, bool)
    if on.any():
        current = A.KAPPA * ca * sr
        n = current.shape[-1]
        for j in np.flatnonzero(on):
            v = state["lus"][j].solve(current[j].ravel()).reshape(n, n)
            state["v"][j] = v
            trig[j] = (v < -A.SIG["theta"]) & (sr[j] != 0) & state["fp"][j]
            if onset[j]:
                state["onset"][j] = ((v < -A.SIG["theta"]) & (sr[j] != 0) & m[j]).sum() / m[j].sum()
    state["hit"] |= trig
    was = state["s"] >= A.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / prm["tau_c"]))
    committed = state["s"] >= A.S_MIN
    if not committed.any():
        return xh, xw, (committed, None)
    agree = (sv == sr) & (sv != 0)
    t = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))      # LR004's arbiter outside commitment
    t = np.where(committed, state["sgn"], t)
    th, tw = L5S.rel(t)
    touch_h = committed | np.roll(committed, -1, -1)
    touch_w = committed | np.roll(committed, -1, -2)
    return np.where(touch_h, th, xh), np.where(touch_w, tw, xw), (committed, t)


def second_record(situation, ev, R0, idx):
    """The vote's second record at t = 0, as ar001.sim.run builds it, tiled over the arms' branches: in memory and
    correlated damage the event hit the first record only (the second holds the acquired record with fresh bonds);
    otherwise it is the post-event record with its bonds."""
    if situation in ("memory", "correlated"):
        H0, W0 = edges_from(bonds(R0, True))
        rB, HB, WB = R0.copy(), H0.copy(), W0.copy()
        HbB, WbB = A.STRENGTH0 * HB, A.STRENGTH0 * WB
    else:
        rB, HB, WB, HbB, WbB = ev["r"], ev["H"], ev["W"], ev["Hb"], ev["Wb"]
    return tuple(x[idx].copy() for x in (rB, HB, WB, HbB, WbB))


def run_vd(body, situation, sigma, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=A.GAIN, tag=D.TAG,
           window=A.WINDOW, size=A.SIZE, clock=None, detectors=None, pre=None, observe=None):
    """One run of vote-default arms: the event (ar001.sim.event), then every arm for `window` updates. arms: names in
    detectors (default D.VD_DETECTORS: each a detector configuration for ar002.sim.detect, {'never': True} or
    {'oracle': True}). pre(t, V, r, P, m) runs after the records' step, on the state the detectors read; observe(t, V, r,
    H, W, rB, states) at the end of an update (probes and checks only)."""
    clock = A.CLOCK if clock is None else clock
    detectors = D.VD_DETECTORS if detectors is None else detectors
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    G = S.ghat(A.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    cfgs = [detectors[a] for a in arms]
    ev = A1S.event(situation, size, sigma, cases, V0, ema0, R0, T, tag)
    m = ev["m"]
    fp2 = B2S.footprint(m, A.SIG["d"])
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    rB, HB, WB, HbB, WbB = second_record(situation, ev, R0, idx)
    Tb, thb, mb, fpb = ev["target"][idx], (th * theta)[idx], m[idx], fp2[idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    s_post = r > 0
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(clock["rate"])
    p = replace(NATIVE, sigma=A.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=A.SIDE) for s in ("future", "record-noise", "bond-noise"))
    xsB, zsB = (Stream(tag, cases, s, "B", side=A.SIDE) for s in ("record-noise", "bond-noise"))
    states = [A2S.new_det(k) for _ in range(na)]
    prm = {"tau_c": clock["tau_c"]}
    out = {key: [] for key in ENDS}
    trace = []
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    signal_updates = {a: 0 for a in arms}
    for t in range(1, window + 1):
        i = (t - 1) % A.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(A.CHUNK), xs.take(A.CHUNK), zs.take(A.CHUNK)
            xbB, zbB = xsB.take(A.CHUNK), zsB.take(A.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(H, W))
        zB = zbB[i][idx]
        h2, w2 = zB > cut, zB < -cut
        HB, WB, HbB, WbB = np.where(h2, -HB, HB), np.where(w2, -WB, WB), np.where(h2, -HbB, HbB), np.where(w2, -WbB, WbB)
        rB = record_step(rB, xbB[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(HB, WB))
        if pre is not None:
            pre(t, V, r, P, m)
        for ai in range(na):
            sl = slice(ai * k, (ai + 1) * k)
            sta = states[ai]
            A2S.detect(sta, V[sl], r[sl], P, cfgs[ai], t, m)
            t_on = sta["t_on"]
            on = (t_on > 0) & (t >= t_on) & (t < t_on + A.SIG["duration"])
            onset = (t_on > 0) & (t == t_on)
            signal_updates[arms[ai]] += int(on.sum())
            xh, xw, extra = vd_targets(prm, V[sl], r[sl], rB[sl], P, sta, on, onset, m)
            zone, tt = extra
            if tt is not None:
                opened[sl] += zone.mean((-2, -1))
                opened_out[sl] += (zone & ~fp2).mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + A.EPS * A.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + eta * (xh - Hb[sl]), Wb[sl] + eta * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
            HbB[sl], WbB[sl] = np.where(lh, HbB[sl] + eta * (xh - HbB[sl]), HbB[sl]), np.where(lw, WbB[sl] + eta * (xw - WbB[sl]), WbB[sl])
            HB[sl] = np.where(lh & (HbB[sl] != 0), np.sign(HbB[sl]), HB[sl])
            WB[sl] = np.where(lw & (WbB[sl] != 0), np.sign(WbB[sl]), WB[sl])
        if observe is not None:
            observe(t, V, r, H, W, rB, states)
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
               signal_updates=signal_updates, V=V, r=r, H=H, W=W, rB=rB, HB=HB, WB=WB, zone=zone_, fp=fp_)
    return res


# the tuning's passive evaluator -----------------------------------------------------------------------------------

def candidate_windows(r, P, cands):
    """{name: {box: (k, n, n) bool}} for cue-channel candidates sharing this state: each candidate's criterion at each of
    its boxes, by ar002.sim's integral images (exact integer counts, so equal to ar002.sim.cue_windows_multi's)."""
    n = r.shape[-1]
    sr = L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    g = max(c["cue"].get("ring", 0) for c in cands.values())
    lo, hi = g, max(max(c["cue"]["boxes"]) for c in cands.values()) + g
    Sd, Sl = A2S.integral(dis, lo, hi), A2S.integral(live, lo, hi)
    sums = {}
    out = {}
    for name, c in cands.items():
        ch = c["cue"]
        gc = ch.get("ring", 0)
        fs = {}
        for b in ch["boxes"]:
            if b not in sums:
                sums[b] = (A2S.window_sums(Sd, lo, b, 0, n), A2S.window_sums(Sl, lo, b, 0, n))
            nd, nl = sums[b]
            f = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
            if gc:
                key = ("ring", b, gc)
                if key not in sums:
                    sums[key] = A2S.window_sums(Sd, lo, b + 2 * gc, -gc, n)
                f &= (sums[key] - nd) <= ch["ring_max"]
            fs[b] = f
        out[name] = fs
    return out


class Scan:
    """The passive evaluator: call as pre(t, V, r, P, m) on a run_vd of one never-firing arm ('vote'). For each
    candidate (single cue channel with boxes, dwell 1 or more) records per case the first update its criterion held for
    its dwell at any box, the number of windows then, its zone (every cell of the windows held then) and its footprint
    (the zone dilated by SIG['d']); and, at that update, the live anchors disagreeing with the record inside the
    footprint (the false-alarm load: the cells the dial would re-specify toward a wrong cue under scattered cue
    damage)."""

    def __init__(self, cands, k):
        self.cands = cands
        self.count = {nm: {} for nm in cands}
        z = lambda: np.zeros((k, A.SIDE, A.SIDE), bool)
        self.t_on = {nm: np.zeros(k, int) for nm in cands}
        self.zone = {nm: z() for nm in cands}
        self.fp = {nm: z() for nm in cands}
        self.nwin = {nm: np.zeros(k, int) for nm in cands}
        self.load = {nm: np.zeros(k) for nm in cands}

    def __call__(self, t, V, r, P, m):
        waiting = {nm: self.t_on[nm] == 0 for nm in self.cands}
        live_c = {nm: c for nm, c in self.cands.items() if waiting[nm].any()}
        if not live_c:
            return
        fs = candidate_windows(r, P, live_c)
        sr = L5S.vote_sign(r)
        ca = np.where(P["am"], P["aval"], 0.0)
        dis = (ca != 0) & (sr != 0) & (ca != sr)
        for nm, c in live_c.items():
            ch = c["cue"]
            ready = []
            for b, f in fs[nm].items():
                cnt = self.count[nm].get(b)
                cnt = np.where(f, (np.zeros(f.shape, np.int32) if cnt is None else cnt) + 1, 0)
                self.count[nm][b] = cnt
                ready.append((b, cnt >= ch["dwell"]))
            anyr = np.zeros(len(r), bool)
            for b, rd in ready:
                anyr |= rd.any((-2, -1))
            new = anyr & waiting[nm]
            if not new.any():
                continue
            zone = np.zeros(r.shape, bool)
            nw = np.zeros(len(r), int)
            for b, rd in ready:
                zone |= A2S.cover(rd, b)
                nw += rd.sum((-2, -1))
            fp = B2S.footprint(zone, A.SIG["d"])
            for j in np.flatnonzero(new):
                self.t_on[nm][j], self.zone[nm][j], self.fp[nm][j], self.nwin[nm][j] = t, zone[j], fp[j], nw[j]
                self.load[nm][j] = (dis[j] & fp[j]).sum()

    def result(self, m):
        out = {}
        for nm in self.cands:
            fp = self.fp[nm]
            out[nm] = {"det_on": np.where(self.t_on[nm] > 0, self.t_on[nm], -1).astype(float),
                       "det_fp_in": (fp & m).sum((-2, -1)) / m.sum((-2, -1)),
                       "det_zone_in": (self.zone[nm] & m).sum((-2, -1)) / m.sum((-2, -1)),
                       "det_fp": fp.sum((-2, -1)).astype(float), "det_windows": self.nwin[nm].astype(float),
                       "load": self.load[nm]}
        return out
