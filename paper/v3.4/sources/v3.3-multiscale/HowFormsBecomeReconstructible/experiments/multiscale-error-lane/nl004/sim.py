"""NL004's tissue: NL003's (nl003.sim, imported unchanged: the anchor sites, the gate, gated_k2; through it nl002.sim's
prepare, step, relearn, apply_R, apply_K, masks, score, and nl001.sim, dl001.sim), with anchors the tissue makes.

run() follows nl003.sim.run's loop line for line, with three changes. Each gated branch's anchors come from its anchor
code (design.ANCHORS) instead of sign(R0_A). NL004's change event sets the start state. After the record step, a slow
copy's anchors learn the record, and a late commitment makes its anchors at the end of update t_c. A branch with
anchor code A under none, R or K equals nl003.sim.run's '+A' branch bit for bit, and an ungated branch equals
nl002.sim.run's (checks Q3). successor() follows nl003.sim.successor's, and appends a coded recipient for every label,
gated by anchors the successor makes at birth from the record it inherits.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import sim as S
from lr001.sim import edges_from, halves
from mse.native import NATIVE
from msegrid.core import Stream, acquire, birth, bonds
from nl001 import sim as N1S
from nl002 import design as D2
from nl002 import sim as S2
from nl003 import sim as S3

from . import design as D

N = D.SIDE
NR = N // D.REGION
cases_for = S2.cases_for
rep = S3.rep
vote_sign = S3.vote_sign
ANC_ENDS = ("anc_present", "anc_A", "anc_B", "anc_A_min", "anc_A_ev", "anc_A_kill", "anc_B_kill", "anc_A_dreg",
            "anc_B_dreg", "anc_A_kd", "anc_B_kd")


def prepare(cases, tag=D.TAG):
    """nl002.sim.prepare (unchanged), and from the same acquisitions what NL004's anchors and change event read:
    B's acquired body and moving average (nl002.sim.acquire_history of B, the call prepare makes; its record must equal
    prepare's RB), A's record stopped early in its acquisition (msegrid.acquire unchanged: settle, then k teaching
    steps, no release), and the anchor sites (nl003.sim.anchors, density 1/4, under this tag)."""
    P = S2.prepare(cases, tag)
    VB, EB, RB, _ = S2.acquire_history(cases, P["TB"], tag)
    if not np.array_equal(RB, P["RB"]):
        raise RuntimeError("B's acquisition did not reproduce prepare's RB")
    P["VB"], P["EB"] = VB, EB
    p = replace(NATIVE, sigma=D2.SIGMA_ACQ)
    for k in sorted(set(D.TEACH_K.values())):
        P[f"Racq{k}"] = acquire(tag, cases, D2.AMPLITUDE * P["TA"], p, N, settle=D2.SETTLE, teach=k, release=0)[2]
    P["sites"] = S3.anchors(cases, D.DENSITY, tag)
    return P


def start_state(event, j, case, P, units, H0, W0, body, dcell, tag):
    """One branch's state at the branch: A's acquired tissue under the event (NL002's R and K; NL004's change)."""
    r, H, W = P["R0"][j], H0[j], W0[j]
    V, E = (P["V0"][j], P["E0"][j]) if body else (None, None)
    if event == "R":
        r, H, W, V, E = S2.apply_R(units[j], r, H, W, V, E)
    elif event == "K":
        r, H, W, V, E = S2.apply_K(units[j], P["TA"][j], case, r, H, W, V, E, tag)
    elif event == "change":
        dc = dcell[j]
        r = np.where(dc, P["RB"][j], r)
        H, W = edges_from(bonds(r, True))
        if body:
            V, E = np.where(dc, P["VB"][j], V), np.where(dc, P["EB"][j], E)
    return r, H, W, V, E


def made_values(arb, j, P, r_start):
    """(present, value) of an anchor code at the branch, before K's removal: value in {-1, 0, +1} on the sheet."""
    if arb in ("A",) or arb in D.ETA:
        val = np.sign(P["R0"][j])
    elif arb == "Mv":
        val = np.sign(P["V0"][j])
    elif arb == "Me":
        val = np.sign(r_start)
    elif arb in D.TEACH_K:
        R = P[f"Racq{D.TEACH_K[arb]}"][j]
        val = vote_sign(R) if arb in D.CONFIDENT else np.sign(R)
    elif arb in D.T_C:
        val = np.zeros((N, N))                                  # nothing yet: made at the end of update t_c
    else:
        raise KeyError(arb)
    return val != 0, val


