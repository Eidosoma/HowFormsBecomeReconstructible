"""Qualification of DL001 on the preflight (engineering) shards; criteria fixed in advance.

python -m dl001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  engine: with alpha = 0 dl001.sim.body equals br001.sim.body_step (open) bit for bit for 300 updates (sides 16
    and 32, with and without the record); the FFT inhibitor solves (1 - L^2 Lap) w = V to 1e-10 (L = 2, 4, 16)
Q4  independent replay: per-site loops for the local terms, conjugate gradients for the inhibitor (no FFT), their own
    wound placement and newborn states, reproduce six full branches of the run within 1e-8
Q5  aliases exact: every double-well branch of one F unit and one U unit equals a run of br001.sim.body_step bit for
    bit; a gain-0 branch is unchanged when given the record; panel F at t = 2000 equals a 2000-update run
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  theory: grown from newborn noise (theta x0, sigma 0.1, no record, 2000 updates) li2's and li4's spacing is within
    20% of 8 and li16's (64-site sheet) within 20% of 16, the linear theory's wavelengths
Q8  efficacy: wounds cover size^2 sites and act as declared (flip: -V0; reset: the newborn values); panel B starts
    from the newborn sheet; elsewhere the acquired state is unchanged
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
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
from dl001 import design as D  # noqa: E402
from dl001 import sim  # noqa: E402
from dl001 import worker as W  # noqa: E402
from mse.assay import BIRTH_SCALE  # noqa: E402
from mse.native import NATIVE, address, center  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "dl001" / "frozen"
WORKERS = 16
Q4_PICKS = (("F", "S4_s0.1_t0", "li4", "free", 0), ("U", "F0_s0.1_t1", "li2", "g0.05", 1),
            ("W", "S4_s0.3_t0", "li4", "flip8-g0", 2), ("B", "BL_s0.1_t1", "dw", "g0.05", 3),
            ("X", "S8_s0.1_t0_x64", "li16/held", "g0.2", 4), ("U", "S4_s0.3_t1", "dw", "g0.2", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def conds_of(panel, tag):
    if panel == "X":
        return D.COND_X[:1] if tag.endswith("/free") else D.COND_X[1:]
    return D.PANELS[panel]["conds"]


def window_of(panel, tag):
    if panel == "X":
        return D.WINDOW_X0 if tag.endswith("/free") else D.WINDOW_X
    return D.PANELS[panel]["window"]


# Independent per-site implementation -----------------------------------------------------------------------------

def lap(x):
    n = x.shape[0]
    out = -4.0 * x
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out = out + x[[(i + di) % n for i in range(n)]][:, [(j + dj) % n for j in range(n)]]
    return out


def screened(V, L, tol=1e-13):
    """Solve (1 - L^2 Lap) w = V by conjugate gradients (symmetric positive definite), without any FFT."""
    A = lambda x: x - L * L * lap(x)
    w = V.copy()
    res = V - A(w)
    d = res.copy()
    rr = float((res * res).sum())
    for _ in range(5000):
        if rr <= tol * tol * float((V * V).sum()):
            break
        Ad = A(d)
        a = rr / float((d * Ad).sum())
        w, res = w + a * d, res - a * Ad
        rr2 = float((res * res).sum())
        d, rr = res + (rr2 / rr) * d, rr2
    return w


def s_patch(case, size, side):
    a, b = address(D.TAG, *case.key(), "wound", size).integers(0, side, 2)
    m = np.zeros((side, side), bool)
    for x in range(size):
        for y in range(size):
            m[(a + x) % side, (b + y) % side] = True
    return m


def s_branch(panel, unit, tag, cname, ci, block):
    """Replay one branch end to end with the per-site implementation; returns the final V."""
    pattern, sigma, theta, side = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, block, "engineering")
    c = [x for x in conds_of(panel, tag) if x.name == cname][0]
    case = cases[ci]
    if D.PANELS[panel]["start"] == "newborn":
        V = BIRTH_SCALE * center(address(D.TAG, *case.key(), "newborn-sheet").standard_normal((side, side)))
    else:
        V = V0[ci].copy()
    if c.wound != "sham":
        m = s_patch(case, c.size, side)
        if c.wound == "flip":
            V = np.where(m, -V, V)
        else:
            nb = D.KILL_SD * address(D.TAG, *case.key(), "newborn", c.size).standard_normal((side, side))
            V = np.where(m, nb, V)
    r = R0[ci] if c.gain > 0 else np.zeros((side, side))
    alpha, L = D.BODIES[tag.split("/")[0]]
    thc = th[ci] * theta
    st = Stream(D.TAG, cases, "future", side=side)
    buf = None
    for t in range(window_of(panel, tag)):
        if t % D.CHUNK == 0:
            buf = st.take(D.CHUNK)[:, ci]
        z = buf[t % D.CHUNK]
        w = screened(V, L) if alpha else None
        new = np.empty_like(V)
        for i in range(side):
            for j in range(side):
                v = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % side, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % side])) / 4.0
                drift = v - v * v * v + float(thc[i, j]) + (nbm - v)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(v + 0.2 * drift + sigma * float(z[i, j]), -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (c.gain * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
    return V


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_branch(*pick, block)


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

    # Q4 runs in the background on the other CPUs while the cheaper checks proceed
    from concurrent.futures import ProcessPoolExecutor
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS), len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])

    missing = []
    for p, u in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for body in D.PANELS[p]["bodies"]:
                for tag in ([f"{body}/free", f"{body}/held"] if p == "X" else [body]):
                    nc = len(conds_of(p, tag))
                    ns = len(D.SNAPS_X0 if tag.endswith("/free") else D.SNAPS_X) if p == "X" else len(D.PANELS[p]["snaps"])
                    eps = ["sign", "shift", "spacing"] + (["patch"] if p == "W" else [])
                    bad += [f"{tag}/{ep}" for ep in eps if e.get(f"{tag}/{ep}", np.zeros(0)).shape != (ns, nc, D.NCASE)]
                    bad += [f"{tag}/{ep}" for ep in ("qual", "w_corr", "w_drift") if e.get(f"{tag}/{ep}", np.zeros(0)).shape != (nc, D.NCASE)]
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
    for side in (16, 32):
        cases, V0, ema0, R0, th, T = sim.prepare("F0", side, lo, "engineering")
        st = Stream(D.TAG, cases, "q3", side=side)
        for gain, r in ((0.2, R0), (0.0, np.zeros_like(R0))):
            a1, b1 = (V0.copy(), ema0.copy()), (V0.copy(), ema0.copy())
            p = replace(NATIVE, sigma=0.3)
            zs = st.take(300)
            for z in zs:
                a1 = sim.body(a1[0], a1[1], r, th, z, p, gain, 0.0, None)[:2]
                b1 = body_step(b1[0], b1[1], r, th, z, p, False, gain)[:2]
            eq[f"side{side}/gain{gain}"] = bool(np.array_equal(a1[0], b1[0]) and np.array_equal(a1[1], b1[1]))
    worst = 0.0
    g = np.random.default_rng(7)
    for side, L in ((32, 2.0), (32, 4.0), (64, 16.0)):
        V = g.standard_normal((side, side))
        w = sim.inhibit(V, sim.ghat(side, L))
        worst = max(worst, float(np.abs(w - L * L * lap(w) - V).max()))
    eq["inhibitor_residual_le_1e-10"] = worst <= 1e-10
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq, "inhibitor_max_residual": worst}

    alias = {}
    for p, u, tag, window in (("F", "S4_s0.1_t1", "dw", D.WINDOW_F), ("U", "BL_s0.3_t1", "dw", D.WINDOW_U)):
        pattern, sigma, theta, side = D.parse_unit(u)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, lo, "engineering")
        conds = D.PANELS[p]["conds"]
        V, E, r, gain, Tb, M = W._branches(p, conds, cases, V0, ema0, R0, T, side)
        idx = np.tile(np.arange(len(cases)), len(conds))
        st = Stream(D.TAG, cases, "future", side=side)
        pp = replace(NATIVE, sigma=sigma)
        gg = gain.reshape(-1, 1, 1)
        buf = None
        for t in range(window):
            if t % D.CHUNK == 0:
                buf = st.take(D.CHUNK)
            V, E, _ = body_step(V, E, r, (th * theta)[idx], buf[t % D.CHUNK][idx], pp, False, gg)
        alias[f"{p}/{u}/{tag}=br001.body_step"] = bool(np.array_equal(V.reshape(len(conds), len(cases), side, side), rawf(p, u)[f"{tag}/V"]))
    u = "S4_s0.1_t0"
    pattern, sigma, theta, side = D.parse_unit(u)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, lo, "engineering")
    c = [x for x in D.COND_W if x.name == "reset8-g0"]
    V, E, r, gain, Tb, M = W._branches("W", c, cases, V0, ema0, R0, T, side)
    o1 = sim.run("li4", V.copy(), E.copy(), r, gain, th * theta, Tb, cases, sigma, 300, {300}, M)
    o2 = sim.run("li4", V.copy(), E.copy(), np.tile(R0, (1, 1, 1)), gain, th * theta, Tb, cases, sigma, 300, {300}, M)
    alias["W/gain0_ignores_record"] = bool(np.array_equal(o1["final"], o2["final"]))
    u = "F0_s0.3_t0"
    pattern, sigma, theta, side = D.parse_unit(u)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, lo, "engineering")
    o = sim.run("li2", V0.copy(), ema0.copy(), np.zeros_like(R0), np.zeros(len(cases)), th * theta, T, cases, sigma, 2000, {2000})
    alias["F_t2000=2000_update_run"] = bool(np.array_equal(o["sign"][0], shard("F", u)["li2/sign"][1, 0]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for p, u in D.tasks():
        raw, e = rawf(p, u), shard(p, u)
        side = D.parse_unit(u)[3]
        for body in D.PANELS[p]["bodies"]:
            for tag in ([f"{body}/free", f"{body}/held"] if p == "X" else [body]):
                nc = len(conds_of(p, tag))
                Vf = raw[f"{tag}/V"].reshape(-1, side, side)
                Tb = np.tile(raw["T"], (nc, 1, 1))
                got = {"sign": sim.sign(Vf, Tb), "shift": sim.best_shift(Vf, Tb), "spacing": sim.spacing(Vf)}
                if p == "W":
                    got["patch"] = sim.patch(Vf, Tb, raw["mask"].reshape(-1, side, side))
                for k, v in got.items():
                    if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{tag}/{k}"][-1]):
                        bad.append(f"{p}/{u}/{tag}/{k}")
                if not np.array_equal(sim.qual(Vf, Tb).reshape(nc, D.NCASE), e[f"{tag}/qual"]):
                    bad.append(f"{p}/{u}/{tag}/qual")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    theory = {}
    for body, side, want in (("li2", 32, 8.0), ("li4", 32, 8.0), ("li16", 64, 16.0)):
        cases, V0, ema0, R0, th, T = sim.prepare("S4", side, lo, "engineering")
        V = sim.newborn_sheet(cases, side)
        o = sim.run(body, V, V.copy(), np.zeros_like(V), np.zeros(len(cases)), th * 0.0, T, cases, 0.1, 2000, {2000})
        s = float(o["spacing"][0].mean())
        theory[body] = {"spacing": round(s, 3), "pass": bool(abs(s - want) <= 0.2 * want)}
    checks["Q7_theory"] = {"pass": all(v["pass"] for v in theory.values()), "items": theory}

    eff = []
    for p in ("W", "B", "F"):
        u = D.PANELS[p]["units"][0]
        pattern, sigma, theta, side = D.parse_unit(u)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, lo, "engineering")
        if D.PANELS[p]["start"] == "newborn":
            V0 = sim.newborn_sheet(cases, side)
            nbs = np.stack([BIRTH_SCALE * center(address(D.TAG, *c.key(), "newborn-sheet").standard_normal((side, side))) for c in cases])
            if not np.array_equal(V0, nbs):
                eff.append(f"{p}/newborn_sheet")
            ema0 = V0.copy()
        conds = D.PANELS[p]["conds"]
        V, E, r, gain, Tb, M = W._branches(p, conds, cases, V0, ema0, R0, T, side)
        k = len(cases)
        for ci, c in enumerate(conds):
            sl = slice(ci * k, (ci + 1) * k)
            if c.wound == "sham":
                if not np.array_equal(V[sl], V0) or M[sl].any():
                    eff.append(f"{p}/{c.name}/sham_changed")
                continue
            m = np.stack([s_patch(cs, c.size, side) for cs in cases])
            if not np.array_equal(m, M[sl]) or not (m.sum((-2, -1)) == c.size ** 2).all():
                eff.append(f"{p}/{c.name}/mask")
            if not np.array_equal(V[sl][~m], V0[~m]):
                eff.append(f"{p}/{c.name}/outside_changed")
            want = -V0 if c.wound == "flip" else np.stack([D.KILL_SD * address(D.TAG, *cs.key(), "newborn", c.size).standard_normal((side, side)) for cs in cases])
            if not np.array_equal(V[sl][m], want[m]):
                eff.append(f"{p}/{c.name}/inside")
            if not np.array_equal(r[sl], R0 if c.gain > 0 else np.zeros_like(R0)):
                eff.append(f"{p}/{c.name}/record")
    checks["Q8_efficacy"] = {"pass": not eff, "failed": eff[:10]}

    walls = {}
    for key, t in manifest["tasks"].items():
        p, u = key.split("/")[:2]
        walls.setdefault((p, u), []).append(t["wall_s"])
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
    proc = subprocess.run([sys.executable, "-m", "dl001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "dl001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts.csv", out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (p, u, tag, cname, ci), V in q4:
        raw = rawf(p, u)
        k = [c.name for c in conds_of(p, tag)].index(cname)
        d = float(np.abs(V - raw[f"{tag}/V"][k, ci]).max())
        items[f"{p}/{u}/{tag}/{cname}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_theory", "Q8_efficacy", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
