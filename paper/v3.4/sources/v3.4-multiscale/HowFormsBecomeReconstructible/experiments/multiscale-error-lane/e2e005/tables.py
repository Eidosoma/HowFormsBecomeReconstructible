"""E2E005's tables: python -m e2e005.tables --dir DIR  ->  DIR/TABLES.md, from DIR/predictions_scored.json: the statement
candidates, the declared frontier reading (the points, F against the fixed rules' line and against the record-body chord,
the normalized coordinates), the reported contrasts, the switch's figures per firing, the costs over the lineages that
fired, and the levels (q_r, u_r, u_v and a_r by lineage and generation, overall and by item set). Every cell shows its
coverage; a partial cell is marked, never pooled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e005 import design as D  # noqa: E402

iv = lambda v, ci, p=4: f"{v:+.{p}f} [{ci[0]:+.{p}f}, {ci[1]:+.{p}f}]"
esc = lambda s: s.replace("|", "\\|")
SETS = tuple(D.ITEM_SETS)
ORDER = ("particular", "all", "native", "permissive")


def cell(rec, fmt=".3f"):
    if rec is None:
        return ""
    if "all" not in rec:
        return f"partial ({rec['tasks']} of {rec['of']} tasks)" if rec.get("partial") else ""
    return f"{rec['all']:{fmt}} ({' / '.join(format(rec[n], fmt) if n in rec else '-' for n in SETS)})"


def opt(x, fmt="+.3f"):
    return "-" if x is None else format(x, fmt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads((a.dir / "predictions_scored.json").read_text())
    L = [f"# E2E005 tables: {S['stage']}", "",
         f"The controller's detector: {S.get('detector')}. Endpoints (e2e001.sim.score, unchanged): q_r SR001's history "
         "specificity (keeping, read on protected storage); u_r and u_v the record's and the successor body's agreement "
         "inside the injury patch, relative to the sheet's own orientation (healing, read on post-damage copying); a_r "
         "whole-sheet inversion-invariant agreement. g 0 is the restored record at t = 8,000. Rules: ctl (the controller: "
         "the record rule by default, the body rule on the bonds touching its footprint once its detector fires), record, "
         "body and vote (E2E004's routes), oracle (the switch over the inherited patch itself: reported only, the ceiling "
         "of where-to-switch). Item sets: native / particular (li4 x F0, read first) / permissive.", "",
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
                 f"{p.get('threshold', '')} | {('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else 'reported, not registered'} | "
                 f"{p['tasks']} of {p['of']} | {al.get(p['id'], '')} | "
                 + " | ".join(f"{bs[n]['value']:+.4f}" if n in bs else "" for n in SETS) + " |")
    for g, fr in sorted(S.get("frontier", {}).items(), key=lambda x: int(x[0])):
        L += ["", f"## The frontier reading at g {g}: the points (keeping q_r of protected, healing u_r of post) and the "
              "controller's healing beyond the fixed rules' line", "",
              "| Set | record | vote | body | ctl | oracle (record's keeping) | line at ctl's keeping | F (pooled points) | F (mean of blocks) | F_RB, chord (pooled) | vote beyond chord | ctl (x, y) | vote (x, y) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for name in ORDER:
            r = fr.get(name)
            if not r:
                continue
            if not r["available"]:
                L.append(f"| {name} | partial ({r['tasks']} of {r['of']} tasks) | | | | | | | | | | | |")
                continue
            pt = r["points"]
            f2 = lambda p: f"({p[0]:.3f}, {p[1]:.3f})"
            nx = lambda n: "-" if r["normalized"].get(n) is None else f"({r['normalized'][n][0]:.2f}, {r['normalized'][n][1]:.2f})"
            L.append(f"| {name} | {f2(pt['record'])} | {f2(pt['vote'])} | {f2(pt['body'])} | {f2(pt['ctl'])} | "
                     f"{f2(pt['oracle']) if 'oracle' in pt else '-'} | {r['line_at_ctl_keep']:.3f} | {r['F_at_pooled']:+.4f} | "
                     f"{r['F_blocks_mean']:+.4f} | {r['F_RB_at_pooled']:+.4f} | {'yes' if r['vote_beyond_chord'] else 'no'} | "
                     f"{nx('ctl')} | {nx('vote')} |")
        L += ["", f"### Beside it at g {g}: the oracle, and the detector's firings and footprints through g {g} (per firing)", "",
              "| Set | F (blocks) | ctl heals | oracle heals | post: fired by g | post: footprint cells | post: patch covered | post: outside the patch | protected: fired by g | protected: footprint cells |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for name in ORDER:
            r = fr.get(name)
            if not r or not r["available"]:
                continue
            b = r.get("beside", {})
            po, pr = b.get("post", {}), b.get("protected", {})
            L.append(f"| {name} | {r['F_blocks_mean']:+.4f} | {opt(b.get('heal_ctl'), '.3f')} | {opt(b.get('heal_oracle'), '.3f')} | "
                     f"{opt(po.get('fired_by_g'), '.3f')} | {opt(po.get('footprint'), '.1f')} | {opt(po.get('patch_covered'), '.3f')} | "
                     f"{opt(po.get('outside_patch'), '.1f')} | {opt(pr.get('fired_by_g'), '.3f')} | {opt(pr.get('footprint'), '.1f')} |")
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
    F = S.get("firing", {})
    if F:
        L += ["", "## The switch, per generation: the share of newborns that fired, and over the firings only (per firing)", "",
              "| Lineage | Set | g | Newborns | Fired | Share | Fired by g (lineages) | Onset q25 / median / q75 | Footprint cells | outside the patch | Patch covered | Zone cells | Windows held | Open bonds |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, r in F.items():
            lab, name, g = k.split("|")
            on = r.get("onset_q")
            L.append(f"| {lab} | {name} | {g} | {r['newborns']} | {r['fired']} | {r['share']:.3f} | {r['ever_by_g']:.3f} | "
                     + (f"{on[0]:.0f} / {on[1]:.0f} / {on[2]:.0f} | {r['footprint']:.1f} | {r['footprint_outside_patch']:.1f} | "
                        f"{r['patch_covered']:.3f} | {r['zone']:.1f} | {r['windows']:.1f} | {opt(r.get('open_bonds'), '.1f')} |"
                        if on else "- | - | - | - | - | - | - |"))
    C = S.get("per_firing_costs", {})
    if C:
        L += ["", "## Over the lineages whose controller fired by g: the mean paired difference against the record rule "
              "(a lineage that never fired is the record rule bit for bit)", "",
              "| Lineage | Endpoint | g | Set | Lineage-cases | Fired by g | Mean over those |", "|---|---|---|---|---|---|---|"]
        for k, r in C.items():
            lab, e, g, name = k.split("|")
            L.append(f"| {lab} | {e} | {g} | {name} | {r['lineage_cases']} | {r['fired_by_g']} | {opt(r['mean_over_fired'], '+.4f')} |")
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
