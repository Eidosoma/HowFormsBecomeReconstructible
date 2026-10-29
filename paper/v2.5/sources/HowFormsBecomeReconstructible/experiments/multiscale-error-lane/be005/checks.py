"""Qualification of BE005 on the preflight (engineering) shards; criteria fixed in advance.

python -m be005.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: at the defaults the arms equal be004.sim.run's bit for bit (body, record and bonds), from the saved final
    states: memory4@0 (cue, bio-1, bio-3, dial-e0.01 = dial, never-e0.01 = bio-3), change4@0 (the references, dial-tv1 =
    dial, the brief and flickering arms at tau 1 = BE004's, never-tv1 = bio-3), cue4@0 (dial-tv1, never-tv1) and the
    dial-e0.01 in memory4@58 (BE004's dial with its signal at 59-1,058); two units, both bodies
Q4  independent replay: per-site loops for the event, the footprint, the body's local terms (conjugate gradients for the
    inhibitor), bond noise (its own cut), the record's own bond sums, LR004's arbiter, the currents, the cable equation by
    sparse LU on be001.checks' own matrix, the membrane's relaxation from the pre-event potentials, the flicker draws, the
    trigger, the slow state, the pull and the Hebbian learners with the arbiter's own rate on the bonds that touch an
    arbiter cell reproduce five full branches (dial-e0.02 in memory4@15, dial-e0.005 in memory4@1876, dial-f0.25-tv100 and
    dial-t10-tv10 in change4@0, dial-tv100 in memory4@0) within 1e-8 (bonds exactly)
Q5  aliases: with the signal never on, each dial-e equals its never-e and dial-tv100 and dial-t1-tv100 equal never-tv100,
    bit for bit; never-e0.01 equals bio-3 bit for bit; on the saved final currents the sparse LU equals the FFT for
    uniform conductances (lengths 1, 1.5, 3) and be001.sim.cable_cg with the footprint's conductances within 1e-9
Q6  reanalysis: the endpoints at t = 4,000 recomputed from the saved final states, the events and the regions equal the
    saved ones
Q7  efficacy: the delayed runs hold each dial-e at round(m T*(eta)); every signal arm on for exactly its updates (1,000,
    or 1, 10, 100; a flicker arm's share within 0.06 of p; a never arm none); onset, hit and the sensors recorded for the
    signal arms only (never arms: sensors and hit, no onset); a bond at +s0 relearning toward -1 at rate eta crosses zero
    after ceil(T*(eta)) updates; the arbiter cells are exactly the anchored, uncommitted cells whose body and record
    disagree; with tau_v = 10 the potentials reach v* + (v0 - v*)(0.9)^T after T updates of constant currents (1e-12); a
    signalled coherent 4 x 4 disagreement triggers dial-tv1 at its centre and not never-tv1
Q8  the static map on the cases' own draw (Amendment 1, 29 October 2026, the lead): for every preflight case the prompt
    dial's onset share (dial-e0.01 in memory4@0) equals within 1e-6 the static share computed on that case's own anchors
    and patch (be005.static's construction: the share of the 4 x 4 patch below -theta under the dial's steady potentials,
    every patch anchor disagreeing and every other anchor agreeing). Reported, not gated: the population comparison of
    the first freeze (the onset mean against the static map's 0.5168, tolerance 0.12; the patch's anchors 4 +- 0.5), which
    ignored the sampling variance of a 4 x 4 patch's anchors over the preflight's cases, and that variance
Q9  resources: forecast development wall <= 12 h on 12 workers with RAM and disk headroom
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
from scipy.sparse.linalg import splu  # noqa: E402

from be001 import sim as B1S  # noqa: E402
from be001.checks import cable_matrix  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from be004 import sim as B4S  # noqa: E402
from be005 import design as D  # noqa: E402
from be005 import sim  # noqa: E402
from be005 import worker as W  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "be005" / "frozen"
WORKERS = 12
Q4_PICKS = (("F0_t0", "dw", "memory", 4, 15, "dial-e0.02", 0), ("S4_t1", "li4", "memory", 4, 1876, "dial-e0.005", 1),
            ("LB_t0", "dw", "change", 4, 0, "dial-f0.25-tv100", 2), ("F0_t1", "li4", "change", 4, 0, "dial-t10-tv10", 3),
            ("S4_t0", "dw", "memory", 4, 0, "dial-tv100", 4))
RUNS = {D.run_name(*x): x for x in D.RUNS}
Q3_MAP = {"memory4@0": (("cue", "cue"), ("bio-1", "bio-1"), ("bio-3", "bio-3"), ("dial-e0.01", "dial"), ("never-e0.01", "bio-3")),
          "change4@0": (("cue", "cue"), ("bio-1", "bio-1"), ("bio-3", "bio-3"), ("dial-tv1", "dial"), ("dial-t1-tv1", "dial-t1"),
                        ("dial-t10-tv1", "dial-t10"), ("dial-t100-tv1", "dial-t100"), ("dial-f0.5-tv1", "dial-f0.5"),
                        ("dial-f0.25-tv1", "dial-f0.25"), ("never-tv1", "bio-3")),
          "cue4@0": (("dial-tv1", "dial"), ("never-tv1", "bio-3")),
          "memory4@58": (("dial-e0.01", "dial"),)}


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def static_onset(cases):
    """Q8 (Amendment 1): per case, the static share on its own anchors and patch, and the patch's anchors."""
    am = L5S.anchor_mask(cases, D.TAG)
    m = sim.patch(cases, 4, D.TAG)
    lus = B2S.factor(*B2S.conductances(sim.footprint(m), D.SIG["lam_rest"], D.SIG["lam_sig"]))
    v = B2S.solve(lus, D.KAPPA * am * np.where(m, -1.0, 1.0))
    return ((v < -D.SIG["theta"]) & m).sum((-2, -1)) / m.sum((-2, -1)), (am & m).sum((-2, -1))


