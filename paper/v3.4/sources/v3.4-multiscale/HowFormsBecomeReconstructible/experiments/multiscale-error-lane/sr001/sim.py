"""SR001's tissue: NP001's (np001.sim.prepare, dl001.sim.body and LR002's record of relations, unchanged and imported),
advanced generation by generation with lr004.sim.relations (unchanged) carrying every route.

One generation advances the body and the records of every route as branches (route-major: index = route x cases + case),
all reading the case's noise streams for that generation (the body's, the first record's and its bonds', and the second
record's for the vote branches), so routes are paired within a case. One update, in order, as lr004.sim.run: the body
reads the first record (dl001.sim.body, the route's gain); bond noise; the records step through their bonds; relearning;
parity. With the stream names of np001.sim.stage1 (or lr004.sim.run) and the acquired body, a generation equals those
runs bit for bit (checks Q3).

A lineage: G0 is the acquired record R0 and its bonds; at each renewal a newborn body (born from noise, the same birth
for every route and body kind) reads the incoming packet (r, H, W, and the vote's second record), the bonds' strengths
restarting at STRENGTH0 x sign. Fresh recipients after the last generation are np001.sim.successor's arithmetic (a
protected record read at gain 0.2, a no-record control at gain 0), with any body kind of BODY_KINDS.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import bond_err, cut_for, edges_from
from lr002 import sim as L2S
from lr004 import sim as L4S
from mse.native import NATIVE
from msegrid.core import Stream, birth, bonds
from np001 import sim as N1S

from . import design as D

prepare = N1S.prepare                                           # DL002's acquisition (np001's, unchanged)
ENDS = ("r_a", "v_a", "r_shape", "v_shape", "r_spacing", "v_spacing", "agree", "bond_err")
FENDS = ("r_f", "v_f")                                          # (foreign placement, branch)
ENDS2 = ("v_a", "v_shape", "v_spacing", "agree")
GEN_NAMES = lambda g: (("gen", g, "future"), ("gen", g, "record-noise"), ("gen", g, "bond-noise"),
                       ("gen", g, "record-noise", "B"), ("gen", g, "bond-noise", "B"))
NP1_NAMES = (("future",), ("record-noise",), ("bond-noise",), ("record-noise", "B"), ("bond-noise", "B"))


def notch(side, kstar, w):
    """exp(-(k - kstar)^2 / (2 w^2)) on the rfft grid, k the lattice Laplacian's eigenvalue (dl001.sim.ghat's grid)."""
    q, qr = 2 * np.pi * np.fft.fftfreq(side), 2 * np.pi * np.fft.rfftfreq(side)
    k = (2 - 2 * np.cos(q))[:, None] + (2 - 2 * np.cos(qr))[None, :]
    return np.exp(-0.5 * ((k - kstar) / w) ** 2)


def kernel(body, notch_params=None):
    """(alpha, G) for dl001.sim.body: DL001's bodies unchanged; a notch body adds beta x notch(K8, w) to its base body's
    inhibition (G = ghat(L) + beta / alpha x notch)."""
    if body in DL.BODIES:
        alpha, L = DL.BODIES[body]
        return alpha, (S.ghat(D.SIDE, L) if alpha else None)
    base, beta, w = notch_params if notch_params is not None else D.NOTCH[body]
    alpha, L = DL.BODIES[base]
    return alpha, S.ghat(D.SIDE, L) + (beta / alpha) * notch(D.SIDE, DL.K8, w)


def params(routes, k):
    """lr004.sim.relations's per-branch parameters: noise cut, source, parity, the vote branches."""
    def rep(f):
        return np.repeat([f(c) for c in routes], k)[:, None, None]
    P = {"cut": rep(lambda c: cut_for(c.rate)), "src": rep(lambda c: D.SOURCES[c.source]), "par": rep(lambda c: c.parity)}
    P["two_idx"] = np.nonzero(np.repeat([c.two for c in routes], k))[0]
    P["cut_two"] = P["cut"][P["two_idx"]]
    P["vote_two"] = P["src"][P["two_idx"]] == D.SOURCES["vote"]
    P["amask"] = np.zeros((len(routes) * k, D.SIDE, D.SIDE), bool)
    return P


def foreign(T, unit, cases):
    """(NFOREIGN, cases, side, side): T rolled across its stripes by 1/8, 1/4 and 3/8 of its period."""
    ax = [-1 if c.message % 2 == 0 else -2 for c in cases]
    return np.stack([np.stack([np.roll(T[j], s, axis=ax[j]) for j in range(len(cases))]) for s in D.foreign_rolls(unit)])


def score(out, V, r, H, W, H0, W0, Tb, Tfb):
    """Append one read: the record and the body against T and the foreign placements, shapes, spacings, agreement and
    bond error against the acquired bonds."""
    out["r_a"].append(S.sign(r, Tb))
    out["v_a"].append(S.sign(V, Tb))
    out["r_f"].append(np.stack([S.sign(r, t) for t in Tfb]))
    out["v_f"].append(np.stack([S.sign(V, t) for t in Tfb]))
    out["r_shape"].append(S.best_shift(r, Tb))
    out["v_shape"].append(S.best_shift(V, Tb))
    out["r_spacing"].append(S.spacing(r))
    out["v_spacing"].append(S.spacing(V))
    out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
    out["bond_err"].append(bond_err(H, W, H0, W0))


