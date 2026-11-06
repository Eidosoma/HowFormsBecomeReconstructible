"""E2E006's tables: python -m e2e006.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json and
DIR/levels.json: the statement candidates, the realized exposures beside them, the reported contrasts, vtol's firings per
firing, and the levels (U_v, q_r, a_v and U by lineage and generation, with the field present where the row has one; the
fresh successors' U_v, q_r and a_v, field-free), overall and by item set. Every cell shows its coverage; a partial cell
is marked, never pooled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e006 import design as D  # noqa: E402

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
    lev = json.loads((a.dir / "levels.json").read_text())["levels"] if (a.dir / "levels.json").exists() else {}
    L = [f"# E2E006 tables: {'+'.join(S.get('merged_from') or [S['stage']])}", "",
         "Endpoints (e2e001.sim.score, unchanged, as E2E003 reads them): U_v the body's agreement on the union of every "
         "patch injured so far (present organization, with the field present where the row has one); q_r SR001's "
         "history specificity of the record; a_v whole-sheet agreement. The fresh successor (x) is a field-free newborn "
         "reading the outgoing record for one generation, never in the lineage. Item sets: native / particular "
         "(li4 x F0, read first) / permissive.", "",
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
    ex = S.get("exposures", {})
    if ex:
        L += ["", "## The realized exposures (beside the contrasts; the lead's ruling 5)", "",
              "x(t) is the exposure the response reads at update t; kappa x x integrated over the updates where the "
              "response acted, a generation (the reference: 8,000 for the full window, 4,000 for each half).", "",
              "| Row | g | mean x | x, updates 1-4,000 | x, 4,001-8,000 | integrated kappa x x |", "|---|---|---|---|---|---|"]
        for label, rows in ex.items():
            if label.endswith("_integrated"):
                continue
            for g, r in rows.items():
                L.append(f"| {label} | {g} | {r['exp_full']:.4f} | {r['exp_early']:.4f} | {r['exp_late']:.4f} | "
                         f"{r['integrated_kexp']:.0f} |")
        for key, words in (("early_over_late_integrated", "early / late"), ("matched_over_shared_integrated",
                           "vote/isolated-matched / vote/shared"), ("isolated_over_shared_integrated",
                           "vote/isolated / vote/shared")):
            if key in ex:
                L += ["", f"{words}, integrated kappa x exposure by generation: "
                      + ", ".join(f"g {g} {v:.3f}" for g, v in ex[key].items())]
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
    pf = S.get("per_firing", {})
    if pf:
        L += ["", "## vtol's firings, per firing", "", "| Row, generation | Firings | Lineage-cases | Zone in patch | Footprint in patch |",
              "|---|---|---|---|---|"]
        for k, r in pf.items():
            z, f = r["zone_in_patch_per_firing"], r["footprint_in_patch_per_firing"]
            L.append(f"| {k} | {r['firings']} | {r['lineage_cases']} | {'' if z is None else f'{z:.3f}'} | "
                     f"{'' if f is None else f'{f:.3f}'} |")
    labels = []
    for k in lev:
        lab = k.split("|")[0]
        if lab not in labels:
            labels.append(lab)
    for e in ("U_v", "q_r", "a_v", "U"):
        L += ["", f"## Levels: {e} by lineage and generation (all; native / particular / permissive)", "",
              "| Lineage | g 0 | g 1 | g 3 | g 8 |", "|---|---|---|---|---|"]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|{g}")) for g in (0,) + D.HORIZONS]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    for e in ("U_v", "q_r", "a_v"):
        L += ["", f"## The fresh successors: {e} after generation g, field-free (all; native / particular / permissive)",
              "", "| Lineage | after g 1 | after g 3 | after g 8 |", "|---|---|---|---|"]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|x{g}")) for g in D.FRESH_AT]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
