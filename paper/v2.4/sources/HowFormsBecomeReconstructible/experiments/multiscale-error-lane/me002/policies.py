"""Policies for the engine's hook: each sees V-tilde, ema and R only and returns (gain, rate).

Arbiter2 generalises ME001's arbiter (me001.policies.Arbiter, P4b's rule): the mismatch feature
may be pooled at site, region or sheet resolution; the latch window W may be shortened or
removed (W = 0: the change-point arm); a burst may be aborted when surprise appears during it;
and the latch may start closed (a newborn's developmental latch). With trigger 'region', W = 1000,
no abort and an open latch it is ME001's rule update for update (tests/test_me002.py). Whether the
latch threshold is ME001's (99.5% of all sham updates) or v2's (99.5% of sham per-trajectory
maxima) is a calibration choice, not a rule change. The event oracle is privileged.
"""
from __future__ import annotations

import numpy as np

from mse.native import NATIVE
from mse.ops import project

from .design import BURST_RATE, BURST_UPDATES, REFRACTORY


def features(Vt, ema, R, trigger):
    """Mismatch pooled at the trigger's resolution, and region-pooled surprise (mean squares)."""
    mismatch = (project(R - Vt, trigger) ** 2).mean(axis=(-2, -1))
    surprise = (project(Vt - ema, "region") ** 2).mean(axis=(-2, -1))
    return mismatch, surprise


class Arbiter2:
    """Hold R and read it; on pooled mismatch with no surprise in the last W updates, stop reading
    for BURST_UPDATES and rewrite R from the body at BURST_RATE, then wait REFRACTORY updates.
    Retained history: latch, burst and refractory counters (three integers per case)."""

    def __init__(self, n, theta_m, theta_s, trigger="region", latch=1000, abort=False, latch0=0,
                 gain=NATIVE.gain):
        self.theta_m, self.theta_s, self.trigger = theta_m, theta_s, trigger
        self.W, self.abort, self.gain = latch, abort, gain
        self.latch = np.full(n, latch0 if latch > 0 else 0, int)
        self.burst = np.zeros(n, int)
        self.refractory = np.zeros(n, int)
        self.bursts = np.zeros(n, int)
        self.aborts = np.zeros(n, int)
        self.latched = np.zeros(n, int)
        self.first = np.full(n, -1)
        self.starts = []          # (t, branch indices) of every burst start
        self.t = 0

    def __call__(self, Vt, ema, R):
        self.t += 1
        m, s = features(Vt, ema, R, self.trigger)
        if self.W > 0:
            self.latch = np.where(s > self.theta_s, self.W, np.maximum(self.latch - 1, 0))
        if self.abort:
            stop = (self.burst > 0) & (s > self.theta_s)
            if stop.any():
                self.aborts += stop
                self.burst = np.where(stop, 0, self.burst)
                self.refractory = np.where(stop, REFRACTORY, self.refractory)
        start = (m > self.theta_m) & (self.latch == 0) & (self.burst == 0) & (self.refractory == 0)
        if start.any():
            self.starts.append((self.t, np.flatnonzero(start)))
        self.burst = np.where(start, BURST_UPDATES, self.burst)
        self.bursts += start
        self.first = np.where(start & (self.first < 0), self.t, self.first)
        self.latched += self.latch > 0
        on = self.burst > 0
        gain = np.where(on, 0.0, self.gain)[:, None, None]
        rate = np.where(on, BURST_RATE, 0.0)[:, None, None]
        ending = on & (self.burst == 1)
        self.burst = np.maximum(self.burst - 1, 0)
        self.refractory = np.where(ending, REFRACTORY, np.maximum(self.refractory - 1, 0))
        return gain, rate

    def first_after(self, times):
        """Per branch: updates from `times` (an event instant) to the first burst start at or after
        it, or -1 if none."""
        out = np.full(len(times), -1)
        for t, idx in self.starts:
            sel = idx[(out[idx] < 0) & (t >= times[idx])]
            out[sel] = t - times[sel]
        return out


class Oracle2:
    """PRIVILEGED event oracle: a burst of BURST_UPDATES from each instant at which only the
    reference is injured, and, for an imposition lasting to the window's end, from 20 updates
    after its onset (adopting the sustained pattern). `on` is the (L, n) burst schedule."""

    def __init__(self, on, gain=NATIVE.gain):
        self.on, self.gain, self.t = on, gain, 0
        starts = on & ~np.vstack([np.zeros((1, on.shape[1]), bool), on[:-1]])
        self.bursts = starts.sum(0)
        self.first = np.where(starts.any(0), starts.argmax(0) + 1, -1)
        self.starts = [(t + 1, np.flatnonzero(starts[t])) for t in range(len(on)) if starts[t].any()]

    def __call__(self, Vt, ema, R):
        self.t += 1
        o = self.on[self.t - 1]
        return np.where(o, 0.0, self.gain)[:, None, None], np.where(o, BURST_RATE, 0.0)[:, None, None]

    first_after = Arbiter2.first_after


class Schedule:
    """Fixed write windows: comparison off and R rewritten from the body at BURST_RATE on the
    updates where window(t) holds; the body route with R held otherwise."""

    def __init__(self, window, gain=NATIVE.gain):
        self.window, self.gain, self.t = window, gain, 0

    def __call__(self, Vt, ema, R):
        self.t += 1
        return (0.0, BURST_RATE) if self.window(self.t) else (self.gain, 0.0)


def first20(t):
    return t <= BURST_UPDATES


def periodic(period):
    return lambda t: (t - 1) % period < BURST_UPDATES


class Gain:
    """A constant body gain (equal-dose sign arms); R is held."""

    def __init__(self, gain):
        self.gain = gain

    def __call__(self, Vt, ema, R):
        return self.gain, 0.0
