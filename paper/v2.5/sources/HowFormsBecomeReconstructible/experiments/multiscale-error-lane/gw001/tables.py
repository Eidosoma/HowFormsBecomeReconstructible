"""Render TABLES.md from the reader's outputs: python -m gw001.tables --out OUT_DIR

Panel R: per geometry, kept at t = 2000 and 8000 and the median t95, rows arms and columns wounded conditions,
and the undamaged record's agreement. Panel B: the body's endpoints per regime. Every number from summary.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gw001 import design as D  # noqa: E402


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in body]
    return "\n".join(out)


def fmt(x, key):
    if key == "t95_median":
        return "never" if x == float("inf") else f"{x:.0f}"
    return f"{x:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    summ = json.loads((a.out / "summary.json").read_text())
    verdicts = json.loads((a.out / "predictions_scored.json").read_text())
    md = [f"# GW001 tables ({summ['stage']}, blocks {summ['blocks'][0]}–{summ['blocks'][1] - 1})", "",
          "Block means over cases (t95: median over cases; 'never' = not within 8,000 updates). Rows are arms.", "",
          "## Registered statements", "", table(["id", "verdict"], [[k, v["verdict"]] for k, v in verdicts.items()]), ""]
    for unit, arms in summ["panels"]["R"]["levels"].items():
        conds = [c.name for c in D.GEOMETRIES[unit] if c.name != "sham"]
        for key in ("kept@2000", "kept@8000", "t95_median"):
            body = [[arm] + [fmt(row[c][key], key) for c in conds] for arm, row in arms.items()]
            md += [f"## R. {unit}: {key}", "", table(["arm"] + conds, body), ""]
        body = [[arm, *(f"{row['sham'][k]:.3f}" for k in ("rsign@2000", "rsign@4000", "rsign@8000"))] for arm, row in arms.items()]
        md += [f"## R. {unit}: undamaged record agreement", "", table(["arm", "t = 2000", "4000", "8000"], body), ""]
    conds = [c.name for c in D.COND_B]
    for unit, arms in summ["panels"]["B"]["levels"].items():
        for ep in ("v_qual", "v_out", "les_v", "les_r"):
            body = [[arm] + [f"{row[ep][c]:.3f}" for c in conds] for arm, row in arms.items()]
            md += [f"## B. {unit}: {ep}", "", table(["arm"] + conds, body), ""]
    (a.out / "TABLES.md").write_text("\n".join(md) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
