"""BE009's registered statements and their scoring, written before any development outcome.

python -m be009.predict   (writes be009/frozen/predictions.json)

Thresholds were set from engineering probe P37 (32 cases on blocks 900548-900551 under tag mse-p37, disclosed in
REGISTRATION_BE009.md) under BE002's rule, with the block SD taken as the larger of two (the lead's review): SD_block =
max(the SD over P37's four blocks of the pooled per-block value, the SD over P37's 32 cases of the pair-pooled per-case
value / sqrt 8). The twelve unit-body pairs share a block's 8 execution draws, so a block value carries the binomial
noise of 8 draws, which four blocks can understate (P37's blocks drew 6, 6, 7 and 6 cases unexecuted at 9 h).
probes/p37b_be009_margins.py prints every part, both SDs and the margin under the larger. Every part is pooled over the
twelve unit-body pairs (the mean over them, scored on unrounded block means); a part needs >= 3 x sqrt(1/4 + 1/16) = 1.68
SD_block between P37's value and its threshold; where both SDs are 0 the bound is derived, not taken from the probe.
Scored by be009.analyze on the 16 development blocks; a statement HOLDS when every one of its parts passes.

Quantities (r_in: the patch's record against the target; clock c in SL, C12, CASE, CELL; D = 900, 1,800, 2,700, 3,600,
4,500, 5,400, 7,200 updates (3, 6, 9, 12, 15, 18, 24 h at 300 updates an hour); every late signal read at D + 4,000):
  prompt(c, t)   dial-c's r_in in memory4@0 at read t (the signal at 1-1,000)
  none(c, t)     never-c's r_in in memory4@0 at read t (the same tissue, the signal never on)
  late(c, D)     dial-c's r_in in memory4@D at D + 4,000
  gain(c, D)     late(c, D) - none(c, D + 4,000): a late signal's worth over no signal, at the same time;
                 gain(c, 0) = prompt(c, 4,000) - none(c, 4,000), the prompt signal's
  R(c, D)        gain(c, D) / gain(c, 0), the remaining effect; a part 'R(c, D) >= x' is scored as gain(c, D) -
                 x gain(c, 0) >= 0 on the pooled gains (and 'R <= x' as x gain(c, 0) - gain(c, D) >= 0)
  dev_case(D)    gain(CASE, D) less its case-matched all-or-none value, the mean over cases of [the case's tau_x >= D + 2]
                 x the case's gain(SL, D) (be009.analyze.derived)
  dev_cell(D)    gain(CELL, D) less its case-matched proportional value, the mean over cases of the share of the case's
                 patch cells with tau_x >= D + 2 x the case's gain(SL, D)
Derived bounds (P37's SD is 0 in these parts; the bound is set by the construction, not the probe):
  G1 closed (C12 at D >= 3,600): at 3,600 every footprint cell with a confident record and no commitment is committed
      to its record's sign before the signal starts, and a later trigger cannot flip a committed cell (BE001's rule), so
      the signal can change only the patch's cells with no confident record at 3,600 (BE007: E2 at 0.05); 0.05 sits far
      above that.
Reported, not registered (be009.analyze's reported.json, with 95% t intervals over blocks): dev_case(D) and dev_cell(D)
at every delay (dev_cell(2,700) was the draft's G7); rep(c, D) for every clock and delay and rep(CELL, D) - rep(CASE, D)
(the draft's G8); gain(C12, 2,700) - gain(CASE, 2,700) (G6's CASE part); gain(C12, 2,700) - gain(SL, 2,700) (the signal
still on at C12's execution).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be009 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
A = D.AFTER
OPEN = tuple(d for d in D.DELAYS if d + D.SIG["duration"] < D.TX_MEDIAN)   # 900, 1,800: the signal ends before C12's execution
CLOSED = tuple(d for d in D.DELAYS if d >= D.TX_MEDIAN)              # 3,600, 4,500, 5,400, 7,200
SPREAD = D.SPREAD
THR = {"G1": {"kept": -0.02, "closed": 0.05},
       "G2": {"mixture": 0.05},
       "G3": {"proportional": 0.07},
       "G4": {"lo": 0.05, "hi": 0.65},
       "G5": {"full": 0.9, "early": 0.75, "late": 0.1},
       "G6": {"earlier": 0.03}}
RUNS = {D.run_name(*x): x for x in D.RUNS}
MEM0 = D.run_name("memory", 4, 0)


def lv(L, u, b, rn, arm, t, e="r_in"):
    return L[u][b][rn][arm][e][D.run_reads(*RUNS[rn]).index(t)][0]


def prompt(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"dial-{c}", t)


def none(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"never-{c}", t)


def late(L, u, b, c, d):
    rn, arm = D.where(c, d)
    return lv(L, u, b, rn, arm, d + A)


def gain(L, u, b, c, d):
    if d == 0:
        return prompt(L, u, b, c, A) - none(L, u, b, c, A)
    return late(L, u, b, c, d) - none(L, u, b, c, d + A)


def dev(L, u, b, kind, d):
    return L[u][b]["_derived"][f"dev_{kind}"][str(d)][0]


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


T = THR
PARTS = [
    *[part("G1", f"G1 gain(C12, {d}) - gain(SL, {d}) (pooled)", ALL, T["G1"]["kept"], "ge", True,
           (lambda d_: lambda L, u, b: gain(L, u, b, "C12", d_) - gain(L, u, b, "SL", d_))(d)) for d in OPEN],
    *[part("G1", f"G1 gain(C12, {d}) (pooled)", ALL, T["G1"]["closed"], "le", True,
           (lambda d_: lambda L, u, b: gain(L, u, b, "C12", d_))(d)) for d in CLOSED],
    *[part("G2", f"G2 dev_case({d}) (pooled)", ALL, T["G2"]["mixture"], "abs", True,
           (lambda d_: lambda L, u, b: dev(L, u, b, "case", d_))(d)) for d in D.DELAYS],
    *[part("G3", f"G3 dev_cell({d}) (pooled)", ALL, T["G3"]["proportional"], "abs", True,
           (lambda d_: lambda L, u, b: dev(L, u, b, "cell", d_))(d)) for d in D.DELAYS],
    *[part("G4", f"G4 gain({c}, 3600) - {T['G4']['lo']} gain({c}, 0) (pooled)", ALL, 0.0, "ge", True,
           (lambda c_: lambda L, u, b: gain(L, u, b, c_, 3600) - T["G4"]["lo"] * gain(L, u, b, c_, 0))(c)) for c in SPREAD],
    *[part("G4", f"G4 {T['G4']['hi']} gain({c}, 0) - gain({c}, 3600) (pooled)", ALL, 0.0, "ge", True,
           (lambda c_: lambda L, u, b: T["G4"]["hi"] * gain(L, u, b, c_, 0) - gain(L, u, b, c_, 3600))(c)) for c in SPREAD],
    *[part("G5", f"G5 gain({c}, 900) - {T['G5']['full']} gain({c}, 0) (pooled)", ALL, 0.0, "ge", True,
           (lambda c_: lambda L, u, b: gain(L, u, b, c_, 900) - T["G5"]["full"] * gain(L, u, b, c_, 0))(c)) for c in SPREAD],
    *[part("G5", f"G5 gain({c}, 1800) - {T['G5']['early']} gain({c}, 0) (pooled)", ALL, 0.0, "ge", True,
           (lambda c_: lambda L, u, b: gain(L, u, b, c_, 1800) - T["G5"]["early"] * gain(L, u, b, c_, 0))(c)) for c in SPREAD],
    *[part("G5", f"G5 {T['G5']['late']} gain({c}, 0) - gain({c}, 7200) (pooled)", ALL, 0.0, "ge", True,
           (lambda c_: lambda L, u, b: T["G5"]["late"] * gain(L, u, b, c_, 0) - gain(L, u, b, c_, 7200))(c)) for c in SPREAD],
    part("G6", "G6 gain(C12, 2700) - gain(CELL, 2700) (pooled)", ALL, T["G6"]["earlier"], "ge", True,
         lambda L, u, b: gain(L, u, b, "C12", 2700) - gain(L, u, b, "CELL", 2700)),
]
CLAIM = {
    "G1": ("one execution time still closes the window as a step",
           "With every case and cell executing at 12 h (BE007's C12), a late signal 3 or 6 h after a 4 x 4 memory "
           "damage (ending before the execution) is worth at most {kept_abs} less over no signal than with no execution, and one 12, 15, 18 or 24 h late is "
           "worth at most {closed} over no signal, on average",
           "HOLDS if on average over the twelve unit-body pairs, gain(C12, D) - gain(SL, D) >= {kept} at D = 900 and "
           "1,800, and gain(C12, D) <= {closed} at D = 3,600, 4,500, 5,400 and 7,200, where gain(c, D) is dial-c's "
           "r_in in memory4@D at D + 4,000 less never-c's r_in in memory4@0 at the same read, else FAILS"),
    "G2": ("spread between cases gives the mixture of all-or-none cases",
           "With each case executing at its own drawn time, a late signal's worth at every delay from 3 to 24 h equals, "
           "within {mixture}, the mean over cases of the case's worth with no execution if the case has not yet executed "
           "when the signal starts and of nothing if it has, on average",
           "HOLDS if on average over the twelve unit-body pairs, |gain(CASE, D) - pred_case(D)| <= {mixture} at every D, "
           "where pred_case(D) is the mean over cases of [the case's tau_x >= D + 2] x the case's gain(SL, D), else FAILS"),
    "G3": ("spread between cells gives a decline in proportion to the cells not yet executed",
           "With each footprint cell executing at its own drawn time, a late signal's worth at every delay from 3 to 24 h "
           "equals, within {proportional}, the mean over cases of the share of the case's patch cells not yet executed when the "
           "signal starts times the case's worth with no execution, on average",
           "HOLDS if on average over the twelve unit-body pairs, |gain(CELL, D) - pred_cell(D)| <= {proportional} at every "
           "D, where pred_cell(D) is the mean over cases of the share of the case's patch cells with tau_x >= D + 2 x the "
           "case's gain(SL, D), else FAILS"),
    "G4": ("with spread, part of the effect remains at 12 h",
           "With execution times spread between cases or between cells around 12 h, a signal 12 h after the damage keeps "
           "between {lo_pct} % and {hi_pct} % of the prompt signal's worth, on average (one execution time at 12 h keeps none, "
           "G1; the planarian landmark, octanol keeping under 60 % of its effect after 12 h, is compared in the report, "
           "not registered)",
           "HOLDS if on average over the twelve unit-body pairs, gain(c, 3,600) >= {lo} gain(c, 0) and gain(c, 3,600) <= "
           "{hi} gain(c, 0) for c = CASE and CELL, where gain(c, 0) is dial-c's r_in less never-c's in memory4@0 at "
           "4,000, else FAILS"),
    "G5": ("with spread, the effect is full early and gone late",
           "With execution times spread between cases or between cells, a signal 3 h after the damage keeps at least "
           "{full_pct} % of the prompt signal's worth, one 6 h after at least {early_pct} % and one 24 h after at most "
           "{late_pct} %, on average (planarian octanol works best within 3-6 h and not at all later)",
           "HOLDS if on average over the twelve unit-body pairs, gain(c, 900) >= {full} gain(c, 0), gain(c, 1,800) >= "
           "{early} gain(c, 0) and gain(c, 7,200) <= {late} gain(c, 0) for c = CASE and CELL, else FAILS"),
    "G6": ("with spread between cells, the decline begins before the median execution time",
           "A signal 9 h after the damage is worth at least {earlier} less over no signal with execution times spread between "
           "cells than with every case and cell executing at 12 h, on average",
           "HOLDS if on average over the twelve unit-body pairs, gain(C12, 2,700) - gain(CELL, 2,700) >= {earlier}, else "
           "FAILS"),
}
WORDS = {"G1": {"kept_abs": -THR["G1"]["kept"]}, "G4": {"lo_pct": round(100 * THR["G4"]["lo"]), "hi_pct": round(100 * THR["G4"]["hi"])},
         "G5": {"full_pct": round(100 * THR["G5"]["full"]), "early_pct": round(100 * THR["G5"]["early"]),
                "late_pct": round(100 * THR["G5"]["late"])}}
STATEMENTS = [{"id": k, "kind": v[0], "claim": v[1].format(**THR[k], **WORDS.get(k, {})), "rule": v[2].format(**THR[k]),
               "thresholds": THR[k]} for k, v in CLAIM.items()]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def passes(x, threshold, sense):
    return {"ge": x >= threshold, "le": x <= threshold, "abs": abs(x) <= threshold}[sense]


def score(L):
    S = {}
    for s in STATEMENTS:
        out, ok = {}, True
        for p in (q for q in PARTS if q["stmt"] == s["id"]):
            vals = {"/".join(map(str, it)): p["value"](L, *it) for it in p["items"]}
            if p["pooled"]:
                x = mean(vals.values())
                good = passes(x, p["threshold"], p["sense"])
                out[p["name"]] = {"pooled": x, "pass": good, "items": vals}
            else:
                good = all(passes(x, p["threshold"], p["sense"]) for x in vals.values())
                out[p["name"]] = {"pass": good, "items": vals}
            ok &= good
        S[s["id"]] = {"verdict": "HOLDS" if ok else "FAILS", "parts": out}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": THR,
                               "parts": [{k: v for k, v in p.items() if k != "value"} for p in PARTS],
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
