"""E2E001's qualification Q1-Q10 (DRAFT): python -m e2e001.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST]

Fixed before their results (PLAN_E2E001.md); in phase B they run on the preflight (AR005's 900779-900789) at the full shape.
  Q1  complete and finite: every task's endpoints at their shapes (rows alive at each horizon = rows whose stop reaches it),
      finite; generation 0 for every row
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed here); the adapted lineage at SR001's own
      settings reproduces SR001's preflight lineage li4/S4/900940 bit for bit (12 routes, G1 and G16); every task's
      acquisition equals its raw file's V0, R0 and T and every row's generation-0 packet its source (the workers' records)
  Q4  an independent replay from the definitions (the body route written out without lr004.sim.relations, at eta 3e-4,
      E2E001's stream names) of two branches through the whole first generation (8,000 updates; the plan named 250):
      a newborn reading protected storage and an uninterrupted, approximate body; V and r within 1e-12, H and W exact
  Q5  aliases: the alias table is complete (every label has a row; a row's labels share one packet); a packet listed twice
      gives the same lineage bit for bit (500 updates)
  Q6  reanalysis: the endpoints recomputed from the saved states equal the shards'
  Q7  efficacy: post-damage differs from protected exactly in the patch under memory; disabled reading never reads (two
      different packets give the same body, 500 updates); every uninterrupted row starts from its saved body; every task is
      a saved record of its stage (no block drawn)
  Q8  pairing: reordering the rows changes no row's output (500 updates)
  Q9  resources: the development forecast structurally (the lead's ruling after the debug run's first Q9): this stage's
      CPU per branch-generation times the development's own row-generations (its rows built at generation 0; the main
      rows in both futures, the rest in the first), within the lead's cap of 35 CPU-hours and 12 h of wall on 12 workers;
      worker memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output <= 256 KiB
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from dl001 import sim as S  # noqa: E402
from e2e001 import design as D  # noqa: E402
from e2e001 import sim  # noqa: E402
from e2e001 import worker as WK  # noqa: E402
from lr001.sim import cut_for, edges_from, halves  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msegrid.core import Stream, birth, bonds, record_step  # noqa: E402
from sm005 import checks as K5  # noqa: E402  (the lane's parallel check runner, unchanged)
from sr001 import design as SRD  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

CAP = 35.0


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}, json.loads(str(f["__meta__"]))


def tasks_of(root):
    M = json.loads((Path(root) / "manifest.json").read_text())
    out = []
    for name, t in sorted(M["tasks"].items()):
        src1, src2, body, unit, block = name.split("/")
        out.append((f"{src1}/{src2}", body, unit, int(block), t))
    return M, out


def q1(root):
    M, tasks = tasks_of(root)
    bad = []
    for src, body, unit, block, t in tasks:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        stops = [r["stop"] for r in meta["rows"]]
        for e in sim.ENDPOINTS:
            if ends[f"g0/{e}"].shape != (len(stops), 8) or not np.isfinite(ends[f"g0/{e}"]).all():
                bad.append(f"{src}/{body}/{unit}/{block} g0/{e}")
        for f in range(meta["futures"]):
            for g in D.HORIZONS:
                alive = [i for i, s in enumerate(stops) if s >= g and (f < D.SIDE_FUTURES or s >= D.G_MAIN)]
                if list(ends[f"f{f}/g{g}/rows"]) != alive:
                    bad.append(f"{src}/{body}/{unit}/{block} f{f}/g{g} rows")
                for e in sim.ENDPOINTS:
                    v = ends[f"f{f}/g{g}/{e}"]
                    if v.shape != (len(alive), 8) or not np.isfinite(v).all():
                        bad.append(f"{src}/{body}/{unit}/{block} f{f}/g{g}/{e}")
    want = set(map(tuple, D.stage_tasks(M["stage"])))
    have = {(s, b, u, blk) for s, b, u, blk, _ in tasks}
    return {"pass": not bad and have == want, "tasks": len(tasks), "bad": bad[:10], "missing": sorted(map(str, want - have))[:5]}


def q2(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    ends, states, meta, bridge = WK.task(src, body, unit, block, M["stage"])
    e0, _ = npz(Path(root) / t["files"]["shards"]["path"])
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    differ = [k for k in e0 if not np.array_equal(e0[k], ends[k])] + [k for k in s0 if not np.array_equal(s0[k], states[k])]
    return {"pass": not differ and set(e0) == set(ends) and set(s0) == set(states), "task": [src, body, unit, block],
            "arrays": len(e0) + len(s0), "differ": differ[:10]}


def sr001_bridge():
    body, unit, block = "li4", "S4", 900940
    cases, V0, ema0, R0, th, T = SRS.prepare(unit, block, "engineering")
    Tf = SRS.foreign(T, unit, cases)
    H0, W0 = edges_from(bonds(R0, True))
    k = len(cases)
    rows = [{"labels": [r.name], "route": r, "stop": SRD.GENS, "persist": False, "V0": None} for r in SRD.ROUTES]
    packet = tuple(np.concatenate([x] * len(rows)) for x in (H0, W0, R0))
    _r, _a, kept, _f = sim.lineage(body, rows, cases, packet, th * SRD.THETA, T, Tf, np.ones_like(T, dtype=bool), H0, W0,
                                   SRD.TAG, sim.SR001_NAMES, sim.SR001_BIRTH, t_gen=SRD.T_GEN, horizons=(),
                                   gen_fn=sim.GENERATION_SR001, keep=(1, SRD.GENS))
    z, _ = npz(Path(D.RUNS) / "sr001" / "preflight" / "raw" / body / unit / f"{block}.npz")
    each = {f"g{g}/{x}": bool(np.array_equal(kept[g][x].reshape(len(rows), k, D.SIDE, D.SIDE), z[f"g{g}/{x}"]))
            for g in (1, SRD.GENS) for x in ("V", "r", "H", "W")}
    return all(each.values()), each


def q3(root):
    M, tasks = tasks_of(root)
    raw_bad, rec_bad = [], []
    for src, body, unit, block, t in tasks:
        Mr = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
        f = Mr["tasks"][f"{body}/{unit}/{block}"]["files"]["raw"]
        if hashlib.sha256((Path(D.SOURCES[src]["root"]) / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            raw_bad.append(f"{src}/{body}/{unit}/{block}")
        rec = json.loads((Path(root) / "done" / WK.key(src) / body / unit / f"{block}.json").read_text())
        if not all(rec["bridge"].values()):
            rec_bad.append(f"{src}/{body}/{unit}/{block}")
    sr_ok, each = sr001_bridge()
    return {"pass": not raw_bad and not rec_bad and sr_ok, "raw_files": len(tasks), "raw_differ": raw_bad[:5],
            "task_bridges_differ": rec_bad[:5], "sr001_bit_for_bit": sr_ok, "sr001_arrays": len(each)}


def _replay(body, cases, j, packet, V_start, thf, tag, f, t_gen):
    """One branch (case j), the first generation, unbatched; the body route's relations written out here."""
    alpha, G = SRS.kernel(body)
    c = cases[j]
    H, W, r = (np.asarray(x, dtype=float).copy() for x in packet)
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    V = (birth(tag, [c], *sim.BIRTH_NAMES(f)(1), side=D.SIDE)[0].copy() if V_start is None else np.asarray(V_start, float).copy())
    E = V.copy()
    cut = cut_for(D.ROUTE.rate)
    p = replace(NATIVE, sigma=SRD.SIGMA)
    names = sim.GEN_NAMES(f)(1)
    st, xs, zs = (Stream(tag, [c], *nm, side=D.SIDE) for nm in names[:3])
    eta = D.CLOCK["eta"]
    for t in range(1, t_gen + 1):
        i = (t - 1) % SRD.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(SRD.CHUNK)[:, 0], xs.take(SRD.CHUNK)[:, 0], zs.take(SRD.CHUNK)[:, 0]
        V, E, _, _, _ = S.body(V[None], E[None], r[None], thf[j][None], buf[i][None], p, D.ROUTE.gain, alpha, G)
        V, E = V[0], E[0]
        z = zbuf[i]
        fh, fw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(fh, -H, H), np.where(fw, -W, W), np.where(fh, -Hb, Hb), np.where(fw, -Wb, Wb)
        r = record_step(r, xbuf[i], SRD.EPS, SRD.KR, SRD.SIGMA_R, SRD.KC, None, halves(H, W))
        xh, xw = V * np.roll(V, -1, -1), V * np.roll(V, -1, -2)
        Hb, Wb = Hb + eta * (np.clip(xh, -1, 1) - Hb), Wb + eta * (np.clip(xw, -1, 1) - Wb)
        H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
    return V, r, H, W


