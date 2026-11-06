"""Qualification of AR001 on the preflight (engineering) shards; criteria fixed in advance.

python -m ar001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every run's endpoints at its declared shape (reads x arms x cases;
    r_in_old exactly in the change runs), its trace and scalars; every value finite (no undefined case is declared)
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine, bit for bit (V, r and bonds): (a) rest and dial at sigma 0 under BE006's tag equal be006.sim.run's never-SL
    and dial-SL over 2,000 updates in memory, change and cue (S4_t1 and F0_t0, both bodies); (b) at the lane's clock on
    an 8 x 8 patch under LR005's tag with the latch's hold 300, record, body, vote, arbiter and latch equal
    lr005.sim.run's record+parity, body, vote2r, cue and community-s over 1,000 updates in every LR005 situation (S4_t1,
    both bodies); (c) the event equals be001.sim.event for none, memory, shared, cue and change, adds exactly the body's
    flip for body (to none) and correlated (to memory), and at sigma 1 its anchors equal gc001.sim.event's misread
Q4  independent replay: per-site loops for the event (patch, anchors, flips, kill, scattered and changed cues, the misread
    by displaced reads), the body's local terms (conjugate gradients for the inhibitor), bond noise at the clock's p_b
    (the second record's from its own streams), the record's own bond sums, the policies' targets (the arbiter, the
    body's co-activity, the three-copy vote, the latch's window counts and hold, the currents, the cable equation by
    sparse LU on be001.checks' own matrix, the trigger and the slow state), the pull and the Hebbian learner reproduce six
    full branches (dial in change@0, latch in correlated@0, vote in memory@0, arbiter in memory@1, body in shared@0,
    dial-d8 in cue@0) within 1e-8 (bonds exactly)
Q5  aliases: (a) inactive, record, body and vote never read the cue, so in every task they are bit-identical across
    none@0, cue@0 and change@0 (every endpoint, read and trace); (b) every delayed dial equals rest at every read and
    trace point before its first update; (c) u(new) + u(old) = 1 exactly for every branch of change@0 and change@1
    (the information-limit identity); (d) the sparse LU equals the FFT for uniform conductances (lengths 1 and 3) and
    be001.sim.cable_cg with the footprint's conductances within 1e-9, on saved final currents
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states, the events and the footprints
    equal the saved ones
Q7  efficacy: on every preflight case the events do exactly their rule (memory and correlated invert the patch's record
    and set consistent bonds; body and correlated invert the patch's body; shared zeroes the patch's record, its inside
    bonds and anchors; cue flips exactly a quarter of the anchors; change flips exactly the patch's anchors and its
    target; the misread changes anchors only); the footprints have their declared sizes and overlaps (d2: 64 sites
    covering the patch, d0: the patch, d8: 400 sites; s4 covers half the patch, s6 none of it); every dial is on for
    exactly 1,000 updates at its declared delay and every other arm never; onset is recorded for the dials only; the
    clock is eta 3e-4, p_b 3e-5, tau_c 15,000 (T* = 1,959 updates); a bond at +s0 relearning toward -1 at 3e-4 crosses
    zero after ceil(T*) updates; the latch holds its decision for exactly its hold
Q8  pairing: the same arm listed twice gives bit-identical branches, and reordering a run's arms changes no arm's branch
Q9  resources: forecast development within 40 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, disk
Q10 reader dry run: analyze, predict and tables complete on the preflight shards, every statement is scored, and every
    git file is 256 KB or less
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
from scipy.sparse.linalg import splu  # noqa: E402

from ar001 import design as D  # noqa: E402
from ar001 import sim  # noqa: E402
from ar001 import worker as W  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from be001.checks import cable_matrix  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from be006 import design as B6  # noqa: E402
from be006 import sim as B6S  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl001 import sim as S  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import design as L5  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "ar001" / "frozen"
WORKERS = 12
RUNS = {D.run_name(*x): x for x in D.RUNS}
Q4_PICKS = (("S4_t1", "li4", "change", 0.0, "dial", 0),
            ("F0_t0", "dw", "correlated", 0.0, "latch", 1),
            ("S4_t0", "dw", "memory", 0.0, "vote", 2),
            ("F0_t1", "li4", "memory", 1.0, "arbiter", 3),
            ("S4_t1", "dw", "shared", 0.0, "body", 4),
            ("F0_t0", "li4", "cue", 0.0, "dial-d8", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, situation, sigma, arm, ci, block, window=D.WINDOW, tag=D.TAG, clock=None, hold=None, size=D.SIZE):
    """One arm's branch end to end with independent per-site code; returns final V, r, H, W."""
    clock = D.CLOCK if clock is None else clock
    hold = int(clock["tau_c"]) if hold is None else hold
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    spec = D.ARM[arm]
    kind = spec["kind"]
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(tag, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    dd, sh = spec["d"], spec["shift"]
    wide = size + 2 * dd
    fp = [[((i - a + dd) % n) < wide and ((j - sh - b + dd) % n) < wide for j in range(n)] for i in range(n)]
    perm = address(tag, *key, "anchors", D.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // D.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    rv0 = R0c.copy()
    if situation in ("memory", "correlated"):
        rv0 = np.where(np.array(patch), -R0c, R0c)
    if situation in ("body", "correlated"):
        V = np.where(np.array(patch), -V, V)
    sg = [[1.0 if rv0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[D.STRENGTH0 * x for x in row] for row in H]
    Ws = [[D.STRENGTH0 * x for x in row] for row in Wd]
    r = rv0.copy()
    if situation == "shared":
        nb = D.KILL_SD * address(tag, *key, "newborn").standard_normal((n, n))
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    V[i, j], r[i, j] = nb[i, j], 0.0
                    anch[i][j] = False
                    if patch[i][(j + 1) % n]:
                        H[i][j], Hs[i][j] = 0.0, 0.0
                    if patch[(i + 1) % n][j]:
                        Wd[i][j], Ws[i][j] = 0.0, 0.0
    if situation == "cue":
        pick = address(tag, *key, "cue-damage").permutation(len(cells))[: len(cells) // 4]
        for p_ in pick:
            q = cells[int(p_)]
            aval[q // n][q % n] *= -1.0
    if situation == "change":
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    aval[i][j] *= -1.0
    if sigma:
        g = address(tag, *key, "gc-eps").standard_normal((2, n, n))
        field = [row[:] for row in aval]
        for i in range(n):
            for j in range(n):
                dx, dy = int(np.rint(sigma * g[0, i, j])), int(np.rint(sigma * g[1, i, j]))
                aval[i][j] = field[(i + dx) % n][(j + dy) % n]
    two = kind == "vote"
    if two:
        sgB = [[1.0 if R0c[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)] if situation in ("memory", "correlated") else sg
        rB = R0c.copy() if situation in ("memory", "correlated") else r.copy()
        HB = [[sgB[i][j] * sgB[i][(j + 1) % n] for j in range(n)] for i in range(n)] if situation in ("memory", "correlated") else [row[:] for row in H]
        WB = [[sgB[i][j] * sgB[(i + 1) % n][j] for j in range(n)] for i in range(n)] if situation in ("memory", "correlated") else [row[:] for row in Wd]
        HsB = [[D.STRENGTH0 * x for x in row] for row in HB] if situation in ("memory", "correlated") else [row[:] for row in Hs]
        WsB = [[D.STRENGTH0 * x for x in row] for row in WB] if situation in ("memory", "correlated") else [row[:] for row in Ws]
        streamsB = [Stream(tag, cases, x, "B", side=n) for x in ("record-noise", "bond-noise")]
    cut = NormalDist().inv_cdf(1.0 - clock["rate"])
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    streams = [Stream(tag, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    rest, sig2 = D.SIG["lam_rest"] ** 2, D.SIG["lam_sig"] ** 2
    if kind in ("rest", "dial"):
        gh = [[sig2 if (fp[i][j] or fp[i][(j + 1) % n]) else rest for j in range(n)] for i in range(n)]
        gw = [[sig2 if (fp[i][j] or fp[(i + 1) % n][j]) else rest for j in range(n)] for i in range(n)]
        lu_on = splu(cable_matrix(n, gh, gw))
        lu_off = splu(cable_matrix(n, [[rest] * n for _ in range(n)], [[rest] * n for _ in range(n)]))
    first, last = spec["delay"] + 1, spec["delay"] + D.SIG["duration"]
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    age = [[0] * n for _ in range(n)]
    decay = math.exp(-1.0 / clock["tau_c"])
    rho = D.RHO
    for t in range(window):
        on = kind == "dial" and first <= t + 1 <= last
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
            if two:
                bufsB = [st.take(D.CHUNK)[:, ci] for st in streamsB]
        z, xi, zb = (bufs[q][t % D.CHUNK] for q in range(3))
        w = screened(V, L) if alpha else None
        new = np.empty_like(V)
        for i in range(n):
            for j in range(n):
                vv = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                drift = vv - vv * vv * vv + float(thc[i, j]) + (nbm - vv)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(vv + 0.2 * drift + D.SIGMA * float(z[i, j]), -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (D.GAIN * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
        recs = [(H, Wd, Hs, Ws, zb, xi, "A")]
        if two:
            recs.append((HB, WB, HsB, WsB, bufsB[1][t % D.CHUNK], bufsB[0][t % D.CHUNK], "B"))
        for Hh, Ww, Hs_, Ws_, zz, xx, which in recs:
            for i in range(n):
                for j in range(n):
                    if float(zz[i, j]) > cut:
                        Hh[i][j], Hs_[i][j] = -Hh[i][j], -Hs_[i][j]
                    elif float(zz[i, j]) < -cut:
                        Ww[i][j], Ws_[i][j] = -Ww[i][j], -Ws_[i][j]
            rr0 = r if which == "A" else rB
            r1 = np.empty_like(rr0)
            for i in range(n):
                for j in range(n):
                    rr = float(rr0[i, j])
                    bs = (Ww[i - 1][j] * float(rr0[i - 1, j]) + Ww[i][j] * float(rr0[(i + 1) % n, j])
                          + Hh[i][j - 1] * float(rr0[i, j - 1]) + Hh[i][j] * float(rr0[i, (j + 1) % n])) / 4.0
                    r1[i, j] = min(max(rr + D.EPS * (rr * (1 - (rr / 1.2) ** 2) + D.KR * (bs - rr)) + D.SIGMA_R * float(xx[i, j]), -2.0), 2.0)
            if which == "A":
                r = r1
            else:
                rB = r1
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        base = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base[i][j] = sv[i][j]
                elif ca[i][j] != 0:
                    base[i][j] = ca[i][j]
                else:
                    base[i][j] = sr[i][j] if sr[i][j] != 0 else sv[i][j]
        tr = [row[:] for row in base]
        if kind in ("rest", "dial"):
            cur = np.array([[D.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
            v = (lu_on if on else lu_off).solve(cur.ravel()).reshape(n, n)
            for i in range(n):
                for j in range(n):
                    trig = float(v[i, j]) < -D.SIG["theta"] and sr[i][j] != 0
                    was = s_[i][j] >= D.S_MIN
                    if trig and not was:
                        sgn[i][j] = -sr[i][j]
                    s_[i][j] = 1.0 if trig else s_[i][j] * decay
                    if s_[i][j] >= D.S_MIN:
                        tr[i][j] = sgn[i][j]
                        r[i, j] = float(r[i, j]) + D.EPS * D.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
        elif kind == "latch":
            live = [[ca[i][j] != 0 and sr[i][j] != 0 for j in range(n)] for i in range(n)]
            for i in range(n):
                for j in range(n):
                    nl = nd = 0
                    for di in range(-rho, rho + 1):
                        for dj in range(-rho, rho + 1):
                            ii, jj = (i + di) % n, (j + dj) % n
                            if live[ii][jj]:
                                nl += 1
                                if ca[ii][jj] != sr[ii][jj]:
                                    nd += 1
                    zone_new = nl >= D.MIN_ANCHORS and nd >= D.Q_LATCH * nl and sr[i][j] != 0
                    if zone_new and age[i][j] == 0:
                        sgn[i][j] = -sr[i][j]
                    age[i][j] = hold if zone_new else max(age[i][j] - 1, 0)
                    if age[i][j] > 0:
                        tr[i][j] = sgn[i][j]
                        r[i, j] = float(r[i, j]) + D.EPS * D.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
        if kind == "body":
            th_ = [[min(max(float(V[i, j]) * float(V[i, (j + 1) % n]), -1.0), 1.0) for j in range(n)] for i in range(n)]
            tw_ = [[min(max(float(V[i, j]) * float(V[(i + 1) % n, j]), -1.0), 1.0) for j in range(n)] for i in range(n)]
        elif kind == "vote":
            sb = [[vs(float(rB[i, j])) for j in range(n)] for i in range(n)]

            def sgn3(x):
                return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)
            th_ = [[sgn3(sv[i][j] * sv[i][(j + 1) % n] + sr[i][j] * sr[i][(j + 1) % n] + sb[i][j] * sb[i][(j + 1) % n])
                    for j in range(n)] for i in range(n)]
            tw_ = [[sgn3(sv[i][j] * sv[(i + 1) % n][j] + sr[i][j] * sr[(i + 1) % n][j] + sb[i][j] * sb[(i + 1) % n][j])
                    for j in range(n)] for i in range(n)]
        else:
            th_ = [[tr[i][j] * tr[i][(j + 1) % n] for j in range(n)] for i in range(n)]
            tw_ = [[tr[i][j] * tr[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        groups = [(H, Wd, Hs, Ws)] + ([(HB, WB, HsB, WsB)] if two else [])
        for Hh, Ww, Hs_, Ws_ in groups:
            for i in range(n):
                for j in range(n):
                    for Ed, Es, x in ((Hh, Hs_, th_[i][j]), (Ww, Ws_, tw_[i][j])):
                        if x != 0:
                            Es[i][j] = Es[i][j] + eta * (x - Es[i][j])
                            if Es[i][j] != 0:
                                Ed[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """(a) rest and dial against be006's never-SL and dial-SL; (b) the fixed policies against lr005 at the lane clock."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    ok = {}
    for situation in ("memory", "change", "cue"):
        a = sim.run(body, situation, 0.0, ("rest", "dial"), cases, V0, ema0, R0, th, T, theta, {2000}, tag=B6.TAG, window=2000)
        b = B6S.run(body, situation, 4, 0, ("never-SL", "dial-SL"), cases, V0, ema0, R0, th, T, theta, {2000}, tag=B6.TAG,
                    window=2000)
        ok[f"{unit}/{body}/{situation}: rest, dial = be006 never-SL, dial-SL"] = all(
            np.array_equal(a[x], b[x]) for x in ("V", "r", "H", "W"))
    if unit == "S4_t1":
        arms_a = ("record", "body", "vote", "arbiter", "latch")
        arms_b = ("record+parity", "body", "vote2r", "cue", "community-s")
        for situation in L5.SITUATIONS:
            a = sim.run(body, situation, 0.0, arms_a, cases, V0, ema0, R0, th, T, theta, {1000}, tag=L5.TAG, window=1000,
                        size=L5.PATCH, clock=D.LANE_CLOCK, hold=L5.COMMUNITY["community-s"][1])
            b = L5S.run(body, situation, cases, V0, ema0, R0, th, T, theta, D.GAIN, {1000}, tag=L5.TAG, window=1000, arms=arms_b)
            ok[f"{unit}/{body}/{situation}: fixed policies = lr005 at the lane clock"] = all(
                np.array_equal(a[x], b[x]) for x in ("V", "r", "H", "W"))
    return ok


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
    rawf = lambda u, b_, blk=lo: npz(root / "raw" / b_ / u / f"{blk}.npz")
    shard = lambda u, b_, blk=lo: npz(root / "shards" / b_ / u / f"{blk}.npz")
    checks = {}
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "F0_t0") for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks), len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q4 = pool.map(replay_job, [(pk, lo, cpu_of(i)) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, cpu_of(len(Q4_PICKS) + i)) for i, (u_, b_) in enumerate(q3_picks)])

    missing = []
    ntr = D.WINDOW // D.TRACE
    for body, u in D.tasks():
        for blk in range(lo, hi):
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(run[2])
                eps = [x for x in W.ENDS if x != "r_in_old"]
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (len(D.READS), na, D.NCASE)]
                if run[0] == "change":
                    bad += [f"{rn}/r_in_old"] if e.get(f"{rn}/r_in_old", np.zeros(0)).shape != (len(D.READS), na, D.NCASE) else []
                else:
                    bad += [f"{rn}/r_in_old"] if f"{rn}/r_in_old" in e else []
                bad += [f"{rn}/{x}" for x in W.SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in ("n_anc", "n_mis") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (D.NCASE,)]
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for d_ in q3:
        eq.update(d_)
    ev_ok = {}
    for uu in ("S4_t1", "F0_t0"):
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for s in D.SITUATIONS:
            mine = sim.event(s, D.SIZE, 0.0, cases, V0, ema0, R0, T, D.TAG)
            base = {"body": "none", "correlated": "memory"}.get(s, s)
            ref = B1S.event(base, D.SIZE, cases, V0, ema0, R0, T, D.TAG)
            if s in ("body", "correlated"):
                ref["V"] = np.where(ref["m"], -ref["V"], ref["V"])
            ev_ok[f"{uu}/{s}"] = all(np.array_equal(mine[x], ref[x]) for x in ref if ref[x] is not None) and not mine["mis"].any()
        for s in ("none", "memory", "change"):
            mine = sim.event(s, D.SIZE, D.MISREAD_SIGMA, cases, V0, ema0, R0, T, D.TAG)
            gc = GCS.event(s, D.SIZE, D.MISREAD_SIGMA, cases, V0, ema0, R0, T, D.TAG)
            ev_ok[f"{uu}/{s}@1 = gc001"] = bool(np.array_equal(mine["aval"], gc["aval"]) and np.array_equal(mine["mis"], gc["mis"])
                                                 and np.array_equal(mine["r"], gc["r"]) and np.array_equal(mine["V"], gc["V"]))
    eq.update({f"event/{k}": v for k, v in ev_ok.items()})
    checks["Q3_engine"] = {"pass": bool(eq) and all(eq.values()), "n_items": len(eq),
                           "failed": [k for k, v in eq.items() if not v][:10]}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            e, raw = shard(uu, body, blk), rawf(uu, body, blk)
            base_arms = list(RUNS["none@0"][2])
            for arm in ("inactive", "record", "body", "vote"):
                j0 = base_arms.index(arm)
                for other in ("cue@0", "change@0"):
                    j1 = list(RUNS[other][2]).index(arm)
                    same_raw = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"{other}/{x}"][j1]) for x in ("V", "r", "H", "W"))
                    if arm == "vote":
                        same_raw &= all(np.array_equal(raw[f"none@0/{x}"], raw[f"{other}/{x}"]) for x in ("rB", "HB", "WB"))
                    if other == "cue@0":
                        same_ep = all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in EP) and \
                            np.array_equal(e["none@0/trace"][:, j0], e[f"{other}/trace"][:, j1])
                    else:
                        same_ep = np.array_equal(e["none@0/r_in"][:, j0], e[f"{other}/r_in_old"][:, j1]) and all(
                            np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in ("r_dose", "r_dose_in"))
                    items[f"{uu}/{body}/{blk}/{arm}: none@0 = {other}"] = bool(same_raw and same_ep)
            for rn, run in RUNS.items():
                arms = list(run[2])
                if "rest" not in arms:
                    continue
                jr = arms.index("rest")
                for i, arm in enumerate(arms):
                    if arm.startswith("dial-m"):
                        first = D.ARM[arm]["delay"] + 1
                        before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                        ntb = (first - 1) // D.TRACE
                        items[f"{uu}/{body}/{blk}/{rn}/{arm} = rest before its signal"] = all(
                            np.array_equal(e[f"{rn}/{q}"][before, i], e[f"{rn}/{q}"][before, jr]) for q in EP) and \
                            np.array_equal(e[f"{rn}/trace"][:ntb, i], e[f"{rn}/trace"][:ntb, jr])
                if run[0] == "change":
                    items[f"{uu}/{body}/{blk}/{rn}: u(new) + u(old) = 1"] = bool(
                        (e[f"{rn}/r_in"] + e[f"{rn}/r_in_old"] == 1.0).all())
    worst_fft, worst_cg = 0.0, 0.0
    for uu in D.UNITS[:2]:
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        m = B1S.patch(cases, D.SIZE, D.TAG)
        for b_ in D.BODIES:
            raw = rawf(uu, b_)
            aval = np.where(raw["R0"] > 0, 1.0, -1.0)
            rf = raw[f"memory@0/r"][list(RUNS["memory@0"][2]).index("dial")]
            cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
            for lam in (1.0, 3.0):
                g = np.full(cur.shape, lam ** 2)
                v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
                worst_fft = max(worst_fft, float(np.abs(B2S.solve(B2S.factor(g, g), cur) - v1).max()))
            gH, gW = B2S.conductances(B2S.footprint(m, D.SIG["d"]), D.SIG["lam_rest"], D.SIG["lam_sig"])
            v_lu = B2S.solve(B2S.factor(gH, gW), cur)
            v_cg = B1S.cable_cg(cur, gH, gW, np.zeros_like(cur))
            worst_cg = max(worst_cg, float(np.abs(v_lu - v_cg).max()))
    items.update({"lu=fft_uniform": worst_fft <= 1e-9, "lu=cg_footprint": worst_cg <= 1e-9})
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "n_items": len(items),
                                  "failed": [k for k, v in items.items() if not v][:10], "max_lu_fft": worst_fft,
                                  "max_lu_cg": worst_cg}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(uu, body), shard(uu, body)
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for run in D.RUNS:
            rn, na = D.run_name(*run), len(run[2])
            ev = sim.event(run[0], D.SIZE, run[1], cases, V0, ema0, R0, T, D.TAG)
            m, tgt, fp = ev["m"], ev["target"], B2S.footprint(ev["m"], D.SIG["d"])
            tile = lambda x: np.tile(x, (na, 1, 1))
            rf = raw[f"{rn}/r"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            Vf = raw[f"{rn}/V"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            post = tile(ev["r"] > 0)
            got = {"r_in": L5S.inside(rf, tile(tgt), tile(m)), "r_all": S.sign(rf, tile(tgt)),
                   "r_fp": L5S.inside(rf, tile(tgt), tile(fp)), "r_out": L5S.inside(rf, tile(tgt), tile(~fp)),
                   "v_in": L5S.inside(Vf, tile(tgt), tile(m)), "v_all": S.sign(Vf, tile(tgt)),
                   "r_dose": ((rf > 0) != post).mean((-2, -1)),
                   "r_dose_in": (((rf > 0) != post) & tile(m)).sum((-2, -1)) / tile(m).sum((-2, -1))}
            if ev["old"] is not None:
                got["r_in_old"] = L5S.inside(rf, tile(ev["old"]), tile(m))
            for x, v in got.items():
                if not np.array_equal(v.reshape(na, D.NCASE), e[f"{rn}/{x}"][-1]):
                    bad.append(f"{uu}/{body}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    pattern, _ = D.parse_unit(D.UNITS[0])
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    evs = {s: sim.event(s, D.SIZE, 0.0, cases, V0, ema0, R0, T, D.TAG) for s in D.SITUATIONS}
    m, am0 = evs["none"]["m"], evs["none"]["am"]
    aval0 = np.where(R0 > 0, 1.0, -1.0)
    cons = lambda ev: all(np.array_equal(ev[x], y) for x, y in zip(("H", "W"), sim.edges_from(sim.bonds(ev["r"], True))))
    eff["memory_and_correlated_invert_the_patch_record_with_consistent_bonds"] = all(
        np.array_equal(evs[s]["r"], np.where(m, -R0, R0)) and cons(evs[s]) for s in ("memory", "correlated"))
    eff["body_and_correlated_invert_the_patch_body"] = all(
        np.array_equal(evs[s]["V"], np.where(m, -V0, V0)) for s in ("body", "correlated")) and np.array_equal(evs["body"]["r"], R0)
    sh = evs["shared"]
    dh, dw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
    eff["shared_kills_record_inside_bonds_and_anchors"] = bool(
        (sh["r"][m] == 0).all() and (sh["H"][dh] == 0).all() and (sh["W"][dw] == 0).all() and (sh["Hb"][dh] == 0).all()
        and not (sh["am"] & m).any() and np.array_equal(sh["am"], am0 & ~m))
    flipped = (evs["cue"]["aval"] != aval0) & am0
    eff["cue_flips_exactly_a_quarter_of_the_anchors"] = all(int(flipped[c].sum()) == int(am0[c].sum()) // 4 for c in range(len(cases)))
    ch = evs["change"]
    eff["change_flips_exactly_the_patch_anchors_and_target"] = bool(
        np.array_equal(ch["aval"], np.where(m, -aval0, aval0)) and np.array_equal(ch["target"], np.where(m, -T, T))
        and np.array_equal(ch["old"], T))
    ev1 = sim.event("none", D.SIZE, D.MISREAD_SIGMA, cases, V0, ema0, R0, T, D.TAG)
    eff["the_misread_changes_anchors_only"] = bool(np.array_equal(ev1["r"], R0) and np.array_equal(ev1["V"], V0)
                                                   and np.array_equal(ev1["am"], am0) and ev1["mis"].any())
    fps = {a_: sim.footprint(m, D.ARM[a_]["d"], D.ARM[a_]["shift"]) for a_ in ("dial", "dial-d0", "dial-d8", "dial-s4", "dial-s6")}
    eff["footprints_have_their_declared_sizes_and_overlaps"] = bool(
        (fps["dial"].sum((-2, -1)) == 64).all() and (fps["dial"] >= m).all() and np.array_equal(fps["dial-d0"], m)
        and (fps["dial-d8"].sum((-2, -1)) == 400).all() and ((fps["dial-s4"] & m).sum((-2, -1)) == 8).all()
        and not (fps["dial-s6"] & m).any())
    sig_ok, rec_ok = True, True
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn = D.run_name(*run)
                for i, arm in enumerate(run[2]):
                    n_on = meta["signal_updates"][rn][arm] / D.NCASE
                    on = e[f"{rn}/onset"][i]
                    if D.ARM[arm]["kind"] == "dial":
                        sig_ok &= n_on == D.SIG["duration"]
                        rec_ok &= bool(((on >= 0) & (on <= 1)).all())
                    else:
                        sig_ok &= n_on == 0
                        rec_ok &= bool((on == -1).all())
    eff["every_dial_on_for_exactly_1000_updates_every_other_arm_never"] = bool(sig_ok)
    eff["onset_for_the_dials_only"] = bool(rec_ok)
    eff["dial_delays_are_round_m_t_star"] = all(D.ARM[f"dial-m{m_:g}"]["delay"] == int(round(m_ * D.T_STAR)) for m_ in D.MULTS)
    eff["the_clock"] = (D.CLOCK["eta"] == 3e-4 and abs(D.CLOCK["rate"] - 3e-5) <= 1e-18 and D.CLOCK["tau_c"] == 15000
                        and round(D.T_STAR) == 1959)
    hb, nsteps = D.STRENGTH0, 0
    while hb > 0:
        hb, nsteps = hb + D.CLOCK["eta"] * (-1.0 - hb), nsteps + 1
    eff["bond_crosses_zero_after_ceil_t_star"] = nsteps == math.ceil(D.T_STAR)
    Pq = {"am": np.ones((1, D.SIDE, D.SIDE), bool), "aval": -np.ones((1, D.SIDE, D.SIDE))}
    Vq, rq = np.ones((1, D.SIDE, D.SIDE)), np.ones((1, D.SIDE, D.SIDE))
    latch = (np.zeros((1, D.SIDE, D.SIDE), int), np.zeros((1, D.SIDE, D.SIDE)))
    sim.latch_targets(Vq, rq, Pq, latch, 50)
    agree = {"am": np.ones((1, D.SIDE, D.SIDE), bool), "aval": np.ones((1, D.SIDE, D.SIDE))}
    held = 0
    while True:
        _, _, (zone, _) = sim.latch_targets(Vq, rq, agree, latch, 50)
        if not zone[0, 0, 0]:
            break
        held += 1
    eff["the_latch_holds_its_decision_for_exactly_its_hold"] = held + 1 == 50
    eff["cut_is_the_exact_quantile"] = abs(NormalDist().cdf(-cut_for(D.CLOCK["rate"])) - D.CLOCK["rate"]) <= 1e-12
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    q8 = {}
    pattern, theta = D.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    for s in ("memory", "correlated"):
        o1 = sim.run("li4", s, 0.0, ("latch", "dial", "latch", "vote"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        o2 = sim.run("li4", s, 0.0, ("vote", "dial", "latch"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        k = D.NCASE
        blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W")]
        q8[f"{s}: latch listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o1, 2)))
        q8[f"{s}: reordering the arms changes no branch"] = all(
            all(np.array_equal(x, y) for x, y in zip(blk_(o1, i), blk_(o2, j))) for i, j in ((0, 2), (1, 1), (3, 0)))
    checks["Q8_pairing"] = {"pass": all(q8.values()), "items": q8}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, uu = key.split("/")[:2]
        walls.setdefault((b_, uu), []).append(t["cpu_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 40 and forecast_h <= 12 and manifest["worker_maxrss_mb_peak"] <= 2048
                                           and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_cpu_h": round(cpu / 3600, 2), "forecast_wall_h_12": round(float(forecast_h), 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar001.{mod}", "--root", str(root), "--out", str(out / name)],
                            cwd=LANE, capture_output=True, text=True, env=env)
             for mod, name in (("analyze", ""), ("predict", "predictions_scored.json"), ("tables", "TABLES.md"))]
    expected = [out / f for f in ("summary.json", "reliability.json", "ranking.json", "side_arms.json",
                                  "predictions_scored.json", "TABLES.md")]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from ar001 import predict as PR
    stmts = sorted({p["stmt"] for p in PR.PARTS})
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in expected)
                                    and sorted(got) == stmts and max(sizes.values(), default=0) <= 262144,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes}

    worst4, items4 = 0.0, {}
    for (uu, body, s, z, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu, body)
        rn = D.run_name(s, z)
        k = list(RUNS[rn][2]).index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{rn}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{rn}/W"][k, ci]).max()))
        items4[f"{uu}/{body}/{rn}/{arm}/case{ci}"], worst4 = d, max(worst4, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst4 <= 1e-8, "max_abs_difference": worst4, "items": items4}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": [lo, hi], "tag": D.TAG, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
