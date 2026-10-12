from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .config import GardConfig, SimulationContract


IntVector = NDArray[np.int64]
FloatVector = NDArray[np.float64]
FloatMatrix = NDArray[np.float64]


class SimulationError(RuntimeError):
    pass


@dataclass(frozen=True)
class FissionRecord:
    parent: IntVector
    daughter: IntVector
    h: float
    growth_steps: int


def cosine_similarity(left: NDArray, right: NDArray) -> float:
    left_f = np.asarray(left, dtype=np.float64)
    right_f = np.asarray(right, dtype=np.float64)
    denominator = float(np.linalg.norm(left_f) * np.linalg.norm(right_f))
    if denominator == 0.0:
        return 0.0
    return float(np.clip(np.dot(left_f, right_f) / denominator, 0.0, 1.0))


def generate_beta(config: GardConfig, rng: np.random.Generator) -> FloatMatrix:
    normal = rng.standard_normal((config.n_types, config.n_types))
    return np.exp(config.beta_log_mean + config.beta_log_sd * normal)


def generate_initial_composition(config: GardConfig, rng: np.random.Generator) -> IntVector:
    composition = np.zeros(config.n_types, dtype=np.int64)
    composition[rng.choice(config.n_types, size=config.n_min, replace=False)] = 1
    return composition


def _sample_without_replacement(
    counts: IntVector, sample_size: int, rng: np.random.Generator
) -> IntVector:
    total = int(counts.sum())
    if not 0 <= sample_size <= total:
        raise SimulationError(f"invalid sample size {sample_size} for mass {total}")
    if sample_size == 0:
        return np.zeros_like(counts)
    return np.asarray(rng.multivariate_hypergeometric(counts, sample_size), dtype=np.int64)


def _trim_whole_assembly(
    composition: IntVector, target: int, rng: np.random.Generator
) -> IntVector:
    excess = int(composition.sum()) - target
    if excess <= 0:
        return composition
    return composition - _sample_without_replacement(composition, excess, rng)


def _fission(
    parent: IntVector,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
) -> IntVector:
    if contract.fission_rule == "fixed_size":
        first = _sample_without_replacement(parent, config.n_min, rng)
    elif contract.fission_rule == "binomial":
        first = np.asarray(rng.binomial(parent, 0.5), dtype=np.int64)
    else:
        raise SimulationError(f"unknown fission rule: {contract.fission_rule}")
    second = parent - first
    daughter = first if contract.daughter_rule == "first" else second
    if int(daughter.sum()) == 0:
        raise SimulationError("selected daughter was empty")
    return daughter


def _grow_neutral(
    composition: IntVector,
    beta: FloatMatrix,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
) -> tuple[IntVector, int]:
    """Exact retained candidate kernel used by the neutral identity fixture."""

    current = np.asarray(composition, dtype=np.int64).copy()
    rho = 1.0 / config.n_types
    for step in range(1, config.max_growth_steps + 1):
        mass = int(current.sum())
        if mass <= 0:
            raise SimulationError("assembly became extinct")
        if mass >= config.n_max:
            return _trim_whole_assembly(current, config.n_max, rng), step - 1
        catalytic_boost = 1.0 + (beta @ current) / mass
        join_rate = config.k_join * rho * mass * catalytic_boost
        leave_rate = config.k_leave * current * catalytic_boost
        exposure = contract.poisson_exposure
        joins = np.asarray(rng.poisson(join_rate * exposure), dtype=np.int64)
        leaves = np.minimum(
            np.asarray(rng.poisson(leave_rate * exposure), dtype=np.int64), current
        )
        survivors = current - leaves
        if contract.overshoot_rule == "admit_joiners_to_capacity":
            capacity = config.n_max - int(survivors.sum())
            if int(joins.sum()) > capacity:
                joins = _sample_without_replacement(joins, capacity, rng)
            current = survivors + joins
        elif contract.overshoot_rule == "trim_whole_assembly":
            current = survivors + joins
            if int(current.sum()) >= config.n_max:
                current = _trim_whole_assembly(current, config.n_max, rng)
        else:
            raise SimulationError(f"unknown overshoot rule: {contract.overshoot_rule}")
        if int(current.sum()) >= config.n_max:
            return current, step
    raise SimulationError(
        f"growth did not reach mass {config.n_max} in {config.max_growth_steps} steps"
    )


