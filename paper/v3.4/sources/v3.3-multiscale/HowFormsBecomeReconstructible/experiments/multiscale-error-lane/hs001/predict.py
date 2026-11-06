"""HS001's registered statements: python -m hs001.predict ROOT [--out PATH]  ->  the parts' values, 95% whole-block
intervals (E014's generator) and verdicts.

The candidates were drafted in PLAN_HS001.md before any long-horizon value; the parts below were chosen and their
thresholds set from probe P49 by the lane's rule (probes/p49b_hs001_margins.py). Every part is a mean over blocks of
a block value (the mean over the block's units: eight founder x recipient lineages), in percentage points of E014's
qualified agreement against the own founder. A statement holds when all its parts hold. The asymptote's fit and the
replicate concordance are prespecified measurements with declared readings (hs001.fit, REGISTRATION_HS001.md), not
parts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
sys.dont_write_bytecode = True

from hs001 import analyze as AN, design as D  # noqa: E402

IX = {n: i for i, n in enumerate(D.CHECKPOINTS)}
LATE = [IX[n] for n in D.LATE]


def _D(f, n):
    return lambda E: E[f]["D"][:, IX[n]]


def _RH(f, n, k):
    """R_H(n) >= k (or <= k) in linear form: D(n) - k Delta_P, per lineage."""
    return lambda E: E[f]["D"][:, IX[n]] - k * E[f]["ref"]


def _diff(f, n1, n0):
    return lambda E: E[f]["D"][:, IX[n1]] - E[f]["D"][:, IX[n0]]


def _late(f):
    return lambda E: E[f]["D"][:, LATE].mean(1)


def _end(f, key, n):
    return lambda E: E[f][key][:, IX[n]]


# Thresholds from P49 (probes/results/p49b_hs001_margins.txt): the strictest value the rule allows at the declared
# granularity, whole points for the floors and the deficits, tenths for the 128-byte band.
PARTS = [
    {"id": "H1", "words": "2,048 bytes: Q(rewrite) - Q(erased) after 256 rewrites", "units": _end(1, "rewrite_minus_erased", 256),
     "sense": "ge", "threshold": 8.0},
    {"id": "H1", "words": "2,048 bytes: Q(foreign) - Q(erased) after 256 rewrites", "units": _end(1, "foreign_minus_erased", 256),
     "sense": "ge", "threshold": 8.0},
    {"id": "H1", "words": "128 bytes: Q(rewrite) - Q(erased) after 256 rewrites", "units": _end(4, "rewrite_minus_erased", 256),
     "sense": "ge", "threshold": 9.0},
    {"id": "H1", "words": "128 bytes: Q(foreign) - Q(erased) after 256 rewrites", "units": _end(4, "foreign_minus_erased", 256),
     "sense": "ge", "threshold": 7.0},
    {"id": "H2", "words": "128 bytes: D(256) - D(16), the lower side", "units": _diff(4, 256, 16), "sense": "ge", "threshold": -0.5},
    {"id": "H2", "words": "128 bytes: D(256) - D(16), the upper side", "units": _diff(4, 256, 16), "sense": "le", "threshold": 0.2},
    {"id": "H3", "words": "2,048 bytes: Q(rewrite) - Q(copy) after 256 rewrites", "units": _end(1, "deficit", 256),
     "sense": "le", "threshold": -8.0},
    {"id": "H3", "words": "128 bytes: Q(rewrite) - Q(copy) after 256 rewrites", "units": _end(4, "deficit", 256),
     "sense": "le", "threshold": -1.0},
]
STATEMENTS = {
    "H1": "Renewal keeps the record against no record: after 256 rewrites, records renewed from an acquired record (own "
          "or foreign) stay far above records renewed from no record, at both budgets.",
    "H2": "At 128 bytes the founder-specific contrast is flat from 16 to 256 rewrites: D(256) - D(16) lies in [-0.5, +0.2].",
    "H3": "Renewal does not recover the protected copy's fidelity: after 256 rewrites own-record renewal stays below the "
          "protected own copy, at both budgets.",
}


def score_all(root):
    d = AN.load(root)
    E = {f: AN.endpoints(d, f) for f in D.FACTORS}
    sets = AN.boot_sets(len(d["blocks"]))
    parts, verdicts = [], {}
    for p in PARTS:
        u = np.asarray(p["units"](E), float)
        blk = u.mean(1)
        v = float(blk.mean())
        lo, hi = AN.ci(blk[sets].mean(1))
        holds = v >= p["threshold"] if p["sense"] == "ge" else v <= p["threshold"]
        parts.append({"id": p["id"], "words": p["words"], "value": v, "ci95": [lo, hi], "sense": p["sense"],
                      "threshold": p["threshold"], "holds": bool(holds), "block_sd": float(blk.std(ddof=1)),
                      "unit_sd_over_sqrt_units": float(u.ravel().std(ddof=1) / np.sqrt(u.shape[1]))})
        verdicts.setdefault(p["id"], []).append(bool(holds))
    return {"study": D.STUDY, "stage": d["manifest"]["stage"], "blocks": d["blocks"], "parts": parts,
            "verdicts": {k: ("HOLDS" if all(v) else "FAILS") for k, v in verdicts.items()}}


MEASUREMENTS = {
    "M-a, the reference and R_H": "Delta_P and R_H(n) at both budgets and every checkpoint, numerator, denominator and "
        "ratio together; the ratio reported only if the reference's 95% lower bound is at least half its estimate; R_H "
        "well below 1 at 16: renewal keeps a fraction of the protected records' readable specificity; near 1: nearly all; "
        "above 1: renewal makes the founders' difference more readable than a protected copy does",
    "M-b, the asymptote": "hs001.fit on D(n) and R_H(n) at each budget: a plateau above zero, a plateau "
        "indistinguishable from zero, a plateau below zero, or not identified within 256 rewrites (M1's 95% upper "
        "bound of h above 64); M1 a decay or a rise (a free in sign); M2's c, the late mean and slope beside it",
    "M-c, the 2,048-byte decline": "D(16) - D(1) at 2,048 bytes (the reviewer's Figure 4D) with its interval; the same "
        "at 128 bytes",
    "M-d, the replicate concordance": "same-founder less cross-founder sign agreement of the decoded records at every "
        "checkpoint and lineage arm; a lasting excess for rewrite and foreign well above the founder-free arms (erased, "
        "background) reads as basins kept, one at their level as mixing; it measures initial-condition information "
        "kept, D measures closeness to the founder's prototype against a foreign founder's lineages",
    "M-e, the floors' course": "Q(rewrite) - Q(erased) and Q(rewrite) - Q(background) at every checkpoint, M1 fitted "
        "to the first",
}


def freeze():
    import time
    out = {"study": D.STUDY, "design_digest": D.digest(), "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "units": "percentage points of E014's qualified agreement Q against the own founder; block means over the "
                    "eight founder x recipient lineages; scored on the 128 development blocks",
           "parts": [{k: p[k] for k in ("id", "words", "sense", "threshold")} for p in PARTS],
           "statements": STATEMENTS, "prespecified_measurements": MEASUREMENTS,
           "rules": {"ratio": f"reported as a ratio only if the reference's 95% lower bound >= {D.DENOM_MIN_FRACTION} x its estimate",
                     "fit": "hs001.fit (PLAN_HS001.md): M1 c + a rho^(n-1) by profile least squares on the 16 checkpoint "
                            "means, M0, M2; 10,000 whole-block resamples, rng('E014', 'bootstrap')",
                     "identified": f"M1's 95% upper bound of the half-life <= {D.IDENTIFIED_H_MAX:g} rewrites"}}
    path = LANE / "hs001" / "frozen" / "predictions.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"-> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        freeze()
        return
    out = a.out or (a.root.parent / f"{a.root.name}_read" / "predictions_scored.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    res = score_all(a.root)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
