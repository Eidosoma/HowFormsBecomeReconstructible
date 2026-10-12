"""Frozen contracts for the exploratory Wagner PH Origin Ladder v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .local_ph_config import CopyNoiseSpec


LADDER_CAMPAIGN_FORMAT = "gre-wagner-ph-origin-ladder-campaign-v1"
LADDER_TASK_FORMAT = "gre-wagner-ph-origin-ladder-task-v1"
LADDER_RESULT_FORMAT = "gre-wagner-ph-origin-ladder-result-v1"
LADDER_ANALYSIS_FORMAT = "gre-wagner-ph-origin-ladder-analysis-v1"


@dataclass(frozen=True)
class WagnerPHLadderSpec:
    """Prospective diagnostic ladder; the confirmation seed is never used here."""

    cohort_id: str
    master_seed: str
    confirmation_seed: str
    tasks: int = 12
    futures_per_history: int = 8
    capacities: tuple[int, ...] = (1, 2, 3, 5, 10)
    bits_per_mark: tuple[int, ...] = (2, 4, 8)
    writer_rates: tuple[float, ...] = (0.0, 0.10, 0.25, 0.50, 0.952)
    reader_couplings: tuple[float, ...] = (0.0, 0.10, 0.25, 0.50, 1.0)
    coordination_capacities: tuple[int, ...] = (1, 3, 10)
    ecology_capacities: tuple[int, ...] = (1, 2, 3, 5, 10)
    ecology_persistence: tuple[float, ...] = (0.0, 0.25, 0.50, 0.75, 0.90, 1.0)
    ecology_generations: int = 16
    checkpoints: tuple[int, ...] = (0, 4, 8)
    noise: CopyNoiseSpec = CopyNoiseSpec("d095-p002", 0.95, 0.02, 0.05)
    strong_write_rate: float = 0.952
    strong_coupling: float = 1.0
    carrier_decay: float = 0.002
    carrier_hysteresis: int = 3
    coordination_bits: int = 4
    ecology_bits: int = 4
    genes: int = 10
    cue_fraction: float = 1.0
    cue_dwell: int = 1
    generation_cycles: int = 4
    horizon: int = 16
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    bootstrap_repetitions: int = 2048
    interval_level: float = 0.95
    gain_gate: float = 0.20
    gain_lower_gate: float = 0.05
    causal_gate: float = 0.10
    causal_lower_gate: float = 0.0
    ecology_gain_gate: float = 0.05
    path_drift_tolerance: float = 0.01
    maximum_workers: int = 4
    hard_wall_seconds: int = 14_400
    soft_wall_seconds: int = 13_500
    confirmation_tasks: int = 24
    confirmation_futures_per_history: int = 16
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32 or len(self.confirmation_seed) < 32:
            raise ValueError("invalid Origin Ladder identity")
        if self.master_seed == self.confirmation_seed:
            raise ValueError("exploration and confirmation seeds must be disjoint")
        if self.tasks < 1 or self.futures_per_history < 4 or self.futures_per_history % 2:
            raise ValueError("invalid Origin Ladder replication dimensions")
        allowed_capacity = {1, 2, 3, 5, 7, self.genes}
        for values in (self.capacities, self.coordination_capacities, self.ecology_capacities):
            if not values or tuple(sorted(set(values))) != values or not set(values) <= allowed_capacity:
                raise ValueError("invalid ordered carrier capacities")
        if tuple(sorted(set(self.bits_per_mark))) != self.bits_per_mark:
            raise ValueError("bit budgets must be increasing and unique")
        if not self.bits_per_mark or min(self.bits_per_mark) < 2 or max(self.bits_per_mark) > 16:
            raise ValueError("bit budgets must lie in [2, 16]")
        for values in (self.writer_rates, self.reader_couplings, self.ecology_persistence):
            if not values or tuple(sorted(set(values))) != values:
                raise ValueError("rate grids must be increasing and unique")
            if min(values) < 0.0 or max(values) > 1.0:
                raise ValueError("rate grids must lie in [0, 1]")
        if self.writer_rates[0] != 0.0 or self.reader_couplings[0] != 0.0:
            raise ValueError("coordination grids must include the inert origin")
        if self.strong_write_rate not in self.writer_rates or self.strong_coupling not in self.reader_couplings:
            raise ValueError("coordination grids must contain the strong endpoint")
        if self.ecology_persistence[0] != 0.0 or self.ecology_persistence[-1] != 1.0:
            raise ValueError("ecology grid must include always-switch and always-stay endpoints")
        if tuple(sorted(set(self.checkpoints))) != self.checkpoints or self.checkpoints[0] != 0:
            raise ValueError("checkpoints must be increasing and start at zero")
        if max(self.checkpoints) < 8 or self.ecology_generations < 2:
            raise ValueError("Origin Ladder must assay multigeneration retention")
        self.noise.validate()
        if self.genes != 10 or self.generation_cycles < 1:
            raise ValueError("Origin Ladder requires ten-gene Wagner GRNs")
        if self.horizon < max(12, self.strict_run) or self.stable_run < 1:
            raise ValueError("invalid developmental horizon")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid expression noise")
        if not 0.0 <= self.carrier_decay < 1.0 or self.carrier_hysteresis not in {1, 2, 3}:
            raise ValueError("invalid strong carrier")
        if min(self.coordination_bits, self.ecology_bits) < 2:
            raise ValueError("quantized stages require at least ternary marks")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid inference settings")
        if not 1 <= self.maximum_workers <= 4:
            raise ValueError("Origin Ladder permits at most four CPU workers")
        if not 0 < self.soft_wall_seconds < self.hard_wall_seconds <= 14_400:
            raise ValueError("initial Origin Ladder is capped at four wall-clock hours")
        if self.confirmation_tasks < self.tasks or self.confirmation_futures_per_history < self.futures_per_history:
            raise ValueError("confirmation reserve must exceed exploration")

    @property
    def capacity_cell_count(self) -> int:
        return len(self.capacities) * len(self.bits_per_mark)

    @property
    def coordination_cell_count(self) -> int:
        return (
            len(self.coordination_capacities)
            * len(self.writer_rates)
            * len(self.reader_couplings)
        )

    @property
    def ecology_cell_count(self) -> int:
        return len(self.ecology_capacities) * len(self.ecology_persistence)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WagnerPHLadderSpec":
        fields = dict(value)
        fields["noise"] = CopyNoiseSpec(**fields["noise"])
        for name in (
            "capacities",
            "bits_per_mark",
            "writer_rates",
            "reader_couplings",
            "coordination_capacities",
            "ecology_capacities",
            "ecology_persistence",
            "checkpoints",
        ):
            fields[name] = tuple(fields[name])
        result = cls(**fields)
        result.validate()
        return result

    def smoke(self) -> "WagnerPHLadderSpec":
        result = replace(
            self,
            cohort_id=f"{self.cohort_id}-smoke",
            master_seed=f"{self.master_seed[:-6]}smoke0",
            confirmation_seed=f"{self.confirmation_seed[:-6]}smoke1",
            tasks=1,
            futures_per_history=4,
            capacities=(1, 10),
            bits_per_mark=(2, 4),
            writer_rates=(0.0, 0.10, 0.952),
            reader_couplings=(0.0, 0.10, 1.0),
            coordination_capacities=(1, 10),
            ecology_capacities=(1, 10),
            ecology_persistence=(0.0, 1.0),
            ecology_generations=2,
            checkpoints=(0, 8),
            generation_cycles=2,
            horizon=12,
            strict_run=2,
            stable_run=2,
            bootstrap_repetitions=64,
            confirmation_tasks=2,
            confirmation_futures_per_history=4,
        )
        result.validate()
        return result
