"""NL002's tissue: NL001's stores (nl001.sim's template, gauge frame, events and read arithmetic, unchanged and
imported) under DL001's double-well body (dl001.sim.body, unchanged), with references acquired by msegrid.acquire.

One update of the 'dw' unit, in LR002's order: the body reads the record (dl001.sim.body, gain 0.2); the record step
(NL001's arithmetic: self-correction through the bonds, the region code in the gauge frame of the current bonds, the
block code, one clip; here with the descending increment capped at CAP); Hebbian relearning of the bonds from the body
(lr002.sim.relations' arithmetic for 'body' learning). No bond noise. The 'none' unit has no body and no relearning,
so with NL001's exact references and no cap a branch is nl001.sim.run's arm bit for bit (checks Q3).
Branches are batched event-major (index = label x cases + case); every branch of a case reads the case's noise streams
(the body's 'future', the record's 'record-noise'), so arms and events are paired within a case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import sim as S
from lr001.sim import edges_from, halves
from mse.assay import enrol
from mse.native import NATIVE, address
from msegrid.core import Stream, acquire, birth, bond_sum, bonds, bproj, record_step
from nl001 import sim as N1S

from . import design as D

N = D.SIDE
NR, NB = N // D.REGION, N // D.BLOCK                       # 16 regions, 4 blocks a side


def cases_for(block, purpose):
    return enrol([block], D.MESSAGES, D.PARENTS, purpose)


def rep(x, size):
    """(..., n, n) unit values broadcast to sites."""
    return np.repeat(np.repeat(x, size, axis=-2), size, axis=-1)


def templates(cases, tag=D.TAG):
    """History A: NL001's template (nl001.sim.template, unchanged). History B: A's block signs, its own minority
    regions and cells (the same counts), drawn from (case, 'history-B')."""
    TA = np.stack([N1S.template(c, tag) for c in cases])
    TB = []
    for j, c in enumerate(cases):
        g = address(tag, *c.key(), "history-B")
        sB = N1S.unit_sign(TA[j], D.BLOCK)
        nr, nc = D.BLOCK // D.REGION, D.REGION
        T = np.zeros((N, N))
        for bi in range(NB):
            for bj in range(NB):
                mr = g.permutation(nr * nr) < D.MINORITY_REGIONS
                for q in range(nr * nr):
                    ri, rj = divmod(q, nr)
                    sR = -sB[bi, bj] if mr[q] else sB[bi, bj]
                    mc = g.permutation(nc * nc) < D.MINORITY_CELLS
                    i0, j0 = bi * D.BLOCK + ri * D.REGION, bj * D.BLOCK + rj * D.REGION
                    T[i0:i0 + nc, j0:j0 + nc] = np.where(mc, -sR, sR).reshape(nc, nc)
        TB.append(T)
    return TA, np.stack(TB)


def acquire_history(cases, T, tag=D.TAG):
    """msegrid.acquire (BR001's birth, settle, teach and release) teaching AMPLITUDE x T; the same birth and noise for
    every history of a case. Returns the body V0, its moving average, the record R0 and theta."""
    return acquire(tag, cases, D.AMPLITUDE * T, replace(NATIVE, sigma=D.SIGMA_ACQ), N,
                   settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)


def read_codes(V0, R0, cases, history, tag=D.TAG, read_sd=D.READ_SD):
    """The codes read from the body at the end of acquisition, at the record's scale R*:
      L2  one sign per region: R* sign(region mean of (the gauge frame of R0's bonds) x V0 + N(0, read_sd)), the
          region's frame sign (NL001's code is exactly R* times its frame sign for a perfect template);
      L3  R* x the block mean of sign(V0), plus N(0, read_sd) per block.
    The noise is addressed by (case, 'code-read', history, level)."""
    H, W = edges_from(bonds(R0, True))
    sig = N1S.gauge_frame(H, W)
    z2 = np.stack([address(tag, *c.key(), "code-read", history, "L2").standard_normal((NR, NR)) for c in cases])
    z3 = np.stack([address(tag, *c.key(), "code-read", history, "L3").standard_normal((NB, NB)) for c in cases])
    Bg = D.R_STAR * np.sign(bproj(sig * V0, D.REGION) + read_sd * rep(z2, D.REGION))
    B3 = D.R_STAR * bproj(np.sign(V0), D.BLOCK) + read_sd * rep(z3, D.BLOCK)
    return Bg, B3


def corrupt_codes(BgA, BgB, cases, tag=D.TAG):
    """A's L2 with the signs of as many regions flipped, at random (case, 'corrupt'), as differ in sign between A's and
    B's L2; the count per case."""
    out, counts = BgA.copy(), []
    for j, c in enumerate(cases):
        a, b = np.sign(BgA[j, ::D.REGION, ::D.REGION]), np.sign(BgB[j, ::D.REGION, ::D.REGION])
        n = int((a != b).sum())
        pick = address(tag, *c.key(), "corrupt").permutation(NR * NR)[:n]
        m = np.zeros(NR * NR, bool)
        m[pick] = True
        out[j] = np.where(rep(m.reshape(NR, NR), D.REGION), -out[j], out[j])
        counts.append(n)
    return out, np.array(counts)


def step(r, xi, J, sig, Bg, B3, k2, k3, cap):
    """NL001's record step (nl001.sim.step's arithmetic with both codes absolute), the descending increment capped at
    cap; returns r and |the increment|. k2, k3: (branches, 1, 1) in absolute units."""
    r = r + D.EPS * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r)) + D.SIGMA_R * xi
    live = sig != 0
    mean_u = bproj(sig * r, D.REGION) / np.maximum(bproj(live * 1.0, D.REGION), 1.0 / D.REGION ** 2)
    inc = k2 * sig * (Bg - mean_u)
    inc = inc + k3 * (B3 - bproj(r, D.BLOCK))
    inc = np.clip(inc, -cap, cap)
    return np.clip(r + inc, -2.0, 2.0), np.abs(inc)


