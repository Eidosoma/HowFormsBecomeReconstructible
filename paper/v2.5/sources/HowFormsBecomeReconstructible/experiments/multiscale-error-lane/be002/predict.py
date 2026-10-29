"""BE002's registered statements and their scoring, written before any development outcome.

python -m be002.predict   (writes be002/frozen/predictions.json)

Thresholds were set from engineering probe P24 (32 cases on blocks 900640-900643 under tag mse-p24, disclosed in
REGISTRATION_BE002.md), with margins from the SD over P24's blocks of each paired quantity (never the spread over units,
which share cases): at least 3 x 0.56 SD_block for a statement that must hold in every unit and body (0.56 =
sqrt(1/4 + 1/16), the SD of a 4-block mean's difference from a 16-block mean, in block SDs). S7 compares the run with the
static map registered beside these statements (frozen/static_map.json, python -m be002.static). Scored by be002.analyze on
block means over the 16 development blocks at t = 4,000 unless stated. r_in: the record's agreement with the correct
target inside the patch; r_fp / r_out: inside / outside the signal's footprint; r_all: over the sheet; opened_out: the
share of cells committed outside the footprint, mean over the window. Runs are named situation + patch side + signal
('_sig': on at updates 1-1,000; '_late': on at 1,001-2,000).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be002 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
STATIC = Path(__file__).resolve().parent / "frozen" / "static_map.json"
STATIC_RUNS = (("change4_sig", "4"), ("change8_sig", "8"))
STATIC_MIN = 0.33
THR = {"S1": {"level": 0.38, "over_bio3": 0.17},
       "S2": {"r_in": 0.045, "r_fp": 0.015},
       "S3": {"r_out": 0.002, "opened_out": 0.0005},
       "S4": {"below_bio3": 0.06, "local_over_global": 0.055},
       "S5": {"adopt_below": 0.08, "rfp_above": 0.013},
       "S6": {"below_prompt": 0.12, "over_bio3": 0.13},
       "S7": {"lo4": -0.155, "hi4": 0.12, "lo8": -0.065, "hi8": 0.03},
       "S8": {"r_all": 0.002}}

STATEMENTS = [
    {"id": "S1", "kind": "a regime signal buys small-group re-specification where it is sent",
     "claim": "With the signal, the local dial (coupling length 3, junctions touching the footprint closed to length 1 "
              "while the signal is on) repairs a 4 x 4 memory damage and adopts a 4 x 4 legitimate change, far above the "
              "long coupling it rests at",
     "rule": "HOLDS if for memory4_sig and change4_sig, in every unit for both bodies, dial-local's r_in is >= {level} and "
             "exceeds bio-3's by >= {over_bio3}, else FAILS"},
    {"id": "S2", "kind": "inside the footprint the dial is the short coupling, for good and ill",
     "claim": "Inside the signalled footprint the local dial behaves as the short coupling everywhere would: it repairs "
              "and adopts as bio-1 does, and under a sham signal over scattered cue corruption it loses as much of the "
              "record inside the footprint as bio-1",
     "rule": "HOLDS if, in every unit for both bodies, dial-local's r_in is within {r_in} of bio-1's for memory4_sig, "
             "change4_sig and change8_sig, and under cue8_sig its r_fp is within {r_fp} of bio-1's, else FAILS"},
    {"id": "S3", "kind": "outside the footprint nothing changes",
     "claim": "Under a sham signal over scattered cue corruption, the local dial leaves the record outside the footprint "
              "as the long coupling does and commits almost no cell there",
     "rule": "HOLDS if under cue8_sig, in every unit for both bodies, dial-local's r_out is within {r_out} of bio-3's and "
             "its opened_out is <= {opened_out}, else FAILS"},
    {"id": "S4", "kind": "a systemic alarm costs the whole sheet",
     "claim": "A sham signal that shortens the coupling over the whole sheet loses the record everywhere under scattered "
              "cue corruption, while the same signal confined to a footprint loses far less",
     "rule": "HOLDS if under cue8_sig, in every unit for both bodies, dial-global's r_all is <= bio-3's - {below_bio3} and "
             "dial-local's r_all exceeds dial-global's by >= {local_over_global}, else FAILS"},
    {"id": "S5", "kind": "a permission gate moves the trade-off inside the footprint; it does not escape it",
     "claim": "A permission gate at the matched coupling (1.5; new commitments only inside the footprint while the signal "
              "is on) adopts less of a small change than the local dial and loses less under a sham over scattered "
              "corruption: inside the signalled region the detector still sits on BE001's one-length trade-off",
     "rule": "HOLDS if, in every unit for both bodies, permit-local's r_in for change4_sig is below dial-local's by >= "
             "{adopt_below}, and under cue8_sig its r_fp exceeds dial-local's by >= {rfp_above}, else FAILS"},
    {"id": "S6", "kind": "the signal must come promptly",
     "claim": "A signal that arrives 1,000 updates after a 4 x 4 memory damage repairs it less than a prompt signal, "
              "though more than none: while the damage stands unrepaired the body follows the damaged record, and the "
              "late repair loses the body's help",
     "rule": "HOLDS if, averaged over the twelve unit-body pairs, dial-local's r_in for memory4_late is below its r_in for "
             "memory4_sig by >= {below_prompt} and above bio-3's for memory4_late by >= {over_bio3}, else FAILS"},
    {"id": "S7", "kind": "the static voltage map predicts the run (registered before the run)",
     "claim": "With the signal, the steady-state voltage map with each arm's conductances, computed with no dynamics, "
              "predicts the share of a legitimate change adopted wherever that share is 0.33 or more",
     "rule": "HOLDS if for dial-local, dial-global and permit-local on change4_sig and change8_sig, wherever the "
             "registered static adoption share (frozen/static_map.json) is >= 0.33, the run's r_in minus that share lies "
             "within [{lo4}, {hi4}] for change4_sig and within [{lo8}, {hi8}] for change8_sig, in every unit for both "
             "bodies, else FAILS"},
    {"id": "S8", "kind": "a false signal over clean tissue costs nothing",
     "claim": "A sham signal over tissue whose cues are intact changes nothing: there is no disagreement to act on",
     "rule": "HOLDS if under none8_sig every signal arm's r_all is within {r_all} of its own r_all under none8, in every "
             "unit for both bodies, else FAILS"},
]
INPUTS = {
    "S1": "P24: dial-local 0.502-0.535 (memory4_sig) and 0.490-0.523 (change4_sig); minus bio-3 +0.285 to +0.440 and "
          "+0.375 to +0.441",
    "S2": "P24: dial-local - bio-1 -0.008 to 0.000 (memory4_sig), -0.010 to -0.004 (change4_sig), -0.006 to -0.003 "
          "(change8_sig); r_fp +0.005 to +0.009",
    "S3": "P24: r_out -0.0001 to +0.0006; opened_out at most 2e-5 in any block (four-block means <= 1e-5). The opened_out "
          "bound 0.0005 is a declared floor, about 14 block-SDs above BE001's bio-3 sheet-wide opened under cue8 (2.4e-5 to "
          "3.2e-5, SD up to 3.5e-5 over 16 blocks; results/be001/summary_*.json)",
    "S4": "P24: dial-global - bio-3 -0.094 to -0.069 (dial-global - bio-1 -0.001 to +0.001); dial-local - dial-global "
          "+0.063 to +0.084",
    "S5": "P24: permit - local -0.188 to -0.176 (change4_sig); r_fp permit - local +0.027 to +0.037",
    "S6": "P24: means over pairs -0.149 and +0.212 (pairs -0.232 to -0.023 and +0.053 to +0.416)",
    "S7": "P24: run - static -0.037 to -0.002 (change4_sig) and -0.026 to -0.010 (change8_sig)",
    "S8": "P24: dial-local 0.0000-0.0001, dial-global 0.0000-0.0007, permit-local 0 in every block (no cell differed)"}
for _s in STATEMENTS:
    _s["rule"] = _s["rule"].format(**THR[_s["id"]])
    _s["thresholds"] = THR[_s["id"]]
    _s["inputs"] = INPUTS[_s["id"]]


def lv(L, u, b, rn, arm, e="r_in", ti=-1):
    return L[u][b][rn][arm][e][ti][0]


def op(L, u, b, rn, arm, key="opened_out"):
    return L[u][b][rn][arm][key][0]


def score(L, static=None):
    if static is None:
        static = json.loads(STATIC.read_text())
    S, R = {}, lambda x: round(x, 4)

    t = THR["S1"]
    v = {f"{u}/{b}/{rn}": {"dial-local": lv(L, u, b, rn, "dial-local"),
                           "minus_bio-3": R(lv(L, u, b, rn, "dial-local") - lv(L, u, b, rn, "bio-3"))}
         for u, b in ALL for rn in ("memory4_sig", "change4_sig")}
    ok = all(x["dial-local"] >= t["level"] and x["minus_bio-3"] >= t["over_bio3"] for x in v.values())
    S["S1"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    t = THR["S2"]
    v = {f"{u}/{b}/{rn}": R(lv(L, u, b, rn, "dial-local") - lv(L, u, b, rn, "bio-1"))
         for u, b in ALL for rn in ("memory4_sig", "change4_sig", "change8_sig")}
    w = {f"{u}/{b}/cue8_sig": R(lv(L, u, b, "cue8_sig", "dial-local", "r_fp") - lv(L, u, b, "cue8_sig", "bio-1", "r_fp"))
         for u, b in ALL}
    ok = max(abs(x) for x in v.values()) <= t["r_in"] and max(abs(x) for x in w.values()) <= t["r_fp"]
    S["S2"] = {"verdict": "HOLDS" if ok else "FAILS", "r_in_dial-local_minus_bio-1": v, "r_fp_dial-local_minus_bio-1": w}

    t = THR["S3"]
    v = {f"{u}/{b}": {"r_out_minus_bio-3": R(lv(L, u, b, "cue8_sig", "dial-local", "r_out") - lv(L, u, b, "cue8_sig", "bio-3", "r_out")),
                      "opened_out": round(op(L, u, b, "cue8_sig", "dial-local"), 6)} for u, b in ALL}
    ok = all(abs(x["r_out_minus_bio-3"]) <= t["r_out"] and x["opened_out"] <= t["opened_out"] for x in v.values())
    S["S3"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    t = THR["S4"]
    v = {f"{u}/{b}": {"global_minus_bio-3": R(lv(L, u, b, "cue8_sig", "dial-global", "r_all") - lv(L, u, b, "cue8_sig", "bio-3", "r_all")),
                      "local_minus_global": R(lv(L, u, b, "cue8_sig", "dial-local", "r_all") - lv(L, u, b, "cue8_sig", "dial-global", "r_all"))}
         for u, b in ALL}
    ok = all(x["global_minus_bio-3"] <= -t["below_bio3"] and x["local_minus_global"] >= t["local_over_global"] for x in v.values())
    S["S4"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    t = THR["S5"]
    v = {f"{u}/{b}": {"change4_sig_permit_minus_local": R(lv(L, u, b, "change4_sig", "permit-local") - lv(L, u, b, "change4_sig", "dial-local")),
                      "cue8_sig_rfp_permit_minus_local": R(lv(L, u, b, "cue8_sig", "permit-local", "r_fp") - lv(L, u, b, "cue8_sig", "dial-local", "r_fp"))}
         for u, b in ALL}
    ok = all(x["change4_sig_permit_minus_local"] <= -t["adopt_below"] and x["cue8_sig_rfp_permit_minus_local"] >= t["rfp_above"]
             for x in v.values())
    S["S5"] = {"verdict": "HOLDS" if ok else "FAILS", "items": v}

    t = THR["S6"]
    v = {f"{u}/{b}": {"late_minus_prompt": R(lv(L, u, b, "memory4_late", "dial-local") - lv(L, u, b, "memory4_sig", "dial-local")),
                      "late_minus_bio-3": R(lv(L, u, b, "memory4_late", "dial-local") - lv(L, u, b, "memory4_late", "bio-3"))}
         for u, b in ALL}
    mp = R(sum(x["late_minus_prompt"] for x in v.values()) / len(v))
    mb = R(sum(x["late_minus_bio-3"] for x in v.values()) / len(v))
    ok = mp <= -t["below_prompt"] and mb >= t["over_bio3"]
    S["S6"] = {"verdict": "HOLDS" if ok else "FAILS", "mean_late_minus_prompt": mp, "mean_late_minus_bio-3": mb, "items": v}

    t = THR["S7"]
    v, ok, rng = {}, True, {}
    for rn, z in STATIC_RUNS:
        for arm in D.SIGNAL_ARMS:
            share = static["adoption"][arm][z]
            if share < STATIC_MIN:
                continue
            for u, b in ALL:
                x = R(lv(L, u, b, rn, arm) - share)
                v[f"{u}/{b}/{rn}/{arm}"] = x
                ok &= t[f"lo{z}"] <= x <= t[f"hi{z}"]
        xs = [x for k, x in v.items() if f"/{rn}/" in k]
        rng[rn] = [min(xs), max(xs)] if xs else None
    ok = ok and bool(v)
    S["S7"] = {"verdict": "HOLDS" if ok else "FAILS", "run_minus_static": v, "range": rng}

    t = THR["S8"]
    v = {f"{u}/{b}/{arm}": R(lv(L, u, b, "none8_sig", arm, "r_all") - lv(L, u, b, "none8", arm, "r_all"))
         for u, b in ALL for arm in D.SIGNAL_ARMS}
    ok = max(abs(x) for x in v.values()) <= t["r_all"]
    S["S8"] = {"verdict": "HOLDS" if ok else "FAILS", "sham_minus_none": v}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "static_map": json.loads(STATIC.read_text()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
