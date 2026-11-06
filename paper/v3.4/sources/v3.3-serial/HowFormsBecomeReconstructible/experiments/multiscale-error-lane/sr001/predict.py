"""SR001's registered statements and their scoring, written before any development outcome.

python -m sr001.predict   (writes sr001/frozen/predictions.json)

Thresholds are set from engineering probe P39 (tag mse-p39, blocks 900936-900939, disclosed in REGISTRATION_SR001.md)
under BE002's rule, with the lead's block SD (BE009): SD_block = max(the SD over P39's four blocks of the part's block
value, the SD over P39's 32 cases of the part's per-case value / sqrt 8); a part sits >= 3 sqrt(1/4 + 1/16) = 1.68
SD_block inside its threshold, and passes in each half of P39. probes/p39b_sr001_margins.py prints every part, both SDs
and the margin. Where both SDs are 0 the bound is derived from the construction, not taken from the probe.

A part's value: for each case, the mean over the part's (body, unit) items of an endpoint (sr001.analyze: a, q,
spacing; recipients rec_a, rec_q); the block value is the mean over the block's 8 cases; the part is scored on the mean
over blocks (16 development blocks), unrounded. A statement HOLDS when every one of its parts passes. G16 is the last
renewal; every endpoint is inversion-invariant.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from sr001 import analyze as Z  # noqa: E402
from sr001 import design as D  # noqa: E402

G = D.GENS
ALL = tuple(D.tasks())
NONNAT = (("li4", "S8"), ("li4", "F0"), ("li16n", "S4"), ("li16n", "S4s2"))   # patterns the lineage's body would not make
NATIVE = (("li4", "S4"), ("li4", "S4s2"), ("li16n", "S8"))                    # the body's own period, at the record's phase
PERM = tuple(("dw", u) for u in D.UNITS)                                      # the permissive body
THR = {"R1": {"protected": 0.95},
       "R2": {"exposed": 0.55},
       "R3": {"keeps": 0.6, "erodes": 0.15, "loses": 0.55},
       "R4": {"rewritten": 0.6},
       "R5": {"phase": 0.75},
       "R6": {"vote_over_body": 0.4, "vote_lost": 0.6},
       "R7": {"compounds": 0.1},
       "R8": {"permissive": 0.9},
       "R9": {"reconstructs": 0.85},
       "R10": {"nothing_left": 0.25},
       "R11": {"no_read": 0.1},
       "R12": {"better_keeper": 0.05}}


def f_q(route, gen=G, x="r"):
    return lambda d, b, u: Z.q(d, b, u, route, gen, x)


def f_a(route, gen=G, x="r"):
    return lambda d, b, u: Z.a(d, b, u, route, gen, x)


def f_rgain(RB, branch):
    return lambda d, b, u: Z.rec_q(d, b, u, RB, branch) - Z.rec_q(d, b, u, RB, "none")


def part(stmt, name, items, threshold, sense, f):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "f": f}


T = THR
PARTS = [
    part("R1", "R1 q_r(protected, G16), every lineage", ALL, T["R1"]["protected"], "ge", f_q("protected")),
    part("R2", "R2 a_r(exposed@0.001, G16), every lineage", ALL, T["R2"]["exposed"], "le", f_a("exposed@0.001")),
    part("R3", "R3 q_r(parity@0.001, G16), every lineage", ALL, T["R3"]["keeps"], "ge", f_q("parity@0.001")),
    part("R3", "R3 q_r(parity@0.001, G1) - q_r(parity@0.001, G16), every lineage", ALL, T["R3"]["erodes"], "ge",
         lambda d, b, u: Z.q(d, b, u, "parity@0.001", 1) - Z.q(d, b, u, "parity@0.001", G)),
    part("R3", "R3 a_r(parity@0.003, G16), every lineage", ALL, T["R3"]["loses"], "le", f_a("parity@0.003")),
    part("R4", "R4 a_r(body@0.003, G16), non-native", NONNAT, T["R4"]["rewritten"], "le", f_a("body@0.003")),
    part("R5", "R5 q_r(body@0.01, G16), native", NATIVE, T["R5"]["phase"], "ge", f_q("body@0.01")),
    part("R6", "R6 q_r(vote@0.001) - q_r(body@0.001) at G16, non-native", NONNAT, T["R6"]["vote_over_body"], "ge",
         lambda d, b, u: Z.q(d, b, u, "vote@0.001", G) - Z.q(d, b, u, "body@0.001", G)),
    part("R6", "R6 a_r(vote@0.01, G16), non-native", NONNAT, T["R6"]["vote_lost"], "le", f_a("vote@0.01")),
    part("R7", "R7 a_r(body@0.001, G1) - a_r(body@0.001, G16), non-native", NONNAT, T["R7"]["compounds"], "ge",
         lambda d, b, u: Z.a(d, b, u, "body@0.001", 1) - Z.a(d, b, u, "body@0.001", G)),
    part("R8", "R8 q_r(body@0.003, G16), permissive dw", PERM, T["R8"]["permissive"], "ge", f_q("body@0.003")),
    *[part("R9", f"R9 rec_q({RB} reading protected) - control, every lineage", ALL, T["R9"]["reconstructs"], "ge",
           f_rgain(RB, "protected")) for RB in D.RECIPIENTS],
    *[part("R10", f"R10 rec_q({RB} reading body@0.003) - control, non-native", NONNAT, T["R10"]["nothing_left"], "le",
           f_rgain(RB, "body@0.003")) for RB in D.RECIPIENTS],
    part("R11", "R11 q_r(noread, G16), every lineage", ALL, T["R11"]["no_read"], "le", f_q("noread")),
    part("R12", "R12 q_r(body@0.01) - q_r(parity@0.001) at G16, native", NATIVE, T["R12"]["better_keeper"], "ge",
         lambda d, b, u: Z.q(d, b, u, "body@0.01", G) - Z.q(d, b, u, "parity@0.001", G)),
]
CLAIM = {
    "R1": ("a protected record keeps every history through sixteen renewals",
           "HOLDS if, pooled over every lineage, the record's history specificity q after the 16th renewal under the "
           "protected route is >= {protected}, else FAILS"),
    "R2": ("a copy exposed to the bond noise loses the pattern",
           "HOLDS if, pooled over every lineage, the exposed copy's agreement after the 16th renewal is <= {exposed}, "
           "else FAILS"),
    "R3": ("a record that keeps itself keeps part of its history at the lowest noise, losing it over generations, and "
           "none at three times that",
           "HOLDS if, pooled over every lineage, q under parity@1e-3 after the 16th renewal is >= {keeps} and has fallen "
           "by >= {erodes} since the 1st (paired within case), and the agreement under parity@3e-3 after the 16th is <= "
           "{loses}, else FAILS"),
    "R4": ("a body that would not make the pattern rewrites the record it relearns",
           "HOLDS if, pooled over the non-native lineages (li4 with S8 and F0, li16n with S4 and S4s2), the record's "
           "agreement after the 16th renewal under body@3e-3 is <= {rewritten}, else FAILS"),
    "R5": ("a body keeps the phase of its own pattern from the record",
           "HOLDS if, pooled over the native lineages (li4 with S4 and S4s2, li16n with S8), q after the 16th renewal "
           "under body@1e-2 is >= {phase}, else FAILS"),
    "R6": ("the three-copy vote outlasts the body where the body would not make the pattern, at the lowest noise only",
           "HOLDS if, pooled over the non-native lineages after the 16th renewal, q under vote@1e-3 less q under "
           "body@1e-3 is >= {vote_over_body} (paired within case) and the agreement under vote@1e-2 is <= {vote_lost}, "
           "else FAILS"),
    "R7": ("the rewrite compounds over generations",
           "HOLDS if, pooled over the non-native lineages under body@1e-3, the record's agreement after the 1st renewal "
           "less after the 16th is >= {compounds}, paired within case, else FAILS"),
    "R8": ("a permissive body keeps every history it relearns at three times the lowest noise",
           "HOLDS if, pooled over dw's lineages, q after the 16th renewal under body@3e-3 is >= {permissive}, else FAILS"),
    "R9": ("fresh bodies of every kind rebuild a protected history",
           "HOLDS if, for each recipient kind (dw, li4, li16n), pooled over every lineage, a fresh recipient reading the "
           "protected G16 record has q >= {reconstructs} above its paired no-record control at 2,000 updates, else FAILS"),
    "R10": ("a rewritten record leaves fresh bodies little to rebuild",
            "HOLDS if, for each recipient kind, pooled over the non-native lineages, a fresh recipient reading the "
            "body@3e-3 G16 record has q at most {nothing_left} above its paired no-record control, else FAILS"),
    "R11": ("without reading the record a lineage keeps no history",
            "HOLDS if, pooled over every lineage, q after the 16th renewal under noread is <= {no_read}, else FAILS"),
    "R12": ("a body that makes the pattern keeps its history better than the record keeps itself",
            "HOLDS if, pooled over the native lineages after the 16th renewal, q under body@1e-2 less q under "
            "parity@1e-3 is >= {better_keeper}, paired within case, else FAILS"),
}
STATEMENTS = [{"id": k, "kind": v[0], "rule": v[1].format(**THR[k]), "thresholds": THR[k]} for k, v in CLAIM.items()]


def passes(x, threshold, sense):
    return {"ge": x >= threshold, "le": x <= threshold, "abs": abs(x) <= threshold}[sense]


def part_cases(data, p):
    """(blocks, cases): the part's per-case value pooled over its items."""
    return Z.pooled_cases(data, p["items"], p["f"])


def score(data):
    S = {}
    for s in STATEMENTS:
        out, ok = {}, True
        for p in (q for q in PARTS if q["stmt"] == s["id"]):
            v = part_cases(data, p).mean(-1)                    # block values
            x = float(v.mean())
            good = bool(passes(x, p["threshold"], p["sense"]))
            out[p["name"]] = {"pooled": x, "blocks": [float(y) for y in v], "pass": good}
            ok &= good
        S[s["id"]] = {"verdict": "HOLDS" if ok else "FAILS", "parts": out}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": THR,
                               "parts": [{k: v for k, v in p.items() if k != "f"} for p in PARTS],
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
