"""BE006's registered statements and their scoring, written before any development outcome.

python -m be006.predict   (writes be006/frozen/predictions.json)

Thresholds were set from engineering probe P33 (32 cases on blocks 900540-900543 under tag mse-p33, disclosed in
REGISTRATION_BE006.md) under BE002's rule; probes/p33b_be006_margins.py prints every part, its SD over P33's four blocks
and the margin at these thresholds. Every part is pooled over the twelve unit-body pairs (the mean over them, scored on
unrounded block means), and its margin uses the SD over P33's four blocks of the pooled per-block value. A part needs
>= 3 x sqrt(1/4 + 1/16) = 1.68 SDs between P33's value and its threshold; where P33's SD is 0 the bound is derived, not
taken from the probe. Scored by be006.analyze on the 16 development blocks; a statement HOLDS when every one of its
parts passes.

Quantities (r_in: the patch's record against the target, the new one in a change; clock c in F, A, AL, S, SL):
  prompt(c, t)     dial-c's r_in in memory4@0 at read t (the signal at 1-1,000)
  late(c, m, t)    dial-c's r_in in memory4@D at read t, D = round(m T*(eta_a(c))), T*(eta) = ln(1.8) / -ln(1 - eta)
  none(c, t)       never-c's r_in in memory4@0 at read t (the same tissue, the signal never on)
  loss(c, m)       prompt(c, t) - late(c, m, t) at the clock's scoring read t: 4,000 for F (BE005's), 8,000 for the
                   calibrated clocks, 12,000 at m = 4
  sensors(c, m)    the share of the patch's anchored cells whose record is right at the delayed signal's first update
                   (per block: right over all)
  adopt(c)         dial-c's r_in in change4@0 at 8,000
  cost(c)          never-c's r_all less dial-c's in cue4@0 at 8,000 (a prompt sham's cost to the sheet)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be006 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
TS, TF, T4 = D.T_SCORE["slow"], D.T_SCORE["F"], D.T_SCORE["m4"]
THR = {"K1": {"early": 0.02, "late": 0.05, "late4": 0.05, "elapsed": 0.05, "elapsed4": 0.05},
       "K2": {"early": 0.02, "late": 0.05},
       "K3": {"intact": 0.05, "repaired": 0.15},
       "K4": {"sensors": 0.1, "loss": 0.03},
       "K5": {"gain": 0.2},
       "K6": {"carry": 0.1},
       "K7": {"more": 0.1},
       "K8": {"none": 0.05},
       "K9": {"sham": 0.001},
       "K10": {"repair": 0.02, "adopt": 0.05}}


def lv(L, u, b, rn, arm, t, e="r_in"):
    return L[u][b][rn][arm][e][D.run_reads(*RUNS[rn]).index(t)][0]


def sc(L, u, b, rn, arm, e):
    return L[u][b][rn][arm][e][0]


RUNS = {D.run_name(*x): x for x in D.RUNS}
MEM0 = D.run_name("memory", 4, 0)
CHG = D.run_name("change", 4, 0)
CUE = D.run_name("cue", 4, 0)


def tscore(c, m=0):
    return TF if c == "F" else (T4 if m == 4 else TS)


def prompt(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"dial-{c}", t)


def late(L, u, b, c, m, t):
    rn, arm = D.where(c, m)
    return lv(L, u, b, rn, arm, t)


def none(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"never-{c}", t)


def loss(L, u, b, c, m):
    t = tscore(c, m)
    return prompt(L, u, b, c, t) - late(L, u, b, c, m, t)


def sensors(L, u, b, c, m):
    rn, arm = D.where(c, m)
    return sc(L, u, b, rn, arm, "anc_on_share")


def adopt(L, u, b, c):
    return lv(L, u, b, CHG, f"dial-{c}", TS)


def cost(L, u, b, c):
    return lv(L, u, b, CUE, f"never-{c}", TS, "r_all") - lv(L, u, b, CUE, f"dial-{c}", TS, "r_all")


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


T = THR
PARTS = [
    *[part("K1", f"K1 prompt(SL) - late(SL, {m}) at {TS} (pooled)", ALL, T["K1"]["early"], "le", True,
           (lambda m_: lambda L, u, b: loss(L, u, b, "SL", m_))(m)) for m in (0.5, 1)],
    part("K1", f"K1 prompt(SL) - late(SL, 2) at {TS} (pooled)", ALL, T["K1"]["late"], "ge", True,
         lambda L, u, b: loss(L, u, b, "SL", 2)),
    part("K1", f"K1 prompt(SL) - late(SL, 4) at {T4} (pooled)", ALL, T["K1"]["late4"], "ge", True,
         lambda L, u, b: loss(L, u, b, "SL", 4)),
    part("K1", f"K1 prompt(SL) at {TF} - late(SL, 2) at {TS}, equal elapsed time (pooled)", ALL, T["K1"]["elapsed"], "ge", True,
         lambda L, u, b: prompt(L, u, b, "SL", TF) - late(L, u, b, "SL", 2, TS)),
    part("K1", f"K1 prompt(SL) at {TF} - late(SL, 4) at {T4}, equal elapsed time (pooled)", ALL, T["K1"]["elapsed4"], "ge", True,
         lambda L, u, b: prompt(L, u, b, "SL", TF) - late(L, u, b, "SL", 4, T4)),
    *[part("K2", f"K2 late(F, {m}) - prompt(F) at {TF} (pooled)", ALL, T["K2"]["early"], "abs", True,
           (lambda m_: lambda L, u, b: -loss(L, u, b, "F", m_))(m)) for m in (0.5, 1)],
    *[part("K2", f"K2 prompt(F) - late(F, {m}) at {TF} (pooled)", ALL, T["K2"]["late"], "ge", True,
           (lambda m_: lambda L, u, b: loss(L, u, b, "F", m_))(m)) for m in (2, 4)],
    *[part("K3", f"K3 sensors(SL, {m}) (pooled)", ALL, T["K3"]["intact"], "le", True,
           (lambda m_: lambda L, u, b: sensors(L, u, b, "SL", m_))(m)) for m in (0.5, 1)],
    part("K3", "K3 sensors(SL, 2) (pooled)", ALL, T["K3"]["repaired"], "ge", True,
         lambda L, u, b: sensors(L, u, b, "SL", 2)),
    part("K4", "K4 sensors(A, 1) - sensors(SL, 1) (pooled)", ALL, T["K4"]["sensors"], "ge", True,
         lambda L, u, b: sensors(L, u, b, "A", 1) - sensors(L, u, b, "SL", 1)),
    part("K4", f"K4 loss(A, 1) - loss(SL, 1) at {TS} (pooled)", ALL, T["K4"]["loss"], "ge", True,
         lambda L, u, b: loss(L, u, b, "A", 1) - loss(L, u, b, "SL", 1)),
    *[part("K5", f"K5 prompt({c}) - none({c}) at {TS} (pooled)", ALL, T["K5"]["gain"], "ge", True,
           (lambda c_: lambda L, u, b: prompt(L, u, b, c_, TS) - none(L, u, b, c_, TS))(c)) for c in ("A", "SL")],
    part("K6", f"K6 prompt(SL) - prompt(S) at {TS} (pooled)", ALL, T["K6"]["carry"], "ge", True,
         lambda L, u, b: prompt(L, u, b, "SL", TS) - prompt(L, u, b, "S", TS)),
    part("K6", f"K6 adopt(SL) - adopt(S) at {TS} (pooled)", ALL, T["K6"]["carry"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "SL") - adopt(L, u, b, "S")),
    part("K7", f"K7 (prompt(SL) - prompt(S)) - (prompt(AL) - prompt(A)) at {TS} (pooled)", ALL, T["K7"]["more"], "ge", True,
         lambda L, u, b: (prompt(L, u, b, "SL", TS) - prompt(L, u, b, "S", TS)) - (prompt(L, u, b, "AL", TS) - prompt(L, u, b, "A", TS))),
    part("K7", f"K7 (adopt(SL) - adopt(S)) - (adopt(AL) - adopt(A)) at {TS} (pooled)", ALL, T["K7"]["more"], "ge", True,
         lambda L, u, b: (adopt(L, u, b, "SL") - adopt(L, u, b, "S")) - (adopt(L, u, b, "AL") - adopt(L, u, b, "A"))),
    part("K8", f"K8 prompt(S) - none(S) at {TS} (pooled)", ALL, T["K8"]["none"], "abs", True,
         lambda L, u, b: prompt(L, u, b, "S", TS) - none(L, u, b, "S", TS)),
    part("K8", f"K8 adopt(S) - adopt(never-S) at {TS} (pooled)", ALL, T["K8"]["none"], "abs", True,
         lambda L, u, b: adopt(L, u, b, "S") - lv(L, u, b, CHG, "never-S", TS)),
    part("K9", f"K9 cost(AL) - cost(A) at {TS} (pooled)", ALL, T["K9"]["sham"], "ge", True,
         lambda L, u, b: cost(L, u, b, "AL") - cost(L, u, b, "A")),
    part("K9", f"K9 cost(SL) - cost(S) at {TS} (pooled)", ALL, T["K9"]["sham"], "ge", True,
         lambda L, u, b: cost(L, u, b, "SL") - cost(L, u, b, "S")),
    part("K10", f"K10 prompt(AL) - prompt(A) at {TS} (pooled)", ALL, T["K10"]["repair"], "ge", True,
         lambda L, u, b: prompt(L, u, b, "AL", TS) - prompt(L, u, b, "A", TS)),
    part("K10", f"K10 adopt(AL) - adopt(A) at {TS} (pooled)", ALL, T["K10"]["adopt"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "AL") - adopt(L, u, b, "A")),
]

CLAIM = {
    "K1": ("with the whole clock calibrated, the deadline is the arbiter's clock, in hours",
           "With every bond relearning at the calibrated pace (T* = 1,959 updates, 6.5 h at 300 updates an hour) and a "
           "commitment of 15,000 updates, a signal that arrives half of T* or T* after a 4 x 4 memory damage repairs it no "
           "more than 0.02 below a prompt one, and one that arrives 2 or 4 times T* after it repairs it less than a prompt "
           "one, read at the same time and at equal elapsed time since each signal's start, on average",
           "HOLDS if on average over the twelve unit-body pairs, dial-SL's r_in in memory4@round(m T*(3e-4)) is no more "
           "than {early} below its r_in in memory4@0 for m = 0.5 and 1 (both at t = 8,000), below it by >= {late} for "
           "m = 2 (t = 8,000) and by >= {late4} for m = 4 (t = 12,000); and, at equal elapsed time since each signal's "
           "start, dial-SL's r_in in memory4@round(2 T*) at t = 8,000 and in memory4@round(4 T*) at t = 12,000 are below "
           "its r_in in memory4@0 at t = 4,000 by >= {elapsed} and >= {elapsed4}, else FAILS"),
    "K2": ("at the lane's rate the deadline is BE005's (the bridge)",
           "With the arbiter at the lane's 0.01 (BE005's dial-e0.01), a signal half of T* or T* late repairs within 0.02 of "
           "a prompt one, and one 2 or 4 times T* late repairs less by at least 0.05, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-F's r_in in memory4@round(m T*(0.01)) "
           "is within {early} of its r_in in memory4@0 for m = 0.5 and 1, and below it by >= {late} for m = 2 and 4, "
           "else FAILS"),
    "K3": ("with the whole clock calibrated, the sensors keep the arbiter's clock",
           "When a delayed signal arrives under the fully calibrated clock, at most 5 per cent of the damaged patch's "
           "anchored cells have been repaired at half of T* or at T*, and at least 15 per cent at twice T*",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells whose record is "
           "right at dial-SL's delayed signal's first update is <= {intact} at m = 0.5 and at m = 1, and >= {repaired} at "
           "m = 2, else FAILS"),
    "K4": ("with only the arbiter calibrated, the evidence erodes before its clock",
           "At T* after the damage, the arbiter slowed alone (A) has had at least 0.1 more of the patch's anchored cells "
           "repaired than the fully calibrated clock (SL), and its late signal loses at least 0.03 more of the repair, "
           "on average",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the "
           "delayed signal's first update at m = 1 is larger for dial-A than for dial-SL by >= {sensors}, and loss(A, 1) "
           "- loss(SL, 1) >= {loss} at t = 8,000, where loss(c, m) is dial-c's r_in in memory4@0 less its r_in in "
           "memory4@round(m T*(3e-4)), else FAILS"),
    "K5": ("a prompt signal still pays at calibrated clocks",
           "A prompt signal repairs at least 0.2 more of a 4 x 4 memory damage than the same tissue with no signal, with "
           "the arbiter calibrated (A) and with the whole clock and the commitment calibrated (SL)",
           "HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-A's r_in in memory4@0 exceeds "
           "never-A's by >= {gain}, and dial-SL's exceeds never-SL's by >= {gain}, else FAILS"),
    "K6": ("when execution is slow, the commitment must outlast it",
           "With every bond relearning at the calibrated pace, a commitment of 15,000 updates repairs a 4 x 4 memory "
           "damage and adopts a legitimate 4 x 4 change more than one of 300 updates, by at least 0.1 each, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-SL's r_in exceeds dial-S's by >= "
           "{carry} in memory4@0 and in change4@0, else FAILS"),
    "K7": ("a long commitment is worth more when execution is slow",
           "What a commitment of 15,000 updates adds over one of 300 to a prompt repair of a 4 x 4 memory damage, and to "
           "the adoption of a legitimate 4 x 4 change, is larger by at least 0.1 with every bond relearning at the "
           "calibrated pace than with only the arbiter calibrated, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 8,000, (dial-SL's r_in - dial-S's) - (dial-AL's r_in "
           "- dial-A's) is >= {more} in memory4@0 and in change4@0, else FAILS"),
    "K8": ("a commitment that lapses before its execution is worth nothing",
           "With every bond relearning at the calibrated pace and a commitment of 300 updates, a prompt signal repairs a "
           "4 x 4 memory damage and adopts a legitimate 4 x 4 change within 0.05 of the same tissue with no signal, on "
           "average",
           "HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-S's r_in is within {none} of never-S's "
           "in memory4@0 and in change4@0, else FAILS"),
    "K9": ("a long commitment raises a sham's cost",
           "A prompt sham over scattered cue corruption costs the sheet's record at least 0.001 more with a commitment of "
           "15,000 updates than with one of 300, with only the arbiter calibrated and with the whole clock calibrated, on "
           "average",
           "HOLDS if on average over the twelve unit-body pairs at t = 8,000 in cue4@0, cost(AL) - cost(A) and cost(SL) - "
           "cost(S) are each >= {sham}, where cost(c) is never-c's r_all less dial-c's, else FAILS"),
    "K10": ("even when execution is fast, a long commitment adds",
            "With only the arbiter calibrated, a commitment of 15,000 updates repairs a 4 x 4 memory damage at least 0.02 "
            "more, and adopts a legitimate 4 x 4 change at least 0.05 more, than one of 300 updates, on average",
            "HOLDS if on average over the twelve unit-body pairs at t = 8,000, dial-AL's r_in exceeds dial-A's by >= "
            "{repair} in memory4@0 and by >= {adopt} in change4@0, else FAILS"),
}
STATEMENTS = [{"id": k, "kind": v[0], "claim": v[1], "rule": v[2].format(**THR[k]), "thresholds": THR[k]} for k, v in CLAIM.items()]


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
