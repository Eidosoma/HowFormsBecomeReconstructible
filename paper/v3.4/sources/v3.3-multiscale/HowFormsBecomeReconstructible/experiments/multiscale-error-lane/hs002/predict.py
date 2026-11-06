"""HS002's registered statements and prespecified measurements: python -m hs002.predict ROOT [--out PATH] | --freeze

The candidates were drafted in PLAN_HS002.md before any value past rewrite 256; the parts below were chosen and their
thresholds set from probe P50 by the lane's rule (probes/p50b_hs002_margins.py). Every part is a mean over blocks of a
block value (the mean over the block's eight founder x recipient lineages), in percentage points of E014's Q against
the own founder. The plateau-or-drift question is answered by the prespecified measurements and their declared
readings (hs002.fit), not by the parts.
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

from hs001 import analyze as A1  # noqa: E402
from hs002 import analyze as AN, design as D  # noqa: E402

IX = {n: i for i, n in enumerate(D.CHECKPOINTS)}


def _end(f, key, n):
    return lambda E: E[f][key][:, IX[n]]


def _diff(f, key, n1, n0):
    return lambda E: E[f][key][:, IX[n1]] - E[f][key][:, IX[n0]]


# Thresholds from P50 (probes/results/p50b_hs002_margins.txt): the strictest value the rule allows at the declared
# granularity, whole points for the floors and deficits, tenths for the 128-byte band (as HS001).
PARTS = [
    {"id": "H1", "words": "2,048 bytes: Q(rewrite) - Q(erased) after 1,024 rewrites", "units": _end(1, "rewrite_minus_erased", 1024),
     "sense": "ge", "threshold": 8.0},
    {"id": "H1", "words": "2,048 bytes: Q(foreign) - Q(erased) after 1,024 rewrites", "units": _end(1, "foreign_minus_erased", 1024),
     "sense": "ge", "threshold": 8.0},
    {"id": "H1", "words": "128 bytes: Q(rewrite) - Q(erased) after 1,024 rewrites", "units": _end(4, "rewrite_minus_erased", 1024),
     "sense": "ge", "threshold": 9.0},
    {"id": "H1", "words": "128 bytes: Q(foreign) - Q(erased) after 1,024 rewrites", "units": _end(4, "foreign_minus_erased", 1024),
     "sense": "ge", "threshold": 7.0},
    {"id": "H2", "words": "128 bytes: D(1024) - D(256), the lower side", "units": _diff(4, "D", 1024, 256), "sense": "ge", "threshold": -0.3},
    {"id": "H2", "words": "128 bytes: D(1024) - D(256), the upper side", "units": _diff(4, "D", 1024, 256), "sense": "le", "threshold": 0.3},
    {"id": "H3", "words": "2,048 bytes: Q(rewrite) - Q(copy) after 1,024 rewrites", "units": _end(1, "deficit", 1024),
     "sense": "le", "threshold": -8.0},
    {"id": "H3", "words": "128 bytes: Q(rewrite) - Q(copy) after 1,024 rewrites", "units": _end(4, "deficit", 1024),
     "sense": "le", "threshold": -1.0},
]
STATEMENTS = {
    "H1": "Renewal keeps the record against no record to 1,024 rewrites: records renewed from an acquired record (own or "
          "foreign) stay far above records renewed from no record, at both budgets.",
    "H2": "At 128 bytes the founder-specific contrast stays flat from 256 to 1,024 rewrites: D(1024) - D(256) lies in [-0.3, +0.3].",
    "H3": "Renewal does not recover the protected copy's fidelity by 1,024 rewrites, at both budgets.",
}
MEASUREMENTS = {
    "M-a, the plateau or drift at 2,048 bytes": "hs002.fit on D(n) over the 24 checkpoints by rule AH (the lead's ruling "
        "on Q7): a slow drift (D(1024) - D(512)'s 95% interval below zero); a plateau within 1,024 rewrites (M1 identified, "
        "h's 95% upper bound <= 256, with its c interval above zero; M2's c interval above zero wherever M2's slow timescale "
        "is identified, h2's 95% upper bound <= 256; and the level holds: LB, the 95% lower bound of D(1024) - D(512), is "
        ">= 0, or D(512) + LB > 0 and 512 ln 2 / ln(D(512) / (D(512) + LB)) >= 1,024); decay to zero or below within "
        "1,024 rewrites (M1 identified, c's interval not above zero); neither resolved, with its reasons. A plateau "
        "reading means: after a fast approach the record settles at a level above zero, and any further decay toward "
        "zero is slower than the horizon, a half-life of at least 1,024 rewrites; a slower drift is not excluded, and "
        "the drift bound says how slow it must be. For a curve whose asymptote is zero, a cohort-wide block-level offset "
        "reads as a plateau at the c interval's nominal one-sided rate, about 2.5% a cohort. Beside it: the drift bound "
        "and the reading as first declared",
    "M-b, the model-free changes": "D(1024) - D(512) and D(1024) - D(256) at 2,048 bytes, and the late mean over 768, "
        "896 and 1,024, with 95% whole-block intervals",
    "M-c, R_H(n) at 2,048 bytes": "the same rules on R_H(n), HS001's reference constant; no ratio reading at a "
        "budget whose reference is not resolved (HS001's ratio rule)",
    "M-d, basins": "the replicate-concordance excess at 1,024 for rewrite and foreign against the founder-free arms: "
        "basins kept to 1,024 (rewrite's and foreign's intervals above zero, erased's and background's including zero), "
        "or replicates mixed by 1,024 (rewrite's or foreign's including zero)",
    "Reported": "the floor Q(rewrite) - Q(erased) by the same rules; the 128-byte record by the same rules; E014's "
        "published lineages continued (2,048 bytes)",
}


def freeze():
    import time
    out = {"study": D.STUDY, "design_digest": D.digest(), "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "units": "percentage points of E014's Q against the own founder; block means over the eight lineages; scored "
                    "on the 128 development blocks",
           "parts": [{k: p[k] for k in ("id", "words", "sense", "threshold")} for p in PARTS],
           "statements": STATEMENTS, "prespecified_measurements": MEASUREMENTS,
           "rules": {"fit": "hs002.fit over the 24 checkpoints (HS001's procedure), 10,000 whole-block resamples, "
                            "rng('E014', 'bootstrap')", "identified": f"M1's 95% upper bound of h <= {D.IDENTIFIED_H_MAX:g}",
                     "readings": "rule AH (hs002.fit.reading), applied to every curve read; the readings as first declared "
                                 "(hs002.fit.reading_declared) reported beside",
                     "ratio": f"R_H as a ratio only if the reference's 95% lower bound >= {D.DENOM_MIN_FRACTION} x its estimate"}}
    path = LANE / "hs002" / "frozen" / "predictions.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"-> {path}")


def score_all(root):
    d = AN.load(root)
    E = {f: A1.endpoints(d, f) for f in d["factors"]}
    sets = A1.boot_sets(len(d["blocks"]))
    parts, verdicts = [], {}
    for p in PARTS:
        u = np.asarray(p["units"](E), float)
        blk = u.mean(1)
        v = float(blk.mean())
        lo, hi = A1.ci(blk[sets].mean(1))
        holds = v >= p["threshold"] if p["sense"] == "ge" else v <= p["threshold"]
        parts.append({"id": p["id"], "words": p["words"], "value": v, "ci95": [lo, hi], "sense": p["sense"],
                      "threshold": p["threshold"], "holds": bool(holds), "block_sd": float(blk.std(ddof=1)),
                      "unit_sd_over_sqrt_units": float(u.ravel().std(ddof=1) / np.sqrt(u.shape[1]))})
        verdicts.setdefault(p["id"], []).append(bool(holds))
    return {"study": D.STUDY, "stage": d["manifest"]["stage"], "blocks": d["blocks"], "parts": parts,
            "verdicts": {k: ("HOLDS" if all(v) else "FAILS") for k, v in verdicts.items()}}


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
    out.write_text(json.dumps(score_all(a.root), indent=1) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
