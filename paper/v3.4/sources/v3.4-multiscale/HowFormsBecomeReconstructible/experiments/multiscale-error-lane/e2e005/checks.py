"""E2E005's qualification Q1-Q10 (DRAFT): python -m e2e005.checks --root STAGE_ROOT [--cpus LIST] [--debug]

Fixed in PLAN_E2E005.md before their results; in phase B they run on the preflight (AR005's 900779-900789).
  Q1  complete and finite: every task's endpoints at their shapes (rows alive at each horizon = rows whose stop reaches
      it) and every generation's switch diagnostics, finite; generation 0 for every row; the stage's tasks all present
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints, diagnostics and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed) and every task's own bridges (the
      acquisition, the generation-0 packets) hold; on the stage's first task, the routed generation equals
      e2e004.sim.generation for the fixed routes (record, body, vote in one call), and in one mixed call a never-opening
      switch equals the record route and a switch open over the whole sheet from update 1 the body route (1,000 updates,
      bit for bit)
  Q4  where the controller never fired in generations 1 to g, its V, r, H and W at g equal the record rule's on the same
      packet, bit for bit, for every task, case and horizon
  Q5  aliases: the alias table is complete; a row listed twice gives the same lineage bit for bit (the controller's row,
      500 updates, its switch reading)
  Q6  reanalysis: the endpoints recomputed from the saved states equal the shards'
  Q7  efficacy: the detector reads V and r only (a short lineage of the controller's rows with the patch moved gives the
      same states and the same switches, bit for bit); the footprint is the zone dilated by 2 and the open bonds its
      touching bonds; each generation's switch starts closed, fires once and stays open to the generation's end; the
      oracle opens at read_from over the patch; the open mask's size (bonds) is the open bonds' count at the
      generation's end; post-damage differs from protected exactly in the patch; every task is a saved record of its
      stage
  Q8  pairing: reordering the rows changes no row's output (500 updates, the controller and the oracle among them)
  Q9  resources: the development forecast structurally (this stage's CPU per branch-generation times the development's
      own row-generations, its rows built at generation 0: packets compared, no successor run), within CAP CPU-hours and
      12 h of wall on 10 workers; worker memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output <= 256 KiB
The receipt: --debug -> ROOT/debug_qualification_receipt.json; otherwise e2e005/frozen/qualification_receipt.json.
"""
from __future__ import annotations

import argparse
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

from be002 import sim as B2S  # noqa: E402
from e2e001 import sim as E1  # noqa: E402
from e2e004 import sim as E4  # noqa: E402
from e2e005 import design as D  # noqa: E402
from e2e005 import sim  # noqa: E402
from e2e005 import worker as WK  # noqa: E402
from msegrid.core import birth  # noqa: E402
from sm005 import checks as K5  # noqa: E402  (the lane's parallel check runner, unchanged)
from sr001 import sim as SRS  # noqa: E402

CAP = 27.0                               # the lead's cap for phase B (phase-A ruling 5, sent 13:23:43Z on 5 November)
FROZEN = LANE / "e2e005" / "frozen"


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
        k, nr = len(meta["cases"]), len(meta["rows"])
        name = f"{src}/{body}/{unit}/{block}"
        for e in E1.ENDPOINTS:
            if ends[f"g0/{e}"].shape != (nr, k) or not np.isfinite(ends[f"g0/{e}"]).all():
                bad.append(f"{name} g0/{e}")
        gmax = max(r["stop"] for r in meta["rows"])
        for f in range(meta["futures"]):
            for g in range(1, gmax + 1):
                alive = [i for i, r in enumerate(meta["rows"]) if r["stop"] >= g]
                if list(ends.get(f"f{f}/d{g}/rows", [])) != alive:
                    bad.append(f"{name} f{f}/d{g} rows")
                    continue
                for e in sim.DIAGS:
                    v = ends[f"f{f}/d{g}/{e}"]
                    if v.shape != (len(alive), k) or not np.isfinite(v).all():
                        bad.append(f"{name} f{f}/d{g}/{e}")
                if g not in D.HORIZONS:
                    continue
                if list(ends.get(f"f{f}/g{g}/rows", [])) != alive:
                    bad.append(f"{name} f{f}/g{g} rows")
                    continue
                for e in E1.ENDPOINTS:
                    v = ends[f"f{f}/g{g}/{e}"]
                    if v.shape != (len(alive), k) or not np.isfinite(v).all():
                        bad.append(f"{name} f{f}/g{g}/{e}")
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


def _first(rows):
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    return (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())


