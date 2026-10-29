"""Qualification of BE001 on the preflight (engineering) shards; criteria fixed in advance.

python -m be001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: with only the cue and community arms on a patch of side 8, every situation equals lr005.sim.run bit for bit
    (body, record and bonds; both bodies; two units)
Q4  independent replay: per-site loops for the event (its own patch, anchors and cue damage), the body's local terms
    (conjugate gradients for the inhibitor, no FFT), bond noise (its own cut, statistics.NormalDist), the record's own
    bond sums, the cue arbiter, the currents, the cable equation solved by sparse LU (its own matrix; gates from the
    previous voltages), the trigger, the slow state, the pull and the Hebbian learners reproduce three full branches
    (bio-2 under a change of side 8, bio-2-gated under memory damage of side 8, bio-2-noisy under cue damage) within
    1e-8 (bonds exactly)
Q5  aliases: a bioelectric arm whose threshold cannot be reached equals the cue arm bit for bit (the machinery has no
    other effect); for every ungated arm the FFT steady state equals the conjugate-gradient solve with uniform gates
    within 1e-9 on the saved final currents
Q6  reanalysis: the endpoints at t = 4000 recomputed from the saved final states and the events equal the saved ones
Q7  efficacy: patches of 16, 64 and 144 cells; anchors on exactly a quarter of the cells, cue damage on exactly a quarter
    of them; a point current's total response is 1/g_l for every coupling length; uniform full disagreement gives a mean
    voltage of -1; a junction at |dv| = d0 has conductance lam^2 (g_min + (1 - g_min) / 2); a cell triggered once is
    committed for 299-301 updates with the inverted record sign; on stripes a coherent 8 x 8 disagreement triggers
    bio-2 at the patch centre and one corrupted anchor triggers bio-3 nowhere
Q8  labyrinths: every LB template is balanced (|mean| <= 0.1) with spacing within 20% of 8
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
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.linalg import splu  # noqa: E402

from be001 import design as D  # noqa: E402
from be001 import sim  # noqa: E402
from be001 import worker as W  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "be001" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t0", "li4", "change", 8, "bio-2", 0), ("LB_t1", "dw", "memory", 8, "bio-2-gated", 1),
            ("F0_t0", "li4", "cue", 8, "bio-2-noisy", 2))


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
                rows += [a, b]
                cols += [b, a]
                vals += [-g, -g]
                diag[a] += g
                diag[b] += g
    rows += list(range(n * n))
    cols += list(range(n * n))
    vals += diag
    return coo_matrix((vals, (rows, cols)), shape=(n * n, n * n)).tocsc()


def s_replay(unit, body, situation, size, arm, ci, block):
    """One bioelectric branch end to end with independent per-site code; returns final V, r, H, W."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    prm = D.BIO[arm]
    lam2 = prm["lam"] ** 2
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
    Hs = [[0.8 * x for x in row] for row in H]
    Ws = [[0.8 * x for x in row] for row in Wd]
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
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise", "voltage-noise")]
    uniform = [[lam2] * n for _ in range(n)]
    lu = None if prm["gate"] else splu(cable_matrix(n, uniform, uniform))
    v = np.zeros((n, n))
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)
    g = D.GATE

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    def gate(dv):
        return lam2 * (g["g_min"] + (1 - g["g_min"]) / (1 + math.exp((abs(dv) - g["d0"]) / g["w"])))

    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
        z, xi, zb, vn = (bufs[q][t % D.CHUNK] for q in range(4))
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
        if prm["gate"]:
            gh = [[gate(float(v[i, j]) - float(v[i, (j + 1) % n])) for j in range(n)] for i in range(n)]
            gw = [[gate(float(v[i, j]) - float(v[(i + 1) % n, j])) for j in range(n)] for i in range(n)]
            v = splu(cable_matrix(n, gh, gw)).solve(cur.ravel()).reshape(n, n)
        else:
            v = lu.solve(cur.ravel()).reshape(n, n)
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base = sv[i][j]
                else:
                    base = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                vo = float(v[i, j]) + (prm["noise"] * float(vn[i, j]) if prm["noise"] else 0.0)
                trig = vo < -prm["theta"] and sr[i][j] != 0
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
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """The cue and community arms on a patch of side 8 against lr005.sim.run, bit for bit, in every situation."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    arms = ("cue", "community-s", "community-c")
    ok = True
    for s in ("none", "cue", "memory", "change", "shared"):
        o = sim.run(body, s, 8, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, arms=arms)
        o5 = L5S.run(body, s, cases, V0, ema0, R0, th, T, theta, D.GAIN, {D.WINDOW}, tag=D.TAG, arms=arms)
        ok &= all(np.array_equal(o[x], o5[x]) for x in ("V", "r", "H", "W"))
    return (unit, body), bool(ok)


def q5_job(args):
    """A bioelectric arm with an unreachable threshold equals the cue arm bit for bit."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    D.BIO = copy.deepcopy(D.BIO)
    D.BIO["bio-1"]["theta"] = 1e300
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    o = sim.run(body, "change", 8, cases, V0, ema0, R0, th, T, theta, {1000}, window=1000, arms=("cue", "bio-1"))
    return bool(all(np.array_equal(o[x][:k], o[x][k:]) for x in ("V", "r", "H", "W")) and float(o["opened"][k:].sum()) == 0.0)


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
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks) + 1, len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, (u_, b_) in enumerate(q3_picks)])
    q5 = pool.submit(q5_job, ("S4_t0", "li4", lo, cpus[(len(Q4_PICKS) + len(q3_picks) + 1) % len(cpus)]))
    na, nr, ntr = len(D.ARMS), len(D.READS), len(D.TRACE_READS)
    runs = [D.run_name(s, z) for s, z in D.RUNS]

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
                for (s, z), rn in zip(D.RUNS, runs):
                    key = f"{body}/{rn}"
                    eps = W.ENDS if s == "change" else W.ENDS[:4]
                    bad += [f"{key}/{x}" for x in eps if e.get(f"{key}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                    bad += [f"{key}/opened"] if e.get(f"{key}/opened", np.zeros(0)).shape != (na, D.NCASE) else []
                    bad += [f"{key}/trace"] if e.get(f"{key}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
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

    eq = {f"{u_}/{b_}/cue,community=lr005.sim.run(every situation)": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {"unreachable_threshold=cue_arm": q5.result()}
    worst = 0.0
    for uu in D.UNITS[:2]:
        raw = rawf(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        aval = np.where(raw["R0"] > 0, 1.0, -1.0)
        for b in D.BODIES:
            for arm, prm in D.BIO.items():
                if prm["gate"]:
                    continue
                rf = raw[f"{b}/none8/r"][D.ARMS.index(arm)]
                cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
                v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / sim.cable_kernel(prm["lam"])))
                gU = np.full(cur.shape, prm["lam"] ** 2)
                v2 = sim.cable_cg(cur, gU, gU, np.zeros_like(cur))
                worst = max(worst, float(np.abs(v1 - v2).max()))
    alias["fft=cg_uniform_gates"] = worst <= 1e-9
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias, "max_solver_difference": worst}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        T = raw["T"]
        for (s, z), rn in zip(D.RUNS, runs):
            m = sim.patch(cases, z)
            tgt = np.where(m, -T, T) if s == "change" else T
            for b in D.BODIES:
                key = f"{b}/{rn}"
                rf, Vf = raw[f"{key}/r"], raw[f"{key}/V"]
                got = {"r_all": S.sign(rf, tgt), "v_all": S.sign(Vf, tgt), "r_in": L5S.inside(rf, tgt, m),
                       "v_in": L5S.inside(Vf, tgt, m)}
                for x, v in got.items():
                    if not np.array_equal(v, e[f"{key}/{x}"][-1]):
                        bad.append(f"{uu}/{key}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    eff["patch_cells_16_64_144"] = all(bool((sim.patch(cases, z).sum((-2, -1)) == z * z).all()) for z in D.SIZES)
    am = L5S.anchor_mask(cases, D.TAG)
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // D.DENSITY).all())
    ev = sim.event("cue", 8, cases, V0, ema0, R0, T)
    base = np.where(R0 > 0, 1.0, -1.0)
    eff["cue_damage_on_a_quarter_of_the_anchors"] = bool((((ev["aval"] != base) & am).sum((-2, -1)) == am.sum((-2, -1)) // 4).all())
    pt = np.zeros((1, D.SIDE, D.SIDE))
    pt[0, 5, 7] = 1.0
    eff["point_response_total_is_1/g_l"] = all(abs(float(np.real(np.fft.ifft2(np.fft.fft2(pt) / sim.cable_kernel(l))).sum()) - 1 / D.G_LEAK) < 1e-12
                                               for l in (1.0, 1.5, 2.0, 3.0))
    full = D.KAPPA * np.where(am[:1], -1.0, 0.0)
    eff["full_disagreement_mean_voltage_-1"] = abs(float(np.real(np.fft.ifft2(np.fft.fft2(full) / sim.cable_kernel(2.0))).mean()) + 1.0) < 1e-12
    gH, _ = sim.gates(np.array([[[0.0, D.GATE["d0"]]]]), 2.0)
    eff["gate_half_at_d0"] = abs(float(gH[0, 0, 0]) - 4.0 * (D.GATE["g_min"] + (1 - D.GATE["g_min"]) / 2)) < 1e-12
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    st = {"v": np.zeros(Tq.shape), "s": np.zeros(Tq.shape), "sgn": np.zeros(Tq.shape), "kernel": sim.cable_kernel(2.0)}
    avb = np.sign(Tq).copy()
    avb[0, 8:16, 8:16] *= -1                              # one update of coherent disagreement, then agreement again
    _, _, (c0, _) = sim.bio_targets("bio-2", Tq.copy(), Tq.copy(), {"am": amq, "aval": avb}, st, np.zeros(Tq.shape))
    stored = float(st["sgn"][0, 11, 11])
    held = 0
    while held < 1000:
        _, _, (cm, _) = sim.bio_targets("bio-2", Tq.copy(), Tq.copy(), {"am": amq, "aval": np.sign(Tq)}, st, np.zeros(Tq.shape))
        if not cm[0, 11, 11]:
            break
        held += 1
    eff["commitment_held_299_to_301_updates_with_the_inverted_sign"] = bool(c0[0, 11, 11]) and 299 <= held <= 301 \
        and stored == -float(np.sign(Tq[0, 11, 11]))
    for name, arm, flip, want in (("coherent_8x8_triggers_bio-2", "bio-2", "block", True),
                                  ("one_corrupted_anchor_triggers_bio-3_nowhere", "bio-3", "one", False)):
        av = np.sign(Tq).copy()
        if flip == "block":
            av[0, 8:16, 8:16] *= -1
        else:
            av[0, 10, 10] *= -1
        state = {"v": np.zeros(Tq.shape), "s": np.zeros(Tq.shape), "sgn": np.zeros(Tq.shape),
                 "kernel": sim.cable_kernel(D.BIO[arm]["lam"])}
        _, _, (committed, tt) = sim.bio_targets(arm, Tq.copy(), Tq.copy(), {"am": amq, "aval": av}, state, np.zeros(Tq.shape))
        eff[name] = bool(committed[0, 11, 11] and tt[0, 11, 11] == -np.sign(Tq[0, 11, 11])) if want else bool(not committed.any())
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
    proc = subprocess.run([sys.executable, "-m", "be001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, s, z, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu)
        k = D.ARMS.index(arm)
        key = f"{body}/{D.run_name(s, z)}"
        d = max(float(np.abs(Vr - raw[f"{key}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{key}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{key}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{key}/W"][k, ci]).max()))
        items[f"{uu}/{key}/{arm}/case{ci}"], worst = d, max(worst, d)
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
