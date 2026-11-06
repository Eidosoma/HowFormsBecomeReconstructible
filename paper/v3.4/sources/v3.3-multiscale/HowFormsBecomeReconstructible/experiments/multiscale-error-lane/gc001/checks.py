"""Qualification of GC001 on the preflight (engineering) shards; criteria fixed in advance.

python -m gc001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: at sigma 0, none8, change4 and memory4 with every arm equal be001.sim.run bit for bit (body, record and
    bonds; both bodies; two units)
Q4  independent replay: per-site loops for the event (its own patch, anchors, displaced reads of the cue field and the
    matched flips), the body's local terms (conjugate gradients for the inhibitor, no FFT), bond noise (its own cut,
    statistics.NormalDist), the record's own bond sums, the cue arbiter, the currents, the cable equation solved by sparse
    LU (its own matrix), the trigger, the slow state, the pull and the Hebbian learners reproduce three full branches
    (bio-1 under none8@1, bio-1.5 under scatter8@2, the cue arm under memory4@1) within 1e-8 (bonds exactly)
Q5  aliases: a bioelectric arm whose threshold cannot be reached equals the cue arm bit for bit under a noisy cue
    (sigma 1); a scattered control with no flips equals the exact cue bit for bit; for every arm the FFT steady state
    equals the conjugate-gradient solve with uniform gates within 1e-9 on the saved final currents
Q6  reanalysis: the endpoints at t = 4000 recomputed from the saved final states and the events equal the saved ones
Q7  efficacy: anchors on exactly a quarter of the cells; the matched control flips exactly as many anchors as the noisy
    read misreads, in every case and sigma, and only anchors; the band and interior partition the sheet; the realised
    misread share lies within 0.03 of the derived expectation over the same anchors and templates (every stage block)
    for every unit and sigma; the displacement offsets
    have SD within 10% of sigma for sigma >= 1; a point current's total response is 1/g_l for every coupling length
Q8  the static map is reproducible: recomputed, it equals gc001/frozen/static_map.json
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import copy  # noqa: E402
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

from be001 import sim as B1S  # noqa: E402
from be001.checks import cable_matrix  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl001.checks import screened  # noqa: E402
from gc001 import design as D  # noqa: E402
from gc001 import sim  # noqa: E402
from gc001 import static  # noqa: E402
from gc001 import worker as W  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "gc001" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t0", "li4", "none", 8, 1.0, "bio-1", 0), ("F0_t1", "dw", "scatter", 8, 2.0, "bio-1.5", 1),
            ("LB_t0", "li4", "memory", 4, 1.0, "cue", 2))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, situation, size, sigma, arm, ci, block):
    """One branch end to end with independent per-site code; returns final V, r, H, W."""
    B = B1S.D
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    bio = arm != "cue"
    lam2 = D.BIO[arm]["lam"] ** 2 if bio else 0.0
    thr = D.BIO[arm]["theta"] if bio else 0.0
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    perm = address(D.TAG, *key, "anchors", B.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // B.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    field = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]
    rv0 = R0c.copy()
    if situation == "memory":
        rv0 = np.where(np.array(patch), -R0c, R0c)
    elif situation == "change":
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    field[i][j] *= -1.0
    gq = address(D.TAG, *key, "gc-eps").standard_normal((2, n, n))
    if situation == "scatter":
        miss = 0
        for i in range(n):
            for j in range(n):
                if anch[i][j]:
                    di, dj = int(round(sigma * float(gq[0, i, j]))), int(round(sigma * float(gq[1, i, j])))
                    miss += field[(i + di) % n][(j + dj) % n] != field[i][j]
        flat = [i * n + j for i in range(n) for j in range(n) if anch[i][j]]
        pick = address(D.TAG, *key, "gc-scatter").permutation(len(flat))[:miss]
        aval = [row[:] for row in field]
        for p_ in pick:
            q = flat[int(p_)]
            aval[q // n][q % n] *= -1.0
    else:
        aval = [[field[(i + int(round(sigma * float(gq[0, i, j])))) % n][(j + int(round(sigma * float(gq[1, i, j])))) % n]
                 for j in range(n)] for i in range(n)]
    sg = [[1.0 if rv0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[B.STRENGTH0 * x for x in row] for row in H]
    Ws = [[B.STRENGTH0 * x for x in row] for row in Wd]
    r = rv0.copy()
    cut = NormalDist().inv_cdf(1.0 - D.RATE)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise", "voltage-noise")]
    uniform = [[lam2] * n for _ in range(n)]
    lu = splu(cable_matrix(n, uniform, uniform)) if bio else None
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)

    def vs(x):
        return 1.0 if x >= B.VMIN else (-1.0 if x <= -B.VMIN else 0.0)

    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
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
                r1[i, j] = min(max(rr + B.EPS * (rr * (1 - (rr / 1.2) ** 2) + B.KR * (bs - rr)) + B.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        r = r1
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        if bio:
            cur = np.array([[D.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
            v = lu.solve(cur.ravel()).reshape(n, n)
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base = sv[i][j]
                else:
                    base = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                if not bio:
                    tr[i][j] = base
                    continue
                trig = float(v[i, j]) < -thr and sr[i][j] != 0
                was = s_[i][j] >= B.S_MIN
                if trig and not was:
                    sgn[i][j] = -sr[i][j]
                s_[i][j] = 1.0 if trig else s_[i][j] * decay
                if s_[i][j] >= B.S_MIN:
                    tr[i][j] = sgn[i][j]
                    r[i, j] = float(r[i, j]) + B.EPS * B.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
                else:
                    tr[i][j] = base
        for i in range(n):
            for j in range(n):
                for E, Es, x in ((H, Hs, tr[i][j] * tr[i][(j + 1) % n]), (Wd, Ws, tr[i][j] * tr[(i + 1) % n][j])):
                    if x != 0:
                        Es[i][j] = Es[i][j] + B.ETA * (x - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """sigma 0 against be001.sim.run, bit for bit, in none8, change4 and memory4 with every arm."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    ok = True
    for s, z in (("none", 8), ("change", 4), ("memory", 4)):
        o = sim.run(body, s, z, 0.0, cases, V0, ema0, R0, th, T, theta, {D.WINDOW})
        o1 = B1S.run(body, s, z, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG, arms=D.ARMS)
        ok &= all(np.array_equal(o[x], o1[x]) for x in ("V", "r", "H", "W"))
    return (unit, body), bool(ok)


