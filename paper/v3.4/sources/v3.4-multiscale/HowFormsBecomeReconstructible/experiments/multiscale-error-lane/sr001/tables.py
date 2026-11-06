"""SR001's tables from the reader's outputs: python -m sr001.tables [--out DIR]  (writes DIR/TABLES.md)

The verdicts and parts; per body and unit, the record's inversion-invariant agreement a and history specificity q after
the 1st, 4th and 16th renewal for every route; the record's spacing after the 16th; and the fresh recipients' q and its
gain over the paired no-record control.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sr001 import design as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sr001")
    a = ap.parse_args()
    C = json.loads((a.out / "curves.json").read_text())
    R = json.loads((a.out / "recipients.json").read_text())
    S = json.loads((a.out / "predictions_scored.json").read_text())
    lines = [f"# SR001 tables ({C['stage']}, blocks {C['blocks'][0]}-{C['blocks'][1] - 1}, design {C['design_digest'][:12]})", ""]
    lines += ["## Statements", "", "| Id | Verdict | Part | Pooled |", "|---|---|---|---|"]
    for k, v in S.items():
        for name, p in v["parts"].items():
            lines.append(f"| {k} | {v['verdict']} | {name} | {p['pooled']:+.4f} |")
    for body in C["bodies"]:
        for unit in C["units"]:
            cur = C["curves"][body][unit]
            lines += ["", f"## {body} x {unit}: the record after renewals G1 / G4 / G16", "",
                      "| Route | a G1 | a G4 | a G16 | q G1 | q G4 | q G16 | spacing G16 | body a G16 |",
                      "|---|---|---|---|---|---|---|---|---|"]
            for route in C["routes"]:
                c = cur[route]
                lines.append(f"| {route} | {c['a_r'][0]:.3f} | {c['a_r'][3]:.3f} | {c['a_r'][-1]:.3f} | {c['q_r'][0]:+.3f} | "
                             f"{c['q_r'][3]:+.3f} | {c['q_r'][-1]:+.3f} | {c['spacing_r'][-1]:.1f} | {c['a_v'][-1]:.3f} |")
            rec = R["recipients"][body][unit]
            lines += ["", f"Fresh recipients reading the G16 record (q, and its gain over the no-record control):", "",
                      "| Route | " + " | ".join(f"{RB} q (gain)" for RB in C["recipients"]) + " |",
                      "|---|" + "---|" * len(C["recipients"])]
            for br in C["routes"] + ["none"]:
                lines.append(f"| {br} | " + " | ".join(f"{rec[RB][br]['rq']:+.3f} ({rec[RB][br]['rq_gain']:+.3f})"
                                                       for RB in C["recipients"]) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
