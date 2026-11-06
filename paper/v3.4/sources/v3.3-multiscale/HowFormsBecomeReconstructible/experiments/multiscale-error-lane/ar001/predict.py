"""AR001's registered statements: python -m ar001.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar001.predict --freeze  (writes ar001/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. Thresholds come from probe P41 under BE002's rule
with the lead's block SD (the larger of the four-block SD and the case-level SD / sqrt 8), each part at least
3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P41. A1 is static (a derived identity).
The best fixed policy BEST is named from P41 (the fixed policy with the largest pooled utility there).
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

from ar001 import analyze as Z  # noqa: E402
from ar001 import design as D  # noqa: E402

BEST = "vote"             # P41's best fixed policy (U 0.6908; body 0.6646 next), named before the freeze
COPIES = ("record", "body", "vote")


def info_limit(data):
    """(blocks, cases): the largest abs(u(new) + u(old) - 1) over every arm of change@0 and change@1."""
    worst = None
    for run in ("change@0", "change@1"):
        for a in Z.RUNARMS[run]:
            x = np.abs(Z.case(data, run, "r_in", a) + Z.case(data, run, "r_in_old", a) - 1.0)
            worst = x if worst is None else np.maximum(worst, x)
    return worst


def adv(h, f, best=None):
    def fn(data):
        return Z.U_ctrl(data, h, f) - Z.U(data, best or BEST)
    return fn


def u_minus(arm, other, s):
    def fn(data):
        return Z.u(data, arm, s) - Z.u(data, other, s)
    return fn


def u_of(arm, s, sigma=0.0):
    def fn(data):
        return Z.u(data, arm, s, sigma)
    return fn


def sham_of(run, arm="dial", ref="rest"):
    def fn(data):
        return Z.sham(data, run, arm, ref)
    return fn


def sham_minus(run, arm, other):
    def fn(data):
        return Z.sham(data, run, arm) - Z.sham(data, run, other)
    return fn


def u_timing_minus(arm, s, ref="dial"):
    def fn(data):
        run, ep = Z.scoring_run(s)
        return Z.case(data, run, ep, arm) - Z.case(data, run, ep, ref)
    return fn


T = {"A1": 1e-12, "A2": 0.04, "A3": 0.0, "A4": 0.03, "A4d": 0.04, "A5r": 0.3, "A5b": 0.1, "A5v": 0.1, "A6c": 0.01,
     "A6n": 0.002, "A7": 0.1, "A8n": 0.02, "A8m": 0.2, "A9late": 0.0, "A9early": -0.02, "A10off": 0.05, "A10half": -0.15,
     "A10wide": 0.02, "A11c": 0.0, "A11n": 0.0}      # thresholds, set from P41 (probes/results/p41b_ar001_margins.txt)


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


def discrimination(data):
    """U_ctrl(h 1, f 0) - U_ctrl(h 1, f 1): what the signal's discrimination is worth at a full hit rate."""
    return Z.U_ctrl(data, 1.0, 0.0) - Z.U_ctrl(data, 1.0, 1.0)


def misread(arm, s):
    def fn(data):
        return Z.u(data, arm, s, D.MISREAD_SIGMA) - Z.u(data, arm, s, 0.0)
    return fn


def sheet_minus(run, arm, other):
    def fn(data):
        return Z.case(data, run, "r_all", arm) - Z.case(data, run, "r_all", other)
    return fn


