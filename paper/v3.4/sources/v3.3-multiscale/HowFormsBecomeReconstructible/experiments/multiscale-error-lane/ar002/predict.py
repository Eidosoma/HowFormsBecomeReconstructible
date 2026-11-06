"""AR002's registered statements: python -m ar002.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar002.predict --freeze  (writes ar002/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. Thresholds come from probe P44 under BE002's rule
with the lead's block SD (the larger of the four-block SD and the case-level SD / sqrt 8), each part at least
3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P44. D1 is static (a derived identity).
BEST is the vote, AR001's, named from its probe P41 and frozen there.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar002 import analyze as Z  # noqa: E402
from ar002 import design as D  # noqa: E402

BEST = D.BEST


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


def info_limit(data):
    return Z.info_limit(data)


def adv(arm, other=None):
    def fn(data):
        return Z.U(data, arm) - Z.U(data, other or BEST)
    return fn


def rate_of(arm, situation, sigma=0.0, which="fired"):
    """The pooled rate at which the arm's detector fired at all ('fired') or with its footprint on the patch ('located')."""
    def fn(data):
        return Z.rate(data, arm, situation, sigma, which)
    return fn


def price(arm):
    def fn(data):
        return Z.U(data, arm) - Z.U_mix(data, arm, "fired")
    return fn


def sham_of(run, arm):
    def fn(data):
        return Z.sham(data, run, arm)
    return fn


def kept(arm):
    """U(arm) - U(rest) less half of U_ctrl(0.9, 0.1) - U(rest): positive when the detector keeps more than half of the
    declared signal's worth at AR001C's confirmed point."""
    def fn(data):
        rest = Z.U(data, "rest")
        return (Z.U(data, arm) - rest) - 0.5 * (Z.U_ctrl(data, 0.9, 0.1) - rest)
    return fn


def located_minus(arm, other, situation):
    def fn(data):
        return Z.rate(data, arm, situation, 0.0, "located") - Z.rate(data, other, situation, 0.0, "located")
    return fn


def to_ceiling(arm):
    def fn(data):
        return Z.U(data, arm) - Z.U_ceiling(data)
    return fn


def misread_u(arm, s):
    def fn(data):
        return Z.u(data, arm, s, D.MISREAD_SIGMA) - Z.u(data, arm, s, 0.0)
    return fn


T = {"D1": 1e-12, "D2": -0.03, "D3m": 0.7, "D3c": 0.7, "D3n": 0.5, "D4": -0.005, "D5c": 0.01, "D5n": 0.002,
     "D6c": 0.4, "D6u": 0.02, "D7": 0.0, "D7c": -0.005, "D8n": 0.005, "D8m": -0.1}   # set from P44 (p44b_ar002_margins.txt)

PARTS = [
    P("D1", "D1 max over arms and cases of abs(u(new) + u(old) - 1), change@0 and change@1", info_limit, "le", "D1"),
    P("D2", "D2 U(det) - U(BEST)", adv("det"), "ge", "D2"),
    P("D3", "D3 p(det fires on the patch | memory)", rate_of("det", "memory", which="located"), "ge", "D3m"),
    P("D3", "D3 p(det fires on the patch | correlated)", rate_of("det", "correlated", which="located"), "ge", "D3c"),
    P("D3", "D3 p(det fires at all | none)", rate_of("det", "none"), "le", "D3n"),
    P("D4", "D4 U(det) - U_pred(det)", price("det"), "ge", "D4"),
    P("D5", "D5 sheet cost under scattered cue damage: r_all(rest) - r_all(det), cue@0", sham_of("cue@0", "det"), "le", "D5c"),
    P("D5", "D5 sheet cost with no event: r_all(rest) - r_all(det), none@0", sham_of("none@0", "det"), "le", "D5n"),
    P("D6", "D6 p(fires on the patch | correlated): det - det-v", located_minus("det", "det-v", "correlated"), "ge", "D6c"),
    P("D6", "D6 U(det) - U(det-v)", adv("det", "det-v"), "ge", "D6u"),
    P("D7", "D7 (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2", kept("det"), "ge", "D7"),
    P("D7", "D7 U(det) - U_ceiling", to_ceiling("det"), "ge", "D7c"),
    P("D8", "D8 sheet cost under misread cues with no event: r_all(rest) - r_all(det), none@1", sham_of("none@1", "det"), "le", "D8n"),
    P("D8", "D8 u(det, memory) misread - exact", misread_u("det", "memory"), "le", "D8m"),
]
for _p in PARTS:
    _p["threshold"] = T[_p["key"]]


