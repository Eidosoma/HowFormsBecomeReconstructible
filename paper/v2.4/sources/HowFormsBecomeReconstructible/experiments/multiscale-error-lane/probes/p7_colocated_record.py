"""Engineering probe P7 (python probes/p7_colocated_record.py CPU): a record that lives in the tissue.
ENGINEERING_PROBE_NOT_EVIDENCE; a design input for the biological-realism study.

Each cell carries a slow record value r_i beside its state v_i. The body reads its own record with the
native gain (ME002's hold route, unchanged physics). The record has its own slow dynamics:
    r <- r + eps [ r (1 - (r / 1.2)^2) + kr (N(r) - r) ] + sigma_r xi        (a quiet, bistable, coupled layer)
    r <- r + kc (P4(B) - P4(r))                                              (optional protected coarse code B:
                                                                              the taught record's 16 region means)
A wound flips the sign of an s x s patch of the body and the record together (also record-only and body-only
lesions). Engineering blocks 900996-900999 (32 cases), F0, window 2,000, lesion at a random position per case.
Arms: static record (ME002's hold), self-correcting record, static record + coarse code, both, protected copy.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from mse.engine import Route, State, step  # noqa: E402
from mse.native import address, neighbours  # noqa: E402
from mse.ops import block_projection  # noqa: E402

BLOCKS = list(range(900996, 901000))
L = 2000
HOLD = Route(reference=None)
ARMS = {  # eps, kr, kc, clamp
    "static": (0.0, 0.0, 0.0, False),
    "self_correcting": (0.05, 1.0, 0.0, False),
    "coarse_code": (0.0, 0.0, 0.02, False),
    "self_correcting+code": (0.05, 1.0, 0.02, False),
    "protected": (0.0, 0.0, 0.0, True),
}


def run(name, sigma_r, s, target, cases, s0, th, p, Z, T):
    k = len(cases)
    pos = np.array([address(D.TAG, *c.key(), "p7", "lesion").integers(0, 16, 2) for c in cases])
    mask = np.zeros((k, 16, 16), bool)
    for i, (a, b) in enumerate(pos):
        rows, cols = (np.arange(a, a + s) % 16), (np.arange(b, b + s) % 16)
        mask[i][np.ix_(rows, cols)] = True
    V, R = s0.V.copy(), s0.R.copy()
    if target in ("both", "body"):
        V = np.where(mask, -V, V)
    if target in ("both", "record"):
        R = np.where(mask, -R, R)
    B = block_projection(s0.R, 4)
    out = {}
    for arm, (eps, kr, kc, clamp) in ARMS.items():
        v, ema, r, Q = V.copy(), s0.ema.copy(), R.copy(), np.zeros_like(V)
        gens = [address(D.TAG, *c.key(), "p7", "record-noise") for c in cases]
        for t in range(L):
            st = step(State(v, ema, r, Q), th, Z[t], HOLD, p)
            v, ema, Q = st.V, st.ema, st.Q
            if eps > 0:
                xi = np.stack([g.standard_normal((16, 16)) for g in gens])
                r = r + eps * (r * (1 - (r / 1.2) ** 2) + kr * (neighbours(r) - r)) + sigma_r * xi
            if kc > 0:
                r = r + kc * (B - block_projection(r, 4))
            r = np.clip(r, -2.0, 2.0)
            if clamp:
                r = s0.R.copy()
        m_body = ((v > 0) == (T > 0)) & (np.abs(v) > 0.2)
        rec_ok = (r > 0) == (T > 0)
        out[arm] = {"v_qual": round(float(m_body.mean()), 4),
                    "lesion_body_repaired": round(float((((v > 0) == (T > 0)) & mask).sum() / max(mask.sum(), 1)), 4),
                    "lesion_record_repaired": round(float((rec_ok & mask).sum() / max(mask.sum(), 1)), 4),
                    "record_sign_outside": round(float((rec_ok & ~mask).sum() / (~mask).sum()), 4)}
    return out


def main():
    os.sched_setaffinity(0, {int(sys.argv[1])} if len(sys.argv) > 1 else os.sched_getaffinity(0))
    t0 = time.time()
    res = {}
    for sigma in (0.1, 0.3):
        name = D.regime("F0", sigma)
        cases, s0, th, p, T, Tf = sim.prepare(name, BLOCKS, "engineering")
        Z = sim.draws(cases, "p7-future", updates=L)
        for sigma_r in (0.02,):
            for target in ("both", "record", "body"):
                for s in (2, 4, 6, 8):
                    key = f"sigma{sigma}/{target}/{s}x{s}"
                    res[key] = run(name, sigma_r, s, target, cases, s0, th, p, Z, T)
                    print(key, json.dumps({a: (v["lesion_record_repaired"], v["lesion_body_repaired"], v["v_qual"]) for a, v in res[key].items()}), flush=True)
            res[f"sigma{sigma}/sham"] = run(name, sigma_r, 0, "both", cases, s0, th, p, Z, T)
    out = {"probe": "P7", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "blocks": [BLOCKS[0], BLOCKS[-1] + 1],
           "window": L, "arms": {k: dict(zip(("eps", "kr", "kc", "clamp"), v)) for k, v in ARMS.items()},
           "results": res, "wall_s": round(time.time() - t0, 1)}
    (LANE / "probes" / "results" / "p7_colocated_record_v1.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wall", out["wall_s"])


if __name__ == "__main__":
    main()
