"""Panel E's store unit, calibrated on engineering sham trajectories before any development outcome.

python -m en001.calibrate --cpus LIST   (writes en001/frozen/calibration.json)

For every panel E regime, the multi and relcode records run the starvation window at the full budget with no event
on the calibration blocks. The unit `work` is the mean paid work per cell per update, every drift paid: the
double well, coupling and theta plus the correction (|dt m drift| + |dt c m (r - V-tilde)|) plus the record's
self-correction and code. The store then holds STORE_CAP units and is supplied at STORE_HEADROOM units per update at
the full budget (phi x that under starvation).
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from en001 import design as D  # noqa: E402
from en001 import sim  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")][:1])
    t0 = time.time()
    blocks = list(range(*D.IDENTITIES["calibration"]))
    out = {}
    for name in D.PANELS["E"]["regimes"]:
        cases, s0, th, p, conserved, T = sim.prepare(name, blocks, "engineering")
        k = len(cases)
        Z = sim.draws(cases, "future", updates=D.WINDOW)
        XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
        works = []
        for arm in D.PANELS["E"]["arms"]:
            o = sim.simulate(D.ARMS[arm], (D.BASE,), (D.CONDS[0],), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T,
                             [None], [None], [None])
            works.append((o["w_drift"] + o["w_corr"] + o["w_rec"]) / (D.STARVE * 256))
        w = np.concatenate(works)
        out[name] = {"work": float(w.mean()), "work_sd_across_cases": float(w.std()), "cases": int(w.size)}
        print(name, out[name], flush=True)
    path = Path(__file__).resolve().parent / "frozen" / "calibration.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                                "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "wall_s": round(time.time() - t0, 1), "blocks": [blocks[0], blocks[-1] + 1],
                                "regimes": out}, indent=1) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
