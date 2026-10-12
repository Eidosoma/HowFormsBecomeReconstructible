"""Repeated-cycle futures, destination assignment, and strict rehoming."""

from __future__ import annotations

import hashlib
import json

import numpy as np

from .boolean import BooleanRulebook
from .engines import Rulebook
from .landscape import Landscape, canonical_cycle, normalized_hamming
from .types import CycleObservation, DevelopmentResult, FutureSummary
from .wagner import WagnerRulebook, gamma_multipliers


GENERIC_DESTINATIONS = (
    "off_library",
    "noise_specific_cycle",
    "nonconvergent",
    "no_stable_destination",
)


def apply_carryover(
    previous_state: int,
    base_state: int,
    genes: int,
    carryover: float,
    flip_probability: float,
    rng: np.random.Generator,
) -> int:
    if not 0 <= carryover <= 1:
        raise ValueError("carryover must lie in [0, 1]")
    if not 0 <= flip_probability <= 1:
        raise ValueError("flip_probability must lie in [0, 1]")
    choices = rng.random(genes) < carryover
    flips = rng.random(genes) < flip_probability
    return apply_carryover_arrays(previous_state, base_state, genes, choices, flips)


def apply_carryover_arrays(
    previous_state: int,
    base_state: int,
    genes: int,
    choices: np.ndarray,
    flips: np.ndarray,
) -> int:
    """Apply pre-generated carryover choices and flips for pathwise fixtures."""

    choices = np.asarray(choices, dtype=bool)
    flips = np.asarray(flips, dtype=bool)
    if choices.shape != (genes,) or flips.shape != (genes,):
        raise ValueError("carryover noise arrays must contain one value per gene")
    result = 0
    for gene in range(genes):
        source = previous_state if choices[gene] else base_state
        value = (source >> gene) & 1
        if flips[gene]:
            value = 1 - value
        result |= value << gene
    return result


def classify_development(result: DevelopmentResult, landscape: Landscape) -> tuple[str, int | None]:
    if result.status == "nonconvergent":
        return "nonconvergent", None
    if result.status == "point":
        label = landscape.point_label_for_exact_state(result.final_state)
        if label is None:
            return "off_library", None
        return label, int(landscape.attractor_index[result.final_state])
    cycle = canonical_cycle(result.cycle)
    for attractor in landscape.attractors:
        if attractor.states == cycle:
            return attractor.label, attractor.index
    return "noise_specific_cycle", None


def first_stable_destination(
    observations: list[CycleObservation], required_run: int
) -> tuple[str, int | None]:
    if required_run < 1:
        raise ValueError("required_run must be positive")
    run_label: str | None = None
    run_start = 0
    run_length = 0
    for observation in observations:
        label = observation.destination
        if label.startswith("point:"):
            if label == run_label:
                run_length += 1
            else:
                run_label = label
                run_start = observation.cycle_index
                run_length = 1
            if run_length >= required_run:
                return label, run_start
        else:
            run_label = None
            run_length = 0
    if observations:
        terminal = observations[-1].destination
        if terminal in GENERIC_DESTINATIONS or terminal.startswith("cycle:"):
            return terminal, None
    return "no_stable_destination", None


def strict_rehoming(
    observations: list[CycleObservation],
    old_state: int,
    genes: int,
    required_run: int,
    minimum_old_distance: float,
) -> tuple[bool, int | None]:
    first_break: int | None = None
    previous = old_state
    for observation in observations:
        if observation.status != "point" or observation.adult_state != previous:
            first_break = observation.cycle_index
            break
        previous = observation.adult_state
    if first_break is None:
        return False, None

    for start in range(first_break + 1, len(observations) - required_run + 1):
        window = observations[start : start + required_run]
        label = window[0].destination
        if not label.startswith("point:"):
            continue
        if any(observation.destination != label for observation in window):
            continue
        if any(observation.status != "point" for observation in window):
            continue
        if any(
            normalized_hamming(observation.adult_state, old_state, genes)
            < minimum_old_distance
            for observation in window
        ):
            continue
        return True, first_break
    return False, first_break


def simulate_development_cycle(
    rulebook: Rulebook,
    landscape: Landscape,
    base_state: int,
    inherited_state: int,
    carryover: float,
    flip_probability: float,
    cycle_index: int,
    carryover_rng: np.random.Generator,
    dynamics_rng: np.random.Generator,
    wagner_variance: float = 0.0,
    wagner_max_sweeps: int = 100,
) -> CycleObservation:
    """Develop one cycle from an explicitly supplied inherited adult state."""

    initial = apply_carryover(
        inherited_state,
        base_state,
        rulebook.genes,
        carryover,
        flip_probability,
        carryover_rng,
    )
    if isinstance(rulebook, WagnerRulebook):
        multipliers = gamma_multipliers(rulebook.genes, wagner_variance, dynamics_rng)
        result = rulebook.develop(initial, multipliers, wagner_max_sweeps)
    elif isinstance(rulebook, BooleanRulebook):
        result = rulebook.develop(initial)
    else:  # pragma: no cover - protected by the Rulebook union.
        raise TypeError(type(rulebook))
    destination, attractor_index = classify_development(result, landscape)
    return CycleObservation(
        cycle_index=cycle_index,
        status=result.status,
        adult_state=result.final_state,
        steps=result.steps,
        destination=destination,
        active_attractor=attractor_index,
    )


