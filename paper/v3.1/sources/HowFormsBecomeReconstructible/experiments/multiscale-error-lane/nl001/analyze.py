"""NL001's frozen reader: block means of every endpoint, the registered statements.

python -m nl001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases (NaN cases, where an endpoint's mask is empty, left out),
then the mean (and SD) over blocks. The statements are scored on these unrounded means at the last read
(nl001.predict.score); the written summaries (one per event, every git file under 256 KB) round to 6 decimals.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from nl001 import design as D  # noqa: E402
from nl001.predict import score  # noqa: E402
from nl001.sim import ENDS  # noqa: E402


def block_means(root, blocks):
    """B[event][arm][endpoint] = (blocks, reads) array of case means."""
    out = {}
    for e in D.EVENTS:
        per = []
        for b in blocks:
            with np.load(root / "shards" / e / f"{b}.npz") as z:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    per.append({k: np.nanmean(z[f"{e}/{k}"], axis=-1) for k in ENDS})      # (reads, arms)
        out[e] = {a: {k: np.stack([p[k][:, ai] for p in per]) for k in ENDS} for ai, a in enumerate(D.RUNS[e])}
    return out


def ms(v):
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return [None, None]
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(B):
    return {e: {a: {k: [ms(x[:, ri]) for ri in range(x.shape[1])] for k, x in node.items()} for a, node in arms.items()}
            for e, arms in B.items()}


def rounded(x, d=6):
    if isinstance(x, dict):
        return {k: rounded(v, d) for k, v in x.items()}
    if isinstance(x, list):
        return [rounded(v, d) for v in x]
    return None if x is None else round(x, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    B = block_means(root, blocks)
    L = levels(B)
    get = lambda arm, event, ep: float(np.nanmean(B[event][arm][ep][:, -1]))
    S = score(get, D.RUNS)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "runs": D.RUNS}
    for e in D.EVENTS:
        (a.out / f"summary_{e}.json").write_text(json.dumps(dict(head, event=e, levels=rounded(L[e])), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
