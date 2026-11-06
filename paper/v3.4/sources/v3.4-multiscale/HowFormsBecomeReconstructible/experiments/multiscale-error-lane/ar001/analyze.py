"""AR001's reader: python -m ar001.analyze --root STAGE_ROOT --out OUT_DIR [--stage development|preflight|probe]

Loads every (body, unit, block) shard, then computes per case (pooled over the eight unit-body pairs: per case the mean
over the pairs; a block's value the mean over its eight cases):
  u(arm, scoring)        the record's agreement with the scoring's correct target inside the patch at t = 8,000
                         (change/new: the legitimate change's target; change/old: the same run against the old target)
  U(arm)                 the declared utility: the mean of u over the eight scorings with design.WEIGHTS
  U_ctrl(h, f)           the controller's expected utility under a signal with hit rate h and false-alarm rate f:
                         per scoring p u(dial) + (1 - p) u(rest), p = h on design.RIGHT and f on design.WRONG
  sham(run)              the cost of a sham to the sheet: r_all(rest) - r_all(dial) at t = 8,000
and writes summaries (every run, arm and endpoint at every read, pooled and per pair), the reliability grid, the side
arms' contrasts and the policy ranking by scoring.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar001 import design as D  # noqa: E402

PAIRS = tuple((b, u) for u in D.UNITS for b in D.BODIES)
RUNARMS = {D.run_name(*x): list(x[2]) for x in D.RUNS}
GRID = tuple(round(x, 2) for x in np.linspace(0, 1, 11))


def load(root, blocks=None):
    """{(body, unit, block): {key: array}} for every shard under root (blocks: an optional subset)."""
    root = Path(root)
    out = {}
    for f in sorted((root / "shards").glob("*/*/*.npz")):
        body, unit, block = f.parts[-3], f.parts[-2], int(f.stem)
        if blocks is not None and block not in blocks:
            continue
        z = np.load(f)
        out[(body, unit, block)] = {k: z[k] for k in z.files}
    return out


def blocks_of(Z):
    return sorted({k[2] for k in Z})


def meta(Z):
    k = next(iter(Z))
    return json.loads(str(Z[k]["__meta__"]))


def raw_case(Z, run, ep, arm, read=D.T_READ, pairs=PAIRS):
    """(blocks, pairs, cases): the endpoint for one arm at one read."""
    ri = D.READS.index(read)
    ai = RUNARMS[run].index(arm)
    bl = blocks_of(Z)
    return np.array([[Z[(b, u, k)][f"{run}/{ep}"][ri, ai] for b, u in pairs] for k in bl])


def case(Z, run, ep, arm, read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): per case the mean over the pairs."""
    return raw_case(Z, run, ep, arm, read, pairs).mean(1)


def scoring_run(s, sigma=0.0):
    sit, _, which = s.partition("/")
    return D.run_name(sit, sigma), ("r_in_old" if which == "old" else "r_in")


def u(Z, arm, s, sigma=0.0, read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): u(arm, scoring s)."""
    run, ep = scoring_run(s, sigma)
    return case(Z, run, ep, arm, read, pairs)


def U(Z, arm, sigma=0.0, read=D.T_READ, pairs=PAIRS, scorings=D.SCORINGS):
    return sum(D.WEIGHTS[s] * u(Z, arm, s, sigma, read, pairs) for s in scorings) / sum(D.WEIGHTS[s] for s in scorings)


def p_on(s, h, f):
    return h if s in D.RIGHT else f


def u_ctrl(Z, s, h, f, on="dial", off="rest", sigma=0.0, read=D.T_READ, pairs=PAIRS):
    p = p_on(s, h, f)
    return p * u(Z, on, s, sigma, read, pairs) + (1 - p) * u(Z, off, s, sigma, read, pairs)


def U_ctrl(Z, h, f, on="dial", off="rest", sigma=0.0, read=D.T_READ, pairs=PAIRS, scorings=D.SCORINGS):
    return sum(D.WEIGHTS[s] * u_ctrl(Z, s, h, f, on, off, sigma, read, pairs) for s in scorings) / sum(
        D.WEIGHTS[s] for s in scorings)


def best_fixed(Z, pairs=PAIRS):
    """The fixed policy with the largest pooled U over every block and case, and every fixed policy's U."""
    vals = {a: float(U(Z, a, pairs=pairs).mean()) for a in D.FIXED}
    return max(vals, key=vals.get), vals


