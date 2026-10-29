"""GC001's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m gc001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. Contrasts are paired within block (same cases,
noise, anchors and displacements), with 95% t intervals over blocks.
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

from gc001 import design as D  # noqa: E402
from gc001.predict import score  # noqa: E402

ALL_READS = ("r_all", "r_in", "r_band")                   # kept at every read; the rest at t = 4,000 only
LAST_ONLY = ("v_all", "v_in", "r_int", "walls", "r_in_old", "v_in_old")


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


def ms(v, d=6):
    v = np.asarray(v, float)
    return [round(float(v.mean()), d), round(float(v.std(ddof=1)), d) if len(v) > 1 else None]


def levels(data):
    """L[unit][body][run][arm][endpoint] = [[mean, SD] at each read] (ALL_READS) or [[mean, SD]] at t = 4,000;
    'opened' = [mean, SD]; L[unit][body][run]['_misread'] = [mean, SD] of the share of anchors misread, '_misread_band'
    likewise. Unrounded block arrays are kept in L['_blocks'] for scoring."""
    out, blocks_ = {}, {}
    for u, arrs in data.items():
        for b in D.BODIES:
            for rn in D.RUNNAMES:
                key = f"{b}/{rn}"
                node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                bnode = blocks_.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                for e in ("misread", "misread_band"):
                    node[f"_{e}"] = ms(arrs[f"{key}/{e}"])
                    bnode[f"_{e}"] = arrs[f"{key}/{e}"]
                for ai, arm in enumerate(D.ARMS):
                    n, bn = node.setdefault(arm, {}), bnode.setdefault(arm, {})
                    for e in ALL_READS + LAST_ONLY:
                        if f"{key}/{e}" not in arrs:
                            continue
                        x = arrs[f"{key}/{e}"][:, :, ai]                     # (blocks, reads)
                        n[e] = [ms(x[:, ti]) for ti in range(len(D.READS))] if e in ALL_READS else [ms(x[:, -1])]
                        bn[e] = x[:, -1]
                    n["opened"] = ms(arrs[f"{key}/opened"][:, ai], 7)
                    bn["opened"] = arrs[f"{key}/opened"][:, ai]
    return out, blocks_


def traces(data):
    """T[unit][body][run][arm] = the record's agreement over the sheet every 2 x TRACE updates (mean over blocks)."""
    T = {}
    for u, arrs in data.items():
        for b in D.BODIES:
            for rn in D.RUNNAMES:
                node = T.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                x = arrs[f"{b}/{rn}/trace_all"]
                for ai, arm in enumerate(D.ARMS):
                    node[arm] = np.round(x[:, 1::2, ai].mean(0), 4).tolist()
    return T


def row(unit, contrast, ep, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, round(m, 6), round(m - half, 6), round(m + half, 6), int((v > 0).sum()), int((v < 0).sum()), n]


def contrasts(B, out):
    """contrasts_arms.csv at t = 4,000: for every unit, body and arm, the sheet's record (r_all) at sigma against sigma 0
    and against the matched scattered control; every bioelectric arm against the cue arm; the patch (r_in) of the
    change and memory runs at sigma against sigma 0."""
    rows = []
    for u, node in B.items():
        for b, runs in node.items():
            for s in D.SIGMAS[1:]:
                g, z0, sc = runs[D.run_name("none", 8, s)], runs[D.run_name("none", 8, 0)], runs[D.run_name("scatter", 8, s)]
                for arm in D.ARMS:
                    rows.append(row(f"{u}/{b}", f"none8@{s:g}-none8@0:{arm}", "r_all", g[arm]["r_all"] - z0[arm]["r_all"]))
                    rows.append(row(f"{u}/{b}", f"none8@{s:g}-scatter8@{s:g}:{arm}", "r_all", g[arm]["r_all"] - sc[arm]["r_all"]))
                    if arm != "cue":
                        rows.append(row(f"{u}/{b}", f"none8@{s:g}:{arm}-cue", "r_all", g[arm]["r_all"] - g["cue"]["r_all"]))
            for sit in ("change", "memory"):
                for s in D.EVENT_SIGMAS[1:]:
                    g, z0 = runs[D.run_name(sit, 4, s)], runs[D.run_name(sit, 4, 0)]
                    for arm in D.ARMS:
                        rows.append(row(f"{u}/{b}", f"{sit}4@{s:g}-{sit}4@0:{arm}", "r_in", g[arm]["r_in"] - z0[arm]["r_in"]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unit", "contrast", "endpoint", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"])
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "gc001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L, B = levels(data)
    S = score(B)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "arms": D.ARMS, "runs": D.RUNNAMES, "all_reads": ALL_READS, "last_only": LAST_ONLY}
    for b in D.BODIES:                          # one summary per body keeps every git file under 256 KB
        Lb = {u: {b: L[u][b]} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=Lb), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(B, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
