"""BE007's registered statements and their scoring, written before any development outcome.

python -m be007.predict   (writes be007/frozen/predictions.json)

Thresholds were set from engineering probe P35 (32 cases on blocks 900570-900573 under tag mse-p35, disclosed in
REGISTRATION_BE007.md) under BE002's rule; probes/p35b_be007_margins.py prints every part, its SD over P35's four blocks
and the margin at these thresholds. Every part is pooled over the twelve unit-body pairs (the mean over them, scored on
unrounded block means), and its margin uses the SD over P35's four blocks of the pooled per-block value. A part needs
>= 3 x sqrt(1/4 + 1/16) = 1.68 SDs between P35's value and its threshold; where P35's SD is 0 the bound is derived, not
taken from the probe. Scored by be007.analyze on the 16 development blocks; a statement HOLDS when every one of its parts
passes.

Quantities (r_in: the patch's record against the target, the new one in a change; clock c in SL, C6, C12, C24, F12;
D = round(m T*), T* = 1,959 updates (6.5 h at 300 updates an hour), m = 0.5, 1, 2, 4; every late signal read at
D + 4,000):
  prompt(c, t)   dial-c's r_in in memory4@0 at read t (the signal at 1-1,000)
  none(c, t)     never-c's r_in in memory4@0 at read t (the same tissue, the signal never on)
  late(c, m)     dial-c's r_in in memory4@D at D + 4,000
  gain(c, m)     late(c, m) - none(c, D + 4,000): a late signal's worth over no signal, at the same time
  loss(c, m)     prompt(c, 4,000) - late(c, m): a late signal's loss against a prompt one, at equal elapsed time
  hit(c, m)      the share of the patch ever triggered by dial-c in memory4@D
  adopt(c)       dial-c's r_in in change4@3918 at 7,918 less never-c's: a late signal's adoption of a legitimate change
  sham(c)        never-c's r_all in cue4@3918 at 7,918 less dial-c's: a late sham's cost to the sheet
  rise(c, t0)    none(c, 12,000) - none(c, t0): the no-signal repair from read t0 to 40 h
Derived bounds (P35's SD is 0 in these parts; the bound is set by the construction, not the probe):
  E2 (C6, C12, F12), E4 (C6, C12, F12): after commitment every footprint cell with a confident record is committed to
      its record's sign before the late signal, and a later trigger cannot flip a committed cell (BE001's rule), so the
      signal can change at most the uncommitted cells (P35: 1 - executed share <= 0.002 of the patch); after fade the
      footprint has no cue, so neither the detector nor the arbiter acts in the patch. 0.05 sits far above both.
  E6 (C6): with no signal C6 executes the whole patch at 1,800 (P35: executed share 1.000) before the no-signal repair
      begins, so the patch cannot change afterwards; 0.005 sits above that.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be007 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
A, W0, LC = D.AFTER, D.WINDOW_0, D.LATE_CN
THR = {"E1": {"loss": 0.02},
       "E2": {"worth": 0.05},
       "E3": {"drop": 0.2},
       "E4": {"refused": 0.05, "adopted": 0.1},
       "E5": {"blocked": 0.001, "costs": 0.001},
       "E6": {"frozen": 0.005, "continues": 0.02, "slower": 0.01},
       "E7": {"hit": 0.1}}
RUNS = {D.run_name(*x): x for x in D.RUNS}
MEM0 = D.run_name("memory", 4, 0)
CHG = D.run_name("change", 4, LC)
CUE = D.run_name("cue", 4, LC)


def lv(L, u, b, rn, arm, t, e="r_in"):
    return L[u][b][rn][arm][e][D.run_reads(*RUNS[rn]).index(t)][0]


def sc(L, u, b, rn, arm, e):
    return L[u][b][rn][arm][e][0]


def dl(m):
    return int(round(m * D.T_STAR))


def prompt(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"dial-{c}", t)


def none(L, u, b, c, t):
    return lv(L, u, b, MEM0, f"never-{c}", t)


def late(L, u, b, c, m):
    rn, arm = D.where(c, m)
    return lv(L, u, b, rn, arm, dl(m) + A)


def gain(L, u, b, c, m):
    return late(L, u, b, c, m) - none(L, u, b, c, dl(m) + A)


def loss(L, u, b, c, m):
    return prompt(L, u, b, c, A) - late(L, u, b, c, m)


def hit(L, u, b, c, m):
    rn, arm = D.where(c, m)
    return sc(L, u, b, rn, arm, "hit")


def adopt(L, u, b, c):
    return lv(L, u, b, CHG, f"dial-{c}", LC + A) - lv(L, u, b, CHG, f"never-{c}", LC + A)


def sham(L, u, b, c):
    return lv(L, u, b, CUE, f"never-{c}", LC + A, "r_all") - lv(L, u, b, CUE, f"dial-{c}", LC + A, "r_all")


def rise(L, u, b, c, t0):
    return none(L, u, b, c, W0) - none(L, u, b, c, t0)


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


ONSET = (("SL", 0.5), ("SL", 1), ("C6", 0.5), ("C12", 0.5), ("C12", 1), ("F12", 0.5), ("F12", 1))    # C24 is SL there (Q5)
CLOSED = (("C6", 1), ("C6", 2), ("C6", 4), ("C12", 2), ("C12", 4), ("C24", 4), ("F12", 2), ("F12", 4))
STEPS = (("C12", "C6", 1), ("C24", "C12", 2), ("SL", "C24", 4))     # (not yet executed, executed, m)
COMMITS = ("C6", "C12", "C24")
AFTER_X = {"C6": 2000, "C12": 4000, "C24": 7918, "F12": 4000}      # the first read of memory4@0 after each tau_x
T = THR
PARTS = [
    *[part("E1", f"E1 loss({c}, {m}) = prompt({c}) at {A} - late({c}, {m}) at D + {A} (pooled)", ALL, T["E1"]["loss"], "le", True,
           (lambda c_, m_: lambda L, u, b: loss(L, u, b, c_, m_))(c, m)) for c, m in ONSET],
    *[part("E2", f"E2 gain({c}, {m}) = late({c}, {m}) - none({c}) at D + {A} (pooled)", ALL, T["E2"]["worth"], "le", True,
           (lambda c_, m_: lambda L, u, b: gain(L, u, b, c_, m_))(c, m)) for c, m in CLOSED],
    *[part("E3", f"E3 gain({o}, {m}) - gain({x}, {m}) (pooled)", ALL, T["E3"]["drop"], "ge", True,
           (lambda o_, x_, m_: lambda L, u, b: gain(L, u, b, o_, m_) - gain(L, u, b, x_, m_))(o, x, m)) for o, x, m in STEPS],
    *[part("E4", f"E4 adopt({c}) at {LC + A} (pooled)", ALL, T["E4"]["refused"], "le", True,
           (lambda c_: lambda L, u, b: adopt(L, u, b, c_))(c)) for c in ("C6", "C12", "F12")],
    *[part("E4", f"E4 adopt({c}) at {LC + A} (pooled)", ALL, T["E4"]["adopted"], "ge", True,
           (lambda c_: lambda L, u, b: adopt(L, u, b, c_))(c)) for c in ("SL", "C24")],
    *[part("E5", f"E5 sham({c}) at {LC + A} (pooled)", ALL, T["E5"]["blocked"], "le", True,
           (lambda c_: lambda L, u, b: sham(L, u, b, c_))(c)) for c in ("C6", "C12", "F12")],
    *[part("E5", f"E5 sham({c}) at {LC + A} (pooled)", ALL, T["E5"]["costs"], "ge", True,
           (lambda c_: lambda L, u, b: sham(L, u, b, c_))(c)) for c in ("SL", "C24")],
    *[part("E6", f"E6 rise({c}) = none({c}) at {W0} - none({c}) at {AFTER_X[c]} (pooled)", ALL, T["E6"]["frozen"], "abs", True,
           (lambda c_: lambda L, u, b: rise(L, u, b, c_, AFTER_X[c_]))(c)) for c in COMMITS],
    part("E6", f"E6 rise(SL) = none(SL) at {W0} - none(SL) at {AFTER_X['C6']} (pooled)", ALL, T["E6"]["continues"], "ge", True,
         lambda L, u, b: rise(L, u, b, "SL", AFTER_X["C6"])),
    part("E6", f"E6 rise(SL) - rise(F12) from {AFTER_X['F12']} to {W0} (pooled)", ALL, T["E6"]["slower"], "ge", True,
         lambda L, u, b: rise(L, u, b, "SL", AFTER_X["F12"]) - rise(L, u, b, "F12", AFTER_X["F12"])),
    *[part("E7", f"E7 hit({c}, {m}) (pooled)", ALL, T["E7"]["hit"], "ge", True,
           (lambda c_, m_: lambda L, u, b: hit(L, u, b, c_, m_))(c, m)) for c, m in CLOSED if c in COMMITS],
]

CLAIM = {
    "E1": ("execution after the evidence clock keeps its onset",
           "With no execution, and with execution after the evidence clock T* (at 12 h, by commitment or by the cue "
           "fading; at 6 h only before it), a signal half of T* or T* after a 4 x 4 memory damage (3.3 or 6.5 h) repairs "
           "no more than 0.02 below a prompt one at equal elapsed time, on average",
           "HOLDS if on average over the twelve unit-body pairs, dial-c's r_in in memory4@0 at t = 4,000 exceeds its r_in in "
           "memory4@round(m T*) at t = round(m T*) + 4,000 by at most {loss}, for clocks SL, C12 and F12 at m = 0.5 and 1 "
           "and for C6 at m = 0.5, else FAILS"),
    "E2": ("after execution a late signal is worth almost nothing",
           "A signal that arrives after the tissue has executed its default outcome (commitment at 6, 12 or 24 h, or the "
           "cue fading at 12 h) repairs a 4 x 4 memory damage at most 0.05 more than no signal at the same time, on "
           "average",
           "HOLDS if on average over the twelve unit-body pairs, dial-c's r_in in memory4@D at D + 4,000 exceeds never-c's "
           "r_in in memory4@0 at the same read by at most {worth}, for C6 at m = 1, 2 and 4, C12 at m = 2 and 4, C24 at m = 4 "
           "and F12 at m = 2 and 4 (D = round(m T*)), else FAILS"),
    "E3": ("the window closes when the tissue executes",
           "At each delay of 1, 2 and 4 T* (6.5, 13.1 and 26.1 h), a late signal is worth at least 0.2 more over no signal "
           "in a tissue that has not yet executed than in one that has just executed (commitment at 6, 12 and 24 h), paired "
           "within each case, on average",
           "HOLDS if on average over the twelve unit-body pairs, gain(C12, 1) - gain(C6, 1), gain(C24, 2) - gain(C12, 2) and "
           "gain(SL, 4) - gain(C24, 4) are each >= {drop}, where gain(c, m) is dial-c's r_in in memory4@round(m T*) at "
           "round(m T*) + 4,000 less never-c's r_in in memory4@0 at the same read, else FAILS"),
    "E4": ("execution refuses a late legitimate change",
           "A signal 13.1 h after a legitimate 4 x 4 change adopts at most 0.05 of it over no signal once the tissue has "
           "executed (commitment at 6 or 12 h, or the cue fading at 12 h), and at least 0.1 with no execution or with "
           "execution only at 24 h, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 7,918 in change4@3918, dial-c's r_in exceeds "
           "never-c's by at most {refused} for C6, C12 and F12, and by >= {adopted} for SL and C24, else FAILS"),
    "E5": ("execution blocks a late sham",
           "A sham signal 13.1 h after scattered cue corruption costs the sheet's record at most 0.001 once the tissue has "
           "executed (commitment at 6 or 12 h, or the cue fading at 12 h), and at least 0.001 with no execution or with "
           "execution only at 24 h, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 7,918 in cue4@3918, never-c's r_all less dial-c's is "
           "at most {blocked} for C6, C12 and F12, and >= {costs} for SL and C24, else FAILS"),
    "E6": ("with no signal, commitment freezes the damage and fade slows its repair",
           "With no signal, once the tissue has committed (at 6, 12 or 24 h) the damaged patch's slow repair stops: it "
           "changes by at most 0.005 from the first read after the commitment to 40 h. Without execution it continues, by "
           "at least 0.02 from 6.7 h to 40 h. With the cue faded at 12 h it continues more slowly than without execution, "
           "by at least 0.01 from 13.3 h to 40 h, paired within each case, on average",
           "HOLDS if on average over the twelve unit-body pairs, |never-c's r_in in memory4@0 at t = 12,000 less its r_in at "
           "the first read after tau_x| <= {frozen} for C6 (from 2,000), C12 (from 4,000) and C24 (from 7,918); never-SL's "
           "r_in rises by >= {continues} from 2,000 to 12,000; and never-SL's rise from 4,000 to 12,000 exceeds never-F12's "
           "by >= {slower}, else FAILS"),
    "E7": ("after execution by commitment a late signal still triggers cells",
           "A signal that arrives after the tissue has committed to its outcome still triggers at least a tenth of the "
           "damaged patch, on average, though it repairs almost nothing (E2)",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch ever triggered by dial-c in "
           "memory4@round(m T*) is >= {hit} for C6 at m = 1, 2 and 4, C12 at m = 2 and 4, and C24 at m = 4, else FAILS"),
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
