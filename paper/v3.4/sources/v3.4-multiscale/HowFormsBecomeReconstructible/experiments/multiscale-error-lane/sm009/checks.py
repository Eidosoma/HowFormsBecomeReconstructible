"""SM009's qualification Q1-Q10 (DRAFT): python -m sm009.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST] [--only Qn,..]

SM008's checks (sm008.checks) adapted to the three arms, fixed in PLAN_SM009.md before their results; in phase A they run on
the debug run (AR005's 900799, li4 and dw, the full set, two futures, a window of 2,000), in phase B on the preflight.
  Q1  complete and finite: every planned task present; every shard's endpoints at the stage's reads and branches (every
      future's, future-major), finite; the shards record the arms' kappas
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the bridges: with every kappa 0 every arm's update equals dl001.sim.run bit for bit (li4 and dw); P arms equal
      sm008.sim.run where the arrangements coincide (300 updates); O in every composition and edge equals iso8/O, the same
      case and unit; sm008 and sm007 frozen (their sources' sha256 equal their frozen designs'); every restored record
      rehashes to its manifest's sha256; the field factor f is the medium's steady exposure under a uniform emission, and
      the medium's stepper reaches it (the 2 x 4 absorbing group and an isolated cell)
  Q4  independent replays: one k1-corner group (absorbing, group 3) under each arm recomputed end to end over the stage's
      window by a loop written here (its own medium and field factor), against the stage's final bodies, every future
  Q5  controls by construction: the layout ((g + p) mod 8 of the declared role, every shard); O's identity in every shard
      (every O sheet equals iso8/O's sheet of the same future and case); R's driver recomputed from the trace
      (max(0, s(t - 1) - GAMMA x(t - 1) / f)) and every arm's gain from its driver, bit for bit
  Q6  reanalysis: sign and a_v recomputed from the saved final bodies equal the shards' at the last read, every task
  Q7  the boundary of information: the inherited record is never written (rerun, compared); the template enters the
      scoring only (a rerun with -T leaves every body, gain and stress bit for bit and complements sign); the responses read
      only the sheet's own stress and its exposure (a rerun with one healthy case's record halved leaves every O sheet of
      every other case bit for bit, and moves a P sheet in that case's groups); every task's restorations matched (its done
      record); the stage's tasks are its declared blocks and bodies
  Q8  pairing: reversing the arrangements changes no arrangement's final bodies (300 updates)
  Q9  resources: phase B's forecast (the preflight and the development, their futures) from this stage's CPU per
      branch-update, with 25% headroom within the cap the lead ruled (8 CPU-hours, Amendment 1); worker memory within 2 GB
Amendment 1: R is dropped from phase B; every check runs the stage's own arrangement set and arms (arms_in), and Q1 expects
an absent arm's kappa as None (expected_kappas). The probe and debug stages keep the 28 they ran, R included.
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

from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msefield.core import Medium  # noqa: E402
from msegrid.core import Stream, birth  # noqa: E402
from sm005 import checks as K5  # noqa: E402  (the lane's parallel check runner, unchanged)
from sm007 import design as D7  # noqa: E402
from sm007 import sim as S7  # noqa: E402
from sm008 import design as D8  # noqa: E402
from sm008 import sim as S8  # noqa: E402
from sm009 import design as D  # noqa: E402
from sm009 import sim  # noqa: E402
from sm009 import worker as WK  # noqa: E402

CAP, HEADROOM = 8.0, 1.25                # phase B's cap with headroom, ruled (PLAN_SM009.md Amendment 1)
WALL_H, WORKERS = 4.0, 10
KAP = {"field": D.KAPPA, "own": D.KAPPA_O, "relative": D.KAPPA_R}


def arms_in(aset):
    """The arms an arrangement set runs, in the order P, O, R (Amendment 1: phase B's set has no R)."""
    kinds = {a[3] for a in aset}
    return tuple(arm for arm in ("P", "O", "R") if D.ARMS[arm] in kinds)


def expected_kappas(aset):
    """The (kappa, kappa_o, kappa_r) a shard of this set records: sim.run leaves an absent arm's kappa None."""
    kinds = {a[3] for a in aset}
    return (D.KAPPA, D.KAPPA_O if "own" in kinds else None, D.KAPPA_R if "relative" in kinds else None)


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}, json.loads(str(f["__meta__"]))


