"""AR004's tables: python -m ar004.tables --res RESULTS_DIR  (reads the reader's JSON and predictions_scored.json,
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
    out = ["# AR004 tables", "", "Intervals: 95% t over the blocks with the block SD (the registration's SD is the larger of "
           "that and the case-level SD over sqrt 8; the lead's check uses it).", ""]
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
    out += ["", f"The recovery fraction (R1 over vms's own misread loss, pooled over the sizes): "
                f"{'n/a' if rf is None else round(rf, 4)}; by size: "
            + ", ".join(f"{k} {'n/a' if v is None else round(v, 4)}" for k, v in U["recovery_fraction_by_size"].items()), "",
            "## u by arm and run", "", "| Arm / run | u |", "|---|---|"]
    for k, v in U["u"].items():
        out.append(f"| {k} | {v:.4f} |")
    if U.get("side_arm_6x6"):
        s = U["side_arm_6x6"]
        out += ["", "## The 6 x 6 side arm (reported)", "", "| Quantity | Value |", "|---|---|"]
        out += [f"| u {k} | {v:.4f} |" for k, v in s["u"].items()]
        out += [f"| R1 at 6 x 6 | {ci(s['R1 at L6'])} |", f"| R0 at 6 x 6 | {ci(s['R0 at L6'])} |",
                f"| recovery fraction at 6 x 6 | {'n/a' if s['recovery_fraction_L6'] is None else round(s['recovery_fraction_L6'], 4)} |"]
        out += [f"| located {k} | {v:.3f} |" for k, v in s["located"].items()]
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
