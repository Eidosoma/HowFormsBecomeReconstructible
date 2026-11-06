"""BE007's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m be007.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. The share of the patch's anchored cells whose record
is right (anc_right) is, per block, the block's right anchored cells over its anchored cells (a ratio of the case sums).
Each run has its own reads (design.run_reads). Contrasts are paired within block (same cases, noise and event), with 95%
t intervals over blocks: in memory4@0 every dial and never arm against SL's at every read; each delayed dial at D + 4,000
against the same clock's never arm (memory4@0) at that read (its gain) and against the same clock's prompt dial at 4,000
(its loss, at equal elapsed time), and against SL's dial in the same run; in change4@3918 and cue4@3918 every dial
against its never arm and every arm against SL's.
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

from be007 import design as D  # noqa: E402
from be007.predict import score  # noqa: E402
from be007.worker import ENDS, SCALARS  # noqa: E402

STORE = {"memory": ("r_in", "anc_right", "committed_in"),          # the summaries' endpoints (every git file <= 256 KB)
         "change": ("r_in", "r_in_old", "r_all", "committed_in"),
         "cue": ("r_all", "r_fp2", "r_out8", "committed_in")}
LSCALARS = SCALARS + ("anc_on_share",)
MEM0 = D.run_name("memory", 4, 0)
RUNS = {D.run_name(*x): x for x in D.RUNS}


def load(root, blocks):
    """data[(unit, body)][key] = (blocks, ...) array of case means."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(u, body)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}
    return data


def ms(v):
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[unit][body][run][arm][endpoint] = [[mean, SD] over blocks at each of the run's reads]; scalars = [mean, SD];
    anc_right per read from the block ratios; L[unit][body][run]['_n_anc'] = [mean, SD]. Unrounded."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            nanc = arrs[f"{rn}/n_anc"]
            node["_n_anc"] = ms(nanc)
            for ai, arm in enumerate(run[3]):
                n = node.setdefault(arm, {})
                for e in ENDS:
                    if f"{rn}/{e}" in arrs:
                        x = arrs[f"{rn}/{e}"]
                        n[e] = [ms(x[:, ti, ai]) for ti in range(x.shape[1])]
                x = arrs[f"{rn}/n_anc_ok"]
                n["anc_right"] = [ms(x[:, ti, ai] / nanc) for ti in range(x.shape[1])]
                for e in SCALARS:
                    n[e] = ms(arrs[f"{rn}/{e}"][:, ai])
                n["anc_on_share"] = ms(arrs[f"{rn}/anc_on"][:, ai] / nanc)
    return out


def at(rn, t):
    """The index of read t in run rn's reads."""
    return D.run_reads(*RUNS[rn]).index(t)


def traces(data):
    """T[unit][body][run][arm] = the record's agreement inside the patch, mean over blocks every 2 x TRACE updates."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            for ai, arm in enumerate(run[3]):
                node[arm] = np.round(arrs[f"{rn}/trace"][:, 1::2, ai].mean(0), 4).tolist()
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
    """contrasts_arms.csv (see the module docstring)."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    arms0 = list(D.RUNS[0][3])
    for (u, b), arrs in data.items():
        x0 = arrs[f"{MEM0}/r_in"]
        for ti, t in enumerate(D.run_reads(*RUNS[MEM0])):
            for a1 in arms0:
                ref = a1.split("-")[0] + "-SL"
                if a1 != ref:
                    rows.append(row(u, f"{b}/{MEM0}:{a1}-{ref}", "r_in", t, x0[:, ti, arms0.index(a1)] - x0[:, ti, arms0.index(ref)]))
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            situation, _, d, arms = run
            arms = list(arms)
            if situation == "memory" and d:
                t = d + D.AFTER
                x = arrs[f"{rn}/r_in"][:, at(rn, t)]
                for a1 in arms:
                    c = a1.split("-", 1)[1]
                    rows.append(row(u, f"{b}/{rn}:{a1}-{MEM0}:never-{c}", "r_in", t,
                                    x[:, arms.index(a1)] - x0[:, at(MEM0, t), arms0.index(f"never-{c}")]))
                    rows.append(row(u, f"{MEM0}:{a1}@{D.AFTER}-{b}/{rn}:{a1}", "r_in", t,
                                    x0[:, at(MEM0, D.AFTER), arms0.index(a1)] - x[:, arms.index(a1)]))
                    if a1 != "dial-SL":
                        rows.append(row(u, f"{b}/{rn}:{a1}-dial-SL", "r_in", t, x[:, arms.index(a1)] - x[:, arms.index("dial-SL")]))
            elif situation in ("change", "cue"):
                e = "r_in" if situation == "change" else "r_all"
                t = d + D.AFTER
                x = arrs[f"{rn}/{e}"][:, at(rn, t)]
                for a1 in arms:
                    kind, c = a1.split("-", 1)
                    if kind == "dial":
                        rows.append(row(u, f"{b}/{rn}:{a1}-never-{c}", e, t, x[:, arms.index(a1)] - x[:, arms.index(f"never-{c}")]))
                    if c != "SL":
                        rows.append(row(u, f"{b}/{rn}:{a1}-{kind}-SL", e, t, x[:, arms.index(a1)] - x[:, arms.index(f"{kind}-SL")]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be007")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(),
            "runs": list(D.RUNNAMES), "run_arms": {rn: list(x[3]) for x, rn in zip(D.RUNS, D.RUNNAMES)},
            "run_reads": {rn: list(D.run_reads(*x)) for x, rn in zip(D.RUNS, D.RUNNAMES)}}
    kind = {rn: x[0] for x, rn in zip(D.RUNS, D.RUNNAMES)}
    for b in D.BODIES:                          # one summary per body: every git file < 256 KB
        Lb = {u: {b: {rn: {arm: ({e: v for e, v in n.items() if e in STORE[kind[rn]] or e in LSCALARS}
                                 if arm != "_n_anc" else n)
                           for arm, n in node.items()} for rn, node in L[u][b].items()}} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(Lb)), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
