"""SM006's qualification Q1-Q10 (DRAFT): python -m sm006.checks --root STAGE_ROOT --fit-gain-root ROOT [--receipt PATH]
[--cpus LIST]

Fixed before their results (PLAN_SM006.md); run on the preflight's rereads (SM004's 900470-900471) at the full shape.
  Q1  complete and finite: every task's new reads at their shapes, finite; the bodies at theirs; the 48 FIT gain rereads
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and bodies
  Q3  the bridges: every task's base reread equals the saved g 1 reads (every sign-based endpoint, every read) and every
      refined task's 1/(2 sqrt 2) read equals SM005's E read; every FIT gain task's control equals SM003's FIT reread's;
      one FIT gain task rerun under the current sources equals its shard bit for bit
  Q4  an independent replay from the definitions (sm005.checks.replay at the base parameters with the gain x 1/4) of one
      branch: the final body within 1e-8, E exact
  Q5  aliases: the no-record control's final body is the same under every gain factor of a task
  Q6  reanalysis: E recomputed from the saved final bodies within 1/64
  Q7  efficacy: the erasure sizes at side 64 and g 1 re-measured equal design.EPS; every condition present; every task a
      saved record of its stage (no block drawn)
  Q8  pairing: a branch listed twice under a gain factor gives identical outputs; reordering changes none
  Q9  resources: the development (the FIT gain rereads as measured plus TEST forecast from this stage over 32 blocks)
      within 35 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB
  Q10 the reader's dry run: the model refitted by the rule equals the frozen one; predict and tables complete; every
      candidate scored; every output <= 256 KiB
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from lr005 import sim as L5S  # noqa: E402
from sm001 import design as S1D  # noqa: E402
from sm001 import sim as S1  # noqa: E402
from sm004 import fitread4 as F4R  # noqa: E402
from sm005 import checks as K5  # noqa: E402
from sm005 import design as D5  # noqa: E402
from sm005 import worker as W5  # noqa: E402
from sm006 import design as D  # noqa: E402
from sm006 import fitread as FR  # noqa: E402
from sm006 import worker as Wk  # noqa: E402

FROZEN = LANE / "sm006" / "frozen"


def _tasks(root):
    M = json.loads((root / "manifest.json").read_text())
    return M, sorted(tuple(k.rsplit("/", 2)) for k in M["tasks"])


def q1(root, fit_root):
    M, tasks = _tasks(root)
    bad = []
    for s, u, b in tasks:
        z, zb = (np.load(root / kind / Wk.key(s) / u / f"{b}.npz") for kind in ("shards", "bodies"))
        na, k, side = len(S1D.unit_arms(u)), S1D.NCASE, S1D.UNIT[u]["side"]
        for L in S1D.UNIT[u]["sizes"]:
            for f in D.TEST_FACTORS[S1D.UNIT[u]["kind"]]:
                fn = D.F_NAME[f]
                for e in Wk.ENDS:
                    x = z[f"L{L}/g1/{fn}/{e}"]
                    if x.shape != (na + 1, k) or not np.isfinite(x).all():
                        bad.append([s, u, b, L, fn, e])
                if zb[f"L{L}/g1/{fn}/V"].shape != (na + 1, k, side, side):
                    bad.append([s, u, b, L, fn, "V"])
    FM = json.loads((fit_root / "manifest.json").read_text())
    want = sorted((s, u, str(b)) for s, u, b in D.stage_tasks(M["stage"]))
    return {"pass": not bad and sorted(tasks) == want and len(FM["tasks"]) == 48, "tasks": len(tasks), "bad": bad[:10],
            "fit_gain_tasks": len(FM["tasks"])}


def q2(root):
    _M, tasks = _tasks(root)
    s, u, b = tasks[0]
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(s, u, int(b), tmp)
        diff, n = [], 0
        for kind in ("shards", "bodies"):
            x, y = np.load(root / kind / Wk.key(s) / u / f"{b}.npz"), np.load(Path(tmp) / kind / Wk.key(s) / u / f"{b}.npz")
            for kk in x.files:
                if kk != "__meta__":
                    n += 1
                    if not np.array_equal(x[kk], y[kk]):
                        diff.append(f"{kind}/{kk}")
    return {"pass": not diff, "task": [s, u, b], "arrays": n, "differ": diff[:10]}


def q3(root, fit_root):
    M, _tasks_ = _tasks(root)
    FMg = json.loads((fit_root / "manifest.json").read_text())
    out = {"every_task_bridge": bool(M["bridge_all_equal"] and all(t["bridge_all_equal"] for t in M["tasks"].values())),
           "every_fit_gain_control_bridge": bool(FMg["bridge_all_equal"])}
    FM = F4R.fit_manifest()
    with tempfile.TemporaryDirectory() as tmp:
        FR.run_task(tmp, "W8_x32", 910628, FM["tasks"]["W8_x32/910628"]["files"])
        za, zb = np.load(fit_root / "shards" / "W8_x32" / "910628.npz"), np.load(Path(tmp) / "shards" / "W8_x32" / "910628.npz")
        keys = [k for k in za.files if k != "__meta__"]
        out["fit_gain_task_rerun_bit_for_bit"] = bool(all(np.array_equal(za[k], zb[k]) for k in keys))
    return {"pass": all(out.values()), **out}


def q4(root):
    _M, tasks = _tasks(root)
    s, u, b = [t for t in tasks if t[1] == "W16_x64_r2"][0]
    raw, _shard, cases, tag, _ = W5.load_task(s, u, int(b))
    side, w, na, k = 64, S1D.UNIT[u]["w"], len(S1D.unit_arms(u)), len(cases)
    r, H, W = F4R.branches(raw, "L8", na, k, side)
    T, m = raw["T"].astype(np.float64), raw["L8/m"]
    ai = [a["name"] for a in S1D.unit_arms(u)].index("dial-c2-m2-t3000")
    j = ai * k
    f = 0.25
    o = S1.successor(r[j:j + 1], H[j:j + 1], W[j:j + 1], cases[:1], np.zeros((1, side, side)), T[:1], m[:1], side, w,
                     [S1D.GAIN * f], tag=tag, reads=(S1D.WINDOW2,))
    V = K5.replay(r[j], H[j], W[j], cases[0], tag, dict(D5.BASE), S1D.GAIN * f)
    e = float(L5S.inside(V[None], T[:1], m[:1])[0])
    dV = float(np.abs(o["V"][0] - V).max())
    return {"pass": dV <= 1e-8 and e == float(o["in"][-1][0]), "branch": [s, u, b, "L8", "dial-c2-m2-t3000", "case 0", f],
            "max_dV": dV, "E_replay": e, "E": float(o["in"][-1][0])}


def q5(root):
    _M, tasks = _tasks(root)
    ok = True
    for s, u, b in tasks:
        zb = np.load(root / "bodies" / Wk.key(s) / u / f"{b}.npz")
        na = len(S1D.unit_arms(u))
        for L in S1D.UNIT[u]["sizes"]:
            cs = [zb[f"L{L}/g1/{D.F_NAME[f]}/V"][na] for f in D.TEST_FACTORS[S1D.UNIT[u]["kind"]]]
            ok &= all(np.array_equal(cs[0], c) for c in cs[1:])
    return {"pass": bool(ok), "controls_alike_across_factors": bool(ok)}


def q6(root):
    _M, tasks = _tasks(root)
    worst = 0.0
    for s, u, b in tasks:
        raw, _shard, cases, _tag, _ = W5.load_task(s, u, int(b))
        z, zb = (np.load(root / kind / Wk.key(s) / u / f"{b}.npz") for kind in ("shards", "bodies"))
        T = raw["T"].astype(float)
        na, k = len(S1D.unit_arms(u)), len(cases)
        for L in S1D.UNIT[u]["sizes"]:
            m = raw[f"L{L}/m"]
            for f in D.TEST_FACTORS[S1D.UNIT[u]["kind"]]:
                fn = D.F_NAME[f]
                V = zb[f"L{L}/g1/{fn}/V"].astype(np.float64)
                e = np.array([[L5S.inside(V[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
                worst = max(worst, float(np.abs(e - z[f"L{L}/g1/{fn}/in"]).max()))
    return {"pass": worst <= 1.0 / 64, "max_abs_diff": worst}


def q7(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location("p55s", LANE / "probes" / "p55s_sm006_smoke.py")
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    cases = P.P5.island_cases()
    k, side, sizes = len(cases), 64, D.ISLAND_SIZES[64]
    nb = len(sizes)
    r, H, W, m = P.P5.islands(cases, side, sizes)
    T1, m1, th = np.ones((k, side, side)), np.ones((k, side, side), bool), np.zeros((k, side, side))
    size = lambda V: max([l for si, l in enumerate(sizes)
                          if ((V[si * k:(si + 1) * k] > 0) & m[si * k:(si + 1) * k]).sum() / m[si * k:(si + 1) * k].sum() >= 0.5],
                         default=0)
    got = {}
    for f in (1.0,) + D.F_GRID:
        o = S1.successor(r, H, W, cases, th, T1, m1, side, 2, [S1D.GAIN * f] * nb, tag=P.P5.ISL_TAG, reads=(S1D.WINDOW2,))
        got[f"64/1/{D.F_NAME[f]}"] = size(o["V"])
    M, tasks = _tasks(root)
    want = sorted((s, u, str(b)) for s, u, b in D.stage_tasks(M["stage"]))
    out = {"eps_measured": got, "eps_equal_design": all(got[kk] == D.EPS[kk] for kk in got),
           "tasks_are_saved_records": sorted(tasks) == want}
    return {"pass": bool(out["eps_equal_design"] and out["tasks_are_saved_records"]), **out}


def q8(root):
    _M, tasks = _tasks(root)
    s, u, b = [t for t in tasks if t[1] == "W16_x64_r2"][0]
    raw, _shard, cases, tag, _ = W5.load_task(s, u, int(b))
    side, w, na, k = 64, S1D.UNIT[u]["w"], len(S1D.unit_arms(u)), len(cases)
    r, H, W = F4R.branches(raw, "L4", na, k, side)
    T, m = raw["T"].astype(np.float64), raw["L4/m"]
    a1, a2 = slice(2 * k, 3 * k), slice(5 * k, 6 * k)
    g = S1D.GAIN * 0.5
    call = lambda sl, gs: S1.successor(np.concatenate([r[x] for x in sl]), np.concatenate([H[x] for x in sl]),
                                       np.concatenate([W[x] for x in sl]), cases, np.zeros_like(T), T, m, side, w, gs, tag=tag,
                                       reads=(S1D.WINDOW2,))
    x, y = call((a1, a1, a2), [g] * 3), call((a2, a1), [g] * 2)
    twice = np.array_equal(x["V"][:k], x["V"][k:2 * k])
    order = np.array_equal(x["V"][:k], y["V"][k:]) and np.array_equal(x["V"][2 * k:], y["V"][:k])
    return {"pass": bool(twice and order), "listed_twice": bool(twice), "reordered": bool(order)}


def q9(root, fit_root):
    M, tasks = _tasks(root)
    FM = json.loads((fit_root / "manifest.json").read_text())
    per = {}
    for kk, t in M["tasks"].items():
        per.setdefault(kk.rsplit("/", 2)[1], []).append(t["cpu_s"])
    n_blocks = len(D.stage_tasks("development")) // len(D.UNITS)
    test = sum(np.mean(per[u]) for u in D.UNITS) * n_blocks / 3600
    fit = FM["cpu_s_total"] / 3600
    wall = max(test * 3600 / 12, max(max(v) for v in per.values())) / 3600
    rss = max(M["worker_maxrss_mb_peak"], FM["worker_maxrss_mb_peak"])
    ok = test + fit <= 35 and wall <= 12 and rss <= 2048
    return {"pass": bool(ok), "forecast_test_cpu_h": round(test, 2), "fit_gain_cpu_h": round(fit, 2),
            "forecast_dev_cpu_h": round(test + fit, 2), "forecast_test_wall_h_12": round(wall, 2), "worker_rss_mb": rss}


def q10(root, fit_root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "sm006.analyze", "fit", "--fit-gain-root", str(fit_root), "--out",
                         str(out / "model.json")], capture_output=True, text=True, env=env, cwd=LANE)
    model = FROZEN / "model.json" if (FROZEN / "model.json").exists() else out / "model.json"
    p2 = subprocess.run([sys.executable, "-m", "sm006.predict", "--root", str(root), "--model", str(model), "--fit-gain-root",
                         str(fit_root), "--out", str(out)], capture_output=True, text=True, env=env, cwd=LANE)
    p3 = subprocess.run([sys.executable, "-m", "sm006.tables", "--dir", str(out), "--model", str(model)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    same = True
    if (FROZEN / "model.json").exists() and (out / "model.json").exists():
        a, b = json.loads((FROZEN / "model.json").read_text()), json.loads((out / "model.json").read_text())
        same = (a["chosen"] == b["chosen"] and a["model"]["terms"] == b["model"]["terms"]
                and float(np.abs(np.array(a["model"]["beta"]) - np.array(b["model"]["beta"])).max()) <= 1e-9)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    ok = (p1.returncode == 0 and p2.returncode == 0 and p3.returncode == 0 and same and len(scored.get("parts", [])) == 11
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "refit_equals_frozen": bool(same), "stderr": (p1.stderr + p2.stderr + p3.stderr)[-600:],
            "sizes": sizes, "parts_scored": len(scored.get("parts", []))}


def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--fit-gain-root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--cpus", default=None)
    a = ap.parse_args()
    root, fit_root = a.root.resolve(), a.fit_gain_root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root), "Q3_bridges": lambda: q3(root, fit_root),
             "Q4_replay": lambda: q4(root), "Q7_efficacy": lambda: q7(root), "Q8_pairing": lambda: q8(root)}
    light = {"Q1_complete_finite": lambda: q1(root, fit_root), "Q5_aliases": lambda: q5(root), "Q6_reanalysis": lambda: q6(root),
             "Q9_resources": lambda: q9(root, fit_root), "Q10_reader_dry_run": lambda: q10(root, fit_root)}
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
