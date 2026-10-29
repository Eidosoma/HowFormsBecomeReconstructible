"""BE003's tissue: SC002's population tissue with BE002's regime signal as a property of two arms.

Branches are arm-major (index = arm x cases + case); every branch of a case reads that case's streams, and population
events depend only on occupancy and the case's uniforms, so every arm of a run shares one population history. One update,
in order, as sc002.sim.run: the body reads the record (cellpop.core.body_step); bond noise; the record steps through its
contacts (k_c 0); per arm the trusted targets (the cue arbiter, or the detector: currents, the cable equation with the
arm's conductances, the trigger and the slow state); the pull toward committed signs; Hebbian relearning; then the
wound's divisions and the contacts' ageing. A twin run re-specifies the cue of its two patches before update d + 1. With
the signal off, the arms here are sc002.sim.run's bit for bit (checks Q3, Q5).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001 import sim as B1S
from be002.sim import footprint
from cellpop import core as C
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream
from sc002 import sim as S2
from sc002.cable import Cable

from . import design as D

ENDS = ("r_all", "r_in", "r_young", "r_twin", "r_ring", "r_out", "r_young_old", "r_twin_old", "v_in", "v_young",
        "v_twin", "maturity", "filled")
REGIONS = ("in", "young", "twin", "ring", "out")
TRACED = ("r_in", "r_young", "r_twin", "r_all")
agree = S2.agree


def regions(cases, tag=D.TAG):
    """The wound (BE001's patch of side 8 at the case's corner), the young patch at its centre, the twin 16 columns away,
    the ring (the wound dilated by 2, less the wound) and the rest of the sheet."""
    wound = B1S.patch(cases, D.WOUND, tag)
    young = np.roll(B1S.patch(cases, D.PATCH, tag), (D.YOUNG_OFFSET, D.YOUNG_OFFSET), (-2, -1))
    twin = np.roll(young, D.TWIN_SHIFT, -1)
    fw, ft = footprint(wound, D.SIG["d"]), footprint(twin, D.SIG["d"])
    return {"in": wound, "young": young, "twin": twin, "ring": fw & ~wound, "out": ~(fw | ft)}


def signal_footprint(situation, size, reg, m):
    """The event's patch dilated by 2: the wound (regrow runs), both re-specified patches (twin runs), or a full-sheet
    event's patch (tests)."""
    if situation == "twin":
        return footprint(reg["young"] | reg["twin"], D.SIG["d"])
    if situation in ("regrow", "regrow+cue"):
        return footprint(reg["in"], D.SIG["d"])
    return footprint(m, D.SIG["d"])


def conductance(arm, ageH, ageW, occ, touch=None):
    """Junction conductances (right, lower) of one arm: lam^2 m(age) on contacts, 0 elsewhere (sc002.sim.conductance's
    arithmetic); with touch = (tH, tW), the contacts touching the footprint carry lam_sig^2 m(age) instead."""
    prm = D.JUNCTIONS[arm]
    ch, cw = C.contacts(occ)
    lam2 = prm["lam"] ** 2
    mH, mW = S2.maturity(ageH, prm["tau_m"]), S2.maturity(ageW, prm["tau_m"])
    if touch is None:
        return np.where(ch, lam2 * mH, 0.0), np.where(cw, lam2 * mW, 0.0)
    ls2 = D.SIG["lam_sig"] ** 2
    return np.where(ch, np.where(touch[0], ls2, lam2) * mH, 0.0), np.where(cw, np.where(touch[1], ls2, lam2) * mW, 0.0)


def detect(arm, V, r, ca, gH, gW, occ, state):
    """sc002.sim.detect for an arm of this design (the arithmetic unchanged); updates state = {v, s, sgn, kernel, cable}
    in place. Returns the bond targets and (committed, trusted signs)."""
    t, sr = S2.arbiter(V, r, ca)
    current = D.KAPPA * ca * sr
    v, how = S2.solve(current, gH, gW, occ, D.JUNCTIONS[arm]["lam"], state["v"], state["kernel"], state["cable"])
    state["v"], state["solver"] = v, how
    trig = (v < -D.THETA) & (sr != 0)
    was = state["s"] >= D.S_MIN
    state["sgn"] = np.where(trig & ~was, -sr, state["sgn"])
    state["s"] = np.where(trig, 1.0, state["s"] * np.exp(-1.0 / D.TAU))
    committed = state["s"] >= D.S_MIN
    t = np.where(committed, state["sgn"], t)
    return *L5S.rel(t), (committed, t)


def maturity_in(arm, ageH, ageW, occ, m):
    """The mean maturity of the contacts touching region m (1 for instant junctions or none)."""
    tau = D.JUNCTIONS[arm]["tau_m"]
    ch, cw = C.contacts(occ)
    tH, tW = C.touching(m)
    sel_h, sel_w = ch & tH, cw & tW
    n = sel_h.sum((-2, -1)) + sel_w.sum((-2, -1))
    if tau == 0:
        return np.ones(len(n))
    s = (S2.maturity(ageH, tau) * sel_h).sum((-2, -1)) + (S2.maturity(ageW, tau) * sel_w).sum((-2, -1))
    return np.where(n > 0, s / np.maximum(n, 1), 1.0)


