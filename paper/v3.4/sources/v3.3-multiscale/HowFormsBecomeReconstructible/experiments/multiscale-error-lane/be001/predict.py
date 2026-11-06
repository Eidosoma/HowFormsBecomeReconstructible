"""BE001's registered statements and their scoring, written before any development outcome.

python -m be001.predict   (writes be001/frozen/predictions.json)

Thresholds were set from engineering probe P23 (32 cases on blocks 900790-900793 under tag mse-p23, disclosed in
REGISTRATION_BE001.md), with margins for 128 cases. Scored by be001.analyze on block means over the 16 development
blocks at t = 4,000. r_in: the record's agreement with the correct target inside the patch (for change, the new
target); r_all: over the sheet; opened: the share of cells committed over the window. Runs are named situation + patch
side (change8 = a legitimate change of an 8 x 8 patch).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
LADDER = ("bio-1", "bio-1.5", "bio-2", "bio-3")
QUIET_BIO = tuple(a for a in D.BIO if a != "bio-2-noisy")

STATEMENTS = [
    {"id": "E1", "kind": "the useful correction survives a bioelectric implementation",
     "claim": "A cable detector with a matched coupling length and a slowly decaying commitment state repairs memory damage "
              "and adopts a legitimate change as well as LR005's abstract community rule",
     "rule": "HOLDS if for change8 and memory8, bio-1.5's r_in is >= 0.65 and within 0.07 of community-s's in every unit "
             "for both bodies, else FAILS",
     "inputs": "P23: bio-1.5 0.712-0.738; bio-1.5 - community-s -0.039 to +0.003"},
    {"id": "E2", "kind": "the cable detector raises fewer false alarms",
     "claim": "At matched coupling, the bioelectric detector loses less of the record than the window count under "
              "scattered cue corruption",
     "rule": "HOLDS if under cue damage bio-1.5's r_all exceeds community-s's by >= 0.02 in every unit for both bodies, "
             "else FAILS",
     "inputs": "P23: +0.038 to +0.045"},
    {"id": "E3", "kind": "coupling sets a minimum group size",
     "claim": "The coupling length sets the smallest group that can be re-specified: short coupling adopts a 4 x 4 change, "
              "long coupling does not, while both adopt a 12 x 12 change",
     "rule": "HOLDS if in every unit for both bodies bio-1's r_in for change4 is >= 0.50, bio-3's r_in for change4 is at "
             "most 0.03 above the cue arm's, and bio-3's r_in for change12 is >= 0.55, else FAILS",
     "inputs": "P23: 0.576-0.600; +0.000; 0.630-0.648"},
    {"id": "E4", "kind": "coupling sets the false-alarm rate",
     "claim": "Under scattered cue corruption the record's loss falls monotonically with the coupling length, from clear "
              "losses at short coupling to none at long coupling",
     "rule": "HOLDS if under cue damage, in every unit for both bodies, r_all rises strictly along bio-1 < bio-1.5 < bio-2 < "
             "bio-3, bio-1's r_all is <= the cue arm's - 0.04 and bio-3's is >= the cue arm's - 0.005, else FAILS",
     "inputs": "P23: strict everywhere (steps >= 0.009); bio-1 -0.093 to -0.066; bio-3 -0.001 to 0.000"},
    {"id": "E5", "kind": "gated junctions shorten coupling where cells disagree",
     "claim": "Voltage-gated gap junctions raise adoption and false alarms together, as if coupling were shorter where "
              "cells disagree",
     "rule": "HOLDS if in every unit for both bodies bio-2-gated's r_in for change8 exceeds bio-2's by >= 0.12 and its "
             "r_all under cue damage is <= bio-2's - 0.03, else FAILS",
     "inputs": "P23: +0.196 to +0.213; -0.070 to -0.050"},
    {"id": "E6", "kind": "channel noise sensitises and causes spontaneous re-specification",
     "claim": "Channel noise raises adoption of a legitimate change but commits cells with no event at all",
     "rule": "HOLDS if in every unit for both bodies bio-2-noisy's r_in for change8 exceeds bio-2's by >= 0.15, and with no "
             "event bio-2-noisy commits >= 0.004 of cells while every other bioelectric arm commits <= 0.002, and its r_all "
             "is <= bio-2's - 0.015, else FAILS",
     "inputs": "P23: +0.244 to +0.259; 0.0087-0.0091 against <= 0.0005; -0.032 to -0.030"},
    {"id": "E7", "kind": "a higher threshold buys back false alarms at the cost of adoption",
     "claim": "A cautious threshold at matched coupling refuses scattered corruption but adopts only part of an 8 x 8 change "
              "and most of a 12 x 12 one",
     "rule": "HOLDS if in every unit for both bodies bio-1.5-cautious's r_all under cue damage is >= the cue arm's - 0.015, "
             "its r_in for change8 is <= 0.45 and for change12 >= 0.50, else FAILS",
     "inputs": "P23: -0.006 to -0.003; 0.358-0.394; 0.564-0.584"},
    {"id": "E8", "kind": "no detector acts inside a wound that removes its cues",
     "claim": "Inside a killed patch, where the anchors and the record's confident signs are gone, every noiseless "
              "bioelectric arm repairs exactly as the cue arbiter does",
     "rule": "HOLDS if under shared damage every bioelectric arm except bio-2-noisy has r_in within 0.02 of the cue arm's "
             "in every unit for both bodies, else FAILS",
     "inputs": "P23: at most 0.001 apart"},
]


def lv(L, u, b, rn, arm, e="r_in"):
    return L[u][b][rn][arm][e][-1][0]


def op(L, u, b, rn, arm):
    return L[u][b][rn][arm]["opened"][0]


def score(L):
    S = {}
    v = {f"{u}/{b}/{rn}": {"bio-1.5": lv(L, u, b, rn, "bio-1.5"), "diff": round(lv(L, u, b, rn, "bio-1.5") - lv(L, u, b, rn, "community-s"), 4)}
         for u, b in ALL for rn in ("change8", "memory8")}
    ok = all(x["bio-1.5"] >= 0.65 and abs(x["diff"]) <= 0.07 for x in v.values())
    S["E1"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    v = {f"{u}/{b}": round(lv(L, u, b, "cue8", "bio-1.5", "r_all") - lv(L, u, b, "cue8", "community-s", "r_all"), 4) for u, b in ALL}
    S["E2"] = {"verdict": "HOLDS" if min(v.values()) >= 0.02 else "FAILS", "bio-1.5_minus_community-s": v}

    v = {f"{u}/{b}": {"bio-1@change4": lv(L, u, b, "change4", "bio-1"),
                      "bio-3_minus_cue@change4": round(lv(L, u, b, "change4", "bio-3") - lv(L, u, b, "change4", "cue"), 4),
                      "bio-3@change12": lv(L, u, b, "change12", "bio-3")} for u, b in ALL}
    ok = all(x["bio-1@change4"] >= 0.50 and x["bio-3_minus_cue@change4"] <= 0.03 and x["bio-3@change12"] >= 0.55 for x in v.values())
    S["E3"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    v = {}
    ok = True
    for u, b in ALL:
        r = [lv(L, u, b, "cue8", a, "r_all") for a in LADDER]
        c = lv(L, u, b, "cue8", "cue", "r_all")
        v[f"{u}/{b}"] = {"ladder": r, "cue": c}
        ok &= all(r[i] < r[i + 1] for i in range(3)) and r[0] <= c - 0.04 and r[-1] >= c - 0.005
    S["E4"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    v = {f"{u}/{b}": {"change8": round(lv(L, u, b, "change8", "bio-2-gated") - lv(L, u, b, "change8", "bio-2"), 4),
                      "cue_r_all": round(lv(L, u, b, "cue8", "bio-2-gated", "r_all") - lv(L, u, b, "cue8", "bio-2", "r_all"), 4)}
         for u, b in ALL}
    ok = all(x["change8"] >= 0.12 and x["cue_r_all"] <= -0.03 for x in v.values())
    S["E5"] = {"verdict": "HOLDS" if ok else "FAILS", "gated_minus_bio-2": v}

    v = {f"{u}/{b}": {"change8": round(lv(L, u, b, "change8", "bio-2-noisy") - lv(L, u, b, "change8", "bio-2"), 4),
                      "opened_none": op(L, u, b, "none8", "bio-2-noisy"),
                      "max_other_opened_none": max(op(L, u, b, "none8", a) for a in QUIET_BIO),
                      "none_r_all": round(lv(L, u, b, "none8", "bio-2-noisy", "r_all") - lv(L, u, b, "none8", "bio-2", "r_all"), 4)}
         for u, b in ALL}
    ok = all(x["change8"] >= 0.15 and x["opened_none"] >= 0.004 and x["max_other_opened_none"] <= 0.002
             and x["none_r_all"] <= -0.015 for x in v.values())
    S["E6"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    v = {f"{u}/{b}": {"cue_r_all": round(lv(L, u, b, "cue8", "bio-1.5-cautious", "r_all") - lv(L, u, b, "cue8", "cue", "r_all"), 4),
                      "change8": lv(L, u, b, "change8", "bio-1.5-cautious"),
                      "change12": lv(L, u, b, "change12", "bio-1.5-cautious")} for u, b in ALL}
    ok = all(x["cue_r_all"] >= -0.015 and x["change8"] <= 0.45 and x["change12"] >= 0.50 for x in v.values())
    S["E7"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    v = {f"{u}/{b}": round(max(abs(lv(L, u, b, "shared8", a) - lv(L, u, b, "shared8", "cue")) for a in QUIET_BIO), 4) for u, b in ALL}
    S["E8"] = {"verdict": "HOLDS" if max(v.values()) <= 0.02 else "FAILS", "max_abs_bio_minus_cue": v}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
