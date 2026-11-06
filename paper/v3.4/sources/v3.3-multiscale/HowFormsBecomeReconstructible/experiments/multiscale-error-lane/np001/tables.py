"""NP001's tables from the reader's outputs: python -m np001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from np001 import design as D  # noqa: E402

FROZEN = LANE / "np001" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "np001")
    ap.add_argument("--predictions", type=Path, default=FROZEN / "predictions.json")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head, L[b] = s, s["levels"]
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads(a.predictions.read_text())["statements"]
    conds, br = head["conds"], head["branches2"]
    lines = [f"# NP001 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). LR002's tissue (DL001's bodies "
             "reading a record of relations at gain 0.2, no coarse code, a 32 x 32 sheet), quiet tissue. Patterns: S4 "
             "(period-8 stripes, DL002's), S4s1-S4s3 (S4 shifted 1-3 sites across its stripes), S8 (period 16), F0 (two "
             "domains). Stage 1 (4,000 updates from the acquired state): alone (no record read), intact (no bond noise), "
             "body1 / body / body3 (bond noise 1e-3 / 1e-2 / 3e-2, bonds relearned from the body), record1 (1e-3, "
             "relearned from the record, plus parity). Stage 2 (2,000 updates): a newborn body of each kind reading one "
             "stage-1 record, protected, or nothing ('none'). Phase conflicts C4sK: the body acquired at S4's phase 0, "
             "the record at phase K. align: the body's sign agreement with the record's history (the acquired template; "
             "phase K in a conflict) at its registration; align_b: with the body's initial pattern (phase 0 in a "
             "conflict, else the same); r_align, r_align_b: the record's; shape: the best agreement over cyclic shifts; "
             "spacing: the body's power-weighted wavelength.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['words']} |" for x in stm]
    for e in ("align", "r_align", "shape", "spacing", "align_b", "r_align_b"):
        units = D.CONFLICTS if e.endswith("_b") else D.UNITS
        lines += ["", f"## Stage 1 at t = {D.READS[-1]:,}: {e}; rows body and pattern, columns condition", "",
                  "| Body | Pattern | " + " | ".join(conds) + " |", "|---|---|" + "---|" * len(conds)]
        for b in D.BODIES:
            for u in units:
                n = L[b][u]["s1"]
                lines.append(f"| {b} | {u} | " + " | ".join(f(n[c][e][-1][0], 1 if e == "spacing" else 3) for c in conds) + " |")
    for e in ("align", "shape", "align_b"):
        units = D.CONFLICTS if e.endswith("_b") else D.UNITS
        lines += ["", f"## Stage 2 at t = {D.READS2[-1]:,}: {e}; rows the body that kept the record, pattern and "
                  "successor; columns the record read", "",
                  "| Kept by | Pattern | Successor | " + " | ".join(br) + " |", "|---|---|---|" + "---|" * len(br)]
        for b in D.BODIES:
            for u in units:
                for B in D.SUCC_BODIES:
                    n = L[b][u]["s2"][B]
                    lines.append(f"| {b} | {u} | {B} | " + " | ".join(f(n[c][e][-1][0]) for c in br) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
