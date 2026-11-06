"""AR003's reader: python -m ar003.analyze --root STAGE_ROOT --out OUT_DIR

Loads every (body, unit, block) shard (ar002.analyze.load: each run's arms from the shards' own meta, which must agree),
then computes per case (pooled over the eight unit-body pairs: per case the mean over the pairs; a block's value the mean
over its eight cases):
  u_L(arm, s)     the record's agreement with scoring s's correct target inside the L-patch at t = 8,000: memory,
                  correlated, body and shared from their runs at L; none and cue from the 4 x 4 runs scored on the
                  L-patch (r_in_L<L>; at 4 the runs' own r_in); change/new and change/old from change@0 at 4
  U_L(arm)        the mean of u_L over the eight scorings with equal weights; at sizes other than 4 the information-limit
                  pair contributes u(new) + u(old) = 1 exactly (the identity, D1 of AR002; checked at 4 by E1), so U_L
                  uses 1/8 for it; U_4 is AR002's U
  U_mix(arm)      the size mix: the mean of U_2, U_4 and U_8 (equal weights)
  fire / located  the arm's detector fired (det_on > 0), and with its footprint covering a patch cell (det_fp_in > 0)
  sham(arm, run)  the sheet's cost against the default alone: r_all(vote) - r_all(arm) at t = 8,000 (for the misread
                  runs the vote's own none@0 / memory@0, since the vote never reads the cue)
  share_L         the declared signal's worth kept in memory and correlated damage at L: the pooled
                  (u(vms) - u(vote)) / (u(vdial) - u(vote)) over the two situations
  gap(arm)        U_4(arm) - U_4(vote) in its terms (hits over the vote, the four scorings, the pair)
and writes summaries (every run, arm and endpoint at every read, pooled and per pair), the detectors' rates, onsets and
footprints by run, the utilities by size and over the mix with every contrast, and the misread side arm.
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

from ar002 import analyze as Z2  # noqa: E402
from ar003 import design as D  # noqa: E402

PAIRS = Z2.PAIRS
load, blocks_of, meta, runs_of, raw_case, raw_scalar, ci = (Z2.load, Z2.blocks_of, Z2.meta, Z2.runs_of, Z2.raw_case,
                                                            Z2.raw_scalar, Z2.ci)
FOUR, HITS, PAIR = D.FOUR, D.HITS, D.PAIR


def rn(situation, size=D.SIZE, sigma=0.0):
    return D.run_name(situation, sigma, size=size)


def case(Zs, run, ep, arm, read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): per case the mean over the pairs."""
    return raw_case(Zs, run, ep, arm, read, pairs).mean(1)


def has(Zs, run, arm):
    return run in runs_of(Zs) and arm in runs_of(Zs)[run]


