"""LR002's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m lr002.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

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

from lr002 import design as D  # noqa: E402
from lr002.predict import score  # noqa: E402

SNAP_EPS = ("sign", "r_sign", "agree", "bond_err")
NAMES = [c.name for c in D.CONDS]


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
            x = arrs[f"{b}/flip_rate"]
            for ci, c in enumerate(NAMES):
                node[c]["flip_rate"] = ms(x[:, ci], 6)
    return out


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_sources.csv: body against record relearning (with and without parity) at every read, and every
    repair against none at t = 4000; contrasts_bodies.csv: li4 - dw under every condition at every read."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    src, bod = [], []
    for u, arrs in data.items():
        for ep in ("sign", "r_sign", "bond_err"):
            for b in D.BODIES:
                x = arrs[f"{b}/{ep}"]
                for rate in D.RATES:
                    for r1, r2 in (("body+parity", "record+parity"), ("body", "record")):
                        i1, i2 = NAMES.index(f"{rate:g}/{r1}"), NAMES.index(f"{rate:g}/{r2}")
                        for si, t in enumerate(D.READS):
                            src.append(row(u, f"{b}:{rate:g}/{r1}-{rate:g}/{r2}", ep, t, x[:, si, i1] - x[:, si, i2]))
                    i0 = NAMES.index(f"{rate:g}/none")
                    for rep in D.REPAIRS[1:]:
                        i1 = NAMES.index(f"{rate:g}/{rep}")
                        src.append(row(u, f"{b}:{rate:g}/{rep}-{rate:g}/none", ep, D.READS[-1], x[:, -1, i1] - x[:, -1, i0]))
        for ep in ("sign", "r_sign"):
            x1, x0 = arrs[f"li4/{ep}"], arrs[f"dw/{ep}"]
            for ci, c in enumerate(NAMES):
                for si, t in enumerate(D.READS):
                    bod.append(row(u, f"li4-dw:{c}", ep, t, x1[:, si, ci] - x0[:, si, ci]))
    for name, rows in (("contrasts_sources.csv", src), ("contrasts_bodies.csv", bod)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "lr002")
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