def run(body, situation, delay, signal, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE, tag=D.TAG,
        window=None, arms=D.ARMS, size=D.WOUND, on=None, observe=None):
    """situation: regrow, regrow+cue or twin (the design's runs), or BE001's none, cue, memory or change on a full sheet
    (tests); delay: a twin run's re-specification time; signal: 'prompt' or 'late' (design.on_window), or on = (first,
    last) to override; size: a full-sheet event's patch side."""
    first, last = on if on is not None else D.on_window(situation, delay, signal)
    window = D.run_window(situation, delay, signal) if window is None else window
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    wound = situation in ("regrow", "regrow+cue", "twin")
    base = "regrow" if situation == "twin" else situation
    ev = S2.event(base, D.WOUND if wound else size, cases, V0, ema0, R0, T, tag)
    reg = regions(cases, tag)
    fp = signal_footprint(situation, size, reg, ev["m"])
    touch = C.touching(fp)
    chg = (reg["young"] | reg["twin"]) if situation == "twin" else None
    idx = np.tile(np.arange(k), na)
    st = {key: ev[key][idx].copy() for key in ("occ", "V", "E", "r", "H", "W", "Hb", "Wb")}
    Tb, thb = ev["target"][idx], (th * theta)[idx]
    Told = None if ev["old"] is None else ev["old"][idx]
    regb = {x: reg[x][idx] for x in REGIONS}
    am, aval = ev["am"], ev["aval"]
    p_div = D.P_REGROW if wound else 0.0
    ageH, ageW = S2.contact_ages(S2.cell_ages(cases, 0.0, tag))
    events = p_div > 0
    none = np.zeros(st["occ"].shape, bool)
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    sb, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    us = {e: C.UStream(tag, cases, "population", e, side=D.SIDE) for e in ("div", "dir", "die")} if events else None
    out = {key: [] for key in ENDS}
    trace = {key: [] for key in TRACED}
    opened, opened_out = np.zeros(na * k), np.zeros(na * k)
    cable = Cable(k)
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": B1S.cable_kernel(D.JUNCTIONS[a]["lam"]),
                   "cable": cable}
              for ai, a in enumerate(arms) if a in D.JUNCTIONS}
    solvers = {ai: {"fft": 0, "cg": 0} for ai in states}
    sig_updates = 0
    for t in range(1, window + 1):
        if chg is not None and t == delay + 1:
            aval = np.where(chg, -aval, aval)
            Told = Tb.copy()
            Tb = np.where(chg[idx], -Tb, Tb)
        is_on = first <= t <= last
        sig_updates += int(is_on)
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
                sig = D.JUNCTIONS[arm]["signal"] and is_on
                gH, gW = conductance(arm, ageH, ageW, occ, touch if sig else None)
                xh, xw, (zone, tt) = detect(arm, V[sl], r[sl], ca, gH, gW, occ, states[ai])
                solvers[ai][states[ai]["solver"]] += 1
                opened[sl] += zone.mean((-2, -1))
                opened_out[sl] += (zone & reg["out"]).mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            else:
                xh, xw = L5S.rel(S2.arbiter(V[sl], r[sl], ca)[0])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + D.ETA * (xh - Hb[sl]), Wb[sl] + D.ETA * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        born = none[:k]
        if events:
            u = {e: b[i][idx] for e, b in ubuf.items()}
            st, born = C.divide(st, p_div, u["div"], u["dir"], True)
            bk = born[:k]
            for s_ in states.values():
                s_["v"] = np.where(st["occ"][:k], s_["v"], 0.0)
            nh, nw = C.touching(bk)
            ageH, ageW = np.where(nh, 0.0, ageH + 1.0), np.where(nw, 0.0, ageW + 1.0)
            born = bk
        else:
            ageH, ageW = ageH + 1.0, ageW + 1.0
        if observe is not None:
            observe(t, st, states, ageH, ageW, born, is_on, aval, fp)
        occb = st["occ"]
        if t % D.TRACE == 0:
            trace["r_in"].append(agree(st["r"], Tb, regb["in"] & occb))
            trace["r_young"].append(agree(st["r"], Tb, regb["young"] & occb))
            trace["r_twin"].append(agree(st["r"], Tb, regb["twin"] & occb))
            trace["r_all"].append(agree(st["r"], Tb, occb))
        if t in reads:
            out["r_all"].append(agree(st["r"], Tb, occb))
            for x in REGIONS:
                out[f"r_{x}"].append(agree(st["r"], Tb, regb[x] & occb))
            for x in ("in", "young", "twin"):
                out[f"v_{x}"].append(agree(st["V"], Tb, regb[x] & occb))
            if Told is not None:
                out["r_young_old"].append(agree(st["r"], Told, regb["young"] & occb))
                out["r_twin_old"].append(agree(st["r"], Told, regb["twin"] & occb))
            out["filled"].append((regb["in"] & occb).sum((-2, -1)) / regb["in"].sum((-2, -1)))
            mat = np.ones(na * k)
            for ai, arm in enumerate(arms):
                if arm in D.JUNCTIONS:
                    mat[ai * k:(ai + 1) * k] = maturity_in(arm, ageH, ageW, occ, reg["in"])
            out["maturity"].append(mat)
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update({f"trace_{x}": np.array(v) for x, v in trace.items()})
    res.update(opened=opened / window, opened_out=opened_out / window, V=st["V"], r=st["r"], H=st["H"], W=st["W"],
               occ=st["occ"], solvers={a: solvers[ai] for ai, a in enumerate(arms) if ai in solvers},
               signal_updates=sig_updates, fp=fp)
    return res
