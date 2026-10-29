"""SC002's theory (derived before the run): the coupling a turning-over population sets, and the static voltage map.

Under stationary turnover at mu every cell's age is exponential with rate mu, so a contact's age (its younger cell's) is
exponential with rate 2 mu and x = exp(-age / tau_m) is Beta(beta, 1) with beta = 2 mu tau_m. A maturing junction's
conductance is g = lam^2 (1 - x), with mean lam^2 / (1 + beta).
  emt_g       the square lattice's bond effective-medium conductance g_e, solving E[(g_e - g) / (g + g_e)] = 0
              (Kirkpatrick 1973; z / 2 - 1 = 1), so lam_eff = sqrt(g_e / g_l); it treats bonds as independent;
  self_young  the share of cells that read only their own cue: a cell all of whose contacts are a years old, among mature
              neighbours at v = 1, sits below -theta when it disagrees iff its total conductance 4 lam^2 m(a) is below
              (kappa - theta) / (1 + theta) (g_l = 1), i.e. while a < a* = -tau_m ln(1 - G*/(4 lam^2));
              a share 1 - exp(-mu a*) of the cells is that young;
  static_map  potentials with no dynamics on a given sheet (anchors, cue, record signs, conductances, occupancy), as
              probes/theory_be001_static_detector.py did for BE001 with uniform coupling.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import integrate, optimize

from . import design as D


def emt_g(beta, lam):
    """Bond EMT conductance for g = lam^2 (1 - x), x ~ Beta(beta, 1); lam^2 with no turnover (beta 0)."""
    g0 = lam ** 2
    if beta == 0:
        return g0

    def f(ge):                                   # x = y^(1/beta), y uniform: E[h(x)] = int_0^1 h(y^(1/beta)) dy
        def integrand(y):
            g = g0 * (1.0 - y ** (1.0 / beta))
            return (ge - g) / (g + ge)
        return integrate.quad(integrand, 0.0, 1.0, limit=200)[0]
    return optimize.brentq(f, 1e-9 * g0, g0, xtol=1e-12)


def lam_eff(mu, tau_m, lam=3.0):
    return math.sqrt(emt_g(2.0 * mu * tau_m, lam) / D.G_LEAK)


def g_star(theta=D.THETA):
    """The total junction conductance below which an isolated disagreeing anchored cell among cells at v = 1 triggers."""
    return (D.KAPPA - theta) / (1.0 + theta)


def a_star(tau_m, lam=3.0, theta=D.THETA):
    """The age below which a cell all of whose contacts are as young as it is reads only its own cue."""
    return -tau_m * math.log(1.0 - g_star(theta) / (4.0 * lam ** 2))


def self_young(mu, tau_m, lam=3.0, theta=D.THETA):
    """The stationary share of cells younger than a* (all four contacts at most as old as the cell)."""
    return 1.0 - math.exp(-mu * a_star(tau_m, lam, theta))


def static_map(cable, ca, sr, gH, gW, occ):
    """Steady potentials with no dynamics: (g_l + L_g) v = kappa * cue * record sign on occupied anchored cells."""
    I = D.KAPPA * np.where(occ, ca, 0.0) * sr
    return cable.solve(I, gH, gW, np.zeros_like(I))[0]


def lam_rms(cable, gH, gW, occ, sites):
    """The spread of the response to a unit current at each given site: sqrt(<r^2> / 4) (= lam on a uniform sheet)."""
    k, n = gH.shape[0], D.SIDE
    ar = np.arange(n)
    out = []
    for (i, j) in sites:
        I = np.zeros((k, n, n))
        I[:, i, j] = 1.0
        v = cable.solve(I, gH, gW, np.zeros_like(I), tol=1e-12)[0]
        di = (ar - i + n // 2) % n - n // 2
        dj = (ar - j + n // 2) % n - n // 2
        r2 = di[:, None] ** 2 + dj[None, :] ** 2
        out.append(np.sqrt((v * r2).sum((-2, -1)) / v.sum((-2, -1)) / 4.0))
    return np.array(out)          # (sites, k)
