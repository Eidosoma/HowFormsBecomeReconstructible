"""BE010's registered statements and their scoring, written before any development outcome.

python -m be010.predict   (writes be010/frozen/predictions.json)

Thresholds were set from engineering probe P38 (32 cases on blocks 900588-900591 under tag mse-p38, disclosed in
REGISTRATION_BE010.md) under BE002's rule; probes/p38b_be010_margins.py prints every part, its SD over P38's four blocks
and the margin at these thresholds. Every part is pooled over the twelve unit-body pairs (the mean over them, scored on
unrounded block means), and its margin uses the SD over P38's four blocks of the pooled per-block value. A part needs
>= 3 x sqrt(1/4 + 1/16) = 1.68 SDs between P38's value and its threshold; where P38's SD is 0 the bound is derived, not
taken from the probe. Scored by be010.analyze on the 16 development blocks; a statement HOLDS when every one of its parts
passes.

Quantities (r_in: the patch's record against the target; T_W = 7,836 (26.1 h), the second event at the start of T_W + 1;
reset x in N (none), W (a new wound at the patch, every contact touching it untrained), K (the same wound, the rim's
contacts kept), R (the drug: every commitment cleared), W0 and R0 (W and R with no re-execution); d = round(m T*),
T* = 1,959 updates (6.5 h at 300 updates an hour), m = 0, 0.5, 1, 2; every dial read at T_W + d + 4,000):
  late(x, m)     dial-x's r_in in memory4@w+d at T_W + d + 4,000 (the signal at T_W + d + 1 to T_W + d + 1,000)
  none(x, t)     never-x's r_in in memory4@w+3918 at read t (the same tissue and reset, the signal never on)
  gain(x, m)     late(x, m) - none(x, T_W + d + 4,000): a signal's worth after reset x over no signal, at the same time
  alone(x, t)    none(x, t) - none(N, t): reset x's own repair, with no signal
  cost(x, t)     never-N's r_in less never-x's in none4@w+0 at read t: reset x's own cost where nothing was wrong
  sham(x, e)     never-x's endpoint e less dial-x's in cue4@w+0 at T_W + 4,000: a sham signal's cost right after reset x
                 (BE007's sham: a quarter of the anchors corrupted; e = r_all, the sheet, or r_fp2, the footprint)
Derived bound (P38's SD is 0 in this part only; the bound is set by the construction, not the probe):
  R3, gain(R, 2): at RE_X = T_W + 3,600, before the signal at T_W + 3,919, every footprint cell with a confident record
      commits to its record's sign, and a later trigger cannot flip a committed cell (BE001's rule), so the signal can
      change at most the uncommitted cells (P38: the patch's uncommitted share, pooled over the pairs, at most 0.0033
      just after RE_X, the largest of the four blocks); 0.05 sits far above that. R1's parts have the same bound (at most
      0.0052 uncommitted at T_W), but their P38 SD is not 0 (one block reads -0.0013), so they carry the probe's margin.
Every part also clears 1.68 under the case-level SD (the SD over P38's 32 pair-pooled cases / sqrt 8; the lead's check
after P38, before the freeze; worst R8's drug part, 1.89).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be010 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
A, TW = D.AFTER, D.T_W
THR = {"R1": {"closed": 0.05},
       "R2": {"open": 0.2},
       "R3": {"closed": 0.05, "open": 0.2},
       "R4": {"alone": 0.05},
       "R5": {"alone": 0.5},
       "R6": {"rim": 0.2, "partial": 0.1},
       "R7": {"narrow": 0.02, "drug_over_rim": 0.2},
       "R8": {"wound": 0.1, "drug": 0.04},
       "R9": {"blocked": 0.001, "exposed": 0.003}}
RUNS = {D.run_name(*x): x for x in D.RUNS}
NV, SH, CU = D.NEVER_RUN, D.SHAM_RUN, D.CUE_RUN
T4 = TW + A                                                     # 11,836: four thousand updates after the reset


def lv(L, u, b, rn, arm, t, e="r_in"):
    return L[u][b][rn][arm][e][D.run_reads(*RUNS[rn]).index(t)][0]


def dl(m):
    return int(round(m * D.T_STAR))


def late(L, u, b, x, m):
    rn, arm = D.where(x, m)
    return lv(L, u, b, rn, arm, TW + dl(m) + A)


def none(L, u, b, x, t):
    return lv(L, u, b, NV, f"never-{x}", t)


def gain(L, u, b, x, m):
    if x in ("W0", "R0"):                                       # only at 2 T*, in memory4@w+3918
        return lv(L, u, b, NV, f"dial-{x}", TW + dl(m) + A) - none(L, u, b, x, TW + dl(m) + A)
    return late(L, u, b, x, m) - none(L, u, b, x, TW + dl(m) + A)


def alone(L, u, b, x, t):
    return none(L, u, b, x, t) - none(L, u, b, "N", t)


def cost(L, u, b, x, t):
    return lv(L, u, b, SH, "never-N", t) - lv(L, u, b, SH, f"never-{x}", t)


def rise(L, u, b, x, t0, t1):
    return none(L, u, b, x, t1) - none(L, u, b, x, t0)


def sham(L, u, b, x, e="r_all"):
    return lv(L, u, b, CU, f"never-{x}", T4, e) - lv(L, u, b, CU, f"dial-{x}", T4, e)


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


OPEN = (0, 0.5, 1)                                              # the dials before re-execution (RE_X = T_W + 3,600)
LAST = TW + D.AFTER_W[-1] + A                                   # 15,754: the never run's last read
T = THR
PARTS = [
    *[part("R1", f"R1 gain(N, {m}) at T_W + d + {A} (pooled)", ALL, T["R1"]["closed"], "le", True,
           (lambda m_: lambda L, u, b: gain(L, u, b, "N", m_))(m)) for m in D.MULTS],
    *[part("R2", f"R2 gain(R, {m}) at T_W + d + {A} (pooled)", ALL, T["R2"]["open"], "ge", True,
           (lambda m_: lambda L, u, b: gain(L, u, b, "R", m_))(m)) for m in OPEN],
    part("R3", f"R3 gain(R, 2) at T_W + 3918 + {A} (pooled)", ALL, T["R3"]["closed"], "le", True,
         lambda L, u, b: gain(L, u, b, "R", 2)),
    part("R3", f"R3 gain(R0, 2) at T_W + 3918 + {A} (pooled)", ALL, T["R3"]["open"], "ge", True,
         lambda L, u, b: gain(L, u, b, "R0", 2)),
    part("R4", f"R4 alone(R) at T_W + {A} (pooled)", ALL, T["R4"]["alone"], "le", True,
         lambda L, u, b: alone(L, u, b, "R", T4)),
    part("R5", f"R5 alone(W) at T_W + {A} (pooled)", ALL, T["R5"]["alone"], "ge", True,
         lambda L, u, b: alone(L, u, b, "W", T4)),
    part("R5", "R5 alone(W) at T_W + 500 (pooled)", ALL, T["R5"]["alone"], "ge", True,
         lambda L, u, b: alone(L, u, b, "W", TW + 500)),
    part("R6", f"R6 alone(W) - alone(K) at T_W + {A} (pooled)", ALL, T["R6"]["rim"], "ge", True,
         lambda L, u, b: alone(L, u, b, "W", T4) - alone(L, u, b, "K", T4)),
    part("R6", f"R6 alone(K) at T_W + {A} (pooled)", ALL, T["R6"]["partial"], "ge", True,
         lambda L, u, b: alone(L, u, b, "K", T4)),
    *[part("R7", f"R7 gain(K, {m}) at T_W + d + {A} (pooled)", ALL, T["R7"]["narrow"], "ge", True,
           (lambda m_: lambda L, u, b: gain(L, u, b, "K", m_))(m)) for m in OPEN],
    *[part("R7", f"R7 gain(R, {m}) - gain(K, {m}) (pooled)", ALL, T["R7"]["drug_over_rim"], "ge", True,
           (lambda m_: lambda L, u, b: gain(L, u, b, "R", m_) - gain(L, u, b, "K", m_))(m)) for m in OPEN],
    part("R8", f"R8 cost(W) at T_W + {A} (pooled)", ALL, T["R8"]["wound"], "ge", True,
         lambda L, u, b: cost(L, u, b, "W", T4)),
    part("R8", f"R8 cost(R) at T_W + {A} (pooled)", ALL, T["R8"]["drug"], "le", True,
         lambda L, u, b: cost(L, u, b, "R", T4)),
    part("R9", f"R9 sham(N) r_all at T_W + {A} (pooled)", ALL, T["R9"]["blocked"], "le", True,
         lambda L, u, b: sham(L, u, b, "N")),
    part("R9", f"R9 sham(W) r_all at T_W + {A} (pooled)", ALL, T["R9"]["blocked"], "le", True,
         lambda L, u, b: sham(L, u, b, "W")),
    part("R9", f"R9 sham(R) r_all at T_W + {A} (pooled)", ALL, T["R9"]["exposed"], "ge", True,
         lambda L, u, b: sham(L, u, b, "R")),
]

CLAIM = {
    "R1": ("without a reset the executed decision stays closed",
           "With no second event, a signal 26.1 h after a 4 x 4 memory damage, or 3.3, 6.5 or 13.1 h later still, after "
           "the tissue executed its default outcome at 12 h, repairs at most 0.05 more than no signal at the same time, on "
           "average",
           "HOLDS if on average over the twelve unit-body pairs, dial-N's r_in in memory4@w+d at T_W + d + 4,000 exceeds "
           "never-N's r_in in memory4@w+3918 at the same read by at most {closed}, for d = round(m T*), m = 0, 0.5, 1 and "
           "2, else FAILS"),
    "R2": ("a reset drug reopens the window",
           "After every commitment is cleared at 26.1 h (cells, records and bonds untouched), a signal at once or 3.3 or "
           "6.5 h later repairs at least 0.2 more of the damaged patch than the drug alone at the same time, on average",
           "HOLDS if on average over the twelve unit-body pairs, dial-R's r_in in memory4@w+d at T_W + d + 4,000 exceeds "
           "never-R's r_in in memory4@w+3918 at the same read by >= {open}, for m = 0, 0.5 and 1, else FAILS"),
    "R3": ("re-execution closes the reopened window",
           "After the drug, a signal 13.1 h later (after the tissue executes again, 12 h after the drug) repairs at most "
           "0.05 more than the drug alone; without that second execution the same signal repairs at least 0.2 more, on "
           "average",
           "HOLDS if on average over the twelve unit-body pairs at T_W + 3,918 + 4,000 in memory4@w+3918, dial-R's r_in "
           "exceeds never-R's by at most {closed} and dial-R0's exceeds never-R0's by >= {open}, else FAILS"),
    "R4": ("the drug alone repairs almost nothing",
           "With no signal, clearing every commitment repairs at most 0.05 of the damaged patch by 13.3 h after the drug, "
           "on average",
           "HOLDS if on average over the twelve unit-body pairs, never-R's r_in at T_W + 4,000 in memory4@w+3918 exceeds "
           "never-N's at the same read by at most {alone}, else FAILS"),
    "R5": ("a new wound alone repairs the executed damage",
           "With no signal, a new wound at the damaged patch (newborn cells, every contact touching them untrained, the "
           "positional cue kept) repairs at least half of the patch within 1.7 h, and still by 13.3 h, on average",
           "HOLDS if on average over the twelve unit-body pairs, never-W's r_in in memory4@w+3918 exceeds never-N's by >= "
           "{alone} at T_W + 500 and at T_W + 4,000, else FAILS"),
    "R6": ("the rim's junctions carry the executed state into the regrowth",
           "With no signal, a new wound that keeps the rim's contacts repairs at least 0.2 less of the patch than one that "
           "untrains them, but still at least 0.1, by 13.3 h after the wound, on average",
           "HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in memory4@w+3918, never-W's r_in less "
           "never-K's is >= {rim} and never-K's r_in less never-N's is >= {partial}, else FAILS"),
    "R7": ("a wound that keeps the rim leaves a narrow window",
           "After a new wound that keeps the rim's contacts, a signal at once or 3.3 or 6.5 h later repairs at least 0.02 "
           "more than the wound alone, and at least 0.2 less than the same signal after the drug, paired within each case, "
           "on average",
           "HOLDS if on average over the twelve unit-body pairs, gain(K, m) >= {narrow} and gain(R, m) - gain(K, m) >= "
           "{drug_over_rim} for m = 0, 0.5 and 1, where gain(x, m) is dial-x's r_in in memory4@w+round(m T*) at T_W + "
           "round(m T*) + 4,000 less never-x's in memory4@w+3918 at the same read, else FAILS"),
    "R8": ("a wound costs an undamaged patch, the drug little",
           "Where nothing was wrong, a new wound at the patch at 26.1 h leaves its record at least 0.1 worse 13.3 h later, "
           "and the drug at most 0.04 worse, on average",
           "HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in none4@w+0, never-N's r_in less "
           "never-W's is >= {wound} and never-N's less never-R's is at most {drug}, else FAILS"),
    "R9": ("the drug re-exposes the tissue to a sham, a wound does not",
           "A sham signal right after the reset at 26.1 h, in a tissue with a quarter of its anchors corrupted, costs the "
           "sheet's record at most 0.001 with no reset or after a new wound, and at least 0.003 after the drug, on average",
           "HOLDS if on average over the twelve unit-body pairs at T_W + 4,000 in cue4@w+0, never-x's r_all less dial-x's "
           "is at most {blocked} for x = N and W, and >= {exposed} for x = R, else FAILS"),
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