def q5_job(args):
    """A bioelectric arm with an unreachable threshold equals the cue arm bit for bit under a noisy cue."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    B1S.D.BIO = copy.deepcopy(B1S.D.BIO)
    B1S.D.BIO["bio-1"]["theta"] = 1e300
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    o = sim.run(body, "none", 8, 1.0, cases, V0, ema0, R0, th, T, theta, {1000}, window=1000, arms=("cue", "bio-1"))
    return bool(all(np.array_equal(o[x][:k], o[x][k:]) for x in ("V", "r", "H", "W")) and float(o["opened"][k:].sum()) == 0.0)


def q8_job(args):
    (cpu,) = args
    os.sched_setaffinity(0, [cpu])
    return static.compute()


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
    rawf = lambda u, b=lo: npz(root / "raw" / "G" / u / f"{b}.npz")
    shard = lambda u, b=lo: npz(root / "shards" / "G" / u / f"{b}.npz")
    checks = {}
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "F0_t0") for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks) + 2, len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, (u_, b_) in enumerate(q3_picks)])
    q5 = pool.submit(q5_job, ("S4_t0", "li4", lo, cpus[(len(Q4_PICKS) + len(q3_picks) + 1) % len(cpus)]))
    q8 = pool.submit(q8_job, (cpus[(len(Q4_PICKS) + len(q3_picks) + 2) % len(cpus)],))
    na, nr, ntr = len(D.ARMS), len(D.READS), len(D.TRACE_READS)

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
                for (s, z, sg), rn in zip(D.RUNS, D.RUNNAMES):
                    key = f"{body}/{rn}"
                    eps = sim.ENDS if s == "change" else tuple(x for x in sim.ENDS if not x.endswith("_old"))
                    bad += [f"{key}/{x}" for x in eps if e.get(f"{key}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                    bad += [f"{key}/opened"] if e.get(f"{key}/opened", np.zeros(0)).shape != (na, D.NCASE) else []
                    bad += [f"{key}/{x}" for x in ("trace", "trace_all") if e.get(f"{key}/{x}", np.zeros(0)).shape != (ntr, na, D.NCASE)]
                    bad += [f"{key}/{x}" for x in W.PER_CASE if e.get(f"{key}/{x}", np.zeros(0)).shape != (D.NCASE,)]
            missing += [f"{p}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    u = D.UNITS[-1]
    W.run_task("G", u, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / "G" / u / f"{lo}.npz"), npz(serial / kind / "G" / u / f"{lo}.npz")
        same[f"{kind}/G/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {f"{u_}/{b_}/sigma0=be001.sim.run(none8,change4,memory4)": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {"unreachable_threshold=cue_arm": q5.result()}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    ev0 = sim.event("none", 8, 0.0, cases, V0, ema0, R0, T)
    exact = B1S.event("none", 8, cases, V0, ema0, R0, T, D.TAG)["aval"]
    noflip = np.where(sim.matched_flips(cases, ev0["am"], np.zeros(len(cases), int)), -exact, exact)
    alias["no_flips=exact_cue"] = bool(np.array_equal(noflip, exact)) and bool(np.array_equal(ev0["aval"], exact))
    worst = 0.0
    for uu in D.UNITS[:2]:
        raw = rawf(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        for b in D.BODIES:
            for sg in (0.0, 1.0):
                rn = D.run_name("none", 8, sg)
                ev = sim.event("none", 8, sg, cases, raw["V0"], raw["V0"], raw["R0"], raw["T"])
                for arm, prm in D.BIO.items():
                    rf = raw[f"{b}/{rn}/r"][D.ARMS.index(arm)]
                    cur = D.KAPPA * np.where(ev["am"], ev["aval"], 0.0) * L5S.vote_sign(rf)
                    v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(prm["lam"])))
                    gU = np.full(cur.shape, prm["lam"] ** 2)
                    v2 = B1S.cable_cg(cur, gU, gU, np.zeros_like(cur))
                    worst = max(worst, float(np.abs(v1 - v2).max()))
    alias["fft=cg_uniform_gates"] = worst <= 1e-9
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias, "max_solver_difference": worst}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        for (s, z, sg), rn in zip(D.RUNS, D.RUNNAMES):
            ev = sim.event(s, z, sg, cases, raw["V0"], raw["V0"], raw["R0"], raw["T"])
            tgt, m = ev["target"], ev["m"]
            band, interior = ev["dist"] == D.BAND, ev["dist"] > D.BAND
            for b in D.BODIES:
                key = f"{b}/{rn}"
                rf, Vf = raw[f"{key}/r"], raw[f"{key}/V"]
                got = {"r_all": S.sign(rf, tgt), "v_all": S.sign(Vf, tgt), "r_in": L5S.inside(rf, tgt, m),
                       "v_in": L5S.inside(Vf, tgt, m), "r_band": L5S.inside(rf, tgt, band),
                       "r_int": L5S.inside(rf, tgt, interior), "walls": sim.walls(rf) / sim.walls(tgt) - 1.0}
                for x, v in got.items():
                    if not np.array_equal(v, e[f"{key}/{x}"][-1]):
                        bad.append(f"{uu}/{key}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    smap = json.loads((FROZEN / "static_map.json").read_text())
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    am = L5S.anchor_mask(cases, D.TAG)
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // B1S.D.DENSITY).all())
    flips_ok = True
    for pattern in D.PATTERNS:
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for sg in D.SIGMAS[1:]:
            g_ = sim.event("none", 8, sg, cases, V0, ema0, R0, T)
            s_ = sim.event("scatter", 8, sg, cases, V0, ema0, R0, T)
            flips_ok &= bool((g_["mis"].sum((-2, -1)) == s_["mis"].sum((-2, -1))).all()) and not bool((s_["mis"] & ~s_["am"]).any())
    eff["matched_flips_equal_counts_on_anchors_only"] = flips_ok
    d_ = sim.boundary_distance(T)
    eff["band_and_interior_partition_the_sheet"] = bool((((d_ == D.BAND) ^ (d_ > D.BAND))).all()) and int(d_.min()) == 1
    devs = {}
    for uu in D.UNITS:          # every stage block; the expectation over the very anchors read (about 5 SE at 0.03)
        pattern, _ = D.parse_unit(uu)
        for sg in D.SIGMAS[1:]:
            got, exp = 0.0, 0.0
            for blk in range(lo, hi):
                e, Tq = shard(uu, blk), rawf(uu, blk)["T"]
                amq = L5S.anchor_mask(sim.prepare(pattern, blk, "engineering")[0], D.TAG)
                got += float(e[f"{D.BODIES[0]}/{D.run_name('none', 8, sg)}/misread"].mean())
                exp += float((static.misread_map(Tq, sg) * amq).sum() / amq.sum())
            devs[f"{uu}/{sg:g}"] = round((got - exp) / (hi - lo), 4)
    eff["misread_within_0.03_of_theory"] = all(abs(v) <= 0.03 for v in devs.values())
    g = sim.unit_normals(cases, D.TAG)
    eff["offset_sd_within_10pct"] = all(abs(float(np.std(np.concatenate(sim.offsets(g, sg)))) / sg - 1) <= 0.10 for sg in D.SIGMAS if sg >= 1)
    pt = np.zeros((1, D.SIDE, D.SIDE))
    pt[0, 5, 7] = 1.0
    eff["point_response_total_is_1/g_l"] = all(abs(float(np.real(np.fft.ifft2(np.fft.fft2(pt) / B1S.cable_kernel(l))).sum()) - 1 / D.G_LEAK) < 1e-12
                                               for l in (1.0, 1.5, 2.0, 3.0))
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff, "misread_minus_theory": devs}

    recomputed = q8.result()
    frozen_cmp = {k: v for k, v in smap.items() if k not in ("utc", "seconds")}
    checks["Q8_static_map_reproducible"] = {"pass": json.loads(json.dumps(recomputed)) == frozen_cmp}

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
    proc = subprocess.run([sys.executable, "-m", "gc001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "gc001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, s, z, sg, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu)
        k = D.ARMS.index(arm)
        key = f"{body}/{D.run_name(s, z, sg)}"
        d = max(float(np.abs(Vr - raw[f"{key}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{key}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{key}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{key}/W"][k, ci]).max()))
        items[f"{uu}/{key}/{arm}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_static_map_reproducible", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
