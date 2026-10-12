"""Restricted observable-response law and its conventional HMM implementation.

The empirical hypothesis is two independent relaxation modes with fixed rates.
The implementation is an ordinary structured hidden Markov model. Parameters:
(stationary_readability, readiness_mode, identity_mode, initial_readability,
 initial_identity_bias). This version restricts both modes to [0,1].
"""
from __future__ import annotations

import itertools
import numpy as np
from scipy.optimize import minimize

from joint_kernel import two_factor_kernel

PATTERNS = np.array(list(itertools.product(range(3), repeat=3)), dtype=int)
# Observable categories A, B, neither. Both unreadable identities emit neither.
EMISSION = np.array([[0., 0., 1.], [1., 0., 0.], [0., 0., 1.], [0., 1., 0.]])
STARTS = [(pi, mu, lam) for pi in (.4, .8) for mu in (.2, .8) for lam in (.8, .99)]


def validate(params):
    theta = np.asarray(params, dtype=float)
    if theta.shape != (5,) or not np.isfinite(theta).all():
        raise ValueError("Five finite parameters required")
    if ((theta[:4] < 0) | (theta[:4] > 1)).any() or not -1 <= theta[4] <= 1:
        raise ValueError("Invalid two-mode parameters")
    return theta


def distributions(params, horizons):
    pi, mu, lam, initial_r, initial_bias = validate(params)
    h = np.asarray(horizons)
    if not np.issubdtype(h.dtype, np.integer) or (h < 0).any():
        raise ValueError("Nonnegative integer horizons required")
    r = pi + (initial_r-pi)*mu**h
    bias = initial_bias*lam**h
    return np.stack((r*(1+bias)/2, r*(1-bias)/2, 1-r), axis=-1)


def hidden_model(params):
    pi, mu, lam, initial_r, initial_bias = validate(params)
    p = two_factor_kernel((1-lam)/2, (1-pi)*(1-mu), pi*(1-mu))
    initial = np.kron([(1+initial_bias)/2, (1-initial_bias)/2], [1-initial_r, initial_r])
    return initial, p


def pattern_probabilities(params):
    initial, p = hidden_model(params)
    forward = initial[None, :] * EMISSION[:, PATTERNS[:, 0]].T
    for t in (1, 2):
        forward = (forward @ p) * EMISSION[:, PATTERNS[:, t]].T
    return forward.sum(axis=1)


def fit_patterns(pattern_counts):
    counts = np.asarray(pattern_counts, dtype=float)
    if counts.shape != (27,) or (counts < 0).any() or not np.isfinite(counts).all() or counts.sum() <= 0:
        raise ValueError("27 nonnegative pattern counts required")
    if not np.equal(counts, np.floor(counts)).all():
        raise ValueError("Pattern counts must be integers")
    first = np.bincount(PATTERNS[:, 0], weights=counts, minlength=3)/counts.sum()
    r0 = first[:2].sum()
    bias0 = (first[0]-first[1])/r0 if r0 > 0 else 0.
    bounds = [(0, 1)]*4 + [(-1, 1)]
    support = counts > 0
    def loss(params):
        prob = pattern_probabilities(params)
        # A numerical log floor is used only by optimization, never in forecasts.
        return float(-np.sum(counts[support]*np.log(np.maximum(prob[support], 1e-15)))/counts.sum())
    attempts = []
    for pi, mu, lam in STARTS:
        x0 = [pi, mu, lam, float(np.clip(r0, .01, .99)), float(np.clip(bias0, -.99, .99))]
        fit = minimize(loss, x0, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-7})
        attempts.append(dict(success=bool(fit.success), loss=float(fit.fun), params=fit.x.tolist(), message=str(fit.message)))
    eligible = [x for x in attempts if x["success"] and np.isfinite(x["loss"])]
    if not eligible:
        raise RuntimeError("All fixed optimizer starts failed")
    best = min(eligible, key=lambda x: x["loss"])
    return dict(params=best["params"], average_negative_log_likelihood=best["loss"], attempts=attempts,
                uncertainty="Point estimate only. Convergence does not establish parameter identifiability or calibrated long-horizon uncertainty.")


def exact_moment_identification(response_probabilities, tolerance=1e-9):
    """Identify the nondegenerate exact law from observables at depths 0,1,2.

    The tolerance is an arithmetic guard, not a statistical equivalence margin.
    Finite sampled proportions require likelihood fitting and uncertainty, not
    this exact inversion or clipping invalid rates back into the model.
    """
    o = np.asarray(response_probabilities, dtype=float)
    if o.shape != (3, 3) or not np.isfinite(o).all() or (o < 0).any() or not np.allclose(o.sum(axis=1), 1):
        raise ValueError("Three normalized response distributions required")
    r = o[:, 0]+o[:, 1]
    if (r <= tolerance).any():
        raise ValueError("Conditional identity bias is not identified at zero readability")
    chi = (o[:, 0]-o[:, 1])/r
    if abs(r[1]-r[0]) <= tolerance or abs(chi[0]) <= tolerance:
        raise ValueError("Stationary readability or zero identity bias leaves rates unidentifiable")
    mu = (r[2]-r[1])/(r[1]-r[0])
    if abs(1-mu) <= tolerance:
        raise ValueError("Stationary level is unidentifiable when readiness mode is one")
    pi = (r[1]-mu*r[0])/(1-mu)
    lam = chi[1]/chi[0]
    if abs(chi[2]-chi[0]*lam**2) > tolerance:
        raise ValueError("Depth-two conditional bias contradicts the two-mode law")
    result = [pi, mu, lam, r[0], chi[0]]
    validate(result)
    return result


def output_markov(pattern_counts):
    counts = np.asarray(pattern_counts, dtype=float)
    transition = np.zeros((3, 3))
    for pattern, n in zip(PATTERNS, counts, strict=True):
        for t in (0, 1):
            transition[pattern[t], pattern[t+1]] += n
    source = transition.sum(axis=1)
    if (source == 0).any():
        raise ValueError("Output baseline has an unobserved source category")
    initial = np.bincount(PATTERNS[:, 0], weights=counts, minlength=3)/counts.sum()
    return initial, transition/source[:, None]
