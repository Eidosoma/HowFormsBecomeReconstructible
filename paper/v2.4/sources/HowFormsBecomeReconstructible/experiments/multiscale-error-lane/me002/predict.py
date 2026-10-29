"""Track B2 and the registered statements of ME002, computed before any development outcome.

python -m me002.predict --cpus LIST   (writes me002/frozen/predictions.json)

The theory is ME001's parameter-free quiet-settle + window-covariance predictor (QSL,
me001.predict.linear), now applied to new couplings (panel B) and to new noise levels and
pattern families (panel C), on the calibration blocks' acquired states (engineering identities,
parent 0, 64 cases per regime): per hold route and condition, the noise-free 1000-update settle
from the injured start, the covariance the linearised noisy update accumulates over the window
around the sham settle, and Gaussian per-site probabilities of a sign match and of qualified
agreement. It also gives the static transfer of a reference error into the held body by band.
Statements PB* test the theory; PA*, PC1, PE1 and PF* are mechanism and design predictions with
rules fixed here; their reasoning, and the engineering inputs behind PA1 and PF1, are disclosed
in REGISTRATION_ME002.md.
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

from me001.predict import BANDS as BAND_MATS, linear  # noqa: E402
from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from mse.engine import Route, State, run  # noqa: E402

ROUTES_T = ("inactive", "site", "region", "sheet")
ARM_OF = {"inactive": "inactive", "site": "hold_site", "region": "hold_region", "sheet": "hold_sheet"}
WINDOW = 1000
SIGMA_C = (0.05, 0.1, 0.2, 0.3, 0.4)
NEW_G = (0.25, 2.5)


def hold_route(r):
    if r == "inactive":
        return Route(body=None, reference=None, capture=None)
    return Route(body=sim.channel(D.ch(r)), reference=None, capture=None)


def quiet(V, R, th, r, p):
    s = State(V.copy(), V.copy(), R.copy(), np.zeros_like(V))
    zero = np.zeros_like(V)
    return run(s, th, lambda t: zero, hold_route(r), WINDOW, p).V


def regime_predictions(job):
    panel, name = job
    conds = D.PANELS[panel]["conditions"]
    lo, hi = D.IDENTITIES["calibration"]
    cases, s0, th, p, T, Tf = sim.prepare(name, list(range(lo, hi)), "engineering")
    keep = [i for i, c in enumerate(cases) if c.parent == 0]
    cases, th, T, Tf = [cases[i] for i in keep], th[keep], T[keep], Tf[keep]
    s0 = State(s0.V[keep], s0.ema[keep], s0.R[keep], s0.Q[keep])
    k, nc = len(cases), len(conds)
    prog = sim.condition_program(conds, cases, np.ones(k, int), Tf, WINDOW)
    V1, R1 = prog.apply(1, np.tile(s0.V, (nc, 1, 1)), np.tile(s0.R, (nc, 1, 1)))
    sgn = np.sign(T)
    out = {"qsl": {}, "spectral_radius": {}, "transfer": {}}
    for r in ROUTES_T:
        vsham = quiet(s0.V, s0.R, th, r, p)
        lin = [linear(vsham[i], r, p) for i in range(k)]
        sd = np.stack([x[0] for x in lin])
        stable = [x for x in lin if x[1] < 1]
        out["spectral_radius"][ARM_OF[r]] = {"min": float(min(x[1] for x in lin)), "max": float(max(x[1] for x in lin)),
                                             "cases_above_1": len(lin) - len(stable), "cases": len(lin)}
        cells = {}
        for ci, cond in enumerate(conds):
            sl = slice(ci * k, (ci + 1) * k)
            vstar = vsham if ci == 0 else quiet(V1[sl], R1[sl], th, r, p)
            ps, pq = norm.cdf(sgn * vstar / sd), norm.cdf((sgn * vstar - 0.2) / sd)
            cells[cond.name] = [float(ps.mean()), float(pq.mean())]
        out["qsl"][ARM_OF[r]] = cells
        if r != "inactive" and stable:
            out["transfer"][ARM_OF[r]] = {b: float(np.mean([np.sum((x[2] @ B) ** 2) / np.sum(B ** 2) for x in stable]))
                                          for b, B in BAND_MATS.items() if b != "constant"}
    return f"{panel}/{name}", out


def statements(theory):
    """The registered statements; PB10t's predicted directions come from the theory."""
    harm = lambda key, band: theory[key]["qsl"]["hold_site"]["sham"][0] - theory[key]["qsl"]["hold_site"][f"reference-{band}-2"][0]
    directions = {}
    for f in ("F0", "F4"):
        for s in (0.3, 0.1):
            for band in ("fine", "regional"):
                hs = [harm(f"B/{D.regime(f, s, g)}", band) for g in (0.25, 1.0, 2.5)]
                directions[f"{f}_s{s:g}_{band}"] = {"predicted_harm_g0.25_g1_g2.5": hs,
                                                    "predicted_sign_g0.25_minus_g2.5": int(np.sign(hs[0] - hs[2]))}
    pa_regimes = list(D.PANELS["A"]["regimes"])
    a03 = [r for r in pa_regimes if D.parse(r)[1] == 0.3]
    return [
        {"id": "PB8", "kind": "theory", "panel": "B",
         "claim": "At sigma = 0.1 the QSL predictor gives the hold routes' body sign agreement within 0.05 at the new couplings g = 0.25 and 2.5",
         "arms": ["hold_site", "hold_region", "hold_sheet"], "endpoint": "v_sign", "instant": 1000,
         "regimes": [D.regime(f, 0.1, g) for f in ("F0", "F4") for g in NEW_G], "conditions": "all 10",
         "denominator": "block means over the 16 development blocks; 3 arms x 10 conditions x 4 regimes = 120 cells",
         "rule": "a cell is a hit if |observed - predicted| <= 0.05; HOLDS if hits >= 50% of cells, else FAILS"},
        {"id": "PB9", "kind": "theory", "panel": "C",
         "claim": "The QSL predictor degrades with noise: its hit fraction falls with sigma and crosses 50% between sigma = 0.1 and 0.3",
         "arms": ["hold_site", "hold_region", "hold_sheet"], "endpoint": "v_sign", "instant": 1000,
         "regimes": "all 25 of panel C", "conditions": "all 8",
         "denominator": "per sigma: 3 arms x 8 conditions x 5 families = 120 cells (block means)",
         "rule": "h(sigma) = fraction of cells with |observed - predicted| <= 0.05; HOLDS if h(0.1) >= 0.5, h(0.3) < 0.5 "
                 "and h(next sigma) <= h(sigma) + 0.05 for each consecutive pair 0.05 -> 0.1 -> 0.2 -> 0.3 -> 0.4, else FAILS"},
        {"id": "PB10", "kind": "physics", "panel": "B",
         "claim": "Stronger coupling filters coarser reference errors: the harm of RMS-2 reference damage to the held body falls as g rises",
         "arm": "hold_site", "endpoint": "v_sign", "instant": 1000,
         "series": "harm(g) = sham minus reference-{fine, regional}-2, block means; 2 families (F0, F4) x 2 sigmas x 2 bands = 8 series",
         "rule": "a series is monotone if harm(1) <= harm(0.25) + 0.01 and harm(2.5) <= harm(1) + 0.01; HOLDS if >= 6 of 8 series are monotone, else FAILS"},
        {"id": "PB10t", "kind": "theory", "panel": "B",
         "claim": "The QSL predictor gives the direction in which the harm of fine and regional reference damage changes from g = 0.25 to g = 2.5",
         "arm": "hold_site", "endpoint": "v_sign", "predicted": directions,
         "rule": "a series agrees if sign(observed harm(0.25) - harm(2.5)) equals the predicted sign (observed differences within +-0.01 count as 0 "
                 "and agree only with a predicted 0); HOLDS if >= 6 of 8 series agree, else FAILS"},
        {"id": "PB12", "kind": "theory", "panel": "B",
         "claim": "A setpoint matters more in a more strongly coupled body: the held reference's gain over no correction rises with coupling",
         "contrast": "hold_site - inactive", "endpoint": "v_sign", "condition": "sham", "instant": 1000,
         "regimes": [D.regime(f, 0.1, g) for f in ("F0", "F4") for g in (0.25, 1.0, 2.5)],
         "predicted": {f: [theory[f"B/{D.regime(f, 0.1, g)}"]["qsl"]["hold_site"]["sham"][0]
                           - theory[f"B/{D.regime(f, 0.1, g)}"]["qsl"]["inactive"]["sham"][0] for g in (0.25, 1.0, 2.5)]
                       for f in ("F0", "F4")},
         "rule": "HOLDS if the observed block-mean contrast increases strictly from g = 0.25 to 1 to 2.5 in both families at sigma = 0.1, "
                 "else FAILS; sigma = 0.3 is reported"},
        {"id": "PB11", "kind": "projection", "panel": "D",
         "claim": "A protected backup only needs the scales the body cannot regenerate: a region-resolution backup (16 values) equals the full "
                  "backup under regional and collective reference damage, and a sheet-resolution backup (4 values) equals it under collective damage",
         "contrasts": {"clamp_region - clamp_site": ["reference-regional-1", "reference-regional-2", "reference-collective-1", "reference-collective-2"],
                       "clamp_sheet - clamp_site": ["reference-collective-1", "reference-collective-2"]},
         "endpoints": ["v_qual", "fQ_qual"], "regimes": "all 5 of panel D",
         "rule": "HOLDS if every one of the 60 paired block contrasts reads NO MEANINGFUL DIFFERENCE (95% interval within +-0.02), else FAILS"},
        {"id": "PD1", "kind": "coding", "panel": "D",
         "claim": "Redundancy does what provenance cannot: two unprotected records that vote with the body repair an injury to the body "
                  "and one record together, which no one-record arm fixes",
         "contrast": "dual_vote - hold_site", "endpoint": "fQ_qual", "regime": D.PRIMARY,
         "conditions": ["both-collective-2", "both-regional-2"],
         "reasoning": "the vote compares each record with the injured body region by region; with independent coherent fields the "
                      "injured record still looks closer in about 35% of regions (P(same sign and |d1| < 2|b|) for iid normals), "
                      "so the expected repair is partial: better than hold, short of protected storage",
         "rule": "HOLDS if the contrast is a BENEFIT under both conditions, else FAILS; dual_vote - clamp_site is reported"},
        {"id": "PA1", "kind": "mechanism", "panel": "A",
         "claim": "Under random onset ME001's unchanged arbiter rarely acts on a coarse reference injury, because spontaneous surprise keeps its "
                  "latch closed (engineering probe P5); the trajectory-calibrated latch (v2) acts at once",
         "arms": ["arbiter_me001", "arbiter"], "telemetry": "a_win20: a burst starts within 20 updates of the injury",
         "conditions": ["reference-regional-2", "reference-collective-2"], "regimes": pa_regimes,
         "rule": "HOLDS if, in every regime and both conditions, arbiter_me001's a_win20 rate <= 0.5 and arbiter's >= 0.9 (fraction of 128 cases), else FAILS"},
        {"id": "PA2", "kind": "mechanism", "panel": "A",
         "claim": "The latch is a duration filter: the v2 arbiter's record adopts a pattern imposed to the end of the window and keeps its own after a "
                  "50-update imposition; without a latch (change-point) even the short imposition is adopted",
         "endpoints": {"impose-inf": "rg_sign (R vs the imposed pattern)", "impose-50": "r_sign (R vs the own target), rg_sign for changepoint"},
         "regimes": a03,
         "rule": "HOLDS if, in every sigma = 0.3 regime (block means), rg_sign >= 0.8 under impose-inf for arbiter, arbiter_W300 and arbiter_W100; "
                 "r_sign >= 0.8 under impose-50 for arbiter and arbiter_W300; and changepoint's rg_sign >= 0.8 under impose-50; else FAILS"},
        {"id": "PA3", "kind": "mechanism", "panel": "A",
         "claim": "A body injury during a burst is copied into the record; aborting the burst on surprise protects the record",
         "contrast": "arbiter_abort - arbiter", "endpoint": "fR_qual", "regime": D.PRIMARY,
         "rule": "HOLDS if the contrast is a BENEFIT under ref-then-body-10 and NO MEANINGFUL DIFFERENCE under ref-then-body-300, else FAILS"},
        {"id": "PA4", "kind": "mechanism", "panel": "A",
         "claim": "A body injury closes the latch, so a reference injury 10 updates later is not acted on while the latch is closed",
         "arms": ["arbiter", "arbiter_W300"], "telemetry": "a_after2: updates from the second injury to the first burst (-1 = none)",
         "condition": "body-then-ref-10", "regimes": pa_regimes,
         "rule": "HOLDS if, in every regime, for both arms, >= 80% of cases have no burst within W - 50 updates of the reference injury "
                 "(a_after2 = -1 or a_after2 >= W - 50), else FAILS"},
        {"id": "PC1", "kind": "design", "panel": "C",
         "claim": "Thresholds pooled over the calibration families (F0, F2, F4) transfer to untouched families without false alarms",
         "arm": "arbiter_pooled", "telemetry": "a_bursts > 0 under sham", "regimes": [D.regime(f, 0.3) for f in ("S4", "BL", "IS")],
         "rule": "HOLDS if the sham false-alarm rate (fraction of 128 cases with any burst) is <= 0.05 in each of the three regimes, else FAILS",
         "disclosed_expectation": "calibration shams of S4 (four walls) reach region-pooled mismatch maxima above the pooled threshold, so a FAIL is expected for S4"},
        {"id": "PE1", "kind": "design", "panel": "E",
         "claim": "At equal correction dose the sheet-sensor majority vote still maintains the aligned target better than linear site correction",
         "contrast": "sign_sheet_site_eq - hold_site", "endpoint": "v_qual", "condition": "sham", "regime": D.PRIMARY,
         "rule": "HOLDS if the contrast is a BENEFIT, else FAILS"},
        {"id": "PF1", "kind": "replication", "panel": "F",
         "claim": "Heredity through body capture decays across generations even without injuries (seen on debug block 900993: 0.75 -> 0.56)",
         "arm": "hold_Q", "environment": "none", "endpoint": "v_qual", "regime": D.PRIMARY,
         "rule": "HOLDS if the generation-8 block mean is below the generation-1 block mean by more than 0.05 with the paired 95% interval "
                 "of (generation 8 - generation 1) below 0, else FAILS"},
        {"id": "PF2", "kind": "mechanism", "panel": "F",
         "claim": "Under a reference injury every generation, in-life provenance-gated repair slows the accumulation that pure copying suffers",
         "arms": ["arbiter_R", "hold_R"], "environment": "reference", "endpoint": "v_qual", "regime": D.PRIMARY,
         "rule": "d = (arbiter_R gen 8 - gen 1) - (hold_R gen 8 - gen 1), paired by block; HOLDS if the point estimate >= 0.05 and its 95% interval excludes 0, else FAILS"},
        {"id": "PF3", "kind": "projection", "panel": "F",
         "claim": "A protected coarse germline (16 values) keeps aligned coarse targets as well as the full germline, but not multi-scale ones",
         "contrast": "germline_region - germline_site", "environment": "none", "endpoint": "v_qual (generation 8)",
         "regimes": {"equal": [D.regime("F0", 0.3), D.regime("F4", 0.3)], "worse": [D.regime("BL", 0.3)]},
         "rule": "HOLDS if the contrast reads NO MEANINGFUL DIFFERENCE for F0 and F4 at sigma = 0.3 and HARM for BL at sigma = 0.3, else FAILS"},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "frozen" / "predictions.json")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    t0 = time.time()
    jobs = [("B", r) for r in D.PANELS["B"]["regimes"]] + [("C", r) for r in D.PANELS["C"]["regimes"]]
    with ProcessPoolExecutor(min(len(cpus), len(jobs))) as pool:
        theory = dict(pool.map(regime_predictions, jobs))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
        "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
        "inputs": {"blocks": list(D.IDENTITIES["calibration"]), "parents": [0], "cases_per_regime": 64,
                   "note": "engineering identities; acquired states and damage fields only, no stochastic outcome"},
        "method": "quiet-settle + window covariance (QSL, me001.predict.linear), no free parameters",
        "statements": statements(theory), "theory": theory}, indent=1) + "\n")
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
