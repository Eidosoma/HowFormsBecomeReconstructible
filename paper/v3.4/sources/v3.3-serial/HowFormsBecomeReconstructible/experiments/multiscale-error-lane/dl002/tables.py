"""DL002's tables from the reader's outputs: python -m dl002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from dl002 import design as D  # noqa: E402

FROZEN = LANE / "dl002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl002")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = s["levels"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    recs_a = [r.name for r in D.PANELS["A"]["records"]]
    recs_r = [r.name for r in D.PANELS["R"]["records"]]
    lines = [f"# DL002 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's strong period-8 lateral-inhibition body. Records: none; a16 and a4 positional anchors at 1/16 and 1/4 of "
             "the sites (gain 1.0); full, the held record at every site (gain 0.2); rel, a tissue-held relational record "
             "(gain 0.2). theta x0, x0.25, x0.5, x1 are environmental-field spreads 0, 0.05, 0.1, 0.2.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", "## A. Who holds the pattern: sign at t = 4,000 (spacing at 4,000 without a record)", "",
              "| Unit | Body | " + " | ".join(recs_a) + " | spacing |", "|---|---|" + "---|" * (len(recs_a) + 1)]
    for u in D.PANELS["A"]["units"]:
        for b in D.BODIES:
            e = L["A"][u][b]
            lines.append(f"| {u} | {b} | " + " | ".join(f(e[r]["sign@4000"][0]) for r in recs_a)
                         + f" | {f(e['none']['spacing@4000'][0], 2)} |")
    lines += ["", "## R. Who repairs it: agreement inside the 8 x 8 wound at t = 500 / 2,000 / 4,000", "",
              "| Unit | Body | " + " | ".join(recs_r) + " | rel record inside |", "|---|---|" + "---|" * (len(recs_r) + 1)]
    for u in D.PANELS["R"]["units"]:
        for b in D.BODIES:
            e = L["R"][u][b]
            cells = [" / ".join(f(e[r][f"patch@{t}"][0], 2) for t in D.SNAPS_R) for r in recs_r]
            rp = " / ".join(f(e["rel"][f"r_patch@{t}"][0], 2) for t in D.SNAPS_R)
            lines.append(f"| {u} | {b} | " + " | ".join(cells) + f" | {rp} |")
    lines += ["", "## A. Correction work (mean |dt g (r - V~)| per site and update, second half of the window)", "",
              "| Unit | Body | " + " | ".join(recs_a) + " |", "|---|---|" + "---|" * len(recs_a)]
    for u in D.PANELS["A"]["units"]:
        for b in D.BODIES:
            lines.append(f"| {u} | {b} | " + " | ".join(f(L["A"][u][b][r]["w_corr"][0], 4) for r in recs_a) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
