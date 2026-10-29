"""SC003's tables from the reader's outputs: python -m sc003.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sc003 import design as D  # noqa: E402

FROZEN = LANE / "sc003" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sc003")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head = s
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    ti = len(D.READS) - 1
    t1 = D.READS[ti]
    lines = [f"# SC003 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). SC002's tissue (BE001's tissue at "
             "read gain 0.2 and p_b = 1e-3 on cellpop's vacancy lattice). Runs are named situation + patch side @ turnover "
             "rate mu (deaths per cell and update; vacancies refilled by division at 0.1, daughters inherit): none8 (no "
             "event), cue8 (a quarter of the anchors corrupted, scattered), change4 (a 4 x 4 patch's anchors re-specified and "
             "the target with them), regrow8 (an 8 x 8 patch emptied and regrown by division from its rim at 0.04, no "
             "turnover), regrow+cue8 (the same with scattered cue corruption). Arms: cue (LR004's anchors as arbiter, no "
             "detector); inst-3 (BE001's cable detector, instant junctions at lam 3); iso-3 (the same, but a contact carries "
             "nothing in its first update: every newborn reads only its own cue once); emt-T (instant junctions at the "
             "effective-medium coupling of mat-T's stationary junctions at the run's mu); iso-emt-T (emt-T with iso-3's "
             "isolation); mat-T (junctions at lam 3 maturing as 1 - exp(-age / T) from each contact's formation). r_in: the "
             "record's agreement with the correct target over the patch's occupied sites (change: the new target; r_in_old: "
             "the old one); r_out: outside the patch; r_all: over the occupied sheet; opened: the share of sites committed, "
             "mean over the window; new commitments per case over the window by the committing cell's age (0, 1-31, 32-104, "
             ">= 105 updates).", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title in (("r_in", "the record inside the patch"), ("r_all", "the record over the sheet"),
                      ("r_out", "the record outside the patch")):
        lines += ["", f"## {title} at t = {t1:,}: rows run, columns arm", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                lines += [f"**{u}, {b}**", "", "| run | " + " | ".join(D.ARMS_T) + " |", "|---|" + "---|" * len(D.ARMS_T)]
                for run, rn in zip(D.RUNS, D.RUNNAMES):
                    n = L[u][b][rn]
                    cell = lambda arm, e=ep: f(n[arm][e][ti][0]) if arm in n else "—"
                    lines.append(f"| {rn} | " + " | ".join(cell(arm) for arm in D.ARMS_T) + " |")
                    if ep == "r_in" and rn.startswith("change"):
                        lines.append(f"| {rn}, old target | " + " | ".join(cell(arm, "r_in_old") for arm in D.ARMS_T) + " |")
                lines.append("")
    lines += ["## New commitments per case over the window by the cell's age (0 / 1-31 / 32-104 / >= 105)", "",
              "| Unit | Body | run | " + " | ".join(D.ARMS_T[1:]) + " |", "|---|---|---|" + "---|" * (len(D.ARMS_T) - 1)]
    for u in D.UNITS:
        for b in D.BODIES:
            for run, rn in zip(D.RUNS, D.RUNNAMES):
                n = L[u][b][rn]
                cell = lambda arm: " / ".join(f(x[0], 1) for x in n[arm]["newc"]) if arm in n else "—"
                lines.append(f"| {u} | {b} | {rn} | " + " | ".join(cell(arm) for arm in D.ARMS_T[1:]) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
