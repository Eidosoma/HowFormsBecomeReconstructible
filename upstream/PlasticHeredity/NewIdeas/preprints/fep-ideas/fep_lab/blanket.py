from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.linalg import expm, solve_continuous_lyapunov

BlanketIntervention = Literal[
    "intact", "sensory_lesion", "active_lesion", "blanket_break"
]


@dataclass(frozen=True)
class LinearBlanketModel:
    generator: np.ndarray
    diffusion_covariance: np.ndarray
    stationary_covariance: np.ndarray
    precision: np.ndarray
    partition: tuple[str, ...] = ("external", "sensory", "internal", "active")
    intervention: BlanketIntervention = "intact"

    @property
    def population_partial_correlation(self) -> float:
        return partial_correlation_from_precision(self.precision, 0, 2)

    @property
    def population_conditional_mutual_information(self) -> float:
        return gaussian_cmi(self.population_partial_correlation)


def build_blanket_model(
    intervention: BlanketIntervention = "intact",
) -> LinearBlanketModel:
    if intervention not in {
        "intact",
        "sensory_lesion",
        "active_lesion",
        "blanket_break",
    }:
        raise ValueError(f"unknown blanket intervention {intervention!r}")
    generator = np.asarray(
        [
            [-1.0, 0.0, 0.0, 0.5],
            [0.5, -1.0, 0.0, 0.0],
            [0.0, 0.5, -1.0, 0.0],
            [0.0, 0.0, 0.5, -1.0],
        ],
        dtype=np.float64,
    )
    if intervention == "sensory_lesion":
        generator[1, 0] = 0.0
    elif intervention == "active_lesion":
        generator[0, 3] = 0.0
    elif intervention == "blanket_break":
        generator[2, 0] = 0.30
    eigenvalues = np.linalg.eigvals(generator)
    if np.any(np.real(eigenvalues) >= 0.0):
        raise ValueError("blanket generator is not stable")
    diffusion = 2.0 * np.eye(4, dtype=np.float64)
    covariance = solve_continuous_lyapunov(generator, -diffusion)
    covariance = 0.5 * (covariance + covariance.T)
    precision = np.linalg.inv(covariance)
    return LinearBlanketModel(
        generator=generator,
        diffusion_covariance=diffusion,
        stationary_covariance=covariance,
        precision=precision,
        intervention=intervention,
    )


def exact_discretization(
    model: LinearBlanketModel, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    if not 0.0 < dt <= 1.0:
        raise ValueError("dt must lie in (0, 1]")
    transition = expm(model.generator * dt)
    innovation = (
        model.stationary_covariance
        - transition @ model.stationary_covariance @ transition.T
    )
    innovation = 0.5 * (innovation + innovation.T)
    eigenvalues, eigenvectors = np.linalg.eigh(innovation)
    if float(eigenvalues.min()) < -1e-12:
        raise ValueError("discrete innovation covariance is not positive semidefinite")
    innovation = (eigenvectors * np.maximum(eigenvalues, 0.0)) @ eigenvectors.T
    return transition, innovation


def simulate_blanket(
    model: LinearBlanketModel,
    trajectories: int,
    steps: int,
    dt: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if trajectories <= 0 or steps <= 0:
        raise ValueError("trajectory counts and lengths must be positive")
    transition, innovation = exact_discretization(model, dt)
    current = rng.multivariate_normal(
        np.zeros(4, dtype=np.float64),
        model.stationary_covariance,
        size=trajectories,
    )
    output = np.empty((trajectories, steps, 4), dtype=np.float64)
    for step in range(steps):
        output[:, step, :] = current
        noise = rng.multivariate_normal(
            np.zeros(4, dtype=np.float64), innovation, size=trajectories
        )
        current = current @ transition.T + noise
    return output


def partial_correlation_from_precision(
    precision: np.ndarray, left: int, right: int
) -> float:
    denominator = float(np.sqrt(precision[left, left] * precision[right, right]))
    return float(-precision[left, right] / denominator)


def gaussian_cmi(partial_correlation: float) -> float:
    squared = min(float(partial_correlation) ** 2, 1.0 - 1e-15)
    return float(-0.5 * np.log1p(-squared))


def estimate_blanket_statistics(samples: np.ndarray) -> dict[str, object]:
    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 3 or values.shape[2] != 4:
        raise ValueError("blanket samples must have shape (trajectory, time, 4)")
    flat = values.reshape(-1, 4)
    covariance = np.cov(flat, rowvar=False, ddof=1)
    precision = np.linalg.inv(covariance)
    partial = partial_correlation_from_precision(precision, 0, 2)
    return {
        "observations": int(len(flat)),
        "covariance": covariance,
        "precision": precision,
        "partial_correlation_external_internal": partial,
        "conditional_mutual_information": gaussian_cmi(partial),
    }


def bootstrap_partial_correlation(
    samples: np.ndarray, repetitions: int, rng: np.random.Generator
) -> np.ndarray:
    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 3 or values.shape[2] != 4:
        raise ValueError("blanket samples must have shape (trajectory, time, 4)")
    if repetitions <= 0:
        raise ValueError("bootstrap repetitions must be positive")
    trajectories = values.shape[0]
    steps = values.shape[1]
    trajectory_sums = values.sum(axis=1)
    trajectory_cross_products = np.einsum("nti,ntj->nij", values, values)
    output = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        selected = rng.integers(0, trajectories, size=trajectories)
        total_count = trajectories * steps
        total_sum = trajectory_sums[selected].sum(axis=0)
        total_cross = trajectory_cross_products[selected].sum(axis=0)
        covariance = (
            total_cross - np.outer(total_sum, total_sum) / total_count
        ) / (total_count - 1)
        precision = np.linalg.inv(covariance)
        output[repetition] = partial_correlation_from_precision(
            precision, 0, 2
        )
    return output


def impulse_response(
    model: LinearBlanketModel, source: int, times: np.ndarray
) -> np.ndarray:
    time_values = np.asarray(times, dtype=np.float64)
    if source not in range(4):
        raise ValueError("source must identify one of the four states")
    initial = np.zeros(4, dtype=np.float64)
    initial[source] = 1.0
    return np.stack([expm(model.generator * time) @ initial for time in time_values])


def alternative_partition_scan(covariance: np.ndarray) -> list[dict[str, object]]:
    """Score each unordered internal/external pair conditioned on the remainder."""

    precision = np.linalg.inv(np.asarray(covariance, dtype=np.float64))
    names = ("external", "sensory", "internal", "active")
    output: list[dict[str, object]] = []
    for left in range(4):
        for right in range(left + 1, 4):
            partial = partial_correlation_from_precision(precision, left, right)
            output.append(
                {
                    "pair": [names[left], names[right]],
                    "conditioning_set": [
                        names[index] for index in range(4) if index not in {left, right}
                    ],
                    "partial_correlation": partial,
                    "conditional_mutual_information": gaussian_cmi(partial),
                }
            )
    return output
