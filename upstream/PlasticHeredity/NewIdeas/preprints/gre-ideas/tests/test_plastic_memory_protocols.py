from __future__ import annotations

from gre_sim.plastic_memory_config import CueDose, PlasticMemorySpec
from gre_sim.plastic_memory_protocols import confirmation_spec, discovery_spec


def _planned_futures(spec: PlasticMemorySpec) -> int:
    counts = {source.name: source.count for source in spec.sources}
    return sum(
        counts[spec.model(condition.model).source_set]
        * spec.midpoint_count
        * 2
        * len(condition.mark_settings)
        * len(condition.carrier_arms)
        * len(condition.washout_ages)
        * len(condition.challenges)
        * condition.futures_per_cell
        for condition in spec.conditions
    )


def test_registered_large_protocols_are_bounded_and_keep_primary_power() -> None:
    cues = {
        "boolean-primary": CueDose(1.0, 4),
        "wagner-primary": CueDose(1.0, 4),
    }
    marks = {model: "half-8.mu-0.5" for model in cues}
    discovery = discovery_spec(cues)
    confirmation = confirmation_spec(cues, marks)
    no_mark_confirmation = confirmation_spec(
        cues, {model: None for model in cues}
    )
    assert _planned_futures(discovery) == 7_716_864
    assert _planned_futures(no_mark_confirmation) == 4_096_000
    assert _planned_futures(confirmation) == 9_830_400
    assert all(
        condition.futures_per_cell == 128
        for condition in confirmation.conditions
        if condition.name.endswith(("state-primary", "state-recurrence", "mark-primary"))
    )