def u_raw(Zs, arm, s, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    """(blocks, pairs, cases): u_L(arm, s)."""
    sit, _, which = s.partition("/")
    if sit in D.SIZE_FREE and L != D.SIZE:
        run = rn(sit, D.SIZE, sigma)
        ai = runs_of(Zs)[run].index(arm)
        return np.array([[Zs[(b, u, k)][f"{run}/r_in_L{L}"][ai] for b, u in pairs] for k in blocks_of(Zs)])
    run = rn(sit, L, sigma)
    return raw_case(Zs, run, "r_in_old" if which == "old" else "r_in", arm, D.T_READ, pairs)


def u(Zs, arm, s, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    """(blocks, cases)."""
    return u_raw(Zs, arm, s, L, sigma, pairs).mean(1)


def U_L(Zs, arm, L, pairs=PAIRS):
    """(blocks, cases): the mean of u_L over the eight scorings; the pair from change@0 at 4 where the arm ran there,
    else its identity value (1 over the two scorings)."""
    tot = 0.0
    for s in D.SCORINGS:
        if s in PAIR:
            continue
        tot = tot + D.WEIGHTS[s] * u(Zs, arm, s, L, pairs=pairs)
    if L == D.SIZE and has(Zs, rn("change"), arm):
        tot = tot + sum(D.WEIGHTS[s] * u(Zs, arm, s, L, pairs=pairs) for s in PAIR)
    else:
        tot = tot + D.WEIGHTS[PAIR[0]] * 1.0
    return tot


def U_mix(Zs, arm, pairs=PAIRS):
    return sum(D.SIZE_WEIGHTS[L] * U_L(Zs, arm, L, pairs) for L in D.SIZES)


def four(Zs, arm, other, L=D.SIZE, pairs=PAIRS):
    """(blocks, cases): sum over none, body, shared and cue of (1/8)(u_L(arm) - u_L(other))."""
    return sum(D.WEIGHTS[s] * (u(Zs, arm, s, L, pairs=pairs) - u(Zs, other, s, L, pairs=pairs)) for s in FOUR)


def hits(Zs, arm, other, L=D.SIZE, pairs=PAIRS):
    """(blocks, cases): sum over memory and correlated of (1/8)(u_L(arm) - u_L(other))."""
    return sum(D.WEIGHTS[s] * (u(Zs, arm, s, L, pairs=pairs) - u(Zs, other, s, L, pairs=pairs)) for s in HITS)


def fired(Zs, arm, situation, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    return raw_scalar(Zs, rn(situation, L, sigma), "det_on", arm, pairs) > 0


def located(Zs, arm, situation, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    return raw_scalar(Zs, rn(situation, L, sigma), "det_fp_in", arm, pairs) > 0


def rate(Zs, arm, situation, L=D.SIZE, sigma=0.0, which="fired", pairs=PAIRS):
    """(blocks, cases): the pooled rate."""
    return (fired if which == "fired" else located)(Zs, arm, situation, L, sigma, pairs).astype(float).mean(1)


def sham(Zs, run, arm, ref="vote", ep="r_all", read=D.T_READ, pairs=PAIRS):
    """(blocks, cases): the sheet's cost against the default alone, r_all(ref) - r_all(arm); the misread runs take the
    vote's sigma-0 run (the vote never reads the cue)."""
    refrun = run if has(Zs, run, ref) else run.replace("@1", "@0")
    return case(Zs, refrun, ep, ref, read, pairs) - case(Zs, run, ep, arm, read, pairs)


def worth(Zs, arm, L, on="vdial", off="vote", pairs=PAIRS):
    """(blocks, cases) numerator and denominator of the share: sums over memory and correlated of u(arm) - u(off) and of
    u(on) - u(off)."""
    num = sum(u(Zs, arm, s, L, pairs=pairs) - u(Zs, off, s, L, pairs=pairs) for s in HITS)
    den = sum(u(Zs, on, s, L, pairs=pairs) - u(Zs, off, s, L, pairs=pairs) for s in HITS)
    return num, den


def share(Zs, arm, L, pairs=PAIRS):
    num, den = worth(Zs, arm, L, pairs=pairs)
    return float(num.mean() / den.mean())


def kept(Zs, arm, L, k, pairs=PAIRS):
    """(blocks, cases): the linear form of the share, (u(arm) - u(vote)) - k (u(vdial) - u(vote)), summed over memory and
    correlated: positive when the arm keeps more than a share k of the declared signal's worth."""
    num, den = worth(Zs, arm, L, pairs=pairs)
    return num - k * den


def price_hits(Zs, arm, L=D.SIZE, pairs=PAIRS):
    """(blocks, cases): over memory and correlated, (1/8) [u(arm) - (fire x u(vdial) + (1 - fire) x u(vote))] per
    lineage-case: what the detector's own onset and footprint cost against the declared signal at its own firing."""
    tot = 0.0
    for s in HITS:
        f = fired(Zs, arm, s, L, pairs=pairs).astype(float)
        pred = f * u_raw(Zs, "vdial", s, L, pairs=pairs) + (1 - f) * u_raw(Zs, "vote", s, L, pairs=pairs)
        tot = tot + D.WEIGHTS[s] * (u_raw(Zs, arm, s, L, pairs=pairs) - pred).mean(1)
    return tot


def info_limit(Zs, arms=None):
    """(blocks, cases): the largest abs(u(new) + u(old) - 1) over every arm (or `arms`) of every change run."""
    return Z2.info_limit(Zs, arms)


def summaries(Zs):
    out = {}
    m = meta(Zs)
    first = Zs[next(iter(Zs))]
    for run, arms in runs_of(Zs).items():
        for ep in ("r_in", "r_in_old", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in"):
            if f"{run}/{ep}" not in first:
                continue
            for a in arms:
                out[f"{run}/{ep}/{a}"] = {"pooled": [round(float(case(Zs, run, ep, a, t).mean()), 6) for t in D.READS],
                                          "pairs": {f"{b}/{un}": round(float(case(Zs, run, ep, a, D.T_READ, ((b, un),)).mean()), 6)
                                                    for b, un in PAIRS}}
        for L in D.SIZES:
            if f"{run}/r_in_L{L}" in first:
                for ai, a in enumerate(arms):
                    out[f"{run}/r_in_L{L}/{a}"] = round(float(np.mean([[Zs[(b, un, k)][f"{run}/r_in_L{L}"][ai] for b, un in PAIRS]
                                                                     for k in blocks_of(Zs)])), 6)
        for sc in ("opened", "opened_out", "onset", "hit"):
            for a in arms:
                out[f"{run}/{sc}/{a}"] = round(float(raw_scalar(Zs, run, sc, a).mean()), 6)
    return {"tag": m["tag"], "digest": m["design_digest"], "blocks": blocks_of(Zs), "reads": list(D.READS), "levels": out}


def det_profile(Zs, run, a):
    on = raw_scalar(Zs, run, "det_on", a)
    f = on > 0
    fp, fpi = raw_scalar(Zs, run, "det_fp", a), raw_scalar(Zs, run, "det_fp_in", a)
    t = on[f]
    return {"p_fired": float(f.mean()), "p_located": float((fpi > 0).mean()),
            "onset_median": float(np.median(t)) if t.size else None,
            "onset_q90": float(np.quantile(t, 0.9)) if t.size else None,
            "by_half_t_star": float((f & (on <= D.T_STAR / 2)).mean()), "by_t_star": float((f & (on <= D.T_STAR)).mean()),
            "fp_cells_mean": float(fp[f].mean()) if t.size else None,
            "patch_covered_mean": float(fpi[f].mean()) if t.size else None}


DET_ARMS = ("det", "ms", "vms")


def detectors(Zs):
    return {f"{run}/{a}": det_profile(Zs, run, a) for run, arms in runs_of(Zs).items() for a in arms if a in DET_ARMS}


def utilities(Zs):
    out = {"U_L": {}, "U_mix": {}, "u": {}}
    for L in D.SIZES:
        for a in ("vote", "det", "ms", "vms"):
            if a == "ms" and L == 8:
                continue
            out["U_L"][f"{a}/L{L}"] = ci(U_L(Zs, a, L))
            out["u"][f"{a}/L{L}"] = {s: float(u(Zs, a, s, L).mean()) for s in D.SCORINGS
                                     if s not in PAIR or L == D.SIZE and has(Zs, rn("change"), a)}
        for s in HITS:
            out["u"][f"vdial/L{L}/{s}"] = float(u(Zs, "vdial", s, L).mean()) if has(Zs, rn(s, L), "vdial") else None
    for a in ("vote", "det", "vms"):
        out["U_mix"][a] = ci(U_mix(Zs, a))
    c = {"a: U_mix(vms) - U_mix(vote)": U_mix(Zs, "vms") - U_mix(Zs, "vote"),
         "U_mix(vms) - U_mix(det)": U_mix(Zs, "vms") - U_mix(Zs, "det"),
         "U_mix(det) - U_mix(vote)": U_mix(Zs, "det") - U_mix(Zs, "vote")}
    for L in D.SIZES:
        c[f"b: U_{L}(vms) - U_{L}(det)"] = U_L(Zs, "vms", L) - U_L(Zs, "det", L)
        c[f"U_{L}(vms) - U_{L}(vote)"] = U_L(Zs, "vms", L) - U_L(Zs, "vote", L)
        c[f"U_{L}(det) - U_{L}(vote)"] = U_L(Zs, "det", L) - U_L(Zs, "vote", L)
    c["c: four at 4: vms - ms"] = four(Zs, "vms", "ms")
    c["c: U_2(vms) - U_2(ms)"] = U_L(Zs, "vms", 2) - U_L(Zs, "ms", 2)
    c["c: hits at 2: vms - ms"] = hits(Zs, "vms", "ms", 2)
    c["four at 4: vms - vote (non-inferiority)"] = four(Zs, "vms", "vote")
    c["four at 4: ms - det"] = four(Zs, "ms", "det")
    c["U_4(ms) - U_4(det)"] = U_L(Zs, "ms", 4) - U_L(Zs, "det", 4)
    c["U_2(ms) - U_2(det)"] = U_L(Zs, "ms", 2) - U_L(Zs, "det", 2)
    for L in (4, 8):
        for k in (0.5, 0.8, 0.9):
            c[f"d: kept at {L} over {k:g} (memory + correlated)"] = kept(Zs, "vms", L, k)
    c["e: sham cue@0 vms"] = sham(Zs, rn("cue"), "vms")
    c["e: sham none@0 vms"] = sham(Zs, rn("none"), "vms")
    c["price at 4 (hits)"] = price_hits(Zs, "vms", 4)
    c["price at 8 (hits)"] = price_hits(Zs, "vms", 8)
    out["contrasts"] = {k: ci(v) for k, v in c.items()}
    out["share"] = {f"L{L}": share(Zs, "vms", L) for L in (4, 8)}
    out["share_by_situation"] = {f"L{L}/{s}": float((u(Zs, "vms", s, L) - u(Zs, "vote", s, L)).mean()
                                                    / (u(Zs, "vdial", s, L) - u(Zs, "vote", s, L)).mean())
                                 for L in (4, 8) for s in HITS}
    out["share_det_rest_default"] = {f"L{L}": float(sum((u(Zs, "det", s, L) - u(Zs, "vote", s, L)).mean() for s in HITS)
                                                    / sum((u(Zs, "vdial", s, L) - u(Zs, "vote", s, L)).mean() for s in HITS))
                                     for L in (4, 8)}
    rates = {}
    for a in DET_ARMS:
        for run, arms in runs_of(Zs).items():
            if a in arms and "@0" in run:
                sit, L = run.split("@")[0], (int(run.split("-L")[1]) if "-L" in run else D.SIZE)
                rates[f"{run}/{a}/fired"] = ci(rate(Zs, a, sit, L))
                rates[f"{run}/{a}/located"] = ci(rate(Zs, a, sit, L, which="located"))
    out["rates"] = rates
    out["sham"] = {f"{run}/{a}": ci(sham(Zs, run, a)) for run in (rn("cue"), rn("none")) for a in ("det", "ms", "vms")}
    gp = {"hits": hits(Zs, "vms", "vote"), "four": four(Zs, "vms", "vote"),
          "pair": sum(D.WEIGHTS[s] * (u(Zs, "vms", s) - u(Zs, "vote", s)) for s in PAIR)}
    gp["total"] = gp["hits"] + gp["four"] + gp["pair"]
    out["gap_4"] = {k: ci(v) for k, v in gp.items()}
    return out


def side_arms(Zs):
    out = {}
    for sit in ("none", "memory"):
        run1, run0 = rn(sit, sigma=D.MISREAD_SIGMA), rn(sit)
        if run1 not in runs_of(Zs):
            continue
        for a in runs_of(Zs)[run1]:
            out[f"{run1}/r_in/{a}-sigma0"] = ci(case(Zs, run1, "r_in", a) - case(Zs, run0, "r_in", a))
            out[f"{run1}/r_all/{a}-sigma0"] = ci(case(Zs, run1, "r_all", a) - case(Zs, run0, "r_all", a))
            out[f"{run1}/sham/{a}"] = ci(sham(Zs, run1, a))
            out[f"{run1}/rate/{a}"] = ci(rate(Zs, a, sit, D.SIZE, D.MISREAD_SIGMA))
            out[f"{run1}/located/{a}"] = ci(rate(Zs, a, sit, D.SIZE, D.MISREAD_SIGMA, which="located"))
            out[f"{run1}/u/{a}"] = ci(case(Zs, run1, "r_in", a))
        out[f"{run1}/vms-det misread loss difference"] = ci((case(Zs, run1, "r_in", "vms") - case(Zs, run0, "r_in", "vms"))
                                                           - (case(Zs, run1, "r_in", "det") - case(Zs, run0, "r_in", "det")))
        out[f"{run1}/u(vms) - u(det)"] = ci(case(Zs, run1, "r_in", "vms") - case(Zs, run1, "r_in", "det"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Zs = load(a.root)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(summaries(Zs), separators=(",", ":")) + "\n")
    (a.out / "detectors.json").write_text(json.dumps(detectors(Zs), indent=0) + "\n")
    (a.out / "utilities.json").write_text(json.dumps(utilities(Zs), separators=(",", ":")) + "\n")
    (a.out / "side_arms.json").write_text(json.dumps(side_arms(Zs), separators=(",", ":")) + "\n")
    print("wrote", sorted(p.name for p in a.out.iterdir()))


if __name__ == "__main__":
    main()
