"""NL001's tissue: LR001's record of relations alone, on a 64 x 64 sheet, with codes at the region and block scales.

One update, in order (lr001.sim.step's arithmetic): the record's self-correction through its bonds,
    r <- r + EPS [r (1 - (r/R*)^2) + KR (bond_sum(J, r) - r)] + SIGMA_R xi,
then L2's increment, k2 sigma (B2 - mean_u) with mean_u the region's mean of sigma r over live frame cells (LR001's
gauge code; B2 the absolute store, or the relative store times the sign of L3's store), then L3's increment,
k3 (B3 - block mean of r) (BR002's plain code at the block scale; B3 the block store, or the block mean implied by
L2's absolute stores), one clip to [-2, 2]. Branches are batched branch-major (index = branch x cases + case); every
branch of a case reads the same record noise, so arms and events are paired.

The gauge frame sigma of a region is +1 at its corner, then along its first row by H and down each column by W
(lr001.sim.gauge_frame's construction, at any side). Its paths stay inside the region, so events that flip only bonds
between regions leave every frame unchanged.
"""
from __future__ import annotations

import numpy as np

from lr001.sim import edges_from, halves
from mse.assay import enrol
from mse.native import address
from msegrid.core import Stream, bond_sum, bonds, bproj

from . import design as D

N = D.SIDE
L2_ID = {"none": 0, "abs": 1, "rel": 2}
L3_ID = {"none": 0, "abs": 1, "derived": 2}


def cases_for(block, purpose):
    return enrol([block], D.MESSAGES, D.PARENTS, purpose)


