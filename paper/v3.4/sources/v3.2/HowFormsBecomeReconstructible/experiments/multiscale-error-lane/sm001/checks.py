"""SM001's qualification Q1-Q10 (DRAFT): python -m sm001.checks --root STAGE_ROOT [--receipt PATH]

Fixed before their results; run on the preflight blocks at the full shape (every FIT and TEST unit). Any failure stops
the campaign.
  Q1  complete and finite: every endpoint at its declared shape; the wall distance -1 or a distance in [0, w)
  Q2  serial equals parallel: one task rerun in-process gives bit-identical shards and raw states
  Q3  the engine: at side 32 (BE006's tag) sm001.sim.prepare equals dl002.sim.prepare (S4, S8, F0); sm001.sim.run equals
      be006.sim.run's dial-F and never-F at delays 0 and 58 over 4,000 updates (every saved endpoint and final state);
      with NP001's tag sm001.sim.successor equals np001.sim.successor over 2,000 updates; all bit for bit
  Q4  an independent per-case replay (its own draws from mse.native.address, its own body, record step, arbiter, cable
      solves by scipy's spsolve, trigger, commitment, pull and relearning; no sm001.sim, be006.sim, be002.sim, msegrid
      or dl001.sim) reproduces three full branches (4,000 updates) within 1e-8 in V and r and the bonds exactly:
      W4_x32 L4 dial-c1-m0-t300; W8_x64_r2 L8 dial-c2-m2-t3000; W16_x64_cross L8 dial-c0.5-m0-t30
  Q5  aliases: the successor's no-record control ends bit-identical across a task's patch sizes; a delayed dial equals
      its 'never' arm (same coupling and commitment) up to its delay (a short in-process run)
  Q6  reanalysis: the episode's patch agreement and the successor's at their last reads, recomputed from the saved raw
      final states, equal the saved endpoints within an absolute 1/64 for every patch size (one site of an 8 x 8 patch:
      the raw states are float32, so a site within 1e-6 of zero may change sign)
  Q7  efficacy: the event flips exactly the patch's record; the footprint is the patch dilated by the unit's dilation;
      every dial is on for exactly 1,000 updates and every 'never' arm for none; the refined units' sizes, couplings
      and dilation are exactly doubled; 'mid' patches sit (w - L) / 2 from the nearest wall and 'cross' patches straddle
      one symmetrically; T* is ln 1.8 / -ln(0.99)
  Q8  pairing: an arm listed twice gives bit-identical branches, and reordering the arms changes no branch (short runs)
  Q9  resources: the forecast for the fit stage (16 blocks) within 25 CPU-hours and for the test stage within 40, on 12
      workers within 12 h of wall, worker memory within 2 GB, and disk headroom
  Q10 the reader dry run: predict and tables complete, every statement scored, the reported parts written, every
      output file <= 256 KB
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as D  # noqa: E402
from sm001 import sim as S  # noqa: E402
from sm001 import worker as Wk  # noqa: E402


def q1(root, pairs):
    bad = []
    for u, b in pairs:
        z = np.load(root / "shards" / u / f"{b}.npz")
        na, k = len(D.unit_arms(u)), D.NCASE
        for L in D.UNIT[u]["sizes"]:
            rn = f"L{L}"
            for e in S.ENDS:
                if z[f"{rn}/{e}"].shape != (len(D.READS), na, k) or not np.isfinite(z[f"{rn}/{e}"]).all():
                    bad.append([u, b, rn, e])
            for e in S.ENDS2:
                if z[f"{rn}/s/{e}"].shape != (len(D.READS2), na + 1, k) or not np.isfinite(z[f"{rn}/s/{e}"]).all():
                    bad.append([u, b, rn, "s/" + e])
            wall = z[f"{rn}/wall"]
            if wall.shape != (k,) or not np.all((wall == -1) | ((wall >= 0) & (wall < D.UNIT[u]["w"]))):
                bad.append([u, b, rn, "wall"])
    return {"pass": not bad, "bad": bad[:10], "tasks": len(pairs)}


def q2(root, pair):
    u, b = pair
    with tempfile.TemporaryDirectory() as tmp:
        Wk.run_task(u, b, D.PURPOSE["preflight"], tmp)
        diff = []
        for kind in ("shards", "raw"):
            a, c = np.load(root / kind / u / f"{b}.npz"), np.load(Path(tmp) / kind / u / f"{b}.npz")
            diff += [f"{kind}/{k}" for k in a.files if k != "__meta__" and not np.array_equal(a[k], c[k])]
    return {"pass": not diff, "task": [u, b], "differ": diff[:10]}


def q3(block):
    from be006 import design as B6
    from be006 import sim as B6S
    from dl002 import sim as D2S
    from np001 import design as N1
    from np001 import sim as N1S
    out = {}
    for pat, w in (("S4", 4), ("S8", 8), ("F0", 16)):
        a, c = D2S.prepare(pat, block, "engineering"), S.prepare(f"W{w}", 32, block, "engineering")
        out[f"prepare_{pat}"] = all(np.array_equal(x, y) for x, y in zip(a[1:], c[1:]))
    cases, V0, ema0, R0, th, T = B6S.prepare("S4", block, "engineering")
    reads = {1000, 2000, 4000}
    for dly, arms_be in ((0, ("dial-F", "never-F")), (58, ("dial-F",))):
        ref = B6S.run("dw", "memory", 4, dly, arms_be, cases, V0, ema0, R0, th, T, 0.0, reads, tag=B6.TAG, window=4000)
        arms = [{"name": a, "lam_rest": 3.0, "lam_sig": 1.0, "delay": dly, "tau_c": 300.0, "never": a.startswith("never")}
                for a in arms_be]
        got = S.run(4, arms, cases, V0, ema0, R0, th, T, 32, 4, tag=B6.TAG, window=4000, reads=reads)
        pairs = [("r_in", "r_in"), ("r_all", "r_all"), ("v_in", "v_in"), ("n_anc_ok", "n_anc_ok"), ("r_fp2", "r_fp"),
                 ("V", "V"), ("r", "r"), ("H", "H"), ("W", "W"), ("hit", "hit"), ("onset", "onset")]
        out[f"run_memory4@{dly}"] = all(np.array_equal(ref[a], got[c]) for a, c in pairs)
        k = len(cases)
        rr, HH, WW = (np.concatenate([ref[x], ref[x][:k]]) for x in ("r", "H", "W"))
        gains = [0.2] * len(arms_be) + [0.0]
        s1 = N1S.successor("dw", rr, HH, WW, cases, th, T, {500, 1000, 2000}, gains, tag=N1.TAG, window=2000)
        s2 = S.successor(rr, HH, WW, cases, th, T, got["m"], 32, 4, gains, tag=N1.TAG, window=2000, reads={500, 1000, 2000})
        out[f"successor_memory4@{dly}"] = all(np.array_equal(s1[e], s2[e]) for e in ("align", "r_align", "shape", "spacing", "agree", "V"))
    return {"pass": all(out.values()), "items": out}


# Q4: the independent replay ----------------------------------------------------------------------------------------

def _draws(tag, case, stream, side, n_updates, chunk):
    """The case's draws, chunk by chunk, from its own generator (mse.native.address's convention)."""
    from mse.native import address
    g = address(tag, *case.key(), *stream)
    out = []
    for _ in range(int(math.ceil(n_updates / chunk))):
        out.append(g.standard_normal((chunk, side, side)))
    return np.concatenate(out)[:n_updates]


def _cable_matrix(side, g_right, g_down, g_leak):
    n = side * side
    idx = np.arange(n).reshape(side, side)
    right, down = np.roll(idx, -1, 1), np.roll(idx, -1, 0)
    rows = np.concatenate([idx.ravel(), idx.ravel(), right.ravel(), idx.ravel(), down.ravel()])
    cols = np.concatenate([idx.ravel(), right.ravel(), idx.ravel(), down.ravel(), idx.ravel()])
    deg = g_leak + g_right + np.roll(g_right, 1, 1) + g_down + np.roll(g_down, 1, 0)
    vals = np.concatenate([deg.ravel(), -g_right.ravel(), -g_right.ravel(), -g_down.ravel(), -g_down.ravel()])
    return sparse.csc_matrix((vals, (rows, cols)), shape=(n, n))


def replay(unit, L, arm_name, block, tag):
    """One case-0 branch replayed per case from the definitions; returns (V, r, H, W) at the end of the episode."""
    from be001 import design as B1
    from mse.native import NATIVE, address
    from scipy.special import ndtri
    u = D.UNIT[unit]
    side, w = u["side"], u["w"]
    arm = [a for a in D.unit_arms(unit) if a["name"] == arm_name][0]
    cases, V0, ema0, R0, th, T = S.prepare(f"W{w}", side, block, "engineering")
    j, c = 0, cases[0]
    # the event
    m = np.zeros((side, side), bool)
    if u["place"] == "random":
        a0, b0 = address(tag, *c.key(), "patch").integers(0, side, 2)
        m[np.ix_(np.arange(a0, a0 + L) % side, np.arange(b0, b0 + L) % side)] = True
    else:
        g = address(tag, *c.key(), "place")
        stripe, along = int(g.integers(0, side // w)), int(g.integers(0, side))
        a0 = stripe * w + (w - L) // 2 if u["place"] == "mid" else (stripe + 1) * w - L // 2
        ia, ib = np.arange(a0, a0 + L) % side, np.arange(along, along + L) % side
        if c.message % 2 == 0:
            m[np.ix_(ib, ia)] = True
        else:
            m[np.ix_(ia, ib)] = True
    am = np.zeros(side * side, bool)
    am[address(tag, *c.key(), "anchors", D.DENSITY).permutation(side * side)[: side * side // D.DENSITY]] = True
    am = am.reshape(side, side)
    V, E, r = V0[j].copy(), ema0[j].copy(), np.where(m, -R0[j], R0[j])
    s = np.where(r >= 0, 1.0, -1.0)
    H, W = s * np.roll(s, -1, 1), s * np.roll(s, -1, 0)
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    aval = np.where(R0[j] > 0, 1.0, -1.0)
    ca = np.where(am, aval, 0.0)
    fp = m.copy()
    for dy in range(-u["dil"], u["dil"] + 1):
        for dx in range(-u["dil"], u["dil"] + 1):
            fp |= np.roll(m, (dy, dx), (0, 1))
    lr2, ls2 = arm["lam_rest"] ** 2, arm["lam_sig"] ** 2
    touch_r, touch_d = fp | np.roll(fp, -1, 1), fp | np.roll(fp, -1, 0)
    A_on = _cable_matrix(side, np.where(touch_r, ls2, lr2), np.where(touch_d, ls2, lr2), B1.G_LEAK)
    A_off = _cable_matrix(side, np.full((side, side), lr2), np.full((side, side), lr2), B1.G_LEAK)
    cut = float(ndtri(1.0 - D.P_B))
    zs = _draws(tag, c, ("future",), side, D.WINDOW, D.CHUNK)
    xs = _draws(tag, c, ("record-noise",), side, D.WINDOW, D.CHUNK)
    bs = _draws(tag, c, ("bond-noise",), side, D.WINDOW, D.CHUNK)
    p = NATIVE
    vote = lambda x: np.where(x >= 0.2, 1.0, np.where(x <= -0.2, -1.0, 0.0))
    st, sgn = np.zeros((side, side)), np.zeros((side, side))
    s_min, theta, kappa = math.exp(-1.0), 0.1, 4.0
    nb = lambda x: (np.roll(x, 1, 0) + np.roll(x, -1, 0) + np.roll(x, 1, 1) + np.roll(x, -1, 1)) / 4.0
    for t in range(1, D.WINDOW + 1):
        drift = V - V ** 3 + p.well_asym + th[j] * D.THETA + p.coupling * (nb(V) - V)
        Vt = np.clip(V + p.dt * drift + D.SIGMA * zs[t - 1], -p.bound, p.bound)
        E = (1.0 - p.ema_rate) * E + p.ema_rate * Vt
        V = np.clip(Vt + p.dt * D.GAIN * (r - Vt), -p.bound, p.bound)
        z = bs[t - 1]
        fh, fw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(fh, -H, H), np.where(fw, -W, W), np.where(fh, -Hb, Hb), np.where(fw, -Wb, Wb)
        bsum = (np.roll(W, 1, 0) * np.roll(r, 1, 0) + W * np.roll(r, -1, 0) + np.roll(H, 1, 1) * np.roll(r, 1, 1)
                + H * np.roll(r, -1, 1)) / 4.0
        r = np.clip(r + D.EPS * (r * (1 - (r / 1.2) ** 2) + D.KR * (bsum - r)) + D.SIGMA_R * xs[t - 1], -2.0, 2.0)
        sv, sr = vote(V), vote(r)
        agree = (sv == sr) & (sv != 0)
        tgt = np.where(agree, sv, np.where(ca != 0, ca, np.where(sr != 0, sr, sv)))
        cur = (kappa * ca * sr).ravel()
        on = (not arm["never"]) and (arm["delay"] + 1 <= t <= arm["delay"] + D.DURATION)
        v = spsolve(A_on if on else A_off, cur).reshape(side, side)
        trig = (v < -theta) & (sr != 0)
        was = st >= s_min
        sgn = np.where(trig & ~was, -sr, sgn)
        st = np.where(trig, 1.0, st * math.exp(-1.0 / arm["tau_c"]))
        com = st >= s_min
        tgt = np.where(com, sgn, tgt)
        r = np.where(com, r + D.EPS * D.PULL * (tgt * 1.2 - r), r)
        xh, xw = tgt * np.roll(tgt, -1, 1), tgt * np.roll(tgt, -1, 0)
        lh, lw = xh != 0, xw != 0
        Hb, Wb = np.where(lh, Hb + D.ETA * (xh - Hb), Hb), np.where(lw, Wb + D.ETA * (xw - Wb), Wb)
        H, W = np.where(lh & (Hb != 0), np.sign(Hb), H), np.where(lw & (Wb != 0), np.sign(Wb), W)
    return V, r, H, W


Q4_BRANCHES = (("W4_x32", 4, "dial-c1-m0-t300"), ("W8_x64_r2", 8, "dial-c2-m2-t3000"), ("W16_x64_cross", 8, "dial-c0.5-m0-t30"))


def q4(block):
    res = {}
    for unit, L, arm_name in Q4_BRANCHES:
        u = D.UNIT[unit]
        arms = D.unit_arms(unit)
        ai = [a["name"] for a in arms].index(arm_name)
        cases, V0, ema0, R0, th, T = S.prepare(f"W{u['w']}", u["side"], block, "engineering")
        o = S.run(L, [arms[ai]], cases, V0, ema0, R0, th, T, u["side"], u["w"], place=u["place"], dil=u["dil"], tag=D.TAG,
                  reads={D.WINDOW})
        V, r, H, W = replay(unit, L, arm_name, block, D.TAG)
        res["/".join([unit, f"L{L}", arm_name])] = {"max_dV": float(np.abs(o["V"][0] - V).max()),
                                                     "max_dr": float(np.abs(o["r"][0] - r).max()),
                                                     "bonds_differ": int((o["H"][0] != H).sum() + (o["W"][0] != W).sum())}
    ok = all(v["max_dV"] <= 1e-8 and v["max_dr"] <= 1e-8 and v["bonds_differ"] == 0 for v in res.values())
    return {"pass": ok, **res}


def q5(root, pairs, block):
    same = []
    for u, b in pairs:
        z = np.load(root / "raw" / u / f"{b}.npz")
        na = len(D.unit_arms(u))
        ctrl = [z[f"L{L}/sV"][na] for L in D.UNIT[u]["sizes"]]
        same.append(all(np.array_equal(ctrl[0], x) for x in ctrl[1:]))
    u = "W4_x32"
    arms = {a["name"]: a for a in D.unit_arms(u)}
    dial, never = arms["dial-c1-m2-t300"], arms["never-c1-t300"]
    cases, V0, ema0, R0, th, T = S.prepare("W4", 32, block, "engineering")
    o = S.run(4, [dial, never], cases, V0, ema0, R0, th, T, 32, 4, tag=D.TAG, window=dial["delay"], reads=set())
    k = len(cases)
    before = all(np.array_equal(o[x][:k], o[x][k:]) for x in ("V", "r", "H", "W"))
    return {"pass": all(same) and before, "control_alike_across_sizes": all(same), "delayed_equals_never_before_onset": before}


def q6(root, pairs):
    from lr005 import sim as L5S
    worst = 0.0
    for u, b in pairs:
        z, raw = np.load(root / "shards" / u / f"{b}.npz"), np.load(root / "raw" / u / f"{b}.npz")
        T = raw["T"].astype(float)
        na, k = len(D.unit_arms(u)), D.NCASE
        for L in D.UNIT[u]["sizes"]:
            rn = f"L{L}"
            m = raw[f"{rn}/m"]
            r = raw[f"{rn}/r"].astype(np.float64)          # saved as float32: a sign at |r| < 1e-6 may differ
            rin = np.array([[L5S.inside(r[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na)])
            sv = raw[f"{rn}/sV"].astype(np.float64)
            sin = np.array([[L5S.inside(sv[ai, j:j + 1], T[j:j + 1], m[j:j + 1])[0] for j in range(k)] for ai in range(na + 1)])
            worst = max(worst, float(np.abs(rin - z[f"{rn}/r_in"][-1]).max()), float(np.abs(sin - z[f"{rn}/s/in"][-1]).max()))
    return {"pass": worst <= 1.0 / 64, "max_abs_diff": worst,
            "note": "an absolute 1/64 for every patch size (one site of an 8 x 8 patch): the raw states are float32, so a "
                    "site within 1e-6 of zero may change sign"}


def q7(root, pairs, block):
    from be002 import sim as B2S
    out = {"T_star": abs(D.T_STAR - math.log(1.8) / -math.log(0.99)) < 1e-12}
    ok_fp, ok_sig, ok_flip = True, True, True
    for u, b in pairs:
        z, raw = np.load(root / "shards" / u / f"{b}.npz"), np.load(root / "raw" / u / f"{b}.npz")
        cfg = D.UNIT[u]
        for L in cfg["sizes"]:
            m = raw[f"L{L}/m"]
            ok_flip &= bool((m.sum((-2, -1)) == L * L).all())
            sig = z[f"L{L}/signal_updates"]
            want = np.array([0 if a["never"] else D.DURATION for a in D.unit_arms(u)], float)
            ok_sig &= bool(np.array_equal(sig, want))
    out.update(patch_sizes=ok_flip, signal_windows=ok_sig)
    for u in D.UNIT:
        if D.UNIT[u]["kind"] == "refine":
            base_u = D.unit_name(D.UNIT[u]["w"] // 2, D.SIDE_FIT)
            b0, r0 = D.UNIT[base_u], D.UNIT[u]
            ok_fp &= r0["sizes"] == tuple(2 * s for s in b0["sizes"]) and r0["couplings"] == tuple(2 * x for x in b0["couplings"])
            ok_fp &= r0["dil"] == 2 * b0["dil"] and r0["side"] == 2 * b0["side"]
    out["refinement_doubles_every_length"] = bool(ok_fp)
    cases, V0, ema0, R0, th, T = S.prepare("W16", 64, block, "engineering")
    ev = S.memory_event(8, cases, V0, ema0, R0, T, 64, 16, "cross", D.TAG)
    out["event_flips_exactly_the_patch"] = bool(np.array_equal(ev["r"], np.where(ev["m"], -R0, R0)))
    fp = B2S.footprint(ev["m"], 2)
    out["footprint_is_the_dilation"] = bool(all(fp[j].sum() == (8 + 4) ** 2 for j in range(len(cases))))
    mid = S.patch(cases, 8, 64, 16, "mid", D.TAG)
    cross = ev["m"]
    out["mid_and_cross"] = all(S.wall_distance(T[j], mid[j], 16, c.message) == 4 and S.wall_distance(T[j], cross[j], 16, c.message) == -1
                               for j, c in enumerate(cases))
    return {"pass": all(out.values()), **out}


def q8(block):
    u = "W4_x32"
    arms = {a["name"]: a for a in D.unit_arms(u)}
    a1, a2 = arms["dial-c1-m1-t300"], arms["dial-c0.5-m0-t3000"]
    cases, V0, ema0, R0, th, T = S.prepare("W4", 32, block, "engineering")
    o1 = S.run(4, [a1, a1, a2], cases, V0, ema0, R0, th, T, 32, 4, tag=D.TAG, window=300, reads={300})
    o2 = S.run(4, [a2, a1], cases, V0, ema0, R0, th, T, 32, 4, tag=D.TAG, window=300, reads={300})
    k = len(cases)
    twice = all(np.array_equal(o1[x][:k], o1[x][k:2 * k]) for x in ("V", "r", "H", "W"))
    order = all(np.array_equal(o1[x][:k], o2[x][k:]) and np.array_equal(o1[x][2 * k:], o2[x][:k]) for x in ("V", "r", "H", "W"))
    return {"pass": twice and order, "listed_twice": twice, "reordered": order}


def q9(root):
    M = json.loads((root / "manifest.json").read_text())
    per = {}
    for key, t in M["tasks"].items():
        per.setdefault(key.split("/")[0], []).append(t["cpu_s"])
    fit = sum(np.mean(per[u]) for u in D.FIT_UNITS) * 16 / 3600
    test = sum(np.mean(per[u]) for u in D.TEST_UNITS) * 16 / 3600
    longest = max(max(v) for v in per.values())
    wall_test = max(test * 3600 / 12, longest) / 3600
    rss = M["worker_maxrss_mb_peak"]
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"]
    ok = fit <= 25 and test <= 40 and wall_test <= 12 and rss <= 2048 and disk
    return {"pass": bool(ok), "forecast_fit_cpu_h": round(fit, 2), "forecast_test_cpu_h": round(test, 2),
            "forecast_test_wall_h_12": round(wall_test, 2), "worker_rss_mb": rss, "disk_headroom": bool(disk)}


def q10(root, stage):
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(__import__("os").environ, PYTHONPATH=str(LANE))
    cmd = [sys.executable, "-m", "sm001.predict", "--root", str(root), "--stage", stage, "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "sm001.tables", "--root", str(root), "--stage", stage, "--dir", str(out)],
                        capture_output=True, text=True, env=env, cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    reported = json.loads((out / "reported.json").read_text()) if (out / "reported.json").exists() else {}
    from sm001 import predict as P
    want = sorted({sid for sid, *_ in P.PARTS})
    want_r = sorted({sid for sid, *_ in P.REPORTED})
    ok = (p.returncode == 0 and p2.returncode == 0 and sorted(scored) == want and want
          and sorted(reported.get("parts", {})) == want_r and "fit_r2" in reported.get("summary", {})
          and all("verdict" in v for v in scored.values()) and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p.stderr + p2.stderr)[-500:], "sizes": sizes, "statements": len(scored),
            "reported": len(reported.get("parts", {}))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--stage", default="preflight")
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    pairs = [tuple(p) for p in M["pairs"]]
    block = pairs[0][1]
    t0 = time.time()
    checks = {}
    for name, fn in (("Q1_complete_finite", lambda: q1(root, pairs)), ("Q2_serial_equals_parallel", lambda: q2(root, pairs[0])),
                     ("Q3_engine", lambda: q3(block)), ("Q4_replay", lambda: q4(block)), ("Q5_aliases", lambda: q5(root, pairs, block)),
                     ("Q6_reanalysis", lambda: q6(root, pairs)), ("Q7_efficacy", lambda: q7(root, pairs, block)),
                     ("Q8_pairing", lambda: q8(block)), ("Q9_resources", lambda: q9(root)), ("Q10_reader_dry_run", lambda: q10(root, a.stage))):
        t1 = time.time()
        try:
            checks[name] = fn()
        except Exception as exc:          # a check that cannot run fails
            checks[name] = {"pass": False, "error": repr(exc)}
        checks[name]["seconds"] = round(time.time() - t1, 1)
        print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": sorted({p[1] for p in pairs}), "tag": M.get("tag"), "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
