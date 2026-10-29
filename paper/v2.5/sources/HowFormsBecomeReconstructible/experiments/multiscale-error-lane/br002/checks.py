"""Qualification of BR002 on the preflight (engineering) shards; criteria fixed in advance.

python -m br002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  engine equivalence: the conserved body with a static record and no event equals mse.engine's hold route
    bit for bit, and the conserved reader equals an engine-run reader
Q4  independent replay: a per-site loop with its own body (BR001's), bonds, kills, gates, hysteresis, window,
    tags, latch, turnover and wall placement reproduces six branches within 1e-9
Q5  aliases exact: the protected record never changes; outside the window arms the cued and uncued lasting
    impositions are identical; rel+code+relink equals rel+code except under kills; panel G's sham equals
    panel R's sham for shared arms
Q6  reanalysis: endpoints recomputed from saved states (and fresh endpoints by re-reading saved records)
    equal the saved ones
Q7  known-reference reader: target-packet minus zero-packet fresh sign >= 0.15 in every regime
Q8  efficacy: every patch covers its declared sites; panel G's patches sit at their declared distance from
    F0's walls or straddle one; onsets lie in range; turnover counts lie within 40% of their expectation
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
from br001.checks import s_body, s_region  # noqa: E402   (BR001's independent per-site body)
from br002 import design as D  # noqa: E402
from br002 import sim  # noqa: E402
from br002 import worker as W  # noqa: E402
from mse.assay import enrol, spread  # noqa: E402
from mse.engine import Route, State, run  # noqa: E402
from mse.native import NATIVE, address, thresholds  # noqa: E402

FROZEN = LANE / "br002" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 16
Q4_PICKS = (("C", D.regime("F0", 0.3), "duration+h", "scar-6x6", 0),
            ("C", D.regime("F0", 0.1, "o"), "phase+tags", "window-scar-6x6", 1),
            ("C", D.regime("F0", 0.3, "o"), "tags+h", "impose-inf", 2),
            ("R", D.regime("BL", 0.1), "rel+code+relink", "kill-8x8", 3),
            ("R", D.regime("IS", 0.1), "rel", "turnover-0.003", 4),
            ("G", D.regime("F0", 0.1), "rel+code", "w6-cross", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def s_patch(c, cond):
    """The lesion patch from addresses alone (BR001's corner rule, or the wall placement rule)."""
    m = np.zeros((16, 16), bool)
    s = cond.size
    if not s:
        return m
    if cond.place == "random":
        a, b = address(D.TAG, *c.key(), "lesion").integers(0, 16, 2)
        rows, cols = [(a + x) % 16 for x in range(s)], [(b + x) % 16 for x in range(s)]
    else:
        g = address(D.TAG, *c.key(), "geometry", f"{s}", cond.place)
        along = int(g.integers(0, 16))
        if cond.place == "cross":
            start = (8 * (int(g.integers(0, 2)) + 1) - s // 2) % 16
        else:
            d = int(cond.place[1:])
            dom, side = int(g.integers(0, 2)), int(g.integers(0, 2))
            start = 8 * dom + (d if side == 0 else 8 - s - d)
        across_idx, along_idx = [(start + x) % 16 for x in range(s)], [(along + x) % 16 for x in range(s)]
        rows, cols = (along_idx, across_idx) if c.message % 2 == 0 else (across_idx, along_idx)
    for i in rows:
        for j in cols:
            m[i, j] = True
    return m


def scalar_branch(panel, name, arm_name, cond_name, ci, cal):
    """One branch from addresses alone, site by site."""
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
    t_dmg = tau + D.WINDOW_DELAY if cond.kind == "window" else tau
    mask = s_patch(c, cond)
    events = []
    if cond.kind == "turnover" and cond.rate > 0:
        g = address(D.TAG, *c.key(), "turnover", f"{cond.rate:g}")
        n = int(g.poisson(cond.rate * D.WINDOW * 256))
        t_, site, val = g.integers(1, D.WINDOW + 1, n), g.integers(0, 256, n), 0.2 * g.standard_normal(n)
        order = np.argsort(t_, kind="stable")
        events = list(zip(t_[order], site[order], val[order]))
    born = D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{cond.size}").standard_normal((16, 16)) if cond.kind == "kill" else None
    Z = address(D.TAG, *c.key(), "future").standard_normal((D.WINDOW, 16, 16))
    XI = address(D.TAG, *c.key(), "record-noise").standard_normal((D.WINDOW, 16, 16))
    sg = np.where(R0 >= 0, 1.0, -1.0)
    # bonds to the four neighbours: up (i-1), down (i+1), left (j-1), right (j+1)
    J = np.ones((4, 16, 16))
    if arm.rel:
        for i in range(16):
            for j in range(16):
                J[0, i, j] = sg[i, j] * sg[(i - 1) % 16, j]
                J[1, i, j] = sg[i, j] * sg[(i + 1) % 16, j]
                J[2, i, j] = sg[i, j] * sg[i, (j - 1) % 16]
                J[3, i, j] = sg[i, j] * sg[i, (j + 1) % 16]
    v, e, r = V.copy(), ema.copy(), R0.copy()
    tag, latch, opened = np.zeros((16, 16)), np.zeros((16, 16), int), np.zeros((16, 16), bool)
    B = fixture.block_projection(R0, 4)
    gain = NATIVE.gain if arm.reads else 0.0
    stop = tau + cond.duration if cond.duration else D.WINDOW + 1
    ev = 0
    for t in range(1, D.WINDOW + 1):
        if t == t_dmg:
            if cond.kind in ("lesion", "wound") or (cond.kind == "window" and cond.damage == "wound"):
                v = np.where(mask, -v, v)
            if cond.kind in ("lesion", "record"):
                r = np.where(mask, -r, r)
            if cond.kind == "kill":
                v, e, r = np.where(mask, born, v), np.where(mask, born, e), np.where(mask, 0.0, r)
                if arm.rel:
                    for i in range(16):
                        for j in range(16):
                            if not mask[i, j]:
                                continue
                            for d, (di, dj) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
                                if mask[(i + di) % 16, (j + dj) % 16]:
                                    J[d, i, j] = 1.0 if arm.relink else 0.0
            if cond.kind in ("wound", "scar", "window"):
                tag = np.where(mask, 1.0, tag)
        if (cond.kind == "scar" or (cond.kind == "window" and cond.damage == "scar")) and t >= t_dmg:
            v = np.where(mask, -T, v)
            tag = np.where(mask, 1.0, tag)
        if cond.kind == "impose" and tau <= t < stop:
            v = Tf.copy()
        v, e, vt = s_body(v, e, r, th, Z[t - 1], p, conserved, gain)
        gate = None
        window = bool(cond.cue and tau <= t < tau + D.WINDOW_P)
        if arm.write == "phase":
            gate = np.full((16, 16), window)
        elif arm.write == "phase_tags":
            gate = window & (tag < D.TAG_GATE)
        elif arm.write != "none":
            mm = s_region(r - vt)
            mis = mm > cal["mismatch"]
            ok = np.ones((16, 16), bool)
            if arm.write == "duration":
                latch = np.where(s_region(vt - e) > cal["surprise"], D.LATCH_W, np.maximum(latch - 1, 0))
                ok = latch == 0
            elif arm.write == "tags":
                ok = tag < D.TAG_GATE
            if arm.hyst:
                opened = (opened & (mm > D.OFF * cal["mismatch"])) | (mis & ok)
                gate = opened & (tag < D.TAG_GATE) if arm.write == "tags" else opened
            else:
                gate = mis & ok
        tag = tag * (1.0 - D.TAG_DECAY)
        changed = False
        if arm.eps > 0:
            nr = np.empty((16, 16))
            for i in range(16):
                for j in range(16):
                    nr[i, j] = (J[0, i, j] * r[(i - 1) % 16, j] + J[1, i, j] * r[(i + 1) % 16, j]
                                + J[2, i, j] * r[i, (j - 1) % 16] + J[3, i, j] * r[i, (j + 1) % 16]) / 4.0
            r = r + arm.eps * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (nr - r)) + D.SIGMA_R * XI[t - 1]
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
            if not arm.clamp:
                r[i, j] = 0.0
            ev += 1
    return v, r


def wall_distance_ok(T, m, place):
    """F0: a 'dK' patch is single-signed at distance K from its nearest wall; a 'cross' patch is two-signed."""
    inside = T[m]
    if place == "cross":
        return bool((inside > 0).any() and (inside < 0).any())
    if not ((inside > 0).all() or (inside < 0).all()):
        return False
    rows, cols = np.where(m)
    split_cols = bool((T[:, 0] == T[:, 0][0]).all())          # columns split: every row has one sign at column 0
    across = cols if split_cols else rows
    return min(min(x % 8, 7 - x % 8) for x in across) == int(place[1:])


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
                for ep in ("v_qual", "r_sign", "les_r", "fR_qual") + (("adopt_flip", "rg_sign") if p == "C" else ()):
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
    for r in (D.regime("F0", 0.1), D.regime("BL", 0.1)):
        cases, s0, th, p, conserved, T, Tf = sim.prepare(r, [lo], "engineering")
        Z = sim.draws(cases, "future", updates=D.WINDOW)
        ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None, capture=None), D.WINDOW, p)
        eq[f"{r}/static_sham=engine"] = bool(np.array_equal(rawf("R", r)["static/V"][0], ref.V))
        births, Zr = sim.recipients(cases)
        k = len(cases)
        Vb = births.reshape(-1, 16, 16)
        s = State(Vb, Vb.copy(), np.repeat(T, D.RECIPIENTS, axis=0), np.zeros_like(Vb))
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
    cc = [c.name for c in D.COND_C]
    for r in D.PANELS["C"]["regimes"]:
        raw = rawf("C", r)
        i1, i2 = cc.index("impose-inf-cued"), cc.index("impose-inf")
        for arm in D.ARMS_C:
            if arm.write not in ("phase", "phase_tags"):
                alias[f"C/{r}/{arm.name}/cued=uncued"] = bool(np.array_equal(raw[f"{arm.name}/R"][i1], raw[f"{arm.name}/R"][i2])
                                                             and np.array_equal(raw[f"{arm.name}/V"][i1], raw[f"{arm.name}/V"][i2]))
    cr = [c.name for c in D.COND_R]
    for r in D.PANELS["R"]["regimes"]:
        raw = rawf("R", r)
        alias[f"R/{r}/protected_record_unchanged"] = bool(all(np.array_equal(raw["protected/R"][c], raw["s0/R"])
                                                              for c in range(len(cr))))
        for ci, c in enumerate(cr):
            if not c.startswith("kill"):
                alias[f"R/{r}/relink=rel+code/{c}"] = bool(np.array_equal(raw["rel+code+relink/R"][ci], raw["rel+code/R"][ci]))
    for r in D.PANELS["G"]["regimes"]:
        if r in D.PANELS["R"]["regimes"]:
            x, y = rawf("G", r), rawf("R", r)
            for arm in ("static", "self", "multi", "rel", "rel+code"):
                alias[f"G(sham)=R(sham)/{r}/{arm}"] = bool(np.array_equal(x[f"{arm}/V"][0], y[f"{arm}/V"][0])
                                                           and np.array_equal(x[f"{arm}/R"][0], y[f"{arm}/R"][0]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": len(alias), "failed": [k for k, v in alias.items() if not v]}

    bad = []
    for p, r in D.tasks():
        raw, e = rawf(p, r), shard(p, r)
        nc = len(D.PANELS[p]["conditions"])
        T = np.tile(raw["targets"], (nc, 1, 1))
        Tf = np.tile(raw["foreign"], (nc, 1, 1))
        mask = raw["mask"].reshape(-1, 16, 16)
        cases, s0, th, pp, conserved, _, _ = sim.prepare(r, [lo], "engineering")
        births, Zr = sim.recipients(cases)
        idx = np.tile(np.arange(D.NCASE), nc)
        for j, arm in enumerate(D.PANELS[p]["arms"]):
            V, R = raw[f"{arm.name}/V"].reshape(-1, 16, 16), raw[f"{arm.name}/R"].reshape(-1, 16, 16)
            got = {"v_qual": sim.qual(V, T), "r_sign": sim.sign(R, T), "les_r": sim.masked_sign(R, T, mask),
                   "les_v": sim.masked_sign(V, T, mask)}
            if p == "C":
                got.update({"rg_sign": sim.sign(R, Tf), "adopt_flip": sim.adopt_flip(R, T, Tf)})
            if j == 0:
                got["fR_qual"] = sim.qual(sim.read(R, idx, th, births, Zr, pp, conserved), T[:, None]).mean(1)
            bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    reader, ok8, eff = {}, True, []
    for p, r in D.tasks():
        es = [shard(p, r, b) for b in range(lo, hi)]
        t_, z_ = np.mean([x["target/fR_sign"].mean() for x in es]), np.mean([x["zero/fR_sign"].mean() for x in es])
        reader[f"{p}/{r}"] = {"target": round(float(t_), 4), "zero": round(float(z_), 4), "pass": bool(t_ - z_ >= 0.15)}
        for b, x in zip(range(lo, hi), es):
            for ci, c in enumerate(D.PANELS[p]["conditions"]):
                if not (x["events/patch_sites"][ci] == c.size ** 2).all():
                    ok8, _ = False, eff.append(f"{p}/{r}/{b}/{c.name}/patch")
                if c.kind == "turnover" and c.rate > 0:
                    exp = c.rate * D.WINDOW * 256
                    if not (np.abs(x["events/turnover_count"][ci] - exp) <= 0.4 * exp).all():
                        ok8, _ = False, eff.append(f"{p}/{r}/{b}/{c.name}/turnover")
            if D.PANELS[p]["onset"] == "random" and not ((x["events/tau"] >= D.ONSET[0]) & (x["events/tau"] < D.ONSET[1])).all():
                ok8, _ = False, eff.append(f"{p}/{r}/{b}/onset")
        if p == "G":
            raw = rawf(p, r)
            for ci, c in enumerate(D.COND_G):
                if c.size and not all(wall_distance_ok(raw["targets"][j], raw["mask"][ci, j], c.place) for j in range(D.NCASE)):
                    ok8, _ = False, eff.append(f"G/{r}/{c.name}/placement")
    checks["Q7_known_reference_reader"] = {"pass": all(v["pass"] for v in reader.values()), "regimes": reader}
    checks["Q8_efficacy"] = {"pass": ok8, "failed": eff[:10]}

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
    proc = subprocess.run([sys.executable, "-m", "br002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "br002.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
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
