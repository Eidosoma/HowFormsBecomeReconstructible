"""AR003C's reader: python -m ar003c.analyze --root STAGE_ROOT --out OUT_DIR  (writes summary.json, the reported values)

AR003's pooled arithmetic, from ar003.analyze imported unchanged (each run's arms are read from the shards' own meta, so
the reader scores reduced and full shards alike): per case the mean over the eight unit-body pairs, a block's value the
mean over its eight cases, equal weights over AR001's eight scorings at t = 8,000 and over the three sizes; none and cue
damage scored on every size's patch from their 4 x 4 runs; the information-limit pair from change@0 at 4 x 4 and its
identity (1/8) at 2 x 2 and 8 x 8. The contrasts, per case:
  c1         U_mix(vms) - U_mix(vote)                                   (C1, primary)
  c2         U_8(vms) - U_8(det)                                        (C2)
  sham_cue   r_all(vote) - r_all(vms) in cue@0                          (C3)
  sham_none  r_all(vote) - r_all(vms) in none@0                         (C3)
Every interval is design.INTERVAL: mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks.
Reported, not criteria: U_2, U_4, U_8 and U_mix of the vote and vms, U_8 of det, u by scoring; the size contrasts
U_L(vms) - U_L(vote); U_4(vms) - U_4(vote) in its terms (memory and correlated, the four scorings, the pair); vms's and
det's rates, onset and footprint by run; the half-widths against their targets; the SDs against the development's; the
difference from the development; the contrasts per unit-body pair; the information-limit identity.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar003 import analyze as AZ  # noqa: E402  (load, U_L, U_mix, u, sham, rate, four, hits, det_profile; unchanged)
from ar003c import design as D  # noqa: E402

PAIRS = AZ.PAIRS
load = AZ.load


def interval(x):
    """x (blocks, cases): the mean over the blocks with design.INTERVAL's 95% t interval."""
    x = np.asarray(x, float)
    blk = x.mean(-1)
    n = len(blk)
    sd_b = float(blk.std(ddof=1))
    sd_c = float(x.ravel().std(ddof=1) / math.sqrt(x.shape[-1]))
    sd = max(sd_b, sd_c)
    m = float(blk.mean())
    h = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n))
    return {"mean": m, "lo": m - h, "hi": m + h, "half_width": h, "sd": sd, "sd_block": sd_b, "sd_case8": sd_c,
            "n_blocks": n, "blocks": [float(v) for v in blk]}


def contrasts(Z, pairs=PAIRS):
    C = D.CONTROLLER
    return {"c1": AZ.U_mix(Z, C, pairs) - AZ.U_mix(Z, D.BEST, pairs),
            "c2": AZ.U_L(Z, C, 8, pairs) - AZ.U_L(Z, "det", 8, pairs),
            "sham_cue": AZ.sham(Z, "cue@0", C, pairs=pairs),
            "sham_none": AZ.sham(Z, "none@0", C, pairs=pairs)}


def reported(Z, X=None):
    X = contrasts(Z) if X is None else X
    I = {k: interval(v) for k, v in X.items()}
    n = I["c1"]["n_blocks"]
    C = D.CONTROLLER
    U = {f"{a}/L{L}": interval(AZ.U_L(Z, a, L)) for a in (D.BEST, C) for L in D.SIZES}
    U["det/L8"] = interval(AZ.U_L(Z, "det", 8))
    out = {"half_widths": {k: {"half_width": I[k]["half_width"], "target": D.TARGET[k],
                               "within": I[k]["half_width"] <= D.TARGET[k]} for k in ("c1", "c2")},
           "sd_against_development": {k: {"sd": I[k]["sd"], "dev_sd": D.DEV[k]["sd"], "ratio": I[k]["sd"] / D.DEV[k]["sd"],
                                          "within_sd_upper": I[k]["sd"] / D.DEV[k]["sd"] <= D.SD_UPPER}
                                      for k in ("c1", "c2", "sham_cue")},
           "against_development": {}, "U_L": U,
           "U_mix": {a: interval(AZ.U_mix(Z, a)) for a in (D.BEST, C)},
           "size_contrasts": {f"U_{L}(vms) - U_{L}(vote)": interval(AZ.U_L(Z, C, L) - AZ.U_L(Z, D.BEST, L)) for L in D.SIZES},
           "u": {f"{a}/L{L}": {s: float(AZ.u(Z, a, s, L).mean()) for s in D.SCORINGS
                               if s not in AZ.PAIR or (L == D.SIZE and AZ.has(Z, "change@0", a))}
                 for a in (D.BEST, C) for L in D.SIZES},
           "gap_4": {"hits": interval(AZ.hits(Z, C, D.BEST)), "four": interval(AZ.four(Z, C, D.BEST)),
                     "pair": interval(sum(D.WEIGHTS[s] * (AZ.u(Z, C, s) - AZ.u(Z, D.BEST, s)) for s in AZ.PAIR))},
           "rates": {f"{run}/{a}": dict(AZ.det_profile(Z, run, a),
                                        p_fired_ci=interval(AZ.rate(Z, a, run.split("@")[0], int(run.split("-L")[1]) if "-L" in run else D.SIZE)),
                                        p_located_ci=interval(AZ.rate(Z, a, run.split("@")[0], int(run.split("-L")[1]) if "-L" in run else D.SIZE,
                                                                      which="located")))
                     for run, arms in AZ.runs_of(Z).items() for a in arms if a in ("det", C)},
           "pairs": {f"{b}/{un}": {k: float(v.mean()) for k, v in contrasts(Z, ((b, un),)).items()} for b, un in PAIRS},
           "information_limit_max": float(AZ.info_limit(Z).max())}
    for k in ("c1", "c2"):
        se_c, se_d = I[k]["sd"] / math.sqrt(n), D.DEV[k]["sd"] / math.sqrt(16)
        diff = I[k]["mean"] - D.DEV[k]["value"]
        out["against_development"][k] = {"confirmation": I[k]["mean"], "development": D.DEV[k]["value"], "difference": diff,
                                         "z": diff / math.sqrt(se_c ** 2 + se_d ** 2)}
    return I, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = load(a.root)
    I, R = reported(Z)
    m = AZ.meta(Z)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps({"study": D.STUDY, "tag": m["tag"], "purpose": m["purpose"],
                                                    "design_digest": m["design_digest"], "blocks": AZ.blocks_of(Z),
                                                    "intervals": I, "reported": R}, indent=0) + "\n")
    print("wrote", a.out / "summary.json")


if __name__ == "__main__":
    main()
