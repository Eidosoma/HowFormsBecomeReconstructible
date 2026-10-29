"""BE003's tables from the reader's outputs: python -m be003.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be003 import design as D  # noqa: E402

FROZEN = LANE / "be003" / "frozen"
SHOW = {"regrow": ("r_in", "r_ring", "r_out", "r_all"), "regrow+cue": ("r_in", "r_ring", "r_out", "r_all"),
        "twin": ("r_young", "r_twin", "r_in", "r_young_old", "r_twin_old")}


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be003")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head = s
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    lines = [f"# BE003 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). SC002's tissue (BE001's at read gain "
             "0.2 and p_b = 1e-3 on cellpop's vacancy lattice), no turnover. Every run empties an 8 x 8 wound at t = 0, regrown "
             "by division from its rim at 0.04 per update (daughters inherit). regrow8: clean cues, the injury signal over the "
             "wound dilated by 2 at updates 1-1,000 (signal arms); regrow8_late: the signal at 1,001-2,000 (signal arms only); "
             "regrow+cue8: a quarter of the anchors corrupted (scattered); twin4@d: after update d the cue of two 4 x 4 patches "
             "is re-specified, 'young' at the wound's centre and its 'twin' 16 columns away in old tissue, the signal over both "
             "dilated by 2 at d + 1 to d + 1,000; read at d + 2,000. Arms: cue (LR004's arbiter); inst-L (instant junctions, "
             "coupling length L); mat-T (lam 3 maturing as 1 - exp(-age / T)); dial (inst-3 with the signal: junctions "
             "touching the footprint at lam_sig^2 = 1 while it is on); mat-dial (mat-300 with the signal). r_in: the wound; "
             "r_young / r_twin: the patches (r_*_old: against the old target); r_ring: the wound dilated by 2, less the wound; "
             "r_out: outside the wound and the twin, each dilated by 2; r_all: the sheet. opened: share of sites committed, "
             "mean over the window.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for run, rn in zip(D.RUNS, D.RUNNAMES):
        arms = D.run_arms(*run)
        t1 = D.run_reads(*run)[-1]
        lines += ["", f"## {rn} at t = {t1:,}: rows unit, body and endpoint; columns arm", "",
                  "| Unit | Body | endpoint | " + " | ".join(arms) + " |", "|---|---|---|" + "---|" * len(arms)]
        for u in D.UNITS:
            for b in D.BODIES:
                n = L[u][b][rn]
                for e in SHOW[run[0]]:
                    if e in n[arms[0]]:
                        lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][-1][0]) for arm in arms) + " |")
                lines.append(f"| {u} | {b} | opened | " + " | ".join(f(n[arm]["opened"][0], 4) for arm in arms) + " |")
    lines += ["", "## Mean maturity of the wound's contacts at each run's reads (mat-300 / mat-1000 / mat-dial)", "",
              "| Unit | Body | run | reads | maturity |", "|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for run, rn in zip(D.RUNS, D.RUNNAMES):
                n = L[u][b][rn]
                ms = [a_ for a_ in ("mat-300", "mat-1000", "mat-dial") if a_ in n]
                lines.append(f"| {u} | {b} | {rn} | {', '.join(str(t) for t in D.run_reads(*run))} | "
                             + "; ".join(f"{a_}: " + "/".join(f(x[0]) for x in n[a_]["maturity"]) for a_ in ms) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
