"""LR004's registered statements and their scoring, written before any development outcome.

python -m lr004.predict   (writes lr004/frozen/predictions.json)

Thresholds were set from engineering probe P19 (32 cases on blocks 900750-900753 under tag mse-p19, disclosed in
REGISTRATION_LR004.md), with margins for 128 cases. Scored by lr004.analyze on block means over the 16 development
blocks at t = 4,000. 'r_sign' is the first record's agreement with the template (the record the body reads); theta x0
and x1 scale the environmental field; p_b is the bond-flip rate per bond and update.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr004 import design as D  # noqa: E402

T1 = D.READS[-1]
FIELD = (("S4", "dw"), ("S4", "li4"), ("LB", "dw"), ("LB", "li4"))       # S4 and LB on both bodies, under theta x1
QUIET = (("S4", "dw"), ("S4", "li4"), ("F0", "dw"), ("LB", "li4"))       # patterns each body makes, quiet tissue

STATEMENTS = [
    {"id": "V1", "kind": "three copies refuse the body's errors",
     "claim": "Without bond noise, two records voting with the body keep every record whole, where teaching from the "
              "body writes in its design and the field's distortions",
     "rule": "HOLDS if at p_b = 0 the vote keeps r_sign >= 0.99 in every unit for both bodies, while body teaching gives "
             "<= 0.82 for li4 on F0 at theta x0 and <= 0.98 for S4 and LB on both bodies at theta x1, else FAILS",
     "inputs": "P19: vote 1.000 everywhere; body 0.785; 0.875-0.934"},
    {"id": "V2", "kind": "three copies keep the body's repair",
     "claim": "In quiet tissue, two records voting with the body keep nearly all of the body's repair at high rates",
     "rule": "HOLDS if at theta x0 and p_b = 1e-2 and 3e-2 the vote's r_sign is >= body teaching's - 0.04 for S4 on both "
             "bodies, F0 on dw and LB on li4, else FAILS",
     "inputs": "P19: vote - body -0.016 to +0.031"},
    {"id": "V3", "kind": "three copies protect where the body errs",
     "claim": "Where the body errs, the vote keeps the record far above every two-copy teacher",
     "rule": "HOLDS if at p_b = 3e-3 the vote gives r_sign >= 0.85 and >= 0.10 above the best of record+parity, body and "
             "site for S4 and LB on both bodies at theta x1, and >= 0.90 for li4 on F0 at theta x0 where body teaching "
             "gives <= 0.70, else FAILS",
     "inputs": "P19: 0.893-0.934, +0.197 to +0.228; 0.954 against 0.647"},
    {"id": "V4", "kind": "two copies cannot break ties",
     "claim": "Two records without a tie-breaker, relearning only where they agree, fail as one record does",
     "rule": "HOLDS if the pair teacher gives r_sign <= 0.70 at p_b = 3e-3 and <= 0.60 at 1e-2, in every unit for both "
             "bodies, else FAILS",
     "inputs": "P19: 0.612-0.614; 0.495-0.503"},
    {"id": "V5", "kind": "a sparse positional copy arbitrates little",
     "claim": "Positional anchors at a quarter of the cells arbitrate too few disagreements to protect the record",
     "rule": "HOLDS if anchors4 gives r_sign at least 0.10 below the vote at p_b = 3e-3 and <= 0.70 at 1e-2, in every unit "
             "for both bodies, else FAILS",
     "inputs": "P19: 0.146-0.233 below; 0.571-0.623"},
    {"id": "V6", "kind": "the vote corrects the body's own pattern",
     "claim": "On the labyrinth, two records voting with the body keep the record better than the body alone, on either body",
     "rule": "HOLDS if at theta x0 and p_b = 1e-2 the vote's r_sign on LB exceeds body teaching's by >= 0.01 on both "
             "bodies, else FAILS",
     "inputs": "P19: +0.227 (dw), +0.027 (li4)"},
    {"id": "V7", "kind": "the vote's limit",
     "claim": "When errors are dense and the body errs, a record error coinciding with the body's makes the wrong side "
              "the majority, and even three copies lose the record",
     "rule": "HOLDS if at p_b = 1e-2 the vote gives r_sign <= 0.80 for S4 and LB on both bodies at theta x1 and <= 0.75 for "
             "li4 on F0 at theta x0, else FAILS",
     "inputs": "P19: 0.666-0.738; 0.666"},
]


def lv(L, unit, body, cond):
    return L[unit][body][cond][f"r_sign@{T1}"][0]


def score(L):
    S = {}
    U = D.unit_name
    v = {f"{u}/{b}": lv(L, u, b, "0/vote") for u in D.UNITS for b in D.BODIES}
    body = {"F0_t0/li4": lv(L, U("F0", 0.0), "li4", "0/body")}
    body.update({f"{p}_t1/{b}": lv(L, U(p, 1.0), b, "0/body") for p, b in FIELD})
    ok = min(v.values()) >= 0.99 and body["F0_t0/li4"] <= 0.82 and all(body[f"{p}_t1/{b}"] <= 0.98 for p, b in FIELD)
    S["V1"] = {"verdict": "HOLDS" if ok else "FAILS", "vote@0": v, "body@0": body}

    v = {f"{p}/{b}/{r:g}": round(lv(L, U(p, 0.0), b, f"{r:g}/vote") - lv(L, U(p, 0.0), b, f"{r:g}/body"), 4)
         for p, b in QUIET for r in (0.01, 0.03)}
    S["V2"] = {"verdict": "HOLDS" if min(v.values()) >= -0.04 else "FAILS", "vote_minus_body": v}

    fld = {}
    for p, b in FIELD:
        u = U(p, 1.0)
        best = max(lv(L, u, b, f"0.003/{rep}") for rep in ("record+parity", "body", "site"))
        fld[f"{p}_t1/{b}"] = {"vote": lv(L, u, b, "0.003/vote"), "best_other": best}
    des = {"vote": lv(L, U("F0", 0.0), "li4", "0.003/vote"), "body": lv(L, U("F0", 0.0), "li4", "0.003/body")}
    ok = all(x["vote"] >= 0.85 and x["vote"] - x["best_other"] >= 0.10 for x in fld.values()) and des["vote"] >= 0.90 \
        and des["body"] <= 0.70
    S["V3"] = {"verdict": "HOLDS" if ok else "FAILS", "field@3e-3": fld, "F0_t0/li4@3e-3": des}

    v3 = {f"{u}/{b}": lv(L, u, b, "0.003/pair") for u in D.UNITS for b in D.BODIES}
    v2 = {f"{u}/{b}": lv(L, u, b, "0.01/pair") for u in D.UNITS for b in D.BODIES}
    S["V4"] = {"verdict": "HOLDS" if max(v3.values()) <= 0.70 and max(v2.values()) <= 0.60 else "FAILS",
               "pair@3e-3": v3, "pair@1e-2": v2}

    gap = {f"{u}/{b}": round(lv(L, u, b, "0.003/vote") - lv(L, u, b, "0.003/anchors4"), 4) for u in D.UNITS for b in D.BODIES}
    a2 = {f"{u}/{b}": lv(L, u, b, "0.01/anchors4") for u in D.UNITS for b in D.BODIES}
    S["V5"] = {"verdict": "HOLDS" if min(gap.values()) >= 0.10 and max(a2.values()) <= 0.70 else "FAILS",
               "vote_minus_anchors4@3e-3": gap, "anchors4@1e-2": a2}

    v = {b: round(lv(L, U("LB", 0.0), b, "0.01/vote") - lv(L, U("LB", 0.0), b, "0.01/body"), 4) for b in D.BODIES}
    S["V6"] = {"verdict": "HOLDS" if min(v.values()) >= 0.01 else "FAILS", "LB_t0_vote_minus_body@1e-2": v}

    f = {f"{p}_t1/{b}": lv(L, U(p, 1.0), b, "0.01/vote") for p, b in FIELD}
    d0 = lv(L, U("F0", 0.0), "li4", "0.01/vote")
    S["V7"] = {"verdict": "HOLDS" if max(f.values()) <= 0.80 and d0 <= 0.75 else "FAILS", "field@1e-2": f, "F0_t0/li4@1e-2": d0}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