def branch_anchors(arb, event, j, P, units, r_start):
    """(am, aval) at the branch for one gated branch: the sites where the code holds a value, K's square removed for
    every code made before the kill (Me reads the killed record, 0 there)."""
    present, val = made_values(arb, j, P, r_start)
    am = P["sites"][j] & present
    if event == "K" and arb != "Me":
        am = am & ~N1S.kill_mask(units[j], P["TA"][j])
    return am, np.where(am, val, 0.0)


def learn(a, r, site, eta):
    """A slow copy's update after a record step: a <- a + eta (sign(r) - a) at the sites, 0 elsewhere."""
    return np.where(site, a + eta * (np.sign(r) - a), 0.0)


def commit(r, site):
    """A commitment from the record: (am, aval), the sites where r != 0 holding sign(r)."""
    am = site & (r != 0)
    return am, np.where(am, np.sign(r), 0.0)


def anchor_shares(am, aval, site, mk):
    """The anchors' endpoints over the case's sites, per branch: (m, n, n) arrays; mk broadcast to branches. Each is
    the share of the sites in a mask that hold a present anchor at A's (or B's) template sign; the denominators count
    sites, at least 1, except 'kd' (the sites in the killed square's differing regions), NaN exactly where the killed
    square holds no differing region (NL002's Amendment 1, as k_spec_reg)."""
    out = {}
    nsite = np.maximum(site.sum((-2, -1)), 1)
    A_ok, B_ok = am & (aval == mk["TA"]), am & (aval == mk["TB"])
    out["anc_present"] = (am & site).sum((-2, -1)) / nsite
    out["anc_A"] = (A_ok & site).sum((-2, -1)) / nsite
    out["anc_B"] = (B_ok & site).sum((-2, -1)) / nsite
    for name, m in (("min", mk["min_cell"]), ("ev", mk["evcell"]), ("kill", mk["kill"]), ("dreg", mk["dcellreg"])):
        n = np.maximum((site & m).sum((-2, -1)), 1)
        out[f"anc_A_{name}"] = (A_ok & site & m).sum((-2, -1)) / n
        if name in ("kill", "dreg"):
            out[f"anc_B_{name}"] = (B_ok & site & m).sum((-2, -1)) / n
    kd = mk["kill"] & mk["dcellreg"]
    defined = mk["kdreg"].any((-2, -1))
    n = np.maximum((site & kd).sum((-2, -1)), 1)
    out["anc_A_kd"] = np.where(defined, (A_ok & site & kd).sum((-2, -1)) / n, np.nan)
    out["anc_B_kd"] = np.where(defined, (B_ok & site & kd).sum((-2, -1)) / n, np.nan)
    return {e: out[e] for e in ANC_ENDS}


def nl004_masks(P, units, nb):
    """nl002.sim.masks for every branch, with the event regions' and the differing regions' cells added."""
    mk = S2.masks(P["TA"], P["TB"], units)
    mk["evcell"], mk["dcellreg"] = rep(mk["ev"]), rep(mk["dreg"])
    return {key: np.concatenate([v] * nb) for key, v in mk.items()}


