"""BE008's registered statements and their scoring, written before any development outcome.

python -m be008.predict   (writes be008/frozen/predictions.json)

Thresholds were set from engineering probe P36 (32 cases on blocks 900580-900583 under tag mse-p36, disclosed in
REGISTRATION_BE008.md) under BE002's rule; probes/p36b_be008_margins.py prints every part, its SD over P36's four blocks
and the margin at these thresholds. Every part is pooled over the twelve unit-body pairs (the mean over them, scored on
unrounded block means), and its margin uses the SD over P36's four blocks of the pooled per-block value. A part needs
>= 3 x sqrt(1/4 + 1/16) = 1.68 SDs between P36's value and its threshold; where P36's SD is 0 the bound is derived, not
taken from the probe. Scored by be008.analyze on the 16 development blocks; a statement HOLDS when every one of its parts
passes.

Quantities (clock c in AL, AL-m, AL-n, SL-m, SL; m in 0.5, 1, 2; D = round(m T*(3e-4)) = 979, 1,959, 3,918):
  sensors(c, m)    the share of the damaged patch's anchored cells whose record is right at dial-c's delayed signal's first
                   update (memory4@D; per block, right over all)
  loss(c, m)       dial-c's r_in in memory4@0 at 4,000 less its r_in in memory4@D at D + 4,000: a late signal against a
                   prompt one at equal elapsed time since each signal's start
  quiet(c, t)      the share of the patch's anchored cells right under never-c in memory4@0 at read t (no signal)
  sheet(c, t)      never-c's r_all in memory4@0 at read t (the sheet's record against its pattern)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be008 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
MEM0 = D.run_name("memory", 4, 0)
RUNS = {D.run_name(*x): x for x in D.RUNS}
THR = {"N1": {"sensors": 0.1, "loss": 0.02},
       "N2": {"intact": 0.05, "early": 0.02, "late": 0.03, "repaired": 0.1},
       "N3": {"dose": 0.1},
       "N4": {"interaction": 0.025, "same": 0.02},
       "N5": {"quiet": 0.05, "intact": 0.04},
       "N6": {"sheet": 0.05, "same": 0.01}}


def lv(L, u, b, rn, arm, t, e="r_in"):
    return L[u][b][rn][arm][e][D.run_reads(*RUNS[rn]).index(t)][0]


def sc(L, u, b, rn, arm, e):
    return L[u][b][rn][arm][e][0]


def sensors(L, u, b, c, m):
    rn, arm = D.where(c, m)
    return sc(L, u, b, rn, arm, "anc_on_share")


def loss(L, u, b, c, m):
    rn, arm = D.where(c, m)
    d = RUNS[rn][2]
    return lv(L, u, b, MEM0, arm, 4000) - lv(L, u, b, rn, arm, d + D.AFTER)


def quiet(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"never-{c}", t, "anc_right")


def sheet(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"never-{c}", t, "r_all")


def part(stmt, name, threshold, sense, value):
    return {"stmt": stmt, "name": name, "items": ALL, "threshold": threshold, "sense": sense, "pooled": True, "value": value}


T = THR
PARTS = [
    part("N1", "N1 sensors(AL, 1) - sensors(AL-n, 1) (pooled)", T["N1"]["sensors"], "ge",
         lambda L, u, b: sensors(L, u, b, "AL", 1) - sensors(L, u, b, "AL-n", 1)),
    part("N1", "N1 loss(AL, 1) - loss(AL-n, 1), equal elapsed time (pooled)", T["N1"]["loss"], "ge",
         lambda L, u, b: loss(L, u, b, "AL", 1) - loss(L, u, b, "AL-n", 1)),
    *[part("N2", f"N2 sensors(AL-n, {m}) (pooled)", T["N2"]["intact"], "le",
           (lambda m_: lambda L, u, b: sensors(L, u, b, "AL-n", m_))(m)) for m in (0.5, 1)],
    *[part("N2", f"N2 loss(AL-n, {m}), equal elapsed time (pooled)", T["N2"]["early"], "le",
           (lambda m_: lambda L, u, b: loss(L, u, b, "AL-n", m_))(m)) for m in (0.5, 1)],
    part("N2", "N2 loss(AL-n, 2), equal elapsed time (pooled)", T["N2"]["late"], "ge",
         lambda L, u, b: loss(L, u, b, "AL-n", 2)),
    part("N2", "N2 sensors(AL-n, 2) (pooled)", T["N2"]["repaired"], "ge",
         lambda L, u, b: sensors(L, u, b, "AL-n", 2)),
    part("N3", "N3 sensors(AL, 1) - sensors(AL-m, 1) (pooled)", T["N3"]["dose"], "ge",
         lambda L, u, b: sensors(L, u, b, "AL", 1) - sensors(L, u, b, "AL-m", 1)),
    part("N4", "N4 (sensors(SL-m, 1) - sensors(SL, 1)) - (sensors(AL-m, 1) - sensors(AL-n, 1)) (pooled)",
         T["N4"]["interaction"], "ge",
         lambda L, u, b: (sensors(L, u, b, "SL-m", 1) - sensors(L, u, b, "SL", 1))
         - (sensors(L, u, b, "AL-m", 1) - sensors(L, u, b, "AL-n", 1))),
    part("N4", "N4 sensors(SL, 1) - sensors(AL-n, 1) (pooled)", T["N4"]["same"], "abs",
         lambda L, u, b: sensors(L, u, b, "SL", 1) - sensors(L, u, b, "AL-n", 1)),
    part("N5", "N5 quiet(AL, 1000) - quiet(AL-n, 1000) (pooled)", T["N5"]["quiet"], "ge",
         lambda L, u, b: quiet(L, u, b, "AL", 1000) - quiet(L, u, b, "AL-n", 1000)),
    *[part("N5", f"N5 quiet({c}, 1000) (pooled)", T["N5"]["intact"], "le",
           (lambda c_: lambda L, u, b: quiet(L, u, b, c_, 1000))(c)) for c in ("AL-n", "SL")],
    part("N6", "N6 sheet(SL, 4000) - sheet(SL-m, 4000) (pooled)", T["N6"]["sheet"], "ge",
         lambda L, u, b: sheet(L, u, b, "SL", 4000) - sheet(L, u, b, "SL-m", 4000)),
    part("N6", "N6 sheet(AL-n, 4000) - sheet(AL-m, 4000) (pooled)", T["N6"]["same"], "abs",
         lambda L, u, b: sheet(L, u, b, "AL-n", 4000) - sheet(L, u, b, "AL-m", 4000)),
]

CLAIM = {
    "N1": ("with the other bonds relearning fast, the lane's bond noise erodes the evidence",
           "With the arbiter at 3e-4, every other bond at the lane's 0.01 and a commitment of 15,000 updates, the lane's "
           "bond noise (1e-3) has repaired at least 0.1 more of the damaged patch's anchored cells by T* (6.5 h) than "
           "noise scaled to 3e-5, and a signal arriving at T* loses at least 0.02 more of a 4 x 4 memory repair against a "
           "prompt one, on average",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the "
           "delayed signal's first update at m = 1 is larger for dial-AL than for dial-AL-n by >= {sensors}, and "
           "loss(AL, 1) - loss(AL-n, 1) >= {loss}, where loss(c, m) is dial-c's r_in in memory4@0 at 4,000 less its r_in "
           "in memory4@round(m T*(3e-4)) 4,000 updates after that signal's start, else FAILS"),
    "N2": ("with the noise scaled alone, the arbiter's clock returns",
           "With every other bond still at the lane's 0.01 but the bond noise scaled to 3e-5, at most 5 per cent of the "
           "patch's anchored cells are repaired by half of T* or T*, a signal then loses no more than 0.02 against a "
           "prompt one, and one at twice T* loses at least 0.03, with at least 10 per cent of the anchored cells repaired "
           "by then, on average",
           "HOLDS if on average over the twelve unit-body pairs, for dial-AL-n the share of the patch's anchored cells "
           "right at the delayed signal's first update is <= {intact} at m = 0.5 and 1 and >= {repaired} at m = 2, and "
           "loss(AL-n, m) is <= {early} at m = 0.5 and 1 and >= {late} at m = 2, else FAILS"),
    "N3": ("the erosion grows with the noise",
           "At the lane's relearning rate, the lane's bond noise (1e-3) has repaired at least 0.1 more of the patch's "
           "anchored cells by T* than a tenth of it (1e-4), on average",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells right at the "
           "delayed signal's first update at m = 1 is larger for dial-AL than for dial-AL-m by >= {dose}, else FAILS"),
    "N4": ("slow relearning elsewhere lets moderate noise erode the evidence",
           "What raising the bond noise from 3e-5 to 1e-4 adds to the anchored cells repaired by T* is at least 0.025 "
           "larger with every other bond relearning at 3e-4 than at 0.01, while at 3e-5 the two relearning rates leave "
           "the same share repaired within 0.02, on average",
           "HOLDS if on average over the twelve unit-body pairs, at m = 1, (sensors(SL-m) - sensors(SL)) - "
           "(sensors(AL-m) - sensors(AL-n)) >= {interaction} and |sensors(SL) - sensors(AL-n)| <= {same}, where "
           "sensors(c) is the share of the patch's anchored cells right at dial-c's delayed signal's first update, else "
           "FAILS"),
    "N5": ("without a signal, before T* only the lane's noise erodes the evidence",
           "With no signal, by 1,000 updates (3.3 h) the lane's bond noise has repaired at least 0.05 more of the "
           "patch's anchored cells than scaled noise, and with scaled noise, at either relearning rate, at most 4 per "
           "cent are repaired, on average",
           "HOLDS if on average over the twelve unit-body pairs in memory4@0 at t = 1,000, the share of the patch's "
           "anchored cells right under never-AL exceeds never-AL-n's by >= {quiet}, and is <= {intact} under never-AL-n "
           "and under never-SL, else FAILS"),
    "N6": ("moderate noise with slow relearning degrades the whole record",
           "With no signal, at 4,000 updates the sheet's record under bond noise 1e-4 is at least 0.05 worse than under "
           "3e-5 when every other bond relearns at 3e-4, and within 0.01 of it when they relearn at 0.01, on average",
           "HOLDS if on average over the twelve unit-body pairs in memory4@0 at t = 4,000, never-SL's r_all exceeds "
           "never-SL-m's by >= {sheet}, and |never-AL-n's r_all - never-AL-m's| <= {same}, else FAILS"),
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
            x = mean(vals.values())
            good = passes(x, p["threshold"], p["sense"])
            out[p["name"]] = {"pooled": x, "pass": good, "items": vals}
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