def template(case, tag=D.TAG):
    """+-1 pattern with structure at every scale: balanced block signs; MINORITY_REGIONS regions per block with the
    block's opposite sign; MINORITY_CELLS cells per region with the region's opposite sign."""
    g = address(tag, *case.key(), "pattern")
    nb, nr, nc = N // D.BLOCK, D.BLOCK // D.REGION, D.REGION
    sB = np.where(g.permutation(nb * nb) < nb * nb // 2, 1.0, -1.0).reshape(nb, nb)
    T = np.zeros((N, N))
    for bi in range(nb):
        for bj in range(nb):
            mr = g.permutation(nr * nr) < D.MINORITY_REGIONS
            for q in range(nr * nr):
                ri, rj = divmod(q, nr)
                sR = -sB[bi, bj] if mr[q] else sB[bi, bj]
                mc = g.permutation(nc * nc) < D.MINORITY_CELLS
                i0, j0 = bi * D.BLOCK + ri * D.REGION, bj * D.BLOCK + rj * D.REGION
                T[i0:i0 + nc, j0:j0 + nc] = np.where(mc, -sR, sR).reshape(nc, nc)
    return T


def gauge_frame(H, W, region=D.REGION):
    """sigma per region: +1 at the region's corner, then along its first row by H and down each column by W (the
    product of the bond signs along that path; 0 beyond a missing bond)."""
    s = np.zeros_like(H)
    s[..., 0::region, 0::region] = 1.0
    for dj in range(region - 1):
        s[..., 0::region, dj + 1::region] = s[..., 0::region, dj::region] * H[..., 0::region, dj::region]
    for di in range(region - 1):
        s[..., di + 1::region, :] = s[..., di::region, :] * W[..., di::region, :]
    return s


def unit_sign(x, size):
    """The sign of each size x size unit's mean of sign(x), (..., n, n)."""
    n = x.shape[-1] // size
    return np.sign(np.sign(x).reshape(*x.shape[:-2], n, size, n, size).mean(axis=(-3, -1)))


def unit_mask(i, j, size, n=N):
    m = np.zeros((n, n), bool)
    m[i * size:(i + 1) * size, j * size:(j + 1) * size] = True
    return m


def prepare(cases, tag=D.TAG):
    """The templates, the exact record R0 = T, its bonds, the frames and the three stores: the absolute region codes
    Bg (bproj(sigma R0) over each region), the relative ones (Bg times the sign of the block store), the block store
    B3 (bproj(R0) over each block)."""
    T = D.AMPLITUDE * np.stack([template(c, tag) for c in cases])
    R0 = T.copy()
    H, W = edges_from(bonds(R0, True))
    sigma = gauge_frame(H, W)
    Bg = bproj(sigma * R0, D.REGION)
    B3 = bproj(R0, D.BLOCK)
    Brel = Bg * np.sign(B3)
    return T, R0, H, W, sigma, Bg, Brel, B3


def event_units(cases, tag=D.TAG):
    """Per case, addressed by (case, 'event'): the block of B and C3, the four regions of R (outside that block; the
    first is C2's), and F's sites (FINE_SHARE of the cells, anywhere)."""
    nb, nr = N // D.BLOCK, N // D.REGION
    out = []
    for c in cases:
        g = address(tag, *c.key(), "event")
        b = int(g.integers(0, nb * nb))
        bi, bj = divmod(b, nb)
        regs = []
        for q in g.permutation(nr * nr):
            ri, rj = divmod(int(q), nr)
            if ri // (D.BLOCK // D.REGION) == bi and rj // (D.BLOCK // D.REGION) == bj:
                continue
            regs.append((ri, rj))
            if len(regs) == D.N_REGIONS:
                break
        sites = g.permutation(N * N)[: int(round(D.FINE_SHARE * N * N))]
        fm = np.zeros(N * N, bool)
        fm[sites] = True
        kb = int(g.integers(0, nb * nb))                           # K: a 2 x 2 square of regions in a block, taken
        ki, kj = divmod(kb, nb)                                    # from those that hold a minority region
        up = D.BLOCK // D.REGION
        sq = [(ki * up + a, kj * up + b_) for a in range(0, up, D.KILL) for b_ in range(0, up, D.KILL)]
        out.append({"block": (bi, bj), "regions": regs, "fine": fm.reshape(N, N), "kill_block": (ki, kj),
                    "kill_squares": sq, "kill_pick": int(g.integers(0, len(sq)))})
    return out


def kill_square(u, T):
    """The KILL x KILL square of regions to kill: among the kill block's squares, the first (from kill_pick) that
    holds a minority region of the template; (top-left region row, column)."""
    reg = unit_sign(T, D.REGION)
    blk = unit_sign(T, D.BLOCK)
    up = D.BLOCK // D.REGION
    sq = u["kill_squares"]
    for q in range(len(sq)):
        ri, rj = sq[(u["kill_pick"] + q) % len(sq)]
        s = blk[ri // up, rj // up]
        if (reg[ri:ri + D.KILL, rj:rj + D.KILL] != s).any():
            return ri, rj
    return sq[u["kill_pick"]]


def flip_boundary(H, W, m):
    """Flip every bond with exactly one end in m (H joins (i, j)-(i, j+1); W joins (i, j)-(i+1, j))."""
    bh = m ^ np.roll(m, -1, -1)
    bw = m ^ np.roll(m, -1, -2)
    return np.where(bh, -H, H), np.where(bw, -W, W)


def kill_mask(u, T):
    ri, rj = kill_square(u, T)
    m = np.zeros((N, N), bool)
    m[ri * D.REGION:(ri + D.KILL) * D.REGION, rj * D.REGION:(rj + D.KILL) * D.REGION] = True
    return m


def apply_event(event, u, r, H, W, Bg, Brel, B3, T):
    """One case's state after an event (copies). B: the block's records, boundary bonds and absolute region codes
    flipped (relative codes keep their relations); R: each region's records and boundary bonds flipped; F: the fine
    sites' records flipped; C3: the block store flipped; C2: the first R region's stores flipped; K: a square of
    KILL x KILL regions killed, every copy there lost (records 0, the bonds between two dead cells 0, the dead
    regions' codes 0), the block store kept by the block's other cells."""
    r, H, W, Bg, Brel, B3 = (x.copy() for x in (r, H, W, Bg, Brel, B3))
    if event in ("B", "FRB"):
        m = unit_mask(*u["block"], D.BLOCK)
        r[m] = -r[m]
        H, W = flip_boundary(H, W, m)
        Bg[m] = -Bg[m]
    if event in ("R", "FRB"):
        for (ri, rj) in u["regions"]:
            m = unit_mask(ri, rj, D.REGION)
            r[m] = -r[m]
            H, W = flip_boundary(H, W, m)
    if event in ("F", "FRB"):
        r[u["fine"]] = -r[u["fine"]]
    if event == "K":
        m = kill_mask(u, T)
        r[m] = 0.0
        H = np.where(m & np.roll(m, -1, -1), 0.0, H)
        W = np.where(m & np.roll(m, -1, -2), 0.0, W)
        Bg[m] = 0.0
        Brel[m] = 0.0
    if event == "C3":
        m = unit_mask(*u["block"], D.BLOCK)
        B3[m] = -B3[m]
    if event == "C2":
        m = unit_mask(*u["regions"][0], D.REGION)
        Bg[m] = -Bg[m]
        Brel[m] = -Brel[m]
    return r, H, W, Bg, Brel, B3


def step(r, xi, J, sigma, Bg, Brel, B3, l2, l3, k2, k3):
    """One update; l2, l3, k2, k3: (branches x cases, 1, 1)."""
    r = r + D.EPS * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r)) + D.SIGMA_R * xi
    live = sigma != 0
    mean_u = bproj(sigma * r, D.REGION) / np.maximum(bproj(live * 1.0, D.REGION), 1.0 / D.REGION ** 2)
    t2 = np.where(l2 == 1, Bg, Brel * np.sign(B3))
    inc = np.where(l2 > 0, k2 * sigma * (t2 - mean_u), 0.0)
    t3 = np.where(l3 == 1, B3, bproj(sigma * Bg, D.BLOCK))
    inc = inc + np.where(l3 > 0, k3 * (t3 - bproj(r, D.BLOCK)), 0.0)
    return np.clip(r + inc, -2.0, 2.0)


