"""AR005's registered statements: python -m ar005.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar005.predict --freeze  (writes ar005/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. The size means are over 4 x 4 and 8 x 8. Thresholds
come from probe P53 under BE002's rule with the lane's block SD (the larger of the four-block SD and the case-level
SD / sqrt 8), each part at least 3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P53
(probes/p53b_ar005_margins.py), each at the strictest round value the rule allows: rates in twentieths; contrasts and
differences in hundredths (in 0.005 where the strictest value lies within 0.01 of zero); sheet costs in thousandths; the
share k in twentieths. The fixed bounds (the confirmed 0.01 and 0.002, AR003's E9 bound 0.01) are kept only where P53
supports them. A part P53 cannot support is dropped and reported (DROPPED), not loosened. BEST is the vote; vms is
AR003's confirmed controller and vpool AR004's (both frozen); the controller is vguard (DET_POOL plus the tuning's guard).
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

from ar005 import analyze as Z  # noqa: E402
from ar005 import design as D  # noqa: E402

C, S1 = D.CONTROLLER, D.MISREAD_SIGMA


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


T = {"K1": 0.01, "K2a": 0.002, "K2b": 0.01, "K3a": 0.01, "K3b": 0.0, "K4": -0.01, "K5": 0.12, "K6a": 0.40, "K6b": 0.37,
     "K6c0": 0.08, "K6c1": 0.02, "K7a": -0.005, "K7b": -0.005}  # set from P53 (p53b_ar005_margins.txt)
K_SHARE = 0.25                                                 # K3b's share k of vpool's recovery: the largest twentieth
# the rule allows on P53. K7a and K7b have SD 0 on P53: the declared allowance -0.005 (AR003's E8).

PARTS = [
    P("K1", "K1 sheet cost under scattered cue damage: r_all(vote) - r_all(vguard), cue@0", lambda d: Z.sham(d, "cue@0", C),
      "le", "K1"),
    P("K2", "K2 (a) sheet cost with no event: r_all(vote) - r_all(vguard), none@0", lambda d: Z.sham(d, "none@0", C), "le",
      "K2a"),
    P("K2", "K2 (b) sheet cost under misreads with no event: r_all(vote, none@0) - r_all(vguard, none@1)",
      lambda d: Z.sham(d, "none@1", C), "le", "K2b"),
    P("K3", "K3 (a) R1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vms, memory@1)", lambda d: Z.R1(d), "ge",
      "K3a"),
    P("K3", "K3 (b) the share kept: R1(vguard) - k R1(vpool)", lambda d: Z.kept(d, K_SHARE if K_SHARE is not None else 0.0), "ge", "K3b"),
    P("K4", "K4 R0 = (1/2) sum over sizes 4, 8 of u(vguard, memory@0) - u(vms, memory@0)", lambda d: Z.R0(d), "ge", "K4"),
    P("K5", "K5 W1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vote, memory@0)", lambda d: Z.W1(d), "ge", "K5"),
    P("K6", "K6 (a) u(vpool) - u(vguard) in correlated damage, 4 x 4, sigma 0", lambda d: Z.corr(d, 0.0), "le", "K6a"),
    P("K6", "K6 (b) u(vpool) - u(vguard) in correlated damage, 4 x 4, sigma 1", lambda d: Z.corr(d, S1), "le", "K6b"),
    P("K6", "K6 (c) u(vguard) - u(vote) in correlated damage, 4 x 4, sigma 0", lambda d: Z.give(d, C, "correlated"), "ge",
      "K6c0"),
    P("K6", "K6 (c) u(vguard, correlated@1) - u(vote, correlated@0), 4 x 4", lambda d: Z.give(d, C, "correlated", S1), "ge",
      "K6c1"),
    P("K7", "K7 u(vguard) - u(vote) in the 4 x 4 patch, none@0", lambda d: Z.give(d, C, "none"), "ge", "K7a"),
    P("K7", "K7 u(vguard, none@1) - u(vote, none@0) in the 4 x 4 patch", lambda d: Z.give(d, C, "none", S1), "ge", "K7b"),
]
for _p in PARTS:
    _p["threshold"] = T[_p["key"]]

# Scored beside the statements, not registered
REPORTED = []
# Parts P53 cannot support under the rule: dropped and reported, not loosened
DROPPED = []


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
        {"id": "K1", "claim": "under scattered cue damage the guarded controller's false alarms cost intact tissue within the "
                              "confirmed bound",
         "rule": f"HOLDS if r_all(vote) - r_all(vguard) in cue@0 <= {t['K1']}, else FAILS"},
        {"id": "K2", "claim": "with no event its false alarms cost intact tissue within the confirmed bound, and under "
                              "misreads within AR003's E9 bound",
         "rule": f"HOLDS if r_all(vote) - r_all(vguard) in none@0 <= {t['K2a']} and r_all(vote, none@0) - r_all(vguard, "
                 f"none@1) <= {t['K2b']}, else FAILS"},
        {"id": "K3", "claim": "under misread cues the guard keeps the pooled detector's recovery over the confirmed controller",
         "rule": f"HOLDS if R1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vms, memory@1) >= {t['K3a']} and "
                 f"R1(vguard) - {K_SHARE} R1(vpool) >= {t['K3b']}, else FAILS"},
        {"id": "K4", "claim": "at sigma 0 it keeps the confirmed controller's hits (non-inferiority)",
         "rule": f"HOLDS if R0 = (1/2) sum over sizes 4, 8 of u(vguard, memory@0) - u(vms, memory@0) >= {t['K4']}, else FAILS"},
        {"id": "K5", "claim": "under misread cues the controller still beats the best fixed policy",
         "rule": f"HOLDS if W1 = (1/2) sum over sizes 4, 8 of u(vguard, memory@1) - u(vote, memory@0) >= {t['K5']}, "
                 f"else FAILS"},
        {"id": "K6", "claim": "the blind spot, measured: where body and record share the error the guard gives up at most a "
                              "measured part of the pooled detector's worth, and keeps at least a measured part of its worth "
                              "over the vote",
         "rule": f"HOLDS if u(vpool) - u(vguard) in correlated damage at 4 x 4 is at most {t['K6a']} at sigma 0 and "
                 f"{t['K6b']} at sigma 1, and u(vguard) - u(vote) there is at least {t['K6c0']} at sigma 0 and "
                 f"{t['K6c1']} at sigma 1 (against the vote's sigma-0 run), else FAILS"},
        {"id": "K7", "claim": "it gives up nothing to the vote where nothing needs correcting (non-inferiority)",
         "rule": f"HOLDS if u(vguard) - u(vote) in the 4 x 4 patch is at least {t['K7a']} in none@0, and u(vguard, none@1) "
                 f"- u(vote, none@0) >= {t['K7b']}, else FAILS"},
    ]


STATEMENTS = statements()


def freeze():
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "best": D.BEST,
                               "controller": C, "vguard_name": D.VGUARD_NAME, "thresholds": T, "k_share": K_SHARE,
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
