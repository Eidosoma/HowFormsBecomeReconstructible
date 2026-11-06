"""P50q (python probes/p50q_hs002_reading_rule.py): the lead's check of HS002's plateau reading before the freeze, on
synthetic cohorts only (no tissue, no lineage, no value of any run). LEAD_CHECK_NOT_REGISTERED; 1 November 2026.

HS002's Q7 found that the declared plateau reading's M2 clause (M2's c interval above zero) almost never passes for a
true plateau, because M2's c is unidentified whenever M2's slow timescale runs off the grid. Fork H1's synthetic cohorts
did not include the case the clause was written for: a fast decay plus a slow decay to zero (HS001's flag, a slow second
timescale absorbing the plateau). This probe reads nine truths with four rules under three noise models:
- the rules (reading 1, the slow drift, first in every rule; hs002.fit.summarise's report, unchanged):
  C (declared): a plateau if M1 is identified and M1's and M2's c intervals lie above zero;
  A256 (fork H1's option A): M2's c counts only if M2's slow timescale is identified, h2's 95% upper bound <= 256;
  A1024: the same with the bound at the horizon, 1,024;
  B: no M2 clause;
  AH (added by the lead after this probe's first pass showed A256 reading fast-plus-slow decays to zero as plateaus
  under independent noise): A256, and the drift bound: the decay toward zero that D(1024) - D(512)'s 95% lower bound
  leaves possible has a half-life of at least the horizon, 1,024 rewrites (D(512) + lower bound > 0 and
  512 ln 2 / ln(D(512) / (D(512) + lower bound)) >= 1,024);
- the truths: plateaus (c 1, a 1, h 5; c 0.5, a 1.5, h 5), zero (c 0, a 2, h 5), a linear drift (1.6 - 0.0012 (n - 1)),
  a slow decay (c 0, a 2, h 600), and fast-plus-slow decays to zero (c 0, a1 1.0 at h 5, a2 1.1 at h2 600, 1,200,
  2,400, 4,800; at n = 256 they stand at 0.82-1.06, HS001's plateau);
- the noise, per block and checkpoint, SD 1.9 (HS001's development: D's block SD 1.70-2.00 over its 16 checkpoints):
  independent (fork H1's model; the drift test at its weakest), and two correlated models calibrated to HS001's own
  late within-block change, the SD of D(256) - D(128) over blocks 0.64 (from its interval, -0.103 [-0.212, +0.009]):
  a block level plus an independent residual (rho 0.943), and a block level plus an AR(1) residual over the checkpoint
  index (phi 0.8, rho 0.842);
- 128 blocks a cohort, 1,000 whole-block resamples, 10 cohorts a cell.
Runs (one core each, nice 10): a first pass with C, A256, A1024 and B from about 18:25Z. AH was added at about 18:31Z,
after that pass's row for the fast-plus-slow decay at h2 600 under independent noise showed A256 reading it as a
plateau, and the whole probe was rerun with the same seed, so the same cohorts (about 18:32-18:40Z;
probes/results/p50q_hs002_reading_rule.txt). The first pass was stopped at about 18:34Z after 26 of its 27 rows; on
all 26 its columns equal the rerun's. The lead's ruling on HS002's Q7 (1 November, after this result): rule AH.
"""
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from hs002 import design as D, fit as F                          # noqa: E402  (HS002's draft fit, read only)

n = np.asarray(D.CHECKPOINTS, float)
K = n.size
e = lambda h: np.exp(-np.log(2) * (n - 1) / h)
TRUTHS = {"plateau c1 h5": 1.0 + 1.0 * e(5), "plateau c0.5 h5": 0.5 + 1.5 * e(5), "zero h5": 2.0 * e(5),
          "linear drift": 1.6 - 0.0012 * (n - 1), "slow decay h600": 2.0 * e(600),
          **{f"fast+slow to 0, h2 {h2}": 1.0 * e(5) + 1.1 * e(h2) for h2 in (600, 1200, 2400, 4800)}}
SD = 1.9


def cov(rho, phi):
    idx = np.arange(K)
    ar = phi ** np.abs(idx[:, None] - idx[None, :]) if phi > 0 else np.eye(K)
    return SD ** 2 * (rho + (1 - rho) * ar)


NOISE = {"independent": cov(0.0, 0.0), "level + independent": cov(0.943, 0.0), "level + AR(1)": cov(0.842, 0.8)}
for name, C_ in NOISE.items():
    i128, i256, i512, i1024 = (list(D.CHECKPOINTS).index(x) for x in (128, 256, 512, 1024))
    sd_late = np.sqrt(C_[i128, i128] + C_[i256, i256] - 2 * C_[i128, i256])
    sd_2nd = np.sqrt(C_[i512, i512] + C_[i1024, i1024] - 2 * C_[i512, i1024])
    print(f"noise {name}: SD of D(256) - D(128) {sd_late:.3f} (HS001 0.64), of D(1024) - D(512) {sd_2nd:.3f}")


def held(rep, d512):
    lb = rep["d1024_minus_d512_ci95"][0]
    return lb >= 0 or (d512 + lb > 0 and 512 * np.log(2) / np.log(d512 / (d512 + lb)) >= 1024)


def rule(rep, kind, d512=None):
    if rep["d1024_minus_d512_ci95"][1] < 0:
        return "drift"
    ident = rep["M1"]["h_ci95"][1] <= 256
    a256 = rep["M2"]["c_ci95"][0] > 0 or rep["M2"]["h2_ci95"][1] > 256
    m2 = {"C": rep["M2"]["c_ci95"][0] > 0, "B": True, "A256": a256,
          "A1024": rep["M2"]["c_ci95"][0] > 0 or rep["M2"]["h2_ci95"][1] > 1024, "AH": a256 and held(rep, d512)}[kind]
    if ident and rep["M1"]["c_ci95"][0] > 0 and m2:
        return "PLATEAU"
    if ident and rep["M1"]["c_ci95"][0] <= 0:
        return "zero"
    return "neither"


RULES = ("C", "A256", "A1024", "B", "AH")
rng = np.random.default_rng(20261101)
print(f"\n{'truth':28s} {'noise':20s} " + "  ".join(f"{r:>22s}" for r in RULES) + "   d1024-512 hit")
for tname, y in TRUTHS.items():
    for nname, C_ in NOISE.items():
        L_ = np.linalg.cholesky(C_)
        tally = {r: {} for r in RULES}
        hits = 0
        for _ in range(10):
            blocks = y[None] + rng.normal(0, 1, (128, K)) @ L_.T
            sets = rng.integers(0, 128, (1000, 128))
            rep = F.summarise(blocks.mean(0), blocks[sets].mean(1))
            hits += rep["d1024_minus_d512_ci95"][1] < 0
            for r in RULES:
                x = rule(rep, r, float(blocks.mean(0)[list(D.CHECKPOINTS).index(512)]))
                tally[r][x] = tally[r].get(x, 0) + 1
        cell = lambda t: ",".join(f"{k}{v}" for k, v in sorted(t.items()))
        print(f"{tname:28s} {nname:20s} " + "  ".join(f"{cell(tally[r]):>22s}" for r in RULES) + f"   {hits}/10", flush=True)