def summarize_future(
    observations: list[CycleObservation] | tuple[CycleObservation, ...],
    old_state: int,
    genes: int,
    stable_destination_run: int,
    strict_run: int,
    minimum_old_distance: float,
) -> FutureSummary:
    """Reduce a complete cycle trace to the persisted endpoint summary."""

    values = list(observations)
    destination, stable_cycle = first_stable_destination(
        values, stable_destination_run
    )
    strict, first_break = strict_rehoming(
        values,
        old_state,
        genes,
        strict_run,
        minimum_old_distance,
    )
    if first_break is None:
        old_return = False
    else:
        old_return = any(
            observation.cycle_index > first_break
            and observation.status == "point"
            and observation.adult_state == old_state
            for observation in values
        )
    trace_value = [
        (
            observation.cycle_index,
            observation.status,
            observation.adult_state,
            observation.steps,
            observation.destination,
        )
        for observation in values
    ]
    trace_digest = hashlib.sha256(
        json.dumps(trace_value, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FutureSummary(
        destination=destination,
        strict_event=strict,
        first_break=first_break,
        stable_destination_cycle=stable_cycle,
        active_capture=destination.startswith("point:")
        or destination.startswith("cycle:"),
        old_return=old_return,
        point_cycles=sum(observation.status == "point" for observation in values),
        cycle_cycles=sum(observation.status == "cycle" for observation in values),
        nonconvergent_cycles=sum(
            observation.status == "nonconvergent" for observation in values
        ),
        trace_digest=trace_digest,
    )


def simulate_future(
    rulebook: Rulebook,
    landscape: Landscape,
    base_state: int,
    previous_state: int,
    old_state: int,
    carryover: float,
    flip_probability: float,
    horizon: int,
    stable_destination_run: int,
    strict_run: int,
    minimum_old_distance: float,
    rng: np.random.Generator,
    wagner_variance: float = 0.0,
    wagner_max_sweeps: int = 100,
    cycle_rngs: tuple[tuple[np.random.Generator, np.random.Generator], ...] | None = None,
) -> tuple[FutureSummary, tuple[CycleObservation, ...]]:
    if cycle_rngs is not None and len(cycle_rngs) != horizon:
        raise ValueError("cycle_rngs must contain carryover and dynamics streams per cycle")
    observations: list[CycleObservation] = []
    previous = int(previous_state)
    for cycle_index in range(horizon):
        if cycle_rngs is None:
            carryover_rng = rng
            dynamics_rng = rng
        else:
            carryover_rng, dynamics_rng = cycle_rngs[cycle_index]
        observation = simulate_development_cycle(
            rulebook,
            landscape,
            base_state,
            previous,
            carryover,
            flip_probability,
            cycle_index,
            carryover_rng,
            dynamics_rng,
            wagner_variance,
            wagner_max_sweeps,
        )
        observations.append(observation)
        previous = observation.adult_state

    summary = summarize_future(
        observations,
        old_state,
        rulebook.genes,
        stable_destination_run,
        strict_run,
        minimum_old_distance,
    )
    return summary, tuple(observations)


def simulate_future_ensemble(
    rulebook: Rulebook,
    landscape: Landscape,
    base_state: int,
    previous_state: int,
    old_state: int,
    carryover: float,
    flip_probability: float,
    horizon: int,
    stable_destination_run: int,
    strict_run: int,
    minimum_old_distance: float,
    inheritance_mode: str,
    rngs: tuple[np.random.Generator, ...],
    cycle_rngs: tuple[
        tuple[tuple[np.random.Generator, np.random.Generator], ...], ...
    ],
    wagner_variance: float = 0.0,
    wagner_max_sweeps: int = 100,
) -> tuple[tuple[FutureSummary, tuple[CycleObservation, ...]], ...]:
    """Advance a frozen half synchronously under self or cyclic-donor inheritance."""

    size = len(rngs)
    if size == 0 or len(cycle_rngs) != size:
        raise ValueError("ensemble RNGs must contain one entry per future")
    if any(len(streams) != horizon for streams in cycle_rngs):
        raise ValueError("cycle_rngs must contain all cycles for every future")
    if inheritance_mode not in {"self", "donor_shuffled"}:
        raise ValueError(f"unknown inheritance mode: {inheritance_mode}")
    if inheritance_mode == "donor_shuffled" and size < 2:
        raise ValueError("donor-shuffled halves require at least two futures")

    donor_positions = donor_ring_positions(size)
    observations: list[list[CycleObservation]] = [[] for _ in range(size)]
    previous = [int(previous_state)] * size
    for cycle_index in range(horizon):
        snapshot = tuple(previous)
        next_adults: list[int] = []
        for recipient in range(size):
            if inheritance_mode == "donor_shuffled" and cycle_index > 0:
                inherited = snapshot[donor_positions[recipient]]
            else:
                inherited = snapshot[recipient]
            carryover_rng, dynamics_rng = cycle_rngs[recipient][cycle_index]
            observation = simulate_development_cycle(
                rulebook,
                landscape,
                base_state,
                inherited,
                carryover,
                flip_probability,
                cycle_index,
                carryover_rng,
                dynamics_rng,
                wagner_variance,
                wagner_max_sweeps,
            )
            observations[recipient].append(observation)
            next_adults.append(observation.adult_state)
        previous = next_adults

    return tuple(
        (
            summarize_future(
                values,
                old_state,
                rulebook.genes,
                stable_destination_run,
                strict_run,
                minimum_old_distance,
            ),
            tuple(values),
        )
        for values in observations
    )


def donor_ring_positions(size: int) -> tuple[int, ...]:
    """Map each recipient position to the next donor inside one frozen half."""

    if size < 2:
        raise ValueError("a donor ring requires at least two futures")
    return tuple((recipient + 1) % size for recipient in range(size))
