"""BE001's tables from the reader's outputs: python -m be001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be001 import design as D  # noqa: E402

FROZEN = LANE / "be001" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be001")
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
    runs = [D.run_name(s, z) for s, z in D.RUNS]
    lines = [f"# BE001 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). LR005's tissue at read gain 0.2 and "
             "p_b = 1e-3. Runs: none8 (no event), cue8 (a quarter of the anchors corrupted, scattered), memory4/8/12 (the "
             "record flipped consistently on a patch of side 4, 8, 12), change4/8/12 (the patch's anchors re-specified and "
             "the target with them), shared8 (the patch's cells killed). Arms: cue (LR004's anchors as arbiter); "
             "community-s / -c (LR005's window count and timer, q 0.5 / 0.75); bio-L (a cable detector with coupling length "
             "L and threshold 0.1, a slow commitment state with tau 300); bio-2-gated (voltage-gated junctions); bio-2-noisy "
             "(channel noise 0.2); bio-1.5-cautious (threshold 0.5). r_in: the record's agreement with the correct target "
             "inside the patch (change: the new target; r_in_old: the old one); r_all: over the sheet; opened: the share of "
             "cells committed, mean over the window.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title in (("r_in", "the record inside the patch"), ("r_all", "the record over the sheet")):
        lines += ["", f"## {title} at t = {t1:,}: rows run, columns arm", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                lines += [f"**{u}, {b}**", "", "| run | " + " | ".join(D.ARMS) + " |", "|---|" + "---|" * len(D.ARMS)]
                for rn in runs:
                    n = L[u][b][rn]
                    lines.append(f"| {rn} | " + " | ".join(f(n[arm][ep][ti][0]) for arm in D.ARMS) + " |")
                    if ep == "r_in" and rn.startswith("change"):
                        lines.append(f"| {rn}, old target | " + " | ".join(f(n[arm]["r_in_old"][ti][0]) for arm in D.ARMS) + " |")
                lines.append("")
    lines += ["## Committed share of cells (mean over the window)", "",
              "| Unit | Body | run | " + " | ".join(D.ARMS) + " |", "|---|---|---|" + "---|" * len(D.ARMS)]
    for u in D.UNITS:
        for b in D.BODIES:
            for rn in runs:
                lines.append(f"| {u} | {b} | {rn} | " + " | ".join(f(L[u][b][rn][arm]["opened"][0], 4) for arm in D.ARMS) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