PARTS = [
    P("A1", "A1 max over arms and cases of abs(u(new) + u(old) - 1), change@0 and change@1", info_limit, "le", "A1"),
    P("A2", "A2 U_ctrl(h 1, f 0) - U(BEST)", adv(1.0, 0.0), "ge", "A2"),
    P("A3", "A3 U_ctrl(h 0.75, f 0.25) - U(BEST)", adv(0.75, 0.25), "ge", "A3"),
    P("A4", "A4 U_ctrl(h 0.5, f 0.5) - U(BEST)", adv(0.5, 0.5), "le", "A4"),
    P("A4", "A4 U_ctrl(h 1, f 0) - U_ctrl(h 1, f 1)", discrimination, "ge", "A4d"),
    P("A5", "A5 u(dial, correlated) - u(record, correlated)", u_minus("dial", "record", "correlated"), "ge", "A5r"),
    P("A5", "A5 u(dial, correlated) - u(body, correlated)", u_minus("dial", "body", "correlated"), "ge", "A5b"),
    P("A5", "A5 u(dial, correlated) - u(vote, correlated)", u_minus("dial", "vote", "correlated"), "ge", "A5v"),
    P("A6", "A6 sham cost to the sheet, cue@0: r_all(rest) - r_all(dial)", sham_of("cue@0"), "le", "A6c"),
    P("A6", "A6 sham cost to the sheet, none@0: r_all(rest) - r_all(dial)", sham_of("none@0"), "le", "A6n"),
    P("A7", "A7 cue@0 sheet: r_all(arbiter) - r_all(latch)", sheet_minus("cue@0", "arbiter", "latch"), "ge", "A7"),
    P("A8", "A8 u(record, none) - u(body, none)", u_minus("record", "body", "none"), "ge", "A8n"),
    P("A8", "A8 u(body, memory) - u(record, memory)", u_minus("body", "record", "memory"), "ge", "A8m"),
    P("A9", "A9 u(dial-m2, memory) - u(dial, memory)", u_timing_minus("dial-m2", "memory"), "le", "A9late"),
    P("A9", "A9 u(dial-m0.5, memory) - u(dial, memory)", u_timing_minus("dial-m0.5", "memory"), "ge", "A9early"),
    P("A10", "A10 u(dial-s6, memory) - u(rest, memory)", u_timing_minus("dial-s6", "memory", "rest"), "le", "A10off"),
    P("A10", "A10 u(dial-s4, memory) - u(dial, memory)", u_timing_minus("dial-s4", "memory"), "le", "A10half"),
    P("A10", "A10 sham(cue@0, dial-d8) - sham(cue@0, dial)", sham_minus("cue@0", "dial-d8", "dial"), "ge", "A10wide"),
    P("A11", "A11 u(dial, change/new) misread - exact", misread("dial", "change/new"), "le", "A11c"),
    P("A11", "A11 u(dial, none) misread - exact", misread("dial", "none"), "le", "A11n"),
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


STATEMENTS = [
    {"id": "A1", "claim": "on the information-limit pair every policy ties, the controller included",
     "rule": "HOLDS if, in change@0 and change@1, the largest abs(u(arm, change/new) + u(arm, change/old) - 1) over every "
             "arm and case is at most 1e-12, else FAILS (derived identity)"},
    {"id": "A2", "claim": "with a perfect signal the controller beats the best fixed policy",
     "rule": "HOLDS if U_ctrl(h 1, f 0) - U(BEST) >= 0.04, else FAILS"},
    {"id": "A3", "claim": "and with a moderately reliable one",
     "rule": "HOLDS if U_ctrl(h 0.75, f 0.25) - U(BEST) >= 0, else FAILS"},
    {"id": "A4", "claim": "an uninformative signal buys nothing; discrimination is what pays",
     "rule": "HOLDS if U_ctrl(h 0.5, f 0.5) - U(BEST) <= 0.03 and U_ctrl(h 1, f 0) - U_ctrl(h 1, f 1) >= 0.04, else FAILS"},
    {"id": "A5", "claim": "copies cannot repair an error they share; the signalled cue can",
     "rule": "HOLDS if, in correlated errors, u(dial) - u(record) >= 0.3, u(dial) - u(body) >= 0.1 and "
             "u(dial) - u(vote) >= 0.1, else FAILS"},
    {"id": "A6", "claim": "a false alarm costs the sheet little",
     "rule": "HOLDS if r_all(rest) - r_all(dial) is at most 0.01 under scattered cue damage and at most 0.002 with no "
             "event (a derived bound; BE002's floor), else FAILS"},
    {"id": "A7", "claim": "a cue latch held for the calibrated commitment turns scattered cue corruption into lasting false "
                          "re-specification",
     "rule": "HOLDS if, under scattered cue damage, r_all(arbiter) - r_all(latch) >= 0.1, else FAILS"},
    {"id": "A8", "claim": "which source to trust depends on the situation",
     "rule": "HOLDS if u(record, none) - u(body, none) >= 0.02 and u(body, memory) - u(record, memory) >= 0.2, else FAILS"},
    {"id": "A9", "claim": "the evidence clock bounds the controller",
     "rule": "HOLDS if, in memory damage, u(dial-m2) - u(dial) <= 0 and u(dial-m0.5) - u(dial) >= -0.02, else FAILS"},
    {"id": "A10", "claim": "the signal must be where the damage is",
     "rule": "HOLDS if, in memory damage, u(dial-s6) - u(rest) <= 0.05 and u(dial-s4) - u(dial) <= -0.15, and under "
             "scattered cue damage sham(dial-d8) - sham(dial) >= 0.02, else FAILS"},
    {"id": "A11", "claim": "misread cues cost the controller",
     "rule": "HOLDS if, at GC001's sigma 1 against sigma 0, the differences in u(dial, change/new) and in u(dial, none) "
             "are each <= 0, else FAILS"},
]


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
