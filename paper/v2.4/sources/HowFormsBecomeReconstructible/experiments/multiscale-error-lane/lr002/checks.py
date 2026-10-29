"""Qualification of LR002 on the preflight (engineering) shards; criteria fixed in advance.

python -m lr002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: with no bond noise and no repair, DL002's coarse code and DL002's tag, LR002's run equals dl002.sim.run's
    rel branch bit for bit (body and record, both bodies, two units); LR002's relations update reproduces
    lr001.sim.simulate_E (every rate and repair of LR001's panel E, one unit at side 16) bit for bit
Q4  independent replay: per-site loops for the body's local terms, the bond noise, the record's own bond sums, the
    Hebbian learners and the plaquette rule, conjugate gradients for the inhibitor (no FFT), its own noise cut
    (statistics.NormalDist), reproduce four full branches (body, record and bonds) within 1e-8 (bonds exactly)
Q5  aliases exact: without body relearning the record and its bonds are the same under both bodies (the record never
    reads the body); without noise, parity added to record relearning changes nothing (the taught bonds have no
    frustrated plaquette); without noise and without relearning the taught bonds are kept
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy: realised flip rates within 4 SE of p_b; parity flips an isolated wrong bond back within one update
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
from dl002 import design as D2  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr001 import design as D1  # noqa: E402
from lr001 import sim as S1  # noqa: E402
from lr002 import design as D  # noqa: E402
from lr002 import sim  # noqa: E402
from lr002 import worker as W  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

FROZEN = LANE / "lr002" / "frozen"
WORKERS = 12
Q4_PICKS = (("S4_t0", "li4", "0.003/body+parity", 0), ("LB_t1", "li4", "0.01/body", 1),
            ("F0_t1", "dw", "0.001/record+parity", 2), ("S4_t1", "dw", "0.003/record", 3))
NAMES = [c.name for c in D.CONDS]


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(unit, body, cname, ci, block):
    """One branch end to end with independent per-site code; returns final V, r, H, W."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    cond = D.CONDS[NAMES.index(cname)]
    n = D.SIDE
    V, r, thc, R0c = V0[ci].copy(), R0[ci].copy(), th[ci] * theta, R0[ci]
    s = [[1.0 if R0c[i, j] >= 0 else -1.0 for j in range(n)] for i in range(n)]
    H = [[s[i][j] * s[i][(j + 1) % n] for j in range(n)] for i in range(n)]          # bond (i, j)-(i, j+1)
    Wd = [[s[i][j] * s[(i + 1) % n][j] for j in range(n)] for i in range(n)]         # bond (i, j)-(i+1, j)
    Hs = [[0.8 * H[i][j] for j in range(n)] for i in range(n)]
    Ws = [[0.8 * Wd[i][j] for j in range(n)] for i in range(n)]
    cut = float("inf") if cond.rate <= 0 else NormalDist().inv_cdf(1.0 - cond.rate)
    alpha, L = DL.BODIES[body]
    st, xs, zs = (Stream(D.TAG, cases, x, side=n) for x in ("future", "record-noise", "bond-noise"))
    buf = xbuf = zbuf = None
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK)[:, ci], xs.take(D.CHUNK)[:, ci], zs.take(D.CHUNK)[:, ci]
        z, xi, zb = buf[t % D.CHUNK], xbuf[t % D.CHUNK], zbuf[t % D.CHUNK]
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
                rv = float(r[i, j])
                bs = (Wd[i - 1][j] * float(r[i - 1, j]) + Wd[i][j] * float(r[(i + 1) % n, j])
                      + H[i][j - 1] * float(r[i, j - 1]) + H[i][j] * float(r[i, (j + 1) % n])) / 4.0
                r1[i, j] = min(max(rv + D.EPS * (rv * (1 - (rv / 1.2) ** 2) + D.KR * (bs - rv)) + D.SIGMA_R * float(xi[i, j]), -2.0), 2.0)
        r = r1
        if cond.learn:
            x = V if cond.learn == "body" else r
            for i in range(n):
                for j in range(n):
                    for E, Es, a in ((H, Hs, float(x[i, (j + 1) % n])), (Wd, Ws, float(x[(i + 1) % n, j]))):
                        c = float(x[i, j]) * a
                        if cond.learn == "record":
                            c = c / 1.44
                        Es[i][j] = Es[i][j] + D.ETA * (min(max(c, -1.0), 1.0) - Es[i][j])
                        if Es[i][j] != 0:
                            E[i][j] = 1.0 if Es[i][j] > 0 else -1.0
        if cond.parity:
            F = [[H[i][j] * Wd[i][(j + 1) % n] * H[(i + 1) % n][j] * Wd[i][j] for j in range(n)] for i in range(n)]
            fh = [[F[i][j] < 0 and F[i - 1][j] < 0 for j in range(n)] for i in range(n)]
            fw = [[F[i][j] < 0 and F[i][j - 1] < 0 for j in range(n)] for i in range(n)]
            for i in range(n):
                for j in range(n):
                    if fh[i][j]:
                        H[i][j] = -H[i][j]
                        if Hs[i][j] * H[i][j] < 0:
                            Hs[i][j] = -Hs[i][j]
                    if fw[i][j]:
                        Wd[i][j] = -Wd[i][j]
                        if Ws[i][j] * Wd[i][j] < 0:
                            Ws[i][j] = -Ws[i][j]
    return V, r, np.array(H), np.array(Wd)


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_replay(*pick, block)


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
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS), len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])
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
                bad += [f"{body}/flip_rate"] if e.get(f"{body}/flip_rate", np.zeros(0)).shape != (nc, D.NCASE) else []
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

    eq = {}
    for u in ("S4_t1", "LB_t0"):
        pattern, theta = D.parse_unit(u)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for b in D.BODIES:
            o = sim.run(b, (D.Cond(0.0, "none"),), cases, V0, ema0, R0, th, T, theta, {D2.WINDOW}, tag=D2.TAG, kc=D2.KC,
                        window=D2.WINDOW)
            o2 = S2.run(b, (D2.Rec("rel", "rel", 0.2),), cases, V0, ema0, R0, th, T, theta, "", {D2.WINDOW})
            eq[f"{u}/{b}/=dl002_rel_branch"] = bool(np.array_equal(o["V"], o2["final"]) and np.array_equal(o["r"], o2["r_rel"]))
    cases1 = S1.cases_for(lo, "engineering")
    _, _, _, R01, _, T1 = S1.prepare("F0", lo, "engineering")
    win1 = 1000
    ends1, fin1 = S1.simulate_E(cases1, R01, T1, window=win1, reads=(win1,))
    rename = {"none": "none", "hebb": "record", "parity": "parity", "both": "record+parity"}
    conds1 = [D.Cond(r_, rename[rep]) for r_ in D1.E_RATES for rep in D1.E_REPAIRS]
    k1 = len(cases1)
    idx = np.tile(np.arange(k1), len(conds1))
    P = sim.params(conds1, k1)
    H0, W0 = S1.edges_from(bonds(R01, True))
    H, Wb_ = H0[idx].copy(), W0[idx].copy()
    Hs, Ws = D.STRENGTH0 * H, D.STRENGTH0 * Wb_
    rr = R01[idx].copy()
    xs, zs = Stream(D1.TAG, cases1, "record-noise", "E", side=D1.SIDE), Stream(D1.TAG, cases1, "bond-noise", side=D1.SIDE)
    for t in range(1, win1 + 1):
        i = (t - 1) % 100
        if i == 0:
            xb, zb = xs.take(100), zs.take(100)
        H, Wb_, Hs, Ws, rr = sim.relations(H, Wb_, Hs, Ws, rr, xb[i][idx], zb[i][idx], None, P, 0.0, None)
    nb1 = len(conds1)
    eq["relations=lr001.simulate_E(F0, every rate and repair)"] = bool(
        np.array_equal(rr.reshape(nb1, k1, D1.SIDE, D1.SIDE), fin1["r"]) and np.array_equal(H.reshape(nb1, k1, D1.SIDE, D1.SIDE), fin1["H"])
        and np.array_equal(Wb_.reshape(nb1, k1, D1.SIDE, D1.SIDE), fin1["W"]))
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    rec_only = [i for i, c in enumerate(D.CONDS) if c.learn != "body"]
    ok = True
    for u in D.UNITS:
        raw = rawf(u)
        for key in ("r", "H", "W"):
            ok &= bool(np.array_equal(raw[f"dw/{key}"][rec_only], raw[f"li4/{key}"][rec_only]))
    alias["record_never_reads_the_body"] = ok
    i_none, i_rec, i_par = NAMES.index("0/none"), NAMES.index("0/record"), NAMES.index("0/record+parity")
    ok1 = ok2 = True
    for u in D.UNITS:
        raw = rawf(u)
        H0, W0 = S1.edges_from(bonds(raw["R0"], True))
        for b in D.BODIES:
            for key in ("V", "r", "H", "W"):
                ok1 &= bool(np.array_equal(raw[f"{b}/{key}"][i_par], raw[f"{b}/{key}"][i_rec]))
            ok2 &= bool(np.array_equal(raw[f"{b}/H"][i_none], H0.astype(np.int8)) and np.array_equal(raw[f"{b}/W"][i_none], W0.astype(np.int8)))
    alias["parity_inert_without_noise"] = ok1
    alias["taught_bonds_kept_without_noise_or_learning"] = ok2
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for u in D.UNITS:
        raw, e = rawf(u), shard(u)
        Tb = np.broadcast_to(raw["T"], (nc, *raw["T"].shape))
        H0, W0 = S1.edges_from(bonds(raw["R0"], True))
        for b in D.BODIES:
            Vf, rf = raw[f"{b}/V"], raw[f"{b}/r"]
            Hf, Wf = raw[f"{b}/H"].astype(float), raw[f"{b}/W"].astype(float)
            got = {"sign": S.sign(Vf, Tb), "r_sign": S.sign(rf, Tb), "agree": ((Vf > 0) == (rf > 0)).mean((-2, -1)),
                   "bond_err": S1.bond_err(Hf, Wf, H0[None], W0[None])}
            for key, v in got.items():
                if not np.array_equal(v, e[f"{b}/{key}"][-1]):
                    bad.append(f"{u}/{b}/{key}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    for ci, c in enumerate(D.CONDS):      # one unit: every unit of a case reads the same bond-noise stream
        fr = np.concatenate([shard(D.UNITS[0], b)["dw/flip_rate"][ci] for b in range(lo, hi)])
        nd = D.WINDOW * 2 * D.SIDE * D.SIDE * len(fr)
        se = np.sqrt(max(c.rate * (1 - c.rate), 1e-300) / nd)
        eff[f"flip_rate/{c.name}"] = bool(abs(fr.mean() - c.rate) <= 4 * se) if c.rate > 0 else bool((fr == 0).all())
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]
    Hq, Wq = S1.edges_from(bonds(Tq, True))
    Hw = Hq.copy()
    Hw[0, 5, 9] *= -1
    Pq = sim.params((D.Cond(0.0, "parity"),), 1)
    Hr, Wr, _, _, _ = sim.relations(Hw, Wq.copy(), 0.8 * Hw, 0.8 * Wq, 1.2 * Tq, np.zeros_like(Tq), np.zeros_like(Tq), None, Pq)
    eff["parity_restores_an_isolated_bond"] = bool(np.array_equal(Hr, Hq) and np.array_equal(Wr, Wq))
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    lab = {}
    for blk in range(lo, hi):
        for kind in (0, 1):
            t_ = S2.template("LB", kind, blk)
            lab[f"{blk}/{kind}"] = {"mean": round(float(t_.mean()), 4), "spacing": round(float(S.spacing(t_[None])[0]), 3)}
    checks["Q8_labyrinths"] = {"pass": all(abs(v["mean"]) <= 0.1 and abs(v["spacing"] - 8.0) <= 1.6 for v in lab.values()), "items": lab}

    walls = {}
    for key, t in manifest["tasks"].items():
        p_, u = key.split("/")[:2]
        walls.setdefault((p_, u), []).append(t["wall_s"])
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
    proc = subprocess.run([sys.executable, "-m", "lr002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "lr002.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_sources.csv", out / "contrasts_bodies.csv", out / "summary.json", out / "predictions_scored.json",
                out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (u, body, cname, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(u)
        k = NAMES.index(cname)
        d = max(float(np.abs(Vr - raw[f"{body}/V"][k, ci]).max()), float(np.abs(rr_ - raw[f"{body}/r"][k, ci]).max()),
                float(np.abs(Hr_ - raw[f"{body}/H"][k, ci]).max()), float(np.abs(Wr_ - raw[f"{body}/W"][k, ci]).max()))
        items[f"{u}/{body}/{cname}/case{ci}"], worst = d, max(worst, d)
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
