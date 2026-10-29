"""Founders, the genome's controller and batched chains of lives for OR001.

The physics is mse.native unchanged. The genome's body drift is
    gs (R - V~) + gr P4(R - V~) + gh center(P8(R - V~)),
times the developmental multiplier during a newborn's first T_DEV updates, then mean removal and
clipping as in mse.engine; the record is written as R <- R - rho_w (R - V) (no mean removal, as the
native reference route) and Q captures the body passively. The controller reads only V-tilde and
R. Branches are genome-major: index = genome x cases + case.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from mse.assay import REFERENCE_BOUND, Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE, address, center, moving_average, sheet
from mse.ops import bands, block_projection

from . import design as O


def params(sigma):
    return replace(NATIVE, sigma=sigma)


def founders(tag, family, sigma, blocks, purpose, parents):
    """Acquired, released founders (ME002's acquisition), their theta and targets."""
    p = params(sigma)
    cases = enrol(blocks, O.MESSAGES, parents, purpose)
    T = O.TEMPLATES[family][[c.message for c in cases]]
    th = theta(tag, cases, p, per_tissue=True)
    V = birth(tag, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(tag, cases, "settle"), Route(capture=None), O.SETTLE, p)
    s = run(s, th, Noise(tag, cases, "teach"), Route(capture=None), O.TEACH, p, imposed=T)
    s = run(s, th, Noise(tag, cases, "release"), ROUTES["body"], O.RELEASE, p)
    return cases, State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, p, T


def step(V, ema, R, Q, th, z, p, gs, gr, gh, rho):
    """One update under the genome's controller; returns the new state and the body dose."""
    Vt = sheet(V, th, z, p)
    ema = moving_average(ema, Vt, p)
    d = R - Vt
    drift = gs * d + gr * block_projection(d, 4) + gh * center(block_projection(d, 8))
    drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    Vn = np.clip(Vt + p.dt * drift, -p.bound, p.bound)
    R = R - rho * (R - Vn)
    Q = Q + p.rho * (Vn - Q)
    return Vn, ema, R, Q, np.abs(Vn - Vt).sum(axis=(-2, -1))


def field(tag, cases, target, bands_, g):
    """Per case: a unit Gaussian field in that case's band, scaled to INJURY_RMS (address
    (case, 'gen', g, 'damage', target, band))."""
    out = []
    for c, b in zip(cases, bands_):
        x = bands(address(tag, *c.key(), "gen", g, "damage", target, b).standard_normal((16, 16)))[b]
        out.append(x * (O.INJURY_RMS / np.sqrt((x ** 2).mean())))
    return np.stack(out)


def injuries(tag, cases, g, kind):
    """(onset (k,), dV (k,16,16) or None, dR or None) for one life; shared by every genome."""
    if kind == "none":
        return None
    tau = np.array([int(address(tag, *c.key(), "gen", g, "onset").integers(*O.ONSET)) for c in cases])
    band = [O.BANDS[int(address(tag, *c.key(), "gen", g, "band").integers(3))] for c in cases]
    if kind == "body":
        loc = ["body"] * len(cases)
    elif kind == "record":
        loc = ["reference"] * len(cases)
    else:
        edges = np.cumsum([w for _, w in O.MIX])
        u = [float(address(tag, *c.key(), "gen", g, "loc").random()) for c in cases]
        loc = [O.MIX[int(np.searchsorted(edges, x, side="right"))][0] for x in u]
    fb, fr = field(tag, cases, "body", band, g), field(tag, cases, "reference", band, g)
    on_b = np.array([x in ("body", "both") for x in loc])[:, None, None]
    on_r = np.array([x in ("reference", "both") for x in loc])[:, None, None]
    return tau, np.where(on_b, fb, 0.0), np.where(on_r, fr, 0.0)


def chain(tag, genes, cases, s0, th, p, T, kind, generations):
    """Run every genome's lineage: the founder (an adult) then `generations` newborns. Returns
    per life (generations + 1, genomes, cases): body qualified agreement and sign agreement with
    the own target, packet sign agreement, and body dose."""
    P, k = len(genes["g_site"]), len(cases)
    n = P * k
    idx = np.tile(np.arange(k), P)
    col = lambda v: np.repeat(np.asarray(v, float), k)[:, None, None]
    gs, gr, gh, rho, w = (col(genes[g]) for g in ("g_site", "g_region", "g_sheet", "rho_w", "w"))
    mdev = col(genes["m_dev"])
    thb, Tb = th[idx], T[idx]
    out = {key: [] for key in ("v_qual", "v_sign", "p_sign", "dose")}
    V, ema, R = s0.V[idx], s0.ema[idx], s0.R[idx]
    for g in range(generations + 1):
        if g:
            nb = birth(tag, cases, "gen", g, "birth")[idx]
            V, ema = nb, nb.copy()
        Q = np.zeros((n, 16, 16))
        Z = np.stack([address(tag, *c.key(), "gen", g, "life").standard_normal((O.LIFE, 16, 16)) for c in cases], 1)
        inj = injuries(tag, cases, g, kind)
        dose = np.zeros(n)
        for t in range(1, O.LIFE + 1):
            if inj is not None:
                m = (inj[0] == t)[idx]
                if m.any():
                    m3 = m[:, None, None]
                    V = np.where(m3, np.clip(V + inj[1][idx], -NATIVE.bound, NATIVE.bound), V)
                    R = np.where(m3, np.clip(R + inj[2][idx], -REFERENCE_BOUND, REFERENCE_BOUND), R)
            boost = mdev if (g and t <= O.T_DEV) else 1.0
            V, ema, R, Q, dd = step(V, ema, R, Q, thb, Z[t - 1][idx], p, gs * boost, gr * boost, gh * boost, rho)
            dose += dd
        packet = w * R + (1.0 - w) * Q
        m, a = (V > 0) == (Tb > 0), np.abs(V) > 0.2
        out["v_qual"].append((m & a).mean((-2, -1)).reshape(P, k))
        out["v_sign"].append(m.mean((-2, -1)).reshape(P, k))
        out["p_sign"].append(((packet > 0) == (Tb > 0)).mean((-2, -1)).reshape(P, k))
        out["dose"].append(dose.reshape(P, k))
        R = packet
    return {key: np.stack(v) for key, v in out.items()}


def fitness(res, cost):
    """Mean body qualified agreement over generations 1.. minus cost x mean dose per life (/1e4)."""
    return res["v_qual"][1:].mean((0, 2)) - cost * res["dose"].mean((0, 2)) / O.DOSE_SCALE
