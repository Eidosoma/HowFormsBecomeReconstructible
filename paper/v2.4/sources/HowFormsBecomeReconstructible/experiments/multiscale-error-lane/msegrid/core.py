"""Side-agnostic primitives. Every array is (..., side, side); the side is read from the array or passed.

Equal to the originals at side 16, bit for bit:
    bproj                 mse.ops.block_projection
    Stream / draws        mse.assay.Noise chunks, br001.sim.draws
    birth, theta          mse.assay.birth, mse.assay.theta (per tissue)
    acquire               br001.sim.prepare's birth, settle, teach and release (mse.engine.run on the site routes)
    record_step           br002.sim.simulate's record step with writing off
    bonds, bond_sum, kill_bonds   br002.sim
    family(F0)            me002.families.templates('F0'); S8 at side 16 equals F0
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from mse.assay import BIRTH_SCALE, spread
from mse.native import NATIVE, address, center, moving_average, neighbours, sheet

SHIFTS = ((1, -2), (-1, -2), (1, -1), (-1, -1))       # the four neighbours, in mse.native.neighbours' order
R_STAR = 1.2


def bproj(x, size):
    """Block means of size x size blocks, broadcast back to sites."""
    if size == 1:
        return x
    n = x.shape[-1] // size
    means = x.reshape(*x.shape[:-2], n, size, n, size).mean(axis=(-3, -1))
    return np.repeat(np.repeat(means, size, axis=-2), size, axis=-1)


class Stream:
    """Addressed standard normals for each case, (n, cases, side, side) per call, drawn in sequence."""

    def __init__(self, tag, cases, *stream, side):
        self.gens = [address(tag, *c.key(), *stream) for c in cases]
        self.side = side

    def take(self, n):
        return np.stack([g.standard_normal((n, self.side, self.side)) for g in self.gens], 1)


def draws(tag, cases, *stream, updates, side):
    return Stream(tag, cases, *stream, side=side).take(updates)


def birth(tag, cases, *stream, side):
    return np.stack([BIRTH_SCALE * center(address(tag, *c.key(), *stream).standard_normal((side, side))) for c in cases])


def theta(tag, cases, p, side):
    """The block's environmental field with the per-tissue spread (mse.assay.theta, per_tissue=True)."""
    def field(b):
        q = replace(p, threshold_spread=spread(tag, b))
        return q.threshold_spread * address(tag, "theta", b).standard_normal((side, side))
    fields = {b: field(b) for b in {c.block for c in cases}}
    return np.stack([fields[c.block] for c in cases])


def _step(V, ema, R, th, z, p, track):
    """mse.engine.step on the site routes: the body reads R - V-tilde (centred); with track, R follows V at rho."""
    Vt = sheet(V, th, z, p)
    ema = moving_average(ema, Vt, p)
    sensed = R - Vt
    drift = p.gain * sensed
    drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    V = np.clip(Vt + p.dt * drift, -p.bound, p.bound)
    if track:
        R = R - p.rho * (R - V)
    return V, ema, R


def acquire(tag, cases, T, p, side, settle=120, teach=1000, release=200, chunk=100):
    """BR001's acquisition at any side: birth; settle and teach on the reciprocal route without capture (the
    record tracks the body at rho; teaching overwrites the body with T before every step); release on the body
    route (record held). Noise drawn in chunks of `chunk` per phase, as mse.assay.Noise."""
    th = theta(tag, cases, p, side)
    V = birth(tag, cases, "birth", side=side)
    ema, R = V.copy(), V.copy()
    for phase, n, track, imposed in (("settle", settle, True, None), ("teach", teach, True, T), ("release", release, False, None)):
        st = Stream(tag, cases, phase, side=side)
        buf = None
        for t in range(1, n + 1):
            i = (t - 1) % chunk
            if i == 0:
                buf = st.take(chunk)
            if imposed is not None:
                V = np.broadcast_to(imposed, V.shape).copy()
            V, ema, R = _step(V, ema, R, th, buf[i], p, track)
    return V, ema, R, th


def bonds(R0, rel):
    if not rel:
        return [np.ones_like(R0) for _ in SHIFTS]
    s = np.where(R0 >= 0, 1.0, -1.0)
    return [s * np.roll(s, sh, ax) for sh, ax in SHIFTS]


def kill_bonds(J, kill, relink):
    return [np.where(kill & np.roll(kill, sh, ax), 1.0 if relink else 0.0, J[d]) for d, (sh, ax) in enumerate(SHIFTS)]


def bond_sum(J, r):
    return (J[0] * np.roll(r, 1, -2) + J[1] * np.roll(r, -1, -2) + J[2] * np.roll(r, 1, -1) + J[3] * np.roll(r, -1, -1)) / 4.0


