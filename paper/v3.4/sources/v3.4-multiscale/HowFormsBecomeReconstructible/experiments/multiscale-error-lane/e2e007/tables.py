"""E2E007's tables: python -m e2e007.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json and
DIR/levels.json: the statement candidates, the realized exposures beside them, the reported contrasts, the observer (the
body's agreement with its record on the generation's patch around the body injury), and the levels (U_v, q_r, a_v and U by
row and generation, with the field present where the row has one; the fresh successors' U_v, q_r and a_v, field-free),
overall and by item set. Every cell shows its coverage; a partial cell is marked, never pooled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e007 import design as D  # noqa: E402

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
    stage = S["stage"]
    fresh_at = D.STAGE_FRESH_AT.get(stage, D.FRESH_AT)
    L = [f"# E2E007 tables: {'+'.join(S.get('merged_from') or [stage])}", "",
         "Rows: the response {none; raise = the reading gain x (1 + kappa x), E2E006's; relax = gain / (1 + kappa x)} x "
         "the injury's target {memory: the generation's patch flipped in the incoming record at update 0, E2E003's; body: "
         f"the same patch flipped in the newborn's V and E at update {D.t_body()}, the record untouched}}. Endpoints "
         "(e2e001.sim.score, unchanged, as E2E003 and E2E006 read them): U_v the body's agreement on the union of every "
         "patch injured so far (present organization, the field present where the row has one); q_r SR001's history "
         "specificity of the record; a_v whole-sheet agreement. The fresh successor (x) is a field-free newborn reading the "
         "outgoing record for one generation, never in the lineage. Item sets: native / particular (li4 x F0, read first) "
         "/ permissive.", "",
         "## The statement candidates", "",
         "| Id | Part | Value [95%] | SD (block, case) | Halves | Narrowest | Registers | Band (a null) | Threshold | | Tasks | native | particular | permissive |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in S["parts"]:
        if not p["available"]:
            L.append(f"| {p['id']} | {esc(p['part'])} | not available ({p['tasks']} of {p['of']} tasks) | | | | | | | | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {esc(p['part'])} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} ({p['sd_block']:.4f}, "
                 f"{p['sd_case']:.4f}) | {p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {p['narrowest']} | "
                 f"{p['registers_at_narrowest']} | {p.get('narrowest_band', '')} | {p.get('threshold', '')} | "
                 f"{('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} | {p['tasks']} of {p['of']} | "
                 + " | ".join(f"{bs[n]['value']:+.4f}" if n in bs else "" for n in SETS) + " |")
    L += ["", f"Aliased tasks (two compared labels on one row): {S.get('aliased_tasks', {})}"]
    ex = S.get("exposures", {})
    if ex:
        L += ["", "## The realized exposures", "",
              "x(t) is the exposure the response reads at update t; kappa x x summed over the generation (the response acts "
              "in every update). raise and relax read the same kind of exposure; their bodies differ, so their exposures "
              "differ.", "",
              "| Row | g | mean x | x, updates 1-4,000 | x, 4,001-8,000 | integrated kappa x x |", "|---|---|---|---|---|---|"]
        for label, rows in ex.items():
            if label.endswith("_integrated"):
                continue
            for g, r in rows.items():
                L.append(f"| {label} | {g} | {r['exp_full']:.4f} | {r['exp_early']:.4f} | {r['exp_late']:.4f} | "
                         f"{r['integrated_kexp']:.0f} |")
        for key, words in (("relax_over_raise_memory_integrated", "relax/memory over raise/memory"),
                           ("relax_over_raise_body_integrated", "relax/body over raise/body"),
                           ("matched_over_raise_memory_integrated", "relax-matched/memory over raise/memory")):
            if key in ex:
                L += ["", f"{words}, integrated kappa x exposure by generation: "
                      + ", ".join(f"g {g} {v:.3f}" for g, v in ex[key].items())]
    labels = []
    for k in lev:
        lab = k.split("|")[0]
        if lab not in labels:
            labels.append(lab)
    gens = sorted({int(k.split("|")[2][1:]) for k in lev if k.split("|")[2].startswith("d")})
    ou = D.obs_updates()
    L += ["", "## The observer: the body's agreement with its own record on the generation's patch (output only)", "",
          "The share of the patch's cells where sign V = sign r, after the body step of the update shown (the body injury "
          f"just before update {D.t_body()}'s body step). All; native / particular / permissive.", "",
          "| Row | g | " + " | ".join(f"{o} ({ou[o]})" for o in D.OBS) + " |", "|---|---|" + "---|" * len(D.OBS)]
    for lab in labels:
        for g in gens:
            cells = [cell(lev.get(f"{lab}|agree_{o}|d{g}")) for o in D.OBS]
            if any(cells):
                L.append(f"| {lab} | {g} | " + " | ".join(cells) + " |")
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
    for e in ("U_v", "q_r", "a_v", "U"):
        L += ["", f"## Levels: {e} by row and generation (all; native / particular / permissive)", "",
              "| Row | g 0 | g 1 | g 3 | g 8 |", "|---|---|---|---|---|"]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|{g}")) for g in (0,) + D.HORIZONS]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    for e in ("U_v", "q_r", "a_v"):
        L += ["", f"## The fresh successors: {e} after generation g, field-free (all; native / particular / permissive)",
              "", "| Row | " + " | ".join(f"after g {g}" for g in fresh_at) + " |", "|---|" + "---|" * len(fresh_at)]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|x{g}")) for g in fresh_at]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L += ["", "## The injury checks (share of lineage-cases where the injury flipped exactly its patch)", "",
          "| Row | " + " | ".join(f"g {g}" for g in gens) + " |", "|---|" + "---|" * len(gens)]
    for lab in labels:
        cells = [cell(lev.get(f"{lab}|injury_ok|d{g}")) for g in gens]
        if any(cells):
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
