"""BE009's frozen reader: block means of every endpoint, the case-matched predictions, the registered statements, paired
contrasts.

python -m be009.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. The share of the patch's anchored cells whose record
is right (anc_right) is, per block, the block's right anchored cells over its anchored cells (a ratio of the case sums).
Each run has its own reads (design.run_reads). The case-matched quantities (derived) are computed per case from the
task's execution draws (tx/case, tx/patch) and the case's own SL gain, then averaged over the block's cases:
  S_case(D)     the share of cases whose tau_x >= D + 2 (executed after the signal's first update)
  q_cell(D)     the mean over cases of the share of the patch's cells whose tau_x >= D + 2
  pred_case(D)  the mean over cases of [tau_x >= D + 2] x gain(SL, D): every case all or none, by its own draw
  pred_cell(D)  the mean over cases of q_cell's case share x gain(SL, D): every patch cell all or none, by its own draw
  dev_case(D), dev_cell(D)   gain(CASE, D) - pred_case(D), gain(CELL, D) - pred_cell(D)
  rep_c(D)      the share of cases repaired: whose prompt gain(c, 0) is above 0 and whose gain(c, D) is at least half of
                it (the denominator all cases; a case-level, all-or-none read like a planarian phenotype), every clock c
where gain(c, D) of a case is dial-c's r_in in memory4@D at D + 4,000 less never-c's in memory4@0 at the same read (at
D = 0: both in memory4@0 at 4,000). Contrasts are paired within block (same cases, noise and event), with 95% t
intervals over blocks: in memory4@0 every dial and never arm against SL's at every read; each delayed dial at D + 4,000
against the same clock's never arm (memory4@0) at that read (its gain), against the same clock's prompt dial at 4,000
(its loss, at equal elapsed time) and against SL's dial in the same run; dev_case and dev_cell at every delay.
reported.json (reported, not registered): pooled over the twelve pairs within each block, the mean over blocks and its
95% t interval of dev_case(D) and dev_cell(D), rep_c(D) for every clock and rep_CELL(D) - rep_CASE(D) at every delay,
gain(C12, 2,700) - gain(CASE, 2,700) and gain(C12, 2,700) - gain(SL, 2,700).
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

from be009 import design as D  # noqa: E402
from be009.predict import score  # noqa: E402
from be009.worker import ENDS, SCALARS  # noqa: E402

STORE = ("r_in", "anc_right", "committed_in")                  # the summaries' endpoints (every git file <= 256 KB)
LSCALARS = SCALARS + ("anc_on_share",)
MEM0 = D.run_name("memory", 4, 0)
RUNS = {D.run_name(*x): x for x in D.RUNS}
DERIVED = ("S_case", "q_cell", "pred_case", "pred_cell", "dev_case", "dev_cell") + tuple(f"rep_{c}" for c in D.CLOCKS)


def load(root, blocks):
    """data[(unit, body)][key] = (blocks, ..., cases) arrays, every case kept."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(u, body)] = {k: np.stack(v) for k, v in arrs.items()}
    return data


def at(rn, t):
    """The index of read t in run rn's reads."""
    return D.run_reads(*RUNS[rn]).index(t)


def case_gain(arrs, c, d):
    """(blocks, cases): clock c's gain at delay d (0: the prompt signal at 4,000)."""
    x0 = arrs[f"{MEM0}/r_in"]
    arms0 = list(RUNS[MEM0][3])
    t = D.AFTER if d == 0 else d + D.AFTER
    none = x0[:, at(MEM0, t), arms0.index(f"never-{c}")]
    if d == 0:
        return x0[:, at(MEM0, t), arms0.index(f"dial-{c}")] - none
    rn = D.run_name("memory", 4, d)
    return arrs[f"{rn}/r_in"][:, at(rn, t), list(RUNS[rn][3]).index(f"dial-{c}")] - none


def derived(arrs):
    """{name: {delay: (blocks,) values}}, the case-matched quantities of the module docstring."""
    tx, txp = arrs["tx/case"], arrs["tx/patch"]                  # (blocks, cases), (blocks, cases, patch cells)
    out = {k: {} for k in DERIVED}
    for d in D.DELAYS:
        late = (tx >= d + 2).astype(float)
        q = (txp >= d + 2).mean(-1)
        g_sl = case_gain(arrs, "SL", d)
        out["S_case"][d] = late.mean(-1)
        out["q_cell"][d] = q.mean(-1)
        out["pred_case"][d] = (late * g_sl).mean(-1)
        out["pred_cell"][d] = (q * g_sl).mean(-1)
        out["dev_case"][d] = case_gain(arrs, "CASE", d).mean(-1) - out["pred_case"][d]
        out["dev_cell"][d] = case_gain(arrs, "CELL", d).mean(-1) - out["pred_cell"][d]
        for c in D.CLOCKS:
            g0 = case_gain(arrs, c, 0)
            out[f"rep_{c}"][d] = ((g0 > 0) & (case_gain(arrs, c, d) >= 0.5 * g0)).mean(-1)
    return out


