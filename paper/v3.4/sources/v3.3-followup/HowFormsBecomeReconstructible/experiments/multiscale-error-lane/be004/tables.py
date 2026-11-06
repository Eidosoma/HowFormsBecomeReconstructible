"""BE004's tables from the reader's outputs: python -m be004.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be004 import design as D  # noqa: E402

FROZEN = LANE / "be004" / "frozen"
SHOW = {"memory": ("r_in", "v_in", "anc_right", "r_all"), "change": ("r_in", "r_in_old", "v_in", "r_all"),
        "cue": ("r_all", "r_fp0", "r_fp2", "r_fp4", "r_fp8", "r_out8")}


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be004")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head = s
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    lines = [f"# BE004 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE002's tissue (BE001's at read gain "
             "0.2 and p_b = 1e-3, a full 32 x 32 sheet), BE001's six units and both bodies. memory4@D: a 4 x 4 memory damage, the "
             "signal over the patch dilated by 2 at D + 1 to D + 1,000; cue4@D: a quarter of the anchors corrupted (scattered), a "
             "sham signal over the 4 x 4 patch's footprint at D + 1 to D + 1,000; change4@0: a legitimate change of a 4 x 4 "
             "patch, the signal at 1-1,000. Arms: cue (LR004's arbiter); bio-L (BE001's cable detector at coupling L); dial "
             "(BE002's dial-local: lam 3 at rest, junctions touching the footprint at lam_sig = 1 while the signal is on); "
             "dial-hold (the dial; while the signal is pending the arbiter takes no cue inside the footprint); dial-sS (the "
             "footprint shifted S sites along the rows); dial-dD (the patch dilated by D); dial-wL (closure to lam_sig = L); "
             "dial-fP (the signal on each update with probability P). r_in: the patch (against the new target in a change); "
             "r_in_old: against the old target; v_in: the body in the patch; anc_right: the share of the patch's anchored "
             "cells whose record is right; r_fpD: the patch dilated by D; r_out8: outside the patch dilated by 8; r_all: the "
             "sheet. opened: share of sites committed, mean over the window; onset: the share of the patch that triggers at "
             "the signal's first update under the footprint's conductances.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", "## Panel E at t = 4,000, and at the signal's onset: rows unit and body", "",
              "| Unit | Body | dial@0 r_in | " + " | ".join(f"dial@{d} / hold@{d} r_in" for d in D.DELAYS[1:]) + " | "
              + " | ".join(f"anc_right at {d}: dial / hold" for d in D.DELAYS[1:]) + " | "
              + " | ".join(f"onset @{d}: dial / hold" for d in D.DELAYS[1:]) + " |",
              "|---|---|---|" + "---|" * (3 * (len(D.DELAYS) - 1))]
    for u in D.UNITS:
        for b in D.BODIES:
            n = L[u][b]
            row = [f(n["memory4@0"]["dial"]["r_in"][-1][0])]
            row += [f"{f(n[f'memory4@{d}']['dial']['r_in'][-1][0])} / {f(n[f'memory4@{d}']['dial-hold']['r_in'][-1][0])}" for d in D.DELAYS[1:]]
            row += [f"{f(n[f'memory4@{d}']['dial']['anc_right'][D.READS.index(d)][0])} / "
                    f"{f(n[f'memory4@{d}']['dial-hold']['anc_right'][D.READS.index(d)][0])}" for d in D.DELAYS[1:]]
            row += [f"{f(n[f'memory4@{d}']['dial']['onset'][0])} / {f(n[f'memory4@{d}']['dial-hold']['onset'][0])}" for d in D.DELAYS[1:]]
            lines.append(f"| {u} | {b} | " + " | ".join(row) + " |")
    for run in D.RUNS:
        rn, arms = D.run_name(*run), run[3]
        lines += ["", f"## {rn} at t = {D.READS[-1]:,}: rows unit, body and endpoint; columns arm", "",
                  "| Unit | Body | endpoint | " + " | ".join(arms) + " |", "|---|---|---|" + "---|" * len(arms)]
        for u in D.UNITS:
            for b in D.BODIES:
                n = L[u][b][rn]
                for e in SHOW[run[0]]:
                    if e in n[arms[0]]:
                        lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][-1][0]) for arm in arms) + " |")
                lines.append(f"| {u} | {b} | opened | " + " | ".join(f(n[arm]["opened"][0], 4) for arm in arms) + " |")
                lines.append(f"| {u} | {b} | onset | " + " | ".join(f(n[arm]["onset"][0]) if arm in D.SIGNAL_ARMS else "—"
                                                                    for arm in arms) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
