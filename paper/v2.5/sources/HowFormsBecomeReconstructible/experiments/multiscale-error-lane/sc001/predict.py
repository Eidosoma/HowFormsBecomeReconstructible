"""SC001's registered statements and their scoring, written before any development outcome.

python -m sc001.predict   (writes sc001/frozen/predictions.json)

Thresholds were set from engineering probes P22b and P22c (32 cases on blocks 900780-900783 under tag mse-p22,
disclosed in REGISTRATION_SC001.md), with margins for 128 cases. Scored by sc001.analyze on block means over the 16
development blocks at t = 4,000 (panel G: S4 at theta x0; panel R: S4 and F0 at theta x0). 'sheet' is the body's
agreement with the pattern over occupied cells; 'far' over the far side (ring distance 12-15 from the boundary);
'patch' and 'r_patch' the body's and the record's agreement inside the killed patch. No statement reads turn/100.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sc001 import design as D  # noqa: E402

UNIT_G = "S4_t0"
SPEEDS = tuple(f"{s:g}" for s in D.REGROW)

STATEMENTS = [
    {"id": "G1", "kind": "the engine reproduces DL003",
     "claim": "Growth by DL003's prescribed front registers the stripes over the whole sheet in cellpop, as in DL003",
     "rule": "HOLDS if li4's front/100 across the stripes (perp) gives sheet >= 0.97 and far side >= 0.95, else FAILS",
     "inputs": "P22c: 0.998, 0.998"},
    {"id": "G2", "kind": "real growth loses the far side",
     "claim": "Growth by division at the margin, at the same speed, does not register the far side as the prescribed "
              "front does",
     "rule": "HOLDS if li4 perp grow/100's far side is <= front/100's - 0.10 and its intact share <= 0.50, else FAILS",
     "inputs": "P22c: -0.176; 0.188"},
    {"id": "G3", "kind": "not inheritance",
     "claim": "The loss does not come from daughters copying their parents: newborn daughters with the same divisions "
              "register alike",
     "rule": "HOLDS if li4 perp |nb/100 - grow/100| on the sheet is <= 0.03, else FAILS",
     "inputs": "P22c: +0.002"},
    {"id": "G4", "kind": "slower growth reaches further",
     "claim": "Slower growth by division lengthens the registered reach but does not restore it",
     "rule": "HOLDS if li4 perp grow/200's far side is >= grow/100's + 0.03 and <= front/200's - 0.05, else FAILS",
     "inputs": "P22c: +0.063; -0.112"},
    {"id": "G5", "kind": "diffusion is a low-pass filter",
     "claim": "A diffusing boundary signal carries only coarse positional information far: its range hardly matters "
              "across the stripes, and along them a long range imposes the wrong sign one stripe out",
     "rule": "HOLDS if for li4 |diff6 - diff1.5| on the sheet is <= 0.03 across the stripes (perp), while along them "
             "(par) diff1.5 - diff6 is >= 0.08 on the sheet and diff6's registration at distance 4 is <= 0.50, "
             "else FAILS",
     "inputs": "P22c: +0.010; +0.157; 0.106"},
    {"id": "G6", "kind": "a diffusing signal widens the boundary's reach across stripes",
     "claim": "Across the stripes, a diffusing boundary signal registers real growth better than the boundary's own "
              "reading",
     "rule": "HOLDS if li4 perp diff6/100 - grow/100 is >= 0.02 on the sheet and >= 0.04 on the far side, else FAILS",
     "inputs": "P22c: +0.040; +0.085"},
    {"id": "G7", "kind": "no boundary, no registration",
     "claim": "Without the boundary's record, growth registers nothing",
     "rule": "HOLDS if none/100 gives sheet <= 0.55 in both geometries on both bodies, else FAILS",
     "inputs": "P22c: 0.454-0.500"},
    {"id": "G8", "kind": "the margin's roughness is the cause",
     "claim": "Across the stripes, division with a flat margin at the same speed registers like the prescribed front: "
              "the uneven margin, not division or inheritance, costs real growth its reach",
     "rule": "HOLDS if li4 perp smooth/100's far side is >= grow/100's + 0.10 and >= front/100's - 0.02, and its intact "
             "share >= 0.90, else FAILS",
     "inputs": "P22c: +0.176; 0.000; 1.000"},
    {"id": "G9", "kind": "along the stripes, inheritance is the cost",
     "claim": "Where new stripes are added parallel to the margin, daughters copying their parents lose registration, "
              "and a flat margin does not help",
     "rule": "HOLDS if along the stripes (par) li4's nb/100 - grow/100 is >= 0.03 on the sheet and smooth/100 - "
             "front/100 is <= -0.03 on the sheet, else FAILS",
     "inputs": "P22c: +0.058; -0.068"},
    {"id": "R1", "kind": "memory regrows with inheriting cells",
     "claim": "A self-taught record refilled by inheriting divisions recovers its memory of the patch; killed in place "
              "or refilled by newborn cells, it does not",
     "rule": "HOLDS if under record+parity, for S4 and F0, both bodies, both rates and both regrowth speeds, regrow's "
             "r_patch is >= reset's + 0.15 and regrow-nb's r_patch is <= 0.55, else FAILS",
     "inputs": "P22c: S4 +0.205 to +0.238, F0 +0.426 to +0.447; regrow-nb 0.473-0.510"},
    {"id": "R2", "kind": "coarse memory regrows better than fine",
     "claim": "Memory regrows more faithfully for coarse domains than for fine stripes, since a daughter copies its "
              "neighbour across any wall within its reach",
     "rule": "HOLDS if under record+parity regrow's r_patch on F0 - S4 is >= 0.10, both bodies, rates and speeds, "
             "else FAILS",
     "inputs": "P22c: +0.181 to +0.211"},
    {"id": "R3", "kind": "inheritance hurts where the body makes the pattern",
     "claim": "Where the body makes the pattern, newborn daughters taught by the body repair the patch better than "
              "daughters inheriting their neighbours' memory",
     "rule": "HOLDS if for li4 on S4 under body teaching, both rates and both regrowth speeds, regrow's patch is <= "
             "regrow-nb's - 0.03 and <= reset's - 0.03, else FAILS",
     "inputs": "P22c: regrow - regrow-nb -0.120 to -0.072; regrow - reset -0.108 to -0.067"},
    {"id": "R4", "kind": "inheritance helps where the body does not make the pattern",
     "claim": "Where the body does not make the pattern, inheriting daughters repair the patch far better than newborn "
              "daughters taught by the body",
     "rule": "HOLDS if for li4 on F0 under body teaching, both rates and both regrowth speeds, regrow's patch is >= "
             "regrow-nb's + 0.20, else FAILS",
     "inputs": "P22c: +0.343 to +0.424"},
]


def gv(L, body, geo, arm, e):
    """Panel G: the mean at t = 4,000 (snapshot endpoints) or the end value (function endpoints)."""
    x = L["G"][UNIT_G][body][geo][arm][e]
    return x[-1][0] if isinstance(x[0], list) else x[0]


def rv(L, unit, body, cond, e):
    return L["R"][unit][body][cond][e][-1][0]


def score(L):
    S = {}
    s, f = gv(L, "li4", "perp", "front/100", "sign"), gv(L, "li4", "perp", "front/100", "far")
    S["G1"] = {"verdict": "HOLDS" if s >= 0.97 and f >= 0.95 else "FAILS", "sheet": s, "far": f}

    gf, ff, gi = gv(L, "li4", "perp", "grow/100", "far"), f, gv(L, "li4", "perp", "grow/100", "intact")
    S["G2"] = {"verdict": "HOLDS" if gf - ff <= -0.10 and gi <= 0.50 else "FAILS", "grow_minus_front_far": round(gf - ff, 4),
               "grow_intact": gi}

    d = gv(L, "li4", "perp", "nb/100", "sign") - gv(L, "li4", "perp", "grow/100", "sign")
    S["G3"] = {"verdict": "HOLDS" if abs(d) <= 0.03 else "FAILS", "nb_minus_grow_sheet": round(d, 4)}

    g2 = gv(L, "li4", "perp", "grow/200", "far")
    a, b = g2 - gf, g2 - gv(L, "li4", "perp", "front/200", "far")
    S["G4"] = {"verdict": "HOLDS" if a >= 0.03 and b <= -0.05 else "FAILS", "grow200_minus_grow100_far": round(a, 4),
               "grow200_minus_front200_far": round(b, 4)}

    pp = gv(L, "li4", "perp", "diff6/100", "sign") - gv(L, "li4", "perp", "diff1.5/100", "sign")
    pa = gv(L, "li4", "par", "diff1.5/100", "sign") - gv(L, "li4", "par", "diff6/100", "sign")
    d4 = L["G"][UNIT_G]["li4"]["par"]["diff6/100"]["profile"][4]
    S["G5"] = {"verdict": "HOLDS" if abs(pp) <= 0.03 and pa >= 0.08 and d4 <= 0.50 else "FAILS",
               "perp_diff6_minus_diff1.5": round(pp, 4), "par_diff1.5_minus_diff6": round(pa, 4), "par_diff6_at_4": d4}

    a = gv(L, "li4", "perp", "diff6/100", "sign") - gv(L, "li4", "perp", "grow/100", "sign")
    b = gv(L, "li4", "perp", "diff6/100", "far") - gf
    S["G6"] = {"verdict": "HOLDS" if a >= 0.02 and b >= 0.04 else "FAILS", "diff6_minus_grow_sheet": round(a, 4),
               "diff6_minus_grow_far": round(b, 4)}

    v = {f"{b_}/{g}": gv(L, b_, g, "none/100", "sign") for b_ in D.BODIES for g in D.GEOMS}
    S["G7"] = {"verdict": "HOLDS" if max(v.values()) <= 0.55 else "FAILS", "none_sheet": v}

    sf = gv(L, "li4", "perp", "smooth/100", "far")
    a, b, c = sf - gf, sf - ff, gv(L, "li4", "perp", "smooth/100", "intact")
    S["G8"] = {"verdict": "HOLDS" if a >= 0.10 and b >= -0.02 and c >= 0.90 else "FAILS",
               "smooth_minus_grow_far": round(a, 4), "smooth_minus_front_far": round(b, 4), "smooth_intact": c}

    a = gv(L, "li4", "par", "nb/100", "sign") - gv(L, "li4", "par", "grow/100", "sign")
    b = gv(L, "li4", "par", "smooth/100", "sign") - gv(L, "li4", "par", "front/100", "sign")
    S["G9"] = {"verdict": "HOLDS" if a >= 0.03 and b <= -0.03 else "FAILS", "par_nb_minus_grow_sheet": round(a, 4),
               "par_smooth_minus_front_sheet": round(b, 4)}

    ok, v = True, {}
    for u in D.UNITS["R"]:
        for b_ in D.BODIES:
            for rate in D.RATES:
                pre = f"{rate:g}/record+parity/"
                reset = rv(L, u, b_, pre + "reset", "r_patch")
                for sp in SPEEDS:
                    rg, nb = rv(L, u, b_, pre + f"regrow@{sp}", "r_patch"), rv(L, u, b_, pre + f"regrow-nb@{sp}", "r_patch")
                    v[f"{u}/{b_}/{rate:g}/{sp}"] = {"regrow_minus_reset": round(rg - reset, 4), "regrow_nb": nb}
                    ok &= rg - reset >= 0.15 and nb <= 0.55
    S["R1"] = {"verdict": "HOLDS" if ok else "FAILS", "r_patch": v}

    v = {f"{b_}/{rate:g}/{sp}": round(rv(L, "F0_t0", b_, f"{rate:g}/record+parity/regrow@{sp}", "r_patch")
                                      - rv(L, "S4_t0", b_, f"{rate:g}/record+parity/regrow@{sp}", "r_patch"), 4)
         for b_ in D.BODIES for rate in D.RATES for sp in SPEEDS}
    S["R2"] = {"verdict": "HOLDS" if min(v.values()) >= 0.10 else "FAILS", "F0_minus_S4": v}

    ok, v = True, {}
    for rate in D.RATES:
        pre = f"{rate:g}/body/"
        reset = rv(L, "S4_t0", "li4", pre + "reset", "patch")
        for sp in SPEEDS:
            rg, nb = rv(L, "S4_t0", "li4", pre + f"regrow@{sp}", "patch"), rv(L, "S4_t0", "li4", pre + f"regrow-nb@{sp}", "patch")
            v[f"{rate:g}/{sp}"] = {"regrow_minus_nb": round(rg - nb, 4), "regrow_minus_reset": round(rg - reset, 4)}
            ok &= rg - nb <= -0.03 and rg - reset <= -0.03
    S["R3"] = {"verdict": "HOLDS" if ok else "FAILS", "S4_li4_body_patch": v}

    v = {f"{rate:g}/{sp}": round(rv(L, "F0_t0", "li4", f"{rate:g}/body/regrow@{sp}", "patch")
                                 - rv(L, "F0_t0", "li4", f"{rate:g}/body/regrow-nb@{sp}", "patch"), 4)
         for rate in D.RATES for sp in SPEEDS}
    S["R4"] = {"verdict": "HOLDS" if min(v.values()) >= 0.20 else "FAILS", "F0_li4_body_regrow_minus_nb": v}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
