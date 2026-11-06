"""AR002's reader: python -m ar002.analyze --root STAGE_ROOT --out OUT_DIR

Loads every (body, unit, block) shard (each run's arms read from the shards' own meta, which must agree), then computes
per case (pooled over the eight unit-body pairs: per case the mean over the pairs; a block's value the mean over its
eight cases):
  u(arm, scoring)    the record's agreement with the scoring's correct target inside the patch at t = 8,000
  U(arm)             the declared utility: the mean of u over the eight scorings with equal weights (AR001's)
  fire(arm, s)       the detector fired (det_on > 0) on a lineage-case in situation s; p_s its pooled rate
  U_pred(arm)        the declared signal's exact value at the detector's own measured firing: per lineage-case and
                     scoring, fire x u(dial) + (1 - fire) x u(rest) (AR001's mixture, prompt and over the patch)
  U_loc(arm)         the same with fire replaced by "fired with its footprint on the patch"
  price(arm)         U(arm) - U_pred(arm): what the detector's own onset, footprint and placement cost or add
  U_ctrl(h, f)       AR001's controller expectation under a declared signal, from this stage's dial and rest
  U_ceiling          the ceiling of a signal sent promptly over the patch: u(dial) on memory and correlated, u(rest)
                     elsewhere (the information-limit pair scores 1/8 for every mixture)
  gap(arm)           U(arm) - U(vote) decomposed (the lead's ruling 4): the worth over the vote on memory and correlated,
                     less the vote's advantage over rest on none, body, shared and cue (which a controller whose default
                     is rest gives up), plus the false alarms' effect on those four, plus the information-limit pair (0)
  sham(arm, run)     the sheet's cost: r_all(rest) - r_all(arm) at t = 8,000
and writes summaries (every run, arm and endpoint at every read, pooled and per pair), the detectors' rates, onsets and
footprints, the utilities with the gap's decomposition, the misread side arm and the size side arm.
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

from ar002 import design as D  # noqa: E402

PAIRS = tuple((b, u) for u in D.UNITS for b in D.BODIES)
RUNARMS = {D.run_name(*x): list(x[2]) + list(x[3]) for x in D.RUNS}      # the design's (the shards' meta is read)
GRID = tuple(round(x, 2) for x in np.linspace(0, 1, 11))
FOUR = ("none", "body", "shared", "cue")                       # where the vote beats rest and no signal can recover it
HITS = ("memory", "correlated")
PAIR = ("change/new", "change/old")


class Shards(dict):
    """{(body, unit, block): {key: array}}, with .runs: {run: arms} from the shards' meta."""
    runs = None


def load(root, blocks=None):
    """Every shard under root (blocks: an optional subset); every shard's meta must name the same runs and arms."""
    root = Path(root)
    out = Shards()
    seen = set()
    for f in sorted((root / "shards").glob("*/*/*.npz")):
        body, unit, block = f.parts[-3], f.parts[-2], int(f.stem)
        if blocks is not None and block not in blocks:
            continue
        z = np.load(f)
        out[(body, unit, block)] = {k: z[k] for k in z.files}
        seen.add(json.dumps(json.loads(str(z["__meta__"]))["runs"]))
    assert len(seen) == 1, "the shards' runs differ"
    out.runs = {r: list(a) for r, a in json.loads(seen.pop())}
    return out


def runs_of(Z):
    r = getattr(Z, "runs", None)
    return r if r is not None else {name: list(a) for name, a in meta(Z)["runs"]}


def blocks_of(Z):
    return sorted({k[2] for k in Z})


def meta(Z):
    k = next(iter(Z))
    return json.loads(str(Z[k]["__meta__"]))


def raw_case(Z, run, ep, arm, read=D.T_READ, pairs=PAIRS):
    """(blocks, pairs, cases): an endpoint for one arm at one read."""
    ri = D.READS.index(read)
    ai = runs_of(Z)[run].index(arm)
    return np.array([[Z[(b, u, k)][f"{run}/{ep}"][ri, ai] for b, u in pairs] for k in blocks_of(Z)])


def raw_scalar(Z, run, sc, arm, pairs=PAIRS):
    """(blocks, pairs, cases): a per-arm scalar (onset, det_on, det_fp_in, ...)."""
    ai = runs_of(Z)[run].index(arm)
    return np.array([[Z[(b, u, k)][f"{run}/{sc}"][ai] for b, u in pairs] for k in blocks_of(Z)])


def case(Z, run, ep, arm, read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): per case the mean over the pairs."""
    return raw_case(Z, run, ep, arm, read, pairs).mean(1)


def scoring_run(s, sigma=0.0):
    sit, _, which = s.partition("/")
    return D.run_name(sit, sigma), ("r_in_old" if which == "old" else "r_in")


def u_raw(Z, arm, s, sigma=0.0, read=D.T_READ, pairs=PAIRS):
    run, ep = scoring_run(s, sigma)
    return raw_case(Z, run, ep, arm, read, pairs)


def u(Z, arm, s, sigma=0.0, read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): u(arm, scoring s)."""
    return u_raw(Z, arm, s, sigma, read, pairs).mean(1)