def run(cases, unit, labels, prep=None, window=D.WINDOW, reads=D.READS, tag=D.TAG, cap=D.CAP, arms=None):
    """nl003.sim.run's loop with the tissue's own anchors. labels: [(arm name, event)], arms in design.ARMS (or
    `arms`). Returns the tissue's endpoints {('r'|'v', name): (reads, branches, cases)}, the arbiter's and the anchors'
    {('a', name): ...}, the dose, the final state, the preparation and the final anchors of every branch."""
    arms = D.ARMS if arms is None else arms
    P = prepare(cases, tag) if prep is None else prep
    k, nb = len(cases), len(labels)
    idx = np.tile(np.arange(k), nb)
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    body = unit == "dw"
    dcell = rep(S2.masks(P["TA"], P["TB"], units)["dreg"])
    st = {x: [] for x in ("r", "H", "W", "V", "E", "Bg", "B3")}
    AM, AV = [], []
    for name, event in labels:
        arm = arms[name]
        Bg, B3 = P["refs"][arm.ref]
        for j in range(k):
            r, H, W, V, E = start_state(event, j, cases[j], P, units, H0, W0, body, dcell, tag)
            if arm.arb:
                am, aval = branch_anchors(arm.arb, event, j, P, units, r)
            else:
                am, aval = np.zeros((N, N), bool), np.zeros((N, N))
            for key, x in zip(("r", "H", "W", "V", "E", "Bg", "B3"), (r, H, W, V, E, Bg[j], B3[j])):
                st[key].append(x)
            AM.append(am)
            AV.append(aval)
    r, H, W, Bg, B3 = (np.stack(st[x]).astype(float) for x in ("r", "H", "W", "Bg", "B3"))
    V, E = (np.stack(st[x]).astype(float) if body else None for x in ("V", "E"))
    AM, AV = np.stack(AM), np.stack(AV)
    Hb, Wb = D2.STRENGTH0 * H, D2.STRENGTH0 * W
    col = lambda f: np.repeat([f(arms[a]) for a, _ in labels], k)[:, None, None]
    k2, k3 = col(lambda a: a.k2 * D.KC), col(lambda a: a.k3 * D.KC)
    codes = np.repeat([arms[a].arb for a, _ in labels], k)
    gidx = np.flatnonzero(codes != "")
    slow = np.flatnonzero(np.isin(codes, list(D.ETA)))
    eta = np.array([D.ETA[c] for c in codes[slow]])[:, None, None]
    a_slow = AV[slow].copy()                                    # the slow copies' continuous anchors
    late = {t_c: np.flatnonzero(codes == c) for c, t_c in D.T_C.items()}
    site_all = np.concatenate([P["sites"]] * nb)
    ones = np.ones(gidx.size)
    n_, q_, ring_, rmax_ = ones * D.RULE["n"], ones * D.RULE["q"], ones * D.RULE["ring"], ones * D.RULE["ring_max"]
    mk = nl004_masks(P, units, nb)
    p = replace(NATIVE, sigma=D2.SIGMA)
    thb = (P["th"] * 0.0)[idx]
    xs = Stream(tag, cases, "record-noise", side=N)
    zs = Stream(tag, cases, "future", side=N) if body else None
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    ends = {(w, e): [] for w in (("r", "v") if body else ("r",)) for e in S2.ENDS}
    for e in ("ref_all", "ref_dreg", "ref_other", "ever") + ANC_ENDS:
        ends[("a", e)] = []
    ever = np.zeros(nb * k, bool)
    dose = np.zeros(nb * k)
    xb = zb = None
    refused = np.zeros((gidx.size, NR, NR), bool)
    dreg = mk["dreg"][gidx] if gidx.size else None
    for t in range(1, window + 1):
        i = (t - 1) % D2.CHUNK
        if i == 0:
            xb = xs.take(D2.CHUNK)
            zb = zs.take(D2.CHUNK) if body else None
        if body:
            V, E, _, _, _ = S.body(V, E, r, thb, zb[i][idx], p, D2.GAIN, 0.0, None)
        if gidx.size:
            refused = S3.gate(r[gidx], sig[gidx], Bg[gidx], AM[gidx], AV[gidx], n_, q_, ring_, rmax_)
            ever[gidx] |= refused.any((-2, -1))
            r, inc = S2.step(r, xb[i][idx], J, sig, Bg, B3, S3.gated_k2(k2, gidx, refused, nb * k), k3, cap)
        else:
            r, inc = S2.step(r, xb[i][idx], J, sig, Bg, B3, k2, k3, cap)
        dose += inc.sum((-2, -1))
        if body:
            H, W, Hb, Wb = S2.relearn(H, W, Hb, Wb, V)
            J = halves(H, W)
            sig = N1S.gauge_frame(H, W)
        if slow.size:                                           # the slow copies learn the record that just stepped
            a_slow = learn(a_slow, r[slow], site_all[slow], eta)
            AM[slow] = a_slow != 0
            AV[slow] = np.sign(a_slow)
        for t_c, rows in late.items():                          # a late commitment, at the end of update t_c
            if t == t_c and rows.size:
                AM[rows], AV[rows] = commit(r[rows], site_all[rows])
        if t in reads:
            for e, v in S2.score(r, mk).items():
                ends[("r", e)].append(v)
            if body:
                for e, v in S2.score(V, mk).items():
                    ends[("v", e)].append(v)
            ra = np.zeros((4, nb * k))
            if gidx.size:
                ra[0, gidx] = refused.mean((-2, -1))
                ra[1, gidx] = N1S.frac(dreg, refused, (-2, -1))
                ra[2, gidx] = N1S.frac(~dreg, refused, (-2, -1))
            ra[3] = ever
            for e, v in zip(("ref_all", "ref_dreg", "ref_other", "ever"), ra):
                ends[("a", e)].append(v)
            for e, v in anchor_shares(AM, AV, site_all, mk).items():      # every branch; an ungated one has none
                ends[("a", e)].append(v)
    out = {key: np.array(v).reshape(len(reads), nb, k) for key, v in ends.items()}
    final = {"r": r.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N), "W": W.reshape(nb, k, N, N)}
    if body:
        final["V"] = V.reshape(nb, k, N, N)
    anc = {"am": AM, "aval": AV, "a_slow": a_slow, "slow_rows": slow}
    return out, dose.reshape(nb, k) / (N * N * window), final, P, anc


