"""T1b: are flipped wounds the worst case? ENGINEERING_PROBE_NOT_EVIDENCE.

BR001's lesions multiply the patch by -1: every wounded cell holds the opposite pattern, a stable wrong state.
Biological wounds mostly remove or reset cells. Here T1's placements at sides 16 and 32 under BR001's consensus
record ('self', k_r 1) and 'multi', with three wound kinds: flip (r -> -r, as BR001), blank (r -> 0, an
unstable point of the bistable record) and newborn (r -> 0.2 N(0,1), turnover's newborn value).
Kept = sign agreement inside the patch at t = 2000 and 4000.
"""
from __future__ import annotations

import time

import numpy as np

import xcommon as X
from xcommon import address

from br001 import design as D

from t1_geometry import placements

AMP, REPS = 0.9109, 8


def main():
    t0 = time.time()
    out = {"test": "T1b wound kind", "levels": {}}
    arms = {"self": (D.EPS, D.KR, 0.0), "multi": (D.EPS, D.KR, D.KC)}
    for side in (16, 32):
        T = X.half_plane0(side)
        pl = [x for x in placements(side) if x[1] >= 4]
        n = len(pl) * REPS
        mask = np.zeros((n, side, side), bool)
        for i, (_, s, c0) in enumerate(pl):
            for j in range(REPS):
                r0 = (5 * j) % side
                mask[i * REPS + j][np.ix_(np.arange(r0, r0 + s) % side, np.arange(c0, c0 + s) % side)] = True
        R0 = np.broadcast_to(AMP * T, (n, side, side)).copy()
        B = X.bproj(R0, 4)
        nb = 0.2 * address(X.TAG, X.BLOCKS[14], "t1b-newborn", side).standard_normal((n, side, side))
        for kind in ("flip", "blank", "newborn"):
            start = {"flip": -R0, "blank": np.zeros_like(R0), "newborn": nb}[kind]
            for name, (eps, kr, kc) in arms.items():
                g = address(X.TAG, X.BLOCKS[14], "t1b-noise", side)
                r = np.where(mask, start, R0)
                res = {}
                for t in range(1, 4001):
                    r = X.record_step(r, g.standard_normal((n, side, side)), eps, kr, D.SIGMA_R, kc, B)
                    if t in (2000, 4000):
                        kept = (((r > 0) == (T > 0)) & mask).sum((-2, -1)) / mask.sum((-2, -1))
                        for i, (pname, _, _) in enumerate(pl):
                            res.setdefault(pname, {})[str(t)] = round(float(kept[i * REPS:(i + 1) * REPS].mean()), 4)
                out["levels"][f"side{side}_{kind}_{name}"] = res
                print(f"side {side} {kind} {name} {time.time() - t0:.0f}s",
                      " ".join(f"{p}:{v['2000']:.2f}/{v['4000']:.2f}" for p, v in res.items()), flush=True)
                X.save("t1b_wound_kind.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
