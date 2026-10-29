"""BE002's tables from the reader's outputs: python -m be002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be002 import design as D  # noqa: E402

FROZEN = LANE / "be002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be002")
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
    runs = list(D.RUNNAMES)
    lines = [f"# BE002 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE001's tissue at read gain 0.2 and "
             "p_b = 1e-3. Runs: none8 (no event), cue8 (a quarter of the anchors corrupted, scattered), memory4 (the record "
             "flipped consistently on a 4 x 4 patch), change4 / change8 (the patch's anchors re-specified and the target with "
             "them); '_sig': with the regime signal on updates 1-1,000 over the patch dilated by 2 sites (none8_sig and "
             "cue8_sig: a sham signal over an 8 x 8 patch's footprint with no event there); '_late': the signal on updates "
             "1,001-2,000. Arms: cue (LR004's anchors as arbiter); bio-L (BE001's cable detector with coupling length L, "
             "threshold 0.1, commitment tau 300); dial-local (length 3, junctions touching the footprint closed to length 1 "
             "while the signal is on); dial-global (length 3, 1 everywhere while the signal is on); permit-local (length 1.5, "
             "new commitments only in the footprint while the signal is on). r_in: the record's agreement with the correct "
             "target inside the patch (change: the new target; r_in_old: the old one, what coherent corruption would cost); "
             "r_fp / r_out: inside / outside the footprint; r_all: over the sheet; opened (opened_out): the share of cells "
             "committed (outside the footprint), mean over the window.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title, which in (("r_in", "the record inside the patch", None),
                             ("r_fp", "the record inside the footprint", None),
                             ("r_out", "the record outside the footprint", None),
                             ("r_all", "the record over the sheet", None)):
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
    lines += ["## Committed share of cells, over the sheet / outside the footprint (mean over the window)", "",
              "| Unit | Body | run | " + " | ".join(D.ARMS) + " |", "|---|---|---|" + "---|" * len(D.ARMS)]
    for u in D.UNITS:
        for b in D.BODIES:
            for rn in runs:
                lines.append(f"| {u} | {b} | {rn} | " + " | ".join(
                    f"{f(L[u][b][rn][arm]['opened'][0], 4)} / {f(L[u][b][rn][arm]['opened_out'][0], 4)}" for arm in D.ARMS) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
