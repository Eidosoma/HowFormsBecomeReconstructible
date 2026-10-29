"""Shared helpers for the model-limits study. ENGINEERING_PROBE_NOT_EVIDENCE.

Side-agnostic restatements of the lane's body and record steps (mse/native.py, br001/sim.py), so that the
same arithmetic can run on sheets larger than 16 x 16. At side 16 they are meant to reproduce the lane's
functions bit for bit; t1_geometry.py checks that against br001.sim.simulate before using them.

Own tag 'mse-expansion'; engineering blocks 900832-900847 only (mse.assay.enrol enforces the range).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

LANE = Path("/e/project1/e-aif-2026pg01-1345/Research/HowFormsBecomeReconstructible/experiments/multiscale-error-lane")
OUT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/expansion")
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from mse.native import NATIVE, address, center, moving_average, neighbours, sheet  # noqa: E402

TAG = "mse-expansion"
BLOCKS = tuple(range(900832, 900848))
STATUS = "ENGINEERING_PROBE_NOT_EVIDENCE"
R_STAR = 1.2


def bproj(x, size):
    """Block projection for any side divisible by size (mse.ops.block_projection at side 16)."""
    if size == 1:
        return x
    side = x.shape[-1]
    n = side // size
    means = x.reshape(*x.shape[:-2], n, size, n, size).mean(axis=(-3, -1))
    return np.repeat(np.repeat(means, size, axis=-2), size, axis=-1)


def body_step(V, ema, r, th, z, p, conserved, gain):
    """br001.sim.body_step restated (side-agnostic already; kept here to vary it in later tests)."""
    if conserved:
        Vt = sheet(V, th, z, p)
    else:
        drift = V - V ** 3 + p.well_asym + th + p.coupling * (neighbours(V) - V)
        Vt = np.clip(V + p.dt * drift + p.sigma * z, -p.bound, p.bound)
    ema = moving_average(ema, Vt, p)
    drift = gain * (r - Vt)
    if conserved:
        drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    return np.clip(Vt + p.dt * drift, -p.bound, p.bound), ema, Vt


def record_step(r, xi, eps, kr, sigma_r, kc, B):
    """BR001's record step for panel L arms (no writing, no clamp), in br001.sim.simulate's order."""
    r_old = r
    if eps > 0:
        r = r + eps * (r * (1 - (r / R_STAR) ** 2) + kr * (neighbours(r) - r)) + sigma_r * xi
    if kc > 0:
        r = r + kc * (B - bproj(r, 4))
    return np.clip(r, -2.0, 2.0) if r is not r_old else r


def half_plane0(side, amplitude=1.0):
    """F0 kind 0 at any side: columns [0, side/2) positive, the rest negative (walls at side/2-1|side/2 and side-1|0)."""
    f = np.full((side, side), -1.0)
    f[:, : side // 2] = 1.0
    return amplitude * f


def smooth(z, sd):
    side = z.shape[-1]
    k = np.fft.fftfreq(side) * 2 * np.pi
    kx, ky = np.meshgrid(k, k, indexing="ij")
    return np.real(np.fft.ifft2(np.fft.fft2(z) * np.exp(-0.5 * sd ** 2 * (kx ** 2 + ky ** 2))))


def balanced_blob(g, side=16, sd=2.0):
    """A BL-like pattern: smoothed white noise thresholded at the median (me002.families.blobs' recipe)."""
    x = smooth(g.standard_normal((side, side)), sd)
    order = np.argsort(x.ravel(), kind="stable")
    out = np.full(side * side, -1.0)
    out[order[side * side // 2:]] = 1.0
    return out.reshape(side, side)


def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save(name, obj):
    obj = {"status": STATUS, "tag": TAG, "finished_utc": stamp(), **obj}
    path = OUT / name
    path.write_text(json.dumps(obj, indent=1, default=float) + "\n")
    return path
