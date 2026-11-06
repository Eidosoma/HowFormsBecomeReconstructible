"""NL001's tables from the reader's outputs: python -m nl001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from nl001 import design as D  # noqa: E402

COLS = ("cell_err", "region_err", "block_err", "min_cell_ok", "min_region_ok", "fine_ok", "regions_ok", "block_ok",
        "bmin_ok", "c2_ok", "kill_ok", "kill_reg_ok", "kill_min_ok")


def f(x, d=4):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl001")
    a = ap.parse_args()
    S = json.loads((a.out / "predictions_scored.json").read_text())
    head = None
    lines = []
    for e in D.EVENTS:
        s = json.loads((a.out / f"summary_{e}.json").read_text())
        head = head or s
        lines += ["", f"## Event {e} at t = {D.READS[-1]:,}: block means (rows arm, columns endpoint)", "",
                  "| Arm | " + " | ".join(COLS) + " |", "|---|" + "---|" * len(COLS)]
        for arm in D.RUNS[e]:
            n = s["levels"][arm]
            lines.append(f"| {arm} | " + " | ".join(f(n[c][-1][0]) for c in COLS) + " |")
    top = [f"# NL001 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
           "Block means (each block's mean over its 8 cases, then the mean over blocks). LR001's record of relations "
           "alone on a 64 x 64 sheet; L2 a region code (4 x 4) in the record's gauge frame, absolute or relative to "
           "the block's store; L3 a block code (16 x 16), a store or derived from the region codes. Events: none; F "
           "scattered fine flips; R coherent regional errors; B a coherent block error (absolute region codes "
           "corrupted with it); FRB all three; C3 a corrupted block store; C2 a corrupted region store; K a killed "
           "2 x 2 square of regions.", "", "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    top += [f"| {k} | {v['verdict']} | {v['words']} |" for k, v in S.items()]
    (a.out / "TABLES.md").write_text("\n".join(top + lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
