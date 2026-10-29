"""Public settings calibrated on engineering sham trajectories before any development outcome.

python -m me002.calibrate --cpus LIST   (writes me002/frozen/calibration.json)

On the calibration blocks (engineering identities; 16 blocks x 8 cases), for every regime an
arbiter runs in, the read-and-hold route is run for LIFE updates from the released state with
no injury, and per update the mismatch power is logged at site, region and sheet pooling, with
the region-pooled surprise. Thresholds are 99.5% quantiles:
  mismatch_traj[level][L]  of per-trajectory maxima over updates 1..L (L = 1000, 1800, 2500)
  surprise_traj[L]         of per-trajectory maxima of surprise over 1..L (the v2 latch)
  surprise_update['1000']  of all surprise values over 1..1000 (ME001's latch rule)
pooled[s_g]: the same quantiles over the union of the calibration families F0, F2, F4.
newborn[regime]: a message-neutral newborn reading the released R with the same route; maxima
  over updates W+1..LIFE for W = 1000 and 300 (a newborn's latch starts closed for W).
gains[regime][sign arm]: the body gain multiplier that makes the sign arm's mean sham body L1
  over 1000 updates equal that of the linear hold route at the coarser of its two levels, capped
  at 1 (a vote that already delivers less correction than its linear comparator stays native).
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from mse.assay import birth  # noqa: E402
from mse.engine import Ledger, Route, State, run  # noqa: E402
from mse.native import LEVELS, NATIVE  # noqa: E402
from mse.ops import project  # noqa: E402
from me002.policies import Gain  # noqa: E402

WINDOWS = (1000, 1800, 2500)
NEWBORN_W = (1000, 300)
CAL = lambda: list(range(*D.IDENTITIES["calibration"]))
HOLD = Route(reference=None)


def log_features(s, th, Z, p, L):
    """Per-update (L, n) mismatch at each level and region surprise along the hold route."""
    feats = {lvl: [] for lvl in LEVELS}
    feats["surprise"] = []

    def tap(Vt, ema, R):
        d = R - Vt
        for lvl in LEVELS:
            feats[lvl].append((project(d, lvl) ** 2).mean(axis=(-2, -1)))
        feats["surprise"].append((project(Vt - ema, "region") ** 2).mean(axis=(-2, -1)))
        return p.gain, 0.0
    run(s, th, lambda t: Z[t - 1], Route(), L, p, policy=tap)
    return {k: np.array(v) for k, v in feats.items()}


def adult(name):
    cases, s0, th, p, T, Tf = sim.prepare(name, CAL(), "engineering")
    Z = sim.draws(cases, "future", updates=D.LIFE)
    return name, log_features(s0, th, Z, p, D.LIFE)


def newborn(name):
    cases, s0, th, p, T, Tf = sim.prepare(name, CAL(), "engineering")
    V = birth(D.TAG, cases, "calib-newborn", "birth")
    s = State(V, V.copy(), s0.R.copy(), np.zeros_like(V))
    Z = sim.draws(cases, "calib-newborn", "life", updates=D.LIFE)
    return name, log_features(s, th, Z, p, D.LIFE)


q = lambda x: float(np.quantile(x, D.QUANTILE))


def adult_thresholds(feats):
    return {"mismatch_traj": {lvl: {str(L): q(feats[lvl][:L].max(0)) for L in WINDOWS} for lvl in LEVELS},
            "surprise_traj": {str(L): q(feats["surprise"][:L].max(0)) for L in WINDOWS},
            "surprise_update": {"1000": q(feats["surprise"][:1000])}}


def pooled_thresholds(group):
    cat = lambda f: np.concatenate(f, axis=1)
    feats = {k: cat([g[k] for g in group]) for k in group[0]}
    return adult_thresholds(feats)


def newborn_thresholds(feats):
    return {"mismatch_traj": {lvl: {str(W): q(feats[lvl][W:].max(0)) for W in NEWBORN_W} for lvl in LEVELS},
            "surprise_traj": {str(W): q(feats["surprise"][W:].max(0)) for W in NEWBORN_W}}


def dose(name, arm_name, kappa, prepared):
    cases, s0, th, p, Z = prepared
    arm = D.ARM["E"][arm_name]
    ledger = Ledger.zeros(len(cases))
    policy = Gain(kappa * NATIVE.gain) if kappa is not None else None
    run(State(s0.V, s0.ema, s0.R, np.zeros_like(s0.V)), th, lambda t: Z[t - 1], sim.route(arm), 1000, p,
        ledger=ledger, policy=policy)
    return float(ledger.body_l1.mean())


def gains(name):
    cases, s0, th, p, T, Tf = sim.prepare(name, CAL(), "engineering")
    prepared = (cases, s0, th, p, sim.draws(cases, "future", updates=1000))
    target = {lvl: dose(name, f"hold_{lvl}", None, prepared) for lvl in LEVELS}
    out, report = {}, {}
    for arm in D.PANELS["E"]["arms"]:
        if arm.control != "matched":
            continue
        s, a = arm.body[0], arm.body[2]
        goal = target[D.coarser(s, a)]
        kappa, hist = 1.0, []
        for _ in range(6):
            got = dose(name, arm.name, kappa, prepared)
            hist.append((kappa, got))
            if abs(got / goal - 1) < 1e-3:
                break
            kappa *= goal / got
        out[arm.name] = min(1.0, kappa)   # equal dose only scales a vote down (ME001's caveat: votes over-dose)
        report[arm.name] = {"target_l1": goal, "achieved_l1": hist[-1][1], "matched_kappa": kappa,
                            "capped": kappa > 1.0, "native_l1": hist[0][1], "iterations": hist}
    return name, out, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "frozen" / "calibration.json")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    t0 = time.time()
    regimes = D.calibration_regimes()
    newborn_regimes = list(D.PANELS["F"]["regimes"])
    with ProcessPoolExecutor(len(cpus)) as pool:
        fa = pool.map(adult, regimes)
        fn = pool.map(newborn, newborn_regimes)
        fg = pool.map(gains, D.gain_regimes())
        feats = dict(fa)
        newborn_feats = dict(fn)
        gain_rows = list(fg)
    pools = {}
    for name in regimes:
        if D.parse(name)[0] in D.CAL_FAMILIES:
            pools.setdefault(D.pool_key(name), []).append(feats[name])
    needed = {D.pool_key(r) for v in D.PANELS.values() if any(x.thresholds == "pooled" for x in v["arms"])
              for r in v["regimes"]}
    out = {"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
           "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": None,
           "blocks": list(D.IDENTITIES["calibration"]), "quantile": D.QUANTILE,
           "regimes": {n: adult_thresholds(f) for n, f in feats.items()},
           "pooled": {k: pooled_thresholds(pools[k]) for k in sorted(needed)},
           "pooled_members": {k: sorted(n for n in regimes if D.parse(n)[0] in D.CAL_FAMILIES and D.pool_key(n) == k)
                              for k in sorted(needed)},
           "newborn": {n: newborn_thresholds(f) for n, f in newborn_feats.items()},
           "gains": {n: g for n, g, _ in gain_rows}, "gain_report": {n: r for n, _, r in gain_rows}}
    out["wall_s"] = round(time.time() - t0, 1)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {a.out} in {out['wall_s']} s: {len(out['regimes'])} regimes, {len(out['pooled'])} pools, "
          f"{len(out['newborn'])} newborn, {len(out['gains'])} gain regimes")


if __name__ == "__main__":
    main()
