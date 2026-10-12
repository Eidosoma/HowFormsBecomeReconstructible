"""State, slow-mark, cue, challenge, and endpoint mechanics."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .endpoints import apply_carryover
from .landscape import Landscape, bits_to_int, int_to_bits, int_to_signs, normalized_hamming
from .mechanism_dynamics import MechanismRulebook
from .types import DevelopmentResult
from .wagner import WagnerRulebook, gamma_multipliers


@dataclass(frozen=True)
class AttractorPair:
    left_index: int
    right_index: int
    left_state: int
    right_state: int

    def state(self, history: str) -> int:
        if history == "A":
            return self.left_state
        if history == "B":
            return self.right_state
        raise ValueError(f"unknown history: {history}")

    def index(self, history: str) -> int:
        if history == "A":
            return self.left_index
        if history == "B":
            return self.right_index
        raise ValueError(f"unknown history: {history}")


@dataclass(frozen=True)
class MemoryCycle:
    state: int
    mark: tuple[float, ...]
    status: str
    steps: int


@dataclass(frozen=True)
class MemoryFutureSummary:
    acquired: bool
    form_destination: str
    correct_hold_run: int
    wrong_hold_run: int
    generic_hold_run: int
    correct_hold8: bool
    wrong_hold8: bool
    generic_hold8: bool
    returned: bool
    return_cycle: int | None
    first_break_cycle: int | None
    point_cycles: int
    cycle_cycles: int
    nonconvergent_cycles: int
    unique_adult_states: int
    start_mark_norm: float
    end_mark_norm: float
    trace_digest: str


def select_attractor_pair(
    landscape: Landscape,
    genes: int,
    minimum_basin_fraction: float,
    minimum_form_distance: float,
) -> AttractorPair | None:
    """Choose a balanced, large, well-separated point pair without future shooting."""

    eligible = [
        index
        for index in landscape.point_indices
        if float(landscape.basin_fractions[index]) >= minimum_basin_fraction
    ]
    candidates: list[tuple[tuple[float, ...], AttractorPair]] = []
    for position, left_index in enumerate(eligible):
        left_state = int(landscape.attractors[left_index].states[0])
        left_basin = float(landscape.basin_fractions[left_index])
        for right_index in eligible[position + 1 :]:
            right_state = int(landscape.attractors[right_index].states[0])
            distance = normalized_hamming(left_state, right_state, genes)
            if distance < minimum_form_distance:
                continue
            right_basin = float(landscape.basin_fractions[right_index])
            balance = abs(math.log(max(left_basin, 1e-15) / max(right_basin, 1e-15)))
            pair = AttractorPair(left_index, right_index, left_state, right_state)
            key = (
                balance,
                -min(left_basin, right_basin),
                -distance,
                float(left_state),
                float(right_state),
            )
            candidates.append((key, pair))
    return min(candidates, key=lambda value: value[0])[1] if candidates else None


def balanced_midpoints(
    pair: AttractorPair,
    genes: int,
    ordering: np.ndarray,
    count: int = 2,
) -> tuple[int, ...]:
    """Construct one or two complementary midpoint states between two forms."""

    if count not in {1, 2}:
        raise ValueError("midpoint count must be one or two")
    left = int_to_bits(pair.left_state, genes)
    right = int_to_bits(pair.right_state, genes)
    differing = [int(index) for index in ordering if left[int(index)] != right[int(index)]]
    if not differing:
        raise ValueError("attractor pair has no differing nodes")
    first = left.copy()
    for position, gene in enumerate(differing):
        first[gene] = left[gene] if position % 2 == 0 else right[gene]
    values = [bits_to_int(first)]
    if count == 2:
        second = first.copy()
        for gene in differing:
            second[gene] = 1 - second[gene]
        values.append(bits_to_int(second))
    return tuple(values)


def cue_nodes(
    pair: AttractorPair,
    genes: int,
    fraction: float,
    ordering: np.ndarray,
) -> tuple[int, ...]:
    if not 0.0 < fraction <= 1.0:
        raise ValueError("cue fraction must lie in (0, 1]")
    left = int_to_bits(pair.left_state, genes)
    right = int_to_bits(pair.right_state, genes)
    differing = [int(index) for index in ordering if left[int(index)] != right[int(index)]]
    amount = max(1, int(math.ceil(fraction * len(differing))))
    return tuple(differing[:amount])


def clamp_state(state: int, target: int, nodes: tuple[int, ...]) -> int:
    value = int(state)
    for gene in nodes:
        if (target >> gene) & 1:
            value |= 1 << gene
        else:
            value &= ~(1 << gene)
    return value


def apply_mark_bias(
    state: int,
    mark: np.ndarray,
    coupling: float,
    rng: np.random.Generator,
) -> int:
    """Let a bounded mark stochastically bias expression initialization."""

    values = np.asarray(mark, dtype=float)
    if not 0.0 <= coupling <= 1.0:
        raise ValueError("mark coupling must lie in [0, 1]")
    if np.any(values < -1.0 - 1e-12) or np.any(values > 1.0 + 1e-12):
        raise ValueError("mark components must lie in [-1, 1]")
    if coupling == 0.0:
        return int(state)
    bits = int_to_bits(state, len(values))
    overrides = rng.random(len(values)) < coupling * np.abs(values)
    for gene in np.flatnonzero(overrides):
        bits[int(gene)] = 1 if values[int(gene)] > 0.0 else 0
    return bits_to_int(bits)


def update_mark(mark: np.ndarray, adult_state: int, genes: int, rho: float) -> np.ndarray:
    if not 0.0 <= rho < 1.0:
        raise ValueError("mark retention rho must lie in [0, 1)")
    values = np.asarray(mark, dtype=float)
    if values.shape != (genes,):
        raise ValueError("mark shape does not match gene count")
    adult = int_to_signs(adult_state, genes).astype(float)
    updated = rho * values + (1.0 - rho) * adult
    return np.clip(updated, -1.0, 1.0)


def develop_memory_cycle(
    rulebook: MechanismRulebook,
    previous_state: int,
    base_state: int,
    mark: np.ndarray,
    carryover: float,
    expression_flip_probability: float,
    mark_rho: float,
    mark_coupling: float,
    gamma_variance: float,
    wagner_max_sweeps: int,
    carry_rng: np.random.Generator,
    mark_rng: np.random.Generator,
    dynamics_rng: np.random.Generator,
    cue_target: int | None = None,
    clamped_nodes: tuple[int, ...] = (),
    write_mark: bool = True,
) -> MemoryCycle:
    """Advance one cycle in the registered inheritance/noise/cue order."""

    initial = apply_carryover(
        previous_state,
        base_state,
        rulebook.genes,
        carryover,
        expression_flip_probability,
        carry_rng,
    )
    initial = apply_mark_bias(initial, mark, mark_coupling, mark_rng)
    if cue_target is not None:
        initial = clamp_state(initial, cue_target, clamped_nodes)
    multipliers = None
    if isinstance(rulebook.source, WagnerRulebook):
        multipliers = gamma_multipliers(rulebook.genes, gamma_variance, dynamics_rng)
    result = rulebook.develop(initial, multipliers, wagner_max_sweeps)
    next_mark = (
        update_mark(mark, result.final_state, rulebook.genes, mark_rho)
        if write_mark
        else np.asarray(mark, dtype=float).copy()
    )
    return MemoryCycle(
        int(result.final_state),
        tuple(float(value) for value in next_mark),
        result.status,
        int(result.steps),
    )


def forced_break_state(
    landscape: Landscape,
    target_index: int,
    target_state: int,
    genes: int,
) -> int:
    """Return the nearest state prospectively known to lie outside a target basin."""

    candidates = [
        state
        for state in range(landscape.state_count)
        if int(landscape.attractor_index[state]) != target_index
    ]
    if not candidates:
        raise ValueError("forced break requires a state outside the target basin")
    return min(
        candidates,
        key=lambda state: (
            normalized_hamming(state, target_state, genes),
            int(landscape.distance[state]),
            state,
        ),
    )


def descriptor_matched_state(
    landscape: Landscape,
    state: int,
    pair: AttractorPair,
    genes: int,
    ordinal: int,
) -> tuple[int, bool]:
    """Choose an untrained state matched on frozen finite-state descriptors."""

    descriptor = (
        int(state).bit_count(),
        (int(state) ^ pair.left_state).bit_count(),
        (int(state) ^ pair.right_state).bit_count(),
        int(landscape.attractor_index[state]),
        int(landscape.distance[state]),
    )
    exact = [
        candidate
        for candidate in range(landscape.state_count)
        if candidate != state
        and (
            candidate.bit_count(),
            (candidate ^ pair.left_state).bit_count(),
            (candidate ^ pair.right_state).bit_count(),
            int(landscape.attractor_index[candidate]),
            int(landscape.distance[candidate]),
        )
        == descriptor
    ]
    if exact:
        return int(exact[ordinal % len(exact)]), True
    fallback = min(
        (candidate for candidate in range(landscape.state_count) if candidate != state),
        key=lambda candidate: (
            int(int(landscape.attractor_index[candidate]) != descriptor[3]),
            abs(candidate.bit_count() - descriptor[0])
            + abs((candidate ^ pair.left_state).bit_count() - descriptor[1])
            + abs((candidate ^ pair.right_state).bit_count() - descriptor[2]),
            abs(int(landscape.distance[candidate]) - descriptor[4]),
            (candidate - ordinal) % landscape.state_count,
        ),
    )
    return int(fallback), False


def permute_mark(mark: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    values = np.asarray(mark, dtype=float)
    perm = np.asarray(permutation, dtype=np.int64)
    if values.shape != perm.shape or sorted(perm.tolist()) != list(range(len(values))):
        raise ValueError("invalid mark permutation")
    result = np.empty_like(values)
    for old_index, new_index in enumerate(perm):
        result[new_index] = values[old_index]
    return result


def permute_state(state: int, genes: int, permutation: np.ndarray) -> int:
    """Move expression components with the same old-to-new convention as marks."""

    perm = np.asarray(permutation, dtype=np.int64)
    if perm.shape != (genes,) or sorted(perm.tolist()) != list(range(genes)):
        raise ValueError("invalid state permutation")
    source = int_to_bits(state, genes)
    result = np.empty_like(source)
    for old_index, new_index in enumerate(perm):
        result[int(new_index)] = source[old_index]
    return bits_to_int(result)


def ablate_mark(mark: np.ndarray, indices: tuple[int, ...]) -> np.ndarray:
    result = np.asarray(mark, dtype=float).copy()
    result[list(indices)] = 0.0
    return result


def damage_state(
    state: int,
    genes: int,
    fraction: float,
    rng: np.random.Generator,
) -> tuple[int, tuple[int, ...]]:
    amount = max(1, int(round(fraction * genes))) if fraction > 0 else 0
    nodes = tuple(sorted(int(value) for value in rng.choice(genes, size=amount, replace=False)))
    damaged = int(state)
    for gene in nodes:
        damaged ^= 1 << gene
    return damaged, nodes


def _max_run(values: list[Any], target: Any | None = None) -> int:
    maximum = 0
    current: Any | None = None
    count = 0
    for value in values:
        valid = value is not None and (target is None or value == target)
        if not valid:
            current = None
            count = 0
            continue
        if value == current:
            count += 1
        else:
            current = value
            count = 1
        maximum = max(maximum, count)
    return maximum


def summarize_memory_future(
    training_states: tuple[int, ...],
    post_cycles: tuple[MemoryCycle, ...],
    pair: AttractorPair,
    history: str,
    start_mark: np.ndarray,
    strict_run: int,
    stable_run: int,
) -> MemoryFutureSummary:
    target = pair.state(history)
    wrong = pair.state("B" if history == "A" else "A")
    acquired = bool(training_states and training_states[-1] == target)
    states = [cycle.state for cycle in post_cycles]
    statuses = [cycle.status for cycle in post_cycles]
    correct_labels = [state if status == "point" and state == target else None for state, status in zip(states, statuses)]
    wrong_labels = [state if status == "point" and state == wrong else None for state, status in zip(states, statuses)]
    point_labels = [state if status == "point" else None for state, status in zip(states, statuses)]
    correct_run = _max_run(correct_labels, target)
    wrong_run = _max_run(wrong_labels, wrong)
    generic_run = _max_run(point_labels)
    destination = "other"
    for start in range(0, max(0, len(states) - stable_run + 1)):
        window = list(zip(states[start : start + stable_run], statuses[start : start + stable_run]))
        if all(status == "point" and state == target for state, status in window):
            destination = history
            break
        if all(status == "point" and state == wrong for state, status in window):
            destination = "B" if history == "A" else "A"
            break
    return_cycle = next(
        (
            index
            for index, (state, status) in enumerate(zip(states, statuses))
            if status == "point" and state == target
        ),
        None,
    )
    first_break = next(
        (
            index
            for index, (state, status) in enumerate(zip(states, statuses))
            if status != "point" or state != target
        ),
        None,
    )
    trace_payload = [
        (index, cycle.status, cycle.state, cycle.steps, list(cycle.mark))
        for index, cycle in enumerate(post_cycles)
    ]
    digest = hashlib.sha256(
        json.dumps(trace_payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    end_mark = np.asarray(post_cycles[-1].mark if post_cycles else start_mark, dtype=float)
    return MemoryFutureSummary(
        acquired=acquired,
        form_destination=destination,
        correct_hold_run=correct_run,
        wrong_hold_run=wrong_run,
        generic_hold_run=generic_run,
        correct_hold8=correct_run >= strict_run,
        wrong_hold8=wrong_run >= strict_run,
        generic_hold8=generic_run >= strict_run,
        returned=return_cycle is not None,
        return_cycle=return_cycle,
        first_break_cycle=first_break,
        point_cycles=sum(status == "point" for status in statuses),
        cycle_cycles=sum(status == "cycle" for status in statuses),
        nonconvergent_cycles=sum(status == "nonconvergent" for status in statuses),
        unique_adult_states=len(set(states)),
        start_mark_norm=float(np.linalg.norm(start_mark)),
        end_mark_norm=float(np.linalg.norm(end_mark)),
        trace_digest=digest,
    )


def development_result_dict(result: DevelopmentResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "final_state": int(result.final_state),
        "steps": int(result.steps),
        "cycle": list(result.cycle),
    }
