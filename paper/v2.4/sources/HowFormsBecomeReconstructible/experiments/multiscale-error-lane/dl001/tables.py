"""DL001's tables from the reader's outputs: python -m dl001.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from dl001 import design as D  # noqa: E402

FROZEN = LANE / "dl001" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl001")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L, P = s["levels"], s["price_gain_for_sign_0.95"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    lines = [f"# DL001 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, "
             "li2 and li4 lateral inhibition tuned to period 8 (weak and strong), li16 tuned to period 16 (panel X).", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", "## F. Free memory (no record): sign at t = 500 / 2,000 / 8,000; spacing at 8,000", "",
              "| Unit | " + " | ".join(D.BODIES_MAIN) + " |", "|---|" + "---|" * len(D.BODIES_MAIN)]
    for u in D.PANELS["F"]["units"]:
        cells = []
        for b in D.BODIES_MAIN:
            e = L["F"][u][b]["free"]
            cells.append(f"{f(e['sign@500'][0])} / {f(e['sign@2000'][0])} / {f(e['sign@8000'][0])}; {f(e['spacing@8000'][0], 2)}")
        lines.append(f"| {u} | " + " | ".join(cells) + " |")
    lines += ["", "## U. The price of holding: sign at t = 2,000 by gain (0 from panel F); least gain for 0.95", ""]
    head = ["0"] + [f"{g:g}" for g in D.GAINS_U]
    lines += ["| Unit | Body | " + " | ".join(head) + " | price |", "|---|---|" + "---|" * (len(head) + 1)]
    for u in D.PANELS["U"]["units"]:
        for b in D.BODIES_MAIN:
            vals = [L["F"][u][b]["free"]["sign@2000"][0]] + [L["U"][u][b][f"g{g:g}"]["sign@2000"][0] for g in D.GAINS_U]
            pr = P[u][b]
            lines.append(f"| {u} | {b} | " + " | ".join(f(v) for v in vals) + f" | {'> 0.4' if pr is None else f'{pr:g}'} |")
    lines += ["", "## U. Correction work at gain 0.2 (mean |dt g (r - V~)| per site and update, second half of the window)", "",
              "| Unit | " + " | ".join(D.BODIES_MAIN) + " |", "|---|" + "---|" * len(D.BODIES_MAIN)]
    for u in D.PANELS["U"]["units"]:
        lines.append(f"| {u} | " + " | ".join(f(L["U"][u][b]["g0.2"]["w_corr"][0], 4) for b in D.BODIES_MAIN) + " |")
    lines += ["", "## W. Free repair in S4: agreement inside the wound at t = 250 / 500 / 2,000", ""]
    for u in D.PANELS["W"]["units"]:
        lines += [f"**{u}**", "", "| Wound | " + " | ".join(D.BODIES_MAIN) + " |", "|---|" + "---|" * len(D.BODIES_MAIN)]
        for c in D.COND_W:
            cells = [" / ".join(f(L["W"][u][b][c.name][f"patch@{t}"][0]) for t in D.SNAPS_W) for b in D.BODIES_MAIN]
            lines.append(f"| {c.name} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## B. Building from newborn noise: sign at t = 500 / 2,000; correction work", "",
              "| Unit | Gain | " + " | ".join(D.BODIES_MAIN) + " |", "|---|---|" + "---|" * len(D.BODIES_MAIN)]
    for u in D.PANELS["B"]["units"]:
        for c in D.COND_B:
            cells = [f"{f(L['B'][u][b][c.name]['sign@500'][0])} / {f(L['B'][u][b][c.name]['sign@2000'][0])}; "
                     f"{f(L['B'][u][b][c.name]['w_corr'][0], 4)}" for b in D.BODIES_MAIN]
            lines.append(f"| {u} | {c.gain:g} | " + " | ".join(cells) + " |")
    lines += ["", "## X. The reversed match, 64-site sheet: no record sign at t = 2,000 / 8,000 and spacing; held record "
              "sign at t = 2,000 by gain", ""]
    head = [f"{c.gain:g}" for c in D.COND_X[1:]]
    lines += ["| Unit | Body | free | spacing | " + " | ".join(head) + " |", "|---|---|---|---|" + "---|" * len(head)]
    for u in D.PANELS["X"]["units"]:
        for b in D.BODIES_X:
            e = L["X"][u][f"{b}/free"]["g0"]
            held = [f(L["X"][u][f"{b}/held"][c.name]["sign@2000"][0]) for c in D.COND_X[1:]]
            lines.append(f"| {u} | {b} | {f(e['sign@2000'][0])} / {f(e['sign@8000'][0])} | {f(e['spacing@8000'][0], 2)} | "
                         + " | ".join(held) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
