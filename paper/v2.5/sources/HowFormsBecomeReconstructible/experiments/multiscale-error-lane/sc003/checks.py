"""Qualification of SC003 on the preflight (engineering) shards; criteria fixed in advance.

python -m sc003.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape (each run's arms: ARMS_T or ARMS_W)
Q2  serial = parallel: one task rerun alone, in its own process, gives bit-identical shards and raw states
Q3  engine: in every run, the saved final states of SC002's arms (cue, inst-3, mat-300, mat-1000) equal
    sc002.sim.run's bit for bit (body, record, bonds and occupancy; both bodies; both units), and so do their
    endpoints at every read: with its new switches off, SC003 is SC002
Q4  independent replay: sc002.checks' per-site loops (its own event, body, bond noise, record, arbiter, currents,
    deaths and divisions, contact ages, cable equation by sparse LU, trigger, slow state, pull and learning), extended by
    the iso law and the effective-medium coupling, reproduce three full branches (iso-emt-1000 under turnover 1e-3 with
    scattered cue damage, iso-3 in a regrowing wound, mat-300 under turnover 2.5e-4 with a change of side 4) within 1e-8
    (bonds and occupancy exactly)
Q5  aliases: with no division (a full sheet, no turnover) iso-3 and inst-3 are equal bit for bit, and so are the
    probe-only laws gate-300 and sister-300 with mat-300; a junction arm whose threshold cannot be reached equals the cue
    arm bit for bit under turnover (the machinery has no other effect); the conjugate-gradient solve with uniform
    junctions equals the FFT within 1e-9 on the saved final currents, at lam 3 and at every EMT_LAM
Q6  reanalysis: the endpoints at t = 4000 recomputed from the saved final states and the events equal the saved ones
Q7  efficacy: patches of 16 and 64 cells; anchors on exactly a quarter of the sites, cue damage on exactly a quarter of
    them; a newborn anchored cell whose contacts are all new and whose record disagrees with its cue sits at
    -kappa / g_l and triggers under iso-3 (and mat-300), and under inst-3 and emt-1000 does not; deaths over 1,000
    updates at mu = 1e-3 within 10% of mu, vacancies below 0.5% of the sites on average and below 2.5% at every update,
    every contact (and cell) touching a newborn at age 0; under turnover 1e-3 with scattered cue damage iso-3's newborns
    commit in their first update (age 0) at least 20 times as often as inst-3's; every wound refilled (filled >= 0.99)
    by t = 1000 in every saved case
Q8  stationary start (every preflight case): for every (mu, tau_m) the mean maturity of the contacts at t = 0 is within
    0.02 of 1 / (1 + 2 mu tau_m), and the share of cells younger than a* within 25% of 1 - exp(-mu a*)
Q9  resources: forecast development wall <= 12 h on 12 workers and CPU <= 30 h (the lane's budget for one development
    run), with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
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
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.linalg import splu  # noqa: E402

from be001 import sim as B1S  # noqa: E402
from cellpop import core as C  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402
from sc002 import sim as S2S  # noqa: E402
from sc002 import theory as T2  # noqa: E402
from sc002.cable import Cable  # noqa: E402
from sc003 import design as D  # noqa: E402
from sc003 import sim  # noqa: E402
from sc003 import worker as W  # noqa: E402

FROZEN = LANE / "sc003" / "frozen"
WORKERS = 12
SC002_ARMS = ("cue", "inst-3", "mat-300", "mat-1000")
Q4_PICKS = (("S4_t0", "li4", ("T", 1e-3, "cue", 8), "iso-emt-1000", 0),
            ("F0_t0", "dw", ("W", 0.0, "regrow", 8), "iso-3", 1),
            ("S4_t0", "dw", ("T", 2.5e-4, "change", 4), "mat-300", 2))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def cable_matrix(n, gh, gw):
    """g_l I + the weighted graph Laplacian of the periodic sheet; gh[i][j] couples (i, j)-(i, j+1), gw (i, j)-(i+1, j)."""
    rows, cols, vals = [], [], []
    diag = [D.G_LEAK] * (n * n)
    for i in range(n):
        for j in range(n):
            a = i * n + j
            for g, b in ((gh[i][j], i * n + (j + 1) % n), (gw[i][j], ((i + 1) % n) * n + j)):
                if g == 0.0:
                    continue
                rows += [a, b]
                cols += [b, a]
                vals += [-g, -g]
                diag[a] += g
                diag[b] += g
    rows += list(range(n * n))
    cols += list(range(n * n))
    vals += diag
    return coo_matrix((vals, (rows, cols)), shape=(n * n, n * n)).tocsc()


def s_replay(unit, body, run, arm, ci, block):
    """One branch end to end with independent per-site code; returns final V, r, H, W and occupancy."""
    panel, mu, situation, size = run
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    perm = address(D.TAG, *key, "anchors", D.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // D.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]
    rv0 = R0c.copy()
    if situation == "memory":
        rv0 = np.where(np.array(patch), -R0c, R0c)
    sg = [[1.0 if rv0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[D.STRENGTH0 * x for x in row] for row in H]
    Ws = [[D.STRENGTH0 * x for x in row] for row in Wd]
    r = rv0.copy()
    occ = [[True] * n for _ in range(n)]
    if situation in ("cue", "regrow+cue"):
        pick = address(D.TAG, *key, "cue-damage").permutation(len(cells))[: len(cells) // 4]
        for p_ in pick:
            q = cells[int(p_)]
            aval[q // n][q % n] *= -1.0
    elif situation == "change":
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    aval[i][j] *= -1.0

    def kill(i, j):
        occ[i][j] = False
        V[i, j], r[i, j] = 0.0, 0.0
        for (E, Es, ii, jj) in ((H, Hs, i, j), (H, Hs, i, (j - 1) % n), (Wd, Ws, i, j), (Wd, Ws, (i - 1) % n, j)):
            E[ii][jj], Es[ii][jj] = 0.0, 0.0

    if situation in ("regrow", "regrow+cue"):
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    kill(i, j)
    cut = NormalDist().inv_cdf(1.0 - D.RATE)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    ustreams = [address(D.TAG, *key, "population", e) for e in ("div", "dir", "die")]
    wound = situation in ("regrow", "regrow+cue")
    p_div = D.P_REGROW if wound else (D.P_DIV if mu > 0 else 0.0)
    events = p_div > 0 or mu > 0
    if mu > 0:
        e = address(D.TAG, *key, "ages").standard_exponential((n, n))
        age = [[math.floor(float(e[i, j]) / mu) for j in range(n)] for i in range(n)]
    else:
        age = [[math.inf] * n for _ in range(n)]
    ageH = [[min(age[i][j], age[i][(j + 1) % n]) for j in range(n)] for i in range(n)]
    ageW = [[min(age[i][j], age[(i + 1) % n][j]) for j in range(n)] for i in range(n)]
    prm = D.LAWS.get(arm)
    assert prm is None or not (prm["gate"] or prm["sister"]), "probe-only laws are not replayed"
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    def mat(ag):
        if prm["iso"]:
            return 1.0 if ag >= prm["iso"] else 0.0
        if prm["tau_m"] == 0:
            return 1.0
        return 1.0 if ag == math.inf else -math.expm1(-ag / prm["tau_m"])

    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
            ubufs = [g.random((D.CHUNK, n, n)) for g in ustreams] if events else None
        z, xi, zb = (bufs[q][t % D.CHUNK] for q in range(3))
        w = screened(V, L) if alpha else None
        new = np.zeros_like(V)
        for i in range(n):
            for j in range(n):
                if not occ[i][j]:
                    continue
                vv = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                drift = vv - vv * vv * vv + float(thc[i, j]) + (nbm - vv)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(vv + 0.2 * drift + D.SIGMA * float(z[i, j]), -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (D.GAIN * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
        for i in range(n):
            for j in range(n):
                if float(zb[i, j]) > cut:
                    H[i][j], Hs[i][j] = -H[i][j], -Hs[i][j]
                elif float(zb[i, j]) < -cut:
                    Wd[i][j], Ws[i][j] = -Wd[i][j], -Ws[i][j]
        r1 = np.zeros_like(r)
        for i in range(n):
            for j in range(n):
                if not occ[i][j]:
                    continue
                rr = float(r[i, j])
                bs = (Wd[i - 1][j] * float(r[i - 1, j]) + Wd[i][j] * float(r[(i + 1) % n, j])
                      + H[i][j - 1] * float(r[i, j - 1]) + H[i][j] * float(r[i, (j + 1) % n])) / 4.0
                r1[i, j] = min(max(rr + D.EPS * (rr * (1 - (rr / 1.2) ** 2) + D.KR * (bs - rr)) + D.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        r = r1
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if (anch[i][j] and occ[i][j]) else 0.0 for j in range(n)] for i in range(n)]
        if prm is not None:
            lam2 = D.lam_of(arm, mu) ** 2
            gh = [[lam2 * mat(ageH[i][j]) if (occ[i][j] and occ[i][(j + 1) % n]) else 0.0 for j in range(n)] for i in range(n)]
            gw = [[lam2 * mat(ageW[i][j]) if (occ[i][j] and occ[(i + 1) % n][j]) else 0.0 for j in range(n)] for i in range(n)]
            cur = np.array([[D.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
            v = splu(cable_matrix(n, gh, gw)).solve(cur.ravel()).reshape(n, n)
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base = sv[i][j]
                else:
                    base = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                if prm is None:
                    tr[i][j] = base
                    continue
                trig = float(v[i, j]) < -D.THETA and sr[i][j] != 0
                was = s_[i][j] >= D.S_MIN
                if trig and not was:
                    sgn[i][j] = -sr[i][j]
                s_[i][j] = 1.0 if trig else s_[i][j] * decay
                if s_[i][j] >= D.S_MIN:
                    tr[i][j] = sgn[i][j]
                    r[i, j] = float(r[i, j]) + D.EPS * D.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
                else:
                    tr[i][j] = base
        for i in range(n):
            for j in range(n):
                for E, Es, x in ((H, Hs, tr[i][j] * tr[i][(j + 1) % n]), (Wd, Ws, tr[i][j] * tr[(i + 1) % n][j])):
                    if x != 0:
                        Es[i][j] = Es[i][j] + D.ETA * (x - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        born = [[False] * n for _ in range(n)]
        if events:
            ud, uw, ux = (ub[t % D.CHUNK] for ub in ubufs)
            if mu > 0:
                for i in range(n):
                    for j in range(n):
                        if occ[i][j] and float(ux[i, j]) < mu:
                            kill(i, j)
                            s_[i][j], sgn[i][j] = 0.0, 0.0
            nbr = (((-1, 0)), ((1, 0)), ((0, -1)), ((0, 1)))
            choice = {}
            for i in range(n):
                for j in range(n):
                    if not occ[i][j] or float(ud[i, j]) >= p_div:
                        continue
                    empty = [d for d, (di, dj) in enumerate(nbr) if not occ[(i + di) % n][(j + dj) % n]]
                    if empty:
                        choice[(i, j)] = empty[int(math.floor(float(uw[i, j]) * len(empty)))]
            before = [row[:] for row in occ]
            for d, (di, dj) in enumerate(nbr):
                for (i, j), dd in sorted(choice.items()):
                    if dd != d:
                        continue
                    ti, tj = (i + di) % n, (j + dj) % n
                    if before[ti][tj] or born[ti][tj]:
                        continue
                    born[ti][tj] = True
                    V[ti, tj], r[ti, tj] = V[i, j], r[i, j]
            for i in range(n):
                for j in range(n):
                    if born[i][j]:
                        occ[i][j] = True
                        for (E, Es, ii, jj) in ((H, Hs, i, j), (H, Hs, i, (j - 1) % n), (Wd, Ws, i, j), (Wd, Ws, (i - 1) % n, j)):
                            E[ii][jj], Es[ii][jj] = 0.0, 0.0
        for i in range(n):
            for j in range(n):
                ageH[i][j] = 0.0 if (born[i][j] or born[i][(j + 1) % n]) else ageH[i][j] + 1.0
                ageW[i][j] = 0.0 if (born[i][j] or born[(i + 1) % n][j]) else ageW[i][j] + 1.0
    return V, r, np.array(H), np.array(Wd), np.array(occ)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q2_job(args):
    """The serial rerun of one task, in its own process on one core (compared with the parallel shards in main)."""
    body, unit, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    W.run_task(body, unit, block, "engineering", root)
    return True


def q3_job(args):
    """One run of one (unit, body): SC002's arms against sc002.sim.run, bit for bit, from the saved raw and shards."""
    unit, body, run, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    sh = npz(Path(root) / "shards" / body / unit / f"{block}.npz")
    panel, mu, s, z = run
    o = S2S.run(body, mu, s, z, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=D.TAG, arms=SC002_ARMS)
    key, k = D.run_name(*run), len(cases)
    idx = [D.arms_of(run).index(a) for a in SC002_ARMS]
    good = True
    for x in ("V", "r", "H", "W"):
        mine = raw[f"{key}/{x}"][idx].reshape(len(idx) * k, D.SIDE, D.SIDE)
        good &= bool(np.array_equal(mine, o[x].astype(mine.dtype)))
    good &= bool(np.array_equal(raw[f"{key}/occ"], o["occ"][:k]))
    for e in ("r_all", "r_in", "r_out", "v_all", "v_in", "filled", "maturity"):
        good &= bool(np.array_equal(sh[f"{key}/{e}"][:, idx], o[e].reshape(len(D.READS), len(idx), k)))
    good &= bool(np.array_equal(sh[f"{key}/opened"][idx], o["opened"].reshape(len(idx), k)))
    return f"{unit}/{body}/{key}", good


