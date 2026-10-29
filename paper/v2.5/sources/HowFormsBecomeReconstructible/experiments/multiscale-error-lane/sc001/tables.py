"""SC001's tables from the reader's outputs: python -m sc001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sc001 import design as D  # noqa: E402

FROZEN = LANE / "sc001" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def half_fill(node):
    """The front's roughness at the first trace point where at least half the sheet is occupied."""
    for fl, ro in zip(node["t_filled"], node["t_rough"]):
        if fl is not None and fl >= 0.5:
            return ro
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sc001")
    a = ap.parse_args()
    G = json.loads((a.out / "summary_G.json").read_text())
    R = json.loads((a.out / "summary_R.json").read_text())
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    ti = len(D.SNAPS) - 1
    lines = [f"# SC001 tables ({G['stage']}, blocks {G['blocks'][0]}–{G['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, NaN-aware, then the mean over blocks). cellpop's vacancy "
             "lattice: cells divide into empty neighbours, die and exchange places; empty sites hold 0. Bodies: dw the "
             "double well, li4 DL001's period-8 lateral-inhibition body. Panel G: S4 stripes grown from DL003's two-line "
             "boundary (perp across the stripes, par along them), the record held at the boundary's cells (gain 1.0). "
             "Arms: front/s DL003's prescribed front, one line per s updates; grow/s division at the margin at 1/s per "
             "update, daughters copying; nb newborn daughters with grow's divisions; smooth division with a flat margin "
             "(one line per 100 updates, cells added in a random order within each line); turn grow with turnover; none "
             "grow without the boundary's record; diffL the boundary's record diffusing with decay length L instead. "
             "Panel R: an 8 x 8 patch killed at t = 0 (reset in place, or emptied and regrown by division at 0.04 or 0.01 "
             "per update with copying or newborn daughters), the record taught by itself (record+parity) or the body.",
             "", "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    cols = ("sign", "far", "near", "intact", "defects", "filled@1000", "rough", "shift", "spacing")
    for u, ub in G["levels"].items():
        for b, bb in ub.items():
            for g, gb in bb.items():
                lines += ["", f"## Panel G, {u}, {b}, {g}: t = {D.SNAPS[ti]:,}", "",
                          "| Arm | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
                for arm, n in gb.items():
                    cells = [f(n["sign"][ti][0]), f(n["far"][ti][0]), f(n["near"][ti][0]), f(n["intact"][0]),
                             f(n["defects"][0], 2), f(n["filled"][0][0]), f(half_fill(n), 2), f(n["shift"][ti][0]),
                             f(n["spacing"][ti][0], 2)]
                    lines.append(f"| {arm} | " + " | ".join(cells) + " |")
                lines += ["", "Registration by distance from the boundary (0 to 15):", "",
                          "| Arm | " + " | ".join(str(d) for d in range(D.DMAX + 1)) + " |",
                          "|---|" + "---|" * (D.DMAX + 1)]
                for arm, n in gb.items():
                    lines.append(f"| {arm} | " + " | ".join(f(x, 2) for x in n["profile"]) + " |")
    rcols = ("patch@250", "patch@1000", "patch@4000", "r_patch@250", "r_patch@4000", "filled@250", "sign", "r_sign",
             "intact", "defects")
    for u, ub in R["levels"].items():
        for b, bb in ub.items():
            lines += ["", f"## Panel R, {u}, {b}", "", "| Condition | " + " | ".join(rcols) + " |",
                      "|---|" + "---|" * len(rcols)]
            for c, n in bb.items():
                cells = [f(n["patch"][0][0]), f(n["patch"][1][0]), f(n["patch"][-1][0]), f(n["r_patch"][0][0]),
                         f(n["r_patch"][-1][0]), f(n["filled"][0][0]), f(n["sign"][-1][0]), f(n["r_sign"][-1][0]),
                         f(n["intact"][0]), f(n["defects"][0], 2)]
                lines.append(f"| {c} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
