"""LR003's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m lr003.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block (same cases and noise), with 95% t intervals over blocks.
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

from lr003 import design as D  # noqa: E402
from lr003.predict import score  # noqa: E402

SNAP_EPS = ("sign", "r_sign", "agree", "bond_err")
NAMES = [c.name for c in D.CONDS]
PAIRS = (("site", "body"), ("site", "syndrome"), ("syndrome", "body"), ("site+parity", "record+parity"),
         ("site+parity", "site"), ("site+parity", "body+parity"), ("agree", "record"), ("agree", "body"),
         ("body", "record+parity"))


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
    """levels[unit][body][condition][endpoint@t] = [mean over blocks, SD over blocks]; condition = 'rate/repair'."""
    out = {}
    for u, arrs in data.items():
        for b in D.BODIES:
            node = out.setdefault(u, {}).setdefault(b, {})
            for ep in SNAP_EPS:
                x = arrs[f"{b}/{ep}"]
                for si, t in enumerate(D.READS):
                    for ci, c in enumerate(NAMES):
                        node.setdefault(c, {})[f"{ep}@{t}"] = ms(x[:, si, ci])
            for ep in ("flip_rate", "opened"):
                x = arrs[f"{b}/{ep}"]
                for ci, c in enumerate(NAMES):
                    node[c][ep] = ms(x[:, ci], 6)
    return out


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_sources.csv: the gates against the other teachers at t = 4000 (record and body agreement);
    contrasts_bodies.csv: li4 - dw under every condition at t = 4000."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    src, bod = [], []
    t1 = D.READS[-1]
    for u, arrs in data.items():
        for ep in ("r_sign", "sign"):
            for b in D.BODIES:
                x = arrs[f"{b}/{ep}"][:, -1]
                for rate in D.RATES:
                    for r1, r2 in PAIRS:
                        i1, i2 = NAMES.index(f"{rate:g}/{r1}"), NAMES.index(f"{rate:g}/{r2}")
                        src.append(row(u, f"{b}:{rate:g}/{r1}-{rate:g}/{r2}", ep, t1, x[:, i1] - x[:, i2]))
            x1, x0 = arrs[f"li4/{ep}"][:, -1], arrs[f"dw/{ep}"][:, -1]
            for ci, c in enumerate(NAMES):
                bod.append(row(u, f"li4-dw:{c}", ep, t1, x1[:, ci] - x0[:, ci]))
    for name, rows in (("contrasts_sources.csv", src), ("contrasts_bodies.csv", bod)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr003")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "levels": L, "statements": S}
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
