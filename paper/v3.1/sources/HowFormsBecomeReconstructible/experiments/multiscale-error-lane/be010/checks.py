"""Qualification of BE010 on the preflight (engineering) shards; criteria fixed in advance.

python -m be010.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape (each run at its own reads and window)
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: reset N's arms equal be007.sim.run's dial-C12 and never-C12 bit for bit (body, record and bonds), from the
    saved final states, at each run's own window: dial-N in memory4@w+0 and memory4@w+979 (be007's memory4@7836 and
    memory4@8815), never-N in memory4@w+3918 (be007's memory4@0, run to 15,754) and in none4@w+0 (be007's none4@0), and
    dial-N and never-N in cue4@w+0 (be007's cue4@7836 and cue4@0); two units, both bodies
Q4  independent replay: per-site loops for the event, the footprint, the body's local terms (conjugate gradients for the
    inhibitor), bond noise at the clock's p_b, the record's own bond sums, LR004's arbiter, the currents, the cable
    equation by sparse LU on be001.checks' own matrix, the trigger, the slow state decaying by exp(-1 / tau_c), the pull,
    the Hebbian learner, the execution at tau_x, the second event (the newborn values drawn from the addressed stream,
    the record 0, the touching or inside contacts untrained, the decision state cleared in the patch or, for the drug,
    everywhere) and the re-execution at T_W + tau_x reproduce five full branches (dial-W in memory4@w+979, dial-R in
    memory4@w+0, dial-K in memory4@w+1959, dial-R in cue4@w+0, dial-R0 in memory4@w+3918) within 1e-8 (bonds exactly)
Q5  aliases: in memory4@w+3918 every dial-X equals its never-X bit for bit at every read before the dial's first update;
    in every run every reset arm equals the N arm of its kind at every read up to T_W and in the trace to T_W; W0 equals W
    and R0 equals R (each kind) at every read and trace point before RE_X; on the saved final currents the sparse LU
    equals the FFT for uniform conductances (lengths 1, 1.5, 3) and be001.sim.cable_cg with the footprint's conductances
    within 1e-9
Q6  reanalysis: the endpoints at each run's last read recomputed from the saved final states, the events and the regions
    equal the saved ones (committed_in excepted: the decision state is not saved)
Q7  efficacy: the runs hold every dial at T_W + round(m T*); every dial on for exactly its 1,000 updates and every never
    arm for none; onset recorded for the dials only, hit and the sensors for every arm; 'executed' recorded for every arm
    and 'executed2' exactly for the re-executing arms; on a constructed state the second event does exactly its rule
    (wound: the patch's bodies and moving averages the newborn values, KILL_SD x the addressed 'newborn' normals, records
    0, every touching contact sign 0 and strength 0; wound-kept: only the contacts inside; both clear the decision
    state in the patch and nothing outside it; decommit: nothing but the decision state, everywhere); re-execution commits
    exactly the uncommitted confident footprint cells at T_W + tau_x and nothing one update earlier; a bond at +s0
    relearning toward -1 at 3e-4 crosses zero after ceil(T*) updates; a cell committed once stays committed for exactly
    15,000 updates, its commitment's update included; the bond-noise cut flips a bond with probability p_b
Q8  the second event, case by case (read T_W + 1): for every preflight case, the W and K arms of every run have no
    confident and no committed patch cell; every reset arm's record outside the footprint dilated by 8 (r_out8) equals
    its N arm's; and every R arm's body in the patch (v_in) equals its N arm's
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
from be007 import design as D7  # noqa: E402
from be007 import sim as S7  # noqa: E402
from be010 import design as D  # noqa: E402
from be010 import sim  # noqa: E402
from be010 import worker as W  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "be010" / "frozen"
WORKERS = 12
RUNS = {D.run_name(*x): x for x in D.RUNS}
NV, SH = D.NEVER_RUN, D.SHAM_RUN
Q4_PICKS = (("F0_t0", "dw", "memory", 4, D.AFTER_W[1], "dial-W", 0),
            ("S4_t1", "li4", "memory", 4, D.AFTER_W[0], "dial-R", 1),
            ("LB_t0", "dw", "memory", 4, D.AFTER_W[2], "dial-K", 2),
            ("F0_t1", "li4", "cue", 4, 0, "dial-R", 3),
            ("S4_t0", "dw", "memory", 4, D.AFTER_W[3], "dial-R0", 4))
Q3_MAP = ((D.run_name("memory", 4, 0), "dial-N", "memory", D.T_W),           # (run, my arm, be007's situation, delay)
          (D.run_name("memory", 4, D.AFTER_W[1]), "dial-N", "memory", D.T_W + D.AFTER_W[1]),
          (NV, "never-N", "memory", 0),
          (SH, "never-N", "none", 0),
          (D.CUE_RUN, "dial-N", "cue", D.T_W),
          (D.CUE_RUN, "never-N", "cue", 0))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, situation, size, d, arm, ci, block):
    """One arm's branch end to end with independent per-site code; returns final V, r, H, W."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    prm = D.SIGNAL_ARMS[arm]
    window = D.run_window(situation, size, d, (arm,))
    first, last = D.T_W + d + 1, D.T_W + d + D.SIG["duration"]
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    E = ema0[ci].astype(float).copy()
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
    cut = NormalDist().inv_cdf(1.0 - prm["rate"])
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    newborn = D.KILL_SD * address(D.TAG, *key, "newborn").standard_normal((n, n))
    rest, sig2 = D.SIG["lam_rest"] ** 2, D.SIG["lam_sig"] ** 2
    gh = [[sig2 if (fp[i][j] or fp[i][(j + 1) % n]) else rest for j in range(n)] for i in range(n)]
    gw = [[sig2 if (fp[i][j] or fp[(i + 1) % n][j]) else rest for j in range(n)] for i in range(n)]
    lu_on = splu(cable_matrix(n, gh, gw))
    lu_off = splu(cable_matrix(n, [[rest] * n for _ in range(n)], [[rest] * n for _ in range(n)]))
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / prm["tau_c"])
    eta, eta_a = prm["eta"], prm["eta_a"]
    tx, reset = prm["tau_x"], prm["reset"]
    tx2 = D.T_W + tx if prm["rexec"] else None
    for t in range(window):
        if t == D.T_W and reset is not None:                   # the second event, before update T_W + 1
            for i in range(n):
                for j in range(n):
                    if patch[i][j] or reset == "decommit":
                        s_[i][j], sgn[i][j] = 0.0, 0.0
                    if patch[i][j] and reset != "decommit":
                        V[i, j], E[i, j], r[i, j] = newborn[i, j], newborn[i, j], 0.0
            if reset != "decommit":
                for i in range(n):
                    for j in range(n):
                        right, down = patch[i][(j + 1) % n], patch[(i + 1) % n][j]
                        if (patch[i][j] or right) if reset == "wound" else (patch[i][j] and right):
                            H[i][j], Hs[i][j] = 0.0, 0.0
                        if (patch[i][j] or down) if reset == "wound" else (patch[i][j] and down):
                            Wd[i][j], Ws[i][j] = 0.0, 0.0
        on = (not prm["never"]) and first <= t + 1 <= last
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
        v = (lu_on if on else lu_off).solve(cur.ravel()).reshape(n, n)
        if t + 1 == tx or (tx2 is not None and t + 1 == tx2):  # the execution and the re-execution
            for i in range(n):
                for j in range(n):
                    if fp[i][j] and s_[i][j] < D.S_MIN and sr[i][j] != 0:
                        sgn[i][j], s_[i][j] = sr[i][j], 1.0
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
                for Ed, Es, x, other in ((H, Hs, tr[i][j] * tr[i][(j + 1) % n], fixc[i][(j + 1) % n]),
                                         (Wd, Ws, tr[i][j] * tr[(i + 1) % n][j], fixc[(i + 1) % n][j])):
                    if x != 0:
                        rate = eta_a if (fixc[i][j] or other) else eta
                        Es[i][j] = Es[i][j] + rate * (x - Es[i][j])
                        if Es[i][j] != 0:
                            Ed[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """Reset N's arms against be007.sim.run's C12 arms, bit for bit, from the saved final states."""
    unit, body, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    ok = {}
    for rn, arm, situation, delay in Q3_MAP:
        wdw = D.run_window(*RUNS[rn])
        arm7 = arm.replace("-N", "-C12")
        o = S7.run(body, situation, 4, delay, (arm7,), cases, V0, ema0, R0, th, T, theta, {wdw}, tag=D.TAG, window=wdw)
        i = RUNS[rn][3].index(arm)
        good = True
        for x in ("V", "r", "H", "W"):
            want = o[x][:k]
            got = raw[f"{rn}/{x}"][i]
            good &= bool(np.array_equal(got, want.astype(got.dtype)) and (x in ("H", "W") or np.array_equal(got, want)))
        ok[f"{unit}/{body}/{rn}:{arm}=be007 {D7.run_name(situation, 4, delay)}:{arm7}"] = good
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
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "LB_t0") for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks), len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q4 = pool.map(replay_job, [(pk, lo, cpu_of(i)) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, str(root), cpu_of(len(Q4_PICKS) + i)) for i, (u_, b_) in enumerate(q3_picks)])

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
                nr, ntr = len(D.run_reads(*run)), D.run_window(*run) // D.TRACE
                eps = [x for x in W.ENDS if x != "r_in_old"]
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in W.SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/n_anc"] if e.get(f"{rn}/n_anc", np.zeros(0)).shape != (D.NCASE,) else []
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
                bad += [f"{rn}/r_in_old"] if f"{rn}/r_in_old" in e else []
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

    items = {}
    EP = ("r_in", "v_in", "r_all", "n_anc_ok", "committed_in", "conf_in")
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn, arms, reads = D.run_name(*run), list(run[3]), D.run_reads(*run)
                first = D.on_window(*run)[0]
                upto = [ti for ti, t_ in enumerate(reads) if t_ <= D.T_W]
                pre_x = [ti for ti, t_ in enumerate(reads) if t_ < D.RE_X]
                ntw, nrx = D.T_W // D.TRACE, (D.RE_X - 1) // D.TRACE
                tr = e[f"{rn}/trace"]
                for i, arm in enumerate(arms):
                    kind, x = arm.split("-")
                    if x != "N" and f"{kind}-N" in arms:
                        j = arms.index(f"{kind}-N")
                        items[f"{uu}/{body}/{blk}/{rn}:{arm}=N to T_W"] = all(
                            np.array_equal(e[f"{rn}/{q}"][upto, i], e[f"{rn}/{q}"][upto, j]) for q in EP) and \
                            np.array_equal(tr[:ntw, i], tr[:ntw, j])
                    if x in ("W0", "R0") and f"{kind}-{x[0]}" in arms:
                        j = arms.index(f"{kind}-{x[0]}")
                        items[f"{uu}/{body}/{blk}/{rn}:{arm}={kind}-{x[0]} before RE_X"] = all(
                            np.array_equal(e[f"{rn}/{q}"][pre_x, i], e[f"{rn}/{q}"][pre_x, j]) for q in EP) and \
                            np.array_equal(tr[:nrx, i], tr[:nrx, j])
                    if rn == NV and kind == "dial":
                        j = arms.index(f"never-{x}")
                        before = [ti for ti, t_ in enumerate(reads) if t_ < first]
                        items[f"{uu}/{body}/{blk}/{rn}:{arm}=never-{x} before the dial"] = all(
                            np.array_equal(e[f"{rn}/{q}"][before, i], e[f"{rn}/{q}"][before, j]) for q in EP)
    worst_fft, worst_cg = 0.0, 0.0
    for uu in D.UNITS[:2]:
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        m = sim.patch(cases, 4, D.TAG)
        for b_ in D.BODIES:
            raw = rawf(uu, b_)
            aval = np.where(raw["R0"] > 0, 1.0, -1.0)
            rf = raw[f"{NV}/r"][RUNS[NV][3].index("dial-R")]
            cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
            for lam in (1.0, 1.5, 3.0):
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
                   "r_out8": L5S.inside(rf, tile(tgt), tile(~B2S.footprint(m, 8))),
                   "conf_in": ((np.abs(rf) >= D.VMIN) & tile(m)).sum((-2, -1)) / tile(m).sum((-2, -1))}
            for dd in (0, 2, 4, 8):
                got[f"r_fp{dd}"] = L5S.inside(rf, tile(tgt), tile(B2S.footprint(m, dd)))
            for x, v in got.items():
                if not np.array_equal(v.reshape(na, D.NCASE), e[f"{rn}/{x}"][-1]):
                    bad.append(f"{uu}/{body}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    eff["dials_at_t_w_plus_round_m_t_star"] = all(
        RUNS[D.where(x, m_)[0]][2] == int(round(m_ * D.T_STAR)) and f"dial-{x}" in RUNS[D.where(x, m_)[0]][3]
        and D.on_window(*RUNS[D.where(x, m_)[0]])[0] == D.T_W + int(round(m_ * D.T_STAR)) + 1
        for x in D.MAIN for m_ in D.MULTS)
    sig_ok, rec_ok, exe_ok = True, True, True
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn = D.run_name(*run)
                for i, arm in enumerate(run[3]):
                    prm = D.SIGNAL_ARMS[arm]
                    on, hit, anc = e[f"{rn}/onset"][i], e[f"{rn}/hit"][i], e[f"{rn}/anc_on"][i]
                    exe, exe2 = e[f"{rn}/executed"][i], e[f"{rn}/executed2"][i]
                    n_on = meta["signal_updates"][rn][arm] / D.NCASE
                    if prm["never"]:
                        sig_ok &= n_on == 0
                        rec_ok &= bool((on == -1).all())
                    else:
                        sig_ok &= n_on == D.SIG["duration"]
                        rec_ok &= bool(((on >= 0) & (on <= 1)).all())
                    rec_ok &= bool(((hit >= 0) & (hit <= 1)).all() and (anc >= 0).all())
                    exe_ok &= bool(((exe >= 0) & (exe <= 1)).all())
                    exe_ok &= bool(((exe2 >= 0) & (exe2 <= 1)).all()) if prm["rexec"] else bool((exe2 == -1).all())
    eff["signal_on_for_exactly_its_updates"] = bool(sig_ok)
    eff["onset_for_dials_hit_and_sensors_for_all"] = bool(rec_ok)
    eff["executed_for_all_executed2_exactly_for_rexec_arms"] = bool(exe_ok)
    # the second event on a constructed state (one case of the first preflight unit)
    pattern, _ = D.parse_unit(D.UNITS[0])
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    ev = sim.event("memory", 4, cases, V0, ema0, R0, T, D.TAG)
    m, k = ev["m"], len(cases)
    nb = np.stack([D.KILL_SD * address(D.TAG, *c.key(), "newborn").standard_normal((D.SIDE, D.SIDE)) for c in cases])
    eff["newborn_values_are_kill_sd_times_the_addressed_normals"] = bool(np.array_equal(nb, L5S.newborn(cases, D.TAG)))
    touch_h = m | np.roll(m, -1, -1)
    touch_w = m | np.roll(m, -1, -2)
    in_h, in_w = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
    rules = True
    for kind in ("wound", "wound-kept", "decommit"):
        V, E, r = ev["V"].copy(), ev["E"].copy(), ev["r"].copy()
        H, Wd, Hb, Wb = ev["H"].copy(), ev["W"].copy(), ev["Hb"].copy(), ev["Wb"].copy()
        st = sim.new_state(k, m)
        st["s"], st["sgn"] = np.ones_like(st["s"]), -np.ones_like(st["sgn"])
        sim.second_event(kind, m, k, V, E, r, H, Wd, Hb, Wb, st, nb)
        if kind == "decommit":
            rules &= bool((st["s"] == 0).all() and (st["sgn"] == 0).all())
        else:
            rules &= bool((st["s"][m] == 0).all() and (st["sgn"][m] == 0).all() and (st["s"][~m] == 1).all()
                          and (st["sgn"][~m] == -1).all())
        if kind == "decommit":
            rules &= all(np.array_equal(x, y) for x, y in ((V, ev["V"]), (E, ev["E"]), (r, ev["r"]), (H, ev["H"]),
                                                            (Wd, ev["W"]), (Hb, ev["Hb"]), (Wb, ev["Wb"])))
            continue
        ch, cw = (touch_h, touch_w) if kind == "wound" else (in_h, in_w)
        rules &= bool(np.array_equal(V, np.where(m, nb, ev["V"])) and np.array_equal(E, np.where(m, nb, ev["E"]))
                      and np.array_equal(r, np.where(m, 0.0, ev["r"])))
        rules &= bool(np.array_equal(H, np.where(ch, 0.0, ev["H"])) and np.array_equal(Hb, np.where(ch, 0.0, ev["Hb"]))
                      and np.array_equal(Wd, np.where(cw, 0.0, ev["W"])) and np.array_equal(Wb, np.where(cw, 0.0, ev["Wb"])))
    eff["second_event_does_exactly_its_rule"] = rules
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    mq = np.zeros(Tq.shape, bool)
    mq[0, 12:16, 12:16] = True
    Vq, rq = Tq.copy(), np.where(mq, -Tq, Tq)
    rq[0, 14, 14] = 0.0
    Pm = {"am": amq, "aval": np.sign(Tq)}
    later = dict(D.SIGNAL_ARMS["never-R"], tau_x=D.T_W + D.C12["tau_x"])     # the run's rule after T_W
    st = sim.new_state(1, mq)
    st["s"][0, 13, 13], st["sgn"][0, 13, 13] = 1.0, -1.0 * np.sign(rq[0, 13, 13])
    sim.sig_targets(later, Vq, rq, Pm, st, False, D.RE_X - 1)
    no_early = "executed" not in st
    st2 = sim.new_state(1, mq)
    st2["s"][0, 13, 13], st2["sgn"][0, 13, 13] = 1.0, -1.0 * np.sign(rq[0, 13, 13])
    g_before = st2["sgn"].copy()
    sim.sig_targets(later, Vq, rq, Pm, st2, False, D.RE_X)
    want = st2["fp"] & ~(np.arange(D.SIDE * D.SIDE).reshape(1, D.SIDE, D.SIDE) == 13 * D.SIDE + 13) & (L5S.vote_sign(rq) != 0)
    eff["re_execution_commits_exactly_the_uncommitted_confident_footprint_at_re_x"] = bool(
        no_early and np.array_equal(st2["executed"], want) and np.array_equal(st2["sgn"][want], L5S.vote_sign(rq)[want])
        and st2["sgn"][0, 13, 13] == g_before[0, 13, 13] and not (st2["sgn"][~st2["fp"]] != 0).any())
    hb, nsteps = D.STRENGTH0, 0
    while hb > 0:
        hb, nsteps = hb + D.ETA_CAL * (-1.0 - hb), nsteps + 1
    eff["bond_crosses_zero_after_ceil_t_star"] = nsteps == math.ceil(D.T_STAR)
    s_, n_ = 1.0, 0
    while s_ * math.exp(-1.0 / D.TAU_LONG) >= D.S_MIN:
        s_, n_ = s_ * math.exp(-1.0 / D.TAU_LONG), n_ + 1
    eff["committed_for_tau_c_updates_its_commitment_included"] = n_ + 1 == math.floor(D.TAU_LONG)
    eff["cut_is_the_exact_quantile"] = abs(NormalDist().cdf(-cut_for(D.C12["rate"])) - D.C12["rate"]) <= 1e-12
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    q8, t1 = {}, D.T_W + 1
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn, arms, reads = D.run_name(*run), list(run[3]), D.run_reads(*run)
                ti = reads.index(t1)
                for i, arm in enumerate(arms):
                    kind, x = arm.split("-")
                    if x == "N":
                        continue
                    j = arms.index(f"{kind}-N") if f"{kind}-N" in arms else arms.index(f"{'never' if kind == 'dial' else 'dial'}-N")
                    if x in ("W", "K", "W0"):
                        q8[f"{uu}/{body}/{blk}/{rn}:{arm} no confident or committed patch cell"] = bool(
                            (e[f"{rn}/conf_in"][ti, i] == 0).all() and (e[f"{rn}/committed_in"][ti, i] == 0).all())
                    q8[f"{uu}/{body}/{blk}/{rn}:{arm} r_out8=N"] = bool(np.array_equal(e[f"{rn}/r_out8"][ti, i], e[f"{rn}/r_out8"][ti, j]))
                    if x in ("R", "R0"):
                        q8[f"{uu}/{body}/{blk}/{rn}:{arm} v_in=N"] = bool(np.array_equal(e[f"{rn}/v_in"][ti, i], e[f"{rn}/v_in"][ti, j]))
    checks["Q8_second_event_case_matched"] = {"pass": bool(q8) and all(q8.values()), "n_items": len(q8),
                                             "failed": [k_ for k_, v in q8.items() if not v][:10]}

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
    pred = FROZEN / "predictions.json"
    if not pred.exists():                       # before the freeze (debug runs): the draft statements, written to the root
        from be010.predict import STATEMENTS
        pred = root / "predictions_draft.json"
        pred.write_text(json.dumps({"status": "DRAFT_NOT_FROZEN", "statements": STATEMENTS}, indent=1) + "\n")
    proc = subprocess.run([sys.executable, "-m", "be010.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be010.tables", "--out", str(out), "--predictions", str(pred)],
                           cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads(pred.read_text())["statements"]] if pred.exists() else []
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and bool(stmts) and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes, "predictions": str(pred)}

    worst4, items4 = 0.0, {}
    for (uu, body, s, z, dl, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu, body)
        rn = D.run_name(s, z, dl)
        k = RUNS[rn][3].index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{rn}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{rn}/W"][k, ci]).max()))
        items4[f"{uu}/{body}/{rn}/{arm}/case{ci}"], worst4 = d, max(worst4, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst4 <= 1e-8, "max_abs_difference": worst4, "items": items4}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_second_event_case_matched", "Q9_resources", "Q10_reader_dry_run"]
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