def relearn(H, W, Hb, Wb, V, eta=D.ETA):
    """lr002.sim.relations' Hebbian relearning from the body (its 'body' repair), every branch."""
    Hb = Hb + eta * (np.clip(V * np.roll(V, -1, -1), -1, 1) - Hb)
    Wb = Wb + eta * (np.clip(V * np.roll(V, -1, -2), -1, 1) - Wb)
    H = np.where(Hb != 0, np.sign(Hb), H)
    W = np.where(Wb != 0, np.sign(Wb), W)
    return H, W, Hb, Wb


def apply_K(u, T, case, r, H, W, V, E, tag=D.TAG):
    """NL001's K square (nl001.sim.kill_mask): the record 0, the bonds between two dead cells 0, and here the body and
    its moving average newborn (KILL_SD x N(0, 1), addressed by (case, 'newborn')); the codes are kept (copies)."""
    m = N1S.kill_mask(u, T)
    r, H, W = r.copy(), H.copy(), W.copy()
    r[m] = 0.0
    H = np.where(m & np.roll(m, -1, -1), 0.0, H)
    W = np.where(m & np.roll(m, -1, -2), 0.0, W)
    if V is not None:
        V, E = V.copy(), E.copy()
        nv = D.KILL_SD * address(tag, *case.key(), "newborn").standard_normal((N, N))
        V[m], E[m] = nv[m], nv[m]
    return r, H, W, V, E


def apply_R(units, r, H, W, V, E):
    """NL001's R: each of the case's four regions flipped coherently in the record, with its boundary bonds, and here
    in the body and its moving average too (copies; per case)."""
    r, H, W = r.copy(), H.copy(), W.copy()
    V, E = (None if x is None else x.copy() for x in (V, E))
    for (ri, rj) in units["regions"]:
        m = N1S.unit_mask(ri, rj, D.REGION)
        r[m] = -r[m]
        H, W = N1S.flip_boundary(H, W, m)
        if V is not None:
            V[m], E[m] = -V[m], -E[m]
    return r, H, W, V, E


ENDS = ("align_A", "region_ok_A", "block_ok", "min_reg_ok_A", "min_cell_ok_A", "ev_reg_ok", "spec_reg", "spec_cell",
        "agree_B", "k_reg_ok_A", "k_min_ok_A", "k_spec_reg", "k_cell_ok_A")


def masks(TA, TB, units):
    """Per case: A's and B's region signs, the block signs, A's minority regions and cells, the regions where A and B
    differ, the cells where they differ, the event regions."""
    regA, regB = N1S.unit_sign(TA, D.REGION), N1S.unit_sign(TB, D.REGION)
    blk = N1S.unit_sign(TA, D.BLOCK)
    up = D.BLOCK // D.REGION
    min_reg = regA != rep(blk, up)
    min_cell = np.sign(TA) != rep(regA, D.REGION)
    ev = np.zeros_like(regA, dtype=bool)
    for j, u in enumerate(units):
        for (ri, rj) in u["regions"]:
            ev[j, ri, rj] = True
    kill = np.stack([N1S.kill_mask(u, TA[j]) for j, u in enumerate(units)])
    kreg = N1S.unit_sign(kill * 1.0, D.REGION) > 0
    return {"regA": regA, "regB": regB, "blk": blk, "min_reg": min_reg, "min_cell": min_cell,
            "dreg": regA != regB, "dcell": np.sign(TA) != np.sign(TB), "ev": ev, "TA": np.sign(TA), "TB": np.sign(TB),
            "kill": kill, "kreg": kreg, "kmin": kreg & min_reg, "kdreg": kreg & (regA != regB)}


