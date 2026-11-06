"""NP002's tables from the reader's outputs: python -m np002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from np002 import design as D  # noqa: E402
from np002.predict import q_body, q_bond, q_rec  # noqa: E402

FROZEN = LANE / "np002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "np002")
    ap.add_argument("--predictions", type=Path, default=FROZEN / "predictions.json")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head, L[b] = s, s["levels"]
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads(a.predictions.read_text())["statements"]
    conds, br = head["conds"], head["branches2"]
    v1 = lambda b, u, c, e: L[b][u]["s1"][c][e][-1][0]
    lines = [f"# NP002 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). LR002's tissue (DL001's bodies "
             "reading a record of relations, no coarse code, a 32 x 32 sheet), quiet tissue. Units: the phase conflicts "
             "C4s1-C4s3 (the body acquired at S4's phase 0, the record and history at phase K) and the spacing conflicts "
             "C84 (the body from S8's acquisition, period 16; the record from S4's, period 8) and C48 (the reverse). "
             "Stage 1 (4,000 updates): NP001's conditions at read gain 0.2 (alone reads nothing) and the race pairs "
             "intact@g (record protected) and body@g (bond noise 1e-2, relearned from the body) at lower gains g. "
             "q: the body's preference (align - align_b) / (1 - a0), +1 at the record's pattern and -1 at the body's "
             "initial one; q_rel: the record's relational preference (|2 r_align - 1| - |2 r_align_b - 1|) / "
             "(1 - |2 a0 - 1|) from case means, the same up to the record's global sign. Stage 2 (spacing conflicts "
             "only, 2,000 updates): newborns of each kind reading one stage-1 record (protected) or nothing ('none').", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict'] if x['id'] in S else '—'} | {x['words']} |" for x in stm]
    gains = [("0.2", "intact", "body")] + [(f"{g:g}", f"intact@{g:g}", f"body@{g:g}") for g in D.RACE_GAINS]
    for what, fn in (("q (the body)", lambda b, u, c: q_body(v1(b, u, c, "align"), v1(b, u, c, "align_b"), u)),
                     ("q_rel (the record)", lambda b, u, c: q_rec(v1(b, u, c, "r_abs"), v1(b, u, c, "r_abs_b"), u)),
                     ("q_bond (the record's bonds; reported)", lambda b, u, c: q_bond(v1(b, u, c, "bond_err"), v1(b, u, c, "bond_b"), u))):
        lines += ["", f"## Stage 1 at t = {D.READS[-1]:,}: {what} by read gain; rows body and unit", "",
                  "| Body | Unit | alone | " + " | ".join(f"intact {g} | body {g}" for g, _, _ in gains) + " |",
                  "|---|---|---|" + "---|---|" * len(gains)]
        for b in D.BODIES:
            for u in D.UNITS:
                lines.append(f"| {b} | {u} | {f(fn(b, u, 'alone'))} | " +
                             " | ".join(f"{f(fn(b, u, ci))} | {f(fn(b, u, cb))}" for _, ci, cb in gains) + " |")
    for e in ("align", "r_align", "shape", "spacing", "align_b", "r_align_b"):
        lines += ["", f"## Stage 1 at t = {D.READS[-1]:,}: {e}; rows body and unit, columns condition", "",
                  "| Body | Unit | " + " | ".join(conds) + " |", "|---|---|" + "---|" * len(conds)]
        for b in D.BODIES:
            for u in D.UNITS:
                lines.append(f"| {b} | {u} | " + " | ".join(f(v1(b, u, c, e), 1 if e == "spacing" else 3) for c in conds) + " |")
    for e in ("align", "align_b", "shape", "spacing"):
        lines += ["", f"## Stage 2 at t = {D.READS2[-1]:,} (spacing conflicts): {e}; rows the body that kept the record, "
                  "unit and successor; columns the record read", "",
                  "| Kept by | Unit | Successor | " + " | ".join(br) + " |", "|---|---|---|" + "---|" * len(br)]
        for b in D.BODIES:
            for u in D.SPACING:
                for B in D.SUCC_BODIES:
                    n = L[b][u]["s2"][B]
                    lines.append(f"| {b} | {u} | {B} | " + " | ".join(f(n[c][e][-1][0], 1 if e == "spacing" else 3) for c in br) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
