"""SM004's qualification Q1-Q10 (DRAFT): python -m sm004.checks --root STAGE_ROOT --fit-g4-root FIT_G4_ROOT
[--receipt PATH] [--cpus LIST]

Fixed before their results; run on the preflight blocks at the full shape (the six units), with the FIT rereads at three
grains. Any failure stops the campaign. SM003's checks (sm003.checks), with SM004's changes:
  Q1  complete and finite: every TEST endpoint at its declared shape (g = 4 exactly where w >= 8; sm003.checks.q1, which
      also requires SM003's 48 FIT rereads complete and finite); the 32 g-4 FIT rereads complete, at their shapes, finite
  Q2  serial equals parallel: one task rerun in-process by sm004.worker.run_task gives bit-identical shards and raw states
  Q3  the bridges: (a) SM004's task (the stage's shard and raw record of W8_x64_r2) equals sm003.worker.task called
      in-process on the same unit, block and tag, every array; (a2) one P45 task (W8_x64, 900476, tag mse-p45) rerun
      under the current sources equals P45's shard and raw record bit for bit; (b) SM003's FIT rereads intact (every
      file's sha256, the g = 1 bridge to SM001 in all 48, the manifest the frozen model names), and one g-4 FIT task
      (W8_x32, 910628) rerun under the current sources equals its shard bit for bit, every source the g-4 rereads ran under
      equal to today's outside sm004/ and for sm004/fitread4.py; (c) the exactness at side 64 (SM003's Q3c: on 4x
      upsampled side-16 records g = 4 equals the unscaled reader at side 16) and at the FIT's side 32 (a FIT record
      coarse-grained twice and upsampled x 4 is returned exactly, and g = 4 on it equals SM001's successor at side 8,
      stream dw-cg4, bit for bit, the lifted score equal to the unlifted one)
  Q4  the independent replay of g = 4 (sm003.checks.replay_g4) on one refined TEST branch (sm003.checks.q4) and on one
      FIT branch (W16_x32, 910628, L 8, dial-c2-m2-t3000, case 0): the coarse body within 1e-8, the lifted score exact
  Q5  aliases (sm003.checks.q5)
  Q6  reanalysis within 1/64 (sm003.checks.q6), and the g-4 FIT reads' E recomputed from their saved coarse bodies
  Q7  efficacy: SM003's items on the stage, and the FIT rows: 864 (648 at g 1 and 2; 216 at g 4, exactly W8_x32 and
      W16_x32), the g = 1 rows' E equal to SM001's FIT shards; every SM004 identity inside mse.assay.RANGES, none shared
      with SM003's, SM001's FIT or AR004's holds
  Q8  pairing (sm003.checks.q8)
  Q9  resources: the development (the g-4 FIT rereads as measured, plus TEST forecast from this stage's tasks over 16
      blocks) within 35 CPU-hours, 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom
  Q10 the reader's dry run: the model refitted by the rule equals the frozen blob's choice and coefficients (within
      1e-9) when sm004/frozen/model.json exists; predict and tables complete on this stage; every candidate scored; every
      output file <= 256 KB; the two frozen sensitivities carry their recorded sha256, their scoring path gives the
      model's own values with the model as the stand-in, and neither is computed on this stage (the lead's ruling)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as S1D  # noqa: E402
from sm001 import sim as S1  # noqa: E402
from sm002 import coarse as C  # noqa: E402
from sm003 import checks as K3  # noqa: E402
from sm003 import readers as RD  # noqa: E402
from sm003 import worker as W3  # noqa: E402
from sm004 import design as D  # noqa: E402
from sm004 import fitread4 as F4R  # noqa: E402
from sm004 import worker as Wk  # noqa: E402

FROZEN = LANE / "sm004" / "frozen"


def _same_files(a_root, b_root, unit, block):
    diff, n = [], 0
    for kind in ("shards", "raw"):
        a, b = np.load(Path(a_root) / kind / unit / f"{block}.npz"), np.load(Path(b_root) / kind / unit / f"{block}.npz")
        ka, kb = sorted(x for x in a.files if x != "__meta__"), sorted(x for x in b.files if x != "__meta__")
        if ka != kb:
            diff.append(f"{kind}: names differ")
        for x in ka:
            n += 1
            if x not in b.files or not np.array_equal(a[x], b[x]):
                diff.append(f"{kind}/{x}")
    return diff, n


def q1(root, pairs, fit_g4_root):
    base = K3.q1(root, pairs, Path(D.FIT12_ROOT))
    RM = json.loads((fit_g4_root / "manifest.json").read_text())
    bad = []
    for key, t in RM["tasks"].items():
        u = key.split("/")[0]
        z = np.load(fit_g4_root / t["file"]["path"])
        na, side = len(S1D.unit_arms(u)), S1D.UNIT[u]["side"]
        for L in S1D.UNIT[u]["sizes"]:
            for e in RD.ENDS:
                x = z[f"L{L}/g4/{e}"]
                if x.shape != (na + 1, S1D.NCASE) or not np.isfinite(x).all():
                    bad.append([key, L, e])
            if z[f"L{L}/g4/V"].shape != (na + 1, S1D.NCASE, side // 4, side // 4):
                bad.append([key, L, "V"])
    want = sorted(f"{u}/{b}" for u, b in F4R.pairs())
    ok = base["pass"] and not bad and sorted(RM["tasks"]) == want and len(want) == 32
    return {"pass": bool(ok), "test_and_sm003_fit": base, "g4_fit_tasks": len(RM["tasks"]), "g4_fit_bad": bad[:10]}


def q2(root, pair, tag, purpose):
    u, b = pair
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(u, b, purpose, tmp, tag)
        diff, n = _same_files(root, tmp, u, b)
    return {"pass": not diff, "task": [u, b], "arrays": n, "differ": diff[:10]}


def q3a(root, block, tag, purpose):
    unit = "W8_x64_r2"
    ends, raw, _, _ = W3.task(unit, block, purpose, tag)
    z, zr = np.load(root / "shards" / unit / f"{block}.npz"), np.load(root / "raw" / unit / f"{block}.npz")
    names_ok = sorted(ends) == sorted(k for k in z.files if k != "__meta__") and sorted(raw) == sorted(k for k in zr.files if k != "__meta__")
    same = [np.array_equal(ends[kk], z[kk]) for kk in ends] + [np.array_equal(raw[kk], zr[kk]) for kk in raw]
    return {"pass": bool(names_ok and all(same)), "a_sm004_task_equals_sm003_task": bool(names_ok and all(same)), "a_items": len(same)}


def q3a2():
    unit, block = D.PROBE_BRIDGE
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(unit, block, D.PROBE_PURPOSE, tmp, D.PROBE_TAG)
        diff, n = _same_files(D.PROBE_ROOT, tmp, unit, block)
    return {"pass": not diff, "a2_p45_task_bit_for_bit": not diff, "a2_task": [unit, block], "a2_arrays": n, "a2_differ": diff[:10]}


def q3bc(fit_g4_root, block, tag, purpose):
    import hashlib
    out = {}
    RM12 = json.loads((Path(D.FIT12_ROOT) / "manifest.json").read_text())
    files_ok = all(hashlib.sha256((Path(D.FIT12_ROOT) / t["file"]["path"]).read_bytes()).hexdigest() == t["file"]["sha256"]
                   for t in RM12["tasks"].values())
    out["b_sm003_fit_rereads_intact"] = bool(files_ok and RM12["bridge_all_equal"] and len(RM12["tasks"]) == 48
                                             and all(t["bridge_all_equal"] for t in RM12["tasks"].values()))
    if (FROZEN / "model.json").exists():
        blob = json.loads((FROZEN / "model.json").read_text())
        out["b_frozen_model_names_these_rereads"] = (
            blob["fit12_manifest_sha256"] == hashlib.sha256((Path(D.FIT12_ROOT) / "manifest.json").read_bytes()).hexdigest()
            and blob["fit_g4_manifest_sha256"] == hashlib.sha256((fit_g4_root / "manifest.json").read_bytes()).hexdigest())
    FM = F4R.fit_manifest()
    with tempfile.TemporaryDirectory() as tmp:
        F4R.run_task(tmp, "W8_x32", 910628, FM["tasks"]["W8_x32/910628"]["files"])
        za, zb = np.load(fit_g4_root / "shards" / "W8_x32" / "910628.npz"), np.load(Path(tmp) / "shards" / "W8_x32" / "910628.npz")
        keys = [k for k in za.files if k != "__meta__"]
        out["b_g4_fit_task_rerun_bit_for_bit"] = bool(sorted(keys) == sorted(k for k in zb.files if k != "__meta__")
                                                      and all(np.array_equal(za[k], zb[k]) for k in keys))
        out["b_g4_fit_task_arrays"] = len(keys)
    RM4 = json.loads((fit_g4_root / "manifest.json").read_text())
    now, rec = D.sources(LANE), RM4["sources"]
    keys = [k for k in set(rec) | set(now) if not k.startswith("sm004/")] + ["sm004/fitread4.py"]
    out["b_g4_fit_sources_equal"] = bool(all(rec.get(k) == now.get(k) and rec.get(k) is not None for k in keys))
    out["b_g4_fit_sources_compared"] = len(keys)
    # (c) at side 64: SM003's Q3c on 4x upsampled side-16 records
    arms = [a for a in S1D.unit_arms("W4_x32") if a["name"] in ("dial-c1-m2-t3000", "dial-c2-m0-t30")]
    cases, V0, ema0, R0, th, T = S1.prepare("W4", 16, block, purpose)
    k = len(cases)
    o = S1.run(2, arms, cases, V0, ema0, R0, th, T, 16, 4, tag=tag)
    pick = lambda x: np.concatenate([x, x[:k]])
    r, H, W = pick(o["r"]), pick(o["H"]), pick(o["W"])
    gains = [S1D.GAIN] * len(arms) + [0.0]
    ref = S1.successor(r, H, W, cases, th, T, o["m"], 16, 4, gains, tag=tag, reads=(S1D.WINDOW2,), stream="dw")
    up = lambda x: C.lift(C.lift(x))
    rf, Hf, Wf = C.upsample(*C.upsample(r, H, W))
    got = RD.read_g4(rf, Hf, Wf, cases, up(th), up(T), up(o["m"]), 64, 16, gains, tag, stream="dw")
    out["c64_coarse4_returns_the_record"] = bool(all(np.array_equal(a, b) for a, b in zip(RD.coarse4(rf, Hf, Wf), (r, H, W))))
    out["c64_V_bit_for_bit"] = bool(np.array_equal(got["V"], ref["V"]))
    out["c64_lifted_in_equals_unlifted"] = bool(np.array_equal(got["in"], ref["in"][-1]))
    # (c) at the FIT's side 32
    unit, blk, L = "W16_x32", 910628, 4
    raw, _, fcases = F4R.load_records(unit, blk, FM["tasks"][f"{unit}/{blk}"]["files"])
    cfg = S1D.UNIT[unit]
    side, w, na, kk = cfg["side"], cfg["w"], len(S1D.unit_arms(unit)), len(fcases)
    rr, HH, WW = F4R.branches(raw, f"L{L}", na, kk, side)
    rc, Hc, Wc = RD.coarse4(rr, HH, WW)
    T8 = C.coarse_template(C.coarse_template(raw["T"].astype(np.float64)))
    m8 = C.coarse_mask(C.coarse_mask(raw[f"L{L}/m"]))
    rf, Hf, Wf = C.upsample(*C.upsample(rc, Hc, Wc))
    g2 = [S1D.GAIN] * na + [0.0]
    o4 = RD.read_g4(rf, Hf, Wf, fcases, np.zeros((kk, side, side)), up(T8), up(m8.astype(np.int8)).astype(bool), side, w, g2,
                    D.FIT_TAG)
    o8 = S1.successor(rc, Hc, Wc, fcases, np.zeros_like(T8), T8, m8, side // 4, w // 4, g2, tag=D.FIT_TAG,
                      reads=(S1D.WINDOW2,), stream=D.STREAMS[4])
    out["c32_coarse4_returns_the_record"] = bool(all(np.array_equal(a, b) for a, b in zip(RD.coarse4(rf, Hf, Wf), (rc, Hc, Wc))))
    out["c32_V_bit_for_bit"] = bool(np.array_equal(o4["V"], o8["V"]))
    out["c32_lifted_in_equals_unlifted"] = bool(np.array_equal(o4["in"], o8["in"][-1]))
    ok = all(v for kk2, v in out.items() if not kk2.endswith(("_arrays", "_compared")))
    return {"pass": bool(ok), **out}


def q4(block, tag, purpose):
    test = K3.q4(block, tag, purpose)
    unit, blk, L, arm = "W16_x32", 910628, 8, "dial-c2-m2-t3000"
    FM = F4R.fit_manifest()
    raw, _, cases = F4R.load_records(unit, blk, FM["tasks"][f"{unit}/{blk}"]["files"])
    side, w, k = S1D.UNIT[unit]["side"], S1D.UNIT[unit]["w"], len(cases)
    ai = [a["name"] for a in S1D.unit_arms(unit)].index(arm)
    r, H, W = (raw[f"L{L}/{x}"].astype(np.float64).reshape(-1, side, side)[ai * k: ai * k + 1] for x in ("r", "H", "W"))
    T, m = raw["T"].astype(np.float64)[:1], raw[f"L{L}/m"][:1]
    got = RD.read_g4(r, H, W, cases[:1], np.zeros_like(T), T, m, side, w, [S1D.GAIN], D.FIT_TAG)
    V = K3.replay_g4(r[0], H[0], W[0], cases[0], D.FIT_TAG, D.STREAMS[4], S1D.GAIN, S1D.WINDOW2)
    dV = float(np.abs(got["V"][0] - V).max())
    Vf = np.repeat(np.repeat(V, 4, 0), 4, 1)
    e = float((((Vf > 0) == (T[0] > 0)) & m[0]).sum() / m[0].sum())
    fit = {"pass": dV <= 1e-8 and e == float(got["in"][0]), "branch": [unit, blk, f"L{L}", arm, "case 0"], "max_dV": dV,
           "E_replay": e, "E_g4": float(got["in"][0])}
    return {"pass": bool(test["pass"] and fit["pass"]), "test_branch": test, "fit_branch": fit}


def q6(root, pairs, fit_g4_root):
    from lr005 import sim as L5S
    base = K3.q6(root, pairs)
    worst = 0.0
    FM = F4R.fit_manifest()
    for u, b in [("W8_x32", 910628), ("W16_x32", 910643)]:
        z = np.load(fit_g4_root / "shards" / u / f"{b}.npz")
        raw, _, cases = F4R.load_records(u, b, FM["tasks"][f"{u}/{b}"]["files"])
        T = raw["T"].astype(float)
        na, k = len(S1D.unit_arms(u)), len(cases)
        for L in S1D.UNIT[u]["sizes"]:
            V = RD.lift4(z[f"L{L}/g4/V"].astype(np.float64))
            m = raw[f"L{L}/m"]
            e = np.array([[L5S.inside(V[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
            worst = max(worst, float(np.abs(e - z[f"L{L}/g4/in"]).max()))
    return {"pass": bool(base["pass"] and worst <= 1.0 / 64), "test": base, "g4_fit_max_abs_diff": worst}


def q7(root, pairs, fit_g4_root):
    from mse.assay import RANGES
    from sm003 import design as D3
    from sm004 import analyze as A
    out = {}
    base = K3.q7(root, pairs, Path(D.FIT12_ROOT))
    out.update({k: v for k, v in base.items() if k not in ("pass", "identities_in_ranges")})
    fr = A.fit_rows(fit_g4_root)
    g4 = [r for r in fr if r["g"] == 4]
    out["fit_rows_864"] = (len(fr) == 864 and len(g4) == 216 and sorted({r["unit"] for r in g4}) == sorted(D.FIT_G4_UNITS)
                           and len([r for r in fr if r["g"] in (1, 2)]) == 648)
    eng = list(D.SMOKE_BLOCKS) + list(D.DEBUG_BLOCKS) + list(D.SPARE_BLOCKS) + list(D.IDENTITIES["preflight"])
    dev = list(D.IDENTITIES["test"]) + list(D.RESERVE)
    holds = set(range(910017, 910020)) | set(range(910057, 910060)) | set(range(910077, 910080)) | set(range(910097, 910100)) \
        | set(range(910117, 910120)) | {910137, 910138, 910139} | set(range(910157, 910160))
    sm003 = set(D3.IDENTITIES["preflight"]) | set(D3.IDENTITIES["test"]) | set(D3.RESERVE) | set(D3.PROBE_BLOCKS) \
        | set(D3.DEBUG_BLOCKS) | set(D3.SMOKE_BLOCKS) | set(D3.SPARE_BLOCKS)
    out["identities_in_ranges_and_free"] = (all(b in RANGES["engineering"] for b in eng) and all(b in RANGES["development"] for b in dev)
                                            and len(set(eng + dev)) == len(eng + dev) and len(D.IDENTITIES["test"]) == 16
                                            and not set(eng + dev) & (holds | sm003 | set(D.FIT_BLOCKS)))
    return {"pass": bool(all(out.values())), **out}


def q9(root, fit_g4_root):
    M = json.loads((root / "manifest.json").read_text())
    RM = json.loads((fit_g4_root / "manifest.json").read_text())
    per = {}
    for key, t in M["tasks"].items():
        per.setdefault(key.split("/")[0], []).append(t["cpu_s"])
    test = sum(np.mean(per[u]) for u in D.UNITS) * len(D.IDENTITIES["test"]) / 3600
    fit = RM["cpu_s_total"] / 3600
    longest = max(max(v) for v in per.values())
    wall = max(test * 3600 / 12, longest) / 3600
    rss = max(M["worker_maxrss_mb_peak"], RM["worker_maxrss_mb_peak"])
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"] * 4
    ok = test + fit <= 35 and wall <= 12 and rss <= 2048 and disk
    return {"pass": bool(ok), "forecast_test_cpu_h": round(test, 2), "g4_fit_reread_cpu_h": round(fit, 3),
            "forecast_dev_cpu_h": round(test + fit, 2), "forecast_test_wall_h_12": round(wall, 2), "worker_rss_mb": rss,
            "disk_headroom": bool(disk)}


def q10(root, fit_g4_root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "sm004.analyze", "fit", "--fit-g4-root", str(fit_g4_root), "--out",
                         str(out / "model.json")], capture_output=True, text=True, env=env, cwd=LANE)
    model = FROZEN / "model.json" if (FROZEN / "model.json").exists() else out / "model.json"
    p2 = subprocess.run([sys.executable, "-m", "sm004.predict", "--root", str(root), "--model", str(model), "--fit-g4-root",
                         str(fit_g4_root), "--out", str(out)], capture_output=True, text=True, env=env, cwd=LANE)
    p3 = subprocess.run([sys.executable, "-m", "sm004.tables", "--root", str(root), "--model", str(model), "--dir", str(out)],
                        capture_output=True, text=True, env=env, cwd=LANE)
    res = {"stderr": (p1.stderr + p2.stderr + p3.stderr)[-600:]}
    same_fit = True
    if (FROZEN / "model.json").exists() and (out / "model.json").exists():
        a, b = json.loads((FROZEN / "model.json").read_text()), json.loads((out / "model.json").read_text())
        same_fit = (a["chosen"] == b["chosen"] and a["model"]["terms"] == b["model"]["terms"]
                    and float(np.abs(np.array(a["model"]["beta"]) - np.array(b["model"]["beta"])).max()) <= 1e-9)
        res["refit_equals_frozen"] = bool(same_fit)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    # the sensitivities (the lead's ruling, 1 November 2026 about 23:53Z): their files carry the recorded sha256, and their scoring path
    # is exercised with the model itself as the stand-in (score_with(.., "new") must equal the model's own values), so
    # neither H2 nor H5 is computed on any stage before TEST
    from sm004 import analyze as A
    from sm004 import predict as PR
    sens_ok = True
    try:
        PR.sensitivity_fits()
    except Exception:
        sens_ok = False
    rows = A.test_rows(root)
    blob = json.loads(model.read_text())
    P = PR.predictions(rows, blob)
    RP = PR.refit_predictions(rows, blob, A.fit_rows(fit_g4_root))
    own = {p["id"]: p for p in PR.score(rows, P, RP)}
    stand = PR.score_with(rows, P, RP, "new")
    same = lambda x, y: x == y or (math.isnan(x) and math.isnan(y))          # a single block's SD is nan
    stand_ok = all(same(p["value"], own[p["id"]]["value"]) and same(p["sd"], own[p["id"]]["sd"]) for p in stand) and len(stand) == 10
    sens_field = scored.get("sensitivities")
    res.update(sensitivity_files_ok=bool(sens_ok), sensitivity_path_stand_in_equal=bool(stand_ok),
               sensitivities_not_computed=isinstance(sens_field, str) and sens_field.startswith("not computed"))
    ok = (p1.returncode == 0 and p2.returncode == 0 and p3.returncode == 0 and same_fit and len(scored.get("parts", [])) == 10
          and (out / "TABLES.md").exists() and all(s <= 256 * 1024 for s in sizes.values()) and sens_ok and stand_ok
          and res["sensitivities_not_computed"])
    return {"pass": bool(ok), **res, "sizes": sizes, "candidates_scored": len(scored.get("parts", []))}


_HEAVY = {}                            # the heavy checks, set before the pool forks (the workers inherit them)


def _pin(q):
    import os
    os.sched_setaffinity(0, {q.get()})


def _run_named(name):
    return _run(name, _HEAVY[name])


def _run(name, fn):
    t1 = time.time()
    try:
        res = fn()
    except Exception as exc:          # a check that cannot run fails
        res = {"pass": False, "error": repr(exc)}
    res["seconds"] = round(time.time() - t1, 1)
    return name, res


def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--fit-g4-root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--cpus", default=None, help="comma-separated CPU ids: the heavy checks run one a core")
    a = ap.parse_args()
    root, fit_g4_root = a.root.resolve(), a.fit_g4_root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    pairs = [tuple(p) for p in M["pairs"]]
    block, tag = pairs[0][1], M["tag"]
    purpose = D.PURPOSE[M["stage"]]
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root, pairs[0], tag, purpose),
             "Q3a": lambda: q3a(root, block, tag, purpose), "Q3a2": q3a2,
             "Q3bc": lambda: q3bc(fit_g4_root, block, tag, purpose), "Q4_replay": lambda: q4(block, tag, purpose),
             "Q8_pairing": lambda: K3.q8(block, tag, purpose)}
    light = {"Q1_complete_finite": lambda: q1(root, pairs, fit_g4_root), "Q5_aliases": lambda: K3.q5(root, pairs),
             "Q6_reanalysis": lambda: q6(root, pairs, fit_g4_root), "Q7_efficacy": lambda: q7(root, pairs, fit_g4_root),
             "Q9_resources": lambda: q9(root, fit_g4_root), "Q10_reader_dry_run": lambda: q10(root, fit_g4_root)}
    checks = {}
    cpus = [int(c) for c in a.cpus.split(",")] if a.cpus else []
    if len(cpus) >= len(heavy):
        ctx = mp.get_context("fork")
        q = ctx.Queue()
        for c in cpus[: len(heavy)]:
            q.put(c)
        _HEAVY.clear()
        _HEAVY.update(heavy)
        with ProcessPoolExecutor(len(heavy), mp_context=ctx, initializer=_pin, initargs=(q,)) as pool:
            futs = [pool.submit(_run_named, name) for name in heavy]
            for name, fn in light.items():
                checks[name] = _run(name, fn)[1]
                print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
            for f in futs:
                name, res = f.result()
                checks[name] = res
                print(name, "PASS" if res["pass"] else "FAIL", res["seconds"], "s", flush=True)
    else:
        for name, fn in {**heavy, **light}.items():
            checks[name] = _run(name, fn)[1]
            print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
    q3 = {"pass": all(checks[k]["pass"] for k in ("Q3a", "Q3a2", "Q3bc")), "a": checks.pop("Q3a"), "a2": checks.pop("Q3a2"),
          "bc": checks.pop("Q3bc")}
    checks["Q3_bridges"] = q3
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_replay", "Q5_aliases", "Q6_reanalysis",
             "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "fit_g4_root": str(fit_g4_root), "blocks": sorted({p[1] for p in pairs}), "tag": tag,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
