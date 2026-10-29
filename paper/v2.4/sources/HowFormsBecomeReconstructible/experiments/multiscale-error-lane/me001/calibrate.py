"""Arbiter thresholds per regime from sham trajectories of the reserved calibration blocks.

python -m me001.calibrate --cpus LIST   (writes me001/frozen/thresholds.json)

Engineering identities only (design.IDENTITIES["calibration"]). As in P4b: the 99.5%
quantile of each sham trajectory's maximum region-pooled mismatch (per-trajectory false-
alarm control) and of region-pooled surprise over all sham updates, under the hold route.
Only sensor statistics are read; no evaluator score, target or label is used.
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

from me001 import design as D  # noqa: E402
from me001.policies import pooled_features  # noqa: E402
from me001.worker import prepare  # noqa: E402
from mse.assay import Noise  # noqa: E402
from mse.engine import Route, run  # noqa: E402


def calibrate(name):
    lo, hi = D.IDENTITIES["calibration"]
    cases, s0, th, p, _, _ = prepare(name, list(range(lo, hi)), "engineering")
    maxima, surprises = np.zeros(len(cases)), []

    def probe(Vt, ema, R):
        nonlocal maxima
        m, s = pooled_features(Vt, ema, R)
        maxima = np.maximum(maxima, m)
        surprises.append(s)
        return p.gain, 0.0
    run(s0, th, Noise(D.TAG, cases, "future"), Route(), D.WINDOW, p, policy=probe)
    return name, {"mismatch": float(np.quantile(maxima, D.QUANTILE)),
                  "surprise": float(np.quantile(np.concatenate(surprises), D.QUANTILE)),
                  "trajectories": len(cases), "updates": D.WINDOW}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "frozen" / "thresholds.json")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    t0 = time.time()
    with ProcessPoolExecutor(min(len(cpus), len(D.REGIMES))) as pool:
        regimes = dict(pool.map(calibrate, D.REGIMES))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "status": "ENGINEERING_CALIBRATION_SENSOR_STATISTICS_ONLY", "design_digest": D.digest(),
        "blocks": list(D.IDENTITIES["calibration"]), "rule": "P4b: per-trajectory max mismatch and all-update "
        "surprise, region pooled, hold route, 99.5% quantiles", "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wall_s": round(time.time() - t0, 1), "regimes": regimes}, indent=1) + "\n")
    print(json.dumps(regimes, indent=1))


if __name__ == "__main__":
    main()
