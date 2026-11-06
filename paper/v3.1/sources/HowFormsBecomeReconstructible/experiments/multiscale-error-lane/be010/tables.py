"""BE010's tables from the reader's outputs: python -m be010.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be010 import design as D  # noqa: E402

FROZEN = LANE / "be010" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be010")
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
    nv, sh = D.NEVER_RUN, D.SHAM_RUN
    lines = [f"# BE010 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE007's tissue and clock C12 (BE006's "
             "fully calibrated clock SL; every uncommitted footprint cell commits to its record's sign at 3,600 updates, 12 h), "
             "BE001's six units and both bodies, a 4 x 4 memory damage at 0, and a second event at T_W = 7,836 (26.1 h) in the "
             "patch: N none; W a new wound (newborn cells, every touching contact untrained, the cue kept); K the same wound "
             "with the rim's contacts kept; R the drug (every commitment cleared); then re-execution at T_W + 3,600 "
             "(W0, R0: none). dial-X: BE004's dial at T_W + d + 1 to T_W + d + 1,000 (d = 0, 979, 1,959, 3,918: 0, 3.3, 6.5, "
             "13.1 h after the reset), read at T_W + d + 4,000; never-X: the signal never on (memory4@w+3918); none4@w+0: the "
             "same resets with no damage; cue4@w+0: BE007's sham (a quarter of the anchors corrupted) right after the reset. "
             "r_in: the patch's record against the target; r_all: the sheet's; r_fp2: the footprint's; conf_in: its confident "
             "share; committed_in: its committed share; sensors: the patch's anchored cells right at the dial's first update; "
             "hit: the patch's share ever triggered.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    rr = [t for t in reads[nv] if t >= D.T_W]
    lines += ["", f"## No signal ({nv}): r_in by read from T_W (updates; hours at {D.TAU_M} an hour); rows unit, body, arm", "",
              "| Unit | Body | Arm | " + " | ".join(f"{t:,} ({D.hours(t):.1f} h)" for t in rr) + " |", "|---|---|---|" + "---|" * len(rr)]
    for u in D.UNITS:
        for b in D.BODIES:
            for x in D.RESETS:
                n = L[u][b][nv][f"never-{x}"]["r_in"]
                lines.append(f"| {u} | {b} | never-{x} | " + " | ".join(f(n[reads[nv].index(t)][0]) for t in rr) + " |")
    lines += ["", "## The signals after the reset: r_in at T_W + d + 4,000 against no signal at that read; sensors and hit", "",
              "| Unit | Body | Reset | m | d | d (h) | late | none | gain | sensors | hit |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            for x in D.MAIN + ("W0", "R0"):
                for m in (D.MULTS if x in D.MAIN else (2,)):
                    rn, arm = D.where(x, m)
                    d = int(round(m * D.T_STAR))
                    t = D.T_W + d + D.AFTER
                    v = L[u][b][rn][arm]["r_in"][reads[rn].index(t)][0]
                    nn = L[u][b][nv][f"never-{x}"]["r_in"][reads[nv].index(t)][0]
                    lines.append(f"| {u} | {b} | {x} | {m:g} | {d:,} | {D.hours(d):.1f} | {f(v)} | {f(nn)} | {f(v - nn)} | "
                                 f"{f(L[u][b][rn][arm]['anc_on_share'][0])} | {f(L[u][b][rn][arm]['hit'][0])} |")
    sr = [t for t in reads[sh] if t >= D.T_W]
    lines += ["", f"## No damage ({sh}): r_in by read from T_W; executed and executed2", "",
              "| Unit | Body | Arm | " + " | ".join(f"{t:,}" for t in sr) + " | executed | executed2 |",
              "|---|---|---|" + "---|" * (len(sr) + 2)]
    for u in D.UNITS:
        for b in D.BODIES:
            for x in D.MAIN:
                n = L[u][b][sh][f"never-{x}"]
                lines.append(f"| {u} | {b} | never-{x} | " + " | ".join(f(n["r_in"][reads[sh].index(t)][0]) for t in sr)
                             + f" | {f(n['executed'][0])} | {f(n['executed2'][0])} |")
    cu = D.CUE_RUN
    t = D.T_W + D.AFTER
    lines += ["", f"## The sham after the reset ({cu}: a quarter of the anchors corrupted, the sham at T_W + 1 to T_W + 1,000), "
              f"at t = {t:,}: never less dial (the sham's cost) and never-x less never-N (the reset's own cost)", "",
              "| Unit | Body | Reset | sham r_all | sham r_fp2 | reset r_all | reset r_in | hit |", "|---|---|---|---|---|---|---|---|"]
    for u in D.UNITS:
        for b in D.BODIES:
            n = L[u][b][cu]
            ti = reads[cu].index(t)
            for x in ("N", "W", "R"):
                nv_, dl_ = n[f"never-{x}"], n[f"dial-{x}"]
                lines.append(f"| {u} | {b} | {x} | {f(nv_['r_all'][ti][0] - dl_['r_all'][ti][0], 4)} | "
                             f"{f(nv_['r_fp2'][ti][0] - dl_['r_fp2'][ti][0], 4)} | "
                             f"{f(n['never-N']['r_all'][ti][0] - nv_['r_all'][ti][0], 4)} | "
                             f"{f(n['never-N']['r_in'][ti][0] - nv_['r_in'][ti][0], 4)} | {f(dl_['hit'][0])} |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
