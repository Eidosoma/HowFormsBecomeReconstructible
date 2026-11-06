"""Qualification of BR001 on the preflight (engineering) shards; criteria fixed in advance.

python -m br001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  engine equivalence: the conserved body with a static record and no event equals mse.engine's hold route
    bit for bit, and the conserved reader equals an engine-run reader
Q4  independent replay: a per-site loop with its own body, record, code, gate, tag, latch and turnover code
    reproduces five branches (conserved and open bodies, lesions, a scar under tags, a wound under the
    duration latch, turnover) within 1e-9
Q5  aliases exact: the protected record never changes; L's sham equals T's turnover-0 for shared arms; P's
    write_none equals L's self-correcting record under sham
Q6  reanalysis: endpoints recomputed from saved states (and fresh endpoints by re-reading saved records)
    equal the saved ones
Q7  known-reference reader: target-packet minus zero-packet fresh sign >= 0.15 in every regime
Q8  efficacy: every lesion, wound, scar or record lesion covers its declared patch; onsets lie in range;
    turnover counts lie within 40% of their expectation
Q9  resources: forecast development wall <= 12 h on 16 workers with RAM and disk headroom
Q10 reader dry run: analyze completes, scores every statement, every git file <= 256 KB
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
from br001 import design as D  # noqa: E402
from br001 import sim  # noqa: E402
from br001 import worker as W  # noqa: E402
from mse.assay import enrol, spread  # noqa: E402
from mse.engine import Route, State, run  # noqa: E402
from mse.native import NATIVE, address, center, thresholds  # noqa: E402

FROZEN = LANE / "br001" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 16


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def nb(x, i, j):
    return (x[(i - 1) % 16, j] + x[(i + 1) % 16, j] + x[i, (j - 1) % 16] + x[i, (j + 1) % 16]) / 4.0


def s_body(V, ema, r, th, z, p, conserved, gain):
    drift = np.empty((16, 16))
    for i in range(16):
        for j in range(16):
            drift[i, j] = V[i, j] - V[i, j] ** 3 + th[i, j] + p.coupling * (nb(V, i, j) - V[i, j])
    if conserved:
        Vt = np.clip(V + p.dt * center(drift) + center(p.sigma * z), -2.0, 2.0)
    else:
        Vt = np.clip(V + p.dt * drift + p.sigma * z, -2.0, 2.0)
    ema = (1 - p.ema_rate) * ema + p.ema_rate * Vt
    d = gain * (r - Vt)
    if conserved:
        d = center(d)
    return np.clip(Vt + p.dt * d, -2.0, 2.0), ema, Vt


def s_region(x):
    return fixture.block_projection(x, 4) ** 2


def scalar_branch(panel, name, arm_name, cond_name, ci, cal):
    """One branch from addresses alone."""
    family, sigma, body = D.parse(name)
    p = replace(NATIVE, sigma=sigma)
    conserved = body == "c"
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    c = cases[ci]
    th = thresholds(address(D.TAG, "theta", BLOCK), replace(p, threshold_spread=spread(D.TAG, BLOCK)))
    T, Tf = D.TEMPLATES[family][c.message], D.TEMPLATES[family][D.FOREIGN[c.message]]
    s0 = sim.prepare(name, [BLOCK], "engineering")[1]          # acquisition is checked by ME002's Q4; reuse it here
    V, ema, R0 = s0.V[ci].copy(), s0.ema[ci].copy(), s0.R[ci].copy()
    arm = D.ARM[panel][arm_name]
    cond = next(x for x in D.PANELS[panel]["conditions"] if x.name == cond_name)
    tau = 1 if D.PANELS[panel]["onset"] == "start" else int(address(D.TAG, *c.key(), "onset").integers(*D.ONSET))
    mask = np.zeros((16, 16), bool)
    if cond.size:
        a, b = address(D.TAG, *c.key(), "lesion").integers(0, 16, 2)
        mask[np.ix_(np.arange(a, a + cond.size) % 16, np.arange(b, b + cond.size) % 16)] = True
    events = []
    if cond.kind == "turnover" and cond.rate > 0:
        g = address(D.TAG, *c.key(), "turnover", f"{cond.rate:g}")
        n = int(g.poisson(cond.rate * D.WINDOW * 256))
        t_, site, val = g.integers(1, D.WINDOW + 1, n), g.integers(0, 256, n), 0.2 * g.standard_normal(n)
        order = np.argsort(t_, kind="stable")
        events = list(zip(t_[order], site[order], val[order]))
    Z = address(D.TAG, *c.key(), "future").standard_normal((D.WINDOW, 16, 16))
    XI = address(D.TAG, *c.key(), "record-noise").standard_normal((D.WINDOW, 16, 16))
    v, e, r = V.copy(), ema.copy(), R0.copy()
    tag, latch = np.zeros((16, 16)), np.zeros((16, 16), int)
    B = fixture.block_projection(R0, 4)
    gain = NATIVE.gain if arm.reads else 0.0
    stop = tau + cond.duration if cond.duration else D.WINDOW + 1
    ev = 0
    for t in range(1, D.WINDOW + 1):
        if t == tau:
            if (cond.kind == "lesion" and cond.target in ("both", "body")) or cond.kind == "wound":
                v = np.where(mask, -v, v)
            if (cond.kind == "lesion" and cond.target in ("both", "record")) or cond.kind == "record":
                r = np.where(mask, -r, r)
            if cond.kind in ("wound", "scar"):
                tag = np.where(mask, 1.0, tag)
        if cond.kind == "scar" and t >= tau:
            v = np.where(mask, -T, v)
            tag = np.where(mask, 1.0, tag)
        if cond.kind == "impose" and tau <= t < stop:
            v = Tf.copy()
        v, e, vt = s_body(v, e, r, th, Z[t - 1], p, conserved, gain)
        gate = None
        if arm.write != "none":
            mis = s_region(r - vt) > cal["mismatch"]
            if arm.write == "always":
                gate = mis
            elif arm.write == "duration":
                latch = np.where(s_region(vt - e) > cal["surprise"], D.LATCH_W, np.maximum(latch - 1, 0))
                gate = mis & (latch == 0)
            elif arm.write == "tags":
                gate = mis & (tag < D.TAG_GATE)
            elif arm.write == "phase":
                gate = np.full((16, 16), bool(cond.cue and tau <= t < tau + D.WINDOW_P))
        tag = tag * (1.0 - D.TAG_DECAY)
        changed = False
        if arm.eps > 0:
            nr = np.array([[nb(r, i, j) for j in range(16)] for i in range(16)])
            r = r + arm.eps * (r * (1 - (r / D.R_STAR) ** 2) + arm.kr * (nr - r)) + arm.sigma_r * XI[t - 1]
            changed = True
        if arm.kc > 0:
            r = r + arm.kc * (B - fixture.block_projection(r, 4))
            changed = True
        if gate is not None:
            r = r + D.RHO_W * gate * (v - r)
            changed = True
        if changed:
            r = np.clip(r, -2.0, 2.0)
        if arm.clamp:
            r = R0.copy()
        while ev < len(events) and events[ev][0] == t:
            _, site, val = events[ev]
            i, j = divmod(int(site), 16)
            v[i, j], e[i, j] = val, val
            if not arm.separate:
                r[i, j] = 0.0
            ev += 1
    return v, r


Q4_PICKS = (("L", D.regime("F0", 0.3), "multi", "both-6x6", 0), ("L", D.regime("F0", 0.1, "o"), "multi", "both-4x4", 1),
            ("P", D.regime("F0", 0.3), "write_tags", "scar-6x6", 2), ("P", D.regime("F0", 0.1, "o"), "write_duration", "wound-6x6", 3),
            ("T", D.regime("F0", 0.1), "self", "turnover-0.001", 4))


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
    checks = {}

    missing = []
    for p, r in D.tasks():
        nc = len(D.PANELS[p]["conditions"])
        for b in range(lo, hi):
            path = root / "shards" / p / r / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{r}/{b}")
                continue
            e = npz(path)
            for arm in D.PANELS[p]["arms"]:
                for ep in ("v_qual", "r_sign", "les_r", "fR_qual"):
                    x = e.get(f"{arm.name}/{ep}")
                    if x is None or x.shape != (nc, D.NCASE) or not np.isfinite(x).all():
                        missing.append(f"{p}/{r}/{b}/{arm.name}/{ep}")
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        r = D.PANELS[p]["regimes"][0]
        W.run_task(p, r, lo, "engineering", calib, str(serial))
        x, y = npz(root / "shards" / p / r / f"{lo}.npz"), npz(serial / "shards" / p / r / f"{lo}.npz")
        same[f"{p}/{r}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for r in (D.regime("F0", 0.1), D.regime("F0", 0.3)):
        cases, s0, th, p, conserved, T, Tf = sim.prepare(r, [lo], "engineering")
        Z = sim.draws(cases, "future", updates=D.WINDOW)
        ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None, capture=None), D.WINDOW, p)
        eq[f"{r}/static_sham=engine"] = bool(np.array_equal(rawf("L", r)["static/V"][0], ref.V))
        births, Zr = sim.recipients(cases)
        k = len(cases)
        V = births.reshape(-1, 16, 16)
        s = State(V, V.copy(), np.repeat(T, D.RECIPIENTS, axis=0), np.zeros_like(V))
        th_r = np.repeat(th, D.RECIPIENTS, axis=0)
        s = run(s, th_r, lambda t: Zr[t - 1].reshape(-1, 16, 16), Route(reference=None, capture=None), D.READ_UPDATES, p)
        mine = sim.read(T, np.arange(k), th, births, Zr, p, True)
        eq[f"{r}/reader=engine"] = bool(np.array_equal(mine, s.V.reshape(k, D.RECIPIENTS, 16, 16)))
    checks["Q3_engine_equivalence"] = {"pass": all(eq.values()), "items": eq}

    worst, items = 0.0, {}
    for p, r, arm, cond, ci in Q4_PICKS:
        v, rr = scalar_branch(p, r, arm, cond, ci, calib["regimes"].get(r))
        raw = rawf(p, r)
        k = [c.name for c in D.PANELS[p]["conditions"]].index(cond)
        d = max(float(np.abs(v - raw[f"{arm}/V"][k, ci]).max()), float(np.abs(rr - raw[f"{arm}/R"][k, ci]).max()))
        items[f"{p}/{r}/{arm}/{cond}/case{ci}"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}

    alias = {}
    for p, r in D.tasks():
        raw = rawf(p, r)
        if "protected" in D.ARM[p]:
            alias[f"{p}/{r}/protected_record_unchanged"] = bool(all(np.array_equal(raw["protected/R"][c], raw["s0/R"])
                                                                   for c in range(len(D.PANELS[p]["conditions"]))))
    for r in D.PANELS["T"]["regimes"]:
        if r in D.PANELS["L"]["regimes"]:
            x, y = rawf("L", r), rawf("T", r)
            for arm in ("static", "self", "multi", "protected"):
                alias[f"L(sham)=T(turnover-0)/{r}/{arm}"] = bool(np.array_equal(x[f"{arm}/V"][0], y[f"{arm}/V"][0])
                                                                 and np.array_equal(x[f"{arm}/R"][0], y[f"{arm}/R"][0]))
    for r in D.PANELS["P"]["regimes"]:
        if r in D.PANELS["L"]["regimes"]:
            x, y = rawf("L", r), rawf("P", r)
            alias[f"P(write_none,sham)=L(self,sham)/{r}"] = bool(np.array_equal(x["self/V"][0], y["write_none/V"][0])
                                                                 and np.array_equal(x["self/R"][0], y["write_none/R"][0]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": len(alias), "failed": [k for k, v in alias.items() if not v]}

    bad = []
    for p, r in D.tasks():
        raw, e = rawf(p, r), shard(p, r)
        nc = len(D.PANELS[p]["conditions"])
        T = np.tile(raw["targets"], (nc, 1, 1))
        mask = raw["mask"].reshape(-1, 16, 16)
        cases, s0, th, pp, conserved, _, _ = sim.prepare(r, [lo], "engineering")
        births, Zr = sim.recipients(cases)
        idx = np.tile(np.arange(D.NCASE), nc)
        for j, arm in enumerate(D.PANELS[p]["arms"]):
            V, R = raw[f"{arm.name}/V"].reshape(-1, 16, 16), raw[f"{arm.name}/R"].reshape(-1, 16, 16)
            got = {"v_qual": sim.qual(V, T), "r_sign": sim.sign(R, T), "les_r": sim.masked_sign(R, T, mask),
                   "les_v": sim.masked_sign(V, T, mask)}
            if j == 0:
                got["fR_qual"] = sim.qual(sim.read(R, idx, th, births, Zr, pp, conserved), T[:, None]).mean(1)
            bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    reader, ok8, eff = {}, True, {}
    for p, r in D.tasks():
        es = [shard(p, r, b) for b in range(lo, hi)]
        t_, z_ = np.mean([x["target/fR_sign"].mean() for x in es]), np.mean([x["zero/fR_sign"].mean() for x in es])
        reader[f"{p}/{r}"] = {"target": round(float(t_), 4), "zero": round(float(z_), 4), "pass": bool(t_ - z_ >= 0.15)}
        for x in es:
            for ci, c in enumerate(D.PANELS[p]["conditions"]):
                ok8 &= bool((x["events/patch_sites"][ci] == c.size ** 2).all())
                if c.kind == "turnover" and c.rate > 0:
                    exp = c.rate * D.WINDOW * 256
                    ok8 &= bool((np.abs(x["events/turnover_count"][ci] - exp) <= 0.4 * exp).all())
            if D.PANELS[p]["onset"] == "random":
                ok8 &= bool(((x["events/tau"] >= D.ONSET[0]) & (x["events/tau"] < D.ONSET[1])).all())
    checks["Q7_known_reference_reader"] = {"pass": all(v["pass"] for v in reader.values()), "regimes": reader}
    checks["Q8_efficacy"] = {"pass": ok8}

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
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "br001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "br001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f"contrasts_{p}_{ep}.csv" for p in D.PANELS for ep in D.PRIMARY_ENDPOINTS[p]]
    expected += [out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
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
