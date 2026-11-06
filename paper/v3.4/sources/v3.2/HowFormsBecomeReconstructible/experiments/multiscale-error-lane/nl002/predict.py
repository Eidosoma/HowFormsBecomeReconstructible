"""NL002's registered statements and their scoring, written before any development outcome.

python -m nl002.predict   (writes nl002/frozen/predictions.json)

Thresholds are set from engineering probe P40 (32 cases on blocks 900804-900807 under tag mse-p40, disclosed in
REGISTRATION_NL002.md) under BE002's rule with the lead's block SD: probes/p40b_nl002_margins.py prints every part, its
SD over P40's four blocks and over its 32 cases / sqrt 8, and the margin under the larger. Every part is read at the
window's last update (2,000 for the tissue, 2,000 for the recipient), on unrounded block means (the mean over the
block's cases), averaged over the development blocks. A statement HOLDS when every part passes.

Quantities (unit 'none': NL001's stores with no body; unit 'dw': the developing body; x the record 'r', or the
recipient's body 's', a fresh dw newborn reading the tissue's final L1 record):
  ev(arm/event)       the share of the four R regions back at A's sign
  min_reg(arm/event)  the share of A's minority regions at A's sign
  min_cell(...)       the share of A's minority cells at A's sign
  spec(arm/event)     over the regions where A's and B's region signs differ: the share at A's sign less the share at
                      B's (+1: the own history, -1: the foreign one)
  k_min(...), k_spec(...)   the same over the killed square's minority regions and differing regions (event K)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nl002 import design as D  # noqa: E402

THR = {"N1": {"repair": 0.9, "overwrite": 0.0},
       "N2": {"repair": 0.3, "keep": 0.6},
       "N3": {"cost": 0.05},
       "N4": {"cells": 0.3, "regions": 0.92},
       "N5": {"protect": 0.05},
       "N6": {"erase": 0.03},
       "N7": {"repair": 0.5, "overwrite": 0.0},
       "N8": {"contrast": 0.5},
       "N9": {"impose": 0.0},
       "N10": {"tissue": 0.9, "successor": 0.4},
       "N11": {"successor": 0.5},
       "N12": {"successor": 0.0},
       "N13": {"successor": 0.04},
       "N14": {"cells": 0.3},
       "N15": {"crosses": 0.5},
       "N16": {"crosses": 0.02},
       "N17": {"imposed": 0.0, "against_l1": 0.3},
       "N18": {"contrast": 0.5},
       "N19": {"erosion": 0.05}}


def v(L, unit, key, branch, read=-1):
    return L[unit][key][branch][read][0]


def part(stmt, name, threshold, sense, terms):
    """terms: [(coefficient, unit, key, branch)]; the part's value is the sum of coefficient x the term's level."""
    return {"stmt": stmt, "name": name, "threshold": threshold, "sense": sense, "terms": tuple(terms)}


def value(p, L):
    return sum(c * v(L, u, k, b) for c, u, k, b in p["terms"])


R_, S_, C_ = "t/r/", "s/", "c/"
T = THR
PARTS = [
    part("N1", "N1 none: ev(copy-k0.75/R), record", T["N1"]["repair"], "ge", [(1, "none", R_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N1", "N1 none: spec(foreign-k0.75/none), record", T["N1"]["overwrite"], "le", [(1, "none", R_ + "spec_reg", "foreign-k0.75/none")]),
    part("N2", "N2 none: ev(copy-k0.5/R), record", T["N2"]["repair"], "le", [(1, "none", R_ + "ev_reg_ok", "copy-k0.5/R")]),
    part("N2", "N2 none: spec(foreign-k0.5/none), record", T["N2"]["keep"], "ge", [(1, "none", R_ + "spec_reg", "foreign-k0.5/none")]),
    part("N3", "N3 none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, record", T["N3"]["cost"], "ge",
         [(1, "none", R_ + "min_reg_ok_A", "copy-k0.75/none"), (-1, "none", R_ + "min_reg_ok_A", "own-k0.75/none")]),
    part("N4", "N4 dw: min_cell(off/none), record", T["N4"]["cells"], "le", [(1, "dw", R_ + "min_cell_ok_A", "off/none")]),
    part("N4", "N4 dw: min_reg(off/none), record", T["N4"]["regions"], "le", [(1, "dw", R_ + "min_reg_ok_A", "off/none")]),
    part("N5", "N5 dw: min_reg(copy-k0.25) - min_reg(off), intact, record", T["N5"]["protect"], "ge",
         [(1, "dw", R_ + "min_reg_ok_A", "copy-k0.25/none"), (-1, "dw", R_ + "min_reg_ok_A", "off/none")]),
    part("N6", "N6 dw: spec(off) - spec(foreign-k0.25), intact, record", T["N6"]["erase"], "ge",
         [(1, "dw", R_ + "spec_reg", "off/none"), (-1, "dw", R_ + "spec_reg", "foreign-k0.25/none")]),
    part("N7", "N7 dw: ev(copy-k0.75/R), record", T["N7"]["repair"], "ge", [(1, "dw", R_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N7", "N7 dw: spec(foreign-k0.75/none), record", T["N7"]["overwrite"], "le", [(1, "dw", R_ + "spec_reg", "foreign-k0.75/none")]),
    part("N8", "N8 dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), record", T["N8"]["contrast"], "ge",
         [(1, "dw", R_ + "k_spec_reg", "copy-k0.75/K"), (-1, "dw", R_ + "k_spec_reg", "foreign-k0.75/K")]),
    part("N9", "N9 dw: k_spec(foreign-k0.75/K), record", T["N9"]["impose"], "le", [(1, "dw", R_ + "k_spec_reg", "foreign-k0.75/K")]),
    part("N10", "N10 none: ev(copy-k0.75/R), record", T["N10"]["tissue"], "ge", [(1, "none", R_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N10", "N10 none: ev(copy-k0.75/R), recipient", T["N10"]["successor"], "le", [(1, "none", S_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N11", "N11 dw: ev(copy-k0.75/R), recipient", T["N11"]["successor"], "ge", [(1, "dw", S_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N12", "N12 dw: spec(foreign-k0.75/none), recipient", T["N12"]["successor"], "le", [(1, "dw", S_ + "spec_reg", "foreign-k0.75/none")]),
    part("N13", "N13 dw: min_reg(copy-k0.25) - min_reg(off), intact, recipient", T["N13"]["successor"], "le",
         [(1, "dw", S_ + "min_reg_ok_A", "copy-k0.25/none"), (-1, "dw", S_ + "min_reg_ok_A", "off/none")]),
    part("N14", "N14 dw: min_cell(acqA), recipient", T["N14"]["cells"], "le", [(1, "dw", S_ + "min_cell_ok_A", "acqA")]),
    part("N15", "N15 none: ev(copy-k0.75/R), coded - L1-only recipient", T["N15"]["crosses"], "ge",
         [(1, "none", C_ + "ev_reg_ok", "copy-k0.75/R"), (-1, "none", S_ + "ev_reg_ok", "copy-k0.75/R")]),
    part("N16", "N16 dw: min_reg(copy-k0.25) - min_reg(off), intact, coded recipient", T["N16"]["crosses"], "ge",
         [(1, "dw", C_ + "min_reg_ok_A", "copy-k0.25/none"), (-1, "dw", C_ + "min_reg_ok_A", "off/none")]),
    part("N17", "N17 none: spec(foreign-k0.75/none), coded recipient", T["N17"]["imposed"], "le",
         [(1, "none", C_ + "spec_reg", "foreign-k0.75/none")]),
    part("N17", "N17 none: spec(foreign-k0.75/none), L1-only - coded recipient", T["N17"]["against_l1"], "ge",
         [(1, "none", S_ + "spec_reg", "foreign-k0.75/none"), (-1, "none", C_ + "spec_reg", "foreign-k0.75/none")]),
    part("N18", "N18 dw: k_spec(copy-k0.75/K) - k_spec(foreign-k0.75/K), coded recipient", T["N18"]["contrast"], "ge",
         [(1, "dw", C_ + "k_spec_reg", "copy-k0.75/K"), (-1, "dw", C_ + "k_spec_reg", "foreign-k0.75/K")]),
    part("N19", "N19 none: min_reg(copy-k0.75) - min_reg(own-k0.75), intact, coded recipient", T["N19"]["erosion"], "ge",
         [(1, "none", C_ + "min_reg_ok_A", "copy-k0.75/none"), (-1, "none", C_ + "min_reg_ok_A", "own-k0.75/none")]),
]

CLAIM = {
    "N1": ("gain decides, not truth, with acquired references",
           "In NL001's stores with no body, a faithful copy of the acquired coarse reference at 0.75 x KC repairs at least "
           "{repair} of four coherently flipped regions, while another history's reference at the same gain leaves the "
           "intact tissue's differing regions at most {overwrite} toward its own history (specificity), on average"),
    "N2": ("a weak descending gain neither repairs nor overwrites",
           "In the stores with no body, at 0.5 x KC the faithful copy repairs at most {repair} of the flipped regions, and "
           "another history's reference leaves the intact tissue's specificity at least {keep}, on average"),
    "N3": ("a reference read from the developing body carries the body's erosion",
           "In the stores with no body, at 0.75 x KC the faithful copy keeps at least {cost} more of A's minority regions "
           "than the reference read from A's body at the end of acquisition, intact tissue, on average"),
    "N4": ("a developing body erodes the acquired detail",
           "With the body, no descending correction and no damage, the record keeps at most {cells} of A's minority cells "
           "and at most {regions} of A's minority regions after 2,000 updates, on average"),
    "N5": ("a faithful reference protects history against the body at a weak gain",
           "With the body and no damage, the faithful copy at 0.25 x KC keeps at least {protect} more of A's minority "
           "regions than no descending correction, on average"),
    "N6": ("a wrong reference erodes history at the same weak gain",
           "With the body and no damage, another history's reference at 0.25 x KC lowers the record's specificity by at "
           "least {erase} against no descending correction, on average"),
    "N7": ("in the body, repairing coherent damage needs a gain at which a wrong reference overwrites",
           "With the body, the faithful copy at 0.75 x KC repairs at least {repair} of four coherently flipped regions, "
           "while another history's reference at the same gain leaves the intact record's specificity at most {overwrite}, "
           "on average"),
    "N8": ("after a kill, the same pathway fills the square toward whichever history its reference holds",
           "With the body, after a 2 x 2 square of regions holding one of A's minority regions is killed (cells, bonds and "
           "body, the codes kept), the killed square's specificity (its regions where A and B differ: the share at A's sign "
           "less the share at B's) is at least {contrast} higher under the faithful copy at 0.75 x KC than under another "
           "history's reference at the same gain, paired within case, on average"),
    "N9": ("a wrong reference fills a killed square with its own history",
           "With the body, after the same kill, another history's reference at 0.75 x KC leaves the killed square's "
           "differing regions at most {impose} toward A's history (specificity), on average"),
    "N10": ("in the stores, the successor re-expresses the relations, not the repaired state",
            "In the stores with no body, the faithful copy at 0.75 x KC repairs at least {tissue} of the flipped regions in "
            "the record, yet a fresh body reading that record keeps at most {successor} of them, on average"),
    "N11": ("in the body, relearning carries the repair across the successor boundary",
            "With the body, a fresh body reading the record repaired by the faithful copy at 0.75 x KC keeps at least "
            "{successor} of the flipped regions, on average"),
    "N12": ("a wrong reference's overwrite crosses the successor boundary",
            "With the body, a fresh body reading the record left by another history's reference at 0.75 x KC (no damage) "
            "has specificity at most {successor}, on average"),
    "N13": ("the weak-gain protection does not cross the successor boundary",
            "With the body and no damage, a fresh body reading the record protected by the faithful copy at 0.25 x KC "
            "keeps at most {successor} more of A's minority regions than one reading the record left with no descending "
            "correction, on average"),
    "N14": ("the finest scale cannot cross into a developing body",
            "A fresh body reading A's acquired record itself, protected, keeps at most {cells} of A's minority cells, on "
            "average"),
    "N15": ("in the stores, the copy's repair crosses when the codes cross",
            "In the stores with no body, a fresh body reading the record repaired by the faithful copy at 0.75 x KC together "
            "with the copy's codes keeps at least {crosses} more of the four flipped regions than one reading the record "
            "alone, paired within case, on average"),
    "N16": ("in the body, the weak-gain protection crosses in part when the codes cross",
            "With the body and no damage, a fresh body reading the record protected by the faithful copy at 0.25 x KC "
            "together with its codes keeps at least {crosses} more of A's minority regions than one reading the record left "
            "with no descending correction (which passes no codes), on average"),
    "N17": ("in the stores, a foreign code crossing imposes the other history where the record alone gives back A's",
            "In the stores with no body and no damage, a fresh body reading the record left by another history's reference "
            "at 0.75 x KC together with that reference's codes has specificity at most {imposed}, and at least {against_l1} "
            "lower than one reading the record alone, paired within case, on average"),
    "N18": ("after a kill, the coded successor fills the square toward whichever history its codes hold",
            "With the body, after the kill, a fresh body reading the record together with the faithful copy's codes at 0.75 "
            "x KC has the killed square's specificity at least {contrast} higher than one reading the record with another "
            "history's codes at the same gain, paired within case, on average"),
    "N19": ("codes read from the developing body carry its erosion across the successor boundary",
            "In the stores with no body and no damage, a fresh body reading the record with the faithful copy's codes at "
            "0.75 x KC keeps at least {erosion} more of A's minority regions than one reading the record with the codes read "
            "from A's body at the same gain, on average"),
}


def rule_text(k):
    parts = [p for p in PARTS if p["stmt"] == k]
    words = {"ge": ">=", "le": "<="}
    body = "; ".join(f"{p['name'].split(' ', 1)[1]} {words[p['sense']]} {p['threshold']:g}" for p in parts)
    return f"HOLDS if, on the mean over the development blocks at the last read, {body}, else FAILS"


STATEMENTS = [{"id": k, "kind": c[0], "claim": c[1].format(**THR[k]), "rule": rule_text(k), "thresholds": THR[k]}
              for k, c in CLAIM.items()]


def passes(x, threshold, sense):
    return {"ge": x >= threshold, "le": x <= threshold}[sense]


def score(L):
    S = {}
    for s in STATEMENTS:
        out, ok = {}, True
        for p in (q for q in PARTS if q["stmt"] == s["id"]):
            x = value(p, L)
            good = bool(passes(x, p["threshold"], p["sense"]))
            out[p["name"]] = {"value": x, "pass": good}
            ok &= good
        S[s["id"]] = {"verdict": "HOLDS" if ok else "FAILS", "parts": out}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": THR,
                               "parts": PARTS,
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
