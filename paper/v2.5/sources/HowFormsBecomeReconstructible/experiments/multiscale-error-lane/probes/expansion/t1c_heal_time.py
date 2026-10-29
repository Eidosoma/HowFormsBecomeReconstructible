"""T1c: how does consensus's healing time grow with wound size, far from walls? ENGINEERING_PROBE_NOT_EVIDENCE.

Side 64, F0 kind 0 (domains 32 thick), wounds centred in the positive domain (margin >= 8), sizes 4-16,
flip and blank, BR001's consensus record ('self', k_r 1), 4 replicates, kept fraction every 100 updates up to
16000. Reports the first time the mean kept fraction reaches 0.5 and 0.95.
"""
from __future__ import annotations

import time

import numpy as np

import xcommon as X
from xcommon import address

from br001 import design as D

AMP, REPS, SIDE, T_MAX = 0.9109, 4, 64, 16000
SIZES = (4, 6, 8, 10, 12, 16)


def main():
    t0 = time.time()
    T = X.half_plane0(SIDE)
    n = len(SIZES) * REPS
    mask = np.zeros((n, SIDE, SIDE), bool)
    for i, s in enumerate(SIZES):
        c0 = (SIDE // 2 - s) // 2
        for j in range(REPS):
            r0 = (11 * j) % SIDE
            mask[i * REPS + j][np.ix_(np.arange(r0, r0 + s) % SIDE, np.arange(c0, c0 + s) % SIDE)] = True
    R0 = np.broadcast_to(AMP * T, (n, SIDE, SIDE)).copy()
    out = {"test": "T1c healing time", "sizes": SIZES, "reps": REPS, "side": SIDE, "levels": {}}
    for kind in ("flip", "blank"):
        g = address(X.TAG, X.BLOCKS[15], "t1c-noise")
        r = np.where(mask, -R0 if kind == "flip" else 0.0, R0)
        curve = {s: [] for s in SIZES}
        for t in range(1, T_MAX + 1):
            r = X.record_step(r, g.standard_normal(r.shape), D.EPS, D.KR, D.SIGMA_R, 0.0, None)
            if t % 100 == 0:
                kept = (((r > 0) == (T > 0)) & mask).sum((-2, -1)) / mask.sum((-2, -1))
                for i, s in enumerate(SIZES):
                    curve[s].append(float(kept[i * REPS:(i + 1) * REPS].mean()))
        res = {}
        for s in SIZES:
            c = np.array(curve[s])
            first = lambda q: int(100 * (np.argmax(c >= q) + 1)) if (c >= q).any() else None
            res[str(s)] = {"t50": first(0.5), "t95": first(0.95), "kept_final": round(c[-1], 4),
                           "kept_2000": round(c[19], 4), "kept_4000": round(c[39], 4)}
        out["levels"][kind] = res
        print(kind, f"{time.time() - t0:.0f}s", res, flush=True)
        X.save("t1c_heal_time.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
