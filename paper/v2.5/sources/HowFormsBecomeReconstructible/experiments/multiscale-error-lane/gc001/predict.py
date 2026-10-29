"""GC001's registered statements and their scoring, written before any development outcome.

python -m gc001.predict   (writes gc001/frozen/predictions.json)

Thresholds were set from engineering probe P29 (32 cases on blocks 900690-900693 under tag mse-p29, disclosed in
REGISTRATION_GC001.md) under BE002's rule; probes/p29b_gc001_margins.py prints every item, its SD over P29's four
blocks and the margin at these thresholds. SD_block = max(the item's own SD, the RMS of the SDs over the part's items);
an every-item part sits >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P29's worst item; a pooled part (the mean over its
items) uses the SD over blocks of the pooled per-block value. No bound is set from an item whose SD is 0.

Scored by gc001.analyze on unrounded block means over the 16 development blocks, at t = 4,000. Runs: none8@s (the steady
state, the anchors reading the cue field at a noisy position with error s sites), scatter8@s (the same count of wrong
anchors placed at random), change4@s (a legitimate change of a 4 x 4 patch), memory4@s (a 4 x 4 memory damage).
Endpoints: r_all (the record's agreement with the target over the sheet), r_band and r_int (in the band of sites adjacent
to a boundary and in the interior), walls (the record's domain walls relative to the target's, minus 1), r_in (inside
the patch), opened (the share of cells committed over the window). The loss of an arm is the cue arm's r_all minus the
arm's, in the same run. An item is one unit and body (and sigma or arm where a part names several).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from gc001 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
NARROW = tuple((u, b) for u, b in ALL if not u.startswith("F0"))
WIDE = tuple((u, b) for u, b in ALL if u.startswith("F0"))
RULE_K = 3 * np.sqrt(1 / 4 + 1 / 16)

THR = {"G1": {"match": 0.003},
       "G2": {"floor": 0.003, "loss1": 0.03, "rise": 0.08},
       "G3": {"step": 0.02},
       "G4": {"coherent": 0.006},
       "G5": {"same": 0.008},
       "G6": {"band": 0.03},
       "G7": {"rough": 0.09},
       "G8": {"blur": 0.15},
       "G9": {"copy": 0.02},
       "G10": {"lo": 0.45, "hi": 1.35, "min_static": 0.02, "mean_lo": 0.8, "mean_hi": 1.05},
       "G11": {"narrow": 0.014, "wide": 0.003}}
STATIC = json.loads((Path(__file__).resolve().parent / "frozen" / "static_map.json").read_text())


def nm(s, sigma, size=8):
    return D.run_name(s, size, sigma)


def lv(B, u, b, run, arm, e="r_all"):
    return np.asarray(B[u][b][run][arm][e], float)


def loss(B, u, b, run, arm, e="r_all"):
    return lv(B, u, b, run, "cue", e) - lv(B, u, b, run, arm, e)


def static_share(pattern, sigma, arm, cond="graded"):
    return STATIC["patterns"][pattern]["sigmas"][f"{sigma:g}"]["trigger"][f"{cond}/{arm}"]["all"]


def pattern_loss(B, pattern, sigma, arm):
    """The run's loss pooled over the pattern's four unit-body pairs, per block."""
    return np.mean([loss(B, u, b, nm("none", sigma), arm) for u, b in ALL if u.startswith(pattern)], 0)


def part(sid, name, items, thr, sense, pooled, f):
    return {"sid": sid, "name": name, "items": items, "thr": thr, "sense": sense, "pooled": pooled, "f": f}


T = THR
G10_ITEMS = tuple((pt, s, a) for pt in D.PATTERNS for s in (0.5, 1.0, 2.0) for a in D.BIO
                  if static_share(pt, s, a) >= T["G10"]["min_static"])
G10_MID, G10_HALF = (T["G10"]["lo"] + T["G10"]["hi"]) / 2, (T["G10"]["hi"] - T["G10"]["lo"]) / 2
PARTS = [
    part("G1", "G1 bio-3 - cue r_all, sigma 0.5 and 1", tuple((u, b, s) for u, b in ALL for s in (0.5, 1.0)), T["G1"]["match"], "abs", False,
         lambda B, u, b, s: lv(B, u, b, nm("none", s), "bio-3") - lv(B, u, b, nm("none", s), "cue")),
    part("G2", "G2 loss of bio-1 at sigma 1, every item", ALL, T["G2"]["floor"], "ge", False,
         lambda B, u, b: loss(B, u, b, nm("none", 1.0), "bio-1")),
    part("G2", "G2 loss of bio-1 at sigma 1 (pooled)", ALL, T["G2"]["loss1"], "ge", True,
         lambda B, u, b: loss(B, u, b, nm("none", 1.0), "bio-1")),
    part("G2", "G2 loss of bio-1, sigma 2 minus sigma 1 (pooled)", ALL, T["G2"]["rise"], "ge", True,
         lambda B, u, b: loss(B, u, b, nm("none", 2.0), "bio-1") - loss(B, u, b, nm("none", 1.0), "bio-1")),
    *(part("G3", f"G3 r_all {hi} - {lo} at sigma 2 (pooled)", ALL, T["G3"]["step"], "ge", True,
           lambda B, u, b, lo=lo, hi=hi: lv(B, u, b, nm("none", 2.0), hi) - lv(B, u, b, nm("none", 2.0), lo))
      for lo, hi in (("bio-1", "bio-1.5"), ("bio-1.5", "bio-2"), ("bio-2", "bio-3"))),
    part("G4", "G4 F0 graded - scatter r_all, bio-1 and bio-1.5, sigma 2 and 3 (pooled)",
         tuple((u, b, a, s) for u, b in WIDE for a in ("bio-1", "bio-1.5") for s in (2.0, 3.0)), -T["G4"]["coherent"], "le", True,
         lambda B, u, b, a, s: lv(B, u, b, nm("none", s), a) - lv(B, u, b, nm("scatter", s), a)),
    part("G5", "G5 S4/LB graded - scatter r_all, bio-1, sigma 1 and 2 (pooled)", tuple((u, b, s) for u, b in NARROW for s in (1.0, 2.0)),
         T["G5"]["same"], "abs", True,
         lambda B, u, b, s: lv(B, u, b, nm("none", s), "bio-1") - lv(B, u, b, nm("scatter", s), "bio-1")),
    part("G6", "G6 bio-1 loss in the band minus in the interior, sigma 1", ALL, T["G6"]["band"], "ge", False,
         lambda B, u, b: loss(B, u, b, nm("none", 1.0), "bio-1", "r_band") - loss(B, u, b, nm("none", 1.0), "bio-1", "r_int")),
    part("G7", "G7 walls bio-1 - cue, sigma 1", ALL, T["G7"]["rough"], "ge", False,
         lambda B, u, b: lv(B, u, b, nm("none", 1.0), "bio-1", "walls") - lv(B, u, b, nm("none", 1.0), "cue", "walls")),
    part("G8", "G8 F0 change4 r_in bio-1, sigma 0 minus sigma 2", WIDE, T["G8"]["blur"], "ge", False,
         lambda B, u, b: lv(B, u, b, nm("change", 0.0, 4), "bio-1", "r_in") - lv(B, u, b, nm("change", 2.0, 4), "bio-1", "r_in")),
    part("G9", "G9 memory4 r_in cue arm, sigma 0 minus sigma 2 (pooled)", ALL, T["G9"]["copy"], "ge", True,
         lambda B, u, b: lv(B, u, b, nm("memory", 0.0, 4), "cue", "r_in") - lv(B, u, b, nm("memory", 2.0, 4), "cue", "r_in")),
    part("G10", "G10 run loss / static share - mid, per pattern (graded, static >= 0.02)", G10_ITEMS, G10_HALF, "abs", False,
         lambda B, pt, s, a: pattern_loss(B, pt, s, a) / static_share(pt, s, a) - G10_MID),
    part("G10", "G10 mean over those items of run loss / static share - mean mid (pooled)", G10_ITEMS,
         (T["G10"]["mean_hi"] - T["G10"]["mean_lo"]) / 2, "abs", True,
         lambda B, pt, s, a: pattern_loss(B, pt, s, a) / static_share(pt, s, a) - (T["G10"]["mean_lo"] + T["G10"]["mean_hi"]) / 2),
    part("G11", "G11 bio-3 loss at sigma 2, S4 and LB", NARROW, T["G11"]["narrow"], "ge", False,
         lambda B, u, b: loss(B, u, b, nm("none", 2.0), "bio-3")),
    part("G11", "G11 bio-3 - cue r_all at sigma 2 and 3, F0", tuple((u, b, s) for u, b in WIDE for s in (2.0, 3.0)), T["G11"]["wide"], "abs", False,
         lambda B, u, b, s: lv(B, u, b, nm("none", s), "bio-3") - lv(B, u, b, nm("none", s), "cue")),
]

STATEMENTS = [
    {"id": "G1", "kind": "long coupling ignores positional error of up to one site",
     "claim": "With the anchors reading the cue field at a position wrong by up to a site (sigma 0.5 or 1), the detector at "
              "coupling length 3 keeps the record over the sheet as the cue arbiter alone does",
     "rule": "HOLDS if at t = 4,000 in none8@0.5 and none8@1, bio-3's r_all is within {match} of the cue arm's in every unit "
             "for both bodies, else FAILS"},
    {"id": "G2", "kind": "short coupling loses to positional error, more as it grows",
     "claim": "At coupling length 1 positional error of one site costs the record over the sheet in every unit, and an error "
              "of two sites costs more",
     "rule": "HOLDS if at t = 4,000 the cue arm's r_all minus bio-1's in none8@1 is >= {floor} in every unit for both bodies "
             "and >= {loss1} on average over the twelve unit-body pairs, and that loss at sigma 2 exceeds the loss at sigma 1 by "
             ">= {rise} on average, else FAILS"},
    {"id": "G3", "kind": "the loss falls with the coupling length",
     "claim": "Under positional error of two sites the record over the sheet rises at each step of the coupling ladder "
              "1 < 1.5 < 2 < 3",
     "rule": "HOLDS if at t = 4,000 in none8@2, on average over the twelve unit-body pairs, r_all rises by >= {step} at each "
             "step bio-1 < bio-1.5 < bio-2 < bio-3, else FAILS"},
    {"id": "G4", "kind": "on wide domains coherent errors cost more than scattered ones",
     "claim": "On wide domains, positional misreads cost short and middle coupling more of the record over the sheet than the "
              "same number of wrong anchors placed at random",
     "rule": "HOLDS if at t = 4,000, on average over F0's four unit-body pairs, the arms bio-1 and bio-1.5 and sigma 2 and 3, "
             "r_all in none8@sigma minus r_all in scatter8@sigma is <= -{coherent}, else FAILS"},
    {"id": "G5", "kind": "on narrow patterns coherence adds nothing",
     "claim": "On stripes and labyrinths, positional misreads cost the short-coupled record over the sheet as much as the same "
              "number of wrong anchors placed at random",
     "rule": "HOLDS if at t = 4,000, on average over the eight S4 and LB unit-body pairs and sigma 1 and 2, bio-1's r_all in "
             "none8@sigma minus in scatter8@sigma is within {same} of 0, else FAILS"},
    {"id": "G6", "kind": "the loss sits at the boundaries",
     "claim": "Under positional error of one site the short-coupled record loses more in the band of sites next to a boundary "
              "than in the interior",
     "rule": "HOLDS if at t = 4,000 in none8@1, bio-1's loss (the cue arm's agreement minus bio-1's) in r_band exceeds its "
             "loss in r_int by >= {band} in every unit for both bodies, else FAILS"},
    {"id": "G7", "kind": "short coupling roughens the boundaries",
     "claim": "Under positional error of one site the short-coupled record carries more domain walls, relative to the "
              "target's, than the cue arbiter's",
     "rule": "HOLDS if at t = 4,000 in none8@1, bio-1's walls exceed the cue arm's by >= {rough} in every unit for both "
             "bodies, else FAILS"},
    {"id": "G8", "kind": "positional error lowers the adoption of a legitimate change",
     "claim": "On domains, at coupling length 1, a legitimate change of a 4 x 4 group is adopted less when the anchors read "
              "the new cue field two sites wrong",
     "rule": "HOLDS if in every F0 unit for both bodies bio-1's r_in at t = 4,000 in change4@0 exceeds its r_in in change4@2 "
             "by >= {blur}, else FAILS"},
    {"id": "G9", "kind": "the cue arbiter repairs memory damage with the misread cues",
     "claim": "The cue arbiter repairs a 4 x 4 memory damage less when its anchors read the cue field two sites wrong",
     "rule": "HOLDS if on average over the twelve unit-body pairs the cue arm's r_in at t = 4,000 in memory4@0 exceeds its "
             "r_in in memory4@2 by >= {copy}, else FAILS"},
    {"id": "G10", "kind": "the static map predicts the loss",
     "claim": "Wherever the registered static map flags at least {min_static} of the sheet under graded cues (sigma up to 2), "
              "the run's loss over the sheet lies between {lo} and {hi} times the static share, and between {mean_lo} and "
              "{mean_hi} times it on average",
     "rule": "HOLDS if for every pattern, sigma in (0.5, 1, 2) and bioelectric arm whose static share (graded) is >= "
             "{min_static}, the cue arm's r_all minus the arm's in none8@sigma at t = 4,000, averaged over the pattern's four "
             "unit-body pairs, divided by the static share, lies in [{lo}, {hi}], and the mean of that ratio over those items "
             "lies in [{mean_lo}, {mean_hi}], else FAILS"},
    {"id": "G11", "kind": "long coupling's tolerance depends on the pattern's scale",
     "claim": "At coupling length 3 positional error of two sites costs the record on stripes and labyrinths, but on domains "
              "even an error of three sites costs no more than {wide} of the sheet",
     "rule": "HOLDS if at t = 4,000 the cue arm's r_all minus bio-3's in none8@2 is >= {narrow} in every S4 and LB unit for "
             "both bodies, and bio-3's r_all is within {wide} of the cue arm's in none8@2 and none8@3 in every F0 unit for "
             "both bodies, else FAILS"},
]
for _s in STATEMENTS:
    _s["rule"] = _s["rule"].format(**THR[_s["id"]])
    _s["claim"] = _s["claim"].format(**THR[_s["id"]])
    _s["thresholds"] = THR[_s["id"]]


def values(B, p):
    """Per-block arrays for every item of a part (an item is a tuple; the last members are the part's extra keys)."""
    return {it: p["f"](B, *it) for it in p["items"]}


def evaluate(B, p):
    vals = values(B, p)
    if p["pooled"]:
        x = float(np.mean([v.mean() for v in vals.values()]))
        xs = [x]
    else:
        xs = [float(v.mean()) for v in vals.values()]
    thr = p["thr"]
    ok = {"ge": all(x >= thr for x in xs), "le": all(x <= thr for x in xs), "abs": all(abs(x) <= thr for x in xs)}[p["sense"]]
    return ok, ({"pooled": round(xs[0], 6)} if p["pooled"] else {"/".join(map(str, it)): round(float(v.mean()), 6) for it, v in vals.items()})


def score(B):
    out = {}
    for s in STATEMENTS:
        parts = [p for p in PARTS if p["sid"] == s["id"]]
        res = [(p["name"], *evaluate(B, p)) for p in parts]
        out[s["id"]] = {"verdict": "HOLDS" if all(ok for _, ok, _ in res) else "FAILS",
                        "parts": {name: {"holds": ok, "values": v} for name, ok, v in res}}
    return out


if __name__ == "__main__":
    lane = Path(__file__).resolve().parents[1]
    path = lane / "gc001" / "frozen" / "predictions.json"
    path.write_text(json.dumps({"study": D.STUDY, "design_digest": D.digest(),
                                "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "statements": STATEMENTS}, indent=1) + "\n")
    print(path)
