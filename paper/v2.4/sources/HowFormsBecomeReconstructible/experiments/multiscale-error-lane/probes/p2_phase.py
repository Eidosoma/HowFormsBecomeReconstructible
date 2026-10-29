"""Engineering probe P2: when does a body need a setpoint, and at what spatial scale?

ENGINEERING IDENTITIES ONLY (blocks 900100-900115, tag mse-v1-eng-p2). Not evidence.
(a) Native memory: from an imposed taught pattern, how long does the body keep it with
    comparison off, across noise sigma and coupling g?
(b) Resolution versus robustness at each coupling: with a correct held reference, which
    stripe widths can the body hold; and how much fine-scale reference corruption does it
    reject (body sign agreement above the corrupted reference's own)?
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
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
from mse.assay import Noise, band_damage, enrol, theta  # noqa: E402
from mse.engine import ROUTES, State, run  # noqa: E402
from mse.native import NATIVE, half_plane  # noqa: E402

TAG = "mse-v1-eng-p2"
BLOCKS = range(900100, 900116)
SIGMAS = (0.05, 0.1, 0.15, 0.2, 0.25, 0.3)
COUPLINGS = (0.25, 0.5, 1.0, 2.0, 4.0)
WIDTHS = (1, 2, 4, 8)
TIMES = (10, 30, 100, 300, 1000)


def stripes(width, amplitude=1.2):
    field = np.where((np.arange(16) // width) % 2 == 0, 1.0, -1.0)
    return amplitude * np.broadcast_to(field, (16, 16)).copy()


def job(spec):
    sigma, g = spec
    p = replace(NATIVE, sigma=sigma, coupling=g)
    cases = enrol(BLOCKS, parents=(0,))
    th = theta(TAG, cases, p)
    T = np.stack([half_plane(c.message) for c in cases])
    z = Noise(TAG, cases, "future")
    zs = np.stack([z(t) for t in range(1, 1001)])
    out = {"sigma": sigma, "coupling": g}
    # (a) native memory, comparison off, from the imposed pattern; reference correct but unread
    trace = {}
    run(State(T.copy(), T.copy(), 0.9 * T, np.zeros_like(T)), th, lambda t: zs[t - 1],
        ROUTES["inactive"], 1000, p, every=1,
        record=lambda t, s: trace.__setitem__(t, float(score.sign_agreement(s.V, T).mean())) if t in TIMES else None)
    out["native_memory_sign"] = trace
    held = {}
    run(State(T.copy(), T.copy(), 0.9 * T, np.zeros_like(T)), th, lambda t: zs[t - 1],
        ROUTES["body"], 1000, p, every=1,
        record=lambda t, s: held.__setitem__(t, float(score.sign_agreement(s.V, T).mean())) if t in TIMES else None)
    out["held_reference_sign"] = held
    # (b1) resolution: stripes of each width, correct reference held, mean sign over the last 200 updates
    res = {}
    for w in WIDTHS:
        S = np.broadcast_to(stripes(w), T.shape).copy()
        acc = []
        run(State(S.copy(), S.copy(), 0.9 * S, np.zeros_like(S)), th, lambda t: zs[t - 1],
            ROUTES["body"], 1000, p, every=1,
            record=lambda t, s: acc.append(score.sign_agreement(s.V, S).mean()) if t > 800 else None)
        res[w] = float(np.mean(acc))
    out["stripe_sign_with_true_reference"] = res
    # (b2) robustness: fine-band reference corruption, held; body sign minus corrupted-R sign
    rob = {}
    for amp in (1.0, 2.0):
        Rd = np.clip(0.9 * T + band_damage(TAG, cases, "reference", "fine", amp), -2, 2)
        acc = []
        run(State(T.copy(), T.copy(), Rd, np.zeros_like(T)), th, lambda t: zs[t - 1],
            ROUTES["body"], 1000, p, every=1,
            record=lambda t, s: acc.append(score.sign_agreement(s.V, T).mean()) if t > 800 else None)
        rob[amp] = {"body_sign": float(np.mean(acc)), "reference_sign": float(score.sign_agreement(Rd, T).mean())}
    out["fine_reference_rejection"] = rob
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cpus", type=str, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as pool:
        results = list(pool.map(job, itertools.product(SIGMAS, COUPLINGS)))
    a.out.write_text(json.dumps({"probe": "P2 setpoint necessity and resolution-robustness",
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "identities": "engineering 900100-900115, four messages, one parent",
                                 "wall_s": round(time.time() - t0, 1), "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
