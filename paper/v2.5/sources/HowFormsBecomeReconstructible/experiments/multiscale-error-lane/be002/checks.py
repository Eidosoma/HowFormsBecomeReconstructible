"""Qualification of BE002 on the preflight (engineering) shards; criteria fixed in advance.

python -m be002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: in every run (with and without the signal) the cue arm and BE001's arms (bio-1, bio-1.5, bio-3) equal
    be001.sim.run bit for bit (body, record and bonds; both bodies; two units), from the saved final states
Q4  independent replay: per-site loops for the event (its own patch, anchors and cue damage), the footprint (its own
    square on the torus), the body's local terms (conjugate gradients for the inhibitor, no FFT), bond noise (its own
    cut, statistics.NormalDist), the record's own bond sums, the cue arbiter, the currents, the cable equation solved by
    sparse LU on be001.checks' own matrix (conductances per bond while the signal is on and after it), the trigger with
    its permission, the slow state, the pull and the Hebbian learners reproduce three full branches (dial-local under
    memory damage with the signal, dial-global under cue damage with the signal, permit-local under memory damage with
    the late signal) within 1e-8 (bonds exactly)
Q5  aliases: without the signal dial-local and dial-global equal bio-3 and permit-local equals the cue arm, bit for bit,
    in every unit, body and run; on the saved final currents the sparse LU equals the FFT for uniform conductances
    (lengths 1, 1.5, 3) within 1e-9, and equals be001.sim.cable_cg with the footprint's conductances within 1e-9
Q6  reanalysis: the endpoints at t = 4000 recomputed from the saved final states, the events and the footprints equal the
    saved ones
Q7  efficacy: patches of 16 and 64 cells, footprints of 64 and 144; anchors on exactly a quarter of the cells, cue damage
    on exactly a quarter of them; the junctions touching a footprint of side s closed, s (s + 1) in each direction; the
    signal windows 1-1,000 and 1,001-2,000; a point current's total response is 1/g_l with the footprint's
    conductances; a coherent 4 x 4 disagreement in a signalled footprint triggers dial-local at its centre while bio-3
    and dial-local without the signal trigger nowhere; permit-local commits no cell outside the footprint in any run
Q8  labyrinths: every LB template is balanced (|mean| <= 0.1) with spacing within 20% of 8
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
from be002 import design as D  # noqa: E402
from be002 import sim  # noqa: E402
from be002 import worker as W  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "be002" / "frozen"
WORKERS = 12
REF_ARMS = ("cue", "bio-1", "bio-1.5", "bio-3")
Q4_PICKS = (("S4_t0", "li4", "memory", 4, "sig", "dial-local", 0), ("LB_t1", "dw", "cue", 8, "sig", "dial-global", 1),
            ("F0_t0", "li4", "memory", 4, "late", "permit-local", 2))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, situation, size, signal, arm, ci, block):
    """One signal arm's branch end to end with independent per-site code; returns final V, r, H, W."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    kind = D.SIGNAL_ARMS[arm]["kind"]
    first, last = D.SIGNALS[signal] or (0, -1)
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < size and ((j - b) % n) < size for j in range(n)] for i in range(n)]
    dd, wide = D.SIG["d"], size + 2 * D.SIG["d"]
    fp = [[((i - a + dd) % n) < wide and ((j - b + dd) % n) < wide for j in range(n)] for i in range(n)]
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
    rest = D.SIG["lam_permit"] ** 2 if kind == "permit" else D.SIG["lam_rest"] ** 2
    sig2 = D.SIG["lam_sig"] ** 2
    if kind == "local":
        gh = [[sig2 if (fp[i][j] or fp[i][(j + 1) % n]) else rest for j in range(n)] for i in range(n)]
        gw = [[sig2 if (fp[i][j] or fp[(i + 1) % n][j]) else rest for j in range(n)] for i in range(n)]
        lu_on = splu(cable_matrix(n, gh, gw))
    elif kind == "global":
        lu_on = splu(cable_matrix(n, [[sig2] * n for _ in range(n)], [[sig2] * n for _ in range(n)]))
    else:
        lu_on = None
    lu_off = splu(cable_matrix(n, [[rest] * n for _ in range(n)], [[rest] * n for _ in range(n)]))
    s_ = [[0.0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    decay = math.exp(-1.0 / D.TAU)
    th_arm = D.SIGNAL_ARMS[arm]["theta"]

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    for t in range(D.WINDOW):
        on = first <= t + 1 <= last
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
        v = (lu_on if (on and lu_on is not None) else lu_off).solve(cur.ravel()).reshape(n, n)
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    base = sv[i][j]
                else:
                    base = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                trig = float(v[i, j]) < -th_arm and sr[i][j] != 0
                if kind == "permit":
                    trig = trig and on and fp[i][j]
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
    """The cue arm and BE001's arms in every run against be001.sim.run, bit for bit, from the saved final states."""
    unit, body, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    raw = npz(Path(root) / "raw" / "E" / unit / f"{block}.npz")
    ok, ref = True, {}
    for s, z, sig in D.RUNS:
        if (s, z) not in ref:
            ref[(s, z)] = B1S.run(body, s, z, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG, arms=REF_ARMS)
        o = ref[(s, z)]
        rn = D.run_name(s, z, sig)
        for j, arm in enumerate(REF_ARMS):
            i = D.ARMS.index(arm)
            for x in ("V", "r", "H", "W"):
                want = o[x][j * k:(j + 1) * k]
                got = raw[f"{body}/{rn}/{x}"][i]
                ok &= bool(np.array_equal(got, want.astype(got.dtype)) and (x in ("H", "W") or np.array_equal(got, want)))
    return (unit, body), bool(ok)


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
    q3 = pool.map(q3_job, [(u_, b_, lo, str(root), cpus[(len(Q4_PICKS) + i + 1) % len(cpus)]) for i, (u_, b_) in enumerate(q3_picks)])
    na, nr, ntr = len(D.ARMS), len(D.READS), len(D.TRACE_READS)
    runs = list(D.RUNNAMES)

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
                for (s, z, sig), rn in zip(D.RUNS, runs):
                    key = f"{body}/{rn}"
                    eps = W.ENDS if s == "change" else W.ENDS[:6]
                    bad += [f"{key}/{x}" for x in eps if e.get(f"{key}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                    bad += [f"{key}/{x}" for x in ("opened", "opened_out") if e.get(f"{key}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
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

    eq = {f"{u_}/{b_}/cue,bio-1,bio-1.5,bio-3=be001.sim.run(every run)": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias, worst_fft, worst_cg = {}, 0.0, 0.0
    for uu in D.UNITS:
        raw = rawf(uu)
        for b in D.BODIES:
            for (s, z, sig), rn in zip(D.RUNS, runs):
                if sig:
                    continue
                for arm, al in D.ALIAS.items():
                    i, j = D.ARMS.index(arm), D.ARMS.index(al)
                    alias[f"{uu}/{b}/{rn}/{arm}={al}"] = all(np.array_equal(raw[f"{b}/{rn}/{x}"][i], raw[f"{b}/{rn}/{x}"][j])
                                                            for x in ("V", "r", "H", "W"))
    for uu in D.UNITS[:2]:
        raw = rawf(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        am = L5S.anchor_mask(cases, D.TAG)
        aval = np.where(raw["R0"] > 0, 1.0, -1.0)
        fp = sim.footprint(sim.patch(cases, 4, D.TAG))
        gH, gW = sim.conductances(fp)
        for b in D.BODIES:
            rf = raw[f"{b}/memory4_sig/r"][D.ARMS.index("dial-local")]
            cur = D.KAPPA * np.where(am, aval, 0.0) * L5S.vote_sign(rf)
            for lam in (1.0, 1.5, 3.0):
                g = np.full(cur.shape, lam ** 2)
                v1 = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
                worst_fft = max(worst_fft, float(np.abs(sim.solve(sim.factor(g, g), cur) - v1).max()))
            v_lu = sim.solve(sim.factor(gH, gW), cur)
            v_cg = B1S.cable_cg(cur, gH, gW, np.zeros_like(cur))
            worst_cg = max(worst_cg, float(np.abs(v_lu - v_cg).max()))
    items = {"without_signal_equal_aliases": all(alias.values()), "lu=fft_uniform": worst_fft <= 1e-9,
             "lu=cg_footprint": worst_cg <= 1e-9}
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "items": items, "alias_failures": [k for k, v in alias.items() if not v][:10],
                                  "max_lu_fft": worst_fft, "max_lu_cg": worst_cg}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        T = raw["T"]
        for (s, z, sig), rn in zip(D.RUNS, runs):
            m = sim.patch(cases, z, D.TAG)
            fp = sim.footprint(m)
            tgt = np.where(m, -T, T) if s == "change" else T
            for b in D.BODIES:
                key = f"{b}/{rn}"
                rf, Vf = raw[f"{key}/r"], raw[f"{key}/V"]
                got = {"r_all": S.sign(rf, tgt), "v_all": S.sign(Vf, tgt), "r_in": L5S.inside(rf, tgt, m),
                       "v_in": L5S.inside(Vf, tgt, m), "r_fp": L5S.inside(rf, tgt, fp), "r_out": L5S.inside(rf, tgt, ~fp)}
                if s == "change":
                    got.update(r_in_old=L5S.inside(rf, T, m), v_in_old=L5S.inside(Vf, T, m))
                for x, v in got.items():
                    if not np.array_equal(v, e[f"{key}/{x}"][-1]):
                        bad.append(f"{uu}/{key}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    eff["patch_cells_16_64"] = all(bool((sim.patch(cases, z, D.TAG).sum((-2, -1)) == z * z).all()) for z in (4, 8))
    eff["footprint_cells_64_144"] = all(bool((sim.footprint(sim.patch(cases, z, D.TAG)).sum((-2, -1)) == (z + 4) ** 2).all()) for z in (4, 8))
    am = L5S.anchor_mask(cases, D.TAG)
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // D.DENSITY).all())
    ev = sim.event("cue", 8, cases, V0, ema0, R0, T, D.TAG)
    base = np.where(R0 > 0, 1.0, -1.0)
    eff["cue_damage_on_a_quarter_of_the_anchors"] = bool((((ev["aval"] != base) & am).sum((-2, -1)) == am.sum((-2, -1)) // 4).all())
    closed = True
    for z in (4, 8):
        gH, gW = sim.conductances(sim.footprint(sim.patch(cases, z, D.TAG)))
        s_ = z + 2 * D.SIG["d"]
        closed &= bool(((gH == D.SIG["lam_sig"] ** 2).sum((-2, -1)) == s_ * (s_ + 1)).all()
                       and ((gW == D.SIG["lam_sig"] ** 2).sum((-2, -1)) == s_ * (s_ + 1)).all())
    eff["junctions_touching_the_footprint_closed"] = closed
    eff["signal_windows"] = D.SIGNALS == {"": None, "sig": (1, 1000), "late": (1001, 2000)}
    gH, gW = sim.conductances(sim.footprint(sim.patch(cases, 8, D.TAG)))
    pt = np.zeros((len(cases), D.SIDE, D.SIDE))
    pt[:, 5, 7] = 1.0
    eff["point_response_total_is_1/g_l_with_the_footprint"] = bool(np.abs(sim.solve(sim.factor(gH, gW), pt).sum((-2, -1)) - 1 / D.G_LEAK).max() < 1e-12)
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    av = np.sign(Tq).copy()
    mq = np.zeros(Tq.shape, bool)
    mq[0, 12:16, 12:16] = True
    av[mq] *= -1
    P = {"am": amq, "aval": av}
    st = sim.new_state("dial-local", 1, sim.footprint(mq))
    _, _, (c_on, t_on) = sim.sig_targets("dial-local", Tq.copy(), Tq.copy(), P, st, True)
    st_off = sim.new_state("dial-local", 1, sim.footprint(mq))
    _, _, (c_off, _) = sim.sig_targets("dial-local", Tq.copy(), Tq.copy(), P, st_off, False)
    st3 = {"v": np.zeros(Tq.shape), "s": np.zeros(Tq.shape), "sgn": np.zeros(Tq.shape), "kernel": B1S.cable_kernel(3.0)}
    _, _, (c3, _) = B1S.bio_targets("bio-3", Tq.copy(), Tq.copy(), P, st3, np.zeros(Tq.shape))
    eff["signalled_4x4_triggers_dial-local_not_bio-3_or_unsignalled"] = bool(c_on[0, 13, 13] and t_on[0, 13, 13] == -np.sign(Tq[0, 13, 13])
                                                                              and not c3.any() and not c_off.any())
    ip = D.ARMS.index("permit-local")
    eff["permit-local_commits_nowhere_outside_the_footprint"] = all(
        float(shard(uu, b)[f"{body}/{rn}/opened_out"][ip].max()) == 0.0
        for uu in D.UNITS for b in range(lo, hi) for body in D.BODIES for rn in runs)
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
    proc = subprocess.run([sys.executable, "-m", "be002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be002.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms_dw.csv", "contrasts_arms_li4.csv", "summary_dw.json", "summary_li4.json",
                                  "summary_body_dw.json", "summary_body_li4.json", "traces.json", "predictions_scored.json",
                                  "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, s, z, sig, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu)
        k = D.ARMS.index(arm)
        key = f"{body}/{D.run_name(s, z, sig)}"
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
