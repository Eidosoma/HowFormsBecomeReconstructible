"""AR002's tables: python -m ar002.tables --root STAGE_ROOT --out TABLES.md

Every arm's u by scoring and U (pooled, t = 8,000), the detectors' rates, onsets and footprints by run, the utilities
(U_pred, U_loc, the price, the ceiling, the worth kept), the vote gap's decomposition, the sheet costs, the misread side
arm, the size side arm, and the registered parts with their verdicts.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar002 import analyze as Z  # noqa: E402
from ar002 import design as D  # noqa: E402
from ar002 import predict as PR  # noqa: E402


def f4(x):
    return "n/a" if x is None else f"{x:.4f}"


def iv(c, fmt="+.4f"):
    return f"{c['mean']:{fmt}} [{c['lo']:{fmt}}, {c['hi']:{fmt}}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = Z.load(a.root)
    m = Z.meta(data)
    runs = Z.runs_of(data)
    L = [f"# AR002 tables ({m['tag']}, digest {m['design_digest'][:12]}, blocks {Z.blocks_of(data)})", ""]
    arms = runs[D.run_name("none", 0.0)]
    dets = [x for x in arms if x in D.DET_ARMS]
    L += ["## u by scoring and U (pooled, t = 8,000)", "",
          "| Arm | " + " | ".join(D.SCORINGS) + " | U |", "|---" * (len(D.SCORINGS) + 2) + "|"]
    for arm in arms:
        L.append(f"| {arm} | " + " | ".join(f"{float(Z.u(data, arm, s).mean()):.3f}" for s in D.SCORINGS)
                 + f" | {float(Z.U(data, arm).mean()):.4f} |")
    L += ["", "## The detectors by run (lineage-cases)", "",
          "| Run | Arm | fired | on the patch | onset median | by 0.5 T* | footprint cells | patch covered | by cue | by body |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for key, d in Z.detectors(data).items():
        run, arm = key.rsplit("/", 1)
        L.append(f"| {run} | {arm} | {d['p_fired']:.3f} | {d['p_located']:.3f} | {d['onset_median']} | {d['by_half_t_star']:.3f} | "
                 f"{f4(d['fp_cells_mean'])} | {f4(d['patch_covered_mean'])} | {d['by_cue']:.3f} | {d['by_body']:.3f} |")
    ut = Z.utilities(data)
    L += ["", "## Utilities (95% intervals over blocks)", "", "| Quantity | " + " | ".join(dets) + " |",
          "|---" * (len(dets) + 1) + "|"]
    for q in ("U_minus_vote", "U_pred", "U_loc", "price", "price_loc", "h", "f"):
        L.append(f"| {q} | " + " | ".join(iv(ut[x][q]) for x in dets) + " |")
    for q in ("U_plane_at_hf", "worth_kept_vs_0.9_0.1", "worth_kept_vs_ceiling"):
        L.append(f"| {q} | " + " | ".join(f"{ut[x][q]:.4f}" for x in dets) + " |")
    L += ["", f"- U ceiling (a signal sent promptly over the patch: u(dial) on memory and correlated, u(rest) elsewhere): "
              f"{ut['U_ceiling']['mean']:.4f}; U_ctrl(0.9, 0.1): {ut['U_ctrl_0.9_0.1']['mean']:.4f}"
              + (f"; U(det) - U(det-v): {iv(ut['det_minus_det_v'])}" if "det_minus_det_v" in ut else ""), ""]
    L += ["## The vote gap, decomposed (weights 1/8; the terms sum to U(arm) - U(vote) exactly)", "",
          "| Arm | U(arm) - U(vote) | hits over the vote (memory, correlated) | default: the vote's advantage over rest "
          "given up (none, body, shared, cue) | false alarms (those four) | the pair | hits over rest | the vote over rest "
          "(memory, correlated) |", "|---|---|---|---|---|---|---|---|"]
    for key, g in ut["gap"].items():
        L.append(f"| {key} | {iv(g['total'])} | {iv(g['hits'])} | {iv(g['default'])} | {iv(g['false_alarms'])} | "
                 f"{g['pair']['mean']:+.6f} | {iv(g['hits_over_rest'])} | {iv(g['vote_over_rest_hits'])} |")
    vr = ut["gap"]["ceiling"]["vote_over_rest_by_scoring"]
    L += ["", "- u(vote) - u(rest) by scoring: " + ", ".join(f"{s} {vr[s]['mean']:+.3f}" for s in vr), ""]
    L += ["## Sheet costs r_all(rest) - r_all(arm)", "", "| Run | " + " | ".join(dets) + " |", "|---" * (len(dets) + 1) + "|"]
    for run in runs:
        L.append(f"| {run} | " + " | ".join(f"{ut[x]['sham'][run]['mean']:+.5f}" if run in ut[x]["sham"] else "n/a"
                                            for x in dets) + " |")
    L += ["", "## Misread side arm (sigma 1 less sigma 0)", "", "| Contrast | mean [95%] |", "|---|---|"]
    for k, v in Z.side_arms(data).items():
        L.append(f"| {k} | {iv(v)} |")
    sz = Z.sizes(data)
    if sz:
        L += ["", "## Size side arm (memory and correlated damage on L x L patches; t = 8,000)", "",
              "| Run | L | u: " + ", ".join(D.A1_ARMS) + " | dial's worth | detector | fired | on the patch | onset median | "
              "footprint cells | patch covered | its worth over rest |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for run, row in sz.items():
            base = (f"| {run} | {row['size']} | " + ", ".join(f"{row['u'][x]['mean']:.3f}" for x in D.A1_ARMS)
                    + f" | {iv(row['dial_worth'])} |")
            for x in (y for y in D.DET_ARMS if y in row):
                d = row[x]
                L.append(base + f" {x} (u {row['u'][x]['mean']:.3f}) | {d['p_fired']:.3f} | {d['p_located']:.3f} | "
                         f"{d['onset_median']} | {f4(d['fp_cells_mean'])} | {f4(d['patch_covered_mean'])} | {iv(d['worth'])} |")
    S = PR.score(data)
    L += ["", "## Registered parts", "", "| Statement | Part | Value | Threshold | Pass | Verdict |", "|---|---|---|---|---|---|"]
    for sid, s in S.items():
        for name, p in s["parts"].items():
            L.append(f"| {sid} | {name.split(' ', 1)[1]} | {p['pooled']:+.6f} | {p['sense']} {p['threshold']} | {p['pass']} | "
                     f"{s['verdict']} |")
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