def _rows_of(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    raw, rmeta, _rf, cases, V0, ema0, R0, th, T, pattern, theta = WK.inputs(src, body, unit, block, M["stage"])
    _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
    lins = WK.stage_lineages(M["stage"])
    rows, labels, aliases, sources = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, lins)
    _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
    Tf = SRS.foreign(T, pattern, cases)
    return (src, body, unit, block), raw, rmeta, cases, V0, ema0, R0, th * theta, T, Tf, m, rows, labels, aliases, meta


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
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, Tf, m, rows, labels, aliases, meta = _rows_of(root)
    body, k, tag, win = key[1], len(cases), "mse-q3", 1000
    each = {}
    # (a) the fixed routes against e2e004.sim.generation itself
    fx = [dict(packet=rows[labels[lab]]["packet"], route=lab.split("/")[0]) for lab in ("record/protected", "body/protected",
                                                                                     "vote/post")]
    routes = [x["route"] for x in fx]
    idx = np.tile(np.arange(k), len(fx))
    nb = birth(tag, cases, *sim.BIRTH_NAMES(0)(1), side=D.SIDE)[idx]
    outs = []
    for mine in (False, True):
        A_ = _first(fx)
        groups = (sim.groups_of if mine else E4.groups_of)(routes, k)
        B_ = tuple(x[dict(groups)["vote"]].copy() for x in A_)
        if mine:
            (V, E, A2, B2), _sw = sim.run_generation(body, groups, cases, nb.copy(), nb.copy(), A_, B_, thf[idx], tag,
                                                     sim.GEN_NAMES(0)(1), win)
        else:
            V, E, A2, B2 = E4.generation(body, groups, cases, nb.copy(), nb.copy(), A_, B_, thf[idx], tag,
                                         sim.GEN_NAMES(0)(1), win)
        outs.append((V, E) + tuple(A2) + tuple(B2))
    each["fixed routes = e2e004.sim.generation"] = all(np.array_equal(x, y) for x, y in zip(*outs))
    # (b) a never-opening switch = the record route; a whole-sheet switch from update 1 = the body route
    for lab in ("protected", D.POST):
        src_row = rows[labels[f"record/{'protected' if lab == 'protected' else 'post'}"]]
        mrows = [dict(packet=src_row["packet"], route=x) for x in ("record", "ctl", "body", "oracle")]
        idx4 = np.tile(np.arange(k), 4)
        groups = sim.groups_of([x["route"] for x in mrows], k)
        nb4 = birth(tag, cases, *sim.BIRTH_NAMES(0)(1), side=D.SIDE)[idx4]
        cfgs = {"ctl": {"never": True}, "oracle": {"full": True, "d": 0, "duration": None}}
        (V, E, A2, _B), sw = sim.run_generation(body, groups, cases, nb4.copy(), nb4.copy(), _first(mrows), None,
                                                thf[idx4], tag, sim.GEN_NAMES(0)(1), win, cfgs=cfgs)
        part = lambda x, j: x[j * k:(j + 1) * k]
        each[f"{lab}: never-opening switch = record"] = all(np.array_equal(part(x, 0), part(x, 1)) for x in (V, E) + tuple(A2))
        each[f"{lab}: whole-sheet switch = body"] = all(np.array_equal(part(x, 2), part(x, 3)) for x in (V, E) + tuple(A2))
    ok = all(each.values())
    return {"pass": not raw_bad and not rec_bad and ok, "raw_files": len(tasks), "raw_differ": raw_bad[:5],
            "task_bridges_differ": rec_bad[:5], "bridge_task": list(key), "updates": win, "bit_for_bit": each}


def q4(root):
    M, tasks = tasks_of(root)
    bad, never, fired, n = [], 0, 0, 0
    for src, body, unit, block, t in tasks:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        states, _ = npz(Path(root) / t["files"]["raw"]["path"])
        k = len(meta["cases"])
        lab = meta["labels"]
        for c_lab, r_lab in (("ctl/protected", "record/protected"), ("ctl/post", "record/post"), ("ctl/vms", "record/vms")):
            if c_lab not in lab or r_lab not in lab:
                continue
            ic, ir = lab[c_lab], lab[r_lab]
            ever = np.zeros(k, bool)
            gmax = max(r["stop"] for r in meta["rows"])
            for g in range(1, gmax + 1):
                drows = list(ends[f"f0/d{g}/rows"])
                if ic not in drows:
                    break
                ever |= ends[f"f0/d{g}/fired"][drows.index(ic)] > 0
                if g not in D.HORIZONS or f"f0/g{g}/rows" not in states:
                    continue
                srows = list(states[f"f0/g{g}/rows"])
                for j in range(k):
                    n += 1
                    if ever[j]:
                        fired += 1
                        continue
                    never += 1
                    a, b = srows.index(ic) * k + j, srows.index(ir) * k + j
                    if not all(np.array_equal(states[f"f0/g{g}/{x}"][a], states[f"f0/g{g}/{x}"][b]) for x in ("V", "r", "H", "W")):
                        bad.append(f"{src}/{body}/{unit}/{block} {c_lab} g{g} case {j}")
    return {"pass": not bad and n > 0, "case_horizons": n, "never_fired": never, "fired_by_then": fired,
            "never_fired_differ_from_record": bad[:10]}


