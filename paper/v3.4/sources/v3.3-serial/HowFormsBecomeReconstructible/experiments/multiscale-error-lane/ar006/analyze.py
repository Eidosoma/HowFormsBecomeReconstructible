"""AR006's reader: python -m ar006.analyze --root STAGE_ROOT --out OUT_DIR

AR005's pooled arithmetic and interval, from ar005.analyze imported unchanged: per case the mean over the eight
unit-body pairs, a block's value the mean over its eight cases; u(arm, run) the record's agreement with the run's correct
target inside its patch at t = 8,000 (the vote's sigma-1 value its sigma-0 run's); intervals 95% t over the blocks with the
lane's SD, the larger of the block SD and the case SD / sqrt 8. The contrasts for vtol, per case, the size means over
4 x 4 and 8 x 8:
  R1      (1/2) sum over sizes of u(arm, memory@1) - u(vms, memory@1)         the misread recovery (vtol, vpool, vguard)
  R0      the same at sigma 0                                                sigma-0 hits kept
  W1      (1/2) sum over sizes of u(arm, memory@1) - u(vote, memory@0)       the worth over the vote under misreads
  sham    r_all(vote) - r_all(arm) in cue@0 and none@0; none@1 against the vote's none@0
  give    u(arm) - u(vote) in the 4 x 4 patch; at sigma 1 against the vote's sigma-0 run
  corr    u(vtol) - u(vms) and u(vtol) - u(vguard) in correlated damage at 4 x 4, sigma 0 and 1
Reported beside them: every arm's u by run, vms's, vpool's and vguard's costs, the recovery fraction, the detectors, and
the branch accounting: per lineage-case, vtol on the vote's branch (it never fired), on vms's or vguard's exactly (its
onset, every endpoint at every read and its trace equal to that arm's), on another branch (a union branch where both
ran; PLAN_AR006.md's derivation), or not compared (a run with neither).
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

from ar005 import analyze as Z5  # noqa: E402  (load, case, u, size_mean, sham, give, rate, ci; unchanged)
from ar006 import design as D  # noqa: E402

PAIRS = Z5.PAIRS
load, case, has, runs_of, det_profile, blocks_of, ci = Z5.load, Z5.case, Z5.has, Z5.runs_of, Z5.det_profile, Z5.blocks_of, Z5.ci
u, size_mean, sham, give, rate = Z5.u, Z5.size_mean, Z5.sham, Z5.give, Z5.rate
S1, C, SZ = D.MISREAD_SIGMA, D.CONTROLLER, D.STATEMENT_SIZES
EPS = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")


def rn(situation, L=D.SIZE, sigma=0.0):
    return D.run_name(situation, sigma, size=L)


def R1(Zs, a=C, sizes=SZ):
    return size_mean(Zs, a, "vms", S1, S1, sizes)


def R0(Zs, a=C, sizes=SZ):
    return size_mean(Zs, a, "vms", 0.0, 0.0, sizes)


def W1(Zs, a=C, sizes=SZ):
    return size_mean(Zs, a, D.BEST, S1, 0.0, sizes)


def kept(Zs, k, sizes=SZ):
    """(blocks, cases): R1(vtol) - k R1(vpool), the share k of vpool's misread recovery kept (as AR003's E5)."""
    return R1(Zs, C, sizes) - k * R1(Zs, "vpool", sizes)


def corr(Zs, sigma, a=C, b="vms"):
    """(blocks, cases): u(a) - u(b) in correlated damage at 4 x 4."""
    return u(Zs, a, "correlated", D.SIZE, sigma) - u(Zs, b, "correlated", D.SIZE, sigma)


def recovery(Zs, sizes=SZ):
    """The recovery fraction: R1(arm) over vms's own misread loss u(vms, sigma 0) - u(vms, sigma 1), pooled."""
    if not all(has(Zs, rn("memory", L, 0.0), "vms") for L in sizes):
        return {}
    den = float(size_mean(Zs, "vms", "vms", 0.0, S1, sizes).mean())
    return {a: float(R1(Zs, a, sizes).mean() / den) for a in ("vpool", "vguard", C)
            if den and all(has(Zs, rn("memory", L, S1), a) for L in sizes)}


def branches(Zs, run):
    """vtol's branch per lineage-case in a run: counts of 'vote' (never fired), 'vms' and 'vguard' (on that arm's branch
    exactly: its onset, every endpoint at every read and its trace equal), 'other' (fired, on neither reference arm's
    branch: a union branch where both ran), and 'not_compared' (fired, in a run with neither reference arm)."""
    arms = runs_of(Zs)[run]
    out = {"n": 0, "vote": 0, "vms": 0, "vguard": 0, "other": 0, "not_compared": 0}
    ai = arms.index(C)
    refs = [a for a in ("vms", "vguard") if a in arms]
    for key in sorted(Zs):
        z = Zs[key]
        on = z[f"{run}/det_on"][ai]
        for c in range(len(on)):
            out["n"] += 1
            if on[c] < 0:
                out["vote"] += 1
                continue
            if not refs:
                out["not_compared"] += 1
                continue
            for ref in refs:
                j = arms.index(ref)
                if (z[f"{run}/det_on"][j][c] == on[c] and np.array_equal(z[f"{run}/trace"][:, ai, c], z[f"{run}/trace"][:, j, c])
                        and all(np.array_equal(z[f"{run}/{e}"][:, ai, c], z[f"{run}/{e}"][:, j, c]) for e in EPS)):
                    out[ref] += 1
                    break
            else:
                out["other"] += 1
    return out


