"""E2E003's tables: python -m e2e003.tables --scored PREDICTIONS_SCORED_JSON --out TABLES.md

The statement candidates J1-J5 (value, 95% interval, SD, halves, the rule's narrowest threshold; the registered threshold
and verdict where one is set), by item set with li4 x F0 (the particular set) first; the reported contrasts; every
lineage's U, u_r on its own patch, a_r and q_r at generations 0-8; the controllers' firing in every generation; the
aliases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SETS = ("particular", "native", "permissive")
LEVELS = ("U", "u_r", "a_r", "q_r")


def f4(x):
    return "n/a" if x is None else f"{x:+.4f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads(a.scored.read_text())
    L = [f"# E2E003 tables ({S['stage']}, design {S['design_digest'][:12]})", "",
         "Parts pooled per case over the eight unit-body pairs, a block the mean of its cases, the part the mean over the "
         "blocks; SD = max(block SD, case SD / sqrt(cases a block)); 95% t over the blocks.", "",
         "## The statement candidates", "",
         "| Id | Kind | Value [95%] | SD | Halves | Narrowest | Registers | Threshold | Verdict | li4 x F0 | li4 x S4 | dw |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in S["parts"]:
        if not p.get("available"):
            L.append(f"| {p['id']} | {p['kind']} | not available ({p['tasks']} of {p['of']} tasks) | | | | | | | | | |")
            continue
        bs = p.get("by_item_set", {})
        L.append(f"| {p['id']} | {p['kind']} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {p['sd']:.4f} | "
                 f"{p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {p['narrowest']} | {p['registers_at_narrowest']} | "
                 f"{p.get('threshold', '')} | {('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} | "
                 + " | ".join(f4(bs.get(s, {}).get("value")) for s in SETS) + " |")
    L += ["", "Parts' words: " + "; ".join(f"{p['id']} {p['part']}" for p in S["parts"]), "",
          f"Aliased tasks per part (the two lineages on one row): {S['aliased_tasks']}", "",
          "## Reported contrasts", "", "| Id | Value [95%] | Halves | li4 x F0 |", "|---|---|---|---|"]
    for r in S["reported"]:
        if not r.get("available"):
            continue
        L.append(f"| {r['id']} | {r['value']:+.4f} [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] | {r['halves'][0]:+.4f}, "
                 f"{r['halves'][1]:+.4f} | {f4(r['by_item_set'].get('particular'))} |")
    lev = S["levels"]
    labels = sorted({k.split("|")[0] for k in lev})
    gens = sorted({int(k.split("|")[2]) for k in lev if k.split("|")[2].isdigit()})
    for e in LEVELS:
        L += ["", f"## {e} by lineage and generation (all pairs; li4 x F0 in brackets)", "",
              "| Lineage | " + " | ".join(f"g {g}" for g in gens) + " |", "|---|" + "---|" * len(gens)]
        for lab in labels:
            cells = []
            for g in gens:
                rec = lev.get(f"{lab}|{e}|{g}")
                cells.append("" if rec is None or "all" not in rec else
                             f"{rec['all']:.3f} ({rec['particular']:.3f})" if "particular" in rec else f"{rec['all']:.3f}")
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
    dgen = sorted({int(k.split("|")[2][1:]) for k in lev if k.split("|")[2].startswith("d")})
    L += ["", "## The controllers' firing in every generation (share of lineage-cases)", "",
          "| Lineage | " + " | ".join(f"g {g}" for g in dgen) + " |", "|---|" + "---|" * len(dgen)]
    for lab in labels:
        cells = [lev.get(f"{lab}|fired|d{g}", {}).get("all") for g in dgen]
        if any(c is not None for c in cells):
            L.append(f"| {lab} | " + " | ".join("" if c is None else f"{c:.3f}" for c in cells) + " |")
    on = S.get("onsets", {})
    if on:
        L += ["", "## The controllers' onsets in every generation (reported; the lead's ruling 6)", "",
              "Pooled shares of lineage-cases firing at update 1 / later / never; the later onsets' quartiles over every "
              "lineage-case.", "", "| Lineage | Generation | at update 1 | later | never | later onsets (25%, 50%, 75%) |",
              "|---|---|---|---|---|---|"]
        for key in sorted(on, key=lambda k: (k.split("|")[0], int(k.split("|")[1][1:]))):
            r = on[key]
            lab, g = key.split("|")
            sh = [r[w].get("all") for w in ("at1", "later", "never")]
            q = r["later_quartiles"]
            L.append(f"| {lab} | {g[1:]} | " + " | ".join("" if x is None else f"{x:.3f}" for x in sh) + " | "
                     + ("" if q is None else ", ".join(f"{x:.0f}" for x in q)) + " |")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