def q4(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    _ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
    states, _ = npz(Path(root) / t["files"]["raw"]["path"])
    raw, rmeta, _ = WK.load(src, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    rows, labels, _al = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, meta["situations"], rmeta["tag"])
    items, ok = [], True
    picks = [("protected", 0)] + [(lab, 1) for lab in labels if lab.startswith("unint/")][:1]
    for lab, j in picks:
        i = labels[lab]
        H, W, r = rows[i]["packet"]
        Vs = None if rows[i]["V0"] is None else rows[i]["V0"][j]
        V, rr, HH, WW = _replay(body, cases, j, (H[j], W[j], r[j]), Vs, th * theta, meta["tag"], 0, D.T_GEN)
        pos = list(_ends["f0/g1/rows"]).index(i)          # every row is alive at generation 1
        g1V, g1r, g1H, g1W = (states[f"f0/g1/{x}"].reshape(len(rows), 8, D.SIDE, D.SIDE)[pos, j] for x in ("V", "r", "H", "W"))
        dV, dr = float(np.abs(V - g1V).max()), float(np.abs(rr - g1r).max())
        bh = bool(np.array_equal(HH.astype(np.int8), g1H) and np.array_equal(WW.astype(np.int8), g1W))
        good = dV <= 1e-12 and dr <= 1e-12 and bh
        items.append([lab, j, dV, dr, bh])
        ok &= good
    return {"pass": bool(ok), "task": [src, body, unit, block], "items": items}


def _mini(body, rows, cases, thf, T, tag, t_gen=500):
    """A 500-update first generation of the given rows (no reads): the states kept at its end."""
    pk = tuple(np.concatenate([row["packet"][x] for row in rows]) for x in range(3))
    m = np.ones_like(T, dtype=bool)
    Tf = np.stack([T] * 3)                                   # unused without reads
    H0, W0 = np.asarray(rows[0]["packet"][0], float), np.asarray(rows[0]["packet"][1], float)
    _r, _a, kept, final = sim.lineage(body, [dict(row, stop=1) for row in rows], cases, pk, thf, T, Tf, m, H0, W0, tag,
                                      sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), t_gen=t_gen, horizons=(), keep=(1,))
    return kept[1]


