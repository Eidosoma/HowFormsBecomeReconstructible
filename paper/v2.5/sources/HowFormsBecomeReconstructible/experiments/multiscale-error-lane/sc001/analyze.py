"""SC001's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m sc001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases (ignoring cases whose region had no occupied cell yet, NaN),
then the mean (and SD) over blocks. Contrasts are paired within block (same cases, streams and division histories),
with 95% t intervals over the blocks where both sides are defined. NaN is written as null.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from sc001 import design as D  # noqa: E402
from sc001.predict import score  # noqa: E402
from sc001.worker import FUNC, G_SNAP, G_TRACE, R_READ, R_TRACE  # noqa: E402

ARMS = [a.name for a in D.ARMS_G]
CONDS = [c.name for c in D.CONDS_R]
PAIRS_G = (("grow/100", "front/100"), ("nb/100", "grow/100"), ("smooth/100", "grow/100"), ("smooth/100", "front/100"),
           ("grow/200", "grow/100"), ("grow/200", "front/200"), ("grow/25", "front/25"), ("diff6/100", "grow/100"),
           ("diff1.5/100", "grow/100"), ("diff1.5/100", "diff6/100"), ("turn/100", "grow/100"), ("none/100", "grow/100"))
PAIRS_R = (("regrow@{s}", "reset"), ("regrow@{s}", "regrow-nb@{s}"), ("regrow-nb@{s}", "reset"))


def nanmean(x, axis):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(x, axis)


def clean(v, d=4):
    v = float(v)
    return None if math.isnan(v) else round(v, d)


def load(root, blocks):
    """data[(panel, unit)][key] = (blocks, ...) case means."""
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        x = z[k]
                        arrs.setdefault(k, []).append(nanmean(x, 1) if k.endswith("/profile") else nanmean(x, -1))
        data[(p, u)] = {k: np.stack(v) for k, v in arrs.items()}
    return data


def ms(v, d=4):
    v = np.asarray(v, float)
    ok = v[~np.isnan(v)]
    if len(ok) == 0:
        return [None, None]
    return [round(float(ok.mean()), d), round(float(ok.std(ddof=1)), d) if len(ok) > 1 else None]


def levels(data):
    """L['G'][unit][body][geo][arm][endpoint] = [[mean, SD] at each snapshot] (function endpoints [mean, SD];
    profile and traces: means over blocks); L['R'][unit][body][cond] likewise over READS_R."""
    L = {"G": {}, "R": {}}
    for (p, u), arrs in data.items():
        if p == "G":
            for b in D.BODIES:
                for g in D.GEOMS:
                    for ai, arm in enumerate(ARMS):
                        n = L["G"].setdefault(u, {}).setdefault(b, {}).setdefault(g, {}).setdefault(arm, {})
                        for e in G_SNAP:
                            n[e] = [ms(arrs[f"{b}/{g}/{e}"][:, si, ai]) for si in range(len(D.SNAPS))]
                        for e in FUNC:
                            n[e] = ms(arrs[f"{b}/{g}/{e}"][:, ai])
                        n["profile"] = [clean(x) for x in nanmean(arrs[f"{b}/{g}/profile"][:, ai], 0)]
                        for e in G_TRACE:
                            n[e] = [clean(x, 3) for x in nanmean(arrs[f"{b}/{g}/{e}"][:, :, ai], 0)]
        else:
            for b in D.BODIES:
                for ci, c in enumerate(CONDS):
                    n = L["R"].setdefault(u, {}).setdefault(b, {}).setdefault(c, {})
                    for e in R_READ:
                        n[e] = [ms(arrs[f"{b}/{e}"][:, ri, ci]) for ri in range(len(D.READS_R))]
                    for e in FUNC:
                        n[e] = ms(arrs[f"{b}/{e}"][:, ci])
                    for e in R_TRACE:
                        n[e] = [clean(x, 3) for x in nanmean(arrs[f"{b}/{e}"][:, :, ci], 0)]
    return L


def row(unit, contrast, ep, t, v):
    v = v[~np.isnan(v)]
    n = len(v)
    if n == 0:
        return [unit, contrast, ep, t, None, None, None, 0, 0, 0]
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), clean(m - half), clean(m + half), int((v > 0).sum()), int((v < 0).sum()), n]


def contrasts(data, out):
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = {"G": [], "R": []}
    for (p, u), arrs in data.items():
        if p == "G":
            for b in D.BODIES:
                for g in D.GEOMS:
                    for a1, a2 in PAIRS_G:
                        i1, i2 = ARMS.index(a1), ARMS.index(a2)
                        for e in ("sign", "far"):
                            x = arrs[f"{b}/{g}/{e}"][:, -1]
                            rows["G"].append(row(u, f"{b}/{g}:{a1}-{a2}", e, D.SNAPS[-1], x[:, i1] - x[:, i2]))
                        x = arrs[f"{b}/{g}/intact"]
                        rows["G"].append(row(u, f"{b}/{g}:{a1}-{a2}", "intact", D.SNAPS[-1], x[:, i1] - x[:, i2]))
        else:
            for b in D.BODIES:
                for rate in D.RATES:
                    for t_ in D.TEACHERS:
                        pre = f"{rate:g}/{t_}/"
                        for sp in D.REGROW:
                            for c1, c2 in PAIRS_R:
                                n1, n2 = pre + c1.format(s=f"{sp:g}"), pre + c2.format(s=f"{sp:g}")
                                for e in ("patch", "r_patch"):
                                    x = arrs[f"{b}/{e}"][:, -1]
                                    rows["R"].append(row(u, f"{b}:{n1}-{n2}", e, D.READS_R[-1],
                                                         x[:, CONDS.index(n1)] - x[:, CONDS.index(n2)]))
                        n1, n2 = pre + f"regrow@{D.REGROW[1]:g}", pre + f"regrow@{D.REGROW[0]:g}"
                        for e in ("patch", "r_patch"):
                            x = arrs[f"{b}/{e}"][:, -1]
                            rows["R"].append(row(u, f"{b}:{n1}-{n2}", e, D.READS_R[-1],
                                                 x[:, CONDS.index(n1)] - x[:, CONDS.index(n2)]))
    for name, key in (("contrasts_G.csv", "G"), ("contrasts_R.csv", "R")):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows[key])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sc001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "snaps": D.SNAPS,
            "reads_r": D.READS_R, "trace": D.TRACE, "arms": ARMS, "conds": CONDS}
    for p in ("G", "R"):
        (a.out / f"summary_{p}.json").write_text(json.dumps(dict(head, levels=L[p]), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
