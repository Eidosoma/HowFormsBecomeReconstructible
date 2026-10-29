"""Track B: soft-mode predictions, computed before any ME001 v2 development outcome.

python -m me001.predict --cpus LIST   (writes me001/frozen/predictions.json)

The quiet-settle + Lyapunov (QSL) predictor has no free parameters. For each regime, hold
route r (inactive, or body correction at site/region/sheet with R held) and condition c, on
the calibration blocks' acquired states (engineering identities, parent 0):
  1. V*_c, the noise-free 1000-update trajectory from the damaged start (nonlinear; R held at
     its damaged value);
  2. Sigma_r, the covariance the linearised noisy update accumulates over the 1000-update
     window, linearised at the sham V* on the centred subspace with noise sigma^2 C. Where the
     update is well damped this is the stationary (Lyapunov) covariance; it stays defined where
     a site is caught mid-flip at the window's end (spectral radius > 1, counted in the output),
     and such a site becomes a coin toss;
  3. per site P(sign match) = Phi(s_i V*_i / sd_i) and P(qualified) = Phi((s_i V*_i - 0.2) / sd_i),
     with s_i the target sign, averaged over sites and cases.
It is a local theory: it ignores noise-driven escape over barriers, so its expected failures
are registered too (PB1c). Theory tables: static transfer of reference errors by band, and
how much of the slow modes each route's sensor can see.
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
from scipy.stats import norm  # noqa: E402

from me001 import design as D  # noqa: E402
from me001.worker import channel, edges, prepare  # noqa: E402
from mse.assay import band_damage, injure, templates  # noqa: E402
from mse.engine import Route, State, run  # noqa: E402
from mse.ops import bands, project  # noqa: E402
from mse.theory import C, sheet_jacobian  # noqa: E402

ROUTES_T = ("inactive", "site", "region", "sheet")
ARM_OF = {"inactive": "inactive", "site": "body_site", "region": "body_region", "sheet": "body_sheet"}
_w, _v = np.linalg.eigh(C)
U = _v[:, _w > 0.5]                               # orthonormal basis of the centred subspace
I256 = np.eye(256)
_E = I256.reshape(256, 16, 16)
PROJ = {lvl: project(_E, lvl).reshape(256, 256).T for lvl in ("site", "region", "sheet")}
BANDS = {k: v.reshape(256, 256).T for k, v in bands(_E).items()}

STATEMENTS = [
    {"id": "PB1a", "claim": "At sigma = 0.1 the QSL predictor gives the hold routes' body sign agreement within 0.05",
     "arms": ["body_site", "body_region", "body_sheet"], "endpoint": "v1000_sign", "instant": 1000,
     "regimes": [r for r in D.REGIMES if D.REGIMES[r][1] == 0.1], "conditions": "all 28",
     "denominator": "block means over the 16 development blocks; 3 arms x 28 conditions x 3 families = 252 cells",
     "rule": "a cell is a hit if |observed - predicted| <= 0.05; HOLDS if hits >= 50% of cells, else FAILS"},
    {"id": "PB1b", "claim": "At sigma = 0.3 the QSL predictor gives the hold routes' body sign agreement within 0.05",
     "arms": ["body_site", "body_region", "body_sheet"], "endpoint": "v1000_sign", "instant": 1000,
     "regimes": [r for r in D.REGIMES if D.REGIMES[r][1] == 0.3], "conditions": "all 28",
     "denominator": "252 cells as PB1a", "rule": "as PB1a"},
    {"id": "PB1c", "claim": "The local theory overpredicts native maintenance at sigma = 0.3 (escape lies outside it)",
     "arms": ["inactive"], "endpoint": "v1000_sign", "instant": 1000, "conditions": ["sham"],
     "regimes": [r for r in D.REGIMES if D.REGIMES[r][1] == 0.3], "denominator": "3 block means",
     "rule": "HOLDS if predicted - observed > 0.20 in all three families, else FAILS"},
    {"id": "PB2", "claim": "The QSL predictor orders the four hold routes correctly",
     "arms": ["inactive", "body_site", "body_region", "body_sheet"], "endpoint": "v1000_sign", "instant": 1000,
     "regimes": "all six", "conditions": "all 28",
     "denominator": "pairs of these arms, per regime and condition, whose paired block contrast is decided (95% interval excludes 0)",
     "rule": "HOLDS if the predicted difference has the observed sign in >= 80% of decided pairs, else FAILS"},
    {"id": "PB3", "claim": "Projection immunity: a body route whose sensor cannot see a band ignores reference damage in that band (up to the clipping leak)",
     "arms": {"reference-fine-0.5": ["body_region", "body_sheet"], "reference-regional-0.5": ["body_sheet"]},
     "endpoint": ["v1000_qual", "f_qual"], "contrast": "the same arm under the condition minus under sham, paired",
     "regimes": "all six", "denominator": "6 regimes x 3 arm-conditions x 2 endpoints = 36 block-mean contrasts",
     "rule": "HOLDS if every point estimate lies within +-0.01, else FAILS"},
    {"id": "PB4", "claim": "Pooled sensors are blind to reference damage in the bands their projection removes; the site sensor sees all of it",
     "arm": "inactive", "feature": "mean of the mismatch power at trace times 1, 2, 3 (tr_mismatch_<level>)",
     "unit": "cases: 128 damaged versus the same 128 cases under sham", "regimes": "all six",
     "rule": "HOLDS if in every regime AUC(region; reference-fine-0.5) <= 0.65, AUC(sheet; reference-fine-0.5) <= 0.65, "
             "AUC(sheet; reference-regional-0.5) <= 0.65 and AUC(site; every reference condition with RMS >= 1) >= 0.95"},
    {"id": "PB5", "claim": "Under the hold route the body's errors concentrate on target-boundary sites (soft modes)",
     "arm": "body_site", "condition": "sham", "instant": 1000,
     "endpoint": "fraction of body sign errors on boundary-adjacent sites, per block (errors pooled over its 8 cases)",
     "regimes": "all six", "rule": "HOLDS if |observed block mean - predicted| <= 0.15 in every regime, else FAILS"},
    {"id": "PB6", "claim": "The mean of V is conserved apart from clipping, so no arm corrects the constant band",
     "arms": "all 41 dynamic arms", "endpoint": "|mean V at t = 1000 - mean V at the window start|",
     "regimes": "all six", "rule": "HOLDS if <= 0.01 in >= 99% of branch-cases of every arm and regime, else FAILS"},
    {"id": "PB7", "claim": "The held body follows coarse reference errors more than fine ones",
     "arm": "body_site", "conditions": ["reference-fine-0.5", "reference-regional-0.5", "reference-collective-0.5"],
     "endpoint": "paired displacement ratio: sum over cases of ||V(damaged) - V(sham)||^2 at t = 1000 over sum of "
                 "||realised dR||^2, per block, block mean", "regimes": "all six",
     "rule": "HOLDS if fine < regional < collective in all six regimes, else FAILS; magnitudes are compared with the "
             "theory's static transfer and reported, not scored"},
]


def hold_route(r):
    if r == "inactive":
        return Route(body=None, reference=None, capture=None)
    return Route(body=channel(D.ch(r)), reference=None, capture=None)


def quiet(V, R, th, r, p):
    s = State(V.copy(), V.copy(), R.copy(), np.zeros_like(V))
    zero = np.zeros_like(V)
    return run(s, th, lambda t: zero, hold_route(r), D.WINDOW, p).V


def window_covariance(A, Q, T=D.WINDOW):
    """sum_{k<T} A^k Q A^k' by binary doubling (blocks are powers of one A, so they commute)."""
    S, P = np.zeros_like(Q), np.eye(len(A))
    Sb, Pb = Q, A
    while T:
        if T & 1:
            S, P = S + P @ Sb @ P.T, P @ Pb
        Sb, Pb = Sb + Pb @ Sb @ Pb.T, Pb @ Pb
        T >>= 1
    return S


