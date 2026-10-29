"""SC002's tissue: BE001's detector on cellpop's vacancy lattice, with junctions set by the population.

Branches are arm-major (index = arm x cases + case); every branch of a case reads that case's streams, and population
events depend only on occupancy and the case's uniforms, so every arm of a run shares one population history (deaths,
divisions, contact ages). One update, in order, as in be001.sim.run: the body reads the record (dl001.sim.body via
cellpop.core.body_step); bond noise; the record steps through its contacts (msegrid.record_step, k_c 0); per arm the
trusted targets (the cue arbiter, or the detector: currents, the cable equation, the trigger and the slow state); the
pull toward committed signs; Hebbian relearning; then the population's events (deaths, divisions) and the contacts'
ageing. With every site occupied, no events and every contact mature, a run equals be001.sim.run bit for bit (checks Q3).
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
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream

from . import design as D
from .cable import Cable

ENDS = ("r_all", "r_in", "r_out", "v_all", "v_in", "r_in_old", "v_in_old", "maturity", "filled")


def event(situation, size, cases, V0, ema0, R0, T, tag=D.TAG):
    """BE001's events (be001.sim.event, unchanged) with the sheet full; the wound empties the patch (values 0, contacts
    lost) and keeps its anchors (the cue is positional); regrow+cue adds BE001's scattered cue corruption."""
    wound = situation in ("regrow", "regrow+cue")
    base = {"regrow": "none", "regrow+cue": "cue"}.get(situation, situation)
    ev = B1S.event(base, size, cases, V0, ema0, R0, T, tag)
    ev["occ"] = np.ones(ev["V"].shape, bool)
    if wound:
        st = C.clear({k: ev[k] for k in ("occ", "V", "E", "r", "H", "W", "Hb", "Wb")}, ev["m"])
        ev.update(st)
    return ev


def cell_ages(cases, mu, tag=D.TAG):
    """Ages at t = 0 under stationary turnover at mu: floor(E / mu), E one standard exponential per site (shared by every
    mu); infinite with no turnover."""
    if mu == 0:
        return np.full((len(cases), D.SIDE, D.SIDE), np.inf)
    e = np.stack([address(tag, *c.key(), "ages").standard_exponential((D.SIDE, D.SIDE)) for c in cases])
    return np.floor(e / mu)


def contact_ages(a):
    """A contact's age is its younger cell's: (H, right; W, lower)."""
    return np.minimum(a, C.at(a, C.RIGHT)), np.minimum(a, C.at(a, C.DOWN))


def maturity(age, tau_m):
    """m = 1 - exp(-age / tau_m) (1 at infinite age); instant junctions (tau_m 0) are mature at once."""
    return -np.expm1(-age / tau_m) if tau_m > 0 else np.ones_like(age)


def conductance(arm, ageH, ageW, occ):
    """Junction conductances (right, lower) of one arm: lam^2 m on contacts, 0 elsewhere."""
    prm = D.JUNCTIONS[arm]
    ch, cw = C.contacts(occ)
    lam2 = prm["lam"] ** 2
    return (np.where(ch, lam2 * maturity(ageH, prm["tau_m"]), 0.0), np.where(cw, lam2 * maturity(ageW, prm["tau_m"]), 0.0))


def solve(I, gH, gW, occ, lam, v0, kernel, cable):
    """The steady potentials: by FFT when every site is occupied and every junction is at lam^2 (be001's arithmetic),
    else by conjugate gradients (sc002.cable, be001's algorithm) warm-started from the previous potentials (0 at empty
    sites)."""
    lam2 = lam ** 2
    if occ.all() and (gH == lam2).all() and (gW == lam2).all():
        return np.real(np.fft.ifft2(np.fft.fft2(I) / kernel)), "fft"
    return cable.solve(I, gH, gW, np.where(occ, v0, 0.0))[0], "cg"


