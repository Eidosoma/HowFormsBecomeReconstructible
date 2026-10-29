"""FN001's tissue (DRAFT): LR004's (DL002's preparation, DL001's body and lr004.sim.relations, unchanged and imported),
injured by killing cells, with function readouts that do not use the template's registration.

A run advances one body under every condition as branches (condition-major: index = condition x cases + case); every
branch reads the case's noise streams (and the second record's, for the vote), so teachers, rates and injury schedules
are paired within a case. One update is lr004.sim.run's: the body reads the first record (dl001.sim.body); bond noise;
the records step through their bonds; relearning; parity. After the reads of update t, the wounds due at t are applied.

A wound kills the cells of an 8 x 8 square: their body values and moving averages become newborn values, their record
values (both records) become 0, and every bond touching them takes a random sign at strength 0 (both records, each its
own draw), so it is relearned at once by the branch's teacher.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy import ndimage

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import bond_err, edges_from
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr004.sim import params, relations
from mse.native import NATIVE, address
from msegrid.core import Stream, bonds

from . import design as D


# injuries ---------------------------------------------------------------------------------------------------------

def wound_masks(cases, tag=D.TAG):
    """Mask 'a' (a random 8 x 8 square per case) and mask 'b' (the same square shifted by half the sheet)."""
    a = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    rows = np.arange(D.WOUND)
    for j, c in enumerate(cases):
        y, x = address(tag, *c.key(), "wound").integers(0, D.SIDE, 2)
        a[j][np.ix_((y + rows) % D.SIDE, (x + rows) % D.SIDE)] = True
    return {"a": a, "b": np.roll(a, (D.SIDE // 2, D.SIDE // 2), (-2, -1))}


def touching(m):
    """Bonds (H: right, W: lower) with at least one end in the mask."""
    return m | np.roll(m, -1, -1), m | np.roll(m, -1, -2)


def kill(state, m, sh, sw):
    """Kill the cells under m in one record's (H, W, Hb, Wb, r): values 0, touching bonds random at strength 0."""
    H, W, Hb, Wb, r = state
    th, tw = touching(m)
    H, W = np.where(th, sh, H), np.where(tw, sw, W)
    Hb, Wb = np.where(th, 0.0, Hb), np.where(tw, 0.0, Wb)
    return H, W, Hb, Wb, np.where(m, 0.0, r)


def random_signs(case, n, which, tag=D.TAG):
    """The dead bonds' new signs (H, W) at wound n of record which ('A' or 'B')."""
    g = address(tag, *case.key(), "bonds", n, which)
    return (np.where(g.random((D.SIDE, D.SIDE)) < 0.5, -1.0, 1.0), np.where(g.random((D.SIDE, D.SIDE)) < 0.5, -1.0, 1.0))


# function readouts ------------------------------------------------------------------------------------------------

def domains(x):
    """Sizes of the connected domains (4-neighbour, periodic) of a boolean sheet."""
    lab, n = ndimage.label(x)
    if n == 0:
        return np.zeros(0, int)
    parent = np.arange(n + 1)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in ((lab[0, :], lab[-1, :]), (lab[:, 0], lab[:, -1])):
        for p, q in zip(a, b):
            if p and q:
                rp, rq = find(p), find(q)
                if rp != rq:
                    parent[max(rp, rq)] = min(rp, rq)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    roots = np.array([find(i) for i in range(n + 1)])
    tot = np.bincount(roots[1:], weights=sizes[1:], minlength=n + 1)
    return tot[tot > 0].astype(int)


def topology(s):
    """(large domains of +, large domains of -, islands) of a +-1 sheet."""
    out = []
    small = 0
    for x in (s > 0, s < 0):
        d = domains(x)
        out.append(int((d >= D.MINCOMP).sum()))
        small += int((d < D.MINCOMP).sum())
    return out[0], out[1], small


def walls(s):
    return (s != np.roll(s, -1, -1)).sum((-2, -1)) + (s != np.roll(s, -1, -2)).sum((-2, -1))


