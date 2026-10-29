"""cellpop: a vacancy lattice for growing, dying and moving cell populations (SC001 onwards).

A tissue is a fixed-capacity periodic grid whose sites are occupied by cells or empty. Every array is
(branches, side, side); empty sites hold 0 in every field, as DL003 held its inactive cells at 0, so DL001's body step
(dl001.sim.body) and the relational record's step (msegrid.record_step) apply unchanged and are re-masked after each
step. Contacts are the bonds between occupied 4-neighbours: H[i, j] joins (i, j) and (i, j + 1), W[i, j] joins (i, j)
and (i + 1, j) (lr001's convention). A bond with an empty end is 0 and carries no coupling. With every site occupied
and no events, every step here is the original's, bit for bit (tests/test_cellpop.py).

Events, each vectorised over branches and drawn from addressed uniform streams shared by all branches of a case:
  divide  an occupied cell with an empty neighbour divides with probability p per update into one of its empty
          neighbours (uniformly); the daughter copies its parent's body value, moving average and record value
          (inherit) or starts from newborn values with record 0; its contacts form untrained (0, strength 0).
          Conflicts (two parents choosing one site in one update) go to the earlier direction (up, down, left, right).
  die     an occupied, unprotected cell dies with probability p per update: its site empties, its contacts are lost.
  swap    neighbouring unprotected cells exchange places with probability p per update, on disjoint bonds (horizontal
          on even updates, vertical on odd; the pairs' parity alternates every two updates); they carry their body
          value, moving average and record value, and their contacts re-form untrained.
  fill    scheduled division: each site due at update t is filled by a daughter of its neighbour in a declared
          direction (its parent, which must be occupied; otherwise the site stays empty), copying or newborn as in
          divide; used for growth whose margin advances in a declared order.
  diffuse a signal on the contact graph: explicit Laplacian over occupied neighbours, linear decay and a source.
"""
from __future__ import annotations

import numpy as np

from dl001 import sim as S
from lr001.sim import halves
from mse.native import address
from msegrid.core import record_step

OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1))          # up, down, left, right
UP, DOWN, LEFT, RIGHT = range(4)
OPPOSITE = (DOWN, UP, RIGHT, LEFT)
FIELDS = ("V", "E", "r")                               # the per-cell values a cell carries
BONDS = ("H", "W", "Hb", "Wb")


class UStream:
    """Addressed uniforms on [0, 1) for each case, (n, cases, side, side) per call, drawn in sequence."""

    def __init__(self, tag, cases, *stream, side):
        self.gens = [address(tag, *c.key(), *stream) for c in cases]
        self.side = side

    def take(self, n):
        return np.stack([g.random((n, self.side, self.side)) for g in self.gens], 1)


def at(x, d):
    """The value at each site's neighbour in direction d."""
    dy, dx = OFFSETS[d]
    return np.roll(x, (-dy, -dx), (-2, -1))


def push(x, d):
    """Each site's value moved to its neighbour in direction d."""
    dy, dx = OFFSETS[d]
    return np.roll(x, (dy, dx), (-2, -1))


def contacts(occ):
    """The bonds with both ends occupied: (H, right; W, lower)."""
    return occ & at(occ, RIGHT), occ & at(occ, DOWN)


def touching(m):
    """The bonds with at least one end in m: (H, W)."""
    return m | at(m, RIGHT), m | at(m, DOWN)


def has_record(st):
    return st.get("r") is not None


def untrain(st, m):
    """Contacts touching m become untrained: sign 0 and strength 0."""
    if st.get("H") is None:
        return st
    th, tw = touching(m)
    st = dict(st)
    st["H"], st["Hb"] = np.where(th, 0.0, st["H"]), np.where(th, 0.0, st["Hb"])
    st["W"], st["Wb"] = np.where(tw, 0.0, st["W"]), np.where(tw, 0.0, st["Wb"])
    return st


