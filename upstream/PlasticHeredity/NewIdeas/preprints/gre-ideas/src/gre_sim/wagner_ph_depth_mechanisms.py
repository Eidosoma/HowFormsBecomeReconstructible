"""Weight perturbation and mutation kernels for Interpreter-Depth v1."""

from __future__ import annotations

from typing import Any

import numpy as np

from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_cooption_evolution import mutate_carrier
from .wagner_ph_robustness_mechanisms import Genotype, mutation_delta
from .wagner_ph_depth_config import ATLAS_PERTURBATIONS, arm_settings


def mutate_wagner_local(
    rulebook: WagnerRulebook,
    random: np.random.Generator,
    sigma: float = 0.1,
    probability: float | None = None,
) -> WagnerRulebook:
    """Mutate the same expected number of weights as Wagner reset mutation, locally."""

    if sigma <= 0.0:
        raise ValueError("local mutation sigma must be positive")
    weights = rulebook.weights.copy()
    p = probability if probability is not None else 1.0 / weights.size
    if not 0.0 <= p <= 1.0:
        raise ValueError("weight mutation probability must lie in [0, 1]")
    mask = random.random(weights.shape) < p
    weights[mask] += random.normal(0.0, sigma, size=int(mask.sum()))
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def mutate_for_arm(
    left: Genotype,
    right: Genotype,
    arm: str,
    random: np.random.Generator,
    *,
    local_sigma: float = 0.1,
) -> Genotype:
    settings = arm_settings(arm)
    recombined = recombine_wagner(left[0], right[0], random)
    if settings["weight_mutation"] == "reset":
        rulebook = mutate_wagner(recombined, random)
    else:
        rulebook = mutate_wagner_local(recombined, random, local_sigma)
    carrier = mutate_carrier(left[1], right[1], "independent", random)
    return rulebook, carrier


def perturb_edge(
    rulebook: WagnerRulebook,
    target: int,
    source: int,
    operation: str,
    random: np.random.Generator,
    *,
    local_sigma: float = 0.1,
) -> WagnerRulebook:
    """Apply exactly one registered intervention to one directed GRN weight."""

    if operation not in ATLAS_PERTURBATIONS:
        raise ValueError(f"unknown interpreter-atlas perturbation: {operation}")
    if not 0 <= target < rulebook.genes or not 0 <= source < rulebook.genes:
        raise IndexError("Wagner edge index out of range")
    weights = rulebook.weights.copy()
    old = float(weights[target, source])
    if operation == "reset":
        weights[target, source] = float(random.normal(0.0, 1.0))
    elif operation == "local_add":
        weights[target, source] = old + float(random.normal(0.0, local_sigma))
    elif operation == "zero":
        weights[target, source] = 0.0
    else:
        weights[target, source] = -old
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def edge_features(rulebook: WagnerRulebook, carrier_mask: tuple[int, ...], target: int, source: int) -> dict[str, Any]:
    marked = set(carrier_mask)
    return {
        "target": target,
        "source": source,
        "self_edge": target == source,
        "source_is_carrier_locus": source in marked,
        "target_is_carrier_locus": target in marked,
        "both_endpoints_are_carrier_loci": source in marked and target in marked,
        "weight": float(rulebook.weights[target, source]),
        "absolute_weight": abs(float(rulebook.weights[target, source])),
        "target_absolute_input": float(np.sum(np.abs(rulebook.weights[target, :]))),
        "source_absolute_output": float(np.sum(np.abs(rulebook.weights[:, source]))),
    }


__all__ = (
    "Genotype",
    "edge_features",
    "mutate_for_arm",
    "mutate_wagner_local",
    "mutation_delta",
    "perturb_edge",
)
