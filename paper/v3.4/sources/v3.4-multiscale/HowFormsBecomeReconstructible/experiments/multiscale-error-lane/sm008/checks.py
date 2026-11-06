"""SM008's qualification Q1-Q10 (DRAFT): python -m sm008.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST]

SM007's checks (sm007.checks) adapted to the mixed layout, fixed in PLAN_SM008.md before their results; in phase A they
run on the debug run (AR005's 900799, li4 and dw, the full set, two futures, a window of 2,000), in phase B on the preflight.
  Q1  complete and finite: every planned task present; every shard's endpoints at the stage's reads and branches (every
      future's, future-major), finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the bridges: at kappa 0 (and kappa_p 0) the update equals dl001.sim.run bit for bit (li4 and dw: mixed, pure, sealed,
      isolated, shared-point and paper groups); where the layouts coincide (k0 and k8 group 0, iso8; absorbing, sealed,
      paper, lambda 2) sm008.sim.run equals sm007.sim.run bit for bit at KAPPA; sm007 is the frozen package (its sources'
      sha256 equal its frozen design's); each isolated block equals a one-sheet Medium; every restored record rehashes to
      its manifest's sha256; the preprint's stress (Eq. 1) equals a case-by-case recomputation written here
  Q4  independent replays: (a) one task's every medium recomputed from the run's traced emissions, and every gain from the
      previous exposure, over 300 updates at KAPPA, bit for bit; (b) one k1-corner group (absorbing, group 3) recomputed end
      to end over the stage's window by a loop written here, against the stage's final bodies, in every future
  Q5  controls by construction: the layout (every composition's case at (g, p) is (g + p) mod 8 of the declared role, in
      every shard); every paper branch emits its case's Eq. 1 stress (trace); the preprint's mixing identity (every sheet of
      k1-corner/paper equals the sheet at the same future, group and position of k0/paper or k8/paper, bit for bit, in
      every shard, and their exposures at every traced update); every iso8 sheet's exposure is a one-sheet medium's driven
      by its own emission alone (trace)
  Q6  reanalysis: sign and a_v recomputed from the saved final bodies equal the shards' at the last read, every task
  Q7  the boundary of information: the inherited record is never written (rerun, compared); the template enters the
      scoring only (a rerun with -T leaves every body, gain, exposure and stress bit for bit and complements sign); the
      preprint's stress never reads the body (a rerun with the record halved leaves every paper emission bit for bit); every
      task's restorations matched (its done record); the stage's tasks are its declared blocks and bodies
  Q8  pairing: reversing the arrangements changes no arrangement's final bodies (300 updates)
  Q9  resources: phase B's forecast (the preflight and the development, their futures) from this stage's CPU per
      branch-update, with 25% headroom within the lead's cap of 14 CPU-hours (Amendment 1); worker memory within 2 GB
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
from sm008 import design as D  # noqa: E402
from sm008 import sim  # noqa: E402
from sm008 import worker as WK  # noqa: E402

CAP, HEADROOM = 14.0, 1.25               # the lead's phase-B cap, with headroom (Amendment 1, the rulings sent 16:32:58Z)
WALL_H, WORKERS = 4.0, 10


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


TWINS7 = [("2x4/absorbing", "2x4", "absorbing", "field", D.LAMBDA), ("2x4/sealed", "2x4", "sealed", "field", D.LAMBDA),
          ("iso8/absorbing", "iso8", "absorbing", "field", D.LAMBDA), ("2x4/absorbing/paper", "2x4", "absorbing", "paper", D.LAMBDA),
          ("2x4/absorbing/shared", "2x4", "absorbing", "field", D.LAMBDA_SHARED)]
PAIRS8 = {"k0/absorbing": ("healthy", "2x4/absorbing"), "k8/absorbing": ("struggling", "2x4/absorbing"),
          "k0/sealed": ("healthy", "2x4/sealed"), "k8/sealed": ("struggling", "2x4/sealed"),
          "k0/absorbing/paper": ("healthy", "2x4/absorbing/paper"), "k8/absorbing/paper": ("struggling", "2x4/absorbing/paper"),
          "k0/absorbing/shared": ("healthy", "2x4/absorbing/shared"), "k8/absorbing/shared": ("struggling", "2x4/absorbing/shared")}


def q3(root):
    import hashlib
    M, tasks = tasks_of(root)
    stage = M["stage"]
    tag = D.STAGE_TAG[stage]
    src, _b, block, _t = tasks[0]
    out = {}
    arr1 = [a for a in D.FULL_SET if a[0] in ("k1-corner/absorbing", "k4-checker/sealed", "k8/sealed", "iso8/absorbing",
                                              "k1-corner/absorbing/shared", "k1-corner/absorbing/paper")]
    arr2 = [a for a in D.FULL_SET if a[0] in PAIRS8 or a[0] == "iso8/absorbing"]
    for body in D.BODIES:
        cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
        k = len(cases)
        V_init = np.stack([0.1 * np.random.default_rng(11 + j).standard_normal((D.SIDE, D.SIDE)) for j in range(k)])
        ref = S.run(body, V_init.copy(), V_init.copy(), R0.copy(), np.full(k, D.G_DIST), thf, T, cases, D.SIGMA, 300, ())["final"]
        res = sim.run(body, arr1, cases, R0, thf, T, tag, kappa=0.0, kappa_paper=0.0, window=300, reads=(),
                      stream=Stream(DL.TAG, cases, "future", side=D.SIDE), V_init=V_init.copy())
        for ai, a in enumerate(arr1):
            b = np.flatnonzero(res["br_arr"] == ai)
            out[f"kappa0/{body}/{a[0]}"] = bool(np.array_equal(res["V"][b], ref[res["br_case"][b]]))
        r8 = sim.run(body, arr2, cases, R0, thf, T, tag, window=300, reads=(300,))
        lab8 = [a[0] for a in arr2]
        lab7 = [a[0] for a in TWINS7]
        for role, sl in (("healthy", slice(0, 8)), ("struggling", slice(8, 16))):
            r7 = S7.run(body, TWINS7, cases[sl], R0[sl], thf[sl], T[sl], tag, window=300, reads=(300,))
            for l8, (rl, l7) in PAIRS8.items():
                if rl != role:
                    continue
                s8 = np.flatnonzero((r8["br_arr"] == lab8.index(l8)) & (r8["br_group"] == 0))
                s7 = np.flatnonzero(r7["br_arr"] == lab7.index(l7))
                out[f"sm007/{body}/{l8}"] = bool(np.array_equal(r8["V"][s8], r7["V"][s7]) and np.array_equal(r8["a_v"][:, s8], r7["a_v"][:, s7])
                                                 and all(np.array_equal(r8[x][s8], r7[x][s7]) for x in ("gain_mean", "expo_mean", "stress_mean")))
            s8 = np.flatnonzero((r8["br_arr"] == lab8.index("iso8/absorbing")) & (r8["br_group"] == (0 if role == "healthy" else 1)))
            s7 = np.flatnonzero(r7["br_arr"] == lab7.index("iso8/absorbing"))
            out[f"sm007/{body}/iso8/{role}"] = bool(np.array_equal(r8["V"][s8], r7["V"][s7]))
    fr = json.loads((LANE / "sm007" / "frozen" / "design.json").read_text())
    now7 = {k: hashlib.sha256((LANE / k).read_bytes()).hexdigest() for k in fr["sources"] if k.startswith(("sm007/", "msefield/"))}
    out["sm007_frozen_sources"] = all(fr["sources"][k] == v for k, v in now7.items()) and fr["digest"] == D7.digest() == D.SM007_FROZEN["digest"]
    rng = np.random.default_rng(7)
    for lam in (D.LAMBDA, D.LAMBDA_SHARED):
        Mi = S7.medium("iso8", "absorbing", lam)
        Ms = [Medium([(0, 0)], D7.d_field(lam), D.GAMMA, 1.0, dt=1.0, m=D.SITES[lam], margin=D.MARGIN) for _ in range(8)]
        ok = True
        for _t in range(100):
            e = rng.uniform(0, 2, 8)
            ok &= bool(np.array_equal(Mi.step(e), np.array([Ms[j].step(e[j:j + 1])[0] for j in range(8)])))
        out[f"isolated/{lam}"] = ok
    cases, _R0, _thf, _T, _br, _rf = WK.inputs(src, "li4", block, check=False)
    Sp = S7.paper_trajectory(tag, cases, 0, 300)
    ok_p = True
    for j in range(len(cases)):
        Sj = S7.paper_init(tag, cases[j:j + 1], 0)
        ok_p &= bool(Sj[0] >= D7.PAPER_SSTAR)
        for t in range(300):
            for _s in range(D7.PAPER["k"]):
                Sj = Sj + D7.PAPER["dt_sub"] * (D7.PAPER["P_max"] * Sj ** 2 / (D7.PAPER["K"] ** 2 + Sj ** 2) - D7.PAPER["delta_S"] * Sj)
            ok_p &= bool(Sj[0] == Sp[t, j])
    out["paper_stress_recomputed"] = ok_p
    rehash = []
    for s, body, blk, _t in tasks:
        root_s = Path(D.SOURCES[s]["root"])
        Ms_ = json.loads((root_s / "manifest.json").read_text())["tasks"]
        for unit in D.ROLES[body]:
            f = Ms_[f"{body}/{unit}/{blk}"]["files"]["raw"]
            rehash.append(hashlib.sha256((root_s / f["path"]).read_bytes()).hexdigest() == f["sha256"])
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
    res["S_paper"] = S7.paper_trajectory(tag, cases, 0, window)
    return res, groups, window


def q4(root):
    res, groups, W = _trace(root)
    tr = res["trace"]
    ok_x = ok_g = True
    for g in groups:
        b = g["branches"]
        Mg = S7.medium(g["shape"], g["boundary"], g["lam"])
        kap = D.KAPPA_PAPER if g["kind"] == "paper" else D.KAPPA
        for t in range(W):
            x = Mg.step(tr["emission"][t][b])
            ok_x &= bool(np.array_equal(tr["exposure"][t][b], x))
            prev = tr["exposure"][t - 1][b] if t else np.zeros(len(b))
            ok_g &= bool(np.array_equal(tr["gain"][t][b], D.G_DIST * (1.0 + kap * prev)))
    M, tasks = tasks_of(root)
    src, body, block, t = tasks[0]
    cases, R0, thf, T, _br, _rf = WK.inputs(src, body, block)
    stage = M["stage"]
    tag, win = D.STAGE_TAG[stage], D.STAGE_WINDOW.get(stage, D.WINDOW)
    aset = D.STAGE_SETS[stage]
    br_case, br_arr, br_group, br_pos, _groups = sim.layout(aset)
    n = len(br_case)
    ai = [a[0] for a in aset].index("k1-corner/absorbing")
    bb = np.flatnonzero((br_arr == ai) & (br_group == 3))
    idx = [3 % 8 + 8] + [(3 + p) % 8 for p in range(1, 8)]          # written out: the struggler at corner 0, the rest healthy
    assert list(br_case[bb]) == idx and list(br_pos[bb]) == list(range(8))
    alpha, L = DL.BODIES[body]
    Gk = S.ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    ok_e2e = []
    for fu in range(D.FUTURES[stage]):
        V = birth(tag, cases, *S7.BIRTH_NAMES(fu), side=D.SIDE)[idx].copy()
        E = V.copy()
        r = np.asarray(R0, float)[idx]
        thb = np.asarray(thf, float)[idx]
        st = Stream(tag, cases, *S7.NOISE_NAMES(fu), side=D.SIDE)
        Mg = Medium(D7.SHAPES["2x4"], D.GAMMA * D.LAMBDA ** 2, D.GAMMA, 1.0, dt=1.0, m=D.SITES[D.LAMBDA], margin=0)
        c = np.zeros(len(idx))
        buf = None
        for u in range(1, win + 1):
            i = (u - 1) % D.CHUNK
            if i == 0:
                buf = st.take(D.CHUNK)
            gain = D.G_DIST * (1.0 + D.KAPPA * c)
            V, E, Vt, _drift, _d = S.body(V, E, r, thb, buf[i][idx], p, gain.reshape(-1, 1, 1), alpha, Gk)
            c = Mg.step(np.abs(r - Vt).mean((-2, -1)))
        ok_e2e.append(bool(np.array_equal(s0["V"][fu * n + bb], V)))
    return {"pass": ok_x and ok_g and all(ok_e2e), "trace_exposures": ok_x, "trace_gains": ok_g,
            "end_to_end_k1corner_group3_by_future": ok_e2e, "task": [src, body, block], "window": win}


def q5(root):
    from sm008 import predict as PR
    M, tasks = tasks_of(root)
    aset = D.STAGE_SETS[M["stage"]]
    labels = [a[0] for a in aset]
    ok_layout = True
    for src, body, block, t in tasks:
        e, _m = npz(Path(root) / t["files"]["shards"]["path"])
        for ai, (lab, comp, _b, _k, _l) in enumerate(aset):
            b = e["br_arr"] == ai
            cs, gs, ps = e["br_case"][b], e["br_group"][b], e["br_pos"][b]
            if comp == "iso8":
                ok_layout &= bool(np.array_equal(cs, np.concatenate([np.arange(16)] * D.FUTURES[M["stage"]])))
                continue
            P = set(D.COMPOSITIONS[comp])
            want = (gs + ps) % 8 + 8 * np.isin(ps, list(P))
            ok_layout &= bool(np.array_equal(cs, want))
    res, groups, W = _trace(root)
    tr = res["trace"]
    Sp = res["S_paper"]
    ok_paper = True
    for g in groups:
        if g["kind"] == "paper":
            ok_paper &= bool(np.array_equal(tr["emission"][:, g["branches"]], Sp[:, g["cases"]]))
    # the preprint's mixing identity in the trace: k1-corner/paper's exposures equal k0/paper's (and k8/paper's) at every
    # (group, position) and update
    bc, ba, bg, bp, _gr = sim.layout(aset)
    def at(lab):
        ai = labels.index(lab)
        return {(int(g), int(p)): i for i, (g, p) in enumerate(zip(bg, bp)) if ba[i] == ai}
    mix, h0, s8 = at("k1-corner/absorbing/paper"), at("k0/absorbing/paper"), at("k8/absorbing/paper")
    ok_mix_trace = all(np.array_equal(tr["exposure"][:, i], tr["exposure"][:, h0[kk]]) and
                       np.array_equal(tr["exposure"][:, i], tr["exposure"][:, s8[kk]]) for kk, i in mix.items())
    tasks_r, _M = PR.load(root)
    ex = PR.x5_exact(tasks_r)
    ok_iso = True
    for g in groups:
        if g["shape"] != "iso8":
            continue
        for j, b in enumerate(g["branches"]):
            M1 = Medium([(0, 0)], D7.d_field(g["lam"]), D.GAMMA, D.LEAKS[g["boundary"]], dt=1.0, m=D.SITES[g["lam"]], margin=D.MARGIN)
            for t in range(W):
                ok_iso &= bool(M1.step(tr["emission"][t][b:b + 1])[0] == tr["exposure"][t][b])
    out = {"layout": ok_layout, "paper_emits_eq1": ok_paper, "paper_mixing_identity_trace": bool(ok_mix_trace),
           "paper_mixing_identity_shards": bool(ex and ex["exact"]), "paper_identity_sheets": ex and ex["sheets"],
           "iso8_feels_no_other_sheet": ok_iso}
    return {"pass": all(v for k, v in out.items() if k != "paper_identity_sheets"), **out}


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
    h = sim.run(body, aset, cases, 0.5 * np.asarray(R0), thf, T, tag, window=200, reads=(), keep_final=False, trace_until=200)
    pb = np.isin(h["br_arr"], [i for i, x in enumerate(aset) if x[3] == "paper"])
    paper_free = bool(np.array_equal(h["trace"]["emission"][:, pb], a["trace"]["emission"][:, pb])
                      and not np.array_equal(h["trace"]["emission"][:, ~pb], a["trace"]["emission"][:, ~pb]))
    complement = bool(np.array_equal(a["sign"], 1.0 - b["sign"]))
    done = []
    for s, bo, blk, _t2 in tasks:
        rec = json.loads((Path(root) / "done" / WK.key(s) / bo / f"{blk}.json").read_text())
        done.append(bool(rec["bridge_all_equal"]))
    planned = sorted(map(tuple, M.get("tasks_planned", []))) == sorted(map(tuple, D.stage_tasks(stage)))
    return {"pass": bool(record and same and complement and paper_free and all(done) and planned),
            "record_unchanged": record, "template_scores_only": bool(same), "sign_complemented": complement,
            "paper_stress_reads_no_body": paper_free, "restorations_matched": all(done), "tasks_are_declared": planned}


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
    trims = {"as drafted": full,
             "sealed only k0, k1-corner, k7-corner, k8": tuple(a for a in full if not (a[2] == "sealed" and a[1] not in
                                                                                       ("k0", "k1-corner", "k7-corner", "k8"))),
             "as drafted, no lambda 2": tuple(a for a in full if a[4] != D.LAMBDA_SHARED)}
    trims["sealed 4, no lambda 2"] = tuple(a for a in trims["sealed only k0, k1-corner, k7-corner, k8"] if a[4] != D.LAMBDA_SHARED)
    fc = {f"{k}, one future": round(forecast(rate, v, futures=1), 2) for k, v in trims.items()}
    fc.update({f"{k}, two futures": round(forecast(rate, v, futures=2), 2) for k, v in trims.items()})
    ruled = forecast(rate, full)                      # the ruled phase B: the full set, the stages' futures (one)
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
    p1 = subprocess.run([sys.executable, "-m", "sm008.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm008.tables", "--in", str(out / "predictions_scored.json"), "--out",
                         str(out / "TABLES.md")], capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from sm008 import predict as PR
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
    selected = None if a.only is None else {x.strip() for x in a.only.split(",")}
    if selected is not None:
        heavy = {k: v for k, v in heavy.items() if k.split("_")[0] in selected}
        light = {k: v for k, v in light.items() if k.split("_")[0] in selected}
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
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "only": sorted(selected) if selected else None,
               "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
