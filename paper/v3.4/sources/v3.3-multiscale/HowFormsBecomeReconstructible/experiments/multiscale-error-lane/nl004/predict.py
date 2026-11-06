"""NL004's registered statements and their scoring, written before any development outcome.

python -m nl004.predict   (writes nl004/frozen/predictions.json)

Thresholds are set from engineering probe P48 (32 cases on blocks 900129-900132 under tag mse-p48, disclosed in
REGISTRATION_NL004.md) under BE002's rule with the lead's block SD: probes/p48b_nl004_margins.py prints every part, its
SD over P48's four blocks and over its 32 cases / sqrt 8, the margin under the larger, and its halves. Every part is
read at the last update (2,000 for the tissue and the recipients), formed per case (paired within the case), on
unrounded block means averaged over the blocks (nl004.analyze). A statement HOLDS when every part passes.

k* = 0.75 x KC. '+X' marks the arbiter (NL003's rule) with anchors X (design.ANCHORS): A given (sign(R0_A), = the
record's commitment at the branch), Mv made from the acquired body, Me made from the record after the event, Mt1000
made from the record at update 1,000, Mpre made before A was taught, S1e-2 and S1e-3 slow copies. An arm without '+'
is NL002's, on the same draws. Units: 'none', NL001's stores; 'dw', the developing body. Endpoints (NL002's): ev the
share of the four R regions at A's sign; spec, over the regions where A's and B's region signs differ, the share at
A's sign less the share at B's; align_A the cells at A's sign; anc_B_kd the share of anchor sites in the killed
square's differing regions holding B's sign; ref_all the arbiter's refused share of regions; k_spec the spec inside the
killed square. 't/r/' the tissue's record, 't/a/' the arbiter and its anchors, 'g/' the coded recipient gated by the
parent's given anchors, 'm/' the coded recipient gated by anchors it makes from the record it inherits.

The parts were recast once, after the full-length smoke's values (engineering block 900137) were read and before P48
was read (PLAN_NL004.md's draft): H3 (protection lost and the faithful copy refused, not 'no protection'), H4 (the
faithful arm's gain kept, not lost), H5 (the repair against the given anchors, not the arbiter off), H6 (the successor's
own anchors against the parent's), H8 (the slow copy inside the killed square, against the given anchors; later moved
to reported by the lead's ruling, below).

Thresholds (set from P48 by probes/p48b_nl004_margins.py): each the tightest round value the rule allows.

H8 (the slow copy inside the killed square against the given anchors) is reported, not registered, in both units (the
lead's ruling, 1 November 2026, about 12:35Z). In the stores its value is fixed by the mechanism, not by who makes the
anchors: without relearning bonds a killed square keeps its gauge frame at its corner cells only, so no anchor can change
it except through a tie (P48: 0 in all 27 defined cases). In the body its P48 value (+0.191, SD 0.164, from 5 of 27
defined cases) allowed no bound under the rule. Registered: H1-H7, 26 parts.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nl004 import design as D  # noqa: E402

THR = {"H1": {"none": -0.9, "dw": -0.5},
       "H2": {"none": 1.25, "dw": 1.05},
       "H3": {"lost_none": 0.8, "lost_dw": 0.65, "refuses_none": 0.2, "refuses_dw": 0.1},
       "H4": {"protect_none": 0.85, "protect_dw": 1.0, "align_dw": 0.03},
       "H5": {"protect_fast_none": 1.3, "protect_fast_dw": 1.15, "protect_slow_none": 1.3, "protect_slow_dw": 1.1,
              "repair_fast_none": -0.85, "repair_fast_dw": -0.45, "repair_slow_none": -0.07, "repair_slow_dw": -0.06},
       "H6": {"kept": 0.6, "lost": -0.3, "as_parent": -0.02},
       "H7": {"admits_none": -0.95, "admits_dw": -0.8, "defends_none": -1.45, "defends_dw": -1.25}}

K = f"k{D.KSTAR:g}"
R_, A_, M_ = "t/r/", "t/a/", "m/"


def part(stmt, name, threshold, sense, terms):
    """terms: [(coefficient, unit, key, branch)]; the part's value is the sum of coefficient x the term's level."""
    return {"stmt": stmt, "name": name, "threshold": threshold, "sense": sense, "terms": tuple(terms)}


def parts():
    T = THR
    one = lambda u, key, br: [(1, u, key, br)]
    diff = lambda u, key, b1, b2: [(1, u, key, b1), (-1, u, key, b2)]
    U = ("none", "dw")
    out = []
    for u in U:
        out.append(part("H1", f"H1 {u}: ev(copy-{K}+Me/R) - ev(copy-{K}/R), record (anchors made after the injury)",
                        T["H1"][u], "le", diff(u, R_ + "ev_reg_ok", f"copy-{K}+Me/R", f"copy-{K}/R")))
    for u in U:
        out.append(part("H2", f"H2 {u}: spec(foreign-{K}+A/none) - spec(foreign-{K}+Mt1000/none), record (protection lost "
                        "by a commitment at 1,000)", T["H2"][u], "ge",
                        diff(u, R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}+Mt1000/none")))
    for u in U:
        out.append(part("H3", f"H3 {u}: spec(foreign-{K}+A/none) - spec(foreign-{K}+Mpre/none), record (protection lost by "
                        "anchors made before the history)", T["H3"][f"lost_{u}"], "ge",
                        diff(u, R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}+Mpre/none")))
        out.append(part("H3", f"H3 {u}: ref_all(copy-{K}+Mpre/none) - ref_all(copy-{K}+A/none), the arbiter (the faithful "
                        "copy refused by them)", T["H3"][f"refuses_{u}"], "ge",
                        diff(u, A_ + "ref_all", f"copy-{K}+Mpre/none", f"copy-{K}+A/none")))
    for u in U:
        out.append(part("H4", f"H4 {u}: spec(foreign-{K}+Mv/none) - spec(foreign-{K}/none), record (protection by "
                        "body-made anchors)", T["H4"][f"protect_{u}"], "ge",
                        diff(u, R_ + "spec_reg", f"foreign-{K}+Mv/none", f"foreign-{K}/none")))
    out.append(part("H4", f"H4 dw: align_A(copy-{K}+Mv/none) - align_A(copy-{K}/none), record (the faithful arm's gain "
                    "with body-made anchors)", T["H4"]["align_dw"], "ge",
                    diff("dw", R_ + "align_A", f"copy-{K}+Mv/none", f"copy-{K}/none")))
    for arb, tag in (("S1e-2", "fast"), ("S1e-3", "slow")):
        for u in U:
            out.append(part("H5", f"H5 {u}: spec(foreign-{K}+{arb}/none) - spec(foreign-{K}/none), record (a slow copy's "
                            "protection)", T["H5"][f"protect_{tag}_{u}"], "ge",
                            diff(u, R_ + "spec_reg", f"foreign-{K}+{arb}/none", f"foreign-{K}/none")))
    for arb, tag, sense in (("S1e-2", "fast", "le"), ("S1e-3", "slow", "ge")):
        for u in U:
            out.append(part("H5", f"H5 {u}: ev(copy-{K}+{arb}/R) - ev(copy-{K}+A/R), record (the repair a slow copy's "
                            "learning costs)", T["H5"][f"repair_{tag}_{u}"], sense,
                            diff(u, R_ + "ev_reg_ok", f"copy-{K}+{arb}/R", f"copy-{K}+A/R")))
    out.append(part("H6", f"H6 dw: m/spec(foreign-{K}+A/none), the successor-made gated recipient after a protected "
                    "parent", T["H6"]["kept"], "ge", one("dw", M_ + "spec_reg", f"foreign-{K}+A/none")))
    out.append(part("H6", f"H6 dw: m/spec(foreign-{K}/none), the successor-made gated recipient after an overwritten "
                    "parent", T["H6"]["lost"], "le", one("dw", M_ + "spec_reg", f"foreign-{K}/none")))
    out.append(part("H6", f"H6 dw: m/spec(foreign-{K}+A/none) - g/spec(foreign-{K}+A/none), the successor's own anchors "
                    "against the parent's given ones", T["H6"]["as_parent"], "ge",
                    diff("dw", M_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}+A/none")[:1]
                    + [(-1, "dw", "g/spec_reg", f"foreign-{K}+A/none")]))
    for u in U:
        out.append(part("H7", f"H7 {u}: spec(foreign-{K}+Me/change), record (the tissue and the reference carry B; "
                        "scored against A)", T["H7"][f"admits_{u}"], "le", one(u, R_ + "spec_reg", f"foreign-{K}+Me/change")))
        out.append(part("H7", f"H7 {u}: spec(copy-{K}+Me/change) - spec(copy-{K}/change), record (the carried change "
                        "defended against the faithful copy)", T["H7"][f"defends_{u}"], "le",
                        diff(u, R_ + "spec_reg", f"copy-{K}+Me/change", f"copy-{K}/change")))
    return out


def score(data):
    from nl004.analyze import estimate, part_cases
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
    path = lane / "nl004" / "frozen" / "predictions.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"study": D.STUDY, "design_digest": D.digest(), "thresholds": THR,
                                "parts": [{k: (list(v) if k == "terms" else v) for k, v in p.items()} for p in parts()],
                                "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1) + "\n")
    print(path)
