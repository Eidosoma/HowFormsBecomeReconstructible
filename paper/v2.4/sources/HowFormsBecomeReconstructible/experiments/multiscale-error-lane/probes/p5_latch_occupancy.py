"""Engineering probe P5 (python probes/p5_latch_occupancy.py) (design input for ME002; ENGINEERING_PROBE_NOT_EVIDENCE).
How often is ME001's arbiter latch closed in sham, and what do per-trajectory maxima of
region-pooled surprise look like? Engineering blocks 900960-900967, tag mse-me002-p5."""
import os, sys, json
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[k] = "1"
from pathlib import Path
LANE = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, LANE)
import numpy as np
from dataclasses import replace
from mse.assay import Noise, acquire, enrol
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE
from mse.ops import project

TAG = "mse-me002-p5"
th_ME001 = {"F0_s0.3": (0.3086, 0.02193), "F0_s0.1": (0.0713, 0.00177)}
out = {}
for name, sigma in (("F0_s0.3", 0.3), ("F0_s0.1", 0.1)):
    p = replace(NATIVE, sigma=sigma)
    cases = enrol(list(range(900960, 900968)))
    s, th = acquire(TAG, cases, 120, 1000, 1.2, p, (0, 0), per_tissue=True)
    s = run(s, th, Noise(TAG, cases, "release"), ROUTES["body"], 200, p)
    s = State(s.V, s.ema, s.R, np.zeros_like(s.V))
    L = 1800
    surp, mism = [], []
    def tap(Vt, ema, R):
        surp.append((project(Vt - ema, "region") ** 2).mean(axis=(-2, -1)))
        mism.append((project(R - Vt, "region") ** 2).mean(axis=(-2, -1)))
        return p.gain, 0.0
    run(s, th, Noise(TAG, cases, "future"), Route(), L, p, policy=tap)
    S, M = np.array(surp), np.array(mism)          # (L, n)
    tm, ts = th_ME001[name]
    exceed = S > ts
    # latch occupancy under ME001's rule (W=1000)
    latch = np.zeros(S.shape[1], int); occ = []
    for t in range(L):
        latch = np.where(exceed[t], 1000, np.maximum(latch - 1, 0)); occ.append(latch > 0)
    occ = np.array(occ)
    out[name] = {"cases": int(S.shape[1]), "exceed_frac_per_update": float(exceed.mean()),
                 "latch_closed_frac_t100_500": float(occ[100:500].mean()),
                 "latch_closed_frac_t500_1800": float(occ[500:].mean()),
                 "cases_ever_exceeding_by_t500": float(exceed[:500].any(0).mean()),
                 "surprise_traj_max_q995_L1800": float(np.quantile(S.max(0), 0.995)),
                 "surprise_traj_max_median": float(np.median(S.max(0))),
                 "surprise_update_q995": float(np.quantile(S, 0.995)),
                 "mismatch_traj_max_q995_L1800": float(np.quantile(M.max(0), 0.995)),
                 "mismatch_traj_max_q995_L1000": float(np.quantile(M[:1000].max(0), 0.995)),
                 "ME001_thresholds": [tm, ts]}
text = json.dumps(out, indent=1)
print(text)
(Path(LANE) / "probes" / "results" / "p5_latch_v1.json").write_text(text + "\n")
