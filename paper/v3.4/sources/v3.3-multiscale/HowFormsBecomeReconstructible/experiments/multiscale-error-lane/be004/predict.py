"""BE004's registered statements and their scoring, written before any development outcome.

python -m be004.predict   (writes be004/frozen/predictions.json)

Thresholds were set from engineering probe P28 (32 cases on blocks 900680-900683 under tag mse-p28, disclosed in
REGISTRATION_BE004.md) under BE002's rule; probes/p28b_be004_margins.py prints every part, its items' SDs over P28's four
blocks and the margin at these thresholds. SD_block = max(the item's own SD, the RMS of the SDs over the part's items);
an every-item part sits >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P28's worst item; a pooled part (the mean over its
items) uses the SD over blocks of the pooled per-block value. An item is one unit and body (and delay or arm where the part
names several). Every part reads t = 4,000 unless it names another instant. Scored by be004.analyze on unrounded block
means over the 16 development blocks; a statement HOLDS when every one of its parts passes.

Runs: memory4@D (a 4 x 4 memory damage, the signal over the patch dilated by 2 at D + 1 to D + 1,000; D = 0: cue, bio-1,
bio-3, dial; D = 250, 500, 1,000: dial, dial-hold), cue4@1000 (scattered cue damage, a late sham: bio-3, dial, dial-hold),
change4@0 (a legitimate 4 x 4 change, the signal at 1-1,000: every arm but the hold), cue4@0 (scattered cue damage, a
prompt sham: the size, closure and flicker arms). Endpoints: r_in (the patch, against the target: the new one in a change),
v_in (the body in the patch), anc_right (the share of the patch's anchored cells whose record is right; per block, right
over all), r_all (the sheet), r_out8 (outside the patch dilated by 8), onset (the share of the patch that triggers at the
signal's first update under the footprint's conductances). The cost of a sham is bio-3's r_all less the arm's in the same
run (bio-3 is every signal arm without its signal, bit for bit).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be004 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
LATE = tuple(d for d in D.DELAYS if d)
STATIC = Path(__file__).resolve().parent / "frozen" / "static_map.json"
THR = {"E1": {"early": 0.015, "late": 0.05, "flat": 0.02},
       "E2": {"same": 0.02},
       "E3": {"recovers": 0.05},
       "E4": {"intact": 0.01, "repaired": 0.2, "kept": 0.01, "onset_loss": 0.10, "onset_same": 0.03},
       "E5": {"record": 0.05, "body": 0.03},
       "E6": {"sham": 0.002},
       "P1": {"s2": 0.03, "s4": 0.10, "s6": 0.05},
       "P2": {"larger": 0.01, "d0": 0.02},
       "P3": {"d2": 0.002, "d4": 0.003, "d8": 0.012},
       "P4": {"adopt": 0.10, "adopt2": 0.07, "cost": 0.001},
       "P5": {"adopt": 0.005, "cost": 0.001},
       "P6": {"adopt": 0.005, "cost": 0.001},
       "P7": {"gap": 0.15, "order": 0.0}}


def lv(L, u, b, rn, arm, e="r_in", t=D.READS[-1]):
    return L[u][b][rn][arm][e][D.READS.index(t)][0]


def sc(L, u, b, rn, arm, e):
    return L[u][b][rn][arm][e][0]


def mem(d):
    return D.run_name("memory", 4, d)


def cost(L, u, b, arm, rn="cue4@0"):
    """The sham's cost to the sheet: bio-3's r_all less the arm's, same run."""
    return lv(L, u, b, rn, "bio-3", "r_all") - lv(L, u, b, rn, arm, "r_all")


def adopt(L, u, b, arm):
    return lv(L, u, b, "change4@0", arm, "r_in")


def pooled_adopt(L, a1, a2):
    """The pooled (over the twelve pairs) adoption of a1 less a2 in change4@0."""
    return sum(adopt(L, u, b, a1) - adopt(L, u, b, a2) for u, b in ALL) / len(ALL)


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


def static_pairs():
    """P7's arm pairs: the registered static map's adoption at least THR gap apart (the higher first)."""
    s = json.loads(STATIC.read_text())["adoption"]
    arms = [a for a in ("bio-1", "bio-3", "dial", "dial-s2", "dial-s4", "dial-s6", "dial-d0", "dial-d4", "dial-d8",
                        "dial-w1.5", "dial-w2") if a in s]
    return tuple((a1, a2) for a1 in arms for a2 in arms if s[a1] - s[a2] >= THR["P7"]["gap"])