def _rows_of(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    raw, rmeta, _ = WK.load(src, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
    rows, labels, aliases = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, meta["situations"], rmeta["tag"])
    return (src, body, unit, block), raw, rmeta, cases, V0, R0, th * theta, T, rows, labels, aliases, meta


def q5(root):
    key, raw, rmeta, cases, V0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    complete = set(labels) == set(meta["labels"]) and all(labels[l] == meta["labels"][l] for l in labels)
    share = all(all(labels[l] == i for l in row["labels"]) for i, row in enumerate(rows))
    k = len(cases)
    i = labels["protected"]
    kept = _mini(key[1], [rows[i], rows[i]], cases, thf, T, meta["tag"])
    V, r = kept["V"].reshape(2, k, D.SIDE, D.SIDE), kept["r"].reshape(2, k, D.SIDE, D.SIDE)
    twice = bool(np.array_equal(V[0], V[1]) and np.array_equal(r[0], r[1]))
    return {"pass": bool(complete and share and twice), "complete": bool(complete), "rows_share_packets": bool(share),
            "listed_twice_identical": twice, "aliases": aliases}


def q6(root):
    M, tasks = tasks_of(root)
    bad, n = [], 0
    for src, body, unit, block, t in tasks[:4]:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        states, _ = npz(Path(root) / t["files"]["raw"]["path"])
        raw, rmeta, _ = WK.load(src, body, unit, block)
        pattern, theta = A.parse_unit(unit)
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
        Tf = SRS.foreign(T, pattern, cases)
        _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
        for f in range(meta["futures"]):
            for g in D.HORIZONS:
                alive = list(ends[f"f{f}/g{g}/rows"])
                idx = np.tile(np.arange(8), len(alive))
                sc = sim.score(states[f"f{f}/g{g}/V"], states[f"f{f}/g{g}/r"], T[idx], Tf[:, idx], m[idx])
                for e in sim.ENDPOINTS:
                    n += 1
                    if not np.array_equal(sc[e].reshape(len(alive), 8), ends[f"f{f}/g{g}/{e}"]):
                        bad.append(f"{src}/{body}/{unit}/{block} f{f}/g{g}/{e}")
    return {"pass": not bad, "compared": n, "differ": bad[:10]}


def q7(root):
    key, raw, rmeta, cases, V0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    pattern, _ = A.parse_unit(key[2])
    cs, V0_, ema0, R0_, th, T_ = A1S.prepare(pattern, key[3], D.SOURCES[key[0]]["purpose"])
    (Hp, Wp, rp), m = sim.post_damage("memory@0", cs, V0_, ema0, R0_, T_, rmeta["tag"])
    post_ok = bool(np.array_equal(rp[~m], R0_[~m]) and np.array_equal(rp[m], -R0_[m]))
    arms_of = {name: list(arms) for name, arms in rmeta["runs"]}
    unint_ok = True
    for lab, i in labels.items():
        if lab.startswith("unint/"):
            arm, sit = lab.split("/")[1:]
            unint_ok &= bool(np.array_equal(rows[i]["V0"], raw[f"{sit}/V"][arms_of[sit].index(arm)]))
    # disabled reading: two different packets, the same body
    i = labels["noread/protected"]
    other = dict(rows[labels[f"post/memory@0"]], route=D.NOREAD)
    kept = _mini(key[1], [rows[i], other], cases, thf, T, meta["tag"])
    V = kept["V"].reshape(2, k, D.SIDE, D.SIDE)
    noread_ok = bool(np.array_equal(V[0], V[1]))
    M, tasks = tasks_of(root)
    stage_ok = {(s, b, u, blk) for s, b, u, blk, _ in tasks} <= set(map(tuple, D.stage_tasks(M["stage"])))
    return {"pass": bool(post_ok and unint_ok and noread_ok and stage_ok), "post_damage_patch_only": post_ok,
            "unint_starts_from_saved_body": bool(unint_ok), "noread_body_independent_of_packet": noread_ok,
            "tasks_are_saved_records": bool(stage_ok)}


def q8(root):
    key, raw, rmeta, cases, V0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    pick = [rows[labels["protected"]], rows[labels["post/memory@0"]], rows[labels[f"vote/memory@0"]]]
    a = _mini(key[1], pick, cases, thf, T, meta["tag"])
    b = _mini(key[1], pick[::-1], cases, thf, T, meta["tag"])
    ra, rb = a["r"].reshape(3, k, D.SIDE, D.SIDE), b["r"].reshape(3, k, D.SIDE, D.SIDE)[::-1]
    Va, Vb = a["V"].reshape(3, k, D.SIDE, D.SIDE), b["V"].reshape(3, k, D.SIDE, D.SIDE)[::-1]
    same = bool(np.array_equal(ra, rb) and np.array_equal(Va, Vb))
    return {"pass": same, "reordered_identical": same}


def row_generations(stops, nf):
    """Every future's row-generations: all rows in the first SIDE_FUTURES futures, the main rows after."""
    return sum(sum(stops) if f < D.SIDE_FUTURES else sum(s for s in stops if s >= D.G_MAIN) for f in range(nf))


def q9(root):
    """The structural forecast (the lead's ruling after the debug run's first Q9): this stage's CPU per
    branch-generation times the development's own row-generations (its rows built at generation 0 only)."""
    M, tasks = tasks_of(root)
    stage = M["stage"]
    done, cpu = 0, 0.0
    for src, body, unit, block, t in tasks:
        _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
        done += 8 * row_generations([r["stop"] for r in meta["rows"]], meta["futures"])
        cpu += t["cpu_s"]
    rate = cpu / done
    dev = 0
    for s, b, u, blk in D.stage_tasks("development"):
        raw, rmeta, _ = WK.load(s, b, u, blk)
        pattern, theta = A.parse_unit(u)
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, D.SOURCES[s]["purpose"])
        rows, _labels, _al = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, D.MAIN + D.SECOND, rmeta["tag"])
        dev += 8 * row_generations([r["stop"] for r in rows], D.FUTURES["development"])
    forecast = rate * dev / 3600
    wall12 = forecast / 12
    rss = max(t["maxrss_mb"] for *_x, t in tasks)
    return {"pass": bool(forecast <= CAP and wall12 <= 12 and rss <= 2048), "forecast_dev_cpu_h": round(forecast, 2),
            "forecast_dev_wall_h_12": round(wall12, 2), "cpu_s_per_branch_generation": round(rate, 4),
            "dev_branch_generations": dev, "worker_rss_mb": rss, "cap": CAP}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "e2e001.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "e2e001.tables", "--dir", str(out)], capture_output=True, text=True, env=env,
                        cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from e2e001 import predict as PR
    ok = (p1.returncode == 0 and p2.returncode == 0 and len(scored.get("parts", [])) == len(PR.parts())
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr)[-600:], "sizes": sizes, "parts_scored": len(scored.get("parts", []))}


