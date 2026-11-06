"""Qualification of AR003 on engineering shards; criteria fixed in advance.

python -m ar003.checks --root ROOT --cpus LIST [--debug]
  (writes ar003/frozen/qualification_receipt.json; with --debug, on the debug stage's block 900158, ROOT/debug_qualification_receipt.json)

Q1  complete and finite: every task's shard holds every run's endpoints at its declared shape (reads x arms x cases;
    r_in_old exactly in the change run; r_in_L<side> for every other size exactly in the 4 x 4 runs of none and cue
    damage), its trace, its scalars and the detectors' scalars; every value finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine, bit for bit (V, r and bonds, both records where held, endpoints, scalars and trace): (a) a never-firing
    vote-default arm equals ar001.sim.run's vote over 2,000 updates in memory, correlated, shared, cue and change at the
    4 x 4 patch, memory at 8 x 8 and body at 2 x 2 (S4_t1 and F0_t0, both bodies); (b) the worker's merged arms equal
    the separate calls for one task's runs at 1,000 updates (ar001.worker.one for the vote, ar002.worker.one for det);
    (c) the vote, det and vms of none and cue damage are independent of the patch (their runs at 2 x 2 and 8 x 8 equal
    the 4 x 4 run's V, r and bonds); the vote under the misread equals the vote without it
Q4  independent replay: per-site loops for the event, the body, bond noise on both records, both records' own bond sums,
    the vote's targets (the sign of the summed relations of the body and the two records), the detector by integral
    images on wrap-padded arrays at each of DET_STAR's boxes (with the surround), the footprint, the cable equation by
    sparse LU on be001.checks' own matrix (the footprint's conductances set per site), the triggers inside the footprint
    during the window only, the slow state, the override on the bonds touching a committed cell (LR004's arbiter's sign
    at the other end), the pull and both records' Hebbian learners; reproduce five full vote-default branches (8,000
    updates; vms and vdial; at 2, 4 and 8; one under scattered cue damage) within 1e-8, both records' bonds exactly, and the detector's onset, zone and
    footprint exactly
Q5  aliases: (a) every vote-default arm equals the vote at every read and trace point before its onset, and throughout
    where it never fires (per case; both records' final states too); (b) det and ms (both rest until their onsets) equal
    each other before the earlier onset; (c) u(new) + u(old) = 1 exactly for every branch of the change run; (d) the vote
    is bit-identical across none@0, cue@0 and change@0 (the second record too); (e) vdial is on for exactly 1,000 updates
    in every case
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states and the events (at each run's patch
    side), r_in_L<side> from the final record and that side's patch, equal the saved ones; each detector's footprint is
    its saved zone dilated by 2, and its scalars follow from them
Q7  efficacy: the events do exactly their rule; the second record at t = 0 is the acquired record with fresh bonds in
    memory and correlated damage and the post-event record otherwise; the vote-default targets on synthetic states (no
    commitment: the vote's exactly; a committed cell: rel(t) on its four bonds and the vote's elsewhere; triggers only in
    the footprint during the window, never after it; the second record learns the first's targets); the detector on
    synthetic states (an island of disagreeing anchors at each box of DET_STAR fires it over the island; one
    disagreeing anchor in the surround stops it; fewer than n do not fire; its windows equal the single-box channel's at
    every box); each fired vote-default arm's window is open for exactly min(1,000, 8,001 - onset) updates; the clock
Q8  pairing: an arm listed twice gives bit-identical branches, and vms run with fewer arms equals it run with others
Q9  resources: forecast development within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, disk
Q10 reader dry run: analyze, predict and tables complete on the shards, every statement is scored, and every AR003 git
    file is 256 KB or less
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

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar001 import worker as AW  # noqa: E402
from ar002 import checks as C2  # noqa: E402
from ar002 import sim as A2S  # noqa: E402
from ar002 import worker as W2  # noqa: E402
from ar003 import design as D  # noqa: E402
from ar003 import sim  # noqa: E402
from ar003 import worker as W  # noqa: E402
from be001.checks import cable_matrix  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "ar003" / "frozen"
WORKERS = 12
RUNS = {D.run_name(*x): x for x in D.RUNS}
ARMS_OF = {k: list(D.arms_of(v)) for k, v in RUNS.items()}
VD_ARMS = ("vote", "vms", "vdial")
DETS = ("det", "ms", "vms")
Q4_PICKS = (("S4_t1", "li4", "memory", 0.0, "vms", 0, 4),
            ("F0_t0", "dw", "correlated", 0.0, "vms", 1, 8),
            ("S4_t0", "dw", "memory", 0.0, "vms", 2, 2),
            ("F0_t1", "li4", "cue", 0.0, "vms", 3, 4),
            ("S4_t1", "dw", "memory", 0.0, "vdial", 4, 4))
npz, replay_detector, wrap_counts = C2.npz, C2.replay_detector, C2.wrap_counts


def s_replay_vd(unit, body, situation, sigma, arm, ci, block, window=D.WINDOW, tag=D.TAG, clock=None, size=D.SIZE):
    """One vote-default branch end to end with independent per-site code; returns final V, r, H, W, rB, HB, WB and
    (onset, zone, footprint)."""
    clock = A.CLOCK if clock is None else clock
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    cfg = D.VD_DETECTORS[arm]
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(tag, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    perm = address(tag, *key, "anchors", A.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // A.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]

    def vs(x):
        return 1.0 if x >= A.VMIN else (-1.0 if x <= -A.VMIN else 0.0)

    def bonds_of(rv):
        sg = [[1.0 if rv[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
        H_ = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        W_ = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        return H_, W_, [[A.STRENGTH0 * x for x in row] for row in H_], [[A.STRENGTH0 * x for x in row] for row in W_]

    rv0 = R0c.copy()
    if situation in ("memory", "correlated"):
        rv0 = np.where(np.array(patch), -R0c, R0c)
    if situation in ("body", "correlated"):
        V = np.where(np.array(patch), -V, V)
    H, Wd, Hs, Ws = bonds_of(rv0)
    r = rv0.copy()
    if situation == "shared":
        nb = A.KILL_SD * address(tag, *key, "newborn").standard_normal((n, n))
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
    if situation in ("memory", "correlated"):                   # the event hit the first record only
        rB = R0c.copy()
        HB, WB, HsB, WsB = bonds_of(R0c)
    else:
        rB = r.copy()
        HB, WB, HsB, WsB = ([row[:] for row in x] for x in (H, Wd, Hs, Ws))
    cut = NormalDist().inv_cdf(1.0 - clock["rate"])
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    streams = [Stream(tag, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    streamsB = [Stream(tag, cases, x, "B", side=n) for x in ("record-noise", "bond-noise")]
    rest_g, sig2 = A.SIG["lam_rest"] ** 2, A.SIG["lam_sig"] ** 2
    lu_on, t_on, zone, fpm = None, 0, None, None
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / clock["tau_c"])

    def rec_step(rr_, Hh, Ww, xi):
        r1 = np.empty_like(rr_)
        for i in range(n):
            for j in range(n):
                rr = float(rr_[i, j])
                bs = (Ww[i - 1][j] * float(rr_[i - 1, j]) + Ww[i][j] * float(rr_[(i + 1) % n, j])
                      + Hh[i][j - 1] * float(rr_[i, j - 1]) + Hh[i][j] * float(rr_[i, (j + 1) % n])) / 4.0
                r1[i, j] = min(max(rr + A.EPS * (rr * (1 - (rr / 1.2) ** 2) + A.KR * (bs - rr)) + A.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        return r1

    def noise(Hh, Ww, Hs_, Ws_, zb):
        for i in range(n):
            for j in range(n):
                if float(zb[i, j]) > cut:
                    Hh[i][j], Hs_[i][j] = -Hh[i][j], -Hs_[i][j]
                elif float(zb[i, j]) < -cut:
                    Ww[i][j], Ws_[i][j] = -Ww[i][j], -Ws_[i][j]

    for t in range(window):
        if t % A.CHUNK == 0:
            bufs = [st.take(A.CHUNK)[:, ci] for st in streams]
            bufsB = [st.take(A.CHUNK)[:, ci] for st in streamsB]
        z, xi, zb = (bufs[q][t % A.CHUNK] for q in range(3))
        xiB, zbB = (bufsB[q][t % A.CHUNK] for q in range(2))
        w = screened(V, L) if alpha else None
        new = np.empty_like(V)
        for i in range(n):
            for j in range(n):
                vv = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                drift = vv - vv * vv * vv + float(thc[i, j]) + (nbm - vv)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(vv + 0.2 * drift + A.SIGMA * float(z[i, j]), -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (A.GAIN * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
        noise(H, Wd, Hs, Ws, zb)
        r = rec_step(r, H, Wd, xi)
        noise(HB, WB, HsB, WsB, zbB)
        rB = rec_step(rB, HB, WB, xiB)
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        sB = [[vs(float(rB[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        if t_on == 0 and not cfg.get("never"):
            held = np.zeros((n, n), bool)
            if cfg.get("oracle"):
                held = np.array(patch)
            else:
                ch = cfg["cue"]
                for bx in ch["boxes"]:
                    f = replay_detector(dict(ch, box=bx), "cue", sv, sr, ca)
                    if f.any():
                        for i in range(n):
                            for j in range(n):
                                if f[i, j]:
                                    for di in range(bx):
                                        for dj in range(bx):
                                            held[(i + di) % n, (j + dj) % n] = True
            if held.any():
                t_on, zone = t + 1, held
                dd = A.SIG["d"]
                fpm = np.zeros((n, n), bool)
                for i in range(n):
                    for j in range(n):
                        if zone[i, j]:
                            for di in range(-dd, dd + 1):
                                for dj in range(-dd, dd + 1):
                                    fpm[(i + di) % n, (j + dj) % n] = True
                gh = [[sig2 if (fpm[i, j] or fpm[i, (j + 1) % n]) else rest_g for j in range(n)] for i in range(n)]
                gw = [[sig2 if (fpm[i, j] or fpm[(i + 1) % n, j]) else rest_g for j in range(n)] for i in range(n)]
                lu_on = splu(cable_matrix(n, gh, gw))
        on = t_on > 0 and t_on <= t + 1 < t_on + A.SIG["duration"]
        xv_h = [[float(np.sign(sv[i][j] * sv[i][(j + 1) % n] + sr[i][j] * sr[i][(j + 1) % n] + sB[i][j] * sB[i][(j + 1) % n]))
                 for j in range(n)] for i in range(n)]
        xv_w = [[float(np.sign(sv[i][j] * sv[(i + 1) % n][j] + sr[i][j] * sr[(i + 1) % n][j] + sB[i][j] * sB[(i + 1) % n][j]))
                 for j in range(n)] for i in range(n)]
        v = None
        if on:
            cur = np.array([[A.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
            v = lu_on.solve(cur.ravel()).reshape(n, n)
        com = [[False] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                trig = on and float(v[i, j]) < -A.SIG["theta"] and sr[i][j] != 0 and bool(fpm[i, j])
                was = s_[i][j] >= A.S_MIN
                if trig and not was:
                    sgn[i][j] = -sr[i][j]
                s_[i][j] = 1.0 if trig else s_[i][j] * decay
                com[i][j] = s_[i][j] >= A.S_MIN
        xh, xw = xv_h, xv_w
        if any(any(row) for row in com):
            tr = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                        tr[i][j] = sv[i][j]
                    elif ca[i][j] != 0:
                        tr[i][j] = ca[i][j]
                    else:
                        tr[i][j] = sr[i][j] if sr[i][j] != 0 else sv[i][j]
                    if com[i][j]:
                        tr[i][j] = sgn[i][j]
                        r[i, j] = float(r[i, j]) + A.EPS * A.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
            xh = [[tr[i][j] * tr[i][(j + 1) % n] if (com[i][j] or com[i][(j + 1) % n]) else xv_h[i][j] for j in range(n)]
                  for i in range(n)]
            xw = [[tr[i][j] * tr[(i + 1) % n][j] if (com[i][j] or com[(i + 1) % n][j]) else xv_w[i][j] for j in range(n)]
                  for i in range(n)]
        for i in range(n):
            for j in range(n):
                for Ed, Es, EdB, EsB, x in ((H, Hs, HB, HsB, xh[i][j]), (Wd, Ws, WB, WsB, xw[i][j])):
                    if x != 0:
                        Es[i][j] = Es[i][j] + eta * (x - Es[i][j])
                        if Es[i][j] != 0:
                            Ed[i][j] = 1.0 if Es[i][j] > 0 else -1.0
                        EsB[i][j] = EsB[i][j] + eta * (x - EsB[i][j])
                        if EsB[i][j] != 0:
                            EdB[i][j] = 1.0 if EsB[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd), rB, np.array(HB), np.array(WB), (t_on, zone, fpm)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay_vd(*pick[:6], block, size=pick[6])


def q3_job(args):
    """(a) a never-firing vote-default arm against ar001's vote; (c) the size-free runs and the misread vote."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, "engineering")
    k = D.NCASE
    ok = {}
    F = ("V", "r", "H", "W", "rB", "HB", "WB")

    def same(a, b, ia, ib, fields=F):
        sl = lambda o, x, i: o[x][i * k:(i + 1) * k] if x not in ("rB", "HB", "WB") or len(o[x]) > k else o[x]
        return (all(np.array_equal(sl(a, x, ia), sl(b, x, ib)) for x in fields)
                and all(np.array_equal(a[e][:, ia * k:(ia + 1) * k], b[e][:, ib * k:(ib + 1) * k]) for e in sim.ENDS if e in a)
                and all(np.array_equal(a[e][ia * k:(ia + 1) * k], b[e][ib * k:(ib + 1) * k]) for e in ("opened", "opened_out"))
                and np.array_equal(a["trace"][:, ia * k:(ia + 1) * k], b["trace"][:, ib * k:(ib + 1) * k]))
    for situation, size in (("memory", 4), ("correlated", 4), ("shared", 4), ("cue", 4), ("change", 4), ("memory", 8),
                            ("body", 2)):
        a = A1S.run(body, situation, 0.0, ("vote",), cases, V0, ema0, R0, th, T, theta, {1000, 2000}, tag=D.TAG, window=2000,
                    size=size)
        b = sim.run_vd(body, situation, 0.0, ("vms", "vote"), cases, V0, ema0, R0, th, T, theta, {1000, 2000}, tag=D.TAG,
                       window=2000, size=size)
        ok[f"{unit}/{body}/{situation}@L{size}: never-firing vote-default = ar001 vote"] = same(a, b, 0, 1)
    for situation in ("none", "cue"):
        base = {}
        for size in (4, 2, 8):
            o1 = A1S.run(body, situation, 0.0, ("vote",), cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.TAG, window=1000, size=size)
            o2 = A2S.run_det(body, situation, 0.0, ("det", "ms"), cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.TAG,
                             window=1000, size=size, detectors=D.DETECTORS)
            o3 = sim.run_vd(body, situation, 0.0, ("vms",), cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.TAG, window=1000,
                            size=size)
            got = [o[x] for o in (o1, o2, o3) for x in ("V", "r", "H", "W")] + [o1["rB"], o3["rB"]]
            if size == 4:
                base = got
            else:
                ok[f"{unit}/{body}/{situation}: vote, det, ms and vms at L {size} = at L 4"] = all(
                    np.array_equal(x, y) for x, y in zip(base, got))
    for situation in ("none", "memory"):
        a0 = A1S.run(body, situation, 0.0, ("vote",), cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.TAG, window=1000)
        a1 = A1S.run(body, situation, D.MISREAD_SIGMA, ("vote",), cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.TAG, window=1000)
        ok[f"{unit}/{body}/{situation}: the vote under the misread = without it"] = same(a0, a1, 0, 0)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("debug") if a.debug else D.stage_blocks("preflight")
    lo = blocks[0]
    receipt_path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda u, b_, blk=lo: npz(root / "raw" / b_ / u / f"{blk}.npz")
    shard = lambda u, b_, blk=lo: npz(root / "shards" / b_ / u / f"{blk}.npz")
    tag = json.loads(str(np.load(root / "shards" / "dw" / D.UNITS[0] / f"{lo}.npz")["__meta__"]))["tag"]
    checks = {}
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "F0_t0") for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks), len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q4 = pool.map(replay_job, [(pk, lo, cpu_of(i)) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, cpu_of(len(Q4_PICKS) + i)) for i, (u_, b_) in enumerate(q3_picks)])

    missing = []
    ntr = D.WINDOW // D.TRACE
    for body, u in D.tasks():
        for blk in blocks:
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all()]
            want = set()
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(D.arms_of(run))
                for x in W.ENDS:
                    if x == "r_in_old" and run[0] != "change":
                        continue
                    want.add(f"{rn}/{x}")
                    bad += [f"{rn}/{x}"] if e.get(f"{rn}/{x}", np.zeros(0)).shape != (len(D.READS), na, D.NCASE) else []
                for x in W.SCALARS + W.DET_SCALARS:
                    want.add(f"{rn}/{x}")
                    bad += [f"{rn}/{x}"] if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE) else []
                for x in ("n_anc", "n_mis"):
                    want.add(f"{rn}/{x}")
                    bad += [f"{rn}/{x}"] if e.get(f"{rn}/{x}", np.zeros(0)).shape != (D.NCASE,) else []
                want.add(f"{rn}/trace")
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
                if run[0] in D.SIZE_FREE and run[5] == D.SIZE:
                    for L in D.SIZES:
                        if L != D.SIZE:
                            want.add(f"{rn}/r_in_L{L}")
                            bad += [f"{rn}/r_in_L{L}"] if e.get(f"{rn}/r_in_L{L}", np.zeros(0)).shape != (na, D.NCASE) else []
            bad += [f"unexpected {k}" for k in set(e) - want]
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, lo, "engineering", str(serial), tag=tag)
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for d_ in q3:
        eq.update(d_)
    pattern, theta = D.parse_unit("S4_t1")
    prep = A1S.prepare(pattern, lo, "engineering")
    for run in (RUNS["none@0"], RUNS["memory@0-L8"], RUNS["shared@0-L2"], RUNS["memory@1"]):
        key = D.run_name(*run)
        e3, raw3, _ = W.one("dw", "S4_t1", lo, "engineering", run, D.TAG, prep, window=1000, reads=(500, 1000))
        na = len(D.arms_of(run))
        n1, nd = len(run[2]), len(run[3])
        okk = True
        if n1:
            e1, raw1, _ = AW.one("dw", "S4_t1", lo, "engineering", (run[0], run[1], run[2]), D.TAG, prep, window=1000,
                                 reads=(500, 1000)) if run[5] == D.SIZE else (None, None, None)
            if e1 is not None:
                okk &= all(np.array_equal(e1[k_], e3[k_][..., :n1, :] if e1[k_].ndim == 3 and not k_.endswith("trace") else
                                          (e3[k_][:n1] if e1[k_].ndim == 2 else e3[k_][:, :n1]))
                           for k_ in e1 if not k_.endswith(("n_anc", "n_mis")) and k_ in e3)
                okk &= all(np.array_equal(raw1[f"{key}/{x}"], raw3[f"{key}/{x}"][:n1]) for x in ("V", "r", "H", "W"))
            else:
                o1 = A1S.run("dw", run[0], run[1], run[2], *prep, 1.0, {500, 1000}, tag=D.TAG, window=1000, size=run[5])
                okk &= all(np.array_equal(e3[f"{key}/{x}"][:, :n1], o1[x].reshape(2, n1, D.NCASE)) for x in sim.ENDS if x in o1)
                okk &= all(np.array_equal(raw3[f"{key}/{x}"][:n1], o1[x].reshape(n1, D.NCASE, D.SIDE, D.SIDE).astype(raw3[f"{key}/{x}"].dtype))
                           for x in ("V", "r", "H", "W"))
        if "det" in run[3]:
            r2 = (run[0], run[1], (), ("det",), run[5])
            e2, raw2, _ = W2.one("dw", "S4_t1", lo, "engineering", r2, D.TAG, prep, window=1000, reads=(500, 1000))
            jd = D.arms_of(run).index("det")
            okk &= all(np.array_equal(e2[f"{key}/{x}"][:, 0], e3[f"{key}/{x}"][:, jd]) for x in sim.ENDS if f"{key}/{x}" in e2)
            okk &= all(np.array_equal(e2[f"{key}/{x}"][0], e3[f"{key}/{x}"][jd]) for x in ("det_on", "det_fp", "det_zone"))
            okk &= all(np.array_equal(raw2[f"{key}/{x}"][0], raw3[f"{key}/{x}"][jd]) for x in ("V", "r", "H", "W"))
        o3 = sim.run_vd("dw", run[0], run[1], run[4], *prep, 1.0, {500, 1000}, tag=D.TAG, window=1000, size=run[5])
        nv = len(run[4])
        okk &= all(np.array_equal(e3[f"{key}/{x}"][:, na - nv:], o3[x].reshape(2, nv, D.NCASE)) for x in sim.ENDS if x in o3)
        okk &= all(np.array_equal(raw3[f"{key}/{x}"][na - nv:], o3[x].reshape(nv, D.NCASE, D.SIDE, D.SIDE).astype(raw3[f"{key}/{x}"].dtype))
                   for x in ("V", "r", "H", "W"))
        eq[f"worker {key}: merged arms = the separate calls"] = bool(okk)
    checks["Q3_engine"] = {"pass": bool(eq) and all(eq.values()), "n_items": len(eq),
                           "failed": [k for k, v in eq.items() if not v][:10]}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, uu in D.tasks():
        for blk in blocks:
            e, raw = shard(uu, body, blk), rawf(uu, body, blk)
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            for rn, run in RUNS.items():
                arms = ARMS_OF[rn]
                if "vote" in arms:
                    jv = arms.index("vote")
                    vds = list(run[4])
                    for arm in vds:
                        i = arms.index(arm)
                        on = e[f"{rn}/det_on"][i]
                        okc = True
                        for c in range(D.NCASE):
                            first = on[c] if on[c] > 0 else D.WINDOW + 1
                            before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                            ntb = int((first - 1) // D.TRACE)
                            okc &= all(np.array_equal(e[f"{rn}/{q}"][before, i, c], e[f"{rn}/{q}"][before, jv, c]) for q in EP)
                            okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, i, c], e[f"{rn}/trace"][:ntb, jv, c]))
                            if on[c] < 0:
                                okc &= all(np.array_equal(raw[f"{rn}/{x}"][i, c], raw[f"{rn}/{x}"][jv, c]) for x in ("V", "r", "H", "W"))
                                ib = 1 + vds.index(arm)
                                okc &= all(np.array_equal(raw[f"{rn}/{x}"][ib, c], raw[f"{rn}/{x}"][0, c]) for x in ("rB", "HB", "WB"))
                        items[f"{uu}/{body}/{blk}/{rn}/{arm} = the vote before its onset"] = bool(okc)
                if "det" in arms and "ms" in arms:
                    i1, i2 = arms.index("det"), arms.index("ms")
                    o1, o2 = e[f"{rn}/det_on"][i1], e[f"{rn}/det_on"][i2]
                    okc = True
                    for c in range(D.NCASE):
                        first = min(x if x > 0 else D.WINDOW + 1 for x in (o1[c], o2[c]))
                        before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                        ntb = int((first - 1) // D.TRACE)
                        okc &= all(np.array_equal(e[f"{rn}/{q}"][before, i1, c], e[f"{rn}/{q}"][before, i2, c]) for q in EP)
                        okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, i1, c], e[f"{rn}/trace"][:ntb, i2, c]))
                    items[f"{uu}/{body}/{blk}/{rn}: det = ms before the earlier onset"] = bool(okc)
                if run[0] == "change":
                    items[f"{uu}/{body}/{blk}/{rn}: u(new) + u(old) = 1"] = bool((e[f"{rn}/r_in"] + e[f"{rn}/r_in_old"] == 1.0).all())
                if "vdial" in arms:
                    iv = arms.index("vdial")
                    items[f"{uu}/{body}/{blk}/{rn}: vdial fires at update 1 and is on for 1,000 updates in every case"] = bool(
                        (e[f"{rn}/det_on"][iv] == 1).all() and meta["signal_updates"][rn]["vdial"] == A.SIG["duration"] * D.NCASE)
            j0 = ARMS_OF["none@0"].index("vote")
            for other in ("cue@0", "change@0"):
                j1 = ARMS_OF[other].index("vote")
                same_raw = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"{other}/{x}"][j1]) for x in ("V", "r", "H", "W"))
                same_raw &= all(np.array_equal(raw[f"none@0/{x}"][0], raw[f"{other}/{x}"][0]) for x in ("rB", "HB", "WB"))
                if other == "cue@0":
                    same_ep = all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in EP)
                else:
                    same_ep = np.array_equal(e["none@0/r_in"][:, j0], e[f"{other}/r_in_old"][:, j1])
                items[f"{uu}/{body}/{blk}/vote: none@0 = {other}"] = bool(same_raw and same_ep)
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "n_items": len(items),
                                  "failed": [k for k, v in items.items() if not v][:10]}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(uu, body), shard(uu, body)
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, lo, "engineering")
        for run in D.RUNS:
            rn = D.run_name(*run)
            na = len(ARMS_OF[rn])
            ev = A1S.event(run[0], run[5], run[1], cases, V0, ema0, R0, T, tag)
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
            for L in D.SIZES:
                if f"{rn}/r_in_L{L}" in e:
                    mL = np.tile(A1S.event(run[0], L, run[1], cases, V0, ema0, R0, T, tag)["m"], (na, 1, 1))
                    if not np.array_equal(L5S.inside(rf, tile(tgt), mL).reshape(na, D.NCASE), e[f"{rn}/r_in_L{L}"]):
                        bad.append(f"{uu}/{body}/{rn}/r_in_L{L}")
            dets = list(run[3]) + list(run[4])
            zone, fpd = raw[f"{rn}/zone"], raw[f"{rn}/fp"]
            for i, arm in enumerate(dets):
                ai = ARMS_OF[rn].index(arm)
                okf = np.array_equal(B2S.footprint(zone[i], D.SIG["d"]) & (e[f"{rn}/det_on"][ai] > 0)[:, None, None], fpd[i])
                okf &= np.array_equal(zone[i].sum((-2, -1)).astype(float), e[f"{rn}/det_zone"][ai])
                okf &= np.array_equal(fpd[i].sum((-2, -1)).astype(float), e[f"{rn}/det_fp"][ai])
                okf &= np.array_equal((fpd[i] & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_fp_in"][ai])
                okf &= np.array_equal((zone[i] & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_zone_in"][ai])
                if not okf:
                    bad.append(f"{uu}/{body}/{rn}/{arm}/footprint")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    pattern, _ = D.parse_unit(D.UNITS[0])
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, lo, "engineering")
    evs = {s: A1S.event(s, D.SIZE, 0.0, cases, V0, ema0, R0, T, tag) for s in D.SITUATIONS}
    m, am0 = evs["none"]["m"], evs["none"]["am"]
    aval0 = np.where(R0 > 0, 1.0, -1.0)
    cons = lambda ev: all(np.array_equal(ev[x], y) for x, y in zip(("H", "W"), A1S.edges_from(A1S.bonds(ev["r"], True))))
    eff["memory_and_correlated_invert_the_patch_record_with_consistent_bonds"] = all(
        np.array_equal(evs[s]["r"], np.where(m, -R0, R0)) and cons(evs[s]) for s in ("memory", "correlated"))
    eff["body_and_correlated_invert_the_patch_body"] = all(
        np.array_equal(evs[s]["V"], np.where(m, -V0, V0)) for s in ("body", "correlated")) and np.array_equal(evs["body"]["r"], R0)
    sh = evs["shared"]
    dh, dw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
    eff["shared_kills_record_inside_bonds_and_anchors"] = bool(
        (sh["r"][m] == 0).all() and (sh["H"][dh] == 0).all() and (sh["W"][dw] == 0).all() and not (sh["am"] & m).any()
        and np.array_equal(sh["am"], am0 & ~m))
    flipped = (evs["cue"]["aval"] != aval0) & am0
    eff["cue_flips_exactly_a_quarter_of_the_anchors"] = all(int(flipped[c].sum()) == int(am0[c].sum()) // 4 for c in range(len(cases)))
    ch_ = evs["change"]
    eff["change_flips_exactly_the_patch_anchors_and_target"] = bool(
        np.array_equal(ch_["aval"], np.where(m, -aval0, aval0)) and np.array_equal(ch_["target"], np.where(m, -T, T))
        and np.array_equal(ch_["old"], T))
    ev1 = A1S.event("none", D.SIZE, D.MISREAD_SIGMA, cases, V0, ema0, R0, T, tag)
    eff["the_misread_changes_anchors_only"] = bool(np.array_equal(ev1["r"], R0) and np.array_equal(ev1["V"], V0)
                                                   and np.array_equal(ev1["am"], am0) and ev1["mis"].any())
    idx1 = np.arange(len(cases))
    sb = {s: sim.second_record(s, evs[s], R0, idx1) for s in ("memory", "correlated", "none", "shared", "change")}
    H0, W0 = A1S.edges_from(A1S.bonds(R0, True))
    eff["the_second_record_at_t0"] = bool(
        all(np.array_equal(sb[s][0], R0) and np.array_equal(sb[s][1], H0) and np.array_equal(sb[s][2], W0)
            and np.array_equal(sb[s][3], A.STRENGTH0 * H0) for s in ("memory", "correlated"))
        and all(np.array_equal(sb[s][0], evs[s]["r"]) and np.array_equal(sb[s][1], evs[s]["H"])
                and np.array_equal(sb[s][3], evs[s]["Hb"]) for s in ("none", "shared", "change")))
    # the vote-default targets on synthetic states (one case)
    n = D.SIDE
    rng = np.random.default_rng(20261101)
    Vs = np.where(rng.random((1, n, n)) < 0.5, 1.0, -1.0)
    rs = np.where(rng.random((1, n, n)) < 0.5, 1.2, -1.2)
    rBs = np.where(rng.random((1, n, n)) < 0.5, 1.2, -1.2)
    Ps = {"am": rng.random((1, n, n)) < 0.25, "aval": np.where(rng.random((1, n, n)) < 0.5, 1.0, -1.0)}
    st = A2S.new_det(1)
    xh, xw, (com, tt) = sim.vd_targets({"tau_c": 15000.0}, Vs, rs, rBs, Ps, st, np.zeros(1, bool), np.zeros(1, bool), np.zeros((1, n, n), bool))
    vh, vw, _ = L5S.targets("vote2r", Vs, rs, rBs, Ps, None)
    eff["no_commitment_gives_the_vote_s_targets_exactly"] = bool(np.array_equal(xh, vh) and np.array_equal(xw, vw) and not com.any())
    st = A2S.new_det(1)
    st["s"][0, 5, 7] = 1.0
    st["sgn"][0, 5, 7] = -1.0
    xh, xw, (com, tt) = sim.vd_targets({"tau_c": 15000.0}, Vs, rs, rBs, Ps, st, np.zeros(1, bool), np.zeros(1, bool), np.zeros((1, n, n), bool))
    th_, tw_ = L5S.rel(tt)
    touch_h = np.zeros((1, n, n), bool)
    touch_h[0, 5, 7] = touch_h[0, 5, 6] = True
    touch_w = np.zeros((1, n, n), bool)
    touch_w[0, 5, 7] = touch_w[0, 4, 7] = True
    eff["a_committed_cell_s_four_bonds_take_rel_t_and_the_others_the_vote_s"] = bool(
        np.array_equal(xh[touch_h], th_[touch_h]) and np.array_equal(xh[~touch_h], vh[~touch_h])
        and np.array_equal(xw[touch_w], tw_[touch_w]) and np.array_equal(xw[~touch_w], vw[~touch_w])
        and tt[0, 5, 7] == -1.0 and com.sum() == 1)
    # triggers only in the footprint during the window: a strongly disagreeing field everywhere
    stq = A2S.new_det(1)
    fp_ = np.zeros((1, n, n), bool)
    fp_[0, 8:16, 8:16] = True
    A2S.fire(stq, 0, fp_[0], 1, 1)
    Pdis = {"am": np.ones((1, n, n), bool), "aval": -np.sign(rs)}
    sim.vd_targets({"tau_c": 15000.0}, Vs, rs, rBs, Pdis, stq, np.ones(1, bool), np.ones(1, bool), fp_)
    inside = stq["s"][0] >= A.S_MIN
    eff["triggers_only_inside_the_footprint_during_the_window"] = bool(inside.any() and not (inside & ~stq["fp"][0]).any())
    s_before = stq["s"].copy()
    sim.vd_targets({"tau_c": 15000.0}, Vs, rs, rBs, Pdis, stq, np.zeros(1, bool), np.zeros(1, bool), fp_)
    eff["no_trigger_after_the_window_the_slow_state_decays"] = bool(np.array_equal(stq["s"], s_before * np.exp(-1.0 / 15000.0)))
    # the detector on synthetic states (agreeing tissue, every other cell anchored)
    cue = D.DET_STAR["cue"]
    Vq, rq = np.ones((1, n, n)), np.ones((1, n, n)) * 1.2
    amq = np.zeros((1, n, n), bool)
    amq[0, ::2, ::2] = True
    amq[0, 1::2, 1::2] = True
    avq = np.ones((1, n, n))

    def fires(aval, cfg=D.DET_STAR):
        st_ = A2S.new_det(1)
        A2S.detect(st_, Vq, rq, {"am": amq, "aval": aval}, cfg, 1, None)
        return bool(st_["t_on"][0] == 1), st_["zone"][0]
    okb = True
    for bx in cue["boxes"]:
        isl = np.zeros((1, n, n), bool)
        isl[0, 6:6 + bx, 6:6 + bx] = True
        if int((isl & amq).sum()) < cue["n"]:
            continue
        f_, zn = fires(np.where(isl, -1.0, avq))
        okb &= f_ and bool((zn >= isl[0]).all())
    eff["an_island_at_each_box_of_det_star_fires_it_over_the_island"] = bool(okb)
    bx = cue["boxes"][0] + 1
    isl = np.zeros((1, n, n), bool)
    isl[0, 6:6 + bx, 6:6 + bx] = True
    avr = np.where(isl, -1.0, avq)
    chb = dict(cue, box=bx)
    win_ok = bool(A2S.channel_windows(Vq, rq, {"am": amq, "aval": avr}, chb, "cue")[0, 6, 6])
    ring_cell = (6 - cue["ring"], 6) if amq[0, 6 - cue["ring"], 6] else (6 - cue["ring"], 7)
    avr[0, ring_cell[0], ring_cell[1]] = -1.0
    eff["one_disagreeing_anchor_in_the_surround_stops_the_window"] = win_ok and not bool(
        A2S.channel_windows(Vq, rq, {"am": amq, "aval": avr}, chb, "cue")[0, 6, 6])
    few = np.zeros((1, n, n), bool)
    for i_, j_ in np.argwhere(isl[0] & amq[0])[: max(cue["n"] - 1, 0)]:
        few[0, i_, j_] = True
    eff["fewer_than_n_disagreeing_anchors_do_not_fire"] = not fires(np.where(few, -1.0, avq))[0]
    rr = 1.2 * np.where(rng.random((8, n, n)) < 0.97, 1.0, 0.0)
    avr8 = np.ones((8, n, n))
    for j in range(8):
        for side in (int(rng.integers(2, 12)) for _ in range(3)):
            a_, b0 = rng.integers(0, n, 2)
            avr8[j][np.ix_(np.arange(a_, a_ + side) % n, np.arange(b0, b0 + side) % n)] = -1.0
    Pr_ = {"am": rng.random((8, n, n)) < 0.25, "aval": avr8}
    multi = A2S.cue_windows_multi(rr, Pr_, cue)
    eff["det_star_windows_equal_the_single_box_channel_at_every_box"] = bool(
        all(np.array_equal(multi[b], A2S.channel_windows(rr, rr, Pr_, dict(cue, box=b), "cue")) for b in cue["boxes"]))
    on_ok = True
    for body, uu in D.tasks():
        for blk in blocks:
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for rn in RUNS:
                arms = ARMS_OF[rn]
                for arm in (x for x in arms if x in ("det", "ms", "vms", "vdial")):
                    on = e[f"{rn}/det_on"][arms.index(arm)]
                    want = sum(min(A.SIG["duration"], D.WINDOW + 1 - int(x)) for x in on if x > 0)
                    on_ok &= meta["signal_updates"][rn][arm] == want
    eff["each_fired_arm_is_on_for_min_1000_8001_minus_onset_and_never_unfired"] = bool(on_ok)
    eff["the_clock"] = (A.CLOCK["eta"] == 3e-4 and abs(A.CLOCK["rate"] - 3e-5) <= 1e-18 and A.CLOCK["tau_c"] == 15000
                        and round(A.T_STAR) == 1959)
    eff["cut_is_the_exact_quantile"] = abs(NormalDist().cdf(-cut_for(A.CLOCK["rate"])) - A.CLOCK["rate"]) <= 1e-12
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    q8 = {}
    pattern, theta = D.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, lo, "engineering")
    k = D.NCASE
    blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W", "rB", "HB", "WB")]
    for s, L in (("memory", 4), ("cue", 4), ("correlated", 8)):
        o1 = sim.run_vd("li4", s, 0.0, ("vms", "vdial", "vms", "vote"), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG,
                        window=600, size=L)
        o2 = sim.run_vd("li4", s, 0.0, ("vms",), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L)
        q8[f"{s}@L{L}: vms listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o1, 2)))
        q8[f"{s}@L{L}: vms alone equals vms with others"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o2, 0)))
    checks["Q8_pairing"] = {"pass": all(q8.values()), "items": q8}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, uu = key.split("/")[:2]
        walls.setdefault((b_, uu), []).append(t["cpu_s"])
    n_dev = len(D.IDENTITIES["development"])
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 35 and forecast_h <= 12 and manifest["worker_maxrss_mb_peak"] <= 2048
                                           and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_cpu_h": round(cpu / 3600, 2), "forecast_wall_h_12": round(float(forecast_h), 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar003.{mod}"] + args, cwd=LANE, capture_output=True, text=True, env=env)
             for mod, args in (("analyze", ["--root", str(root), "--out", str(out)]),
                               ("predict", ["--root", str(root), "--out", str(out / "predictions_scored.json")]),
                               ("tables", ["--res", str(out)]))]
    expected = [out / f for f in ("summary.json", "detectors.json", "utilities.json", "side_arms.json",
                                  "predictions_scored.json", "TABLES.md")]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from ar003 import predict as PR
    stmts = sorted({p["stmt"] for p in PR.PARTS if p["fn"] is not None})
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    git_files = [f for f in list((LANE / "ar003").rglob("*")) + list((LANE / "probes").rglob("*p47*"))
                 + [LANE / "tests" / "test_ar003.py", LANE / "PLAN_AR003.md", LANE / "REGISTRATION_AR003.md"] if f.is_file()]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in expected)
                                    and sorted(got) == stmts and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big}

    worst4, items4 = 0.0, {}
    det_same = True
    for (uu, body, s, z, arm, ci, size), (Vr, rr_, Hr_, Wr_, rBr, HBr, WBr, (t_on, zone, fpm)) in q4:
        raw, e = rawf(uu, body), shard(uu, body)
        rn = D.run_name(s, z, size=size)
        kk = ARMS_OF[rn].index(arm)
        vds = list(RUNS[rn][4])
        kb = (1 if "vote" in RUNS[rn][2] else 0) + vds.index(arm)
        kd = len(RUNS[rn][3]) + vds.index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][kk, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][kk, ci]).max()),
                float(np.abs(rBr - raw[f"{rn}/rB"][kb, ci]).max()))
        bonds_exact = bool(np.array_equal(Hr_, raw[f"{rn}/H"][kk, ci]) and np.array_equal(Wr_, raw[f"{rn}/W"][kk, ci])
                           and np.array_equal(HBr, raw[f"{rn}/HB"][kb, ci]) and np.array_equal(WBr, raw[f"{rn}/WB"][kb, ci]))
        same_det = int(t_on if t_on else -1) == int(e[f"{rn}/det_on"][kk, ci])
        if t_on:
            same_det &= bool(np.array_equal(zone, raw[f"{rn}/zone"][kd, ci]) and np.array_equal(fpm, raw[f"{rn}/fp"][kd, ci]))
        det_same &= same_det and bonds_exact
        items4[f"{uu}/{body}/{rn}/{arm}/case{ci}"] = {"max_abs": d, "onset": int(t_on), "detector_exact": bool(same_det),
                                                      "bonds_exact": bonds_exact}
        worst4 = max(worst4, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst4 <= 1e-8 and det_same, "max_abs_difference": worst4, "items": items4}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": blocks, "tag": tag, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