ENDS = ("cell_err", "region_err", "block_err", "min_cell_ok", "min_region_ok", "fine_ok", "regions_ok", "block_ok",
        "c2_ok", "bmin_ok", "kill_ok", "kill_reg_ok", "kill_min_ok", "e_fine", "e_regional", "e_block", "e_sheet")


def masks(T, units):
    """Per case: minority cells (against their region's sign), minority regions (against their block's sign, as
    region units), and the event units."""
    k = T.shape[0]
    sT = np.sign(T)
    reg = unit_sign(T, D.REGION)                                   # (k, 16, 16)
    blk = unit_sign(T, D.BLOCK)                                    # (k, 4, 4)
    min_cell = sT != np.repeat(np.repeat(reg, D.REGION, -2), D.REGION, -1)
    up = D.BLOCK // D.REGION
    min_reg = reg != np.repeat(np.repeat(blk, up, -2), up, -1)    # (k, 16, 16)
    rmask = np.zeros_like(reg, dtype=bool)
    bmask = np.zeros_like(blk, dtype=bool)
    c2 = np.zeros_like(reg, dtype=bool)
    fine = np.stack([u["fine"] for u in units])
    kill = np.stack([kill_mask(u, T[j]) for j, u in enumerate(units)])
    kreg = unit_sign(kill * 1.0, D.REGION) > 0                     # the killed regions (wholly inside the square)
    for j, u in enumerate(units):
        for (ri, rj) in u["regions"]:
            rmask[j, ri, rj] = True
        c2[j][u["regions"][0]] = True
        bmask[j][u["block"]] = True
    inblk = np.repeat(np.repeat(bmask, up, -2), up, -1)             # the event block's regions
    return {"min_cell": min_cell, "min_reg": min_reg, "fine": fine, "regions": rmask, "block": bmask, "c2": c2,
            "reg": reg, "blk": blk, "kill": kill, "kreg": kreg, "kmin": kreg & min_reg, "bmin": inblk & min_reg}


