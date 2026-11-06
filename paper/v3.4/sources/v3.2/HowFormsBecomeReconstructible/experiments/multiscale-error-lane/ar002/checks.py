"""Qualification of AR002 on the preflight (engineering) shards; criteria fixed in advance (the lead's rulings of
31 October included).

python -m ar002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks B1,B2]   (writes frozen/qualification_receipt.json;
with --blocks, the debug blocks, ROOT/debug_qualification_receipt.json)

Q1  complete and finite: every task's shard holds every run's endpoints at its declared shape (reads x arms x cases;
    r_in_old exactly in the change runs), its trace, its scalars and the detectors' scalars; every value finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine, bit for bit (V, r and bonds, endpoints and scalars): (a) run_det's oracle (fires at update 1 over the patch)
    equals ar001.sim.run's dial and run_det's rest equals ar001's rest, run in separate calls, over 2,000 updates in
    memory, change and cue, and in memory on the 8 x 8 patch (S4_t1 and F0_t0, both bodies); (b) the oracle at delay
    979 equals ar001's dial-m0.5 in memory over 2,000 updates; (c) the worker's merged AR001 arms equal
    ar001.worker.one's for the same arms (none@0, change@0 and memory@1, one task) and ar001.sim.run's at size 8
    (memory@0-L8)
Q4  independent replay: per-site loops for the event, the body, bond noise, the record's own bond sums, the arbiter's
    targets, the currents, the cable equation by sparse LU on be001.checks' own matrix (the footprint's conductances
    set per site from the detector's zone), the trigger and the slow state, the pull and the Hebbian learner; the
    detector by integral images on wrap-padded arrays (window counts at each of a channel's boxes, the surround, the
    body channel, the dwell); reproduce seven full det branches (8,000 updates; one of them det-ms on the 8 x 8 patch)
    within 1e-8, bonds exactly, and the detector's onset, zone and footprint exactly
Q5  aliases: (a) every det arm (det-ms included) equals rest at every read and trace point before its onset, and
    throughout where it never fires (per case); (b) u(new) + u(old) = 1 exactly for every branch of every change run;
    (c) the vote, which never reads the cue, is bit-identical across none@0, cue@0 and change@0 (every endpoint, read
    and trace); (d) the dial of each run is AR001's: on for exactly 1,000 updates in every case
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states, the events (at each run's patch
    side) and the footprints equal the saved ones; each det footprint is its saved zone dilated by 2, and the
    detector's scalars follow from them
Q7  efficacy: the events do exactly their rule (memory and correlated invert the patch's record with consistent bonds;
    body and correlated invert its body; shared kills its record, inside bonds and anchors; cue flips exactly a quarter
    of the anchors; change flips exactly the patch's anchors and target; the misread changes anchors only); the
    detector on synthetic states: an island of n disagreeing anchors in agreeing tissue fires the cue channel over its
    window, one disagreeing anchor in the surround stops it, fewer than n does not fire, the body channel fires on n
    mismatches (and a fraction q) in a window and not one fewer, a window must hold its dwell; an 8 x 8 island fires
    det-ms and not det, and a 4 x 4 island fires both; det-ms's windows equal the single-box channel's at every box
    (and det's at box 4) on random states; each fired det's dial is on for exactly min(1,000, 8,001 - onset)
    updates, and never where it did not fire; the clock is AR001's
Q8  pairing: an arm listed twice gives bit-identical branches, and a det arm (det-v, det-ms) run with fewer arms equals
    it run with others
Q9  resources: forecast development within 30 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB, disk
Q10 reader dry run: analyze, predict and tables complete on the shards, every statement is scored, and every git file is
    256 KB or less
Reported beside them (the lead's ruling 6, gates for the reported det-ms, not Q criteria): det-ms's sheet cost under
scattered cue damage at most 0.01, and its rate of firing on the patch on the 8 x 8 patch at least det's (memory and
correlated damage each).
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
from ar002 import design as D  # noqa: E402
from ar002 import sim  # noqa: E402
from ar002 import worker as W  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from be001.checks import cable_matrix  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl001 import sim as S  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "ar002" / "frozen"
WORKERS = 12
RUNS = {D.run_name(*x): x for x in D.RUNS}
ARMS_OF = {k: list(v[2]) + list(v[3]) for k, v in RUNS.items()}
Q4_PICKS = (("S4_t1", "li4", "memory", 0.0, "det", 0, D.SIZE),
            ("F0_t0", "dw", "correlated", 0.0, "det", 1, D.SIZE),
            ("S4_t0", "dw", "cue", 0.0, "det", 2, D.SIZE),
            ("F0_t1", "li4", "memory", 0.0, "det-v", 3, D.SIZE),
            ("S4_t1", "dw", "change", 1.0, "det", 4, D.SIZE),
            ("F0_t0", "li4", "body", 0.0, "det", 5, D.SIZE),
            ("S4_t1", "dw", "memory", 0.0, "det-ms", 6, 8))            # the lead's ruling 2: one det-ms branch at L 8


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def wrap_counts(x, b, shift=0):
    """Independent window counts by an integral image on a wrap-padded array: out[i, j] = the sum of x over rows
    i - shift .. i - shift + b - 1 and columns j - shift .. j - shift + b - 1 (periodic)."""
    n = x.shape[-1]
    pad = np.zeros((2 * n + 1, 2 * n + 1))
    pad[1:, 1:] = np.tile(x, (2, 2)).astype(float).cumsum(0).cumsum(1)
    out = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            a0, b0 = (i - shift) % n, (j - shift) % n
            a1, b1 = a0 + b, b0 + b
            out[i, j] = pad[a1, b1] - pad[a0, b1] - pad[a1, b0] + pad[a0, b0]
    return np.rint(out).astype(int)


def replay_detector(ch, kind, sv, sr, ca):
    """One channel's windows (by top-left corner) on one case, by integral images (independent of sim.wsum)."""
    n = len(sr)
    srl, svl = np.array(sr), np.array(sv)
    cal = np.array(ca)
    b = ch["box"]
    if kind == "cue":
        live = (cal != 0) & (srl != 0)
        dis = live & (cal != srl)
        nd, nl = wrap_counts(dis, b), wrap_counts(live, b)
        f = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
        if ch.get("ring", 0):
            g = ch["ring"]
            f &= (wrap_counts(dis, b + 2 * g, g) - nd) <= ch["ring_max"]
        return f
    both = (svl != 0) & (srl != 0)
    mis = both & (svl != srl)
    nm, nb = wrap_counts(mis, b), wrap_counts(both, b)
    return (nm >= ch["n"]) & (nm >= ch["q"] * nb)


