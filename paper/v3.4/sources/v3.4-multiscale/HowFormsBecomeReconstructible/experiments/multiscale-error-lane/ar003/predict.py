"""AR003's registered statements: python -m ar003.predict --root STAGE_ROOT --out FILE  (scores a stage)
python -m ar003.predict --freeze  (writes ar003/frozen/predictions.json)

Every part is pooled: per case the mean over the eight unit-body pairs, a block's value the mean over its eight cases;
the part is scored on the mean over the stage's blocks, unrounded. Thresholds come from probe P47 under BE002's rule
with the lead's block SD (the larger of the four-block SD and the case-level SD / sqrt 8), each part at least
3 sqrt(1/4 + 1/16) = 1.68 SD inside and passing in each half of P47 (probes/p47b_ar003_margins.py). E1 is static (a
derived identity). BEST is the vote, AR001's, named from its probe P41 and frozen there; the controller is vms (the
tuned multi-size detector DET_STAR with the vote as its default).
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

from ar003 import analyze as Z  # noqa: E402
from ar003 import design as D  # noqa: E402

BEST = D.BEST
C = D.CONTROLLER


def P(stmt, name, fn, sense, key):
    return {"stmt": stmt, "name": name, "fn": fn, "sense": sense, "key": key}


def info_limit(data):
    return Z.info_limit(data)


def mix(arm, other):
    return lambda data: Z.U_mix(data, arm) - Z.U_mix(data, other)


def at(arm, other, L):
    return lambda data: Z.U_L(data, arm, L) - Z.U_L(data, other, L)


def four(arm, other):
    return lambda data: Z.four(data, arm, other)


def kept(L, k):
    return lambda data: Z.kept(data, C, L, k)


def sham(run, arm=C):
    return lambda data: Z.sham(data, run, arm)


def rate(arm, situation, L, which):
    return lambda data: Z.rate(data, arm, situation, L, which=which)


def misread_adv(arm, other, situation="memory"):
    run = D.run_name(situation, D.MISREAD_SIGMA)
    return lambda data: Z.case(data, run, "r_in", arm) - Z.case(data, run, "r_in", other)


T = {"E1": 1e-12, "E2": 0.09, "E3_2": 0.06, "E3_4": 0.03, "E3_8": 0.11, "E4f": 0.005, "E4s": 0.08, "E5_4": 0.0,
     "E5_8": 0.0, "E6c": 0.01, "E6n": 0.002, "E7m4": 0.6, "E7c4": 0.6, "E7m8": 0.95, "E7c8": 0.95, "E7n": 0.05,
     "E8f": -0.005, "E8s": -0.01, "E9u": 0.05, "E9n": 0.01, "E10": -0.005}   # set from P47 (p47b_ar003_margins.txt)
K = {"E5_4": 0.9, "E5_8": 0.9}                                   # the declared shares (set from P47)

PARTS = [
    P("E1", "E1 max over arms and cases of abs(u(new) + u(old) - 1), change@0", info_limit, "le", "E1"),
    P("E2", "E2 U_mix(vms) - U_mix(vote)", mix(C, BEST), "ge", "E2"),
    P("E3", "E3 U_2(vms) - U_2(det)", at(C, "det", 2), "ge", "E3_2"),
    P("E3", "E3 U_4(vms) - U_4(det)", at(C, "det", 4), "ge", "E3_4"),
    P("E3", "E3 U_8(vms) - U_8(det)", at(C, "det", 8), "ge", "E3_8"),
    P("E4", "E4 four scorings at 4 (none, body, shared, cue): (1/8) sum u(vms) - u(ms)", four(C, "ms"), "ge", "E4f"),
    P("E4", "E4 U_2(vms) - U_2(ms)", at(C, "ms", 2), "ge", "E4s"),
    P("E5", "E5 kept at 4: (u(vms) - u(vote)) - k (u(vdial) - u(vote)), memory + correlated", None, "ge", "E5_4"),
    P("E5", "E5 kept at 8: (u(vms) - u(vote)) - k (u(vdial) - u(vote)), memory + correlated", None, "ge", "E5_8"),
    P("E6", "E6 sheet cost under scattered cue damage: r_all(vote) - r_all(vms), cue@0", sham("cue@0"), "le", "E6c"),
    P("E6", "E6 sheet cost with no event: r_all(vote) - r_all(vms), none@0", sham("none@0"), "le", "E6n"),
    P("E7", "E7 p(vms fires on the patch | memory, 4 x 4)", rate(C, "memory", 4, "located"), "ge", "E7m4"),
    P("E7", "E7 p(vms fires on the patch | correlated, 4 x 4)", rate(C, "correlated", 4, "located"), "ge", "E7c4"),
    P("E7", "E7 p(vms fires on the patch | memory, 8 x 8)", rate(C, "memory", 8, "located"), "ge", "E7m8"),
    P("E7", "E7 p(vms fires on the patch | correlated, 8 x 8)", rate(C, "correlated", 8, "located"), "ge", "E7c8"),
    P("E7", "E7 p(vms fires at all | none)", rate(C, "none", 4, "fired"), "le", "E7n"),
    P("E8", "E8 four scorings at 4: (1/8) sum u(vms) - u(vote)", four(C, BEST), "ge", "E8f"),
    P("E8", "E8 U_2(vms) - U_2(vote)", at(C, BEST, 2), "ge", "E8s"),
    P("E9", "E9 under misread cues (sigma 1), memory damage: u(vms) - u(det), memory@1", misread_adv(C, "det"), "ge", "E9u"),
    P("E9", "E9 under misread cues with no event: r_all(vote) - r_all(vms), none@1 (the vote's none@0)", sham("none@1"), "le", "E9n"),
    P("E10", "E10 price at 4 x 4 over memory and correlated: (1/8) sum u(vms) - (fire u(vdial) + (1 - fire) u(vote))",
      lambda data: Z.price_hits(data, C, 4), "ge", "E10"),
]


def bind():
    for p in PARTS:
        p["threshold"] = T[p["key"]]
        if p["key"] in K:
            k, L = K[p["key"]], int(p["key"][-1])
            p["k"] = k
            p["fn"] = (lambda kk, LL: (lambda data: Z.kept(data, C, LL, kk)))(k, L) if k is not None else None


bind()


def score(data):
    out = {}
    for p in PARTS:
        if p["fn"] is None:
            continue
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
    """The registered claims and rules, with the thresholds as set (T, K)."""
    t, k = T, K
    return [
        {"id": "E1", "claim": "on the information-limit pair no arm can win: every arm ties, the controller included",
         "rule": f"HOLDS if, in change@0, the largest abs(u(arm, change/new) + u(arm, change/old) - 1) over every arm and case "
                 f"is at most {t['E1']:g}, else FAILS (derived identity)"},
        {"id": "E2", "claim": "over the declared mix of injury sizes the controller (DET_STAR with the vote as its default) beats "
                              "the best fixed policy",
         "rule": f"HOLDS if U_mix(vms) - U_mix(vote) >= {t['E2']}, else FAILS"},
        {"id": "E3", "claim": "the controller beats or matches AR002's controller (det with the rest default) at each size",
         "rule": f"HOLDS if U_2(vms) - U_2(det) >= {t['E3_2']}, U_4(vms) - U_4(det) >= {t['E3_4']} and "
                 f"U_8(vms) - U_8(det) >= {t['E3_8']}, else FAILS"},
        {"id": "E4", "claim": "the vote default is worth something of its own: against the same detector with the rest default, "
                              "where nothing needs correcting and at 2 x 2",
         "rule": f"HOLDS if (1/8) sum over none, body, shared and cue at 4 x 4 of u(vms) - u(ms) >= {t['E4f']} and "
                 f"U_2(vms) - U_2(ms) >= {t['E4s']}, else FAILS"},
        {"id": "E5", "claim": "the controller keeps a declared share of the declared signal's worth (vdial: the signal sent "
                              "promptly over the patch under the same default) at 4 x 4 and at 8 x 8",
         "rule": f"HOLDS if, summed over memory and correlated damage, (u(vms) - u(vote)) - k (u(vdial) - u(vote)) >= "
                 f"{t['E5_4']} at 4 x 4 with k = {k['E5_4']} and >= {t['E5_8']} at 8 x 8 with k = {k['E5_8']}, else FAILS"},
        {"id": "E6", "claim": "the controller's false alarms cost intact tissue within the confirmed harm bound",
         "rule": f"HOLDS if r_all(vote) - r_all(vms) is at most {t['E6c']} under scattered cue damage (cue@0) and at most "
                 f"{t['E6n']} with no event (none@0), else FAILS"},
        {"id": "E7", "claim": "the detector finds memory and correlated damage on the patch at 4 x 4 and 8 x 8, and seldom fires "
                              "with no event",
         "rule": f"HOLDS if vms fires with its footprint on the patch in at least {t['E7m4']} and {t['E7c4']} of memory and "
                 f"correlated lineage-cases at 4 x 4 and {t['E7m8']} and {t['E7c8']} at 8 x 8, and fires at all in at most "
                 f"{t['E7n']} of no-event lineage-cases, else FAILS"},
        {"id": "E8", "claim": "the controller gives up nothing where nothing is wrong, and nothing at 2 x 2, against the vote "
                              "(non-inferiority)",
         "rule": f"HOLDS if (1/8) sum over none, body, shared and cue at 4 x 4 of u(vms) - u(vote) >= {t['E8f']} and "
                 f"U_2(vms) - U_2(vote) >= {t['E8s']}, else FAILS"},
        {"id": "E9", "claim": "under misread cues (GC001's sigma 1) the controller keeps an advantage over AR002's controller in "
                              "memory damage, and its false alarms with no event cost the sheet within the confirmed bound",
         "rule": f"HOLDS if u(vms) - u(det) in memory@1 >= {t['E9u']} and r_all(vote) - r_all(vms) with no event under "
                 f"misreads (none@1, against the vote's none@0) <= {t['E9n']}, else FAILS"},
        {"id": "E10", "claim": "making the signal costs nothing: the declared signal's exact value at the controller's own "
                               "firing predicts its value in memory and correlated damage at 4 x 4",
         "rule": f"HOLDS if (1/8) sum over memory and correlated at 4 x 4 of u(vms) - (fire x u(vdial) + (1 - fire) x "
                 f"u(vote)), per lineage-case, >= {t['E10']}, else FAILS"},
    ]


STATEMENTS = statements()


def freeze():
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "best": BEST,
                               "controller": C, "thresholds": T, "shares": K,
                               "parts": [{k: v for k, v in p.items() if k != "fn"} for p in PARTS],
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