def tasks_of(root):
    M = json.loads((Path(root) / "manifest.json").read_text())
    out = []
    for name, t in sorted(M["tasks"].items()):
        src1, src2, body, block = name.split("/")
        out.append((f"{src1}/{src2}", body, int(block), t))
    return M, out


def q1(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    aset = D.STAGE_SETS[stage]
    n = len(sim.layout(aset)[0])
    F = D.FUTURES[stage]
    win = D.STAGE_WINDOW.get(stage, D.WINDOW)
    reads = [r for r in D.READS if r <= win] or [win]
    bad = []
    for src, body, block, t in tasks:
        e, meta = npz(Path(root) / t["files"]["shards"]["path"])
        nm = f"{src}/{body}/{block}"
        if list(e["reads"]) != reads or e["a_v"].shape != (len(reads), n * F) or e["sign"].shape != (len(reads), n * F):
            bad.append(f"{nm} shapes")
        if not np.array_equal(e["br_future"], np.repeat(np.arange(F), n)) or meta["futures"] != F:
            bad.append(f"{nm} futures")
        for k in ("a_v", "sign", "gain_mean", "expo_mean", "stress_mean"):
            if not np.isfinite(e[k]).all():
                bad.append(f"{nm} {k}")
        if [list(a) for a in meta["arrangements"]] != [list(a) for a in aset] or meta["window"] != win:
            bad.append(f"{nm} arrangements or window")
        if (meta["kappa"], meta["kappa_o"], meta["kappa_r"]) != expected_kappas(aset):
            bad.append(f"{nm} kappas")
    want = set(map(tuple, D.stage_tasks(stage)))
    have = {(s, b, blk) for s, b, blk, _ in tasks}
    return {"pass": not bad and have == want, "tasks": len(tasks), "branches_a_future": n, "futures": F, "reads": reads,
            "bad": bad[:10], "missing": sorted(map(str, want - have))[:5]}


def q2(root):
    M, tasks = tasks_of(root)
    src, body, block, t = tasks[0]
    ends, states, meta, bridge = WK.task(src, body, block, M["stage"])
    e0, _ = npz(Path(root) / t["files"]["shards"]["path"])
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    differ = [k for k in e0 if not np.array_equal(e0[k], ends[k])] + [k for k in s0 if not np.array_equal(s0[k], states[k])]
    return {"pass": not differ and set(e0) == set(ends) and set(s0) == set(states), "task": [src, body, block],
            "arrays": len(e0) + len(s0), "differ": differ[:10]}


def q3(root):
    import hashlib
    M, tasks = tasks_of(root)
    stage = M["stage"]
    tag = D.STAGE_TAG[stage]
    src, _b, block, _t = tasks[0]
    out = {}
    aset = D.STAGE_SETS[stage]                  # the stage's own set (Amendment 1: phase B's has no R arrangement)
    arr1 = [a for a in aset if a[0] in ("k1-corner/absorbing/P", "k4-half/absorbing/O", "k7-corner/absorbing/R",
                                        "iso8/absorbing/O", "k8/sealed/P", "k0/absorbing/R")]
    arr8 = [a for a in D8.FULL_SET if a[0] in ("k0/absorbing", "k1-corner/absorbing", "k4-half/absorbing", "k8/sealed",
                                               "iso8/absorbing")]
    arrO = [a for a in aset if a[3] == "own"] + [("k1-corner/sealed/O", "k1-corner", "sealed", "own", D.LAMBDA)]
    for body in D.BODIES:
        cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
        k = len(cases)
        V_init = np.stack([0.1 * np.random.default_rng(11 + j).standard_normal((D.SIDE, D.SIDE)) for j in range(k)])
        ref = S.run(body, V_init.copy(), V_init.copy(), R0.copy(), np.full(k, D.G_DIST), thf, T, cases, D.SIGMA, 300, ())["final"]
        res = sim.run(body, arr1, cases, R0, thf, T, tag, kappa=0.0, kappa_o=0.0, kappa_r=0.0, window=300, reads=(),
                      stream=Stream(DL.TAG, cases, "future", side=D.SIDE), V_init=V_init.copy())
        for ai, a in enumerate(arr1):
            b = np.flatnonzero(res["br_arr"] == ai)
            out[f"kappa0/{body}/{a[0]}"] = bool(np.array_equal(res["V"][b], ref[res["br_case"][b]]))
        r9 = sim.run(body, arr8, cases, R0, thf, T, tag, window=300, reads=(300,))
        r8 = S8.run(body, arr8, cases, R0, thf, T, tag, window=300, reads=(300,))
        out[f"P_equals_sm008/{body}"] = bool(np.array_equal(r9["V"], r8["V"]) and np.array_equal(r9["a_v"], r8["a_v"])
                                             and all(np.array_equal(r9[x], r8[x]) for x in ("gain_mean", "expo_mean", "stress_mean")))
        rO = sim.run(body, arrO, cases, R0, thf, T, tag, window=300, reads=(300,))
        iso = [a[0] for a in arrO].index("iso8/absorbing/O")
        refO = {int(rO["br_case"][b]): b for b in np.flatnonzero(rO["br_arr"] == iso)}
        out[f"O_identity/{body}"] = all(np.array_equal(rO["V"][b], rO["V"][refO[int(rO["br_case"][b])]])
                                        for b in range(len(rO["br_case"])))
    fr8 = json.loads((LANE / "sm008" / "frozen" / "design.json").read_text())
    fr7 = json.loads((LANE / "sm007" / "frozen" / "design.json").read_text())
    now8 = {k: hashlib.sha256((LANE / k).read_bytes()).hexdigest() for k in fr8["sources"] if k.startswith(("sm007/", "sm008/", "msefield/"))}
    out["sm008_sm007_frozen_sources"] = (all(fr8["sources"][k] == v for k, v in now8.items()) and fr8["digest"] == D.SM008_FROZEN["digest"]
                                         and fr7["digest"] == D.SM007_FROZEN["digest"])
    for shape in ("2x4", "iso8"):
        Mf = S7.medium(shape, "absorbing", D.LAMBDA)
        f = np.asarray(sim.field_factor(shape, "absorbing", D.LAMBDA))
        e = 0.37
        steady = Mf.sample(Mf.steady_state(np.full(Mf.n_sheets, e)))
        lin_ok = bool(np.allclose(steady, f * e / D.GAMMA, rtol=1e-12, atol=0))
        Ms = S7.medium(shape, "absorbing", D.LAMBDA)
        for _t in range(3000):
            x = Ms.step(np.full(Ms.n_sheets, e))
        out[f"field_factor/{shape}"] = lin_ok and bool(np.allclose(x, steady, rtol=1e-9))
    rehash = []
    for s, body, blk, _t in tasks:
        root_s = Path(D.SOURCES[s]["root"])
        Ms_ = json.loads((root_s / "manifest.json").read_text())["tasks"]
        for unit in D.ROLES[body]:
            f_ = Ms_[f"{body}/{unit}/{blk}"]["files"]["raw"]
            rehash.append(hashlib.sha256((root_s / f_["path"]).read_bytes()).hexdigest() == f_["sha256"])
    out["records_rehash"] = all(rehash)
    return {"pass": all(out.values()), **out}


def _trace(root, window=300):
    M, tasks = tasks_of(root)
    src, body, block, _t = tasks[0]
    cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
    aset = D.STAGE_SETS[M["stage"]]
    tag = D.STAGE_TAG[M["stage"]]
    res = sim.run(body, aset, cases, R0, thf, T, tag, window=window, reads=(), keep_final=False, trace_until=window)
    _bc, _ba, _bg, _bp, groups = sim.layout(aset)
    return res, groups, window


def q4(root):
    M, tasks = tasks_of(root)
    src, body, block, t = tasks[0]
    cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
    stage = M["stage"]
    tag, win = D.STAGE_TAG[stage], D.STAGE_WINDOW.get(stage, D.WINDOW)
    aset = D.STAGE_SETS[stage]
    labels = [a[0] for a in aset]
    br_case, br_arr, br_group, br_pos, _groups = sim.layout(aset)
    n = len(br_case)
    alpha, L = DL.BODIES[body]
    Gk = S.ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    idx = [3 % 8 + 8] + [(3 + q) % 8 for q in range(1, 8)]          # written out: the struggler at corner 0, the rest healthy
    Mref = Medium(D7.SHAPES["2x4"], D.GAMMA * D.LAMBDA ** 2, D.GAMMA, 1.0, dt=1.0, m=D.SITES[D.LAMBDA], margin=0)
    f_own = Mref.sample(Mref.steady_state(np.full(8, D.GAMMA)))     # the field factor, computed here from the medium alone
    out = {}
    kap_of = {"P": D.KAPPA, "O": D.KAPPA_O, "R": D.KAPPA_R}
    for arm in arms_in(aset):                   # the stage's arms (Amendment 1: P and O in phase B)
        kap = kap_of[arm]
        ai = labels.index(f"k1-corner/absorbing/{arm}")
        bb = np.flatnonzero((br_arr == ai) & (br_group == 3))
        assert list(br_case[bb]) == idx and list(br_pos[bb]) == list(range(8))
        oks = []
        for fu in range(D.FUTURES[stage]):
            V = birth(tag, cases, *S7.BIRTH_NAMES(fu), side=D.SIDE)[idx].copy()
            E = V.copy()
            r = np.asarray(R0, float)[idx]
            thb = np.asarray(thf, float)[idx]
            st = Stream(tag, cases, *S7.NOISE_NAMES(fu), side=D.SIDE)
            Mg = Medium(D7.SHAPES["2x4"], D.GAMMA * D.LAMBDA ** 2, D.GAMMA, 1.0, dt=1.0, m=D.SITES[D.LAMBDA], margin=0)
            c = np.zeros(8)
            s_prev = np.zeros(8)
            buf = None
            for u in range(1, win + 1):
                i = (u - 1) % D.CHUNK
                if i == 0:
                    buf = st.take(D.CHUNK)
                drv = {"P": c, "O": s_prev, "R": np.maximum(0.0, s_prev - D.GAMMA * c / f_own)}[arm]
                gain = D.G_DIST * (1.0 + kap * drv)
                V, E, Vt, _drift, _d = S.body(V, E, r, thb, buf[i][idx], p, gain.reshape(-1, 1, 1), alpha, Gk)
                s_prev = np.abs(r - Vt).mean((-2, -1))
                c = Mg.step(s_prev)
            oks.append(bool(np.array_equal(s0["V"][fu * n + bb], V)))
        out[f"end_to_end_k1corner_group3/{arm}"] = oks
    return {"pass": all(all(v) for v in out.values()), **out, "task": [src, body, block], "window": win}


def q5(root):
    from sm009 import predict as PR
    M, tasks = tasks_of(root)
    aset = D.STAGE_SETS[M["stage"]]
    ok_layout = True
    for src, body, block, t in tasks:
        e, _m = npz(Path(root) / t["files"]["shards"]["path"])
        for ai, (lab, comp, _b, _k, _l) in enumerate(aset):
            b = e["br_arr"] == ai
            cs, gs, ps = e["br_case"][b], e["br_group"][b], e["br_pos"][b]
            if comp == "iso8":
                ok_layout &= bool(np.array_equal(cs, np.concatenate([np.arange(16)] * D.FUTURES[M["stage"]])))
                continue
            P_ = set(D.COMPOSITIONS[comp])
            want = (gs + ps) % 8 + 8 * np.isin(ps, list(P_))
            ok_layout &= bool(np.array_equal(cs, want))
    tasks_r, _M = PR.load(root)
    ex = PR.o_exact(tasks_r)
    res, groups, W = _trace(root)
    tr = res["trace"]
    ok_r = ok_g = True
    ff = np.ones(len(res["br_case"]))
    kind = np.empty(len(res["br_case"]), dtype=object)
    for g in groups:
        ff[g["branches"]] = sim.field_factor(g["shape"], g["boundary"], g["lam"])
        kind[g["branches"]] = g["kind"]
    for t in range(W):
        s_prev = tr["emission"][t - 1] if t else np.zeros(len(ff))
        x_prev = tr["exposure"][t - 1] if t else np.zeros(len(ff))
        want_r = np.maximum(0.0, s_prev - D.GAMMA * x_prev / ff)
        drv = np.where(kind == "field", x_prev, np.where(kind == "own", s_prev, want_r))
        ok_r &= bool(np.array_equal(tr["driver"][t], drv))
        kap = np.array([KAP[k_] for k_ in kind])
        ok_g &= bool(np.array_equal(tr["gain"][t], D.G_DIST * (1.0 + kap * drv)))
    out = {"layout": ok_layout, "O_identity_shards": bool(ex and ex["exact"]), "O_identity_sheets": ex and ex["sheets"],
           "drivers_from_trace": ok_r, "gains_from_drivers": ok_g}
    return {"pass": all(v for k, v in out.items() if k != "O_identity_sheets"), **out}


def q6(root):
    M, tasks = tasks_of(root)
    bad = []
    for src, body, block, t in tasks:
        e, _m = npz(Path(root) / t["files"]["shards"]["path"])
        s, _m2 = npz(Path(root) / t["files"]["raw"]["path"])
        _c, _R0, _thf, T, _br, _rf = WK.inputs(src, body, block, check=False)
        sg = S.sign(s["V"], np.asarray(T, float)[s["br_case"]])
        if not (np.array_equal(sg, e["sign"][-1]) and np.array_equal(sim.inv(sg), e["a_v"][-1])):
            bad.append(f"{src}/{body}/{block}")
    return {"pass": not bad, "tasks": len(tasks), "bad": bad}


def q7(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    src, body, block, _t = tasks[0]
    cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
    aset = D.STAGE_SETS[stage]
    tag = D.STAGE_TAG[stage]
    R_copy = np.array(R0, copy=True)
    a = sim.run(body, aset, cases, R0, thf, T, tag, window=200, reads=(200,), trace_until=200)
    b = sim.run(body, aset, cases, R0, thf, -np.asarray(T), tag, window=200, reads=(200,), trace_until=200)
    record = bool(np.array_equal(R0, R_copy))
    same = (np.array_equal(a["V"], b["V"]) and all(np.array_equal(a["trace"][k], b["trace"][k]) for k in a["trace"])
            and np.array_equal(a["stress_mean"], b["stress_mean"]))
    complement = bool(np.array_equal(a["sign"], 1.0 - b["sign"]))
    R1 = np.array(R0, copy=True)
    R1[3] = 0.5 * R1[3]                                  # one healthy case's record halved
    h = sim.run(body, aset, cases, R1, thf, T, tag, window=200, reads=(200,))
    kinds = np.array([aset[i][3] for i in a["br_arr"]])
    o_other = (kinds == "own") & (a["br_case"] != 3)
    o_free = bool(np.array_equal(h["V"][o_other], a["V"][o_other]))
    p_moved = bool(not np.array_equal(h["V"][(kinds == "field") & (a["br_case"] != 3)], a["V"][(kinds == "field") & (a["br_case"] != 3)]))
    done = []
    for s, bo, blk, _t2 in tasks:
        rec = json.loads((Path(root) / "done" / WK.key(s) / bo / f"{blk}.json").read_text())
        done.append(bool(rec["bridge_all_equal"]))
    planned = sorted(map(tuple, M.get("tasks_planned", []))) == sorted(map(tuple, D.stage_tasks(stage)))
    return {"pass": bool(record and same and complement and o_free and p_moved and all(done) and planned),
            "record_unchanged": record, "template_scores_only": bool(same), "sign_complemented": complement,
            "O_reads_no_neighbour": o_free, "P_feels_the_neighbour": p_moved, "restorations_matched": all(done),
            "tasks_are_declared": planned}


def q8(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    src, body, block, _t = tasks[0]
    cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
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


def forecast(rate, aset, futures=None):
    n = len(sim.layout(aset)[0])
    f_dev = D.FUTURES["development"] if futures is None else futures
    f_pre = D.FUTURES["preflight"] if futures is None else futures
    dev = len(D.stage_tasks("development")) * n * D.WINDOW * f_dev
    pre = len(D.stage_tasks("preflight")) * n * D.WINDOW * f_pre
    return rate * (dev + pre) / 3600


def q9(root):
    M, tasks = tasks_of(root)
    stage = M["stage"]
    win = D.STAGE_WINDOW.get(stage, D.WINDOW)
    n = len(sim.layout(D.STAGE_SETS[stage])[0])
    cpu = sum(t["cpu_s"] for *_x, t in tasks)
    rate = cpu / (len(tasks) * n * D.FUTURES[stage] * win)
    full = D.STAGE_SETS["development"]
    trims = {"as ruled (Amendment 1)": full,
             "O on iso8 only (O is the same in every composition)": tuple(a for a in full if not (a[3] == "own" and a[1] != "iso8")),
             "as ruled, no sealed": tuple(a for a in full if a[2] != "sealed")}
    fc = {f"{k}, one future": round(forecast(rate, v, futures=1), 2) for k, v in trims.items()}
    fc.update({f"{k}, two futures": round(forecast(rate, v, futures=2), 2) for k, v in trims.items()})
    ruled = forecast(rate, full)
    wall = ruled / WORKERS
    rss = max(t["maxrss_mb"] for *_x, t in tasks)
    return {"pass": bool(ruled * HEADROOM <= CAP and wall <= WALL_H and rss <= 2048), "forecast_phase_b_cpu_h": round(ruled, 2),
            "forecast_with_headroom_cpu_h": round(ruled * HEADROOM, 2), "headroom": HEADROOM, "cap": CAP,
            "futures": {"preflight": D.FUTURES["preflight"], "development": D.FUTURES["development"]},
            "forecast_wall_h_10": round(wall, 2), "cpu_s_per_branch_update": rate, "worker_rss_mb": rss,
            "forecasts_by_trim_cpu_h": fc}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE), PYTHONDONTWRITEBYTECODE="1")
    p1 = subprocess.run([sys.executable, "-m", "sm009.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm009.tables", "--in", str(out / "predictions_scored.json"), "--out",
                         str(out / "TABLES.md")], capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from sm009 import predict as PR
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
    ap.add_argument("--only", default=None, help="comma-separated check numbers, e.g. Q9,Q10 (a partial re-run)")
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root), "Q3_bridges": lambda: q3(root), "Q4_replay": lambda: q4(root),
             "Q5_controls": lambda: q5(root), "Q7_information": lambda: q7(root), "Q8_pairing": lambda: q8(root)}
    light = {"Q1_complete_finite": lambda: q1(root), "Q6_reanalysis": lambda: q6(root), "Q9_resources": lambda: q9(root),
             "Q10_reader_dry_run": lambda: q10(root)}
    chosen = None if a.only is None else {x.strip() for x in a.only.split(",")}
    if chosen is not None:
        heavy = {k: v for k, v in heavy.items() if k.split("_")[0] in chosen}
        light = {k: v for k, v in light.items() if k.split("_")[0] in chosen}
    checks = {}
    cpus = [int(c) for c in a.cpus.split(",")] if a.cpus else []
    if heavy and len(cpus) >= len(heavy):
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
    checks = {k: checks[k] for k in order if k in checks}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "only": sorted(chosen) if chosen else None,
               "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
