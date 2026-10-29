"""Qualification of SC001 on the preflight (engineering) shards; criteria fixed in advance.

python -m sc001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete: every shard at its declared shapes; no infinite value; at the last read every endpoint is defined
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states (NaN equal to NaN)
Q3  engine: on a full sheet with no events, cellpop's loop equals dl001.sim.run (anchors and the record's pull),
    lr004.sim.run (record+parity and body teachers, p_b = 1e-3) and dl003.sim.run (prescribed fronts), bit for bit,
    over the full window
Q4  independent replay: per-site loops (the body with conjugate gradients for the inhibitor, no FFT; division by
    each cell's own draws, direction choice and conflicts; inheritance; untrained contacts; the record's bond noise
    with its own cut, own bond sums and Hebbian relearning; the diffusing signal's Laplacian, decay and sources) on
    the run's addressed streams reproduce three full branches (a growth branch, a regrowth branch with the record, a
    diffusion branch) within 1e-8, with occupancy and bonds exact
Q5  aliases exact: grow, nb, none and both diff arms share their occupancy history (filled and roughness traces) in
    every case; front/100 and smooth/100 fill exactly their schedules (one line per 100 updates); regrow and
    regrow-nb at each speed share their refilling; record+parity's record (values and bonds) is the same on both bodies
Q6  reanalysis: the last read's endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy on synthetic sheets: division places a daughter in the chosen empty neighbour, copying or newborn, with
    untrained contacts; death empties and never touches protected cells; exchange swaps and untrains; contacts stay
    consistent over random events; scheduled fill needs its parent; the smooth schedule completes line d at d x 100;
    diffusion's steady line profile has the declared decay length and stops at empty sites
Q8  geometry: the par boundary straddles a wall and the perp boundary crosses every stripe; each distance 0-15 has two
    lines; the patch is 8 x 8; the templates are S4 stripes of period 8 and F0 two domains
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
from statistics import NormalDist  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from cellpop import core as C  # noqa: E402
from cellpop.loop import Branches, evolve  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S1  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl003 import design as D3  # noqa: E402
from dl003 import sim as S3  # noqa: E402
from fn001.sim import function  # noqa: E402
from lr001.sim import bond_err, edges_from  # noqa: E402
from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from mse.assay import BIRTH_SCALE  # noqa: E402
from mse.native import NATIVE, address, center  # noqa: E402
from msegrid.core import bonds  # noqa: E402
from sc001 import design as D  # noqa: E402
from sc001 import sim  # noqa: E402
from sc001 import worker as W  # noqa: E402

FROZEN = LANE / "sc001" / "frozen"
WORKERS = 16
ARMS = [a.name for a in D.ARMS_G]
CONDS = [c.name for c in D.CONDS_R]
Q4_PICKS = (("G", "perp", "li4", "grow/100", 0), ("R", "S4_t0", "li4", "0.001/body/regrow@0.04", 1),
            ("G", "par", "dw", "diff6/100", 2))
SAME_GEOMETRY = ("grow/100", "nb/100", "none/100", "diff1.5/100", "diff6/100")


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def same(x, y):
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != y.shape:
        return False
    if np.issubdtype(x.dtype, np.floating):
        return bool(np.array_equal(x, y, equal_nan=True))
    return bool(np.array_equal(x, y))


# Q4: the independent per-site replay ---------------------------------------------------------------------------

def _draws(gen, kind, n):
    return gen.standard_normal((D.CHUNK, n, n)) if kind == "normal" else gen.random((D.CHUNK, n, n))


def replay(pick, block, tag=D.TAG, window=D.WINDOW):
    """One branch end to end with per-site code. Returns final V, occupancy and, for panel R, r, H, W."""
    panel, where, body, name, ci = pick
    n = D.SIDE
    pattern = "S4" if panel == "G" else D.parse_unit(where)[0]
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering", tag)
    case = cases[ci]
    key = case.key()
    alpha, L = DL.BODIES[body]
    p = replace(NATIVE, sigma=D.SIGMA)
    r0 = R0[ci]
    rec = panel == "R"
    occ = [[True] * n for _ in range(n)]
    V = V0[ci].astype(float).copy()
    r = r0.copy() if rec else None
    gain = [[D.GAIN if rec else 0.0] * n for _ in range(n)]
    sig = None
    if panel == "G":
        arm = next(a for a in D.ARMS_G if a.name == name)
        geo = where
        g = address(tag, *key, "geometry")
        w_ = int(g.integers(0, n // 4))
        wall = [(4 * w_ - 1) % n, (4 * w_) % n]
        o_ = int(g.integers(0, n))
        across = [o_, (o_ + 1) % n]
        lines = across if geo == "perp" else wall
        by_row = (case.message % 2 == 0) == (geo == "perp")          # the distance varies with the row index

        def dist(i, j):
            x = i if by_row else j
            return min(abs((x - l + n // 2) % n - n // 2) for l in lines)
        nb = BIRTH_SCALE * center(address(tag, *key, "newborn-sheet").standard_normal((n, n)))
        seed = [[dist(i, j) == 0 for j in range(n)] for i in range(n)]
        occ = [row[:] for row in seed]
        V = np.array([[nb[i, j] if seed[i][j] else 0.0 for j in range(n)] for i in range(n)])
        anchored = arm.mode not in ("none", "diff")
        gain = [[D.G_ANCHOR if (anchored and seed[i][j]) else 0.0 for j in range(n)] for i in range(n)]
        p_div, inherit = 1.0 / arm.speed, arm.mode != "nb"
        if arm.mode == "diff":
            kappa = D.KAPPA
            decay = 2.0 * kappa * (math.cosh(1.0 / arm.lam) - 1.0)
            sig = [[0.0] * n for _ in range(n)]
        stream = ("future", "G")
    else:
        cond = next(c for c in D.CONDS_R if c.name == name)
        a_, b_ = (int(x) for x in address(tag, *key, "patch").integers(0, n, 2))
        patch = [[((i - a_) % n) < D.PATCH and ((j - b_) % n) < D.PATCH for j in range(n)] for i in range(n)]
        nb = D.KILL_SD * address(tag, *key, "newborn").standard_normal((n, n))
        s = [[1.0 if r0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
        H = [[s[i][j] * s[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        Wd = [[s[i][j] * s[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        Hs = [[D.STRENGTH0 * x for x in row] for row in H]
        Ws = [[D.STRENGTH0 * x for x in row] for row in Wd]
        assert cond.mode == "regrow" and cond.teacher == "body"
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    occ[i][j], V[i, j], r[i, j] = False, 0.0, 0.0
        for i in range(n):
            for j in range(n):
                if patch[i][j] or patch[i][(j + 1) % n]:
                    H[i][j] = Hs[i][j] = 0.0
                if patch[i][j] or patch[(i + 1) % n][j]:
                    Wd[i][j] = Ws[i][j] = 0.0
        p_div, inherit = cond.speed, True
        cut = NormalDist().inv_cdf(1.0 - cond.rate)
        stream = ("future",)
    gens = {"body": address(tag, *key, *stream), "div": address(tag, *key, *stream, "div"),
            "dir": address(tag, *key, *stream, "dir")}
    if rec:
        gens["xi"], gens["zb"] = address(tag, *key, "record-noise"), address(tag, *key, "bond-noise")
    OFF = ((-1, 0), (1, 0), (0, -1), (0, 1))
    buf = {}
    for t in range(1, window + 1):
        i_ = (t - 1) % D.CHUNK
        if i_ == 0:
            for nm, gen in gens.items():
                buf[nm] = _draws(gen, "uniform" if nm in ("div", "dir") else "normal", n)
        z = buf["body"][i_]
        wv = screened(V, L) if alpha else None
        new = np.zeros_like(V)
        for i in range(n):
            for j in range(n):
                v = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                th_ij = 0.0 + (D.G_SIG * sig[i][j] if sig is not None else 0.0)
                drift = v - v * v * v + th_ij + (nbm - v)
                if alpha:
                    drift -= alpha * float(wv[i, j])
                vt = min(max(v + 0.2 * drift + D.SIGMA * float(z[i, j]), -2.0), 2.0)
                ref = float(r[i, j]) if rec else float(r0[i, j])
                val = min(max(vt + 0.2 * (gain[i][j] * (ref - vt)), -2.0), 2.0)
                new[i, j] = val if occ[i][j] else 0.0
        V = new
        if rec:
            zb, xi = buf["zb"][i_], buf["xi"][i_]
            for i in range(n):
                for j in range(n):
                    if float(zb[i, j]) > cut:
                        H[i][j], Hs[i][j] = -H[i][j], -Hs[i][j]
                    elif float(zb[i, j]) < -cut:
                        Wd[i][j], Ws[i][j] = -Wd[i][j], -Ws[i][j]
            r1 = np.zeros_like(r)
            for i in range(n):
                for j in range(n):
                    rv = float(r[i, j])
                    bs = (Wd[i - 1][j] * float(r[i - 1, j]) + Wd[i][j] * float(r[(i + 1) % n, j])
                          + H[i][j - 1] * float(r[i, j - 1]) + H[i][j] * float(r[i, (j + 1) % n])) / 4.0
                    val = min(max(rv + D.EPS * (rv * (1 - (rv / 1.2) ** 2) + D.KR * (bs - rv)) + D.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
                    r1[i, j] = val if occ[i][j] else 0.0
            r = r1
            for i in range(n):
                for j in range(n):
                    for E, Es, i2, j2 in ((H, Hs, i, (j + 1) % n), (Wd, Ws, (i + 1) % n, j)):
                        if occ[i][j] and occ[i2][j2]:
                            x = min(max(float(V[i, j]) * float(V[i2, j2]), -1.0), 1.0)
                            Es[i][j] = Es[i][j] + D.ETA * (x - Es[i][j])
                            if Es[i][j] != 0:
                                E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        if sig is not None:
            s2 = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    if not occ[i][j]:
                        continue
                    lap = 0.0
                    for dy, dx in OFF:
                        i2, j2 = (i + dy) % n, (j + dx) % n
                        if occ[i2][j2]:
                            lap += sig[i2][j2] - sig[i][j]
                    s2[i][j] = sig[i][j] + kappa * lap - decay * sig[i][j] + 0.0
                    if seed[i][j]:
                        s2[i][j] = 1.0 if r0[i, j] > 0 else -1.0
            sig = s2
        ud, uw = buf["div"][i_], buf["dir"][i_]
        choice = {}
        for i in range(n):
            for j in range(n):
                if not occ[i][j]:
                    continue
                empty = [d for d, (dy, dx) in enumerate(OFF) if not occ[(i + dy) % n][(j + dx) % n]]
                if empty and float(ud[i, j]) < p_div:
                    choice[(i, j)] = empty[int(math.floor(float(uw[i, j]) * len(empty)))]
        born = set()
        for d, (dy, dx) in enumerate(OFF):
            for (i, j), dd in choice.items():
                if dd != d:
                    continue
                ti, tj = (i + dy) % n, (j + dx) % n
                if occ[ti][tj] or (ti, tj) in born:
                    continue
                born.add((ti, tj))
                V[ti, tj] = V[i, j] if inherit else nb[ti, tj]
                if rec:
                    r[ti, tj] = r[i, j] if inherit else 0.0
                if sig is not None:
                    pass                                              # the signal of a newborn site starts at 0
        for (ti, tj) in born:
            occ[ti][tj] = True
            if rec:
                for (a, b) in ((ti, tj), (ti, (tj - 1) % n)):
                    H[a][b] = Hs[a][b] = 0.0
                for (a, b) in ((ti, tj), ((ti - 1) % n, tj)):
                    Wd[a][b] = Ws[a][b] = 0.0
    out = {"V": V, "occ": np.array(occ)}
    if rec:
        out.update(r=r, H=np.array(H), W=np.array(Wd))
    return out


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, replay(pick, block)


# Q3: engine equality -------------------------------------------------------------------------------------------

def q3_job(args):
    which, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    full = lambda x: np.ones(x.shape, bool)
    if which == "dl001":
        cases, V0, ema0, R0, th, T = S1.prepare("S4", D.SIDE, block, "engineering")
        k = len(cases)
        V, E, r = np.tile(V0, (2, 1, 1)), np.tile(ema0, (2, 1, 1)), np.tile(R0, (2, 1, 1))
        gains = np.repeat([0.0, 0.2], k)
        o = S1.run("li4", V.copy(), E.copy(), r, gains, th, np.tile(T, (2, 1, 1)), cases, 0.1, D.WINDOW, {D.WINDOW})
        idx = np.tile(np.arange(k), 2)
        out, _ = evolve("li4", {"occ": full(V), "V": V.copy(), "E": E.copy()},
                        Branches(gain=np.broadcast_to(gains[:, None, None], V.shape).copy(), read=r), cases, th[idx],
                        DL.TAG, ("future",), D.WINDOW)
        return which, same(out["V"], o["final"])
    if which == "lr004":
        cases, V0, ema0, R0, th, T = L4S.prepare("S4", block, "engineering")
        k = len(cases)
        conds = (L4D.Cond(0.001, "record+parity"), L4D.Cond(0.001, "body"))
        o = L4S.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {D.WINDOW}, tag=L4D.TAG)
        idx = np.tile(np.arange(k), 2)
        H0, W0 = edges_from(bonds(R0, True))
        st = {"occ": full(V0[idx]), "V": V0[idx].copy(), "E": ema0[idx].copy(), "r": R0[idx].copy(),
              "H": H0[idx].copy(), "W": W0[idx].copy(), "Hb": L4D.STRENGTH0 * H0[idx], "Wb": L4D.STRENGTH0 * W0[idx]}
        first = np.repeat([True, False], k)[:, None, None]
        out, _ = evolve("li4", st, Branches(gain=np.full(V0[idx].shape, L4D.GAIN), learn_record=first,
                                            learn_body=~first, parity=first),
                        cases, (th * 1.0)[idx], L4D.TAG, ("future",), D.WINDOW, rate=0.001, eps=L4D.EPS, kr=L4D.KR,
                        sigma_r=L4D.SIGMA_R, kc=L4D.KC, eta=L4D.ETA, sigma=L4D.SIGMA)
        return which, all(same(out[x], o[x]) for x in ("V", "r", "H", "W"))
    cases, V0, ema0, R0, th, T = S3.prepare(block, "engineering")
    arms = (D3.Arm("perp/f100", "perp", 100), D3.Arm("par/f25", "par", 25), D3.Arm("full", "full"))
    o = S3.run("li4", arms, cases, V0, ema0, R0, th, T, 0.0, "B", {D3.WINDOW})
    V, E, gain, fdist, every, masks, dist = S3.branches(arms, cases, V0, ema0, "B")
    k = len(cases)
    idx = np.tile(np.arange(k), len(arms))
    out, _ = evolve("li4", {"occ": (fdist < 0) | (fdist == 0), "V": V, "E": E},
                    Branches(gain=gain, read=np.tile(R0, (len(arms), 1, 1)), fdist=fdist, every=every,
                             newborn=np.tile(S3.newborn(cases), (len(arms), 1, 1))),
                    cases, (th * 0.0)[idx], D3.TAG, ("future", "B"), D3.WINDOW)
    return which, same(out["V"], o["final"]) and same(out["E"], o["final_ema"])


# Q7: efficacy on synthetic sheets ------------------------------------------------------------------------------

def toy(side=8, n=1):
    z = np.zeros((n, side, side))
    return {"occ": np.zeros((n, side, side), bool), "V": z.copy(), "E": z.copy(), "r": z.copy(), "H": z.copy(),
            "W": z.copy(), "Hb": z.copy(), "Wb": z.copy()}


def efficacy(cases):
    eff = {}
    one = np.ones((1, 1, 1), bool)
    st = toy()
    st["occ"][0, 3, 3] = st["occ"][0, 3, 4] = True
    st["V"][0, 3, 3], st["E"][0, 3, 3], st["r"][0, 3, 3] = 0.7, 0.5, -1.1
    st["H"][0, 3, 3], st["Hb"][0, 3, 3] = -1.0, -0.8
    u = np.ones((1, 8, 8))
    u[0, 3, 3] = 0.0
    w = np.full((1, 8, 8), 0.99)                                   # the last empty neighbour in order: left
    out, born = C.divide(st, np.full((1, 1, 1), 0.5), u, w, one)
    eff["division_places_and_copies"] = bool(born[0, 3, 2] and born.sum() == 1 and out["V"][0, 3, 2] == 0.7
                                             and out["E"][0, 3, 2] == 0.5 and out["r"][0, 3, 2] == -1.1
                                             and out["H"][0, 3, 2] == 0 and out["H"][0, 3, 3] == -1.0)
    out, _ = C.divide(st, np.full((1, 1, 1), 0.5), u, w, ~one, np.full((1, 8, 8), 0.05))
    eff["newborn_daughters"] = bool(out["V"][0, 3, 2] == 0.05 and out["r"][0, 3, 2] == 0.0)
    rng = np.random.default_rng(11)
    st = toy(16, 3)
    st["occ"][:] = rng.random((3, 16, 16)) < 0.7
    for f_ in ("V", "E", "r"):
        st[f_] = np.where(st["occ"], rng.standard_normal((3, 16, 16)), 0.0)
    ch, cw = C.contacts(st["occ"])
    st["H"], st["W"] = np.where(ch, 1.0, 0.0), np.where(cw, -1.0, 0.0)
    st["Hb"], st["Wb"] = 0.8 * st["H"], 0.8 * st["W"]
    prot = st["occ"].copy()
    prot[:, 1:, :] = False
    pv = st["V"].copy()
    ok_prot = ok_book = True
    for t in range(1, 80):
        x = rng.random((4, 3, 16, 16))
        st, dead = C.die(st, np.full((3, 1, 1), 0.03), x[0], prot)
        st, moved = C.swap(st, np.full((3, 1, 1), 0.05), x[1], t, prot)
        st, b_ = C.divide(st, np.full((3, 1, 1), 0.05), x[2], x[3], np.ones((3, 1, 1), bool))
        ok_prot &= not (dead & prot).any() and not (moved & prot).any()
        ch, cw = C.contacts(st["occ"])
        ok_book &= bool((st["H"][~ch] == 0).all() and (st["W"][~cw] == 0).all() and (st["Hb"][~ch] == 0).all()
                        and (st["Wb"][~cw] == 0).all() and all((st[f_][~st["occ"]] == 0).all() for f_ in ("V", "E", "r")))
    eff["death_and_exchange_spare_protected_cells"] = bool(ok_prot and (st["V"][prot] == pv[prot]).all() and st["occ"][prot].all())
    eff["contacts_consistent_under_random_events"] = bool(ok_book)
    a = toy(4)
    a["occ"][:] = True
    a["V"][0] = np.arange(16.0).reshape(4, 4)
    a["H"][:] = a["W"][:] = 1.0
    u = np.ones((1, 4, 4))
    u[0, 1, 0] = 0.0
    out, moved = C.swap(a, np.full((1, 1, 1), 0.5), u, 4, np.zeros((1, 4, 4), bool))
    eff["exchange_swaps_and_untrains"] = bool(out["V"][0, 1, 0] == 5.0 and out["V"][0, 1, 1] == 4.0 and moved.sum() == 2
                                              and out["H"][0, 1, 0] == 0 and out["H"][0, 2, 2] == 1.0)
    st = toy()
    st["occ"][0, 3, 3] = True
    st["V"][0, 3, 3] = 0.6
    due = np.zeros((1, 8, 8), bool)
    due[0, 3, 4] = due[0, 5, 5] = True
    out, born = C.fill(st, due, np.full((1, 8, 8), C.LEFT, np.int8), one)
    eff["scheduled_fill_needs_its_parent"] = bool(born[0, 3, 4] and not born[0, 5, 5] and out["V"][0, 3, 4] == 0.6)
    ok = True
    for geo in D.GEOMS:
        tf, pd = sim.smooth_schedule(cases, geo, 100)
        bd = sim.geometry(cases)[1][geo]
        for d in range(1, D.DMAX + 1):
            tt = tf[bd == d]
            ok &= bool(tt.min() > (d - 1) * 100 and tt.max() == d * 100)
    eff["smooth_schedule_completes_line_d_at_d_x_100"] = bool(ok)
    kappa, decay = 0.2, sim.decay_for(6.0)
    occ = np.ones((1, 8, 64), bool)
    x = np.zeros(occ.shape)
    src = np.zeros(occ.shape, bool)
    src[..., 0] = True
    for _ in range(8000):
        x = np.where(src, 1.0, C.diffuse(x, occ, kappa, decay, 0.0))
    eff["diffusion_decay_length"] = bool(abs(x[0, 0, 11] / x[0, 0, 10] - math.exp(-1.0 / 6.0)) < 1e-3
                                         and abs(C.decay_length(kappa, decay) - 6.0) < 1e-9)
    occ[..., 20] = occ[..., 40] = False
    x = np.zeros(occ.shape)
    for _ in range(2000):
        x = np.where(src, 1.0, C.diffuse(x, occ, kappa, decay, 0.0))
    eff["diffusion_stops_at_empty_sites"] = bool((x[..., 21:40] == 0).all() and (x[..., 19] > 0).all())
    return eff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    receipt_path = FROZEN / "qualification_receipt.json" if a.blocks is None else root / "debug_qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda p, u, b=lo: npz(root / "raw" / p / u / f"{b}.npz")
    shard = lambda p, u, b=lo: npz(root / "shards" / p / u / f"{b}.npz")
    checks = {}
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + 3, len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(w, lo, cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, w in enumerate(("dl001", "lr004", "dl003"))])
    na, nc, ns, nr, ntr = len(ARMS), len(CONDS), len(D.SNAPS), len(D.READS_R), D.WINDOW // D.TRACE
    k = D.NCASE

    missing = []
    for p, u in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [kk for kk, v in e.items() if np.issubdtype(v.dtype, np.floating) and np.isinf(v).any()]
            shapes, last = {}, []
            for body in D.BODIES:
                if p == "G":
                    for g in D.GEOMS:
                        pre = f"{body}/{g}"
                        shapes.update({f"{pre}/{x}": (ns, na, k) for x in W.G_SNAP})
                        shapes.update({f"{pre}/{x}": (ntr, na, k) for x in W.G_TRACE})
                        shapes.update({f"{pre}/{x}": (na, k) for x in W.FUNC})
                        shapes[f"{pre}/profile"] = (na, k, D.DMAX + 1)
                        last += [f"{pre}/{x}" for x in ("sign", "far", "near")]
                else:
                    shapes.update({f"{body}/{x}": (nr, nc, k) for x in W.R_READ})
                    shapes.update({f"{body}/{x}": (ntr, nc, k) for x in W.R_TRACE})
                    shapes.update({f"{body}/{x}": (nc, k) for x in W.FUNC})
                    last += [f"{body}/{x}" for x in W.R_READ]
            bad += [x for x, shp in shapes.items() if e.get(x, np.zeros(0)).shape != shp]
            bad += [x for x in last if x in e and np.isnan(e[x][-1]).any()]                 # defined at the last read
            bad += [x for x in shapes if x.endswith("/profile") and x in e and np.isnan(e[x]).any()]
            missing += [f"{p}/{u}/{b}/{x}" for x in bad]
    checks["Q1_complete"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    sm = {}
    p0, u0 = D.tasks()[0]
    W.run_task(p0, u0, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / p0 / u0 / f"{lo}.npz"), npz(serial / kind / p0 / u0 / f"{lo}.npz")
        sm[f"{kind}/{p0}/{u0}"] = bool(x.keys() == y.keys() and all(same(x[kk], y[kk]) for kk in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(sm.values()), "tasks": sm}

    eq = {f"{w}_bit_for_bit": ok for w, ok in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    ok_geo = ok_sched = True
    for b in range(lo, hi):
        e = shard("G", "S4_t0", b)
        for body in D.BODIES:
            for g in D.GEOMS:
                for tr in ("t_filled", "t_rough"):
                    x = e[f"{body}/{g}/{tr}"]
                    ref = x[:, ARMS.index(SAME_GEOMETRY[0])]
                    ok_geo &= all(same(ref, x[:, ARMS.index(a_)]) for a_ in SAME_GEOMETRY[1:])
                fl = e[f"{body}/{g}/t_filled"]
                want = np.minimum((2.0 + 2.0 * np.floor(np.arange(1, ntr + 1) * D.TRACE / 100.0)) / D.SIDE, 1.0)
                for a_ in ("front/100", "smooth/100"):
                    ok_sched &= bool(np.allclose(fl[:, ARMS.index(a_)], want[:, None], rtol=0, atol=1e-12))
    alias["grow_nb_none_diff_share_their_occupancy"] = bool(ok_geo)
    alias["front_and_smooth_fill_their_schedules"] = bool(ok_sched)
    ok_reg = ok_rec = True
    for u in D.UNITS["R"]:
        for b in range(lo, hi):
            e = shard("R", u, b)
            for body in D.BODIES:
                for rate in D.RATES:
                    for t_ in D.TEACHERS:
                        for sp in D.REGROW:
                            i1, i2 = CONDS.index(f"{rate:g}/{t_}/regrow@{sp:g}"), CONDS.index(f"{rate:g}/{t_}/regrow-nb@{sp:g}")
                            ok_reg &= same(e[f"{body}/filled"][:, i1], e[f"{body}/filled"][:, i2])
        raw = rawf("R", u)
        rp = [i for i, c in enumerate(CONDS) if "/record+parity/" in c]
        ok_rec &= all(same(raw[f"dw/{x}"][rp], raw[f"li4/{x}"][rp]) for x in ("r", "H", "W"))
    alias["regrow_and_regrow_nb_share_their_refilling"] = bool(ok_reg)
    alias["record_never_reads_the_body"] = bool(ok_rec)
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    masks, dist = sim.geometry(cases)
    top, tw = sim.template_function(T)
    e, raw = shard("G", "S4_t0"), rawf("G", "S4_t0")
    for body in D.BODIES:
        for g in D.GEOMS:
            Vf, oc = raw[f"{body}/{g}/V"], raw[f"{body}/{g}/occ"]
            bd = dist[g][None]
            Tb = np.broadcast_to(T[None], Vf.shape)
            far = (bd >= D.FAR[0]) & (bd < D.FAR[1])
            near = (bd >= D.NEAR[0]) & (bd <= D.NEAR[1])
            got = {"sign": sim.agree(Vf, Tb, oc), "far": sim.agree(Vf, Tb, oc & far), "near": sim.agree(Vf, Tb, oc & near)}
            for x, v in got.items():
                if not same(v, e[f"{body}/{g}/{x}"][-1]):
                    bad.append(f"G/{body}/{g}/{x}")
            prof = np.stack([sim.agree(Vf, Tb, oc & (bd == d)) for d in range(D.DMAX + 1)], -1)
            if not same(prof, e[f"{body}/{g}/profile"]):
                bad.append(f"G/{body}/{g}/profile")
            fn = function(Vf.reshape(-1, D.SIDE, D.SIDE), [top[i] for i in range(k)] * na, np.tile(tw, na))
            for x, v in zip(W.FUNC, fn):
                if not same(v.reshape(na, k), e[f"{body}/{g}/{x}"]):
                    bad.append(f"G/{body}/{g}/{x}")
    for u in D.UNITS["R"]:
        pattern, _ = D.parse_unit(u)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        m = sim.patch(cases)
        H0, W0 = edges_from(bonds(R0, True))
        top, tw = sim.template_function(T)
        e, raw = shard("R", u), rawf("R", u)
        for body in D.BODIES:
            Vf, rf, Hf, Wf, oc = (raw[f"{body}/{x}"] for x in ("V", "r", "H", "W", "occ"))
            Tb, mb = np.broadcast_to(T[None], Vf.shape), np.broadcast_to(m[None], Vf.shape)
            got = {"patch": sim.agree(Vf, Tb, oc & mb), "r_patch": sim.agree(rf, Tb, oc & mb),
                   "filled": (oc & mb).sum((-2, -1)) / mb.sum((-2, -1)), "sign": sim.agree(Vf, Tb, oc),
                   "r_sign": sim.agree(rf, Tb, oc), "bond_err": bond_err(Hf, Wf, H0[None], W0[None])}
            for x, v in got.items():
                if not same(v, e[f"{body}/{x}"][-1]):
                    bad.append(f"R/{u}/{body}/{x}")
            fn = function(Vf.reshape(-1, D.SIDE, D.SIDE), [top[i] for i in range(k)] * nc, np.tile(tw, nc))
            for x, v in zip(W.FUNC, fn):
                if not same(v.reshape(nc, k), e[f"{body}/{x}"]):
                    bad.append(f"R/{u}/{body}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    cs = sim.prepare("S4", lo, "engineering")[0]
    eff = efficacy(cs)
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    geo = {}
    for blk in range(lo, hi):
        cases, V0, ema0, R0, th, T = sim.prepare("S4", blk, "engineering")
        masks, dist = sim.geometry(cases)
        ok = True
        for j, c in enumerate(cases):
            t_ = np.sign(T[j])
            ok &= bool(set(np.unique(t_[masks["par"][j]])) == {-1.0, 1.0} and (t_[masks["perp"][j]] > 0).sum() == 2 * D.SIDE // 2)
            for g in D.GEOMS:
                ok &= bool((np.bincount(dist[g][j].ravel(), minlength=D.DMAX + 1) == 2 * D.SIDE).all())
            per = t_[0] if c.message % 2 == 0 else t_[:, 0]
            ok &= bool(all(per[x] == per[x % 8] for x in range(D.SIDE)) and (per[:4] == per[0]).all() and (per[4:8] == -per[0]).all())
        ok &= bool((sim.patch(cases).sum((-2, -1)) == D.PATCH ** 2).all())
        cf = sim.prepare("F0", blk, "engineering")
        tf = np.sign(cf[5])
        ok &= bool(all(abs(tf[j].mean()) == 0 and len(np.unique(tf[j])) == 2 for j in range(len(cf[0]))))
        geo[str(blk)] = ok
    checks["Q8_geometry"] = {"pass": all(geo.values()), "items": geo}

    walls = {}
    for key_, t_ in manifest["tasks"].items():
        p_, uu = key_.split("/")[:2]
        walls.setdefault((p_, uu), []).append(t_["wall_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "sc001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "sc001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("summary_G.json", "summary_R.json", "predictions_scored.json", "contrasts_G.csv",
                                  "contrasts_R.csv", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items, exact = 0.0, {}, True
    for (panel, where, body, name, ci), res in q4:
        if panel == "G":
            raw = rawf("G", "S4_t0")
            ai = ARMS.index(name)
            Vs, os_ = raw[f"{body}/{where}/V"][ai, ci], raw[f"{body}/{where}/occ"][ai, ci]
            d = float(np.abs(res["V"] - Vs).max())
            exact &= same(res["occ"], os_)
        else:
            raw = rawf("R", where)
            c_i = CONDS.index(name)
            d = max(float(np.abs(res["V"] - raw[f"{body}/V"][c_i, ci]).max()), float(np.abs(res["r"] - raw[f"{body}/r"][c_i, ci]).max()))
            exact &= same(res["occ"], raw[f"{body}/occ"][c_i, ci]) and same(res["H"], raw[f"{body}/H"][c_i, ci]) \
                and same(res["W"], raw[f"{body}/W"][c_i, ci])
        items[f"{panel}/{where}/{body}/{name}/case{ci}"] = d
        worst = max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8 and bool(exact), "max_abs_difference": worst,
                                       "occupancy_and_bonds_exact": bool(exact), "items": items}

    order = ["Q1_complete", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_geometry", "Q9_resources", "Q10_reader_dry_run"]
    checks = {kk: checks[kk] for kk in order}
    failed = [kk for kk, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
