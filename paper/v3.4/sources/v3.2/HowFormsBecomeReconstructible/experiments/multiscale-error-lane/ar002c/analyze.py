"""AR002C's reader: python -m ar002c.analyze --root STAGE_ROOT --out OUT_DIR  (writes summary.json, the reported values)

AR002's pooled arithmetic, from ar002.analyze imported unchanged (each run's arms are read from the shards' own meta, so
the reader scores reduced and full shards alike): per case the mean over the eight unit-body pairs, a block's value the
mean over its eight cases, equal weights over AR001's eight scorings at t = 8,000. The contrasts, per case:
  (a)        U(det) - U(vote)                                           (C1, primary)
  (b)        (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2       (C2, co-primary); U_ctrl per scoring
             p u(dial) + (1 - p) u(rest), p = 0.9 on memory, correlated and change/new, 0.1 elsewhere
  sham_cue   r_all(rest) - r_all(det) in cue@0                          (C3)
  sham_none  r_all(rest) - r_all(det) in none@0                         (C3)
Every interval is design.INTERVAL: mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks.
Reported, not criteria: every arm's U and u by scoring; U_pred(det) (the declared signal's exact value at det's own
firing), U_loc, the price U(det) - U_pred; U_ceiling and U_ctrl(0.9, 0.1); det's rates, onset and footprint by run; the
vote-gap terms (ar002.analyze.gap) for the ceiling and det; the half-widths against their targets; the SDs against the
development's; the difference from the development; (a) and (b) per unit-body pair; the information-limit identity.
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

from ar002 import analyze as AZ  # noqa: E402  (load, U, u, U_ctrl, U_mix, sham, rate, gap, det_profile; unchanged)
from ar002c import design as D  # noqa: E402

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
    h, f = D.POINT
    rest = AZ.U(Z, "rest", pairs=pairs)
    det = AZ.U(Z, "det", pairs=pairs)
    return {"a": det - AZ.U(Z, D.BEST, pairs=pairs),
            "b": (det - rest) - (AZ.U_ctrl(Z, h, f, pairs=pairs) - rest) / 2,
            "sham_cue": AZ.sham(Z, "cue@0", "det", pairs=pairs),
            "sham_none": AZ.sham(Z, "none@0", "det", pairs=pairs)}


def reported(Z, X=None):
    X = contrasts(Z) if X is None else X
    I = {k: interval(v) for k, v in X.items()}
    n = I["a"]["n_blocks"]
    arms = AZ.runs_of(Z)[D.run_name("none", 0.0)]
    U = {a: AZ.U(Z, a) for a in arms}
    rest = U["rest"]
    pred, loc = AZ.U_mix(Z, "det", "fired"), AZ.U_mix(Z, "det", "located")
    ceiling, ctrl = AZ.U_ceiling(Z), AZ.U_ctrl(Z, *D.POINT)
    out = {"half_widths": {k: {"half_width": I[k]["half_width"], "target": D.TARGET[k],
                               "within": I[k]["half_width"] <= D.TARGET[k]} for k in ("a", "b")},
           "sd_against_development": {k: {"sd": I[k]["sd"], "dev_sd": D.DEV[k]["sd"], "ratio": I[k]["sd"] / D.DEV[k]["sd"],
                                          "within_sd_upper": I[k]["sd"] / D.DEV[k]["sd"] <= D.SD_UPPER} for k in ("a", "b")},
           "against_development": {}, "U": {a: interval(v) for a, v in U.items()},
           "u": {a: {s: float(AZ.u(Z, a, s).mean()) for s in D.SCORINGS} for a in arms},
           "U_pred": interval(pred), "U_loc": interval(loc), "price": interval(U["det"] - pred),
           "price_loc": interval(U["det"] - loc), "U_ceiling": interval(ceiling), "U_ctrl_0.9_0.1": interval(ctrl),
           "det_minus_ceiling": interval(U["det"] - ceiling),
           "worth_kept_vs_0.9_0.1": float((U["det"] - rest).mean() / (ctrl - rest).mean()),
           "worth_kept_vs_ceiling": float((U["det"] - rest).mean() / (ceiling - rest).mean()),
           "rates": {run: dict(AZ.det_profile(Z, run, "det"),
                               p_fired_ci=interval(AZ.rate(Z, "det", run.partition("@")[0])),
                               p_located_ci=interval(AZ.rate(Z, "det", run.partition("@")[0], which="located")))
                     for run in D.RUNNAMES},
           "gap": {name: {k: (interval(v) if not isinstance(v, dict) else {s: float(x.mean()) for s, x in v.items()})
                          for k, v in AZ.gap(Z, arm).items()} for name, arm in (("ceiling", None), ("det", "det"))},
           "pairs": {f"{b}/{un}": {k: float(v.mean()) for k, v in contrasts(Z, ((b, un),)).items()} for b, un in PAIRS},
           "information_limit_max": float(AZ.info_limit(Z).max())}
    for k in ("a", "b"):
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
