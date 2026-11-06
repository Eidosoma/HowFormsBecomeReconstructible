"""AR004's registered statements: python -m ar004.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar004.predict --freeze  (writes ar004/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. Thresholds come from probe P51 under BE002's rule
with the lead's block SD (the larger of the four-block SD and the case-level SD / sqrt 8), each part at least
3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P51 (probes/p51b_ar004_margins.py), each at the strictest
round value the rule allows: rates in twentieths; contrasts and differences in hundredths (in 0.005 where the strictest
value lies within 0.01 of zero, as AR003's E4); sheet costs in thousandths (as the confirmed 0.01 and 0.002). A part P51
cannot support is dropped and reported (DROPPED), not loosened; REPORTED parts are scored beside the statements, not
registered. BEST is the vote; vms is AR003's confirmed controller (frozen); the controller is vpool (DET_POOL with the
vote default).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar004 import analyze as Z  # noqa: E402
from ar004 import design as D  # noqa: E402

C, S1 = D.CONTROLLER, D.MISREAD_SIGMA


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


T = {"G1": 0.04, "G2": -0.005, "G3a": 0.008, "G3b": 0.029, "G3c": 0.002, "G5n": -0.005, "G5n1": -0.03, "G6_4": 0.25,
     "G6_8": 0.3, "G6d": 0.04, "G7": 0.09}                     # set from P51 (p51b_ar004_margins.txt)
# G3 (a) and (b) are the measured trade-off under cue damage (the lead's ruling 2): the confirmed 0.01 bound is not
# claimed for vpool, only reported beside them; G3 (c) is the confirmed 0.002 bound with no event (the lead's ruling 4
# on phase A). G5n has SD 0 on P51: the declared allowance -0.005 (AR003's E8).

PARTS = [
    P("G1", "G1 R1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vms, memory@1)", lambda d: Z.R1(d), "ge", "G1"),
    P("G2", "G2 R0 = (1/3) sum over sizes of u(vpool, memory@0) - u(vms, memory@0)", lambda d: Z.R0(d), "ge", "G2"),
    P("G3", "G3 (a) the trade-off: sheet cost under scattered cue damage, vpool less vms, cue@0",
      lambda d: Z.sham(d, "cue@0", C) - Z.sham(d, "cue@0", "vms"), "ge", "G3a"),
    P("G3", "G3 (b) vpool's sheet cost under scattered cue damage: r_all(vote) - r_all(vpool), cue@0",
      lambda d: Z.sham(d, "cue@0", C), "le", "G3b"),
    P("G3", "G3 (c) vpool's sheet cost with no event: r_all(vote) - r_all(vpool), none@0 (the confirmed bound)",
      lambda d: Z.sham(d, "none@0", C), "le", "G3c"),
    P("G5", "G5 u(vpool) - u(vote) in the 4 x 4 patch, none@0", lambda d: Z.give(d, C, "none"), "ge", "G5n"),
    P("G5", "G5 u(vpool, none@1) - u(vote, none@0) in the 4 x 4 patch", lambda d: Z.give(d, C, "none", S1), "ge", "G5n1"),
    P("G6", "G6 p(vpool fires on the patch | memory@1, 4 x 4)", lambda d: Z.rate(d, C, "memory", 4, S1, "located"), "ge", "G6_4"),
    P("G6", "G6 p(vpool fires on the patch | memory@1, 8 x 8)", lambda d: Z.rate(d, C, "memory", 8, S1, "located"), "ge", "G6_8"),
    P("G6", "G6 p(on the patch | memory@1, 4 x 4): vpool - vms",
      lambda d: Z.rate(d, C, "memory", 4, S1, "located") - Z.rate(d, "vms", "memory", 4, S1, "located"), "ge", "G6d"),
    P("G7", "G7 W1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vote, memory@0)", lambda d: Z.W1(d), "ge", "G7"),
]
for _p in PARTS:
    _p["threshold"] = T[_p["key"]]

# Scored beside the statements, not registered (the lead's ruling 1 on phase A)
REPORTED = [{"name": "G5's cue@0 part, u(vpool) - u(vote) in the 4 x 4 patch, cue@0: the trade-off inside the patch",
             "fn": lambda d: Z.give(d, C, "cue"),
             "why": "on P51 -0.0325, patch cells lost to the vote in 17 of 256 lineage-cases against vms's 1; the -0.11 "
                    "the rule allowed bounds nothing a reader can use"}]

# Parts P51 cannot support under the rule: dropped and reported, not loosened (the lead's ruling 2)
DROPPED = [dict(P("G4", "G4 sheet cost under misreads with no event: r_all(vote, none@0) - r_all(vpool, none@1)",
                  lambda d: Z.sham(d, "none@1", C), "le", "G4"), threshold=0.01,
                why="AR003's E9 bound 0.01, as planned; on P51 +0.010094 (halves +0.008522, +0.011665), margin -0.04: "
                    "the value and the second half exceed it")]


def score(data):
    out = {}
    for p in PARTS:
        v = p["fn"](data)
        blk = v.mean(-1)
        val = float(blk.mean())
        thr = p["threshold"]
        ok = None if thr is None else bool(val >= thr if p["sense"] == "ge" else val <= thr)
        s = out.setdefault(p["stmt"], {"parts": {}})
        s["parts"][p["name"]] = {"pooled": val, "blocks": [float(x) for x in blk], "threshold": thr,
                                 "sense": p["sense"], "pass": ok}
    for s in out.values():
        oks = [x["pass"] for x in s["parts"].values()]
        s["verdict"] = "UNSET" if any(o is None for o in oks) else ("HOLDS" if all(oks) else "FAILS")
    return out


def statements():
    t = T
    return [
        {"id": "G1", "claim": "under misread cues the pooled detector recovers worth the confirmed controller loses",
         "rule": f"HOLDS if R1 = (1/3) sum over sizes 2, 4, 8 of u(vpool, memory@1) - u(vms, memory@1) >= {t['G1']}, else FAILS"},
        {"id": "G2", "claim": "at sigma 0 it keeps the confirmed controller's hits (non-inferiority)",
         "rule": f"HOLDS if R0 = (1/3) sum over sizes of u(vpool, memory@0) - u(vms, memory@0) >= {t['G2']}, else FAILS"},
        {"id": "G3", "claim": "the trade-off: pooling's false alarms under scattered cue damage cost intact tissue more than "
                              "the confirmed controller's, by at least a measured amount, and at most a measured amount in "
                              "all (the confirmed 0.01 bound is reported beside it as context, not claimed); with no event "
                              "at sigma 0 they cost it within the confirmed bound",
         "rule": f"HOLDS if (r_all(vote) - r_all(vpool)) - (r_all(vote) - r_all(vms)) in cue@0 >= {t['G3a']}, "
                 f"r_all(vote) - r_all(vpool) in cue@0 <= {t['G3b']}, and r_all(vote) - r_all(vpool) in none@0 <= "
                 f"{t['G3c']}, else FAILS"},
        {"id": "G5", "claim": "it gives up nothing to the vote with no event, with or without misread cues (non-inferiority)",
         "rule": f"HOLDS if u(vpool) - u(vote) in the 4 x 4 patch is at least {t['G5n']} in none@0, and u(vpool, none@1) - "
                 f"u(vote, none@0) >= {t['G5n1']}, else FAILS"},
        {"id": "G6", "claim": "it finds memory damage on the patch under misread cues, more often than the confirmed controller",
         "rule": f"HOLDS if vpool fires with its footprint on the patch in at least {t['G6_4']} of memory@1 lineage-cases at 4 x 4 "
                 f"and {t['G6_8']} at 8 x 8, and its 4 x 4 rate exceeds vms's by at least {t['G6d']}, else FAILS"},
        {"id": "G7", "claim": "under misread cues the controller still beats the best fixed policy over the sizes",
         "rule": f"HOLDS if W1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vote, memory@0) >= {t['G7']}, else FAILS"},
    ]


STATEMENTS = statements()


def freeze():
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "best": D.BEST,
                               "controller": C, "thresholds": T,
                               "parts": [{k: v for k, v in p.items() if k != "fn"} for p in PARTS],
                               "dropped": [{k: v for k, v in p.items() if k != "fn"} for p in DROPPED],
                               "reported": [{k: v for k, v in p.items() if k != "fn"} for p in REPORTED],
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        freeze()
        return
    data = Z.load(a.root)
    S = score(data)
    a.out.write_text(json.dumps(S, indent=1) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