def sham(Z, run, arm="dial", ref="rest", ep="r_all", read=D.T_READ, pairs=PAIRS):
    return case(Z, run, ep, ref, read, pairs) - case(Z, run, ep, arm, read, pairs)


def ci(x):
    from scipy import stats
    blk = x.mean(-1) if x.ndim == 2 else x
    m, se = float(blk.mean()), float(blk.std(ddof=1) / np.sqrt(len(blk)))
    h = float(stats.t.ppf(0.975, len(blk) - 1) * se)
    return {"mean": m, "lo": m - h, "hi": m + h, "sd_block": float(blk.std(ddof=1)),
            "sd_case8": float(x.ravel().std(ddof=1) / np.sqrt(8)) if x.ndim == 2 else None,
            "blocks": [float(v) for v in blk]}


def summaries(Z):
    """Every run, arm and endpoint at every read: pooled means (and per pair at the scoring read)."""
    out = {}
    m = meta(Z)
    for run, arms in RUNARMS.items():
        for ep in ("r_in", "r_in_old", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in"):
            key = f"{run}/{ep}"
            if key not in Z[next(iter(Z))]:
                continue
            for a in arms:
                out[f"{key}/{a}"] = {"pooled": [round(float(case(Z, run, ep, a, t).mean()), 6) for t in D.READS],
                                     "pairs": {f"{b}/{un}": round(float(case(Z, run, ep, a, D.T_READ, ((b, un),)).mean()), 6)
                                               for b, un in PAIRS}}
        for sc in ("opened", "opened_out", "onset", "hit"):
            arr = np.array([[Z[(b, un, k)][f"{run}/{sc}"] for b, un in PAIRS] for k in blocks_of(Z)])   # (blocks, pairs, arms, cases)
            for j, a in enumerate(arms):
                out[f"{run}/{sc}/{a}"] = round(float(arr[:, :, j].mean()), 6)
    return {"tag": m["tag"], "digest": m["design_digest"], "blocks": blocks_of(Z), "reads": list(D.READS),
            "levels": out}


def reliability(Z, pairs=PAIRS):
    """U_ctrl over the (h, f) grid, the fixed policies' U and the advantage over the best fixed policy."""
    best, vals = best_fixed(Z, pairs)
    grid = {f"{h:g},{f:g}": float(U_ctrl(Z, h, f, pairs=pairs).mean()) for h in GRID for f in GRID}
    return {"best_fixed": best, "U_fixed": vals, "U_ctrl": grid,
            "advantage": {k: v - vals[best] for k, v in grid.items()}}


def ranking(Z, pairs=PAIRS):
    """Per scoring: every arm's pooled u, the best fixed policy and the dial's."""
    out = {}
    for s in D.SCORINGS:
        vals = {a: float(u(Z, a, s, pairs=pairs).mean()) for a in D.MAIN}
        fixed = {a: v for a, v in vals.items() if a in D.FIXED}
        out[s] = {"u": vals, "best_fixed": max(fixed, key=fixed.get)}
    return out


def side_arms(Z, pairs=PAIRS):
    out = {}
    for run in (D.run_name(x[0], x[1]) for x in D.RUNS if x[1] == 0):
        for a in RUNARMS[run]:
            if a.startswith("dial-"):
                for ep in ("r_in", "r_in_old", "r_all", "r_out"):
                    if f"{run}/{ep}" in Z[next(iter(Z))]:
                        out[f"{run}/{ep}/{a}-dial"] = ci(case(Z, run, ep, a, pairs=pairs) - case(Z, run, ep, "dial", pairs=pairs))
    for run in ("none@1", "memory@1", "change@1"):
        base = run.replace("@1", "@0")
        for a in D.CUE_READERS:
            for ep in ("r_in", "r_in_old", "r_all"):
                if f"{run}/{ep}" in Z[next(iter(Z))]:
                    out[f"{run}/{ep}/{a}-sigma0"] = ci(case(Z, run, ep, a, pairs=pairs) - case(Z, base, ep, a, pairs=pairs))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = load(a.root)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(summaries(Z), separators=(",", ":")) + "\n")
    (a.out / "reliability.json").write_text(json.dumps(reliability(Z), indent=0) + "\n")
    (a.out / "ranking.json").write_text(json.dumps(ranking(Z), indent=0) + "\n")
    (a.out / "side_arms.json").write_text(json.dumps(side_arms(Z), separators=(",", ":")) + "\n")
    print("wrote", sorted(p.name for p in a.out.iterdir()))


if __name__ == "__main__":
    main()
