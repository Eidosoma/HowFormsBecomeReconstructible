"""Render TABLES.md from the reader's outputs: python -m br002.tables --out OUT_DIR

Block-mean levels per arm and condition (every number from summary.json), then the statements.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from br002 import design as D  # noqa: E402

SHOW = {"C": ("les_r", "adopt_flip", "rg_sign", "v_qual", "w_l1"), "R": ("les_r", "r_sign", "v_qual", "fR_qual"),
        "G": ("les_r", "les_v")}


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in body]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    summ = json.loads((a.out / "summary.json").read_text())
    verdicts = json.loads((a.out / "predictions_scored.json").read_text())
    md = [f"# BR002 tables ({summ['stage']}, blocks {summ['blocks'][0]}–{summ['blocks'][1] - 1})", "",
          "Block means over cases; rows are arms, columns conditions.", "",
          "## Registered statements", "", table(["id", "verdict"], [[k, v["verdict"]] for k, v in verdicts.items()]), ""]
    for p, spec in D.PANELS.items():
        conds = summ["panels"][p]["conditions"]
        for r, lv in summ["panels"][p]["levels"].items():
            for ep in SHOW[p]:
                if ep not in lv:
                    continue
                body = [[arm] + [("" if x is None else f"{x:.3f}" if ep != "w_l1" else f"{x:.0f}") for x in vals]
                        for arm, vals in lv[ep].items()]
                md += [f"## {p}. {spec['title']}: {r}, {ep}", "", table(["arm"] + conds, body), ""]
    (a.out / "TABLES.md").write_text("\n".join(md) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
