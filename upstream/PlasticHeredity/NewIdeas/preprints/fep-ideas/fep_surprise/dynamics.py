from __future__ import annotations

import numpy as np

from . import compat as _compat  # noqa: F401
from plastic_heredity.config import GardConfig


EPS = 1e-12


def expected_flux(composition: np.ndarray, beta: np.ndarray, config: GardConfig) -> np.ndarray:
    n = np.asarray(composition, dtype=np.float64)
    mass = max(float(n.sum()), 1.0)
    boost = 1.0 + (beta @ n) / mass
    join = config.k_join * (1.0 / config.n_types) * mass * boost
    leave = config.k_leave * n * boost
    return join - leave


def rq_alignment(composition: np.ndarray, beta: np.ndarray, config: GardConfig) -> float:
    n = np.asarray(composition, dtype=np.float64)
    flux = expected_flux(n, beta, config)
    denominator = float(np.linalg.norm(n) * np.linalg.norm(flux))
    return float(np.dot(n, flux) / denominator) if denominator > EPS else 0.0


def meanfield_forms(
    beta: np.ndarray,
    config: GardConfig,
    *,
    starts: int,
    iterations: int,
    seed: int,
    merge_cosine: float = 0.95,
) -> np.ndarray:
    """Derive expected-flow endpoints independently of stochastic futures."""

    rng = np.random.default_rng(seed)
    endpoints = []
    mass = 0.5 * (config.n_min + config.n_max)
    for _ in range(starts):
        x = rng.dirichlet(np.ones(config.n_types))
        for _ in range(iterations):
            n = mass * x
            flux = expected_flux(n, beta, config)
            tangent = flux - x * float(flux.sum())
            step = 2e-4 / max(float(np.max(np.abs(tangent))), EPS)
            updated = np.maximum(x + step * tangent, 0.0)
            total = float(updated.sum())
            if total <= EPS:
                break
            updated /= total
            if np.linalg.norm(updated - x) < 1e-9:
                x = updated
                break
            x = updated
        norm = float(np.linalg.norm(x))
        if norm > EPS:
            endpoints.append(x / norm)
    forms: list[np.ndarray] = []
    for endpoint in endpoints:
        if not any(float(np.dot(endpoint, form)) >= merge_cosine for form in forms):
            forms.append(endpoint)
    if not forms:
        forms = [np.ones(config.n_types) / np.sqrt(config.n_types)]
    return np.stack(forms)


def nearest_form_distance(compositions: np.ndarray, forms: np.ndarray) -> np.ndarray:
    values = np.asarray(compositions, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    return 1.0 - np.max(values @ forms.T, axis=1)


def permute_system(beta: np.ndarray, compositions: np.ndarray, order: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact molecule-label relabeling used by the invariance gate."""

    order = np.asarray(order, dtype=np.int64)
    if np.unique(order).size != len(order):
        raise ValueError("order must be a permutation")
    return beta[np.ix_(order, order)], np.asarray(compositions)[..., order]