def clear(st, m):
    """Empty the sites under m: values 0, contacts lost."""
    st = dict(st)
    st["occ"] = st["occ"] & ~m
    for f in FIELDS:
        if st.get(f) is not None:
            st[f] = np.where(m, 0.0, st[f])
    return untrain(st, m)


def mask(st):
    """Zero every value at empty sites and every bond with an empty end (a no-op on a full sheet)."""
    st = dict(st)
    occ = st["occ"]
    for f in FIELDS:
        if st.get(f) is not None:
            st[f] = np.where(occ, st[f], 0.0)
    if st.get("H") is not None:
        ch, cw = contacts(occ)
        st["H"], st["Hb"] = np.where(ch, st["H"], 0.0), np.where(ch, st["Hb"], 0.0)
        st["W"], st["Wb"] = np.where(cw, st["W"], 0.0), np.where(cw, st["Wb"], 0.0)
    return st


def divide(st, p, u, w, inherit, newborn=None):
    """One round of division. p: per-branch probability (n, 1, 1); u, w: uniforms (n, side, side); inherit: per-branch
    bool (n, 1, 1); newborn: (n, side, side) values for daughters that do not inherit. Returns the state and the sites
    born this update."""
    occ = st["occ"]
    emp = [~at(occ, d) for d in range(4)]
    n_emp = sum(e.astype(np.int8) for e in emp)
    go = occ & (n_emp > 0) & (u < p)
    k = np.floor(w * n_emp).astype(np.int8)            # which empty neighbour, in direction order
    cum = np.zeros_like(n_emp)
    born = np.zeros_like(occ)
    st = dict(st)
    for d in range(4):
        pick = go & emp[d] & (cum == k)
        cum = cum + emp[d]
        tgt = push(pick, d) & ~occ & ~born
        if not tgt.any():
            continue
        for f in ("V", "E"):
            alt = newborn if newborn is not None else np.zeros_like(st[f])
            st[f] = np.where(tgt, np.where(inherit, push(st[f], d), alt), st[f])
        if has_record(st):
            st["r"] = np.where(tgt, np.where(inherit, push(st["r"], d), 0.0), st["r"])
        born = born | tgt
    st["occ"] = occ | born
    return untrain(st, born), born


def fill(st, due, pdir, inherit, newborn=None):
    """Scheduled division. due: (n, side, side) bool; pdir: (n, side, side) direction from each site to its parent
    (0-3); inherit, newborn as in divide. Returns the state and the sites filled."""
    occ = st["occ"]
    st = dict(st)
    born = np.zeros_like(occ)
    for d in range(4):
        tgt = due & ~occ & (pdir == d) & at(occ, d)
        if not tgt.any():
            continue
        for f in ("V", "E"):
            alt = newborn if newborn is not None else np.zeros_like(st[f])
            st[f] = np.where(tgt, np.where(inherit, at(st[f], d), alt), st[f])
        if has_record(st):
            st["r"] = np.where(tgt, np.where(inherit, at(st["r"], d), 0.0), st["r"])
        born = born | tgt
    st["occ"] = occ | born
    return untrain(st, born), born


def die(st, p, u, protected):
    dead = st["occ"] & ~protected & (u < p)
    return clear(st, dead), dead


