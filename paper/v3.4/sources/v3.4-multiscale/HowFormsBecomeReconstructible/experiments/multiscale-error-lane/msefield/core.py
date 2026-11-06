"""msefield: a shared diffusible medium for a group of tissue sheets (built for SM007; imported by E2E006).

The field c lives on a grid of sites of side h = 1/m in units of the sheet spacing a (a = 1). Each sheet occupies one cell
of a square lattice of spacing 1, i.e. an m x m block of sites; the domain is the union of the occupied blocks, widened
by `margin` sites of medium on every side. Inside the domain

    dc/dt = D lap(c) - gamma c + sigma(x, t),

with lap the 5-point Laplacian over the domain's sites (divided by h^2) and sigma the emission density: a sheet with total
emission rate e (amount per unit time) spreads it uniformly over its block, sigma = e / a^2 = e there. So with a uniform
density sigma everywhere and a sealed boundary the steady state is sigma / gamma, and the decay length is
lambda = sqrt(D / gamma), in spacings.

The boundary at the domain's perimeter (every face between a domain site and a site outside it) is declared by `leak` in
[0, 1]: the ghost value outside the face is (1 - leak) c of the site inside.
    leak = 0   sealed: zero flux (Neumann);
    leak = 1   absorbing: c = 0 just outside (Dirichlet; the surrounding medium holds the field at zero);
    between    a partly permeable boundary (a discrete Robin condition).

Time: one call of step() advances one tissue update, dt (default 1), by forward Euler in `nsub` equal substeps, nsub the
least integer with D (dt / nsub) / h^2 <= 0.2 (the 2D explicit bound is 0.25) and gamma dt / nsub <= 0.5. A sheet's
exposure is the mean of c over its block (sample()). steady_state() solves the linear steady state directly (a sparse LU),
the reference the qualification (tests/test_msefield.py, probes/p61q) compares the stepper with.

Positions are integer lattice cells (row, col), one per sheet; any footprint is allowed (rectangles, lines, L-shapes).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as splinalg

SAFE_DIFF = 0.2          # D dt_sub / h^2 per substep (2D explicit stability needs <= 0.25)
SAFE_DECAY = 0.5         # gamma dt_sub per substep


class Medium:
    """A shared medium over sheets at lattice `positions` [(row, col), ...]."""

    def __init__(self, positions, D, gamma, leak, dt=1.0, m=4, margin=0):
        if not 0.0 <= leak <= 1.0:
            raise ValueError("leak must lie in [0, 1]")
        if D < 0 or gamma < 0 or m < 1 or margin < 0:
            raise ValueError("D, gamma >= 0; m >= 1; margin >= 0")
        pos = np.asarray(positions, dtype=np.int64).reshape(-1, 2)
        if len({tuple(p) for p in pos}) != len(pos):
            raise ValueError("two sheets at one lattice cell")
        self.D, self.gamma, self.leak, self.dt, self.m, self.margin = float(D), float(gamma), float(leak), float(dt), int(m), int(margin)
        self.h = 1.0 / self.m
        self.n_sheets = len(pos)
        r0, c0 = pos.min(0)
        self.pos = pos - np.array([r0, c0])
        R, C = self.pos.max(0) + 1
        g = self.margin
        self.shape = (int(R) * self.m + 2 * g, int(C) * self.m + 2 * g)
        dom = np.zeros(self.shape, bool)
        self.blocks = []
        for (r, c) in self.pos:
            sl = (slice(g + r * self.m, g + (r + 1) * self.m), slice(g + c * self.m, g + (c + 1) * self.m))
            self.blocks.append(sl)
            dom[sl] = True
        if g:
            # the margin: every site within g sites (Chebyshev) of an occupied block is medium too
            grown = dom.copy()
            for dr in range(-g, g + 1):
                for dc in range(-g, g + 1):
                    grown |= _shift(dom, dr, dc)
            dom = grown
        self.domain = dom
        # neighbour structure: for each of the 4 directions, whether the neighbour is inside the domain
        self._inside = [_shift(dom, dr, dc) & dom for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        self._faces_out = sum((~ins) & dom for ins in self._inside).astype(float)     # boundary faces per site
        self.c = np.zeros(self.shape)
        self.nsub = max(1, math.ceil(self.D * self.dt / (self.h * self.h) / SAFE_DIFF),
                        math.ceil(self.gamma * self.dt / SAFE_DECAY))
        self.dts = self.dt / self.nsub
        self._sig = np.zeros(self.shape)
        self._A = None

    # ------------------------------------------------------------------ the operator
    def lap(self, c):
        """The 5-point Laplacian over the domain with the declared boundary (per h^2); 0 outside the domain."""
        out = np.zeros_like(c)
        for (dr, dc), ins in zip(((1, 0), (-1, 0), (0, 1), (0, -1)), self._inside):
            nb = _shift_vals(c, dr, dc)
            out += np.where(ins, nb - c, 0.0)
        # a boundary face's ghost is (1 - leak) c: its contribution is ((1 - leak) c - c) = -leak c
        out -= self.leak * self._faces_out * c
        return np.where(self.domain, out, 0.0) / (self.h * self.h)

    def density(self, emissions):
        """The emission density sigma on the sites: each sheet's rate spread uniformly over its block."""
        e = np.asarray(emissions, dtype=float).reshape(self.n_sheets)
        sig = np.zeros(self.shape)
        for k, sl in enumerate(self.blocks):
            sig[sl] = e[k]
        return sig

    # ------------------------------------------------------------------ time stepping and sampling
    def step(self, emissions):
        """Advance one tissue update with the sheets' emission rates (N,); returns the exposures after the step."""
        sig = self.density(emissions)
        c = self.c
        for _ in range(self.nsub):
            c = c + self.dts * (self.D * self.lap(c) - self.gamma * c + sig)
        self.c = np.where(self.domain, c, 0.0)
        return self.sample()

    def sample(self, c=None):
        """Each sheet's exposure: the mean of c over its block (N,)."""
        c = self.c if c is None else c
        return np.array([c[sl].mean() for sl in self.blocks])

    def mass(self, c=None):
        c = self.c if c is None else c
        return float(c[self.domain].sum() * self.h * self.h)

    def reset(self, value=0.0):
        self.c = np.where(self.domain, float(value), 0.0)

    # ------------------------------------------------------------------ the steady state, directly
    def _operator(self):
        if self._A is None:
            idx = -np.ones(self.shape, np.int64)
            sites = np.argwhere(self.domain)
            idx[tuple(sites.T)] = np.arange(len(sites))
            rows, cols, vals = [], [], []
            inv_h2 = 1.0 / (self.h * self.h)
            for (dr, dc), ins in zip(((1, 0), (-1, 0), (0, 1), (0, -1)), self._inside):
                nb_idx = _shift_vals(idx.astype(float), dr, dc).astype(np.int64)
                sel = ins[tuple(sites.T)]
                i = np.arange(len(sites))[sel]
                j = nb_idx[tuple(sites[sel].T)]
                rows += [i, i]
                cols += [j, i]
                vals += [np.full(len(i), self.D * inv_h2), np.full(len(i), -self.D * inv_h2)]
            diag = -self.gamma - self.D * inv_h2 * self.leak * self._faces_out[tuple(sites.T)]
            rows.append(np.arange(len(sites)))
            cols.append(np.arange(len(sites)))
            vals.append(diag)
            A = sparse.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                                  shape=(len(sites), len(sites)))
            self._A, self._sites = A, sites
        return self._A, self._sites

    def steady_state(self, emissions):
        """The steady-state field for constant emission rates (the domain's sites; 0 outside)."""
        A, sites = self._operator()
        sig = self.density(emissions)[tuple(sites.T)]
        if self.gamma == 0 and self.leak == 0:
            raise ValueError("no steady state without decay or leakage")
        x = splinalg.spsolve(A, -sig)
        c = np.zeros(self.shape)
        c[tuple(sites.T)] = x
        return c

    @property
    def decay_length(self):
        return math.sqrt(self.D / self.gamma) if self.gamma > 0 else math.inf


def _shift(mask, dr, dc):
    """out[i, j] = mask[i + dr, j + dc], False beyond the grid."""
    out = np.zeros_like(mask)
    R, C = mask.shape
    rs, rd = (slice(dr, R), slice(0, R - dr)) if dr >= 0 else (slice(0, R + dr), slice(-dr, R))
    cs, cd = (slice(dc, C), slice(0, C - dc)) if dc >= 0 else (slice(0, C + dc), slice(-dc, C))
    out[rd, cd] = mask[rs, cs]
    return out


def _shift_vals(a, dr, dc):
    """out[i, j] = a[i + dr, j + dc], 0 beyond the grid."""
    out = np.zeros_like(a)
    R, C = a.shape
    rs, rd = (slice(dr, R), slice(0, R - dr)) if dr >= 0 else (slice(0, R + dr), slice(-dr, R))
    cs, cd = (slice(dc, C), slice(0, C - dc)) if dc >= 0 else (slice(0, C + dc), slice(-dc, C))
    out[rd, cd] = a[rs, cs]
    return out


def rectangle(rows, cols):
    """Lattice positions of a rows x cols group, row-major."""
    return [(r, c) for r in range(rows) for c in range(cols)]
