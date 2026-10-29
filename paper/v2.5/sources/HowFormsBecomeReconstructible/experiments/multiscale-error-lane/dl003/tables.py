"""DL003's tables from the reader's outputs: python -m dl003.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from dl003 import design as D  # noqa: E402

FROZEN = LANE / "dl003" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl003")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = s["levels"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    lines = [f"# DL003 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's strong period-8 lateral-inhibition body. Positional information at 64 cells holding the acquired record "
             "at gain 1.0: scatter (random cells), par (a boundary along the stripes, straddling a wall), perp (a boundary "
             "across the stripes), cluster (an 8 x 8 block); none; full (the held record everywhere, gain 0.2). /fN: the "
             "sheet is activated by a front from the boundary, one line per N updates; none/perp-f100 spreads from the perp "
             "boundary's position without anchors. theta x0, x0.25, x0.5, x1 scale the environmental field.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for p in D.PANELS:
        arms = D.PANELS[p]["arms"]
        lines += ["", f"## {p}. {D.PANELS[p]['title'].capitalize()}: sign at t = 1,000 / 4,000", "",
                  "| Arm | " + " | ".join(f"{b} x{th:g}" for b in D.BODIES for th in D.THETAS) + " |",
                  "|---|" + "---|" * (len(D.BODIES) * len(D.THETAS))]
        for arm in arms:
            cells = [f"{f(L[p][D.unit_name(th)][b][arm.name]['sign@1000'][0], 2)} / {f(L[p][D.unit_name(th)][b][arm.name]['sign@4000'][0])}"
                     for b in D.BODIES for th in D.THETAS]
            lines.append(f"| {arm.name} | " + " | ".join(cells) + " |")
        lines += ["", f"## {p}. Layout (best cyclic shift) and spacing at t = 4,000", "",
                  "| Arm | " + " | ".join(f"{b} x{th:g}" for b in D.BODIES for th in D.THETAS) + " |",
                  "|---|" + "---|" * (len(D.BODIES) * len(D.THETAS))]
        for arm in arms:
            cells = [f"{f(L[p][D.unit_name(th)][b][arm.name]['shift@4000'][0])} / {f(L[p][D.unit_name(th)][b][arm.name]['spacing@4000'][0], 2)}"
                     for b in D.BODIES for th in D.THETAS]
            lines.append(f"| {arm.name} | " + " | ".join(cells) + " |")
        lines += ["", f"## {p}. Agreement by distance from the arm's boundary or cluster at t = 4,000 (li4)", "",
                  "Distances across the boundary (0: its own lines; 15: the far side); for the cluster, Chebyshev distance. "
                  "Columns: theta x0 / x0.5 / x1, each as distance 0-1 | 2-5 | 6-11 | 12-15 (cluster: 0-1 | 2-5 | 6-9 | 10-12).", "",
                  "| Arm | x0 | x0.5 | x1 |", "|---|---|---|---|"]
        for arm in arms:
            if not arm.home:
                continue
            cells = []
            for th in (0.0, 0.5, 1.0):
                pr = L[p][D.unit_name(th)]["li4"][arm.name][f"prof_{arm.home}"]
                wins = ((0, 2), (2, 6), (6, 10), (10, 13)) if arm.home == "cluster" else ((0, 2), (2, 6), (6, 12), (12, 16))
                cells.append(" | ".join(f(float(np.mean(pr[a:b])), 2) for a, b in wins))
            lines.append(f"| {arm.name} | " + " | ".join(cells) + " |")
    lines += ["", "## Correction work (mean |dt g (r - V~)| per site and update, second half of the window), li4", "",
              "| Panel, arm | x0 | x0.25 | x0.5 | x1 |", "|---|---|---|---|---|"]
    for p in D.PANELS:
        for arm in D.PANELS[p]["arms"]:
            lines.append(f"| {p}, {arm.name} | " + " | ".join(f(L[p][D.unit_name(th)]["li4"][arm.name]["w_corr"][0], 4) for th in D.THETAS) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
