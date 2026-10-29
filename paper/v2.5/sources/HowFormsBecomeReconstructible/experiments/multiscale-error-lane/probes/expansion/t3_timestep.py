"""T3: are the numbers properties of the equations or of the time step? ENGINEERING_PROBE_NOT_EVIDENCE.

Part B (body). The native update is one Euler step of dt = 0.2 with noise sigma z per step (diffusion
D = sigma^2 / (2 dt)). Here the same physical time (2000 native updates) is integrated with m = 1, 2 or 4
sub-steps of dt / m with noise sigma / sqrt(m), the sub-step draws built from the native draw by Brownian
bridging, so the m paths share the native path (z = sum of the sub-draws / sqrt(m)). Conserved body, F0 and
BL, sigma 0.1, 0.2, 0.3, gain 0 and 0.2 reading the held record. Blocks 900837-900838 (16 cases).

Part R (record). BR001's consensus record ('self', k_r = 1) with eps / m, sigma_r / sqrt(m) and m times the
updates, on T1's critical placements at side 16 and 32.
"""
from __future__ import annotations

from dataclasses import replace
import time

import numpy as np

import xcommon as X
from xcommon import NATIVE, address

from br001 import design as D
from mse.assay import Noise, enrol

from t1_geometry import acquire, placements
from t2_bodies import scores

BLOCKS = list(X.BLOCKS[5:7])
UPDATES = 2000


def substeps(z, ws):
    """Split one native draw into len(ws) + 1 = m sub-draws (m = 1, 2, 4) whose sum / sqrt(m) is z."""
    if not ws:
        return [z]
    if len(ws) == 1:
        w = ws[0]
        return [(z + w) / np.sqrt(2), (z - w) / np.sqrt(2)]
    a, b = (z + ws[0]) / np.sqrt(2), (z - ws[0]) / np.sqrt(2)
    return [(a + ws[1]) / np.sqrt(2), (a - ws[1]) / np.sqrt(2), (b + ws[2]) / np.sqrt(2), (b - ws[2]) / np.sqrt(2)]


def body_part(out, t0):
    cases = enrol(BLOCKS, D.MESSAGES, D.PARENTS, "engineering")
    k = len(cases)
    for fam in ("F0", "BL"):
        for sigma in (0.1, 0.2, 0.3):
            p = replace(NATIVE, sigma=sigma)
            s0, th, T, _ = acquire(cases, p, fam)
            g = np.repeat([0.0, 0.2], k)[:, None, None]
            r = np.tile(s0.R, (2, 1, 1))
            thb = np.tile(th, (2, 1, 1))
            for m in (1, 2, 4):
                pm = replace(p, dt=p.dt / m, sigma=sigma / np.sqrt(m))
                base = Noise(X.TAG, cases, "t3-future")
                splits = [Noise(X.TAG, cases, "t3-split", j) for j in range(m - 1)]
                v, e = np.tile(s0.V, (2, 1, 1)), np.tile(s0.ema, (2, 1, 1))
                for t in range(1, UPDATES + 1):
                    for z in substeps(base(t), [s(t) for s in splits]):
                        v, e, _ = X.body_step(v, e, r, thb, np.tile(z, (2, 1, 1)), pm, True, g)
                key = f"{fam}_s{sigma:g}_m{m}"
                out["body"][key] = {name: {q: round(float(x.mean()), 4) for q, x in scores(v[i * k:(i + 1) * k], T).items()}
                                    for i, name in enumerate(("g0", "g0.2"))}
                print(key, f"{time.time() - t0:.0f}s", {n: (d["sign"], d["qual"], d["shift_best"])
                                                      for n, d in out["body"][key].items()}, flush=True)
            X.save("t3_timestep.json", out)


def record_part(out, t0, amp=0.9109):
    keep = {"s4-m0", "s4-m1", "s4-m2-mid", "s6-m0", "s6-m1-mid", "s6-cross", "s8-cross", "s8-m0-mid",
            "s8-m2", "s8-m4-mid", "s12-m2-mid", "s6-m2"}
    for side in (16, 32):
        T = X.half_plane0(side)
        pl = [x for x in placements(side) if x[0] in keep]
        reps = 8
        n = len(pl) * reps
        mask = np.zeros((n, side, side), bool)
        for i, (_, s, c0) in enumerate(pl):
            for j in range(reps):
                r0 = (5 * j) % side
                mask[i * reps + j][np.ix_(np.arange(r0, r0 + s) % side, np.arange(c0, c0 + s) % side)] = True
        R0 = np.broadcast_to(amp * T, (n, side, side)).copy()
        for m in (1, 2, 4):
            gs = [address(X.TAG, X.BLOCKS[7], "t3-record-noise", side, j) for j in range(m)]
            r = np.where(mask, -R0, R0)
            for t in range(1, UPDATES + 1):
                # m sub-draws per native update; their sum / sqrt(m) is the same native draw for every m
                if m == 1:
                    subs = [gs[0].standard_normal((n, side, side))]
                else:
                    z = gs[0].standard_normal((n, side, side))
                    subs = substeps(z, [gg.standard_normal((n, side, side)) for gg in gs[1:]])
                for xi in subs:
                    r = X.record_step(r, xi, D.EPS / m, D.KR, D.SIGMA_R / np.sqrt(m), 0.0, None)
            kept = (((r > 0) == (T > 0)) & mask).sum((-2, -1)) / mask.sum((-2, -1))
            out["record"][f"side{side}_m{m}"] = {name: round(float(kept[i * reps:(i + 1) * reps].mean()), 4)
                                                 for i, (name, _, _) in enumerate(pl)}
            print(f"record side {side} m {m} {time.time() - t0:.0f}s", out["record"][f"side{side}_m{m}"], flush=True)
            X.save("t3_timestep.json", out)


def main():
    t0 = time.time()
    out = {"test": "T3 time step", "blocks": BLOCKS, "body": {}, "record": {}}
    record_part(out, t0)
    body_part(out, t0)
    out["wall_s"] = round(time.time() - t0, 1)
    X.save("t3_timestep.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
