"""BE007's tables from the reader's outputs: python -m be007.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be007 import design as D  # noqa: E402

FROZEN = LANE / "be007" / "frozen"
SHOW = {"change": ("r_in", "r_in_old", "r_all", "committed_in"), "cue": ("r_all", "r_fp2", "r_out8", "committed_in")}


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be007")
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
    lines = [f"# BE007 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE006's fully calibrated tissue "
             "(clock SL: every bond relearning at 3e-4 with the bond noise scaled, a commitment of 15,000 updates), BE001's "
             "six units and both bodies, with execution in the signal's footprint from update tau_x after the event: SL (none), "
             "C6, C12, C24 (every uncommitted footprint cell commits to its record's sign at 1,800, 3,600 or 7,200 updates: "
             "6, 12, 24 h) and F12 (the cue at the footprint's anchors gone from 3,600). dial-X: BE004's dial; never-X: the "
             "signal never on. memory4@D: a 4 x 4 memory damage, the signal at D + 1 to D + 1,000 (D = 0, 979, 1,959, 3,918, "
             "7,836: 0, 3.3, 6.5, 13.1, 26.1 h); change4@3918: a legitimate change of a 4 x 4 patch, the signal 13.1 h late; "
             "cue4@3918: a quarter of the anchors corrupted, a sham 13.1 h late. T* = 1,959 updates (6.53 h at 300 updates "
             "an hour). r_in: the patch (against the new target in a change); r_all: the sheet; committed_in: the patch's "
             "committed share; sensors: the share of the patch's anchored cells right at the signal's first update; hit: "
             "the patch's share ever triggered.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    mem0 = D.run_name("memory", 4, 0)
    lines += ["", f"## memory4@0: r_in by read (updates; hours at {D.TAU_M} an hour); rows unit, body and arm", "",
              "| Unit | Body | Arm | " + " | ".join(f"{t:,} ({D.hours(t):.1f} h)" for t in reads[mem0]) + " |",
              "|---|---|---|" + "---|" * len(reads[mem0])]
    for u in D.UNITS:
        for b in D.BODIES:
            for arm in D.RUNS[0][3]:
                lines.append(f"| {u} | {b} | {arm} | " + " | ".join(f(x[0]) for x in L[u][b][mem0][arm]["r_in"]) + " |")
    lines += ["", "## The late signals: r_in at D + 4,000 against no signal at that read and the prompt signal at 4,000; the "
              "sensors and the patch's triggered share", "",
              "| Unit | Body | Clock | m | D | D (h) | late | none | gain | prompt | loss | sensors | hit |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for c in D.CLOCKS:
                for m in D.MULTS:
                    rn, arm = D.where(c, m)
                    d = int(round(m * D.T_STAR))
                    t = d + D.AFTER
                    x = L[u][b][rn][arm]["r_in"][reads[rn].index(t)][0]
                    nn = L[u][b][mem0][f"never-{c}"]["r_in"][reads[mem0].index(t)][0]
                    p = L[u][b][mem0][arm]["r_in"][reads[mem0].index(D.AFTER)][0]
                    lines.append(f"| {u} | {b} | {c} | {m:g} | {d:,} | {D.hours(d):.1f} | {f(x)} | {f(nn)} | {f(x - nn)} | "
                                 f"{f(p)} | {f(p - x)} | {f(L[u][b][rn][arm]['anc_on_share'][0])} | {f(L[u][b][rn][arm]['hit'][0])} |")
    for run in D.RUNS:
        if run[0] == "memory":
            continue
        rn, arms = D.run_name(*run), run[3]
        t = reads[rn][-1]
        lines += ["", f"## {rn} at t = {t:,}: rows unit, body and endpoint; columns arm", "",
                  "| Unit | Body | endpoint | " + " | ".join(arms) + " |", "|---|---|---|" + "---|" * len(arms)]
        for u in D.UNITS:
            for b in D.BODIES:
                n = L[u][b][rn]
                for e in SHOW[run[0]]:
                    if e in n[arms[0]]:
                        lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][-1][0]) for arm in arms) + " |")
                for e in ("hit", "executed"):
                    lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][0]) for arm in arms) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
