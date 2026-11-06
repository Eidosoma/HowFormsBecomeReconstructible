"""LR004's tables from the reader's outputs: python -m lr004.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from lr004 import design as D  # noqa: E402

FROZEN = LANE / "lr004" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr004")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = s["levels"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    t1 = D.READS[-1]
    lines = [f"# LR004 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's strong period-8 lateral-inhibition body, each reading a relational record (no coarse code) at gain 0.2. "
             "Every bond's sign flips at rate p_b per update. Teachers: record+parity (LR001's two layers); body (relearning "
             "from the body, LR002); site (the body on every bond of a site with a frustrated bond, LR003); pair (a second "
             "record; both relearn where they agree); vote (two records and the body, majority of the three relations); "
             "anchors4/16 (the acquired record's sign at a quarter or sixteenth of the cells decides where body and record "
             "disagree). theta x0 and x1 scale the environmental field. sign: the body's agreement with the template; r_sign: "
             "the first record's; bond_err: the share of the first record's bonds that differ from the taught ones; opened: "
             "the mean share of bonds the body taught (body, site), of bonds where the two records disagreed (pair, vote), "
             "or of cells an anchor arbitrated (anchors).", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title, d in (("r_sign", "the record's sign", 3), ("sign", "the body's sign", 3), ("bond_err", "bond error", 4)):
        lines += ["", f"## {title} at t = {t1:,}: rows p_b, columns teacher", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                lines += [f"**{u}, {b}**", "", "| p_b | " + " | ".join(D.REPAIRS) + " |", "|---|" + "---|" * len(D.REPAIRS)]
                for rate in D.RATES:
                    cells = [f(L[u][b][f"{rate:g}/{rep}"][f"{ep}@{t1}"][0], d) for rep in D.REPAIRS]
                    lines.append(f"| {rate:g} | " + " | ".join(cells) + " |")
                lines.append("")
    lines += ["## Share of bonds where the body or the third copy decided (mean over the window)", ""]
    for u in D.UNITS:
        for b in D.BODIES:
            lines += [f"**{u}, {b}**", "", "| p_b | " + " | ".join(D.REPAIRS) + " |", "|---|" + "---|" * len(D.REPAIRS)]
            for rate in D.RATES:
                lines.append(f"| {rate:g} | " + " | ".join(f(L[u][b][f"{rate:g}/{rep}"]["opened"][0], 4) for rep in D.REPAIRS) + " |")
            lines.append("")
    lines += ["## The record's sign over time (t = " + " / ".join(f"{t:,}" for t in D.READS) + "), vote, body and record+parity", "",
              "| Unit | Body | p_b | vote | body | record+parity |", "|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for rate in D.RATES:
                cells = [" / ".join(f(L[u][b][f"{rate:g}/{rep}"][f"r_sign@{t}"][0]) for t in D.READS) for rep in ("vote", "body", "record+parity")]
                lines.append(f"| {u} | {b} | {rate:g} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
