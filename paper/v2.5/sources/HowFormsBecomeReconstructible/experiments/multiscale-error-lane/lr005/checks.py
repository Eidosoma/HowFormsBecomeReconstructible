"""Qualification of LR005 on the preflight (engineering) shards; criteria fixed in advance.

python -m lr005.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: with no event at gain 0.2, the record+parity and body arms equal lr004.sim.run's record+parity and body
    teachers at p_b = 1e-3 bit for bit (body, record and bonds; both bodies; two units)
Q4  independent replay: per-site loops for the event (its own patch, anchors, cue damage and kill), the body's local
    terms (conjugate gradients for the inhibitor, no FFT), bond noise (its own cut, statistics.NormalDist), the record's
    own bond sums, the confident votes, the vote2r, vote3 and community rules (the zone counted cell by cell, the latch,
    the pull) and the Hebbian learners reproduce three full branches within 1e-8 (bonds exactly)
Q5  aliases exact: under cue damage the arms that never read the cue (record+parity, body, vote2r) equal the run without
    an event; the record of record+parity is the same with and without body damage, and at both read gains (the record
    never reads the body)
Q6  reanalysis: the endpoints at t = 4000 recomputed from the saved final states and the events equal the saved ones
Q7  efficacy: the patch is 8 x 8; anchors cover exactly a quarter of the cells and cue damage flips exactly a quarter of
    them; memory damage flips the record exactly in the patch and leaves no frustrated bond; shared damage zeroes the
    record in the patch, loses exactly the bonds between two dead cells and the anchors there; change flips exactly the
    patch's anchors; on stripes a coherent 8 x 8 disagreement opens a community zone and one corrupted anchor opens
    none; vote3 breaks a tie toward the record; a value below VMIN casts no vote
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
from lr001 import sim as S1  # noqa: E402
from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from lr005 import design as D  # noqa: E402
from lr005 import sim  # noqa: E402
from lr005 import worker as W  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

FROZEN = LANE / "lr005" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t0", "li4", 0.2, "change", "community-s", 0), ("LB_t1", "dw", 0.05, "cue", "vote3", 1),
            ("F0_t0", "li4", 0.2, "shared", "vote2r", 2))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, gain, situation, arm, ci, block):
    """One branch end to end with independent per-site code; returns final V, r, H, W of the first record."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    n, key = D.SIDE, cases[ci].key()
    V, thc, R0c = V0[ci].astype(float).copy(), th[ci] * theta, R0[ci]
    a, b = address(D.TAG, *key, "patch").integers(0, n, 2)
    patch = [[((i - a) % n) < D.PATCH and ((j - b) % n) < D.PATCH for j in range(n)] for i in range(n)]
    perm = address(D.TAG, *key, "anchors", D.DENSITY).permutation(n * n)
    cells = [int(q) for q in perm[: n * n // D.DENSITY]]
    anch = [[False] * n for _ in range(n)]
    for q in cells:
        anch[q // n][q % n] = True
    aval = [[1.0 if R0c[i, j] > 0 else -1.0 for j in range(n)] for i in range(n)]

    def new_record(rv):
        sg = [[1.0 if rv[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
        H = [[sg[i][j] * sg[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        Wd = [[sg[i][j] * sg[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        return [rv.copy(), H, Wd, [[0.8 * x for x in row] for row in H], [[0.8 * x for x in row] for row in Wd]]
    recs = [new_record(R0c)]
    if arm == "vote2r":
        recs.append(new_record(R0c))
    if situation == "body":
        V = np.where(np.array(patch), -V, V)
    elif situation == "memory":
        recs[0] = new_record(np.where(np.array(patch), -R0c, R0c))
    elif situation == "shared":
        nb = D.KILL_SD * address(D.TAG, *key, "newborn").standard_normal((n, n))
        for rec in recs:
            r_, H, Wd, Hs, Ws = rec
            for i in range(n):
                for j in range(n):
                    if patch[i][j]:
                        V[i, j], r_[i, j] = nb[i, j], 0.0
                        if patch[i][(j + 1) % n]:
                            H[i][j] = Hs[i][j] = 0.0
                        if patch[(i + 1) % n][j]:
                            Wd[i][j] = Ws[i][j] = 0.0
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    anch[i][j] = False
    elif situation == "cue":
        pick = address(D.TAG, *key, "cue-damage").permutation(len(cells))[: len(cells) // 4]
        flat = sorted(cells)                               # anchors in flat order, as np.flatnonzero lists them
        for p_ in pick:
            q = flat[int(p_)]
            aval[q // n][q % n] *= -1.0
    elif situation == "change":
        for i in range(n):
            for j in range(n):
                if patch[i][j]:
                    aval[i][j] *= -1.0
    q_, hold = D.COMMUNITY.get(arm, (0.0, 0))
    age = [[0] * n for _ in range(n)]
    sgn = [[0.0] * n for _ in range(n)]
    cut = NormalDist().inv_cdf(1.0 - D.RATE)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    if arm == "vote2r":
        streams += [Stream(D.TAG, cases, x, "B", side=n) for x in ("record-noise", "bond-noise")]

    def vs(x):
        return 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)

    def learn(E, Es, i, j, x):
        if x == 0:
            return
        Es[i][j] = Es[i][j] + D.ETA * (x - Es[i][j])
        if Es[i][j] != 0:
            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0

    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
        z = bufs[0][t % D.CHUNK]
        noises = [(bufs[1][t % D.CHUNK], bufs[2][t % D.CHUNK])]
        if arm == "vote2r":
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
                new[i, j] = min(max(vt + 0.2 * (gain * (float(r0[i, j]) - vt)), -2.0), 2.0)
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
        r, H, Wd, Hs, Ws = recs[0]
        sv = [[vs(float(V[i, j])) for j in range(n)] for i in range(n)]
        sr = [[vs(float(r[i, j])) for j in range(n)] for i in range(n)]
        if arm == "vote2r":
            rB, HB, WB, HsB, WsB = recs[1]
            sb = [[vs(float(rB[i, j])) for j in range(n)] for i in range(n)]
            for i in range(n):
                for j in range(n):
                    for k, (i2, j2) in enumerate(((i, (j + 1) % n), ((i + 1) % n, j))):
                        tot = sv[i][j] * sv[i2][j2] + sr[i][j] * sr[i2][j2] + sb[i][j] * sb[i2][j2]
                        m = 1.0 if tot > 0 else (-1.0 if tot < 0 else 0.0)
                        for E, Es in (((H, Hs), (HB, HsB)) if k == 0 else ((Wd, Ws), (WB, WsB))):
                            learn(E, Es, i, j, m)
            continue
        ca = [[aval[i][j] if anch[i][j] else 0.0 for j in range(n)] for i in range(n)]
        tr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if arm == "vote3":
                    tot = sv[i][j] + sr[i][j] + ca[i][j]
                    tr[i][j] = (1.0 if tot > 0 else -1.0) if tot != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
                elif sv[i][j] == sr[i][j] and sv[i][j] != 0:
                    tr[i][j] = sv[i][j]
                else:
                    tr[i][j] = ca[i][j] if ca[i][j] != 0 else (sr[i][j] if sr[i][j] != 0 else sv[i][j])
        if arm.startswith("community"):
            rho = D.RHO
            lv_ = [[1 if ca[i][j] != 0 and sr[i][j] != 0 else 0 for j in range(n)] for i in range(n)]
            ds_ = [[1 if lv_[i][j] and ca[i][j] != sr[i][j] else 0 for j in range(n)] for i in range(n)]
            rl = [[sum(lv_[i][(j + dj) % n] for dj in range(-rho, rho + 1)) for j in range(n)] for i in range(n)]
            rd = [[sum(ds_[i][(j + dj) % n] for dj in range(-rho, rho + 1)) for j in range(n)] for i in range(n)]
            for i in range(n):
                for j in range(n):
                    live = sum(rl[(i + di) % n][j] for di in range(-rho, rho + 1))
                    dis = sum(rd[(i + di) % n][j] for di in range(-rho, rho + 1))
                    zone = live >= D.MIN_ANCHORS and dis >= q_ * live and sr[i][j] != 0
                    if zone and age[i][j] == 0:
                        sgn[i][j] = -sr[i][j]
                    age[i][j] = hold if zone else max(age[i][j] - 1, 0)
                    if age[i][j] > 0:
                        tr[i][j] = sgn[i][j]
                        r[i, j] = float(r[i, j]) + D.EPS * D.PULL * (sgn[i][j] * 1.2 - float(r[i, j]))
        for i in range(n):
            for j in range(n):
                learn(H, Hs, i, j, tr[i][j] * tr[i][(j + 1) % n])
                learn(Wd, Ws, i, j, tr[i][j] * tr[(i + 1) % n][j])
    r, H, Wd, _, _ = recs[0]
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """No event at gain 0.2: the record+parity and body arms against lr004.sim.run, bit for bit."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    o5 = sim.run(body, "none", cases, V0, ema0, R0, th, T, theta, 0.2, {D.WINDOW}, arms=("record+parity", "body"))
    c4 = tuple(L4D.Cond(D.RATE, rep) for rep in ("record+parity", "body"))
    o4 = L4S.run(body, c4, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG)
    return (unit, body), bool(all(np.array_equal(o5[x][:2 * k], o4[x][:2 * k]) for x in ("V", "r", "H", "W")))


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
                for g in D.GAINS:
                    for s in D.SITUATIONS:
                        key = f"{body}/{g:g}/{s}"
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

    eq = {f"{u_}/{b_}/record+parity,body=lr004.sim.run": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {"cue_unread_by_record+parity,body,vote2r": True, "record_never_reads_the_body(body damage)": True,
             "record_never_reads_the_body(gain)": True}
    blind = [D.ARMS.index(x) for x in ("record+parity", "body", "vote2r")]
    i_rp = D.ARMS.index("record+parity")
    for uu in D.UNITS:
        raw = rawf(uu)
        for b in D.BODIES:
            for g in D.GAINS:
                for x in ("V", "r", "H", "W"):
                    alias["cue_unread_by_record+parity,body,vote2r"] &= bool(np.array_equal(
                        raw[f"{b}/{g:g}/cue/{x}"][blind], raw[f"{b}/{g:g}/none/{x}"][blind]))
                for x in ("r", "H", "W"):
                    alias["record_never_reads_the_body(body damage)"] &= bool(np.array_equal(
                        raw[f"{b}/{g:g}/body/{x}"][i_rp], raw[f"{b}/{g:g}/none/{x}"][i_rp]))
            for x in ("r", "H", "W"):
                alias["record_never_reads_the_body(gain)"] &= bool(np.array_equal(
                    raw[f"{b}/{D.GAINS[0]:g}/none/{x}"][i_rp], raw[f"{b}/{D.GAINS[1]:g}/none/{x}"][i_rp]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        pattern, _ = D.parse_unit(uu)
        cases = sim.prepare(pattern, lo, "engineering")[0]
        m = sim.patch(cases)
        T = raw["T"]
        for s in D.SITUATIONS:
            tgt = np.where(m, -T, T) if s == "change" else T
            for b in D.BODIES:
                for g in D.GAINS:
                    key = f"{b}/{g:g}/{s}"
                    rf, Vf = raw[f"{key}/r"], raw[f"{key}/V"]
                    got = {"r_all": S.sign(rf, tgt), "v_all": S.sign(Vf, tgt), "r_in": sim.inside(rf, tgt, m),
                           "v_in": sim.inside(Vf, tgt, m)}
                    for x, v in got.items():
                        if not np.array_equal(v, e[f"{key}/{x}"][-1]):
                            bad.append(f"{uu}/{key}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    pattern = "S4"
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    m, am = sim.patch(cases), sim.anchor_mask(cases)
    eff["patch_is_8x8"] = bool((m.sum((-2, -1)) == D.PATCH ** 2).all())
    eff["anchors_cover_a_quarter"] = bool((am.sum((-2, -1)) == D.SIDE * D.SIDE // D.DENSITY).all())
    ev = {s: sim.event(s, cases, V0, ema0, R0, T) for s in D.SITUATIONS}
    base = np.where(R0 > 0, 1.0, -1.0)
    eff["cue_damage_flips_a_quarter_of_the_anchors"] = bool(
        (((ev["cue"]["aval"] != base) & am).sum((-2, -1)) == am.sum((-2, -1)) // 4).all() and not ((ev["cue"]["aval"] != base) & ~am).any())
    mem = ev["memory"]
    J = S1.halves(mem["H"], mem["W"])
    sg = np.where(mem["r"] >= 0, 1.0, -1.0)
    frus = sum(((Jd * sg * np.roll(sg, sh, ax)) < 0).sum() for Jd, (sh, ax) in zip(J, ((1, -2), (-1, -2), (1, -1), (-1, -1))))
    eff["memory_flips_the_patch_with_no_frustrated_bond"] = bool(np.array_equal(mem["r"], np.where(m, -R0, R0)) and frus == 0)
    sh_ = ev["shared"]
    dh, dw = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
    eff["shared_kills_record_bonds_and_anchors"] = bool((sh_["r"][m] == 0).all() and (sh_["H"][dh] == 0).all() and (sh_["W"][dw] == 0).all()
                                                        and (sh_["H"][~dh] != 0).all() and (sh_["W"][~dw] != 0).all()
                                                        and not (sh_["am"] & m).any() and np.array_equal(sh_["am"], am & ~m))
    eff["change_flips_exactly_the_patch_anchors"] = bool(np.array_equal(ev["change"]["aval"], np.where(m, -base, base)))
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    blockm = np.zeros_like(amq)
    blockm[0, 8:16, 8:16] = True
    for name, flip, want in (("coherent_8x8_opens_a_zone", blockm, True), ("one_corrupted_anchor_opens_none", None, False)):
        av = np.sign(Tq).copy()
        if flip is None:
            av[0, 10, 10] *= -1
        else:
            av = np.where(flip, -av, av)
        P = {"am": amq, "aval": av}
        latch = (np.zeros(Tq.shape, int), np.zeros(Tq.shape))
        _, _, (zone, _) = sim.targets("community-s", Tq.copy(), Tq.copy(), None, P, latch)
        eff[name] = bool(zone[0, 11, 11]) if want else bool(not zone.any())
    tie = sim.targets("vote3", np.array([[[1.2, 1.2]]]), np.array([[[-1.2, -1.2]]]), None,
                      {"am": np.zeros((1, 1, 2), bool), "aval": np.ones((1, 1, 2))})
    eff["vote3_tie_goes_to_the_record"] = bool((tie[0] == 1).all())
    eff["weak_value_casts_no_vote"] = bool(sim.vote_sign(np.array([D.VMIN * 0.99, -D.VMIN * 0.99, D.VMIN])).tolist() == [0.0, 0.0, 1.0])
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
    proc = subprocess.run([sys.executable, "-m", "lr005.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "lr005.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "contrasts_gains.csv", "summary_dw.json", "summary_li4.json",
                                  "traces.json", "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, g, s, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu)
        k = D.ARMS.index(arm)
        key = f"{body}/{g:g}/{s}"
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
