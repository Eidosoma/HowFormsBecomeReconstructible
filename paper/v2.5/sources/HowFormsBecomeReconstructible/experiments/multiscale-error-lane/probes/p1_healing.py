"""Engineering probe P1: what does the native sheet correct by itself, at which scale?

ENGINEERING IDENTITIES ONLY (blocks 900000-900015, tag mse-v1-eng). Not ME001 evidence;
its outcomes may inform damage calibration and qualification design, which is what the
engineering range is for. Body or reference damage in one band at one pre-clipping RMS,
then 1000 updates under each fixed route with common draws, then four fresh recipients
read each outgoing Q. Writes a compact JSON summary; no raw arrays are kept.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import os
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[k] = "1"

import numpy as np  # noqa: E402

from mse import score  # noqa: E402
from mse.assay import Noise, acquire, band_damage, enrol, injure, read, templates  # noqa: E402
from mse.engine import ROUTES, run  # noqa: E402
from mse.native import half_plane  # noqa: E402

TAG = "mse-v1-eng"
BLOCKS = range(900000, 900016)
TIMES = (0, 1, 5, 20, 100, 300, 1000)
BANDS = ("fine", "regional", "collective")
AMPS = (0.5, 1.0, 1.5, 2.0, 3.0)
ROUTE_NAMES = ("inactive", "body", "reference", "reciprocal")


def block_mean(x, cases):
    blocks = np.array([c.block for c in cases])
    return np.array([x[blocks == b].mean() for b in sorted(set(blocks))])


def stats(x, cases):
    per_block = block_mean(np.asarray(x, dtype=float), cases)
    return {"mean": float(per_block.mean()), "block_sd": float(per_block.std(ddof=1)),
            "min_block": float(per_block.min()), "max_block": float(per_block.max())}


def job(spec):
    location, band, amp = spec
    cases = enrol(BLOCKS, parents=(0,))
    acquired, th = acquire(TAG, cases)
    T = templates(cases)
    future = Noise(TAG, cases, "future")
    z = np.stack([future(t) for t in range(1, 1001)])
    injury = None
    if location != "sham":
        f = band_damage(TAG, cases, location, band, amp)
        injury = injure(acquired, body=f if location == "body" else None,
                        reference=f if location == "reference" else None)
    else:
        injury = injure(acquired)
    out = {"location": location, "band": band, "rms": amp,
           "realised_body_change_rms": float(np.sqrt(((injury.V - acquired.V) ** 2).mean())),
           "realised_ref_change_rms": float(np.sqrt(((injury.R - acquired.R) ** 2).mean())),
           "initial_sign_flips_body": float(((injury.V > 0) != (acquired.V > 0)).mean()),
           "initial_sign_flips_ref": float(((injury.R > 0) != (acquired.R > 0)).mean()),
           "routes": {}}
    for name in ROUTE_NAMES:
        trace = {}

        def record(t, s):
            if t in TIMES:
                trace[t] = {"V_sign": stats(score.sign_agreement(s.V, T), cases),
                            "V_qual": stats(score.qualified(s.V, T), cases),
                            "R_sign": stats(score.sign_agreement(s.R, T), cases),
                            "Q_sign": stats(score.sign_agreement(s.Q, T), cases)}
        end = run(injury.copy(), th, lambda t: z[t - 1], ROUTES[name], 1000, every=1, record=record)
        fresh = read(TAG, cases, end.Q, th)
        rec = score.recognition(fresh, np.stack([half_plane(k) for k in range(4)]),
                                np.array([c.message for c in cases])[:, None].repeat(4, 1))
        out["routes"][name] = {
            "trace": {str(t): v for t, v in trace.items()},
            "fresh_qualified": stats(score.qualified(fresh, T[:, None]).mean(1), cases),
            "fresh_sign": stats(score.sign_agreement(fresh, T[:, None]).mean(1), cases),
            "fresh_recognition": stats(rec.mean(1), cases),
            "end_err": {k: float(v.mean()) for k, v in score.band_errors(end.V, T).items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cpus", type=str, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    specs = [("sham", "none", 0.0)] + list(itertools.product(("body", "reference"), BANDS, AMPS))
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool:
        results = list(pool.map(job, specs))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"probe": "P1 self-healing and damage calibration",
                                 "identities": "engineering 900000-900015, one parent, four messages",
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "wall_s": round(time.time() - t0, 1), "cpus": cpus,
                                 "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
