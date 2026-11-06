"""NL002's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m nl002.analyze --root RUN_ROOT --stage {preflight,development,probe} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases (NaN cases, an endpoint undefined for that case, are left
out of that case mean), then the mean (and SD) over blocks. The statements are scored on these unrounded means; the
written summaries round to 6 decimals. Contrasts are paired within block (the same cases, acquisitions, noise and event).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from nl002 import design as D  # noqa: E402
from nl002.predict import score  # noqa: E402
from nl002.worker import BRANCHES2  # noqa: E402

LABELNAMES = tuple(f"{a}/{e}" for a, e in D.LABELS)
CKEYS = ("min_reg_ok_A", "ev_reg_ok", "spec_reg", "k_spec_reg")                  # the contrasts' endpoints
STORE = ("region_ok_A", "min_reg_ok_A", "min_cell_ok_A", "ev_reg_ok", "spec_reg", "spec_cell", "k_reg_ok_A",
         "k_min_ok_A", "k_spec_reg")                                                # the summaries' endpoints (<= 256 KB)
SRC = ("t/", "s/", "c/")                                                            # tissue, L1-only and coded recipients


def load(root, blocks, units=D.UNITS):
    """data[unit][key] = (blocks, ...) arrays, every case kept."""
    data = {}
    for u in units:
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[u] = {k: np.stack(v) for k, v in arrs.items()}
    return data


def block_means(x):
    """(blocks, ..., cases) -> (blocks, ...): the case mean, NaN cases left out."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(x, axis=-1)


def ms(v):
    v = np.asarray(v, float)
    return [float(np.mean(v)), float(np.std(v, ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[unit][key][branch] = [[mean, SD] over blocks at each read]; key 't/r/<e>', 't/v/<e>' (the tissue's record and
    body, branches LABELNAMES), 's/<e>' (the L1-only recipient's body, branches BRANCHES2) or 'c/<e>' (the coded
    recipient's body, branches LABELNAMES); L[unit]['dose'][label] = [mean, SD]. Unrounded. A block's mean leaves out
    the cases where an endpoint is undefined (NaN: a killed square with no differing region)."""
    L = {}
    for u, arrs in data.items():
        node = L.setdefault(u, {})
        for key, x in arrs.items():
            if key.startswith(SRC):
                names = BRANCHES2 if key.startswith("s/") else LABELNAMES
                bm = block_means(x)                              # (blocks, reads, branches)
                node[key] = {nm: [ms(bm[:, ti, bi]) for ti in range(bm.shape[1])] for bi, nm in enumerate(names)}
            elif key == "dose":
                bm = block_means(x)                              # (blocks, labels)
                node["dose"] = {nm: ms(bm[:, bi]) for bi, nm in enumerate(LABELNAMES)}
            else:
                node[key] = ms(block_means(x))
    return L


def rounded(x, d=6):
    if isinstance(x, dict):
        return {k: rounded(v, d) for k, v in x.items()}
    if isinstance(x, list):
        return [rounded(v, d) for v in x]
    return None if x is None else round(x, d)


def row(unit, contrast, ep, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * np.std(v, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(np.mean(v))
    return [unit, contrast, ep, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()), int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_arms.csv: at the last read, for the endpoints in CKEYS, every arm against 'off' in the same event
    (record, body and recipient), copy against own and copy against foreign at each gain, paired within block."""
    head = ["unit", "contrast", "endpoint", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    li = {nm: i for i, nm in enumerate(LABELNAMES)}
    for u, arrs in data.items():
        for key in sorted(k for k in arrs if k.startswith(SRC) and k.split("/")[-1] in CKEYS):
            bm = block_means(arrs[key])[:, -1]                  # (blocks, branches) at the last read
            li = {nm: i for i, nm in enumerate(BRANCHES2 if key.startswith("s/") else LABELNAMES)}
            for e in D.EVENTS:
                for a in D.ARMNAMES:
                    if a == "off":
                        continue
                    rows.append(row(u, f"{a}/{e} - off/{e}", key, bm[:, li[f"{a}/{e}"]] - bm[:, li[f"off/{e}"]]))
                for g in D.GAINS2:
                    rows.append(row(u, f"copy-k{g:g}/{e} - own-k{g:g}/{e}", key, bm[:, li[f"copy-k{g:g}/{e}"]] - bm[:, li[f"own-k{g:g}/{e}"]]))
                    rows.append(row(u, f"copy-k{g:g}/{e} - foreign-k{g:g}/{e}", key, bm[:, li[f"copy-k{g:g}/{e}"]] - bm[:, li[f"foreign-k{g:g}/{e}"]]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development", "probe"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl002")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    if a.stage == "probe":                      # P40's shards (the reader run unstubbed before the freeze)
        blocks = list(range(*D.PROBE_BLOCKS))
    else:
        blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "units": list(D.UNITS),
            "labels": list(LABELNAMES), "branches2": list(BRANCHES2), "reads": list(D.READS), "reads2": list(D.READS2)}
    for u in D.UNITS:                            # one summary per unit: every git file < 256 KB
        keep = {k: v for k, v in L[u].items() if not k.startswith(SRC) or k.split("/")[-1] in STORE}
        (a.out / f"summary_{u}.json").write_text(json.dumps(dict(head, levels=rounded(keep)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
