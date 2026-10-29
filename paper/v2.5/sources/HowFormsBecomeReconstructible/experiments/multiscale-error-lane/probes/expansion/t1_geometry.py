"""T1: does consensus repair depend on lesion size, or on the 16-site torus? ENGINEERING_PROBE_NOT_EVIDENCE.

Part Q (qualification). On engineering block 900832 under the tag 'mse-expansion': BR001's acquisition and
br001.sim.simulate for the panel-L arms static/self/code/multi, conserved and open bodies, sigma 0.1 and 0.3,
against this study's side-agnostic restatement (xcommon.body_step, record_step). Required: v and r equal bit
for bit. Also checked: with writing off, the record r is bit-identical across bodies (it never reads v).

Part G (geometry). The record alone (it does not read the body when writing is off), F0 kind 0 at sides 16,
32 and 64 (domains side/2 thick), R0 = A sign(T) with A the mean |R0| of the acquired sigma-0.3 records.
Lesions flip r in an s x s patch at declared column margins from the nearest wall (d0 touches a wall, 'mid'
is centred, 'cross' straddles a wall); rows vary by replicate. Kept = sign agreement inside the patch at
t = 250 ... 4000; 'undecided' = fraction of patch sites with |r| < 0.2.
"""
from __future__ import annotations

from dataclasses import replace
import sys
import time

import numpy as np

import xcommon as X
from xcommon import NATIVE, address

from br001 import design as D
from br001 import sim
from mse.assay import Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run

W = D.WINDOW


