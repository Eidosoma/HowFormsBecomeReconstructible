"""AR006C's reader: python -m ar006c.analyze --root STAGE_ROOT --out OUT_DIR  (writes summary.json, the reported values)

AR006's pooled arithmetic, from ar006.analyze imported unchanged (each run's arms are read from the shards' own meta, so
the reader scores reduced and full shards alike): per case the mean over the eight unit-body pairs, a block's value the
mean over its eight cases; u(arm, run) the record's agreement with the run's correct target inside its patch at
t = 8,000. The criteria's contrasts, per case (ar006.analyze's own functions):
  k1_cue    r_all(vote) - r_all(vtol) in cue@0                                       K1
  k1_none   r_all(vote) - r_all(vtol) in none@0                                      K1
  k3a       R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1)   K3 (a)
  k5a       u(vtol) - u(vms) in correlated@0 at 4 x 4                                K5 (a)
Every interval is ar006.analyze.ci (design.INTERVAL): mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n).
Reported, not criteria: vtol less vms under cue@0, and vms's own sheet costs; vtol's give inside the patch under cue@0;
R1 by size; u by arm and run; vms's and vtol's rates, onsets and footprints by run; vtol's branch against vms's per
lineage-case (ar006.analyze.branches); both halves (the first and the last half of the stage's blocks in ascending
order: for the confirmation design.HALVES); the SDs against the development's; each contrast's difference from the
development with its z; the contrasts per unit-body pair (ar005.analyze's functions with one pair).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar005 import analyze as Z5  # noqa: E402  (u, sham, R1 with a pair subset; unchanged)
from ar006 import analyze as Z6  # noqa: E402  (load, sham, R1, corr, give, case, det_profile, branches, ci; unchanged)
from ar006c import design as D  # noqa: E402

PAIRS = Z6.PAIRS
load, blocks_of, case, runs_of, det_profile = Z6.load, Z6.blocks_of, Z6.case, Z6.runs_of, Z6.det_profile
C, S1 = D.CONTROLLER, D.S1


def interval(x):
    """x (blocks, cases): ar006.analyze.ci (the mean over the blocks with design.INTERVAL's 95% t interval)."""
    c = Z6.ci(np.asarray(x, float))
    return dict(c, half_width=c["hi"] - c["mean"], n_blocks=len(c["blocks"]))


def contrasts(Z, pairs=None):
    """The criteria's contrasts, (blocks, cases); pooled over the eight pairs by ar006.analyze's own functions, or over
    a subset of pairs by ar005.analyze's (the same arithmetic)."""
    if pairs is None:
        return {"k1_cue": Z6.sham(Z, "cue@0", C), "k1_none": Z6.sham(Z, "none@0", C), "k3a": Z6.R1(Z),
                "k5a": Z6.corr(Z, 0.0)}
    return {"k1_cue": Z5.sham(Z, "cue@0", C, pairs), "k1_none": Z5.sham(Z, "none@0", C, pairs),
            "k3a": Z5.R1(Z, C, D.STATEMENT_SIZES, pairs),
            "k5a": Z5.u(Z, C, "correlated", D.SIZE, 0.0, pairs) - Z5.u(Z, "vms", "correlated", D.SIZE, 0.0, pairs)}


def vtol_less_vms(Z):
    return Z6.sham(Z, "cue@0", C) - Z6.sham(Z, "cue@0", "vms")


def halves(Z, X):
    bl = blocks_of(Z)
    h = len(bl) // 2
    return {"blocks": [bl[:h], bl[h:]],
            "values": {k: {"half1": interval(v[:h]), "half2": interval(v[h:])} for k, v in X.items()}}


def reported(Z, X=None):
    X = contrasts(Z) if X is None else X
    I = {k: interval(v) for k, v in X.items()}
    n = I["k1_cue"]["n_blocks"]
    vl = vtol_less_vms(Z)
    Y = dict(X, vtol_less_vms_cue=vl)
    IY = dict(I, vtol_less_vms_cue=interval(vl))
    out = {"vtol_less_vms_cue": IY["vtol_less_vms_cue"],
           "sham_vms": {run: interval(Z6.sham(Z, run, "vms")) for run in ("cue@0", "none@0")},
           "give_cue": interval(Z6.give(Z, C, "cue")),
           "R1_by_size": {f"L{L}": interval(Z5.u(Z, C, "memory", L, S1) - Z5.u(Z, "vms", "memory", L, S1))
                          for L in D.STATEMENT_SIZES},
           "u": {f"{a}/{run}": float(case(Z, run, "r_in", a).mean()) for run, arms in runs_of(Z).items() for a in arms},
           "rates": {f"{run}/{a}": det_profile(Z, run, a) for run, arms in runs_of(Z).items() for a in arms
                     if a != D.BEST},
           "branches": {run: Z6.branches(Z, run) for run, arms in runs_of(Z).items() if C in arms},
           "halves": halves(Z, Y),
           "sd_against_development": {k: {"sd": IY[k]["sd"], "dev_sd": D.DEV[k]["sd"],
                                          "ratio": IY[k]["sd"] / D.DEV[k]["sd"],
                                          "within_sd_upper": IY[k]["sd"] / D.DEV[k]["sd"] <= D.SD_UPPER} for k in Y},
           "against_development": {},
           "pairs": {f"{b}/{un}": {k: float(v.mean()) for k, v in contrasts(Z, ((b, un),)).items()} for b, un in PAIRS}}
    for k in Y:
        se_c, se_d = IY[k]["sd"] / math.sqrt(n), D.DEV[k]["sd"] / math.sqrt(D.DEV_BLOCKS)
        diff = IY[k]["mean"] - D.DEV[k]["value"]
        out["against_development"][k] = {"confirmation": IY[k]["mean"], "development": D.DEV[k]["value"],
                                         "difference": diff, "z": diff / math.sqrt(se_c ** 2 + se_d ** 2)}
    return I, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = load(a.root)
    I, R = reported(Z)
    m = Z5.AZ.meta(Z)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps({"study": D.STUDY, "tag": m["tag"], "purpose": m["purpose"],
                                                    "design_digest": m["design_digest"], "blocks": blocks_of(Z),
                                                    "intervals": I, "reported": R}, indent=0, default=float) + "\n")
    print("wrote", a.out / "summary.json")


if __name__ == "__main__":
    main()
