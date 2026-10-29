"""LR005's registered statements and their scoring, written before any development outcome.

python -m lr005.predict   (writes lr005/frozen/predictions.json)

Thresholds were set from engineering probe P20 (32 cases on blocks 900760-900763 under tag mse-p20, disclosed in
REGISTRATION_LR005.md), with margins for 128 cases. Scored by lr005.analyze on block means over the 16 development
blocks at t = 4,000. r_in: the first record's agreement with the correct target inside the 8 x 8 patch (for change, the
new target; r_in_old, the old one); r_all: over the sheet; opened: the share of cells in a community zone over the
window. Gains are the body's read gain on the first record.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr005 import design as D  # noqa: E402

COPIES = ("record+parity", "body", "vote2r", "cue", "vote3")       # every arm without the community rule
FIELD = (("S4_t1", "dw"), ("S4_t1", "li4"), ("LB_t1", "dw"), ("LB_t1", "li4"))
OWN = (("S4_t0", "li4"), ("F0_t0", "dw"))                           # quiet tissue, a pattern the body holds by itself
ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)

STATEMENTS = [
    {"id": "C1", "kind": "a consistent memory error recruits the body",
     "claim": "When the body reads the record strongly, a consistently corrupted patch of the record pulls the body with "
              "it, and no copy-based teacher repairs it, not even LR004's two-record vote",
     "rule": "HOLDS if at read gain 0.2 under memory damage every arm without the community rule (record+parity, body, "
             "vote2r, cue, vote3) gives r_in <= 0.40 in every unit for both bodies, else FAILS",
     "inputs": "P20: at most 0.31"},
    {"id": "C2", "kind": "weak reading keeps the body an independent copy",
     "claim": "When the body reads the record weakly, body teaching and the vote repair the same damage where the body "
              "holds the pattern by itself",
     "rule": "HOLDS if under memory damage at read gain 0.05, for li4 on S4 and dw on F0 in quiet tissue, body teaching "
             "gives r_in >= 0.90 and exceeds its own level at gain 0.2 by >= 0.50, and vote2r gives r_in >= 0.75, else FAILS",
     "inputs": "P20: body 1.00 and 0.99 (+0.86, +0.74); vote2r 0.86 and 0.95"},
    {"id": "C3", "kind": "the price of independence",
     "claim": "A body that reads its record weakly writes its own distortions into the record when nothing has happened",
     "rule": "HOLDS if with no event under the full field (S4 and LB, both bodies) body teaching's r_all at gain 0.05 is "
             ">= 0.10 below its r_all at gain 0.2, else FAILS",
     "inputs": "P20: -0.23 to -0.28"},
    {"id": "C4", "kind": "a latched community rule repairs memory damage",
     "claim": "A positional cue that overrules body and record where its neighbours agree, held by a slow latch, repairs a "
              "consistent memory error that every copy-based teacher keeps",
     "rule": "HOLDS if under memory damage community-s gives r_in >= 0.65 in every unit, body and gain, and at gain 0.2 "
             "exceeds every arm without the community rule by >= 0.30, else FAILS",
     "inputs": "P20: 0.73-0.79; margin 0.45-0.67 at gain 0.2"},
    {"id": "C5", "kind": "only the community rule adopts a legitimate change",
     "claim": "A coherent re-specification of the cue is adopted by the community rule and refused by every majority or "
              "arbitration rule",
     "rule": "HOLDS if under change community-s gives r_in >= 0.62 in every unit, body and gain, while record+parity, "
             "vote2r, cue and vote3 give r_in <= 0.25, else FAILS",
     "inputs": "P20: 0.70-0.77; others at most 0.18"},
    {"id": "C6", "kind": "sensitivity costs false alarms",
     "claim": "The sensitive community rule opens zones on scattered cue corruption and loses agreement there, though "
              "never without an event",
     "rule": "HOLDS if under cue damage community-s's r_all is >= 0.04 below the cue arm's in every unit, body and gain, "
             "and with no event both community arms open zones on <= 0.001 of cells, else FAILS",
     "inputs": "P20: -0.07 to -0.09; 0.000"},
    {"id": "C7", "kind": "caution costs adoption",
     "claim": "The conservative community rule refuses scattered corruption, but adopts a legitimate change and repairs "
              "memory damage only in part",
     "rule": "HOLDS if community-c opens zones on <= 0.002 of cells under cue damage and its r_all is within 0.01 of the "
             "cue arm's there, while under change its r_in is <= 0.50 and under memory damage <= 0.55, in every unit, "
             "body and gain, else FAILS",
     "inputs": "P20: 0.000; within 0.001; at most 0.42; at most 0.50"},
    {"id": "C8", "kind": "shared damage leaves only the surroundings",
     "claim": "A wound that removes body, record and cue together is restored only partly by any rule under the field, and "
              "the record alone keeps chance-level agreement plus what its edge supplies",
     "rule": "HOLDS if under shared damage at read gain 0.2 under the full field (S4 and LB, both bodies) every arm gives "
             "r_in <= 0.90, and record+parity gives r_in <= 0.70 in every unit, body and gain, else FAILS",
     "inputs": "P20: at most 0.79; record+parity 0.62-0.63"},
]


def lv(L, u, b, g, s, arm, e="r_in"):
    return L[u][b][f"{g:g}"][s][arm][e][-1][0]


def score(L):
    S = {}
    v = {f"{u}/{b}/{a}": lv(L, u, b, 0.2, "memory", a) for u, b in ALL for a in COPIES}
    S["C1"] = {"verdict": "HOLDS" if max(v.values()) <= 0.40 else "FAILS", "max": max(v.values()), "r_in": v}

    v = {}
    for u, b in OWN:
        lo, hi = lv(L, u, b, 0.05, "memory", "body"), lv(L, u, b, 0.2, "memory", "body")
        v[f"{u}/{b}"] = {"body@0.05": lo, "body@0.2": hi, "vote2r@0.05": lv(L, u, b, 0.05, "memory", "vote2r")}
    ok = all(x["body@0.05"] >= 0.90 and x["body@0.05"] - x["body@0.2"] >= 0.50 and x["vote2r@0.05"] >= 0.75 for x in v.values())
    S["C2"] = {"verdict": "HOLDS" if ok else "FAILS", "memory": v}

    v = {f"{u}/{b}": round(lv(L, u, b, 0.05, "none", "body", "r_all") - lv(L, u, b, 0.2, "none", "body", "r_all"), 4)
         for u, b in FIELD}
    S["C3"] = {"verdict": "HOLDS" if max(v.values()) <= -0.10 else "FAILS", "body_r_all_0.05_minus_0.2": v}

    lvl = {f"{u}/{b}/{g:g}": lv(L, u, b, g, "memory", "community-s") for u, b in ALL for g in D.GAINS}
    gap = {f"{u}/{b}": round(lv(L, u, b, 0.2, "memory", "community-s") - max(lv(L, u, b, 0.2, "memory", a) for a in COPIES), 4)
           for u, b in ALL}
    S["C4"] = {"verdict": "HOLDS" if min(lvl.values()) >= 0.65 and min(gap.values()) >= 0.30 else "FAILS",
               "community-s": lvl, "margin@0.2": gap}

    cs = {f"{u}/{b}/{g:g}": lv(L, u, b, g, "change", "community-s") for u, b in ALL for g in D.GAINS}
    oth = {f"{u}/{b}/{g:g}/{a}": lv(L, u, b, g, "change", a) for u, b in ALL for g in D.GAINS
           for a in ("record+parity", "vote2r", "cue", "vote3")}
    S["C5"] = {"verdict": "HOLDS" if min(cs.values()) >= 0.62 and max(oth.values()) <= 0.25 else "FAILS",
               "community-s": cs, "max_other": max(oth.values())}

    fa = {f"{u}/{b}/{g:g}": round(lv(L, u, b, g, "cue", "community-s", "r_all") - lv(L, u, b, g, "cue", "cue", "r_all"), 4)
          for u, b in ALL for g in D.GAINS}
    quiet = max(L[u][b][f"{g:g}"]["none"][a]["opened"][0] for u, b in ALL for g in D.GAINS for a in D.COMMUNITY)
    S["C6"] = {"verdict": "HOLDS" if max(fa.values()) <= -0.04 and quiet <= 0.001 else "FAILS",
               "cue_r_all_minus_cue_arm": fa, "max_opened_without_event": quiet}

    op = max(L[u][b][f"{g:g}"]["cue"]["community-c"]["opened"][0] for u, b in ALL for g in D.GAINS)
    diff = max(abs(lv(L, u, b, g, "cue", "community-c", "r_all") - lv(L, u, b, g, "cue", "cue", "r_all"))
               for u, b in ALL for g in D.GAINS)
    ch = max(lv(L, u, b, g, "change", "community-c") for u, b in ALL for g in D.GAINS)
    mem = max(lv(L, u, b, g, "memory", "community-c") for u, b in ALL for g in D.GAINS)
    ok = op <= 0.002 and diff <= 0.01 and ch <= 0.50 and mem <= 0.55
    S["C7"] = {"verdict": "HOLDS" if ok else "FAILS", "max_opened_cue": op, "max_abs_r_all_vs_cue": round(diff, 4),
               "max_change": ch, "max_memory": mem}

    fld = {f"{u}/{b}/{a}": lv(L, u, b, 0.2, "shared", a) for u, b in FIELD for a in D.ARMS}
    rp = {f"{u}/{b}/{g:g}": lv(L, u, b, g, "shared", "record+parity") for u, b in ALL for g in D.GAINS}
    S["C8"] = {"verdict": "HOLDS" if max(fld.values()) <= 0.90 and max(rp.values()) <= 0.70 else "FAILS",
               "max_field": max(fld.values()), "record+parity": rp}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