def q5_job(args):
    """Aliases: (a) a junction arm whose threshold cannot be reached equals the cue arm bit for bit under turnover;
    (b) with no division iso-3 equals inst-3 and gate-300, sister-300 equal mat-300 bit for bit."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    out = {}
    saved = D.THETA
    try:
        D.THETA = 1e300
        o = sim.run(body, 1e-3, "change", 4, cases, V0, ema0, R0, th, T, theta, {500}, window=500,
                    arms=("cue", "iso-3", "iso-emt-300", "mat-1000"))
        out["unreachable_threshold=cue_arm_under_turnover"] = bool(
            all(np.array_equal(o[x][:k], o[x][q * k:(q + 1) * k]) for x in ("V", "r", "H", "W") for q in (1, 2, 3))
            and float(o["opened"].sum()) == 0.0)
    finally:
        D.THETA = saved
    arms = ("inst-3", "iso-3", "mat-300", "gate-300", "sister-300")
    o = sim.run(body, 0.0, "change", 4, cases, V0, ema0, R0, th, T, theta, {500}, window=500, arms=arms)
    same = all(np.array_equal(o[x][:k], o[x][k:2 * k]) for x in ("V", "r", "H", "W"))
    same &= all(np.array_equal(o[x][2 * k:3 * k], o[x][q * k:(q + 1) * k]) for x in ("V", "r", "H", "W") for q in (3, 4))
    out["no_division:iso-3=inst-3,gate-300=sister-300=mat-300"] = bool(same)
    return out


def q7_population(block):
    """Deaths, vacancies, newborn contacts and first-update commitments over 1,000 updates at mu = 1e-3 (S4, dw,
    scattered cue damage)."""
    cases, V0, ema0, R0, th, T = sim.prepare("S4", block, "engineering")
    k = len(cases)
    log = {"deaths": 0, "cells": 0, "vac": 0.0, "vac_sum": 0.0, "n": 0, "new_ok": True}

    def observe(t, st, states, ageH, ageW, born, dead, extra):
        occ = st["occ"][:k]
        log["deaths"] += int(dead.sum())
        log["cells"] += int(occ.sum() + dead.sum() - born.sum())
        log["vac"] = max(log["vac"], float(1.0 - occ.mean((-2, -1)).min()))
        log["vac_sum"] += float(1.0 - occ.mean())
        log["n"] += 1
        nh, nw = C.touching(born)
        log["new_ok"] &= bool((ageH[nh] == 0).all() and (ageW[nw] == 0).all() and (extra["age"][born] == 0).all())

    arms = ("cue", "inst-3", "iso-3", "emt-300", "emt-1000", "mat-300")
    o = sim.run("dw", 1e-3, "cue", 8, cases, V0, ema0, R0, th, T, 0.0, {1000}, window=1000, arms=arms,
                observe=observe)
    first = {a: float(o["newc"][0, i * k:(i + 1) * k].sum() * D.SIDE * D.SIDE) for i, a in enumerate(arms)}
    rate = log["deaths"] / log["cells"]
    return {"death_rate": rate, "mean_vacancy_share": log["vac_sum"] / log["n"], "max_vacancy_share": log["vac"],
            "newborn_contacts_at_age_0": log["new_ok"], "first_update_commitments": first}


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
    rawf = lambda b_, u_, blk=lo: npz(root / "raw" / b_ / u_ / f"{blk}.npz")
    shard = lambda b_, u_, blk=lo: npz(root / "shards" / b_ / u_ / f"{blk}.npz")
    checks = {}
    q3_picks = [(u_, b_, run) for u_ in D.UNITS for b_ in D.BODIES for run in D.RUNS]
    nw = max(1, len(cpus) - 1)
    pool = ProcessPoolExecutor(max_workers=nw)
    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    q2_body, q2_unit = D.tasks()[-1]
    q2 = pool.submit(q2_job, (q2_body, q2_unit, lo, str(serial), cpus[-1]))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q5 = [pool.submit(q5_job, (u_, b_, lo, cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]))
          for i, (u_, b_) in enumerate((("S4_t0", "li4"), ("F0_t0", "dw")))]
    q3 = pool.map(q3_job, [(u_, b_, run, lo, str(root), cpus[(len(Q4_PICKS) + 2 + i + 1) % (len(cpus) - 1)])
                           for i, (u_, b_, run) in enumerate(q3_picks)])
    nr, ntr, nq = len(D.READS), len(D.TRACE_READS), len(D.AGE_BINS)

    missing = []
    for body, u in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / body / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for run, rn in zip(D.RUNS, D.RUNNAMES):
                na = len(D.arms_of(run))
                s = run[2]
                eps = W.ENDS if s == "change" else tuple(x for x in W.ENDS if not x.endswith("_old"))
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                bad += [f"{rn}/opened"] if e.get(f"{rn}/opened", np.zeros(0)).shape != (na, D.NCASE) else []
                bad += [f"{rn}/newc"] if e.get(f"{rn}/newc", np.zeros(0)).shape != (nq, na, D.NCASE) else []
                bad += [f"{rn}/births"] if e.get(f"{rn}/births", np.zeros(0)).shape != (D.NCASE,) else []
                bad += [f"{rn}/{x}" for x in ("trace", "trace_all") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (ntr, na, D.NCASE)]
            missing += [f"{body}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    alias = {}
    solver_worst = 0.0
    for body, uu in D.tasks():
        raw = rawf(body, uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        aval = np.where(raw["R0"] > 0, 1.0, -1.0)
        cab = Cable(len(cases))
        rf = raw["none8@0.001/r"][D.ARMS_T.index("inst-3")]
        cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
        for lam in sorted({3.0, *D.EMT_LAM.values()}):
            v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
            gU = np.full(cur.shape, lam ** 2)
            v2 = cab.solve(cur, gU, gU, np.zeros_like(cur))[0]
            solver_worst = max(solver_worst, float(np.abs(v1 - v2).max()))
    alias["fft=cg_uniform"] = solver_worst <= 1e-9

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(body, uu), shard(body, uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        T = raw["T"]
        for (p, mu, s, z), rn in zip(D.RUNS, D.RUNNAMES):
            m = B1S.patch(cases, z, D.TAG)
            tgt = np.where(m, -T, T) if s == "change" else T
            rf, Vf, occ = raw[f"{rn}/r"], raw[f"{rn}/V"], raw[f"{rn}/occ"]
            got = {"r_all": sim.agree(rf, tgt, occ), "v_all": sim.agree(Vf, tgt, occ), "r_in": sim.agree(rf, tgt, m & occ),
                   "v_in": sim.agree(Vf, tgt, m & occ), "r_out": sim.agree(rf, tgt, ~m & occ),
                   "filled": np.broadcast_to((m & occ).sum((-2, -1)) / m.sum((-2, -1)), rf.shape[:2])}
            for x, v in got.items():
                if not np.array_equal(v, e[f"{rn}/{x}"][-1]):
                    bad.append(f"{body}/{uu}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    eff["patch_cells_16_64"] = all(bool((B1S.patch(cases, z, D.TAG).sum((-2, -1)) == z * z).all()) for z in (4, 8))
    am = L5S.anchor_mask(cases, D.TAG)
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // D.DENSITY).all())
    ev = sim.event("cue", 8, cases, V0, ema0, R0, T, D.TAG)
    base = np.where(R0 > 0, 1.0, -1.0)
    eff["cue_damage_on_a_quarter_of_the_anchors"] = bool((((ev["aval"] != base) & am).sum((-2, -1)) == am.sum((-2, -1)) // 4).all())
    ages = np.full((1, D.SIDE, D.SIDE), np.inf)
    ages[0, 10, 10] = 0.0
    aH, aW = sim.contact_ages(ages)
    full = np.ones(ages.shape, bool)
    rec, ca = np.ones(ages.shape), np.zeros(ages.shape)
    ca[0, ::2, ::2] = 1.0
    ca[0, 10, 10] = -1.0
    newborn = {}
    for arm, mu in (("iso-3", 1e-3), ("mat-300", 1e-3), ("inst-3", 1e-3), ("emt-1000", 1e-3)):
        gH, gW = sim.conductance(arm, aH, aW, full, mu=mu)
        lam = D.lam_of(arm, mu)
        st = {"v": np.zeros(ages.shape), "s": np.zeros(ages.shape), "sgn": np.zeros(ages.shape),
              "kernel": B1S.cable_kernel(lam), "lam": lam, "cable": Cable(1)}
        _, _, (cm, _), _ = sim.detect(arm, rec, rec, ca, gH, gW, full, st)
        newborn[arm] = (bool(cm[0, 10, 10]), int(cm.sum()), float(st["v"][0, 10, 10]))
    eff["isolated_newborn_triggers_alone_iso_and_mat"] = all(
        newborn[a][:2] == (True, 1) and abs(newborn[a][2] + D.KAPPA / D.G_LEAK) < 1e-9 for a in ("iso-3", "mat-300"))
    eff["instant_and_emt_junctions_outvote_it"] = newborn["inst-3"][1] == 0 and newborn["emt-1000"][1] == 0
    pop = q7_population(lo)
    eff["deaths_within_10pct_of_mu"] = abs(pop["death_rate"] / 1e-3 - 1.0) <= 0.10
    eff["vacancies_below_0.5pct_mean_2.5pct_max"] = pop["mean_vacancy_share"] < 0.005 and pop["max_vacancy_share"] < 0.025
    eff["newborn_contacts_and_ages_at_0"] = pop["newborn_contacts_at_age_0"]
    fu = pop["first_update_commitments"]
    eff["first_update_commitments_by_isolation"] = fu["iso-3"] > 0 and fu["inst-3"] <= 0.05 * fu["iso-3"]
    fill = min(float(shard(b_, u_)[f"{rn}/filled"][1].min()) for b_, u_ in D.tasks()
               for (p, mu, s, z), rn in zip(D.RUNS, D.RUNNAMES) if p == "W")
    eff["wounds_refilled_by_t1000"] = fill >= 0.99
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff, "population": pop, "newborn": newborn,
                             "min_filled_t1000": fill}

    stat = {}
    allc = enrol(blocks, D.MESSAGES, D.PARENTS, "engineering")
    fulls = np.ones((len(allc), D.SIDE, D.SIDE), bool)
    for mu in D.MUS:
        age = sim.cell_ages(allc, mu, D.TAG)
        aH, aW = sim.contact_ages(age)
        for arm in ("mat-300", "mat-1000"):
            tau = D.LAWS[arm]["tau_m"]
            gH, gW = sim.conductance(arm, aH, aW, fulls, mu=mu)
            m_mean = float((gH.sum() + gW.sum()) / (2 * gH.size * 9.0))
            young = float((age < T2.a_star(tau)).mean())
            want_m, want_y = 1 / (1 + 2 * mu * tau), T2.self_young(mu, tau)
            stat[f"{mu:g}/{arm}"] = {"mean_m": round(m_mean, 4), "theory": round(want_m, 4), "young": round(young, 4),
                                     "young_theory": round(want_y, 4),
                                     "pass": abs(m_mean - want_m) <= 0.02 and abs(young / want_y - 1) <= 0.25}
    checks["Q8_stationary_start"] = {"pass": all(v["pass"] for v in stat.values()), "items": stat}

    walls = {}
    for key, t in manifest["tasks"].items():
        p_, uu = key.split("/")[:2]
        walls.setdefault((p_, uu), []).append(t["cpu_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and cpu / 3600 <= 30 and rss <= 0.8 * avail
                                           and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "sc003.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "sc003.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces_dw.json",
                                  "traces_li4.json", "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    same = {}
    body, u = q2_body, q2_unit
    q2.result()
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = dict(q3)
    checks["Q3_engine"] = {"pass": len(eq) == len(q3_picks) and all(eq.values()), "items": eq}

    for f in q5:
        alias.update({f"{k}": v for k, v in f.result().items()})
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias, "max_solver_difference": solver_worst}

    worst, items = 0.0, {}
    for (uu, body, run, arm, ci), (Vr, rr_, Hr_, Wr_, occr) in q4:
        raw = rawf(body, uu)
        k = D.arms_of(run).index(arm)
        key = D.run_name(*run)
        d = max(float(np.abs(Vr - raw[f"{key}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{key}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{key}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{key}/W"][k, ci]).max()),
                float(np.abs(occr.astype(int) - raw[f"{key}/occ"][ci].astype(int)).max()))
        items[f"{uu}/{body}/{key}/{arm}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_stationary_start", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