def function(V, Ttop, Twalls):
    """intact, defects, islands and wall excess of each sheet in V against its template's (large +, large -) domain
    counts and wall length. defects = |large + - the template's| + |large - - the template's| + islands."""
    s = np.where(V > 0, 1.0, -1.0)
    intact, defects, isl = np.zeros(len(V)), np.zeros(len(V)), np.zeros(len(V))
    for i in range(len(V)):
        p, q, small = topology(s[i])
        intact[i] = float((p, q) == tuple(Ttop[i]))
        defects[i] = abs(p - Ttop[i][0]) + abs(q - Ttop[i][1]) + small
        isl[i] = small
    return intact, defects, isl, walls(s) / Twalls - 1.0


# the run ----------------------------------------------------------------------------------------------------------

def run(body, conds, cases, V0, ema0, R0, th, T, theta, reads, tag=D.TAG, window=D.WINDOW):
    """Advance one body under every condition (teacher x rate x schedule) for `window` updates. Endpoints per read:
    the body's and the first record's agreement with the template, overall and in the current wound; the function
    readouts; the first record's bond error against the taught bonds. Finals V, r, H, W."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(conds)
    idx = np.tile(np.arange(k), nb)
    V, E, r = V0[idx].copy(), ema0[idx].copy(), R0[idx].copy()
    Tb, thb = T[idx], (th * theta)[idx]
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    P = params([c.teacher for c in conds], cases, tag)
    aval = np.where(R0[idx] > 0, 1.0, -1.0)
    two = P["two_idx"]
    B = None
    if len(two):
        B = (H0[two].copy(), W0[two].copy(), D.STRENGTH0 * H0[two], D.STRENGTH0 * W0[two], R0[idx][two].copy())
        xsB, zsB = (Stream(tag, cases, s, "B", side=D.SIDE) for s in ("record-noise", "bond-noise"))
        ctwo = idx[two]
        bpos = {g: i for i, g in enumerate(two)}
    masks = wound_masks(cases, tag)
    events = {}                                    # t -> list of (branch row, mask name, wound number)
    for ci, c in enumerate(conds):
        for n, (tw, which) in enumerate(c.wounds):
            events.setdefault(tw, []).extend((ci * k + j, which, n) for j in range(k))
    current = np.stack([masks[c.wounds[0][1]][j] for c in conds for j in range(k)])   # the wound read as 'patch'
    nbv = {n: np.stack([D.KILL_SD * address(tag, *c.key(), "newborn", n).standard_normal((D.SIDE, D.SIDE))
                        for c in cases]) for n in (0, 1)}
    Ts = np.where(T > 0, 1.0, -1.0)
    Ttop = np.array([topology(Ts[j])[:2] for j in range(k)])[idx]
    Twalls = walls(Ts)[idx]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in D.ENDPOINTS}
    buf = xbuf = zbuf = xbB = zbB = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if B is not None:
                xbB, zbB = xsB.take(D.CHUNK), zsB.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, D.GAIN, alpha, G)
        A, B, _ = relations((H, W, Hb, Wb, r), B, xbuf[i][idx], zbuf[i][idx], None if B is None else xbB[i][ctwo],
                            None if B is None else zbB[i][ctwo], V, P, aval)
        H, W, Hb, Wb, r = A
        if t in reads:
            intact, dfx, isl, wex = function(V, Ttop, Twalls)
            out["sign"].append(S.sign(V, Tb))
            out["r_sign"].append(S.sign(r, Tb))
            out["patch"].append(S.patch(V, Tb, current))
            out["r_patch"].append(S.patch(r, Tb, current))
            out["intact"].append(intact)
            out["defects"].append(dfx)
            out["islands"].append(isl)
            out["walls"].append(wex)
            out["bond_err"].append(bond_err(H, W, H0, W0))
        for row, which, n in events.get(t, ()):
            j = row % k
            m = masks[which][j]
            V[row], E[row] = np.where(m, nbv[n][j], V[row]), np.where(m, nbv[n][j], E[row])
            sh, sw = random_signs(cases[j], n, "A", tag)
            H[row], W[row], Hb[row], Wb[row], r[row] = kill((H[row], W[row], Hb[row], Wb[row], r[row]), m, sh, sw)
            if B is not None and row in bpos:
                q = bpos[row]
                sh, sw = random_signs(cases[j], n, "B", tag)
                st_b = kill(tuple(x[q] for x in B), m, sh, sw)
                for x, y in zip(B, st_b):
                    x[q] = y
            current[row] = m
    res = {key: np.array(v) for key, v in out.items()}
    res.update(V=V, r=r, H=H, W=W)
    return res
