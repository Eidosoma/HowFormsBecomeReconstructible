"""BE005's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m be005.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. The share of the patch's anchored cells whose record
is right (anc_right) is, per block, the block's right anchored cells over its anchored cells (a ratio of the case sums).
Contrasts are paired within block (same cases, noise and event), with 95% t intervals over blocks: arm against arm within
a run, and the signal arms of each delayed memory run against the prompt dial (memory4@0, the same cases and event).
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

from be005 import design as D  # noqa: E402
from be005.predict import score  # noqa: E402
from be005.worker import ENDS  # noqa: E402

REGION_ENDS = {"memory": ("r_in",), "change": ("r_in",), "cue": ("r_all",)}      # contrasts
STORE = {"memory": ("r_in", "v_in", "anc_right", "r_all"), "change": ("r_in", "r_in_old", "v_in", "r_fp2", "r_all"),
         "cue": ("r_all", "r_fp2", "r_fp8", "r_out8")}          # written to the summaries: memory runs
                                                                                   # at every read, the others at 4,000
SCALARS = ("opened", "opened_out", "onset", "hit", "anc_on", "anc_on_share")
PROMPT = D.run_name("memory", 4, 0)


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
    """L[unit][body][run][arm][endpoint] = [[mean, SD] over blocks at each read]; opened, opened_out and onset =
    [mean, SD]; anc_right per read from the block ratios; L[unit][body][run]['_n_anc'] = [mean, SD]. Unrounded."""
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


def baseline(arm, arms):
    """The no-signal arm of the same setting in the same run, if present."""
    if arm.startswith("dial-e"):
        b = "never-e" + arm[len("dial-e"):]
    elif arm.startswith("dial-"):
        b = "never-tv" + arm.rsplit("-tv", 1)[1]
    else:
        return None
    return b if b in arms else None


def contrasts(data, out):
    """contrasts_arms.csv at t = 4,000: every signal arm against its run's no-signal arm of the same setting, and each
    delayed dial-e arm against the same arm's prompt signal (memory4@0, the same cases and event)."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows, t1 = [], D.READS[-1]
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            arms = list(run[3])
            for e in REGION_ENDS[run[0]]:
                x = arrs[f"{rn}/{e}"][:, -1]
                for a1 in arms:
                    a2 = baseline(a1, arms)
                    if a2 is not None:
                        rows.append(row(u, f"{b}/{rn}:{a1}-{a2}", e, t1, x[:, arms.index(a1)] - x[:, arms.index(a2)]))
                if run[0] == "memory" and run[2]:
                    x0 = arrs[f"{PROMPT}/{e}"][:, -1]
                    for a1 in arms:
                        rows.append(row(u, f"{b}/{rn}:{a1}-{PROMPT}:{a1}", e, t1,
                                        x[:, arms.index(a1)] - x0[:, D.RUNS[0][3].index(a1)]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be005")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "runs": list(D.RUNNAMES), "run_arms": {rn: list(x[3]) for x, rn in zip(D.RUNS, D.RUNNAMES)}}
    kind = {rn: x[0] for x, rn in zip(D.RUNS, D.RUNNAMES)}
    for b in D.BODIES:                          # one summary per body, the endpoints each run needs: every git file < 256 KB
        Lb = {u: {b: {rn: {arm: ({e: (v if kind[rn] == "memory" or e in SCALARS else v[-1:]) for e, v in n.items()
                                  if e in STORE[kind[rn]] or e in SCALARS} if arm != "_n_anc" else n)
                           for arm, n in node.items()} for rn, node in L[u][b].items()}} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(Lb)), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
