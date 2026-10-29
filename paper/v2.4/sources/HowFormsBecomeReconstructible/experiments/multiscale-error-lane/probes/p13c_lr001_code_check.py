"""Engineering probe P13c (python probes/p13c_lr001_code_check.py CPUS): LR001's own panel C simulator (lr001.sim,
before the freeze) on P13's engineering blocks 900868-900871 (32 cases) under LR001's tag and wound placements, for
the families with region-minority cells (BL, IS). ENGINEERING_PROBE_NOT_EVIDENCE.

Why: on LR001's debug blocks (900856-900857) the plain code kept 1.000 of an 8 x 8 flipped wound on IS, minority cells
included, where P13 v2 had 0.953 (minority cells 0.86) under P13's placements. This sizes the plain code's harm to
region-minority cells under LR001's placements before the thresholds are fixed.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from lr001 import design as D  # noqa: E402
from lr001 import sim  # noqa: E402

BLOCKS = tuple(range(900868, 900872))
OUT = LANE / "probes" / "results" / "p13c_lr001_code_check.json"


def one(args):
    family, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    cases, V, ema, R0, th, T = sim.prepare(family, block, "engineering")
    masks = {s: sim.patch(cases, s) for s in (0, *D.C_SIZES)}
    out, _ = sim.simulate_C(cases, R0, T, masks)
    return family, block, {k: out[k][-1] for k in ("kept", "kept_min", "kept_maj")}   # t = 4000: (branches, cases)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    jobs = [(f, b) for f in ("BL", "IS") for b in BLOCKS]
    with ProcessPoolExecutor(len(cpus)) as ex:
        res = list(ex.map(one, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    rows = {}
    br = D.branches("C")
    for family in ("BL", "IS"):
        per = [r for f, b, r in res if f == family]
        for ep in ("kept", "kept_min", "kept_maj"):
            x = np.concatenate([p[ep] for p in per], axis=1)                     # (branches, 32 cases)
            for i, b in enumerate(br):
                v = x[i]
                rows.setdefault(family, {}).setdefault(b, {})[ep] = (
                    [round(float(np.nanmean(v)), 4), int(np.isfinite(v).sum())] if np.isfinite(v).any() else [None, 0])
    out = {"probe": "P13c", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.TAG, "blocks": list(BLOCKS),
           "endpoint": "t = 4000, [mean over cases with the sites, number of such cases]", "rows": rows,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
