"""Engineering probe P4: does provenance-gated arbitration beat fixed routes?

ENGINEERING IDENTITIES ONLY (calibration 900400-900415, test 900300-900315; tag
mse-v1-eng-p4). A feasibility pilot, not ME002: thresholds come from sham calibration
blocks only, the burst constants were fixed before any test outcome, and nothing here is
confirmatory.

Normal mode reads R and holds it (the best fixed route for successors in P1). The arbiter
sees only V-tilde, ema and R. If reference-attributed mismatch appears (site mismatch above
its sham 99.5% level with no body surprise in the last W updates), it stops reading R for
K updates and rewrites R from the body at rate RHO_BURST, inside the body's retention time.
The latch is a declared retained history: one counter per case.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
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
from mse.engine import ROUTES, Route, run  # noqa: E402
from mse.native import NATIVE, half_plane  # noqa: E402
from mse.ops import project  # noqa: E402

TAG = "mse-v1-eng-p4"
CAL, TEST = range(900400, 900416), range(900300, 900316)
K, RHO_BURST, W, REFRACTORY, QUANTILE = 20, 0.1, 300, 200, 0.995
RELEASE = 200
CONDITIONS = [("sham", None, 0.0)] + [(loc, band, amp) for loc in ("body", "reference", "both")
                                      for band in ("fine", "regional", "collective") for amp in (1.0, 2.0)]


def features(Vt, ema, R):
    mismatch = ((R - Vt) ** 2).mean(axis=(-2, -1))
    surprise = (project(Vt - ema, "region") ** 2).mean(axis=(-2, -1))
    return mismatch, surprise


class Arbiter:
    def __init__(self, n, theta_m, theta_s):
        self.theta_m, self.theta_s = theta_m, theta_s
        self.latch = np.zeros(n, int)
        self.burst = np.zeros(n, int)
        self.refractory = np.zeros(n, int)
        self.bursts = np.zeros(n, int)
        self.first = np.full(n, -1)
        self.t = 0

    def __call__(self, Vt, ema, R):
        self.t += 1
        m, s = features(Vt, ema, R)
        self.latch = np.where(s > self.theta_s, W, np.maximum(self.latch - 1, 0))
        start = (m > self.theta_m) & (self.latch == 0) & (self.burst == 0) & (self.refractory == 0)
        self.burst = np.where(start, K, self.burst)
        self.bursts += start
        self.first = np.where(start & (self.first < 0), self.t, self.first)
        on = self.burst > 0
        gain = np.where(on, 0.0, NATIVE.gain)[:, None, None]
        rate = np.where(on, RHO_BURST, 0.0)[:, None, None]
        ending = on & (self.burst == 1)
        self.burst = np.maximum(self.burst - 1, 0)
        self.refractory = np.where(ending, REFRACTORY, np.maximum(self.refractory - 1, 0))
        return gain, rate


class Oracle:
    """Privileged ceiling: told whether only the reference was damaged."""
    def __init__(self, n, ref_only):
        self.ref_only, self.t = np.broadcast_to(ref_only, (n,)), 0

    def __call__(self, Vt, ema, R):
        self.t += 1
        on = self.ref_only & (self.t <= K)
        return (np.where(on, 0.0, NATIVE.gain)[:, None, None],
                np.where(on, RHO_BURST, 0.0)[:, None, None])


def prepared(blocks):
    cases = enrol(blocks)
    s, th = acquire(TAG, cases)
    s = run(s, th, Noise(TAG, cases, "release"), ROUTES["body"], RELEASE)
    s.Q[:] = 0.0
    return cases, s, th


def calibrate():
    cases, s, th = prepared(CAL)
    z = Noise(TAG, cases, "future")
    ms, ss = [], []

    def probe(Vt, ema, R):
        m, sp = features(Vt, ema, R)
        ms.append(m), ss.append(sp)
        return NATIVE.gain, 0.0
    run(s, th, z, Route(), 1000, policy=probe)
    return float(np.quantile(np.concatenate(ms), QUANTILE)), float(np.quantile(np.concatenate(ss), QUANTILE))


def evaluate(args):
    (loc, band, amp), theta_m, theta_s = args
    cases, base, th = prepared(TEST)
    T = templates(cases)
    zs = Noise(TAG, cases, "future")
    zs = np.stack([zs(t) for t in range(1, 1001)])
    body = ref = None
    if loc in ("body", "both"):
        body = band_damage(TAG, cases, "body", band, amp)
    if loc in ("reference", "both"):
        ref = band_damage(TAG, cases, "reference", band, amp)
    start = injure(base, body=body, reference=ref)
    n = len(cases)
    policies = {"hold": (ROUTES["body"], None), "reciprocal": (ROUTES["reciprocal"], None),
                "arbiter": (Route(), Arbiter(n, theta_m, theta_s)),
                "oracle": (Route(), Oracle(n, loc == "reference"))}
    out = {"location": loc, "band": band, "rms": amp, "policies": {}}
    templ = np.stack([half_plane(k) for k in range(4)])
    own = np.array([c.message for c in cases])[:, None].repeat(4, 1)
    for name, (route, pol) in policies.items():
        end = run(start.copy(), th, lambda t: zs[t - 1], route, 1000, policy=pol)
        fresh = read(TAG, cases, end.Q, th)
        res = {"V_sign": float(score.sign_agreement(end.V, T).mean()),
               "V_qualified": float(score.qualified(end.V, T).mean()),
               "R_sign": float(score.sign_agreement(end.R, T).mean()),
               "Q_sign": float(score.sign_agreement(end.Q, T).mean()),
               "fresh_qualified": float(score.qualified(fresh, T[:, None]).mean()),
               "fresh_recognition": float(score.recognition(fresh, templ, own).mean())}
        per_block = score.qualified(fresh, T[:, None]).mean(1).reshape(len(TEST), -1).mean(1)
        res["fresh_qualified_blocks"] = per_block.tolist()
        if isinstance(pol, Arbiter):
            res["cases_bursting"] = float((pol.bursts > 0).mean())
            res["mean_bursts"] = float(pol.bursts.mean())
            res["median_first_burst"] = float(np.median(pol.first[pol.first > 0])) if (pol.first > 0).any() else None
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
    a.out.write_text(json.dumps({"probe": "P4 provenance-gated arbitration pilot",
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "constants": {"K": K, "rho_burst": RHO_BURST, "W": W, "refractory": REFRACTORY,
                                               "quantile": QUANTILE, "release": RELEASE},
                                 "thresholds_from_sham_calibration": {"site_mismatch": theta_m,
                                                                      "region_surprise": theta_s},
                                 "wall_s": round(time.time() - t0, 1), "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
