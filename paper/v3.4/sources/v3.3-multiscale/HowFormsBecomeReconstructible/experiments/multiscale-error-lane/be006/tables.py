"""BE006's tables from the reader's outputs: python -m be006.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be006 import design as D  # noqa: E402

FROZEN = LANE / "be006" / "frozen"
SHOW = {"memory": ("r_in", "v_in", "r_all"), "change": ("r_in", "r_in_old", "r_all"), "cue": ("r_all", "r_fp2", "r_out8")}


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be006")
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
    lines = [f"# BE006 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE005's tissue (BE004's: BE001's at "
             "read gain 0.2, a full 32 x 32 sheet), BE001's six units and both bodies, with three clocks per arm: the "
             "arbiter's relearning rate eta_a, every other bond's rate eta (with p_b = 1e-3 x eta / 0.01) and the "
             "commitment's decay tau_c. Clocks: F (eta_a 0.01, eta 0.01, tau_c 300: BE005's dial-e0.01), A (eta_a 3e-4), AL "
             "(A with tau_c 15,000), S (eta_a = eta = 3e-4, tau_c 300), SL (S with tau_c 15,000). dial-X: BE004's dial; "
             "never-X: the signal never on. memory4@D: a 4 x 4 memory damage, the signal at D + 1 to D + 1,000; change4@0: a "
             "legitimate change of a 4 x 4 patch, the prompt signal; cue4@0: a quarter of the anchors corrupted, a prompt "
             "sham. T*(0.01) = 58.5 and T*(3e-4) = 1,959 updates; at 300 updates an hour, 0.19 h and 6.53 h. r_in: the "
             "patch (against the new target in a change); v_in: the body in the patch; r_all: the sheet; r_fp2: the "
             "footprint; r_out8: outside the patch dilated by 8; sensors: the share of the patch's anchored cells right at "
             "the signal's first update.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    mem0 = D.run_name("memory", 4, 0)
    lines += ["", f"## memory4@0: r_in by read (updates; hours at {D.TAU_M} an hour); rows unit, body and arm", "",
              "| Unit | Body | Arm | " + " | ".join(f"{t:,} ({D.hours(t):g} h)" for t in reads[mem0]) + " |",
              "|---|---|---|" + "---|" * len(reads[mem0])]
    for u in D.UNITS:
        for b in D.BODIES:
            for arm in D.RUNS[0][3]:
                lines.append(f"| {u} | {b} | {arm} | " + " | ".join(f(x[0]) for x in L[u][b][mem0][arm]["r_in"]) + " |")
    lines += ["", "## The delayed dials: r_in at the clock's scoring read against the prompt dial, and the sensors at onset", "",
              "| Unit | Body | Clock | m | D (updates) | D (h) | t | prompt | late | loss | sensors |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for c, ms in D.LATE.items():
                for m in ms:
                    rn, arm = D.where(c, m)
                    t = D.T_SCORE["F"] if c == "F" else (D.T_SCORE["m4"] if m == 4 else D.T_SCORE["slow"])
                    p = L[u][b][mem0][arm]["r_in"][reads[mem0].index(t)][0]
                    x = L[u][b][rn][arm]["r_in"][reads[rn].index(t)][0]
                    dl = D.delay(D.eta_of(c), m)
                    lines.append(f"| {u} | {b} | {c} | {m:g} | {dl:,} | {D.hours(dl):.2f} | {t:,} | {f(p)} | {f(x)} | "
                                 f"{f(p - x)} | {f(L[u][b][rn][arm]['anc_on_share'][0])} |")
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
                for e in ("onset", "hit"):
                    lines.append(f"| {u} | {b} | {e} | " + " | ".join(f(n[arm][e][0]) for arm in arms) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