def U(Z, arm, sigma=0.0, read=D.T_READ, pairs=PAIRS):
    return sum(D.WEIGHTS[s] * u(Z, arm, s, sigma, read, pairs) for s in D.SCORINGS)


def fired(Z, arm, situation, sigma=0.0, pairs=PAIRS, size=D.SIZE):
    """(blocks, pairs, cases) bool: the arm's detector fired at all (any update, anywhere)."""
    return raw_scalar(Z, D.run_name(situation, sigma, size=size), "det_on", arm, pairs) > 0


def located(Z, arm, situation, sigma=0.0, pairs=PAIRS, size=D.SIZE):
    """(blocks, pairs, cases) bool: it fired with its footprint on the patch."""
    return raw_scalar(Z, D.run_name(situation, sigma, size=size), "det_fp_in", arm, pairs) > 0


def rate(Z, arm, situation, sigma=0.0, which="fired", pairs=PAIRS, size=D.SIZE):
    """(blocks, cases): the pooled firing rate."""
    return (fired if which == "fired" else located)(Z, arm, situation, sigma, pairs, size).astype(float).mean(1)


def U_mix(Z, arm, which="fired", on="dial", off="rest", pairs=PAIRS):
    """(blocks, cases): the declared signal's exact value at the arm's own firing (U_pred) or located firing (U_loc)."""
    tot = 0.0
    for s in D.SCORINGS:
        sit = s.partition("/")[0]
        x = (fired if which == "fired" else located)(Z, arm, sit, 0.0, pairs).astype(float)
        tot = tot + D.WEIGHTS[s] * (x * u_raw(Z, on, s, pairs=pairs) + (1 - x) * u_raw(Z, off, s, pairs=pairs)).mean(1)
    return tot


def U_ctrl(Z, h, f, on="dial", off="rest", pairs=PAIRS):
    tot = 0.0
    for s in D.SCORINGS:
        p = h if s in D.RIGHT else f
        tot = tot + D.WEIGHTS[s] * (p * u(Z, on, s, pairs=pairs) + (1 - p) * u(Z, off, s, pairs=pairs))
    return tot


def U_ceiling(Z, on="dial", off="rest", pairs=PAIRS):
    """The ceiling of a signal sent promptly over the patch: u(dial) on memory and correlated, u(rest) elsewhere."""
    return sum(D.WEIGHTS[s] * u(Z, on if s in HITS else off, s, pairs=pairs) for s in D.SCORINGS)


def u_ceiling(Z, s, pairs=PAIRS):
    return u(Z, "dial" if s in HITS else "rest", s, pairs=pairs)


def gap(Z, arm=None, pairs=PAIRS):
    """U(arm) - U(vote) (arm None: U_ceiling - U(vote)) in four (blocks, cases) terms that sum to it exactly:
    hits         sum over memory and correlated of u(arm) - u(vote), weighted (the worth over the vote there)
    default      minus the vote's advantage over rest on none, body, shared and cue, weighted (what a controller whose
                 default is rest gives up; no signal recovers it)
    false_alarms sum over those four of u(arm) - u(rest), weighted (0 for the ceiling)
    pair         sum over the information-limit pair of u(arm) - u(vote), weighted (0 by the identity)
    and, reported beside them, the hits measured against rest and the vote's advantage over rest on memory and
    correlated (hits = hits_over_rest - vote_over_rest_hits)."""
    ua = (lambda s: u_ceiling(Z, s, pairs)) if arm is None else (lambda s: u(Z, arm, s, pairs=pairs))
    w = D.WEIGHTS
    uv = {s: u(Z, "vote", s, pairs=pairs) for s in D.SCORINGS}
    ur = {s: u(Z, "rest", s, pairs=pairs) for s in D.SCORINGS}
    ux = {s: ua(s) for s in D.SCORINGS}
    t = {"hits": sum(w[s] * (ux[s] - uv[s]) for s in HITS),
         "default": -sum(w[s] * (uv[s] - ur[s]) for s in FOUR),
         "false_alarms": sum(w[s] * (ux[s] - ur[s]) for s in FOUR),
         "pair": sum(w[s] * (ux[s] - uv[s]) for s in PAIR),
         "hits_over_rest": sum(w[s] * (ux[s] - ur[s]) for s in HITS),
         "vote_over_rest_hits": sum(w[s] * (uv[s] - ur[s]) for s in HITS),
         "vote_over_rest_by_scoring": {s: uv[s] - ur[s] for s in FOUR + HITS}}
    t["total"] = t["hits"] + t["default"] + t["false_alarms"] + t["pair"]
    return t


