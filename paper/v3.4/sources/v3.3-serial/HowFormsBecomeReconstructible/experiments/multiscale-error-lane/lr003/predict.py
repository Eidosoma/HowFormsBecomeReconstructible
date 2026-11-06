"""LR003's registered statements and their scoring, written before any development outcome.

python -m lr003.predict   (writes lr003/frozen/predictions.json)

Thresholds were set from engineering probes P18 and P18b (32 cases on blocks 900740-900743 under tag mse-p18, the
same cases and draws; disclosed in REGISTRATION_LR003.md), with margins for 128 cases. Scored by lr003.analyze on
block means over the 16 development blocks at t = 4,000. 'r_sign' is the record's agreement with the template;
'opened' the mean share of bonds taught by the body over the window; theta x0 and x1 scale the environmental field;
p_b is the bond-flip rate per bond and update.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr003 import design as D  # noqa: E402

T1 = D.READS[-1]
TEACHERS = D.REPAIRS
FIELD = (("S4", "dw"), ("S4", "li4"), ("LB", "dw"), ("LB", "li4"))       # S4 and LB on both bodies, under theta x1

STATEMENTS = [
    {"id": "T1", "kind": "without noise the gates refuse the body's errors",
     "claim": "Without bond noise every gate keeps the record whole, where teaching from the body writes in the body's "
              "design and the field's distortions",
     "rule": "HOLDS if at p_b = 0 the agree, syndrome and site teachers keep r_sign >= 0.99 in every unit for both bodies, "
             "while body teaching gives <= 0.82 for li4 on F0 at theta x0 and <= 0.98 for S4 and LB on both bodies at "
             "theta x1, else FAILS",
     "inputs": "P18/P18b: gates 1.000 everywhere; body 0.789; 0.918-0.969"},
    {"id": "T2", "kind": "a bond-level check loses the body's repair",
     "claim": "Asking the body only about frustrated bonds loses most of its repair in quiet tissue at a moderate rate",
     "rule": "HOLDS if at theta x0 and p_b = 1e-2 the syndrome teacher gives r_sign <= 0.80 and at least 0.15 below body "
             "teaching for S4 on both bodies and LB on li4, else FAILS",
     "inputs": "P18: 0.598, 0.699, 0.619; body 0.974, 0.972, 0.871 (gaps 0.253-0.375)"},
    {"id": "T3", "kind": "a site-level check recovers it",
     "claim": "Asking the body about every bond of a site with a frustrated bond recovers nearly all of its repair in "
              "quiet tissue",
     "rule": "HOLDS if at theta x0 and p_b = 1e-2 the site teacher's r_sign is >= body teaching's - 0.04 for S4 on both "
             "bodies, F0 on dw and LB on li4, and >= the syndrome teacher's + 0.15 for S4 on both bodies and LB on li4, "
             "else FAILS",
     "inputs": "P18b: site - body -0.009, -0.012, -0.001, -0.020; site - syndrome 0.367, 0.261, 0.233"},
    {"id": "T4", "kind": "noise opens the gate to the body's errors",
     "claim": "Once noise opens the site gate it lets in the body's errors with its help: the stripe body's design and "
              "the field's distortions",
     "rule": "HOLDS if at p_b = 1e-3 the site gate opens on >= 0.30 of the bonds (mean over the window) in every unit for "
             "both bodies, and the site teacher's r_sign is <= 0.80 for li4 on F0 at theta x0 and <= 0.95 for S4 and LB "
             "on both bodies at theta x1, else FAILS",
     "inputs": "P18b: opened 0.356-0.494; 0.693; 0.823-0.902"},
    {"id": "T5", "kind": "agreement is a stronger signal, not new information",
     "claim": "Teaching from the body where body and record agree beats the record teaching itself, but fails above a "
              "rate of about 1e-3 as the record does",
     "rule": "HOLDS if agree - record in r_sign is >= 0.05 at p_b = 1e-3, and the agree teacher's r_sign is <= 0.80 at "
             "3e-3, in every unit for both bodies, else FAILS",
     "inputs": "P18: +0.089 to +0.155; at most 0.754"},
    {"id": "T6", "kind": "with parity a gate is the record's two layers",
     "claim": "With parity, the site gate keeps the record at a low rate where the body errs, but no better than "
              "LR001's two layers",
     "rule": "HOLDS if at p_b = 1e-3 site+parity gives r_sign >= 0.97 and within 0.02 of record+parity for li4 on F0 at "
             "theta x0 and for S4 and LB on both bodies at theta x1, else FAILS",
     "inputs": "P18/P18b: 0.987-0.991; differences +0.002 to +0.006"},
    {"id": "T7", "kind": "no teacher survives disorder at a high rate",
     "claim": "Under the full field at a high rate no teacher keeps stripes or the labyrinth",
     "rule": "HOLDS if at theta x1 and p_b = 1e-2 every teacher gives r_sign <= 0.70 for S4 and LB on both bodies, else FAILS",
     "inputs": "P18/P18b: at most 0.651 (body, li4 S4)"},
    {"id": "T8", "kind": "parity defeats a learner when errors are dense",
     "claim": "Adding parity to the site gate at a high rate in quiet tissue undoes its repair",
     "rule": "HOLDS if at theta x0 and p_b = 1e-2 on S4 the site teacher gives r_sign >= 0.90 and site+parity <= 0.75, on "
             "both bodies, else FAILS",
     "inputs": "P18b: site 0.965, 0.960; site+parity 0.530, 0.632"},
]


def lv(L, unit, body, cond, ep="r_sign"):
    x = L[unit][body][cond][ep if ep == "opened" else f"{ep}@{T1}"]
    return x[0]


def score(L):
    S = {}
    U = D.unit_name
    v = {f"{u}/{b}/{g}": lv(L, u, b, f"0/{g}") for u in D.UNITS for b in D.BODIES for g in ("agree", "syndrome", "site")}
    body = {"F0_t0/li4": lv(L, U("F0", 0.0), "li4", "0/body")}
    body.update({f"{p}_t1/{b}": lv(L, U(p, 1.0), b, "0/body") for p, b in FIELD})
    ok = min(v.values()) >= 0.99 and body["F0_t0/li4"] <= 0.82 and all(body[f"{p}_t1/{b}"] <= 0.98 for p, b in FIELD)
    S["T1"] = {"verdict": "HOLDS" if ok else "FAILS", "gates@0": v, "body@0": body}

    pairs = (("S4", "dw"), ("S4", "li4"), ("LB", "li4"))
    v = {f"{p}/{b}": {"syndrome": lv(L, U(p, 0.0), b, "0.01/syndrome"), "body": lv(L, U(p, 0.0), b, "0.01/body")} for p, b in pairs}
    ok = all(x["syndrome"] <= 0.80 and x["body"] - x["syndrome"] >= 0.15 for x in v.values())
    S["T2"] = {"verdict": "HOLDS" if ok else "FAILS", "t0@1e-2": v}

    near = {f"{p}/{b}": round(lv(L, U(p, 0.0), b, "0.01/site") - lv(L, U(p, 0.0), b, "0.01/body"), 4)
            for p, b in (("S4", "dw"), ("S4", "li4"), ("F0", "dw"), ("LB", "li4"))}
    over = {f"{p}/{b}": round(lv(L, U(p, 0.0), b, "0.01/site") - lv(L, U(p, 0.0), b, "0.01/syndrome"), 4) for p, b in pairs}
    ok = min(near.values()) >= -0.04 and min(over.values()) >= 0.15
    S["T3"] = {"verdict": "HOLDS" if ok else "FAILS", "site_minus_body@1e-2": near, "site_minus_syndrome@1e-2": over}

    op = {f"{u}/{b}": lv(L, u, b, "0.001/site", "opened") for u in D.UNITS for b in D.BODIES}
    f0 = lv(L, U("F0", 0.0), "li4", "0.001/site")
    fld = {f"{p}_t1/{b}": lv(L, U(p, 1.0), b, "0.001/site") for p, b in FIELD}
    ok = min(op.values()) >= 0.30 and f0 <= 0.80 and max(fld.values()) <= 0.95
    S["T4"] = {"verdict": "HOLDS" if ok else "FAILS", "opened@1e-3": op, "F0_t0/li4@1e-3": f0, "field@1e-3": fld}

    d = {f"{u}/{b}": round(lv(L, u, b, "0.001/agree") - lv(L, u, b, "0.001/record"), 4) for u in D.UNITS for b in D.BODIES}
    a3 = {f"{u}/{b}": lv(L, u, b, "0.003/agree") for u in D.UNITS for b in D.BODIES}
    ok = min(d.values()) >= 0.05 and max(a3.values()) <= 0.80
    S["T5"] = {"verdict": "HOLDS" if ok else "FAILS", "agree_minus_record@1e-3": d, "agree@3e-3": a3}

    cells = (("F0", 0.0, "li4"),) + tuple((p, 1.0, b) for p, b in FIELD)
    v = {f"{U(p, t)}/{b}": {"site+parity": lv(L, U(p, t), b, "0.001/site+parity"),
                            "record+parity": lv(L, U(p, t), b, "0.001/record+parity")} for p, t, b in cells}
    ok = all(x["site+parity"] >= 0.97 and abs(x["site+parity"] - x["record+parity"]) <= 0.02 for x in v.values())
    S["T6"] = {"verdict": "HOLDS" if ok else "FAILS", "at1e-3": v}

    v = {f"{p}_t1/{b}/{rep}": lv(L, U(p, 1.0), b, f"0.01/{rep}") for p, b in FIELD for rep in TEACHERS}
    S["T7"] = {"verdict": "HOLDS" if max(v.values()) <= 0.70 else "FAILS", "t1@1e-2": v}

    v = {b: {"site": lv(L, U("S4", 0.0), b, "0.01/site"), "site+parity": lv(L, U("S4", 0.0), b, "0.01/site+parity")}
         for b in D.BODIES}
    ok = all(x["site"] >= 0.90 and x["site+parity"] <= 0.75 for x in v.values())
    S["T8"] = {"verdict": "HOLDS" if ok else "FAILS", "S4_t0@1e-2": v}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