def frac(mask, ok, axes):
    n = mask.sum(axes)
    return np.where(n > 0, (mask & ok).sum(axes) / np.maximum(n, 1), np.nan)


def read(r, T, mk):
    """Endpoints of one read, per sheet (branches x cases)."""
    ok = np.sign(r) == np.sign(T)
    reg_ok = unit_sign(r, D.REGION) == mk["reg"]
    blk_ok = unit_sign(r, D.BLOCK) == mk["blk"]
    e = (np.sign(r) != np.sign(T)).astype(float)
    p4, p16 = bproj(e, D.REGION), bproj(e, D.BLOCK)
    dc = e.mean((-2, -1), keepdims=True)
    return {"cell_err": 1 - ok.mean((-2, -1)), "region_err": 1 - reg_ok.mean((-2, -1)),
            "block_err": 1 - blk_ok.mean((-2, -1)),
            "min_cell_ok": frac(mk["min_cell"], ok, (-2, -1)), "min_region_ok": frac(mk["min_reg"], reg_ok, (-2, -1)),
            "fine_ok": frac(mk["fine"], ok, (-2, -1)), "regions_ok": frac(mk["regions"], reg_ok, (-2, -1)),
            "block_ok": frac(mk["block"], blk_ok, (-2, -1)), "c2_ok": frac(mk["c2"], reg_ok, (-2, -1)),
            "bmin_ok": frac(mk["bmin"], reg_ok, (-2, -1)),
            "kill_ok": frac(mk["kill"], ok, (-2, -1)), "kill_reg_ok": frac(mk["kreg"], reg_ok, (-2, -1)),
            "kill_min_ok": frac(mk["kmin"], reg_ok, (-2, -1)),
            "e_fine": ((e - p4) ** 2).mean((-2, -1)), "e_regional": ((p4 - p16) ** 2).mean((-2, -1)),
            "e_block": ((p16 - dc) ** 2).mean((-2, -1)), "e_sheet": (dc ** 2).mean((-2, -1))}


def run(cases, labels, window=D.WINDOW, reads=D.READS, tag=D.TAG):
    """labels: [(arm, event)]. Returns endpoints {name: (reads, branches, cases)} and final r (branches, cases, N, N)."""
    k, nb = len(cases), len(labels)
    T, R0, H0, W0, sigma, Bg0, Brel0, B30 = prepare(cases, tag)
    units = event_units(cases, tag)
    st = {x: [] for x in ("r", "H", "W", "Bg", "Brel", "B3")}
    for arm, event in labels:
        for j in range(k):
            out = apply_event(event, units[j], R0[j], H0[j], W0[j], Bg0[j], Brel0[j], B30[j], T[j])
            for name, x in zip(("r", "H", "W", "Bg", "Brel", "B3"), out):
                st[name].append(x)
    r, H, W, Bg, Brel, B3 = (np.stack(st[x]) for x in ("r", "H", "W", "Bg", "Brel", "B3"))
    J = halves(H, W)
    idx = np.tile(np.arange(k), nb)
    sig, Tb = gauge_frame(H, W), T[idx]           # the frame of each branch's bonds (events between regions keep it)
    col = lambda f: np.repeat([f(a) for a, _ in labels], k)[:, None, None]
    l2, l3 = col(lambda a: L2_ID[a.l2]), col(lambda a: L3_ID[a.l3])
    k2, k3 = col(lambda a: a.k2), col(lambda a: a.k3)
    mk0 = masks(T, units)
    mk = {key: np.concatenate([v] * nb) for key, v in mk0.items()}
    xs = Stream(tag, cases, "record-noise", side=N)
    ends = {e: [] for e in ENDS}
    xb = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            xb = xs.take(D.CHUNK)
        r = step(r, xb[i][idx], J, sig, Bg, Brel, B3, l2, l3, k2, k3)
        if t in reads:
            for e, v in read(r, Tb, mk).items():
                ends[e].append(v)
    return {e: np.array(v).reshape(len(reads), nb, k) for e, v in ends.items()}, r.reshape(nb, k, N, N)