def part_cases(data, p):
    return p["fn"](data)


def score(data):
    out = {}
    for p in PARTS:
        v = part_cases(data, p)
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
    """The registered claims and rules, with the thresholds as set (T)."""
    t = T
    return [
        {"id": "D1", "claim": "on the information-limit pair the tissue's detector cannot win: its controller ties like every arm",
         "rule": f"HOLDS if, in change@0 and change@1, the largest abs(u(arm, change/new) + u(arm, change/old) - 1) over every "
                 f"arm (the detectors' included) and case is at most {t['D1']:g}, else FAILS (derived identity)"},
        {"id": "D2", "claim": "the controller driven by the tissue's own detector is not worse than the best fixed policy by "
                              "more than 0.03 (non-inferiority; whether it beats the vote is the development's 95% interval, "
                              "reported, and the confirmation's test)",
         "rule": f"HOLDS if U(det) - U(BEST) >= {t['D2']}, else FAILS"},
        {"id": "D3", "claim": "the detector finds memory and correlated damage on the patch and stays quiet with no event",
         "rule": f"HOLDS if det fires with its footprint on the patch in at least {t['D3m']} of memory-damage lineage-cases and "
                 f"{t['D3c']} of correlated-damage ones, and fires at all in at most {t['D3n']} of no-event ones, else FAILS"},
        {"id": "D4", "claim": "making the signal costs little: the declared signal's exact value at det's own firing predicts "
                              "U(det) from below",
         "rule": f"HOLDS if U(det) - U_pred(det) >= {t['D4']}, else FAILS (U_pred: per lineage-case and scoring, "
                 f"fire x u(dial) + (1 - fire) x u(rest))"},
        {"id": "D5", "claim": "the tissue's false alarms cost the sheet within AR001C's harm bound",
         "rule": f"HOLDS if r_all(rest) - r_all(det) is at most {t['D5c']} under scattered cue damage (cue@0) and at most "
                 f"{t['D5n']} with no event (none@0), else FAILS"},
        {"id": "D6", "claim": "a detector built from the copies mostly misses an error they share; the independent cue's sees it "
                              "and is worth more",
         "rule": f"HOLDS if, in correlated damage, det's rate of firing with its footprint on the patch exceeds det-v's by at "
                 f"least {t['D6c']}, and U(det) - U(det-v) >= {t['D6u']}, else FAILS"},
        {"id": "D7", "claim": "the tissue's signal keeps at least half of the declared signal's worth at AR001C's confirmed point, "
                              "and reaches the ceiling of a signal sent promptly over the patch",
         "rule": f"HOLDS if (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2 >= {t['D7']} and U(det) - U_ceiling >= "
                 f"{t['D7c']}, else FAILS"},
        {"id": "D8", "claim": "misread cues cost the detector: false alarms with no event, and lost hits in memory damage",
         "rule": f"HOLDS if, under GC001's misread (sigma 1) against the exact cue, r_all(rest) - r_all(det) with no event is at "
                 f"most {t['D8n']}, and u(det, memory) misread - exact <= {t['D8m']}, else FAILS"},
    ]


STATEMENTS = statements()


def freeze():
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "best": BEST,
                               "thresholds": T, "parts": [{k: v for k, v in p.items() if k != "fn"} for p in PARTS],
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
