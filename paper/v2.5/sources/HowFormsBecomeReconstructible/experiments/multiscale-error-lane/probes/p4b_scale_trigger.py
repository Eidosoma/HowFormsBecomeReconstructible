"""Engineering probe P4b: does a pooled (coarse-scale) trigger fix P4's failures?

ENGINEERING IDENTITIES ONLY (calibration 900600-900615, test 900500-900515, both unused
before; tag mse-v1-eng-p4b). Changes from P4, fixed before any P4b outcome and derived
from P4's failure analysis plus P3's sensor characterisation:
  1. the rewrite trigger is mismatch pooled at the region or sheet scale, which P3 found
     blind to fine reference corruption, the corruption the body already filters (P1);
  2. its threshold is the 99.5% quantile of each sham calibration trajectory's maximum,
     so it controls false alarms per trajectory rather than per update;
  3. body surprise latches attribution for the whole window (W = 1000).
Burst constants are unchanged (K = 20, rate 0.1).
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

import numpy as np  # noqa: E402

from mse import score  # noqa: E402
from mse.assay import Noise, band_damage, injure, read, templates  # noqa: E402
from mse.engine import ROUTES, Route, run  # noqa: E402
from mse.native import NATIVE, half_plane  # noqa: E402
from mse.ops import project  # noqa: E402

base.TAG = "mse-v1-eng-p4b"
CAL, TEST = range(900600, 900616), range(900500, 900516)
W = 1000
TRIGGERS = ("region", "sheet")


def pooled(level):
    def features(Vt, ema, R):
        mismatch = (project(R - Vt, level) ** 2).mean(axis=(-2, -1))
        surprise = (project(Vt - ema, "region") ** 2).mean(axis=(-2, -1))
        return mismatch, surprise
    return features


class ScaleArbiter(base.Arbiter):
    def __init__(self, n, theta_m, theta_s, level):
        super().__init__(n, theta_m, theta_s)
        self.features = pooled(level)

    def __call__(self, Vt, ema, R):
        self.t += 1
        m, s = self.features(Vt, ema, R)
        self.latch = np.where(s > self.theta_s, W, np.maximum(self.latch - 1, 0))
        start = (m > self.theta_m) & (self.latch == 0) & (self.burst == 0) & (self.refractory == 0)
        self.burst = np.where(start, base.K, self.burst)
        self.bursts += start
        self.first = np.where(start & (self.first < 0), self.t, self.first)
        on = self.burst > 0
        gain = np.where(on, 0.0, NATIVE.gain)[:, None, None]
        rate = np.where(on, base.RHO_BURST, 0.0)[:, None, None]
        ending = on & (self.burst == 1)
        self.burst = np.maximum(self.burst - 1, 0)
        self.refractory = np.where(ending, base.REFRACTORY, np.maximum(self.refractory - 1, 0))
        return gain, rate


def calibrate():
    cases, s, th = base.prepared(CAL)
    z = Noise(base.TAG, cases, "future")
    maxima = {lvl: np.zeros(len(cases)) for lvl in TRIGGERS}
    surprises = []

    def probe(Vt, ema, R):
        for lvl in TRIGGERS:
            m, sp = pooled(lvl)(Vt, ema, R)
            maxima[lvl] = np.maximum(maxima[lvl], m)
        surprises.append(sp)
        return NATIVE.gain, 0.0
    run(s, th, z, Route(), 1000, policy=probe)
    return ({lvl: float(np.quantile(maxima[lvl], base.QUANTILE)) for lvl in TRIGGERS},
            float(np.quantile(np.concatenate(surprises), base.QUANTILE)))


def evaluate(args):
    (loc, band, amp), theta_m, theta_s = args
    cases, start0, th = base.prepared(TEST)
    T = templates(cases)
    zs = Noise(base.TAG, cases, "future")
    zs = np.stack([zs(t) for t in range(1, 1001)])
    body = band_damage(base.TAG, cases, "body", band, amp) if loc in ("body", "both") else None
    ref = band_damage(base.TAG, cases, "reference", band, amp) if loc in ("reference", "both") else None
    start = injure(start0, body=body, reference=ref)
    n = len(cases)
    policies = {"hold": (ROUTES["body"], None),
                "oracle": (Route(), base.Oracle(n, loc == "reference"))}
    for lvl in TRIGGERS:
        policies[f"arbiter_{lvl}"] = (Route(), ScaleArbiter(n, theta_m[lvl], theta_s, lvl))
    templ = np.stack([half_plane(k) for k in range(4)])
    own = np.array([c.message for c in cases])[:, None].repeat(4, 1)
    out = {"location": loc, "band": band, "rms": amp, "policies": {}}
    for name, (route, pol) in policies.items():
        end = run(start.copy(), th, lambda t: zs[t - 1], route, 1000, policy=pol)
        fresh = read(base.TAG, cases, end.Q, th)
        q = score.qualified(fresh, T[:, None])
        res = {"V_sign": float(score.sign_agreement(end.V, T).mean()),
               "R_sign": float(score.sign_agreement(end.R, T).mean()),
               "fresh_qualified": float(q.mean()),
               "fresh_recognition": float(score.recognition(fresh, templ, own).mean()),
               "fresh_qualified_blocks": q.mean(1).reshape(len(TEST), -1).mean(1).tolist()}
        if isinstance(pol, base.Arbiter):
            res["cases_bursting"] = float((pol.bursts > 0).mean())
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
        results = list(pool.map(evaluate, [(c, theta_m, theta_s) for c in base.CONDITIONS]))
    a.out.write_text(json.dumps({"probe": "P4b scale-matched trigger",
                                 "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                                 "changes_from_p4": ["pooled trigger", "per-trajectory threshold", "W=1000"],
                                 "thresholds": {"mismatch_per_trajectory_max": theta_m, "region_surprise": theta_s},
                                 "wall_s": round(time.time() - t0, 1), "results": results}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