def s_replay_det(unit, body, situation, sigma, arm, ci, block, window=D.WINDOW, tag=D.TAG, clock=None, size=D.SIZE):
    """One det arm's branch end to end with independent per-site code; returns final V, r, H, W and (onset, zone, fp)."""
    clock = A.CLOCK if clock is None else clock
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    cfg = D.DETECTORS[arm]
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

    rv0 = R0c.copy()
    if situation in ("memory", "correlated"):
        rv0 = np.where(np.array(patch), -R0c, R0c)
    if situation in ("body", "correlated"):
        V = np.where(np.array(patch), -V, V)
    sg = [[1.0 if rv0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[A.STRENGTH0 * x for x in row] for row in H]
    Ws = [[A.STRENGTH0 * x for x in row] for row in Wd]
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
    cut = NormalDist().inv_cdf(1.0 - clock["rate"])
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    streams = [Stream(tag, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    rest_g, sig2 = A.SIG["lam_rest"] ** 2, A.SIG["lam_sig"] ** 2
    lu_off = splu(cable_matrix(n, [[rest_g] * n for _ in range(n)], [[rest_g] * n for _ in range(n)]))
    lu_on, t_on, zone, fpm = None, 0, None, None
    counts = {}
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / clock["tau_c"])
    for t in range(window):
        if t % A.CHUNK == 0:
            bufs = [st.take(A.CHUNK)[:, ci] for st in streams]
        z, xi, zb = (bufs[q][t % A.CHUNK] for q in range(3))
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
        for i in range(n):
            for j in range(n):
                if float(zb[i, j]) > cut:
                    H[i][j], Hs[i][j] = -H[i][j], -Hs[i][j]
                elif float(zb[i, j]) < -cut:
                    Wd[i][j], Ws[i][j] = -Wd[i][j], -Ws[i][j]
        r1 = np.empty_like(r)
        for i in range(n):
            for j in range(n):
                rr = float(r[i, j])
                bs = (Wd[i - 1][j] * float(r[i - 1, j]) + Wd[i][j] * float(r[(i + 1) % n, j])
                      + H[i][j - 1] * float(r[i, j - 1]) + H[i][j] * float(r[i, (j + 1) % n])) / 4.0
                r1[i, j] = min(max(rr + A.EPS * (rr * (1 - (rr / 1.2) ** 2) + A.KR * (bs - rr)) + A.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        r = r1
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        if t_on == 0:
            held = np.zeros((n, n), bool)
            for c in ("cue", "body"):
                ch = cfg.get(c)
                if not ch:
                    continue
                for bx in ch.get("boxes", (ch.get("box"),)):
                    f = replay_detector(dict(ch, box=bx), c, sv, sr, ca)
                    counts[(c, bx)] = np.where(f, counts.get((c, bx), 0) + 1, 0)
                    ready = counts[(c, bx)] >= ch["dwell"]
                    if ready.any():
                        for i in range(n):
                            for j in range(n):
                                if ready[i, j]:
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
        cur = np.array([[A.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
        v = (lu_on if on else lu_off).solve(cur.ravel()).reshape(n, n)
        for i in range(n):
            for j in range(n):
                trig = float(v[i, j]) < -A.SIG["theta"] and sr[i][j] != 0
                was = s_[i][j] >= A.S_MIN
                if trig and not was:
                    sgn[i][j] = -sr[i][j]
                s_[i][j] = 1.0 if trig else s_[i][j] * decay
                if s_[i][j] >= A.S_MIN:
                    tr[i][j] = sgn[i][j]
                    r[i, j] = float(r[i, j]) + A.EPS * A.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
        th_ = [[tr[i][j] * tr[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        tw_ = [[tr[i][j] * tr[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(n):
                for Ed, Es, x in ((H, Hs, th_[i][j]), (Wd, Ws, tw_[i][j])):
                    if x != 0:
                        Es[i][j] = Es[i][j] + eta * (x - Es[i][j])
                        if Es[i][j] != 0:
                            Ed[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd), (t_on, zone, fpm)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay_det(*pick[:6], block, size=pick[6])


def q3_job(args):
    """(a) the oracle against ar001's dial and rest against rest, at the 4 x 4 patch and (memory) at 8 x 8; (b) the
    delayed oracle against dial-m0.5."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    dets = {"oracle": {"oracle": True}, "oracle-979": {"oracle": True, "delay": A.ARM["dial-m0.5"]["delay"]}}
    ok = {}
    sl = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W")]

    def equal(a, b, ia, ib):
        return (all(np.array_equal(x, y) for x, y in zip(sl(a, ia), sl(b, ib)))
                and all(np.array_equal(a[e][:, ia * k:(ia + 1) * k], b[e][:, ib * k:(ib + 1) * k]) for e in sim.ENDS if e in a)
                and all(np.array_equal(a[e][ia * k:(ia + 1) * k], b[e][ib * k:(ib + 1) * k])
                        for e in ("opened", "opened_out", "onset", "hit"))
                and np.array_equal(a["trace"][:, ia * k:(ia + 1) * k], b["trace"][:, ib * k:(ib + 1) * k]))
    a8 = A1S.run(body, "memory", 0.0, ("rest", "dial"), cases, V0, ema0, R0, th, T, theta, {1000, 2000}, tag=D.TAG,
                 window=2000, size=8)
    b8 = sim.run_det(body, "memory", 0.0, ("oracle", "rest"), cases, V0, ema0, R0, th, T, theta, {1000, 2000}, tag=D.TAG,
                     window=2000, size=8, detectors=dets)
    ok[f"{unit}/{body}/memory at L 8: oracle = ar001 dial at size 8"] = equal(a8, b8, 1, 0)
    ok[f"{unit}/{body}/memory at L 8: run_det rest = ar001 rest at size 8"] = equal(a8, b8, 0, 1)
    for situation in ("memory", "change", "cue"):
        a = A1S.run(body, situation, 0.0, ("rest", "dial", "dial-m0.5"), cases, V0, ema0, R0, th, T, theta, {1000, 2000},
                    tag=D.TAG, window=2000)
        arms = ("oracle", "rest") + (("oracle-979",) if situation == "memory" else ())
        b = sim.run_det(body, situation, 0.0, arms, cases, V0, ema0, R0, th, T, theta, {1000, 2000}, tag=D.TAG, window=2000,
                        detectors=dets)
        same = lambda ia, ib: (all(np.array_equal(x, y) for x, y in zip(sl(a, ia), sl(b, ib)))
                               and all(np.array_equal(a[e][:, ia * k:(ia + 1) * k], b[e][:, ib * k:(ib + 1) * k])
                                       for e in sim.ENDS if e in a)
                               and all(np.array_equal(a[e][ia * k:(ia + 1) * k], b[e][ib * k:(ib + 1) * k])
                                       for e in ("opened", "opened_out", "onset", "hit"))
                               and np.array_equal(a["trace"][:, ia * k:(ia + 1) * k], b["trace"][:, ib * k:(ib + 1) * k]))
        ok[f"{unit}/{body}/{situation}: oracle = ar001 dial"] = same(1, 0)
        ok[f"{unit}/{body}/{situation}: run_det rest = ar001 rest"] = same(0, 1)
        if situation == "memory":
            ok[f"{unit}/{body}/{situation}: oracle at 979 = ar001 dial-m0.5"] = same(2, 2)
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
    lo = blocks[0]
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
        for blk in blocks:
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(run[2]) + len(run[3])
                eps = [x for x in W.ENDS if x != "r_in_old"]
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (len(D.READS), na, D.NCASE)]
                if run[0] == "change":
                    bad += [f"{rn}/r_in_old"] if e.get(f"{rn}/r_in_old", np.zeros(0)).shape != (len(D.READS), na, D.NCASE) else []
                else:
                    bad += [f"{rn}/r_in_old"] if f"{rn}/r_in_old" in e else []
                bad += [f"{rn}/{x}" for x in W.SCALARS + W.DET_SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in ("n_anc", "n_mis") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (D.NCASE,)]
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, lo, "engineering", str(serial), tag=json.loads(str(np.load(root / "shards" / body / u / f"{lo}.npz")["__meta__"]))["tag"])
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for d_ in q3:
        eq.update(d_)
    pattern, theta = D.parse_unit("S4_t1")
    prep = sim.prepare(pattern, lo, "engineering")
    for run in (("none", 0.0), ("change", 0.0), ("memory", D.MISREAD_SIGMA)):
        r2 = next(x for x in D.RUNS if x[:2] == run and x[4] == D.SIZE)
        e2, raw2, _ = W.one("dw", "S4_t1", lo, "engineering", r2, D.TAG, prep, window=1000, reads=(500, 1000))
        e1, raw1, _ = AW.one("dw", "S4_t1", lo, "engineering", (run[0], run[1], r2[2]), D.TAG, prep, window=1000, reads=(500, 1000))
        na1 = len(r2[2])
        key = D.run_name(*run)
        okk = all(np.array_equal(e1[k_], e2[k_][..., :na1, :] if e1[k_].ndim == 3 else
                                 (e2[k_][:na1] if e1[k_].ndim == 2 and k_.split("/")[-1] != "trace" else e2[k_][:, :na1]))
                  for k_ in e1 if not k_.endswith(("n_anc", "n_mis")))
        okk &= all(np.array_equal(raw1[f"{key}/{x}"], raw2[f"{key}/{x}"][:na1]) for x in ("V", "r", "H", "W"))
        eq[f"worker {key}: merged AR001 arms = ar001.worker.one"] = bool(okk)
    r8 = next(x for x in D.RUNS if x[:2] == ("memory", 0.0) and x[4] == 8)
    key8, na1 = D.run_name(*r8), len(r8[2])
    e2, raw2, _ = W.one("dw", "S4_t1", lo, "engineering", r8, D.TAG, prep, window=1000, reads=(500, 1000))
    o8 = A1S.run("dw", "memory", 0.0, r8[2], *prep, 1.0, {500, 1000}, tag=D.TAG, window=1000, size=8)
    k8 = D.NCASE
    okk = all(np.array_equal(e2[f"{key8}/{x}"][:, :na1], o8[x].reshape(2, na1, k8)) for x in sim.ENDS if x in o8)
    okk &= all(np.array_equal(raw2[f"{key8}/{x}"][:na1], o8[x].reshape(na1, k8, D.SIDE, D.SIDE).astype(raw2[f"{key8}/{x}"].dtype))
               for x in ("V", "r", "H", "W"))
    eq[f"worker {key8}: merged AR001 arms = ar001.sim.run at size 8"] = bool(okk)
    checks["Q3_engine"] = {"pass": bool(eq) and all(eq.values()), "n_items": len(eq),
                           "failed": [k for k, v in eq.items() if not v][:10]}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, uu in D.tasks():
        for blk in blocks:
            e, raw = shard(uu, body, blk), rawf(uu, body, blk)
            for rn, run in RUNS.items():
                arms = ARMS_OF[rn]
                jr = arms.index("rest")
                for i, arm in enumerate(arms):
                    if arm not in D.DET_ARMS:
                        continue
                    on = e[f"{rn}/det_on"][i]
                    okc = True
                    for c in range(D.NCASE):
                        first = on[c] if on[c] > 0 else D.WINDOW + 1
                        before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                        ntb = int((first - 1) // D.TRACE)
                        okc &= all(np.array_equal(e[f"{rn}/{q}"][before, i, c], e[f"{rn}/{q}"][before, jr, c]) for q in EP)
                        okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, i, c], e[f"{rn}/trace"][:ntb, jr, c]))
                        if on[c] < 0:
                            okc &= all(np.array_equal(raw[f"{rn}/{x}"][i, c], raw[f"{rn}/{x}"][jr, c]) for x in ("V", "r", "H", "W"))
                    items[f"{uu}/{body}/{blk}/{rn}/{arm} = rest before its onset"] = bool(okc)
                if run[0] == "change":
                    items[f"{uu}/{body}/{blk}/{rn}: u(new) + u(old) = 1"] = bool((e[f"{rn}/r_in"] + e[f"{rn}/r_in_old"] == 1.0).all())
            j0 = ARMS_OF["none@0"].index("vote")
            for other in ("cue@0", "change@0"):
                j1 = ARMS_OF[other].index("vote")
                same_raw = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"{other}/{x}"][j1]) for x in ("V", "r", "H", "W"))
                same_raw &= all(np.array_equal(raw[f"none@0/{x}"], raw[f"{other}/{x}"]) for x in ("rB", "HB", "WB"))
                if other == "cue@0":
                    same_ep = all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in EP)
                else:
                    same_ep = np.array_equal(e["none@0/r_in"][:, j0], e[f"{other}/r_in_old"][:, j1])
                items[f"{uu}/{body}/{blk}/vote: none@0 = {other}"] = bool(same_raw and same_ep)
    sig_ok = True
    for body, uu in D.tasks():
        for blk in blocks:
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for rn in RUNS:
                arms = ARMS_OF[rn]
                if "dial" in arms:
                    sig_ok &= meta["signal_updates"][rn]["dial"] == A.SIG["duration"] * D.NCASE
                    sig_ok &= bool(((e[f"{rn}/onset"][arms.index("dial")] >= 0)).all())
    items["the dial of every run is on for exactly 1,000 updates in every case"] = bool(sig_ok)
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "n_items": len(items),
                                  "failed": [k for k, v in items.items() if not v][:10]}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(uu, body), shard(uu, body)
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for run in D.RUNS:
            rn = D.run_name(*run)
            na = len(ARMS_OF[rn])
            ev = sim.event(run[0], run[4], run[1], cases, V0, ema0, R0, T, D.TAG)
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
            nd = len(run[3])
            zone, fpd = raw[f"{rn}/zone"], raw[f"{rn}/fp"]
            for i, arm in enumerate(run[3]):
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
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    evs = {s: sim.event(s, D.SIZE, 0.0, cases, V0, ema0, R0, T, D.TAG) for s in D.SITUATIONS}
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
    ev1 = sim.event("none", D.SIZE, D.MISREAD_SIGMA, cases, V0, ema0, R0, T, D.TAG)
    eff["the_misread_changes_anchors_only"] = bool(np.array_equal(ev1["r"], R0) and np.array_equal(ev1["V"], V0)
                                                   and np.array_equal(ev1["am"], am0) and ev1["mis"].any())
    # the detector on synthetic states (one case): agreeing tissue, every cell anchored with the record's sign
    n = D.SIDE
    cue_ch = D.DETECTORS["det"]["cue"] or {"box": 4, "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
    body_ch = D.DETECTORS["det"]["body"] or D.DETECTORS["det-v"]["body"]
    b_ = cue_ch["box"]
    Vq, rq = np.ones((1, n, n)), np.ones((1, n, n))
    amq = np.zeros((1, n, n), bool)
    amq[0, ::2, ::2] = True                                    # a quarter of the cells anchored
    avq = np.ones((1, n, n))
    isl = np.zeros((1, n, n), bool)
    isl[0, 10:10 + b_, 10:10 + b_] = True
    k_isl = int((isl & amq).sum())
    Pq = {"am": amq, "aval": np.where(isl, -1.0, avq)}
    f = sim.channel_windows(Vq, rq, Pq, cue_ch, "cue")
    eff["an_island_of_disagreeing_anchors_fires_the_cue_channel_over_its_window"] = bool(
        k_isl >= cue_ch["n"] and f[0, 10, 10] and np.array_equal(sim.cover(f, b_)[0], isl[0]) if f[0].sum() == 1 else
        k_isl >= cue_ch["n"] and f[0, 10, 10] and (sim.cover(f, b_)[0] >= isl[0]).all())
    if cue_ch.get("ring", 0):
        Pr = {"am": amq, "aval": np.where(isl, -1.0, avq)}
        Pr["aval"][0, 10 - cue_ch["ring"], 10] = -1.0          # one disagreeing anchor in the surround (an anchored cell)
        eff["one_disagreeing_anchor_in_the_surround_stops_it"] = bool(not sim.channel_windows(Vq, rq, Pr, cue_ch, "cue")[0, 10, 10])
    few = np.zeros((1, n, n), bool)
    idx = np.argwhere(isl[0] & amq[0])[: max(cue_ch["n"] - 1, 0)]
    for i_, j_ in idx:
        few[0, i_, j_] = True
    eff["fewer_than_n_disagreeing_anchors_do_not_fire"] = bool(
        not sim.channel_windows(Vq, rq, {"am": amq, "aval": np.where(few, -1.0, avq)}, cue_ch, "cue").any())
    bb = body_ch["box"]
    Vb = np.ones((1, n, n))
    need = max(body_ch["n"], math.ceil(body_ch["q"] * bb * bb))         # the channel's threshold in one window
    cells_b = [(20 + i_ // bb, 20 + i_ % bb) for i_ in range(need)]
    for i_, j_ in cells_b:
        Vb[0, i_, j_] = -1.0
    Pnone = {"am": np.zeros((1, n, n), bool), "aval": np.ones((1, n, n))}
    fb = sim.channel_windows(Vb, rq, Pnone, body_ch, "body")
    Vb2 = Vb.copy()
    Vb2[0, cells_b[-1][0], cells_b[-1][1]] = 1.0
    fb2 = sim.channel_windows(Vb2, rq, Pnone, body_ch, "body")
    eff["the_body_channel_fires_at_its_threshold_in_a_window_and_not_one_below"] = bool(fb[0, 20, 20] and not fb2.any())
    stq = sim.new_det(1)
    cfg_dw = {"cue": None, "body": dict(body_ch, dwell=5)}
    fired_at = None
    for t_ in range(1, 12):
        sim.detect(stq, Vb, rq, Pnone, cfg_dw, t_, None)
        if stq["t_on"][0] and fired_at is None:
            fired_at = int(stq["t_on"][0])
    eff["a_window_must_hold_its_dwell"] = fired_at == 5
    ms = D.DETECTORS["det-ms"]

    def fires(cfg, aval):
        st_ = sim.new_det(1)
        sim.detect(st_, Vq, rq, {"am": amq, "aval": aval}, cfg, 1, None)
        return bool(st_["t_on"][0] == 1)
    isl8 = np.zeros((1, n, n), bool)
    isl8[0, 10:18, 10:18] = True
    av8, av4 = np.where(isl8, -1.0, avq), np.where(isl, -1.0, avq)
    eff["an_8x8_island_fires_det_ms_and_not_det_and_a_4x4_island_fires_both"] = bool(
        fires(ms, av8) and not fires(D.DETECTORS["det"], av8) and fires(ms, av4) and fires(D.DETECTORS["det"], av4))
    rng = np.random.default_rng(20261031)                      # agreeing records with islands of flipped anchors
    rr = 1.2 * np.where(rng.random((8, n, n)) < 0.97, 1.0, 0.0)
    avr = np.ones((8, n, n))
    for j in range(8):
        for side in (4, int(rng.integers(2, 12)), int(rng.integers(2, 12))):
            a_, b0 = rng.integers(0, n, 2)
            avr[j][np.ix_(np.arange(a_, a_ + side) % n, np.arange(b0, b0 + side) % n)] = -1.0
    Pr_ = {"am": rng.random((8, n, n)) < 0.25, "aval": avr}
    msc = ms["cue"]
    multi = sim.cue_windows_multi(rr, Pr_, msc)
    eff["det_ms_windows_equal_the_single_box_channel_at_every_box_and_det_at_4"] = bool(
        all(np.array_equal(multi[b], sim.channel_windows(rr, rr, Pr_, dict(msc, box=b), "cue")) for b in msc["boxes"])
        and np.array_equal(multi[4], sim.channel_windows(rr, rr, Pr_, D.DETECTORS["det"]["cue"], "cue")))
    on_ok = True
    for body, uu in D.tasks():
        for blk in blocks:
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for rn in RUNS:
                arms = ARMS_OF[rn]
                for arm in (x for x in arms if x in D.DET_ARMS):
                    on = e[f"{rn}/det_on"][arms.index(arm)]
                    want = sum(min(A.SIG["duration"], D.WINDOW + 1 - int(x)) for x in on if x > 0)
                    on_ok &= meta["signal_updates"][rn][arm] == want
    eff["each_fired_det_is_on_for_min_1000_8001_minus_onset_and_never_unfired"] = bool(on_ok)
    eff["the_clock"] = (A.CLOCK["eta"] == 3e-4 and abs(A.CLOCK["rate"] - 3e-5) <= 1e-18 and A.CLOCK["tau_c"] == 15000
                        and round(A.T_STAR) == 1959)
    eff["cut_is_the_exact_quantile"] = abs(NormalDist().cdf(-cut_for(A.CLOCK["rate"])) - A.CLOCK["rate"]) <= 1e-12
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    q8 = {}
    pattern, theta = D.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    k = D.NCASE
    blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W")]
    for s in ("memory", "cue"):
        o1 = sim.run_det("li4", s, 0.0, ("det", "det-v", "det", "det-ms"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        o2 = sim.run_det("li4", s, 0.0, ("det-v", "det-ms"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        q8[f"{s}: det listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o1, 2)))
        q8[f"{s}: det-v alone equals det-v with others"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 1), blk_(o2, 0)))
        q8[f"{s}: det-ms equals det-ms with other arms"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 3), blk_(o2, 1)))
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
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 30 and forecast_h <= 12 and manifest["worker_maxrss_mb_peak"] <= 2048
                                           and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_cpu_h": round(cpu / 3600, 2), "forecast_wall_h_12": round(float(forecast_h), 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar002.{mod}", "--root", str(root), "--out", str(out / name)],
                            cwd=LANE, capture_output=True, text=True, env=env)
             for mod, name in (("analyze", ""), ("predict", "predictions_scored.json"), ("tables", "TABLES.md"))]
    expected = [out / f for f in ("summary.json", "detectors.json", "utilities.json", "side_arms.json", "sizes.json",
                                  "predictions_scored.json", "TABLES.md")]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from ar002 import predict as PR
    stmts = sorted({p["stmt"] for p in PR.PARTS})
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    git_files = [f for d in ("ar002", "probes") for f in (LANE / d).rglob("*") if f.is_file() and ("ar002" in f.name or d == "ar002")]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in expected)
                                    and sorted(got) == stmts and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big}

    worst4, items4 = 0.0, {}
    det_same = True
    for (uu, body, s, z, arm, ci, size), (Vr, rr_, Hr_, Wr_, (t_on, zone, fpm)) in q4:
        raw, e = rawf(uu, body), shard(uu, body)
        rn = D.run_name(s, z, size=size)
        kk = ARMS_OF[rn].index(arm)
        kd = list(RUNS[rn][3]).index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][kk, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][kk, ci]).max()),
                float(np.abs(Hr_ - raw[f"{rn}/H"][kk, ci]).max()), float(np.abs(Wr_ - raw[f"{rn}/W"][kk, ci]).max()))
        same_det = int(t_on if t_on else -1) == int(e[f"{rn}/det_on"][kk, ci])
        if t_on:
            same_det &= bool(np.array_equal(zone, raw[f"{rn}/zone"][kd, ci]) and np.array_equal(fpm, raw[f"{rn}/fp"][kd, ci]))
        det_same &= same_det
        items4[f"{uu}/{body}/{rn}/{arm}/case{ci}"] = {"max_abs": d, "onset": int(t_on), "detector_exact": bool(same_det)}
        worst4 = max(worst4, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst4 <= 1e-8 and det_same, "max_abs_difference": worst4, "items": items4}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    from ar002 import analyze as AZ
    Zs = AZ.load(root, blocks)
    g1 = float(AZ.sham(Zs, "cue@0", "det-ms").mean())
    g2 = {sit: {"det-ms": float(AZ.rate(Zs, "det-ms", sit, which="located", size=8).mean()),
                "det": float(AZ.rate(Zs, "det", sit, which="located", size=8).mean())} for sit in D.SIZE_SITUATIONS}
    gates = {"det_ms_sheet_cost_under_scattered_cue_damage_le_0.01": {"value": g1, "pass": g1 <= 0.01},
             "det_ms_rate_on_the_patch_at_L8_at_least_det_s": {"values": g2, "pass": all(v["det-ms"] >= v["det"]
                                                                                           for v in g2.values())}}
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": blocks, "tag": D.TAG, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks, "gates": gates}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed,
                      "gates": {k: v["pass"] for k, v in gates.items()}}, indent=1))


if __name__ == "__main__":
    main()
