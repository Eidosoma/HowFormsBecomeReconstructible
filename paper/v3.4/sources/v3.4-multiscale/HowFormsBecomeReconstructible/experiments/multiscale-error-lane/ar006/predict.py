"""AR006's registered statements: python -m ar006.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar006.predict --freeze  (writes ar006/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. The size means are over 4 x 4 and 8 x 8. Thresholds
come from probe P57 under BE002's rule with the lane's block SD (the larger of the four-block SD and the case-level
SD / sqrt 8), each part at least 3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P57
(probes/p57b_ar006_margins.py), each at the strictest round value the rule allows: rates in twentieths; contrasts and
differences in hundredths (in 0.005 where the strictest value lies within 0.01 of zero); sheet costs in thousandths; the
share k in twentieths. The fixed bounds (the confirmed 0.01 and 0.002, AR003's E9 bound 0.01) are kept only where P57
supports them; a part with SD 0 takes the declared allowance -0.005 (AR003's E8). A part P57 cannot support is dropped and
reported (DROPPED), not loosened. BEST is the vote; vms, vpool and vguard are AR003's, AR004's and AR005's controllers
(frozen); the controller is vtol (DET_STAR's windows unguarded, DET_POOL's further windows guarded by g-body-f05).
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

from ar006 import analyze as Z  # noqa: E402
from ar006 import design as D  # noqa: E402

C, S1 = D.CONTROLLER, D.MISREAD_SIGMA


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


T = {"K2a": 0.002, "K2b": 0.01, "K3a": 0.04, "K3b": 0.0, "K4": -0.005, "K5a": -0.005, "K5b": 0.25, "K5c": -0.03,
     "K5d": 0.0, "K6": 0.12, "K7a": -0.005, "K7b": -0.005}     # set from P57 (p57b_ar006_margins.txt)
K_SHARE = 0.5                                                  # K3b's share k of vpool's recovery: the largest twentieth
# the rule allows on P57. K5a and K7a have SD 0 on P57: the declared allowance -0.005 (AR003's E8). K1, the confirmed
# 0.01 under scattered cue damage, is not supported by P57 under the rule and is DROPPED (below), not loosened.

PARTS = [
    P("K2", "K2 (a) sheet cost with no event: r_all(vote) - r_all(vtol), none@0", lambda d: Z.sham(d, "none@0", C), "le",
      "K2a"),
    P("K2", "K2 (b) sheet cost under misreads with no event: r_all(vote, none@0) - r_all(vtol, none@1)",
      lambda d: Z.sham(d, "none@1", C), "le", "K2b"),
    P("K3", "K3 (a) R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1)", lambda d: Z.R1(d), "ge", "K3a"),
    P("K3", "K3 (b) the share kept: R1(vtol) - k R1(vpool)", lambda d: Z.kept(d, K_SHARE if K_SHARE is not None else 0.0),
      "ge", "K3b"),
    P("K4", "K4 R0 = (1/2) sum over sizes 4, 8 of u(vtol, memory@0) - u(vms, memory@0)", lambda d: Z.R0(d), "ge", "K4"),
    P("K5", "K5 (a) u(vtol) - u(vms) in correlated damage, 4 x 4, sigma 0", lambda d: Z.corr(d, 0.0), "ge", "K5a"),
    P("K5", "K5 (b) u(vtol) - u(vguard) in correlated damage, 4 x 4, sigma 0", lambda d: Z.corr(d, 0.0, C, "vguard"), "ge",
      "K5b"),
    P("K5", "K5 (c) u(vtol) - u(vms) in correlated damage, 4 x 4, sigma 1", lambda d: Z.corr(d, S1), "ge", "K5c"),
    P("K5", "K5 (d) u(vtol) - u(vguard) in correlated damage, 4 x 4, sigma 1", lambda d: Z.corr(d, S1, C, "vguard"), "ge",
      "K5d"),
    P("K6", "K6 W1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vote, memory@0)", lambda d: Z.W1(d), "ge", "K6"),
    P("K7", "K7 u(vtol) - u(vote) in the 4 x 4 patch, none@0", lambda d: Z.give(d, C, "none"), "ge", "K7a"),
    P("K7", "K7 u(vtol, none@1) - u(vote, none@0) in the 4 x 4 patch", lambda d: Z.give(d, C, "none", S1), "ge", "K7b"),
]
for _p in PARTS:
    _p["threshold"] = T[_p["key"]]

# Scored beside the statements, not registered
REPORTED = []
# Parts P57 cannot support under the rule: dropped and reported, not loosened
DROPPED = [dict(P("K1", "K1 sheet cost under scattered cue damage: r_all(vote) - r_all(vtol), cue@0",
                  lambda d: Z.sham(d, "cue@0", C), "le", "K1"), threshold=0.01,
                why="the confirmed bound 0.01, as planned; on P57 +0.008713 (sd_block 0.002786, halves +0.009705, +0.007721), "
                    "margin 0.46 against the rule's 1.68: P57 cannot support it; not registered (the lead's ruling (a) at "
                    "phase A), reported at the development with its 95% interval beside the confirmed 0.01")]


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
        {"id": "K2", "claim": "with no event its false alarms cost intact tissue within the confirmed bound, and under "
                              "misreads within AR003's E9 bound",
         "rule": f"HOLDS if r_all(vote) - r_all(vtol) in none@0 <= {t['K2a']} and r_all(vote, none@0) - r_all(vtol, "
                 f"none@1) <= {t['K2b']}, else FAILS"},
        {"id": "K3", "claim": "under misread cues it keeps the pooled detector's recovery over the confirmed controller",
         "rule": f"HOLDS if R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1) >= {t['K3a']} and "
                 f"R1(vtol) - {K_SHARE} R1(vpool) >= {t['K3b']}, else FAILS"},
        {"id": "K4", "claim": "at sigma 0 it keeps the confirmed controller's hits (non-inferiority)",
         "rule": f"HOLDS if R0 = (1/2) sum over sizes 4, 8 of u(vtol, memory@0) - u(vms, memory@0) >= {t['K4']}, else FAILS"},
        {"id": "K5", "claim": "the blind spot resolved: where body and record share the error it is not worse than the "
                              "confirmed controller, and it gains over the fully guarded one",
         "rule": f"HOLDS if in correlated damage at 4 x 4 u(vtol) - u(vms) >= {t['K5a']} and u(vtol) - u(vguard) >= "
                 f"{t['K5b']} at sigma 0, and u(vtol) - u(vms) >= {t['K5c']} and u(vtol) - u(vguard) >= {t['K5d']} at "
                 f"sigma 1, else FAILS"},
        {"id": "K6", "claim": "under misread cues the controller still beats the best fixed policy",
         "rule": f"HOLDS if W1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vote, memory@0) >= {t['K6']}, "
                 f"else FAILS"},
        {"id": "K7", "claim": "it gives up nothing to the vote with no event, with or without misread cues (non-inferiority)",
         "rule": f"HOLDS if u(vtol) - u(vote) in the 4 x 4 patch is at least {t['K7a']} in none@0, and u(vtol, none@1) - "
                 f"u(vote, none@0) >= {t['K7b']}, else FAILS"},
    ]


STATEMENTS = statements()


def freeze():
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "best": D.BEST,
                               "controller": C, "vtol": D.VTOL, "thresholds": T, "k_share": K_SHARE,
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
