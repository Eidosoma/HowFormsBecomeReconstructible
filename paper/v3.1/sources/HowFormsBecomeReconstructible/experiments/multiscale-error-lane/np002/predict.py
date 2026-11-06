"""NP002's registered statements and their scoring, written before any development outcome (DRAFT until the freeze).

python -m np002.predict   (writes np002/frozen/predictions.json)

Statements are drafted from engineering probe P32 (32 cases on blocks 900520-900523 under tag mse-p32) under BE002's
rule; probes/p32b_np002_margins.py prints every part, its items' SDs over P32's four blocks and the margin at these
thresholds.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from np002 import design as D  # noqa: E402


def q_body(align, align_b, unit):
    """The body's preference: (alignment with the record's pattern - alignment with the body's initial one) /
    (1 - a0); +1 at the record's pattern, -1 at the body's initial one (a0: the two templates' sign agreement)."""
    return (align - align_b) / (1.0 - D.A0[unit])


def q_rec(r_abs, r_abs_b, unit):
    """The record's relational preference: (|2 r_align - 1| - |2 r_align_b - 1|) / (1 - |2 a0 - 1|), the case means of
    the absolute agreements; +1 when the record holds the history's relations (in either global sign), -1 when it
    holds the body's initial pattern's."""
    return (r_abs - r_abs_b) / (1.0 - abs(2.0 * D.A0[unit] - 1.0))


def q_bond(bond_err, bond_b, unit):
    """The record's bonds' preference: (bond_b - bond_err) / (1 - b0), from the shares of bonds that differ from the body's
    initial relations and from the history's; +1 at the history's relations, -1 at the body's (reported, not registered;
    b0 is the two patterns' bond agreement, design.B0, checked in Q7)."""
    return (bond_b - bond_err) / (1.0 - D.B0[unit])


def s1(L, b, u, c, e="align", t=-1):
    return L[b][u]["s1"][c][e][t][0]


def s2(L, b, u, B, c, e="align"):
    return L[b][u]["s2"][B][c][e][-1][0]


def qb(L, b, u, c, t=-1):
    return q_body(s1(L, b, u, c, "align", t), s1(L, b, u, c, "align_b", t), u)


def qr(L, b, u, c, t=-1):
    return q_rec(s1(L, b, u, c, "r_abs", t), s1(L, b, u, c, "r_abs_b", t), u)


def s2q(L, b, u, B, c):
    """A successor's preference reading stage-1 body b's record c (spacing conflicts only)."""
    return q_body(s2(L, b, u, B, c, "align"), s2(L, b, u, B, c, "align_b"), u)


SHARP, PERM = ("li2", "li4"), ("dw", "li16")            # the period-8 bodies; the bodies that drift on period-8 stripes
HELD = (("li2", "C48"), ("li4", "C48"), ("dw", "C84"), ("li16", "C84"))   # the record's period against a held one
EASY = (("li2", "C84"), ("li4", "C84"), ("dw", "C48"), ("li16", "C48"))   # the other spacing conflicts
G_HI = {"li2": 0.02, "li4": 0.02, "dw": 0.05, "li16": 0.05}  # the protected record still switches every body here (P32)
ic = lambda g: "intact" if g == D.GAIN else f"intact@{g:g}"
bc = lambda g: "body" if g == D.GAIN else f"body@{g:g}"

THR = {"R1": {"sharp": 0.5, "perm": 0.25},
       "R2": {"sharp": -0.5, "perm": -0.25},
       "R3": {"wins": 0.5, "sharp": -0.5, "perm": -0.25},
       "R4": {"sharp": 1.0, "perm": 0.25},
       "R5": {"kept": 0.5, "lost": 0.0},
       "S1": {"stays": -0.5},
       "S2": {"exact": 0.95, "takes": 0.5},
       "S3": {"split": 0.5, "wins": 0.5, "harder": 0.3},
       "S4": {"lost": 0.5, "won": 0.5}}


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


T = THR
PH = D.PHASE
PARTS = [
    part("R1", "R1 li2, li4: q under intact@0.02", [(b, u) for b in SHARP for u in PH], T["R1"]["sharp"], "ge", False,
         lambda L, b, u: qb(L, b, u, ic(G_HI[b]))),
    part("R1", "R1 dw, li16: q under intact@0.05", [(b, u) for b in PERM for u in PH], T["R1"]["perm"], "ge", False,
         lambda L, b, u: qb(L, b, u, ic(G_HI[b]))),
    part("R2", "R2 li2, li4: q under intact@0.005", [(b, u) for b in SHARP for u in PH], T["R2"]["sharp"], "le", False,
         lambda L, b, u: qb(L, b, u, ic(0.005))),
    part("R2", "R2 dw, li16: q under intact@0.005", [(b, u) for b in PERM for u in PH], T["R2"]["perm"], "le", False,
         lambda L, b, u: qb(L, b, u, ic(0.005))),
    part("R3", "R3 every body: q under body (gain 0.2)", [(b, u) for b in D.BODIES for u in PH], T["R3"]["wins"], "ge",
         False, lambda L, b, u: qb(L, b, u, bc(D.GAIN))),
    part("R3", "R3 li2, li4: q under body@0.02", [(b, u) for b in SHARP for u in PH], T["R3"]["sharp"], "le", False,
         lambda L, b, u: qb(L, b, u, bc(0.02))),
    part("R3", "R3 dw, li16: q under body@0.02", [(b, u) for b in PERM for u in PH], T["R3"]["perm"], "le", False,
         lambda L, b, u: qb(L, b, u, bc(0.02))),
    part("R4", "R4 li2, li4: q(intact@0.02) - q(body@0.02)", [(b, u) for b in SHARP for u in PH], T["R4"]["sharp"], "ge",
         False, lambda L, b, u: qb(L, b, u, ic(G_HI[b])) - qb(L, b, u, bc(G_HI[b]))),
    part("R4", "R4 dw, li16: q(intact@0.05) - q(body@0.05)", [(b, u) for b in PERM for u in PH], T["R4"]["perm"], "ge",
         False, lambda L, b, u: qb(L, b, u, ic(G_HI[b])) - qb(L, b, u, bc(G_HI[b]))),
    part("R5", "R5 every body: the record's q_rel under body (gain 0.2)", [(b, u) for b in D.BODIES for u in PH],
         T["R5"]["kept"], "ge", False, lambda L, b, u: qr(L, b, u, bc(D.GAIN))),
    part("R5", "R5 every body: the record's q_rel under body@0.02", [(b, u) for b in D.BODIES for u in PH],
         T["R5"]["lost"], "le", False, lambda L, b, u: qr(L, b, u, bc(0.02))),
    part("S1", "S1 alone: q, a period held against the record's", HELD, T["S1"]["stays"], "le", False,
         lambda L, b, u: qb(L, b, u, "alone")),
    part("S2", "S2 intact: align, every body, C84 and C48", [(b, u) for b in D.BODIES for u in D.SPACING],
         T["S2"]["exact"], "ge", False, lambda L, b, u: s1(L, b, u, "intact")),
    part("S2", "S2 newborns of the intact C84 and C48 records: align", [("dw", u, B) for u in D.SPACING for B in D.SUCC_BODIES],
         T["S2"]["exact"], "ge", False, lambda L, b, u, B: s2(L, b, u, B, "intact")),
    part("S2", "S2 record1: q, every body, C84 and C48", [(b, u) for b in D.BODIES for u in D.SPACING],
         T["S2"]["takes"], "ge", False, lambda L, b, u: qb(L, b, u, "record1")),
    part("S3", "S3 body (gain 0.2): q, a period held against the record's", HELD, T["S3"]["split"], "le", False,
         lambda L, b, u: qb(L, b, u, "body")),
    part("S3", "S3 body (gain 0.2): q, the other spacing conflicts", EASY, T["S3"]["wins"], "ge", False,
         lambda L, b, u: qb(L, b, u, "body")),
    part("S3", "S3 body (gain 0.2): phase-conflict q (mean of C4s1-C4s3) - spacing q, held", HELD, T["S3"]["harder"], "ge",
         False, lambda L, b, u: sum(qb(L, b, v, "body") for v in PH) / 3 - qb(L, b, u, "body")),
    part("S4", "S4 newborns of the held conflicts' body records: q", [(b, u, B) for b, u in HELD for B in D.SUCC_BODIES],
         T["S4"]["lost"], "le", False, lambda L, b, u, B: s2q(L, b, u, B, "body")),
    part("S4", "S4 newborns of the other spacing conflicts' body records: q", [(b, u, B) for b, u in EASY for B in D.SUCC_BODIES],
         T["S4"]["won"], "ge", False, lambda L, b, u, B: s2q(L, b, u, B, "body")),
]

CLAIM = {
    "R1": ("a protected record wins the phase race down to a low read gain",
           "Read at gain 0.02 (li2, li4) or 0.05 (dw, li16), a record the body cannot write still moves every body nearer "
           "the record's phase than its own in every phase conflict",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@0.02' is >= {sharp} for li2 and li4 "
           "and under 'intact@0.05' is >= {perm} for dw and li16, else FAILS"),
    "R2": ("below it, the body keeps its own phase",
           "Read at gain 0.005, the same protected record leaves every body nearer its own initial phase",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@0.005' is <= {sharp} for li2 and li4 "
           "and <= {perm} for dw and li16, else FAILS"),
    "R3": ("a record relearned from the body wins the race at gain 0.2 and loses it at 0.02",
           "With its bonds relearned from the body under bond noise 1e-2, the record moves every body to its phase at "
           "gain 0.2 (NP001's N8), and at gain 0.02 every body stays nearer its own initial phase",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's q under 'body' is >= {wins}, and under 'body@0.02' "
           "is <= {sharp} for li2 and li4 and <= {perm} for dw and li16, else FAILS"),
    "R4": ("relearning from the body moves the turn above the protected record's",
           "At the gain where the protected record still switches every body (0.02 for li2 and li4, 0.05 for dw and "
           "li16), the record relearned from the body moves the body's phase preference less, paired within each case",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 the body's q under 'intact@g' exceeds its q under 'body@g' "
           "by >= {sharp} for li2 and li4 (g = 0.02) and by >= {perm} for dw and li16 (g = 0.05), else FAILS"),
    "R5": ("the record that loses the race loses its history",
           "A record relearned from the body holds the history's relations (in either sign) while it wins the race (gain "
           "0.2), and holds the body's initial relations more than the history's once it has lost it (gain 0.02)",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's record q_rel under 'body' is >= {kept} and under "
           "'body@0.02' is <= {lost}, else FAILS"),
    "S1": ("with no record read, a body keeps its present period",
           "Read nothing, li2 and li4 keep their period-8 stripes against a period-16 record (C48) and dw and li16 keep "
           "their period-16 stripes against a period-8 record (C84)",
           "HOLDS if at t = 4,000 the body's q under 'alone' is <= {stays} for li2 and li4 in C48 and for dw and li16 in "
           "C84, else FAILS"),
    "S2": ("a record the body never writes wins every spacing conflict, and newborns take its period",
           "Every body reading an intact record of the other period takes it exactly, a record relearned from itself with "
           "parity moves every body to its period, and a newborn of every kind reading the intact record takes its period "
           "exactly",
           "HOLDS if the align under 'intact' at t = 4,000 is >= {exact} for every body in C84 and C48, every newborn's "
           "align reading the 'intact' C84 and C48 records at t = 2,000 is >= {exact}, and the body's q under 'record1' "
           "at t = 4,000 is >= {takes} for every body in C84 and C48, else FAILS"),
    "S3": ("relearned from the body, the record wins two kinds of spacing conflict and not the other two",
           "At gain 0.2 with bonds relearned from the body, the record does not move li2 or li4 off period 8 (C48), nor dw "
           "or li16 off period 16 (C84), nearer its own period than q 0.5, and it does so less than in the phase "
           "conflicts; it moves li2 and li4 to period 8 (C84) and dw and li16 to period 16 (C48)",
           "HOLDS if at t = 4,000 the body's q under 'body' is <= {split} for li2 and li4 in C48 and dw and li16 in C84, "
           ">= {wins} for li2 and li4 in C84 and dw and li16 in C48, and each of the first four is below the same body's "
           "mean q under 'body' over C4s1-C4s3 by >= {harder}, else FAILS"),
    "S4": ("newborns inherit what the race left in the record",
           "Newborns of every kind reading a spacing conflict's record relearned from the body (gain 0.2, 1e-2) lean to the "
           "record's period less than q 0.5 where the record did not win (li2 and li4 in C48, dw and li16 in C84), and "
           "more where it won (li2 and li4 in C84, dw and li16 in C48)",
           "HOLDS if at t = 2,000 every successor's q reading the 'body' record is <= {lost} for li2's and li4's C48 and "
           "dw's and li16's C84 records and >= {won} for li2's and li4's C84 and dw's and li16's C48 records, else FAILS"),
}
STATEMENTS = [{"id": k, "title": v[0], "words": v[1], "rule": v[2].format(**THR[k])} for k, v in CLAIM.items()]


def passes(x, threshold, sense):
    return {"ge": x >= threshold, "le": x <= threshold, "abs": abs(x) <= threshold}[sense]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def score(L):
    S = {}
    for s in STATEMENTS:
        out, ok = {}, True
        for p in (q for q in PARTS if q["stmt"] == s["id"]):
            vals = {"/".join(map(str, it)): p["value"](L, *it) for it in p["items"]}
            if p["pooled"]:
                x = mean(vals.values())
                good = passes(x, p["threshold"], p["sense"])
                out[p["name"]] = {"pooled": x, "pass": good, "items": vals}
            else:
                good = all(passes(x, p["threshold"], p["sense"]) for x in vals.values())
                out[p["name"]] = {"pass": good, "items": vals}
            ok &= good
        S[s["id"]] = {"verdict": "HOLDS" if ok else "FAILS", "parts": out}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": THR,
                               "parts": [{k: v for k, v in p.items() if k != "value"} for p in PARTS],
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
