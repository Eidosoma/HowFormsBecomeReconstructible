"""Exact finite-state attractor and basin mapping."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def canonical_cycle(states: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in states)
    if not values:
        raise ValueError("cycle cannot be empty")
    rotations = tuple(values[index:] + values[:index] for index in range(len(values)))
    return min(rotations)


@dataclass(frozen=True)
class Attractor:
    index: int
    states: tuple[int, ...]

    @property
    def kind(self) -> str:
        return "point" if len(self.states) == 1 else "cycle"

    @property
    def label(self) -> str:
        prefix = "point" if len(self.states) == 1 else "cycle"
        return f"{prefix}:" + ".".join(str(state) for state in self.states)


@dataclass(frozen=True)
class Landscape:
    successor: np.ndarray
    attractor_index: np.ndarray
    distance: np.ndarray
    attractors: tuple[Attractor, ...]

    @property
    def state_count(self) -> int:
        return int(self.successor.size)

    @property
    def basin_sizes(self) -> np.ndarray:
        return np.bincount(self.attractor_index, minlength=len(self.attractors))

    @property
    def basin_fractions(self) -> np.ndarray:
        return self.basin_sizes.astype(float) / self.state_count

    @property
    def point_indices(self) -> tuple[int, ...]:
        return tuple(attr.index for attr in self.attractors if attr.kind == "point")

    @property
    def basin_entropy(self) -> float:
        probabilities = self.basin_fractions
        positive = probabilities[probabilities > 0]
        return float(-np.sum(positive * np.log(positive)))

    @property
    def mean_transient(self) -> float:
        return float(np.mean(self.distance))

    def point_label_for_exact_state(self, state: int) -> str | None:
        index = int(self.attractor_index[state])
        attractor = self.attractors[index]
        if attractor.kind == "point" and attractor.states[0] == state:
            return attractor.label
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "state_count": self.state_count,
            "successor": self.successor.tolist(),
            "attractor_index": self.attractor_index.tolist(),
            "distance": self.distance.tolist(),
            "attractors": [list(attractor.states) for attractor in self.attractors],
            "basin_sizes": self.basin_sizes.tolist(),
            "basin_entropy": self.basin_entropy,
            "mean_transient": self.mean_transient,
        }


def enumerate_landscape(successor: np.ndarray) -> Landscape:
    """Resolve every component of a finite functional graph exactly."""

    transitions = np.asarray(successor, dtype=np.int64)
    state_count = int(transitions.size)
    if state_count == 0:
        raise ValueError("successor table cannot be empty")
    if np.any(transitions < 0) or np.any(transitions >= state_count):
        raise ValueError("successor table points outside the state space")

    assignment = np.full(state_count, -1, dtype=np.int64)
    distance = np.full(state_count, -1, dtype=np.int64)
    attractor_states: list[tuple[int, ...]] = []

    for start in range(state_count):
        if assignment[start] >= 0:
            continue
        path: list[int] = []
        positions: dict[int, int] = {}
        current = start
        while assignment[current] < 0 and current not in positions:
            positions[current] = len(path)
            path.append(current)
            current = int(transitions[current])

        if current in positions:
            cycle_start = positions[current]
            cycle = canonical_cycle(path[cycle_start:])
            attractor_id = len(attractor_states)
            attractor_states.append(cycle)
            for state in cycle:
                assignment[state] = attractor_id
                distance[state] = 0
            prefix = path[:cycle_start]
        else:
            attractor_id = int(assignment[current])
            prefix = path

        for state in reversed(prefix):
            next_state = int(transitions[state])
            assignment[state] = attractor_id
            distance[state] = distance[next_state] + 1

    # Canonical ordering makes saved landscapes independent of discovery details.
    ordering = sorted(range(len(attractor_states)), key=lambda index: attractor_states[index])
    remap = np.empty(len(ordering), dtype=np.int64)
    for new_index, old_index in enumerate(ordering):
        remap[old_index] = new_index
    assignment = remap[assignment]
    attractors = tuple(
        Attractor(index=new_index, states=attractor_states[old_index])
        for new_index, old_index in enumerate(ordering)
    )
    transitions.setflags(write=False)
    assignment.setflags(write=False)
    distance.setflags(write=False)
    return Landscape(transitions, assignment, distance, attractors)


def int_to_bits(state: int, genes: int) -> np.ndarray:
    return np.asarray([(state >> gene) & 1 for gene in range(genes)], dtype=np.int8)


def bits_to_int(bits: np.ndarray) -> int:
    return int(sum(int(bit) << index for index, bit in enumerate(bits)))


def int_to_signs(state: int, genes: int) -> np.ndarray:
    return 2 * int_to_bits(state, genes) - 1


def signs_to_int(signs: np.ndarray) -> int:
    return bits_to_int((np.asarray(signs) > 0).astype(np.int8))


def normalized_hamming(left: int, right: int, genes: int) -> float:
    return (int(left) ^ int(right)).bit_count() / genes


def permute_state(state: int, permutation: np.ndarray | tuple[int, ...], genes: int) -> int:
    """Move old gene ``i`` to new index ``permutation[i]``."""

    perm = np.asarray(permutation, dtype=np.int64)
    if sorted(perm.tolist()) != list(range(genes)):
        raise ValueError("invalid node permutation")
    old = int_to_bits(state, genes)
    new = np.empty_like(old)
    for old_index, new_index in enumerate(perm):
        new[new_index] = old[old_index]
    return bits_to_int(new)


def permute_successor(successor: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    genes = int(np.log2(successor.size))
    result = np.empty_like(successor)
    for old_state in range(successor.size):
        new_state = permute_state(old_state, permutation, genes)
        result[new_state] = permute_state(int(successor[old_state]), permutation, genes)
    return result