def _mini(body, rows, cases, thf, T, Tf, m, tag, t_gen=500, gens=1, cfgs=None):
    _r, _a, kept, dg = sim.lineage(body, [dict(row, stop=gens) for row in rows], cases, thf, T, Tf, m, tag,
                                   sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), t_gen=t_gen, horizons=(), keep=(gens,), cfgs=cfgs)
    return kept[gens], dg


def q5(root):
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, Tf, m, rows, labels, aliases, meta = _rows_of(root)
    complete = set(labels) == set(meta["labels"]) and all(labels[l] == meta["labels"][l] for l in labels)
    share = all(all(labels[l] == i for l in row["labels"]) for i, row in enumerate(rows))
    k = len(cases)
    i = labels["ctl/post"]
    early = {"ctl": dict(D.DETECTOR, read_from=100)}
    kept, dg = _mini(key[1], [rows[i], rows[i]], cases, thf, T, Tf, m, meta["tag"], cfgs=early)
    V, r = kept["V"].reshape(2, k, D.SIDE, D.SIDE), kept["r"].reshape(2, k, D.SIDE, D.SIDE)
    twice = bool(np.array_equal(V[0], V[1]) and np.array_equal(r[0], r[1])
                 and all(np.array_equal(dg[1][e][0], dg[1][e][1]) for e in sim.DIAGS))
    return {"pass": bool(complete and share and twice), "complete": bool(complete), "rows_share_packets": bool(share),
            "listed_twice_identical": twice, "aliases": aliases}


def q6(root):
    M, tasks = tasks_of(root)
    bad, n = [], 0
    for task in tasks[:4]:
        src, body, unit, block, t = task
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        states, _ = npz(Path(root) / t["files"]["raw"]["path"])
        raw, rmeta, _rf, cases, V0, ema0, R0, th, T, pattern, theta = WK.inputs(src, body, unit, block, M["stage"])
        k = len(cases)
        Tf = SRS.foreign(T, pattern, cases)
        _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
        for f in range(meta["futures"]):
            for g in D.HORIZONS:
                if f"f{f}/g{g}/rows" not in ends:
                    continue
                alive = list(ends[f"f{f}/g{g}/rows"])
                idx = np.tile(np.arange(k), len(alive))
                sc = sim.score(states[f"f{f}/g{g}/V"], states[f"f{f}/g{g}/r"], T[idx], Tf[:, idx], m[idx])
                for e, v in sc.items():
                    n += 1
                    if not np.array_equal(v.reshape(len(alive), k), ends[f"f{f}/g{g}/{e}"]):
                        bad.append(f"{src}/{body}/{unit}/{block} f{f}/g{g}/{e}")
    return {"pass": not bad and n > 0, "compared": n, "differ": bad[:10]}


def q7(root):
    M, tasks = tasks_of(root)
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, Tf, m, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    out = {}
    pick = [rows[labels[lab]] for lab in ("ctl/protected", "ctl/post", "oracle/post")]
    early = {"ctl": dict(D.DETECTOR, read_from=100), "oracle": dict(D.ORACLE, read_from=100)}
    seen = []
    real = sim.run_generation

    def spy(*args, **kw):
        res, sw = real(*args, **kw)
        seen.append(sw)
        return res, sw

    sim.run_generation = spy
    try:
        keptA, dgA = _mini(key[1], pick, cases, thf, T, Tf, m, meta["tag"], t_gen=600, gens=2, cfgs=early)
        swA = list(seen)
        seen.clear()
        m2 = np.roll(m, (8, 8), (-2, -1))                       # the patch moved: the controller's rows must not change
        keptB, dgB = _mini(key[1], pick[:2], cases, thf, T, Tf, m2, meta["tag"], t_gen=600, gens=2, cfgs=early)
        swB = list(seen)
    finally:
        sim.run_generation = real
    same_states = all(np.array_equal(keptA[x][:2 * k], keptB[x]) for x in ("V", "r", "H", "W"))
    same_switch = all(np.array_equal(getattr(swA[g]["ctl"], a), getattr(swB[g]["ctl"], a)) for g in range(2)
                      for a in ("t_on", "zone", "fp", "nwin"))
    out["detector_reads_V_and_r_only"] = bool(same_states and same_switch and list(
        __import__("inspect").signature(sim.windows).parameters) == ["V", "r", "cfg"])
    geo = True
    for g in range(2):
        for route in ("ctl", "oracle"):
            s = swA[g][route]
            fired = s.t_on > 0
            geo &= bool(np.array_equal(s.fp[fired], B2S.footprint(s.zone[fired], D.FOOT_D)) and not s.fp[~fired].any())
            mk = s.masks(600)
            if fired.any():
                fp = s.fp & fired[:, None, None]
                geo &= bool(mk is not None and np.array_equal(mk[0], fp | np.roll(fp, -1, -1))
                            and np.array_equal(mk[1], fp | np.roll(fp, -1, -2)))
            geo &= bool((s.t_on[fired] <= 600).all())
            want = np.zeros(len(s.t_on)) if mk is None else (mk[0].sum((-2, -1)) + mk[1].sum((-2, -1))).astype(float)
            got = dgA[g + 1]["bonds"][:2].ravel() if route == "ctl" else dgA[g + 1]["bonds"][2]
            geo &= bool(np.array_equal(got, want))
    out["footprint_and_open_bonds"] = geo
    out["fresh_switch_each_generation"] = bool(len(swA) == 2 and swA[0]["ctl"] is not swA[1]["ctl"]
                                               and all(dgA[g]["t_on"].shape == (3, k) for g in (1, 2)))
    o = swA[0]["oracle"]
    out["oracle_opens_at_read_from_over_the_patch"] = bool((o.t_on == 100).all() and np.array_equal(o.zone, m)
                                                           and np.array_equal(o.fp, B2S.footprint(m, D.FOOT_D)))
    (Hp, Wp, rp), mm = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
    out["post_damage_patch_only"] = bool(np.array_equal(rp[~mm], R0[~mm]) and np.array_equal(rp[mm], -R0[mm]))
    out["tasks_are_saved_records"] = bool({(s, b, u, blk) for s, b, u, blk, _ in tasks}
                                          <= set(map(tuple, D.stage_tasks(M["stage"]))))
    return {"pass": all(out.values()), **out}


