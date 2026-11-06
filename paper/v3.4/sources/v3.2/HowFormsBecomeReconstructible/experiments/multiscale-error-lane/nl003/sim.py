"""NL003's tissue: NL002's (nl002.sim, imported unchanged: prepare, step, relearn, apply_R, apply_K, masks, score, and
through it nl001.sim and dl001.sim), with anchors and the arbiter's gate on the descending increment.

run() and successor() follow nl002.sim.run's and nl002.sim.successor's loops line for line, with one change: the record
step is nl002.sim.step called with k2 x G in place of k2, G (branches, n, n) in {0, 1} the arbiter's gate, constant on
each region. An arm without an arbiter has G = 1.0 everywhere, so k2 x G = k2 exactly and its branch equals NL002's bit
for bit (checks Q3). The gate of a gated branch is computed each update, just before the record step, from the current
record, the current gauge frame and the branch's anchors.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import sim as S
from lr001.sim import edges_from, halves
from mse.native import NATIVE, address
from msegrid.core import Stream, birth, bonds
from nl001 import sim as N1S
from nl002 import design as D2
from nl002 import sim as S2

from . import design as D

N = D.SIDE
NR = N // D.REGION
cases_for = S2.cases_for
prepare = S2.prepare


def rep(x, size=D.REGION):
    return np.repeat(np.repeat(x, size, axis=-2), size, axis=-1)


def vote_sign(x):
    """lr005.sim.vote_sign's rule: +1, -1, or 0 for a value not confident enough (|x| < VMIN)."""
    return np.where(x >= D.VMIN, 1.0, np.where(x <= -D.VMIN, -1.0, 0.0))


