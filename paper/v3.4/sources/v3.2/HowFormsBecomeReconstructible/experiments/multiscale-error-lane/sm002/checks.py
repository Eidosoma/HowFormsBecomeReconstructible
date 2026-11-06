"""SM002's qualification Q1-Q10 (DRAFT): python -m sm002.checks --root STAGE_ROOT [--receipt PATH]

Fixed before their results; run on the preflight blocks at the full shape (the six units). Any failure stops the
campaign.
  Q1  complete and finite: every endpoint at its declared shape; the ties counted, >= 0; the wall distance -1 or in [0, w)
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the engine: (a) SM002's task equals sm001.worker.task on the same unit, block and tag in every shared endpoint and
      raw state (the episode, the unscaled reader), bit for bit; (b) on 2x upsampled side-32 records the cg reader at
      side 64 equals sm001.sim.successor at side 32 bit for bit (same stream name), the lifted patch score equal to the
      unlifted one, and the coarse-graining returns the records exactly; (c) the declared coarse-graining on a
      hand-built record: block means, majority bonds, a tie taking the coarse record's relation, +1 where that is 0
  Q4  an independent replay of the cg reader (its own coarse-graining by explicit loops, its own draws from
      mse.native.address, its own body and record step from the definitions; no sm001.sim, sm002.coarse, msegrid or
      dl001.sim) reproduces one refined branch's final coarse body within 1e-8 and its lifted score exactly
  Q5  aliases: each reader's no-record control ends bit-identical across a task's patch sizes, and the cg control across
      the units of a block
  Q6  reanalysis: E_u and E_cg recomputed from the saved raw final bodies (float32; the cg body lifted) equal the saved
      endpoints within an absolute 1/64 for every patch size
  Q7  efficacy: the six units are SM001's, the refined ones doubled from their twins (sizes, couplings, dilation, width;
      the same side); every refined condition has its twin on the same blocks; every patch has L^2 sites and its corner
      equals its twin's; every dial is on for exactly 1,000 updates; the coarse edges tied, recounted from the raw final
      bonds, equal the saved counts (their fraction reported); the cg reader draws from its own stream (its control
      differs from u's)
  Q8  pairing: a cg branch listed twice gives bit-identical outputs, and reordering the branches changes none (short runs)
  Q9  resources: the forecast for the development stage (16 blocks) within 30 CPU-hours on 12 workers within 12 h of
      wall, worker memory within 2 GB, and disk headroom
  Q10 the reader dry run: predict and tables complete, every statement scored, the reported parts written, every
      output file <= 256 KB
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
from sm002 import design as D  # noqa: E402
from sm002 import worker as Wk  # noqa: E402


def q1(root, pairs):
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
            for key, shape in want.items():
                if key not in z or z[key].shape != shape or not np.isfinite(z[key]).all():
                    bad.append([u, b, key])
            if (z[f"{rn}/cg/ties"] < 0).any():
                bad.append([u, b, rn, "ties"])
            wall = z[f"{rn}/wall"]
            if not np.all((wall == -1) | ((wall >= 0) & (wall < S1D.UNIT[u]["w"]))):
                bad.append([u, b, rn, "wall"])
    return {"pass": not bad, "bad": bad[:10], "tasks": len(pairs)}


def q2(root, pair, tag):
    u, b = pair
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(u, b, "engineering", tmp, tag)
        diff = []
        for kind in ("shards", "raw"):
            a, c = np.load(root / kind / u / f"{b}.npz"), np.load(Path(tmp) / kind / u / f"{b}.npz")
            diff += [f"{kind}/{k}" for k in a.files if k != "__meta__" and not np.array_equal(a[k], c[k])]
    return {"pass": not diff, "task": [u, b], "differ": diff[:10]}


def q3(root, block, tag):
    from sm001 import worker as S1W
    out = {}
    unit = "W8_x64_r2"
    ends, raw, _, _ = S1W.task(unit, block, "engineering", tag)
    z, zr = np.load(root / "shards" / unit / f"{block}.npz"), np.load(root / "raw" / unit / f"{block}.npz")
    same = []
    for L in S1D.UNIT[unit]["sizes"]:
        rn = f"L{L}"
        for e in S1.ENDS + ("hit", "onset", "wall", "signal_updates"):
            same.append(np.array_equal(ends[f"{rn}/{e}"], z[f"{rn}/{e}"]))
        for e in S1.ENDS2:
            same.append(np.array_equal(ends[f"{rn}/s/{e}"], z[f"{rn}/u/{e}"]))
        for e in ("r", "H", "W", "m"):
            same.append(np.array_equal(raw[f"{rn}/{e}"], zr[f"{rn}/{e}"]))
        same.append(np.array_equal(raw[f"{rn}/sV"], zr[f"{rn}/uV"]))
    out["a_sm002_task_equals_sm001_task"] = all(same)
    out["a_items"] = len(same)
    # (b) upsampled side-32 records
    arms = [a for a in S1D.unit_arms("W4_x32") if a["name"] in ("dial-c1-m2-t3000", "dial-c2-m0-t30")]
    cases, V0, ema0, R0, th, T = S1.prepare("W4", 32, block, "engineering")
    k = len(cases)
    o = S1.run(4, arms, cases, V0, ema0, R0, th, T, 32, 4, tag=tag)
    pick = lambda x: np.concatenate([x, x[:k]])
    r, H, W = pick(o["r"]), pick(o["H"]), pick(o["W"])
    gains = [S1D.GAIN] * len(arms) + [0.0]
    ref = S1.successor(r, H, W, cases, th, T, o["m"], 32, 4, gains, tag=tag, stream="dw")
    rf, Hf, Wf = C.upsample(r, H, W)
    rc, Hc, Wc = C.coarse_grain(rf, Hf, Wf)
    got = C.read_cg(rf, Hf, Wf, cases, C.lift(th), C.lift(T), C.lift(o["m"]), 64, 8, gains, tag=tag, stream="dw")
    out["b_coarse_grain_returns_the_record"] = bool(np.array_equal(rc, r) and np.array_equal(Hc, H) and np.array_equal(Wc, W))
    out["b_V_bit_for_bit"] = bool(np.array_equal(got["Vc"], ref["V"]))
    out["b_coarse_endpoints_bit_for_bit"] = bool(all(np.array_equal(got[f"c/{e}"], ref[e]) for e in C.ENDS_C))
    out["b_lifted_in_equals_unlifted"] = bool(np.array_equal(got["in"], ref["in"][-1]))
    # (c) the rule by hand: a 4 x 4 record -> 2 x 2
    r4 = np.array([[1.2, 1.0, -1.2, -1.2], [1.2, 1.2, -1.0, -1.2], [-1.2, 1.2, 1.2, 1.2], [-1.2, -1.2, 1.2, 1.2]])
    H4 = np.ones((4, 4))
    W4 = np.ones((4, 4))
    H4[0, 1], H4[1, 1] = -1, -1          # coarse H (0, 0)-(0, 1): both crossing bonds -1: -1
    H4[2, 1], H4[3, 1] = 1, -1           # coarse H (1, 0)-(1, 1): a tie: the coarse relation r_c(1,0) r_c(1,1)
    H4[0, 3], H4[1, 3] = 1, -1           # coarse H (0, 1)-(0, 0) across the wrap: a tie
    W4[1, 0], W4[1, 1] = -1, 1           # coarse W (0, 0)-(1, 0): a tie
    rc4 = C.coarse_values(r4)
    Hc4, Wc4 = C.coarse_bonds(H4, W4, rc4)
    want_rc = np.array([[(1.2 + 1.0 + 1.2 + 1.2) / 4, (-1.2 - 1.2 - 1.0 - 1.2) / 4], [(-1.2 + 1.2 - 1.2 - 1.2) / 4, 1.2]])
    want_H = np.array([[-1.0, np.sign(rc4[0, 1] * rc4[0, 0])], [np.sign(rc4[1, 0] * rc4[1, 1]), 1.0]])
    want_W = np.array([[np.sign(rc4[0, 0] * rc4[1, 0]), 1.0], [1.0, 1.0]])
    zero_tie = C.coarse_bonds(np.array([[1.0, 1.0], [1.0, -1.0]]), np.ones((2, 2)), np.zeros((1, 1)))[0]
    out["c_values"] = bool(np.allclose(rc4, want_rc, atol=1e-15))
    out["c_majority_and_ties"] = bool(np.array_equal(Hc4, want_H) and np.array_equal(Wc4, want_W))
    out["c_zero_relation_tie_is_plus_one"] = bool(np.array_equal(zero_tie, np.ones((1, 1))))
    ok = all(v for kk, v in out.items() if kk != "a_items")
    return {"pass": ok, **out}


# Q4: the independent replay -----------------------------------------------------------------------------------------

def replay_cg(r, H, W, case, side, tag, stream, gain, window):
    """The cg reader for one case and one branch from the definitions: coarse-grain by explicit loops, then a fresh dw
    body born from newborn noise reading the protected coarse record for `window` updates; returns the final coarse V."""
    from mse.assay import BIRTH_SCALE
    from mse.native import NATIVE, address
    s = side // 2
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


def q4(block, tag):
    unit, L, arm_name = "W16_x64_r2", 8, "dial-c2-m2-t3000"
    u = S1D.UNIT[unit]
    arm = [a for a in D.unit_arms(unit) if a["name"] == arm_name][0]
    cases, V0, ema0, R0, th, T = S1.prepare(f"W{u['w']}", u["side"], block, "engineering")
    o = S1.run(L, [arm], cases, V0, ema0, R0, th, T, u["side"], u["w"], place=u["place"], dil=u["dil"], tag=tag,
               reads={S1D.WINDOW})
    got = C.read_cg(o["r"], o["H"], o["W"], cases, th, T, o["m"], u["side"], u["w"], [S1D.GAIN], tag=tag)
    j = 0
    V = replay_cg(o["r"][j], o["H"][j], o["W"][j], cases[j], u["side"], tag, D.CG_STREAM, S1D.GAIN, S1D.WINDOW2)
    dV = float(np.abs(got["Vc"][j] - V).max())
    Vf = np.repeat(np.repeat(V, 2, 0), 2, 1)
    m = o["m"][j]
    e = float((((Vf > 0) == (T[j] > 0)) & m).sum() / m.sum())
    return {"pass": dV <= 1e-8 and e == float(got["in"][j]), "branch": [unit, f"L{L}", arm_name, "case 0"], "max_dV": dV,
            "E_replay": e, "E_cg": float(got["in"][j])}


def q5(root, pairs):
    same_size, same_unit = [], []
    by_block = {}
    for u, b in pairs:
        z = np.load(root / "raw" / u / f"{b}.npz")
        na = len(D.unit_arms(u))
        for key in ("uV", "cgV"):
            ctrl = [z[f"L{L}/{key}"][na] for L in S1D.UNIT[u]["sizes"]]
            same_size.append(all(np.array_equal(ctrl[0], x) for x in ctrl[1:]))
        by_block.setdefault(b, []).append(z[f"L{S1D.UNIT[u]['sizes'][0]}/cgV"][na])
    for b, xs in by_block.items():
        same_unit.append(all(np.array_equal(xs[0], x) for x in xs[1:]))
    return {"pass": all(same_size) and all(same_unit), "controls_alike_across_sizes": all(same_size),
            "cg_control_alike_across_units": all(same_unit)}


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
            uV = raw[f"{rn}/uV"].astype(np.float64)
            cgV = C.lift(raw[f"{rn}/cgV"].astype(np.float64))
            eu = np.array([[L5S.inside(uV[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
            ec = np.array([[L5S.inside(cgV[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
            worst = max(worst, float(np.abs(eu - z[f"{rn}/u/in"][-1]).max()), float(np.abs(ec - z[f"{rn}/cg/in"]).max()))
    return {"pass": worst <= 1.0 / 64, "max_abs_diff": worst}


def q7(root, pairs):
    out = {}
    ok_units = True
    for r_u, t_u in zip(D.REFINE, D.TWINS):
        a, b = S1D.UNIT[r_u], S1D.UNIT[t_u]
        ok_units &= (a["kind"], b["kind"]) == ("refine", "transfer") and a["side"] == b["side"] == 64
        ok_units &= a["w"] == 2 * b["w"] and a["sizes"] == tuple(2 * s for s in b["sizes"])
        ok_units &= a["couplings"] == tuple(2 * c for c in b["couplings"]) and a["dil"] == 2 * b["dil"]
        ok_units &= D.twin_unit(r_u) == t_u and D.unit_arms(r_u)[0]["m"] == D.unit_arms(t_u)[0]["m"]
    out["refined_doubled_from_twins"] = bool(ok_units)
    blocks = {u: sorted(b for uu, b in pairs if uu == u) for u in D.UNITS}
    out["twins_on_the_same_blocks"] = all(blocks[r] == blocks[t] for r, t in zip(D.REFINE, D.TWINS))
    ok_p, ok_corner, ok_sig, ok_ties, tie_frac = True, True, True, True, 0.0
    for u, b in pairs:
        z, raw = np.load(root / "shards" / u / f"{b}.npz"), np.load(root / "raw" / u / f"{b}.npz")
        cfg = S1D.UNIT[u]
        for L in cfg["sizes"]:
            m = raw[f"L{L}/m"]
            ok_p &= bool((m.sum((-2, -1)) == L * L).all())
            want = np.array([0 if a["never"] else S1D.DURATION for a in D.unit_arms(u)], float)
            ok_sig &= bool(np.array_equal(z[f"L{L}/signal_updates"], want))
            tie_frac = max(tie_frac, float(z[f"L{L}/cg/ties"].max()) / (2 * (cfg["side"] // 2) ** 2))
            ok_ties &= bool(np.array_equal(C.ties(raw[f"L{L}/H"].astype(float), raw[f"L{L}/W"].astype(float)),
                                           z[f"L{L}/cg/ties"]))
        if u in D.REFINE:
            t = D.twin_unit(u)
            rt = np.load(root / "raw" / t / f"{b}.npz")
            for L in cfg["sizes"]:
                m, mt = raw[f"L{L}/m"], rt[f"L{L // 2}/m"]
                for j in range(len(m)):
                    # the corner: the patch's first row and column on the torus (the same address for both)
                    ok_corner &= _corner(m[j]) == _corner(mt[j])
    out.update(patch_sizes=ok_p, corner_equals_twins=bool(ok_corner), signal_windows=ok_sig,
               ties_recount_equal=ok_ties, max_tied_edge_fraction=tie_frac)
    u, b = pairs[0]
    z = np.load(root / "shards" / u / f"{b}.npz")
    L = S1D.UNIT[u]["sizes"][0]
    na = len(D.unit_arms(u))
    out["cg_stream_differs"] = D.CG_STREAM != S1D.BODY and not np.array_equal(z[f"L{L}/cg/in"][na], z[f"L{L}/u/in"][-1, na])
    out["T_star"] = abs(S1D.T_STAR - math.log(1.8) / -math.log(0.99)) < 1e-12
    return {"pass": all(v for kk, v in out.items() if kk != "max_tied_edge_fraction"), **out}


def _corner(m):
    """The patch's corner on the torus: the row and column where it starts (the patch is a contiguous run mod side)."""
    rows, cols = np.where(m.any(1))[0], np.where(m.any(0))[0]
    start = lambda idx, n: int(idx[0]) if (n - 1) not in idx or 0 not in idx else int(next(i for i in idx if (i - 1) % n not in idx))
    return start(rows, m.shape[0]), start(cols, m.shape[1])


