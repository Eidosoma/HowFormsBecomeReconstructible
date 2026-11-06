"""AR005's reader: python -m ar005.analyze --root STAGE_ROOT --out OUT_DIR

AR003's pooled arithmetic, from ar003.analyze imported unchanged (each run's arms read from the shards' own meta): per
case the mean over the eight unit-body pairs, a block's value the mean over its eight cases; u(arm, run) is the record's
agreement with the run's correct target inside its patch at t = 8,000. The vote never reads the cue, so its value under
misreads is its sigma-0 run's. Intervals are 95% t over the blocks with the lane's SD: the larger of the block SD and the
case SD / sqrt 8 (ci). The contrasts, per case, the size means over 4 x 4 and 8 x 8 (STATEMENT_SIZES):
  R1      (1/2) sum over sizes of u(arm, memory@1) - u(vms, memory@1)            the misread recovery (vguard, vpool)
  R0      the same at sigma 0                                                   sigma-0 hits kept
  W1      (1/2) sum over sizes of u(arm, memory@1) - u(vote, memory@0)          the worth over the vote under misreads
  sham    r_all(vote) - r_all(arm), cue@0 and none@0; none@1 against the vote's none@0   the sheet's costs
  give    u(arm) - u(vote) in the 4 x 4 patch; at sigma 1 against the vote's sigma-0 run
  corr    u(vpool) - u(vguard) in correlated damage at sigma 0 and 1 (the blind spot's cost)
  rates   the arm's detector fired at all / with its footprint on the patch, by run
Reported beside them: every arm's u by run and size (2 x 2 included where run), the recovery fraction, the misread
losses, vms's and vpool's sheet costs, give under cue@0, body damage, and the detectors' rates, onsets and footprints.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar003 import analyze as AZ  # noqa: E402  (load, case, rate, det_profile, has, runs_of; unchanged)
from ar005 import design as D  # noqa: E402

PAIRS = AZ.PAIRS
load, case, has, runs_of, det_profile, blocks_of = AZ.load, AZ.case, AZ.has, AZ.runs_of, AZ.det_profile, AZ.blocks_of
S1, C, SZ = D.MISREAD_SIGMA, D.CONTROLLER, D.STATEMENT_SIZES


def ci(v):
    """The pooled value of a (blocks, cases) array with its 95% t interval over the blocks; the SD is the larger of the
    block SD and the case SD / sqrt 8 (the lane's rule)."""
    blk = v.mean(-1)
    nb, m = len(blk), float(blk.mean())
    sdb = float(blk.std(ddof=1)) if nb > 1 else 0.0
    sdc = float(v.ravel().std(ddof=1) / math.sqrt(8)) if v.size > 1 else 0.0
    sd = max(sdb, sdc)
    h = float(stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb)) if nb > 1 else 0.0
    return {"mean": m, "lo": m - h, "hi": m + h, "sd": sd, "sd_block": sdb, "sd_case8": sdc,
            "blocks": [float(x) for x in blk]}


def rn(situation, L=D.SIZE, sigma=0.0):
    return D.run_name(situation, sigma, size=L)


