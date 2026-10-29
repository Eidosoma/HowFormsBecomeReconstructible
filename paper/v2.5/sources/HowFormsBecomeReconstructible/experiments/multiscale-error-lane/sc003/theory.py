"""SC003's theory (derived before the run): the pooled coupling of each arm, and the static voltage maps.

SC002's (sc002.theory): under stationary turnover at mu a contact's age is exponential with rate 2 mu, x = exp(-a/tau_m)
is Beta(beta, 1) with beta = 2 mu tau_m, and the bond effective-medium conductance g_e solves E[(g_e - g)/(g + g_e)] = 0
on the square lattice. Per arm:
  inst-3      g = lam^2: lam_eff = 3
  emt-T       g = EMT_LAM(mu, T)^2: lam_eff = EMT_LAM(mu, T) (mat-T's, rounded to 4 decimals)
  iso arms    g = 0 on contacts younger than ISO (a share q = 1 - exp(-2 mu ISO)), else lam^2: g_e = lam^2 (1 - 2 q)
  mat, gate   SC002's lam_eff(mu, tau_m) (the gate leaves every conductance as mat's)
  sister      in the stationary state a quarter of the contacts are daughter-parent contacts (each newborn forms one
              with its parent among its four, and every contact ends at either cell's death, whatever its kind), held
              mature; the rest as mat's: E = 1/4 (g_e - lam^2)/(lam^2 + g_e) + 3/4 E_Beta[...] = 0
The birth check (SC002, THEORY 8.9): a cell whose own conductance is below G* = (kappa - theta)/(1 + theta) = 3.55 and
whose neighbours read v = 1 triggers when its record disagrees with its cue. A newborn's conductance is 0 under mat and
iso (G = 0 < G*), lam^2 = 9 under sister (> G*). Such checks fall at mu / 4 per site and update (births at anchored
sites), whatever tau_m; so adoption through them should follow the births per site, mu t, at either rate.
  static_map          sc002.theory.static_map (potentials with no dynamics on a given sheet)
  static_triggers     the cells the static map triggers (v < -theta, record sign nonzero), optionally gated (G >= G*)
  stationary_sisters  the population process alone (deaths, divisions, ages, daughter-parent contacts) run from the
                      stationary start until it forgets it, for the sister arm's static snapshot
"""
from __future__ import annotations

import math

import numpy as np
from scipy import integrate, optimize

from cellpop import core as C
from sc002 import theory as T2

from . import design as D
from . import sim

emt_g, g_star, a_star, self_young, static_map, lam_rms = T2.emt_g, T2.g_star, T2.a_star, T2.self_young, T2.static_map, \
    T2.lam_rms


def lam_eff(arm, mu):
    """The bond-EMT coupling length of an arm's stationary conductances at turnover mu."""
    prm = D.LAWS[arm]
    lam = D.lam_of(arm, mu) if mu else prm["lam"] or 3.0
    g0 = lam ** 2
    if mu == 0:
        return lam
    if prm["iso"]:
        q = 1.0 - math.exp(-2.0 * mu * prm["iso"])
        return math.sqrt(g0 * (1.0 - 2.0 * q) / D.G_LEAK)
    if prm["tau_m"] == 0:
        return lam
    beta = 2.0 * mu * prm["tau_m"]
    if not prm["sister"]:
        return T2.lam_eff(mu, prm["tau_m"], lam)

    def f(ge):
        def integrand(y):
            g = g0 * (1.0 - y ** (1.0 / beta))
            return (ge - g) / (g + ge)
        return 0.25 * (ge - g0) / (g0 + ge) + 0.75 * integrate.quad(integrand, 0.0, 1.0, limit=200)[0]
    return math.sqrt(optimize.brentq(f, 1e-9 * g0, g0, xtol=1e-12) / D.G_LEAK)


def static_triggers(cable, ca, sr, gH, gW, occ, gate=False):
    """The cells a static map triggers: v < -theta with a nonzero record sign (and, gated, own conductance >= G*)."""
    v = static_map(cable, ca, sr, gH, gW, occ)
    trig = (v < -D.THETA) & (sr != 0)
    if gate:
        trig &= sim.own(gH, gW) >= D.G_STAR
    return trig


def stationary_sisters(cases, mu, updates, tag):
    """The population process alone from SC003's stationary start (full sheet; cell ages floor(E / mu)) for `updates`
    updates under the case's own population streams (a probe's tag: independent of any run). Returns the occupancy, the
    contact ages and the daughter-parent contacts."""
    k = len(cases)
    occ = np.ones((k, D.SIDE, D.SIDE), bool)
    age = sim.cell_ages(cases, mu, tag)
    ageH, ageW = sim.contact_ages(age)
    sisH, sisW = np.zeros(occ.shape, bool), np.zeros(occ.shape, bool)
    us = {e: C.UStream(tag, cases, "population-static", e, side=D.SIDE) for e in ("div", "dir", "die")}
    st = {"occ": occ, "V": np.zeros(occ.shape), "E": np.zeros(occ.shape)}
    none = np.zeros(occ.shape, bool)
    for t in range(updates):
        if t % D.CHUNK == 0:
            ubuf = {e: s_.take(D.CHUNK) for e, s_ in us.items()}
        u = {e: b[t % D.CHUNK] for e, b in ubuf.items()}
        st, dead = C.die(st, mu, u["die"], none)
        pre = st["occ"]
        st, born = C.divide(st, D.P_DIV, u["div"], u["dir"], True)
        mine, pdir = sim.parents(pre, D.P_DIV, u["div"], u["dir"])
        assert np.array_equal(mine, born)
        nh, nw = C.touching(born)
        dh, dw = C.touching(dead)
        ageH, ageW = np.where(nh, 0.0, ageH + 1.0), np.where(nw, 0.0, ageW + 1.0)
        sh, sw = sim.sister_bonds(pdir)
        sisH, sisW = (sisH & ~dh & ~nh) | sh, (sisW & ~dw & ~nw) | sw
    return st["occ"], ageH, ageW, sisH, sisW