def _grow_controlled(
    composition: IntVector,
    beta: FloatMatrix,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
    reservoir: FloatVector,
    exposure_multiplier: float,
) -> tuple[IntVector, int]:
    current = np.asarray(composition, dtype=np.int64).copy()
    rho = np.asarray(reservoir, dtype=np.float64)
    if rho.shape != (config.n_types,) or np.any(rho < 0.0):
        raise ValueError("reservoir must be a nonnegative n_types vector")
    if exposure_multiplier <= 0.0:
        raise ValueError("exposure multiplier must be positive")
    for step in range(1, config.max_growth_steps + 1):
        mass = int(current.sum())
        if mass <= 0:
            raise SimulationError("assembly became extinct")
        if mass >= config.n_max:
            return _trim_whole_assembly(current, config.n_max, rng), step - 1
        catalytic_boost = 1.0 + (beta @ current) / mass
        join_rate = config.k_join * rho * mass * catalytic_boost
        leave_rate = config.k_leave * current * catalytic_boost
        exposure = contract.poisson_exposure * exposure_multiplier
        joins = np.asarray(rng.poisson(join_rate * exposure), dtype=np.int64)
        leaves = np.minimum(
            np.asarray(rng.poisson(leave_rate * exposure), dtype=np.int64), current
        )
        survivors = current - leaves
        if contract.overshoot_rule == "admit_joiners_to_capacity":
            capacity = config.n_max - int(survivors.sum())
            if int(joins.sum()) > capacity:
                joins = _sample_without_replacement(joins, capacity, rng)
            current = survivors + joins
        elif contract.overshoot_rule == "trim_whole_assembly":
            current = survivors + joins
            if int(current.sum()) >= config.n_max:
                current = _trim_whole_assembly(current, config.n_max, rng)
        else:
            raise SimulationError(f"unknown overshoot rule: {contract.overshoot_rule}")
        if int(current.sum()) >= config.n_max:
            return current, step
    raise SimulationError(
        f"growth did not reach mass {config.n_max} in {config.max_growth_steps} steps"
    )


def advance_fission(
    composition: IntVector,
    beta: FloatMatrix,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
    *,
    reservoir: FloatVector | None = None,
    exposure_multiplier: float = 1.0,
) -> FissionRecord:
    if reservoir is None and exposure_multiplier == 1.0:
        parent, steps = _grow_neutral(composition, beta, config, contract, rng)
    else:
        effective = (
            np.full(config.n_types, 1.0 / config.n_types, dtype=np.float64)
            if reservoir is None
            else np.asarray(reservoir, dtype=np.float64)
        )
        parent, steps = _grow_controlled(
            composition,
            beta,
            config,
            contract,
            rng,
            effective,
            exposure_multiplier,
        )
    daughter = _fission(parent, config, contract, rng)
    return FissionRecord(parent, daughter, cosine_similarity(parent, daughter), steps)


def balanced_partition(n_types: int, seed: int) -> NDArray[np.int8]:
    if n_types % 2:
        raise ValueError("balanced partition requires an even number of types")
    order = np.random.default_rng(seed).permutation(n_types)
    values = np.zeros(n_types, dtype=np.int8)
    values[order[n_types // 2 :]] = 1
    return values


def simultaneous_permutation(beta: FloatMatrix, order: NDArray[np.int64]) -> FloatMatrix:
    values = np.asarray(beta, dtype=np.float64)
    permutation = np.asarray(order, dtype=np.int64)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("beta must be square")
    if sorted(permutation.tolist()) != list(range(values.shape[0])):
        raise ValueError("order must be a permutation")
    return values[np.ix_(permutation, permutation)].copy()


def variance_restored_log_morph(
    beta: FloatMatrix, permuted: FloatMatrix, alpha: float
) -> FloatMatrix:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("morph alpha must lie in [0, 1]")
    left = np.log(np.maximum(np.asarray(beta, dtype=np.float64), np.finfo(float).tiny))
    right = np.log(np.maximum(np.asarray(permuted, dtype=np.float64), np.finfo(float).tiny))
    mixed = (1.0 - alpha) * left + alpha * right
    target_mean = float(left.mean())
    target_sd = float(left.std())
    observed_sd = float(mixed.std())
    if observed_sd == 0.0:
        raise ValueError("cannot variance-restore a constant log matrix")
    restored = target_mean + (mixed - float(mixed.mean())) * (target_sd / observed_sd)
    return np.exp(restored)


def normalized_gate(scores: FloatVector, direction: int, strength: float) -> FloatVector:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("gate scores must be a finite vector")
    if direction not in (-1, 1):
        raise ValueError("gate direction must be -1 or 1")
    centered = values - float(values.mean())
    scale = float(centered.std())
    standardized = centered / scale if scale > 0.0 else centered
    gate = np.exp(np.clip(direction * strength * standardized, -6.0, 6.0))
    return gate / float(gate.mean())


def apply_ranked_substitution(
    composition: IntVector, target_scores: FloatVector
) -> tuple[IntVector, int, int]:
    values = np.asarray(composition, dtype=np.int64)
    scores = np.asarray(target_scores, dtype=np.float64)
    if values.ndim != 1 or scores.shape != values.shape:
        raise ValueError("composition and target scores must be aligned vectors")
    present = np.flatnonzero(values > 0)
    if present.size == 0:
        raise SimulationError("cannot edit an empty assembly")
    add_order = np.lexsort((np.arange(values.size), -scores))
    remove_order = present[np.lexsort((present, scores[present]))]
    add = int(add_order[0])
    remove = next((int(index) for index in remove_order if int(index) != add), -1)
    if remove < 0:
        return values.copy(), -1, -1
    edited = values.copy()
    mass = int(edited.sum())
    edited[remove] -= 1
    edited[add] += 1
    if np.any(edited < 0) or int(edited.sum()) != mass:
        raise AssertionError("ranked substitution violated mass conservation")
    return edited, remove, add

