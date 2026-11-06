"""The half-scale reader seen at twice the grain (SM002's cg reader).

A 2 x 2 block of sites is the coarse reader's cell. The record is coarse-grained by one declared rule:
  value   r_c(I) = ((r00 + r01) + (r10 + r11)) / 4, the block's mean (summed in pairs, so that four equal values give
          that value exactly)
  bonds   a coarse bond is the majority of the two fine bonds crossing the coarse edge (H between columns 2j+1 and
          2j+2 in rows 2i and 2i+1; W between rows 2i+1 and 2i+2 in columns 2j and 2j+1); a tie (one +1, one -1) takes
          the coarse record's own relation sign(r_c(I) r_c(J)), and +1 where that is 0
then read by sm001.sim.successor, unchanged, on the half-side lattice: the same body, parameters, gain, window, reads,
record step and protection, with its birth and noise drawn from its own stream name. The final body is lifted back
(each coarse cell to its 4 sites) and scored on the full grid exactly as the unscaled reader's is (lr005's inside on the
patch and template, sm001's generic recovery over every shift of 2w, dl001's sign, best shift and spacing).

Exactness: coarse-graining a 2x upsampled record (upsample) returns it bit for bit (block means of equal values; the two
crossing bonds equal, so no tie), so on an upsampled record the cg reader at side 2s is the unscaled reader at side s,
bit for bit with the same stream name, and the lifted score over an upsampled patch equals the unlifted score.
"""
from __future__ import annotations

import numpy as np

from dl001 import sim as S
from lr005 import sim as L5S
from sm001 import sim as S1

from . import design as D

ENDS_CG = ("in", "in_gen", "align", "shape", "spacing")          # on the full grid, at the last read
ENDS_C = S1.ENDS2                                                  # on the coarse grid, at every read (reported)


def coarse_values(x):
    """(..., 2s, 2s) -> (..., s, s): the block mean, in pairs."""
    a, b = x[..., 0::2, 0::2], x[..., 0::2, 1::2]
    c, d = x[..., 1::2, 0::2], x[..., 1::2, 1::2]
    return ((a + b) + (c + d)) * 0.25


def coarse_bonds(H, W, rc):
    """The coarse bonds from the fine ones (H[y, x] relates (y, x) and (y, x + 1); W[y, x] relates (y, x) and (y + 1, x)):
    the majority of the two crossing bonds, a tie taking the coarse record's relation (+1 where that is 0)."""
    hs = H[..., 0::2, 1::2] + H[..., 1::2, 1::2]
    ws = W[..., 1::2, 0::2] + W[..., 1::2, 1::2]
    rh = np.sign(rc * np.roll(rc, -1, -1))
    rw = np.sign(rc * np.roll(rc, -1, -2))
    Hc = np.where(hs != 0, np.sign(hs), np.where(rh != 0, rh, 1.0))
    Wc = np.where(ws != 0, np.sign(ws), np.where(rw != 0, rw, 1.0))
    return Hc.astype(float), Wc.astype(float)


def coarse_grain(r, H, W):
    rc = coarse_values(r)
    Hc, Wc = coarse_bonds(H, W, rc)
    return rc, Hc, Wc


def ties(H, W):
    """The number of tied coarse edges (reported)."""
    hs = H[..., 0::2, 1::2] + H[..., 1::2, 1::2]
    ws = W[..., 1::2, 0::2] + W[..., 1::2, 1::2]
    return (hs == 0).sum((-2, -1)) + (ws == 0).sum((-2, -1))


def coarse_mask(m):
    """A coarse cell is in the coarse patch if any of its sites is (the coarse endpoints only; reported)."""
    return m[..., 0::2, 0::2] | m[..., 0::2, 1::2] | m[..., 1::2, 0::2] | m[..., 1::2, 1::2]


def coarse_template(T):
    """The template at each block's first site (exact for walls at even positions, as every SM002 template's)."""
    return T[..., 0::2, 0::2].copy()


def lift(x):
    return np.repeat(np.repeat(x, 2, -2), 2, -1)


def upsample(r, H, W):
    """A record at side s -> its 2x upsampled record at side 2s: each site to a 2 x 2 block of its value, the bonds inside
    a block +1, the bonds between blocks the coarse bond (for the checks)."""
    rf = lift(r)
    Hf, Wf = np.ones_like(rf), np.ones_like(rf)
    Hf[..., :, 1::2] = np.repeat(H, 2, -2)
    Wf[..., 1::2, :] = np.repeat(W, 2, -1)
    return rf, Hf, Wf


def read_cg(r, H, W, cases, th, T, m, side, w, gains, tag=D.TAG, window=D.WINDOW2, reads=D.READS2, stream=D.CG_STREAM):
    """The cg reader on records (r, H, W: (nb x k, side, side), branch-major) of a case set whose templates T and patches
    m are (k, side, side): coarse-grain, read with sm001.sim.successor at side / 2 (its stream name `stream`), lift the
    final body back and score it on the full grid. Returns the full-grid endpoints at the last read (ENDS_CG, each
    (nb x k,)), the coarse endpoints at every read ('c/' + ENDS_C), the coarse final body and the ties."""
    if side % 2 or w % 2:
        raise ValueError("the cg reader needs an even side and an even width")
    rc, Hc, Wc = coarse_grain(r, H, W)
    k, nb = len(cases), len(gains)
    o = S1.successor(rc, Hc, Wc, cases, coarse_values(th), coarse_template(T), coarse_mask(m), side // 2, w // 2, gains,
                     tag=tag, window=window, reads=reads, stream=stream)
    idx = np.tile(np.arange(k), nb)
    Vf = lift(o["V"])
    Tb, mb = T[idx], m[idx]
    out = {"in": L5S.inside(Vf, Tb, mb), "in_gen": S1.in_generic(Vf, Tb, mb, w), "align": S.sign(Vf, Tb),
           "shape": S.best_shift(Vf, Tb), "spacing": S.spacing(Vf)}
    out.update({f"c/{e}": o[e] for e in ENDS_C})
    out.update(Vc=o["V"], ties=ties(H, W))
    return out