def plane_rates(Z, arm, pairs=PAIRS):
    """The detector's pooled (h, f) in AR001's sense: its mean rate over RIGHT and over WRONG scorings."""
    sit = lambda s: s.partition("/")[0]
    h = np.mean([rate(Z, arm, sit(s), pairs=pairs) for s in D.RIGHT], 0)
    f = np.mean([rate(Z, arm, sit(s), pairs=pairs) for s in D.WRONG], 0)
    return h, f


def sham(Z, run, arm, ref="rest", ep="r_all", read=D.T_READ, pairs=PAIRS):
    return case(Z, run, ep, ref, read, pairs) - case(Z, run, ep, arm, read, pairs)


def info_limit(Z, arms=None):
    """(blocks, cases): the largest abs(u(new) + u(old) - 1) over every arm (or `arms`) of every change run."""
    worst = None
    runs = runs_of(Z)
    for run in (r for r in runs if r.startswith("change@")):
        for a in (runs[run] if arms is None else [x for x in arms if x in runs[run]]):
            x = np.abs(raw_case(Z, run, "r_in", a) + raw_case(Z, run, "r_in_old", a) - 1.0).max(1)
            worst = x if worst is None else np.maximum(worst, x)
    return worst


def ci(x):
    from scipy import stats
    blk = x.mean(-1) if x.ndim == 2 else x
    m, se = float(blk.mean()), float(blk.std(ddof=1) / np.sqrt(len(blk))) if len(blk) > 1 else 0.0
    h = float(stats.t.ppf(0.975, len(blk) - 1) * se) if len(blk) > 1 else 0.0
    return {"mean": m, "lo": m - h, "hi": m + h, "sd_block": float(blk.std(ddof=1)) if len(blk) > 1 else 0.0,
            "sd_case8": float(x.ravel().std(ddof=1) / np.sqrt(8)) if x.ndim == 2 else None,
            "blocks": [float(v) for v in blk]}


