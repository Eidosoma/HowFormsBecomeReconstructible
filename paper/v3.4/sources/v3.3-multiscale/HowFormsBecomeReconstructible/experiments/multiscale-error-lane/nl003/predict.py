"""NL003's registered statements and their scoring, written before any development outcome.

python -m nl003.predict   (writes nl003/frozen/predictions.json)

Thresholds are set from engineering probe P46 (32 cases on blocks 900488-900491 under tag mse-p46, disclosed in
REGISTRATION_NL003.md) under BE002's rule with the lead's block SD: probes/p46b_nl003_margins.py prints every part, its
SD over P46's four blocks and over its 32 cases / sqrt 8, the margin under the larger, and its halves. Every part is
read at the last update (2,000 for the tissue and the recipients), formed per case (paired within the case), on
unrounded block means averaged over the blocks (nl003.analyze). A statement HOLDS when every part passes.

k* = 0.75 x KC (NL002's switch). '+A' marks the arbiter (the tuned rule, anchors at density 1/4); an arm without it is
NL002's, on the same draws. Units: 'none', NL001's stores with no body; 'dw', the developing body. Endpoints (NL002's):
ev the share of the four R regions at A's sign; spec, over the regions where A's and B's region signs differ, the share
at A's sign less the share at B's; k_spec the same inside the killed square (event K); align_A the cells at A's sign;
ref_all the arbiter's refused share of regions. 't/r/' the tissue's record, 's/' the L1-only recipient's body, 'g/' the
gated coded recipient's body.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nl003 import design as D  # noqa: E402

THR = {"G1": {"repair": 0.95, "keep": 0.95},
       "G2": {"repair": 0.6, "keep": 0.6},
       "G3": {"protect_none": 1.25, "protect_dw": 1.1, "repair_cost_none": -0.01, "repair_cost_dw": -0.11},
       "G4": {"keep_none": 0.95, "keep_dw": 0.75},
       "G5": {"align_gain": 0.03},
       "G6": {"crosses": 0.85, "gated": 0.6},
       "G7": {"blind": 0.5, "outside": 1.05},
       "G8": {"admits": -0.4}}

K = f"k{D.KSTAR:g}"
R_, A_, S_, G_ = "t/r/", "t/a/", "s/", "g/"


def part(stmt, name, threshold, sense, terms):
    """terms: [(coefficient, unit, key, branch)]; the part's value is the sum of coefficient x the term's level."""
    return {"stmt": stmt, "name": name, "threshold": threshold, "sense": sense, "terms": tuple(terms)}


def parts():
    T = THR
    one = lambda u, key, br: [(1, u, key, br)]
    diff = lambda u, key, b1, b2: [(1, u, key, b1), (-1, u, key, b2)]
    return [
        part("G1", f"G1 none: ev(copy-{K}+A/R), record", T["G1"]["repair"], "ge", one("none", R_ + "ev_reg_ok", f"copy-{K}+A/R")),
        part("G1", f"G1 none: spec(foreign-{K}+A/none), record", T["G1"]["keep"], "ge", one("none", R_ + "spec_reg", f"foreign-{K}+A/none")),
        part("G2", f"G2 dw: ev(copy-{K}+A/R), record", T["G2"]["repair"], "ge", one("dw", R_ + "ev_reg_ok", f"copy-{K}+A/R")),
        part("G2", f"G2 dw: spec(foreign-{K}+A/none), record", T["G2"]["keep"], "ge", one("dw", R_ + "spec_reg", f"foreign-{K}+A/none")),
        part("G3", f"G3 none: spec(foreign-{K}+A/none) - spec(foreign-{K}/none), record", T["G3"]["protect_none"], "ge",
             diff("none", R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}/none")),
        part("G3", f"G3 dw: spec(foreign-{K}+A/none) - spec(foreign-{K}/none), record", T["G3"]["protect_dw"], "ge",
             diff("dw", R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}/none")),
        part("G3", f"G3 none: ev(copy-{K}+A/R) - ev(copy-{K}/R), record", T["G3"]["repair_cost_none"], "ge",
             diff("none", R_ + "ev_reg_ok", f"copy-{K}+A/R", f"copy-{K}/R")),
        part("G3", f"G3 dw: ev(copy-{K}+A/R) - ev(copy-{K}/R), record", T["G3"]["repair_cost_dw"], "ge",
             diff("dw", R_ + "ev_reg_ok", f"copy-{K}+A/R", f"copy-{K}/R")),
        part("G4", f"G4 none: spec(corrupt-{K}+A/none), record", T["G4"]["keep_none"], "ge", one("none", R_ + "spec_reg", f"corrupt-{K}+A/none")),
        part("G4", f"G4 dw: spec(corrupt-{K}+A/none), record", T["G4"]["keep_dw"], "ge", one("dw", R_ + "spec_reg", f"corrupt-{K}+A/none")),
        part("G5", f"G5 dw: align_A(copy-{K}+A/none) - align_A(copy-{K}/none), record", T["G5"]["align_gain"], "ge",
             diff("dw", R_ + "align_A", f"copy-{K}+A/none", f"copy-{K}/none")),
        part("G6", f"G6 dw: s/spec(foreign-{K}+A/none) - s/spec(foreign-{K}/none), the L1-only recipient", T["G6"]["crosses"], "ge",
             diff("dw", S_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}/none")),
        part("G6", f"G6 dw: g/spec(foreign-{K}+A/none), the gated coded recipient", T["G6"]["gated"], "ge",
             one("dw", G_ + "spec_reg", f"foreign-{K}+A/none")),
        part("G7", f"G7 dw: [spec(foreign-{K}+A/K) - spec(foreign-{K}/K)] - [k_spec(foreign-{K}+A/K) - k_spec(foreign-{K}/K)], "
             "record (the protection over the sheet less inside the killed square)", T["G7"]["blind"], "ge",
             diff("dw", R_ + "spec_reg", f"foreign-{K}+A/K", f"foreign-{K}/K")
             + [(-1, "dw", R_ + "k_spec_reg", f"foreign-{K}+A/K"), (1, "dw", R_ + "k_spec_reg", f"foreign-{K}/K")]),
        part("G7", f"G7 dw: spec(foreign-{K}+A/K) - spec(foreign-{K}/K), record (the whole sheet)", T["G7"]["outside"], "ge",
             diff("dw", R_ + "spec_reg", f"foreign-{K}+A/K", f"foreign-{K}/K")),
        part("G8", f"G8 dw: spec(foreign-{K}+A/change), record (anchors and reference both carry B)", T["G8"]["admits"], "le",
             one("dw", R_ + "spec_reg", f"foreign-{K}+A/change")),
    ]


def score(data):
    from nl003.analyze import estimate, part_cases
    out = {}
    for p in parts():
        est = estimate(part_cases(data, p["terms"]))
        th = p["threshold"]
        ok = None if th is None else (est["value"] >= th if p["sense"] == "ge" else est["value"] <= th)
        node = out.setdefault(p["stmt"], {"parts": {}})
        node["parts"][p["name"]] = dict(est, threshold=th, sense=p["sense"], pass_=ok)
    for sid, node in out.items():
        oks = [v["pass_"] for v in node["parts"].values()]
        node["verdict"] = "UNSET" if any(o is None for o in oks) else ("HOLDS" if all(oks) else "FAILS")
    return out


if __name__ == "__main__":
    lane = Path(__file__).resolve().parents[1]
    path = lane / "nl003" / "frozen" / "predictions.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"study": D.STUDY, "design_digest": D.digest(), "thresholds": THR,
                                "parts": [{k: (list(v) if k == "terms" else v) for k, v in p.items()} for p in parts()],
                                "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1) + "\n")
    print(path)
