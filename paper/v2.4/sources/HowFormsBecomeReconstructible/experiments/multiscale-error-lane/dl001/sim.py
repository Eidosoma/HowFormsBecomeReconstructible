"""DL001's tissue on msegrid: the open body of br001.sim.body_step with lateral inhibition, at any side.

    drift = V - V^3 + well_asym + theta + c (N(V) - V) - alpha (G_L * V),   Vt = clip(V + dt drift + sigma z)
    then the record's pull: V <- clip(Vt + dt gain (r - Vt))

alpha = 0 skips the inhibitor, so the step is br001.sim.body_step (open) bit for bit (tests/test_dl001.py, Q3).
A run advances branches in condition-major order (index = condition x cases + case); every branch of a case reads
that case's noise stream, so bodies, conditions and panels are paired within a case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from mse.assay import enrol
from mse.native import NATIVE, address, moving_average, neighbours
from msegrid.core import Stream, acquire, base, birth

from . import design as D


def template(family, kind, side, block):
    """+-1 pattern of one message: S4 stripes 4 thick (period 8) here; S8, F0 and BL from msegrid.base."""
    if family == "S4":
        f = np.tile(np.where((np.arange(side) // 4) % 2 == 0, 1.0, -1.0), (side, 1))
        if kind % 2 == 1:
            f = f.T.copy()
        return f if kind < 2 else -f
    return base(family, kind, side, D.TAG, block)


def ghat(side, L):
    """The inhibitor's transfer function 1 / (1 + L^2 k) on the rfft grid of a side x side periodic lattice."""
    q, qr = 2 * np.pi * np.fft.fftfreq(side), 2 * np.pi * np.fft.rfftfreq(side)
    k = (2 - 2 * np.cos(q))[:, None] + (2 - 2 * np.cos(qr))[None, :]
    return 1.0 / (1.0 + L * L * k)


def inhibit(V, G):
    return np.fft.irfft2(np.fft.rfft2(V) * G, s=V.shape[-2:])


def body(V, ema, r, th, z, p, gain, alpha, G):
    """One update; returns V, ema, V-tilde, the body's drift and the record's pull."""
    drift = V - V ** 3 + p.well_asym + th + p.coupling * (neighbours(V) - V)
    if alpha:
        drift = drift - alpha * inhibit(V, G)
    Vt = np.clip(V + p.dt * drift + p.sigma * z, -p.bound, p.bound)
    ema = moving_average(ema, Vt, p)
    d = gain * (r - Vt)
    return np.clip(Vt + p.dt * d, -p.bound, p.bound), ema, Vt, drift, d


def prepare(pattern, side, block, purpose):
    """Cases, the acquired body, moving average, record and theta, and the +-AMPLITUDE templates."""
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = np.stack([D.AMPLITUDE * template(pattern, c.message, side, block) for c in cases])
    V, ema, R0, th = acquire(D.TAG, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), side,
                             settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T


def newborn_sheet(cases, side):
    return birth(D.TAG, cases, "newborn-sheet", side=side)


def wound_mask(cases, size, side):
    out = np.zeros((len(cases), side, side), bool)
    for j, c in enumerate(cases):
        a, b = address(D.TAG, *c.key(), "wound", size).integers(0, side, 2)
        out[j][np.ix_(np.arange(a, a + size) % side, np.arange(b, b + size) % side)] = True
    return out


def newborn_values(cases, size, side):
    return np.stack([D.KILL_SD * address(D.TAG, *c.key(), "newborn", size).standard_normal((side, side)) for c in cases])


# endpoints -----------------------------------------------------------------------------------------------------

def sign(V, T):
    return ((V > 0) == (T > 0)).mean((-2, -1))


def qual(V, T):
    return (((V > 0) == (T > 0)) & (np.abs(V) > 0.2)).mean((-2, -1))


def patch(V, T, m):
    return (((V > 0) == (T > 0)) & m).sum((-2, -1)) / np.maximum(m.sum((-2, -1)), 1)


def best_shift(V, T):
    """Best agreement of sign(V) with sign(T) over all cyclic shifts: the layout, whatever the registration."""
    side = V.shape[-1]
    a, b = np.sign(V), np.sign(T)
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=(side, side))
    return (1.0 + c.reshape(len(c), -1).max(-1) / (side * side)) / 2.0


def spacing(V):
    """Power-weighted mean wavelength 2 pi / <|q|> over 0 < |q| <= QMAX (wavelengths of 4 sites or more)."""
    side = V.shape[-1]
    S = np.abs(np.fft.fft2(V - V.mean((-2, -1), keepdims=True))) ** 2
    q = 2 * np.pi * np.fft.fftfreq(side)
    qq = np.hypot(q[:, None], q[None, :])
    w = (qq > 0) & (qq <= D.QMAX)
    return 2 * np.pi / ((S * qq * w).sum((-2, -1)) / (S * w).sum((-2, -1)))


# the run -------------------------------------------------------------------------------------------------------

def run(body_name, V, ema, r, gain, th, T, cases, sigma, window, snaps, masks=None):
    """Advance len(V) branches (condition-major over len(cases) cases) for `window` updates.

    V, ema, r: (n, side, side) per branch; gain: (n,); th: (k, side, side) per case; T: (n, side, side).
    Returns per-snapshot sign, best shift, spacing (and patch agreement if masks), the correction and drift work
    averaged over the second half of the window, and the final V."""
    alpha, L = D.BODIES[body_name]
    side, k, n = V.shape[-1], len(cases), len(V)
    idx = np.tile(np.arange(k), n // k)
    G = ghat(side, L) if alpha else None
    p = replace(NATIVE, sigma=sigma)
    g = np.asarray(gain, float).reshape(n, 1, 1)
    thb = th[idx]
    st = Stream(D.TAG, cases, "future", side=side)
    out = {"sign": [], "shift": [], "spacing": [], "patch": []}
    wc, wd, nwork, buf = np.zeros(n), np.zeros(n), 0, None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        V, ema, Vt, drift, d = body(V, ema, r, thb, buf[i][idx], p, g, alpha, G)
        if t > window // 2:
            wc += np.abs(p.dt * d).mean((-2, -1))
            wd += np.abs(p.dt * drift).mean((-2, -1))
            nwork += 1
        if t in snaps:
            out["sign"].append(sign(V, T))
            out["shift"].append(best_shift(V, T))
            out["spacing"].append(spacing(V))
            if masks is not None:
                out["patch"].append(patch(V, T, masks))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(w_corr=wc / nwork, w_drift=wd / nwork, final=V)
    return res
