"""Qualification of DL003 on the preflight (engineering) shards; criteria fixed in advance.

python -m dl003.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint and profile at its declared shape
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards and raw states
Q3  engine: dl001's body with alpha = 0 equals br001.sim.body_step (open) bit for bit; an arm without a front equals a
    plain loop of dl001.sim.body from the same start, gains and draws, bit for bit (the front machinery leaves it alone)
Q4  independent replay: per-site loops for the body's local terms, conjugate gradients for the inhibitor (no FFT), own
    geometry (masks and distances by brute force from the same draws), own front schedule and newborn states,
    reproduce four full branches within 1e-8
Q5  aliases: an arm without positional information ignores the record (record and its inverse give identical runs);
    S4 kinds 2 and 3 are kinds 0 and 1 reversed and kind 1 is kind 0 transposed; every profile on the par and perp maps
    averages to the arm's sign over the sheet (within 1e-12)
Q6  reanalysis: endpoints and profiles recomputed from the saved final states equal the saved ones
Q7  geometry: every mask has 64 cells; the par boundary straddles a wall (its two lines have opposite, constant signs);
    each perp line crosses every stripe (16 cells of each sign); the cluster is one 8 x 8 block; every distance 0-15
    on the par and perp maps covers 64 cells and the cluster's own cells are at distance 0
Q8  efficacy: fronts activate on schedule (at t = 50 one line per 25 updates has reached distance 2, whose cells hold
    exactly their newborn values; cells beyond are exactly 0); gains are G_ANCHOR on the 64 cells and 0 elsewhere,
    G_FULL everywhere for full; panel H starts from the acquired state and panel B from the newborn sheet
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
from dl003 import design as D  # noqa: E402
from dl003 import sim  # noqa: E402
from dl003 import worker as W  # noqa: E402
from mse.assay import BIRTH_SCALE, enrol  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "dl003" / "frozen"
WORKERS = 16
Q4_PICKS = (("H", "S4_t1", "li4", "par", 0), ("B", "S4_t0", "li4", "perp/f100", 1),
            ("B", "S4_t0.5", "dw", "scatter", 2), ("B", "S4_t0.25", "li4", "none/perp-f100", 3))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def arm_of(panel, name):
    return [a for a in D.PANELS[panel]["arms"] if a.name == name][0]


def s_geometry(case):
    """Masks and distance maps of one case by brute force, from the same draws as dl003.sim.geometry."""
    n = D.SIDE
    g = address(D.TAG, *case.key(), "geometry")
    perm = g.permutation(n * n)
    w = int(g.integers(0, n // 4))
    o = int(g.integers(0, n))
    a, b = (int(x) for x in g.integers(0, n, 2))
    masks = {k: np.zeros((n, n), bool) for k in D.GEOMETRIES}
    for q in range(D.N_ANCHOR):
        masks["scatter"][int(perm[q]) // n, int(perm[q]) % n] = True

    def ring(x, lines):
        return min(min(abs(x - L), n - abs(x - L)) for L in lines)

    wall, across = [(4 * w - 1) % n, (4 * w) % n], [o, (o + 1) % n]
    vertical = case.message % 2 == 0
    dist = {k: np.zeros((n, n), int) for k in ("par", "perp", "cluster")}
    rows = [(a + x) % n for x in range(8)]
    cols = [(b + y) % n for y in range(8)]
    for i in range(n):
        for j in range(n):
            if vertical:
                masks["par"][i, j], dist["par"][i, j] = j in wall, ring(j, wall)
                masks["perp"][i, j], dist["perp"][i, j] = i in across, ring(i, across)
            else:
                masks["par"][i, j], dist["par"][i, j] = i in wall, ring(i, wall)
                masks["perp"][i, j], dist["perp"][i, j] = j in across, ring(j, across)
            masks["cluster"][i, j] = i in rows and j in cols
            dist["cluster"][i, j] = max(ring(i, rows), ring(j, cols))
    return masks, dist


def s_replay(panel, unit, body, armname, ci, block):
    """One branch end to end with independent per-site code; returns the final V."""
    theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(block, "engineering")
    arm = arm_of(panel, armname)
    case, n = cases[ci], D.SIDE
    masks, dist = s_geometry(case)
    gain = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if arm.geo == "full":
                gain[i, j] = D.G_FULL
            elif arm.geo in masks and masks[arm.geo][i, j]:
                gain[i, j] = D.G_ANCHOR
    z0 = address(D.TAG, *case.key(), "newborn-sheet").standard_normal((n, n))
    mean = sum(float(z0[i, j]) for i in range(n) for j in range(n)) / (n * n)
    newb = np.array([[BIRTH_SCALE * (float(z0[i, j]) - mean) for j in range(n)] for i in range(n)])
    V = V0[ci].copy() if panel == "H" else newb.copy()
    fd = dist[arm.home] if arm.front else None
    live = np.ones((n, n), bool)
    if fd is not None:
        for i in range(n):
            for j in range(n):
                live[i, j] = fd[i, j] == 0
                if not live[i, j]:
                    V[i, j] = 0.0
    thc, r = th[ci] * theta, R0[ci]
    alpha, L = DL.BODIES[body]
    st = Stream(D.TAG, cases, "future", panel, side=n)
    buf = None
    for t in range(1, D.WINDOW + 1):
        if (t - 1) % D.CHUNK == 0:
            buf = st.take(D.CHUNK)[:, ci]
        z = buf[(t - 1) % D.CHUNK]
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
        if fd is not None:
            for i in range(n):
                for j in range(n):
                    if fd[i, j] * arm.front <= t:
                        if not live[i, j]:
                            new[i, j], live[i, j] = newb[i, j], True
                    else:
                        new[i, j] = 0.0
        V = new
    return V


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
        na, ns = len(D.PANELS[p]["arms"]), len(D.SNAPS)
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for body in D.BODIES:
                bad += [f"{body}/{ep}" for ep in ("sign", "shift", "spacing") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (ns, na, D.NCASE)]
                bad += [f"{body}/{ep}" for ep in ("w_corr", "qual") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{body}/prof_{g}" for g, dm in D.DMAX.items() if e.get(f"{body}/prof_{g}", np.zeros(0)).shape != (na, D.NCASE, dm + 1)]
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
    cases, V0, ema0, R0, th0, T = sim.prepare(lo, "engineering")
    masks, _ = sim.geometry(cases)
    alpha, L = DL.BODIES["li4"]
    G = S.ghat(D.SIDE, L)
    Vp = sim.newborn(cases)
    Ep = Vp.copy()
    gp = D.G_ANCHOR * masks["par"]
    st = Stream(D.TAG, cases, "future", "B", side=D.SIDE)
    pn = replace(NATIVE, sigma=D.SIGMA)
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            buf = st.take(D.CHUNK)
        Vp, Ep = S.body(Vp, Ep, R0, th0 * 0.5, buf[t % D.CHUNK], pn, gp, alpha, G)[:2]
    names = [a_.name for a_ in D.PANELS["B"]["arms"]]
    eq["B/S4_t0.5/li4/par=plain_loop"] = bool(np.array_equal(Vp, rawf("B", "S4_t0.5")["li4/V"][names.index("par")]))
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    none = (D.Arm("none", "none"), D.Arm("none/perp-f100", "none", 100, "perp"))
    o1 = sim.run("li4", none, cases, V0, ema0, R0, th0, T, 1.0, "B", {300}, window=300)
    o2 = sim.run("li4", none, cases, V0, ema0, -R0, th0, T, 1.0, "B", {300}, window=300)
    alias["no_information_ignores_the_record"] = bool(np.array_equal(o1["final"], o2["final"]))
    T0 = np.stack([S.template("S4", kind, D.SIDE, lo) for kind in range(4)])
    alias["S4_kinds"] = bool(np.array_equal(T0[2], -T0[0]) and np.array_equal(T0[3], -T0[1]) and np.array_equal(T0[1], T0[0].T))
    worst = 0.0
    for p_, u in D.tasks():
        e = shard(p_, u)
        for b in D.BODIES:
            for gname in ("par", "perp"):
                worst = max(worst, float(np.abs(e[f"{b}/prof_{gname}"].mean(-1) - e[f"{b}/sign"][-1]).max()))
    alias["profiles_average_to_sign"] = bool(worst <= 1e-12)
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias, "profile_worst": worst}

    bad = []
    for p_, u in D.tasks():
        raw, e = rawf(p_, u), shard(p_, u)
        na = len(D.PANELS[p_]["arms"])
        Tb = np.tile(raw["T"], (na, 1, 1))
        cs = enrol([lo], D.MESSAGES, D.PARENTS, "engineering")
        _, dist = sim.geometry(cs)
        for b in D.BODIES:
            Vf = raw[f"{b}/V"].reshape(-1, D.SIDE, D.SIDE)
            got = {"sign": S.sign(Vf, Tb), "shift": S.best_shift(Vf, Tb), "spacing": S.spacing(Vf)}
            for key, v in got.items():
                if not np.array_equal(v.reshape(na, D.NCASE), e[f"{b}/{key}"][-1]):
                    bad.append(f"{p_}/{u}/{b}/{key}")
            if not np.array_equal(S.qual(Vf, Tb).reshape(na, D.NCASE), e[f"{b}/qual"]):
                bad.append(f"{p_}/{u}/{b}/qual")
            ok = (Vf > 0) == (Tb > 0)
            for gname, dm in D.DMAX.items():
                pr = sim.profile(ok, np.tile(dist[gname], (na, 1, 1)), dm).reshape(na, D.NCASE, -1)
                if not np.array_equal(pr, e[f"{b}/prof_{gname}"]):
                    bad.append(f"{p_}/{u}/{b}/prof_{gname}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    geo = []
    for blk in range(lo, hi):
        cs = enrol([blk], D.MESSAGES, D.PARENTS, "engineering")
        mk, dist = sim.geometry(cs)
        for j, c in enumerate(cs):
            t_ = S.template("S4", c.message, D.SIDE, blk)
            if any(mk[gname][j].sum() != D.N_ANCHOR for gname in D.GEOMETRIES):
                geo.append(f"{blk}/{j}/count")
            vals = t_[mk["par"][j]].reshape(-1)
            lines = [t_[:, x] if c.message % 2 == 0 else t_[x, :] for x in np.unique(np.nonzero(mk["par"][j])[1 if c.message % 2 == 0 else 0])]
            if len(lines) != 2 or any(len(set(l_)) != 1 for l_ in lines) or lines[0][0] == lines[1][0] or set(vals) != {-1.0, 1.0}:
                geo.append(f"{blk}/{j}/par_wall")
            pl = [t_[x, :] if c.message % 2 == 0 else t_[:, x] for x in np.unique(np.nonzero(mk["perp"][j])[0 if c.message % 2 == 0 else 1])]
            if len(pl) != 2 or any((l_ > 0).sum() != D.SIDE // 2 for l_ in pl):
                geo.append(f"{blk}/{j}/perp_crossing")
            rr, cc = np.nonzero(mk["cluster"][j])
            if len(set(rr.tolist())) != 8 or len(set(cc.tolist())) != 8 or not (dist["cluster"][j][mk["cluster"][j]] == 0).all():
                geo.append(f"{blk}/{j}/cluster")
            for gname in ("par", "perp"):
                counts = np.bincount(dist[gname][j].reshape(-1), minlength=16)
                if counts.shape[0] != 16 or not (counts == 2 * D.SIDE).all():
                    geo.append(f"{blk}/{j}/{gname}_distances")
    checks["Q7_geometry"] = {"pass": not geo, "failed": geo[:10]}

    eff = []
    fr = (D.Arm("perp/f25", "perp", 25),)
    o = sim.run("li4", fr, cases, V0, ema0, R0, th0, T, 0.0, "B", {50}, window=50)
    _, dist = sim.geometry(cases)
    dp, nbv = dist["perp"], sim.newborn(cases)
    if not (np.array_equal(o["final"][dp == 2], nbv[dp == 2]) and (o["final"][dp > 2] == 0).all()
            and (o["final_ema"][dp > 2] == 0).all() and (o["final"][dp < 2] != 0).all()):
        eff.append("front_schedule")
    for panel in ("H", "B"):
        arms = D.PANELS[panel]["arms"]
        V, E, gain, fdist, every, mk, _ = sim.branches(arms, cases, V0, ema0, panel)
        kk = len(cases)
        for i, arm in enumerate(arms):
            sl = slice(i * kk, (i + 1) * kk)
            if arm.geo in D.GEOMETRIES:
                if not (np.array_equal(gain[sl] == D.G_ANCHOR, mk[arm.geo]) and (gain[sl][~mk[arm.geo]] == 0).all()):
                    eff.append(f"{panel}/{arm.name}/gain")
            elif arm.geo == "full" and not (gain[sl] == D.G_FULL).all():
                eff.append(f"{panel}/{arm.name}/gain")
            elif arm.geo == "none" and gain[sl].any():
                eff.append(f"{panel}/{arm.name}/gain")
            start = V0 if panel == "H" else sim.newborn(cases)
            if not arm.front and not np.array_equal(V[sl], start):
                eff.append(f"{panel}/{arm.name}/start")
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
    proc = subprocess.run([sys.executable, "-m", "dl003.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "dl003.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts.csv", out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (p_, u, body, armname, ci), Vr in q4:
        names = [a_.name for a_ in D.PANELS[p_]["arms"]]
        d = float(np.abs(Vr - rawf(p_, u)[f"{body}/V"][names.index(armname), ci]).max())
        items[f"{p_}/{u}/{body}/{armname}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_geometry", "Q8_efficacy", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
