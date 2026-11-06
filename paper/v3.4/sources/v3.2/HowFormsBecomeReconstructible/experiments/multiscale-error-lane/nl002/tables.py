"""NL002's tables: python -m nl002.tables --summary-dir DIR  ->  DIR/TABLES.md (from the reader's summaries).

For each unit and event, every arm's record (and, for dw, body) and recipient at the last read: regions at A's sign,
A's minority regions and cells, the R regions repaired, the killed square, own-versus-foreign specificity, and the
descending dose.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from nl002 import design as D  # noqa: E402

COLS = (("region_ok_A", "regions A"), ("min_reg_ok_A", "min regions A"), ("min_cell_ok_A", "min cells A"),
        ("ev_reg_ok", "R regions"), ("k_min_ok_A", "killed min"), ("spec_reg", "specificity"), ("k_spec_reg", "killed spec"))
TISSUE = ("t/r/", "t/v/")


def fmt(x):
    return "" if x is None else f"{x:+.3f}" if x < 0 else f"{x:.3f}"


def table(L, unit, src, event):
    rows = [f"| arm | {' | '.join(c for _, c in COLS)} | dose |", "|---" * (len(COLS) + 2) + "|"]
    for a in D.ARMNAMES:
        lab = f"{a}/{event}"
        vals = [L[f"{src}{e}"][lab][-1][0] for e, _ in COLS]
        dose = L["dose"][lab][0] if src in TISSUE else None
        rows.append(f"| {a} | {' | '.join(fmt(v) for v in vals)} | {'' if dose is None else f'{dose:.5f}'} |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-dir", type=Path, required=True)
    a = ap.parse_args()
    out = ["# NL002 tables", "", "Block means over the stage's blocks at the last read (2,000 updates); the recipient is a fresh dw body "
           "reading each branch's final L1 record for 2,000 updates.", ""]
    for u in D.UNITS:
        S = json.loads((a.summary_dir / f"summary_{u}.json").read_text())
        L = S["levels"]
        srcs = ((("t/r/", "record"), ("t/v/", "body")) if u == "dw" else (("t/r/", "record"),)) + \
            (("s/", "recipient of the L1 record"), ("c/", "recipient of the L1 record and the codes"))
        for e in D.EVENTS:
            for src, name in srcs:
                out += [f"## unit {u}, event {e}: {name}", "", table(L, u, src, e), ""]
        out += [f"## unit {u}: recipients of the acquired records", "",
                "| recipient | " + " | ".join(c for _, c in COLS) + " |", "|---" * (len(COLS) + 1) + "|"]
        for nm in ("acqA", "acqB", "none"):
            out.append(f"| {nm} | " + " | ".join(fmt(L[f's/{e}'][nm][-1][0]) for e, _ in COLS) + " |")
        out.append("")
    (a.summary_dir / "TABLES.md").write_text("\n".join(out) + "\n")
    print("wrote", a.summary_dir / "TABLES.md")


if __name__ == "__main__":
    main()