def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--cpus", default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root), "Q3_bridges": lambda: q3(root), "Q4_replay": lambda: q4(root),
             "Q7_efficacy": lambda: q7(root), "Q8_pairing": lambda: q8(root)}
    light = {"Q1_complete_finite": lambda: q1(root), "Q5_aliases": lambda: q5(root), "Q6_reanalysis": lambda: q6(root),
             "Q9_resources": lambda: q9(root), "Q10_reader_dry_run": lambda: q10(root)}
    checks = {}
    cpus = [int(c) for c in a.cpus.split(",")] if a.cpus else []
    if len(cpus) >= len(heavy):
        ctx = mp.get_context("fork")
        q = ctx.Queue()
        for c in cpus[: len(heavy)]:
            q.put(c)
        K5._HEAVY.clear()
        K5._HEAVY.update(heavy)
        with ProcessPoolExecutor(len(heavy), mp_context=ctx, initializer=K5._pin, initargs=(q,)) as pool:
            futs = [pool.submit(K5._run_named, name) for name in heavy]
            for name, fn in light.items():
                checks[name] = K5._run(name, fn)[1]
                print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
            for fu in futs:
                name, res = fu.result()
                checks[name] = res
                print(name, "PASS" if res["pass"] else "FAIL", res["seconds"], "s", flush=True)
    else:
        for name, fn in {**heavy, **light}.items():
            checks[name] = K5._run(name, fn)[1]
            print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_replay", "Q5_aliases", "Q6_reanalysis",
             "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
