"""Static theory of BE001's cable detector (python probes/theory_be001_static_detector.py), THEORY.md §8.7.
A calculation, not a probe: written after BE001's development run (28 October 2026), from the frozen design's constants.

No dynamics. Anchors at a random quarter of the lane's 32 x 32 torus inject I = kappa * (+1 agree / -1 disagree), and the
steady-state potentials solve (g_leak + lambda^2 L) v = I. For every noiseless, ungated arm of BE001:
- the continuum radius of the smallest disagreeing disc whose centre crosses -theta (x K1(x) = (1 - theta) / 2);
- on the lattice, the anchors in the weighted average (n_eff), and the potential's SD and Gaussian false-alarm share under
  scattered corruption of a quarter of the anchors;
- by Monte Carlo (400 draws, exact counts as the engine draws them), the share of a re-specified patch of side 4, 8 and 12
  whose potential falls below -theta, and the share of all cells below -theta under scattered corruption;
- BE001's development levels at t = 4,000 for comparison (results/be001/summary_*.json, ranges over units and bodies).
Writes probes/results/theory_be001_static_detector.json.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import optimize, special, stats  # noqa: E402

from be001 import design as D  # noqa: E402

OUT = LANE / "probes" / "results" / "theory_be001_static_detector.json"
N, Q, DRAWS, SEED = D.SIDE, 0.25, 400, 20261028
ARMS = {a: p for a, p in D.BIO.items() if not p["gate"] and not p["noise"]}
K = 2 * np.pi * np.fft.fftfreq(N)
LAP = (2 - 2 * np.cos(K))[:, None] + (2 - 2 * np.cos(K))[None, :]


def radius(theta):
    return optimize.brentq(lambda x: x * special.k1(x) - (1 - theta) / 2, 0.05, 8.0)


def lattice(lam, theta):
    G = np.real(np.fft.ifft2(1.0 / (D.G_LEAK + lam ** 2 * LAP)))
    s1, s2, rho = G.sum(), (G ** 2).sum(), 1.0 / D.DENSITY
    sd = math.sqrt(D.KAPPA ** 2 * (rho - rho ** 2 * (1 - 2 * Q) ** 2) * s2)
    mean = D.KAPPA * rho * (1 - 2 * Q) * s1
    return {"n_eff": rho * s1 ** 2 / s2, "mean_v": mean, "sd_v": sd, "false_alarms_gaussian": stats.norm.cdf((-theta - mean) / sd)}


def monte_carlo(lam, theta, rng):
    Gh = 1.0 / (D.G_LEAK + lam ** 2 * LAP)
    n = N * N
    cover, fa = {z: [] for z in D.SIZES}, []
    for _ in range(DRAWS):
        anch = np.zeros(n, bool)
        anch[rng.permutation(n)[: n // D.DENSITY]] = True
        anch = anch.reshape(N, N)
        for z in D.SIZES:
            s = np.ones((N, N))
            s[:z, :z] = -1
            v = np.real(np.fft.ifft2(np.fft.fft2(D.KAPPA * anch * s) * Gh))
            cover[z].append((v[:z, :z] < -theta).mean())
        idx = np.flatnonzero(anch)
        s = np.ones(n)
        s[rng.permutation(idx)[: len(idx) // 4]] = -1
        v = np.real(np.fft.ifft2(np.fft.fft2(D.KAPPA * anch * s.reshape(N, N)) * Gh))
        fa.append((v < -theta).mean())
    return {"cover": {str(z): float(np.mean(c)) for z, c in cover.items()}, "false_alarms": float(np.mean(fa))}


def development():
    levels = {}
    for body in ("dw", "li4"):
        s = json.loads((LANE / "results" / "be001" / f"summary_{body}.json").read_text())
        for unit, x in s["levels"].items():
            levels[f"{unit}/{body}"] = x[body]
    out = {}
    for a in ARMS:
        rows = {f"change{z}": [x[f"change{z}"][a]["r_in"][-1][0] for x in levels.values()] for z in D.SIZES}
        rows["loss_cue8"] = [x["cue8"]["cue"]["r_all"][-1][0] - x["cue8"][a]["r_all"][-1][0] for x in levels.values()]
        out[a] = {k: [round(min(v), 4), round(max(v), 4)] for k, v in rows.items()}
    return out


def main():
    rng = np.random.default_rng(SEED)
    res = {"note": "calculation after BE001's development run; static, no dynamics", "draws": DRAWS, "seed": SEED,
           "radius_over_lambda": {str(t): radius(t) for t in sorted({p["theta"] for p in ARMS.values()})}, "arms": {}}
    dev = development()
    for a, p in ARMS.items():
        res["arms"][a] = {"lam": p["lam"], "theta": p["theta"], **lattice(p["lam"], p["theta"]),
                          **monte_carlo(p["lam"], p["theta"], rng), "development": dev[a]}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print("R/lambda:", {k: round(v, 3) for k, v in res["radius_over_lambda"].items()})
    for a, r in res["arms"].items():
        c, d = r["cover"], r["development"]
        print(f"{a:17s} n_eff {r['n_eff']:5.1f} sd {r['sd_v']:.3f} gauss {r['false_alarms_gaussian']:.4f} | static "
              + " ".join(f"{c[str(z)]:.2f}" for z in D.SIZES) + f" fa {r['false_alarms']:.4f} | dynamic "
              + " ".join(f"{d[f'change{z}'][0]:.3f}-{d[f'change{z}'][1]:.3f}" for z in D.SIZES)
              + f" loss {d['loss_cue8'][0]:.4f}-{d['loss_cue8'][1]:.4f}")


if __name__ == "__main__":
    main()
