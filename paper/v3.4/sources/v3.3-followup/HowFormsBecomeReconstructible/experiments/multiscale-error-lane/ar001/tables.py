"""AR001's tables: python -m ar001.tables --root STAGE_ROOT --out TABLES.md

The statements; every arm's record inside the patch by scoring (pooled, t = 8,000) and its utility; the controller's
utility over the declared reliability grid against the best fixed policy; the sheet's cost of a sham; the side arms;
and the per-pair levels of the main arms.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar001 import analyze as Z  # noqa: E402
from ar001 import design as D  # noqa: E402
from ar001 import predict as PR  # noqa: E402

POINTS = ((1.0, 0.0), (0.9, 0.1), (0.75, 0.25), (0.5, 0.5), (1.0, 1.0), (0.0, 0.0), (0.9, 0.5), (0.5, 0.1))


def f4(x):
    return f"{x:+.4f}" if x < 0 else f"{x:.4f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = Z.load(a.root)
    m = Z.meta(data)
    bl = Z.blocks_of(data)
    L = [f"# AR001 tables ({m['purpose']}, blocks {bl[0]}-{bl[-1]}, design {m['design_digest'][:12]})", ""]
    S = PR.score(data)
    L += ["## Statements", "", "| Id | Verdict | Part | Pooled | Threshold |", "|---|---|---|---|---|"]
    for sid, s in S.items():
        for name, p in s["parts"].items():
            thr = "" if p["threshold"] is None else f"{p['sense']} {p['threshold']:g}"
            L.append(f"| {sid} | {s['verdict']} | {name} | {p['pooled']:+.6f} | {thr} |")
    L += ["", "## The record inside the patch by scoring (pooled, t = 8,000), and the utility U", ""]
    L += ["| Arm | " + " | ".join(D.SCORINGS) + " | U |", "|---" * (len(D.SCORINGS) + 2) + "|"]
    for arm in D.MAIN:
        L.append(f"| {arm} | " + " | ".join(f4(float(Z.u(data, arm, s).mean())) for s in D.SCORINGS)
                 + f" | {f4(float(Z.U(data, arm).mean()))} |")
    best, vals = Z.best_fixed(data)
    L += ["", f"Best fixed policy here: **{best}** (U {vals[best]:.4f}); P41's (registered): **{PR.BEST}**.", ""]
    L += ["## The controller over the declared reliability (U_ctrl(h, f) and its advantage)", "",
          "| h | f | U_ctrl | minus U(best here) | minus U(P41's best) |", "|---|---|---|---|---|"]
    for h, f in POINTS:
        uc = float(Z.U_ctrl(data, h, f).mean())
        L.append(f"| {h:g} | {f:g} | {uc:.4f} | {uc - vals[best]:+.4f} | {uc - vals[PR.BEST]:+.4f} |")
    L += ["", "## A sham's cost to the sheet (r_all(rest) - r_all(arm), t = 8,000)", "",
          "| Run | " + " | ".join(a_ for a_ in ("dial",) + D.TIMING + D.PRECISION) + " |",
          "|---" * (2 + len(D.TIMING + D.PRECISION)) + "|"]
    for run in ("none@0", "body@0", "shared@0", "cue@0", "change@0"):
        cells = []
        for a_ in ("dial",) + D.TIMING + D.PRECISION:
            cells.append(f4(float(Z.sham(data, run, a_).mean())) if a_ in Z.RUNARMS[run] else "")
        L.append(f"| {run} | " + " | ".join(cells) + " |")
    L += ["", "## Side arms: the record inside the patch (pooled, t = 8,000)", "",
          "| Scoring | rest | dial | " + " | ".join(D.TIMING + D.PRECISION) + " |", "|---" * (3 + len(D.TIMING + D.PRECISION)) + "|"]
    for s in D.SCORINGS:
        run, ep = Z.scoring_run(s)
        cells = [f4(float(Z.case(data, run, ep, a_).mean())) if a_ in Z.RUNARMS[run] else ""
                 for a_ in ("rest", "dial") + D.TIMING + D.PRECISION]
        L.append(f"| {s} | " + " | ".join(cells) + " |")
    L += ["", "## Misread cues (GC001, sigma 1): the cue readers inside the patch and over the sheet (t = 8,000)", "",
          "| Scoring | " + " | ".join(f"{a_} σ0 / σ1" for a_ in D.CUE_READERS) + " |", "|---" * 5 + "|"]
    for s in ("none", "memory", "change/new", "change/old"):
        run, ep = Z.scoring_run(s)
        run1 = run.replace("@0", "@1")
        L.append(f"| {s} | " + " | ".join(
            f"{float(Z.case(data, run, ep, a_).mean()):.4f} / {float(Z.case(data, run1, ep, a_).mean()):.4f}"
            for a_ in D.CUE_READERS) + " |")
    L.append("| none: sheet | " + " | ".join(
        f"{float(Z.case(data, 'none@0', 'r_all', a_).mean()):.4f} / {float(Z.case(data, 'none@1', 'r_all', a_).mean()):.4f}"
        for a_ in D.CUE_READERS) + " |")
    L += ["", "## Per unit-body pair: U and the record inside the patch at memory and correlated (t = 8,000)", "",
          "| Pair | " + " | ".join(f"U {a_}" for a_ in D.MAIN) + " |", "|---" * (len(D.MAIN) + 1) + "|"]
    for b, un in Z.PAIRS:
        L.append(f"| {un}/{b} | " + " | ".join(f"{float(Z.U(data, a_, pairs=((b, un),)).mean()):.4f}" for a_ in D.MAIN) + " |")
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out, a.out.stat().st_size, "B")


if __name__ == "__main__":
    main()
