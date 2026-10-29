"""Qualification of BE003 on the preflight (engineering) shards; criteria fixed in advance.

python -m be003.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: the arms without the signal (cue, inst-1.5, inst-3, mat-300, mat-1000) in regrow8 and regrow+cue8 equal
    sc002.sim.run's panel W arms bit for bit (body, record, bonds and occupancy; both bodies; both units), and on a full
    sheet the dial equals be002.sim.run's dial-local (a 4 x 4 change with the signal on at updates 1-1,000) within 1e-9
Q4  independent replay: per-site loops for the event (the wound, its patch, the anchors, the cue damage), the body's
    local terms (conjugate gradients for the inhibitor, no FFT), bond noise (its own cut, statistics.NormalDist), the
    record's own bond sums, the cue arbiter, the currents, the wound's divisions (its own direction choice and conflict
    order), the contacts' ages and maturities, the footprint and the signal's conductances (its own dilation), the
    re-specification of the twin patches before update d + 1, the cable equation solved by sparse LU (its own matrix),
    the trigger, the slow state, the pull and the Hebbian learner reproduce three full branches (mat-dial in twin4@300,
    dial in regrow8_late, mat-1000 in regrow+cue8) within 1e-8 (bonds and occupancy exactly)
Q5  aliases: with the signal never on, dial and mat-dial equal inst-3 and mat-300 bit for bit; the late run's signal
    arms run alone equal the same arms run beside every other arm; a junction arm whose threshold cannot be reached
    equals the cue arm bit for bit in a twin run; the conjugate-gradient solve with uniform junctions equals the FFT
    within 1e-9 on the saved final currents
Q6  reanalysis: the endpoints at each run's last read recomputed from the saved final states and the regions equal the
    saved ones
Q7  efficacy: regions (wound 64 cells; young 16, inside the wound, dilated by 2 exactly the wound; twin 16, 10 columns
    from the wound; ring 80); anchors on exactly a quarter of the sites, cue damage on exactly a quarter of them; in a twin
    run the cue flips at exactly the anchors of both patches before update d + 1 and nowhere before; the signal is on for
    exactly 1,000 updates in its window in every run; while it is on the contacts touching the footprint carry
    lam_sig^2 m and the others lam^2 m; every wound refilled (filled >= 0.99) at the first read (t = 250) of the regrow
    runs and the young patch full before the change at d = 300 in every case; a newborn whose contacts are all new and
    whose record disagrees with its cue sits at -kappa / g_l and triggers under maturing junctions and not under inst-3
Q8  the registered static map's population: over the preflight cases (both blocks) the newborns' occupied neighbours
    at their first update are within 0.05 of the static map's shares (1-4 neighbours) and the mean fill time within 15% of its mean
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
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.linalg import splu  # noqa: E402

from be001 import sim as B1S  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from be003 import design as D  # noqa: E402
from be003 import sim  # noqa: E402
from be003 import worker as W  # noqa: E402
from cellpop import core as C  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001.checks import screened  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402
from sc002 import sim as S2  # noqa: E402
from sc002.cable import Cable  # noqa: E402

FROZEN = LANE / "be003" / "frozen"
WORKERS = 12
Q4_PICKS = (("S4_t0", "li4", ("twin", 300, "prompt"), "mat-dial", 0),
            ("F0_t0", "dw", ("regrow", 0, "late"), "dial", 1),
            ("S4_t0", "dw", ("regrow+cue", 0, "prompt"), "mat-1000", 2))
SC002_ARMS = ("cue", "inst-1.5", "inst-3", "mat-300", "mat-1000")


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


def s_replay(unit, body, run, arm, ci, block, window=None):
    """One branch end to end with independent per-site code; returns final V, r, H, W and occupancy."""
    situation, delay, signal = run
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    wound = [[((i - a) % n) < D.WOUND and ((j - b) % n) < D.WOUND for j in range(n)] for i in range(n)]
    o = D.YOUNG_OFFSET
    young = [[o <= ((i - a) % n) < o + D.PATCH and o <= ((j - b) % n) < o + D.PATCH for j in range(n)] for i in range(n)]
    twin = [[young[i][(j - D.TWIN_SHIFT) % n] for j in range(n)] for i in range(n)]
    perm = address(D.TAG, *key, "anchors", D.DENSITY).permutation(n * n)
    cells = sorted(int(q) for q in perm[: n * n // D.DENSITY])
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]
    tgt = [[float(T[ci][i, j]) for j in range(n)] for i in range(n)]
    sg = [[1.0 if R0c[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
    Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
    Hs = [[D.STRENGTH0 * x for x in row] for row in H]
    Ws = [[D.STRENGTH0 * x for x in row] for row in Wd]
    r = R0c.copy()
    occ = [[True] * n for _ in range(n)]
    if situation == "regrow+cue":
        pick = address(D.TAG, *key, "cue-damage").permutation(len(cells))[: len(cells) // 4]
        for p_ in pick:
            q = cells[int(p_)]
            aval[q // n][q % n] *= -1.0
    base = [row[:] for row in (young if situation == "twin" else wound)]
    if situation == "twin":
        base = [[young[i][j] or twin[i][j] for j in range(n)] for i in range(n)]
    d = D.SIG["d"]
    fp = [[any(base[(i + di) % n][(j + dj) % n] for di in range(-d, d + 1) for dj in range(-d, d + 1)) for j in range(n)]
          for i in range(n)]
    first, last = D.on_window(*run)

    def kill(i, j):
        occ[i][j] = False
        V[i, j], r[i, j] = 0.0, 0.0
        for (E, Es, ii, jj) in ((H, Hs, i, j), (H, Hs, i, (j - 1) % n), (Wd, Ws, i, j), (Wd, Ws, (i - 1) % n, j)):
            E[ii][jj], Es[ii][jj] = 0.0, 0.0

    for i in range(n):
        for j in range(n):
            if wound[i][j]:
                kill(i, j)
    cut = NormalDist().inv_cdf(1.0 - D.RATE)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    ustreams = [address(D.TAG, *key, "population", e) for e in ("div", "dir", "die")]
    age = [[math.inf] * n for _ in range(n)]
    ageH = [row[:] for row in age]
    ageW = [row[:] for row in age]
    prm = D.JUNCTIONS.get(arm)
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    def mat(ag):
        if prm["tau_m"] == 0:
            return 1.0
        return 1.0 if ag == math.inf else -math.expm1(-ag / prm["tau_m"])

    for t in range(D.run_window(*run) if window is None else window):
        u_ = t + 1                                         # the update's number
        if situation == "twin" and u_ == delay + 1:
            for i in range(n):
                for j in range(n):
                    if young[i][j] or twin[i][j]:
                        aval[i][j] = -aval[i][j]
                        tgt[i][j] = -tgt[i][j]
        on = first <= u_ <= last
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
            ubufs = [g.random((D.CHUNK, n, n)) for g in ustreams]
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
            closed = prm["signal"] and on

            def g(i, j, i2, j2, ag):
                if not (occ[i][j] and occ[i2][j2]):
                    return 0.0
                full = D.SIG["lam_sig"] ** 2 if (closed and (fp[i][j] or fp[i2][j2])) else prm["lam"] ** 2
                return full * mat(ag)

            gh = [[g(i, j, i, (j + 1) % n, ageH[i][j]) for j in range(n)] for i in range(n)]
            gw = [[g(i, j, (i + 1) % n, j, ageW[i][j]) for j in range(n)] for i in range(n)]
            cur = np.array([[D.KAPPA * ca[i][j] * sr[i][j] for j in range(n)] for i in range(n)])
            v = splu(cable_matrix(n, gh, gw)).solve(cur.ravel()).reshape(n, n)
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base_ = sv[i][j]
                else:
                    base_ = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                if prm is None:
                    tr[i][j] = base_
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
                    tr[i][j] = base_
        for i in range(n):
            for j in range(n):
                for E, Es, x in ((H, Hs, tr[i][j] * tr[i][(j + 1) % n]), (Wd, Ws, tr[i][j] * tr[(i + 1) % n][j])):
                    if x != 0:
                        Es[i][j] = Es[i][j] + D.ETA * (x - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        born = [[False] * n for _ in range(n)]
        ud, uw, _ = (ub[t % D.CHUNK] for ub in ubufs)
        nbr = ((-1, 0), (1, 0), (0, -1), (0, 1))
        choice = {}
        for i in range(n):
            for j in range(n):
                if not occ[i][j] or float(ud[i, j]) >= D.P_REGROW:
                    continue
                empty = [dd for dd, (di, dj) in enumerate(nbr) if not occ[(i + di) % n][(j + dj) % n]]
                if empty:
                    choice[(i, j)] = empty[int(math.floor(float(uw[i, j]) * len(empty)))]
        before = [row[:] for row in occ]
        for dd, (di, dj) in enumerate(nbr):
            for (i, j), c in sorted(choice.items()):
                if c != dd:
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


def q3_job(args):
    """regrow8 and regrow+cue8's arms without the signal against sc002.sim.run's panel W, bit for bit, from the saved
    raw states; and on a full sheet the dial against be002.sim.run's dial-local."""
    unit, body, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    k, ok = len(cases), {}
    for run, rn in zip(D.RUNS, D.RUNNAMES):
        if run[0] == "twin" or run[2] == "late":
            continue
        o = S2.run(body, 0.0, run[0], D.WOUND, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG, arms=SC002_ARMS)
        arms = D.run_arms(*run)
        good = True
        for x in ("V", "r", "H", "W"):
            mine = raw[f"{rn}/{x}"][[arms.index(a) for a in SC002_ARMS]].reshape(len(SC002_ARMS) * k, D.SIDE, D.SIDE)
            good &= bool(np.array_equal(mine, o[x].astype(mine.dtype)))
        good &= bool(np.array_equal(raw[f"{rn}/occ"], o["occ"][:k]))
        ok[f"{unit}/{body}/{rn}"] = good
    if unit == D.UNITS[0]:
        a = sim.run(body, "change", 0, "prompt", cases, V0, ema0, R0, th, T, theta, {1200}, window=1200,
                    arms=("inst-3", "dial"), size=4)
        b = B2S.run(body, "change", 4, "sig", cases, V0, ema0, R0, th, T, theta, {1200}, tag=D.TAG, window=1200,
                    arms=("bio-3", "dial-local"))
        ok[f"{unit}/{body}/full_sheet_dial=be002_dial-local"] = bool(
            max(float(np.abs(a[x] - b[x]).max()) for x in ("V", "r", "H", "W")) <= 1e-9)
    return ok


