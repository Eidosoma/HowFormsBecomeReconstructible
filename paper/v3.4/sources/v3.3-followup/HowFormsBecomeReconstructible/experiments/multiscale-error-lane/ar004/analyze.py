"""AR004's reader: python -m ar004.analyze --root STAGE_ROOT --out OUT_DIR

AR003's pooled arithmetic, from ar003.analyze imported unchanged (each run's arms read from the shards' own meta): per
case the mean over the eight unit-body pairs, a block's value the mean over its eight cases; u(arm, run) is the record's
agreement with the run's correct target inside its patch at t = 8,000. The vote never reads the cue, so its value under
misreads is its sigma-0 run's. The contrasts, per case:
  R1      (1/3) sum over sizes 2, 4, 8 of u(vpool, memory, sigma 1) - u(vms, memory, sigma 1)      the misread recovery
  R0      the same at sigma 0                                                                    sigma-0 hits kept
  sham    r_all(vote) - r_all(arm) in cue@0 and none@0, and in none@1 against the vote's none@0   the sheet's costs
          (G3: vpool less vms in cue@0, vpool's own in cue@0, and its own in none@0 within the confirmed 0.002;
          the confirmed 0.01 bound under cue damage is context only)
  give    u(arm) - u(vote) in the 4 x 4 patch in none@0, cue@0, and none@1 against the vote's none@0
  W1      (1/3) sum over sizes of u(arm, memory, sigma 1) - u(vote, memory, sigma 0)             the worth under misreads
  rates   the arm's detector fired at all / with its footprint on the patch, by run
Reported beside them: the recovery fraction (R1 over vms's own misread loss, pooled and by size), vms's misread loss, the
detectors' rates, onsets and footprints by run, and the 6 x 6 side arm where its runs are present.
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

from ar003 import analyze as AZ  # noqa: E402  (load, case, sham, rate, det_profile, ci, has, runs_of; unchanged)
from ar004 import design as D  # noqa: E402

PAIRS = AZ.PAIRS
load, ci, case, has, runs_of, det_profile = AZ.load, AZ.ci, AZ.case, AZ.has, AZ.runs_of, AZ.det_profile
S1 = D.MISREAD_SIGMA


def rn(situation, L=D.SIZE, sigma=0.0):
    return D.run_name(situation, sigma, size=L)


def u(Zs, arm, situation, L=D.SIZE, sigma=0.0, pairs=PAIRS):
    """(blocks, cases): u(arm) in the run; the vote's sigma-1 value is its sigma-0 run's (it never reads the cue)."""
    run = rn(situation, L, sigma)
    if not has(Zs, run, arm) and arm == D.BEST:
        run = rn(situation, L, 0.0)
    return case(Zs, run, "r_in", arm, pairs=pairs)


def size_mean(Zs, a, b, sigma_a, sigma_b, sizes=D.SIZES, pairs=PAIRS):
    """(blocks, cases): (1/n) sum over sizes of u(a, memory, sigma_a) - u(b, memory, sigma_b)."""
    return sum(u(Zs, a, "memory", L, sigma_a, pairs) - u(Zs, b, "memory", L, sigma_b, pairs) for L in sizes) / len(sizes)


def R1(Zs, a=D.CONTROLLER, b="vms", pairs=PAIRS):
    return size_mean(Zs, a, b, S1, S1, pairs=pairs)


def R0(Zs, a=D.CONTROLLER, b="vms", pairs=PAIRS):
    return size_mean(Zs, a, b, 0.0, 0.0, pairs=pairs)


def W1(Zs, a=D.CONTROLLER, pairs=PAIRS):
    return size_mean(Zs, a, D.BEST, S1, 0.0, pairs=pairs)


def sham(Zs, run, arm, pairs=PAIRS):
    return AZ.sham(Zs, run, arm, pairs=pairs)


def give(Zs, arm, situation, sigma=0.0, pairs=PAIRS):
    """(blocks, cases): u(arm) - u(vote) in the 4 x 4 patch."""
    return u(Zs, arm, situation, D.SIZE, sigma, pairs) - u(Zs, D.BEST, situation, D.SIZE, 0.0, pairs)


def rate(Zs, arm, situation, L=D.SIZE, sigma=0.0, which="fired", pairs=PAIRS):
    return AZ.rate(Zs, arm, situation, L, sigma, which, pairs)


def recovery(Zs, sizes=D.SIZES):
    """The recovery fraction: [u(vpool, sigma 1) - u(vms, sigma 1)] / [u(vms, sigma 0) - u(vms, sigma 1)], pooled."""
    num = size_mean(Zs, D.CONTROLLER, "vms", S1, S1, sizes)
    den = size_mean(Zs, "vms", "vms", 0.0, S1, sizes)
    return float(num.mean() / den.mean()) if float(den.mean()) != 0 else None


def contrasts(Zs):
    C = D.CONTROLLER
    out = {"G1 R1 (misread recovery over vms)": R1(Zs), "G2 R0 (sigma-0 hits against vms)": R0(Zs),
           "G3 (a) sham cue@0, vpool less vms": sham(Zs, "cue@0", C) - sham(Zs, "cue@0", "vms"),
           "G3 (b) sham cue@0 vpool": sham(Zs, "cue@0", C),
           "G3 (c) sham none@0 vpool": sham(Zs, "none@0", C),
           "sham none@1 vpool (the dropped G4)": sham(Zs, "none@1", C),
           "G5 give none@0": give(Zs, C, "none"), "G5 give none@1": give(Zs, C, "none", S1),
           "give cue@0 vpool (reported: the trade-off inside the patch)": give(Zs, C, "cue"),
           "G6 located memory@1 L4": rate(Zs, C, "memory", 4, S1, "located"),
           "G6 located memory@1 L8": rate(Zs, C, "memory", 8, S1, "located"),
           "G6 located memory@1 L4 minus vms": rate(Zs, C, "memory", 4, S1, "located") - rate(Zs, "vms", "memory", 4, S1, "located"),
           "G7 W1 vpool (worth over the vote under misreads)": W1(Zs),
           "W1 vms": W1(Zs, "vms"), "vms misread loss (sigma 1 - sigma 0)": size_mean(Zs, "vms", "vms", S1, 0.0),
           "vpool misread loss (sigma 1 - sigma 0)": size_mean(Zs, C, C, S1, 0.0),
           "sham cue@0 vms": sham(Zs, "cue@0", "vms"), "sham none@0 vms": sham(Zs, "none@0", "vms"),
           "sham none@1 vms": sham(Zs, "none@1", "vms")}
    for L in D.SIZES:
        out[f"R1 at L{L}"] = u(Zs, C, "memory", L, S1) - u(Zs, "vms", "memory", L, S1)
        out[f"R0 at L{L}"] = u(Zs, C, "memory", L, 0.0) - u(Zs, "vms", "memory", L, 0.0)
    return out


def utilities(Zs):
    X = contrasts(Zs)
    out = {"contrasts": {k: ci(v) for k, v in X.items()}, "recovery_fraction": recovery(Zs),
           "recovery_fraction_by_size": {f"L{L}": recovery(Zs, (L,)) for L in D.SIZES},
           "u": {f"{a}/{s}@{z:g}-L{L}": float(u(Zs, a, s, L, z).mean())
                 for a in (D.BEST, "vms", D.CONTROLLER) for s, z, L in [("memory", zz, LL) for zz in (0.0, S1) for LL in D.SIZES]
                 + [("none", 0.0, 4), ("cue", 0.0, 4), ("none", S1, 4)] if not (a == D.BEST and z == S1)}}
    side = {}
    if has(Zs, rn("memory", D.SIDE_SIZE, 0.0), "vms"):
        L = D.SIDE_SIZE
        side = {"u": {f"{a}/memory@{z:g}-L{L}": float(u(Zs, a, "memory", L, z).mean())
                      for a in (D.BEST, "vms", D.CONTROLLER) for z in (0.0, S1) if not (a == D.BEST and z == S1)},
                "R1 at L6": ci(u(Zs, D.CONTROLLER, "memory", L, S1) - u(Zs, "vms", "memory", L, S1)),
                "R0 at L6": ci(u(Zs, D.CONTROLLER, "memory", L, 0.0) - u(Zs, "vms", "memory", L, 0.0)),
                "recovery_fraction_L6": recovery(Zs, (L,)),
                "located": {f"{a}/memory@{z:g}-L{L}": float(rate(Zs, a, "memory", L, z, "located").mean())
                            for a in ("vms", D.CONTROLLER) for z in (0.0, S1)}}
    out["side_arm_6x6"] = side
    return out


def detectors(Zs):
    return {f"{run}/{a}": det_profile(Zs, run, a) for run, arms in runs_of(Zs).items() for a in arms if a in ("vms", D.CONTROLLER)}


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
    return {"tag": m["tag"], "digest": m["design_digest"], "blocks": AZ.blocks_of(Zs), "reads": list(D.READS), "levels": out}


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
