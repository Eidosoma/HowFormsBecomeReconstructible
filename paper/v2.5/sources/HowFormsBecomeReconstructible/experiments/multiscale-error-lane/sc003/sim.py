"""SC003's tissue: SC002's population tissue with the birth check switched on and off.

sc002.sim.run's update, unchanged in order and arithmetic for SC002's arms: the body reads the record; bond noise; the
record steps through its contacts; per arm the trusted targets (the cue arbiter, or the detector: currents, the cable
equation, the trigger and the slow state); the pull toward committed signs; Hebbian relearning; then the population's
events (deaths, divisions) and the contacts' ageing. Added, shared by every arm of a case (one population history):
each newborn's parent (the direction cellpop.core.divide chose, recomputed by the same rule and checked against its
births), the sister contacts (daughter-parent contacts formed by a division and not yet lost) and the cells' ages. Per
arm: the junction law (instant, maturing, isolated in the first ISO updates, sister contacts mature) and the gate (no
trigger while the cell's own conductance sum is below G*); an effective-medium arm's coupling length is set by the
run's mu (design.EMT_LAM). Counted per arm: new commitments by the cell's age.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001 import sim as B1S
from cellpop import core as C
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr005 import sim as L5S
from mse.native import NATIVE, address  # noqa: F401
from msegrid.core import R_STAR, Stream
from sc002 import sim as S2S
from sc002.cable import Cable

from . import design as D

ENDS = S2S.ENDS
event, cell_ages, contact_ages, maturity, solve, arbiter, agree = (S2S.event, S2S.cell_ages, S2S.contact_ages,
                                                                   S2S.maturity, S2S.solve, S2S.arbiter, S2S.agree)


def law(prm, ageH, ageW, sisH, sisW):
    """The maturity of every bond under an arm's junction law (before masking by contacts)."""
    if prm["iso"]:
        mH, mW = (ageH >= prm["iso"]).astype(float), (ageW >= prm["iso"]).astype(float)
    else:
        mH, mW = maturity(ageH, prm["tau_m"]), maturity(ageW, prm["tau_m"])
    if prm["sister"]:
        mH, mW = np.where(sisH, 1.0, mH), np.where(sisW, 1.0, mW)
    return mH, mW


def conductance(arm, ageH, ageW, occ, sisH=None, sisW=None, mu=0.0):
    """Junction conductances (right, lower) of one arm at turnover mu: lam^2 m on contacts, 0 elsewhere
    (sc002.sim.conductance's arithmetic for SC002's arms)."""
    prm = D.LAWS[arm]
    ch, cw = C.contacts(occ)
    lam2 = D.lam_of(arm, mu) ** 2
    mH, mW = law(prm, ageH, ageW, sisH, sisW)
    return np.where(ch, lam2 * mH, 0.0), np.where(cw, lam2 * mW, 0.0)


def own(gH, gW):
    """Each cell's own junction conductance sum (right, left, lower, upper)."""
    return gH + np.roll(gH, 1, -1) + gW + np.roll(gW, 1, -2)


def detect(arm, V, r, ca, gH, gW, occ, state):
    """sc002.sim.detect (be001.sim.bio_targets with the population's conductances), with the gate for gate arms;
    updates state = {v, s, sgn, kernel, cable} in place. Returns the bond targets, (committed, trusted signs) and the
    new commitments."""
    prm = D.LAWS[arm]
    t, sr = arbiter(V, r, ca)
    current = D.KAPPA * ca * sr
    v, how = solve(current, gH, gW, occ, state["lam"], state["v"], state["kernel"], state["cable"])
    state["v"], state["solver"] = v, how
    trig = (v < -D.THETA) & (sr != 0)
    if prm["gate"]:
        trig = trig & (own(gH, gW) >= D.G_STAR)
    was = state["s"] >= D.S_MIN
    new = trig & ~was
    state["sgn"] = np.where(new, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t), new