def u(Zs, arm, situation, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    """(blocks, cases): u(arm) in the run; the vote's sigma-1 value is its sigma-0 run's (it never reads the cue)."""
    run = rn(situation, L, sigma)
    if not has(Zs, run, arm) and arm == D.BEST:
        run = rn(situation, L, 0.0)
    return case(Zs, run, "r_in", arm, pairs=pairs)


def size_mean(Zs, a, b, sigma_a, sigma_b, sizes=SZ, pairs=PAIRS):
    """(blocks, cases): (1/n) sum over sizes of u(a, memory, sigma_a) - u(b, memory, sigma_b)."""
    return sum(u(Zs, a, "memory", L, sigma_a, pairs) - u(Zs, b, "memory", L, sigma_b, pairs) for L in sizes) / len(sizes)


def R1(Zs, a=C, sizes=SZ, pairs=PAIRS):
    return size_mean(Zs, a, "vms", S1, S1, sizes, pairs)


def R0(Zs, a=C, sizes=SZ, pairs=PAIRS):
    return size_mean(Zs, a, "vms", 0.0, 0.0, sizes, pairs)


def W1(Zs, a=C, sizes=SZ, pairs=PAIRS):
    return size_mean(Zs, a, D.BEST, S1, 0.0, sizes, pairs)


def kept(Zs, k, sizes=SZ, pairs=PAIRS):
    """(blocks, cases): R1(vguard) - k R1(vpool), the share k of vpool's misread recovery kept (as AR003's E5)."""
    return R1(Zs, C, sizes, pairs) - k * R1(Zs, "vpool", sizes, pairs)


def sham(Zs, run, arm, pairs=PAIRS):
    """(blocks, cases): r_all(vote) - r_all(arm); a sigma-1 run takes the vote's sigma-0 run."""
    return AZ.sham(Zs, run, arm, pairs=pairs)


def give(Zs, arm, situation, sigma=0.0, pairs=PAIRS):
    """(blocks, cases): u(arm) - u(vote) in the 4 x 4 patch (at sigma 1 against the vote's sigma-0 run)."""
    return u(Zs, arm, situation, D.SIZE, sigma, pairs) - u(Zs, D.BEST, situation, D.SIZE, 0.0, pairs)


def corr(Zs, sigma, a="vpool", b=C, pairs=PAIRS):
    """(blocks, cases): u(a) - u(b) in correlated damage at 4 x 4: what the guard gives up where body and record share
    the error."""
    return u(Zs, a, "correlated", D.SIZE, sigma, pairs) - u(Zs, b, "correlated", D.SIZE, sigma, pairs)


def rate(Zs, arm, situation, L=D.SIZE, sigma=0.0, which="fired", pairs=PAIRS):
    return AZ.rate(Zs, arm, situation, L, sigma, which, pairs)


def recovery(Zs, sizes=SZ):
    """The recovery fraction: R1(arm) over vms's own misread loss u(vms, sigma 0) - u(vms, sigma 1), pooled."""
    den = size_mean(Zs, "vms", "vms", 0.0, S1, sizes)
    if not float(den.mean()):
        return {}
    return {a: float(R1(Zs, a, sizes).mean() / den.mean()) for a in ("vpool", C) if has(Zs, rn("memory", sizes[0], S1), a)}


def contrasts(Zs):
    """Every contrast the shards can carry (the probe runs a subset of the registered runs)."""
    have = lambda run, *arms: all(has(Zs, run, a) for a in arms)
    m1 = all(have(rn("memory", L, S1), "vms", C) for L in SZ)
    m0 = all(have(rn("memory", L, 0.0), "vms", C) for L in SZ)
    out = {}
    if m1:
        out["K3 R1 vguard (misread recovery over vms, sizes 4 and 8)"] = R1(Zs)
        if all(has(Zs, rn("memory", L, S1), "vpool") for L in SZ):
            out["R1 vpool (sizes 4 and 8)"] = R1(Zs, "vpool")
            out["R1 vguard less vpool"] = R1(Zs) - R1(Zs, "vpool")
        out["vms misread loss (sigma 1 - sigma 0)"] = size_mean(Zs, "vms", "vms", S1, 0.0) if m0 else None
    if m0:
        out["K4 R0 vguard (sigma-0 hits against vms)"] = R0(Zs)
    if m1 and all(has(Zs, rn("memory", L, 0.0), D.BEST) for L in SZ):
        out["K5 W1 vguard (worth over the vote under misreads)"] = W1(Zs)
        if all(has(Zs, rn("memory", L, S1), "vpool") for L in SZ):
            out["W1 vpool"] = W1(Zs, "vpool")
        out["W1 vms"] = W1(Zs, "vms")
    for run, label in (("cue@0", "K1"), ("none@0", "K2a"), ("none@1", "K2b")):
        for a in ("vms", "vpool", C):
            if has(Zs, run, a):
                out[f"{label + ' ' if a == C else ''}sham {run} {a}"] = sham(Zs, run, a)
    for situation, sigma, label in (("none", 0.0, "K7a give none@0"), ("none", S1, "K7b give none@1"),
                                    ("cue", 0.0, "give cue@0 (reported: inside the patch)"),
                                    ("body", 0.0, "give body@0 (reported)")):
        if has(Zs, rn(situation, D.SIZE, sigma), C):
            out[f"{label} vguard"] = give(Zs, C, situation, sigma)
    for sigma, tag in ((0.0, "a"), (S1, "b")):
        run = rn("correlated", D.SIZE, sigma)
        if have(run, "vpool", C):
            out[f"K6{tag} corr@{sigma:g} cost: u(vpool) - u(vguard)"] = corr(Zs, sigma)
        if has(Zs, run, C):
            out[f"K6c corr@{sigma:g}: u(vguard) - u(vote)"] = give(Zs, C, "correlated", sigma)
            if has(Zs, run, "vms"):
                out[f"corr@{sigma:g}: u(vguard) - u(vms)"] = corr(Zs, sigma, C, "vms")
    for L in D.SIZES:
        for sigma in (0.0, S1):
            run = rn("memory", L, sigma)
            if have(run, "vms", C):
                out[f"u(vguard) - u(vms), memory@{sigma:g} L{L}"] = u(Zs, C, "memory", L, sigma) - u(Zs, "vms", "memory", L, sigma)
            if have(run, "vpool", C):
                out[f"u(vguard) - u(vpool), memory@{sigma:g} L{L}"] = u(Zs, C, "memory", L, sigma) - u(Zs, "vpool", "memory", L, sigma)
    return {k: v for k, v in out.items() if v is not None}


def utilities(Zs):
    X = contrasts(Zs)
    us = {}
    for run, arms in runs_of(Zs).items():
        for a in arms:
            us[f"{a}/{run}"] = float(case(Zs, run, "r_in", a).mean())
    return {"contrasts": {k: ci(v) for k, v in X.items()}, "recovery_fraction": recovery(Zs), "u": us,
            "statement_sizes": list(SZ)}


def detectors(Zs):
    return {f"{run}/{a}": det_profile(Zs, run, a) for run, arms in runs_of(Zs).items() for a in arms
            if a not in (D.BEST,)}


def summaries(Zs):
    out = {}
    m = AZ.meta(Zs)
    first = Zs[next(iter(Zs))]
    for run, arms in runs_of(Zs).items():
        for ep in ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in"):
            if f"{run}/{ep}" not in first:
                continue
            for a in arms:
                out[f"{run}/{ep}/{a}"] = {"pooled": [round(float(case(Zs, run, ep, a, t).mean()), 6) for t in D.READS],
                                          "pairs": {f"{b}/{un}": round(float(case(Zs, run, ep, a, D.T_READ, ((b, un),)).mean()), 6)
                                                    for b, un in PAIRS}}
    return {"tag": m["tag"], "digest": m["design_digest"], "blocks": blocks_of(Zs), "reads": list(D.READS), "levels": out}


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
    print("wrote", sorted(p.name for p in a.out.iterdir()))


if __name__ == "__main__":
    main()
