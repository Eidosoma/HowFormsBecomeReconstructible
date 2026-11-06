"""SM005's tables: python -m sm005.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json (sm005.predict):
the parts, the shares of the late loss recovered, each reader's levels, and the parts by unit and by patch size."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm005 import design as D  # noqa: E402

iv = lambda v, ci, p=4: f"{v:+.{p}f} [{ci[0]:+.{p}f}, {ci[1]:+.{p}f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads((a.dir / "predictions_scored.json").read_text())
    R = S["reported"]
    L = [f"# SM005 tables: {S['stage']}", "", "Per refined condition read at full resolution: F = E_cg - E_base, V_X = E_X - E_base "
         "(X: C the coupling length, E the erasure size, B the record's bond grain); A = V_C + V_E + V_B - F.", "",
         "## The parts", "", "| Id | Part | Value [95%] | SD | Halves | Narrowest | Threshold | |", "|---|---|---|---|---|---|---|---|"]
    for p in S["parts"]:
        L.append(f"| {p['id']} | {p['part']} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} | {p['halves'][0]:+.4f}, "
                 f"{p['halves'][1]:+.4f} | {p['narrowest']} | {p.get('threshold', '')} | "
                 f"{('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} |")
    for sig in ("late", "prompt"):
        sh = R[f"shares_{sig}"]
        L += ["", f"## The shares of the {sig} recovery, V_X / F (F {sh['F']:+.4f} [{sh['F_ci95'][0]:+.4f}, {sh['F_ci95'][1]:+.4f}]; "
              f"read as ratios: {sh['ratio_read']})", "", "| Variant | Share [95%, whole-block bootstrap] |", "|---|---|"]
        L += [f"| {x} | {iv(sh[x]['share'], sh[x]['ci95'], 3)} |" for x in D.VARIANTS]
    L += ["", f"The prompt additivity A: {iv(R['additivity_prompt']['value'], R['additivity_prompt']['ci95'])}.", "",
          "Late less prompt, V_X: " + "; ".join(f"{x} {iv(v['value'], v['ci95'])}" for x, v in R["late_less_prompt"].items()) + ".",
          "", "## Each reader's levels (mean E, generic recovery, phase E - generic)", "",
          "| Reader | late E | late gen | late phase | prompt E | prompt gen | prompt phase |", "|---|---|---|---|---|---|---|"]
    for rd in D.READERS:
        a1, b1 = R["levels"]["late"][rd], R["levels"]["prompt"][rd]
        L.append(f"| {rd} | {a1['E']:.4f} | {a1['gen']:.4f} | {a1['phase']:+.4f} | {b1['E']:.4f} | {b1['gen']:.4f} | {b1['phase']:+.4f} |")
    for name, key in (("unit", "by_unit"), ("patch size", "by_size")):
        L += ["", f"## The late parts by {name}", "", "| " + name + " | L1 V_C | L2 V_E | L3 V_B | L4 F | L5 A |", "|---|---|---|---|---|---|"]
        for k, v in R[key].items():
            L.append(f"| {k} | " + " | ".join(f"{v[p]:+.4f}" for p in ("L1", "L2", "L3", "L4", "L5")) + " |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
