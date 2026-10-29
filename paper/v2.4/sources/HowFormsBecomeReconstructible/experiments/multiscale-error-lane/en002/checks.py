"""Qualification of EN002 on the preflight (engineering) shards; criteria fixed in advance.

python -m en002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards and raw states
Q3  engine: with every multiplier 1 the step equals dl001.sim.body bit for bit (dw and li4, with and without the
    record, 300 updates); with alpha = 0 and paid rates (thermal and activity, phi 0.25) it equals en001.sim.body_step
    (open body) bit for bit (300 updates)
Q4  independent replay: per-site loops with their own paid rates, conjugate gradients for the inhibitor (no FFT;
    dl001.checks' solver), their own wound placement and newborn states, reproduce six full branches (starvation and
    recovery) within 1e-8
Q5  aliases exact: every dw branch of one G unit equals a run of en001.sim.body_step with the same multipliers and
    draws; every base-budget branch of one W unit (li4) equals a run of dl001.sim.body; a branch without a record is
    unchanged when given the record
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  efficacy: wounds and records act as declared; every condition's starvation multipliers are its budget's
Q8  the phase switch: a starved branch equals a loop that applies its multipliers for t <= STARVE and 1 afterwards
Q9  resources: forecast development wall <= 12 h on 12 workers with RAM and disk headroom
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

from dl001 import sim as DLS  # noqa: E402
from dl001.checks import screened  # noqa: E402
from en001.sim import body_step as en001_body_step  # noqa: E402
from en002 import design as D  # noqa: E402
from en002 import sim  # noqa: E402
from en002 import worker as W  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from msegrid.core import Stream  # noqa: E402

FROZEN = LANE / "en002" / "frozen"
WORKERS = 12
Q4_PICKS = (("G", "S4_t0", "li4", "B0.1/none", 0), ("G", "F0_t1", "dw", "C0.25/held", 1),
            ("W", "S4_t0", "li4", "C0.1/none/flip8", 2), ("W", "S4_t1", "li2", "B0.5/held/reset8", 3),
            ("G", "S4_t1", "li2", "B0.25/held", 4), ("G", "F0_t0", "li4", "base/none", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def cond_of(panel, name):
    return [c for c in D.PANELS[panel]["conds"] if c.name == name][0]


# Independent per-site implementation -----------------------------------------------------------------------------

def s_patch(case, size):
    a, b = address(D.TAG, *case.key(), "wound", size).integers(0, D.SIDE, 2)
    m = np.zeros((D.SIDE, D.SIDE), bool)
    for x in range(size):
        for y in range(size):
            m[(a + x) % D.SIDE, (b + y) % D.SIDE] = True
    return m


def s_branch(panel, unit, body, cname, ci, block):
    """Replay one branch end to end with the per-site implementation; returns the final V."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    c = cond_of(panel, cname)
    case, n = cases[ci], D.SIDE
    V = V0[ci].copy()
    if c.wound != "sham":
        m = s_patch(case, c.size)
        if c.wound == "flip":
            V = np.where(m, -V, V)
        else:
            nb = D.KILL_SD * address(D.TAG, *case.key(), "newborn", c.size).standard_normal((n, n))
            V = np.where(m, nb, V)
    gain = D.GAIN if c.record == "held" else 0.0
    r = R0[ci] if c.record == "held" else np.zeros((n, n))
    alpha, L = D.BODIES[body]
    thc = th[ci] * theta
    phi = c.budget.phi
    st = Stream(D.TAG, cases, "future", side=n)
    buf = None
    for t in range(D.WINDOW):
        if t % D.CHUNK == 0:
            buf = st.take(D.CHUNK)[:, ci]
        z = buf[t % D.CHUNK]
        starving = t + 1 <= D.STARVE
        md = phi if (starving and c.budget.acct in ("B", "C")) else 1.0
        nbody = phi if (starving and c.budget.acct == "C") else 1.0
        w = screened(V, L) if alpha else None
        new = np.empty_like(V)
        for i in range(n):
            for j in range(n):
                v = float(V[i, j])
                nbm = (float(V[i - 1, j]) + float(V[(i + 1) % n, j]) + float(V[i, j - 1]) + float(V[i, (j + 1) % n])) / 4.0
                drift = v - v * v * v + float(thc[i, j]) + (nbm - v)
                if alpha:
                    drift -= alpha * float(w[i, j])
                vt = min(max(v + 0.2 * md * drift + D.SIGMA * float(z[i, j]) * nbody ** 0.5, -2.0), 2.0)
                new[i, j] = min(max(vt + 0.2 * (gain * md * (float(r[i, j]) - vt)), -2.0), 2.0)
        V = new
    return V


def replay_job(args):
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    return pick, s_branch(*pick, block)


