"""Engineering probe P3: can a two-timescale signal say WHICH source was damaged?

ENGINEERING IDENTITIES ONLY (blocks 900200-900215, tag mse-v1-eng-p3). Not evidence.
PROTOCOL section 6: a static snapshot with V = Y, R = X cannot tell body damage from
reference damage. A trajectory can: body damage moves V away from its own recent moving
average (surprise |V - ema|) as well as from R; reference damage moves only R - V. Both
features are local, native and target-free. After a 200-update release, apply body,
reference or sham damage in one band, run the reciprocal route, and score how well
pooled mismatch and pooled surprise separate the three conditions (AUC over cases).
"""
from __future__ import annotations

import argparse
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

from mse.assay import Noise, acquire, band_damage, enrol, injure  # noqa: E402
from mse.engine import ROUTES, run  # noqa: E402
from mse.ops import project  # noqa: E402

TAG = "mse-v1-eng-p3"
BLOCKS = range(900200, 900216)
LEVELS = ("site", "region", "sheet")
WINDOW = 10


def auc(pos, neg):
    """Probability a positive case scores above a negative one, ties counted half."""
    pos, neg = np.asarray(pos)[:, None], np.asarray(neg)[None, :]
    return float((pos > neg).mean() + 0.5 * (pos == neg).mean())


def features(s, prev_ema):
    out = {}
    for lvl in LEVELS:
        out[f"mismatch_{lvl}"] = (project(s.R - s.V, lvl) ** 2).mean(axis=(-2, -1))
        out[f"surprise_{lvl}"] = (project(s.V - prev_ema, lvl) ** 2).mean(axis=(-2, -1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", type=str, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    t0 = time.time()
    cases = enrol(BLOCKS, parents=(0, 1))
    acquired, th = acquire(TAG, cases)
    release = Noise(TAG, cases, "release")
    base = run(acquired, th, release, ROUTES["reciprocal"], 200)
    z = Noise(TAG, cases, "future")
    zs = np.stack([z(t) for t in range(1, WINDOW + 1)])
    results = {}
    for band in ("fine", "regional", "collective"):
        for amp in (0.5, 1.0, 2.0):
            f = band_damage(TAG, cases, "both", band, amp)
            conditions = {"sham": injure(base), "body": injure(base, body=f), "reference": injure(base, reference=f)}
            feats = {}
            for name, start in conditions.items():
                acc = []

                def record(t, s, acc=acc):
                    if t >= 1:
                        acc.append(features(s, s.ema))
                run(start.copy(), th, lambda t: zs[t - 1], ROUTES["reciprocal"], WINDOW, every=1, record=record)
                feats[name] = {k: np.mean([x[k] for x in acc[:3]], axis=0) for k in acc[0]}
            key = f"{band}_{amp}"
            results[key] = {}
            for k in feats["sham"]:
                results[key][k] = {
                    "auc_body_vs_reference": auc(feats["body"][k], feats["reference"][k]),
                    "auc_body_vs_sham": auc(feats["body"][k], feats["sham"][k]),
                    "auc_reference_vs_sham": auc(feats["reference"][k], feats["sham"][k]),
                    "means": {c: float(np.mean(feats[c][k])) for c in feats}}
    a.out.write_text(json.dumps({"probe": "P3 provenance from two timescales",
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "identities": "engineering 900200-900215, four messages, two parents",
                                 "window": "mean of features over updates 1-3 after damage",
                                 "wall_s": round(time.time() - t0, 1), "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
