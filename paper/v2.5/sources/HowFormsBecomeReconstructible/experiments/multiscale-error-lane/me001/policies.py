"""Policies for the engine's hook: each sees V-tilde, ema and R only and returns (gain, rate).

The arbiter restates P4b's ScaleArbiter (probes/p4b_scale_trigger.py) with its constants;
tests/test_me001.py checks the two agree update for update. The change-point arm is the
same rule with the provenance latch removed. The location oracle is privileged: it is told
whether only the reference was damaged and is an instrument ceiling, not a controller.
"""
from __future__ import annotations

import numpy as np

from mse.native import NATIVE
from mse.ops import project

from .design import BURST_RATE, BURST_UPDATES, LATCH, REFRACTORY, TRACE_TIMES

LEVELS = ("site", "region", "sheet")


def pooled_features(Vt, ema, R):
    """Region-pooled mismatch and region-pooled surprise (mean squared, per case)."""
    mismatch = (project(R - Vt, "region") ** 2).mean(axis=(-2, -1))
    surprise = (project(Vt - ema, "region") ** 2).mean(axis=(-2, -1))
    return mismatch, surprise


class Arbiter:
    """Hold R and read it; on region-pooled mismatch with no recent region surprise, stop
    reading for BURST_UPDATES and rewrite R from the body at BURST_RATE. The latch, burst and
    refractory counters are a declared retained history (three integers per case)."""

    def __init__(self, n, theta_m, theta_s, latch=True, gain=NATIVE.gain):
        self.theta_m, self.theta_s, self.use_latch, self.gain = theta_m, theta_s, latch, gain
        self.latch = np.zeros(n, int)
        self.burst = np.zeros(n, int)
        self.refractory = np.zeros(n, int)
        self.bursts = np.zeros(n, int)
        self.first = np.full(n, -1)
        self.t = 0

    def __call__(self, Vt, ema, R):
        self.t += 1
        m, s = pooled_features(Vt, ema, R)
        if self.use_latch:
            self.latch = np.where(s > self.theta_s, LATCH, np.maximum(self.latch - 1, 0))
        start = (m > self.theta_m) & (self.latch == 0) & (self.burst == 0) & (self.refractory == 0)
        self.burst = np.where(start, BURST_UPDATES, self.burst)
        self.bursts += start
        self.first = np.where(start & (self.first < 0), self.t, self.first)
        on = self.burst > 0
        gain = np.where(on, 0.0, self.gain)[:, None, None]
        rate = np.where(on, BURST_RATE, 0.0)[:, None, None]
        ending = on & (self.burst == 1)
        self.burst = np.maximum(self.burst - 1, 0)
        self.refractory = np.where(ending, REFRACTORY, np.maximum(self.refractory - 1, 0))
        return gain, rate


class Oracle:
    """PRIVILEGED: bursts for the first BURST_UPDATES updates exactly when only R was damaged."""

    def __init__(self, ref_only, gain=NATIVE.gain):
        self.ref_only, self.gain, self.t = np.asarray(ref_only, bool), gain, 0
        self.bursts = self.ref_only.astype(int)
        self.first = np.where(self.ref_only, 1, -1)

    def __call__(self, Vt, ema, R):
        self.t += 1
        on = self.ref_only & (self.t <= BURST_UPDATES)
        return np.where(on, 0.0, self.gain)[:, None, None], np.where(on, BURST_RATE, 0.0)[:, None, None]


def burst(Vt, ema, R):
    """The fixed early write window: comparison off, R rewritten from the body at BURST_RATE."""
    return 0.0, BURST_RATE


FEATURES = tuple(f"{kind}_{lvl}" for kind in ("mismatch", "surprise") for lvl in LEVELS)


class Tap:
    """Records sensor features (mean squared projections of R - V-tilde and V-tilde - ema)
    at TRACE_TIMES and their running maxima, then defers to the inner policy (or the native
    constants, which leaves the update bit-exact)."""

    def __init__(self, n, inner=None, p=NATIVE):
        self.inner, self.p, self.t = inner, p, 0
        self.trace = np.full((len(TRACE_TIMES), len(FEATURES), n), np.nan)
        self.maximum = np.zeros((len(FEATURES), n))

    def __call__(self, Vt, ema, R):
        self.t += 1
        d, e = R - Vt, Vt - ema
        f = np.stack([(project(x, lvl) ** 2).mean(axis=(-2, -1)) for x in (d, e) for lvl in LEVELS])
        self.maximum = np.maximum(self.maximum, f)
        if self.t in TRACE_TIMES:
            self.trace[TRACE_TIMES.index(self.t)] = f
        return self.inner(Vt, ema, R) if self.inner is not None else (self.p.gain, self.p.rho)
