"""SM007's qualification Q1-Q10 (DRAFT): python -m sm007.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST]

Fixed in PLAN_SM007.md (Amendments 1 and 2) before their results; in phase A they run on the debug run (AR005's 900799,
the full development set with the paper arm, two futures, a window of 2,000), in phase B on the preflight.
  Q1  complete and finite: every planned task present; every shard's endpoints at the stage's reads and branches (every
      future's, future-major), finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the bridges: at kappa 0 the update equals dl001.sim.run bit for bit (dw and li4: field, isolated, nofield and
      undisturbed); stress, emission and respond equal e2e006.sim.FieldAdapter's; the shared point's and the isolated
      media equal E2E006's; each isolated block equals a one-sheet Medium at every lambda and leak; msefield's P61q
      passes; every restored record rehashes to its manifest's sha256; the paper's stress (Eq. 1) equals a case-by-case
      recomputation written here, starts at or above its separatrix and holds at its high state
  Q4  independent replays: (a) one task's every medium recomputed from the run's traced emissions, and every field gain
      from the previous exposure, over 300 updates at KAPPA, bit for bit; (b) one field group (2x4 absorbing at lambda
      0.5) recomputed end to end over the stage's window by a loop written here, against the stage's final bodies, in
      every future
  Q5  controls by construction (the trace of Q4a's form): every nofield branch reads G_DIST and every undisturbed branch
      G_LANE at every update; a uniform group's exposures equal its own medium's mean; a rearranged group's are its own
      medium's, permuted with no fixed point; every paper branch emits its case's Eq. 1 stress at every update
  Q6  reanalysis: sign and a_v recomputed from the saved final bodies equal the shards' at the last read, every task
  Q7  the boundary of information: the inherited record is never written (rerun, compared); the template enters the
      scoring only (a rerun with -T leaves every body, gain, exposure and stress bit for bit and complements sign); the
      paper's stress never reads the body (a rerun with the record halved leaves every paper emission bit for bit); every
      task's restored record and acquisition matched (its done record); the stage's tasks are its declared blocks
  Q8  pairing: reordering the arrangements changes no arrangement's final bodies (300 updates)
  Q9  resources: phase B's forecast (the preflight and the development, every future) from this stage's CPU per
      branch-update, within the lead's cap of 15 CPU-hours (ruling 7, 13:01:00Z) and 3 h of wall on 10 workers; worker
      memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output <= 256 KiB
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
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from dataclasses import replace  # noqa: E402

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msefield.core import Medium  # noqa: E402
from msegrid.core import Stream, birth  # noqa: E402
from sm005 import checks as K5  # noqa: E402  (the lane's parallel check runner, unchanged)
from sm007 import design as D  # noqa: E402
from sm007 import sim  # noqa: E402
from sm007 import worker as WK  # noqa: E402

CAP = 15.0                               # the lead's phase-B cap (phase-A ruling 7, sent 13:01:00Z)
WALL_H, WORKERS = 3.0, 10


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


def inputs(src, body, unit, block):
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    return cases, R0, th * theta, T


def q1(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    aset = D.STAGE_SETS[stage]
    n = len(sim.layout(aset, 8, D.STAGE_TAG[stage])[0])
    F = D.FUTURES[stage]
    win = D.STAGE_WINDOW.get(stage, D.WINDOW)
    reads = [r for r in D.READS if r <= win] or [win]
    bad = []
    for src, body, unit, block, t in tasks:
        e, meta = npz(Path(root) / t["files"]["shards"]["path"])
        nm = f"{src}/{body}/{unit}/{block}"
        if list(e["reads"]) != reads or e["a_v"].shape != (len(reads), n * F) or e["sign"].shape != (len(reads), n * F):
            bad.append(f"{nm} shapes")
        if not np.array_equal(e["br_future"], np.repeat(np.arange(F), n)) or meta["futures"] != F:
            bad.append(f"{nm} futures")
        for k in ("a_v", "sign", "gain_mean", "expo_mean", "stress_mean"):
            if not np.isfinite(e[k]).all():
                bad.append(f"{nm} {k}")
        if [list(a) for a in meta["arrangements"]] != [list(a) for a in aset] or meta["window"] != win:
            bad.append(f"{nm} arrangements or window")
    want = set(map(tuple, D.stage_tasks(stage)))
    have = {(s, b, u, blk) for s, b, u, blk, _ in tasks}
    return {"pass": not bad and have == want, "tasks": len(tasks), "branches_a_future": n, "futures": F, "reads": reads,
            "bad": bad[:10], "missing": sorted(map(str, want - have))[:5]}


def q2(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    ends, states, meta, bridge = WK.task(src, body, unit, block, M["stage"])
    e0, _ = npz(Path(root) / t["files"]["shards"]["path"])
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    differ = [k for k in e0 if not np.array_equal(e0[k], ends[k])] + [k for k in s0 if not np.array_equal(s0[k], states[k])]
    return {"pass": not differ and set(e0) == set(ends) and set(s0) == set(states), "task": [src, body, unit, block],
            "arrays": len(e0) + len(s0), "differ": differ[:10]}


def q3(root):
    import hashlib
    import msefield
    from e2e006 import sim as E6
    sys.path.insert(0, str(LANE / "probes"))
    import p61q_msefield_qualification as P61Q
    M, tasks = tasks_of(root)
    src, _b, unit, block, _t = tasks[0]
    cases, R0, thf, T = inputs(src, "dw", unit, block)
    k = len(cases)
    V_init = np.stack([0.1 * np.random.default_rng(11 + j).standard_normal((D.SIDE, D.SIDE)) for j in range(k)])
    arrs = [("2x4/absorbing", "2x4", "absorbing", "field", D.LAMBDA),
            ("iso8/absorbing/shared", "iso8", "absorbing", "field", D.LAMBDA_SHARED),
            ("nofield", "iso8", None, "nofield", None), ("undisturbed", "iso8", None, "undisturbed", None)]
    out = {}
    for body in ("dw", "li4"):
        refs = {g: S.run(body, V_init.copy(), V_init.copy(), R0.copy(), np.full(k, g), thf, T, cases, D.SIGMA, 300, ())["final"]
                for g in (D.G_DIST, D.G_LANE)}
        res = sim.run(body, arrs, cases, R0, thf, T, D.STAGE_TAG[M["stage"]], kappa=0.0, window=300, reads=(),
                      stream=Stream(DL.TAG, cases, "future", side=D.SIDE), V_init=V_init.copy())
        for ai, a in enumerate(arrs):
            b = np.flatnonzero(res["br_arr"] == ai)
            ref = refs[D.G_LANE if a[3] == "undisturbed" else D.G_DIST]
            out[f"kappa0/{body}/{a[0]}"] = bool(np.array_equal(res["V"][b], ref[res["br_case"][b]]))
    ad = E6.FieldAdapter(msefield.core)
    rng = np.random.default_rng(7)
    fn_ok = True
    for _ in range(20):
        V, Vt, drift, d, r = (rng.standard_normal((12, D.SIDE, D.SIDE)) for _ in range(5))
        s1 = sim.stress(V, Vt, drift, d, r)
        fn_ok &= bool(np.array_equal(s1, ad.stress(V=V, Vt=Vt, drift=drift, d=d, r=r)))
        fn_ok &= bool(np.array_equal(sim.emission(s1), ad.emission(s1)))
        c = rng.uniform(0, 15, (12, 1, 1))
        g2, _t, _p = ad.respond(c, np.ones((12, 1, 1), bool), np.full((12, 1, 1), D.KAPPA), gain=D.G_DIST, thb=None, p=None)
        fn_ok &= bool(np.array_equal(sim.respond(c, D.KAPPA, D.G_DIST), g2))
    out["functions_e2e006"] = fn_ok
    attrs = ("pos", "D", "gamma", "leak", "dt", "m", "margin", "nsub", "dts", "shape")
    for mine, theirs, name in ((sim.medium("2x4", "absorbing", D.LAMBDA_SHARED), ad.medium(8), "shared"),
                               (sim.medium("iso8", "absorbing", D.LAMBDA_SHARED), ad.medium_isolated(), "isolated")):
        out[f"medium_e2e006/{name}"] = all(np.array_equal(np.asarray(getattr(mine, x)), np.asarray(getattr(theirs, x)))
                                           for x in attrs)
    for lam in (D.LAMBDA, D.LAMBDA2, D.LAMBDA_SHARED):
        for bd in ("absorbing", "half", "sealed"):
            Mi = sim.medium("iso8", bd, lam)
            Ms = [Medium([(0, 0)], D.d_field(lam), D.GAMMA, D.LEAKS[bd], dt=1.0, m=D.SITES[lam], margin=D.MARGIN)
                  for _ in range(8)]
            ok = True
            for _t in range(100):
                e = rng.uniform(0, 2, 8)
                ok &= bool(np.array_equal(Mi.step(e), np.array([Ms[j].step(e[j:j + 1])[0] for j in range(8)])))
            out[f"isolated/{lam}/{bd}"] = ok
    out["p61q"] = all(ok for case in P61Q.CASES for _n, _v, _b, ok in case())
    Sp = sim.paper_trajectory(D.STAGE_TAG[M["stage"]], cases, 0, 400)   # (not S: that is dl001.sim here)
    ok_p = True
    for j in range(k):
        Sj = sim.paper_init(D.STAGE_TAG[M["stage"]], cases[j:j + 1], 0)
        ok_p &= bool(Sj[0] >= D.PAPER_SSTAR)
        for t in range(400):
            for _s in range(D.PAPER["k"]):
                Sj = Sj + D.PAPER["dt_sub"] * (D.PAPER["P_max"] * Sj ** 2 / (D.PAPER["K"] ** 2 + Sj ** 2)
                                               - D.PAPER["delta_S"] * Sj)
            ok_p &= bool(Sj[0] == Sp[t, j])
    out["paper_stress_recomputed"] = ok_p
    out["paper_stress_holds_high"] = bool(abs(Sp[-1] - D.PAPER_SHIGH).max() < 1e-12)
    rehash = []
    for s, body, unit, blk, _t in tasks:
        root_s = Path(D.SOURCES[s]["root"])
        f = json.loads((root_s / "manifest.json").read_text())["tasks"][f"{body}/{unit}/{blk}"]["files"]["raw"]
        rehash.append(hashlib.sha256((root_s / f["path"]).read_bytes()).hexdigest() == f["sha256"])
    out["records_rehash"] = all(rehash)
    return {"pass": all(out.values()), **out}


def _trace(root, window=300):
    M, tasks = tasks_of(root)
    src, body, unit, block, _t = tasks[0]
    cases, R0, thf, T = inputs(src, body, unit, block)
    aset = D.STAGE_SETS[M["stage"]]
    res = sim.run(body, aset, cases, R0, thf, T, D.STAGE_TAG[M["stage"]], window=window, reads=(), keep_final=False,
                  trace_until=window)
    _bc, _ba, groups = sim.layout(aset, len(cases), D.STAGE_TAG[M["stage"]])
    res["S_paper"] = sim.paper_trajectory(D.STAGE_TAG[M["stage"]], cases, 0, window)
    return res, groups, window


def _kappa(g):
    return D.KAPPA_PAPER if g["kind"] == "paper" else D.KAPPA


def q4(root):
    res, groups, W = _trace(root)
    tr = res["trace"]
    ok_x = ok_g = True
    for g in groups:
        if g["kind"] not in sim.FIELD_KINDS:
            continue
        b = g["branches"]
        Mg = sim.medium(g["shape"], g["boundary"], g["lam"])
        for t in range(W):
            x = Mg.step(tr["emission"][t][b])
            x = np.full(len(x), x.mean()) if g["kind"] == "uniform" else (x[g["perm"]] if g["kind"] == "rearranged" else x)
            ok_x &= bool(np.array_equal(tr["exposure"][t][b], x))
            prev = tr["exposure"][t - 1][b] if t else np.zeros(len(b))
            ok_g &= bool(np.array_equal(tr["gain"][t][b], D.G_DIST * (1.0 + _kappa(g) * prev)))
    # (b) one field group end to end in every future, written out here
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    cases, R0, thf, T = inputs(src, body, unit, block)
    stage = M["stage"]
    tag, win = D.STAGE_TAG[stage], D.STAGE_WINDOW.get(stage, D.WINDOW)
    aset = D.STAGE_SETS[stage]
    br_case, br_arr, groups = sim.layout(aset, len(cases), tag)
    n = len(br_case)
    ai = [a[0] for a in aset].index("2x4/absorbing")
    g = [x for x in groups if x["arr"] == ai][0]
    idx = g["cases"]
    alpha, L = DL.BODIES[body]
    Gk = S.ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    ok_e2e = []
    for fu in range(D.FUTURES[stage]):
        V = birth(tag, cases, *sim.BIRTH_NAMES(fu), side=D.SIDE)[idx].copy()
        E = V.copy()
        r = np.asarray(R0, float)[idx]
        thb = np.asarray(thf, float)[idx]
        st = Stream(tag, cases, *sim.NOISE_NAMES(fu), side=D.SIDE)
        Mg = Medium(D.SHAPES["2x4"], D.GAMMA * D.LAMBDA ** 2, D.GAMMA, 1.0, dt=1.0, m=D.SITES[D.LAMBDA], margin=0)
        c = np.zeros(len(idx))
        buf = None
        for u in range(1, win + 1):
            i = (u - 1) % D.CHUNK
            if i == 0:
                buf = st.take(D.CHUNK)
            gain = D.G_DIST * (1.0 + D.KAPPA * c)
            V, E, Vt, _drift, _d = S.body(V, E, r, thb, buf[i][idx], p, gain.reshape(-1, 1, 1), alpha, Gk)
            c = Mg.step(np.abs(r - Vt).mean((-2, -1)))
        ok_e2e.append(bool(np.array_equal(s0["V"][fu * n + g["branches"]], V)))
    return {"pass": ok_x and ok_g and all(ok_e2e), "trace_exposures": ok_x, "trace_gains": ok_g,
            "end_to_end_2x4_by_future": ok_e2e, "task": [src, body, unit, block], "window": win}


def q5(root):
    res, groups, W = _trace(root)
    tr = res["trace"]
    out = {"nofield": True, "undisturbed": True, "uniform": True, "rearranged": True, "paper": True}
    Sp = res["S_paper"]
    for g in groups:
        b = g["branches"]
        if g["kind"] == "paper":
            out["paper"] &= bool(np.array_equal(tr["emission"][:, b], Sp[:, g["cases"]]))
        if g["kind"] == "nofield":
            out["nofield"] &= bool(np.all(tr["gain"][:, b] == D.G_DIST))
        elif g["kind"] == "undisturbed":
            out["undisturbed"] &= bool(np.all(tr["gain"][:, b] == D.G_LANE))
        elif g["kind"] in ("uniform", "rearranged"):
            Mg = sim.medium(g["shape"], g["boundary"], g["lam"])
            for t in range(W):
                x = Mg.step(tr["emission"][t][b])
                if g["kind"] == "uniform":
                    out["uniform"] &= bool(np.all(tr["exposure"][t][b] == x.mean()))
                else:
                    out["rearranged"] &= (bool(np.array_equal(tr["exposure"][t][b], x[g["perm"]]))
                                          and not np.any(g["perm"] == np.arange(len(b))))
    return {"pass": all(out.values()), **out}


def q6(root):
    M, tasks = tasks_of(root)
    bad = []
    for src, body, unit, block, t in tasks:
        e, _m = npz(Path(root) / t["files"]["shards"]["path"])
        s, _m2 = npz(Path(root) / t["files"]["raw"]["path"])
        _c, _R0, _thf, T = inputs(src, body, unit, block)
        sg = S.sign(s["V"], np.asarray(T, float)[s["br_case"]])
        if not (np.array_equal(sg, e["sign"][-1]) and np.array_equal(sim.inv(sg), e["a_v"][-1])):
            bad.append(f"{src}/{body}/{unit}/{block}")
    return {"pass": not bad, "tasks": len(tasks), "bad": bad}


def q7(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    src, body, unit, block, _t = tasks[0]
    cases, R0, thf, T = inputs(src, body, unit, block)
    aset = D.STAGE_SETS[stage]
    R_copy = np.array(R0, copy=True)
    a = sim.run(body, aset, cases, R0, thf, T, D.STAGE_TAG[stage], window=200, reads=(200,), trace_until=200)
    b = sim.run(body, aset, cases, R0, thf, -np.asarray(T), D.STAGE_TAG[stage], window=200, reads=(200,), trace_until=200)
    record = bool(np.array_equal(R0, R_copy))
    same = (np.array_equal(a["V"], b["V"]) and all(np.array_equal(a["trace"][k], b["trace"][k]) for k in a["trace"])
            and np.array_equal(a["stress_mean"], b["stress_mean"]))
    h = sim.run(body, aset, cases, 0.5 * np.asarray(R0), thf, T, D.STAGE_TAG[stage], window=200, reads=(), keep_final=False,
                trace_until=200)
    pb = np.isin(h["br_arr"], [i for i, x in enumerate(aset) if x[3] == "paper"])
    paper_free = bool(np.array_equal(h["trace"]["emission"][:, pb], a["trace"]["emission"][:, pb])
                      and not np.array_equal(h["trace"]["emission"][:, ~pb], a["trace"]["emission"][:, ~pb]))
    complement = bool(np.array_equal(a["sign"], 1.0 - b["sign"]) or np.allclose(a["sign"], 1.0 - b["sign"], atol=0, rtol=0))
    done = []
    for s, bo, u, blk, _t2 in tasks:
        rec = json.loads((Path(root) / "done" / WK.key(s) / bo / u / f"{blk}.json").read_text())
        done.append(bool(rec["bridge_all_equal"]))
    planned = sorted(map(tuple, M.get("tasks_planned", []))) == sorted(map(tuple, D.stage_tasks(stage)))
    return {"pass": bool(record and same and complement and paper_free and all(done) and planned),
            "record_unchanged": record, "template_scores_only": bool(same), "sign_complemented": complement,
            "paper_stress_reads_no_body": paper_free, "restorations_matched": all(done), "tasks_are_declared": planned}


def q8(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    src, body, unit, block, _t = tasks[0]
    cases, R0, thf, T = inputs(src, body, unit, block)
    aset = list(D.STAGE_SETS[stage])
    tag = D.STAGE_TAG[stage]
    a = sim.run(body, aset, cases, R0, thf, T, tag, window=300, reads=())
    b = sim.run(body, aset[::-1], cases, R0, thf, T, tag, window=300, reads=())
    bad = []
    for i, arr in enumerate(aset):
        j = len(aset) - 1 - i
        if not np.array_equal(a["V"][a["br_arr"] == i], b["V"][b["br_arr"] == j]):
            bad.append(arr[0])
    return {"pass": not bad, "arrangements": len(aset), "differ": bad[:10]}


def q9(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    win = D.STAGE_WINDOW.get(stage, D.WINDOW)
    n = len(sim.layout(D.STAGE_SETS[stage], 8, D.STAGE_TAG[stage])[0])
    cpu = sum(t["cpu_s"] for *_x, t in tasks)
    rate = cpu / (len(tasks) * n * D.FUTURES[stage] * win)
    n_dev = len(sim.layout(D.STAGE_SETS["development"], 8, D.TAG)[0])
    dev = len(D.stage_tasks("development")) * n_dev * D.WINDOW * D.FUTURES["development"]
    pre = (len(D.stage_tasks("preflight")) * len(sim.layout(D.STAGE_SETS["preflight"], 8, D.TAG)[0]) * D.WINDOW
           * D.FUTURES["preflight"])
    forecast = rate * (dev + pre) / 3600
    wall = forecast / WORKERS
    rss = max(t["maxrss_mb"] for *_x, t in tasks)
    return {"pass": bool(forecast <= CAP and wall <= WALL_H and rss <= 2048), "forecast_phase_b_cpu_h": round(forecast, 2),
            "forecast_wall_h_10": round(wall, 2), "cpu_s_per_branch_update": rate, "worker_rss_mb": rss, "cap": CAP}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "sm007.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm007.tables", "--in", str(out / "predictions_scored.json"), "--out",
                         str(out / "TABLES.md")], capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from sm007 import predict as PR
    parts = scored.get("parts", [])
    every = all(("value" in p) or (p.get("available") is False) for p in parts)
    ok = (p1.returncode == 0 and p2.returncode == 0 and len(parts) == len(PR.parts()) and every
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr)[-600:], "sizes": sizes, "parts_scored": len(parts),
            "unavailable": [p["id"] for p in parts if p.get("available") is False], "out": str(out)}


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
             "Q5_controls": lambda: q5(root), "Q7_information": lambda: q7(root), "Q8_pairing": lambda: q8(root)}
    light = {"Q1_complete_finite": lambda: q1(root), "Q6_reanalysis": lambda: q6(root), "Q9_resources": lambda: q9(root),
             "Q10_reader_dry_run": lambda: q10(root)}
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
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_replay", "Q5_controls", "Q6_reanalysis",
             "Q7_information", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
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
