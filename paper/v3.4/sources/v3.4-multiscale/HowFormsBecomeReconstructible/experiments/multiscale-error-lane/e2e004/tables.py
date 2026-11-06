"""E2E004's tables: python -m e2e004.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json: the statement
candidates, the declared trade-off reading, the reported contrasts and the levels (q_r, u_r, u_v and a_r by lineage and
generation, overall and by item set). Every cell shows its coverage; a partial cell is marked, never pooled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e004 import design as D  # noqa: E402

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
    L = [f"# E2E004 tables: {S['stage']}", "",
         "Endpoints (e2e001.sim.score, unchanged): q_r SR001's history specificity; u_r and u_v the record's and the "
         "successor body's agreement inside the injury patch, relative to the sheet's own orientation; a_r whole-sheet "
         "inversion-invariant agreement. g 0 is the restored record at t = 8,000. Routes: body (the body's co-activity), "
         "vote (vote2r with a second copy), record (the record keeping itself, with parity), vote1 (vote2r, the second "
         "copy abstaining). Packets: protected (R0) and post (the injured record). Item sets: native / particular "
         "(li4 x F0) / permissive.", "",
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
    for key, title in (("trade_off", "every route run (the plan's declared reading)"),
                       ("trade_off_core", "AR001's three fixed policies, body, vote and record (added to the reader after P60's values)")):
        to = S.get(key, {})
        if not to:
            continue
        L += ["", f"## The trade-off reading (g 8), {title}: the route that keeps the most history heals the least", "",
              "| Set | q_r(protected) by route | u_r(post) by route | order by keeping (most first) | order by healing (least first) | reversed |",
              "|---|---|---|---|---|---|"]
        for name in ("particular", "all", "native", "permissive"):
            r = to.get(name)
            if r:
                L.append(f"| {name} | " + ", ".join(f"{k} {v:.3f}" for k, v in r["keep_q_r"].items()) + " | "
                         + ", ".join(f"{k} {v:.3f}" for k, v in r["heal_u_r"].items()) + f" | {' > '.join(r['order_by_keeping'])} | "
                         f"{' < '.join(r['order_by_healing_least_first'])} | {'yes' if r['reversed'] else 'no'} |")
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
    for e in ("q_r", "u_r", "u_v", "a_r"):
        L += ["", f"## Levels: {e} by lineage and generation (all; native / particular / permissive)", "",
              "| Lineage | g 0 | g 1 | g 3 | g 8 |", "|---|---|---|---|---|"]
        for lab in labels:
            cells = [cell(lev.get(f"{lab}|{e}|{g}")) for g in (0,) + D.HORIZONS]
            if any(cells):
                L.append(f"| {lab} | " + " | ".join(cells) + " |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