def summaries(Z):
    """Every run, arm and endpoint at every read: pooled means (and per pair at the scoring read)."""
    out = {}
    m = meta(Z)
    first = Z[next(iter(Z))]
    for run, arms in runs_of(Z).items():
        for ep in ("r_in", "r_in_old", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in"):
            if f"{run}/{ep}" not in first:
                continue
            for a in arms:
                out[f"{run}/{ep}/{a}"] = {"pooled": [round(float(case(Z, run, ep, a, t).mean()), 6) for t in D.READS],
                                          "pairs": {f"{b}/{un}": round(float(case(Z, run, ep, a, D.T_READ, ((b, un),)).mean()), 6)
                                                    for b, un in PAIRS}}
        for sc in ("opened", "opened_out", "onset", "hit"):
            for a in arms:
                out[f"{run}/{sc}/{a}"] = round(float(raw_scalar(Z, run, sc, a).mean()), 6)
    return {"tag": m["tag"], "digest": m["design_digest"], "blocks": blocks_of(Z), "reads": list(D.READS), "levels": out}


def det_profile(Z, run, a):
    """One detector arm in one run, over its lineage-cases: rates (at all, on the patch), onset, footprint, channel."""
    on = raw_scalar(Z, run, "det_on", a)
    f = on > 0
    fp, fpi = raw_scalar(Z, run, "det_fp", a), raw_scalar(Z, run, "det_fp_in", a)
    by = raw_scalar(Z, run, "det_by", a).astype(int)
    t = on[f]
    return {"p_fired": float(f.mean()), "p_located": float((fpi > 0).mean()),
            "onset_median": float(np.median(t)) if t.size else None,
            "onset_q90": float(np.quantile(t, 0.9)) if t.size else None,
            "by_half_t_star": float((f & (on <= D.T_STAR / 2)).mean()), "by_t_star": float((f & (on <= D.T_STAR)).mean()),
            "fp_cells_mean": float(fp[f].mean()) if t.size else None,
            "patch_covered_mean": float(fpi[f].mean()) if t.size else None,
            "by_cue": float((f & (by & 1 > 0)).mean()), "by_body": float((f & (by & 2 > 0)).mean())}


def detectors(Z):
    """Per det arm and run: det_profile among the lineage-cases."""
    return {f"{run}/{a}": det_profile(Z, run, a) for run, arms in runs_of(Z).items() for a in arms if a in D.DET_ARMS}


def utilities(Z):
    runs = runs_of(Z)
    arms = runs[D.run_name("none", 0.0)]
    out = {"U": {a: ci(U(Z, a)) for a in arms}, "U_ceiling": ci(U_ceiling(Z)),
           "U_ctrl_0.9_0.1": ci(U_ctrl(Z, 0.9, 0.1)), "U_ctrl_grid": {f"{h:g},{f:g}": float(U_ctrl(Z, h, f).mean())
                                                                     for h in GRID for f in GRID}}
    jsonify = lambda t: {k: (ci(v) if not isinstance(v, dict) else {s: ci(x) for s, x in v.items()}) for k, v in t.items()}
    out["gap"] = {"ceiling": jsonify(gap(Z))}
    rest = U(Z, "rest")
    for a in (x for x in arms if x in D.DET_ARMS):
        h, f = plane_rates(Z, a)
        pred, loc, Ud = U_mix(Z, a, "fired"), U_mix(Z, a, "located"), U(Z, a)
        out["gap"][a] = jsonify(gap(Z, a))
        out[a] = {"U_minus_vote": ci(Ud - U(Z, D.BEST)), "U_pred": ci(pred), "U_loc": ci(loc), "price": ci(Ud - pred),
                  "price_loc": ci(Ud - loc), "h": ci(h), "f": ci(f), "U_plane_at_hf": float(U_ctrl(Z, h.mean(), f.mean()).mean()),
                  "worth_kept_vs_0.9_0.1": float((Ud - rest).mean() / (U_ctrl(Z, 0.9, 0.1) - rest).mean()),
                  "worth_kept_vs_ceiling": float((Ud - rest).mean() / (U_ceiling(Z) - rest).mean()),
                  "rates": {s: ci(rate(Z, a, s)) for s in D.SITUATIONS},
                  "located": {s: ci(rate(Z, a, s, which="located")) for s in D.SITUATIONS},
                  "u": {s: ci(u(Z, a, s)) for s in D.SCORINGS},
                  "sham": {run: ci(sham(Z, run, a)) for run in runs if a in runs[run] and "rest" in runs[run]}}
    if "det" in arms and "det-v" in arms:
        out["det_minus_det_v"] = ci(U(Z, "det") - U(Z, "det-v"))
    out["u_by_arm"] = {a: {s: float(u(Z, a, s).mean()) for s in D.SCORINGS} for a in arms}
    return out


def side_arms(Z):
    """The misread side arm: every arm's sigma 1 less sigma 0, and the detectors' sheet costs and rates under misreads."""
    out = {}
    runs = runs_of(Z)
    first = Z[next(iter(Z))]
    for sit in D.MISREAD:
        run1 = D.run_name(sit, D.MISREAD_SIGMA)
        if run1 not in runs:
            continue
        for a in runs[run1]:
            for ep in ("r_in", "r_in_old", "r_all"):
                if f"{run1}/{ep}" in first:
                    out[f"{run1}/{ep}/{a}-sigma0"] = ci(case(Z, run1, ep, a) - case(Z, D.run_name(sit, 0.0), ep, a))
        for a in (x for x in runs[run1] if x in D.DET_ARMS):
            out[f"{run1}/sham/{a}"] = ci(sham(Z, run1, a))
            out[f"{run1}/rate/{a}"] = ci(rate(Z, a, sit, D.MISREAD_SIGMA))
    return out


def sizes(Z):
    """The size side arm (the lead's ruling 2): memory and correlated damage on 2 x 2, 4 x 4 (the main grid) and 8 x 8
    patches: u per arm, the dial's worth u(dial) - u(rest), and each detector's rates, onset, footprint and its own
    worth u(det) - u(rest)."""
    out = {}
    runs = runs_of(Z)
    for sit in D.SIZE_SITUATIONS:
        for L in sorted(set(D.SIZES) | {D.SIZE}):
            run = D.run_name(sit, 0.0, size=L)
            if run not in runs:
                continue
            arms = runs[run]
            row = {"size": L, "u": {a: ci(case(Z, run, "r_in", a)) for a in arms},
                   "dial_worth": ci(case(Z, run, "r_in", "dial") - case(Z, run, "r_in", "rest"))}
            for a in (x for x in arms if x in D.DET_ARMS):
                row[a] = dict(det_profile(Z, run, a), rate_fired=ci(rate(Z, a, sit, size=L)),
                              rate_located=ci(rate(Z, a, sit, which="located", size=L)),
                              worth=ci(case(Z, run, "r_in", a) - case(Z, run, "r_in", "rest")))
            out[run] = row
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = load(a.root)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(summaries(Z), separators=(",", ":")) + "\n")
    (a.out / "detectors.json").write_text(json.dumps(detectors(Z), indent=0) + "\n")
    (a.out / "utilities.json").write_text(json.dumps(utilities(Z), separators=(",", ":")) + "\n")
    (a.out / "side_arms.json").write_text(json.dumps(side_arms(Z), separators=(",", ":")) + "\n")
    (a.out / "sizes.json").write_text(json.dumps(sizes(Z), separators=(",", ":")) + "\n")
    print("wrote", sorted(p.name for p in a.out.iterdir()))


if __name__ == "__main__":
    main()