def drive(step, conds, cases, V, E, r, th, starve_multipliers=True):
    """A plain loop over STARVE + RECOVER updates with the given step(V, E, z, mults) -> (V, E)."""
    k = len(cases)
    idx = np.tile(np.arange(k), len(conds))
    st = Stream(D.TAG, cases, "future", side=D.SIDE)
    md, mc, nb = sim.multipliers(conds, k)
    one = np.ones_like(md)
    buf = None
    for t in range(1, D.WINDOW + 1):
        if (t - 1) % D.CHUNK == 0:
            buf = st.take(D.CHUNK)
        mults = (md, mc, nb) if (t <= D.STARVE and starve_multipliers) else (one, one, one)
        V, E = step(V, E, buf[(t - 1) % D.CHUNK][idx], th[idx], mults)
    return V


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

    from concurrent.futures import ProcessPoolExecutor
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS), len(cpus) - 1)))
    q4 = pool.map(replay_job, [(pk, lo, cpus[(i + 1) % len(cpus)]) for i, pk in enumerate(Q4_PICKS)])

    missing = []
    for p, u in D.tasks():
        nc, ns = len(D.PANELS[p]["conds"]), len(D.PANELS[p]["snaps"])
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for body in D.BODIES:
                eps = ["sign", "shift", "spacing"] + (["patch"] if p == "W" else [])
                bad += [f"{body}/{ep}" for ep in eps if e.get(f"{body}/{ep}", np.zeros(0)).shape != (ns, nc, D.NCASE)]
                bad += [f"{body}/{ep}" for ep in ("w_drift", "w_corr") if e.get(f"{body}/{ep}", np.zeros(0)).shape != (nc, D.NCASE)]
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
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    p = replace(NATIVE, sigma=D.SIGMA)
    st = Stream(D.TAG, cases, "q3", side=D.SIDE)
    zs = st.take(300)
    one = np.ones((len(cases), 1, 1))
    for body in ("dw", "li4"):
        alpha, L = D.BODIES[body]
        G = DLS.ghat(D.SIDE, L) if alpha else None
        for gain, r in ((0.2, R0), (0.0, np.zeros_like(R0))):
            g = np.full((len(cases), 1, 1), gain)
            x1, x2 = (V0.copy(), ema0.copy()), (V0.copy(), ema0.copy())
            for z in zs:
                x1 = sim.body(x1[0], x1[1], r, th, z, p, g, alpha, G, one, one, one)[:2]
                x2 = DLS.body(x2[0], x2[1], r, th, z, p, g, alpha, G)[:2]
            eq[f"mult1=dl001.body/{body}/gain{gain}"] = bool(np.array_equal(x1[0], x2[0]) and np.array_equal(x1[1], x2[1]))
    for acct, nmul in (("thermal", 1.0), ("activity", 0.25)):
        m = np.full((len(cases), 1, 1), 0.25)
        nb = np.full((len(cases), 1, 1), nmul)
        x1, x2 = (V0.copy(), ema0.copy()), (V0.copy(), ema0.copy())
        for z in zs:
            x1 = sim.body(x1[0], x1[1], R0, th, z, p, 0.2, 0.0, None, m, m, nb)[:2]
            x2 = en001_body_step(x2[0], x2[1], R0, th, z, p, False, 0.2, m, m, nb)[:2]
        eq[f"alpha0=en001.body_step/{acct}"] = bool(np.array_equal(x1[0], x2[0]) and np.array_equal(x1[1], x2[1]))
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    u = "F0_t1"
    pattern, theta = D.parse_unit(u)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    conds = D.PANELS["G"]["conds"]
    V, E, r, Tb, M = W.branches(conds, cases, V0, ema0, R0, T)
    gain = np.repeat([D.GAIN if c.record == "held" else 0.0 for c in conds], len(cases))[:, None, None]
    pp = replace(NATIVE, sigma=D.SIGMA)
    step = lambda V_, E_, z, thb, mm: tuple(en001_body_step(V_, E_, r, thb, z, pp, False, gain, mm[0], mm[1], mm[2])[:2])
    Vf = drive(step, conds, cases, V, E, r, th * theta)
    alias["G/F0_t1/dw=en001.body_step"] = bool(np.array_equal(Vf.reshape(len(conds), len(cases), D.SIDE, D.SIDE), rawf("G", u)["dw/V"]))
    u = "S4_t1"
    pattern, theta = D.parse_unit(u)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    allw = D.PANELS["W"]["conds"]
    base = [c for c in allw if c.budget.name == "base"]
    V, E, r, Tb, M = W.branches(base, cases, V0, ema0, R0, T)
    gain = np.repeat([D.GAIN if c.record == "held" else 0.0 for c in base], len(cases))[:, None, None]
    alpha, L = D.BODIES["li4"]
    G = DLS.ghat(D.SIDE, L)
    step = lambda V_, E_, z, thb, mm: tuple(DLS.body(V_, E_, r, thb, z, pp, gain, alpha, G)[:2])
    Vf = drive(step, base, cases, V, E, r, th * theta, starve_multipliers=False).reshape(len(base), len(cases), D.SIDE, D.SIDE)
    raw = rawf("W", u)["li4/V"]
    alias["W/S4_t1/li4/base=dl001.body"] = bool(all(np.array_equal(Vf[i], raw[[c.name for c in allw].index(c.name)])
                                                    for i, c in enumerate(base)))
    c1 = [cond_of("W", "B0.25/none/reset8")]
    V, E, r, Tb, M = W.branches(c1, cases, V0, ema0, R0, T)
    o1 = sim.run("li2", c1, V.copy(), E.copy(), r, th * theta, Tb, cases, {300}, M, window=300)
    o2 = sim.run("li2", c1, V.copy(), E.copy(), R0.copy(), th * theta, Tb, cases, {300}, M, window=300)
    alias["W/no_record_ignores_the_record"] = bool(np.array_equal(o1["final"], o2["final"]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for p, u in D.tasks():
        raw, e = rawf(p, u), shard(p, u)
        nc = len(D.PANELS[p]["conds"])
        Tb = np.tile(raw["T"], (nc, 1, 1))
        for body in D.BODIES:
            Vf = raw[f"{body}/V"].reshape(-1, D.SIDE, D.SIDE)
            got = {"sign": sim.sign(Vf, Tb), "shift": sim.best_shift(Vf, Tb), "spacing": sim.spacing(Vf)}
            if p == "W":
                got["patch"] = sim.patch(Vf, Tb, raw["mask"].reshape(-1, D.SIDE, D.SIDE))
            for k, v in got.items():
                if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{body}/{k}"][-1]):
                    bad.append(f"{p}/{u}/{body}/{k}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = []
    cases, V0, ema0, R0, th, T = sim.prepare("S4", lo, "engineering")
    k = len(cases)
    for p in ("G", "W"):
        conds = D.PANELS[p]["conds"]
        V, E, r, Tb, M = W.branches(conds, cases, V0, ema0, R0, T)
        md, mc, nb = sim.multipliers(conds, k)
        for ci, c in enumerate(conds):
            sl = slice(ci * k, (ci + 1) * k)
            want_m = c.budget.phi if c.budget.acct in ("B", "C") else 1.0
            want_n = c.budget.phi if c.budget.acct == "C" else 1.0
            if not (np.all(md[sl] == want_m) and np.all(mc[sl] == want_m) and np.all(nb[sl] == want_n)):
                eff.append(f"{p}/{c.name}/multipliers")
            if not np.array_equal(r[sl], R0 if c.record == "held" else np.zeros_like(R0)):
                eff.append(f"{p}/{c.name}/record")
            if c.wound == "sham":
                if not np.array_equal(V[sl], V0) or M[sl].any():
                    eff.append(f"{p}/{c.name}/sham_changed")
                continue
            m = np.stack([s_patch(cs, c.size) for cs in cases])
            if not np.array_equal(m, M[sl]) or not (m.sum((-2, -1)) == c.size ** 2).all():
                eff.append(f"{p}/{c.name}/mask")
            if not np.array_equal(V[sl][~m], V0[~m]):
                eff.append(f"{p}/{c.name}/outside_changed")
            want = -V0 if c.wound == "flip" else np.stack([D.KILL_SD * address(D.TAG, *cs.key(), "newborn", c.size).standard_normal((D.SIDE, D.SIDE)) for cs in cases])
            if not np.array_equal(V[sl][m], want[m]):
                eff.append(f"{p}/{c.name}/inside")
    checks["Q7_efficacy"] = {"pass": not eff, "failed": eff[:10]}

    sw = {}
    u = "S4_t0"
    pattern, theta = D.parse_unit(u)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
    for cname in ("B0.1/held", "C0.25/none"):
        c = [cond_of("G", cname)]
        V, E, r, Tb, M = W.branches(c, cases, V0, ema0, R0, T)
        gain = np.full((len(cases), 1, 1), D.GAIN if c[0].record == "held" else 0.0)
        alpha, L = D.BODIES["li4"]
        G = DLS.ghat(D.SIDE, L)
        step = lambda V_, E_, z, thb, mm: tuple(sim.body(V_, E_, r, thb, z, pp, gain, alpha, G, mm[0], mm[1], mm[2])[:2])
        Vf = drive(step, c, cases, V, E, r, th * theta)
        sw[cname] = bool(np.array_equal(Vf, rawf("G", u)["li4/V"][[x.name for x in D.PANELS["G"]["conds"]].index(cname)]))
    checks["Q8_phase_switch"] = {"pass": all(sw.values()), "items": sw}

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
    proc = subprocess.run([sys.executable, "-m", "en002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "en002.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_bodies.csv", out / "contrasts_budgets.csv", out / "summary.json", out / "predictions_scored.json",
                out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for (p, u, body, cname, ci), V in q4:
        raw = rawf(p, u)
        kk = [c.name for c in D.PANELS[p]["conds"]].index(cname)
        d = float(np.abs(V - raw[f"{body}/V"][kk, ci]).max())
        items[f"{p}/{u}/{body}/{cname}/case{ci}"], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-8, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_phase_switch", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
