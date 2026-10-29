"""FN001's tables from the reader's outputs: python -m fn001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from fn001 import design as D  # noqa: E402
from fn001.analyze import read_levels  # noqa: E402
from fn001.predict import STATEMENTS  # noqa: E402

NAMES = [c.name for c in D.CONDS]


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "fn001")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = read_levels(a.out)
    stm = STATEMENTS

    def lv(u, b, ep, t, c):
        return L[u][b][ep]["mean"][D.READS.index(t)][NAMES.index(c)]

    t0, t1, t2 = D.T_W1, D.T_W2, D.READS[-1]
    lines = [f"# FN001 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's strong period-8 lateral-inhibition body, each reading a relational record (no coarse code) at gain 0.2. "
             "Every bond's sign flips at rate p_b per update. Teachers (lr004.sim.relations): record+parity (LR001's two "
             "layers); body (LR002); site (LR003's whole-site gate); vote (two records and the body, LR004). A wound kills an "
             f"8 x 8 square after t = {t0:,} (W12, W12x) and after t = {t1:,} (W12 at the same place, W12x elsewhere, W2 in "
             "naive tissue): newborn body values, record values 0 (both records), every touching bond a random sign at "
             "strength 0. sign: the body's agreement with the template; patch: in the current wound; r_patch: the record's in "
             "the current wound; intact: the share of sheets whose large domains (>= 8 cells) match the template's in number "
             "for each sign; defects: the count mismatch plus small islands; walls: wall length over the template's, minus 1. "
             f"t = {t0:,} is the pre-wound baseline.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", f"## Pre-wound baseline at t = {t0:,} (W12 branches): sign / intact / defects", "",
              "| Unit | Body | p_b | " + " | ".join(D.REPAIRS) + " |", "|---|---|---|" + "---|" * len(D.REPAIRS)]
    for u in D.UNITS:
        for b in D.BODIES:
            for rate in D.RATES:
                cells = [" / ".join((f(lv(u, b, "sign", t0, c)), f(lv(u, b, "intact", t0, c), 2), f(lv(u, b, "defects", t0, c), 2)))
                         for c in (f"{rate:g}/{rep}/W12" for rep in D.REPAIRS)]
                lines.append(f"| {u} | {b} | {rate:g} | " + " | ".join(cells) + " |")
    for ep, title, d in (("patch", "the body in the wound", 3), ("intact", "intact sheets", 2), ("defects", "defects", 2),
                         ("r_patch", "the record in the wound", 3)):
        lines += ["", f"## {title}: after the first wound (t = {t1:,}, W12) and after the second (t = {t2:,}: W12 / W12x / W2)", "",
                  "| Unit | Body | p_b | " + " | ".join(D.REPAIRS) + " |", "|---|---|---|" + "---|" * len(D.REPAIRS)]
        for u in D.UNITS:
            for b in D.BODIES:
                for rate in D.RATES:
                    cells = [f(lv(u, b, ep, t1, f"{rate:g}/{rep}/W12"), d) + " → " +
                             " / ".join(f(lv(u, b, ep, t2, f"{rate:g}/{rep}/{sc}"), d) for sc in D.SCHEDULES) for rep in D.REPAIRS]
                    lines.append(f"| {u} | {b} | {rate:g} | " + " | ".join(cells) + " |")
    lines += ["", "## The body in the wound over time (t = " + " / ".join(f"{t:,}" for t in D.READS) + "), W12", "",
              "| Unit | Body | p_b | " + " | ".join(D.REPAIRS) + " |", "|---|---|---|" + "---|" * len(D.REPAIRS)]
    for u in D.UNITS:
        for b in D.BODIES:
            for rate in D.RATES:
                cells = [" / ".join(f(lv(u, b, "patch", t, f"{rate:g}/{rep}/W12")) for t in D.READS) for rep in D.REPAIRS]
                lines.append(f"| {u} | {b} | {rate:g} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
