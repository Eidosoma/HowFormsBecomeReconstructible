"""Inclusive endpoints and inheritance controls for mechanism experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from .endpoints import apply_carryover
from .landscape import Landscape, canonical_cycle, normalized_hamming
from .mechanism_dynamics import MechanismRulebook
from .types import DevelopmentResult
from .wagner import gamma_multipliers


@dataclass(frozen=True)
class MechanismObservation:
    cycle_index: int
    status: str
    adult_state: int
    steps: int
    frozen_destination: str
    realized_signature: str


@dataclass(frozen=True)
class MechanismSummary:
    frozen_destination: str
    point_state_destination: str
    signature_destination: str
    competing_outcome: str
    active_capture: bool
    stable_point_capture: bool
    stable_signature_capture: bool
    strict_library: bool
    strict_state: bool
    strict_library_by_run: tuple[bool, ...]
    strict_state_by_run: tuple[bool, ...]
    max_library_run: int
    max_point_state_run: int
    max_signature_run: int
    first_break: int | None
    old_return: bool
    point_cycles: int
    cycle_cycles: int
    nonconvergent_cycles: int
    unique_adult_states: int
    donor_reassignments: int
    donor_fallbacks: int
    trace_digest: str


def classify_result(
    result: DevelopmentResult, landscape: Landscape
) -> tuple[str, str]:
    """Return frozen-library and realized-state labels without dropping outcomes."""

    if result.status == "nonconvergent":
        return "nonconvergent", "nonconvergent"
    if result.status == "point":
        label = landscape.point_label_for_exact_state(result.final_state)
        return label or "off_library", f"point:{int(result.final_state)}"
    cycle = canonical_cycle(result.cycle)
    signature = "cycle:" + ".".join(str(value) for value in cycle)
    for attractor in landscape.attractors:
        if attractor.states == cycle:
            return attractor.label, signature
    return "noise_specific_cycle", signature


def _first_repeated_label(
    observations: list[MechanismObservation],
    labels: list[str | None],
    required: int,
    prefix: str | None = None,
    terminal_fallback: bool = False,
) -> str:
    current: str | None = None
    count = 0
    for label in labels:
        valid = label is not None and (prefix is None or label.startswith(prefix))
        if not valid:
            current = None
            count = 0
            continue
        if label == current:
            count += 1
        else:
            current = label
            count = 1
        if count >= required:
            return str(label)
    if terminal_fallback and observations:
        terminal = observations[-1].frozen_destination
        if terminal in {
            "off_library",
            "noise_specific_cycle",
            "nonconvergent",
        } or terminal.startswith("cycle:"):
            return terminal
    return "no_stable_destination"


def _maximum_run(labels: list[str | None], prefix: str | None = None) -> int:
    maximum = 0
    current: str | None = None
    count = 0
    for label in labels:
        valid = label is not None and (prefix is None or label.startswith(prefix))
        if not valid:
            current = None
            count = 0
            continue
        if label == current:
            count += 1
        else:
            current = label
            count = 1
        maximum = max(maximum, count)
    return maximum


def _first_break(
    observations: list[MechanismObservation], old_state: int
) -> int | None:
    previous = int(old_state)
    for observation in observations:
        if observation.status != "point" or observation.adult_state != previous:
            return observation.cycle_index
        previous = observation.adult_state
    return None


def _strict_for_run(
    observations: list[MechanismObservation],
    old_state: int,
    genes: int,
    first_break: int | None,
    required: int,
    minimum_old_distance: float,
    library_only: bool,
) -> bool:
    if first_break is None:
        return False
    for start in range(first_break + 1, len(observations) - required + 1):
        window = observations[start : start + required]
        if any(item.status != "point" for item in window):
            continue
        if library_only:
            label = window[0].frozen_destination
            if not label.startswith("point:") or any(
                item.frozen_destination != label for item in window
            ):
                continue
        else:
            state = window[0].adult_state
            if any(item.adult_state != state for item in window):
                continue
        if any(
            normalized_hamming(item.adult_state, old_state, genes)
            < minimum_old_distance
            for item in window
        ):
            continue
        return True
    return False


def summarize_mechanism_future(
    observations: tuple[MechanismObservation, ...] | list[MechanismObservation],
    old_state: int,
    genes: int,
    stable_destination_run: int,
    strict_run: int,
    minimum_old_distance: float,
    donor_reassignments: int = 0,
    donor_fallbacks: int = 0,
) -> MechanismSummary:
    values = list(observations)
    frozen_labels = [item.frozen_destination for item in values]
    point_labels = [
        f"state:{item.adult_state}" if item.status == "point" else None
        for item in values
    ]
    signature_labels = [
        item.realized_signature if item.status != "nonconvergent" else None
        for item in values
    ]
    frozen = _first_repeated_label(
        values, frozen_labels, stable_destination_run, "point:", True
    )
    point_state = _first_repeated_label(values, point_labels, stable_destination_run)
    signature = _first_repeated_label(
        values, signature_labels, stable_destination_run
    )
    first_break = _first_break(values, old_state)
    library_curve = tuple(
        _strict_for_run(
            values,
            old_state,
            genes,
            first_break,
            run,
            minimum_old_distance,
            True,
        )
        for run in range(1, 13)
    )
    state_curve = tuple(
        _strict_for_run(
            values,
            old_state,
            genes,
            first_break,
            run,
            minimum_old_distance,
            False,
        )
        for run in range(1, 13)
    )
    if frozen.startswith("point:"):
        competing = "recognized_point"
    elif frozen.startswith("cycle:"):
        competing = "recognized_cycle"
    elif point_state.startswith("state:"):
        competing = "off_library_point"
    elif signature.startswith("cycle:"):
        competing = "noise_specific_cycle"
    elif values:
        terminal = values[-1]
        if terminal.status == "point" and terminal.frozen_destination == "off_library":
            competing = "off_library_point"
        elif terminal.status == "cycle" and terminal.frozen_destination == "noise_specific_cycle":
            competing = "noise_specific_cycle"
        elif terminal.status == "nonconvergent":
            competing = "nonconvergent"
        else:
            competing = "no_stable_destination"
    else:
        competing = "no_stable_destination"
    if first_break is None:
        old_return = False
    else:
        old_return = any(
            item.cycle_index > first_break
            and item.status == "point"
            and item.adult_state == old_state
            for item in values
        )
    trace_value = [
        (
            item.cycle_index,
            item.status,
            item.adult_state,
            item.steps,
            item.frozen_destination,
            item.realized_signature,
        )
        for item in values
    ]
    digest = hashlib.sha256(
        json.dumps(trace_value, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return MechanismSummary(
        frozen_destination=frozen,
        point_state_destination=point_state,
        signature_destination=signature,
        competing_outcome=competing,
        active_capture=frozen.startswith("point:") or frozen.startswith("cycle:"),
        stable_point_capture=point_state.startswith("state:"),
        stable_signature_capture=signature.startswith(("point:", "cycle:")),
        strict_library=library_curve[strict_run - 1],
        strict_state=state_curve[strict_run - 1],
        strict_library_by_run=library_curve,
        strict_state_by_run=state_curve,
        max_library_run=_maximum_run(frozen_labels, "point:"),
        max_point_state_run=_maximum_run(point_labels),
        max_signature_run=_maximum_run(signature_labels),
        first_break=first_break,
        old_return=old_return,
        point_cycles=sum(item.status == "point" for item in values),
        cycle_cycles=sum(item.status == "cycle" for item in values),
        nonconvergent_cycles=sum(item.status == "nonconvergent" for item in values),
        unique_adult_states=len({item.adult_state for item in values}),
        donor_reassignments=donor_reassignments,
        donor_fallbacks=donor_fallbacks,
        trace_digest=digest,
    )


def donor_sources(
    mode: str,
    states: tuple[int, ...],
    destinations: tuple[str, ...],
) -> tuple[tuple[int, ...], tuple[bool, ...]]:
    """Choose synchronous donor indices and flag recipients that fell back."""

    size = len(states)
    if size < 2 and mode != "self":
        raise ValueError("donor inheritance needs at least two futures")
    if mode == "self":
        return tuple(range(size)), (False,) * size
    if mode == "donor_shuffled":
        return tuple((index + 1) % size for index in range(size)), (False,) * size
    keys: tuple[object, ...]
    if mode == "destination_matched_donor":
        keys = destinations
    elif mode == "exact_state_donor":
        keys = states
    else:
        raise ValueError(f"unknown inheritance mode: {mode}")
    groups: dict[object, list[int]] = {}
    for index, key in enumerate(keys):
        groups.setdefault(key, []).append(index)
    donors = list(range(size))
    fallbacks = [False] * size
    for members in groups.values():
        if len(members) == 1:
            index = members[0]
            donors[index] = (index + 1) % size
            fallbacks[index] = True
            continue
        for position, index in enumerate(members):
            donors[index] = members[(position + 1) % len(members)]
    return tuple(donors), tuple(fallbacks)


def simulate_mechanism_ensemble(
    rulebook: MechanismRulebook,
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
    cycle_rngs: tuple[
        tuple[tuple[np.random.Generator, np.random.Generator], ...], ...
    ],
    gamma_variance: float,
    wagner_max_sweeps: int,
) -> list[tuple[MechanismSummary, tuple[MechanismObservation, ...]]]:
    """Advance one A/B half synchronously under a registered donor rule."""

    size = len(cycle_rngs)
    if size < 1 or any(len(streams) != horizon for streams in cycle_rngs):
        raise ValueError("invalid mechanism cycle streams")
    previous = [int(previous_state)] * size
    destinations = [f"initial:{previous_state}"] * size
    traces: list[list[MechanismObservation]] = [[] for _ in range(size)]
    reassignment_counts = [0] * size
    fallback_counts = [0] * size
    for cycle_index in range(horizon):
        donors, fallbacks = donor_sources(
            inheritance_mode, tuple(previous), tuple(destinations)
        )
        next_states: list[int] = []
        next_destinations: list[str] = []
        for recipient in range(size):
            donor = donors[recipient]
            if donor != recipient:
                reassignment_counts[recipient] += 1
            if fallbacks[recipient]:
                fallback_counts[recipient] += 1
            carry_rng, dynamics_rng = cycle_rngs[recipient][cycle_index]
            initial = apply_carryover(
                previous[donor],
                base_state,
                rulebook.genes,
                carryover,
                flip_probability,
                carry_rng,
            )
            multipliers = None
            if rulebook.variant.startswith("wagner_") and rulebook.variant != "wagner_compiled":
                multipliers = gamma_multipliers(
                    rulebook.genes, gamma_variance, dynamics_rng
                )
            result = rulebook.develop(initial, multipliers, wagner_max_sweeps)
            frozen, signature = classify_result(result, landscape)
            observation = MechanismObservation(
                cycle_index,
                result.status,
                int(result.final_state),
                int(result.steps),
                frozen,
                signature,
            )
            traces[recipient].append(observation)
            next_states.append(int(result.final_state))
            next_destinations.append(frozen)
        previous = next_states
        destinations = next_destinations
    return [
        (
            summarize_mechanism_future(
                tuple(trace),
                old_state,
                rulebook.genes,
                stable_destination_run,
                strict_run,
                minimum_old_distance,
                reassignment_counts[index],
                fallback_counts[index],
            ),
            tuple(trace),
        )
        for index, trace in enumerate(traces)
    ]