def q8(block, tag):
    unit = "W16_x64_r2"
    u = S1D.UNIT[unit]
    arms = D.unit_arms(unit)
    a1, a2 = arms[2], arms[5]
    cases, V0, ema0, R0, th, T = S1.prepare(f"W{u['w']}", u["side"], block, "engineering")
    k = len(cases)
    o = S1.run(4, [a1, a2], cases, V0, ema0, R0, th, T, u["side"], u["w"], dil=u["dil"], tag=tag, window=300, reads={300})
    r1, r2 = o["r"][:k], o["r"][k:]
    H1, H2, W1, W2 = o["H"][:k], o["H"][k:], o["W"][:k], o["W"][k:]
    g = [S1D.GAIN] * 3
    x = C.read_cg(np.concatenate([r1, r1, r2]), np.concatenate([H1, H1, H2]), np.concatenate([W1, W1, W2]), cases, th, T,
                  o["m"], 64, u["w"], g, tag=tag, window=200, reads={200})
    y = C.read_cg(np.concatenate([r2, r1]), np.concatenate([H2, H1]), np.concatenate([W2, W1]), cases, th, T, o["m"], 64,
                  u["w"], g[:2], tag=tag, window=200, reads={200})
    twice = np.array_equal(x["Vc"][:k], x["Vc"][k:2 * k]) and np.array_equal(x["in"][:k], x["in"][k:2 * k])
    order = (np.array_equal(x["Vc"][:k], y["Vc"][k:]) and np.array_equal(x["Vc"][2 * k:], y["Vc"][:k])
             and np.array_equal(x["in"][2 * k:], y["in"][:k]))
    return {"pass": bool(twice and order), "listed_twice": bool(twice), "reordered": bool(order)}