def s_replay(unit, body, situation, size, delay, arm, ci, block):
    """One signal arm's branch end to end with independent per-site code; returns final V, r, H, W."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    prm = D.SIGNAL_ARMS[arm]
    first, last = delay + 1, delay + D.SIG["duration"]
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    dd = D.SIG["d"]
    wide = size + 2 * dd
    fp = [[((i - a + dd) % n) < wide and ((j - b + dd) % n) < wide for j in range(n)] for i in range(n)]
    perm = address(D.TAG, *key, "anchors", D.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // D.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    cur_pre = np.array([[D.KAPPA * (aval[i][j] if anch[i][j] else 0.0) * vs(float(R0c[i, j])) for j in range(n)] for i in range(n)])
    rv0 = R0c.copy()
    if situation == "memory":
        rv0 = np.where(np.array(patch), -R0c, R0c)
    sg = [[1.0 if rv0[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[D.STRENGTH0 * x for x in row] for row in H]
    Ws = [[D.STRENGTH0 * x for x in row] for row in Wd]
    r = rv0.copy()
    if situation == "cue":
        pick = address(D.TAG, *key, "cue-damage").permutation(len(cells))[: len(cells) // 4]
        for p_ in pick:
            q = cells[int(p_)]
            aval[q // n][q % n] *= -1.0
    elif situation == "change":
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    aval[i][j] *= -1.0
    cut = NormalDist().inv_cdf(1.0 - D.RATE)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    u_fl = address(D.TAG, *key, "flicker").random(D.WINDOW)
    rest, sig2 = D.SIG["lam_rest"] ** 2, D.SIG["lam_sig"] ** 2
    gh = [[sig2 if (fp[i][j] or fp[i][(j + 1) % n]) else rest for j in range(n)] for i in range(n)]
    gw = [[sig2 if (fp[i][j] or fp[(i + 1) % n][j]) else rest for j in range(n)] for i in range(n)]
    lu_on = splu(cable_matrix(n, gh, gw))
    lu_off = splu(cable_matrix(n, [[rest] * n for _ in range(n)], [[rest] * n for _ in range(n)]))
    v_prev = lu_off.solve(cur_pre.ravel()).reshape(n, n)
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)
    tau_v, eta_a = prm["tau_v"], prm["eta_a"]
    for t in range(D.WINDOW):
        on = (not prm["never"]) and first <= t + 1 <= min(last, first + prm["dur"] - 1) and (prm["p_on"] >= 1.0 or u_fl[t] < prm["p_on"])
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
                r1[i, j] = min(max(rr + D.EPS * (rr * (1 - (rr / 1.2) ** 2) + D.KR * (bs - rr)) + D.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        r = r1
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        cur = np.array([[D.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
        v_star = (lu_on if on else lu_off).solve(cur.ravel()).reshape(n, n)
        v = v_star if tau_v == 1 else v_prev + (v_star - v_prev) / tau_v
        v_prev = v
        tr = [[0.0] * n for _ in range(n)]
        fixc = [[False] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                cue_base = False
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base = sv[i][j]
                elif ca[i][j] != 0:
                    base, cue_base = ca[i][j], True
                else:
                    base = sr[i][j] if sr[i][j] != 0 else sv[i][j]
                trig = float(v[i, j]) < -D.SIG["theta"] and sr[i][j] != 0
                was = s_[i][j] >= D.S_MIN
                if trig and not was:
                    sgn[i][j] = -sr[i][j]
                s_[i][j] = 1.0 if trig else s_[i][j] * decay
                if s_[i][j] >= D.S_MIN:
                    tr[i][j] = sgn[i][j]
                    r[i, j] = float(r[i, j]) + D.EPS * D.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
                else:
                    tr[i][j] = base
                    fixc[i][j] = cue_base
        for i in range(n):
            for j in range(n):
                for E, Es, x, other in ((H, Hs, tr[i][j] * tr[i][(j + 1) % n], fixc[i][(j + 1) % n]),
                                        (Wd, Ws, tr[i][j] * tr[(i + 1) % n][j], fixc[(i + 1) % n][j])):
                    if x != 0:
                        rate = eta_a if (fixc[i][j] or other) else D.ETA
                        Es[i][j] = Es[i][j] + rate * (x - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """BE005's arms at the defaults against be004.sim.run's, bit for bit, from the saved final states."""
    unit, body, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    ok = {}
    for rn, pairs in Q3_MAP.items():
        situation, size, delay, mine = RUNS[rn]
        theirs = tuple(dict.fromkeys(b4 for _, b4 in pairs))
        o = B4S.run(body, situation, size, delay, theirs, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG)
        good = True
        for a5, a4 in pairs:
            i, j = mine.index(a5), theirs.index(a4)
            for x in ("V", "r", "H", "W"):
                want = o[x][j * k:(j + 1) * k]
                got = raw[f"{rn}/{x}"][i]
                good &= bool(np.array_equal(got, want.astype(got.dtype)) and (x in ("H", "W") or np.array_equal(got, want)))
        ok[f"{unit}/{body}/{rn}"] = good
    return ok


def q5_job(args):
    """With the signal never on, a signal arm equals its no-signal arm (bit for bit), over 1,200 updates."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, out = len(cases), {}
    for situation, arms in (("memory", tuple(a for e in D.ETAS for a in (f"dial-e{D.fmt(e)}", f"never-e{D.fmt(e)}"))),
                            ("change", ("dial-tv100", "never-tv100", "dial-t1-tv100", "never-tv100"))):
        o = sim.run(body, situation, 4, 0, arms, cases, V0, ema0, R0, th, T, theta, {1200}, window=1200, on_window=(0, -1))
        for j in range(0, len(arms), 2):
            out[f"{unit}/{body}/{situation}4,no signal:{arms[j]}={arms[j + 1]}"] = all(
                np.array_equal(o[x][j * k:(j + 1) * k], o[x][(j + 1) * k:(j + 2) * k]) for x in ("V", "r", "H", "W"))
    return out


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
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "LB_t0") for b_ in D.BODIES]
    q5_picks = [("F0_t0", b_) for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks) + len(q5_picks), len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q4 = pool.map(replay_job, [(pk, lo, cpu_of(i)) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, str(root), cpu_of(len(Q4_PICKS) + i)) for i, (u_, b_) in enumerate(q3_picks)])
    q5 = pool.map(q5_job, [(u_, b_, lo, cpu_of(len(Q4_PICKS) + len(q3_picks) + i)) for i, (u_, b_) in enumerate(q5_picks)])
    nr, ntr = len(D.READS), D.WINDOW // D.TRACE

    missing = []
    for body, u in D.tasks():
        for blk in range(lo, hi):
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(run[3])
                eps = [x for x in W.ENDS if x != "r_in_old" or run[0] == "change"]
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in W.SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/n_anc"] if e.get(f"{rn}/n_anc", np.zeros(0)).shape != (D.NCASE,) else []
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
    checks["Q3_engine"] = {"pass": bool(eq) and all(eq.values()), "items": eq}

    alias = {}
    for d_ in q5:
        alias.update(d_)
    for uu in ("S4_t1", "LB_t0"):
        for b_ in D.BODIES:
            raw = rawf(uu, b_)
            arms = RUNS["memory4@0"][3]
            i, j = arms.index("never-e0.01"), arms.index("bio-3")
            alias[f"{uu}/{b_}/memory4@0:never-e0.01=bio-3"] = all(np.array_equal(raw[f"memory4@0/{x}"][i], raw[f"memory4@0/{x}"][j])
                                                                   for x in ("V", "r", "H", "W"))
    worst_fft, worst_cg = 0.0, 0.0
    for uu in D.UNITS[:2]:
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        m = sim.patch(cases, 4, D.TAG)
        for b_ in D.BODIES:
            raw = rawf(uu, b_)
            aval = np.where(raw["R0"] > 0, 1.0, -1.0)
            rf = raw["memory4@0/r"][RUNS["memory4@0"][3].index("dial-e0.01")]
            cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
            for lam in (1.0, 1.5, 3.0):
                g = np.full(cur.shape, lam ** 2)
                v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
                worst_fft = max(worst_fft, float(np.abs(B2S.solve(B2S.factor(g, g), cur) - v1).max()))
            gH, gW = B2S.conductances(sim.footprint(m), D.SIG["lam_rest"], D.SIG["lam_sig"])
            v_lu = B2S.solve(B2S.factor(gH, gW), cur)
            v_cg = B1S.cable_cg(cur, gH, gW, np.zeros_like(cur))
            worst_cg = max(worst_cg, float(np.abs(v_lu - v_cg).max()))
    items = dict(alias)
    items.update({"lu=fft_uniform": worst_fft <= 1e-9, "lu=cg_footprint": worst_cg <= 1e-9})
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "items": items, "max_lu_fft": worst_fft, "max_lu_cg": worst_cg}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(uu, body), shard(uu, body)
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for run in D.RUNS:
            rn = D.run_name(*run)
            ev = sim.event(run[0], run[1], cases, V0, ema0, R0, T, D.TAG)
            m, tgt = ev["m"], ev["target"]
            na = len(run[3])
            tile = lambda x: np.tile(x, (na, 1, 1))
            rf = raw[f"{rn}/r"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            Vf = raw[f"{rn}/V"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            got = {"r_all": S.sign(rf, tile(tgt)), "r_in": L5S.inside(rf, tile(tgt), tile(m)),
                   "v_in": L5S.inside(Vf, tile(tgt), tile(m)),
                   "n_anc_ok": (((rf > 0) == (tile(tgt) > 0)) & tile(m & ev["am"])).sum((-2, -1)).astype(float),
                   "r_out8": L5S.inside(rf, tile(tgt), tile(~B2S.footprint(m, 8)))}
            for dd in D.FOOTPRINTS:
                got[f"r_fp{dd}"] = L5S.inside(rf, tile(tgt), tile(B2S.footprint(m, dd)))
            if run[0] == "change":
                got["r_in_old"] = L5S.inside(rf, tile(ev["old"]), tile(m))
            for x, v in got.items():
                if not np.array_equal(v.reshape(na, D.NCASE), e[f"{rn}/{x}"][-1]):
                    bad.append(f"{uu}/{body}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    eff["delays_round_m_t_star"] = all(f"dial-e{D.fmt(e)}" in RUNS[D.where(e, m_)[0]][3] and
                                       RUNS[D.where(e, m_)[0]][2] == int(round(m_ * D.t_star(e))) for e in D.ETAS for m_ in D.MULTS)
    sig_ok, rec_ok = True, True
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn = D.run_name(*run)
                for i, arm in enumerate(run[3]):
                    on, hit, anc = e[f"{rn}/onset"][i], e[f"{rn}/hit"][i], e[f"{rn}/anc_on"][i]
                    if arm in D.SIGNAL_ARMS:
                        prm = D.SIGNAL_ARMS[arm]
                        n_on = meta["signal_updates"][rn][arm] / D.NCASE
                        if prm["never"]:
                            sig_ok &= n_on == 0
                            rec_ok &= bool((on == -1).all())
                        elif prm["p_on"] >= 1.0:
                            sig_ok &= n_on == prm["dur"]
                            rec_ok &= bool(((on >= 0) & (on <= 1)).all())
                        else:
                            sig_ok &= abs(n_on / prm["dur"] - prm["p_on"]) <= 0.06
                            rec_ok &= bool(((on >= 0) & (on <= 1)).all())
                        rec_ok &= bool(((hit >= 0) & (hit <= 1)).all() and (anc >= 0).all())
                    else:
                        rec_ok &= bool((on == -1).all() and (hit == -1).all() and (anc == -1).all())
    eff["signal_on_for_exactly_its_updates"] = bool(sig_ok)
    eff["onset_hit_sensors_recorded_for_signal_arms_only"] = bool(rec_ok)
    clock = True
    for e_ in D.ETAS:
        hb, nsteps = D.STRENGTH0, 0
        while hb > 0:
            hb, nsteps = hb + e_ * (-1.0 - hb), nsteps + 1
        clock &= nsteps == math.ceil(D.t_star(e_))
    eff["bond_crosses_zero_after_ceil_t_star"] = bool(clock)
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    mq = np.zeros(Tq.shape, bool)
    mq[0, 12:16, 12:16] = True
    Vq, rq = Tq.copy(), np.where(mq, -Tq, Tq)                   # a damaged record under a body that holds the pattern
    Pm = {"am": amq, "aval": np.sign(Tq)}
    st = sim.new_state(1, mq)
    _, _, (comm, _), fix = sim.sig_targets("dial-e0.005", Vq, rq, Pm, st, False)
    want = amq & mq & ~comm                                      # anchored, body and record disagree, not committed
    eff["arbiter_cells_are_the_anchored_disagreeing_uncommitted"] = bool(want.any() and np.array_equal(fix, want))
    cur_v = []
    st10 = sim.new_state(1, mq, v0=np.ones(Tq.shape))
    P0 = {"am": amq, "aval": np.sign(Tq)}
    for _ in range(25):
        sim.sig_targets("dial-tv10", Tq.copy(), Tq.copy(), P0, st10, False)
        cur_v.append(st10["v"].copy())
    v_star = np.real(np.fft.ifft2(np.fft.fft2(D.KAPPA * np.where(amq, np.sign(Tq), 0.0) * L5S.vote_sign(Tq)) / B1S.cable_kernel(3.0)))
    want25 = v_star + (1.0 - v_star) * 0.9 ** 25
    eff["membrane_relaxes_as_0.9^T"] = bool(np.abs(cur_v[-1] - want25).max() <= 1e-12)
    av = np.sign(Tq).copy()
    av[mq] *= -1
    P = {"am": amq, "aval": av}
    st1 = sim.new_state(1, mq)
    _, _, (c_on, t_on), _ = sim.sig_targets("dial-tv1", Tq.copy(), Tq.copy(), P, st1, True)
    stn = sim.new_state(1, mq)
    _, _, (c_off, _), _ = sim.sig_targets("never-tv1", Tq.copy(), Tq.copy(), P, stn, False)
    eff["signalled_4x4_triggers_dial-tv1_not_never-tv1"] = bool(c_on[0, 13, 13] and t_on[0, 13, 13] == -np.sign(Tq[0, 13, 13])
                                                                and not c_off.any())
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    static = json.loads((FROZEN / "static_map.json").read_text())
    kd = RUNS["memory4@0"][3].index("dial-e0.01")
    onsets, nancs, matched, own = [], [], [], {}
    for body, uu in D.tasks():
        pattern, _ = D.parse_unit(uu)
        for blk in range(lo, hi):
            e = shard(uu, body, blk)
            if (pattern, blk) not in own:
                cs = sim.prepare(pattern, blk, "engineering")[0]
                own[(pattern, blk)] = (*static_onset(cs), [c.key() for c in cs])
            onsets.append(e["memory4@0/onset"][kd])
            nancs.append(e["memory4@0/n_anc"])
            matched.append(own[(pattern, blk)])
    on8, na8 = np.concatenate(onsets), np.concatenate(nancs)
    st8, sa8 = np.concatenate([x[0] for x in matched]), np.concatenate([x[1] for x in matched])
    worst8 = float(np.abs(on8 - st8).max())
    anchors_of = {kk: int(c) for x in own.values() for kk, c in zip(x[2], x[1])}       # a case's anchors and patch
    per_case = [anchors_of[kk] for kk in sorted(anchors_of)]                         # do not depend on the pattern
    q, N = 1.0 / D.DENSITY, D.SIDE * D.SIDE
    mo, mn = float(on8.mean()), float(na8.mean())
    checks["Q8_static_case_matched"] = {
        "pass": worst8 <= 1e-6, "max_abs_onset_minus_case_static": worst8, "prompt_onset_mean": mo,
        "case_static_mean": float(st8.mean()),
        "reported_not_gated": {"static_adoption_dial": static["relaxation"]["1"]["dial"],
                               "onset_minus_static_map": mo - static["relaxation"]["1"]["dial"],
                               "patch_anchors_mean": mn, "patch_anchors_expected": 16 * q,
                               "patch_anchors_se_over_cases": math.sqrt(16 * q * (1 - q) * (N - 16) / (N - 1) / len(per_case)),
                               "cases": len(per_case), "patch_anchors_per_case": per_case,
                               "patch_anchors_equal_shards": bool(np.array_equal(na8, sa8))}}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, uu = key.split("/")[:2]
        walls.setdefault((b_, uu), []).append(t["wall_s"])
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
    proc = subprocess.run([sys.executable, "-m", "be005.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be005.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, s, z, dl, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu, body)
        rn = D.run_name(s, z, dl)
        k = RUNS[rn][3].index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{rn}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{rn}/W"][k, ci]).max()))
        items[f"{uu}/{body}/{rn}/{arm}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_static_case_matched", "Q9_resources", "Q10_reader_dry_run"]
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
