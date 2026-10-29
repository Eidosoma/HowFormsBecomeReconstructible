"""LR002's registered statements and their scoring, written before any development outcome.

python -m lr002.predict   (writes lr002/frozen/predictions.json)

Thresholds were set from engineering probe P17 (32 cases on blocks 900730-900733 under tag mse-p17, disclosed in
REGISTRATION_LR002.md), with margins for 128 cases. Scored by lr002.analyze on block means over the 16 development
blocks at t = 4,000. 'r_sign' is the record's agreement with the template, 'sign' the body's; theta x0 and x1 are
environmental-field spreads 0 and 0.2; p_b is the bond-flip rate per bond and update.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr002 import design as D  # noqa: E402

T1 = D.READS[-1]
NATIVE_T0 = (("li4", "S4"), ("dw", "S4"), ("dw", "F0"))      # patterns each body holds by itself in a clean sheet

STATEMENTS = [
    {"id": "L1", "kind": "unrepaired relations are lost",
     "claim": "Without repair, bond noise erases the record of relations at every rate tested, on every pattern and body",
     "rule": "HOLDS if with no repair r_sign at t = 4000 is <= 0.60 at p_b = 1e-3, 3e-3, 1e-2 and 3e-2 in every unit for "
             "both bodies, else FAILS",
     "inputs": "P17: 0.494-0.502"},
    {"id": "L2", "kind": "repair from the record itself has a threshold",
     "claim": "LR001's two layers, relearning from the record and plaquette parity, keep the record below a bond-flip "
              "rate of about 1e-3 and lose it above",
     "rule": "HOLDS if with record+parity r_sign at t = 4000 is >= 0.95 at p_b = 1e-3, <= 0.80 at 3e-3 and <= 0.60 at "
             "1e-2 in every unit for both bodies, else FAILS",
     "inputs": "P17: 0.984; 0.688-0.690; 0.496-0.504"},
    {"id": "L3", "kind": "the body repairs the relations of what it holds",
     "claim": "Relearning from the body keeps the record, and the body its pattern, far above that threshold for patterns "
              "the body holds by itself in a clean sheet",
     "rule": "HOLDS if at theta x0 with body relearning, at p_b = 1e-2 and 3e-2, r_sign at t = 4000 is >= 0.90 for li4 on "
             "S4, dw on S4 and dw on F0 and >= 0.80 for li4 on LB, and at 1e-2 the body's sign is >= 0.95 for the first "
             "three and >= 0.85 for li4 on LB, else FAILS",
     "inputs": "P17: r_sign 0.963-0.981, LB 0.869 and 0.859; sign 0.996-0.999, LB 0.891"},
    {"id": "L4", "kind": "the teacher must be outside the record",
     "claim": "The same learning rule fails when the record teaches itself and works when the body teaches it",
     "rule": "HOLDS if at theta x0 and p_b = 1e-3 relearning from the record alone gives r_sign at t = 4000 <= 0.85 in "
             "every unit for both bodies, while relearning from the body alone gives >= 0.95 for li4 on S4 and LB and dw "
             "on S4 and F0, else FAILS",
     "inputs": "P17: record 0.795-0.796; body 0.984-0.999"},
    {"id": "L5", "kind": "a body teaches only what it holds",
     "claim": "A body that cannot hold a pattern teaches its record the wrong relations: the stripe body corrupts two "
              "domains even without noise, and under noise each body keeps the record of its own pattern far better "
              "than the other body",
     "rule": "HOLDS if at theta x0 li4's body relearning at p_b = 0 gives r_sign on F0 at t = 4000 <= 0.85 while "
             "record+parity gives >= 0.99, and at p_b = 1e-2 with body relearning (li4 - dw) r_sign on LB is >= 0.15 "
             "and (dw - li4) on F0 is >= 0.25, else FAILS",
     "inputs": "P17: 0.781 against 1.000; +0.269; +0.379"},
    {"id": "L6", "kind": "under disorder the body teaches the disorder",
     "claim": "Under the full environmental field relearning from the body copies the disorder into the record even "
              "without noise, and no longer protects it at a high rate",
     "rule": "HOLDS if at theta x1 for S4 and LB on both bodies r_sign at t = 4000 with body relearning is <= 0.97 at "
             "p_b = 0 (where no repair keeps >= 0.99) and <= 0.75 at p_b = 1e-2, else FAILS",
     "inputs": "P17: 0.886-0.933 (none 1.000); 0.557-0.597"},
    {"id": "L7", "kind": "coarse domains keep the body's protection",
     "claim": "The double well still protects the record of its two domains under the full field at a high rate",
     "rule": "HOLDS if at theta x1 and p_b = 1e-2 dw's body relearning gives r_sign on F0 at t = 4000 >= 0.80, else FAILS",
     "inputs": "P17: 0.880"},
    {"id": "L8", "kind": "parity helps sparse errors and harms dense ones",
     "claim": "Adding plaquette parity to body relearning helps where errors are sparse and harms where they are dense",
     "rule": "HOLDS if on S4 for both bodies (body+parity - body) r_sign at t = 4000 is >= 0.02 at theta x1 and "
             "p_b = 1e-3, and (body - body+parity) is >= 0.04 at theta x0 and p_b = 1e-2, else FAILS",
     "inputs": "P17: +0.067 (dw), +0.076 (li4); +0.124 (dw), +0.087 (li4)"},
]


def lv(L, unit, body, cond, ep="r_sign"):
    return L[unit][body][cond][f"{ep}@{T1}"][0]


def score(L):
    S = {}
    t0 = [u for u in D.UNITS if D.parse_unit(u)[1] == 0.0]

    v = {f"{u}/{b}/{r:g}": lv(L, u, b, f"{r:g}/none") for u in D.UNITS for b in D.BODIES for r in D.RATES[1:]}
    S["L1"] = {"verdict": "HOLDS" if max(v.values()) <= 0.60 else "FAILS", "none_r_sign": v}

    v = {f"{r:g}/{u}/{b}": lv(L, u, b, f"{r:g}/record+parity") for r in (0.001, 0.003, 0.01) for u in D.UNITS for b in D.BODIES}
    ok = all(v[f"0.001/{u}/{b}"] >= 0.95 and v[f"0.003/{u}/{b}"] <= 0.80 and v[f"0.01/{u}/{b}"] <= 0.60
             for u in D.UNITS for b in D.BODIES)
    S["L2"] = {"verdict": "HOLDS" if ok else "FAILS", "record+parity_r_sign": v}

    r = {f"{b}/{p}/{rt:g}": lv(L, f"{p}_t0", b, f"{rt:g}/body") for rt in (0.01, 0.03) for b, p in (*NATIVE_T0, ("li4", "LB"))}
    s = {f"{b}/{p}": lv(L, f"{p}_t0", b, "0.01/body", "sign") for b, p in (*NATIVE_T0, ("li4", "LB"))}
    ok = all(r[f"{b}/{p}/{rt:g}"] >= 0.90 for b, p in NATIVE_T0 for rt in (0.01, 0.03)) \
        and all(r[f"li4/LB/{rt:g}"] >= 0.80 for rt in (0.01, 0.03)) \
        and all(s[f"{b}/{p}"] >= 0.95 for b, p in NATIVE_T0) and s["li4/LB"] >= 0.85
    S["L3"] = {"verdict": "HOLDS" if ok else "FAILS", "body_r_sign": r, "body_sign@1e-2": s}

    rec = {f"{u}/{b}": lv(L, u, b, "0.001/record") for u in t0 for b in D.BODIES}
    bod = {f"{b}/{p}": lv(L, f"{p}_t0", b, "0.001/body") for b, p in (("li4", "S4"), ("li4", "LB"), ("dw", "S4"), ("dw", "F0"))}
    ok = max(rec.values()) <= 0.85 and min(bod.values()) >= 0.95
    S["L4"] = {"verdict": "HOLDS" if ok else "FAILS", "record_alone@1e-3": rec, "body_alone@1e-3": bod}

    a = {"li4_F0_body@0": lv(L, "F0_t0", "li4", "0/body"), "li4_F0_record+parity@0": lv(L, "F0_t0", "li4", "0/record+parity")}
    c = {"LB_li4-dw@1e-2": round(lv(L, "LB_t0", "li4", "0.01/body") - lv(L, "LB_t0", "dw", "0.01/body"), 4),
         "F0_dw-li4@1e-2": round(lv(L, "F0_t0", "dw", "0.01/body") - lv(L, "F0_t0", "li4", "0.01/body"), 4)}
    ok = a["li4_F0_body@0"] <= 0.85 and a["li4_F0_record+parity@0"] >= 0.99 and c["LB_li4-dw@1e-2"] >= 0.15 \
        and c["F0_dw-li4@1e-2"] >= 0.25
    S["L5"] = {"verdict": "HOLDS" if ok else "FAILS", "levels": a, "contrasts": c}

    z = {f"{p}/{b}": lv(L, f"{p}_t1", b, "0/body") for p in ("S4", "LB") for b in D.BODIES}
    n = {f"{p}/{b}": lv(L, f"{p}_t1", b, "0/none") for p in ("S4", "LB") for b in D.BODIES}
    h = {f"{p}/{b}": lv(L, f"{p}_t1", b, "0.01/body") for p in ("S4", "LB") for b in D.BODIES}
    ok = max(z.values()) <= 0.97 and min(n.values()) >= 0.99 and max(h.values()) <= 0.75
    S["L6"] = {"verdict": "HOLDS" if ok else "FAILS", "body@0": z, "none@0": n, "body@1e-2": h}

    v = lv(L, "F0_t1", "dw", "0.01/body")
    S["L7"] = {"verdict": "HOLDS" if v >= 0.80 else "FAILS", "dw_F0_t1_body@1e-2": v}

    sp = {b: round(lv(L, "S4_t1", b, "0.001/body+parity") - lv(L, "S4_t1", b, "0.001/body"), 4) for b in D.BODIES}
    de = {b: round(lv(L, "S4_t0", b, "0.01/body") - lv(L, "S4_t0", b, "0.01/body+parity"), 4) for b in D.BODIES}
    ok = min(sp.values()) >= 0.02 and min(de.values()) >= 0.04
    S["L8"] = {"verdict": "HOLDS" if ok else "FAILS", "t1@1e-3_parity_gain": sp, "t0@1e-2_parity_loss": de}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