def q9(root):
    M = json.loads((root / "manifest.json").read_text())
    per = {}
    for key, t in M["tasks"].items():
        per.setdefault(key.split("/")[0], []).append(t["cpu_s"])
    dev = sum(np.mean(per[u]) for u in D.UNITS) * len(D.IDENTITIES["dev"]) / 3600
    longest = max(max(v) for v in per.values())
    wall = max(dev * 3600 / 12, longest) / 3600
    rss = M["worker_maxrss_mb_peak"]
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"]
    ok = dev <= 30 and wall <= 12 and rss <= 2048 and disk
    return {"pass": bool(ok), "forecast_dev_cpu_h": round(dev, 2), "forecast_dev_wall_h_12": round(wall, 2),
            "worker_rss_mb": rss, "disk_headroom": bool(disk)}


def q10(root, stage):
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(__import__("os").environ, PYTHONPATH=str(LANE))
    p = subprocess.run([sys.executable, "-m", "sm002.predict", "--root", str(root), "--stage", stage, "--out", str(out)],
                       capture_output=True, text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm002.tables", "--root", str(root), "--stage", stage, "--dir", str(out)],
                        capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    rep = json.loads((out / "reported.json").read_text()) if (out / "reported.json").exists() else {}
    from sm002 import predict as P
    want = sorted({s for s, *_ in P.PARTS})
    ok = (p.returncode == 0 and p2.returncode == 0 and bool(want) and sorted(scored) == want
          and sorted(rep.get("parts", {})) == sorted(P.CONTRASTS) and all("verdict" in v for v in scored.values())
          and (out / "TABLES.md").exists() and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p.stderr + p2.stderr)[-500:], "sizes": sizes, "statements": len(scored),
            "reported": len(rep.get("parts", {}))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--stage", default="preflight")
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    pairs = [tuple(p) for p in M["pairs"]]
    block, tag = pairs[0][1], M["tag"]
    t0 = time.time()
    checks = {}
    for name, fn in (("Q1_complete_finite", lambda: q1(root, pairs)), ("Q2_serial_equals_parallel", lambda: q2(root, pairs[0], tag)),
                     ("Q3_engine", lambda: q3(root, block, tag)), ("Q4_replay", lambda: q4(block, tag)),
                     ("Q5_aliases", lambda: q5(root, pairs)), ("Q6_reanalysis", lambda: q6(root, pairs)),
                     ("Q7_efficacy", lambda: q7(root, pairs)), ("Q8_pairing", lambda: q8(block, tag)),
                     ("Q9_resources", lambda: q9(root)), ("Q10_reader_dry_run", lambda: q10(root, a.stage))):
        t1 = time.time()
        try:
            checks[name] = fn()
        except Exception as exc:          # a check that cannot run fails
            checks[name] = {"pass": False, "error": repr(exc)}
        checks[name]["seconds"] = round(time.time() - t1, 1)
        print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": sorted({p[1] for p in pairs}), "tag": tag, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