def generation(body, routes, cases, V, E, A, B, tag, names, window, reads, Tb, Tfb, H0, W0, thb, P=None, notch_params=None):
    """Advance one generation of `window` updates. V, E: the bodies (n = routes x cases); A = (H, W, Hb, Wb, r) every
    branch's first record; B the vote branches' second record (or None). Returns V, E, A, B and the reads."""
    alpha, G = kernel(body, notch_params)
    k = len(cases)
    n = len(routes) * k
    idx = np.tile(np.arange(k), len(routes))
    P = params(routes, k) if P is None else P
    gain = np.repeat([c.gain for c in routes], k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, *nm, side=D.SIDE) for nm in names[:3])
    two = P["two_idx"]
    if len(two):
        xsB, zsB = (Stream(tag, cases, *nm, side=D.SIDE) for nm in names[3:5])
        ctwo = idx[two]
    aval = np.zeros((n, D.SIDE, D.SIDE))                        # no anchors in this study
    out = {key: [] for key in ENDS + FENDS}
    buf = xbuf = zbuf = xbB = zbB = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if len(two):
                xbB, zbB = xsB.take(D.CHUNK), zsB.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, A[4], thb, buf[i][idx], p, gain, alpha, G)
        A, B, op = L4S.relations(A, B, xbuf[i][idx], zbuf[i][idx], None if not len(two) else xbB[i][ctwo],
                                 None if not len(two) else zbB[i][ctwo], V, P, aval)
        if t in reads:
            score(out, V, A[4], A[0], A[1], H0, W0, Tb, Tfb)
    return V, E, A, B, out


def handoff(A, B):
    """The packet: the record's values and bond signs; the bonds' strengths restart at STRENGTH0 x sign."""
    H, W, Hb, Wb, r = A
    A = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    if B is not None:
        HB, WB, HbB, WbB, rB = B
        B = (HB.copy(), WB.copy(), D.STRENGTH0 * HB, D.STRENGTH0 * WB, rB.copy())
    return A, B


def lineage(body, routes, cases, R0, th, T, Tf, tag=D.TAG, gens=D.GENS, t_gen=D.T_GEN, notch_params=None, keep=(1, 16)):
    """G0's acquired record, then `gens` renewals by newborn bodies of kind `body`. Returns the reads at each
    generation's last update (gens, ...), the records kept at the generations in `keep`, and the last records."""
    k = len(cases)
    n = len(routes) * k
    idx = np.tile(np.arange(k), len(routes))
    P = params(routes, k)
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    A = (H0.copy(), W0.copy(), D.STRENGTH0 * H0, D.STRENGTH0 * W0, R0[idx].copy())
    two = P["two_idx"]
    B = (H0[two].copy(), W0[two].copy(), D.STRENGTH0 * H0[two], D.STRENGTH0 * W0[two], R0[idx][two].copy()) if len(two) else None
    Tb, Tfb, thb = T[idx], Tf[:, idx], (th * D.THETA)[idx]
    reads = {key: [] for key in ENDS + FENDS}
    reads["rB_a"] = []
    kept = {}
    for g in range(1, gens + 1):
        V = birth(tag, cases, "gen", g, "birth", side=D.SIDE)[idx].copy()
        E = V.copy()
        V, E, A, B, out = generation(body, routes, cases, V, E, A, B, tag, GEN_NAMES(g), t_gen, {t_gen}, Tb, Tfb, H0, W0,
                                     thb, P, notch_params)
        for key in ENDS + FENDS:
            reads[key].append(out[key][0])
        reads["rB_a"].append(S.sign(B[4], Tb[two]) if B is not None else np.zeros(0))
        if g in keep:
            kept[g] = {"V": V.copy(), "r": A[4].copy(), "H": A[0].astype(np.int8), "W": A[1].astype(np.int8)}
        A, B = handoff(A, B)
    res = {key: np.array(v) for key, v in reads.items()}
    return res, kept, A, B


class _Protected:
    """No bond noise, no relearning, no parity: the record steps through its bonds only (np001.sim._Protected)."""
    rate, learn, parity = 0.0, "", False


def recipient(body, r, H, W, cases, th, T, Tf, reads, gains, tag=D.TAG, window=D.WINDOW2, names=None, born=None,
              notch_params=None):
    """np001.sim.successor's arithmetic with any body kind: a newborn reading each record (r, H, W: branch-major) at
    gains[branch] (0 for the no-record control), the record protected; all branches of a case share the birth and the
    noise. names: (birth, body noise, record noise) stream addresses."""
    alpha, G = kernel(body, notch_params)
    names = names or (("recipient", "birth"), ("recipient", "future"), ("recipient", "record-noise"))
    k, nb = len(cases), len(gains)
    idx = np.tile(np.arange(k), nb)
    V = (born if born is not None else birth(tag, cases, *names[0], side=D.SIDE))[idx].copy()
    E = V.copy()
    r, H, W = r.copy(), H.copy(), W.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    Tb, Tfb, thb = T[idx], Tf[:, idx], (th * D.THETA)[idx]
    P = L2S.params([_Protected()] * nb, k)
    gain = np.repeat(np.asarray(gains, float), k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs = (Stream(tag, cases, *nm, side=D.SIDE) for nm in names[1:3])
    zero = np.zeros_like(V)
    out = {key: [] for key in ENDS2 + ("v_f",)}
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        H, W, Hb, Wb, r = L2S.relations(H, W, Hb, Wb, r, xbuf[i][idx], zero, V, P, D.KC, None)
        if t in reads:
            out["v_a"].append(S.sign(V, Tb))
            out["v_f"].append(np.stack([S.sign(V, t_) for t_ in Tfb]))
            out["v_shape"].append(S.best_shift(V, Tb))
            out["v_spacing"].append(S.spacing(V))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(V=V)
    return res
