"""Stochastic Wagner-style recurrent gene-regulatory networks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .accelerate import wagner_sweep
from .landscape import (
    Landscape,
    canonical_cycle,
    enumerate_landscape,
    int_to_signs,
    signs_to_int,
)
from .types import DevelopmentResult


@dataclass(frozen=True)
class WagnerRulebook:
    """A real-valued regulatory matrix, cue bias, and asynchronous update order."""

    weights: np.ndarray
    bias: np.ndarray
    order: np.ndarray

    def __post_init__(self) -> None:
        weights = np.asarray(self.weights, dtype=np.float64).copy()
        bias = np.asarray(self.bias, dtype=np.float64).copy()
        order = np.asarray(self.order, dtype=np.int64).copy()
        if weights.ndim != 2 or weights.shape[0] != weights.shape[1]:
            raise ValueError("weights must be a square matrix")
        genes = weights.shape[0]
        if bias.shape != (genes,):
            raise ValueError("bias must contain one entry per gene")
        if order.shape != (genes,) or sorted(order.tolist()) != list(range(genes)):
            raise ValueError("order must be a permutation of gene indices")
        for value in (weights, bias, order):
            value.setflags(write=False)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "bias", bias)
        object.__setattr__(self, "order", order)

    @property
    def genes(self) -> int:
        return int(self.weights.shape[0])

    @property
    def state_count(self) -> int:
        return 1 << self.genes

    @property
    def uid(self) -> str:
        payload = self.weights.tobytes() + self.bias.tobytes() + self.order.tobytes()
        digest = hashlib.blake2b(payload, digest_size=12).hexdigest()
        return f"wagner-{self.genes}-{digest}"

    def effective_weights(self, multipliers: np.ndarray | None = None) -> np.ndarray:
        if multipliers is None:
            return self.weights
        values = np.asarray(multipliers, dtype=np.float64)
        if values.shape != self.weights.shape:
            raise ValueError("multipliers must match the regulatory matrix")
        return self.weights * values

    def step(self, state: int, multipliers: np.ndarray | None = None) -> int:
        signs = int_to_signs(state, self.genes)
        updated = wagner_sweep(
            self.effective_weights(multipliers), self.bias, self.order, signs
        )
        return signs_to_int(updated)

    def successor_table(self) -> np.ndarray:
        result = np.asarray(
            [self.step(state) for state in range(self.state_count)], dtype=np.int64
        )
        result.setflags(write=False)
        return result

    def landscape(self) -> Landscape:
        return enumerate_landscape(self.successor_table())

    def develop(
        self,
        initial_state: int,
        multipliers: np.ndarray | None = None,
        max_sweeps: int = 100,
    ) -> DevelopmentResult:
        current = int(initial_state)
        positions: dict[int, int] = {}
        path: list[int] = []
        for sweep in range(max_sweeps):
            if current in positions:
                cycle = canonical_cycle(path[positions[current] :])
                if len(cycle) == 1:
                    return DevelopmentResult("point", cycle[0], sweep, cycle)
                return DevelopmentResult("cycle", current, sweep, cycle)
            positions[current] = len(path)
            path.append(current)
            following = self.step(current, multipliers)
            if following == current:
                return DevelopmentResult("point", current, sweep + 1, (current,))
            current = following
        return DevelopmentResult("nonconvergent", current, max_sweeps, ())

    def permute(self, permutation: np.ndarray | tuple[int, ...]) -> "WagnerRulebook":
        perm = np.asarray(permutation, dtype=np.int64)
        if sorted(perm.tolist()) != list(range(self.genes)):
            raise ValueError("invalid node permutation")
        weights = np.empty_like(self.weights)
        bias = np.empty_like(self.bias)
        for old_i, new_i in enumerate(perm):
            bias[new_i] = self.bias[old_i]
            for old_j, new_j in enumerate(perm):
                weights[new_i, new_j] = self.weights[old_i, old_j]
        order = np.asarray([perm[index] for index in self.order], dtype=np.int64)
        return WagnerRulebook(weights, bias, order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": "wagner",
            "genes": self.genes,
            "uid": self.uid,
            "weights": self.weights.tolist(),
            "bias": self.bias.tolist(),
            "order": self.order.tolist(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WagnerRulebook":
        return cls(
            np.asarray(value["weights"], dtype=np.float64),
            np.asarray(value["bias"], dtype=np.float64),
            np.asarray(value["order"], dtype=np.int64),
        )

    @classmethod
    def random(cls, genes: int, rng: np.random.Generator) -> "WagnerRulebook":
        return cls(
            rng.normal(0.0, 1.0, size=(genes, genes)),
            np.zeros(genes, dtype=np.float64),
            np.arange(genes, dtype=np.int64),
        )

    @classmethod
    def constant(cls, genes: int, target_state: int) -> "WagnerRulebook":
        target = int_to_signs(target_state, genes).astype(np.float64)
        return cls(
            np.zeros((genes, genes), dtype=np.float64),
            target,
            np.arange(genes, dtype=np.int64),
        )


def gamma_multipliers(
    genes: int, variance: float, rng: np.random.Generator
) -> np.ndarray:
    if variance < 0:
        raise ValueError("gamma variance cannot be negative")
    if variance == 0:
        return np.ones((genes, genes), dtype=np.float64)
    return rng.gamma(shape=1.0 / variance, scale=variance, size=(genes, genes))


def permute_wagner_noise(multipliers: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    result = np.empty_like(multipliers)
    for old_i, new_i in enumerate(permutation):
        for old_j, new_j in enumerate(permutation):
            result[new_i, new_j] = multipliers[old_i, old_j]
    return result


def mutate_wagner(
    rulebook: WagnerRulebook,
    rng: np.random.Generator,
    probability: float | None = None,
) -> WagnerRulebook:
    weights = rulebook.weights.copy()
    p = probability if probability is not None else 1.0 / weights.size
    mask = rng.random(weights.shape) < p
    weights[mask] = rng.normal(0.0, 1.0, size=int(mask.sum()))
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def recombine_wagner(
    first: WagnerRulebook,
    second: WagnerRulebook,
    rng: np.random.Generator,
) -> WagnerRulebook:
    if first.weights.shape != second.weights.shape:
        raise ValueError("Wagner parents must have identical dimensions")
    choose_first = rng.random(first.genes) < 0.5
    weights = np.where(choose_first[:, None], first.weights, second.weights)
    # Bias and update order are experimental context, not inherited genotype.
    return WagnerRulebook(weights, first.bias, first.order)