def record_step(r, xi, eps, kr, sigma_r, kc, B, J):
    """BR002's record step with writing off, in its order: self-correction through the bonds, code, clip."""
    r_old = r
    if eps > 0:
        r = r + eps * (r * (1 - (r / R_STAR) ** 2) + kr * (bond_sum(J, r) - r)) + sigma_r * xi
    if kc > 0:
        r = r + kc * (B - bproj(r, 4))
    return np.clip(r, -2.0, 2.0) if r is not r_old else r


# Pattern families at any side -------------------------------------------------------------------------------

def _smooth(z, sd):
    side = z.shape[-1]
    k = np.fft.fftfreq(side) * 2 * np.pi
    kx, ky = np.meshgrid(k, k, indexing="ij")
    return np.real(np.fft.ifft2(np.fft.fft2(z) * np.exp(-0.5 * sd ** 2 * (kx ** 2 + ky ** 2))))


def _balanced(x):
    side = x.shape[-1]
    order = np.argsort(x.ravel(), kind="stable")
    out = np.full(side * side, -1.0)
    out[order[side * side // 2:]] = 1.0
    return out.reshape(side, side)


def blobs(tag, block, side, sd=2.0, overlap=0.05):
    """Two balanced blob patterns (me002.families.blobs' recipe) drawn fresh for one block at one side."""
    draw = lambda j: _balanced(_smooth(address(tag, "family", "BL", block, side, j).standard_normal((side, side)), sd))
    b0, j = draw(0), 1
    while abs((b0 * draw(j)).mean()) > overlap:
        j += 1
    return b0, draw(j)


def base(family, kind, side, tag=None, block=None):
    """+-1 pattern of one message. F0: half-planes (domains side/2 thick); S8: stripes 8 thick; BL: fresh blobs
    with 2-site smoothing; BLx2 / BLx4: blobs drawn at side/2 or side/4 and repeated in 2 x 2 or 4 x 4 blocks."""
    if family in ("F0", "S8"):
        if family == "F0":
            f = np.full((side, side), -1.0)
            f[:, : side // 2] = 1.0
        else:
            f = np.tile(np.where((np.arange(side) // 8) % 2 == 0, 1.0, -1.0), (side, 1))
        if kind % 2 == 1:
            f = f.T.copy()
        return f if kind < 2 else -f
    scale = int(family[3:]) if family.startswith("BLx") else 1
    b0, b1 = blobs(tag, block, side // scale)
    f = b0 if kind % 2 == 0 else b1
    if scale > 1:
        f = np.repeat(np.repeat(f, scale, axis=0), scale, axis=1)
    return f if kind < 2 else -f


def wall_axis(family, kind):
    """For F0 and S8: the axis along which the sign changes (1 = across columns for kinds 0 and 2)."""
    return 1 if kind % 2 == 0 else 0


def domain(family, side):
    return side // 2 if family == "F0" else 8


def place_mask(family, kind, side, size, place, g):
    """A size x size patch: 'random' (uniform corner), 'dK' (inside one domain at distance K from its nearest
    wall), 'mid' (centred in its domain) or 'cross' (straddling a wall symmetrically). g: the case's generator."""
    m = np.zeros((side, side), bool)
    if place == "random":
        a, b = g.integers(0, side, 2)
        m[np.ix_(np.arange(a, a + size) % side, np.arange(b, b + size) % side)] = True
        return m
    D = domain(family, side)
    walls = side // D                                       # number of domains along the axis
    along = int(g.integers(0, side))
    if place == "cross":
        a = (D * (int(g.integers(0, walls)) + 1) - size // 2) % side
    else:
        d = (D - size) // 2 if place == "mid" else int(place[1:])
        dom, s_ = int(g.integers(0, walls)), int(g.integers(0, 2))
        a = dom * D + (d if s_ == 0 else D - size - d)
    ia, ib = np.arange(a, a + size) % side, np.arange(along, along + size) % side
    if wall_axis(family, kind) == 1:
        m[np.ix_(ib, ia)] = True
    else:
        m[np.ix_(ia, ib)] = True
    return m


def wall_distance(T, m, family, kind):
    """For F0 and S8 patches: -1 if the patch straddles a wall, else the distance from the patch to the nearest wall."""
    inside = T[m]
    if (inside > 0).any() and (inside < 0).any():
        return -1
    side = T.shape[-1]
    D = domain(family, side)
    rows, cols = np.where(m)
    across = cols if wall_axis(family, kind) == 1 else rows
    return int(min(min(x % D, D - 1 - x % D) for x in across))
