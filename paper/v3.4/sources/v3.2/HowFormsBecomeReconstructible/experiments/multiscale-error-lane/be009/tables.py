"""BE009's tables from the reader's outputs: python -m be009.tables [--out DIR]  (writes DIR/TABLES.md)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be009 import design as D  # noqa: E402

FROZEN = LANE / "be009" / "frozen"


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def half_effect(ds, rs):
    """The first delay (updates) where the remaining effect falls to 0.5, by linear interpolation; None if it never does."""
    for (d0, r0), (d1, r1) in zip(zip(ds, rs), zip(ds[1:], rs[1:])):
        if r0 >= 0.5 > r1:
            return d0 + (r0 - 0.5) * (d1 - d0) / (r0 - r1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be009")
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
    pairs = [(u, b) for u in D.UNITS for b in D.BODIES]

    def r_at(u, b, rn, arm, t):
        return L[u][b][rn][arm]["r_in"][reads[rn].index(t)][0]

    def gain(u, b, c, d):
        t = D.AFTER if d == 0 else d + D.AFTER
        late = r_at(u, b, mem0 if d == 0 else D.run_name("memory", 4, d), f"dial-{c}", t)
        return late - r_at(u, b, mem0, f"never-{c}", t)

    def pooled(fn):
        return sum(fn(u, b) for u, b in pairs) / len(pairs)

    lines = [f"# BE009 tables ({head['stage']}, blocks {head['blocks'][0]}–{head['blocks'][1] - 1})", "",
             "Block means (each block's mean over its 8 cases, then the mean over blocks). BE007's tissue (BE006's clock SL: "
             "every bond relearning at 3e-4 with the bond noise scaled, a commitment of 15,000 updates), BE001's six units and "
             "both bodies, with execution (commit: every uncommitted footprint cell with a confident record commits to its "
             "record's sign) at: SL none; C12 3,600 updates (12 h) for every case and cell (BE007's C12); CASE each case's "
             "own tau_x; CELL each footprint cell's own tau_x (log-normal, median 3,600, CV 0.4). dial-X: BE004's dial; "
             "never-X: the signal never on. memory4@D: a 4 x 4 memory damage, the signal at D + 1 to D + 1,000 (D = 0, 900, "
             "1,800, 2,700, 3,600, 4,500, 5,400, 7,200: 0, 3, 6, 9, 12, 15, 18, 24 h at 300 updates an hour). gain(c, D): "
             "dial-c's r_in at D + 4,000 less never-c's at that read; remaining effect: gain(c, D) / gain(c, 0), pooled over "
             "the twelve unit-body pairs. S_pop: the drawn distribution's share of tau_x after the signal's first update; "
             "S_case, q_cell: the drawn cases' and patch cells' share (case-matched); pred_case, pred_cell: every case or "
             "patch cell all or none by its own draw, times SL's gain of the same case.", "",
             "## Registered statements", "", "| Id | Verdict | Claim |", "|---|---|---|"]
    lines += [f"| {x['id']} | {S[x['id']]['verdict']} | {x['claim']} |" for x in stm]
    lines += ["", "## The remaining effect by delay, pooled over the twelve unit-body pairs", "",
              "| D | D (h) | S_pop | S_case | q_cell | " + " | ".join(f"gain {c}" for c in D.CLOCKS) + " | pred_case | pred_cell | "
              + " | ".join(f"R {c}" for c in D.CLOCKS) + " |", "|---" * (7 + 2 * len(D.CLOCKS)) + "|"]
    g0 = {c: pooled(lambda u, b, c=c: gain(u, b, c, 0)) for c in D.CLOCKS}
    curves = {c: [1.0] for c in D.CLOCKS}
    lines.append(f"| 0 | 0 | 1 | 1 | 1 | " + " | ".join(f(g0[c]) for c in D.CLOCKS) + " | — | — | " + " | ".join("1" for _ in D.CLOCKS) + " |")
    for d in D.DELAYS:
        dv = lambda k: pooled(lambda u, b: L[u][b]["_derived"][k][str(d)][0])
        g = {c: pooled(lambda u, b, c=c: gain(u, b, c, d)) for c in D.CLOCKS}
        for c in D.CLOCKS:
            curves[c].append(g[c] / g0[c])
        lines.append(f"| {d:,} | {D.hours(d):g} | {f(D.survival(d))} | {f(dv('S_case'))} | {f(dv('q_cell'))} | "
                     + " | ".join(f(g[c]) for c in D.CLOCKS) + f" | {f(dv('pred_case'))} | {f(dv('pred_cell'))} | "
                     + " | ".join(f(g[c] / g0[c]) for c in D.CLOCKS) + " |")
    ds = (0,) + D.DELAYS
    lines += ["", "## Against the planarian landmarks (octanol: best within 3-6 h, under 60 % of its effect after 12 h, "
              "none later)", "", "| Clock | half effect (h) | R at 6 h | R at 12 h | R at 15 h | R at 18 h | R at 24 h |",
              "|---|---|---|---|---|---|---|"]
    for c in D.CLOCKS:
        h = half_effect(ds, curves[c])
        r = dict(zip(ds, curves[c]))
        lines.append(f"| {c} | {'none' if h is None else f'{D.hours(h):.1f}'} | " + " | ".join(f(r[x]) for x in (1800, 3600, 4500, 5400, 7200)) + " |")
    lines += ["", "## Reported, not registered: the share of cases repaired (a prompt gain above 0 and a late gain at least "
              "half of it; the denominator all cases), pooled over the pairs", "", "| Clock | " + " | ".join(f"{D.hours(d):g} h" for d in D.DELAYS) + " |",
              "|---|" + "---|" * len(D.DELAYS)]
    for c in D.CLOCKS:
        lines.append(f"| {c} | " + " | ".join(f(pooled(lambda u, b, d=d: L[u][b]['_derived'][f'rep_{c}'][str(d)][0]))
                                                for d in D.DELAYS) + " |")
    rep_path = a.out / "reported.json"
    if rep_path.exists():
        R = json.loads(rep_path.read_text())["reported"]
        ci = lambda k: f"{R[k]['mean']:+.4f} [{R[k]['lo95']:+.4f}, {R[k]['hi95']:+.4f}]"
        lines += ["", "## Reported, not registered: the case-matched deviations and the case-level contrast, pooled over the "
                  "pairs (mean over blocks [95% t interval])", "",
                  "| D | D (h) | dev_case | dev_cell | rep CELL - rep CASE |", "|---|---|---|---|---|"]
        for d in D.DELAYS:
            lines.append(f"| {d:,} | {D.hours(d):g} | {ci(f'dev_case@{d}')} | {ci(f'dev_cell@{d}')} | "
                         f"{ci(f'rep_CELL-rep_CASE@{d}')} |")
        lines += ["", f"gain(C12, 2,700) - gain(CASE, 2,700): {ci('gain_C12-gain_CASE@2700')}; gain(C12, 2,700) - "
                  f"gain(SL, 2,700) (the signal still on at C12's execution): {ci('gain_C12-gain_SL@2700')}."]
    lines += ["", "## The late signals by pair: gain, executed share before the signal, sensors and hit", "",
              "| Unit | Body | Clock | D (h) | late | none | gain | exec_pre | executed | sensors | hit |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for u, b in pairs:
        for c in D.CLOCKS:
            for d in D.DELAYS:
                rn, arm = D.where(c, d)
                t = d + D.AFTER
                n = L[u][b][rn][arm]
                lines.append(f"| {u} | {b} | {c} | {D.hours(d):g} | {f(r_at(u, b, rn, arm, t))} | "
                             f"{f(r_at(u, b, mem0, f'never-{c}', t))} | {f(gain(u, b, c, d))} | {f(n['exec_pre'][0])} | "
                             f"{f(n['executed'][0])} | {f(n['anc_on_share'][0])} | {f(n['hit'][0])} |")
    lines += ["", f"## memory4@0: r_in by read (updates; hours at {D.TAU_M} an hour); rows unit, body and arm", "",
              "| Unit | Body | Arm | " + " | ".join(f"{t:,} ({D.hours(t):.1f} h)" for t in reads[mem0]) + " |",
              "|---|---|---|" + "---|" * len(reads[mem0])]
    for u, b in pairs:
        for arm in D.RUNS[0][3]:
            lines.append(f"| {u} | {b} | {arm} | " + " | ".join(f(x[0]) for x in L[u][b][mem0][arm]["r_in"]) + " |")
    (a.out / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