def q5_job(args):
    """Aliases in short runs: the signal never on; the late run's arms alone and beside the others; an unreachable
    threshold."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, res = len(cases), {}
    o = sim.run(body, "twin", 100, "prompt", cases, V0, ema0, R0, th, T, theta, {400}, window=400, on=(0, -1),
                arms=("inst-3", "mat-300", "dial", "mat-dial"))
    res["signal_off=alias"] = all(np.array_equal(o[x][:k], o[x][2 * k:3 * k]) and np.array_equal(o[x][k:2 * k], o[x][3 * k:])
                                  for x in ("V", "r", "H", "W"))
    a = sim.run(body, "regrow", 0, "late", cases, V0, ema0, R0, th, T, theta, {1100}, window=1100, arms=D.SIGNAL_ARMS)
    b = sim.run(body, "regrow", 0, "late", cases, V0, ema0, R0, th, T, theta, {1100}, window=1100, arms=D.ARMS)
    i0 = D.ARMS.index(D.SIGNAL_ARMS[0])
    res["late_arms_alone=beside_others"] = all(np.array_equal(a[x], b[x][i0 * k:(i0 + 2) * k]) for x in ("V", "r", "H", "W"))
    saved = D.THETA
    try:
        D.THETA = 1e300
        c = sim.run(body, "twin", 0, "prompt", cases, V0, ema0, R0, th, T, theta, {400}, window=400,
                    arms=("cue", "inst-3", "mat-1000", "mat-dial"))
        res["unreachable_threshold=cue_arm"] = bool(
            all(np.array_equal(c[x][:k], c[x][j * k:(j + 1) * k]) for x in ("V", "r", "H", "W") for j in (1, 2, 3))
            and float(c["opened"].sum()) == 0.0)
    finally:
        D.THETA = saved
    return res


def q7_q8_population(blocks):
    """Change timing, signal timing and conductances in a short twin run; newborns' neighbours and fill times in every
    preflight case (S4 and F0 share the population streams' addresses per case)."""
    out, nb, fl = {}, [], []
    for block in blocks:
        o, n_, f_ = q7_q8_block(block)
        for k, v in o.items():
            out[k] = out.get(k, True) and v
        nb.append(n_)
        fl.append(f_)
    return out, np.concatenate(nb), np.concatenate(fl)


def q7_q8_block(block):
    out = {}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", block, "engineering")
    k = len(cases)
    reg = sim.regions(cases, D.TAG)
    am = L5S.anchor_mask(cases, D.TAG)
    base = np.where(R0 > 0, 1.0, -1.0)
    log = {"flip_ok": True, "on": [], "g_ok": True, "nbrs": [], "fill": np.full(k, -1), "young_full_300": None}

    def observe(t, st, states, ageH, ageW, born, is_on, aval, fp):
        flipped = (aval != base) & am
        want = (am & (reg["young"] | reg["twin"])) if t >= 301 else np.zeros_like(am)
        log["flip_ok"] &= bool(np.array_equal(flipped, want))
        log["on"].append(bool(is_on))
        occ = st["occ"][:k]
        if born.any():
            cnt = sum(C.at(occ, d).astype(int) for d in range(4))
            log["nbrs"].extend(cnt[born].tolist())
        full = occ[reg["in"]].reshape(k, -1).all(-1)
        log["fill"] = np.where((log["fill"] < 0) & full, t, log["fill"])
        if t == 300:
            log["young_full_300"] = bool(occ[reg["young"]].all())
        if t in (150, 350, 1300, 1301):
            tH, tW = C.touching(fp)
            gH, gW = sim.conductance("mat-dial", ageH, ageW, occ, (tH, tW) if is_on else None)
            ch, cw = C.contacts(occ)
            m = S2.maturity(ageH, 300.0)
            want_h = np.where(ch, np.where(tH & is_on, 1.0, 9.0) * m, 0.0)
            log["g_ok"] &= bool(np.array_equal(gH, want_h))

    sim.run("dw", "twin", 300, "prompt", cases, V0, ema0, R0, th, T, 0.0, {1400}, window=1400, arms=("cue",), observe=observe)
    on = np.array(log["on"])
    out["change_flips_exactly_the_patches_anchors_from_d+1"] = log["flip_ok"]
    out["signal_on_exactly_d+1_to_d+1000"] = bool(on[300:1300].all() and not on[:300].any() and not on[1300:].any())
    out["signal_conductances_lam_sig2_m_on_touching_contacts"] = log["g_ok"]
    out["young_patch_full_before_the_change_at_300"] = bool(log["young_full_300"])
    return out, np.array(log["nbrs"]), log["fill"]


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
    q3_picks = [(u_, b_) for u_ in D.UNITS for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks) + 2, len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, str(root), cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, (u_, b_) in enumerate(q3_picks)])
    q5 = pool.submit(q5_job, ("S4_t0", "li4", lo, cpus[(len(Q4_PICKS) + len(q3_picks) + 1) % len(cpus)]))

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
                na, nr = len(D.run_arms(*run)), len(D.run_reads(*run))
                ntr = D.run_window(*run) // D.TRACE
                eps = W.ENDS if run[0] == "twin" else tuple(x for x in W.ENDS if not x.endswith("_old"))
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in ("opened", "opened_out") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/trace_{x}" for x in sim.TRACED if e.get(f"{rn}/trace_{x}", np.zeros(0)).shape != (ntr, na, D.NCASE)]
            missing += [f"{body}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[-1]
    W.run_task(body, u, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for part in q3:
        eq.update(part)
    checks["Q3_engine"] = {"pass": bool(eq) and all(eq.values()), "items": eq}

    alias = dict(q5.result())
    worst = 0.0
    for body, uu in D.tasks():
        raw = rawf(body, uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        aval = np.where(raw["R0"] > 0, 1.0, -1.0)
        cab = Cable(len(cases))
        arms = D.run_arms(*D.RUNS[0])
        for arm in ("inst-1", "inst-1.5", "inst-3"):
            lam = D.JUNCTIONS[arm]["lam"]
            rf = raw[f"{D.RUNNAMES[0]}/r"][arms.index(arm)]
            cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
            v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
            gU = np.full(cur.shape, lam ** 2)
            v2 = cab.solve(cur, gU, gU, np.zeros_like(cur))[0]
            worst = max(worst, float(np.abs(v1 - v2).max()))
    alias["fft=cg_uniform"] = worst <= 1e-9
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias, "max_solver_difference": worst}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(body, uu), shard(body, uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        reg = sim.regions(cases, D.TAG)
        T = raw["T"]
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            tgt = np.where(reg["young"] | reg["twin"], -T, T) if run[0] == "twin" else T
            rf, Vf, occ = raw[f"{rn}/r"], raw[f"{rn}/V"], raw[f"{rn}/occ"]
            got = {"r_all": S2.agree(rf, tgt, occ), "filled": np.broadcast_to((reg["in"] & occ).sum((-2, -1)) / 64.0, rf.shape[:2])}
            for x in sim.REGIONS:
                got[f"r_{x}"] = S2.agree(rf, tgt, reg[x] & occ)
            for x in ("in", "young", "twin"):
                got[f"v_{x}"] = S2.agree(Vf, tgt, reg[x] & occ)
            if run[0] == "twin":
                got["r_young_old"] = S2.agree(rf, T, reg["young"] & occ)
                got["r_twin_old"] = S2.agree(rf, T, reg["twin"] & occ)
            for x, v in got.items():
                if not np.array_equal(v, e[f"{rn}/{x}"][-1]):
                    bad.append(f"{body}/{uu}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    reg = sim.regions(cases, D.TAG)
    eff["regions_64_16_16_80"] = all(bool((reg[x].sum((-2, -1)) == z).all()) for x, z in (("in", 64), ("young", 16), ("twin", 16), ("ring", 80)))
    eff["young_inside_the_wound_and_its_footprint_the_wound"] = bool((reg["young"] <= reg["in"]).all()
                                                                    and np.array_equal(B2S.footprint(reg["young"], 2), reg["in"]))
    eff["twin_10_columns_from_the_wound"] = bool(not (reg["twin"] & B2S.footprint(reg["in"], 9)).any())
    am = L5S.anchor_mask(cases, D.TAG)
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // D.DENSITY).all())
    ev = S2.event("regrow+cue", 8, cases, V0, ema0, R0, T, D.TAG)
    basev = np.where(R0 > 0, 1.0, -1.0)
    eff["cue_damage_on_a_quarter_of_the_anchors"] = bool((((ev["aval"] != basev) & am).sum((-2, -1)) == am.sum((-2, -1)) // 4).all())
    pop, nbrs, fill = q7_q8_population(blocks)
    eff.update(pop)
    sig = {}
    for body, uu in D.tasks():
        meta = json.loads(str(np.load(root / "shards" / body / uu / f"{lo}.npz")["__meta__"]))
        sig.update({f"{body}/{uu}/{rn}": n_ for rn, n_ in meta["signal_updates"].items()})
    eff["signal_on_for_1000_updates_in_every_run"] = all(v == D.SIG["duration"] for v in sig.values())
    filled = min(float(shard(b_, u_)[f"{rn}/filled"][0].min()) for b_, u_ in D.tasks() for run, rn in zip(D.RUNS, D.RUNNAMES)
                 if run[0] != "twin")
    eff["wounds_refilled_by_t250"] = filled >= 0.99
    ages = np.full((1, D.SIDE, D.SIDE), np.inf)
    ages[0, 10, 10] = 0.0
    aH, aW = S2.contact_ages(ages)
    full = np.ones(ages.shape, bool)
    rec, ca = np.ones(ages.shape), np.zeros(ages.shape)
    ca[0, ::2, ::2] = 1.0
    ca[0, 10, 10] = -1.0
    newborn = {}
    for arm in ("mat-300", "inst-3"):
        gH, gW = sim.conductance(arm, aH, aW, full)
        st = {"v": np.zeros(ages.shape), "s": np.zeros(ages.shape), "sgn": np.zeros(ages.shape),
              "kernel": B1S.cable_kernel(D.JUNCTIONS[arm]["lam"]), "cable": Cable(1)}
        _, _, (cm, _) = sim.detect(arm, rec, rec, ca, gH, gW, full, st)
        newborn[arm] = (bool(cm[0, 10, 10]), int(cm.sum()), float(st["v"][0, 10, 10]))
    eff["isolated_newborn_triggers_alone"] = newborn["mat-300"][:2] == (True, 1) and abs(newborn["mat-300"][2] + D.KAPPA / D.G_LEAK) < 1e-9
    eff["instant_junctions_outvote_it"] = newborn["inst-3"][1] == 0
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff, "min_filled_t250": filled}

    static = json.loads((FROZEN / "static_map.json").read_text())
    shares = {str(c): float((nbrs == c).mean()) for c in range(1, 5)}
    q8 = {f"neighbours_{c}": {"preflight": round(shares[str(c)], 4), "static": static["newborn_neighbours"][str(c)],
                              "pass": abs(shares[str(c)] - static["newborn_neighbours"][str(c)]) <= 0.05} for c in range(1, 5)}
    q8["fill_time"] = {"preflight": round(float(fill.mean()), 1), "static": static["fill_time"]["mean"],
                       "pass": abs(float(fill.mean()) / static["fill_time"]["mean"] - 1.0) <= 0.15}
    checks["Q8_static_population"] = {"pass": all(v["pass"] for v in q8.values()), "items": q8, "newborns": int(len(nbrs))}

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
    proc = subprocess.run([sys.executable, "-m", "be003.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be003.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, run, arm, ci), (Vr, rr_, Hr_, Wr_, occr) in q4:
        raw = rawf(body, uu)
        k = D.run_arms(*run).index(arm)
        key = D.run_name(*run)
        d_ = max(float(np.abs(Vr - raw[f"{key}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{key}/r"][k, ci]).max()),
                 float(np.abs(Hr_ - raw[f"{key}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{key}/W"][k, ci]).max()),
                 float(np.abs(occr.astype(int) - raw[f"{key}/occ"][ci].astype(int)).max()))
        items[f"{uu}/{body}/{key}/{arm}/case{ci}"], worst = d_, max(worst, d_)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_static_population", "Q9_resources", "Q10_reader_dry_run"]
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
