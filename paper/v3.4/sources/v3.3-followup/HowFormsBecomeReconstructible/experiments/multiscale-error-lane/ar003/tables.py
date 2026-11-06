"""AR003's tables: python -m ar003.tables --res RESULTS_DIR  (reads the reader's JSON and predictions_scored.json,
writes TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def f(x, d=3):
    return "n/a" if x is None else f"{x:+.{d}f}"


def ci(c, d=4):
    return f"{c['mean']:+.{d}f} [{c['lo']:+.{d}f}, {c['hi']:+.{d}f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=Path, required=True)
    a = ap.parse_args()
    U = json.loads((a.res / "utilities.json").read_text())
    Dt = json.loads((a.res / "detectors.json").read_text())
    S = json.loads((a.res / "side_arms.json").read_text())
    P = json.loads((a.res / "predictions_scored.json").read_text()) if (a.res / "predictions_scored.json").exists() else {}
    out = ["# AR003 tables", "", "Intervals: 95% t over the blocks with the block SD (the registration's SD is the larger of "
           "that and the case-level SD over sqrt 8; the lead's check uses it).", ""]
    if P:
        out += ["## Registered statements", "", "| Id | Verdict | Part | Value | Threshold |", "|---|---|---|---|---|"]
        for sid, s in P.items():
            for nm, p in s["parts"].items():
                out.append(f"| {sid} | {s['verdict']} | {nm} | {p['pooled']:+.6f} | {p['sense']} {p['threshold']} |")
        out.append("")
    out += ["## Utilities by size", "", "| Arm | U_2 | U_4 | U_8 | U_mix |", "|---|---|---|---|---|"]
    for arm in ("vote", "det", "ms", "vms"):
        cells = [ci(U["U_L"][f"{arm}/L{L}"]) if f"{arm}/L{L}" in U["U_L"] else "not run" for L in (2, 4, 8)]
        cells.append(ci(U["U_mix"][arm]) if arm in U["U_mix"] else "n/a")
        out.append(f"| {arm} | " + " | ".join(cells) + " |")
    out += ["", "## Contrasts", "", "| Contrast | Value [95%] |", "|---|---|"]
    for k, c in U["contrasts"].items():
        out.append(f"| {k} | {ci(c)} |")
    out += ["", f"Shares of the declared signal's worth (vms, memory + correlated): "
            + ", ".join(f"{k} {v:.4f}" for k, v in U["share"].items())
            + "; by situation: " + ", ".join(f"{k} {v:.4f}" for k, v in U["share_by_situation"].items())
            + "; det (rest default) against the same: " + ", ".join(f"{k} {v:.4f}" for k, v in U["share_det_rest_default"].items()), ""]
    out += ["## u by scoring", "", "| Arm / size | " + " | ".join(["none", "body", "memory", "correlated", "shared", "cue",
                                                                      "change/new", "change/old"]) + " |",
            "|---|" + "---|" * 8]
    for k, row in U["u"].items():
        if isinstance(row, dict):
            out.append(f"| {k} | " + " | ".join(f"{row[s]:.3f}" if s in row else "-" for s in
                                                 ("none", "body", "memory", "correlated", "shared", "cue", "change/new",
                                                  "change/old")) + " |")
    out += ["", "vdial: " + ", ".join(f"{k} {v:.3f}" for k, v in U["u"].items() if not isinstance(v, dict) and v is not None), ""]
    out += ["## Detectors", "", "| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |",
            "|---|---|---|---|---|---|"]
    for k, d in Dt.items():
        out.append(f"| {k} | {d['p_fired']:.3f} | {d['p_located']:.3f} | {d['onset_median']} | "
                   f"{'n/a' if d['fp_cells_mean'] is None else round(d['fp_cells_mean'], 1)} | "
                   f"{'n/a' if d['patch_covered_mean'] is None else round(d['patch_covered_mean'], 3)} |")
    out += ["", "## Sheet costs against the vote", "", "| Run / arm | r_all(vote) - r_all(arm) |", "|---|---|"]
    for k, c in U["sham"].items():
        out.append(f"| {k} | {ci(c, 5)} |")
    out += ["", "## The misread side arm (sigma 1)", "", "| Quantity | Value [95%] |", "|---|---|"]
    for k, c in S.items():
        out.append(f"| {k} | {ci(c)} |")
    out += ["", "## U_4(vms) - U_4(vote), decomposed", "", "| Term | Value [95%] |", "|---|---|"]
    for k, c in U["gap_4"].items():
        out.append(f"| {k} | {ci(c)} |")
    (a.res / "TABLES.md").write_text("\n".join(out) + "\n")
    print("wrote", a.res / "TABLES.md")


if __name__ == "__main__":
    main()
