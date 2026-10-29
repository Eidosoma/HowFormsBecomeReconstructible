"""Qualification of GW001 on the preflight (engineering) shards; criteria fixed in advance.

python -m gw001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  engine equivalence at side 16, bit for bit: msegrid's acquisition equals br002.sim.prepare; panel R's record
    equals br002's record path (rel + code, flip and kill); panel B equals br002.sim.simulate (both bodies)
Q4  independent replay: a per-site loop with its own placement, wounds, bonds, record step and body step
    reproduces six branches at sides 16, 32 and 64 within 1e-9 (acquisition reused, checked by Q3 and the tests)
Q5  aliases exact: for J = 1 arms a kill equals a reset; the protected record never changes; the static record
    keeps its wounded initial state
Q6  reanalysis: endpoints recomputed from the saved final states equal the saved ones
Q7  placement audit: every F0 and S8 patch sits at its declared distance from the nearest wall, or straddles one
Q8  efficacy: every patch covers its declared sites; wounds act as declared on the initial record
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

from br002 import design as D2  # noqa: E402
from br002 import sim as S2  # noqa: E402
from gw001 import design as D  # noqa: E402
from gw001 import sim  # noqa: E402
from gw001 import worker as W  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE, address, center  # noqa: E402
from msegrid import core as G  # noqa: E402

FROZEN = LANE / "gw001" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 16
Q4_PICKS = (("R", "F0_32", "rel+code", "k8-mid", 0), ("R", "S8_32", "self", "f4-d1", 1),
            ("R", "BLx2_32", "code", "r8-random", 2), ("R", "F0_64", "multi", "f16-mid", 3),
            ("B", "F0_32_s0.1_c", "multi", "f8-d0", 4), ("B", "F0_16_s0.1_o", "rel+code", "r4-mid", 5))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


# Independent per-site implementations --------------------------------------------------------------------

def s_patch(family, kind, side, size, place, g):
    m = np.zeros((side, side), bool)
    if place == "random":
        a, b = g.integers(0, side, 2)
        rows, cols = [(a + x) % side for x in range(size)], [(b + x) % side for x in range(size)]
    else:
        Dm = side // 2 if family == "F0" else 8
        walls = side // Dm
        along = int(g.integers(0, side))
        if place == "cross":
            start = (Dm * (int(g.integers(0, walls)) + 1) - size // 2) % side
        else:
            d = (Dm - size) // 2 if place == "mid" else int(place[1:])
            dom, s_ = int(g.integers(0, walls)), int(g.integers(0, 2))
            start = dom * Dm + (d if s_ == 0 else Dm - size - d)
        across = [(start + x) % side for x in range(size)]
        alongs = [(along + x) % side for x in range(size)]
        rows, cols = (alongs, across) if kind % 2 == 0 else (across, alongs)
    for i in rows:
        for j in cols:
            m[i, j] = True
    return m


def s_bproj(x, size):
    n = x.shape[-1]
    out = np.empty_like(x)
    for bi in range(0, n, size):
        for bj in range(0, n, size):
            out[bi:bi + size, bj:bj + size] = x[bi:bi + size, bj:bj + size].mean()
    return out


def s_bonds(R0, rel):
    n = R0.shape[-1]
    J = np.ones((4, n, n))
    if rel:
        s = np.where(R0 >= 0, 1.0, -1.0)
        for i in range(n):
            for j in range(n):
                J[0, i, j] = s[i, j] * s[(i - 1) % n, j]
                J[1, i, j] = s[i, j] * s[(i + 1) % n, j]
                J[2, i, j] = s[i, j] * s[i, (j - 1) % n]
                J[3, i, j] = s[i, j] * s[i, (j + 1) % n]
    return J


def s_record(r, xi, arm, B, J):
    n = r.shape[-1]
    if arm.eps > 0:
        nr = np.empty((n, n))
        for i in range(n):
            for j in range(n):
                nr[i, j] = (J[0, i, j] * r[(i - 1) % n, j] + J[1, i, j] * r[(i + 1) % n, j]
                            + J[2, i, j] * r[i, (j - 1) % n] + J[3, i, j] * r[i, (j + 1) % n]) / 4.0
        r = r + arm.eps * (r * (1 - (r / G.R_STAR) ** 2) + arm.kr * (nr - r)) + D.SIGMA_R * xi
    if arm.kc > 0:
        r = r + arm.kc * (B - s_bproj(r, 4))
    if arm.eps > 0 or arm.kc > 0:
        r = np.clip(r, -2.0, 2.0)
    return r


def s_body(V, ema, r, th, z, p, conserved, gain):
    n = V.shape[-1]
    drift = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            nb = (V[(i - 1) % n, j] + V[(i + 1) % n, j] + V[i, (j - 1) % n] + V[i, (j + 1) % n]) / 4.0
            drift[i, j] = V[i, j] - V[i, j] ** 3 + p.well_asym + th[i, j] + p.coupling * (nb - V[i, j])
    if conserved:
        Vt = np.clip(V + p.dt * center(drift) + center(p.sigma * z), -2.0, 2.0)
    else:
        Vt = np.clip(V + p.dt * drift + p.sigma * z, -2.0, 2.0)
    ema = (1 - p.ema_rate) * ema + p.ema_rate * Vt
    d = gain * (r - Vt)
    if conserved:
        d = center(d)
    return np.clip(Vt + p.dt * d, -2.0, 2.0), ema


def scalar_branch(panel, unit, arm_name, cond_name, ci):
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    c = cases[ci]
    arm = D.ARM[panel][arm_name]
    cond = next(x for x in D.conditions(panel, unit) if x.name == cond_name)
    if panel == "R":
        family, side = D.parse_geometry(unit)
        _, R0all, Tall = sim.prepare_R(unit, BLOCK, "engineering")
        window, every = D.WINDOW_R, D.EVERY_R
    else:
        family, side, sigma, body = D.parse_regime(unit)
        _, Vall, Eall, R0all, THall, Tall, p, conserved = sim.prepare_B(unit, BLOCK, "engineering")
        window, every = D.WINDOW_B, D.EVERY_B
    R0, T = R0all[ci].copy(), Tall[ci]
    m = s_patch(family, c.message, side, cond.size, cond.place, address(D.TAG, *c.key(), "lesion", cond.place))
    r = R0.copy()
    if cond.wound == "flip":
        r = np.where(m, -r, r)
    elif cond.wound in ("reset", "kill"):
        r = np.where(m, 0.0, r)
    J = s_bonds(R0, arm.rel)
    if cond.wound == "kill" and arm.rel:
        n = side
        for i in range(n):
            for j in range(n):
                if m[i, j]:
                    for d, (di, dj) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
                        if m[(i + di) % n, (j + dj) % n]:
                            J[d, i, j] = 0.0
    B = s_bproj(R0, 4)
    gx = address(D.TAG, *c.key(), "record-noise")
    if panel == "B":
        v, e, th = Vall[ci].copy(), Eall[ci].copy(), THall[ci]
        if cond.wound == "flip":
            v = np.where(m, -v, v)
        elif cond.wound in ("reset", "kill"):
            nb = D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{cond.size}").standard_normal((side, side))
            v, e = np.where(m, nb, v), np.where(m, nb, e)
        gz = address(D.TAG, *c.key(), "future")
    for t in range(1, window + 1):
        i = (t - 1) % every
        if i == 0:
            xs = gx.standard_normal((every, side, side))
            if panel == "B":
                zs = gz.standard_normal((every, side, side))
        if panel == "B":
            v, e = s_body(v, e, r, th, zs[i], p, conserved, NATIVE.gain)
        r = s_record(r, xs[i], arm, B, J)
        if arm.clamp:
            r = R0.copy()
    return (v if panel == "B" else None), r


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
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda p, u, b=lo: npz(root / "raw" / p / u / f"{b}.npz")
    shard = lambda p, u, b=lo: npz(root / "shards" / p / u / f"{b}.npz")
    checks = {}

    missing = []
    for p, u in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            nc = len(D.conditions(p, u))
            key = "kept_curve" if p == "R" else "les_v"
            for arm in D.PANELS[p]["arms"]:
                x = e.get(f"{arm.name}/{key}")
                if x is None or x.shape[-2:] != (nc, D.NCASE):
                    bad.append(f"{arm.name}/{key}")
            missing += [f"{p}/{u}/{b}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        u = D.PANELS[p]["units"][0]
        W.run_task(p, u, lo, "engineering", str(serial))
        x, y = npz(root / "shards" / p / u / f"{lo}.npz"), npz(serial / "shards" / p / u / f"{lo}.npz")
        same[f"{p}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for name in (D2.regime("F0", 0.3), D2.regime("F0", 0.3, "o")):
        cases, s0, th, p, conserved, T, Tf = S2.prepare(name, [lo], "engineering")
        V, ema, R, th2 = G.acquire(D2.TAG, cases, T, p, 16)
        eq[f"{name}/acquire=br002.prepare"] = bool(np.array_equal(V, s0.V) and np.array_equal(R, s0.R) and np.array_equal(ema, s0.ema))
        k = len(cases)
        m4, born = S2.patch_masks(cases, 4), S2.newborn(cases, 4)
        Z, XI = S2.draws(cases, "future", updates=2000), S2.draws(cases, "record-noise", updates=2000)
        c2 = (D2.Cond("both-4x4", "lesion", 4), D2.Cond("kill-4x4", "kill", 4))
        v2, _, r2, _ = S2.simulate(D2.ARM["R"]["multi"], c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf,
                                   np.ones(k, int), [m4, m4], [None, None], [None, born])
        v, _, r, _ = sim.simulate_B(D.ARM["B"]["multi"], (D.Cond("f4", "flip", 4), D.Cond("r4", "reset", 4)), k, s0.V, s0.ema,
                                    s0.R, th, T, p, conserved, [m4, m4], [None, born], cases, 2000, 500, tag=D2.TAG)
        eq[f"{name}/panel_B=br002"] = bool(np.array_equal(v, v2) and np.array_equal(r, r2))
        _, _, r3, _ = S2.simulate(D2.ARM["R"]["rel+code"], c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf,
                                  np.ones(k, int), [m4, m4], [None, None], [None, born])
        r4, _, _ = sim.simulate_R(D.ARM["R"]["rel+code"], (D.Cond("f4", "flip", 4), D.Cond("k4", "kill", 4)), k, s0.R, T,
                                  [m4, m4], cases, 2000, 250, tag=D2.TAG)
        eq[f"{name}/panel_R_record=br002"] = bool(np.array_equal(r3, r4))
    checks["Q3_engine_equivalence"] = {"pass": all(eq.values()), "items": eq}

    worst, items = 0.0, {}
    for p, u, arm, cond, ci in Q4_PICKS:
        v, r = scalar_branch(p, u, arm, cond, ci)
        raw = rawf(p, u)
        k = [c.name for c in D.conditions(p, u)].index(cond)
        d = float(np.abs(r - raw[f"{arm}/R"][k, ci]).max())
        if v is not None:
            d = max(d, float(np.abs(v - raw[f"{arm}/V"][k, ci]).max()))
        items[f"{p}/{u}/{arm}/{cond}/case{ci}"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}

    alias = {}
    for u in D.PANELS["R"]["units"]:
        names = [c.name for c in D.GEOMETRIES[u]]
        raw = rawf("R", u)
        for kname in [n for n in names if n.startswith("k")]:
            rname = "r" + kname[1:]
            for arm in D.ARMS_R:
                if not arm.rel:
                    alias[f"R/{u}/{arm.name}/{kname}={rname}"] = bool(np.array_equal(raw[f"{arm.name}/R"][names.index(kname)],
                                                                                 raw[f"{arm.name}/R"][names.index(rname)]))
    for u in D.PANELS["B"]["units"]:
        raw = rawf("B", u)
        alias[f"B/{u}/protected_unchanged"] = bool(all(np.array_equal(raw["protected/R"][c], raw["R0"]) for c in range(len(D.COND_B))))
        alias[f"B/{u}/static_sham_unchanged"] = bool(np.array_equal(raw["static/R"][0], raw["R0"]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": len(alias), "failed": [k for k, v in alias.items() if not v]}

    bad = []
    for p, u in D.tasks():
        raw, e = rawf(p, u), shard(p, u)
        nc = len(D.conditions(p, u))
        T = np.tile(raw["T"], (nc, 1, 1))
        mask = raw["mask"].reshape(-1, *raw["T"].shape[-2:])
        for arm in D.PANELS[p]["arms"]:
            R = raw[f"{arm.name}/R"].reshape(-1, *raw["T"].shape[-2:])
            if p == "R":
                got = {"committed": sim.committed_kept(R, T, mask)}
                last = {"kept_curve": sim.masked_sign(R, T, mask), "rsign_curve": sim.sign(R, T)}
                bad += [f"{p}/{u}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"])]
                bad += [f"{p}/{u}/{arm.name}/{k}" for k, v in last.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"][-1])]
            else:
                V = raw[f"{arm.name}/V"].reshape(-1, *raw["T"].shape[-2:])
                got = {"v_qual": sim.qual(V, T), "v_out": sim.outside_agree(V, T, mask), "les_v": sim.masked_sign(V, T, mask),
                       "les_r": sim.masked_sign(R, T, mask), "r_sign": sim.sign(R, T)}
                bad += [f"{p}/{u}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    placed = []
    for p, u in D.tasks():
        family = D.parse_geometry(u)[0] if p == "R" else "F0"
        if family not in ("F0", "S8"):
            continue
        conds = D.conditions(p, u)
        for b in range(lo, hi):
            e = shard(p, u, b)
            for ci, c in enumerate(conds):
                if not c.size:
                    continue
                if c.place == "random":
                    continue
                side = D.parse_geometry(u)[1] if p == "R" else D.parse_regime(u)[1]
                Dm = side // 2 if family == "F0" else 8
                want = -1 if c.place == "cross" else ((Dm - c.size) // 2 if c.place == "mid" else int(c.place[1:]))
                if not (e["events/wall_distance"][ci] == want).all():
                    placed.append(f"{p}/{u}/{b}/{c.name}")
    checks["Q7_placement_audit"] = {"pass": not placed, "failed": placed[:10]}

    eff = []
    for p, u in D.tasks():
        conds = D.conditions(p, u)
        for b in range(lo, hi):
            e = shard(p, u, b)
            for ci, c in enumerate(conds):
                if not (e["events/patch_sites"][ci] == c.size ** 2).all():
                    eff.append(f"{p}/{u}/{b}/{c.name}/patch")
    cases, R0, T = sim.prepare_R("F0_32", lo, "engineering")
    conds = (D.Cond("f8", "flip", 8, "mid"), D.Cond("r8", "reset", 8, "mid"), D.Cond("k8", "kill", 8, "mid"))
    masks = sim.masks_for(cases, conds, "F0", 32)
    for cond, m in zip(conds, masks):
        r0 = np.where(m, -R0, R0) if cond.wound == "flip" else np.where(m, 0.0, R0)
        r1, _, _ = sim.simulate_R(D.Arm("hold"), (cond,), len(cases), R0, T, [m], cases, D.EVERY_R, D.EVERY_R)
        if not np.array_equal(r1, r0):
            eff.append(f"wound/{cond.wound}")
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
    proc = subprocess.run([sys.executable, "-m", "gw001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "gw001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_R_kept2000.csv", out / "contrasts_R_kept8000.csv", out / "contrasts_B.csv",
                out / "summary.json", out / "predictions_scored.json", out / "TABLES.md"]
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
