"""SC001's tissue (DRAFT): cellpop's vacancy lattice with DL001's bodies and the relational record.

Preparation is DL003's and DL002's recipe under SC001's tag (msegrid.acquire; S4 stripes or F0 domains on a 32-site
sheet). Every run advances one body under every arm or condition as branches (arm-major: index = arm x cases + case),
all reading the case's streams, so arms are paired within a case: in panel G, grow, nb and none share one division
history (the same geometry) and differ only in what daughters carry or what the boundary reads.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from cellpop import core as C
from cellpop.loop import Branches, evolve
from dl001 import sim as S
from fn001.sim import function, topology, walls
from lr001.sim import bond_err, edges_from
from mse.assay import enrol
from mse.native import NATIVE, address
from msegrid.core import acquire, birth, bonds

from . import design as D


def prepare(pattern, block, purpose, tag=D.TAG):
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = np.stack([D.AMPLITUDE * S.template(pattern, c.message, D.SIDE, block) for c in cases])
    V, ema, R0, th = acquire(tag, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), D.SIDE,
                             settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T


def ring_dist(lines):
    ar = np.arange(D.SIDE)
    return (np.abs((ar[:, None] - np.asarray(lines)[None, :] + D.SIDE // 2) % D.SIDE - D.SIDE // 2)).min(1)


def geometry(cases, tag=D.TAG):
    """DL003's boundaries: par, two adjacent lines straddling a wall of the stripes; perp, two adjacent lines across
    them. Per case: masks and ring distance from the boundary (0 on it)."""
    n, k = D.SIDE, len(cases)
    masks = {g: np.zeros((k, n, n), bool) for g in D.GEOMS}
    dist = {g: np.zeros((k, n, n), int) for g in D.GEOMS}
    for j, c in enumerate(cases):
        g = address(tag, *c.key(), "geometry")
        w = int(g.integers(0, n // 4))
        wall = [(4 * w - 1) % n, (4 * w) % n]
        o = int(g.integers(0, n))
        across = [o, (o + 1) % n]
        dw, da = ring_dist(wall), ring_dist(across)
        if c.message % 2 == 0:
            masks["par"][j][:, wall] = True
            dist["par"][j] = np.broadcast_to(dw[None, :], (n, n))
            masks["perp"][j][across, :] = True
            dist["perp"][j] = np.broadcast_to(da[:, None], (n, n))
        else:
            masks["par"][j][wall, :] = True
            dist["par"][j] = np.broadcast_to(dw[:, None], (n, n))
            masks["perp"][j][:, across] = True
            dist["perp"][j] = np.broadcast_to(da[None, :], (n, n))
    return masks, dist


def patch(cases, tag=D.TAG):
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        a, b = address(tag, *c.key(), "patch").integers(0, D.SIDE, 2)
        out[j][np.ix_(np.arange(a, a + D.PATCH) % D.SIDE, np.arange(b, b + D.PATCH) % D.SIDE)] = True
    return out


def newborn(cases, tag=D.TAG):
    return np.stack([D.KILL_SD * address(tag, *c.key(), "newborn").standard_normal((D.SIDE, D.SIDE)) for c in cases])


def agree(x, T, m):
    """Agreement of sign(x) with sign(T) over the sites in m (nan where m is empty)."""
    n = m.sum((-2, -1))
    return np.where(n > 0, (((x > 0) == (T > 0)) & m).sum((-2, -1)) / np.maximum(n, 1), np.nan)


def template_function(T):
    s = np.where(T > 0, 1.0, -1.0)
    return [topology(x)[:2] for x in s], walls(s)


def decay_for(lam, kappa=D.KAPPA):
    return 2.0 * kappa * (np.cosh(1.0 / lam) - 1.0)


def growth_axis(cases, geo):
    """True where the growth runs along the rows axis (lines of growth are columns; the lines that fill are rows)."""
    return np.array([(c.message % 2 == 0) == (geo == "perp") for c in cases])


def smooth_schedule(cases, geo, speed, tag=D.TAG):
    """The smooth arm's scheduled divisions, per case: each site at distance d >= 1 from the boundary is filled at
    (d - 1) * speed + floor((rank + 1) * speed / SIDE), rank being its place in a random order of its line (drawn per
    case), by a daughter of its neighbour at distance d - 1. Line d is complete at d * speed. Returns (tfill, pdir)."""
    bd = geometry(cases, tag)[1][geo]
    pdir = np.zeros(bd.shape, np.int8)
    for d in range(4):
        pdir = np.where((C.at(bd, d) == bd - 1) & (bd >= 1), d, pdir)
    along = growth_axis(cases, geo)[:, None, None]
    keys = np.stack([address(tag, *c.key(), "smooth-order").random((D.SIDE, D.SIDE)) for c in cases])
    rank_row = np.argsort(np.argsort(keys, -1), -1)          # order within each row
    rank_col = np.argsort(np.argsort(keys, -2), -2)          # order within each column
    rank = np.where(along, rank_row, rank_col)
    tfill = np.where(bd >= 1, (bd - 1) * speed + ((rank + 1) * speed) // D.SIDE, -1)
    return tfill, pdir


# panel G ----------------------------------------------------------------------------------------------------------

def run_G(body, geo, arms, cases, R0, th, T, theta, tag=D.TAG, window=D.WINDOW, snaps=D.SNAPS):
    k, na = len(cases), len(arms)
    n = k * na
    idx = np.tile(np.arange(k), na)
    masks, dist = geometry(cases, tag)
    bm, bd = masks[geo][idx], dist[geo][idx]
    nbv = birth(tag, cases, "newborn-sheet", side=D.SIDE)[idx]
    seed = bd == 0
    one = np.ones((n, 1, 1))
    per = lambda f: np.repeat([f(a) for a in arms], k)[:, None, None]
    mode = np.repeat([a.mode for a in arms], k)
    anchored = per(lambda a: a.mode not in ("none", "diff"))
    st = {"occ": seed.copy(), "V": np.where(seed, nbv, 0.0), "E": np.where(seed, nbv, 0.0)}
    front = (mode == "front")[:, None, None]
    tfill, pdir = np.full(bd.shape, -1), np.zeros(bd.shape, np.int8)
    for i, a in enumerate(arms):
        if a.mode == "smooth":
            sl = slice(i * k, (i + 1) * k)
            tfill[sl], pdir[sl] = smooth_schedule(cases, geo, a.speed, tag)
    br = Branches(gain=np.where(anchored & bm, D.G_ANCHOR, 0.0), read=R0[idx],
                  p_div=per(lambda a: 0.0 if a.mode in ("front", "smooth") else 1.0 / a.speed),
                  inherit=per(lambda a: a.mode != "nb").astype(bool), newborn=nbv,
                  p_die=per(lambda a: D.TURN if a.mode == "turn" else 0.0),
                  p_swap=per(lambda a: D.TURN if a.mode == "turn" else 0.0), protected=seed,
                  fdist=np.where(front, bd, -1), every=np.repeat([a.speed for a in arms], k).astype(float),
                  tfill=tfill, pdir=pdir,
                  kappa=per(lambda a: D.KAPPA if a.mode == "diff" else 0.0),
                  decay=per(lambda a: decay_for(a.lam) if a.mode == "diff" else 0.0),
                  src=bm & per(lambda a: a.mode == "diff").astype(bool), src_val=np.where(R0[idx] > 0, 1.0, -1.0),
                  g_sig=per(lambda a: D.G_SIG if a.mode == "diff" else 0.0))
    Tb = T[idx]
    far = (bd >= D.FAR[0]) & (bd < D.FAR[1])
    near = (bd >= D.NEAR[0]) & (bd <= D.NEAR[1])
    out = {key: [] for key in ("sign", "filled", "far", "near", "shift", "spacing")}
    tr = {"t_filled": [], "t_sign": [], "t_rough": []}
    # the growth axis: perp grows across its boundary rows (kinds 0, 2) or columns (kinds 1, 3); par the other way
    along = growth_axis(cases, geo)[idx]

    def observe(t, s, sig):
        occ = s["occ"]
        if t % D.TRACE == 0:
            tr["t_filled"].append(occ.mean((-2, -1)))
            tr["t_sign"].append(agree(s["V"], Tb, occ))
            per_line = np.where(along[:, None], occ.sum(-2), occ.sum(-1))      # cells grown in each line of growth
            tr["t_rough"].append(per_line.std(-1) / 2.0)                       # the front's roughness (two fronts)
        if t in snaps:
            out["sign"].append(agree(s["V"], Tb, occ))
            out["filled"].append(occ.mean((-2, -1)))
            out["far"].append(agree(s["V"], Tb, occ & far))
            out["near"].append(agree(s["V"], Tb, occ & near))
            out["shift"].append(S.best_shift(s["V"], Tb))
            out["spacing"].append(S.spacing(s["V"]))
    stf, _ = evolve(body, st, br, cases, (th * theta)[idx], tag, ("future", "G"), window, sigma=D.SIGMA,
                    chunk=D.CHUNK, observe=observe)
    res = {key: np.array(v) for key, v in {**out, **tr}.items()}
    res["profile"] = np.stack([agree(stf["V"], Tb, stf["occ"] & (bd == d)) for d in range(D.DMAX + 1)], -1)
    top, tw = template_function(T)
    res["intact"], res["defects"], res["islands"], res["walls"] = function(stf["V"], [top[i] for i in idx], tw[idx])
    res.update(V=stf["V"], occ=stf["occ"])
    return res


# panel R ----------------------------------------------------------------------------------------------------------

def run_R(body, conds, cases, V0, ema0, R0, th, T, theta, tag=D.TAG, window=D.WINDOW, reads=D.READS_R):
    """Advance one body under every condition (grouped by bond-flip rate, one evolve per rate); the event at t = 0."""
    k = len(cases)
    m, nb = patch(cases, tag), newborn(cases, tag)
    H0, W0 = edges_from(bonds(R0, True))
    top, tw = template_function(T)
    res = {}
    for rate in sorted({c.rate for c in conds}):
        sub = [c for c in conds if c.rate == rate]
        nc = len(sub)
        idx = np.tile(np.arange(k), nc)
        per = lambda f: np.repeat([f(c) for c in sub], k)[:, None, None]
        mode = np.repeat([c.mode for c in sub], k)[:, None, None]
        mb, nbb = m[idx], nb[idx]
        st = {"occ": np.ones((nc * k, D.SIDE, D.SIDE), bool), "V": V0[idx].copy(), "E": ema0[idx].copy(),
              "r": R0[idx].copy(), "H": H0[idx].copy(), "W": W0[idx].copy(),
              "Hb": D.STRENGTH0 * H0[idx], "Wb": D.STRENGTH0 * W0[idx]}
        reset = (mode == "reset") & mb
        st["V"], st["E"], st["r"] = np.where(reset, nbb, st["V"]), np.where(reset, nbb, st["E"]), np.where(reset, 0.0, st["r"])
        st = C.untrain(st, reset)
        st = C.clear(st, np.isin(mode, ("regrow", "regrow-nb")) & mb)
        rec_t = per(lambda c: c.teacher == "record+parity").astype(bool)
        br = Branches(gain=np.full(st["V"].shape, D.GAIN), learn_record=rec_t, learn_body=~rec_t, parity=rec_t,
                      p_div=per(lambda c: c.speed if c.mode.startswith("regrow") else 0.0),
                      inherit=per(lambda c: c.mode == "regrow").astype(bool), newborn=nbb)
        Tb = T[idx]
        out = {key: [] for key in ("patch", "r_patch", "filled", "sign", "r_sign", "bond_err")}
        tr = {"t_patch": [], "t_r_patch": []}

        def observe(t, s, sig):
            occ = s["occ"]
            if t % D.TRACE == 0:
                tr["t_patch"].append(agree(s["V"], Tb, occ & mb))
                tr["t_r_patch"].append(agree(s["r"], Tb, occ & mb))
            if t in reads:
                out["patch"].append(agree(s["V"], Tb, occ & mb))
                out["r_patch"].append(agree(s["r"], Tb, occ & mb))
                out["filled"].append((occ & mb).sum((-2, -1)) / mb.sum((-2, -1)))
                out["sign"].append(agree(s["V"], Tb, occ))
                out["r_sign"].append(agree(s["r"], Tb, occ))
                out["bond_err"].append(bond_err(s["H"], s["W"], H0[idx], W0[idx]))
        stf, _ = evolve(body, st, br, cases, (th * theta)[idx], tag, ("future",), window, rate=rate, eps=D.EPS,
                        kr=D.KR, sigma_r=D.SIGMA_R, kc=D.KC, eta=D.ETA, sigma=D.SIGMA, chunk=D.CHUNK, observe=observe)
        part = {key: np.array(v) for key, v in {**out, **tr}.items()}
        part["intact"], part["defects"], part["islands"], part["walls"] = function(stf["V"], [top[i] for i in idx], tw[idx])
        part.update(V=stf["V"], r=stf["r"], H=stf["H"], W=stf["W"], occ=stf["occ"])
        for c_i, c in enumerate(sub):
            sl = slice(c_i * k, (c_i + 1) * k)
            res[c.name] = {key: (v[..., sl] if v.ndim == 2 and key not in ("V", "r", "H", "W", "occ") else v[sl])
                           for key, v in part.items()}
    return res