def score(x, mk):
    """Endpoints of one read of x (the record or a body), per sheet (branches x cases); mk broadcast to branches."""
    s = np.sign(x)
    reg, blk = N1S.unit_sign(x, D.REGION), N1S.unit_sign(x, D.BLOCK)
    okA, okB = s == mk["TA"], s == mk["TB"]
    rA, rB = reg == mk["regA"], reg == mk["regB"]
    f = N1S.frac
    return {"align_A": okA.mean((-2, -1)), "region_ok_A": rA.mean((-2, -1)), "block_ok": (blk == mk["blk"]).mean((-2, -1)),
            "min_reg_ok_A": f(mk["min_reg"], rA, (-2, -1)), "min_cell_ok_A": f(mk["min_cell"], okA, (-2, -1)),
            "ev_reg_ok": f(mk["ev"], rA, (-2, -1)),
            "spec_reg": f(mk["dreg"], rA, (-2, -1)) - f(mk["dreg"], rB, (-2, -1)),
            "spec_cell": f(mk["dcell"], okA, (-2, -1)) - f(mk["dcell"], okB, (-2, -1)),
            "agree_B": okB.mean((-2, -1)),
            "k_reg_ok_A": f(mk["kreg"], rA, (-2, -1)), "k_min_ok_A": f(mk["kmin"], rA, (-2, -1)),
            "k_spec_reg": f(mk["kdreg"], rA, (-2, -1)) - f(mk["kdreg"], rB, (-2, -1)),
            "k_cell_ok_A": f(mk["kill"], okA, (-2, -1))}


def prepare(cases, tag=D.TAG, read_sd=D.READ_SD):
    """Both histories' templates and acquisitions, the tissue's start (A's acquired body and record, its bonds) and the
    four references (L2, L3) per case."""
    TA, TB = templates(cases, tag)
    VA, EA, RA, th = acquire_history(cases, TA, tag)
    VB, _, RB, _ = acquire_history(cases, TB, tag)
    BgA, B3A = read_codes(VA, RA, cases, "A", tag, read_sd)
    BgK, B3K = read_codes(RA, RA, cases, "A-copy", tag, read_sd)          # read from the acquired record
    BgB, B3B = read_codes(VB, RB, cases, "B", tag, read_sd)
    BgC, ncorrupt = corrupt_codes(BgA, BgB, cases, tag)
    refs = {"own": (BgA, B3A), "copy": (BgK, B3K), "foreign": (BgB, B3B), "corrupt": (BgC, B3A), "off": (BgA, B3A)}
    return {"TA": TA, "TB": TB, "V0": VA, "E0": EA, "R0": RA, "RB": RB, "th": th, "refs": refs, "ncorrupt": ncorrupt}


def run(cases, unit, labels=D.LABELS, prep=None, window=D.WINDOW, reads=D.READS, tag=D.TAG, cap=D.CAP):
    """labels: [(arm name, event)]. Returns the tissue's endpoints {('r'|'v', name): (reads, branches, cases)}, the dose
    (branches, cases) and the final state."""
    P = prepare(cases, tag) if prep is None else prep
    k, nb = len(cases), len(labels)
    idx = np.tile(np.arange(k), nb)
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    body = unit == "dw"
    st = {x: [] for x in ("r", "H", "W", "V", "E", "Bg", "B3")}
    for name, event in labels:
        arm = D.ARM[name]
        Bg, B3 = P["refs"][arm.ref]
        for j in range(k):
            r, H, W, V, E = P["R0"][j], H0[j], W0[j], (P["V0"][j] if body else None), (P["E0"][j] if body else None)
            if event == "R":
                r, H, W, V, E = apply_R(units[j], r, H, W, V, E)
            elif event == "K":
                r, H, W, V, E = apply_K(units[j], P["TA"][j], cases[j], r, H, W, V, E, tag)
            for key, x in zip(("r", "H", "W", "V", "E", "Bg", "B3"), (r, H, W, V, E, Bg[j], B3[j])):
                st[key].append(x)
    r, H, W, Bg, B3 = (np.stack(st[x]).astype(float) for x in ("r", "H", "W", "Bg", "B3"))
    V, E = (np.stack(st[x]).astype(float) if body else None for x in ("V", "E"))
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W                    # a killed bond: strength 0
    col = lambda f: np.repeat([f(D.ARM[a]) for a, _ in labels], k)[:, None, None]
    k2, k3 = col(lambda a: a.k2 * D.KC), col(lambda a: a.k3 * D.KC)
    mk = {key: np.concatenate([v] * nb) for key, v in masks(P["TA"], P["TB"], units).items()}
    p = replace(NATIVE, sigma=D.SIGMA)
    thb = (P["th"] * 0.0)[idx]                              # quiet tissue: theta x 0
    xs = Stream(tag, cases, "record-noise", side=N)
    zs = Stream(tag, cases, "future", side=N) if body else None
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    ends = {(w, e): [] for w in (("r", "v") if body else ("r",)) for e in ENDS}
    dose = np.zeros(nb * k)
    xb = zb = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            xb = xs.take(D.CHUNK)
            zb = zs.take(D.CHUNK) if body else None
        if body:
            V, E, _, _, _ = S.body(V, E, r, thb, zb[i][idx], p, D.GAIN, 0.0, None)
        r, inc = step(r, xb[i][idx], J, sig, Bg, B3, k2, k3, cap)
        dose += inc.sum((-2, -1))
        if body:
            H, W, Hb, Wb = relearn(H, W, Hb, Wb, V)
            J = halves(H, W)
            sig = N1S.gauge_frame(H, W)
        if t in reads:
            for e, v in score(r, mk).items():
                ends[("r", e)].append(v)
            if body:
                for e, v in score(V, mk).items():
                    ends[("v", e)].append(v)
    out = {key: np.array(v).reshape(len(reads), nb, k) for key, v in ends.items()}
    final = {"r": r.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N), "W": W.reshape(nb, k, N, N)}
    if body:
        final["V"] = V.reshape(nb, k, N, N)
    return out, dose.reshape(nb, k) / (N * N * window), final, P


