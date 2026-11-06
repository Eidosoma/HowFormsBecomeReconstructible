"""E2E002's tables: python -m e2e002.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json: the statement
candidates, the reported contrasts, the levels (u_r, u_v and q_r by lineage and generation, overall and by item set) and
the detectors' diagnostics in every generation. Every cell shows its coverage; a partial cell is marked, never pooled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e002 import design as D  # noqa: E402

iv = lambda v, ci, p=4: f"{v:+.{p}f} [{ci[0]:+.{p}f}, {ci[1]:+.{p}f}]"
esc = lambda s: s.replace("|", "\\|")
SETS = tuple(D.ITEM_SETS)


def cell(rec, fmt=".3f"):
    if rec is None:
        return ""
    if "all" not in rec:
        return f"partial ({rec['tasks']} of {rec['of']} tasks)" if rec.get("partial") else ""
    return f"{rec['all']:{fmt}} ({' / '.join(format(rec[n], fmt) if n in rec else '-' for n in SETS)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads((a.dir / "predictions_scored.json").read_text())
    L = [f"# E2E002 tables: {S['stage']}", "",
         "Endpoints (e2e001.sim.score, unchanged): u_r and u_v the record's and the successor body's agreement inside the "
         "injury patch, relative to the sheet's own orientation; a_r whole-sheet inversion-invariant agreement; q_r "
         "SR001's history specificity. g 0 is the restored record at t = 8,000. 'every': vms in every successor; 'once': "
         "the vote's never-firing detector in every successor. Item sets: native / particular (li4 x F0) / permissive.", "",
         "## The statement candidates", "",
         "| Id | Part | Value [95%] | SD (block, case) | Halves | Narrowest | Threshold | | Tasks | Aliased | native | particular | permissive |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    al = S.get("aliased_tasks", {})
    for p in S["parts"]:
        if not p["available"]:
            L.append(f"| {p['id']} | {esc(p['part'])} | not available ({p['tasks']} of {p['of']} tasks) | | | | | | | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {esc(p['part'])} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} ({p['sd_block']:.4f}, "
                 f"{p['sd_case']:.4f}) | {p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {p['narrowest']} | "
                 f"{p.get('threshold', '')} | {('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} | "
                 f"{p['tasks']} of {p['of']} | {al.get(p['id'], '')} | "
                 + " | ".join(f"{bs[n]['value']:+.4f}" if n in bs else "" for n in SETS) + " |")
    L += ["", "## Reported contrasts", "", "| Id | Part | Value [95%] | Halves | Tasks | native | particular | permissive |",
          "|---|---|---|---|---|---|---|---|"]
    for p in S["reported"]:
        if not p["available"]:
            if p["tasks"]:
                L.append(f"| {p['id']} | {esc(p['part'])} | partial ({p['tasks']} of {p['of']} tasks) | | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {esc(p['part'])} | {iv(p['value'], p['ci95'])} | {p['halves'][0]:+.4f}, "
                 f"{p['halves'][1]:+.4f} | {p['tasks']} of {p['of']} | "
                 + " | ".join(f"{bs[n]:+.4f}" if n in bs else "" for n in SETS) + " |")
    lev = S["levels"]
    labels = []
    for k in lev:
        lab = k.split("|")[0]
        if lab not in labels:
            labels.append(lab)
    for e in ("u_r", "u_v", "q_r", "a_r"):
        L += ["", f"## Levels: {e} by lineage and generation (all; native / particular / permissive)", "",
              "| Lineage | g 0 | g 1 | g 3 | g 8 |", "|---|---|---|---|---|"]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|{g}")) for g in (0,) + D.HORIZONS]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    gens = range(1, D.G_MAIN + 1)
    for e, fmt, words in (("fired", ".3f", "the firing rate (share of branches whose detector fired)"),
                          ("det_fp", ".1f", "the footprint (cells; 0 where it did not fire)"),
                          ("det_fp_in", ".3f", "the footprint's share of the injury patch"),
                          ("committed_end", ".1f", "committed cells at the generation's end"),
                          ("cue_dis_birth", ".2f", "anchors disagreeing with the incoming record at birth")):
        L += ["", f"## Diagnostics: {words}, by generation (all; native / particular / permissive)", "",
              "| Lineage | " + " | ".join(f"g {g}" for g in gens) + " |", "|---|" + "---|" * len(gens)]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|d{g}"), fmt) for g in gens]
            if any(cells) and (e != "fired" or any(lev.get(f"{lab}|fired|d{g}", {}).get("all", 0) for g in gens)
                               or "vms" in lab):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
