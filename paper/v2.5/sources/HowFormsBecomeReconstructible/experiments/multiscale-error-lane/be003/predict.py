"""BE003's registered statements and their scoring, written before any development outcome.

python -m be003.predict   (writes be003/frozen/predictions.json)

Thresholds were set from engineering probe P27 (32 cases on blocks 900670-900673 under tag mse-p27, disclosed in
REGISTRATION_BE003.md) under BE002's rule; probes/p27b_be003_margins.py prints every item, its SD over P27's four blocks
and the margin at these thresholds. SD_block = max(the item's own SD, the RMS of the SDs over the part's items); an
every-item part sits >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P27's worst item; a pooled part (the mean over its
items) uses the SD over blocks of the pooled per-block value. An item is one unit and body (and arm, delay or region where
the part names several). Scored by be003.analyze on unrounded block means over the 16 development blocks.

Runs: regrow8 (an 8 x 8 wound regrown by division; the signal arms' injury signal at updates 1-1,000 over the wound
dilated by 2), regrow8_late (the signal at 1,001-2,000), regrow+cue8 (with scattered corruption of a quarter of the
anchors), twin4@d (the cue of a 4 x 4 'young' patch at the wound's centre and of its 'twin' in old tissue re-specified
after update d; the signal over both, dilated by 2, at d + 1 to d + 1,000). Regions: r_in the wound, r_ring the wound
dilated by 2 less the wound, r_out outside the wound's and the twin's footprints, r_young and r_twin the patches. Extra
loss under corruption: (regrow8 - regrow+cue8) for the arm, less the same for the cue arm. Net effect of a change on the
young patch: r_young(twin4@d) - (1 - r_young(regrow8 at d + 2,000)), regrow8 being every arm's no-change counterfactual
for the arms without the signal (design.py).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be003 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
S4 = tuple(x for x in ALL if x[0].startswith("S4"))
F0 = tuple(x for x in ALL if x[0].startswith("F0"))
R8, RL, RC = "regrow8", "regrow8_late", "regrow+cue8"
TWIN = {d: D.run_name("twin", d, "prompt") for d in D.DELAYS}
STATIC = Path(__file__).resolve().parent / "frozen" / "static_map.json"
THR = {"W1": {"match": 0.012, "s4": 0.025, "f0": 0.003},
       "W2": {"interaction": -0.025, "stack": 0.0},
       "W3": {"same": 0.005, "over_inst3": 0.01, "deficit": 0.035},
       "W4": {"loss": 0.015},
       "W5": {"ring_dial": 0.045, "ring_free": 0.01, "out": 0.0025},
       "W6": {"free": 0.02, "told": 0.23},
       "W7": {"item": 0.035, "mean": 0.11},
       "W8": {"d300_mean": 0.07, "closed": 0.04, "open": 0.12}}

STATEMENTS = [
    {"id": "W1", "kind": "in a wound the free window equals the prescribed one",
     "claim": "Inside a regrowing wound, junctions that mature after each contact forms leave the wound's record as close to "
              "the target as a prescribed signal that closes the junctions over the wound does, and as a uniformly short "
              "coupling does; both the free and the prescribed window leave it closer than instant long junctions",
     "rule": "HOLDS if in regrow8 at t = 4,000 mat-300's r_in is within {match} of the dial's and of inst-1's in every unit "
             "for both bodies, and mat-300's and the dial's r_in exceed inst-3's by >= {s4} for S4 in both bodies and by "
             ">= {f0} on average over F0's four items (two arms x two bodies), else FAILS"},
    {"id": "W2", "kind": "the two windows do not add",
     "claim": "The prescribed signal raises a wound's repair more when added to instant long junctions than when added to "
              "maturing ones, and added to maturing junctions it does not raise it",
     "rule": "HOLDS if in regrow8 at t = 4,000, on average over the four unit-body pairs, (mat-dial - mat-300) - (dial - "
             "inst-3) in r_in is <= {interaction} and mat-dial - mat-300 is <= {stack}, else FAILS"},
    {"id": "W3", "kind": "a late signal still repairs a wound",
     "claim": "A signal that arrives 1,000 updates after the wounding still repairs the wound, nearly as well as a prompt "
              "one; with maturing junctions a late signal changes the wound's record by at most 0.005 against the free "
              "window alone",
     "rule": "HOLDS if at t = 4,000 mat-dial's r_in under regrow8_late is within {same} of mat-300's under regrow8 in every "
             "unit for both bodies, and on average over the four unit-body pairs the dial's r_in under regrow8_late exceeds "
             "inst-3's under regrow8 by >= {over_inst3} and is below the dial's under regrow8 by at most {deficit}, else "
             "FAILS"},
    {"id": "W4", "kind": "both windows lose to corrupted cues",
     "claim": "Under scattered cue corruption, maturing junctions and the prescribed signal each lose more of the regrowing "
              "wound's record than the cue arbiter does",
     "rule": "HOLDS if the extra loss in r_in at t = 4,000 ((regrow8 - regrow+cue8) for the arm, less the same for the cue "
             "arm) is >= {loss} for mat-300 and for the dial in every unit for both bodies, else FAILS"},
    {"id": "W5", "kind": "the prescribed signal costs the old tissue it covers; the free window does not",
     "claim": "Under scattered cue corruption the prescribed signal costs the mature tissue around the wound that its "
              "footprint covers, and maturing junctions do not; beyond the footprints neither window, alone or together, "
              "costs the record anything against instant long junctions",
     "rule": "HOLDS if at t = 4,000 the extra loss in r_ring is >= {ring_dial} for the dial and within {ring_free} of 0 for "
             "mat-300 and mat-1000, and under regrow+cue8 the r_out of mat-300, mat-1000, the dial and mat-dial is within "
             "{out} of inst-3's, in every unit for both bodies, else FAILS"},
    {"id": "W6", "kind": "far from the wound the signal re-specifies and maturation does not",
     "claim": "A small group of old tissue far from the wound adopts a re-specified cue with the prescribed signal at every "
              "delay after the wounding, while maturing junctions change nothing there against instant long junctions",
     "rule": "HOLDS if in twin4@0, twin4@300, twin4@1000 and twin4@2000 at d + 2,000, mat-300's and mat-1000's r_twin are "
             "within {free} of inst-3's and the dial's exceeds inst-3's by >= {told}, in every unit for both bodies, else "
             "FAILS"},
    {"id": "W7", "kind": "tissue regrowing when the cue changes adopts the change unprompted",
     "claim": "When a small group's cue is re-specified while the wound around it regrows, maturing junctions adopt more of "
              "the change there than instant long junctions do, with no signal, counted against the same run without the "
              "change",
     "rule": "HOLDS if the change's net effect on the young patch in twin4@0 (r_young at t = 2,000 minus 1 - regrow8's "
             "r_young at t = 2,000) exceeds inst-3's by >= {item} for mat-300 in every unit for both bodies and by >= "
             "{mean} on average over the four unit-body pairs, else FAILS"},
    {"id": "W8", "kind": "the free window closes as the junctions mature; the prescribed one stays open",
     "claim": "Re-specified 300 updates after the wounding, the regrown patch adopts more of the change with slower-maturing "
              "junctions than with faster ones; re-specified 2,000 updates after it, neither maturation time differs from "
              "instant long junctions by more than 0.04 on average, while the prescribed signal still re-specifies the same "
              "patch (each counted against the same run without the change)",
     "rule": "HOLDS if the net effect on the young patch in twin4@300 (at t = 2,300, against regrow8 at 2,300) is larger for "
             "mat-1000 than for mat-300 by >= {d300_mean} on average over the four unit-body pairs, and in twin4@2000 (at "
             "t = 4,000) mat-300's and mat-1000's net effects are each within "
             "{closed} of inst-3's on average over the four pairs while the dial's exceeds inst-3's by >= {open}, else FAILS"},
]
for _s in STATEMENTS:
    _s["rule"] = _s["rule"].format(**THR[_s["id"]])
    _s["thresholds"] = THR[_s["id"]]


def lv(L, u, b, rn, arm, e="r_in", ti=-1):
    return L[u][b][rn][arm][e][ti][0]


def at(rn, t):
    """The index of read t in run rn."""
    run = D.RUNS[D.RUNNAMES.index(rn)]
    return D.run_reads(*run).index(t)


def extra(L, u, b, arm, e):
    return (lv(L, u, b, R8, arm, e) - lv(L, u, b, RC, arm, e)) - (lv(L, u, b, R8, "cue", e) - lv(L, u, b, RC, "cue", e))


def net(L, u, b, arm, d):
    """The change's net effect on the young patch: r_young(twin4@d) - (1 - r_young(regrow8 at d + 2,000)); the signal
    arms against their alias."""
    cf = D.ALIAS.get(arm, arm)
    return lv(L, u, b, TWIN[d], arm, "r_young") - (1.0 - lv(L, u, b, R8, cf, "r_young", at(R8, d + D.HORIZON)))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def score(L):
    S = {}
    t = THR["W1"]
    v = {f"{u}/{b}": {"mat-300_minus_dial": lv(L, u, b, R8, "mat-300") - lv(L, u, b, R8, "dial"),
                      "mat-300_minus_inst-1": lv(L, u, b, R8, "mat-300") - lv(L, u, b, R8, "inst-1"),
                      "mat-300_minus_inst-3": lv(L, u, b, R8, "mat-300") - lv(L, u, b, R8, "inst-3"),
                      "dial_minus_inst-3": lv(L, u, b, R8, "dial") - lv(L, u, b, R8, "inst-3")} for u, b in ALL}
    f0 = mean(v[f"{u}/{b}"][k] for u, b in F0 for k in ("mat-300_minus_inst-3", "dial_minus_inst-3"))
    ok = all(abs(x["mat-300_minus_dial"]) <= t["match"] and abs(x["mat-300_minus_inst-1"]) <= t["match"] for x in v.values()) \
        and all(v[f"{u}/{b}"][k] >= t["s4"] for u, b in S4 for k in ("mat-300_minus_inst-3", "dial_minus_inst-3")) and f0 >= t["f0"]
    S["W1"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v, "F0_mean_over_inst-3": f0}

    t = THR["W2"]
    v = {f"{u}/{b}": {"interaction": (lv(L, u, b, R8, "mat-dial") - lv(L, u, b, R8, "mat-300"))
                                     - (lv(L, u, b, R8, "dial") - lv(L, u, b, R8, "inst-3")),
                      "mat-dial_minus_mat-300": lv(L, u, b, R8, "mat-dial") - lv(L, u, b, R8, "mat-300")} for u, b in ALL}
    mi, ms = mean(x["interaction"] for x in v.values()), mean(x["mat-dial_minus_mat-300"] for x in v.values())
    S["W2"] = {"verdict": "HOLDS" if (mi <= t["interaction"] and ms <= t["stack"]) else "FAILS", "items": v,
               "mean_interaction": mi, "mean_mat-dial_minus_mat-300": ms}

    t = THR["W3"]
    v = {f"{u}/{b}": {"mat-dial_late_minus_mat-300": lv(L, u, b, RL, "mat-dial") - lv(L, u, b, R8, "mat-300"),
                      "dial_late_minus_inst-3": lv(L, u, b, RL, "dial") - lv(L, u, b, R8, "inst-3"),
                      "dial_late_minus_prompt": lv(L, u, b, RL, "dial") - lv(L, u, b, R8, "dial")} for u, b in ALL}
    mo, md = mean(x["dial_late_minus_inst-3"] for x in v.values()), mean(x["dial_late_minus_prompt"] for x in v.values())
    ok = all(abs(x["mat-dial_late_minus_mat-300"]) <= t["same"] for x in v.values()) and mo >= t["over_inst3"] and md >= -t["deficit"]
    S["W3"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v, "mean_dial_late_minus_inst-3": mo,
               "mean_dial_late_minus_prompt": md}

    t = THR["W4"]
    v = {f"{u}/{b}/{a}": extra(L, u, b, a, "r_in") for u, b in ALL for a in ("mat-300", "dial")}
    S["W4"] = {"verdict": "HOLDS" if min(v.values()) >= t["loss"] else "FAILS", "extra_loss_r_in": v,
               "reported_extra_loss_r_in": {f"{u}/{b}/{a}": extra(L, u, b, a, "r_in") for u, b in ALL
                                            for a in ("inst-1", "inst-1.5", "inst-3", "mat-1000", "mat-dial")}}

    t = THR["W5"]
    ring = {f"{u}/{b}/{a}": extra(L, u, b, a, "r_ring") for u, b in ALL for a in ("dial", "mat-300", "mat-1000")}
    out = {f"{u}/{b}/{a}": lv(L, u, b, RC, a, "r_out") - lv(L, u, b, RC, "inst-3", "r_out") for u, b in ALL
           for a in ("mat-300", "mat-1000", "dial", "mat-dial")}
    ok = all(x >= t["ring_dial"] for k, x in ring.items() if k.endswith("/dial")) \
        and all(abs(x) <= t["ring_free"] for k, x in ring.items() if not k.endswith("/dial")) \
        and all(abs(x) <= t["out"] for x in out.values())
    S["W5"] = {"verdict": "HOLDS" if ok else "FAILS", "extra_loss_r_ring": ring, "r_out_minus_inst-3": out}

    t = THR["W6"]
    v = {f"{u}/{b}/d{d}": {a: lv(L, u, b, TWIN[d], a, "r_twin") - lv(L, u, b, TWIN[d], "inst-3", "r_twin")
                           for a in ("mat-300", "mat-1000", "dial")} for u, b in ALL for d in D.DELAYS}
    ok = all(abs(x["mat-300"]) <= t["free"] and abs(x["mat-1000"]) <= t["free"] and x["dial"] >= t["told"] for x in v.values())
    S["W6"] = {"verdict": "HOLDS" if ok else "FAILS", "r_twin_minus_inst-3": v}

    t = THR["W7"]
    v = {f"{u}/{b}": net(L, u, b, "mat-300", 0) - net(L, u, b, "inst-3", 0) for u, b in ALL}
    ok = min(v.values()) >= t["item"] and mean(v.values()) >= t["mean"]
    S["W7"] = {"verdict": "HOLDS" if ok else "FAILS", "net_mat-300_minus_inst-3": v, "mean": mean(v.values()),
               "reported_net": {f"{u}/{b}/{a}": net(L, u, b, a, 0) for u, b in ALL for a in D.ARMS}}

    t = THR["W8"]
    v300 = {f"{u}/{b}": net(L, u, b, "mat-1000", 300) - net(L, u, b, "mat-300", 300) for u, b in ALL}
    c = {a: {f"{u}/{b}": net(L, u, b, a, 2000) - net(L, u, b, "inst-3", 2000) for u, b in ALL} for a in ("mat-300", "mat-1000", "dial")}
    cm = {a: mean(x.values()) for a, x in c.items()}
    ok = mean(v300.values()) >= t["d300_mean"] \
        and abs(cm["mat-300"]) <= t["closed"] and abs(cm["mat-1000"]) <= t["closed"] and cm["dial"] >= t["open"]
    S["W8"] = {"verdict": "HOLDS" if ok else "FAILS", "d300_net_mat-1000_minus_mat-300": v300, "d300_mean": mean(v300.values()),
               "d2000_net_minus_inst-3": c, "d2000_means": cm,
               "reported_net": {f"{u}/{b}/d{d}/{a}": net(L, u, b, a, d) for u, b in ALL for d in D.DELAYS for a in D.ARMS}}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "static_map": json.loads(STATIC.read_text()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