def linear(Vstar, r, p):
    """Centred-subspace Jacobian, window site SDs, and the static R -> V transfer."""
    G = np.zeros((256, 256)) if r == "inactive" else p.dt * p.gain * C @ PROJ[r]
    A = (I256 - G) @ sheet_jacobian(Vstar, p)
    At = U.T @ A @ U
    radius = float(np.abs(np.linalg.eigvals(At)).max())
    Qn = U.T @ (p.sigma ** 2 * (I256 - G) @ C @ (I256 - G).T) @ U
    S = U @ window_covariance(At, Qn) @ U.T
    Gs = U @ np.linalg.solve(np.eye(255) - At, U.T @ G)
    return np.sqrt(np.clip(np.diag(S), 0.0, None)).reshape(16, 16), radius, Gs, At


def regime_predictions(name):
    lo, hi = D.IDENTITIES["calibration"]
    cases, s0, th, p, shift, _ = prepare(name, list(range(lo, hi)), "engineering")
    keep = [i for i, c in enumerate(cases) if c.parent == 0]
    cases = [cases[i] for i in keep]
    s0 = State(s0.V[keep], s0.ema[keep], s0.R[keep], s0.Q[keep])
    th = th[keep]
    T = templates(cases, D.AMPLITUDE, shift)
    sgn, edge = np.sign(T), edges(T)
    starts = []
    for loc, band, rms in D.CONDITIONS:
        bd = band_damage(D.TAG, cases, "body", band, rms) if loc in ("body", "both") else None
        rd = band_damage(D.TAG, cases, "reference", band, rms) if loc in ("reference", "both") else None
        starts.append(injure(s0, bd, rd))
    out = {"qsl": {}, "boundary_error_fraction": {}, "spectral_radius": {}, "transfer": {}, "coverage": {}}
    for r in ROUTES_T:
        vsham = quiet(starts[0].V, starts[0].R, th, r, p)
        lin = [linear(vsham[i], r, p) for i in range(len(cases))]
        sd = np.stack([x[0] for x in lin])
        stable = [x for x in lin if x[1] < 1]
        out["spectral_radius"][ARM_OF[r]] = {"min": float(min(x[1] for x in lin)), "max": float(max(x[1] for x in lin)),
                                             "cases_above_1": len(lin) - len(stable), "cases": len(lin)}
        cells = {}
        for ci in D.FULL:
            vstar = vsham if ci == 0 else quiet(starts[ci].V, starts[ci].R, th, r, p)
            ps = norm.cdf(sgn * vstar / sd)
            pq = norm.cdf((sgn * vstar - 0.2) / sd)
            cells[D.condition_name(ci)] = [float(ps.mean()), float(pq.mean())]
            if ci == 0:
                err = 1 - ps
                out["boundary_error_fraction"][ARM_OF[r]] = float(np.mean(
                    (err * edge).sum((-2, -1)) / err.sum((-2, -1))))
        out["qsl"][ARM_OF[r]] = cells
        if r != "inactive":    # static transfer exists only around a stable state
            out["transfer"][ARM_OF[r]] = {b: float(np.mean([np.sum((x[2] @ B) ** 2) / np.sum(B ** 2) for x in stable]))
                                          for b, B in BANDS.items() if b != "constant"}
        if r == "site":
            M = np.stack([U.T @ sheet_jacobian(vsham[i], p) @ U for i in range(len(cases))])
            cover, rates, bweight = {"region": [], "sheet": []}, [], []
            for i, At in enumerate(M):
                w, v = np.linalg.eig(At)
                order = np.argsort(-np.abs(w))[:10]
                modes = np.real(U @ v[:, order])
                modes /= np.linalg.norm(modes, axis=0)
                rates.append(float(np.mean(1 - np.abs(w[order]))))
                for lvl in cover:
                    cover[lvl].append(float(np.mean(np.sum((PROJ[lvl] @ modes) ** 2, 0))))
                bweight.append(float(np.mean(np.sum(modes ** 2 * edge[i].ravel()[:, None], 0))))
            out["coverage"] = {"slow_modes": 10, "relaxation_rate_mean": float(np.mean(rates)),
                               "boundary_weight_mean": float(np.mean(bweight)),
                               "visible_fraction": {"site": 1.0, **{k: float(np.mean(v)) for k, v in cover.items()}},
                               "boundary_sites_fraction": float(edge.mean())}
    return name, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "frozen" / "predictions.json")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    t0 = time.time()
    with ProcessPoolExecutor(min(len(cpus), len(D.REGIMES))) as pool:
        regimes = dict(pool.map(regime_predictions, D.REGIMES))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
        "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
        "inputs": {"blocks": list(D.IDENTITIES["calibration"]), "parents": [0], "cases_per_regime": 64,
                   "note": "engineering identities; acquired states and damage fields only, no stochastic outcome"},
        "method": "quiet-settle + Lyapunov (QSL), no free parameters", "statements": STATEMENTS,
        "regimes": regimes}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
