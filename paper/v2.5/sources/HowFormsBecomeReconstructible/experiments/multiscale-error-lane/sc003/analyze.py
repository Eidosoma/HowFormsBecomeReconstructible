"""SC003's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m sc003.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are
scored on the unrounded block means (sc003.predict.score); the files written round once, at the end. Contrasts are
paired within block (same cases, noise, events and population history), with 95% t intervals over blocks.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from sc003 import design as D  # noqa: E402
from sc003.predict import score  # noqa: E402
from sc003.worker import ENDS  # noqa: E402

PAIRS_T = (("iso-3", "inst-3"), ("emt-300", "inst-3"), ("iso-emt-300", "emt-300"), ("mat-300", "emt-300"),
           ("mat-300", "iso-emt-300"), ("mat-300", "inst-3"), ("emt-1000", "inst-3"), ("iso-emt-1000", "emt-1000"),
           ("mat-1000", "emt-1000"), ("mat-1000", "iso-emt-1000"), ("mat-1000", "inst-3"), ("inst-3", "cue"),
           ("iso-3", "cue"))
PAIRS_W = (("iso-3", "inst-3"), ("mat-300", "inst-3"), ("mat-1000", "inst-3"), ("mat-300", "iso-3"),
           ("mat-1000", "iso-3"), ("inst-3", "cue"))


def load(root, blocks):
    """B[(unit, body)][key] = array over blocks of each block's mean over its cases (unrounded)."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(u, body)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}      # block means over cases
    return data


def ms(v, d=5):
    return [round(float(v.mean()), d), round(float(v.std(ddof=1)), d) if len(v) > 1 else None]


def levels(data):
    """levels[unit][body][run][arm][endpoint] = [[mean over blocks, SD over blocks] at each of READS]; 'opened' and
    'newc' (new commitments per case by the cell's age, AGE_BINS) as [mean, SD]; 'births' per site over the window.
    traces[body][unit][run][arm] = {'r_in', 'r_all'}: the means over blocks every TRACE updates."""
    out, traces = {}, {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            arms = D.arms_of(run)
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            tnode = traces.setdefault(b, {}).setdefault(u, {}).setdefault(rn, {})
            node["births"] = ms(arrs[f"{rn}/births"])
            for ai, arm in enumerate(arms):
                n = node.setdefault(arm, {})
                for e in ENDS:
                    if f"{rn}/{e}" in arrs:
                        n[e] = [ms(arrs[f"{rn}/{e}"][:, ti, ai]) for ti in range(len(D.READS))]
                n["opened"] = ms(arrs[f"{rn}/opened"][:, ai], 6)
                n["newc"] = [ms(arrs[f"{rn}/newc"][:, q, ai] * D.SIDE * D.SIDE, 3) for q in range(len(D.AGE_BINS))]
                tnode[arm] = {"r_in": np.round(arrs[f"{rn}/trace"][:, :, ai].mean(0), 4).tolist(),
                              "r_all": np.round(arrs[f"{rn}/trace_all"][:, :, ai].mean(0), 4).tolist()}
    return out, traces


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_arms.csv: arm against arm at t = 4000: the record inside the patch (r_in; for change also r_in_old) and
    outside it (r_out) for the patch events, and over the sheet (r_all) for none and cue."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    t1 = D.READS[-1]
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            arms = D.arms_of(run)
            s = run[2]
            eps = ("r_all",) if s in ("none", "cue") else (("r_in", "r_in_old") if s == "change" else ("r_in", "r_out"))
            for e in eps:
                x = arrs[f"{rn}/{e}"][:, -1]
                for a1, a2 in (PAIRS_T if run[0] == "T" else PAIRS_W):
                    i1, i2 = arms.index(a1), arms.index(a2)
                    rows.append(row(u, f"{b}/{rn}:{a1}-{a2}", e, t1, x[:, i1] - x[:, i2]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sc003")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L, TR = levels(data)
    S = score(data)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "arms_t": D.ARMS_T, "arms_w": D.ARMS_W, "age_bins": D.AGE_BINS, "runs": list(D.RUNNAMES)}
    for b in D.BODIES:                          # one summary and one trace file per body keeps every git file < 256 KB
        Lb = {u: {b: L[u][b]} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=Lb), separators=(",", ":")) + "\n")
        (a.out / f"traces_{b}.json").write_text(json.dumps(dict(head, every=D.TRACE, traces=TR[b]), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
