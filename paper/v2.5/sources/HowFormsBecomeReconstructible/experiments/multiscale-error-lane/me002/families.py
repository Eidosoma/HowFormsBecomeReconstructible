"""Target families: four messages each (kinds 0 and 1, and their sign reversals 2 and 3).

F0/F2/F4 are ME001's half-planes rolled by 0, 2 or 4 sites. The new families are untouched by
ME001 and by the pooled threshold calibration:
  S4  stripes of width 4 (vertical, horizontal): 100% regional band, four flat walls
  IS  half-planes carrying one 4 x 4 island of the opposite sign in each half (off the pooling
      grid): curved walls the native curvature flow would shrink
  BL  two smoothed random fields (periodic Gaussian, sd 2 sites) thresholded at the median,
      the second drawn until |overlap| <= 0.05: multi-scale content, curved walls
Every template is balanced (128 sites of each sign) and scaled by the teaching amplitude.
"""
from __future__ import annotations

import numpy as np

from mse.native import SIDE, address, half_plane

BLOB_SMOOTHING = 2.0
BLOB_OVERLAP = 0.05


def _smooth(z, sd):
    k = np.fft.fftfreq(SIDE) * 2 * np.pi
    kx, ky = np.meshgrid(k, k, indexing="ij")
    return np.real(np.fft.ifft2(np.fft.fft2(z) * np.exp(-0.5 * sd ** 2 * (kx ** 2 + ky ** 2))))


def _balanced(x):
    order = np.argsort(x.ravel(), kind="stable")
    out = np.full(SIDE * SIDE, -1.0)
    out[order[SIDE * SIDE // 2:]] = 1.0
    return out.reshape(SIDE, SIDE)


def blobs(tag):
    """The two BL base patterns and the address index used for the second."""
    draw = lambda j: _balanced(_smooth(address(tag, "family", "BL", j).standard_normal((SIDE, SIDE)), BLOB_SMOOTHING))
    b0, j = draw(0), 1
    while abs((b0 * draw(j)).mean()) > BLOB_OVERLAP:
        j += 1
    return b0, draw(j), j


def _base(family, kind, tag):
    if family in ("F0", "F2", "F4"):
        k = int(family[1])
        return np.roll(half_plane(kind, 1.0), (k, k), axis=(0, 1))
    if family == "S4":
        x = np.where((np.arange(SIDE) // 4) % 2 == 0, 1.0, -1.0)
        f = np.tile(x, (SIDE, 1))
    elif family == "IS":
        f = half_plane(0, 1.0)
        f[6:10, 2:6] = -1.0
        f[6:10, 10:14] = 1.0
    elif family == "BL":
        b0, b1, _ = blobs(tag)
        f = b0 if kind % 2 == 0 else b1
        return f if kind < 2 else -f
    else:
        raise ValueError(f"Unknown family: {family}")
    if kind % 2 == 1:
        f = f.T.copy()
    return f if kind < 2 else -f


def templates(family, tag, amplitude):
    """(4, 16, 16): the family's four messages at the teaching amplitude."""
    return np.stack([amplitude * _base(family, k, tag) for k in range(4)])
