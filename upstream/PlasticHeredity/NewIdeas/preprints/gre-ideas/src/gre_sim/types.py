"""Shared immutable scientific data structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DevelopmentStatus = Literal["point", "cycle", "nonconvergent"]


@dataclass(frozen=True)
class DevelopmentResult:
    """The complete discrete outcome of one developmental relaxation."""

    status: DevelopmentStatus
    final_state: int
    steps: int
    cycle: tuple[int, ...] = ()

    @property
    def stable(self) -> bool:
        return self.status == "point"


@dataclass(frozen=True)
class CycleObservation:
    """One adult observation in a repeated developmental future."""

    cycle_index: int
    status: DevelopmentStatus
    adult_state: int
    steps: int
    destination: str
    active_attractor: int | None


@dataclass(frozen=True)
class FutureSummary:
    """Compact persisted result for one stochastic future."""

    destination: str
    strict_event: bool
    first_break: int | None
    stable_destination_cycle: int | None
    active_capture: bool
    old_return: bool
    point_cycles: int
    cycle_cycles: int
    nonconvergent_cycles: int
    trace_digest: str