def arbiter(V, r, ca):
    """LR004's cue arbiter (lr005.sim.targets' 'cue' branch): the body where body and record agree, the cue where they
    disagree at an anchored cell, else the record."""
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    agree = (sv == sr) & (sv != 0)
    return np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv))), sr


def detect(arm, V, r, ca, gH, gW, occ, state):
    """be001.sim.bio_targets for one arm with the population's conductances; updates state = {v, s, sgn, kernel} in
    place. Returns the bond targets and (committed, trusted signs)."""
    t, sr = arbiter(V, r, ca)
    current = D.KAPPA * ca * sr
    v, how = solve(current, gH, gW, occ, D.JUNCTIONS[arm]["lam"], state["v"], state["kernel"], state["cable"])
    state["v"], state["solver"] = v, how
    trig = (v < -D.THETA) & (sr != 0)
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t)


def agree(x, T, m):
    """Agreement of sign(x) with sign(T) over the sites in m (occupied sites; 0 where m is empty: no cell agrees)."""
    n = m.sum((-2, -1))
    return np.where(n > 0, (((x > 0) == (T > 0)) & m).sum((-2, -1)) / np.maximum(n, 1), 0.0)


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
    ageH, ageW = contact_ages(cell_ages(cases, mu, tag))
    events = p_div > 0 or mu > 0
    none = np.zeros(st["occ"].shape, bool)
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    sb, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    us = {e: C.UStream(tag, cases, "population", e, side=D.SIDE) for e in ("div", "dir", "die")} if events else None
    out = {key: [] for key in ENDS}
    trace = {"r_in": [], "r_all": []}
    opened = np.zeros(na * k)
    cable = Cable(k)
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": B1S.cable_kernel(D.JUNCTIONS[a]["lam"]),
                   "cable": cable}
              for ai, a in enumerate(arms) if a in D.JUNCTIONS}
    solvers = {ai: {"fft": 0, "cg": 0} for ai in states}
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
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            if arm in D.JUNCTIONS:
                gH, gW = conductance(arm, ageH, ageW, occ)
                xh, xw, (zone, tt) = detect(arm, V[sl], r[sl], ca, gH, gW, occ, states[ai])
                solvers[ai][states[ai]["solver"]] += 1
                opened[sl] += zone.mean((-2, -1))
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
            st, born = C.divide(st, p_div, u["div"], u["dir"], True)
            dk, bk = dead[:k], born[:k]
            for s_ in states.values():
                s_["s"], s_["sgn"] = np.where(dk, 0.0, s_["s"]), np.where(dk, 0.0, s_["sgn"])
                s_["v"] = np.where(st["occ"][:k], s_["v"], 0.0)
            nh, nw = C.touching(bk)
            ageH, ageW = np.where(nh, 0.0, ageH + 1.0), np.where(nw, 0.0, ageW + 1.0)
        else:
            ageH, ageW = ageH + 1.0, ageW + 1.0
        if observe is not None:
            observe(t, st, states, ageH, ageW, born[:k] if events else None, dead[:k] if events else None)
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
                if arm in D.JUNCTIONS and D.JUNCTIONS[arm]["tau_m"] > 0:
                    tau = D.JUNCTIONS[arm]["tau_m"]
                    mat[ai * k:(ai + 1) * k] = ((maturity(ageH, tau) * ch).sum((-2, -1)) + (maturity(ageW, tau) * cw).sum((-2, -1))) \
                        / (ch.sum((-2, -1)) + cw.sum((-2, -1)))
            out["maturity"].append(mat)
            if oldb is not None:
                out["r_in_old"].append(agree(st["r"], oldb, mb & occb))
                out["v_in_old"].append(agree(st["V"], oldb, mb & occb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace["r_in"]), trace_all=np.array(trace["r_all"]), opened=opened / window,
               V=st["V"], r=st["r"], H=st["H"], W=st["W"], occ=st["occ"],
               solvers={a: solvers[ai] for ai, a in enumerate(arms) if ai in solvers})
    return res
