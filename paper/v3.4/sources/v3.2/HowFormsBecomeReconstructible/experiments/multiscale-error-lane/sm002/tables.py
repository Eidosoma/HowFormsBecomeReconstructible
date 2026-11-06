"""SM002's tables: python -m sm002.tables --root ROOT --stage STAGE --dir OUT_DIR -> OUT_DIR/TABLES.md

The scored statements; every reported contrast; and every condition's pooled endpoints under both readers beside its
twin's (refined) and the episode's own patch agreement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm002 import analyze as A  # noqa: E402


def part_rows(scored):
    out = []
    for sid, st in scored.items():
        for name, p in st["parts"].items():
            out.append(f"| {sid} | {st['verdict']} | {name} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | "
                       f"{p['sense']} {p['threshold']:+} | {p['sd']:.4f} | {p['margin']:.2f} | "
                       f"{', '.join(f'{h:+.4f}' for h in p['halves'])} |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    scored = json.loads((a.dir / "predictions_scored.json").read_text())
    rj = json.loads((a.dir / "reported.json").read_text())
    rep, sm = rj["parts"], rj["summary"]
    pairs = A.stage_pairs(a.stage, a.root)
    Z, _ = A.load(a.root, pairs)
    rows = A.attach_twins(A.conditions(Z, pairs))
    L = [f"# SM002 tables ({a.stage}, {len(pairs)} tasks)", "", "## Registered statements", "",
         "| Id | Verdict | Part | Value [95%] | Rule | SD | Margin (SD) | Halves |", "|---|---|---|---|---|---|---|---|",
         *part_rows(scored), "",
         f"T2 leaves {sm['T2_over_T1']:+.3f} of T1's loss (T2 / T1; <= 0 where none remains), its 95% interval's bounds "
         f"{sm['T2_ci95_over_T1'][0]:+.3f} to {sm['T2_ci95_over_T1'][1]:+.3f}.", "",
         "## Reported contrasts", "", "| Contrast | Value [95%] | SD (block, case) | Halves |", "|---|---|---|---|"]
    for name, p in rep.items():
        L.append(f"| {name} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {p['sd']:.4f} "
                 f"({p['sd4']:.4f}, {p['sdc']:.4f}) | {', '.join(f'{h:+.4f}' for h in p['halves'])} |")
    L += ["", "## Conditions (pooled over blocks and cases; 3 decimals)", "",
          "| Unit | L | Arm | x2 | E_u | E_cg | twin E_u | r_in | twin r_in | gen_u | gen_cg | E_u ctrl | E_cg ctrl | ties |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    f3 = lambda x: f"{x.mean():.3f}"                                       # noqa: E731
    for r in rows:
        t = r["twin"]
        L.append(f"| {r['unit']} | {r['L']} | {r['arm']} | {r['x2']:.3f} | {f3(r['E_u'])} | {f3(r['E_cg'])} | "
                 f"{f3(t['E_u']) if t else ''} | {f3(r['r_in'])} | {f3(t['r_in']) if t else ''} | {f3(r['gen_u'])} | "
                 f"{f3(r['gen_cg'])} | {f3(r['E_u_ctrl'])} | {f3(r['E_cg_ctrl'])} | {r['ties'].mean():.1f} |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"wrote {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