def acquire(cases, p, family="F0"):
    T = D.TEMPLATES[family][[c.message for c in cases]]
    Tf = D.TEMPLATES[family][[D.FOREIGN[c.message] for c in cases]]
    th = theta(X.TAG, cases, p, per_tissue=D.PER_TISSUE_THETA)
    V = birth(X.TAG, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(X.TAG, cases, "settle"), Route(capture=None), D.SETTLE, p)
    s = run(s, th, Noise(X.TAG, cases, "teach"), Route(capture=None), D.TEACH, p, imposed=T)
    s = run(s, th, Noise(X.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, T, Tf


def masks_for(cases, size, stream):
    out = np.zeros((len(cases), 16, 16), bool)
    for i, c in enumerate(cases):
        a, b = address(X.TAG, *c.key(), "t1-lesion", stream).integers(0, 16, 2)
        out[i][np.ix_(np.arange(a, a + size) % 16, np.arange(b, b + size) % 16)] = True
    return out


def general(arm, conds, k, V, ema, R, R0, th, Z, XI, p, conserved, tau, masks):
    nc = len(conds)
    idx = np.tile(np.arange(k), nc)
    thb, taub = th[idx], np.tile(tau, nc)
    mask = np.concatenate([masks[c] if masks[c] is not None else np.zeros((k, 16, 16), bool) for c in range(nc)])
    kind = np.repeat([c.kind for c in conds], k)
    target = np.repeat([c.target for c in conds], k)
    gain = NATIVE.gain if arm.reads else 0.0
    B = X.bproj(R0, 4)[idx]
    R0b = R0[idx]
    v, e, r = V[idx].copy(), ema[idx].copy(), R[idx].copy()
    for t in range(1, W + 1):
        start = taub == t
        if start.any():
            m3 = mask & start[:, None, None]
            hit_v = m3 & ((kind == "lesion") & np.isin(target, ("both", "body")))[:, None, None]
            hit_r = m3 & ((kind == "lesion") & np.isin(target, ("both", "record")))[:, None, None]
            v = np.where(hit_v, -v, v)
            r = np.where(hit_r, -r, r)
        v, e, _ = X.body_step(v, e, r, thb, Z[t - 1][idx], p, conserved, gain)
        r = X.record_step(r, XI[t - 1][idx], arm.eps, arm.kr, arm.sigma_r, arm.kc, B)
        if arm.clamp:
            r = R0b.copy()
    return v, e, r


def qualify():
    cases = enrol([X.BLOCKS[0]], D.MESSAGES, D.PARENTS, "engineering")
    k = len(cases)
    conds = (D.Cond("sham"), D.Cond("both-4x4", "lesion", "both", 4), D.Cond("both-8x8", "lesion", "both", 8),
             D.Cond("record-6x6", "lesion", "record", 6), D.Cond("body-6x6", "lesion", "body", 6))
    masks = [None] + [masks_for(cases, c.size, c.name) for c in conds[1:]]
    tau = np.ones(k, int)
    Z = np.stack([address(X.TAG, *c.key(), "t1-future").standard_normal((W, 16, 16)) for c in cases], 1)
    XI = np.stack([address(X.TAG, *c.key(), "t1-record-noise").standard_normal((W, 16, 16)) for c in cases], 1)
    rows, amp = [], None
    for sigma in (0.1, 0.3):
        p = replace(NATIVE, sigma=sigma)
        s0, th, T, Tf = acquire(cases, p)
        if sigma == 0.3:
            amp = float(np.abs(s0.R).mean())
        r_by_body = {}
        for conserved in (True, False):
            for name in ("static", "self", "code", "multi"):
                arm = D.ARM["L"][name]
                t0 = time.time()
                v1, e1, r1, _ = sim.simulate(arm, conds, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved,
                                             T, Tf, tau, masks, [None] * len(conds))
                v2, e2, r2 = general(arm, conds, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, tau, masks)
                same = bool(np.array_equal(v1, v2) and np.array_equal(e1, e2) and np.array_equal(r1, r2))
                r_by_body.setdefault(name, []).append(r1)
                rows.append({"sigma": sigma, "conserved": conserved, "arm": name, "bit_exact": same,
                             "wall_s": round(time.time() - t0, 1)})
                print(rows[-1], flush=True)
        for name, (rc, ro) in r_by_body.items():
            rows.append({"sigma": sigma, "arm": name, "record_identical_across_bodies": bool(np.array_equal(rc, ro))})
            print(rows[-1], flush=True)
    return rows, amp


def placements(side):
    """(name, size, first column) inside the positive domain [0, side/2), or straddling the wall at side/2."""
    h = side // 2
    out = []
    for s in sorted({2, 4, 6, 8, 12, 16, 24} & set(range(2, h + 1))):
        for m in sorted({0, 1, 2, 4, (h - s) // 2}):
            if s + m <= h and m <= (h - s) // 2:
                out.append((f"s{s}-m{m}" + ("-mid" if m == (h - s) // 2 else ""), s, m))
        out.append((f"s{s}-cross", s, h - s // 2))
    return out


def geometry(amp, side, reps, arms, snaps=(250, 500, 1000, 2000, 4000)):
    T = X.half_plane0(side)
    pl = placements(side)
    n = len(pl) * reps
    mask = np.zeros((n, side, side), bool)
    for i, (_, s, c0) in enumerate(pl):
        for j in range(reps):
            r0 = (5 * j) % side
            mask[i * reps + j][np.ix_(np.arange(r0, r0 + s) % side, np.arange(c0, c0 + s) % side)] = True
    R0 = np.broadcast_to(amp * T, (n, side, side)).copy()
    B = X.bproj(R0, 4)
    out = {}
    for name, (eps, kr, kc) in arms.items():
        t0 = time.time()
        g = address(X.TAG, X.BLOCKS[1], "t1-geometry-noise", side)   # the same draws for every arm
        r = np.where(mask, -R0, R0)
        res = {}
        for t in range(1, max(snaps) + 1):
            r = X.record_step(r, g.standard_normal((n, side, side)), eps, kr, D.SIGMA_R, kc, B)
            if t in snaps:
                agree = ((r > 0) == (T > 0)) & mask
                und = (np.abs(r) < 0.2) & mask
                kept = agree.sum((-2, -1)) / mask.sum((-2, -1))
                undec = und.sum((-2, -1)) / mask.sum((-2, -1))
                outside = (((r > 0) == (T > 0)) & ~mask).sum((-2, -1)) / (~mask).sum((-2, -1))
                for i, (pname, s, c0) in enumerate(pl):
                    sl = slice(i * reps, (i + 1) * reps)
                    res.setdefault(pname, {})[str(t)] = {"kept": round(float(kept[sl].mean()), 4),
                                                        "kept_min": round(float(kept[sl].min()), 4),
                                                        "undecided": round(float(undec[sl].mean()), 4),
                                                        "outside": round(float(outside[sl].mean()), 4)}
        out[name] = res
        print(f"side {side} arm {name}: {time.time() - t0:.0f} s", flush=True)
        for pname in res:
            print(f"  {pname:14s} " + " ".join(f"{res[pname][str(t)]['kept']:.3f}" for t in snaps)
                  + f"  undecided@{max(snaps)} {res[pname][str(max(snaps))]['undecided']:.3f}", flush=True)
    return out


def main():
    t0 = time.time()
    rows, amp = qualify()
    ok = all(r.get("bit_exact", True) and r.get("record_identical_across_bodies", True) for r in rows)
    print("QUALIFIED" if ok else "QUALIFICATION FAILED", "amp", amp, flush=True)
    result = {"test": "T1 geometry", "qualification": rows, "qualified": ok, "amp": amp}
    X.save("t1_geometry.json", result)
    if not ok:
        sys.exit(1)
    arms = {"self": (D.EPS, D.KR, 0.0), "multi": (D.EPS, D.KR, D.KC), "code": (0.0, D.KR, D.KC),
            "self_kr2": (D.EPS, 2.0, 0.0)}
    result["geometry"] = {}
    for side, reps in ((16, 8), (32, 8), (64, 4)):
        result["geometry"][str(side)] = geometry(amp, side, reps, arms)
        result["wall_s"] = round(time.time() - t0, 1)
        X.save("t1_geometry.json", result)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
