"""Qualification of FN001 (draft) on the preflight (engineering) shards; criteria fixed in advance.

python -m fn001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json;
with --blocks, ROOT/debug_qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: before any wound, every condition equals lr004.sim.run on the same teacher, tag and draws, bit for bit
    (body, record and bonds after T_W1 - 1 updates; both bodies; two units), and the shards' pre-wound reads of sign,
    r_sign and bond_err equal lr004.sim.run's at T_W1
Q4  independent replay: per-site loops for the body's local terms, the record's bond noise and bond sums, body teaching
    and the vote, the kills (wound squares, newborn values, dead bonds drawn by the replay itself), conjugate
    gradients for the inhibitor (no FFT), its own noise cut (statistics.NormalDist), reproduce four full branches,
    three of them wounded twice, within 1e-8 (bonds exactly); and a flood fill written apart from sim.topology
    reproduces each replayed branch's final intact, defects, islands and walls exactly
Q5  aliases exact: W12 and W12x equal at every read up to T_W2 (same first wound); W2 equals W12 at T_W1 (before any
    wound); W2 and W2x equal up to T_W2 in every endpoint not read in a square; under record+parity the record and its
    bonds are the same under both bodies (the record never reads the body, and the kills are the same draws)
Q6  reanalysis: the last read's endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy: each wound covers 64 cells, squares a and b are disjoint; a kill zeroes the record in the wound, gives
    the 72 + 72 touching bonds strength 0 and leaves every other bond; the function readouts on synthetic sheets with
    known answers (stripes intact; a bridge, an island (still intact) and a double cut as declared; walls 0)
Q8  labyrinths: every LB template is balanced (|mean| <= 0.1) with spacing within 20% of 8
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from collections import deque  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
from statistics import NormalDist  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from fn001 import design as D  # noqa: E402
from fn001 import sim  # noqa: E402
from fn001 import worker as W  # noqa: E402
from fn001.predict import STATEMENTS  # noqa: E402
from lr001 import sim as S1  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

FROZEN = LANE / "fn001" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t0", "dw", "0.003/body/W12", 0), ("S4_t0", "li4", "0.001/vote/W12x", 1),
            ("LB_t1", "li4", "0.003/vote/W2x", 2), ("F0_t1", "dw", "0/body/W12", 3))
NAMES = [c.name for c in D.CONDS]


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


# an independent function readout ---------------------------------------------------------------------------------

def flood_topology(s):
    """(large + domains, large - domains, islands) of a +-1 sheet by breadth-first flood fill on the torus."""
    n = len(s)
    seen = [[False] * n for _ in range(n)]
    large, small = {1: 0, -1: 0}, 0
    for i in range(n):
        for j in range(n):
            if seen[i][j]:
                continue
            sg, size, q = (1 if s[i][j] > 0 else -1), 0, deque([(i, j)])
            seen[i][j] = True
            while q:
                a, b = q.popleft()
                size += 1
                for a2, b2 in (((a + 1) % n, b), ((a - 1) % n, b), (a, (b + 1) % n), (a, (b - 1) % n)):
                    if not seen[a2][b2] and (1 if s[a2][b2] > 0 else -1) == sg:
                        seen[a2][b2] = True
                        q.append((a2, b2))
            if size >= D.MINCOMP:
                large[sg] += 1
            else:
                small += 1
    return large[1], large[-1], small


def flood_function(V, T):
    n = len(V)
    s = [[1 if V[i][j] > 0 else -1 for j in range(n)] for i in range(n)]
    t = [[1 if T[i][j] > 0 else -1 for j in range(n)] for i in range(n)]
    p, q, small = flood_topology(s)
    tp, tq, _ = flood_topology(t)

    def wl(x):
        return sum((x[i][j] != x[i][(j + 1) % n]) + (x[i][j] != x[(i + 1) % n][j]) for i in range(n) for j in range(n))
    return {"intact": float(p == tp and q == tq), "defects": float(abs(p - tp) + abs(q - tq) + small),
            "islands": float(small), "walls": wl(s) / wl(t) - 1.0}


# an independent replay -------------------------------------------------------------------------------------------

def s_replay(unit, body, cname, ci, block):
    """One wounded branch (body teaching or the vote) end to end with independent per-site code; returns final V, r,
    H, W of the first record."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    cond = D.CONDS[NAMES.index(cname)]
    src = cond.teacher.source
    assert src in ("body", "vote")
    n, key = D.SIDE, cases[ci].key()
    V, thc, R0c = V0[ci].copy(), th[ci] * theta, R0[ci]
    s = [[1.0 if R0c[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]

    def taught():
        H = [[s[i][j] * s[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        Wd = [[s[i][j] * s[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        return H, Wd, [[0.8 * H[i][j] for j in range(n)] for i in range(n)], [[0.8 * Wd[i][j] for j in range(n)] for i in range(n)]
    recs = [[R0c.copy(), *taught()]]                     # [r, H, W, Hs, Ws] per record
    if src == "vote":
        recs.append([R0c.copy(), *taught()])
    y0, x0 = (int(v) for v in address(D.TAG, *key, "wound").integers(0, n, 2))
    squares = {"a": (y0, x0), "b": ((y0 + n // 2) % n, (x0 + n // 2) % n)}
    plan = {tw: (which, k) for k, (tw, which) in enumerate(cond.wounds)}
    cut = float("inf") if cond.rate <= 0 else NormalDist().inv_cdf(1.0 - cond.rate)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    if src == "vote":
        streams += [Stream(D.TAG, cases, x, "B", side=n) for x in ("record-noise", "bond-noise")]
    bufs = [None] * len(streams)

    def rel(x, i, j, i2, j2):
        return 1.0 if (float(x[i, j]) > 0) == (float(x[i2, j2]) > 0) else -1.0
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
        z = bufs[0][t % D.CHUNK]
        noises = [(bufs[1][t % D.CHUNK], bufs[2][t % D.CHUNK])]
        if src == "vote":
            noises.append((bufs[3][t % D.CHUNK], bufs[4][t % D.CHUNK]))
        r0 = recs[0][0]
        w = screened(V, L) if alpha else None
        new = np.empty_like(V)
        for i in range(n):
            for j in range(n):
                v = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                drift = v - v * v * v + float(thc[i, j]) + (nbm - v)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(v + 0.2 * drift + D.SIGMA * float(z[i, j]), -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (D.GAIN * (float(r0[i, j]) - vt)), -2.0), 2.0)
        V = new
        for rec, (xi, zb) in zip(recs, noises):
            r, H, Wd, Hs, Ws = rec
            for i in range(n):
                for j in range(n):
                    if float(zb[i, j]) > cut:
                        H[i][j], Hs[i][j] = -H[i][j], -Hs[i][j]
                    elif float(zb[i, j]) < -cut:
                        Wd[i][j], Ws[i][j] = -Wd[i][j], -Ws[i][j]
            r1 = np.empty_like(r)
            for i in range(n):
                for j in range(n):
                    rv = float(r[i, j])
                    bs = (Wd[i - 1][j] * float(r[i - 1, j]) + Wd[i][j] * float(r[(i + 1) % n, j])
                          + H[i][j - 1] * float(r[i, j - 1]) + H[i][j] * float(r[i, (j + 1) % n])) / 4.0
                    r1[i, j] = min(max(rv + D.EPS * (rv * (1 - (rv / 1.2) ** 2) + D.KR * (bs - rv)) + D.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
            rec[0] = r1
        if src == "body":
            r, H, Wd, Hs, Ws = recs[0]
            for i in range(n):
                for j in range(n):
                    for E, Es, i2, j2 in ((H, Hs, i, (j + 1) % n), (Wd, Ws, (i + 1) % n, j)):
                        x = float(V[i, j]) * float(V[i2, j2])
                        Es[i][j] = Es[i][j] + D.ETA * (min(max(x, -1.0), 1.0) - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        else:
            rA, HA, WA, HsA, WsA = recs[0]
            rB, HB, WB, HsB, WsB = recs[1]
            for i in range(n):
                for j in range(n):
                    for k, (i2, j2) in enumerate(((i, (j + 1) % n), ((i + 1) % n, j))):
                        m = 1.0 if rel(V, i, j, i2, j2) + rel(rA, i, j, i2, j2) + rel(rB, i, j, i2, j2) > 0 else -1.0
                        for E, Es in ((HA, HsA), (HB, HsB)) if k == 0 else ((WA, WsA), (WB, WsB)):
                            Es[i][j] = Es[i][j] + D.ETA * (m - Es[i][j])
                            if Es[i][j] != 0:
                                E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        if t + 1 in plan:                                 # the kill, after update t + 1
            which, wn = plan[t + 1]
            ya, xa = squares[which]
            dead = {((ya + a) % n, (xa + b) % n) for a in range(D.WOUND) for b in range(D.WOUND)}
            g = address(D.TAG, *key, "newborn", wn)
            nb = D.KILL_SD * g.standard_normal((n, n))
            for (i, j) in dead:
                V[i, j] = nb[i, j]
            for rec, lab in zip(recs, "AB"):
                gb = address(D.TAG, *key, "bonds", wn, lab)
                rh, rw = gb.random((n, n)), gb.random((n, n))
                r, H, Wd, Hs, Ws = rec
                for i in range(n):
                    for j in range(n):
                        if (i, j) in dead:
                            r[i, j] = 0.0
                        if (i, j) in dead or (i, (j + 1) % n) in dead:
                            H[i][j], Hs[i][j] = (-1.0 if rh[i, j] < 0.5 else 1.0), 0.0
                        if (i, j) in dead or ((i + 1) % n, j) in dead:
                            Wd[i][j], Ws[i][j] = (-1.0 if rw[i, j] < 0.5 else 1.0), 0.0
    r, H, Wd, _, _ = recs[0]
    return V, r, np.array(H), np.array(Wd), T[ci]


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    V, r, H, Wd, T = s_replay(*pick, block)
    return pick, (V, r, H, Wd), flood_function(V, T)


def q3_job(args):
    """Every condition before any wound against lr004.sim.run, bit for bit; and the pre-wound reads at T_W1."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    teach = tuple(c.teacher for c in D.CONDS)
    o = sim.run(body, D.CONDS, cases, V0, ema0, R0, th, T, theta, {D.T_W1 - 1}, tag=D.TAG, window=D.T_W1 - 1)
    o4 = L4S.run(body, teach, cases, V0, ema0, R0, th, T, theta, {D.T_W1 - 1}, tag=D.TAG, window=D.T_W1 - 1)
    finals = bool(all(np.array_equal(o[k], o4[k]) for k in ("V", "r", "H", "W")))
    o4b = L4S.run(body, teach, cases, V0, ema0, R0, th, T, theta, {D.T_W1}, tag=D.TAG, window=D.T_W1)
    return (unit, body), finals, {k: o4b[k][0].reshape(len(D.CONDS), len(cases)) for k in ("sign", "r_sign", "bond_err")}


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
    rawf = lambda u, b=lo: npz(root / "raw" / "E" / u / f"{b}.npz")
    shard = lambda u, b=lo: npz(root / "shards" / "E" / u / f"{b}.npz")
    checks = {}
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "LB_t0") for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks), len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, (u_, b_) in enumerate(q3_picks)])
    nc, nr = len(D.CONDS), len(D.READS)
    i0, i1 = D.READS.index(D.T_W1), D.READS.index(D.T_W2)

    missing = []
    for p, u in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for body in D.BODIES:
                bad += [f"{body}/{ep}" for ep in D.ENDPOINTS if e.get(f"{body}/{ep}", np.zeros(0)).shape != (nr, nc, D.NCASE)]
            missing += [f"{p}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    u = D.UNITS[0]
    W.run_task("E", u, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / "E" / u / f"{lo}.npz"), npz(serial / kind / "E" / u / f"{lo}.npz")
        same[f"{kind}/E/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for (u_, b_), finals, pre in q3:
        e = shard(u_)
        eq[f"{u_}/{b_}/finals_before_any_wound=lr004.sim.run"] = finals
        eq[f"{u_}/{b_}/pre_wound_reads=lr004.sim.run"] = bool(all(np.array_equal(e[f"{b_}/{k}"][i0], pre[k]) for k in pre))
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    ok_x = ok_pre = ok_rec = ok_2x = True
    for uu in D.UNITS:
        e, raw = shard(uu), rawf(uu)
        for b in D.BODIES:
            for rate in D.RATES:
                for rep in D.REPAIRS:
                    j12, j12x, j2, j2x = (NAMES.index(f"{rate:g}/{rep}/{s}") for s in D.SCHEDULES)
                    for ep in D.ENDPOINTS:
                        x = e[f"{b}/{ep}"]
                        ok_x &= bool(np.array_equal(x[: i1 + 1, j12], x[: i1 + 1, j12x]))
                        ok_pre &= bool(np.array_equal(x[i0, j12], x[i0, j2]))
                        if ep not in ("patch", "r_patch"):              # W2 and W2x read different squares
                            ok_2x &= bool(np.array_equal(x[: i1 + 1, j2], x[: i1 + 1, j2x]))
        rp = [i for i, c in enumerate(D.CONDS) if c.repair == "record+parity"]
        for key in ("r", "H", "W"):
            ok_rec &= bool(np.array_equal(raw[f"dw/{key}"][rp], raw[f"li4/{key}"][rp]))
    alias["W12=W12x_up_to_the_second_wound"] = ok_x
    alias["W2=W12_before_any_wound"] = ok_pre
    alias["W2=W2x_up_to_their_wound_outside_the_squares"] = ok_2x
    alias["record_never_reads_the_body"] = ok_rec
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        k = len(raw["T"])
        Tb = np.broadcast_to(raw["T"], (nc, *raw["T"].shape)).reshape(nc * k, D.SIDE, D.SIDE)
        H0, W0 = S1.edges_from(bonds(raw["R0"], True))
        ms = sim.wound_masks(enrol([lo], D.MESSAGES, D.PARENTS, "engineering"), D.TAG)
        last = np.stack([ms[c.wounds[-1][1]][j] for c in D.CONDS for j in range(k)])
        Ts = np.where(raw["T"] > 0, 1.0, -1.0)
        Ttop = np.array([sim.topology(Ts[j])[:2] for j in range(k)])[np.tile(np.arange(k), nc)]
        Tw = sim.walls(Ts)[np.tile(np.arange(k), nc)]
        for b in D.BODIES:
            Vf = raw[f"{b}/V"].reshape(nc * k, D.SIDE, D.SIDE)
            rf = raw[f"{b}/r"].reshape(nc * k, D.SIDE, D.SIDE)
            Hf = raw[f"{b}/H"].astype(float).reshape(nc * k, D.SIDE, D.SIDE)
            Wf = raw[f"{b}/W"].astype(float).reshape(nc * k, D.SIDE, D.SIDE)
            intact, dfx, isl, wex = sim.function(Vf, Ttop, Tw)
            got = {"sign": S.sign(Vf, Tb), "r_sign": S.sign(rf, Tb), "patch": S.patch(Vf, Tb, last),
                   "r_patch": S.patch(rf, Tb, last), "intact": intact, "defects": dfx, "islands": isl, "walls": wex,
                   "bond_err": S1.bond_err(Hf, Wf, np.tile(H0, (nc, 1, 1)), np.tile(W0, (nc, 1, 1)))}
            for key, v in got.items():
                if not np.array_equal(v.reshape(nc, k), e[f"{b}/{key}"][-1]):
                    bad.append(f"{uu}/{b}/{key}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cs = sim.prepare("S4", lo, "engineering")[0]
    ms = sim.wound_masks(cs)
    eff["wounds_cover_64_cells"] = bool((ms["a"].sum((-2, -1)) == D.WOUND ** 2).all() and (ms["b"].sum((-2, -1)) == D.WOUND ** 2).all())
    eff["squares_a_and_b_disjoint"] = bool(not (ms["a"] & ms["b"]).any())
    one = np.ones((D.SIDE, D.SIDE))
    m = ms["a"][0]
    H, Wd, Hb, Wb, r = sim.kill((one, one, 0.8 * one, 0.8 * one, one), m, -one, -one)
    th_, tw_ = sim.touching(m)
    eff["kill_as_declared"] = bool(th_.sum() == tw_.sum() == D.WOUND * (D.WOUND + 1) and (r[m] == 0).all() and (r[~m] == 1).all()
                                   and (Hb[th_] == 0).all() and (Hb[~th_] == 0.8).all() and (Wb[tw_] == 0).all()
                                   and (Wb[~tw_] == 0.8).all() and (H[th_] == -1).all() and (H[~th_] == 1).all())
    st = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)
    ttop = np.array([sim.topology(st)[:2]])
    tw = sim.walls(st[None])
    syn = {"stripes": (st, (1.0, 0.0, 0.0, 0.0))}
    x = st.copy(); x[10, 4:8] = 1.0
    syn["bridge"] = (x, (0.0, 1.0, 0.0, None))
    x = st.copy(); x[10, 1] = -1.0
    syn["island"] = (x, (1.0, 1.0, 1.0, None))                  # an island leaves every large domain: intact
    x = st.copy(); x[3:5, 0:4] = -1.0; x[20:22, 0:4] = -1.0
    syn["double_cut"] = (x, (0.0, 2.0, 0.0, None))
    for name, (sheet, want) in syn.items():
        got = [float(v[0]) for v in sim.function(sheet[None], ttop, tw)]
        fl = flood_function(sheet, st)
        ok = all(w_ is None or g_ == w_ for g_, w_ in zip(got, want))
        ok &= got == [fl["intact"], fl["defects"], fl["islands"], fl["walls"]]
        eff[f"function/{name}"] = bool(ok)
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    lab = {}
    for blk in range(lo, hi):
        for kind in (0, 1):
            t_ = S2.template("LB", kind, blk)
            lab[f"{blk}/{kind}"] = {"mean": round(float(t_.mean()), 4), "spacing": round(float(S.spacing(t_[None])[0]), 3)}
    checks["Q8_labyrinths"] = {"pass": all(abs(v["mean"]) <= 0.1 and abs(v["spacing"] - 8.0) <= 1.6 for v in lab.values()), "items": lab}

    walls = {}
    for key, t in manifest["tasks"].items():
        p_, uu = key.split("/")[:2]
        walls.setdefault((p_, uu), []).append(t["wall_s"])
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
    proc = subprocess.run([sys.executable, "-m", "fn001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "fn001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_capacity.csv", out / "contrasts_teachers.csv", out / "summary.json",
                *(out / f"levels_{b}.json" for b in D.BODIES), out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in STATEMENTS]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, cname, ci), (Vr, rr_, Hr_, Wr_), fl in q4:
        raw, e = rawf(uu), shard(uu)
        k = NAMES.index(cname)
        d = max(float(np.abs(Vr - raw[f"{body}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{body}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{body}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{body}/W"][k, ci]).max()))
        fok = all(fl[ep] == float(e[f"{body}/{ep}"][-1, k, ci]) for ep in ("intact", "defects", "islands", "walls"))
        items[f"{uu}/{body}/{cname}/case{ci}"] = {"max_abs": d, "function_readouts_equal": bool(fok)}
        worst = max(worst, d) if fok else float("inf")
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_labyrinths", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
