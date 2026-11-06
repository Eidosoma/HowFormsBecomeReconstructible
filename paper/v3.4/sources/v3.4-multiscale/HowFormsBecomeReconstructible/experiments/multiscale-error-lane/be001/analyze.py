"""BE001's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m be001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block (same cases, noise and event), with 95% t intervals over blocks.
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

from be001 import design as D  # noqa: E402
from be001.predict import score  # noqa: E402
from be001.worker import ENDS  # noqa: E402

PAIRS = (("bio-1.5", "community-s"), ("bio-1.5-cautious", "community-c"), ("bio-1", "bio-1.5"), ("bio-1.5", "bio-2"),
         ("bio-2", "bio-3"), ("bio-2-gated", "bio-2"), ("bio-2-noisy", "bio-2"), ("bio-1.5", "bio-1.5-cautious"),
         ("community-s", "cue"))
RUNNAMES = [D.run_name(s, z) for s, z in D.RUNS]


def load(root, blocks):
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[u] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}      # block means over cases
    return data


def ms(v, d=4):
    return [round(float(v.mean()), d), round(float(v.std(ddof=1)), d) if len(v) > 1 else None]


def levels(data):
    """levels[unit][body][run][arm][endpoint] = [[mean over blocks, SD over blocks] at each of READS];
    'opened' = [mean, SD]. traces[unit][body][run][arm] = the record's mean agreement inside the patch every 2 x TRACE
    updates."""
    out, traces = {}, {}
    for u, arrs in data.items():
        for b in D.BODIES:
            for rn in RUNNAMES:
                key = f"{b}/{rn}"
                node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                tnode = traces.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                for ai, arm in enumerate(D.ARMS):
                    n = node.setdefault(arm, {})
                    for e in ENDS:
                        if f"{key}/{e}" in arrs:
                            n[e] = [ms(arrs[f"{key}/{e}"][:, ti, ai]) for ti in range(len(D.READS))]
                    n["opened"] = ms(arrs[f"{key}/opened"][:, ai], 6)
                    tnode[arm] = np.round(arrs[f"{key}/trace"][:, 1::2, ai].mean(0), 3).tolist()
    return out, traces


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_arms.csv: arm against arm at t = 4000: the record inside the patch (r_in; for change also r_in_old),
    and over the sheet (r_all) for the runs without a patch event (none, cue)."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    t1 = D.READS[-1]
    for u, arrs in data.items():
        for b in D.BODIES:
            for (s, z), rn in zip(D.RUNS, RUNNAMES):
                eps = ("r_all",) if s in ("none", "cue") else (("r_in", "r_in_old") if s == "change" else ("r_in",))
                for e in eps:
                    x = arrs[f"{b}/{rn}/{e}"][:, -1]
                    for a1, a2 in PAIRS:
                        i1, i2 = D.ARMS.index(a1), D.ARMS.index(a2)
                        rows.append(row(u, f"{b}/{rn}:{a1}-{a2}", e, t1, x[:, i1] - x[:, i2]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L, TR = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "arms": D.ARMS, "runs": RUNNAMES}
    for b in D.BODIES:                          # one summary per body keeps every git file under 256 KB
        Lb = {u: {b: L[u][b]} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=Lb), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=TR), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
