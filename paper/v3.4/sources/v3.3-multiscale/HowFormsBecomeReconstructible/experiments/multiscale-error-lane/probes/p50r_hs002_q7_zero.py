"""P50r (python probes/p50r_hs002_q7_zero.py): the lead's check of HS002's amended Q7 failure, before the freeze, on
synthetic cohorts only (no tissue, no lineage, no value of any run). LEAD_CHECK_NOT_REGISTERED; 1 November 2026.

The amended Q7 (the lead's, after P50q) required that no zero-asymptote cohort (c 0, a 2, h 5) of 10 read as a plateau,
under the noise calibrated to HS001's development (a block level plus an independent residual, SD 1.9, rho 0.943).
One of 10 did (fork H1's cohort 4: its cohort-wide level over rewrites 128-1,024 +0.412, M1's c [+0.095, +0.715]).
This checks whether that is the rule's nominal error or a fault:
1. the spread of the cohort level under the model, over 4,000 cohorts (no fits), against 1.9 sqrt(0.943) / sqrt(128),
   and the one-sided rate of a level beyond 1.96 of its SE (a plateau-type error for a zero truth);
2. Q7's own ten zero cohorts (rng 20261101, Q7's order: the plateau truth's ten first), their levels and spread;
3. M1's c interval (hs002.fit.fit1 on the point curve and 1,000 whole-block resamples, percentiles) over 40 cohorts of
   the plateau truth (c 1, a 1, h 5) and of the zero truth: its coverage, and how often its lower bound is above zero.
"""
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from hs002 import design as D, fit as F                          # noqa: E402  (HS002's fit, read only)

n = np.asarray(D.CHECKPOINTS, float)
K = n.size
Lc = np.linalg.cholesky(1.9 ** 2 * (0.943 + 0.057 * np.eye(K)))
e = lambda h: np.exp(-np.log(2) * (n - 1) / h)
SE = 1.9 * np.sqrt(0.943) / np.sqrt(128)

rng = np.random.default_rng(5)
lev = np.array([(rng.normal(0, 1, (128, K)) @ Lc.T).mean(0)[n >= 128].mean() for _ in range(4000)])
print(f"1. the cohort level over rewrites 128-1,024 under the model, 4,000 cohorts: SD {lev.std():.4f} (expected "
      f"{SE:.4f}); beyond +1.96 SE {(lev > 1.96 * SE).mean():.4f}, beyond +-1.96 SE {(np.abs(lev) > 1.96 * SE).mean():.4f}")

r2 = np.random.default_rng(20261101)
vals = []
for name in ("plateau", "zero"):
    for i in range(10):
        blocks = (1.0 + e(5.0) if name == "plateau" else 2.0 * e(5.0))[None] + r2.normal(0, 1, (128, K)) @ Lc.T
        r2.integers(0, 128, (1000, 128))
        if name == "zero":
            vals.append(blocks.mean(0)[n >= 128].mean())
vals = np.array(vals)
print(f"2. Q7's ten zero cohorts' levels {np.round(vals, 3).tolist()}: SD {vals.std(ddof=1):.3f} (the model's {SE:.3f}); "
      f"beyond +-1.96 SE: {(np.abs(vals) > 1.96 * SE).sum()} of 10")

rng = np.random.default_rng(11)
for name, y, c0 in (("plateau c 1", 1.0 + 1.0 * e(5.0), 1.0), ("zero", 2.0 * e(5.0), 0.0)):
    cov, above = [], 0
    for _ in range(40):
        blocks = y[None] + rng.normal(0, 1, (128, K)) @ Lc.T
        sets = rng.integers(0, 128, (1000, 128))
        m = F.fit1(np.vstack([blocks.mean(0)[None], blocks[sets].mean(1)]), n)
        lo, hi = np.quantile(m["c"][1:], [0.025, 0.975])
        cov.append(lo <= c0 <= hi)
        above += lo > 0
    print(f"3. {name}: M1's c interval covers the truth in {np.mean(cov):.3f} of 40 cohorts; its lower bound above zero in "
          f"{above} of 40")
