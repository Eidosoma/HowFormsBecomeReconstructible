"""Linear analysis of the native update around a settled state.

For the reciprocal identity route, a small displacement (dV, dR) maps as
    dV-tilde = M dV,                    M = I + dt C (diag(1 - 3 V^2) + g (N - I))
    dV'      = (I - dt c C) M dV + dt c C dR
    dR'      = (1 - rho) dR + rho dV'
with C the mean-removal projector and N four-neighbour averaging; clipped sites have zero
derivative. Eigenvectors of M with eigenvalue near 1 are the soft directions that native
physics does not restore; on those the reference decides where the body goes.
"""
from __future__ import annotations

import numpy as np

from .engine import Route, State, run
from .native import NATIVE, Params
from .ops import bands

N_SITES = 256


def neighbour_matrix(side=16):
    idx = np.arange(side * side).reshape(side, side)
    N = np.zeros((side * side, side * side))
    for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
        N[idx.ravel(), np.roll(idx, shift, axis).ravel()] += 0.25
    return N


C = np.eye(N_SITES) - np.full((N_SITES, N_SITES), 1.0 / N_SITES)
NB = neighbour_matrix()


def sheet_jacobian(V, p: Params = NATIVE):
    """Jacobian of the native sheet step at V (one 16 x 16 field), noise excluded."""
    v = V.ravel()
    J = np.eye(N_SITES) + p.dt * C @ (np.diag(1 - 3 * v ** 2) + p.coupling * (NB - np.eye(N_SITES)))
    inside = np.abs(v) < p.bound
    return J * inside[:, None]


def full_jacobian(V, p: Params = NATIVE, body=True, reference=True):
    M = sheet_jacobian(V, p)
    I = np.eye(N_SITES)
    G = p.dt * p.gain * C if body else np.zeros_like(C)
    A_vv, A_vr = (I - G) @ M, G
    rho = p.rho if reference else 0.0
    A_rv, A_rr = rho * A_vv, (1 - rho) * I + rho * A_vr
    return np.block([[A_vv, A_vr], [A_rv, A_rr]])


def settle_quiet(V, R, theta, updates=400, p: Params = NATIVE, route: Route | None = None):
    """Deterministic settling with the noise switched off (z = 0)."""
    s = State(V.copy(), V.copy(), R.copy(), np.zeros_like(V))
    zero = np.zeros_like(V)
    return run(s, theta, lambda t: zero, route or Route(reference=None, capture=None), updates, p)


def band_fractions(vectors):
    """Energy fraction of each column vector in the fine/regional/collective/constant bands."""
    x = np.real(vectors).T.reshape(-1, 16, 16)
    e = {k: (b ** 2).sum(axis=(-2, -1)) for k, b in bands(x).items()}
    total = sum(e.values())
    return {k: v / np.where(total > 0, total, 1.0) for k, v in e.items()}


def boundary_weight(vectors, V):
    """Energy fraction of each mode on sites adjacent to a sign boundary of V."""
    s = V > 0
    edge = np.zeros_like(s)
    for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
        edge |= s != np.roll(s, shift, axis)
    w = np.abs(np.real(vectors)) ** 2
    return (w * edge.ravel()[:, None]).sum(0) / w.sum(0)


def matched_filter_snr(band_energy: dict, noise_var: float):
    """Detection SNR of a static error under white per-site noise for each sensor level.

    Nested projections: site keeps every band (rank 256), region keeps regional, collective
    and constant (rank 16), sheet keeps collective only (rank 3 after mean removal).
    """
    keep = {"site": ("fine", "regional", "collective", "constant"),
            "region": ("regional", "collective", "constant"), "sheet": ("collective",)}
    rank = {"site": 256, "region": 16, "sheet": 3}
    return {lvl: sum(band_energy.get(b, 0.0) for b in keep[lvl]) / (noise_var * rank[lvl])
            for lvl in keep}