def parents(occ, p, u, w):
    """The sites cellpop.core.divide(st, p, u, w, ...) fills on occupancy occ, and the direction from each to its
    parent (-1 elsewhere), by divide's own selection and conflict order."""
    emp = [~C.at(occ, d) for d in range(4)]
    n_emp = sum(e.astype(np.int8) for e in emp)
    go = occ & (n_emp > 0) & (u < p)
    k = np.floor(w * n_emp).astype(np.int8)
    cum = np.zeros_like(n_emp)
    born = np.zeros_like(occ)
    pdir = np.full(occ.shape, -1, np.int8)
    for d in range(4):
        pick = go & emp[d] & (cum == k)
        cum = cum + emp[d]
        tgt = C.push(pick, d) & ~occ & ~born
        pdir = np.where(tgt, np.int8(C.OPPOSITE[d]), pdir)
        born = born | tgt
    return born, pdir


def sister_bonds(pdir):
    """The bonds (H, W) joining each daughter to its parent: parent right -> H at the daughter, left -> H at the parent,
    below -> W at the daughter, above -> W at the parent."""
    sh = (pdir == C.RIGHT) | C.push(pdir == C.LEFT, C.LEFT)
    sw = (pdir == C.DOWN) | C.push(pdir == C.UP, C.UP)
    return sh, sw


