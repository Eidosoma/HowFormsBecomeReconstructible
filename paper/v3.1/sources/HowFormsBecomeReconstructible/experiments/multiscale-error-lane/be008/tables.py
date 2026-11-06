"""BE008's tables from the reader's outputs: python -m be008.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be008 import design as D  # noqa: E402

FROZEN = LANE / "be008" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be008")
    ap.add_argument("--predictions", type=Path, default=FROZEN / "predictions.json")
    a = ap.parse_args()
    L, head = {}, None
    for b in D.BODIES:
        s = json.loads((a.out / f"summary_{b}.json").read_text())
        head = s
        for u, node in s["levels"].items():
            L.setdefault(u, {}).update(node)
    S = json.loads((a.out / "predictions_scored.json").read_text())
    stm = json.loads(a.predictions.read_text())["statements"]
    reads = head["run_reads"]
    mem0 = D.run_name("memory", 4, 0)
    lines = [f"# BE008 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE006's tissue (be006.sim.run: "
             "BE005's at read gain 0.2 on a full 32 x 32 sheet), BE001's six units and both bodies, the arbiter at 3e-4 "
             "and the commitment at 15,000 updates throughout. Clocks: AL (every other bond eta 0.01, bond noise p_b 1e-3; "
             "BE006's AL), AL-m (0.01, 1e-4), AL-n (0.01, 3e-5), SL-m (3e-4, 1e-4), SL (3e-4, 3e-5; BE006's SL). dial-X: "
             "BE004's dial; never-X: the signal never on. memory4@D: a 4 x 4 memory damage, the signal at D + 1 to "
             "D + 1,000; D = 979, 1,959, 3,918 = 0.5, 1, 2 T*(3e-4) (3.3, 6.5 and 13.1 h at 300 updates an hour). sensors: "
             "the share of the patch's anchored cells right at the signal's first update; anc_right: the same at a read; "
             "loss: r_in at 4,000 in memory4@0 less r_in at D + 4,000 in memory4@D (equal elapsed time).", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", f"## memory4@0: the anchored cells right without a signal (anc_right) by read; rows unit, body and clock", "",
              "| Unit | Body | Clock | " + " | ".join(f"{t:,} ({D.hours(t):.1f} h)" for t in reads[mem0]) + " |",
              "|---|---|---|" + "---|" * len(reads[mem0])]
    for u in D.UNITS:
        for b in D.BODIES:
            for c in D.CLOCKS:
                lines.append(f"| {u} | {b} | {c} | " + " | ".join(f(x[0]) for x in L[u][b][mem0][f"never-{c}"]["anc_right"]) + " |")
    lines += ["", "## memory4@0: the sheet's record without a signal (r_all) and the prompt repair (dial r_in) at 4,000", "",
              "| Unit | Body | " + " | ".join(f"{c} r_all | {c} prompt" for c in D.CLOCKS) + " |",
              "|---|---|" + "---|---|" * len(D.CLOCKS)]
    i4 = reads[mem0].index(4000)
    for u in D.UNITS:
        for b in D.BODIES:
            n = L[u][b][mem0]
            lines.append(f"| {u} | {b} | " + " | ".join(f"{f(n[f'never-{c}']['r_all'][i4][0])} | {f(n[f'dial-{c}']['r_in'][i4][0])}"
                                                         for c in D.CLOCKS) + " |")
    lines += ["", "## The delayed dials: sensors at onset and the loss at equal elapsed time", "",
              "| Unit | Body | Clock | m | D | prompt (4,000) | late (D + 4,000) | loss | sensors |", "|---|---|---|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for c in D.CLOCKS:
                for m in D.MULTS:
                    rn, arm = D.where(c, m)
                    dl = D.delay(D.ETA_CAL, m)
                    p = L[u][b][mem0][arm]["r_in"][reads[mem0].index(4000)][0]
                    x = L[u][b][rn][arm]["r_in"][reads[rn].index(dl + D.AFTER)][0]
                    lines.append(f"| {u} | {b} | {c} | {m:g} | {dl:,} | {f(p)} | {f(x)} | {f(p - x)} | "
                                 f"{f(L[u][b][rn][arm]['anc_on_share'][0])} |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
