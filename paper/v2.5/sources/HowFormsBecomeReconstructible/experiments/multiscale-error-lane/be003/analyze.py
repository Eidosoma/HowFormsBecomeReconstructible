"""BE003's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m be003.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. Contrasts are paired within block (same cases, noise,
events and population history), with 95% t intervals over blocks.
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

from be003 import design as D  # noqa: E402
from be003.predict import score  # noqa: E402
from be003.worker import ENDS  # noqa: E402

PAIRS = (("mat-300", "inst-3"), ("mat-1000", "inst-3"), ("dial", "inst-3"), ("mat-dial", "inst-3"),
         ("mat-dial", "mat-300"), ("mat-dial", "dial"), ("dial", "inst-1"), ("mat-300", "inst-1.5"),
         ("inst-1", "inst-3"), ("inst-3", "cue"))
REGION_ENDS = {"regrow": ("r_in", "r_ring", "r_out", "r_all"), "regrow+cue": ("r_in", "r_ring", "r_out", "r_all"),
               "twin": ("r_young", "r_twin", "r_in", "r_out", "r_young_old", "r_twin_old")}


def load(root, blocks):
    """data[(unit, body)][key] = (blocks, ...) array of case means."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(u, body)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}
    return data


def ms(v):
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[unit][body][run][arm][endpoint] = [[mean, SD] over blocks at each of the run's reads]; opened and opened_out
    = [mean, SD]. Unrounded."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            for ai, arm in enumerate(D.run_arms(*run)):
                n = node.setdefault(arm, {})
                for e in ENDS:
                    if f"{rn}/{e}" in arrs:
                        x = arrs[f"{rn}/{e}"]
                        n[e] = [ms(x[:, ti, ai]) for ti in range(x.shape[1])]
                for e in ("opened", "opened_out"):
                    n[e] = ms(arrs[f"{rn}/{e}"][:, ai])
    return out


def traces(data):
    """T[unit][body][run][arm][x] = the mean over blocks every 2 x TRACE updates (x: r_in, r_young, r_twin, r_all)."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            for ai, arm in enumerate(D.run_arms(*run)):
                node[arm] = {x: np.round(arrs[f"{rn}/trace_{x}"][:, 1::2, ai].mean(0), 4).tolist() for x in ("r_in", "r_young", "r_twin", "r_all")}
    return out


def rounded(x, d=6):
    if isinstance(x, dict):
        return {k: rounded(v, d) for k, v in x.items()}
    if isinstance(x, list):
        return [rounded(v, d) for v in x]
    return None if x is None else round(x, d)


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_arms.csv: arm against arm at each run's last read, by region."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            arms = D.run_arms(*run)
            t1 = D.run_reads(*run)[-1]
            for e in REGION_ENDS[run[0]]:
                if f"{rn}/{e}" not in arrs:
                    continue
                x = arrs[f"{rn}/{e}"][:, -1]
                for a1, a2 in PAIRS:
                    if a1 in arms and a2 in arms:
                        rows.append(row(u, f"{b}/{rn}:{a1}-{a2}", e, t1, x[:, arms.index(a1)] - x[:, arms.index(a2)]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be003")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(),
            "runs": list(D.RUNNAMES), "run_arms": {rn: D.run_arms(*x) for x, rn in zip(D.RUNS, D.RUNNAMES)},
            "run_reads": {rn: D.run_reads(*x) for x, rn in zip(D.RUNS, D.RUNNAMES)}}
    for b in D.BODIES:                          # one summary per body keeps every git file under 256 KB
        Lb = {u: {b: L[u][b]} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(Lb)), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
