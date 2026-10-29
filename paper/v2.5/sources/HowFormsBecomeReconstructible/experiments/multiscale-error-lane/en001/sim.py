"""EN001's tissue: BR002's body, record and events under an energy budget.

One update, in order: events due at t (flip and reset wounds at t = 1); the body step (BR001's, with its paid
rates multiplied: the double well, coupling and theta by m_drift, the correction by m_corr, the noise variance
by n_body); the record step (self-correction through the bonds and coarse code at m_rec, record noise variance
n_rec); turnover on the outside clock; snapshots; the store. With every multiplier 1 the body and record steps
are br002.sim.simulate's bit for bit (tests/test_en001.py). Branch index = (budget x conditions + condition) x
cases + case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from br001.sim import masked_sign, qual, sign  # noqa: F401  (unchanged scoring)
from br002.sim import bond_sum, bonds, kill_bonds
from mse.assay import Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE, address, moving_average, neighbours
from mse.ops import block_projection

from . import design as D


def params(name):
    family, sigma, body = D.parse(name)
    return family, replace(NATIVE, sigma=sigma), body == "c"


def prepare(name, blocks, purpose):
    """BR001's acquisition under EN001's tag."""
    family, p, conserved = params(name)
    cases = enrol(blocks, D.MESSAGES, D.PARENTS, purpose)
    T = D.TEMPLATES[family][[c.message for c in cases]]
    th = theta(D.TAG, cases, p, per_tissue=D.PER_TISSUE_THETA)
    V = birth(D.TAG, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(D.TAG, cases, "settle"), Route(capture=None), D.SETTLE, p)
    s = run(s, th, Noise(D.TAG, cases, "teach"), Route(capture=None), D.TEACH, p, imposed=T)
    s = run(s, th, Noise(D.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return cases, State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, p, conserved, T


def draws(cases, *stream, updates):
    return np.stack([address(D.TAG, *c.key(), *stream).standard_normal((updates, 16, 16)) for c in cases], 1)


def patch_masks(cases, size):
    out = np.zeros((len(cases), 16, 16), bool)
    for i, c in enumerate(cases):
        a, b = address(D.TAG, *c.key(), "lesion").integers(0, 16, 2)
        out[i][np.ix_(np.arange(a, a + size) % 16, np.arange(b, b + size) % 16)] = True
    return out


def turnover_events(cases, rate, updates):
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


def newborn(cases, size):
    return np.stack([D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{size}").standard_normal((16, 16)) for c in cases])


def body_step(V, ema, r, th, z, p, conserved, gain, m_drift, m_corr, n_body):
    """br001.sim.body_step with paid rates: returns the new V, ema, V-tilde and the unpaid drift."""
    drift = V - V ** 3 + p.well_asym + th + p.coupling * (neighbours(V) - V)
    paid = m_drift * drift
    noise = (p.sigma * z) * np.sqrt(n_body)
    if conserved:
        paid = paid - paid.mean(axis=(-2, -1), keepdims=True)
        noise = noise - noise.mean(axis=(-2, -1), keepdims=True)
    Vt = np.clip(V + p.dt * paid + noise, -p.bound, p.bound)
    ema = moving_average(ema, Vt, p)
    d = (gain * m_corr) * (r - Vt)
    if conserved:
        d = d - d.mean(axis=(-2, -1), keepdims=True)
    return np.clip(Vt + p.dt * d, -p.bound, p.bound), ema, Vt, drift


def availability(E, cap):
    x = E / cap
    return x * (1.0 + D.STORE_K) / (x + D.STORE_K)


def simulate(arm, budgets, conds, k, V, ema, R, R0, th, Z, XI, p, conserved, T, masks, turn, born, work=None):
    """Advance len(budgets) x len(conds) x k branches WINDOW updates under one record arm.
    masks[c]: (k,16,16) patch or None; turn[c]: turnover events or None; born[c]: kill newborns or None;
    work: the calibrated sham work per cell per update (the store's unit), needed for store budgets."""
    nb, nc = len(budgets), len(conds)
    n = nb * nc * k
    idx = np.tile(np.arange(k), nb * nc)
    thb, Tb = th[idx], T[idx]
    mask1 = np.concatenate([masks[c] if masks[c] is not None else np.zeros((k, 16, 16), bool) for c in range(nc)])
    mask = np.tile(mask1, (nb, 1, 1))
    nbn = np.tile(np.concatenate([born[c] if born[c] is not None else np.zeros((k, 16, 16)) for c in range(nc)]), (nb, 1, 1))
    kind = np.tile(np.repeat([c.kind for c in conds], k), nb)
    rep = lambda f: np.repeat([f(b) for b in budgets], nc * k)[:, None, None]
    phi = rep(lambda b: b.phi)
    store = rep(lambda b: b.scheme == "store")
    paid_all = rep(lambda b: b.paid == "all")
    active = rep(lambda b: b.noise == "activity")
    body_cut = rep(lambda b: b.alloc in ("uniform", "record"))
    rec_cut = rep(lambda b: b.alloc in ("uniform", "body"))
    gain = NATIVE.gain
    B = block_projection(R0, 4)[idx]
    J = bonds(R0[idx], arm.rel)
    v, e, r = V[idx].copy(), ema[idx].copy(), R[idx].copy()
    has_store = bool(store.any())
    if has_store:
        cap, supply0 = D.STORE_CAP * work, D.STORE_HEADROOM * work
        E = np.full((n, 16, 16), cap)
    w_drift, w_corr, w_rec = np.zeros(n), np.zeros(n), np.zeros(n)
    a_sum, a_in, a_out = np.zeros(n), np.zeros(n), np.zeros(n)
    n_in, n_out = np.maximum(mask.sum((-2, -1)), 1), np.maximum((~mask).sum((-2, -1)), 1)
    nsnap = D.WINDOW // D.SNAP
    snap_r, snap_v = np.zeros((n, nsnap)), np.zeros((n, nsnap))
    out = {}
    for t in range(1, D.WINDOW + 1):
        if t == 1:
            flip = mask & (kind == "lesion")[:, None, None]
            v, r = np.where(flip, -v, v), np.where(flip, -r, r)
            kill = mask & (kind == "kill")[:, None, None]
            if kill.any():
                v, e, r = np.where(kill, nbn, v), np.where(kill, nbn, e), np.where(kill, 0.0, r)
                if arm.rel:
                    J = kill_bonds(J, kill, arm.relink)
        starving = t <= D.STARVE
        f = np.where(starving, phi, 1.0) if not has_store else np.where(store, 1.0, np.where(starving, phi, 1.0))
        m_body = np.where(body_cut, f, 1.0)
        m_rec = np.where(rec_cut, f, 1.0)
        if has_store:
            a = availability(E, cap)
            m_body = np.where(store, a, m_body)
            m_rec = np.where(store, a, m_rec)
        m_drift = np.where(paid_all, m_body, 1.0)
        m_corr = m_body
        n_body = np.where(active, m_drift, 1.0)
        n_rec = np.where(active, m_rec, 1.0)
        r_in = r
        v, e, vt, drift = body_step(v, e, r, thb, Z[t - 1][idx], p, conserved, gain, m_drift, m_corr, n_body)
        wd = np.abs(p.dt * m_drift * drift)
        wc = np.abs(p.dt * (gain * m_corr) * (r_in - vt))
        wr = np.zeros((n, 16, 16))
        r_old = r
        if arm.eps > 0:
            inc = (arm.eps * m_rec) * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r))
            wr = wr + np.abs(inc)
            r = r + inc + (D.SIGMA_R * XI[t - 1][idx]) * np.sqrt(n_rec)
        if arm.kc > 0:
            inc = (arm.kc * m_rec) * (B - block_projection(r, 4))
            wr = wr + np.abs(inc)
            r = r + inc
        r = np.clip(r, -2.0, 2.0) if r is not r_old else r
        if starving:
            w_drift += wd.sum((-2, -1))
            w_corr += wc.sum((-2, -1))
            w_rec += wr.sum((-2, -1))
        if has_store:
            spend = wd + wc + wr
            supply = np.where(starving, phi, 1.0) * supply0
            E = np.where(store, np.clip(E + supply - spend, 0.0, cap), E)
            if starving:
                a_sum += a.mean((-2, -1))
                if t <= D.REPAIR:
                    a_in += (a * mask).sum((-2, -1)) / n_in
                    a_out += (a * ~mask).sum((-2, -1)) / n_out
        if turn is not None:
            for bi in range(nb):
                for ci in range(nc):
                    if turn[ci] is None:
                        continue
                    for j in range(k):
                        tt, site, val = turn[ci][j]
                        lo, hi = np.searchsorted(tt, t, "left"), np.searchsorted(tt, t, "right")
                        if hi > lo:
                            b = (bi * nc + ci) * k + j
                            ii, jj = np.divmod(site[lo:hi], 16)
                            v[b, ii, jj] = val[lo:hi]
                            e[b, ii, jj] = val[lo:hi]
                            r[b, ii, jj] = 0.0
        if t % D.SNAP == 0:
            snap_r[:, t // D.SNAP - 1] = masked_sign(r, Tb, mask)
            snap_v[:, t // D.SNAP - 1] = sign(v, Tb)
        if t == D.STARVE:
            out.update({"V_s": v.copy(), "R_s": r.copy()})
    out.update({"V_r": v, "R_r": r, "snap_r": snap_r, "snap_v": snap_v, "w_drift": w_drift, "w_corr": w_corr,
                "w_rec": w_rec, "a_mean": a_sum / D.STARVE,
                "a_patch": np.where(mask.any((-2, -1)), a_in / D.REPAIR, np.nan), "a_rest": a_out / D.REPAIR, "mask": mask})
    return out


def t95(snap_r, mask_any):
    """Updates until the record kept inside the wound first reaches 0.95 (snapshot grain); inf if never; nan without wound."""
    hit = snap_r >= 0.95
    first = np.where(hit.any(1), (hit.argmax(1) + 1) * D.SNAP, np.inf)
    return np.where(mask_any, first, np.nan)
