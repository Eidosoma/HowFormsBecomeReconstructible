"""T4b: is consensus's loss of BL detail a property of the shapes or of the lattice spacing? ENGINEERING_PROBE_NOT_EVIDENCE.

The same 18 patterns as T4 (BR001's two BL bases and 16 fresh blobs), each also drawn at 2x and 4x resolution
by repeating every site as a 2 x 2 or 4 x 4 block (side 32 and 64: the same shapes on a finer lattice). The
record alone, BR001's 'self' arm (k_r = 1), R0 = 0.911 sign(P), 4 replicates, 2000 and 8000 updates. If the
loss belongs to the shapes it should not fall with resolution at matched physical time; the lattice coupling
is per site, so a finer lattice also means slower curvature flow in pattern units (4x per doubling).
"""
from __future__ import annotations

import time

import numpy as np

import xcommon as X
from xcommon import address

from br001 import design as D
from me002.families import blobs

REPS, AMP = 4, 0.9109


def main():
    t0 = time.time()
    b0, b1, _ = blobs("mse-me002")
    fresh = [X.balanced_blob(address(X.TAG, X.BLOCKS[8], "t4-pattern", j)) for j in range(16)]
    base = np.stack([b0, b1, *fresh])
    out = {"test": "T4b resolution", "reps": REPS, "levels": {}}
    for scale in (1, 2, 4):
        pats = np.stack([np.kron(p, np.ones((scale, scale))) for p in base])
        P = np.repeat(pats, REPS, axis=0)
        g = address(X.TAG, X.BLOCKS[8], "t4b-record-noise", scale)
        r = AMP * P.copy()
        res = {}
        for t in range(1, 8001):
            r = X.record_step(r, g.standard_normal(r.shape), D.EPS, D.KR, D.SIGMA_R, 0.0, None)
            if t in (2000, 8000):
                rs = ((r > 0) == (P > 0)).mean((-2, -1)).reshape(len(base), REPS).mean(1)
                res[str(t)] = {"BR001": [round(float(x), 4) for x in rs[:2]],
                               "fresh_mean": round(float(rs[2:].mean()), 4), "fresh_min": round(float(rs[2:].min()), 4),
                               "fresh_max": round(float(rs[2:].max()), 4)}
        out["levels"][f"x{scale}"] = res
        print(f"scale {scale} side {16 * scale} {time.time() - t0:.0f}s", res, flush=True)
        X.save("t4b_resolution.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
