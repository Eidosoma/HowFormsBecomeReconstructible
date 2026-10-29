"""SC002's tables from the reader's outputs: python -m sc002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sc002 import design as D  # noqa: E402

FROZEN = LANE / "sc002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sc002")
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
    lines = [f"# SC002 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE001's tissue at read gain 0.2 and "
             "p_b = 1e-3 on cellpop's vacancy lattice. Runs are named situation + patch side @ turnover rate mu (deaths per "
             "cell and update; vacancies refilled by division at 0.1, daughters inherit): none8 (no event), cue8 (a quarter "
             "of the anchors corrupted, scattered), change4/8 (the patch's anchors re-specified and the target with them), "
             "regrow8 (the patch emptied and regrown by division from its rim at 0.04, no turnover), regrow+cue8 (the same "
             "with scattered cue corruption). Arms: cue (LR004's anchors as arbiter, no detector); inst-L (BE001's cable "
             "detector with instant junctions at coupling length L, threshold 0.1, a slow commitment state with tau 300); "
             "mat-T (junctions at lam 3 maturing as 1 - exp(-age / T) from each contact's formation). r_in: the record's "
             "agreement with the correct target over the patch's occupied sites (change: the new target; r_in_old: the old "
             "one); r_out: outside the patch; r_all: over the occupied sheet; opened: the share of sites committed, mean "
             "over the window; maturity: the mean maturity of the contacts.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title in (("r_in", "the record inside the patch"), ("r_all", "the record over the sheet"),
                      ("r_out", "the record outside the patch")):
        lines += ["", f"## {title} at t = {t1:,}: rows run, columns arm", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                lines += [f"**{u}, {b}**", "", "| run | " + " | ".join(D.ARMS) + " |", "|---|" + "---|" * len(D.ARMS)]
                for rn in D.RUNNAMES:
                    n = L[u][b][rn]
                    lines.append(f"| {rn} | " + " | ".join(f(n[arm][ep][ti][0]) for arm in D.ARMS) + " |")
                    if ep == "r_in" and rn.startswith("change"):
                        lines.append(f"| {rn}, old target | " + " | ".join(f(n[arm]["r_in_old"][ti][0]) for arm in D.ARMS) + " |")
                lines.append("")
    lines += ["## Committed share of sites (mean over the window) and contact maturity at t = 4,000", "",
              "| Unit | Body | run | " + " | ".join(D.ARMS) + " | maturity mat-300 / mat-1000 |",
              "|---|---|---|" + "---|" * len(D.ARMS) + "---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for rn in D.RUNNAMES:
                n = L[u][b][rn]
                lines.append(f"| {u} | {b} | {rn} | " + " | ".join(f(n[arm]["opened"][0], 4) for arm in D.ARMS)
                             + f" | {f(n['mat-300']['maturity'][ti][0])} / {f(n['mat-1000']['maturity'][ti][0])} |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
