"""AR006C's tables: python -m ar006c.tables --root STAGE_ROOT --out TABLES.md

The verdict and the criteria; the contrasts with design.INTERVAL's intervals (both SDs shown, the larger used); both
halves; the SDs against the development's and the differences from the development with their z; vtol less vms under
cue@0, vms's own costs and vtol's give; R1 by size; u by arm and run; the rates, onsets and footprints by run; vtol's
branch against vms's; the contrasts per unit-body pair.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar006c import analyze as AN  # noqa: E402
from ar006c import design as D  # noqa: E402
from ar006c import predict as PR  # noqa: E402

NAMES = {"k1_cue": "K1 sheet cost r_all(vote) - r_all(vtol), cue@0", "k1_none": "K1 sheet cost, none@0",
         "k3a": "K3 (a) R1 = u(vtol) - u(vms), memory@1, sizes 4 and 8",
         "k5a": "K5 (a) u(vtol) - u(vms), correlated@0, 4 x 4",
         "vtol_less_vms_cue": "vtol less vms, sheet cost under cue@0 (reported)"}


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
    c = S["criteria"]
    L = [f"# AR006C tables ({S['purpose']}, {len(b)} blocks {b[0]}-{b[-1]}, tag {S['tag']}, design {S['design_digest'][:12]})",
         "", f"**Verdict: {S['verdict']}**" + (f" (failed: {', '.join(S['failed'])})" if S["failed"] else ""), "",
         f"Intervals: {D.INTERVAL}.", "", "| Criterion | Bound | Rule | Pass |", "|---|---|---|---|",
         f"| K1 sheet cost, cue@0 | upper {c['K1']['upper_bound_cue']:+.5f} | <= 0.01 | {c['K1']['pass']} |",
         f"| K1 sheet cost, none@0 | upper {c['K1']['upper_bound_none']:+.5f} | <= 0.002 | {c['K1']['pass']} |",
         f"| K3 (a) R1 | lower {c['K3a']['lower_bound']:+.4f} | >= 0.04 | {c['K3a']['pass']} |",
         f"| K5 (a) correlated@0 | lower {c['K5a']['lower_bound']:+.5f} | >= -0.005 | {c['K5a']['pass']} |",
         "", "## The contrasts", "", "| Contrast | Mean [95%] | Half-width | SD used | Block SD | Case SD / sqrt 8 |",
         "|---|---|---|---|---|---|"]
    IY = dict(I, vtol_less_vms_cue=R["vtol_less_vms_cue"])
    for k, i in IY.items():
        L.append(f"| {NAMES[k]} | {iv(i, '+.5f')} | {i['half_width']:.5f} | {i['sd']:.5f} | {i['sd_block']:.5f} | "
                 f"{i['sd_case8']:.5f} |")
    hb = R["halves"]["blocks"]
    L += ["", f"## Both halves (half 1: {hb[0][0]}-{hb[0][-1]}, half 2: {hb[1][0]}-{hb[1][-1]})" if hb[0] and hb[1]
          else "## Both halves", "", "| Contrast | Half 1 | Half 2 |", "|---|---|---|"]
    for k, v in R["halves"]["values"].items():
        L.append(f"| {NAMES[k]} | {iv(v['half1'], '+.5f')} | {iv(v['half2'], '+.5f')} |")
    L += ["", "## Against the development", "", "| Contrast | Confirmation | Development | Difference | z | SD / development SD |",
          "|---|---|---|---|---|---|"]
    for k, v in R["against_development"].items():
        L.append(f"| {NAMES[k]} | {v['confirmation']:+.5f} | {v['development']:+.5f} | {v['difference']:+.5f} | "
                 f"{v['z']:+.2f} | {R['sd_against_development'][k]['ratio']:.3f} |")
    L += ["", "## Reported beside the criteria", "", "| Quantity | Mean [95%] |", "|---|---|",
          f"| vms's sheet cost, cue@0 | {iv(R['sham_vms']['cue@0'], '+.5f')} |",
          f"| vms's sheet cost, none@0 | {iv(R['sham_vms']['none@0'], '+.5f')} |",
          f"| vtol's give inside the patch, cue@0 | {iv(R['give_cue'])} |"]
    L += [f"| R1 at {k[1:]} x {k[1:]} | {iv(v)} |" for k, v in R["R1_by_size"].items()]
    L += ["", "## u by arm and run", "", "| Run | " + " | ".join((D.BEST, "vms", D.CONTROLLER)) + " |", "|---|---|---|---|"]
    for run in D.RUNNAMES:
        L.append(f"| {run} | " + " | ".join(f"{R['u'][f'{a}/{run}']:.3f}" if f"{a}/{run}" in R["u"] else "" for a in
                                          (D.BEST, "vms", D.CONTROLLER)) + " |")
    L += ["", "## Rates, onset and footprint", "", "| Run / arm | fired | on the patch | onset median | patch covered |",
          "|---|---|---|---|---|"]
    for k, d in R["rates"].items():
        L.append(f"| {k} | {d['p_fired']:.3f} | {d['p_located']:.3f} | {d['onset_median']} | "
                 f"{'n/a' if d['patch_covered_mean'] is None else round(d['patch_covered_mean'], 3)} |")
    L += ["", "## vtol's branch against vms's (lineage-cases)", "", "| Run | n | never fired (the vote's) | vms's exactly | other |",
          "|---|---|---|---|---|"]
    for run, v in R["branches"].items():
        L.append(f"| {run} | {v['n']} | {v['vote']} | {v['vms']} | {v['other'] + v['vguard'] + v['not_compared']} |")
    L += ["", "## Per unit-body pair", "", "| Pair | k1_cue | k1_none | k3a | k5a |", "|---|---|---|---|---|"]
    for k, v in R["pairs"].items():
        L.append(f"| {k} | {v['k1_cue']:+.5f} | {v['k1_none']:+.5f} | {v['k3a']:+.4f} | {v['k5a']:+.5f} |")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
