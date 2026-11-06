"""SM009's tables: python -m sm009.tables --in SCORED_OR_MARGINS_JSON --out TABLES.md

From a reader's output (predict's predictions_scored.json, or P65b's margins record): the parts, the reported parts, O's
identity, the decomposition of Y1 and Y2, O's realized mean help against P's per composition, the realized mean gains by
arm and role, and the members' levels against k by body, arm and role, as markdown, at most 256 KiB. Amendment 1: arms P
and O only (R dropped).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sm008 import tables as T8
from sm009 import design as D

LIMIT = 256 * 1024
KORDER = tuple(D.COMPOSITIONS)
ARMS = ("P", "O")
f = T8.f


def render(rec):
    out = [f"# SM009 tables: {rec.get('stage', '?')} ({rec.get('root', '')})"]
    out += T8._parts(rec["parts"], "## Parts (li4)", True)
    out += T8._parts(rec.get("reported", []), "## Reported", False)
    ox = rec.get("o_exact")
    if ox:
        out += ["", "## O's identity (the field not read)", "",
                f"{ox['sheets']} sheets of O arrangements against iso8/O's sheet of the same future and case: largest "
                f"difference {ox['largest_difference']:.3e} (exact: {ox['exact']})"]
    dc = rec.get("decomposition")
    if dc:
        out += ["", "## The decomposition, case by case: Y1 = Y4 - X1/P and Y2 = (O - P)/k0 - X2/P", "",
                "| Body | Y1 | Y4 (position) | -X1/P (undoing the dilution) | largest case residual | Y2 | (O - P)/k0 "
                "(position) | -X2/P (undoing the mixing gain) | largest case residual |", "|---|---|---|---|---|---|---|---|---|"]
        for body in D.BODIES:
            r = dc.get(body)
            if not r:
                continue
            out.append(f"| {body} | {f(r['Y1'])} | {f(r['Y4 (position)'])} | {f(r['-X1/P (undoing the dilution)'])} | "
                       f"{r['Y1 - (Y4 - X1/P), largest |case|']:.1e} | {f(r['Y2'])} | {f(r['(O - P)/k0 (position)'])} | "
                       f"{f(r['-X2/P (undoing the mixing gain)'])} | {r['Y2 - ((O - P)/k0 - X2/P), largest |case|']:.1e} |")
    rh = rec.get("realized_help")
    if rh:
        out += ["", "## O's realized mean help against P's (each arrangement's mean gain, every sheet and future)", "",
                "| Body | Composition | P | O | O / P |", "|---|---|---|---|---|"]
        for body in D.BODIES:
            for c in (*KORDER, "iso8"):
                r = rh.get(f"{body}|{c}")
                if r:
                    out.append(f"| {body} | {c} | {f(r['P'])} | {f(r['O'])} | {f(r['O/P'])} |")
    gn = rec.get("gains")
    if gn:
        out += ["", "## The realized mean gain by arm and role (every absorbing composition pooled)", "",
                "| Body | Arm | healthy | struggling |", "|---|---|---|---|"]
        for body in D.BODIES:
            for arm in ARMS:
                out.append(f"| {body} | {arm} | {f(gn.get(f'{body}|{arm}|healthy'))} | {f(gn.get(f'{body}|{arm}|struggling'))} |")
    lv = rec.get("levels", {})
    for body in D.BODIES:
        for arm, edge in (("P", "absorbing"), ("O", "absorbing"), ("P", "sealed")):
            rows = [(c, lv.get(f"{body}|{c}/{edge}/{arm}")) for c in KORDER]
            rows = [(c, r) for c, r in rows if r is not None]
            if not rows:
                continue
            out += ["", f"## {body}, arm {arm}, {edge}: the members' a at the last read against k "
                    f"(healthy {D.ROLES[body][0]}, struggling {D.ROLES[body][1]})", "",
                    "| Composition | k | struggling a | healthy a | group mean | struggling gain | healthy gain | "
                    "struggling stress | healthy stress |", "|---|---|---|---|---|---|---|---|---|"]
            for c, r in rows:
                s, h = r.get("struggling"), r.get("healthy")
                last = max(int(k[2:]) for k in (s or h) if k.startswith("a_") and k[2:].isdigit())
                out.append(f"| {c} | {len(D.COMPOSITIONS[c])} | {f(s and s[f'a_{last}'])} | {f(h and h[f'a_{last}'])} | "
                           f"{f(r.get('group_mean'))} | {f(s and s['gain_mean'])} | {f(h and h['gain_mean'])} | "
                           f"{f(s and s['stress_mean'])} | {f(h and h['stress_mean'])} |")
        for arm in ARMS:
            iso = lv.get(f"{body}|iso8/absorbing/{arm}")
            if iso:
                out += ["", f"## {body}, iso8 (isolated), arm {arm}", "", "| Role | a | rescued | gain | stress |",
                        "|---|---|---|---|---|"]
                for role in ("struggling", "healthy"):
                    r = iso[role]
                    last = max(int(k[2:]) for k in r if k.startswith("a_") and k[2:].isdigit())
                    out.append(f"| {role} ({D.ROLES[body][role == 'struggling']}) | {f(r[f'a_{last}'])} | {f(r['rescued'], 3)} | "
                               f"{f(r['gain_mean'])} | {f(r['stress_mean'])} |")
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
