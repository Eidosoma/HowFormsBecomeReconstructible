"""Qualification of LR003 on the preflight (engineering) shards; criteria fixed in advance.

python -m lr003.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: the record and body teachers (with and without parity) equal lr002.sim.run on the same conditions, tag and
    draws, bit for bit (body, record and bonds; both bodies; two units, every rate)
Q4  independent replay: per-site loops for the body's local terms, the bond noise, the record's own bond sums, both
    gates (agreement of signs at both ends of a bond; frustration of a bond against the record's values; any frustrated
    bond at either end site), the Hebbian
    learners and the plaquette rule, conjugate gradients for the inhibitor (no FFT), its own noise cut
    (statistics.NormalDist), reproduce four full branches (body, record and bonds) within 1e-8 (bonds exactly)
Q5  aliases exact: without noise the syndrome and site gates never open, both teachers equal record relearning, and
    parity added to the site gate changes nothing; the record and its bonds are the same under both bodies for the
    record teachers (the record never reads the body)
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy: realised flip rates within 4 SE of p_b; on a stripe pattern, one flipped bond opens the syndrome gate on
    exactly that bond and the site gate on exactly the seven bonds touching its two sites, and one site where the body
    disagrees with the record closes the agreement gate on exactly its four bonds
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
from lr002 import design as L2D  # noqa: E402
from lr002 import sim as L2S  # noqa: E402
from lr003 import design as D  # noqa: E402
from lr003 import sim  # noqa: E402
from lr003 import worker as W  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

FROZEN = LANE / "lr003" / "frozen"
WORKERS = 16
Q4_PICKS = (("S4_t1", "li4", "0.003/syndrome", 0), ("LB_t0", "li4", "0.01/site+parity", 1),
            ("F0_t0", "li4", "0.001/site", 2), ("S4_t1", "dw", "0.001/agree", 3))
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
        if cond.source:
            sgn = [[1.0 if float(r[i, j]) > 0 else -1.0 for j in range(n)] for i in range(n)]
            ag = [[(float(V[i, j]) > 0) == (float(r[i, j]) > 0) for j in range(n)] for i in range(n)]
            fr_h = [[H[i][j] * sgn[i][j] * sgn[i][(j + 1) % n] < 0 for j in range(n)] for i in range(n)]
            fr_w = [[Wd[i][j] * sgn[i][j] * sgn[(i + 1) % n][j] < 0 for j in range(n)] for i in range(n)]
            alarm = [[fr_h[i][j] or fr_h[i][j - 1] or fr_w[i][j] or fr_w[i - 1][j] for j in range(n)] for i in range(n)]
            for i in range(n):
                for j in range(n):
                    for E, Es, i2, j2 in ((H, Hs, i, (j + 1) % n), (Wd, Ws, (i + 1) % n, j)):
                        if cond.source == "body":
                            use_v = True
                        elif cond.source == "agree":
                            use_v = ag[i][j] and ag[i2][j2]
                        elif cond.source == "syndrome":
                            use_v = E[i][j] * sgn[i][j] * sgn[i2][j2] < 0
                        elif cond.source == "site":
                            use_v = alarm[i][j] or alarm[i2][j2]
                        else:
                            use_v = False
                        c = float(V[i, j]) * float(V[i2, j2]) if use_v else float(r[i, j]) * float(r[i2, j2]) / 1.44
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


def q3_job(args):
    """The record and body teachers (with and without parity, every rate) against lr002.sim.run, bit for bit."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    reps = ("record", "record+parity", "body", "body+parity")
    c3 = tuple(D.Cond(rt, rep) for rt in D.RATES for rep in reps)
    c2 = tuple(L2D.Cond(rt, rep) for rt in D.RATES for rep in reps)
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    o3 = sim.run(body, c3, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG)
    o2 = L2S.run(body, c2, cases, V0, ema0, R0, th, T, theta, {D.WINDOW}, tag=D.TAG, kc=D.KC, window=D.WINDOW)
    return (unit, body), bool(all(np.array_equal(o3[k], o2[k]) for k in ("V", "r", "H", "W")))


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

    eq = {f"{u_}/{b_}/record_and_body_teachers=lr002.sim.run": ok_ for (u_, b_), ok_ in q3}
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    i_syn, i_site, i_sp, i_rec = (NAMES.index(f"0/{x}") for x in ("syndrome", "site", "site+parity", "record"))
    ok_open = ok_rec = ok_par = True
    for uu in D.UNITS:
        raw, e = rawf(uu), shard(uu)
        for b in D.BODIES:
            ok_open &= bool(all((e[f"{b}/opened"][i] == 0).all() for i in (i_syn, i_site, i_sp)))
            for key in ("V", "r", "H", "W"):
                ok_rec &= bool(np.array_equal(raw[f"{b}/{key}"][i_syn], raw[f"{b}/{key}"][i_rec])
                               and np.array_equal(raw[f"{b}/{key}"][i_site], raw[f"{b}/{key}"][i_rec]))
                ok_par &= bool(np.array_equal(raw[f"{b}/{key}"][i_sp], raw[f"{b}/{key}"][i_site]))
    alias["frustration_gates_closed_without_noise"] = ok_open
    alias["syndrome_and_site=record_relearning_without_noise"] = ok_rec
    alias["parity_inert_on_site_without_noise"] = ok_par
    rec_only = [i for i, c in enumerate(D.CONDS) if c.source == "record"]
    ok = True
    for uu in D.UNITS:
        raw = rawf(uu)
        for key in ("r", "H", "W"):
            ok &= bool(np.array_equal(raw[f"dw/{key}"][rec_only], raw[f"li4/{key}"][rec_only]))
    alias["record_never_reads_the_body"] = ok
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
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]
    Hq, Wq = S1.edges_from(bonds(Tq, True))
    Hw = Hq.copy()
    Hw[0, 5, 9] *= -1
    src = np.array([D.SOURCES["syndrome"]])[:, None, None]
    uh, uw = sim.gates(Hw, Wq, 1.2 * Tq, 1.2 * Tq, src)
    want = np.zeros_like(Hq, bool)
    want[0, 5, 9] = True
    eff["syndrome_gate_opens_on_the_flipped_bond_only"] = bool(np.array_equal(uh, want) and not uw.any())
    uh, uw = sim.gates(Hw, Wq, 1.2 * Tq, 1.2 * Tq, np.array([D.SOURCES["site"]])[:, None, None])
    want_h = np.zeros_like(Hq, bool)
    want_h[0, 5, 8] = want_h[0, 5, 9] = want_h[0, 5, 10] = True
    want_w = np.zeros_like(Wq, bool)
    want_w[0, 4, 9] = want_w[0, 5, 9] = want_w[0, 4, 10] = want_w[0, 5, 10] = True
    eff["site_gate_opens_the_seven_bonds_around_a_flipped_bond"] = bool(np.array_equal(uh, want_h) and np.array_equal(uw, want_w))
    Vq = 1.2 * Tq.copy()
    Vq[0, 7, 12] *= -1
    src = np.array([D.SOURCES["agree"]])[:, None, None]
    uh, uw = sim.gates(Hq, Wq, 1.2 * Tq, Vq, src)
    closed_h = np.zeros_like(Hq, bool)
    closed_h[0, 7, 12] = closed_h[0, 7, 11] = True
    closed_w = np.zeros_like(Wq, bool)
    closed_w[0, 7, 12] = closed_w[0, 6, 12] = True
    eff["agreement_gate_closes_the_four_bonds_of_a_disagreeing_site"] = bool(np.array_equal(~uh, closed_h) and np.array_equal(~uw, closed_w))
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
    proc = subprocess.run([sys.executable, "-m", "lr003.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "lr003.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
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
