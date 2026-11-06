"""Panel P write thresholds, calibrated on engineering sham trajectories before any development outcome.

python -m br001.calibrate --cpus LIST   (writes br001/frozen/calibration.json)

For every panel P regime, the self-correcting record (write_none) runs WINDOW updates with no event on
the calibration blocks; per update the largest region-pooled mismatch (P4(r - V-tilde))^2 and the largest
region-pooled surprise (P4(V-tilde - ema))^2 over the sheet are logged. Thresholds are the 99.5% quantiles
of their per-trajectory maxima (ME002's v2 rule), so a sham trajectory crosses either at most 0.5% of the time.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from br001 import design as D  # noqa: E402
from br001 import sim  # noqa: E402
from mse.native import NATIVE, neighbours  # noqa: E402


def calibrate(name):
    cases, s0, th, p, conserved, T, Tf = sim.prepare(name, list(range(*D.IDENTITIES["calibration"])), "engineering")
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    v, e, r = s0.V.copy(), s0.ema.copy(), s0.R.copy()
    mis, sur = [], []
    for t in range(D.WINDOW):
        v, e, vt = sim.body_step(v, e, r, th, Z[t], p, conserved, NATIVE.gain)
        mis.append(sim.region(r - vt).max((-2, -1)))
        sur.append(sim.region(vt - e).max((-2, -1)))
        r = np.clip(r + D.EPS * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (neighbours(r) - r)) + D.SIGMA_R * XI[t], -2.0, 2.0)
    q = lambda x: float(np.quantile(np.array(x).max(0), D.QUANTILE))
    return name, {"mismatch": q(mis), "surprise": q(sur), "cases": len(cases)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "frozen" / "calibration.json")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    t0 = time.time()
    with ProcessPoolExecutor(min(len(cpus), len(D.PANELS["P"]["regimes"]))) as pool:
        regimes = dict(pool.map(calibrate, D.PANELS["P"]["regimes"]))
    out = {"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
           "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
           "blocks": list(D.IDENTITIES["calibration"]), "regimes": regimes}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(regimes, indent=1))


if __name__ == "__main__":
    main()
