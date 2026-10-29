"""FN001's reader (draft): block means of every endpoint, the registered statements, paired contrasts.

python -m fn001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block (same cases and noise), with 95% t intervals over blocks. The read at t = T_W1 is every branch's pre-wound
baseline.
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

from fn001 import design as D  # noqa: E402
from fn001.predict import score  # noqa: E402

NAMES = [c.name for c in D.CONDS]
CONTRAST_EPS = ("patch", "intact", "defects", "sign", "r_patch")


def read_levels(out):
    """The levels written by main, as levels[unit][body][endpoint]."""
    per = {b: json.loads((out / f"levels_{b}.json").read_text()) for b in D.BODIES}
    return {u: {b: per[b][u] for b in D.BODIES} for u in per[D.BODIES[0]]}


def load(root, blocks):
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[u] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}      # (blocks, reads, conds): means over cases
    return data


def ms(v, d=4):
    return [round(float(v.mean()), d), round(float(v.std(ddof=1)), d) if len(v) > 1 else None]


SD_EPS, SD_READS = ("sign", "patch", "intact", "defects"), (D.T_W2, D.READS[-1])


def levels(data, full=False):
    """levels[unit][body][endpoint] = {"mean": [read][condition]} (conditions in design.CONDS order, reads in
    design.READS order), with "sd" over blocks for SD_EPS at SD_READS ([read][condition]); full=True keeps every SD."""
    out = {}
    for u, arrs in data.items():
        for b in D.BODIES:
            node = out.setdefault(u, {}).setdefault(b, {})
            for ep in D.ENDPOINTS:
                x = arrs[f"{b}/{ep}"]                                        # (blocks, reads, conds)
                node[ep] = {"mean": np.round(x.mean(0), 4).tolist()}
                if full or ep in SD_EPS:
                    rd = range(len(D.READS)) if full else [D.READS.index(t) for t in SD_READS]
                    sd = x.std(0, ddof=1) if x.shape[0] > 1 else np.full(x.shape[1:], np.nan)
                    node[ep]["sd"] = np.round(sd[list(rd)], 4).tolist()
    return out


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_capacity.csv: W12 - W2 and W12x - W2x (same teacher, rate, body and place) at the last read;
    contrasts_teachers.csv: vote - body, site - body and record+parity - body after the first wound (W12)."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    cap, tea = [], []
    after2 = [D.READS[-1]]
    for u, arrs in data.items():
        for b in D.BODIES:
            for ep in CONTRAST_EPS:
                x = arrs[f"{b}/{ep}"]
                for rate in D.RATES:
                    for rep in D.REPAIRS:
                        for s1, s2 in (("W12", "W2"), ("W12x", "W2x")):
                            i1, i2 = NAMES.index(f"{rate:g}/{rep}/{s1}"), NAMES.index(f"{rate:g}/{rep}/{s2}")
                            for t in after2:
                                si = D.READS.index(t)
                                cap.append(row(u, f"{b}:{rate:g}/{rep}/{s1}-{s2}", ep, t, x[:, si, i1] - x[:, si, i2]))
                    ib = NAMES.index(f"{rate:g}/body/W12")
                    si = D.READS.index(D.T_W2)
                    for rep in ("vote", "site", "record+parity"):
                        i1 = NAMES.index(f"{rate:g}/{rep}/W12")
                        tea.append(row(u, f"{b}:{rate:g}/{rep}-body", ep, D.T_W2, x[:, si, i1] - x[:, si, ib]))
    for name, rows in (("contrasts_capacity.csv", cap), ("contrasts_teachers.csv", tea)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "fn001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(),
               "layout": "levels_<body>.json: [unit][endpoint]['mean'][read][condition]; 'sd' at reads " + str(list(SD_READS)),
               "reads": list(D.READS), "conds": NAMES, "statements": S}
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    for b in D.BODIES:                                                   # one file per body keeps each under 256 KB
        (a.out / f"levels_{b}.json").write_text(json.dumps({u: L[u][b] for u in L}, separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    (root / "levels_full.json").write_text(json.dumps(levels(data, full=True), separators=(",", ":")) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
