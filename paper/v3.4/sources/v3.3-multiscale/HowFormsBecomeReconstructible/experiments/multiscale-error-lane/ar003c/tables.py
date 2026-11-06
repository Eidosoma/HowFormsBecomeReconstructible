"""AR003C's tables: python -m ar003c.tables --root STAGE_ROOT --out TABLES.md

The verdict and the criteria; the contrasts with design.INTERVAL's intervals (both SDs shown, the larger used); the
half-widths against their targets and the SDs against the development's; U by size and over the mix for the vote and
vms, U_8 of det; u by scoring; U_4(vms) - U_4(vote) in its terms; the rates, onset and footprint by run; the contrasts
per unit-body pair; the difference from the development.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar003c import analyze as AN  # noqa: E402
from ar003c import design as D  # noqa: E402
from ar003c import predict as PR  # noqa: E402


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
    L = [f"# AR003C tables ({S['purpose']}, {len(b)} blocks {b[0]}-{b[-1]}, tag {S['tag']}, design {S['design_digest'][:12]})", "",
         f"**Verdict: {S['verdict']}**" + (f" (failed: {', '.join(S['failed'])})" if S["failed"] else ""), "",
         f"Intervals: {D.INTERVAL}.", "", "| Criterion | Bound | Rule | Pass |", "|---|---|---|---|"]
    c = S["criteria"]
    L.append(f"| C1 U_mix(vms) - U_mix(vote) | lower {c['C1']['lower_bound']:+.4f} | > 0 | {c['C1']['pass']} |")
    L.append(f"| C2 U_8(vms) - U_8(det) | lower {c['C2']['lower_bound']:+.4f} | > 0 | {c['C2']['pass']} |")
    L.append(f"| C3 sheet cost, cue@0 | upper {c['C3']['upper_bound_cue']:+.5f} | <= 0.01 | {c['C3']['pass']} |")
    L.append(f"| C3 sheet cost, none@0 | upper {c['C3']['upper_bound_none']:+.5f} | <= 0.002 | {c['C3']['pass']} |")
    L += ["", "## The contrasts", "", "| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |",
          "|---|---|---|---|---|---|"]
    for k, name in (("c1", "U_mix(vms) - U_mix(vote)"), ("c2", "U_8(vms) - U_8(det)"),
                    ("sham_cue", "sheet cost r_all(vote) - r_all(vms), cue@0"), ("sham_none", "sheet cost, none@0")):
        i = I[k]
        L.append(f"| {name} | {iv(i, '+.5f')} | {i['half_width']:.5f} | {i['sd']:.5f} | {i['sd_block']:.5f} | {i['sd_case8']:.5f} |")
    L += ["", "| Contrast | Half-width | Target (a third of the development's value) | Within | SD / development SD |",
          "|---|---|---|---|---|"]
    for k in ("c1", "c2"):
        h, s = R["half_widths"][k], R["sd_against_development"][k]
        L.append(f"| {k} | {h['half_width']:.4f} | {h['target']:.4f} | {h['within']} | {s['ratio']:.3f} |")
    L += ["", "| Contrast | Confirmation | Development | Difference | z |", "|---|---|---|---|---|"]
    for k, v in R["against_development"].items():
        L.append(f"| {k} | {v['confirmation']:+.4f} | {v['development']:+.4f} | {v['difference']:+.4f} | {v['z']:+.2f} |")
    L += ["", "## Utilities", "", "| Arm | U_2 | U_4 | U_8 | U_mix |", "|---|---|---|---|---|"]
    for arm in (D.BEST, D.CONTROLLER):
        L.append(f"| {arm} | " + " | ".join(iv(R["U_L"][f"{arm}/L{s}"]) for s in D.SIZES) + f" | {iv(R['U_mix'][arm])} |")
    L.append(f"| det | not run | not run | {iv(R['U_L']['det/L8'])} | not run |")
    L += ["", "| Size contrast | Mean [95%] |", "|---|---|"] + [f"| {k} | {iv(v)} |" for k, v in R["size_contrasts"].items()]
    L += ["", "U_4(vms) - U_4(vote) in its terms: " + ", ".join(f"{k} {iv(v)}" for k, v in R["gap_4"].items()), "",
          "## u by scoring", "", "| Arm / size | " + " | ".join(D.SCORINGS) + " |", "|---|" + "---|" * len(D.SCORINGS)]
    for k, row in R["u"].items():
        L.append(f"| {k} | " + " | ".join(f"{row[s]:.3f}" if s in row else "-" for s in D.SCORINGS) + " |")
    L += ["", "## Rates, onset and footprint", "", "| Run / arm | fired | on the patch | onset median | patch covered |",
          "|---|---|---|---|---|"]
    for k, d in R["rates"].items():
        L.append(f"| {k} | {d['p_fired']:.3f} | {d['p_located']:.3f} | {d['onset_median']} | "
                 f"{'n/a' if d['patch_covered_mean'] is None else round(d['patch_covered_mean'], 3)} |")
    L += ["", "## Per unit-body pair", "", "| Pair | c1 | c2 | sham_cue | sham_none |", "|---|---|---|---|---|"]
    for k, v in R["pairs"].items():
        L.append(f"| {k} | {v['c1']:+.4f} | {v['c2']:+.4f} | {v['sham_cue']:+.5f} | {v['sham_none']:+.5f} |")
    L += ["", f"The information-limit identity: the largest abs(u(new) + u(old) - 1) over the change run's arms and cases is "
              f"{R['information_limit_max']:.3g}."]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
