"""LR005's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m lr005.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

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

from lr005 import design as D  # noqa: E402
from lr005.predict import score  # noqa: E402
from lr005.worker import ENDS  # noqa: E402

PAIRS = (("community-s", "body"), ("community-s", "vote2r"), ("community-s", "cue"), ("community-s", "vote3"),
         ("community-s", "record+parity"), ("community-c", "community-s"), ("community-c", "body"),
         ("body", "vote2r"), ("body", "record+parity"), ("vote2r", "record+parity"), ("cue", "vote3"))


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
    """levels[unit][body][gain][situation][arm][endpoint] = [[mean over blocks, SD over blocks] at each of READS];
    'opened' = [mean, SD]. traces[unit][body][gain][situation][arm] = the mean agreement of the record inside the patch
    every 2 x TRACE updates."""
    out, traces = {}, {}
    for u, arrs in data.items():
        for b in D.BODIES:
            for g in D.GAINS:
                for s in D.SITUATIONS:
                    key = f"{b}/{g:g}/{s}"
                    node = out.setdefault(u, {}).setdefault(b, {}).setdefault(f"{g:g}", {}).setdefault(s, {})
                    tnode = traces.setdefault(u, {}).setdefault(b, {}).setdefault(f"{g:g}", {}).setdefault(s, {})
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
    """contrasts_arms.csv: arm against arm, the record inside the patch at t = 4000 (r_in; for change also r_in_old);
    contrasts_gains.csv: read gain 0.05 - 0.2 for every arm and situation."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    arm_rows, gain_rows = [], []
    t1 = D.READS[-1]
    for u, arrs in data.items():
        for b in D.BODIES:
            for s in D.SITUATIONS:
                eps = ("r_in", "v_in", "r_in_old") if s == "change" else ("r_in", "v_in")
                for e in eps:
                    for g in D.GAINS if e != "v_in" else ():          # arm contrasts on the record only
                        x = arrs[f"{b}/{g:g}/{s}/{e}"][:, -1]
                        for a1, a2 in PAIRS:
                            i1, i2 = D.ARMS.index(a1), D.ARMS.index(a2)
                            arm_rows.append(row(u, f"{b}/{g:g}/{s}:{a1}-{a2}", e, t1, x[:, i1] - x[:, i2]))
                    lo, hi = (arrs[f"{b}/{g:g}/{s}/{e}"][:, -1] for g in D.GAINS)
                    for ai, arm in enumerate(D.ARMS):
                        gain_rows.append(row(u, f"{b}/{s}/{arm}:{D.GAINS[0]:g}-{D.GAINS[1]:g}", e, t1, lo[:, ai] - hi[:, ai]))
    for name, rows in (("contrasts_arms.csv", arm_rows), ("contrasts_gains.csv", gain_rows)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr005")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L, TR = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS}
    for b in D.BODIES:                          # one summary per body keeps every git file under 256 KB
        Lb = {u: {b: L[u][b]} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=Lb), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=TR), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
