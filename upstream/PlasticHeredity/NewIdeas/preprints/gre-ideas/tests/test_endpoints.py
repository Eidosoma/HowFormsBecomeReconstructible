from __future__ import annotations

import numpy as np

from gre_sim.boolean import BooleanRulebook
from gre_sim.endpoints import (
    apply_carryover,
    donor_ring_positions,
    first_stable_destination,
    simulate_future,
    simulate_future_ensemble,
    strict_rehoming,
)
from gre_sim.types import CycleObservation


def observation(index: int, state: int, destination: str) -> CycleObservation:
    return CycleObservation(index, "point", state, 1, destination, state)


def test_discrete_carryover_extremes() -> None:
    assert apply_carryover(0b1111, 0b0011, 4, 0.0, 0.0, np.random.default_rng(1)) == 0b0011
    assert apply_carryover(0b1111, 0b0011, 4, 1.0, 0.0, np.random.default_rng(1)) == 0b1111


def test_destination_run_and_strict_window_are_separate() -> None:
    values = [
        observation(0, 0, "point:0"),
        observation(1, 1, "point:1"),
        observation(2, 3, "point:3"),
        observation(3, 3, "point:3"),
    ]
    assert first_stable_destination(values, 2) == ("point:3", 2)
    assert strict_rehoming(values, 0, 2, 2, 0.5) == (True, 1)
    active_cycle = CycleObservation(0, "cycle", 2, 2, "cycle:1.2", 0)
    assert first_stable_destination([active_cycle], 2) == ("cycle:1.2", None)


def test_stochastic_future_replays_from_same_generator_seed() -> None:
    rulebook = BooleanRulebook.constant(3, 7)
    landscape = rulebook.landscape()
    first, first_trace = simulate_future(
        rulebook,
        landscape,
        0,
        0,
        0,
        1.0,
        0.1,
        5,
        2,
        2,
        0.2,
        np.random.default_rng(22),
    )
    second, second_trace = simulate_future(
        rulebook,
        landscape,
        0,
        0,
        0,
        1.0,
        0.1,
        5,
        2,
        2,
        0.2,
        np.random.default_rng(22),
    )
    assert first == second
    assert first_trace == second_trace


def test_remaining_in_old_form_is_not_counted_as_return() -> None:
    rulebook = BooleanRulebook.constant(3, 7)
    summary, _ = simulate_future(
        rulebook,
        rulebook.landscape(),
        7,
        7,
        7,
        1.0,
        0.0,
        4,
        2,
        2,
        0.2,
        np.random.default_rng(23),
    )
    assert summary.first_break is None
    assert not summary.old_return


def _ensemble_streams(
    size: int = 2, horizon: int = 4
) -> tuple[
    tuple[np.random.Generator, ...],
    tuple[tuple[tuple[np.random.Generator, np.random.Generator], ...], ...],
]:
    rngs = tuple(np.random.default_rng(900 + index) for index in range(size))
    cycles = tuple(
        tuple(
            (
                np.random.default_rng(1000 + index * 20 + cycle * 2),
                np.random.default_rng(1001 + index * 20 + cycle * 2),
            )
            for cycle in range(horizon)
        )
        for index in range(size)
    )
    return rngs, cycles


def test_donor_ring_is_fixed_has_no_self_donors_and_preserves_multiset() -> None:
    positions = donor_ring_positions(4)
    assert positions == (1, 2, 3, 0)
    assert all(recipient != donor for recipient, donor in enumerate(positions))
    states = (3, 8, 5, 1)
    assert sorted(states[donor] for donor in positions) == sorted(states)


def test_self_and_donor_are_pathwise_equal_at_zero_carryover() -> None:
    rulebook = BooleanRulebook.from_successor(np.arange(4))
    results = []
    for mode in ("self", "donor_shuffled"):
        rngs, cycle_rngs = _ensemble_streams()
        results.append(
            simulate_future_ensemble(
                rulebook,
                rulebook.landscape(),
                0,
                3,
                3,
                0.0,
                0.5,
                4,
                2,
                2,
                0.2,
                mode,
                rngs,
                cycle_rngs,
            )
        )
    assert results[0] == results[1]


def test_full_carryover_diverges_when_donor_histories_differ() -> None:
    rulebook = BooleanRulebook.from_successor(np.arange(4))
    results = []
    for mode in ("self", "donor_shuffled"):
        rngs, cycle_rngs = _ensemble_streams()
        results.append(
            simulate_future_ensemble(
                rulebook,
                rulebook.landscape(),
                0,
                0,
                0,
                1.0,
                0.5,
                4,
                2,
                2,
                0.2,
                mode,
                rngs,
                cycle_rngs,
            )
        )
    self_traces = [[item.adult_state for item in trace] for _, trace in results[0]]
    donor_traces = [[item.adult_state for item in trace] for _, trace in results[1]]
    assert self_traces != donor_traces
