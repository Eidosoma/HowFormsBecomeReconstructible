"""E2E001's tables: python -m e2e001.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json: the statement
candidates, the reported contrasts and the levels (u_r and u_v by label and generation, overall and by item set)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e001 import design as D  # noqa: E402
from e2e001 import predict as PR  # noqa: E402

iv = lambda v, ci, p=4: f"{v:+.{p}f} [{ci[0]:+.{p}f}, {ci[1]:+.{p}f}]"
esc = lambda s: s.replace("|", "\\|")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads((a.dir / "predictions_scored.json").read_text())
    L = [f"# E2E001 tables: {S['stage']}", "",
         "Endpoints (e2e001.sim.score): u_r and u_v the record's and the successor body's agreement inside the injury patch, "
         "relative to the sheet's own orientation; a_r whole-sheet inversion-invariant agreement; q_r SR001's history "
         "specificity. g 0 is the restored record at t = 8,000. 'unint' is the uninterrupted, approximate control.", "",
         "## The statement candidates", "",
         "| Id | Part | Value [95%] | SD (block, case/√8) | Halves | Narrowest | Threshold | | native | particular | permissive |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in S["parts"]:
        if not p["available"]:
            L.append(f"| {p['id']} | {esc(p['part'])} | not available on this stage | | | | | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {esc(p['part'])} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} ({p['sd_block']:.4f}, "
                 f"{p['sd_case8']:.4f}) | {p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {p['narrowest']} | "
                 f"{p.get('threshold', '')} | {('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} | "
                 + " | ".join(f"{bs[n]['value']:+.4f}" if n in bs else "" for n in D.ITEM_SETS) + " |")
    L += ["", "## Reported contrasts", "", "| Id | Part | Value [95%] | Halves | native | particular | permissive |",
          "|---|---|---|---|---|---|---|"]
    for p in S["reported"]:
        if not p["available"]:
            L.append(f"| {p['id']} | {esc(p['part'])} | not available on this stage | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {esc(p['part'])} | {iv(p['value'], p['ci95'])} | {p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | "
                 + " | ".join(f"{bs[n]:+.4f}" if n in bs else "" for n in D.ITEM_SETS) + " |")
    lev = S["levels"]
    for e in ("u_r", "u_v", "q_r"):
        L += ["", f"## Levels: {e} by label and generation (all; native / particular / permissive)", "",
              "| Label | g 0 | g 1 | g 3 | g 8 |", "|---|---|---|---|---|"]
        for label in PR.LEVEL_LABELS:
            cells = []
            for g in (0, 1, 3, 8):
                rec = lev.get(f"{label}|{e}|{g}")
                cells.append("" if rec is None else f"{rec['all']:.3f} ({' / '.join(format(rec[n], '.3f') if n in rec else '-' for n in D.ITEM_SETS)})")
            if any(cells):
                L.append(f"| {label} | " + " | ".join(cells) + " |")
    if S.get("futures_spread"):
        L += ["", "## The futures' spread (u_r at g 8, memory@0: the mean over cases of the SD across futures)", ""]
        L += [f"- {k}: {'' if v is None else format(v, '.4f')}" for k, v in S["futures_spread"].items()]
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
