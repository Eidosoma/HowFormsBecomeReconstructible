"""AR005's tables: python -m ar005.tables --res RESULTS_DIR  (reads the reader's JSON and predictions_scored.json,
writes TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def ci(c, d=4):
    return f"{c['mean']:+.{d}f} [{c['lo']:+.{d}f}, {c['hi']:+.{d}f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=Path, required=True)
    a = ap.parse_args()
    U = json.loads((a.res / "utilities.json").read_text())
    Dt = json.loads((a.res / "detectors.json").read_text())
    P = json.loads((a.res / "predictions_scored.json").read_text()) if (a.res / "predictions_scored.json").exists() else {}
    out = ["# AR005 tables", "", "Intervals: 95% t over the blocks with the lane's SD, the larger of the block SD and the "
           "case-level SD over sqrt 8. Size means over 4 x 4 and 8 x 8.", ""]
    if P:
        out += ["## Registered statements", "", "| Id | Verdict | Part | Value | Threshold |", "|---|---|---|---|---|"]
        for sid, s in P.items():
            for nm, p in s["parts"].items():
                out.append(f"| {sid} | {s['verdict']} | {nm} | {p['pooled']:+.6f} | {p['sense']} {p['threshold']} |")
        out.append("")
    out += ["## Contrasts", "", "| Contrast | Value [95%] |", "|---|---|"]
    for k, c in U["contrasts"].items():
        out.append(f"| {k} | {ci(c)} |")
    rf = U["recovery_fraction"]
    out += ["", "The recovery fraction (R1 over vms's own misread loss, sizes 4 and 8): "
            + (", ".join(f"{k} {v:.4f}" for k, v in rf.items()) if rf else "n/a"), "",
            "## u by arm and run", "", "| Arm / run | u |", "|---|---|"]
    for k, v in U["u"].items():
        out.append(f"| {k} | {v:.4f} |")
    out += ["", "## Detectors", "", "| Run / arm | fired | on the patch | onset median | footprint cells | patch covered |",
            "|---|---|---|---|---|---|"]
    for k, d in Dt.items():
        out.append(f"| {k} | {d['p_fired']:.3f} | {d['p_located']:.3f} | {d['onset_median']} | "
                   f"{'n/a' if d['fp_cells_mean'] is None else round(d['fp_cells_mean'], 1)} | "
                   f"{'n/a' if d['patch_covered_mean'] is None else round(d['patch_covered_mean'], 3)} |")
    (a.res / "TABLES.md").write_text("\n".join(out) + "\n")
    print("wrote", a.res / "TABLES.md")


if __name__ == "__main__":
    main()
