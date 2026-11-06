"""SM003's readers by their grain g: the reader's cell is a g x g block of sites.

  g = 1   SM001's successor (sm001.sim.successor at the full side, u's stream name)
  g = 2   SM002's cg reader (sm002.coarse.read_cg: the declared 2 x 2 rule, read at side / 2, stream dw-cg)
  g = 4   the declared 2 x 2 rule applied twice (the half-scale reader of the half-scale record): read by
          sm001.sim.successor at side / 4 with its own stream name (dw-cg4), the final body lifted x 4 and scored on the
          full grid exactly as u's and cg's are (lr005's inside on the patch and template, sm001's generic recovery over
          every shift of 2w); only where w >= 8 (sm003.design.g_ok)
Every reader reads every branch's record and its paired no-record control (gain 0). Exactness: the 2 x 2 rule returns a
2x upsampled record bit for bit (sm002.coarse), so on a 4x upsampled record the g = 4 reader is the unscaled reader at a
quarter of the side, bit for bit with the same stream name (checked in the tests and Q3).
"""
from __future__ import annotations

import numpy as np

from dl001 import sim as S
from lr005 import sim as L5S
from sm001 import sim as S1
from sm002 import coarse as C

from . import design as D

ENDS = ("in", "in_gen", "align", "shape", "spacing")              # on the full grid, at the reader's last read


def coarse4(r, H, W):
    """The declared 2 x 2 rule twice: (side, side) -> (side / 4, side / 4)."""
    r1, H1, W1 = C.coarse_grain(r, H, W)
    return C.coarse_grain(r1, H1, W1)


def lift4(x):
    return C.lift(C.lift(x))


def read_g4(r, H, W, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2, stream=D.STREAMS[4]):
    """The g = 4 reader on records (r, H, W: (nb x k, side, side), branch-major) of a case set whose templates T and patches
    m are (k, side, side). Returns the full-grid endpoints at the last read (ENDS, each (nb x k,)) and the coarse final
    body."""
    if side % 4 or not D.g_ok(w, 4):
        raise ValueError(f"the g = 4 reader needs side % 4 == 0 and w >= {D.G4_MIN_W} (side {side}, w {w})")
    rc, Hc, Wc = coarse4(r, H, W)
    k, nb = len(cases), len(gains)
    th4 = C.coarse_values(C.coarse_values(th))
    T4 = C.coarse_template(C.coarse_template(T))
    m4 = C.coarse_mask(C.coarse_mask(m))
    o = S1.successor(rc, Hc, Wc, cases, th4, T4, m4, side // 4, w // 4, gains, tag=tag, window=window, reads=(window,),
                     stream=stream)
    idx = np.tile(np.arange(k), nb)
    Vf = lift4(o["V"])
    Tb, mb = T[idx], m[idx]
    return {"in": L5S.inside(Vf, Tb, mb), "in_gen": S1.in_generic(Vf, Tb, mb, w), "align": S.sign(Vf, Tb),
            "shape": S.best_shift(Vf, Tb), "spacing": S.spacing(Vf), "V": o["V"]}


def read_g2(r, H, W, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2):
    """SM002's cg reader (sm002.coarse.read_cg, unchanged), its full-grid endpoints at the last read."""
    o = C.read_cg(r, H, W, cases, th, T, m, side, w, gains, tag=tag, window=window, reads=D.READS2)
    return {e: o[e] for e in ENDS} | {"V": o["Vc"], "ties": o["ties"]}


def read_g1(r, H, W, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2):
    """SM001's successor (sm001.sim.successor, unchanged), its endpoints at the last read."""
    o = S1.successor(r, H, W, cases, th, T, m, side, w, gains, tag=tag, window=window, reads=D.READS2)
    return {e: o[e][-1] for e in ENDS} | {"V": o["V"]}


READ = {1: read_g1, 2: read_g2, 4: read_g4}
