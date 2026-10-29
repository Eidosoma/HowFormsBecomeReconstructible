"""SC002's registered statements and their scoring, written before any development outcome.

python -m sc002.predict   (writes sc002/frozen/predictions.json)

Thresholds were set from engineering probe P25 (32 cases on blocks 900650-900653 under tag mse-p25, disclosed in
REGISTRATION_SC002.md) and revised at the lead's review (28 October 2026) under BE002's rule. For each quantity,
SD_block = max(the item's own SD over P25's four blocks, the RMS of those SDs over the part's items). An every-item part
must sit >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P25's worst item; a pooled part (the mean over its items) uses
the SD over blocks of the pooled per-block value. An item is one unit and body (and arm, where the part names two).
Margins at the registered thresholds (worst item, or the pooled value):

  C1  change8 every item >= 0.10: 1.90; change4 every item >= 0.035: 1.73; change4 mean of 8 >= 0.10 (0.272): 2.49
  C2  change4 mean of 4 >= 0.06 (0.222): 2.16; cue8 r_all every pair <= -0.04: 4.25
      (reported, not a rule: change8 mean of 4 +0.100 against the static maps' +0.031, 1.59)
  C3  change8 mean of 4 >= 0.02 at 1e-3 (0.065): 3.04, at 2.5e-4 (0.089): 3.53; none8 every pair within 0.003: >= 7.69
  C4  every item <= -0.025 at 1e-3: 2.07; <= -0.012 at 2.5e-4: 4.09; difference <= -0.003: 1.90
  C5  every item >= 0.003: 1.79; S4 items >= 0.015: 3.11
  C6  change8 every pair within 0.06: 2.14; cue8 r_all every pair <= inst-1.5's + 0.01: 3.32
  C7  S4 items >= 0.02: 1.85; F0 mean of 4 > 0 (0.0226): 1.81; every item >= inst-1.5's - 0.03: 2.70;
      r_out every item within 0.002: 5.22
  C8  inst-1.5's r_out every pair <= inst-3's - 0.02: 4.35; maturing arms' r_out every item within 0.002: 2.78
  C9  the shrink, mean of 8 >= 0.02 (0.054): 2.20

Scored by sc002.analyze on block means over the 16 development blocks at t = 4,000. r_in: the record's agreement with
the correct target over the patch's occupied sites (for change, the new target); r_out: outside the patch; r_all: over
the sheet. Runs are named situation + patch side @ mu (change8@0.001 = a legitimate change of an 8 x 8 patch under
turnover 1e-3).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sc002 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
MAT = ("mat-300", "mat-1000")
HI, LO = "@0.001", "@0.00025"

STATEMENTS = [
    {"id": "C1", "kind": "turnover lets maturing junctions re-specify small groups",
     "claim": "Under turnover, junctions that mature after each contact forms adopt a legitimate change of a small group that "
              "the same junctions formed at full strength refuse",
     "rule": "HOLDS if at mu = 1e-3 mat-300's and mat-1000's r_in exceed inst-3's by >= 0.10 for change8 in every unit for "
             "both bodies, and for change4 by >= 0.035 in every unit for both bodies and by >= 0.10 on average over the "
             "eight items (two arms x two units x two bodies), else FAILS",
     "inputs": "P25: change8 +0.203 to +0.452 (margin 1.90 SD_block); change4 +0.162 to +0.375 (1.73), mean 0.272 "
               "(SD 0.069, 2.49)"},
    {"id": "C2", "kind": "the birth rate, not mu tau_m, sets the detector",
     "claim": "Two tissues with nearly equal mu tau_m (beta 0.6 and 0.5), whose junctions' effective-medium couplings "
              "(lam_eff 2.18 and 2.28) and static voltage maps nearly agree (the faster's map minus the slower's: change4 "
              "+0.004, false alarms +0.0022, change8 +0.031), differ in the run: the faster-renewing one adopts a 4 x 4 "
              "change more and loses more of the record under scattered corruption",
     "rule": "HOLDS if mat-300 at mu = 1e-3 minus mat-1000 at mu = 2.5e-4 is >= 0.06 in r_in for change4 on average over the "
             "four unit-body pairs, and <= -0.04 in r_all under cue damage in every unit for both bodies, else FAILS",
     "inputs": "P25: change4 mean +0.222 (SD 0.075, margin 2.16); cue8 r_all -0.132 to -0.071 (4.25); reported, not "
               "registered: change8 mean +0.100 (SD 0.044) against the static maps' +0.031"},
    {"id": "C3", "kind": "maturation time acts through pooled coupling only",
     "claim": "Slower junction maturation helps a group adopt a change, through a shorter pooled coupling, but changes nothing "
              "for single cells: with no event the two maturation times keep the record alike",
     "rule": "HOLDS if for change8 mat-1000's r_in exceeds mat-300's by >= 0.02 on average over the four unit-body pairs at "
             "each turnover rate, and with no event their r_all differ by at most 0.003 in every unit for both bodies at "
             "both rates, else FAILS",
     "inputs": "P25: change8 mean +0.065 at 1e-3 (SD 0.015, margin 3.04) and +0.089 at 2.5e-4 (SD 0.020, 3.53); none8 at "
               "most 0.0002 apart (>= 7.69)"},
    {"id": "C4", "kind": "renewal pays in false alarms",
     "claim": "Under scattered cue corruption, maturing junctions lose more of the record than instant long junctions, and the "
              "more so the faster the tissue renews",
     "rule": "HOLDS if under cue damage mat-300's and mat-1000's r_all minus inst-3's is <= -0.025 at mu = 1e-3 and <= -0.012 "
             "at mu = 2.5e-4, and the former is below the latter by >= 0.003, in every unit for both bodies, else FAILS",
     "inputs": "P25: -0.132 to -0.038 (margin 2.07); -0.057 to -0.023 (4.09); -0.074 to -0.015 (1.90)"},
    {"id": "C5", "kind": "renewal repairs inherited errors",
     "claim": "With no event, under turnover, maturing junctions keep more of the record than instant ones, more where the "
              "pattern has many walls",
     "rule": "HOLDS if with no event at mu = 1e-3 mat-300's and mat-1000's r_all exceed inst-3's by >= 0.003 in every unit "
             "for both bodies and by >= 0.015 for S4, else FAILS",
     "inputs": "P25: +0.006 to +0.027 (margin 1.79); S4 +0.022 to +0.027 (3.11)"},
    {"id": "C6", "kind": "steady renewal moves along the trade-off",
     "claim": "In steady turnover the population's detector does not escape BE001's trade-off: at the faster rate, mat-1000 "
              "adopts like a uniformly short coupling and loses at least as much under scattered corruption",
     "rule": "HOLDS if at mu = 1e-3 mat-1000's r_in for change8 is within 0.06 of inst-1.5's and its r_all under cue damage "
             "is <= inst-1.5's + 0.01, in every unit for both bodies, else FAILS",
     "inputs": "P25: -0.004 to +0.031 (margin 2.14); -0.043 to -0.004 (3.32)"},
    {"id": "C7", "kind": "a regrowing wound opens its own detector",
     "claim": "In a wound regrown by division, maturing junctions repair the regrown cells' inherited records better than "
              "instant long junctions and as well as uniformly short ones, while the mature tissue outside is untouched",
     "rule": "HOLDS if in regrow8 mat-300's and mat-1000's r_in exceed inst-3's by >= 0.02 for S4 in both bodies and by > 0 on "
             "average over F0's four items, are >= inst-1.5's - 0.03 and have r_out within 0.002 of inst-3's in every unit "
             "for both bodies, else FAILS",
     "inputs": "P25: S4 +0.062 to +0.093 (margin 1.85); F0 mean +0.023 (SD 0.013, 1.81); -0.001 to +0.017 (2.70); r_out "
               "at most 0.0001 apart (5.22)"},
    {"id": "C8", "kind": "the regrowth signal is local",
     "claim": "Under scattered cue corruption during regrowth, a uniformly short coupling raises false alarms over the whole "
              "sheet, while maturing junctions raise none outside the young tissue",
     "rule": "HOLDS if in regrow+cue8 inst-1.5's r_out is <= inst-3's - 0.02 while mat-300's and mat-1000's r_out are within "
             "0.002 of inst-3's, in every unit for both bodies, else FAILS",
     "inputs": "P25: -0.048 to -0.033 (margin 4.35); at most 0.0005 apart (2.78)"},
    {"id": "C9", "kind": "young tissue also reads corrupted cues",
     "claim": "The regrowing tissue's advantage over instant long junctions shrinks when the cue is corrupted",
     "rule": "HOLDS if (mat - inst-3) in r_in, regrow8 minus regrow+cue8, is >= 0.02 on average over the eight items (two "
             "arms x two units x two bodies), else FAILS",
     "inputs": "P25: mean +0.054 (SD 0.016, margin 2.20); items +0.031 to +0.068"},
]


def lv(L, u, b, rn, arm, e="r_in"):
    return L[u][b][rn][arm][e][-1][0]


def op(L, u, b, rn, arm):
    return L[u][b][rn][arm]["opened"][0]


def d(L, u, b, rn, a1, a2, e="r_in"):
    return round(lv(L, u, b, rn, a1, e) - lv(L, u, b, rn, a2, e), 4)


def mean(xs):
    xs = list(xs)
    return round(sum(xs) / len(xs), 4)


def score(L):
    S = {}
    v8 = {f"{u}/{b}/{m}": d(L, u, b, f"change8{HI}", m, "inst-3") for u, b in ALL for m in MAT}
    v4 = {f"{u}/{b}/{m}": d(L, u, b, f"change4{HI}", m, "inst-3") for u, b in ALL for m in MAT}
    ok = min(v8.values()) >= 0.10 and min(v4.values()) >= 0.035 and mean(v4.values()) >= 0.10
    S["C1"] = {"verdict": "HOLDS" if ok else "FAILS", "change8_mat_minus_inst-3": v8, "change4_mat_minus_inst-3": v4,
               "change4_mean": mean(v4.values())}

    c4 = {f"{u}/{b}": round(lv(L, u, b, f"change4{HI}", "mat-300") - lv(L, u, b, f"change4{LO}", "mat-1000"), 4) for u, b in ALL}
    cue = {f"{u}/{b}": round(lv(L, u, b, f"cue8{HI}", "mat-300", "r_all") - lv(L, u, b, f"cue8{LO}", "mat-1000", "r_all"), 4)
           for u, b in ALL}
    c8 = {f"{u}/{b}": round(lv(L, u, b, f"change8{HI}", "mat-300") - lv(L, u, b, f"change8{LO}", "mat-1000"), 4) for u, b in ALL}
    ok = mean(c4.values()) >= 0.06 and max(cue.values()) <= -0.04
    S["C2"] = {"verdict": "HOLDS" if ok else "FAILS", "change4_fast_minus_slow": c4, "change4_mean": mean(c4.values()),
               "cue_r_all_fast_minus_slow": cue, "reported_change8_fast_minus_slow": c8,
               "reported_change8_mean": mean(c8.values())}

    v = {}
    ok = True
    for mu in (HI, LO):
        c = {f"{u}/{b}": d(L, u, b, f"change8{mu}", "mat-1000", "mat-300") for u, b in ALL}
        n = {f"{u}/{b}": d(L, u, b, f"none8{mu}", "mat-1000", "mat-300", "r_all") for u, b in ALL}
        v[mu] = {"change8": c, "change8_mean": mean(c.values()), "none_r_all": n}
        ok &= mean(c.values()) >= 0.02 and max(abs(x) for x in n.values()) <= 0.003
    S["C3"] = {"verdict": "HOLDS" if ok else "FAILS", "mat-1000_minus_mat-300": v}

    v = {}
    ok = True
    for u, b in ALL:
        for m in MAT:
            hi, lo = d(L, u, b, f"cue8{HI}", m, "inst-3", "r_all"), d(L, u, b, f"cue8{LO}", m, "inst-3", "r_all")
            v[f"{u}/{b}/{m}"] = {"mu1e-3": hi, "mu2.5e-4": lo, "difference": round(hi - lo, 4)}
            ok &= hi <= -0.025 and lo <= -0.012 and hi - lo <= -0.003
    S["C4"] = {"verdict": "HOLDS" if ok else "FAILS", "mat_minus_inst-3_r_all": v}

    v = {f"{u}/{b}/{m}": d(L, u, b, f"none8{HI}", m, "inst-3", "r_all") for u, b in ALL for m in MAT}
    ok = all(x >= 0.003 for x in v.values()) and all(x >= 0.015 for k, x in v.items() if k.startswith("S4"))
    S["C5"] = {"verdict": "HOLDS" if ok else "FAILS", "mat_minus_inst-3_r_all": v}

    v = {f"{u}/{b}": {"change8": d(L, u, b, f"change8{HI}", "mat-1000", "inst-1.5"),
                      "cue_r_all": d(L, u, b, f"cue8{HI}", "mat-1000", "inst-1.5", "r_all")} for u, b in ALL}
    ok = all(abs(x["change8"]) <= 0.06 and x["cue_r_all"] <= 0.01 for x in v.values())
    S["C6"] = {"verdict": "HOLDS" if ok else "FAILS", "mat-1000_minus_inst-1.5": v}

    v = {f"{u}/{b}/{m}": {"minus_inst-3": d(L, u, b, "regrow8@0", m, "inst-3"),
                          "minus_inst-1.5": d(L, u, b, "regrow8@0", m, "inst-1.5"),
                          "r_out_minus_inst-3": d(L, u, b, "regrow8@0", m, "inst-3", "r_out")} for u, b in ALL for m in MAT}
    f0 = mean(x["minus_inst-3"] for k, x in v.items() if k.startswith("F0"))
    ok = all(x["minus_inst-3"] >= 0.02 for k, x in v.items() if k.startswith("S4")) and f0 > 0 \
        and all(x["minus_inst-1.5"] >= -0.03 and abs(x["r_out_minus_inst-3"]) <= 0.002 for x in v.values())
    S["C7"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v, "F0_mean_minus_inst-3": f0}

    v = {f"{u}/{b}": {a: d(L, u, b, "regrow+cue8@0", a, "inst-3", "r_out") for a in ("inst-1.5", *MAT)} for u, b in ALL}
    ok = all(x["inst-1.5"] <= -0.02 and all(abs(x[m]) <= 0.002 for m in MAT) for x in v.values())
    S["C8"] = {"verdict": "HOLDS" if ok else "FAILS", "r_out_minus_inst-3": v}

    v = {f"{u}/{b}/{m}": round(d(L, u, b, "regrow8@0", m, "inst-3") - d(L, u, b, "regrow+cue8@0", m, "inst-3"), 4)
         for u, b in ALL for m in MAT}
    S["C9"] = {"verdict": "HOLDS" if mean(v.values()) >= 0.02 else "FAILS", "advantage_shrink": v,
               "mean": mean(v.values())}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