T = THR
PARTS = [
    part("E1", "E1 dial@50 - dial@0 (pooled)", ALL, T["E1"]["early"], "abs", True,
         lambda L, u, b: lv(L, u, b, mem(50), "dial") - lv(L, u, b, mem(0), "dial")),
    *[part("E1", f"E1 dial@{d} - dial@0 (pooled)", ALL, -T["E1"]["late"], "le", True,
           (lambda d_: lambda L, u, b: lv(L, u, b, mem(d_), "dial") - lv(L, u, b, mem(0), "dial"))(d)) for d in (100, 1000)],
    part("E1", "E1 dial@1000 - dial@250 (pooled)", ALL, T["E1"]["flat"], "abs", True,
         lambda L, u, b: lv(L, u, b, mem(1000), "dial") - lv(L, u, b, mem(250), "dial")),
    *[part("E2", f"E2 hold@{d} - dial@0 (pooled)", ALL, T["E2"]["same"], "abs", True,
           (lambda d_: lambda L, u, b: lv(L, u, b, mem(d_), "dial-hold") - lv(L, u, b, mem(0), "dial"))(d)) for d in LATE],
    part("E3", "E3 hold@1000 - dial@1000 (pooled)", ALL, T["E3"]["recovers"], "ge", True,
         lambda L, u, b: lv(L, u, b, mem(1000), "dial-hold") - lv(L, u, b, mem(1000), "dial")),
    part("E4", "E4 anc_right at t=50, dial@50 (pooled)", ALL, T["E4"]["intact"], "le", True,
         lambda L, u, b: lv(L, u, b, mem(50), "dial", "anc_right", 50)),
    part("E4", "E4 anc_right at t=100, dial@100 (pooled)", ALL, T["E4"]["repaired"], "ge", True,
         lambda L, u, b: lv(L, u, b, mem(100), "dial", "anc_right", 100)),
    part("E4", "E4 anc_right at t=1000, hold@1000 (pooled)", ALL, T["E4"]["kept"], "le", True,
         lambda L, u, b: lv(L, u, b, mem(1000), "dial-hold", "anc_right", 1000)),
    part("E4", "E4 onset dial@0 - onset dial@1000 (pooled)", ALL, T["E4"]["onset_loss"], "ge", True,
         lambda L, u, b: sc(L, u, b, mem(0), "dial", "onset") - sc(L, u, b, mem(1000), "dial", "onset")),
    part("E4", "E4 onset hold@1000 - onset dial@0 (pooled)", ALL, T["E4"]["onset_same"], "abs", True,
         lambda L, u, b: sc(L, u, b, mem(1000), "dial-hold", "onset") - sc(L, u, b, mem(0), "dial", "onset")),
    part("E5", "E5 r_in at t=1000: dial@1000 - hold@1000 (pooled)", ALL, T["E5"]["record"], "ge", True,
         lambda L, u, b: lv(L, u, b, mem(1000), "dial", "r_in", 1000) - lv(L, u, b, mem(1000), "dial-hold", "r_in", 1000)),
    part("E5", "E5 v_in at t=1000: dial@1000 - hold@1000 (pooled)", ALL, T["E5"]["body"], "ge", True,
         lambda L, u, b: lv(L, u, b, mem(1000), "dial", "v_in", 1000) - lv(L, u, b, mem(1000), "dial-hold", "v_in", 1000)),
    part("E6", "E6 late sham: r_all hold - dial (pooled)", ALL, T["E6"]["sham"], "abs", True,
         lambda L, u, b: lv(L, u, b, "cue4@1000", "dial-hold", "r_all") - lv(L, u, b, "cue4@1000", "dial", "r_all")),
    part("P1", "P1 adoption dial-s2 - dial (pooled)", ALL, T["P1"]["s2"], "abs", True,
         lambda L, u, b: adopt(L, u, b, "dial-s2") - adopt(L, u, b, "dial")),
    part("P1", "P1 adoption dial - dial-s4 (pooled)", ALL, T["P1"]["s4"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial") - adopt(L, u, b, "dial-s4")),
    part("P1", "P1 adoption dial-s4 - dial-s6 (pooled)", ALL, T["P1"]["s6"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-s4") - adopt(L, u, b, "dial-s6")),
    *[part("P2", f"P2 adoption {a} - dial (pooled)", ALL, T["P2"]["larger"], "abs", True,
           (lambda a_: lambda L, u, b: adopt(L, u, b, a_) - adopt(L, u, b, "dial"))(a)) for a in ("dial-d4", "dial-d8")],
    part("P2", "P2 adoption dial - dial-d0 (pooled)", ALL, T["P2"]["d0"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial") - adopt(L, u, b, "dial-d0")),
    *[part("P3", f"P3 cost {a2} - cost {a1} (pooled)", ALL, T["P3"][k], "ge", True,
           (lambda a1_, a2_: lambda L, u, b: cost(L, u, b, a2_) - cost(L, u, b, a1_))(a1, a2))
      for a1, a2, k in (("dial-d0", "dial", "d2"), ("dial", "dial-d4", "d4"), ("dial-d4", "dial-d8", "d8"))],
    part("P4", "P4 adoption dial - dial-w1.5 (pooled)", ALL, T["P4"]["adopt"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial") - adopt(L, u, b, "dial-w1.5")),
    part("P4", "P4 adoption dial-w1.5 - dial-w2 (pooled)", ALL, T["P4"]["adopt2"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-w1.5") - adopt(L, u, b, "dial-w2")),
    part("P4", "P4 cost dial - cost dial-w1.5 (pooled)", ALL, T["P4"]["cost"], "ge", True,
         lambda L, u, b: cost(L, u, b, "dial") - cost(L, u, b, "dial-w1.5")),
    *[part("P5", f"P5 adoption {a} - dial (pooled)", ALL, T["P5"]["adopt"], "abs", True,
           (lambda a_: lambda L, u, b: adopt(L, u, b, a_) - adopt(L, u, b, "dial"))(a)) for a in ("dial-f0.5", "dial-f0.25")],
    *[part("P5", f"P5 cost {a} - cost dial (pooled)", ALL, T["P5"]["cost"], "abs", True,
           (lambda a_: lambda L, u, b: cost(L, u, b, a_) - cost(L, u, b, "dial"))(a)) for a in ("dial-f0.5", "dial-f0.25")],
    *[part("P6", f"P6 adoption {a} - dial (pooled)", ALL, T["P6"]["adopt"], "abs", True,
           (lambda a_: lambda L, u, b: adopt(L, u, b, a_) - adopt(L, u, b, "dial"))(a)) for a in ("dial-t1", "dial-t10", "dial-t100")],
    *[part("P6", f"P6 cost {a} - cost dial (pooled)", ALL, T["P6"]["cost"], "abs", True,
           (lambda a_: lambda L, u, b: cost(L, u, b, a_) - cost(L, u, b, "dial"))(a)) for a in ("dial-t1", "dial-t10", "dial-t100")],
    part("P7", "P7 run adoption follows the static map's order (every pair at least 0.15 apart statically)",
         static_pairs(), T["P7"]["order"], "ge", False, lambda L, a1, a2: pooled_adopt(L, a1, a2)),
]

CLAIM = {
    "E1": ("the window for a late signal closes early",
           "A signal that arrives 50 updates after a 4 x 4 memory damage repairs it as a prompt one does; one that arrives "
           "100 or 1,000 updates after it repairs less; and one 1,000 updates late repairs about as much as one 250 late",
           "HOLDS if, on average over the twelve unit-body pairs at t = 4,000, the dial's r_in in memory4@50 is within "
           "{early} of the dial's in memory4@0, the dial's r_in in memory4@100 and in memory4@1000 are each below the dial's "
           "in memory4@0 by >= {late}, and the dial's r_in in memory4@1000 and in memory4@250 differ by at most {flat}, else "
           "FAILS"),
    "E2": ("held, a late signal repairs as a prompt one",
           "With the arbiter taking no cue inside the footprint until the signal comes, a signal that arrives 50 to 1,000 "
           "updates after a 4 x 4 memory damage repairs it as much as a prompt signal does, within 0.02 on average",
           "HOLDS if for every delay D in {{50, 100, 250, 500, 1,000}}, on average over the twelve unit-body pairs, dial-hold's "
           "r_in in memory4@D at t = 4,000 is within {same} of the dial's in memory4@0, else FAILS"),
    "E3": ("the hold recovers what the wait cost",
           "A signal that arrives 1,000 updates after the damage repairs more of it with the hold than without",
           "HOLDS if on average over the twelve unit-body pairs dial-hold's r_in in memory4@1000 at t = 4,000 exceeds the "
           "dial's by >= {recovers}, else FAILS"),
    "E4": ("the evidence at the signal's onset",
           "While a signal waits, the arbiter repairs at most 1 per cent of the damaged patch's anchored cells in the first 50 "
           "updates and at least a fifth of them by 100, and the share of the patch that triggers when a signal 1,000 updates "
           "late comes is smaller than a prompt signal's; with the hold, at most 1 per cent of them is repaired and the share "
           "that triggers is within 0.03 of the prompt signal's",
           "HOLDS if on average over the twelve unit-body pairs the dial's anc_right is <= {intact} in memory4@50 at t = 50 "
           "and >= {repaired} in memory4@100 at t = 100; dial-hold's anc_right in memory4@1000 at t = 1,000 is <= {kept}; "
           "the dial's onset in memory4@1000 is below its onset in memory4@0 by >= {onset_loss}; and dial-hold's onset in "
           "memory4@1000 is within {onset_same} of the dial's in memory4@0, else FAILS"),
    "E5": ("while it waits, the hold leaves the damage standing",
           "While a signal waits, the hold leaves more of the damaged patch wrong than the arbiter does, in the record and in "
           "the body",
           "HOLDS if on average over the twelve unit-body pairs, in memory4@1000 at t = 1,000, the dial's r_in exceeds "
           "dial-hold's by >= {record} and the dial's v_in exceeds dial-hold's by >= {body}, else FAILS"),
    "E6": ("a held arbiter and a late sham",
           "Under scattered cue corruption with a sham signal 1,000 updates late, holding the arbiter while the sham is pending "
           "changes the sheet's record by at most 0.002 on average",
           "HOLDS if on average over the twelve unit-body pairs dial-hold's r_all in cue4@1000 at t = 4,000 is within {sham} "
           "of the dial's, else FAILS"),
    "P1": ("an offset footprint",
           "A footprint shifted by 2 sites, which still covers the patch, adopts a 4 x 4 change as the centred one does; "
           "shifted by 4, covering half the patch, it adopts less; shifted by 6, covering none of it, less again",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-s2's r_in is within {s2} of "
           "the dial's, the dial's exceeds dial-s4's by >= {s4}, and dial-s4's exceeds dial-s6's by >= {s6}, else FAILS"),
    "P2": ("a footprint's size",
           "A footprint larger than BE002's (the patch dilated by 4 or 8 instead of 2) adopts a 4 x 4 change as BE002's does; "
           "the patch alone (dilated by 0) adopts less",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-d4's and dial-d8's r_in are "
           "each within {larger} of the dial's and the dial's exceeds dial-d0's by >= {d0}, else FAILS"),
    "P3": ("a sham's cost grows with its footprint's area",
           "Under scattered cue corruption a sham signal costs the sheet's record more the larger its footprint: the patch "
           "dilated by 0, 2, 4 and 8 in increasing order",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in cue4@0, with cost = bio-3's r_all less the "
           "arm's, the dial's cost exceeds dial-d0's by >= {d2}, dial-d4's exceeds the dial's by >= {d4}, and dial-d8's "
           "exceeds dial-d4's by >= {d8}, else FAILS"),
    "P4": ("a weaker closure",
           "Closing the footprint's junctions to coupling length 1.5 instead of 1 adopts a 4 x 4 change less and costs a "
           "sham less; closing them to 2 adopts less again",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, the dial's r_in in change4@0 exceeds "
           "dial-w1.5's by >= {adopt}, dial-w1.5's exceeds dial-w2's by >= {adopt2}, and the dial's cost in cue4@0 exceeds "
           "dial-w1.5's by >= {cost}, else FAILS"),
    "P5": ("a flickering signal",
           "A signal on at each update with probability 0.5 or 0.25 adopts a 4 x 4 change and costs a sham as a steady "
           "signal does",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-f0.5's and dial-f0.25's r_in in "
           "change4@0 are each within {adopt} of the dial's, and their costs in cue4@0 each within {cost} of the dial's, "
           "else FAILS"),
    "P6": ("a brief signal",
           "A signal on for only its first 1, 10 or 100 updates adopts a 4 x 4 change and costs a sham as a 1,000-update "
           "signal does",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-t1's, dial-t10's and dial-t100's r_in in "
           "change4@0 are each within {adopt} of the dial's, and their costs in cue4@0 each within {cost} of the dial's, "
           "else FAILS"),
    "P7": ("the static map orders the footprints",
           "Wherever the static map registered before the run gives one arm's footprint and closure a share of a 4 x 4 patch "
           "below threshold at least 0.15 above another's, the run adopts the change at least as much with the first",
           "HOLDS if for every pair of the arms bio-1, bio-3, dial, dial-s2, dial-s4, dial-s6, dial-d0, dial-d4, dial-d8, "
           "dial-w1.5 and dial-w2 whose static adoption differs by >= {gap}, the first's pooled r_in in change4@0 at "
           "t = 4,000 (over the twelve unit-body pairs) is >= the second's, else FAILS"),
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
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "static_map": json.loads(STATIC.read_text()), "thresholds": THR,
                               "parts": [{k: v for k, v in p.items() if k != "value"} for p in PARTS],
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
