"""SM005's qualification Q1-Q10 (DRAFT): python -m sm005.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST]

Fixed before their results (PLAN_SM005.md); run on the preflight's rereads (SM004's 900470-900471) at the full shape. Any
failure stops the campaign.
  Q1  complete and finite: every task's endpoints for the five readers at their shapes, finite; the bodies at theirs
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and bodies
  Q3  the bridges: (a) every task's base and cg rereads equal the saved g 1 and cg reads (every sign-based endpoint, every
      read; the spacing and the body recorded); (b) cg against SM002's definitions: on a 2x upsampled side-32 record cg at
      side 64 equals SM001's reader at side 32 bit for bit; (c) every variant at its base setting equals the base bit for
      bit (C at coupling 1, dt 0.2, 2,000 updates, gain x 1; E at gain x 1; B on a record whose bonds have a 2-site grain)
  Q4  an independent replay from the definitions (the body and record steps written out, B's bond map by explicit loops)
      of one C, one E and one B branch: the final body within 1e-8, E exact
  Q5  aliases: the no-record control's final body is the same under base, E and B (gain 0)
  Q6  reanalysis: E recomputed from the saved final bodies (float32; cg lifted) within 1/64 of the saved endpoints
  Q7  efficacy: the erasure sizes re-measured (base; C at G_C equal to the base's; E at G_E at least twice it); C's
      multiplier in (-0.5, 1); every refined condition present (27 late, 54 prompt, the control) in every task; every task
      a saved record of its stage (no block drawn)
  Q8  pairing: a variant branch listed twice gives identical outputs, and reordering the branches changes none
  Q9  resources: the development (96 tasks) forecast from this stage's tasks within 35 CPU-hours and 12 h of wall on 12
      workers, worker memory within 2 GB, disk headroom
  Q10 the reader's dry run: predict and tables complete on this stage, every candidate scored, every output <= 256 KiB
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
from dataclasses import replace

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from lr005 import sim as L5S  # noqa: E402
from mse.assay import BIRTH_SCALE  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from sm001 import design as S1D  # noqa: E402
from sm001 import sim as S1  # noqa: E402
from sm002 import coarse as C  # noqa: E402
from sm003 import checks as K3  # noqa: E402
from sm004 import fitread4 as F4R  # noqa: E402
from sm005 import design as D  # noqa: E402
from sm005 import readers as RD  # noqa: E402
from sm005 import worker as Wk  # noqa: E402


def _tasks(root):
    M = json.loads((root / "manifest.json").read_text())
    return M, sorted(tuple(k.rsplit("/", 2)) for k in M["tasks"])


def _record(source, unit, block, L):
    raw, _shard, cases, tag, _ = Wk.load_task(source, unit, int(block))
    cfg = S1D.UNIT[unit]
    na, k, side, w = len(S1D.unit_arms(unit)), len(cases), cfg["side"], cfg["w"]
    r, H, W = F4R.branches(raw, f"L{L}", na, k, side)
    return r, H, W, cases, raw["T"].astype(np.float64), raw[f"L{L}/m"], side, w, [S1D.GAIN] * na + [0.0], tag


def q1(root):
    M, tasks = _tasks(root)
    bad = []
    for s, u, b in tasks:
        z = np.load(root / "shards" / Wk.key(s) / u / f"{b}.npz")
        zb = np.load(root / "bodies" / Wk.key(s) / u / f"{b}.npz")
        na, k, side = len(S1D.unit_arms(u)), S1D.NCASE, S1D.UNIT[u]["side"]
        for L in S1D.UNIT[u]["sizes"]:
            for rd in D.READERS:
                for e in RD.ENDS:
                    x = z[f"L{L}/{rd}/{e}"]
                    if x.shape != (na + 1, k) or not np.isfinite(x).all():
                        bad.append([s, u, b, L, rd, e])
                sv = side // 2 if rd == "cg" else side
                if zb[f"L{L}/{rd}/V"].shape != (na + 1, k, sv, sv):
                    bad.append([s, u, b, L, rd, "V"])
    want = sorted((s, u, str(b)) for s, u, b in D.stage_tasks(M["stage"]))
    return {"pass": not bad and sorted(tasks) == want, "tasks": len(tasks), "bad": bad[:10]}


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


def q3(root):
    M, tasks = _tasks(root)
    out = {"a_every_task_bridge_equal": bool(M["bridge_all_equal"] and all(t["bridge_all_equal"] for t in M["tasks"].values()))}
    s, u, b = tasks[0]
    r, H, W, cases, T, m, side, w, gains, tag = _record(s, u, b, 4)
    # (b) cg against SM002's definitions: a 2x upsampled side-32 record
    rc, Hc, Wc = C.coarse_grain(r, H, W)
    ru, Hu, Wu = C.upsample(rc, Hc, Wc)
    Tc, mc = C.coarse_template(T), C.coarse_mask(m)
    ref = S1.successor(rc, Hc, Wc, cases, np.zeros_like(Tc), Tc, mc, side // 2, w // 2, gains, tag=tag, stream="dw")
    got = C.read_cg(ru, Hu, Wu, cases, np.zeros_like(T), C.lift(Tc), C.lift(mc), side, w, gains, tag=tag, stream="dw")
    out["b_cg_returns_record"] = bool(all(np.array_equal(x, y) for x, y in zip(C.coarse_grain(ru, Hu, Wu), (rc, Hc, Wc))))
    out["b_cg_equals_successor_at_half_side"] = bool(np.array_equal(got["Vc"], ref["V"]))
    # (c) every variant at its base setting
    base = S1.successor(r, H, W, cases, np.zeros_like(T), T, m, side, w, gains, tag=tag, reads=(S1D.WINDOW2,))
    same = lambda o, ref: bool(np.array_equal(o["V"], ref["V"]) and np.array_equal(o["in"], ref["in"][-1]))
    out["c_C_at_base_setting"] = same(RD.read_variant("C", r, H, W, cases, T, m, side, w, gains, tag, g_c=1.0, coupling=1.0,
                                                      dt=0.2, window=2000, sigma=S1D.SIGMA, eps=S1D.EPS,
                                                      sigma_r=S1D.SIGMA_R), base)
    out["c_E_at_gain_x1"] = same(RD.read_variant("E", r, H, W, cases, T, m, side, w, gains, tag, g_e=1.0), base)
    Hb, Wb = RD.coarse_bonds(ru, Hu, Wu)
    refu = S1.successor(ru, Hu, Wu, cases, np.zeros_like(T), T, m, side, w, gains, tag=tag, reads=(S1D.WINDOW2,))
    out["c_B_bond_map_identity_on_2_grain"] = bool(np.array_equal(Hb, Hu) and np.array_equal(Wb, Wu))
    out["c_B_on_2_grain_equals_base"] = same(RD.read_variant("B", ru, Hu, Wu, cases, T, m, side, w, gains, tag), refu)
    return {"pass": all(out.values()), "record": [s, u, b, "L4"], **out}


def _bonds_loops(r, H, W):
    """B's bond map by explicit loops: SM002's 2 x 2 rule (a bond the majority of the two crossing fine bonds, a tie the
    coarse record's relation, +1 if 0), lifted back (bonds inside a block +1, across blocks the coarse bond)."""
    s = r.shape[0] // 2
    rc = np.zeros((s, s))
    for i in range(s):
        for j in range(s):
            rc[i, j] = ((r[2 * i, 2 * j] + r[2 * i, 2 * j + 1]) + (r[2 * i + 1, 2 * j] + r[2 * i + 1, 2 * j + 1])) * 0.25
    Hf, Wf = np.ones_like(r), np.ones_like(r)
    for i in range(s):
        for j in range(s):
            jn, i_n = (j + 1) % s, (i + 1) % s
            h = H[2 * i, 2 * j + 1] + H[2 * i + 1, 2 * j + 1]
            rel = np.sign(rc[i, j] * rc[i, jn])
            hc = np.sign(h) if h != 0 else (rel if rel != 0 else 1.0)
            v = W[2 * i + 1, 2 * j] + W[2 * i + 1, 2 * j + 1]
            rel = np.sign(rc[i, j] * rc[i_n, j])
            wc = np.sign(v) if v != 0 else (rel if rel != 0 else 1.0)
            Hf[2 * i, 2 * j + 1] = Hf[2 * i + 1, 2 * j + 1] = hc
            Wf[2 * i + 1, 2 * j] = Wf[2 * i + 1, 2 * j + 1] = wc
    return Hf, Wf


def replay(r, H, W, case, tag, cfg, gain):
    """One branch from the definitions: a fresh dw body from newborn noise (BIRTH_SCALE, centred) reading the protected
    record, the body's step and pull and the record's step through its bonds written out."""
    if cfg["bonds"] == "coarse2":
        H, W = _bonds_loops(r, H, W)
    side = r.shape[0]
    g0 = address(tag, *case.key(), "successor", D.STREAM).standard_normal((side, side))
    V = BIRTH_SCALE * (g0 - g0.mean())
    gz = address(tag, *case.key(), "successor-future", D.STREAM)
    gx = address(tag, *case.key(), "successor-record-noise", D.STREAM)
    p = replace(NATIVE, sigma=cfg["sigma"], coupling=cfg["coupling"], dt=cfg["dt"])
    rr = r.copy()
    nb = lambda x: (np.roll(x, 1, 0) + np.roll(x, -1, 0) + np.roll(x, 1, 1) + np.roll(x, -1, 1)) / 4.0
    zs = xs = None
    for t in range(1, cfg["window"] + 1):
        i = (t - 1) % S1D.CHUNK
        if i == 0:
            zs, xs = gz.standard_normal((S1D.CHUNK, side, side)), gx.standard_normal((S1D.CHUNK, side, side))
        drift = V - V ** 3 + p.well_asym + 0.0 + p.coupling * (nb(V) - V)
        Vt = np.clip(V + p.dt * drift + p.sigma * zs[i], -p.bound, p.bound)
        V = np.clip(Vt + p.dt * gain * cfg["gain_x"] * (rr - Vt), -p.bound, p.bound)
        bsum = (np.roll(W, 1, 0) * np.roll(rr, 1, 0) + W * np.roll(rr, -1, 0) + np.roll(H, 1, 1) * np.roll(rr, 1, 1)
                + H * np.roll(rr, -1, 1)) / 4.0
        rr = np.clip(rr + cfg["eps"] * (rr * (1 - (rr / 1.2) ** 2) + cfg["kr"] * (bsum - rr)) + cfg["sigma_r"] * xs[i], -2.0, 2.0)
    return V


def q4(root):
    _M, tasks = _tasks(root)
    s, u, b = [t for t in tasks if t[1] == "W16_x64_r2"][0]
    r, H, W, cases, T, m, side, w, gains, tag = _record(s, u, b, 8)
    na, k = len(S1D.unit_arms(u)), len(cases)
    ai = [a["name"] for a in S1D.unit_arms(u)].index("dial-c2-m2-t3000")
    out = {"branch": [s, u, b, "L8", "dial-c2-m2-t3000", "case 0"]}
    j = ai * k
    for v in D.VARIANTS:
        o = RD.read_variant(v, r[j:j + 1], H[j:j + 1], W[j:j + 1], cases[:1], T[:1], m[:1], side, w, [S1D.GAIN], tag)
        V = replay(r[j], H[j], W[j], cases[0], tag, D.variant(v), S1D.GAIN)
        e = float(L5S.inside(V[None], T[:1], m[:1])[0])
        out[v] = {"max_dV": float(np.abs(o["V"][0] - V).max()), "E_replay": e, "E": float(o["in"][0])}
    ok = all(out[v]["max_dV"] <= 1e-8 and out[v]["E_replay"] == out[v]["E"] for v in D.VARIANTS)
    return {"pass": bool(ok), **out}


def q5(root):
    _M, tasks = _tasks(root)
    ok = True
    for s, u, b in tasks:
        zb = np.load(root / "bodies" / Wk.key(s) / u / f"{b}.npz")
        na = len(S1D.unit_arms(u))
        for L in S1D.UNIT[u]["sizes"]:
            c0 = zb[f"L{L}/base/V"][na]
            ok &= bool(np.array_equal(c0, zb[f"L{L}/E/V"][na]) and np.array_equal(c0, zb[f"L{L}/B/V"][na]))
    return {"pass": bool(ok), "controls_alike_base_E_B": bool(ok)}


def q6(root):
    _M, tasks = _tasks(root)
    worst = 0.0
    for s, u, b in tasks:
        raw, _shard, cases, _tag, _ = Wk.load_task(s, u, int(b))
        z = np.load(root / "shards" / Wk.key(s) / u / f"{b}.npz")
        zb = np.load(root / "bodies" / Wk.key(s) / u / f"{b}.npz")
        T = raw["T"].astype(float)
        na, k = len(S1D.unit_arms(u)), len(cases)
        for L in S1D.UNIT[u]["sizes"]:
            m = raw[f"L{L}/m"]
            for rd in D.READERS:
                V = zb[f"L{L}/{rd}/V"].astype(np.float64)
                V = C.lift(V) if rd == "cg" else V
                e = np.array([[L5S.inside(V[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
                worst = max(worst, float(np.abs(e - z[f"L{L}/{rd}/in"]).max()))
    return {"pass": worst <= 1.0 / 64, "max_abs_diff": worst}


def q7(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location("p54s", LANE / "probes" / "p54s_sm005_smoke.py")
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    cases = P.island_cases()
    k, side, sizes = len(cases), 64, D.ISLAND_SIZES
    nb = len(sizes)
    r, H, W, m = P.islands(cases, side, sizes)
    T1, m1 = np.ones((k, side, side)), np.ones((k, side, side), bool)
    size = lambda V: max([l for si, l in enumerate(sizes)
                          if ((V[si * k:(si + 1) * k] > 0) & m[si * k:(si + 1) * k]).sum() / m[si * k:(si + 1) * k].sum() >= 0.5],
                         default=0)
    er = {"base": size(RD.reader(r, H, W, cases, T1, m1, side, 2, [S1D.GAIN] * nb, P.ISL_TAG, **D.BASE)["V"])}
    for v in ("C", "E", "B"):
        er[v] = size(RD.reader(r, H, W, cases, T1, m1, side, 2, [S1D.GAIN] * nb, P.ISL_TAG, **D.variant(v))["V"])
    cfg = D.variant("C")
    vv = 1.0
    for _ in range(4000):
        vt = vv + cfg["dt"] * (vv - vv ** 3)
        vv = vt + cfg["dt"] * S1D.GAIN * cfg["gain_x"] * (1.2 - vt)
    mult = (1 + cfg["dt"] * (1 - 3 * vv * vv - 2 * cfg["coupling"])) * (1 - cfg["dt"] * S1D.GAIN * cfg["gain_x"])
    M, tasks = _tasks(root)
    conds_ok = True
    for s, u, b in tasks:
        arms = S1D.unit_arms(u)
        conds_ok &= sum(a["m"] == 2 for a in arms) == 3 and sum(a["m"] == 0 for a in arms) == 6 and u in D.REFINE
    want = sorted((s, u, str(b)) for s, u, b in D.stage_tasks(M["stage"]))
    out = {"erasure_sizes": er, "C_holds_base_erasure": er["C"] == er["base"], "E_doubles_erasure": er["E"] >= 2 * er["base"],
           "C_multiplier": mult, "C_stable": -0.5 < mult < 1, "conditions": bool(conds_ok),
           "tasks_are_saved_records": sorted(tasks) == want and all(D.SOURCES[s] for s, _u, _b in tasks)}
    return {"pass": bool(out["C_holds_base_erasure"] and out["E_doubles_erasure"] and out["C_stable"] and conds_ok
                         and out["tasks_are_saved_records"]), **out}


def q8(root):
    _M, tasks = _tasks(root)
    s, u, b = [t for t in tasks if t[1] == "W16_x64_r2"][0]
    r, H, W, cases, T, m, side, w, gains, tag = _record(s, u, b, 4)
    k = len(cases)
    a1, a2 = slice(2 * k, 3 * k), slice(5 * k, 6 * k)
    x = RD.read_variant("E", np.concatenate([r[a1], r[a1], r[a2]]), np.concatenate([H[a1], H[a1], H[a2]]),
                        np.concatenate([W[a1], W[a1], W[a2]]), cases, T, m, side, w, [S1D.GAIN] * 3, tag)
    y = RD.read_variant("E", np.concatenate([r[a2], r[a1]]), np.concatenate([H[a2], H[a1]]), np.concatenate([W[a2], W[a1]]),
                        cases, T, m, side, w, [S1D.GAIN] * 2, tag)
    twice = np.array_equal(x["V"][:k], x["V"][k:2 * k])
    order = np.array_equal(x["V"][:k], y["V"][k:]) and np.array_equal(x["V"][2 * k:], y["V"][:k])
    return {"pass": bool(twice and order), "listed_twice": bool(twice), "reordered": bool(order)}


def q9(root):
    M, tasks = _tasks(root)
    per = {}
    for kk, t in M["tasks"].items():
        per.setdefault(kk.rsplit("/", 2)[1], []).append(t["cpu_s"])
    n_dev = len(D.stage_tasks("development"))
    dev = sum(np.mean(per[u]) for u in D.REFINE) / len(D.REFINE) * n_dev / 3600
    longest = max(max(v) for v in per.values())
    wall = max(dev * 3600 / 12, longest) / 3600
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"] * (n_dev / max(1, len(tasks)))
    ok = dev <= 35 and wall <= 12 and M["worker_maxrss_mb_peak"] <= 2048 and disk
    return {"pass": bool(ok), "forecast_dev_cpu_h": round(dev, 2), "forecast_dev_wall_h_12": round(wall, 2),
            "worker_rss_mb": M["worker_maxrss_mb_peak"], "disk_headroom": bool(disk)}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "sm005.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm005.tables", "--dir", str(out)], capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    ok = (p1.returncode == 0 and p2.returncode == 0 and len(scored.get("parts", [])) == 12 and (out / "TABLES.md").exists()
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr)[-600:], "sizes": sizes, "parts_scored": len(scored.get("parts", []))}


_HEAVY = {}


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
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_replay", "Q5_aliases", "Q6_reanalysis",
             "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