def run(body, mu, situation, size, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE, tag=D.TAG,
        window=D.WINDOW, arms=D.ARMS, observe=None):
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, size, cases, V0, ema0, R0, T, tag)
    idx = np.tile(np.arange(k), na)
    st = {key: ev[key][idx].copy() for key in ("occ", "V", "E", "r", "H", "W", "Hb", "Wb")}
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], ev["m"][idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    am, aval = ev["am"], ev["aval"]
    wound = situation in ("regrow", "regrow+cue")
    p_div = D.P_REGROW if wound else (D.P_DIV if mu > 0 else 0.0)
    age = cell_ages(cases, mu, tag)
    ageH, ageW = contact_ages(age)
    sisH, sisW = np.zeros(ageH.shape, bool), np.zeros(ageW.shape, bool)     # no genealogy before t = 0
    events = p_div > 0 or mu > 0
    none = np.zeros(st["occ"].shape, bool)
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    sb, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    us = {e: C.UStream(tag, cases, "population", e, side=D.SIDE) for e in ("div", "dir", "die")} if events else None
    out = {key: [] for key in ENDS}
    trace = {"r_in": [], "r_all": []}
    opened = np.zeros(na * k)
    newc = np.zeros((len(D.AGE_BINS), na * k))
    births = np.zeros(k)
    cable = Cable(k)
    if wound and any(D.LAWS[a]["emt"] for a in arms if a in D.LAWS):
        raise ValueError("effective-medium arms are defined under steady turnover only")
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": B1S.cable_kernel(D.lam_of(a, mu)),
                   "lam": D.lam_of(a, mu), "cable": cable}
              for ai, a in enumerate(arms) if a in D.LAWS}
    solvers = {ai: {"fft": 0, "cg": 0} for ai in states}
    bins = np.array(D.AGE_BINS[1:], float)
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = sb.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if events:
                ubuf = {e: s_.take(D.CHUNK) for e, s_ in us.items()}
        st, _ = C.body_step(st, st["r"], thb, buf[i][idx], p, gain, alpha, G)
        st = C.bond_noise(st, zbuf[i][idx], cut)
        st = C.record_on(st, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC)
        occ = st["occ"][:k]
        ca = np.where(am & occ, aval, 0.0)
        V, r, H, W, Hb, Wb = (st[x] for x in ("V", "r", "H", "W", "Hb", "Wb"))
        agebin = np.digitize(age, bins)                                       # 0: age 0; 1: 1-31; 2: 32-104; 3: older
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            if arm in D.LAWS:
                gH, gW = conductance(arm, ageH, ageW, occ, sisH, sisW, mu)
                xh, xw, (zone, tt), new = detect(arm, V[sl], r[sl], ca, gH, gW, occ, states[ai])
                solvers[ai][states[ai]["solver"]] += 1
                opened[sl] += zone.mean((-2, -1))
                for q in range(len(D.AGE_BINS)):
                    newc[q, sl] += (new & (agebin == q)).mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            else:
                xh, xw = L5S.rel(arbiter(V[sl], r[sl], ca)[0])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + D.ETA * (xh - Hb[sl]), Wb[sl] + D.ETA * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if events:
            u = {e: b[i][idx] for e, b in ubuf.items()}
            dead = none
            if mu > 0:
                st, dead = C.die(st, mu, u["die"], none)
            pre = st["occ"][:k]
            st, born = C.divide(st, p_div, u["div"], u["dir"], True)
            dk, bk = dead[:k], born[:k]
            mine, pdir = parents(pre, p_div, u["div"][:k], u["dir"][:k])
            if not np.array_equal(mine, bk):
                raise AssertionError("parents() disagrees with cellpop.core.divide's births")
            for s_ in states.values():
                s_["s"], s_["sgn"] = np.where(dk, 0.0, s_["s"]), np.where(dk, 0.0, s_["sgn"])
                s_["v"] = np.where(st["occ"][:k], s_["v"], 0.0)
            nh, nw = C.touching(bk)
            ageH, ageW = np.where(nh, 0.0, ageH + 1.0), np.where(nw, 0.0, ageW + 1.0)
            dh, dw = C.touching(dk)
            sh, sw = sister_bonds(pdir)
            sisH, sisW = (sisH & ~dh & ~nh) | sh, (sisW & ~dw & ~nw) | sw
            age = np.where(bk, 0.0, age + 1.0)
            births += bk.sum((-2, -1))
        else:
            ageH, ageW = ageH + 1.0, ageW + 1.0
            age = age + 1.0
        if observe is not None:
            observe(t, st, states, ageH, ageW, born[:k] if events else None, dead[:k] if events else None,
                    {"sisH": sisH, "sisW": sisW, "pdir": pdir if events else None, "age": age})
        occb = st["occ"]
        if t % D.TRACE == 0:
            trace["r_in"].append(agree(st["r"], Tb, mb & occb))
            trace["r_all"].append(agree(st["r"], Tb, occb))
        if t in reads:
            out["r_all"].append(agree(st["r"], Tb, occb))
            out["v_all"].append(agree(st["V"], Tb, occb))
            out["r_in"].append(agree(st["r"], Tb, mb & occb))
            out["v_in"].append(agree(st["V"], Tb, mb & occb))
            out["r_out"].append(agree(st["r"], Tb, ~mb & occb))
            out["filled"].append((mb & occb).sum((-2, -1)) / mb.sum((-2, -1)))
            mat = np.ones(na * k)
            ch, cw = C.contacts(st["occ"][:k])
            for ai, arm in enumerate(arms):
                if arm in D.LAWS and (D.LAWS[arm]["tau_m"] > 0 or D.LAWS[arm]["iso"]):
                    mH, mW = law(D.LAWS[arm], ageH, ageW, sisH, sisW)
                    mat[ai * k:(ai + 1) * k] = ((mH * ch).sum((-2, -1)) + (mW * cw).sum((-2, -1))) \
                        / (ch.sum((-2, -1)) + cw.sum((-2, -1)))
            out["maturity"].append(mat)
            if oldb is not None:
                out["r_in_old"].append(agree(st["r"], oldb, mb & occb))
                out["v_in_old"].append(agree(st["V"], oldb, mb & occb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace["r_in"]), trace_all=np.array(trace["r_all"]), opened=opened / window,
               newc=newc, births=births / (D.SIDE * D.SIDE),
               V=st["V"], r=st["r"], H=st["H"], W=st["W"], occ=st["occ"],
               solvers={a: solvers[ai] for ai, a in enumerate(arms) if ai in solvers})
    return res