def contrasts(Zs):
    """Every contrast the shards can carry (the probe runs a subset of the registered runs)."""
    have = lambda run, *arms: all(has(Zs, run, a) for a in arms)
    m1 = all(have(rn("memory", L, S1), "vms", C) for L in SZ)
    m0 = all(have(rn("memory", L, 0.0), "vms", C) for L in SZ)
    out = {}
    if m1:
        out["K3 R1 vtol (misread recovery over vms, sizes 4 and 8)"] = R1(Zs)
        for a in ("vpool", "vguard"):
            if all(has(Zs, rn("memory", L, S1), a) for L in SZ):
                out[f"R1 {a} (sizes 4 and 8)"] = R1(Zs, a)
                out[f"R1 vtol less {a}"] = R1(Zs) - R1(Zs, a)
    if m0:
        out["K4 R0 vtol (sigma-0 hits against vms)"] = R0(Zs)
        if m1:
            out["vms misread loss (sigma 1 - sigma 0)"] = size_mean(Zs, "vms", "vms", S1, 0.0)
    if m1 and all(has(Zs, rn("memory", L, 0.0), D.BEST) for L in SZ):
        out["K6 W1 vtol (worth over the vote under misreads)"] = W1(Zs)
        for a in ("vms", "vpool", "vguard"):
            if all(has(Zs, rn("memory", L, S1), a) for L in SZ):
                out[f"W1 {a}"] = W1(Zs, a)
    for run, label in (("cue@0", "K1 (not registered: beside the confirmed 0.01)"), ("none@0", "K2a"), ("none@1", "K2b")):
        for a in ("vms", "vpool", "vguard", C):
            if has(Zs, run, a):
                out[f"{label + ' ' if a == C else ''}sham {run} {a}"] = sham(Zs, run, a)
        if have(run, C, "vms"):
            out[f"sham {run}: vtol less vms (the extra false-alarm cost)"] = sham(Zs, run, C) - sham(Zs, run, "vms")
    for situation, sigma, label in (("none", 0.0, "K7a give none@0"), ("none", S1, "K7b give none@1"),
                                    ("cue", 0.0, "give cue@0 (reported: inside the patch)")):
        if has(Zs, rn(situation, D.SIZE, sigma), C):
            out[f"{label} vtol"] = give(Zs, C, situation, sigma)
    for sigma, ta, tb in ((0.0, "K5a", "K5b"), (S1, "K5c", "K5d")):
        run = rn("correlated", D.SIZE, sigma)
        if have(run, C, "vms"):
            out[f"{ta} corr@{sigma:g}: u(vtol) - u(vms)"] = corr(Zs, sigma)
        if have(run, C, "vguard"):
            out[f"{tb} corr@{sigma:g}: u(vtol) - u(vguard)"] = corr(Zs, sigma, C, "vguard")
        if have(run, C, "vpool"):
            out[f"corr@{sigma:g}: u(vtol) - u(vpool)"] = corr(Zs, sigma, C, "vpool")
    for L in SZ:
        for sigma in (0.0, S1):
            for a in ("vms", "vpool", "vguard"):
                if have(rn("memory", L, sigma), a, C):
                    out[f"u(vtol) - u({a}), memory@{sigma:g} L{L}"] = u(Zs, C, "memory", L, sigma) - u(Zs, a, "memory", L, sigma)
    return out


def utilities(Zs):
    X = contrasts(Zs)
    us = {f"{a}/{run}": float(case(Zs, run, "r_in", a).mean()) for run, arms in runs_of(Zs).items() for a in arms}
    br = {run: branches(Zs, run) for run, arms in runs_of(Zs).items() if C in arms}
    return {"contrasts": {k: ci(v) for k, v in X.items()}, "recovery_fraction": recovery(Zs), "u": us, "branches": br,
            "statement_sizes": list(SZ)}


def detectors(Zs):
    return {f"{run}/{a}": det_profile(Zs, run, a) for run, arms in runs_of(Zs).items() for a in arms if a != D.BEST}


def summaries(Zs):
    out = {}
    m = Z5.AZ.meta(Zs)
    first = Zs[next(iter(Zs))]
    for run, arms in runs_of(Zs).items():
        for ep in EPS:
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
