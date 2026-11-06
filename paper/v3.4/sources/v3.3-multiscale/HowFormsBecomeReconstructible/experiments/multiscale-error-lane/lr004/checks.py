"""Qualification of LR004 on the preflight (engineering) shards; criteria fixed in advance.

python -m lr004.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: the record+parity, body and site teachers equal lr003.sim.run on the same conditions, tag and draws, bit for
    bit (body, record and bonds; both bodies; two units, every rate)
Q4  independent replay: per-site loops for the body's local terms, both records' bond noise and own bond sums, the vote
    and pair rules, the anchors' arbitration (anchored cells drawn by the replay itself) and the Hebbian learners,
    conjugate gradients for the inhibitor (no FFT), its own noise cut (statistics.NormalDist), reproduce four full
    branches (body, first record and its bonds) within 1e-8 (bonds exactly)
Q5  aliases exact: without noise the pair and vote teachers give the same first record and body, bit for bit, and keep
    the taught bonds; without noise anchors at a quarter and at a sixteenth of the cells give the same run; the first
    record and its bonds are the same under both bodies for record+parity (the record never reads the body)
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy: realised flip rates within 4 SE of p_b; anchors cover exactly a quarter and a sixteenth of the cells; on a
    stripe pattern the vote sides with the two agreeing copies whichever they are, the pair rule learns only where the
    records agree, and an anchor decides a disagreement at its cell while the record decides elsewhere
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
from lr003 import design as L3D  # noqa: E402
from lr003 import sim as L3S  # noqa: E402
from lr004 import design as D  # noqa: E402
from lr004 import sim  # noqa: E402
from lr004 import worker as W  # noqa: E402
from mse.native import address  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

FROZEN = LANE / "lr004" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t1", "li4", "0.003/vote", 0), ("F0_t0", "li4", "0.001/vote", 1),
            ("LB_t0", "li4", "0.01/pair", 2), ("S4_t1", "dw", "0.003/anchors4", 3))
NAMES = [c.name for c in D.CONDS]


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, cname, ci, block):
    """One branch of a third-copy teacher end to end with independent per-site code; returns final V, r, H, W of the
    first record."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    cond = D.CONDS[NAMES.index(cname)]
    n = D.SIDE
    V, thc, R0c = V0[ci].copy(), th[ci] * theta, R0[ci]
    s = [[1.0 if R0c[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]

    def taught():
        H = [[s[i][j] * s[i][(j + 1) % n] for j in range(n)] for i in range(n)]
        Wd = [[s[i][j] * s[(i + 1) % n][j] for j in range(n)] for i in range(n)]
        return H, Wd, [[0.8 * H[i][j] for j in range(n)] for i in range(n)], [[0.8 * Wd[i][j] for j in range(n)] for i in range(n)]
    recs = [[R0c.copy(), *taught()]]                     # [r, H, W, Hs, Ws] per record
    if cond.two:
        recs.append([R0c.copy(), *taught()])
    anchored = [[False] * n for _ in range(n)]
    if cond.density:
        perm = address(D.TAG, *cases[ci].key(), "anchors", cond.density).permutation(n * n)
        for q in range(n * n // cond.density):
            anchored[int(perm[q]) // n][int(perm[q]) % n] = True
    cut = float("inf") if cond.rate <= 0 else NormalDist().inv_cdf(1.0 - cond.rate)
    alpha, L = DL.BODIES[body]
    streams = [Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise")]
    if cond.two:
        streams += [Stream(D.TAG, cases, x, "B", side=n) for x in ("record-noise", "bond-noise")]
    bufs = [None] * len(streams)
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            bufs = [st.take(D.CHUNK)[:, ci] for st in streams]
        z = bufs[0][t % D.CHUNK]
        noises = [(bufs[1][t % D.CHUNK], bufs[2][t % D.CHUNK])]
        if cond.two:
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
                new[i, j] = min(max(vt + 0.2 * (D.GAIN * (float(r0[i, j]) - vt)), -2.0), 2.0)
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

        def rel(x, i, j, i2, j2):
            return 1.0 if (float(x[i, j]) > 0) == (float(x[i2, j2]) > 0) else -1.0
        if cond.source == "anchors":
            r, H, Wd, Hs, Ws = recs[0]
            tr = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    sv = 1.0 if float(V[i, j]) > 0 else -1.0
                    sr = 1.0 if float(r[i, j]) > 0 else -1.0
                    tr[i][j] = sv if sv == sr else ((1.0 if R0c[i, j] > 0 else -1.0) if anchored[i][j] else sr)
            for i in range(n):
                for j in range(n):
                    for E, Es, i2, j2 in ((H, Hs, i, (j + 1) % n), (Wd, Ws, (i + 1) % n, j)):
                        x = tr[i][j] * tr[i2][j2]
                        Es[i][j] = Es[i][j] + D.ETA * (min(max(x, -1.0), 1.0) - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        else:                                             # pair and vote
            rA, HA, WA, HsA, WsA = recs[0]
            rB, HB, WB, HsB, WsB = recs[1]
            for i in range(n):
                for j in range(n):
                    for k, (i2, j2) in enumerate(((i, (j + 1) % n), ((i + 1) % n, j))):
                        sV, sA, sB = rel(V, i, j, i2, j2), rel(rA, i, j, i2, j2), rel(rB, i, j, i2, j2)
                        if cond.source == "vote":
                            m, ok = (1.0 if sV + sA + sB > 0 else -1.0), True
                        else:
                            m, ok = sA, sA == sB
                        if not ok:
                            continue
                        for E, Es in ((HA, HsA), (HB, HsB)) if k == 0 else ((WA, WsA), (WB, WsB)):
                            Es[i][j] = Es[i][j] + D.ETA * (m - Es[i][j])
                            if Es[i][j] != 0:
                                E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
    r, H, Wd, _, _ = recs[0]
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


def q3_job(args):
    """The record+parity, body and site teachers (every rate) against lr003.sim.run, bit for bit."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    reps = ("record+parity", "body", "site")
    c4 = tuple(D.Cond(rt, rep) for rt in D.RATES for rep in reps)
    c3 = tuple(L3D.Cond(rt, rep) for rt in D.RATES for rep in reps)
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    o4 = sim.run(body, c4, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG)
    o3 = L3S.run(body, c3, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG)
    return (unit, body), bool(all(np.array_equal(o4[k], o3[k]) for k in ("V", "r", "H", "W")))


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
    nc, nr = len(D.CONDS), len(D.READS)

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
                bad += [f"{body}/{ep}" for ep in ("sign", "r_sign", "agree", "bond_err")
                        if e.get(f"{body}/{ep}", np.zeros(0)).shape != (nr, nc, D.NCASE)]
                bad += [f"{body}/{ep}" for ep in ("flip_rate", "opened") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (nc, D.NCASE)]
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

    eq = {f"{u_}/{b_}/reference_teachers=lr003.sim.run": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    i_pair, i_vote, i_a4, i_a16 = (NAMES.index(f"0/{x}") for x in ("pair", "vote", "anchors4", "anchors16"))
    rec_only = [i for i, c in enumerate(D.CONDS) if c.source == "record"]
    ok_pv = ok_kept = ok_anc = ok_rec = True
    for uu in D.UNITS:
        raw = rawf(uu)
        H0, W0 = S1.edges_from(bonds(raw["R0"], True))
        for b in D.BODIES:
            for key in ("V", "r", "H", "W"):
                ok_pv &= bool(np.array_equal(raw[f"{b}/{key}"][i_pair], raw[f"{b}/{key}"][i_vote]))
                ok_anc &= bool(np.array_equal(raw[f"{b}/{key}"][i_a4], raw[f"{b}/{key}"][i_a16]))
            ok_kept &= bool(np.array_equal(raw[f"{b}/H"][i_vote], H0.astype(np.int8)) and np.array_equal(raw[f"{b}/W"][i_vote], W0.astype(np.int8)))
        for key in ("r", "H", "W"):
            ok_rec &= bool(np.array_equal(raw[f"dw/{key}"][rec_only], raw[f"li4/{key}"][rec_only]))
    alias["pair=vote_without_noise"] = ok_pv
    alias["vote_keeps_the_taught_bonds_without_noise"] = ok_kept
    alias["anchors4=anchors16_without_noise"] = ok_anc
    alias["record_never_reads_the_body"] = ok_rec
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        Tb = np.broadcast_to(raw["T"], (nc, *raw["T"].shape))
        H0, W0 = S1.edges_from(bonds(raw["R0"], True))
        for b in D.BODIES:
            Vf, rf = raw[f"{b}/V"], raw[f"{b}/r"]
            Hf, Wf = raw[f"{b}/H"].astype(float), raw[f"{b}/W"].astype(float)
            got = {"sign": S.sign(Vf, Tb), "r_sign": S.sign(rf, Tb), "agree": ((Vf > 0) == (rf > 0)).mean((-2, -1)),
                   "bond_err": S1.bond_err(Hf, Wf, H0[None], W0[None])}
            for key, v in got.items():
                if not np.array_equal(v, e[f"{b}/{key}"][-1]):
                    bad.append(f"{uu}/{b}/{key}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    for ci, c in enumerate(D.CONDS):      # one unit: every unit of a case reads the same bond-noise stream
        fr = np.concatenate([shard(D.UNITS[0], b)["dw/flip_rate"][ci] for b in range(lo, hi)])
        nd = D.WINDOW * 2 * D.SIDE * D.SIDE * len(fr)
        se = np.sqrt(max(c.rate * (1 - c.rate), 1e-300) / nd)
        eff[f"flip_rate/{c.name}"] = bool(abs(fr.mean() - c.rate) <= 4 * se) if c.rate > 0 else bool((fr == 0).all())
    cs = sim.prepare("S4", lo, "engineering")[0]
    for dens in (4, 16):
        eff[f"anchors_cover_1/{dens}"] = bool((sim.anchors(cs, dens).sum((-2, -1)) == D.SIDE * D.SIDE // dens).all())
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]
    Hq, Wq = S1.edges_from(bonds(Tq, True))
    zero, inf = np.zeros_like(Tq), np.full((1, 1, 1), np.inf)

    def rec(r):
        return Hq.copy(), Wq.copy(), 0.8 * Hq, 0.8 * Wq, r

    def pq(src, two, vote, amask):
        return {"cut": inf, "src": np.array([D.SOURCES[src]])[:, None, None], "par": np.zeros((1, 1, 1), bool),
                "two_idx": np.array([0]) if two else np.array([], int), "cut_two": inf,
                "vote_two": np.full((1 if two else 0, 1, 1), vote), "amask": amask}
    Vf = 1.2 * Tq.copy()
    Vf[0, :, 2] *= -1                                     # a column whose relations differ from the taught ones
    for name, rB in (("body_outvoted", 1.2 * Tq), ("first_record_outvoted", Vf.copy())):
        Ar, Br, _ = sim.relations(rec(1.2 * Tq), rec(rB), zero, zero, zero, zero, Vf, pq("vote", True, True, np.zeros_like(Tq, bool)), np.sign(Tq))
        sVh, sAh, sBh = sim.signs(Vf)[0], sim.signs(Ar[4])[0], sim.signs(Br[4])[0]
        m = np.sign(sVh + sAh + sBh)
        want = sAh if name == "body_outvoted" else sVh
        eff[f"vote_{name}"] = bool(np.array_equal(m, want) and np.array_equal(Ar[2], 0.8 * Hq + D.ETA * (m - 0.8 * Hq))
                                   and not np.array_equal(sVh, sAh))
    Ar, Br, _ = sim.relations(rec(1.2 * Tq), rec(Vf.copy()), zero, zero, zero, zero, 1.2 * Tq, pq("pair", True, False, np.zeros_like(Tq, bool)), np.sign(Tq))
    dis = sim.signs(Ar[4])[0] != sim.signs(Br[4])[0]
    eff["pair_learns_only_where_the_records_agree"] = bool(dis.any() and np.array_equal(Ar[2][dis], (0.8 * Hq)[dis])
                                                           and np.array_equal(Ar[2][~dis], (0.8 * Hq + D.ETA * (Hq - 0.8 * Hq))[~dis]))
    am = np.zeros_like(Tq, bool)
    am[0, 5, 2] = True
    Vd = 1.2 * Tq.copy()
    Vd[0, 5, 2] *= -1
    Vd[0, 9, 2] *= -1                                     # the body disagrees at an anchored and at an unanchored cell
    aval = np.sign(Tq).copy()
    aval[0, 5, 2] *= -1                                   # the anchor sides with the body at its cell
    Ar, _, op = sim.relations(rec(1.2 * Tq), None, zero, zero, None, None, Vd, pq("anchors", False, False, am), aval)
    tq = np.sign(Tq).copy()
    tq[0, 5, 2] *= -1                                     # trusted: the anchor at (5, 2), the record at (9, 2)
    xh = tq * np.roll(tq, -1, -1)
    eff["anchor_decides_at_its_cell_record_elsewhere"] = bool(np.array_equal(Ar[2], 0.8 * Hq + D.ETA * (xh - 0.8 * Hq))
                                                               and float(op[0]) == 1 / (D.SIDE * D.SIDE))
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
    proc = subprocess.run([sys.executable, "-m", "lr004.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "lr004.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_sources.csv", out / "contrasts_bodies.csv", out / "summary.json", out / "predictions_scored.json",
                out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (uu, body, cname, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu)
        k = NAMES.index(cname)
        d = max(float(np.abs(Vr - raw[f"{body}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{body}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{body}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{body}/W"][k, ci]).max()))
        items[f"{uu}/{body}/{cname}/case{ci}"], worst = d, max(worst, d)
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
