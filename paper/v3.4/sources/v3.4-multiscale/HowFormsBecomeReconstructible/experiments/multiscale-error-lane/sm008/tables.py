"""SM008's tables: python -m sm008.tables --in SCORED_OR_MARGINS_JSON --out TABLES.md

From a reader's output (predict's predictions_scored.json, or P64b's margins record): the parts, the reported parts, the
preprint's mixing identity, the members' levels against k by body, role and edge, and every arrangement's levels, as
markdown, at most 256 KiB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sm008 import design as D

LIMIT = 256 * 1024
KORDER = ("k0", "k1-corner", "k1-inner", "k2-adjacent", "k2-apart", "k4-half", "k4-checker", "k6", "k7-corner", "k7-inner", "k8")


def f(x, d=4, sign=False):
    if x is None:
        return "—"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def _parts(rows, title, with_rule):
    out = ["", title, ""]
    if with_rule:
        out += ["| Id | Part | Kind | Value | 95% CI | SD | Halves | Narrowest | Registers |", "|---|---|---|---|---|---|---|---|---|"]
    else:
        out += ["| Id | Part | Value | 95% CI | SD | Halves |", "|---|---|---|---|---|---|"]
    for p in rows:
        if not p.get("available"):
            out.append(f"| {p['id']} | {p['part']} | " + ("| " if with_rule else "") + f"unavailable ({p['tasks']} of {p['of']} tasks) | | | |"
                       + (" | |" if with_rule else ""))
            continue
        ci = p.get("ci95", [None, None])
        cells = [p["id"], p["part"]] + ([str(p.get("kind"))] if with_rule else []) + [
            f(p["value"], 5, True), f"[{f(ci[0], 5, True)}, {f(ci[1], 5, True)}]", f(p["sd"], 5),
            f"{f(p['halves'][0], 5, True)}, {f(p['halves'][1], 5, True)}"]
        if with_rule:
            cells += [str(p.get("narrowest")), str(p.get("registers_at_narrowest"))]
        out.append("| " + " | ".join(cells) + " |")
    return out


def render(rec):
    out = [f"# SM008 tables: {rec.get('stage', '?')} ({rec.get('root', '')})"]
    out += _parts(rec["parts"], "## Parts (li4)", True)
    out += _parts(rec.get("reported", []), "## Reported", False)
    x5 = rec.get("x5_exact")
    if x5:
        out += ["", "## The preprint's mixing identity (X5 by the layout)", "",
                f"{x5['sheets']} sheets of k1-corner under the preprint's stress against the sheet at the same future, group "
                f"and position of k0 or k8: largest difference {x5['largest_difference']:.3e} (exact: {x5['exact']})"]
    lv = rec.get("levels", {})
    if lv:
        reads = None
        for body in D.BODIES:
            for edge, suffix in (("absorbing", ""), ("sealed", ""), ("absorbing", "/shared"), ("absorbing", "/paper")):
                rows = [(c, lv.get(f"{body}|{c}/{edge}{suffix}")) for c in KORDER]
                rows = [(c, r) for c, r in rows if r is not None]
                if not rows:
                    continue
                out += ["", f"## {body}, {edge}{suffix}: the members' a at the last read against k "
                        f"(healthy {D.ROLES[body][0]}, struggling {D.ROLES[body][1]})", "",
                        "| Composition | k | struggling a | healthy a | group mean | struggling exposure | healthy exposure | "
                        "struggling gain | healthy gain |", "|---|---|---|---|---|---|---|---|---|"]
                for c, r in rows:
                    s, h = r.get("struggling"), r.get("healthy")
                    last = (max(int(k[2:]) for k in (s or h) if k.startswith("a_") and k[2:].isdigit()))
                    out.append(f"| {c} | {len(D.COMPOSITIONS[c])} | {f(s and s[f'a_{last}'])} | {f(h and h[f'a_{last}'])} | "
                               f"{f(r.get('group_mean'))} | {f(s and s['expo_mean'], 3)} | {f(h and h['expo_mean'], 3)} | "
                               f"{f(s and s['gain_mean'])} | {f(h and h['gain_mean'])} |")
            iso = lv.get(f"{body}|iso8/absorbing")
            if iso:
                out += ["", f"## {body}, iso8 (isolated)", "", "| Role | a | rescued | gain | exposure |", "|---|---|---|---|---|"]
                for role in ("struggling", "healthy"):
                    r = iso[role]
                    last = max(int(k[2:]) for k in r if k.startswith("a_") and k[2:].isdigit())
                    out.append(f"| {role} ({D.ROLES[body][role == 'struggling']}) | {f(r[f'a_{last}'])} | {f(r['rescued'], 3)} | "
                               f"{f(r['gain_mean'])} | {f(r['expo_mean'], 3)} |")
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
