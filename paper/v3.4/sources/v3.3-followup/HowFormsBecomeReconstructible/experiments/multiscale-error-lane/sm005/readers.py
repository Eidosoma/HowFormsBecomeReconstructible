"""SM005's readers on saved final records (r, H, W: (nb x k, side, side), branch-major, float64).

  base   SM001's successor (sm001.sim.successor, stream dw), unchanged: SM003's g 1
  cg     SM002's cg reader (sm003.readers.read_g2 -> sm002.coarse.read_cg, stream dw-cg), unchanged: SM003's g 2
  C/E/B  `reader`: SM002's smoke reader loop (probes/p43s_sm002_smoke.py, sm001.sim.successor's arithmetic with the
         parameters as arguments; at the base parameters it equals sm001.sim.successor bit for bit, a bridge), with the
         gain factor and the bond map; streams the base's (paired)
The variants' parameters are sm005.design.variant(name).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import sim as S
from lr001.sim import halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import Stream, birth, record_step
from sm001 import design as S1D
from sm001 import sim as S1
from sm002 import coarse as C

from . import design as D

ENDS = ("in", "in_gen", "align", "shape", "spacing")


def coarse_bonds(r, H, W):
    """The record's bonds at a 2-site grain: coarse-grained 2 x 2 by SM002's declared rule (a bond the majority of the
    two crossing fine bonds; a tie the coarse record's relation, +1 if 0) and lifted back (bonds inside a block +1,
    across blocks the coarse bond). The values are not touched."""
    rc, Hc, Wc = C.coarse_grain(r, H, W)
    _, Hf, Wf = C.upsample(rc, Hc, Wc)
    return Hf, Wf


def reader(r, H, W, cases, T, m, side, w, gains, tag, coupling, dt, window, gain_x, sigma, eps, kr, sigma_r, bonds,
           stream=D.STREAM):
    """A fresh dw body from newborn noise reading each protected record at gains[branch] x gain_x (the control's 0 stays
    0), with the body's coupling, dt and noise, the record step's eps, kr and sigma_r, and the bond map; the full-grid
    endpoints at the last update and the final body."""
    if bonds == "coarse2":
        H, W = coarse_bonds(r, H, W)
    elif bonds != "fine":
        raise ValueError(bonds)
    k, nb = len(cases), len(gains)
    idx = np.tile(np.arange(k), nb)
    V = birth(tag, cases, "successor", stream, side=side)[idx].copy()
    E = V.copy()
    rr = r.copy()
    thb = np.zeros((nb * k, side, side))                  # SM001's THETA is 0
    gain = np.repeat(np.asarray(gains, float) * gain_x, k)[:, None, None]
    p = replace(NATIVE, sigma=sigma, coupling=coupling, dt=dt)
    st, xs = (Stream(tag, cases, s, stream, side=side) for s in ("successor-future", "successor-record-noise"))
    J = halves(H, W)
    buf = xbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % S1D.CHUNK
        if i == 0:
            buf, xbuf = st.take(S1D.CHUNK), xs.take(S1D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, rr, thb, buf[i][idx], p, gain, 0.0, None)
        rr = record_step(rr, xbuf[i][idx], eps, kr, sigma_r, 0.0, None, J)
    Tb, mb = T[idx], m[idx]
    return {"in": L5S.inside(V, Tb, mb), "in_gen": S1.in_generic(V, Tb, mb, w), "align": S.sign(V, Tb),
            "shape": S.best_shift(V, Tb), "spacing": S.spacing(V), "V": V}


def read_variant(name, r, H, W, cases, T, m, side, w, gains, tag, **over):
    """A variant (C, E or B) at its declared parameters; `over` replaces any of them (the base-setting bridges and the
    calibration)."""
    cfg = dict(D.variant(name, over.pop("g_c", None), over.pop("g_e", None)), **over)
    return reader(r, H, W, cases, T, m, side, w, gains, tag, **cfg)


def read_base(r, H, W, cases, T, m, side, w, gains, tag, reads=S1D.READS2):
    """SM001's successor, unchanged (sm001.sim.successor; stream dw), at every read."""
    return S1.successor(r, H, W, cases, np.zeros_like(T), T, m, side, w, gains, tag=tag, reads=reads)