def q8(root):
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, Tf, m, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    pick = [rows[labels[lab]] for lab in ("record/protected", "ctl/post", "vote/post", "oracle/post")]
    early = {"ctl": dict(D.DETECTOR, read_from=100), "oracle": dict(D.ORACLE, read_from=100)}
    a, _da = _mini(key[1], pick, cases, thf, T, Tf, m, meta["tag"], cfgs=early)
    b, _db = _mini(key[1], pick[::-1], cases, thf, T, Tf, m, meta["tag"], cfgs=early)
    n = len(pick)
    same = all(np.array_equal(a[x].reshape(n, k, D.SIDE, D.SIDE), b[x].reshape(n, k, D.SIDE, D.SIDE)[::-1])
               for x in ("V", "r", "H", "W"))
    return {"pass": bool(same), "reordered_identical": bool(same)}


def q9(root):
    M, tasks = tasks_of(root)
    done, cpu = 0, 0.0
    for src, body, unit, block, t in tasks:
        _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
        done += len(meta["cases"]) * sum(r["stop"] for r in meta["rows"]) * meta["futures"]
        cpu += t["cpu_s"]
    rate = cpu / done
    dev = 0
    for s, b, u, blk in D.stage_tasks("development"):
        raw, rmeta, _rf, cases, V0, ema0, R0, th, T, pattern, theta = WK.inputs(s, b, u, blk, "development")
        rows, _l, _al, _src = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, D.lineages("development"))
        dev += len(cases) * sum(r["stop"] for r in rows) * D.FUTURES["development"]
    forecast = rate * dev / 3600
    wall10 = forecast / 10
    rss = max(t["maxrss_mb"] for *_x, t in tasks)
    return {"pass": bool(forecast <= CAP and wall10 <= 12 and rss <= 2048), "forecast_dev_cpu_h": round(forecast, 2),
            "forecast_dev_wall_h_10": round(wall10, 2), "cpu_s_per_branch_generation": round(rate, 4),
            "dev_branch_generations": dev, "worker_rss_mb": rss, "cap": CAP}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "e2e005.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "e2e005.tables", "--dir", str(out)], capture_output=True, text=True, env=env,
                        cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from e2e005 import predict as PR
    ok = (p1.returncode == 0 and p2.returncode == 0 and len(scored.get("parts", [])) == len(PR.parts())
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr)[-600:], "sizes": sizes, "parts_scored": len(scored.get("parts", []))}


def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", default=None)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root), "Q3_bridges": lambda: q3(root), "Q5_aliases": lambda: q5(root),
             "Q7_efficacy": lambda: q7(root), "Q8_pairing": lambda: q8(root), "Q9_resources": lambda: q9(root)}
    light = {"Q1_complete_finite": lambda: q1(root), "Q4_never_fired_is_record": lambda: q4(root),
             "Q6_reanalysis": lambda: q6(root), "Q10_reader_dry_run": lambda: q10(root)}
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
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_never_fired_is_record", "Q5_aliases",
             "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed, "->", path)


if __name__ == "__main__":
    main()
