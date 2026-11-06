"""NP001's tissue: LR002's (lr002.sim.relations, lr002.sim.params, dl001.sim.body and dl002.sim.prepare, unchanged and
imported), with a per-branch reading gain (0 for 'alone') and a second stage of fresh successors.

Stage 1 advances one body under every condition as branches (condition-major: index = condition x cases + case), all
reading the case's three noise streams (the body's, the record's and the bonds'), so conditions are paired within a
case. One update, in order, as lr002.sim.run: the body reads the record (dl001.sim.body, gain per branch); bond noise;
the record's step through its bonds; Hebbian relearning (from the record or the body); parity. With every branch at
gain 0.2 a run equals lr002.sim.run bit for bit (checks Q3).

Stage 2 hands each stage-1 record (r and its bonds H, W) to a fresh body of a given kind, born from newborn noise, which
reads it at gain 0.2 with the record protected (no bond noise, no relearning, no parity: the record steps through its
bonds only); one more branch is the same newborn body reading nothing (gain 0), the paired control. Every branch of a
successor body shares its birth and its noise, so successor contrasts isolate what each record carries.

A phase conflict (C4sK) starts the body from S4's acquisition (phase 0) and the record from S4sK's (phase K). Every
read scores against T (the record's history: phase K) and against T0 (the body's initial pattern: phase 0); for every
other unit T0 = T, so align_b = align.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from dl002 import design as D2
from dl002 import sim as S2
from lr001.sim import bond_err, edges_from
from lr002 import sim as L2S
from mse.assay import enrol
from mse.native import NATIVE
from msegrid.core import Stream, acquire, birth, bonds

from . import design as D

ENDS1 = ("align", "r_align", "shape", "r_shape", "spacing", "agree", "bond_err", "align_b", "r_align_b")
ENDS2 = ("align", "r_align", "shape", "spacing", "agree", "align_b")


def template(pattern, kind, block):
    """+-1 pattern of one message. S4sX: DL001's S4 (period 8, stripes 4 thick) rolled X sites across its stripes
    (columns for kinds 0 and 2, rows for kinds 1 and 3); everything else is DL002's template, unchanged."""
    s = D.shift_of(pattern)
    if pattern[:3] in ("S4s", "C4s"):
        f = S.template("S4", kind, D.SIDE, block)
        return np.roll(f, s, axis=-1 if kind % 2 == 0 else -2)
    return S2.template(pattern, kind, block)


def prepare(pattern, block, purpose):
    """DL002's preparation for S4, S8 and F0 (dl002.sim.prepare, unchanged); for S4sX the same acquisition (DL002's
    tag, birth, settle, teach and release noise) teaching the shifted template; for C4sK the body, moving average and
    theta of S4's acquisition with the record and template (the history) of S4sK's."""
    if D.is_conflict(pattern):
        cases, V0, ema0, _, th, _ = S2.prepare("S4", block, purpose)
        _, _, _, R0, _, T = prepare(f"S4s{D.shift_of(pattern)}", block, purpose)
        return cases, V0, ema0, R0, th, T
    if not pattern.startswith("S4s"):
        return S2.prepare(pattern, block, purpose)
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, purpose)
    T = np.stack([D2.AMPLITUDE * template(pattern, c.message, block) for c in cases])
    V, ema, R0, th = acquire(D2.TAG, cases, T, replace(NATIVE, sigma=D2.SIGMA_ACQ), D2.SIDE,
                             settle=D2.SETTLE, teach=D2.TEACH, release=D2.RELEASE)
    return cases, V, ema, R0, th, T


def initial(pattern, cases, block):
    """T0: the body's initial template (S4's, phase 0, for a conflict; else the unit's own)."""
    unit = "S4" if D.is_conflict(pattern) else pattern
    return np.stack([D2.AMPLITUDE * template(unit, c.message, block) for c in cases])


def _read1(out, V, r, H, W, H0, W0, Tb, Tb0):
    out["align_b"].append(S.sign(V, Tb0))
    out["r_align_b"].append(S.sign(r, Tb0))
    out["align"].append(S.sign(V, Tb))
    out["r_align"].append(S.sign(r, Tb))
    out["shape"].append(S.best_shift(V, Tb))
    out["r_shape"].append(S.best_shift(r, Tb))
    out["spacing"].append(S.spacing(V))
    out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
    out["bond_err"].append(bond_err(H, W, H0, W0))


def stage1(body, conds, cases, V0, ema0, R0, th, T, reads, tag=D.TAG, window=D.WINDOW, theta=D.THETA, T0=None):
    """Advance one body under every condition for `window` updates from the acquired state."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(conds)
    idx = np.tile(np.arange(k), nb)
    V, E, r = V0[idx].copy(), ema0[idx].copy(), R0[idx].copy()
    Tb, thb = T[idx], (th * theta)[idx]
    Tb0 = Tb if T0 is None else T0[idx]
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    P = L2S.params(conds, k)
    gain = np.repeat([c.gain for c in conds], k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ENDS1}
    buf = xbuf = zbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        H, W, Hb, Wb, r = L2S.relations(H, W, Hb, Wb, r, xbuf[i][idx], zbuf[i][idx], V, P, D.KC, None)
        if t in reads:
            _read1(out, V, r, H, W, H0, W0, Tb, Tb0)
    res = {key: np.array(v) for key, v in out.items()}
    res.update(V=V, r=r, H=H, W=W)
    return res


class _Protected:
    """A condition with no bond noise, no relearning and no parity: the record steps through its bonds only."""
    rate, learn, parity = 0.0, "", False


def successor(body, r, H, W, cases, th, T, reads, gains, tag=D.TAG, window=D.WINDOW2, theta=D.THETA, T0=None):
    """A fresh body of kind `body`, born from newborn noise, reading each record (r, H, W: (nb x k, side, side),
    branch-major) at gains[branch] (0 for the no-record control), the record protected. All branches of a case share
    the birth and the noise."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(gains)
    idx = np.tile(np.arange(k), nb)
    V = birth(tag, cases, "successor", body, side=D.SIDE)[idx].copy()
    E = V.copy()
    r, H, W = r.copy(), H.copy(), W.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    Tb, thb = T[idx], (th * theta)[idx]
    Tb0 = Tb if T0 is None else T0[idx]
    P = L2S.params([_Protected()] * nb, k)
    gain = np.repeat(np.asarray(gains, float), k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs = (Stream(tag, cases, s, body, side=D.SIDE) for s in ("successor-future", "successor-record-noise"))
    zero = np.zeros_like(V)
    out = {key: [] for key in ENDS2}
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        H, W, Hb, Wb, r = L2S.relations(H, W, Hb, Wb, r, xbuf[i][idx], zero, V, P, D.KC, None)
        if t in reads:
            out["align"].append(S.sign(V, Tb))
            out["r_align"].append(S.sign(r, Tb))
            out["shape"].append(S.best_shift(V, Tb))
            out["spacing"].append(S.spacing(V))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
            out["align_b"].append(S.sign(V, Tb0))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(V=V)
    return res
