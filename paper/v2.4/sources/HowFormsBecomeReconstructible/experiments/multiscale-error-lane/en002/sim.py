"""EN002's tissue: DL001's open body (dl001/sim.py, unchanged and imported) under EN001's budget.

    drift = V - V^3 + well_asym + theta + c (N(V) - V) - alpha (G_L * V)          (dl001.sim.body)
    Vt    = clip(V + dt m_drift drift + sigma z sqrt(n_body))                         (en001.sim.body_step's paid rates)
    V    <- clip(Vt + dt (gain m_corr) (r - Vt))

With every multiplier 1 the step is dl001.sim.body bit for bit; with alpha = 0 it is en001.sim.body_step (open body)
bit for bit (tests/test_en002.py, Q3). During starvation (t <= STARVE) a branch's multipliers are set by its budget:
accounting B pays every drift (m_drift = m_corr = phi, thermal noise n_body = 1); accounting C also scales the noise
variance (n_body = phi). Afterwards every multiplier is 1. Branches are condition-major (index = condition x cases +
case) and every branch of a case reads that case's noise stream, so bodies, budgets and records are paired.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001.sim import best_shift, ghat, inhibit, patch, sign, spacing  # noqa: F401  (unchanged)
from mse.assay import enrol
from mse.native import NATIVE, address, moving_average, neighbours
from msegrid.core import Stream, acquire, base

from . import design as D


def template(family, kind, side):
    """+-1 pattern of one message: S4 stripes 4 thick (period 8) as DL001; F0 half-planes from msegrid.base."""
    if family == "S4":
        f = np.tile(np.where((np.arange(side) // 4) % 2 == 0, 1.0, -1.0), (side, 1))
        if kind % 2 == 1:
            f = f.T.copy()
        return f if kind < 2 else -f
    return base(family, kind, side)


def body(V, ema, r, th, z, p, gain, alpha, G, m_drift, m_corr, n_body):
    """One update under paid rates; returns V, ema, V-tilde, the unpaid drift and the paid pull."""
    drift = V - V ** 3 + p.well_asym + th + p.coupling * (neighbours(V) - V)
    if alpha:
        drift = drift - alpha * inhibit(V, G)
    paid = m_drift * drift
    noise = (p.sigma * z) * np.sqrt(n_body)
    Vt = np.clip(V + p.dt * paid + noise, -p.bound, p.bound)
    ema = moving_average(ema, Vt, p)
    d = (gain * m_corr) * (r - Vt)
    return np.clip(Vt + p.dt * d, -p.bound, p.bound), ema, Vt, drift, d


def prepare(pattern, block, purpose, tag=D.TAG):
    """Cases, the acquired body, moving average, record and theta (msegrid.acquire, as DL001), and the templates."""
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = np.stack([D.AMPLITUDE * template(pattern, c.message, D.SIDE) for c in cases])
    V, ema, R0, th = acquire(tag, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), D.SIDE,
                             settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T


def wound_mask(cases, size, tag=D.TAG):
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        a, b = address(tag, *c.key(), "wound", size).integers(0, D.SIDE, 2)
        out[j][np.ix_(np.arange(a, a + size) % D.SIDE, np.arange(b, b + size) % D.SIDE)] = True
    return out


def newborn_values(cases, size, tag=D.TAG):
    return np.stack([D.KILL_SD * address(tag, *c.key(), "newborn", size).standard_normal((D.SIDE, D.SIDE)) for c in cases])


def multipliers(conds, k):
    """Per-branch starvation multipliers (m_drift, m_corr, n_body), each (n, 1, 1), condition-major."""
    phi = np.repeat([c.budget.phi for c in conds], k)[:, None, None]
    paid_all = np.repeat([c.budget.acct in ("B", "C") for c in conds], k)[:, None, None]
    active = np.repeat([c.budget.acct == "C" for c in conds], k)[:, None, None]
    m_drift = np.where(paid_all, phi, 1.0)
    m_corr = np.where(paid_all, phi, 1.0)
    n_body = np.where(active, m_drift, 1.0)
    return m_drift, m_corr, n_body


def run(body_name, conds, V, ema, r, th, T, cases, snaps, masks=None, tag=D.TAG, window=D.WINDOW):
    """Advance len(conds) x len(cases) branches (condition-major) through starvation and recovery.

    V, ema, r, T, masks: (n, side, side) per branch; th: (k, side, side) per case (already scaled). The gain is GAIN
    for branches with the held record and 0 without. Returns per-snapshot sign, best shift, spacing (and patch
    agreement if masks), the paid drift and correction work per site and update over the starvation phase, and V."""
    alpha, L = D.BODIES[body_name]
    k, n = len(cases), len(V)
    idx = np.tile(np.arange(k), n // k)
    G = ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    gain = np.repeat([D.GAIN if c.record == "held" else 0.0 for c in conds], k)[:, None, None]
    ms_drift, ms_corr, ns_body = multipliers(conds, k)
    one = np.ones((n, 1, 1))
    thb = th[idx]
    st = Stream(tag, cases, "future", side=D.SIDE)
    out = {"sign": [], "shift": [], "spacing": [], "patch": []}
    wd, wc, buf = np.zeros(n), np.zeros(n), None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        starving = t <= D.STARVE
        m_drift, m_corr, n_body = (ms_drift, ms_corr, ns_body) if starving else (one, one, one)
        V, ema, Vt, drift, d = body(V, ema, r, thb, buf[i][idx], p, gain, alpha, G, m_drift, m_corr, n_body)
        if starving:
            wd += np.abs(p.dt * m_drift * drift).mean((-2, -1))
            wc += np.abs(p.dt * d).mean((-2, -1))
        if t in snaps:
            out["sign"].append(sign(V, T))
            out["shift"].append(best_shift(V, T))
            out["spacing"].append(spacing(V))
            if masks is not None:
                out["patch"].append(patch(V, T, masks))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(w_drift=wd / D.STARVE, w_corr=wc / D.STARVE, final=V)
    return res