def anchors(cases, density, tag=D.TAG):
    """The anchored cells: a random 1/density of the sheet per case (lr004.sim.anchors' rule), without replacement."""
    n = N * N
    out = np.zeros((len(cases), N, N), bool)
    for j, c in enumerate(cases):
        out[j].flat[address(tag, *c.key(), "anchors", density).permutation(n)[: n // density]] = True
    return out


def read_displaced(field, cases, sigma, tag=D.TAG):
    """GC001's quenched misread: each site reads field at its own displaced site (i + dx, j + dy), periodic, with
    (dx, dy) = rint(sigma x N(0, 1)) per site and axis, addressed by (case, 'nl003-misread'); sigma 0 returns field."""
    if sigma == 0:
        return field
    out = np.empty_like(field)
    i, j = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    for c, case in enumerate(cases):
        g = address(tag, *case.key(), "nl003-misread").standard_normal((2, N, N))
        dx, dy = np.rint(sigma * g[0]).astype(int), np.rint(sigma * g[1]).astype(int)
        out[c] = field[c][(i + dx) % N, (j + dy) % N]
    return out


def anchor_fields(cases, P, arm, event, units, tag=D.TAG):
    """Per case: (am, aval) for a gated arm under an event: the anchors at the arm's density holding sign(R0_A) (read
    displaced under a misread); K removes the anchors in the killed square; change respecifies the anchors in the
    regions where A and B differ to B's acquired record signs."""
    cfg = D.gate_config(arm.arb)
    am = anchors(cases, cfg["density"], tag)
    aval = read_displaced(np.sign(P["R0"]), cases, cfg["sigma"], tag)
    if event == "K":
        kill = np.stack([N1S.kill_mask(units[j], P["TA"][j]) for j in range(len(cases))])
        am = am & ~kill
    elif event == "change":
        mk = S2.masks(P["TA"], P["TB"], units)
        dcells = rep(mk["dreg"])
        aval = np.where(dcells, np.sign(P["RB"]), aval)
    return am, np.where(am, aval, 0.0)


def ring_counts(x, g):
    """(m, NR, NR): the sums of x (m, n, n) over each region widened by g sites on every side (periodic)."""
    m = x.shape[0]
    Pd = np.pad(x.astype(np.int32), ((0, 0), (g, g), (g, g)), mode="wrap")
    Sm = np.zeros((m, N + 2 * g + 1, N + 2 * g + 1), np.int32)
    Sm[:, 1:, 1:] = Pd.cumsum(1).cumsum(2)
    i0 = np.arange(NR) * D.REGION
    i1 = i0 + D.REGION + 2 * g
    return (Sm[:, i1][:, :, i1] - Sm[:, i0][:, :, i1] - Sm[:, i1][:, :, i0] + Sm[:, i0][:, :, i0])


def gate(r, sig, Bg, am, aval, n, q, ring, ring_max):
    """The arbiter on m branches: r, sig, Bg, am, aval (m, n, n); n, q, ring, ring_max (m,) arrays.
    Returns refused (m, NR, NR) bool: the regions whose L2 increment is refused this update."""
    m = r.shape[0]
    target = np.sign(sig * Bg)
    live = am & (vote_sign(r) != 0) & (target != 0)
    dis = live & (aval != target)
    nd = dis.reshape(m, NR, D.REGION, NR, D.REGION).sum((2, 4))
    nl = live.reshape(m, NR, D.REGION, NR, D.REGION).sum((2, 4))
    refused = (nd >= n[:, None, None]) & (nd >= q[:, None, None] * nl)
    for g in sorted(set(int(x) for x in ring if x > 0)):
        sel = ring == g
        outer = ring_counts(dis[sel], g) - nd[sel]
        refused[sel] &= outer <= ring_max[sel][:, None, None]
    return refused


def gate_arrays(labels, k):
    """Per branch (event-major, label x cases): gated (bool), n, q, ring, ring_max arrays, from each arm's config."""
    cfgs = [D.gate_config(D_ARMS[a].arb) for a, _ in labels]
    rep_ = lambda f: np.repeat([f(c) for c in cfgs], k)
    return {"gated": rep_(lambda c: c is not None), "n": rep_(lambda c: c["n"] if c else 0),
            "q": rep_(lambda c: c["q"] if c else 0.0), "ring": rep_(lambda c: c["ring"] if c else 0),
            "ring_max": rep_(lambda c: c["ring_max"] if c else 0)}


D_ARMS = {}                                                     # set by use_stage()


def use_stage(stage):
    """The stage's arms (the tuning has its own); returns (arms, labels)."""
    arms, labels = D.arms_labels(stage)
    D_ARMS.clear()
    D_ARMS.update(arms)
    return arms, labels


def gated_k2(k2, refused_idx, refused, nb):
    """k2 (nb, 1, 1) times the gate G (nb, n, n): 1.0 except on the refused regions of the gated branches."""
    G = np.ones((nb, N, N))
    if refused_idx.size:
        G[refused_idx] = 1.0 - rep(refused).astype(float)
    return k2 * G


def run(cases, unit, labels, prep=None, window=D.WINDOW, reads=D.READS, tag=D.TAG, cap=D.CAP):
    """nl002.sim.run's loop with the arbiter. labels: [(arm name, event)] with arms in D_ARMS (use_stage). Returns the
    tissue's endpoints {('r'|'v', name): (reads, branches, cases)}, the arbiter's {('a', name): ...}, the dose, the
    final state, the prepared references and the anchors of the gated branches."""
    P = S2.prepare(cases, tag) if prep is None else prep
    k, nb = len(cases), len(labels)
    idx = np.tile(np.arange(k), nb)
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    body = unit == "dw"
    st = {x: [] for x in ("r", "H", "W", "V", "E", "Bg", "B3")}
    AM, AV = [], []
    for name, event in labels:
        arm = D_ARMS[name]
        Bg, B3 = P["refs"][arm.ref]
        ev2 = event if event in ("R", "K") else "none"          # change: the record, body and codes as in none
        if arm.arb:
            am, aval = anchor_fields(cases, P, arm, event, units, tag)
        else:
            am, aval = np.zeros((k, N, N), bool), np.zeros((k, N, N))
        for j in range(k):
            r, H, W, V, E = P["R0"][j], H0[j], W0[j], (P["V0"][j] if body else None), (P["E0"][j] if body else None)
            if ev2 == "R":
                r, H, W, V, E = S2.apply_R(units[j], r, H, W, V, E)
            elif ev2 == "K":
                r, H, W, V, E = S2.apply_K(units[j], P["TA"][j], cases[j], r, H, W, V, E, tag)
            for key, x in zip(("r", "H", "W", "V", "E", "Bg", "B3"), (r, H, W, V, E, Bg[j], B3[j])):
                st[key].append(x)
            AM.append(am[j])
            AV.append(aval[j])
    r, H, W, Bg, B3 = (np.stack(st[x]).astype(float) for x in ("r", "H", "W", "Bg", "B3"))
    V, E = (np.stack(st[x]).astype(float) if body else None for x in ("V", "E"))
    AM, AV = np.stack(AM), np.stack(AV)
    Hb, Wb = D2.STRENGTH0 * H, D2.STRENGTH0 * W
    col = lambda f: np.repeat([f(D_ARMS[a]) for a, _ in labels], k)[:, None, None]
    k2, k3 = col(lambda a: a.k2 * D.KC), col(lambda a: a.k3 * D.KC)
    ga = gate_arrays(labels, k)
    gidx = np.flatnonzero(ga["gated"])
    mk = {key: np.concatenate([v] * nb) for key, v in S2.masks(P["TA"], P["TB"], units).items()}
    p = replace(NATIVE, sigma=D2.SIGMA)
    thb = (P["th"] * 0.0)[idx]
    xs = Stream(tag, cases, "record-noise", side=N)
    zs = Stream(tag, cases, "future", side=N) if body else None
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    ends = {(w, e): [] for w in (("r", "v") if body else ("r",)) for e in S2.ENDS}
    for e in ("ref_all", "ref_dreg", "ref_other", "ever"):
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
            refused = gate(r[gidx], sig[gidx], Bg[gidx], AM[gidx], AV[gidx], ga["n"][gidx], ga["q"][gidx],
                           ga["ring"][gidx], ga["ring_max"][gidx])
            ever[gidx] |= refused.any((-2, -1))
            r, inc = S2.step(r, xb[i][idx], J, sig, Bg, B3, gated_k2(k2, gidx, refused, nb * k), k3, cap)
        else:
            r, inc = S2.step(r, xb[i][idx], J, sig, Bg, B3, k2, k3, cap)
        dose += inc.sum((-2, -1))
        if body:
            H, W, Hb, Wb = S2.relearn(H, W, Hb, Wb, V)
            J = halves(H, W)
            sig = N1S.gauge_frame(H, W)
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
    out = {key: np.array(v).reshape(len(reads), nb, k) for key, v in ends.items()}
    final = {"r": r.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N), "W": W.reshape(nb, k, N, N)}
    if body:
        final["V"] = V.reshape(nb, k, N, N)
    return out, dose.reshape(nb, k) / (N * N * window), final, P, {"am": AM, "aval": AV}


SUCC = S2.SUCC                                                  # A's and B's acquired records, and nothing


def successor(cases, final, P, labels, anchors_=None, window=D.WINDOW2, reads=D.READS2, tag=D.TAG, cap=D.CAP):
    """nl002.sim.successor's recipients for every label (L1-only, the three extra, coded), then a third recipient for
    the gated labels: coded and gated by the arbiter, with the branch's anchors, read against the recipient's record.
    Returns ({e: (reads, nb + 3, k)}, {e: (reads, nb, k)}, {e: (reads, ng, k)}, the gated label indices)."""
    k, nb = len(cases), len(labels)
    H0, W0 = edges_from(bonds(P["R0"], True))
    HB, WB = edges_from(bonds(P["RB"], True))
    rL, HL, WL = (final[x].reshape(nb * k, N, N) for x in ("r", "H", "W"))
    gl = [i for i, (a, _) in enumerate(labels) if D_ARMS[a].arb]
    gsel = np.concatenate([np.arange(i * k, (i + 1) * k) for i in gl]) if gl else np.zeros(0, int)
    ng = len(gl)
    r = np.concatenate([rL, P["R0"], P["RB"], np.zeros_like(P["R0"]), rL, rL[gsel]])
    H = np.concatenate([HL, H0, HB, np.ones_like(H0), HL, HL[gsel]])
    W = np.concatenate([WL, W0, WB, np.ones_like(W0), WL, WL[gsel]])
    nt = 2 * nb + len(SUCC) + ng
    idx = np.tile(np.arange(k), nt)
    gains = np.repeat([D2.GAIN] * (nb + 2) + [0.0] + [D2.GAIN] * nb + [D2.GAIN] * ng, k)[:, None, None]
    zero = np.zeros((k, N, N))
    codes = [P["refs"][D_ARMS[a].ref] for a, _ in labels]
    Bg = np.concatenate([zero] * (nb + 3) + [c[0] for c in codes] + [codes[i][0] for i in gl])
    B3 = np.concatenate([zero] * (nb + 3) + [c[1] for c in codes] + [codes[i][1] for i in gl])
    kk = lambda f: np.repeat([0.0] * (nb + 3) + [f(D_ARMS[a]) * D.KC for a, _ in labels]
                             + [f(D_ARMS[labels[i][0]]) * D.KC for i in gl], k)[:, None, None]
    k2, k3 = kk(lambda a: a.k2), kk(lambda a: a.k3)
    V = birth(tag, cases, "successor", "dw", side=N)[idx].copy()
    E = V.copy()
    J = halves(H, W)
    sig = N1S.gauge_frame(H, W)
    units = N1S.event_units(cases, tag)
    mk = {key: np.concatenate([v] * nt) for key, v in S2.masks(P["TA"], P["TB"], units).items()}
    p = replace(NATIVE, sigma=D2.SIGMA)
    thb = np.zeros_like(V)
    st, xs = (Stream(tag, cases, s_, "dw", side=N) for s_ in ("successor-future", "successor-record-noise"))
    ends = {e: [] for e in S2.ENDS}
    gev, gever = [], np.zeros(ng * k, bool)
    if ng:
        g0 = 2 * nb + len(SUCC)
        gidx = np.arange(g0 * k, nt * k)
        ga = gate_arrays([labels[i] for i in gl], k)
        AM, AV = anchors_["am"][gsel], anchors_["aval"][gsel]
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D2.CHUNK
        if i == 0:
            buf, xbuf = st.take(D2.CHUNK), xs.take(D2.CHUNK)
        V, E, _, _, _ = S.body(V, E, r, thb, buf[i][idx], p, gains, 0.0, None)
        if ng:
            refused = gate(r[gidx], sig[gidx], Bg[gidx], AM, AV, ga["n"], ga["q"], ga["ring"], ga["ring_max"])
            gever |= refused.any((-2, -1))
            r, _ = S2.step(r, xbuf[i][idx], J, sig, Bg, B3, gated_k2(k2, gidx, refused, nt * k), k3, cap)
        else:
            r, _ = S2.step(r, xbuf[i][idx], J, sig, Bg, B3, k2, k3, cap)
        if t in reads:
            for e, v in S2.score(V, mk).items():
                ends[e].append(v)
            gev.append(gever.astype(float).copy())
    full = {e: np.array(v).reshape(len(reads), nt, k) for e, v in ends.items()}
    gated = {e: v[:, 2 * nb + 3:] for e, v in full.items()}
    gated["ever"] = np.array(gev).reshape(len(reads), ng, k)
    return ({e: v[:, :nb + 3] for e, v in full.items()}, {e: v[:, nb + 3:2 * nb + 3] for e, v in full.items()}, gated, gl)
