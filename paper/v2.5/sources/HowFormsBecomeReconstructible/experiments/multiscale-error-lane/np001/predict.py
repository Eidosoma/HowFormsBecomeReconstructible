"""NP001's registered statements and their scoring, written before any development outcome.

python -m np001.predict   (writes np001/frozen/predictions.json)

Thresholds were set from engineering probe P31 (32 cases on blocks 900628-900631 under tag mse-p31, disclosed in
REGISTRATION_NP001.md) under BE002's rule; probes/p31b_np001_margins.py prints every part, its items' SDs over P31's four
blocks and the margin at these thresholds. SD_block = max(the item's own SD, the RMS of the SDs over the part's items);
an every-item part sits >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P31's worst item; a pooled part (the mean over its
items) uses the SD over blocks of the pooled per-block value. Scored by np001.analyze on unrounded block means over the
16 development blocks; a statement HOLDS when every one of its parts passes.

Endpoints: align (the body's agreement in sign with the acquired template at its own registration: historical
alignment), r_align (the record's), at t = 4,000 in stage 1 and t = 2,000 in stage 2. Stage 1: the body that kept the
pattern, under 'alone' (no record read), 'intact' (record read, no bond noise), 'body1' / 'body' / 'body3' (bond noise
1e-3 / 1e-2 / 3e-2, bonds relearned from the body: LR002's repair behind the 0.97) and 'record1' (bond noise 1e-3, bonds
relearned from the record, plus parity). Stage 2: a newborn body of each kind reading one stage-1 record (protected), or
reading nothing ('none'), all branches of one successor sharing birth and noise. S4x: the four phases S4, S4s1-S4s3.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from np001 import design as D  # noqa: E402

S4X = ("S4", "S4s1", "S4s2", "S4s3")
OFF = ("S8", "F0")                       # the acquired patterns that differ from the imposing bodies' preference
PERM = ("dw", "li16")                    # the permissive bodies
IMP = ("li2", "li4")                     # the imposing bodies
THR = {"N1": {"breaks": 0.70, "holds": 0.95},
       "N2": {"kept": 0.95, "same": 0.02},
       "N3": {"lost": 0.70, "kept": 0.95},
       "N4": {"kept": 0.97, "moved": 0.20},
       "N5": {"recovered": 0.95, "chance": 0.10, "taught": 0.85},
       "N6": {"lost": 0.70, "recovered": 0.95, "perm": 0.90},
       "N7": {"short": 0.10, "short2": 0.05},
       "N8": {"stays": -0.5, "takes": 0.5, "kept": 0.5},
       "N9": {"recovered": 0.95, "taught": 0.5}}


def s1(L, b, u, c, e="align"):
    return L[b][u]["s1"][c][e][-1][0]


def s2(L, b, u, B, c, e="align"):
    return L[b][u]["s2"][B][c][e][-1][0]


def q1(L, b, u, c, rec=False):
    """Phase preference in a conflict C4sK: (align with the record's phase - align with the body's initial phase) / (K/4);
    +1 at the record's phase, -1 at the body's initial phase (the two templates agree on 1 - K/4 of the sheet)."""
    a, a0 = ("r_align", "r_align_b") if rec else ("align", "align_b")
    return (s1(L, b, u, c, a) - s1(L, b, u, c, a0)) / (D.shift_of(u) / 4)


def q2(L, b, u, B, c):
    return (s2(L, b, u, B, c) - s2(L, b, u, B, c, "align_b")) / (D.shift_of(u) / 4)


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


T = THR
PARTS = [
    part("N1", "N1 li2, li4 alone: align S8, F0", [(b, u) for b in IMP for u in OFF], T["N1"]["breaks"], "le", False,
         lambda L, b, u: s1(L, b, u, "alone")),
    part("N1", "N1 li2, li4 alone: align S4x", [(b, u) for b in IMP for u in S4X], T["N1"]["holds"], "ge", False,
         lambda L, b, u: s1(L, b, u, "alone")),
    part("N1", "N1 dw, li16 alone: align S8, F0", [(b, u) for b in PERM for u in OFF], T["N1"]["holds"], "ge", False,
         lambda L, b, u: s1(L, b, u, "alone")),
    part("N2", "N2 body (1e-2): r_align S4x on li2, li4, dw", [(b, u) for b in ("li2", "li4", "dw") for u in S4X],
         T["N2"]["kept"], "ge", False, lambda L, b, u: s1(L, b, u, "body", "r_align")),
    part("N2", "N2 li2, li4: align body - alone, S4x", [(b, u) for b in IMP for u in S4X], T["N2"]["same"], "abs", False,
         lambda L, b, u: s1(L, b, u, "body") - s1(L, b, u, "alone")),
    part("N3", "N3 li2, li4 body, body3: r_align S8, F0", [(b, u, c) for b in IMP for u in OFF for c in ("body", "body3")],
         T["N3"]["lost"], "le", False, lambda L, b, u, c: s1(L, b, u, c, "r_align")),
    part("N3", "N3 dw, li16 body: r_align S8, F0", [(b, u) for b in PERM for u in OFF], T["N3"]["kept"], "ge", False,
         lambda L, b, u: s1(L, b, u, "body", "r_align")),
    part("N4", "N4 intact, record1: r_align S8, F0", [("li4", u, c) for u in OFF for c in ("intact", "record1")],
         T["N4"]["kept"], "ge", False, lambda L, b, u, c: s1(L, b, u, c, "r_align")),
    part("N4", "N4 li2, li4: align intact/record1 - alone, S8, F0",
         [(b, u, c) for b in IMP for u in OFF for c in ("intact", "record1")], T["N4"]["moved"], "ge", False,
         lambda L, b, u, c: s1(L, b, u, c) - s1(L, b, u, "alone")),
    part("N5", "N5 successors of intact S4x records: align", [("dw", u, B) for u in S4X for B in D.SUCC_BODIES],
         T["N5"]["recovered"], "ge", False, lambda L, b, u, B: s2(L, b, u, B, "intact")),
    part("N5", "N5 no-record successors: align - 0.5, S4x (pooled)", [(B, u) for B in D.SUCC_BODIES for u in S4X],
         T["N5"]["chance"], "abs", True, lambda L, B, u: s2(L, "dw", u, B, "none") - 0.5),
    part("N5", "N5 successors of body-taught S4x records: align", [(b, u, B) for b in D.BODIES for u in S4X for B in D.SUCC_BODIES],
         T["N5"]["taught"], "ge", False, lambda L, b, u, B: s2(L, b, u, B, "body")),
    part("N6", "N6 successors of li2's, li4's body records: align S8, F0",
         [(b, u, B) for b in IMP for u in OFF for B in D.SUCC_BODIES], T["N6"]["lost"], "le", False,
         lambda L, b, u, B: s2(L, b, u, B, "body")),
    part("N6", "N6 dw successor of the intact/record1 records: align", [("li4", u, c) for u in OFF for c in ("intact", "record1")],
         T["N6"]["recovered"], "ge", False, lambda L, b, u, c: s2(L, b, u, "dw", c)),
    part("N6", "N6 dw successor of dw's, li16's body records: align", [(b, u) for b in PERM for u in OFF],
         T["N6"]["perm"], "ge", False, lambda L, b, u: s2(L, b, u, "dw", "body")),
    part("N7", "N7 F0 intact record: dw - li4 successor align", [("dw", "F0")], T["N7"]["short"], "ge",
         False, lambda L, b, u: s2(L, b, u, "dw", "intact") - s2(L, b, u, "li4", "intact")),
    part("N7", "N7 S8, F0 body records of dw, li16: dw - li4 successor", [(b, u) for b in PERM for u in OFF],
         T["N7"]["short"], "ge", False, lambda L, b, u: s2(L, b, u, "dw", "body") - s2(L, b, u, "li4", "body")),
    part("N7", "N7 S8, F0 body records of dw, li16: dw - li2 successor", [(b, u) for b in PERM for u in OFF],
         T["N7"]["short2"], "ge", False, lambda L, b, u: s2(L, b, u, "dw", "body") - s2(L, b, u, "li2", "body")),
    part("N8", "N8 alone: phase preference q, C4sK", [(b, u) for b in D.BODIES for u in D.CONFLICTS],
         T["N8"]["stays"], "le", False, lambda L, b, u: q1(L, b, u, "alone")),
    part("N8", "N8 intact, body: phase preference q, C4sK",
         [(b, u, c) for b in D.BODIES for u in D.CONFLICTS for c in ("intact", "body")], T["N8"]["takes"], "ge", False,
         lambda L, b, u, c: q1(L, b, u, c)),
    part("N8", "N8 body: the record's phase preference, C4sK", [(b, u) for b in D.BODIES for u in D.CONFLICTS],
         T["N8"]["kept"], "ge", False, lambda L, b, u: q1(L, b, u, "body", rec=True)),
    part("N9", "N9 successors of intact conflict records: align", [("dw", u, B) for u in D.CONFLICTS for B in D.SUCC_BODIES],
         T["N9"]["recovered"], "ge", False, lambda L, b, u, B: s2(L, b, u, B, "intact")),
    part("N9", "N9 successors of body-taught conflict records: q",
         [(b, u, B) for b in D.BODIES for u in D.CONFLICTS for B in D.SUCC_BODIES], T["N9"]["taught"], "ge", False,
         lambda L, b, u, B: q2(L, b, u, B, "body")),
]

CLAIM = {
    "N1": ("the native preferences",
           "With no record read, li2 and li4 turn period-16 stripes and two domains toward their own pattern while they "
           "hold period-8 stripes at each of four phases; dw and li16 hold period-16 stripes and two domains",
           "HOLDS if at t = 4,000 under 'alone' li2's and li4's align is <= {breaks} for S8 and for F0 and >= {holds} for "
           "each of S4, S4s1, S4s2 and S4s3, and dw's and li16's align is >= {holds} for S8 and for F0, else FAILS"),
    "N2": ("on period-8 stripes LR002's 0.97 does not separate record from body",
           "Under bond noise 1e-2 with relearning from the body, li2's, li4's and dw's records of period-8 stripes at each "
           "of four phases keep the pattern (>= 0.95), as LR002 found for li4 and dw; and li2's and li4's bodies align "
           "with the pattern as well with no record read as with that record (within 0.02)",
           "HOLDS if at t = 4,000 under 'body' li2's, li4's and dw's r_align is >= {kept} for each of S4, S4s1, S4s2 and "
           "S4s3, and li2's and li4's align under 'body' is within {same} of their align under 'alone' for each of them, "
           "else FAILS"),
    "N3": ("a record relearned from an imposing body follows the body",
           "Under bond noise 1e-2 or 3e-2 with relearning from the body, li2's and li4's records of period-16 stripes and "
           "of two domains lose their acquired pattern (<= 0.70), while dw's and li16's records of the same patterns "
           "keep it (>= 0.95 at 1e-2)",
           "HOLDS if at t = 4,000 li2's and li4's r_align under 'body' and under 'body3' is <= {lost} for S8 and for F0, "
           "and dw's and li16's r_align under 'body' is >= {kept} for S8 and for F0, else FAILS"),
    "N4": ("a record the body never writes keeps history, and pulls an imposing body toward it",
           "A record with no bond noise, or under bond noise 1e-3 relearned from itself with parity, is never written by "
           "the body (it is the same under every body); it keeps period-16 stripes and two domains (>= 0.97), and "
           "reading it keeps li2's and li4's bodies closer to the acquired pattern than each alone by at least 0.2",
           "HOLDS if at t = 4,000 the r_align under 'intact' and under 'record1' is >= {kept} for S8 and for F0, and li2's "
           "and li4's align under each of them exceeds their align under 'alone' by >= {moved} for S8 and for F0, else "
           "FAILS"),
    "N5": ("a newborn body takes the historical registration from the record",
           "A newborn body of any of the four kinds reading an intact record of period-8 stripes (the same whichever "
           "body read it) aligns with the acquired phase, each of four, at >= 0.95 by 2,000 updates; the same newborn "
           "bodies reading nothing align with it at chance (within 0.10 of 0.5 on average); and reading the record that "
           "any of the four bodies relearned from itself under bond noise 1e-2, they align with the acquired phase at "
           ">= 0.85",
           "HOLDS if at t = 2,000 the align of every successor (dw, li2, li4, li16) reading the 'intact' record is >= "
           "{recovered} for each of S4, S4s1, S4s2 and S4s3; the mean over the four successors and four phases of the "
           "no-record control's align is within {chance} of 0.5; and every successor's align reading each stage-1 body's "
           "'body' record is >= {taught} for each of the four phases, else FAILS"),
    "N6": ("what a successor inherits from an imposing body's record",
           "Newborn bodies of every kind reading li2's or li4's record of period-16 stripes or two domains relearned from "
           "that body under bond noise 1e-2 align at most 0.70 with the acquired pattern; a newborn dw reading the intact "
           "or the record-relearned record (which no body writes) aligns >= 0.95, and reading dw's or li16's "
           "body-relearned record >= 0.90",
           "HOLDS if at t = 2,000 every successor's align reading li2's and li4's 'body' records is <= {lost} for S8 and "
           "for F0, a dw successor's align reading the 'intact' and 'record1' records is >= {recovered} for S8 and for F0, "
           "and a dw successor's align reading dw's and li16's 'body' records is >= {perm} for S8 and for F0, else FAILS"),
    "N7": ("an imposing newborn body reads a foreign pattern less faithfully",
           "A newborn li4 reading the intact record of two domains aligns with it at least 0.10 less than a newborn dw "
           "reading the same record, and so it does reading dw's or li16's body-relearned record of period-16 stripes or "
           "of two domains; a newborn li2 reading those body-relearned records aligns at least 0.05 less than a newborn dw",
           "HOLDS if at t = 2,000 the dw successor's align exceeds the li4 successor's by >= {short} reading the 'intact' "
           "F0 record and reading dw's and li16's 'body' S8 and F0 records, and exceeds the li2 successor's by >= {short2} "
           "reading dw's and li16's 'body' S8 and F0 records, else FAILS"),
    "N8": ("at the same spacing, the body takes the record's phase",
           "A body acquired at one phase of period-8 stripes and handed a record of another phase (shifted 1, 2 or 3 "
           "sites): with no record read every body stays nearer its own phase, and reading the record every body moves "
           "nearer the record's phase, whether the record is intact or relearned from the body under bond noise 1e-2; "
           "and the record relearned from the body stays nearer its own phase. Nearer means a phase preference q "
           "(alignment with the record's phase less alignment with the body's initial phase, over K/4: +1 at the "
           "record's phase, -1 at the body's) beyond -0.5 or +0.5",
           "HOLDS if at t = 4,000 in C4s1, C4s2 and C4s3 every body's q under 'alone' is <= {stays}; every body's q under "
           "'intact' and under 'body' is >= {takes}; and the record's q (r_align and r_align_b) under 'body' is >= {kept} "
           "under every body, else FAILS"),
    "N9": ("a newborn body inherits the record's phase, not the body's",
           "Newborn bodies of every kind reading the record of a phase conflict take the record's phase: exactly (align "
           ">= 0.95) reading the intact record, and nearer the record's phase than the body's initial one (q >= 0.5) "
           "reading the record any body relearned from itself under bond noise 1e-2",
           "HOLDS if at t = 2,000 in C4s1, C4s2 and C4s3 every successor's align (with the record's phase) reading the "
           "'intact' record is >= {recovered}, and every successor's q reading every stage-1 body's 'body' record is >= "
           "{taught}, else FAILS"),
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