SUCC = S2.SUCC                                                  # A's and B's acquired records, and nothing
M_ENDS = S2.ENDS


def successor(cases, final, P, labels, anchors_=None, window=D.WINDOW2, reads=D.READS2, tag=D.TAG, cap=D.CAP, arms=None):
    """nl003.sim.successor's recipients (NL002's record-only, the three extra, coded; NL003's coded recipient gated by
    the parent's anchors, for the labels in design.parent_gated), then a coded recipient for every label gated by
    anchors the successor makes at birth from the record it inherits (sign(r) where r != 0, the case's sites, fixed).
    final: the labels' final states (nb, k, n, n); anchors_: the labels' anchors (nb * k rows).
    Returns ({e: (reads, nb + 3, k)} record-only, {e: (reads, nb, k)} coded, {e: (reads, ng, k)} parent-gated with
    'ever', {e: (reads, nb, k)} successor-made with 'ever' and the made anchors' shares, the parent-gated labels)."""
    arms = D.ARMS if arms is None else arms
    k, nb = len(cases), len(labels)
    H0, W0 = edges_from(bonds(P["R0"], True))
    HB, WB = edges_from(bonds(P["RB"], True))
    rL, HL, WL = (final[x].reshape(nb * k, N, N) for x in ("r", "H", "W"))
    gl = [i for i, l in enumerate(labels) if l in D.parent_gated(arms, labels)]
    gsel = np.concatenate([np.arange(i * k, (i + 1) * k) for i in gl]) if gl else np.zeros(0, int)
    ng = len(gl)
    r = np.concatenate([rL, P["R0"], P["RB"], np.zeros_like(P["R0"]), rL, rL[gsel], rL])
    H = np.concatenate([HL, H0, HB, np.ones_like(H0), HL, HL[gsel], HL])
    W = np.concatenate([WL, W0, WB, np.ones_like(W0), WL, WL[gsel], WL])
    nt = 3 * nb + len(SUCC) + ng
    idx = np.tile(np.arange(k), nt)
    gains = np.repeat([D2.GAIN] * (nb + 2) + [0.0] + [D2.GAIN] * (2 * nb + ng), k)[:, None, None]
    zero = np.zeros((k, N, N))
    codes = [P["refs"][arms[a].ref] for a, _ in labels]
    Bg = np.concatenate([zero] * (nb + 3) + [c[0] for c in codes] + [codes[i][0] for i in gl] + [c[0] for c in codes])
    B3 = np.concatenate([zero] * (nb + 3) + [c[1] for c in codes] + [codes[i][1] for i in gl] + [c[1] for c in codes])
    kk = lambda f: np.repeat([0.0] * (nb + 3) + [f(arms[a]) * D.KC for a, _ in labels]
                             + [f(arms[labels[i][0]]) * D.KC for i in gl] + [f(arms[a]) * D.KC for a, _ in labels],
                             k)[:, None, None]
    k2, k3 = kk(lambda a: a.k2), kk(lambda a: a.k3)
    V = birth(tag, cases, "successor", "dw", side=N)[idx].copy()
    E = V.copy()
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    units = N1S.event_units(cases, tag)
    mk = nl004_masks(P, units, nt)
    p = replace(NATIVE, sigma=D2.SIGMA)
    thb = np.zeros_like(V)
    st, xs = (Stream(tag, cases, s_, "dw", side=N) for s_ in ("successor-future", "successor-record-noise"))
    g0 = 2 * nb + len(SUCC)
    gidx = np.arange(g0 * k, nt * k)                            # the parent-gated, then the successor-made
    site_m = np.concatenate([P["sites"]] * nb)
    am_m, av_m = commit(rL, site_m)                             # the successor's anchors, made at birth
    if ng:
        AM = np.concatenate([anchors_["am"][gsel], am_m])
        AV = np.concatenate([anchors_["aval"][gsel], av_m])
    else:
        AM, AV = am_m, av_m
    ones = np.ones(gidx.size)
    n_, q_, ring_, rmax_ = ones * D.RULE["n"], ones * D.RULE["q"], ones * D.RULE["ring"], ones * D.RULE["ring_max"]
    m_sh = anchor_shares(am_m, av_m, site_m, {key: v[(g0 + ng) * k:] for key, v in mk.items()})
    ends = {e: [] for e in M_ENDS}
    gev, gever = [], np.zeros(gidx.size, bool)
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D2.CHUNK
        if i == 0:
            buf, xbuf = st.take(D2.CHUNK), xs.take(D2.CHUNK)
        V, E, _, _, _ = S.body(V, E, r, thb, buf[i][idx], p, gains, 0.0, None)
        refused = S3.gate(r[gidx], sig[gidx], Bg[gidx], AM, AV, n_, q_, ring_, rmax_)
        gever |= refused.any((-2, -1))
        r, _ = S2.step(r, xbuf[i][idx], J, sig, Bg, B3, S3.gated_k2(k2, gidx, refused, nt * k), k3, cap)
        if t in reads:
            for e, v in S2.score(V, mk).items():
                ends[e].append(v)
            gev.append(gever.astype(float).copy())
    full = {e: np.array(v).reshape(len(reads), nt, k) for e, v in ends.items()}
    ev = np.array(gev).reshape(len(reads), ng + nb, k)
    rec = {e: v[:, :nb + 3] for e, v in full.items()}
    coded = {e: v[:, nb + 3:2 * nb + 3] for e, v in full.items()}
    pg = {e: v[:, g0:g0 + ng] for e, v in full.items()}
    pg["ever"] = ev[:, :ng]
    made = {e: v[:, g0 + ng:] for e, v in full.items()}
    made["ever"] = ev[:, ng:]
    for e, v in m_sh.items():
        made[e] = np.broadcast_to(v.reshape(1, nb, k), (len(reads), nb, k)).copy()
    return rec, coded, pg, made, [labels[i] for i in gl]
