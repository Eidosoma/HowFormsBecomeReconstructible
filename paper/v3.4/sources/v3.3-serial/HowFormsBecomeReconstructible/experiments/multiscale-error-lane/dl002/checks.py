"""Qualification of DL002 on the preflight (engineering) shards; criteria fixed in advance.

python -m dl002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards and raw states
Q3  engine: dl001's body with alpha = 0 equals br001.sim.body_step (open) bit for bit; the relational record's final
    state equals a record-only run of msegrid.record_step on the same draws (the record never reads the body)
Q4  independent replay: per-site loops for the body's local terms and the relational record (own bond sums and block
    means), conjugate gradients for the inhibitor (no FFT), own anchors, wounds and newborn states, reproduce four
    full branches (body and record) within 1e-8
Q5  aliases exact: anchors at every site with gain 0.2 equal the full held record; a record read at gain 0 changes
    nothing; LB kinds 2 and 3 are kinds 0 and 1 reversed
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  labyrinths: every LB template is balanced (|mean| <= 0.1) with spacing within 20% of 8
Q8  efficacy: anchor densities within 3 SE of 1/16 and 1/4; wounds cover 64 sites and act as declared; anchors inside
    a wound are lost, the relational record is wounded with the body, the full held record is kept
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from br001.sim import body_step  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl001.checks import screened  # noqa: E402
from dl002 import design as D  # noqa: E402
from dl002 import sim  # noqa: E402
from dl002 import worker as W  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from msegrid.core import Stream, bonds, bproj, record_step  # noqa: E402

FROZEN = LANE / "dl002" / "frozen"
WORKERS = 16
Q4_PICKS = (("A", "LB_t0.5", "li4", "a16", 0), ("A", "S4_t1", "dw", "rel", 1),
            ("R", "S4_t1_flip", "li4", "rel", 2), ("R", "LB_t0_reset", "dw", "a4", 3))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_replay(panel, unit, body, recname, ci, block):
    """One branch end to end with independent per-site code; returns (final V, final relational record or None)."""
    pattern, theta, wound = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    rec = [r for r in D.PANELS[panel]["records"] if r.name == recname][0]
    case, n = cases[ci], D.SIDE
    V, R0c, thc = V0[ci].copy(), R0[ci], th[ci] * theta
    gain = np.zeros((n, n))
    if rec.kind in ("full", "rel"):
        gain[:] = rec.gain
    elif rec.kind == "anchors":
        u = address(D.TAG, *case.key(), "anchors", rec.density).random((n, n))
        for i in range(n):
            for j in range(n):
                gain[i, j] = rec.gain if u[i, j] < 1.0 / rec.density else 0.0
    r = R0c.copy()
    if wound:
        a, b = address(D.TAG, *case.key(), "wound").integers(0, n, 2)
        inside = [((a + x) % n, (b + y) % n) for x in range(8) for y in range(8)]
        nb = D.KILL_SD * address(D.TAG, *case.key(), "newborn").standard_normal((n, n)) if wound == "reset" else None
        for i, j in inside:
            V[i, j] = -V[i, j] if wound == "flip" else nb[i, j]
            if rec.kind == "anchors":
                gain[i, j] = 0.0
            if rec.kind == "rel":
                r[i, j] = -R0c[i, j] if wound == "flip" else 0.0
    s = np.where(R0c >= 0, 1.0, -1.0)
    Bc = np.zeros((n, n))
    for bi in range(0, n, 4):
        for bj in range(0, n, 4):
            Bc[bi:bi + 4, bj:bj + 4] = sum(float(R0c[bi + x, bj + y]) for x in range(4) for y in range(4)) / 16.0
    alpha, L = DL.BODIES[body]
    st, xs = Stream(D.TAG, cases, "future", side=n), Stream(D.TAG, cases, "record-noise", side=n)
    buf = xbuf = None
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            buf, xbuf = st.take(D.CHUNK)[:, ci], xs.take(D.CHUNK)[:, ci]
        z, xi = buf[t % D.CHUNK], xbuf[t % D.CHUNK]
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
                new[i, j] = min(max(vt + 0.2 * (float(gain[i, j]) * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
        if rec.kind == "rel":
            r1 = np.empty_like(r)
            for i in range(n):
                for j in range(n):
                    rv = float(r[i, j])
                    si = s[i, j]
                    bs = (si * s[i - 1, j] * float(r[i - 1, j]) + si * s[(i + 1) % n, j] * float(r[(i + 1) % n, j])
                          + si * s[i, j - 1] * float(r[i, j - 1]) + si * s[i, (j + 1) % n] * float(r[i, (j + 1) % n])) / 4.0
                    r1[i, j] = rv + D.EPS * (rv * (1 - (rv / 1.2) ** 2) + D.KR * (bs - rv)) + D.SIGMA_R * float(xi[i, j])
            r2 = np.empty_like(r)
            for bi in range(0, n, 4):
                for bj in range(0, n, 4):
                    mean = sum(float(r1[bi + x, bj + y]) for x in range(4) for y in range(4)) / 16.0
                    for x in range(4):
                        for y in range(4):
                            r2[bi + x, bj + y] = min(max(r1[bi + x, bj + y] + D.KC * (Bc[bi + x, bj + y] - mean), -2.0), 2.0)
            r = r2
    return V, (r if rec.kind == "rel" else None)


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
    rawf = lambda p, u, b=lo: npz(root / "raw" / p / u / f"{b}.npz")
    shard = lambda p, u, b=lo: npz(root / "shards" / p / u / f"{b}.npz")
    checks = {}
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS), len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])

    missing = []
    for p, u in D.tasks():
        nr, ns = len(D.PANELS[p]["records"]), len(D.PANELS[p]["snaps"])
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for body in D.BODIES:
                bad += [f"{body}/{ep}" for ep in ("sign", "patch", "shift", "spacing") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (ns, nr, D.NCASE)]
                bad += [f"{body}/{ep}" for ep in ("r_sign", "r_patch") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (ns, D.NCASE)]
                bad += [f"{body}/{ep}" for ep in ("w_corr", "qual") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (nr, D.NCASE)]
            missing += [f"{p}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        u = D.PANELS[p]["units"][0]
        W.run_task(p, u, lo, "engineering", str(serial))
        for kind in ("shards", "raw"):
            x, y = npz(root / kind / p / u / f"{lo}.npz"), npz(serial / kind / p / u / f"{lo}.npz")
            same[f"{kind}/{p}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    g = np.random.default_rng(3)
    V, ema, r, th = (g.standard_normal((4, D.SIDE, D.SIDE)) for _ in range(4))
    a1, b1 = (V.copy(), ema.copy()), (V.copy(), ema.copy())
    p = replace(NATIVE, sigma=0.3)
    for _ in range(100):
        z = g.standard_normal((4, D.SIDE, D.SIDE))
        a1 = S.body(a1[0], a1[1], r, th, z, p, 0.2, 0.0, None)[:2]
        b1 = body_step(b1[0], b1[1], r, th, z, p, False, 0.2)[:2]
    eq["dw_body=br001.body_step"] = bool(np.array_equal(a1[0], b1[0]) and np.array_equal(a1[1], b1[1]))
    for p_, u in (("A", "S4_t1"), ("R", "S4_t1_flip")):
        pattern, theta, wound = D.parse_unit(u)
        cases, V0, ema0, R0, th0, T = sim.prepare(pattern, lo, "engineering")
        m = sim.wound_mask(cases)
        rr = (np.where(m, -R0, R0) if wound == "flip" else R0.copy()) if wound else R0.copy()
        J, B = bonds(R0, True), bproj(R0, 4)
        xs = Stream(D.TAG, cases, "record-noise", side=D.SIDE)
        for t in range(D.WINDOW):
            if t % D.CHUNK == 0:
                xb = xs.take(D.CHUNK)
            rr = record_step(rr, xb[t % D.CHUNK], D.EPS, D.KR, D.SIGMA_R, D.KC, B, J)
        raw = rawf(p_, u)
        eq[f"{p_}/{u}/rel_record=record_only_run"] = bool(all(np.array_equal(rr, raw[f"{b}/r_rel"]) for b in D.BODIES))
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    cases, V0, ema0, R0, th0, T = sim.prepare("LB", lo, "engineering")
    dense = (D.Rec("full", "full", 0.2), D.Rec("a1", "anchors", 0.2, 1), D.Rec("none", "none"))
    o = sim.run("li4", dense, cases, V0, ema0, R0, th0, T, 1.0, "", {300})
    o2 = sim.run("li4", dense[2:], cases, V0, ema0, -R0, th0, T, 1.0, "", {300})   # the inverted record, read at gain 0
    k = len(cases)
    Vf = o["final"].reshape(len(dense), k, D.SIDE, D.SIDE)
    alias["anchors_everywhere=full"] = bool(np.array_equal(Vf[0], Vf[1]))
    alias["gain0_record_changes_nothing"] = bool(np.array_equal(Vf[2], o2["final"]))
    T0 = np.stack([sim.template("LB", kind, lo) for kind in range(4)])
    alias["LB_kinds_2_3_reversed"] = bool(np.array_equal(T0[2], -T0[0]) and np.array_equal(T0[3], -T0[1]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for p_, u in D.tasks():
        raw, e = rawf(p_, u), shard(p_, u)
        pattern, theta, wound = D.parse_unit(u)
        nr = len(D.PANELS[p_]["records"])
        Tb = np.tile(raw["T"], (nr, 1, 1))
        mb = np.tile(raw["mask"], (nr, 1, 1)) if wound else None
        for b in D.BODIES:
            Vf = raw[f"{b}/V"].reshape(-1, D.SIDE, D.SIDE)
            got = {"sign": S.sign(Vf, Tb), "shift": S.best_shift(Vf, Tb), "spacing": S.spacing(Vf)}
            if wound:
                got["patch"] = S.patch(Vf, Tb, mb)
            for key, v in got.items():
                if not np.array_equal(v.reshape(nr, D.NCASE), e[f"{b}/{key}"][-1]):
                    bad.append(f"{p_}/{u}/{b}/{key}")
            if not np.array_equal(S.qual(Vf, Tb).reshape(nr, D.NCASE), e[f"{b}/qual"]):
                bad.append(f"{p_}/{u}/{b}/qual")
            if not np.array_equal(S.sign(raw[f"{b}/r_rel"], raw["T"]), e[f"{b}/r_sign"][-1]):
                bad.append(f"{p_}/{u}/{b}/r_sign")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    lab = {}
    for blk in range(lo, hi):
        for kind in (0, 1):
            t_ = sim.template("LB", kind, blk)
            lab[f"{blk}/{kind}"] = {"mean": round(float(t_.mean()), 4), "spacing": round(float(S.spacing(t_[None])[0]), 3)}
    checks["Q7_labyrinths"] = {"pass": all(abs(v["mean"]) <= 0.1 and abs(v["spacing"] - 8.0) <= 1.6 for v in lab.values()), "items": lab}

    eff = []
    for density in (16, 4):
        frac = float(sim.anchors(cases, density).mean())
        se = np.sqrt((1 / density) * (1 - 1 / density) / (len(cases) * D.SIDE * D.SIDE))
        if abs(frac - 1 / density) > 3 * se:
            eff.append(f"anchors_{density}: {frac:.4f}")
    for wound in ("flip", "reset"):
        recs = D.RECORDS_R
        V, E, r, gain, m = sim.branches(recs, cases, V0, ema0, R0, wound)
        if not (m.sum((-2, -1)) == 64).all():
            eff.append(f"{wound}/mask")
        kk = len(cases)
        for i, rec in enumerate(recs):
            sl = slice(i * kk, (i + 1) * kk)
            want = -V0 if wound == "flip" else sim.newborn_values(cases)
            if not np.array_equal(V[sl][m], want[m]) or not np.array_equal(V[sl][~m], V0[~m]):
                eff.append(f"{wound}/{rec.name}/body")
            if rec.kind == "anchors" and gain[sl][m].any():
                eff.append(f"{wound}/{rec.name}/anchors_inside")
            if rec.kind == "full" and not (gain[sl] == rec.gain).all():
                eff.append(f"{wound}/full_changed")
            if rec.kind == "rel":
                wr = np.where(m, -R0, R0) if wound == "flip" else np.where(m, 0.0, R0)
                if not np.array_equal(r[sl], wr):
                    eff.append(f"{wound}/rel_record")
    checks["Q8_efficacy"] = {"pass": not eff, "failed": eff[:10]}

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
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "dl002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "dl002.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts.csv", out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (p_, u, body, recname, ci), (Vr, rr) in q4:
        raw = rawf(p_, u)
        ri = [r.name for r in D.PANELS[p_]["records"]].index(recname)
        d = float(np.abs(Vr - raw[f"{body}/V"][ri, ci]).max())
        if rr is not None:
            d = max(d, float(np.abs(rr - raw[f"{body}/r_rel"][ci]).max()))
        items[f"{p_}/{u}/{body}/{recname}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_labyrinths", "Q8_efficacy", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
