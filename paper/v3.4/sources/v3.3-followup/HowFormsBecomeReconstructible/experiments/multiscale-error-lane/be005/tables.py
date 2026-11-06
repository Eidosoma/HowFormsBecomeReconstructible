"""BE005's tables from the reader's outputs: python -m be005.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be005 import design as D  # noqa: E402

FROZEN = LANE / "be005" / "frozen"
SHOW = {"memory": ("r_in", "v_in", "r_all"), "change": ("r_in", "r_in_old", "r_all"), "cue": ("r_all", "r_fp2", "r_out8")}


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be005")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head = s
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    lines = [f"# BE005 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE004's tissue (BE002's: BE001's at "
             "read gain 0.2 and p_b = 1e-3, a full 32 x 32 sheet), BE001's six units and both bodies. memory4@D: a 4 x 4 memory "
             "damage, the signal over the patch dilated by 2 at D + 1 to D + 1,000; change4@0: a legitimate change of a 4 x 4 "
             "patch, the signal at 1-1,000; cue4@0: a quarter of the anchors corrupted, a prompt sham. Arms: cue (LR004's "
             "arbiter); bio-L (BE001's detector at coupling L); dial-eE (BE002's dial, the arbiter's bonds relearning at E; "
             "dial-e0.01 is BE004's dial); never-eE (the same, the signal never on); dial-tvT (the dial with membrane time "
             "constant T); dial-tN-tvT (on for its first N updates); dial-fP-tvT (on at each update with probability P); "
             "never-tvT. r_in: the patch (against the new target in a change); r_in_old: against the old target; v_in: the "
             "body in the patch; r_fp2: the footprint; r_out8: outside the patch dilated by 8; r_all: the sheet. onset: the "
             "share of the patch below -theta at the signal's first update under the footprint's steady potentials; hit: the "
             "share of the patch that ever triggered; sensors: the share of the patch's anchored cells right at the signal's "
             "first update.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", "## Panel D: r_in at t = 4,000 by the delay's multiple of T*(eta), and the sensors at onset; rows unit, body, eta", "",
              "| Unit | Body | eta | never | " + " | ".join(f"m = {m:g}" for m in D.MULTS) + " | "
              + " | ".join(f"sensors m = {m:g}" for m in D.MULTS[1:]) + " |",
              "|---|---|---|---|" + "---|" * (2 * len(D.MULTS) - 1)]
    for u in D.UNITS:
        for b in D.BODIES:
            for e in D.ETAS:
                n = L[u][b]
                ef = D.fmt(e)
                row = [f(n[D.run_name("memory", 4, 0)][f"never-e{ef}"]["r_in"][-1][0])]
                row += [f(n[D.where(e, m)[0]][f"dial-e{ef}"]["r_in"][-1][0]) for m in D.MULTS]
                row += [f(n[D.where(e, m)[0]][f"dial-e{ef}"]["anc_on_share"][0]) for m in D.MULTS[1:]]
                lines.append(f"| {u} | {b} | {ef} | " + " | ".join(row) + " |")
    for run in D.RUNS:
        if run[0] == "memory" and run[2]:
            continue
        rn, arms = D.run_name(*run), run[3]
        lines += ["", f"## {rn} at t = {D.READS[-1]:,}: rows unit, body and endpoint; columns arm", "",
                  "| Unit | Body | endpoint | " + " | ".join(arms) + " |", "|---|---|---|" + "---|" * len(arms)]
        for u in D.UNITS:
            for b in D.BODIES:
                n = L[u][b][rn]
                for e in SHOW[run[0]]:
                    if e in n[arms[0]]:
                        lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][-1][0]) for arm in arms) + " |")
                for e in ("onset", "hit"):
                    lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][0]) if arm in D.SIGNAL_ARMS else "—"
                                                                      for arm in arms) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