def ms(v):
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[unit][body][run][arm][endpoint] = [[mean, SD] over blocks at each of the run's reads]; scalars = [mean, SD];
    anc_right per read from the block ratios; L[unit][body][run]['_n_anc'] = [mean, SD]; L[unit][body]['_derived']
    [name][delay] = [mean, SD]. Unrounded."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            nanc = arrs[f"{rn}/n_anc"].sum(-1)
            node["_n_anc"] = ms(arrs[f"{rn}/n_anc"].mean(-1))
            for ai, arm in enumerate(run[3]):
                n = node.setdefault(arm, {})
                for e in ENDS:
                    if f"{rn}/{e}" in arrs:
                        x = arrs[f"{rn}/{e}"].mean(-1)
                        n[e] = [ms(x[:, ti, ai]) for ti in range(x.shape[1])]
                x = arrs[f"{rn}/n_anc_ok"].sum(-1)
                n["anc_right"] = [ms(x[:, ti, ai] / nanc) for ti in range(x.shape[1])]
                for e in SCALARS:
                    n[e] = ms(arrs[f"{rn}/{e}"][:, ai].mean(-1))
                n["anc_on_share"] = ms(arrs[f"{rn}/anc_on"][:, ai].sum(-1) / nanc)
        out[u][b]["_derived"] = {k: {str(d): ms(v) for d, v in dv.items()} for k, dv in derived(arrs).items()}
    return out


def traces(data):
    """T[unit][body][run][arm] = the record's agreement inside the patch, mean over blocks every 2 x TRACE updates."""
    out = {}
    for (u, b), arrs in data.items():
        for run, rn in zip(D.RUNS, D.RUNNAMES):
            node = out.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            for ai, arm in enumerate(run[3]):
                node[arm] = np.round(arrs[f"{rn}/trace"][:, 1::2, ai].mean((0, -1)), 4).tolist()
    return out


def interval(v):
    """Mean over blocks and its 95% t interval (unrounded)."""
    n, m = len(v), float(v.mean())
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    return {"mean": m, "lo95": m - half, "hi95": m + half, "blocks_pos": int((v > 0).sum()), "blocks_neg": int((v < 0).sum()),
            "blocks": n}


def reported(data):
    """reported.json's quantities (see the module docstring), each pooled over the twelve pairs within a block."""
    dv = {key: derived(arrs) for key, arrs in data.items()}
    pool = lambda f: np.mean([f(key) for key in data], axis=0)
    out = {}
    for d in D.DELAYS:
        for k in ("dev_case", "dev_cell"):
            out[f"{k}@{d}"] = interval(pool(lambda key: dv[key][k][d]))
        for c in D.CLOCKS:
            out[f"rep_{c}@{d}"] = interval(pool(lambda key: dv[key][f"rep_{c}"][d]))
        out[f"rep_CELL-rep_CASE@{d}"] = interval(pool(lambda key: dv[key]["rep_CELL"][d] - dv[key]["rep_CASE"][d]))
    for c in ("CASE", "SL"):
        out[f"gain_C12-gain_{c}@2700"] = interval(pool(lambda key: case_gain(data[key], "C12", 2700).mean(-1)
                                                        - case_gain(data[key], c, 2700).mean(-1)))
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
        x0 = arrs[f"{MEM0}/r_in"].mean(-1)
        for ti, t in enumerate(D.run_reads(*RUNS[MEM0])):
            for a1 in arms0:
                ref = a1.split("-")[0] + "-SL"
                if a1 != ref:
                    rows.append(row(u, f"{b}/{MEM0}:{a1}-{ref}", "r_in", t, x0[:, ti, arms0.index(a1)] - x0[:, ti, arms0.index(ref)]))
        for run, rn in zip(D.RUNS[1:], D.RUNNAMES[1:]):
            d, arms = run[2], list(run[3])
            t = d + D.AFTER
            x = arrs[f"{rn}/r_in"].mean(-1)[:, at(rn, t)]
            for a1 in arms:
                c = a1.split("-", 1)[1]
                rows.append(row(u, f"{b}/{rn}:{a1}-{MEM0}:never-{c}", "r_in", t,
                                x[:, arms.index(a1)] - x0[:, at(MEM0, t), arms0.index(f"never-{c}")]))
                rows.append(row(u, f"{MEM0}:{a1}@{D.AFTER}-{b}/{rn}:{a1}", "r_in", t,
                                x0[:, at(MEM0, D.AFTER), arms0.index(a1)] - x[:, arms.index(a1)]))
                if a1 != "dial-SL":
                    rows.append(row(u, f"{b}/{rn}:{a1}-dial-SL", "r_in", t, x[:, arms.index(a1)] - x[:, arms.index("dial-SL")]))
        dv = derived(arrs)
        for d in D.DELAYS:
            for k in ("dev_case", "dev_cell"):
                rows.append(row(u, f"{b}/{k}@{d}", "gain", d + D.AFTER, dv[k][d]))
    with open(out / "contrasts_arms.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development", "probe"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "be009")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    if a.stage == "probe":                      # P37's shards (the reader run unstubbed before the freeze)
        blocks = list(range(*D.PROBE_BLOCKS))
    else:
        blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(),
            "runs": list(D.RUNNAMES), "run_arms": {rn: list(x[3]) for x, rn in zip(D.RUNS, D.RUNNAMES)},
            "run_reads": {rn: list(D.run_reads(*x)) for x, rn in zip(D.RUNS, D.RUNNAMES)}}
    for b in D.BODIES:                          # one summary per body: every git file < 256 KB
        Lb = {u: {b: {rn: ({arm: ({e: v for e, v in n.items() if e in STORE or e in LSCALARS} if arm != "_n_anc" else n)
                            for arm, n in node.items()} if rn != "_derived" else node)
                      for rn, node in L[u][b].items()}} for u in L}
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(Lb)), separators=(",", ":")) + "\n")
    (a.out / "traces.json").write_text(json.dumps(dict(head, every=2 * D.TRACE, traces=traces(data)), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    (a.out / "reported.json").write_text(json.dumps(dict(head, reported=rounded(reported(data), 8)), indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
