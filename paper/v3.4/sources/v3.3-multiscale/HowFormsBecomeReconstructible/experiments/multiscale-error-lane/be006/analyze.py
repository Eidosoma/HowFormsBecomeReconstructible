"""BE006's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m be006.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. The share of the patch's anchored cells whose record
is right (anc_right) is, per block, the block's right anchored cells over its anchored cells (a ratio of the case sums).
Each run has its own reads (design.run_reads). Contrasts are paired within block (same cases, noise and event), with 95%
t intervals over blocks: each dial against its own clock's never arm in the same run, AL against A and SL against S, and
each delayed dial against the same clock's prompt dial (memory4@0, the same cases and event) at that clock's scoring read.
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

from be006 import design as D  # noqa: E402
from be006.predict import score  # noqa: E402
from be006.worker import ENDS  # noqa: E402

REGION_ENDS = {"memory": ("r_in",), "change": ("r_in",), "cue": ("r_all",)}      # contrasts
STORE = {"memory": ("r_in", "v_in", "anc_right", "r_all"), "change": ("r_in", "r_in_old", "v_in", "r_fp2", "r_all"),
         "cue": ("r_all", "r_fp2", "r_fp8", "r_out8")}
SCALARS = ("opened", "opened_out", "onset", "hit", "anc_on", "anc_on_share")
PROMPT = D.run_name("memory", 4, 0)
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
                for e in ("opened", "opened_out", "onset", "hit", "anc_on"):
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


def t_score(c, m=0):
    return D.T_SCORE["F"] if c == "F" else (D.T_SCORE["m4"] if m == 4 else D.T_SCORE["slow"])


def contrasts(data, out):
    """contrasts_arms.csv: within each run at its scoring read, every dial against its clock's never arm, AL - A and
    SL - S (dial and never); each delayed dial against its clock's prompt dial in memory4@0 at the same read."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows = []
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            arms = list(run[3])
            for e in REGION_ENDS[run[0]]:
                for a1 in arms:
                    kind, c = a1.split("-", 1)
                    m = next((mm for mm in D.LATE.get(c, ()) if D.delay(D.eta_of(c), mm) == run[2]), 0)
                    t = t_score(c, m)
                    if t not in D.run_reads(*run):
                        continue
                    x = arrs[f"{rn}/{e}"][:, at(rn, t)]
                    pairs = []
                    if kind == "dial" and f"never-{c}" in arms:
                        pairs.append((a1, f"never-{c}"))
                    for long_, short in (("AL", "A"), ("SL", "S")):
                        if c == long_ and f"{kind}-{short}" in arms:
                            pairs.append((a1, f"{kind}-{short}"))
                    for p1, p2 in pairs:
                        rows.append(row(u, f"{b}/{rn}:{p1}-{p2}", e, t, x[:, arms.index(p1)] - x[:, arms.index(p2)]))
                    if run[0] == "memory" and run[2] and kind == "dial":
                        x0 = arrs[f"{PROMPT}/{e}"][:, at(PROMPT, t)]
                        rows.append(row(u, f"{b}/{rn}:{a1}-{PROMPT}:{a1}", e, t,
                                        x[:, arms.index(a1)] - x0[:, D.RUNS[0][3].index(a1)]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be006")
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
        Lb = {u: {b: {rn: {arm: ({e: v for e, v in n.items() if e in STORE[kind[rn]] or e in SCALARS}
                                 if arm != "_n_anc" else n)
                           for arm, n in node.items()} for rn, node in L[u][b].items()}} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(Lb)), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
