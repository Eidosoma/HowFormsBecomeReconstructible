"""LR002's tables from the reader's outputs: python -m lr002.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from lr002 import design as D  # noqa: E402

FROZEN = LANE / "lr002" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr002")
    a = ap.parse_args()
    s = json.loads((a.out / "summary.json").read_text())
    L = s["levels"]
    stm = json.loads((FROZEN / "predictions.json").read_text())["statements"]
    t1 = D.READS[-1]
    lines = [f"# LR002 tables ({s['stage']}, blocks {s['blocks'][0]}–{s['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). Bodies: dw the double well, li4 "
             "DL001's strong period-8 lateral-inhibition body, each reading a relational record (no coarse code) at gain 0.2. "
             "Every bond's sign flips at rate p_b per update. Repairs: none; parity (plaquette rule); record (Hebbian "
             "relearning from the record); record+parity (LR001's two layers); body (Hebbian relearning from the body); "
             "body+parity. theta x0 and x1 are environmental-field spreads 0 and 0.2. sign: the body's agreement with the "
             "template; r_sign: the record's; bond_err: the share of bonds that differ from the taught ones.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {s['statements'][x['id']]['verdict']} | {x['claim']} |" for x in stm]
    for ep, title, d in (("sign", "the body's sign", 3), ("r_sign", "the record's sign", 3), ("bond_err", "bond error", 4)):
        lines += ["", f"## {title} at t = {t1:,}: rows p_b, columns repair", ""]
        for u in D.UNITS:
            for b in D.BODIES:
                lines += [f"**{u}, {b}**", "", "| p_b | " + " | ".join(D.REPAIRS) + " |", "|---|" + "---|" * len(D.REPAIRS)]
                for rate in D.RATES:
                    cells = [f(L[u][b][f"{rate:g}/{rep}"][f"{ep}@{t1}"][0], d) for rep in D.REPAIRS]
                    lines.append(f"| {rate:g} | " + " | ".join(cells) + " |")
                lines.append("")
    lines += ["## The body's sign over time (t = " + " / ".join(f"{t:,}" for t in D.READS) + "), body+parity and record+parity", "",
              "| Unit | Body | p_b | body+parity | record+parity |", "|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for rate in D.RATES[1:]:
                cells = [" / ".join(f(L[u][b][f"{rate:g}/{rep}"][f"sign@{t}"][0]) for t in D.READS) for rep in ("body+parity", "record+parity")]
                lines.append(f"| {u} | {b} | {rate:g} | " + " | ".join(cells) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
