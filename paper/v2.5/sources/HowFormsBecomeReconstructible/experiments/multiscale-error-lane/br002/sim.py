"""BR002's tissue: BR001's body, record and events (br001/sim.py), plus committed gates, a window that
respects damage tags, damage inside an open window, a relational record with killable bonds, and lesions
placed at declared distances from F0's walls.

One update, in order: events due at t (lesions, kills, wounds, scars, impositions; window damage at
tau + WINDOW_DELAY); the body step (br001.sim.body_step, unchanged); the gates; tag decay; the record step
(self-correction through the bonds, coarse code, gated writing, clipping, clamp); turnover. With J = 1, no
hysteresis, no kills and no window damage this is br001.sim.simulate bit for bit (tests/test_br002.py).
Branches are condition-major: index = condition x cases + case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from br001.sim import body_step, masked_sign, qual, read, region, sign  # noqa: F401  (unchanged)
from mse.assay import Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE, address
from mse.ops import block_projection

from . import design as D

SHIFTS = ((1, -2), (-1, -2), (1, -1), (-1, -1))       # the four neighbours, in mse.native.neighbours' order


def params(name):
    family, sigma, body = D.parse(name)
    return family, replace(NATIVE, sigma=sigma), body == "c"


def prepare(name, blocks, purpose):
    """BR001's acquisition under BR002's tag: birth, settle, teach the family template, release on the hold
    route. Returns cases, state, theta, params, conserved flag, own and foreign targets."""
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


def patch_masks(cases, size):
    """(cases, 16, 16) bool: a size x size patch at a per-case addressed corner (periodic), as BR001."""
    out = np.zeros((len(cases), 16, 16), bool)
    for i, c in enumerate(cases):
        a, b = address(D.TAG, *c.key(), "lesion").integers(0, 16, 2)
        out[i][np.ix_(np.arange(a, a + size) % 16, np.arange(b, b + size) % 16)] = True
    return out


def geometry_masks(cases, size, place):
    """F0 only. Messages 0 and 2 split columns (walls between columns 7|8 and 15|0), 1 and 3 split rows.
    place 'dK': the patch lies inside one domain at distance K from its nearest wall; 'cross': it straddles a
    wall symmetrically. Domain, wall side and the position along the wall are addressed per case."""
    out = np.zeros((len(cases), 16, 16), bool)
    for i, c in enumerate(cases):
        g = address(D.TAG, *c.key(), "geometry", f"{size}", place)
        b = int(g.integers(0, 16))
        if place == "cross":
            a = (D.DOMAIN * (int(g.integers(0, 2)) + 1) - size // 2) % 16
        else:
            d = int(place[1:])
            dom, side = int(g.integers(0, 2)), int(g.integers(0, 2))
            a = dom * D.DOMAIN + (d if side == 0 else D.DOMAIN - size - d)
        ia, ib = np.arange(a, a + size) % 16, np.arange(b, b + size) % 16
        if c.message % 2 == 0:
            out[i][np.ix_(ib, ia)] = True
        else:
            out[i][np.ix_(ia, ib)] = True
    return out


def masks_for(cases, conds):
    return [None if not c.size else patch_masks(cases, c.size) if c.place == "random"
            else geometry_masks(cases, c.size, c.place) for c in conds]


def onsets(cases, kind):
    if kind == "random":
        return np.array([int(address(D.TAG, *c.key(), "onset").integers(*D.ONSET)) for c in cases])
    return np.ones(len(cases), int)


def turnover_events(cases, rate, updates):
    """Per case: arrays (t, flat site, newborn value) of cell replacements, as BR001 under BR002's tag."""
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
    """(cases, 16, 16): newborn body states for a kill lesion, addressed by (case, 'kill', size)."""
    return np.stack([D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{size}").standard_normal((16, 16)) for c in cases])


def bonds(R0, rel):
    """J for the four neighbour directions: sign(R0_i) sign(R0_j), or 1 (BR001's consensus)."""
    if not rel:
        return [np.ones_like(R0) for _ in SHIFTS]
    s = np.where(R0 >= 0, 1.0, -1.0)
    return [s * np.roll(s, sh, ax) for sh, ax in SHIFTS]


def kill_bonds(J, kill, relink):
    """Bonds with both ends among killed cells are lost (0), or re-form as +1 under relink; the rest stay."""
    return [np.where(kill & np.roll(kill, sh, ax), 1.0 if relink else 0.0, J[d]) for d, (sh, ax) in enumerate(SHIFTS)]


def bond_sum(J, r):
    """sum_j J_ij r_j / 4 in neighbours' order, so J = 1 reproduces mse.native.neighbours bit for bit."""
    return (J[0] * np.roll(r, 1, -2) + J[1] * np.roll(r, -1, -2) + J[2] * np.roll(r, 1, -1) + J[3] * np.roll(r, -1, -1)) / 4.0


def simulate(arm, conds, k, V, ema, R, R0, th, Z, XI, p, conserved, T, Tf, tau, masks, turn, born, cal=None):
    """Advance len(conds) x k branches WINDOW updates under one arm. masks[c]: (k,16,16) patch per condition
    (or None); turn[c]: per-case turnover events (or None); born[c]: kill newborn states (or None); cal: the
    write thresholds of panel C."""
    nc = len(conds)
    n = nc * k
    idx = np.tile(np.arange(k), nc)
    thb, Tb, Tfb, taub = th[idx], T[idx], Tf[idx], np.tile(tau, nc)
    mask = np.concatenate([masks[c] if masks[c] is not None else np.zeros((k, 16, 16), bool) for c in range(nc)])
    nb = np.concatenate([born[c] if born[c] is not None else np.zeros((k, 16, 16)) for c in range(nc)])
    kind = np.repeat([c.kind for c in conds], k)
    dur = np.repeat([c.duration for c in conds], k)
    cue = np.repeat([c.cue for c in conds], k)
    dmg = np.repeat([c.damage for c in conds], k)
    gain = NATIVE.gain if arm.reads else 0.0
    B = block_projection(R0, 4)[idx]
    R0b = R0[idx]
    J = bonds(R0b, arm.rel)
    v, e, r = V[idx].copy(), ema[idx].copy(), R[idx].copy()
    tag = np.zeros((n, 16, 16))
    latch = np.zeros((n, 16, 16), int)
    opened = np.zeros((n, 16, 16), bool)
    w_l1 = np.zeros(n)
    imp_stop = np.where(dur > 0, taub + dur, D.WINDOW + 1)
    win_stop = taub + D.WINDOW_P
    t_dmg = np.where(kind == "window", taub + D.WINDOW_DELAY, taub)
    held = (kind == "scar") | ((kind == "window") & (dmg == "scar"))
    flip_v = (kind == "lesion") | (kind == "wound") | ((kind == "window") & (dmg == "wound"))
    flip_r = (kind == "lesion") | (kind == "record")
    tagged = (kind == "wound") | (kind == "scar") | (kind == "window")
    for t in range(1, D.WINDOW + 1):
        start = t_dmg == t
        if start.any():
            m3 = mask & start[:, None, None]
            v = np.where(m3 & flip_v[:, None, None], -v, v)
            r = np.where(m3 & flip_r[:, None, None], -r, r)
            kill = m3 & (kind == "kill")[:, None, None]
            if kill.any():
                v, e, r = np.where(kill, nb, v), np.where(kill, nb, e), np.where(kill, 0.0, r)
                if arm.rel:
                    J = kill_bonds(J, kill, arm.relink)
            tag = np.where(m3 & tagged[:, None, None], 1.0, tag)
        scar = held & (t >= t_dmg)
        if scar.any():
            m3 = mask & scar[:, None, None]
            v = np.where(m3, -Tb, v)
            tag = np.where(m3, 1.0, tag)
        imp = (kind == "impose") & (t >= taub) & (t < imp_stop)
        if imp.any():
            v = np.where(imp[:, None, None], Tfb, v)
        v, e, vt = body_step(v, e, r, thb, Z[t - 1][idx], p, conserved, gain)
        gate = None
        if arm.write in ("phase", "phase_tags"):
            win = (cue & (t >= taub) & (t < win_stop))[:, None, None]
            gate = np.broadcast_to(win, v.shape) if arm.write == "phase" else win & (tag < D.TAG_GATE)
        elif arm.write != "none":
            mm = region(r - vt)
            mis = mm > cal["mismatch"]
            ok = None
            if arm.write == "duration":
                latch = np.where(region(vt - e) > cal["surprise"], D.LATCH_W, np.maximum(latch - 1, 0))
                ok = latch == 0
            elif arm.write == "tags":
                ok = tag < D.TAG_GATE
            if arm.hyst:
                opened = (opened & (mm > D.OFF * cal["mismatch"])) | (mis if ok is None else mis & ok)
                gate = opened & (tag < D.TAG_GATE) if arm.write == "tags" else opened
            else:
                gate = mis if ok is None else mis & ok
        tag = tag * (1.0 - D.TAG_DECAY)
        r_old = r
        if arm.eps > 0:
            r = r + arm.eps * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r)) + D.SIGMA_R * XI[t - 1][idx]
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
                        if not arm.clamp:            # the protected copy is privileged storage outside the cells
                            r[b, ii, jj] = 0.0
    return v, e, r, w_l1


def recipients(cases):
    births = np.stack([birth(D.TAG, cases, "recipient", i, "birth") for i in range(D.RECIPIENTS)], 1)
    Zr = np.stack([draws(cases, "recipient", i, "read", updates=D.READ_UPDATES) for i in range(D.RECIPIENTS)], 2)
    return births, Zr


def adopt_flip(r, T, Tf):
    """Agreement with the imposed message at the sites where it differs from the original."""
    flip = np.sign(Tf) != np.sign(T)
    return (((r > 0) == (Tf > 0)) & flip).sum((-2, -1)) / np.maximum(flip.sum((-2, -1)), 1)
