"""Engineering probe P4c: does P4b survive targets that are off the pooling grid?

ENGINEERING IDENTITIES ONLY (calibration 900800-900815, test 900700-900715, unused
before; tag mse-v1-eng-p4c). The four half-plane messages are rolled by (2, 2), so every
boundary falls inside a 4 x 4 block and no message is a quadrant pattern. Policies,
constants and calibration rules are P4b's, unchanged; thresholds are recalibrated on
shifted-message shams because the trigger statistics belong to the target family.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p4_arbiter as base  # noqa: E402
import p4b_scale_trigger as scaled  # noqa: E402

import numpy as np  # noqa: E402

from mse import score  # noqa: E402
from mse.assay import Noise, acquire, band_damage, enrol, injure, read, templates  # noqa: E402
from mse.engine import ROUTES, Route, run  # noqa: E402
from mse.native import NATIVE, half_plane  # noqa: E402

TAG = "mse-v1-eng-p4c"
CAL, TEST = range(900800, 900816), range(900700, 900716)
SHIFT = (2, 2)
CONDITIONS = [("sham", None, 0.0)] + [(loc, band, amp) for loc in ("body", "reference", "both")
                                      for band in ("fine", "regional", "collective") for amp in (1.0, 2.0)]


def prepared(blocks):
    cases = enrol(blocks)
    s, th = acquire(TAG, cases, shift=SHIFT)
    s = run(s, th, Noise(TAG, cases, "release"), ROUTES["body"], base.RELEASE)
    s.Q[:] = 0.0
    return cases, s, th


def calibrate():
    cases, s, th = prepared(CAL)
    maxima = {lvl: np.zeros(len(cases)) for lvl in scaled.TRIGGERS}
    surprises = []

    def probe(Vt, ema, R):
        for lvl in scaled.TRIGGERS:
            m, sp = scaled.pooled(lvl)(Vt, ema, R)
            maxima[lvl] = np.maximum(maxima[lvl], m)
        surprises.append(sp)
        return NATIVE.gain, 0.0
    run(s, th, Noise(TAG, cases, "future"), Route(), 1000, policy=probe)
    return ({lvl: float(np.quantile(maxima[lvl], base.QUANTILE)) for lvl in scaled.TRIGGERS},
            float(np.quantile(np.concatenate(surprises), base.QUANTILE)))


def evaluate(args):
    (loc, band, amp), theta_m, theta_s = args
    cases, start0, th = prepared(TEST)
    T = templates(cases, shift=SHIFT)
    zs = Noise(TAG, cases, "future")
    zs = np.stack([zs(t) for t in range(1, 1001)])
    body = band_damage(TAG, cases, "body", band, amp) if loc in ("body", "both") else None
    ref = band_damage(TAG, cases, "reference", band, amp) if loc in ("reference", "both") else None
    start = injure(start0, body=body, reference=ref)
    n = len(cases)
    policies = {"hold": (ROUTES["body"], None), "oracle": (Route(), base.Oracle(n, loc == "reference"))}
    for lvl in scaled.TRIGGERS:
        policies[f"arbiter_{lvl}"] = (Route(), scaled.ScaleArbiter(n, theta_m[lvl], theta_s, lvl))
    templ = np.stack([np.roll(half_plane(k), SHIFT, axis=(0, 1)) for k in range(4)])
    own = np.array([c.message for c in cases])[:, None].repeat(4, 1)
    out = {"location": loc, "band": band, "rms": amp, "policies": {}}
    for name, (route, pol) in policies.items():
        end = run(start.copy(), th, lambda t: zs[t - 1], route, 1000, policy=pol)
        fresh = read(TAG, cases, end.Q, th)
        q = score.qualified(fresh, T[:, None])
        res = {"V_sign": float(score.sign_agreement(end.V, T).mean()),
               "R_sign": float(score.sign_agreement(end.R, T).mean()),
               "fresh_qualified": float(q.mean()),
               "fresh_recognition": float(score.recognition(fresh, templ, own).mean()),
               "fresh_qualified_blocks": q.mean(1).reshape(len(TEST), -1).mean(1).tolist()}
        if isinstance(pol, base.Arbiter):
            res["cases_bursting"] = float((pol.bursts > 0).mean())
        out["policies"][name] = res
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cpus", type=str, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    t0 = time.time()
    theta_m, theta_s = calibrate()
    with ProcessPoolExecutor(a.workers) as pool:
        results = list(pool.map(evaluate, [(c, theta_m, theta_s) for c in CONDITIONS]))
    a.out.write_text(json.dumps({"probe": "P4c P4b on off-grid targets", "shift": SHIFT,
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "thresholds": {"mismatch_per_trajectory_max": theta_m, "region_surprise": theta_s},
                                 "wall_s": round(time.time() - t0, 1), "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
