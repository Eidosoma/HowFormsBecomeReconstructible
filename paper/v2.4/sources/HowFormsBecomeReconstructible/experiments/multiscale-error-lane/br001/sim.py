"""The tissue-held record: body and record steps, events, gates, turnover and the fresh reader.

One update, in order: events due at t (lesions, wounds, scars, impositions); the body step (native
sheet and the body reading its own record r with gain c; the conserved body removes the mean from
drift, noise and correction exactly as mse.engine.step, the open body removes nothing); the gates
(panel P); the record step (self-correction, coarse code, gated writing, clipping, clamp); turnover.
With every new element off, the conserved body is mse.engine's hold route bit for bit
(tests/test_br001.py). Branches are condition-major: index = condition x cases + case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from mse.assay import Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE, address, center, moving_average, neighbours, sheet
from mse.ops import block_projection

from . import design as D


def params(name):
    family, sigma, body = D.parse(name)
    return family, replace(NATIVE, sigma=sigma), body == "c"


def prepare(name, blocks, purpose):
    """ME002's acquisition under BR001's tag with the native physics: birth, settle, teach the
    family template, release on the hold route, Q = 0. Returns cases, state, theta, params,
    conserved flag, own and foreign targets."""
    family, p, conserved = params(name)
    cases = enrol(blocks, D.MESSAGES, D.PARENTS, purpose)
    T = D.TEMPLATES[family][[c.message for c in cases]]
    Tf = D.TEMPLATES[family][[D.FOREIGN[c.message] for c in cases]]
    th = theta(D.TAG, cases, p, per_tissue=D.PER_TISSUE_THETA)
    V = birth(D.TAG, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(D.TAG, cases, "settle"), Route(capture=None), D.SETTLE, p)
    s = run(s, th, Noise(D.TAG, cases, "teach"), Route(capture=None), D.TEACH, p, imposed=T)
    s = run(s, th, Noise(D.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return cases, State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, p, conserved, T, Tf


def draws(cases, *stream, updates):
    return np.stack([address(D.TAG, *c.key(), *stream).standard_normal((updates, 16, 16)) for c in cases], 1)


def body_step(V, ema, r, th, z, p, conserved, gain):
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


def patch_masks(cases, size, *stream):
    """(cases, 16, 16) bool: an size x size patch at a per-case addressed corner (periodic)."""
    out = np.zeros((len(cases), 16, 16), bool)
    if size == 0:
        return out
    for i, c in enumerate(cases):
        a, b = address(D.TAG, *c.key(), "lesion", *stream).integers(0, 16, 2)
        out[i][np.ix_(np.arange(a, a + size) % 16, np.arange(b, b + size) % 16)] = True
    return out


def onsets(cases, kind):
    if kind == "random":
        return np.array([int(address(D.TAG, *c.key(), "onset").integers(*D.ONSET)) for c in cases])
    return np.ones(len(cases), int)


def turnover_events(cases, rate, updates):
    """Per case: arrays (t, flat site, newborn value) of cell replacements (Poisson count, uniform times and
    sites), addressed by (case, 'turnover', rate) and shared by every arm."""
    out = []
    for c in cases:
        g = address(D.TAG, *c.key(), "turnover", f"{rate:g}")
        n = int(g.poisson(rate * updates * 256)) if rate > 0 else 0
        t = g.integers(1, updates + 1, n)
        site = g.integers(0, 256, n)
        val = 0.2 * g.standard_normal(n)
        order = np.argsort(t, kind="stable")
        out.append((t[order], site[order], val[order]))
    return out


def region(x):
    """Mean square of the 4 x 4 region projection, broadcast to sites."""
    return block_projection(x, 4) ** 2


def simulate(arm, conds, k, V, ema, R, R0, th, Z, XI, p, conserved, T, Tf, tau, masks, turn, cal=None):
    """Advance len(conds) x k branches WINDOW updates under one arm. masks[c]: (k,16,16) patch per
    condition (or None); turn[c]: per-case turnover events (or None); cal: panel P thresholds."""
    nc = len(conds)
    n = nc * k
    idx = np.tile(np.arange(k), nc)
    thb, Tb, Tfb, taub = th[idx], T[idx], Tf[idx], np.tile(tau, nc)
    mask = np.concatenate([masks[c] if masks[c] is not None else np.zeros((k, 16, 16), bool) for c in range(nc)])
    kind = np.repeat([c.kind for c in conds], k)
    target = np.repeat([c.target for c in conds], k)
    dur = np.repeat([c.duration for c in conds], k)
    cue = np.repeat([c.cue for c in conds], k)
    gain = NATIVE.gain if arm.reads else 0.0
    B = block_projection(R0, 4)[idx]
    R0b = R0[idx]
    v, e, r = V[idx].copy(), ema[idx].copy(), R[idx].copy()
    tag = np.zeros((n, 16, 16))
    latch = np.zeros((n, 16, 16), int)
    w_l1 = np.zeros(n)
    imp_stop = np.where(dur > 0, taub + dur, D.WINDOW + 1)
    win_stop = taub + D.WINDOW_P
    for t in range(1, D.WINDOW + 1):
        start = taub == t
        if start.any():
            m3 = (mask & start[:, None, None])
            hit_v = m3 & (((kind == "lesion") & np.isin(target, ("both", "body"))) | (kind == "wound"))[:, None, None]
            hit_r = m3 & (((kind == "lesion") & np.isin(target, ("both", "record"))) | (kind == "record"))[:, None, None]
            v = np.where(hit_v, -v, v)
            r = np.where(hit_r, -r, r)
            tag = np.where(m3 & ((kind == "wound") | (kind == "scar"))[:, None, None], 1.0, tag)
        scar = (kind == "scar") & (t >= taub)
        if scar.any():
            m3 = mask & scar[:, None, None]
            v = np.where(m3, -Tb, v)
            tag = np.where(m3, 1.0, tag)
        imp = (kind == "impose") & (t >= taub) & (t < imp_stop)
        if imp.any():
            v = np.where(imp[:, None, None], Tfb, v)
        v, e, vt = body_step(v, e, r, thb, Z[t - 1][idx], p, conserved, gain)
        gate = None
        if arm.write != "none":
            mis = region(r - vt) > (cal["mismatch"] if cal else np.inf)
            if arm.write == "always":
                gate = mis
            elif arm.write == "duration":
                latch = np.where(region(vt - e) > cal["surprise"], D.LATCH_W, np.maximum(latch - 1, 0))
                gate = mis & (latch == 0)
            elif arm.write == "tags":
                gate = mis & (tag < D.TAG_GATE)
            elif arm.write == "phase":
                gate = np.broadcast_to((cue & (t >= taub) & (t < win_stop))[:, None, None], v.shape)
        tag = tag * (1.0 - D.TAG_DECAY)
        r_old = r
        if arm.eps > 0:
            r = r + arm.eps * (r * (1 - (r / D.R_STAR) ** 2) + arm.kr * (neighbours(r) - r)) + arm.sigma_r * XI[t - 1][idx]
        if arm.kc > 0:
            r = r + arm.kc * (B - block_projection(r, 4))
        if gate is not None:
            dw = D.RHO_W * gate * (v - r)
            w_l1 += np.abs(dw).sum(axis=(-2, -1))
            r = r + dw
        r = np.clip(r, -2.0, 2.0) if r is not r_old else r
        if arm.clamp:
            r = R0b.copy()
        if turn is not None:
            for ci in range(nc):
                if turn[ci] is None:
                    continue
                for j in range(k):
                    tt, site, val = turn[ci][j]
                    lo, hi = np.searchsorted(tt, t, "left"), np.searchsorted(tt, t, "right")
                    if hi > lo:
                        b = ci * k + j
                        ii, jj = np.divmod(site[lo:hi], 16)
                        v[b, ii, jj] = val[lo:hi]
                        e[b, ii, jj] = val[lo:hi]
                        if not arm.separate:
                            r[b, ii, jj] = 0.0
    return v, e, r, w_l1


def recipients(cases):
    births = np.stack([birth(D.TAG, cases, "recipient", i, "birth") for i in range(D.RECIPIENTS)], 1)
    Zr = np.stack([draws(cases, "recipient", i, "read", updates=D.READ_UPDATES) for i in range(D.RECIPIENTS)], 2)
    return births, Zr


def read(packets, idx, th, births, Zr, p, conserved):
    """Fresh recipients hold each packet as their (static) record for READ_UPDATES with gain c."""
    n, k = len(packets), D.RECIPIENTS
    v = births[idx].reshape(n * k, 16, 16)
    e = v.copy()
    r = np.repeat(packets, k, axis=0)
    thr = np.repeat(th[idx], k, axis=0)
    for t in range(D.READ_UPDATES):
        v, e, _ = body_step(v, e, r, thr, Zr[t][idx].reshape(n * k, 16, 16), p, conserved, NATIVE.gain)
    return v.reshape(n, k, 16, 16)


def qual(V, T):
    return (((V > 0) == (T > 0)) & (np.abs(V) > 0.2)).mean((-2, -1))


def sign(V, T):
    return ((V > 0) == (T > 0)).mean((-2, -1))


def masked_sign(V, T, m):
    return (((V > 0) == (T > 0)) & m).sum((-2, -1)) / np.maximum(m.sum((-2, -1)), 1)
