"""Render TABLES.md from the reader's outputs: python -m en001.tables --out OUT_DIR

Block means over cases; one table per panel, regime and record design, budgets as rows. Columns: the body's
pattern (v_qual) and the record (r_sign) without damage at the end of starvation; the record kept in a flipped and
in a reset wound at the end of starvation and after recovery; the body under turnover; the body after recovery;
t95 of the flipped wound (a wound never healed counts as the window plus one snapshot); the spend per cell and
update; the store's availability inside and outside a flipped wound (panel E).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from en001 import design as D  # noqa: E402

COLS = (("sham v", "v_qual", "sham"), ("sham r", "r_sign", "sham"), ("flip kept", "les_r", "flip-6x6"),
        ("flip kept, rec.", "les_r_rec", "flip-6x6"), ("reset kept", "les_r", "reset-6x6"),
        ("turnover v", "v_qual", "turnover-0.001"), ("sham v, rec.", "v_qual_rec", "sham"), ("flip t95", "t95", "flip-6x6"))


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
    conds = summ["conditions"]
    md = [f"# EN001 tables ({summ['stage']}, blocks {summ['blocks'][0]}–{summ['blocks'][1] - 1})", "",
          "Block means over cases. Starvation lasts 2,000 updates at the budget shown, then 1,000 updates of recovery "
          "at the full budget ('rec.'). t95 counts a wound never healed as 3,100.", "",
          "## Registered statements", "", table(["id", "verdict"], [[k, v["verdict"]] for k, v in verdicts.items()]), ""]
    for p, spec in D.PANELS.items():
        for r, arms in summ["panels"][p].items():
            for arm, buds in arms.items():
                hdr = ["budget"] + [c[0] for c in COLS] + (["a in wound", "a outside"] if p == "E" else [])
                body = []
                for b, eps in buds.items():
                    row = [b]
                    for _, ep, cond in COLS:
                        x = eps.get(ep, [None] * len(conds))[conds.index(cond)]
                        row.append("" if x is None else (f"{x:.0f}" if ep == "t95" else f"{x:.3f}"))
                    if p == "E":
                        for ep in ("a_patch", "a_rest"):
                            x = eps.get(ep, [None] * len(conds))[conds.index("flip-6x6")]
                            row.append("" if x is None else f"{x:.3f}")
                    body.append(row)
                md += [f"## {p}. {r}, {arm}", "", table(hdr, body), ""]
    (a.out / "TABLES.md").write_text("\n".join(md) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