def swap(st, p, u, t, protected):
    """Neighbour exchange on disjoint bonds; returns the state and the sites that moved."""
    d = RIGHT if t % 2 == 0 else DOWN
    side = st["occ"].shape[-1]
    par = (np.arange(side) % 2 == (t // 2) % 2)
    lead = np.broadcast_to(par[None, :] if d == RIGHT else par[:, None], st["occ"].shape[-2:])
    free = st["occ"] & ~protected
    a = free & at(free, d) & lead & (u < p)             # the first cell of each exchanging pair
    if not a.any():
        return st, a
    b = push(a, d)
    st = dict(st)
    for f in FIELDS:
        if st.get(f) is not None:
            x = st[f]
            st[f] = np.where(a, at(x, d), np.where(b, at(x, OPPOSITE[d]), x))
    moved = a | b
    return untrain(st, moved), moved


def diffuse(x, occ, kappa, decay, source):
    """One explicit step of a signal on the contact graph; empty sites hold 0."""
    lap = sum(np.where(occ & at(occ, d), at(x, d) - x, 0.0) for d in range(4))
    return np.where(occ, x + kappa * lap - decay * x + source, 0.0)


def decay_length(kappa, decay):
    """The steady decay length of the step above along a straight line of cells: u_x proportional to exp(-x / L)."""
    return 1.0 / np.arccosh(1.0 + decay / (2.0 * kappa))


def body_step(st, rread, th, z, p, gain, alpha, G):
    """dl001.sim.body on the sheet, then empty sites back to 0. Returns the state and the record's pull d."""
    V, E, Vt, drift, d = S.body(st["V"], st["E"], rread, th, z, p, gain, alpha, G)
    st = dict(st)
    st["V"], st["E"] = np.where(st["occ"], V, 0.0), np.where(st["occ"], E, 0.0)
    return st, d


def bond_noise(st, z, cut):
    """LR001's bond-sign noise (z > cut flips H, z < -cut flips W, with their strengths); 0 bonds stay 0."""
    hh, hw = z > cut, z < -cut
    st = dict(st)
    st["H"], st["W"] = np.where(hh, -st["H"], st["H"]), np.where(hw, -st["W"], st["W"])
    st["Hb"], st["Wb"] = np.where(hh, -st["Hb"], st["Hb"]), np.where(hw, -st["Wb"], st["Wb"])
    return st


def record_on(st, xi, eps, kr, sigma_r, kc):
    """msegrid.record_step through the contacts (k_c 0 here), then empty sites back to 0."""
    st = dict(st)
    st["r"] = np.where(st["occ"], record_step(st["r"], xi, eps, kr, sigma_r, kc, None, halves(st["H"], st["W"])), 0.0)
    return st


# relearning the contacts (LR001-LR005's arithmetic, restricted to occupied pairs) -----------------------------------

def targets_record(r, r_star):
    """The record's own co-activity, as lr004.sim.relations computes it for the record sources."""
    return (np.clip(r * np.roll(r, -1, -1) / r_star ** 2, -1, 1), np.clip(r * np.roll(r, -1, -2) / r_star ** 2, -1, 1))


def targets_body(V):
    """The body's co-activity (LR002's teacher)."""
    return np.clip(V * np.roll(V, -1, -1), -1, 1), np.clip(V * np.roll(V, -1, -2), -1, 1)


def learn(st, xh, xw, eta, on):
    """Hebbian relearning toward (xh, xw) on the contacts of branches with `on` (n, 1, 1)."""
    ch, cw = contacts(st["occ"])
    lh, lw = ch & on, cw & on
    st = dict(st)
    Hn, Wn = st["Hb"] + eta * (xh - st["Hb"]), st["Wb"] + eta * (xw - st["Wb"])
    st["Hb"], st["Wb"] = np.where(lh, Hn, st["Hb"]), np.where(lw, Wn, st["Wb"])
    st["H"] = np.where(lh & (st["Hb"] != 0), np.sign(st["Hb"]), st["H"])
    st["W"] = np.where(lw & (st["Wb"] != 0), np.sign(st["Wb"]), st["W"])
    return st


def parity(st, on, repair):
    """LR001's plaquette rule on branches with `on` (a plaquette with a missing bond is never frustrated)."""
    H2, W2 = repair(st["H"], st["W"])
    st = dict(st)
    st["Hb"] = np.where(on & (np.sign(st["Hb"]) * H2 < 0), -st["Hb"], st["Hb"])
    st["Wb"] = np.where(on & (np.sign(st["Wb"]) * W2 < 0), -st["Wb"], st["Wb"])
    st["H"], st["W"] = np.where(on, H2, st["H"]), np.where(on, W2, st["W"])
    return st
