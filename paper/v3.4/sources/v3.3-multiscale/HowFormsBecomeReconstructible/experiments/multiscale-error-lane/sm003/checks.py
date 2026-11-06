"""SM003's qualification Q1-Q10 (DRAFT): python -m sm003.checks --root STAGE_ROOT --fit-root FIT_REREAD_ROOT [--receipt PATH]

Fixed before their results; run on the preflight blocks at the full shape (the six units), with the FIT rereads. Any
failure stops the campaign.
  Q1  complete and finite: every endpoint at its declared shape (g = 4 exactly where design.unit_grains allows it); the
      ties counted, >= 0; the wall distance -1 or in [0, w); the FIT rereads complete (48 tasks), finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the bridges: (a) SM003's task equals sm002.worker.task (frozen) on the same unit, block and tag in every SM002
      endpoint and raw state, bit for bit; (b) every FIT reread task's g = 1 read equals SM001's saved successor
      endpoints at every read bit for bit (the spacing's last bits recorded); (c) on 4x upsampled side-16 records the
      g = 4 reader at side 64 equals sm001.sim.successor at side 16 bit for bit (same stream name), the lifted patch
      score equal to the unlifted one, and the composed coarse-graining returns the records exactly
  Q4  an independent replay of the g = 4 reader (the 2 x 2 rule by explicit loops, twice; its own draws from
      mse.native.address; its own body and record step from the definitions, as sm002.checks.replay_cg) reproduces one
      refined branch's final coarse body within 1e-8 and its lifted score exactly
  Q5  aliases: each reader's no-record control ends bit-identical across a task's patch sizes, and the cg and g = 4
      controls across the units of a block
  Q6  reanalysis: E at g = 1, 2 and 4 recomputed from the saved raw final bodies (float32; lifted) equal the saved
      endpoints within an absolute 1/64
  Q7  efficacy: the six units are SM001's, the refined doubled from their twins; every refined condition has its twins
      (at g and g / 2) on the same blocks; every patch has L^2 sites; every dial on for 1,000 updates; the ties recount
      equal; g = 4 only where w >= 8; the readers' streams differ (their controls differ); the FIT rows are 648 (324 x 2),
      their g = 1 E equal to SM001's FIT shards; every identity inside mse.assay.RANGES; T*
  Q8  pairing: a g = 4 branch listed twice gives bit-identical outputs, and reordering the branches changes none
  Q9  resources: the development (the FIT rereads as measured, and TEST forecast from this stage's tasks over 16 blocks)
      within 35 CPU-hours, within 12 h of wall on 12 workers, worker memory within 2 GB, and disk headroom
  Q10 the reader dry run: the model fitted on the FIT rereads (the selection rule run), predict and tables complete on
      this stage, every statement scored, every output file <= 256 KB
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
from sm003 import design as D  # noqa: E402
from sm003 import readers as RD  # noqa: E402
from sm003 import worker as Wk  # noqa: E402


def q1(root, pairs, fit_root):
    bad = []
    for u, b in pairs:
        z = np.load(root / "shards" / u / f"{b}.npz")
        na, k = len(D.unit_arms(u)), S1D.NCASE
        for L in S1D.UNIT[u]["sizes"]:
            rn = f"L{L}"
            want = {**{f"{rn}/{e}": (len(S1D.READS), na, k) for e in S1.ENDS},
                    **{f"{rn}/u/{e}": (len(S1D.READS2), na + 1, k) for e in S1.ENDS2},
                    **{f"{rn}/cg/{e}": (na + 1, k) for e in C.ENDS_CG},
                    **{f"{rn}/cg/c/{e}": (len(S1D.READS2), na + 1, k) for e in C.ENDS_C},
                    f"{rn}/cg/ties": (na, k), f"{rn}/hit": (na, k), f"{rn}/onset": (na, k), f"{rn}/wall": (k,)}
            if 4 in D.unit_grains(u):
                want.update({f"{rn}/g4/{e}": (na + 1, k) for e in RD.ENDS})
            elif any(key.startswith(f"{rn}/g4/") for key in z.files):
                bad.append([u, b, rn, "g4 where not allowed"])
            for key, shape in want.items():
                if key not in z or z[key].shape != shape or not np.isfinite(z[key]).all():
                    bad.append([u, b, key])
            if (z[f"{rn}/cg/ties"] < 0).any():
                bad.append([u, b, rn, "ties"])
            wall = z[f"{rn}/wall"]
            if not np.all((wall == -1) | ((wall >= 0) & (wall < S1D.UNIT[u]["w"]))):
                bad.append([u, b, rn, "wall"])
    RM = json.loads((fit_root / "manifest.json").read_text())
    fit_bad = []
    for key, t in RM["tasks"].items():
        z = np.load(fit_root / t["file"]["path"])
        u = key.split("/")[0]
        na = len(S1D.unit_arms(u))
        for L in S1D.UNIT[u]["sizes"]:
            for g in D.FIT_GRAINS:
                for e in RD.ENDS:
                    x = z[f"L{L}/g{g}/{e}"]
                    if x.shape != (na + 1, S1D.NCASE) or not np.isfinite(x).all():
                        fit_bad.append([key, L, g, e])
    return {"pass": not bad and not fit_bad and len(RM["tasks"]) == 48, "bad": bad[:10], "tasks": len(pairs),
            "fit_tasks": len(RM["tasks"]), "fit_bad": fit_bad[:10]}


def q2(root, pair, tag, purpose):
    u, b = pair
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(u, b, purpose, tmp, tag)
        diff = []
        for kind in ("shards", "raw"):
            a, c = np.load(root / kind / u / f"{b}.npz"), np.load(Path(tmp) / kind / u / f"{b}.npz")
            diff += [f"{kind}/{k}" for k in a.files if k != "__meta__" and not np.array_equal(a[k], c[k])]
    return {"pass": not diff, "task": [u, b], "differ": diff[:10]}


def q3(root, block, tag, purpose, fit_root):
    from sm002 import worker as W2
    out = {}
    unit = "W8_x64_r2"
    ends, raw, _, _ = W2.task(unit, block, purpose, tag)
    z, zr = np.load(root / "shards" / unit / f"{block}.npz"), np.load(root / "raw" / unit / f"{block}.npz")
    same = [np.array_equal(ends[kk], z[kk]) for kk in ends] + [np.array_equal(raw[kk], zr[kk]) for kk in raw]
    out["a_sm003_task_equals_sm002_task"] = bool(all(same))
    out["a_items"] = len(same)
    RM = json.loads((fit_root / "manifest.json").read_text())
    out["b_fit_reread_g1_equals_sm001"] = bool(RM["bridge_all_equal"] and all(t["bridge_all_equal"] for t in RM["tasks"].values()))
    out["b_fit_tasks"] = len(RM["tasks"])
    # (b, the lead's phase-B items) one FIT reread task rerun under the current sources equals its shard bit for bit, and
    # every source the FIT rereads ran under equals today's outside sm003/ and for sm003/fitread.py and sm003/readers.py
    from sm003 import fitread as FR
    FM = FR.fit_manifest()
    with tempfile.TemporaryDirectory() as tmp:
        FR.run_task(tmp, "W8_x32", 910628, FM["tasks"]["W8_x32/910628"]["files"])
        za, zb = np.load(fit_root / "shards" / "W8_x32" / "910628.npz"), np.load(Path(tmp) / "shards" / "W8_x32" / "910628.npz")
        keys = [k for k in za.files if k != "__meta__"]
        out["b_fit_task_rerun_bit_for_bit"] = bool(sorted(keys) == sorted(k for k in zb.files if k != "__meta__")
                                                   and all(np.array_equal(za[k], zb[k]) for k in keys))
        out["b_fit_task_rerun_arrays"] = len(keys)
    now = D.sources(LANE)
    rec = RM["sources"]
    keys = [k for k in set(rec) | set(now) if not k.startswith("sm003/")] + ["sm003/fitread.py", "sm003/readers.py"]
    out["b_fit_sources_equal"] = bool(all(rec.get(k) == now.get(k) and rec.get(k) is not None for k in keys))
    out["b_fit_sources_compared"] = len(keys)
    # (c) 4x upsampled side-16 records
    arms = [a for a in S1D.unit_arms("W4_x32") if a["name"] in ("dial-c1-m2-t3000", "dial-c2-m0-t30")]
    cases, V0, ema0, R0, th, T = S1.prepare("W4", 16, block, purpose)
    k = len(cases)
    o = S1.run(2, arms, cases, V0, ema0, R0, th, T, 16, 4, tag=tag)
    pick = lambda x: np.concatenate([x, x[:k]])
    r, H, W = pick(o["r"]), pick(o["H"]), pick(o["W"])
    gains = [S1D.GAIN] * len(arms) + [0.0]
    ref = S1.successor(r, H, W, cases, th, T, o["m"], 16, 4, gains, tag=tag, reads=(S1D.WINDOW2,), stream="dw")
    rf, Hf, Wf = C.upsample(*C.upsample(r, H, W))
    back = RD.coarse4(rf, Hf, Wf)
    up = lambda x: C.lift(C.lift(x))
    got = RD.read_g4(rf, Hf, Wf, cases, up(th), up(T), up(o["m"]), 64, 16, gains, tag, stream="dw")
    out["c_coarse4_returns_the_record"] = bool(all(np.array_equal(a, b) for a, b in zip(back, (r, H, W))))
    out["c_V_bit_for_bit"] = bool(np.array_equal(got["V"], ref["V"]))
    out["c_lifted_in_equals_unlifted"] = bool(np.array_equal(got["in"], ref["in"][-1]))
    ok = all(v for kk, v in out.items() if kk not in ("a_items", "b_fit_tasks", "b_fit_task_rerun_arrays", "b_fit_sources_compared"))
    return {"pass": ok, **out}


# Q4: the independent replay -----------------------------------------------------------------------------------------

def _coarse_loops(r, H, W):
    s = r.shape[0] // 2
    rc, Hc, Wc = np.zeros((s, s)), np.zeros((s, s)), np.zeros((s, s))
    for i in range(s):
        for j in range(s):
            rc[i, j] = ((r[2 * i, 2 * j] + r[2 * i, 2 * j + 1]) + (r[2 * i + 1, 2 * j] + r[2 * i + 1, 2 * j + 1])) * 0.25
    for i in range(s):
        for j in range(s):
            jn, i_n = (j + 1) % s, (i + 1) % s
            h = H[2 * i, 2 * j + 1] + H[2 * i + 1, 2 * j + 1]
            rel = np.sign(rc[i, j] * rc[i, jn])
            Hc[i, j] = np.sign(h) if h != 0 else (rel if rel != 0 else 1.0)
            v = W[2 * i + 1, 2 * j] + W[2 * i + 1, 2 * j + 1]
            rel = np.sign(rc[i, j] * rc[i_n, j])
            Wc[i, j] = np.sign(v) if v != 0 else (rel if rel != 0 else 1.0)
    return rc, Hc, Wc


def replay_g4(r, H, W, case, tag, stream, gain, window):
    """The g = 4 reader for one case and one branch from the definitions: the 2 x 2 rule by explicit loops twice, then a
    fresh dw body born from newborn noise reading the protected coarse record (sm002.checks.replay_cg's dynamics)."""
    from mse.assay import BIRTH_SCALE
    from mse.native import NATIVE, address
    rc, Hc, Wc = _coarse_loops(*_coarse_loops(r, H, W))
    s = rc.shape[0]
    g0 = address(tag, *case.key(), "successor", stream).standard_normal((s, s))
    V = BIRTH_SCALE * (g0 - g0.mean())
    gz = address(tag, *case.key(), "successor-future", stream)
    gx = address(tag, *case.key(), "successor-record-noise", stream)
    p = NATIVE
    rr = rc.copy()
    nb = lambda x: (np.roll(x, 1, 0) + np.roll(x, -1, 0) + np.roll(x, 1, 1) + np.roll(x, -1, 1)) / 4.0
    zs = xs = None
    for t in range(1, window + 1):
        i = (t - 1) % S1D.CHUNK
        if i == 0:
            zs, xs = gz.standard_normal((S1D.CHUNK, s, s)), gx.standard_normal((S1D.CHUNK, s, s))
        drift = V - V ** 3 + p.well_asym + 0.0 + p.coupling * (nb(V) - V)
        Vt = np.clip(V + p.dt * drift + S1D.SIGMA * zs[i], -p.bound, p.bound)
        V = np.clip(Vt + p.dt * gain * (rr - Vt), -p.bound, p.bound)
        bsum = (np.roll(Wc, 1, 0) * np.roll(rr, 1, 0) + Wc * np.roll(rr, -1, 0) + np.roll(Hc, 1, 1) * np.roll(rr, 1, 1)
                + Hc * np.roll(rr, -1, 1)) / 4.0
        rr = np.clip(rr + 0.05 * (rr * (1 - (rr / 1.2) ** 2) + 1.0 * (bsum - rr)) + 0.02 * xs[i], -2.0, 2.0)
    return V


def q4(block, tag, purpose):
    unit, L, arm_name = "W16_x64_r2", 8, "dial-c2-m2-t3000"
    u = S1D.UNIT[unit]
    arm = [a for a in D.unit_arms(unit) if a["name"] == arm_name][0]
    cases, V0, ema0, R0, th, T = S1.prepare(f"W{u['w']}", u["side"], block, purpose)
    o = S1.run(L, [arm], cases, V0, ema0, R0, th, T, u["side"], u["w"], place=u["place"], dil=u["dil"], tag=tag,
               reads={S1D.WINDOW})
    got = RD.read_g4(o["r"], o["H"], o["W"], cases, th, T, o["m"], u["side"], u["w"], [S1D.GAIN], tag)
    j = 0
    V = replay_g4(o["r"][j], o["H"][j], o["W"][j], cases[j], tag, D.STREAMS[4], S1D.GAIN, S1D.WINDOW2)
    dV = float(np.abs(got["V"][j] - V).max())
    Vf = np.repeat(np.repeat(V, 4, 0), 4, 1)
    m = o["m"][j]
    e = float((((Vf > 0) == (T[j] > 0)) & m).sum() / m.sum())
    return {"pass": dV <= 1e-8 and e == float(got["in"][j]), "branch": [unit, f"L{L}", arm_name, "case 0"], "max_dV": dV,
            "E_replay": e, "E_g4": float(got["in"][j])}


def q5(root, pairs):
    same_size, same_unit = [], []
    by_block = {}
    for u, b in pairs:
        z = np.load(root / "raw" / u / f"{b}.npz")
        na = len(D.unit_arms(u))
        keys = ("uV", "cgV") + (("g4V",) if 4 in D.unit_grains(u) else ())
        for key in keys:
            ctrl = [z[f"L{L}/{key}"][na] for L in S1D.UNIT[u]["sizes"]]
            same_size.append(all(np.array_equal(ctrl[0], x) for x in ctrl[1:]))
        L0 = S1D.UNIT[u]["sizes"][0]
        by_block.setdefault((b, "cgV"), []).append(z[f"L{L0}/cgV"][na])
        if 4 in D.unit_grains(u):
            by_block.setdefault((b, "g4V"), []).append(z[f"L{L0}/g4V"][na])
    for xs in by_block.values():
        same_unit.append(all(np.array_equal(xs[0], x) for x in xs[1:]))
    return {"pass": all(same_size) and all(same_unit), "controls_alike_across_sizes": all(same_size),
            "cg_and_g4_controls_alike_across_units": all(same_unit)}


def q6(root, pairs):
    from lr005 import sim as L5S
    worst = 0.0
    for u, b in pairs:
        z, raw = np.load(root / "shards" / u / f"{b}.npz"), np.load(root / "raw" / u / f"{b}.npz")
        T = raw["T"].astype(float)
        na, k = len(D.unit_arms(u)), S1D.NCASE
        for L in S1D.UNIT[u]["sizes"]:
            rn = f"L{L}"
            m = raw[f"{rn}/m"]
            bodies = {"u/in": raw[f"{rn}/uV"].astype(np.float64), "cg/in": C.lift(raw[f"{rn}/cgV"].astype(np.float64))}
            if 4 in D.unit_grains(u):
                bodies["g4/in"] = RD.lift4(raw[f"{rn}/g4V"].astype(np.float64))
            for key, V in bodies.items():
                e = np.array([[L5S.inside(V[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
                saved = z[f"{rn}/{key}"][-1] if key == "u/in" else z[f"{rn}/{key}"]
                worst = max(worst, float(np.abs(e - saved).max()))
    return {"pass": worst <= 1.0 / 64, "max_abs_diff": worst}


def q7(root, pairs, fit_root):
    from mse.assay import RANGES
    from sm003 import analyze as A
    out = {}
    ok_units = True
    for r_u, t_u in zip(D.REFINE, D.TWINS):
        a, b = S1D.UNIT[r_u], S1D.UNIT[t_u]
        ok_units &= (a["kind"], b["kind"]) == ("refine", "transfer") and a["side"] == b["side"] == 64
        ok_units &= a["w"] == 2 * b["w"] and a["sizes"] == tuple(2 * s for s in b["sizes"])
        ok_units &= a["couplings"] == tuple(2 * c for c in b["couplings"]) and a["dil"] == 2 * b["dil"]
        ok_units &= D.twin_unit(r_u) == t_u
    out["refined_doubled_from_twins"] = bool(ok_units)
    rows = A.test_rows(root)
    ref = [r for r in rows if r["kind"] == "refine"]
    out["every_refined_condition_has_its_twins"] = all(
        (r["twin"] is not None or r["g"] not in D.unit_grains(D.twin_unit(r["unit"])))
        and (r["g"] == 1 or r["twin_half"] is not None) for r in ref)
    ok_p, ok_sig, ok_ties, ok_g4 = True, True, True, True
    for u, b in pairs:
        z, raw = np.load(root / "shards" / u / f"{b}.npz"), np.load(root / "raw" / u / f"{b}.npz")
        cfg = S1D.UNIT[u]
        ok_g4 &= (4 in D.unit_grains(u)) == (cfg["w"] >= D.G4_MIN_W) == any(k.endswith("/g4/in") for k in z.files)
        for L in cfg["sizes"]:
            m = raw[f"L{L}/m"]
            ok_p &= bool((m.sum((-2, -1)) == L * L).all())
            want = np.array([0 if a["never"] else S1D.DURATION for a in D.unit_arms(u)], float)
            ok_sig &= bool(np.array_equal(z[f"L{L}/signal_updates"], want))
            ok_ties &= bool(np.array_equal(C.ties(raw[f"L{L}/H"].astype(float), raw[f"L{L}/W"].astype(float)),
                                           z[f"L{L}/cg/ties"]))
    out.update(patch_sizes=ok_p, signal_windows=ok_sig, ties_recount_equal=ok_ties, g4_exactly_where_w_ge_8=bool(ok_g4))
    u = next(uu for uu, _ in pairs if 4 in D.unit_grains(uu))
    b = pairs[0][1]
    z = np.load(root / "shards" / u / f"{b}.npz")
    L = S1D.UNIT[u]["sizes"][0]
    na = len(D.unit_arms(u))
    c1, c2, c4 = z[f"L{L}/u/in"][-1, na], z[f"L{L}/cg/in"][na], z[f"L{L}/g4/in"][na]
    out["streams_differ"] = len(set(D.STREAMS.values())) == 3 and not (np.array_equal(c1, c4) or np.array_equal(c2, c4))
    fr = A.fit_rows(fit_root)
    out["fit_rows_648"] = len(fr) == 648 and sorted({r["g"] for r in fr}) == [1, 2]
    FM = json.loads((Path(D.FIT_ROOT) / "manifest.json").read_text())
    g1_same = True
    for r in [x for x in fr if x["g"] == 1][::37]:
        ai = [a["name"] for a in S1D.unit_arms(r["unit"])].index(r["arm"])
        saved = np.array([np.load(Path(D.FIT_ROOT) / "shards" / r["unit"] / f"{bb}.npz")[f"L{r['L']}/s/in"][-1, ai] for bb in r["blocks"]])
        g1_same &= bool(np.array_equal(saved, r["E"]))
    out["fit_g1_equals_sm001_shards"] = g1_same and FM["tag"] == D.FIT_TAG
    blocks_eng = list(D.PROBE_BLOCKS) + list(D.DEBUG_BLOCKS) + list(D.SMOKE_BLOCKS) + list(D.IDENTITIES["preflight"])
    out["identities_in_ranges"] = (all(b in RANGES["engineering"] for b in blocks_eng)
                                   and all(b in RANGES["development"] for b in list(D.IDENTITIES["test"]) + list(D.RESERVE)))
    out["T_star"] = abs(S1D.T_STAR - math.log(1.8) / -math.log(0.99)) < 1e-12
    return {"pass": all(out.values()), **out}


def q8(block, tag, purpose):
    unit = "W16_x64_r2"
    u = S1D.UNIT[unit]
    arms = D.unit_arms(unit)
    a1, a2 = arms[2], arms[5]
    cases, V0, ema0, R0, th, T = S1.prepare(f"W{u['w']}", u["side"], block, purpose)
    k = len(cases)
    o = S1.run(4, [a1, a2], cases, V0, ema0, R0, th, T, u["side"], u["w"], dil=u["dil"], tag=tag, window=300, reads={300})
    r1, r2 = o["r"][:k], o["r"][k:]
    H1, H2, W1, W2 = o["H"][:k], o["H"][k:], o["W"][:k], o["W"][k:]
    g = [S1D.GAIN] * 3
    x = RD.read_g4(np.concatenate([r1, r1, r2]), np.concatenate([H1, H1, H2]), np.concatenate([W1, W1, W2]), cases, th, T,
                   o["m"], 64, u["w"], g, tag, window=200)
    y = RD.read_g4(np.concatenate([r2, r1]), np.concatenate([H2, H1]), np.concatenate([W2, W1]), cases, th, T, o["m"], 64,
                   u["w"], g[:2], tag, window=200)
    twice = np.array_equal(x["V"][:k], x["V"][k:2 * k]) and np.array_equal(x["in"][:k], x["in"][k:2 * k])
    order = (np.array_equal(x["V"][:k], y["V"][k:]) and np.array_equal(x["V"][2 * k:], y["V"][:k])
             and np.array_equal(x["in"][2 * k:], y["in"][:k]))
    return {"pass": bool(twice and order), "listed_twice": bool(twice), "reordered": bool(order)}


def q9(root, fit_root):
    M = json.loads((root / "manifest.json").read_text())
    RM = json.loads((fit_root / "manifest.json").read_text())
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
    return {"pass": bool(ok), "forecast_test_cpu_h": round(test, 2), "fit_reread_cpu_h": round(fit, 2),
            "forecast_dev_cpu_h": round(test + fit, 2), "forecast_test_wall_h_12": round(wall, 2), "worker_rss_mb": rss,
            "disk_headroom": bool(disk)}


def q10(root, fit_root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "sm003.analyze", "fit", "--fit-root", str(fit_root), "--out", str(out / "model.json")],
                        capture_output=True, text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm003.predict", "--root", str(root), "--model", str(out / "model.json"),
                         "--fit-root", str(fit_root), "--out", str(out)], capture_output=True, text=True, env=env, cwd=LANE)
    p3 = subprocess.run([sys.executable, "-m", "sm003.tables", "--root", str(root), "--model", str(out / "model.json"),
                         "--dir", str(out)], capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from sm003 import analyze as A
    from sm003 import predict as P
    want = sorted({p[0] for p in P.parts(A.test_rows(root))})
    ok = (p1.returncode == 0 and p2.returncode == 0 and p3.returncode == 0 and sorted(scored.get("verdicts", {})) == want
          and (out / "TABLES.md").exists() and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr + p3.stderr)[-600:], "sizes": sizes,
            "statements": len(scored.get("verdicts", {}))}


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
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--fit-root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--cpus", default=None, help="comma-separated CPU ids: the heavy checks run one a core")
    a = ap.parse_args()
    root, fit_root = a.root.resolve(), a.fit_root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    pairs = [tuple(p) for p in M["pairs"]]
    block, tag = pairs[0][1], M["tag"]
    purpose = D.PURPOSE[M["stage"]]
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root, pairs[0], tag, purpose),
             "Q3_bridges": lambda: q3(root, block, tag, purpose, fit_root), "Q4_replay": lambda: q4(block, tag, purpose),
             "Q8_pairing": lambda: q8(block, tag, purpose)}
    light = {"Q1_complete_finite": lambda: q1(root, pairs, fit_root), "Q5_aliases": lambda: q5(root, pairs),
             "Q6_reanalysis": lambda: q6(root, pairs), "Q7_efficacy": lambda: q7(root, pairs, fit_root),
             "Q9_resources": lambda: q9(root, fit_root), "Q10_reader_dry_run": lambda: q10(root, fit_root)}
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
               "fit_root": str(fit_root), "blocks": sorted({p[1] for p in pairs}), "tag": tag,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
