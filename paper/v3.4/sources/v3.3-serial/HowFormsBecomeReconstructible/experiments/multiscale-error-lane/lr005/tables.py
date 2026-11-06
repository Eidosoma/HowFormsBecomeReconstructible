"""LR005's tables from the reader's outputs: python -m lr005.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from lr005 import design as D  # noqa: E402

FROZEN = LANE / "lr005" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr005")
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
    lines = [f"# LR005 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's period-8 lateral-inhibition body, each reading the first relational record (no coarse code) at gain "
             "0.05 or 0.2. Bond signs flip at p_b = 1e-3 per update. One event at t = 0 on an 8 x 8 patch: none; body (the "
             "body flipped); memory (the record flipped with consistent bonds); shared (the cells killed: body newborn, record "
             "0, bonds between dead cells lost, anchors lost); cue (a quarter of the anchors flipped, scattered); change (the "
             "patch's anchors flipped and the target with them). Arms: record+parity (LR001); body (LR002); vote2r (LR004's "
             "vote, the second record sharing the wounds); cue (LR004's anchors at a quarter of the cells); vote3 (majority "
             "of body, record and anchor); community-s / -c (cue, with a latched community zone, sensitive Q 0.5 or "
             "conservative Q 0.75). r_in / v_in: the record's / body's agreement with the correct target inside the patch "
             "(change: the new target; r_in_old: the old one); r_all: over the sheet; opened: the share of cells in a "
             "community zone, mean over the window.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title in (("r_in", "the record inside the patch"), ("v_in", "the body inside the patch"),
                      ("r_all", "the record over the sheet")):
        lines += ["", f"## {title} at t = {t1:,}: rows situation, columns arm", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                for g in D.GAINS:
                    lines += [f"**{u}, {b}, read gain {g:g}**", "", "| situation | " + " | ".join(D.ARMS) + " |",
                              "|---|" + "---|" * len(D.ARMS)]
                    for s in D.SITUATIONS:
                        n = L[u][b][f"{g:g}"][s]
                        lines.append(f"| {s} | " + " | ".join(f(n[arm][ep][ti][0]) for arm in D.ARMS) + " |")
                    n = L[u][b][f"{g:g}"]["change"]
                    if ep == "r_in":
                        lines.append("| change, old target | " + " | ".join(f(n[arm]["r_in_old"][ti][0]) for arm in D.ARMS) + " |")
                    lines.append("")
    lines += ["## Community zones: share of cells in a zone (mean over the window)", "",
              "| Unit | Body | Gain | Arm | " + " | ".join(D.SITUATIONS) + " |", "|---|---|---|---|" + "---|" * len(D.SITUATIONS)]
    for u in D.UNITS:
        for b in D.BODIES:
            for g in D.GAINS:
                for arm in ("community-s", "community-c"):
                    cells = [f(L[u][b][f"{g:g}"][s][arm]["opened"][0], 4) for s in D.SITUATIONS]
                    lines.append(f"| {u} | {b} | {g:g} | {arm} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
