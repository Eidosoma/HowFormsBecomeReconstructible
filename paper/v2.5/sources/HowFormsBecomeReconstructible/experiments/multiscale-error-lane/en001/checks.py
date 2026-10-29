"""Qualification of EN001 on the preflight (engineering) shards; criteria fixed in advance.

python -m en001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite (t95, healed and the store's availabilities may be NaN where undefined)
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  equivalence: at the full budget the starvation phase equals br002.sim.simulate bit for bit (consensus, consensus +
    code, relational + code; sham, flip, reset, turnover), and the static record in sham equals mse.engine's hold route
Q4  independent replay: a per-site loop with its own paid body step, bonds, code, kill and relink, turnover, budget
    schedule, allocation and per-cell store reproduces six branches to the end of recovery within 1e-9
Q5  aliases exact: panel G's base equals panel P's base; G's B0.25 equals P's thermal-uniform and G's C0.25 equals P's
    activity-uniform, for the shared arms and regimes
Q6  reanalysis: endpoints recomputed from the saved states and snapshots equal the saved ones
Q7  efficacy: every wound covers its 36 sites; turnover counts lie within 40% of their expectation; the store's
    availability lies in [0, 1] and stays >= 0.95 on average in sham at full supply
Q8  the budget acts: in every panel G regime the record's paid work at a tenth of the budget is below half its full value
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

import operators as fixture  # noqa: E402
from br001.checks import nb  # noqa: E402   (BR001's per-site neighbour mean)
from br002 import design as D2  # noqa: E402
from br002 import sim as S2  # noqa: E402
from en001 import design as D  # noqa: E402
from en001 import sim  # noqa: E402
from en001 import worker as W  # noqa: E402
from mse.assay import enrol, spread  # noqa: E402
from mse.engine import Route, run  # noqa: E402
from mse.native import NATIVE, address, center, thresholds  # noqa: E402

FROZEN = LANE / "en001" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 12
Q4_PICKS = (("G", D.regime("F0", 0.3), "multi", "B0.1", "flip-6x6", 0),
            ("G", D.regime("BL", 0.1), "relcode", "C0.25", "reset-6x6", 1),
            ("P", D.regime("F0", 0.3), "multi", "activity-record", "turnover-0.001", 2),
            ("E", D.regime("BL", 0.1), "multi", "store-thermal0.25", "flip-6x6", 3),
            ("G", D.regime("F0", 0.1), "hold", "A0.5", "sham", 4),
            ("E", D.regime("F0", 0.3), "relcode", "store-activity0.1", "flip-6x6", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_body(V, ema, r, th, z, p, conserved, gain, md, mc, nbody):
    drift = np.empty((16, 16))
    for i in range(16):
        for j in range(16):
            drift[i, j] = V[i, j] - V[i, j] ** 3 + th[i, j] + p.coupling * (nb(V, i, j) - V[i, j])
    paid = md * drift
    noise = (p.sigma * z) * np.sqrt(nbody)
    if conserved:
        Vt = np.clip(V + p.dt * center(paid) + center(noise), -2.0, 2.0)
    else:
        Vt = np.clip(V + p.dt * paid + noise, -2.0, 2.0)
    ema = (1 - p.ema_rate) * ema + p.ema_rate * Vt
    d = (gain * mc) * (r - Vt)
    if conserved:
        d = center(d)
    return np.clip(Vt + p.dt * d, -2.0, 2.0), ema, Vt, drift


def scalar_branch(panel, name, arm_name, budget_name, cond_name, ci, cal):
    """One branch from addresses alone, site by site, to the end of recovery."""
    family, sigma, body = D.parse(name)
    p = replace(NATIVE, sigma=sigma)
    conserved = body == "c"
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    c = cases[ci]
    th = thresholds(address(D.TAG, "theta", BLOCK), replace(p, threshold_spread=spread(D.TAG, BLOCK)))
    T = D.TEMPLATES[family][c.message]
    s0 = sim.prepare(name, [BLOCK], "engineering")[1]          # acquisition is checked by ME002's Q4; reuse it here
    V, ema, R0 = s0.V[ci].copy(), s0.ema[ci].copy(), s0.R[ci].copy()
    arm = D.ARMS[arm_name]
    bud = next(b for b in D.PANELS[panel]["budgets"] if b.name == budget_name)
    cond = next(x for x in D.CONDS if x.name == cond_name)
    mask = np.zeros((16, 16), bool)
    if cond.size:
        a0, b0 = address(D.TAG, *c.key(), "lesion").integers(0, 16, 2)
        for i in range(cond.size):
            for j in range(cond.size):
                mask[(a0 + i) % 16, (b0 + j) % 16] = True
    events = []
    if cond.kind == "turnover":
        g = address(D.TAG, *c.key(), "turnover", f"{cond.rate:g}")
        n = int(g.poisson(cond.rate * D.WINDOW * 256))
        t_, site, val = g.integers(1, D.WINDOW + 1, n), g.integers(0, 256, n), 0.2 * g.standard_normal(n)
        order = np.argsort(t_, kind="stable")
        events = list(zip(t_[order], site[order], val[order]))
    born = D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{cond.size}").standard_normal((16, 16)) if cond.kind == "kill" else None
    Z = address(D.TAG, *c.key(), "future").standard_normal((D.WINDOW, 16, 16))
    XI = address(D.TAG, *c.key(), "record-noise").standard_normal((D.WINDOW, 16, 16))
    sg = np.where(R0 >= 0, 1.0, -1.0)
    J = np.ones((4, 16, 16))
    if arm.rel:
        for i in range(16):
            for j in range(16):
                J[0, i, j] = sg[i, j] * sg[(i - 1) % 16, j]
                J[1, i, j] = sg[i, j] * sg[(i + 1) % 16, j]
                J[2, i, j] = sg[i, j] * sg[i, (j - 1) % 16]
                J[3, i, j] = sg[i, j] * sg[i, (j + 1) % 16]
    v, e, r = V.copy(), ema.copy(), R0.copy()
    B = fixture.block_projection(R0, 4)
    gain = NATIVE.gain
    store = bud.scheme == "store"
    if store:
        cap, supply0 = D.STORE_CAP * cal, D.STORE_HEADROOM * cal
        E = np.full((16, 16), cap)
    ev = 0
    for t in range(1, D.WINDOW + 1):
        if t == 1:
            if cond.kind == "lesion":
                v, r = np.where(mask, -v, v), np.where(mask, -r, r)
            if cond.kind == "kill":
                v, e, r = np.where(mask, born, v), np.where(mask, born, e), np.where(mask, 0.0, r)
                if arm.rel:
                    for i in range(16):
                        for j in range(16):
                            if mask[i, j]:
                                for d, (di, dj) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
                                    if mask[(i + di) % 16, (j + dj) % 16]:
                                        J[d, i, j] = 1.0 if arm.relink else 0.0
        f = bud.phi if t <= D.STARVE else 1.0
        if store:
            x = E / cap
            a = x * (1.0 + D.STORE_K) / (x + D.STORE_K)
            m_body, m_rec = a, a
        else:
            m_body = f if bud.alloc in ("uniform", "record") else 1.0
            m_rec = f if bud.alloc in ("uniform", "body") else 1.0
        md = m_body if bud.paid == "all" else 1.0
        nbody = md if bud.noise == "activity" else 1.0
        nrec = m_rec if bud.noise == "activity" else 1.0
        r_in = r
        v, e, vt, drift = s_body(v, e, r, th, Z[t - 1], p, conserved, gain, md, m_body, nbody)
        wd = np.abs(p.dt * md * drift)
        wc = np.abs(p.dt * (gain * m_body) * (r_in - vt))
        wr = np.zeros((16, 16))
        changed = False
        if arm.eps > 0:
            nr = np.empty((16, 16))
            for i in range(16):
                for j in range(16):
                    nr[i, j] = (J[0, i, j] * r[(i - 1) % 16, j] + J[1, i, j] * r[(i + 1) % 16, j]
                                + J[2, i, j] * r[i, (j - 1) % 16] + J[3, i, j] * r[i, (j + 1) % 16]) / 4.0
            inc = (arm.eps * m_rec) * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (nr - r))
            wr = wr + np.abs(inc)
            r = r + inc + (D.SIGMA_R * XI[t - 1]) * np.sqrt(nrec)
            changed = True
        if arm.kc > 0:
            inc = (arm.kc * m_rec) * (B - fixture.block_projection(r, 4))
            wr = wr + np.abs(inc)
            r = r + inc
            changed = True
        if changed:
            r = np.clip(r, -2.0, 2.0)
        if store:
            E = np.clip(E + f * supply0 - (wd + wc + wr), 0.0, cap)
        while ev < len(events) and events[ev][0] == t:
            _, site, val = events[ev]
            i, j = divmod(int(site), 16)
            v[i, j], e[i, j], r[i, j] = val, val, 0.0
            ev += 1
    return v, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    global BLOCK
    BLOCK = lo
    receipt_path = FROZEN / "qualification_receipt.json" if a.blocks is None else root / "debug_qualification_receipt.json"
    calib = json.loads((FROZEN / "calibration.json").read_text())
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda p, r, b=lo: npz(root / "raw" / p / r / f"{b}.npz")
    shard = lambda p, r, b=lo: npz(root / "shards" / p / r / f"{b}.npz")
    nan_ok = ("t95", "healed", "a_mean", "a_patch", "a_rest")
    checks = {}

    missing = []
    for p, r in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / r / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{r}/{b}")
                continue
            e = npz(path)
            for arm, bud in D.branches(p):
                for ep in D.ENDPOINTS:
                    x = e.get(f"{arm}/{bud.name}/{ep}")
                    if x is None or x.shape != (len(D.CONDS), D.NCASE) or (ep not in nan_ok and not np.isfinite(x).all()):
                        missing.append(f"{p}/{r}/{b}/{arm}/{bud.name}/{ep}")
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        r = D.PANELS[p]["regimes"][0]
        W.run_task(p, r, lo, "engineering", calib, str(serial))
        x, y = npz(root / "shards" / p / r / f"{lo}.npz"), npz(serial / "shards" / p / r / f"{lo}.npz")
        same[f"{p}/{r}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k], equal_nan=True) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    name = D.regime("F0", 0.3)
    cases, s0, th, p, conserved, T = sim.prepare(name, [lo], "engineering")
    k = len(cases)
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    masks = [None if not c.size else sim.patch_masks(cases, c.size) for c in D.CONDS]
    turn = [sim.turnover_events(cases, c.rate, D.WINDOW) if c.kind == "turnover" else None for c in D.CONDS]
    born = [sim.newborn(cases, c.size) if c.kind == "kill" else None for c in D.CONDS]
    c2 = (D2.Cond("sham"), D2.Cond("flip", "lesion", D.WOUND), D2.Cond("reset", "kill", D.WOUND),
          D2.Cond("turn", "turnover", rate=D.TURNOVER))
    raw = rawf("G", name)
    for arm, arm2 in (("self", D2.ARM["R"]["self"]), ("multi", D2.ARM["R"]["multi"]), ("relcode", D2.ARM["R"]["rel+code+relink"])):
        v2, _, r2, _ = S2.simulate(arm2, c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, T, np.ones(k, int),
                                   masks, turn, born)
        eq[f"G/{name}/{arm}/base=br002"] = bool(np.array_equal(raw[f"{arm}/base/V_s"].reshape(-1, 16, 16), v2)
                                               and np.array_equal(raw[f"{arm}/base/R_s"].reshape(-1, 16, 16), r2))
    ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None, capture=None), D.STARVE, p)
    eq[f"G/{name}/hold/base/sham=engine"] = bool(np.array_equal(raw["hold/base/V_s"][0], ref.V))
    checks["Q3_equivalence"] = {"pass": all(eq.values()), "items": eq}

    worst, items = 0.0, {}
    for p_, r_, arm, bud, cond, ci in Q4_PICKS:
        v, rr = scalar_branch(p_, r_, arm, bud, cond, ci, calib["regimes"].get(r_, {}).get("work"))
        rw = rawf(p_, r_)
        kk = [c.name for c in D.CONDS].index(cond)
        d = max(float(np.abs(v - rw[f"{arm}/{bud}/V_r"][kk, ci]).max()), float(np.abs(rr - rw[f"{arm}/{bud}/R_r"][kk, ci]).max()))
        items[f"{p_}/{r_}/{arm}/{bud}/{cond}/case{ci}"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}

    alias = {}
    for r in D.PANELS["P"]["regimes"]:
        g, pp = rawf("G", r), rawf("P", r)
        for arm in D.PANELS["P"]["arms"]:
            for bg, bp in (("base", "base"), ("B0.25", "thermal-uniform"), ("C0.25", "activity-uniform")):
                alias[f"{r}/{arm}/G:{bg}=P:{bp}"] = bool(all(np.array_equal(g[f"{arm}/{bg}/{key}"], pp[f"{arm}/{bp}/{key}"])
                                                             for key in ("V_s", "R_s", "V_r", "R_r")))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": len(alias), "failed": [k for k, v in alias.items() if not v]}

    bad = []
    for p, r in D.tasks():
        rw, e = rawf(p, r), shard(p, r)
        T = rw["targets"]
        m = rw["mask"]                                       # (conds, cases, 16, 16)
        for arm, bud in D.branches(p):
            key = f"{arm}/{bud.name}"
            Vs, Rs, Vr, Rr = (rw[f"{key}/{x}"] for x in ("V_s", "R_s", "V_r", "R_r"))
            got = {"v_qual": sim.qual(Vs, T), "r_sign": sim.sign(Rs, T), "les_r": sim.masked_sign(Rs, T, m),
                   "v_qual_rec": sim.qual(Vr, T), "les_r_rec": sim.masked_sign(Rr, T, m)}
            snap = rw[f"{key}/snap_r"].reshape(-1, D.WINDOW // D.SNAP)
            got["t95"] = sim.t95(snap, m.reshape(-1, 16, 16).any((-2, -1))).reshape(len(D.CONDS), D.NCASE)
            bad += [f"{p}/{r}/{key}/{ep}" for ep, x in got.items() if not np.array_equal(x, e[f"{key}/{ep}"], equal_nan=True)]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    ok7, eff = True, []
    for p, r in D.tasks():
        for b in range(lo, hi):
            x = shard(p, r, b)
            for ci, c in enumerate(D.CONDS):
                if not (x["events/patch_sites"][ci] == c.size ** 2).all():
                    ok7 = False
                    eff.append(f"{p}/{r}/{b}/{c.name}/patch")
                if c.kind == "turnover":
                    exp = c.rate * D.WINDOW * 256
                    if not (np.abs(x["events/turnover_count"][ci] - exp) <= 0.4 * exp).all():
                        ok7 = False
                        eff.append(f"{p}/{r}/{b}/{c.name}/turnover")
            if p == "E":
                for arm, bud in D.branches(p):
                    am = x[f"{arm}/{bud.name}/a_mean"]
                    if not ((am >= 0) & (am <= 1)).all():
                        ok7 = False
                        eff.append(f"{p}/{r}/{b}/{arm}/{bud.name}/a_range")
                    if bud.phi == 1.0 and am[0].mean() < 0.95:
                        ok7 = False
                        eff.append(f"{p}/{r}/{b}/{arm}/{bud.name}/a_full")
    checks["Q7_efficacy"] = {"pass": ok7, "failed": eff[:10]}

    acts = {}
    for r in D.PANELS["G"]["regimes"]:
        x = shard("G", r)
        acts[r] = bool(x["multi/B0.1/w_rec"][0].mean() < 0.5 * x["multi/base/w_rec"][0].mean())
    checks["Q8_budget_acts"] = {"pass": all(acts.values()), "regimes": acts}

    walls = {}
    for key, t in manifest["tasks"].items():
        walls.setdefault(key.split("/")[0], []).append(t["wall_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(walls[p]) * len(D.PANELS[p]["regimes"]) * n_dev for p in walls)
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and cpu / 3600 <= 4 and rss <= 0.8 * avail
                                           and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "en001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "en001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
