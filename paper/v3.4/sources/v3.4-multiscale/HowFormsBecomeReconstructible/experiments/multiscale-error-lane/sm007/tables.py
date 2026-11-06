"""SM007's tables: python -m sm007.tables --in SCORED_OR_MARGINS_JSON --out TABLES.md

From a reader's output (predict's predictions_scored.json, or P61b's margins record): the parts, the reported parts and every
arrangement's levels (a_v at each read, rescued, the item sets, mean gain, exposure and stress), as markdown, at most
256 KiB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LIMIT = 256 * 1024


def f(x, d=4, sign=False):
    if x is None:
        return "—"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def render(rec):
    out = [f"# SM007 tables: {rec.get('stage', '?')} ({rec.get('root', '')})", ""]
    out += ["## Parts", "", "| Id | Part | Kind | Value | 95% CI | SD | Halves | Narrowest | Registers |",
            "|---|---|---|---|---|---|---|---|---|"]
    for p in rec["parts"]:
        if not p.get("available"):
            out.append(f"| {p['id']} | {p['part']} | {p['kind']} | unavailable ({p['tasks']} of {p['of']} tasks) | | | | | |")
            continue
        ci = p.get("ci95", [None, None])
        out.append(f"| {p['id']} | {p['part']} | {p['kind']} | {f(p['value'], sign=True)} | [{f(ci[0], sign=True)}, "
                   f"{f(ci[1], sign=True)}] | {f(p['sd'])} | {f(p['halves'][0], sign=True)}, {f(p['halves'][1], sign=True)} | "
                   f"{p.get('narrowest')} | {p.get('registers_at_narrowest')} |")
    rep = rec.get("reported", [])
    sections = (("## G against headcount and the field factor (M7's and M8's cells; reported, the lead's ruling 6)",
                 lambda i: i.startswith("C")),
                ("## The paper's stress against the ruled stress (reported; Amendment 2)", lambda i: i.startswith("RP")),
                ("## Reported", lambda i: not (i.startswith("C") or i.startswith("RP"))))
    for title, keep in sections:
        rows = [p for p in rep if keep(p["id"])]
        if not rows:
            continue
        out += ["", title, "", "| Id | Part | Value | 95% CI | SD | Halves |", "|---|---|---|---|---|---|"]
        for p in rows:
            if not p.get("available"):
                out.append(f"| {p['id']} | {p['part']} | unavailable | | | |")
                continue
            ci = p.get("ci95", [None, None])
            out.append(f"| {p['id']} | {p['part']} | {f(p['value'], sign=True)} | [{f(ci[0], sign=True)}, {f(ci[1], sign=True)}] | "
                       f"{f(p['sd'])} | {f(p['halves'][0], sign=True)}, {f(p['halves'][1], sign=True)} |")
    lv = rec.get("levels", {})
    twins = [(lab, lab.rsplit("/paper", 1)[0]) for lab in lv if lab.endswith("/paper")]
    if twins and rec.get("hist_bins"):
        hb = rec["hist_bins"]
        out += ["", "## Per-sheet a_v at the last read, the paper arm and its ruled twins (counts in bins of "
                f"{hb[1] - hb[0]:.2f} from {hb[0]:.2f} to {hb[-1]:.2f})", "", "| Arrangement | a | rescued | counts |", "|---|---|---|---|"]
        for pa, tw in twins:
            for lab in (tw, pa):
                v = lv[lab]
                last = max(int(k[2:]) for k in v if k.startswith("a_") and k[2:].isdigit())
                out.append(f"| {lab} | {f(v[f'a_{last}'])} | {f(v['rescued'], 3)} | {' '.join(map(str, v.get('hist', [])))} |")
    if lv:
        reads = sorted(int(k[2:]) for k in next(iter(lv.values())) if k.startswith("a_") and k[2:].isdigit())
        out += ["", "## Levels (pooled a_v; rescued = a_v of at least 0.95; means over the window)", "",
                "| Arrangement | " + " | ".join(f"a at {r:,}" for r in reads) + " | rescued | native | particular | "
                "permissive | gain | exposure | stress |",
                "|---|" + "---|" * (len(reads) + 7)]
        for lab, v in lv.items():
            out.append(f"| {lab} | " + " | ".join(f(v[f'a_{r}']) for r in reads) + f" | {f(v['rescued'], 3)} | "
                       f"{f(v.get('a_native'))} | {f(v.get('a_particular'))} | {f(v.get('a_permissive'))} | "
                       f"{f(v['gain_mean'])} | {f(v['expo_mean'], 3)} | {f(v['stress_mean'])} |")
    if rec.get("G"):
        out += ["", "## G (frozen on P61)", "", "| x = L_eff / lambda | a |", "|---|---|"]
        out += [f"| {x:.4f} | {y:.4f} |" for x, y in zip(rec["G"]["x"], rec["G"]["y"])]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    text = render(json.loads(a.inp.read_text()))
    if len(text.encode()) > LIMIT:
        raise SystemExit(f"tables exceed {LIMIT} bytes")
    a.out.write_text(text)
    print(a.out, len(text.encode()), "bytes")


if __name__ == "__main__":
    main()
