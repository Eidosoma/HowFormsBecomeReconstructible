"""EN002's tables from the reader's outputs: python -m en002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from en002 import design as D  # noqa: E402

FROZEN = LANE / "en002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "en002")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = s["levels"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    bodies = tuple(D.BODIES)
    budgets = [b.name for b in D.BUDGETS]
    lines = [f"# EN002 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li2 "
             "and li4 lateral inhibition tuned to period 8 (DL001). Budgets: B every drift paid with thermal noise, C every "
             "drift paid with activity-driven noise; the number is phi. Starvation to t = 2,000, recovery at full budget to "
             "t = 3,000.", "", "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for rec in ("none", "held"):
        lines += ["", f"## G. Sign at the end of starvation / after recovery (t = 2,000 / 3,000), record: {rec}", "",
                  "| Unit | Body | " + " | ".join(budgets) + " |", "|---|---|" + "---|" * len(budgets)]
        for u in D.PANELS["G"]["units"]:
            for b in bodies:
                cells = [f"{f(L['G'][u][b][f'{bb}/{rec}']['sign@2000'][0])} / {f(L['G'][u][b][f'{bb}/{rec}']['sign@3000'][0])}"
                         for bb in budgets]
                lines.append(f"| {u} | {b} | " + " | ".join(cells) + " |")
    lines += ["", "## G. Spacing at the end of starvation / after recovery, no record", "",
              "| Unit | Body | " + " | ".join(budgets) + " |", "|---|---|" + "---|" * len(budgets)]
    for u in D.PANELS["G"]["units"]:
        for b in bodies:
            cells = [f"{f(L['G'][u][b][f'{bb}/none']['spacing@2000'][0], 2)} / {f(L['G'][u][b][f'{bb}/none']['spacing@3000'][0], 2)}"
                     for bb in budgets]
            lines.append(f"| {u} | {b} | " + " | ".join(cells) + " |")
    lines += ["", "## G. Work per site and update during starvation, held record: drift / correction", "",
              "| Unit | Body | " + " | ".join(budgets) + " |", "|---|---|" + "---|" * len(budgets)]
    for u in D.PANELS["G"]["units"]:
        for b in bodies:
            cells = [f"{f(L['G'][u][b][f'{bb}/held']['w_drift'][0], 4)} / {f(L['G'][u][b][f'{bb}/held']['w_corr'][0], 4)}"
                     for bb in budgets]
            lines.append(f"| {u} | {b} | " + " | ".join(cells) + " |")
    for u in D.PANELS["W"]["units"]:
        for rec in ("none", "held"):
            for wd in ("reset8", "flip8"):
                lines += ["", f"## W. {u}, {wd}, record {rec}: agreement inside the wound at t = 250 / 500 / 2,000 / 3,000", "",
                          "| Body | " + " | ".join(budgets) + " |", "|---|" + "---|" * len(budgets)]
                for b in bodies:
                    cells = [" / ".join(f(L["W"][u][b][f"{bb}/{rec}/{wd}"][f"patch@{t}"][0], 2) for t in D.SNAPS_W) for bb in budgets]
                    lines.append(f"| {b} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
