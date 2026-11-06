"""AR002C's tables: python -m ar002c.tables --root STAGE_ROOT --out TABLES.md

The verdict and the criteria; the contrasts with design.INTERVAL's intervals (both SDs shown, the larger used); the
half-widths against their targets and the SDs against the development's; every arm's u by scoring and U; U_pred, U_loc,
the price, the ceiling and the worth kept; det's rates, onset and footprint by run; the vote-gap terms; (a) and (b) per
unit-body pair; the difference from the development.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar002c import analyze as AN  # noqa: E402
from ar002c import design as D  # noqa: E402
from ar002c import predict as PR  # noqa: E402


def iv(c, fmt="+.4f"):
    return f"{c['mean']:{fmt}} [{c['lo']:{fmt}}, {c['hi']:{fmt}}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = AN.load(a.root)
    S = PR.score(Z)
    I, R = AN.reported(Z)
    b = S["blocks"]
    L = [f"# AR002C tables ({S['purpose']}, {len(b)} blocks {b[0]}-{b[-1]}, tag {S['tag']}, design {S['design_digest'][:12]})", "",
         f"**Verdict: {S['verdict']}**" + (f" (failed: {', '.join(S['failed'])})" if S["failed"] else ""), "",
         f"Intervals: {D.INTERVAL}.", "", "| Criterion | Bound | Rule | Pass |", "|---|---|---|---|"]
    c = S["criteria"]
    L.append(f"| C1 (a) U(det) - U(vote) | lower {c['C1']['lower_bound']:+.4f} | > 0 | {c['C1']['pass']} |")
    L.append(f"| C2 (b) (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2 | lower {c['C2']['lower_bound']:+.4f} | > 0 | "
             f"{c['C2']['pass']} |")
    L.append(f"| C3 sheet cost, cue@0 | upper {c['C3']['upper_bound_cue']:+.4f} | <= 0.01 | {c['C3']['pass']} |")
    L.append(f"| C3 sheet cost, none@0 | upper {c['C3']['upper_bound_none']:+.4f} | <= 0.002 | {c['C3']['pass']} |")
    L += ["", "## The contrasts", "", "| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |",
          "|---|---|---|---|---|---|"]
    for k, name in (("a", "(a) U(det) - U(vote)"), ("b", "(b) kept half the declared worth"),
                    ("sham_cue", "sheet cost r_all(rest) - r_all(det), cue@0"), ("sham_none", "sheet cost, none@0")):
        i = I[k]
        L.append(f"| {name} | {iv(i)} | {i['half_width']:.4f} | {i['sd']:.4f} | {i['sd_block']:.4f} | {i['sd_case8']:.4f} |")
    hw, sd, dv = R["half_widths"], R["sd_against_development"], R["against_development"]
    L += ["", "- Half-widths against their targets (a third of the development values): "
          + "; ".join(f"({k}) {v['half_width']:.4f} against {v['target']:.4f}" for k, v in hw.items()),
          "- SDs against the development's: " + "; ".join(f"({k}) {v['sd']:.4f} against {v['dev_sd']:.4f} (x{v['ratio']:.2f})"
                                                          for k, v in sd.items()),
          "- Against the development: " + "; ".join(f"({k}) {v['confirmation']:+.4f} against {v['development']:+.4f}, "
                                                    f"{v['difference']:+.4f} (z {v['z']:+.2f})" for k, v in dv.items()), ""]
    L += ["## Every arm by scoring (pooled, t = 8,000)", "", "| Arm | " + " | ".join(D.SCORINGS) + " | U |",
          "|---" * (len(D.SCORINGS) + 2) + "|"]
    for arm, us in R["u"].items():
        L.append(f"| {arm} | " + " | ".join(f"{us[s]:.3f}" for s in D.SCORINGS) + f" | {iv(R['U'][arm])} |")
    L += ["", "## The detector's worth", "",
          f"- U_pred(det) {iv(R['U_pred'])}; U_loc {iv(R['U_loc'])}; the price U(det) - U_pred {iv(R['price'])}",
          f"- U_ceiling {iv(R['U_ceiling'])}; U(det) - U_ceiling {iv(R['det_minus_ceiling'])}; U_ctrl(0.9, 0.1) "
          f"{iv(R['U_ctrl_0.9_0.1'])}",
          f"- the worth kept: {R['worth_kept_vs_0.9_0.1']:.3f} of the declared (0.9, 0.1) signal's, "
          f"{R['worth_kept_vs_ceiling']:.3f} of the ceiling's", "",
          "## det by run (lineage-cases)", "",
          "| Run | fired [95%] | on the patch [95%] | onset median | by 0.5 T* | footprint cells | patch covered |",
          "|---|---|---|---|---|---|---|"]
    for run, d in R["rates"].items():
        fp = "n/a" if d["fp_cells_mean"] is None else f"{d['fp_cells_mean']:.1f}"
        cov = "n/a" if d["patch_covered_mean"] is None else f"{d['patch_covered_mean']:.3f}"
        L.append(f"| {run} | {iv(d['p_fired_ci'], '.3f')} | {iv(d['p_located_ci'], '.3f')} | {d['onset_median']} | "
                 f"{d['by_half_t_star']:.3f} | {fp} | {cov} |")
    L += ["", "## The vote gap, decomposed (weights 1/8; the terms sum to the total exactly)", "",
          "| | total | hits over the vote | the vote's advantage given up | false alarms | the pair |", "|---|---|---|---|---|---|"]
    for name, g in R["gap"].items():
        L.append(f"| {name} | {iv(g['total'])} | {iv(g['hits'])} | {iv(g['default'])} | {iv(g['false_alarms'])} | "
                 f"{g['pair']['mean']:+.6f} |")
    L += ["", "## Per unit-body pair", "", "| Pair | (a) | (b) | sheet cost cue | sheet cost none |", "|---|---|---|---|---|"]
    for p, v in R["pairs"].items():
        L.append(f"| {p} | {v['a']:+.4f} | {v['b']:+.4f} | {v['sham_cue']:+.5f} | {v['sham_none']:+.5f} |")
    L += ["", f"- The information-limit identity: the largest abs(u(new) + u(old) - 1) over every arm and case is "
              f"{R['information_limit_max']:.1e}."]
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
