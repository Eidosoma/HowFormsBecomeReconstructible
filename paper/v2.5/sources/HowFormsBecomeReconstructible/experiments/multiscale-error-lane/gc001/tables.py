"""GC001's tables from the reader's summaries: python -m gc001.tables --out RESULTS_DIR  (writes TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from gc001 import design as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "gc001")
    a = ap.parse_args()
    L = {}
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    sc = json.loads((a.out / "predictions_scored.json").read_text())
    lines = ["# GC001 tables", "", "Block means over the stage's blocks at t = 4,000 (4 decimals; the reader scores unrounded means).", "",
             "## Verdicts", "", "| Id | Verdict |", "|---|---|"]
    lines += [f"| {k} | {v['verdict']} |" for k, v in sc.items()]
    for title, run_of, ep in (("The sheet's record with no event (r_all), by sigma", lambda s: D.run_name("none", 8, s), "r_all"),
                              ("The matched scattered control (r_all), by sigma", lambda s: D.run_name("scatter", 8, s), "r_all"),
                              ("The boundary band (r_band), no event", lambda s: D.run_name("none", 8, s), "r_band"),
                              ("The interior (r_int), no event", lambda s: D.run_name("none", 8, s), "r_int"),
                              ("Excess domain walls, no event", lambda s: D.run_name("none", 8, s), "walls")):
        lines += ["", f"## {title}", "", "| Unit/body | Arm | " + " | ".join(f"sigma {s:g}" for s in D.SIGMAS) + " |",
                  "|---|---|" + "---|" * len(D.SIGMAS)]
        for u in D.UNITS:
            for b in D.BODIES:
                for arm in D.ARMS:
                    cells = []
                    for s in D.SIGMAS:
                        rn = run_of(s)
                        node = L[u][b].get(rn)
                        cells.append("—" if node is None else f"{node[arm][ep][-1][0]:.4f}")
                    lines.append(f"| {u}/{b} | {arm} | " + " | ".join(cells) + " |")
    for sit in ("change", "memory"):
        lines += ["", f"## {sit}4: the record inside the patch (r_in)", "",
                  "| Unit/body | Arm | " + " | ".join(f"sigma {s:g}" for s in D.EVENT_SIGMAS) + " |", "|---|---|" + "---|" * len(D.EVENT_SIGMAS)]
        for u in D.UNITS:
            for b in D.BODIES:
                for arm in D.ARMS:
                    cells = [f"{L[u][b][D.run_name(sit, 4, s)][arm]['r_in'][-1][0]:.4f}" for s in D.EVENT_SIGMAS]
                    lines.append(f"| {u}/{b} | {arm} | " + " | ".join(cells) + " |")
    lines += ["", "## Misread share of anchors (mean over blocks)", "", "| Unit/body | " + " | ".join(f"sigma {s:g}" for s in D.SIGMAS[1:]) + " |",
              "|---|" + "---|" * (len(D.SIGMAS) - 1)]
    for u in D.UNITS:
        for b in D.BODIES:
            lines.append(f"| {u}/{b} | " + " | ".join(f"{L[u][b][D.run_name('none', 8, s)]['_misread'][0]:.4f}" for s in D.SIGMAS[1:]) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print("wrote", a.out / "TABLES.md")


if __name__ == "__main__":
    main()
