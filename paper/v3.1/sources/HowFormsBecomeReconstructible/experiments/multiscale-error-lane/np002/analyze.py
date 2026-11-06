"""NP002's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m np002.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. Derived quantities (np002.predict):
  q      the body's preference (align - align_b) / (1 - a0): +1 at the record's pattern, -1 at the body's initial one
  q_rel  the record's relational preference (r_abs - r_abs_b) / (1 - |2 a0 - 1|), where r_abs = |2 r_align - 1| per case:
         the same, up to the record's global sign (a record of relations cannot tell a pattern from its inverse)
  q_bond the record's bonds' preference (bond_b - bond_err) / (1 - b0) at the last read: +1 when its bonds are the
         history's relations, -1 when they are the body's initial pattern's (reported, not registered)
Contrasts are paired within block (the same cases, acquisitions and noise), with 95% t intervals over blocks, at the
last reads (stage 1 at 4,000, stage 2 at 2,000): every condition's q and q_rel; at each race gain, q(intact@g) -
q(body@g); for the spacing conflicts, every stage-2 branch against the successor's no-record control (align and
align_b).
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

from np002 import design as D  # noqa: E402
from np002.predict import score, q_body, q_bond, q_rec  # noqa: E402
from np002.sim import ENDS1, ENDS2  # noqa: E402
from np002.worker import BRANCHES2  # noqa: E402

ENDS1X = ENDS1 + ("abs", "abs_b", "r_abs", "r_abs_b")


def load(root, blocks):
    """data[(body, unit)][key] = (blocks, reads, branches) array of case means."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(body, u)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}
    return data


def ms(v):
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[body][unit]['s1'][cond][endpoint] and, for the spacing conflicts, L[body][unit]['s2'][successor][branch]
    [endpoint] = [[mean, SD] over blocks at each read]. Unrounded."""
    out = {}
    for (b, u), arrs in data.items():
        node = out.setdefault(b, {}).setdefault(u, {"s1": {}, "s2": {}})
        for ci, c in enumerate(D.CONDNAMES):
            node["s1"][c] = {e: [ms(arrs[f"s1/{e}"][:, ti, ci]) for ti in range(len(D.READS))] for e in ENDS1X}
            node["s1"][c]["bond_b"] = [ms(arrs["s1/bond_b"][:, 0, ci])]                 # the last read only
        if D.has_successors(u):
            for B in D.SUCC_BODIES:
                node["s2"][B] = {c: {e: [ms(arrs[f"s2/{B}/{e}"][:, ti, ci]) for ti in range(len(D.READS2))]
                                     for e in ENDS2} for ci, c in enumerate(BRANCHES2)}
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
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows1, rows2, t1, t2 = [], [], D.READS[-1], D.READS2[-1]
    for (b, u), arrs in data.items():
        x = {e: arrs[f"s1/{e}"][:, -1] for e in ("align", "align_b", "r_abs", "r_abs_b", "bond_err", "bond_b")}
        for ci, c in enumerate(D.CONDNAMES):
            rows1.append(row(u, f"{b}/s1:{c}", "q", t1, q_body(x["align"][:, ci], x["align_b"][:, ci], u)))
            rows1.append(row(u, f"{b}/s1:{c}", "q_rel", t1, q_rec(x["r_abs"][:, ci], x["r_abs_b"][:, ci], u)))
            rows1.append(row(u, f"{b}/s1:{c}", "q_bond", t1, q_bond(x["bond_err"][:, ci], x["bond_b"][:, ci], u)))
        for g in (D.GAIN,) + D.RACE_GAINS:
            ci = D.CONDNAMES.index("intact" if g == D.GAIN else f"intact@{g:g}")
            cj = D.CONDNAMES.index("body" if g == D.GAIN else f"body@{g:g}")
            rows1.append(row(u, f"{b}/s1:intact-body@{g:g}", "q", t1,
                             q_body(x["align"][:, ci], x["align_b"][:, ci], u) - q_body(x["align"][:, cj], x["align_b"][:, cj], u)))
        if D.has_successors(u):
            for e in ("align", "align_b"):
                for B in D.SUCC_BODIES:
                    y = arrs[f"s2/{B}/{e}"][:, -1]
                    for ci, c in enumerate(BRANCHES2[:-1]):
                        rows2.append(row(u, f"{b}/s2/{B}:{c}-none", e, t2, y[:, ci] - y[:, -1]))
    for name, rows in (("contrasts_stage1.csv", rows1), ("contrasts_stage2.csv", rows2)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "np002")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "reads2": D.READS2, "conds": D.CONDNAMES, "branches2": BRANCHES2, "a0": D.A0}
    for b in D.BODIES:                          # one summary per stage-1 body: every git file < 256 KB
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(L[b])), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