SUCC = ("acqA", "acqB", "none")                                 # extra L1-only recipient branches


def successor(cases, final, P, labels=D.LABELS, window=D.WINDOW2, reads=D.READS2, tag=D.TAG, cap=D.CAP):
    """Fresh dw bodies born from newborn noise, each reading a record at gain 0.2, the record protected (no noise, no
    relearning: it steps through its own bonds). Branches, in order:
      L1-only  every label's final L1 record (r, H, W); then A's and B's acquired records; then nothing (gain 0);
      coded    every label's final L1 record together with the branch's coarse codes (its reference's L2 and L3 at its
               own gains k2, k3, NL001's arithmetic with the cap, in the gauge frame of the inherited bonds); 'off'
               passes no codes (k2 = k3 = 0), so its coded recipient equals its L1-only one.
    The record step is nl002.sim.step for every branch (with k2 = k3 = 0 it is msegrid.record_step's arithmetic). All
    recipient branches of a case share the birth and the noise. Returns ({e: (reads, nb + 3, k)}, {e: (reads, nb, k)})."""
    k, nb = len(cases), len(labels)
    H0, W0 = edges_from(bonds(P["R0"], True))
    HB, WB = edges_from(bonds(P["RB"], True))
    rL, HL, WL = (final[x].reshape(nb * k, N, N) for x in ("r", "H", "W"))
    r = np.concatenate([rL, P["R0"], P["RB"], np.zeros_like(P["R0"]), rL])
    H = np.concatenate([HL, H0, HB, np.ones_like(H0), HL])
    W = np.concatenate([WL, W0, WB, np.ones_like(W0), WL])
    nt = 2 * nb + len(SUCC)
    idx = np.tile(np.arange(k), nt)
    gains = np.repeat([D.GAIN] * (nb + 2) + [0.0] + [D.GAIN] * nb, k)[:, None, None]
    zero = np.zeros((k, N, N))
    codes = [P["refs"][D.ARM[a].ref] for a, _ in labels]
    Bg = np.concatenate([zero] * (nb + 3) + [c[0] for c in codes])
    B3 = np.concatenate([zero] * (nb + 3) + [c[1] for c in codes])
    kk = lambda f: np.repeat([0.0] * (nb + 3) + [f(D.ARM[a]) * D.KC for a, _ in labels], k)[:, None, None]
    k2, k3 = kk(lambda a: a.k2), kk(lambda a: a.k3)
    V = birth(tag, cases, "successor", "dw", side=N)[idx].copy()
    E = V.copy()
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    units = N1S.event_units(cases, tag)
    mk = {key: np.concatenate([v] * nt) for key, v in masks(P["TA"], P["TB"], units).items()}
    p = replace(NATIVE, sigma=D.SIGMA)
    thb = np.zeros_like(V)
    st, xs = (Stream(tag, cases, s_, "dw", side=N) for s_ in ("successor-future", "successor-record-noise"))
    ends = {e: [] for e in ENDS}
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, _, _, _ = S.body(V, E, r, thb, buf[i][idx], p, gains, 0.0, None)
        r, _ = step(r, xbuf[i][idx], J, sig, Bg, B3, k2, k3, cap)
        if t in reads:
            for e, v in score(V, mk).items():
                ends[e].append(v)
    full = {e: np.array(v).reshape(len(reads), nt, k) for e, v in ends.items()}
    return ({e: v[:, :nb + 3] for e, v in full.items()}, {e: v[:, nb + 3:] for e, v in full.items()})
