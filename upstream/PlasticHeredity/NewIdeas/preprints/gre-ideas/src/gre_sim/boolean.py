"""Exact synchronous Boolean truth-table GRNs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .accelerate import boolean_successors
from .landscape import (
    Landscape,
    canonical_cycle,
    enumerate_landscape,
    permute_state,
    permute_successor,
)
from .types import DevelopmentResult


@dataclass(frozen=True)
class BooleanRulebook:
    """One Boolean genome: a full input truth table for every gene."""

    truth_table: np.ndarray

    def __post_init__(self) -> None:
        table = np.asarray(self.truth_table, dtype=np.uint8).copy()
        if table.ndim != 2:
            raise ValueError("truth_table must have shape (genes, 2**genes)")
        genes, states = table.shape
        if states != 1 << genes:
            raise ValueError("truth_table must contain one column per global state")
        if np.any((table != 0) & (table != 1)):
            raise ValueError("truth_table entries must be binary")
        table.setflags(write=False)
        object.__setattr__(self, "truth_table", table)

    @property
    def genes(self) -> int:
        return int(self.truth_table.shape[0])

    @property
    def state_count(self) -> int:
        return 1 << self.genes

    @property
    def uid(self) -> str:
        digest = hashlib.blake2b(self.truth_table.tobytes(), digest_size=12).hexdigest()
        return f"boolean-{self.genes}-{digest}"

    @property
    def successor(self) -> np.ndarray:
        result = np.asarray(boolean_successors(self.truth_table), dtype=np.int64)
        result.setflags(write=False)
        return result

    def landscape(self) -> Landscape:
        return enumerate_landscape(self.successor)

    def step(self, state: int) -> int:
        if state < 0 or state >= self.state_count:
            raise ValueError("state lies outside the Boolean state space")
        successor = 0
        for gene in range(self.genes):
            successor |= int(self.truth_table[gene, state]) << gene
        return successor

    def develop(self, initial_state: int, max_steps: int | None = None) -> DevelopmentResult:
        limit = max_steps if max_steps is not None else self.state_count + 1
        current = int(initial_state)
        positions: dict[int, int] = {}
        path: list[int] = []
        for step_index in range(limit):
            if current in positions:
                cycle = canonical_cycle(path[positions[current] :])
                if len(cycle) == 1:
                    return DevelopmentResult("point", cycle[0], step_index, cycle)
                return DevelopmentResult("cycle", current, step_index, cycle)
            positions[current] = len(path)
            path.append(current)
            following = self.step(current)
            if following == current:
                return DevelopmentResult("point", current, step_index + 1, (current,))
            current = following
        return DevelopmentResult("nonconvergent", current, limit, ())

    def permute(self, permutation: np.ndarray | tuple[int, ...]) -> "BooleanRulebook":
        perm = np.asarray(permutation, dtype=np.int64)
        successor = permute_successor(self.successor, perm)
        return BooleanRulebook.from_successor(successor)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": "boolean",
            "genes": self.genes,
            "uid": self.uid,
            "truth_table": self.truth_table.tolist(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BooleanRulebook":
        return cls(np.asarray(value["truth_table"], dtype=np.uint8))

    @classmethod
    def random(cls, genes: int, rng: np.random.Generator) -> "BooleanRulebook":
        return cls(rng.integers(0, 2, size=(genes, 1 << genes), dtype=np.uint8))

    @classmethod
    def constant(cls, genes: int, target_state: int) -> "BooleanRulebook":
        table = np.empty((genes, 1 << genes), dtype=np.uint8)
        for gene in range(genes):
            table[gene, :] = (target_state >> gene) & 1
        return cls(table)

    @classmethod
    def from_successor(cls, successor: np.ndarray) -> "BooleanRulebook":
        transitions = np.asarray(successor, dtype=np.int64)
        states = int(transitions.size)
        genes = states.bit_length() - 1
        if 1 << genes != states:
            raise ValueError("successor length must be a power of two")
        table = np.empty((genes, states), dtype=np.uint8)
        for state in range(states):
            for gene in range(genes):
                table[gene, state] = (int(transitions[state]) >> gene) & 1
        return cls(table)


def permute_boolean_noise(flips: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    result = np.empty_like(flips)
    for old_index, new_index in enumerate(permutation):
        result[new_index] = flips[old_index]
    return result


def mutate_boolean(
    rulebook: BooleanRulebook,
    rng: np.random.Generator,
    probability: float | None = None,
) -> BooleanRulebook:
    table = rulebook.truth_table.copy()
    p = probability if probability is not None else 1.0 / table.size
    mask = rng.random(table.shape) < p
    table[mask] = 1 - table[mask]
    return BooleanRulebook(table)


def recombine_boolean(
    first: BooleanRulebook,
    second: BooleanRulebook,
    rng: np.random.Generator,
) -> BooleanRulebook:
    if first.truth_table.shape != second.truth_table.shape:
        raise ValueError("Boolean parents must have identical dimensions")
    choose_first = rng.random(first.genes) < 0.5
    table = np.where(choose_first[:, None], first.truth_table, second.truth_table)
    return BooleanRulebook(table)


def conjugate_state(state: int, rulebook: BooleanRulebook, permutation: np.ndarray) -> int:
    return permute_state(state, permutation, rulebook.genes)

