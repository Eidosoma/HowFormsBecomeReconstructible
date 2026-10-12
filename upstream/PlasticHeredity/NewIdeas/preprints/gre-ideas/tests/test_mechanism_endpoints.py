from __future__ import annotations

from gre_sim.mechanism_endpoints import (
    MechanismObservation,
    donor_sources,
    summarize_mechanism_future,
)


def obs(index: int, state: int, frozen: str, signature: str | None = None):
    return MechanismObservation(
        index,
        "point",
        state,
        1,
        frozen,
        signature or f"point:{state}",
    )


def test_off_library_point_can_form_inclusive_destination() -> None:
    values = [
        obs(0, 0, "point:0"),
        obs(1, 3, "off_library"),
        obs(2, 3, "off_library"),
        obs(3, 3, "off_library"),
        obs(4, 3, "off_library"),
    ]
    summary = summarize_mechanism_future(values, 0, 2, 3, 3, 0.5)
    assert not summary.active_capture
    assert summary.point_state_destination == "state:3"
    assert summary.signature_destination == "point:3"
    assert summary.stable_point_capture
    assert summary.competing_outcome == "off_library_point"
    assert summary.strict_state
    assert not summary.strict_library


def test_all_registered_strict_run_lengths_are_computed() -> None:
    values = [obs(0, 0, "point:0")] + [obs(i, 3, "point:3") for i in range(1, 14)]
    summary = summarize_mechanism_future(values, 0, 2, 3, 8, 0.5)
    assert len(summary.strict_state_by_run) == 12
    assert all(summary.strict_state_by_run)
    assert summary.max_point_state_run == 13


def test_destination_matched_donors_preserve_groups_and_flag_singletons() -> None:
    donors, fallbacks = donor_sources(
        "destination_matched_donor",
        (1, 2, 3, 4),
        ("a", "a", "b", "c"),
    )
    assert donors[:2] == (1, 0)
    assert fallbacks == (False, False, True, True)
    assert all(donor != index for index, donor in enumerate(donors))


def test_exact_state_shuffle_is_value_invariant_without_singletons() -> None:
    states = (1, 1, 3, 3)
    donors, fallbacks = donor_sources("exact_state_donor", states, ("",) * 4)
    assert not any(fallbacks)
    assert tuple(states[index] for index in donors) == states
