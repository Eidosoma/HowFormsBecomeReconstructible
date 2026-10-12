"""Immutable contracts for the Wagner plastic-heredity evidence ladder."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from .plastic_memory_config import (
    MEMORY_CARRIERS,
    MEMORY_CHALLENGES,
    CueDose,
    MarkSetting,
    MemoryCondition,
    MemoryModelSpec,
    MemorySourceSpec,
    PlasticMemorySpec,
)
from .wagner_rescue_config import CueIntervention


WAGNER_HEREDITY_PROTOCOL_FORMAT = "gre-wagner-heredity-study-v1"
WAGNER_HEREDITY_REGISTRATION_FORMAT = "gre-wagner-heredity-registration-v1"
WAGNER_HEREDITY_RAW_FORMAT = "gre-wagner-heredity-futures-v1"
WAGNER_HEREDITY_ANALYSIS_FORMAT = "gre-wagner-heredity-analysis-v1"

HEREDITY_TIERS = ("hard", "soft", "noisy", "boundary", "fixture")


@dataclass(frozen=True)
class HeredityWriterSpec:
    """One temporary induction policy and its post-release noise regime."""

    name: str
    tier: str
    intervention: CueIntervention
    gamma_variance: float
    primary: bool = True
    ceiling_writer: str | None = None

    def validate(self) -> None:
        if not self.name:
            raise ValueError("heredity writer name cannot be empty")
        if self.tier not in HEREDITY_TIERS:
            raise ValueError(f"unknown heredity tier: {self.tier}")
        self.intervention.validate()
        if self.intervention.mode in {"no_cue", "target_injection"}:
            raise ValueError("heredity writers must use a temporary active cue")
        if not isfinite(self.gamma_variance) or self.gamma_variance < 0.0:
            raise ValueError("heredity gamma variance must be nonnegative")


@dataclass(frozen=True)
class HeredityCondition:
    """A compact registered Cartesian block for one writer."""

    name: str
    writer: str
    mark_settings: tuple[str, ...]
    carrier_arms: tuple[str, ...]
    descendant_ages: tuple[int, ...]
    challenges: tuple[str, ...]
    futures_per_cell: int

    def validate(self) -> None:
        if not self.name or not self.writer:
            raise ValueError("heredity condition names cannot be empty")
        if not self.mark_settings:
            raise ValueError("heredity condition requires mark settings")
        if not self.carrier_arms or not set(self.carrier_arms).issubset(
            MEMORY_CARRIERS
        ):
            raise ValueError(f"unknown heredity carrier: {self.carrier_arms}")
        if not self.descendant_ages or any(age < 0 for age in self.descendant_ages):
            raise ValueError("heredity descendant ages must be nonnegative")
        if not self.challenges or not set(self.challenges).issubset(
            MEMORY_CHALLENGES
        ):
            raise ValueError(f"unknown heredity challenge: {self.challenges}")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("heredity futures per cell must be even and at least four")


@dataclass(frozen=True)
class WagnerHereditySpec:
    """Complete immutable contract for one Wagner heredity phase."""

    cohort_id: str
    phase: str
    master_seed: str
    parent_candidate_digest: str
    genes: int
    source_count: int
    writers: tuple[HeredityWriterSpec, ...]
    mark_settings: tuple[MarkSetting, ...]
    conditions: tuple[HeredityCondition, ...]
    protocol_format: str = WAGNER_HEREDITY_PROTOCOL_FORMAT
    midpoint_count: int = 2
    horizon: int = 32
    stable_run: int = 3
    strict_run: int = 8
    expression_flip_probability: float = 0.05
    expression_carryover: float = 1.0
    neutral_damage_fraction: float = 0.20
    minimum_basin_fraction: float = 0.05
    minimum_form_distance: float = 0.40
    maximum_source_proposals: int = 500_000
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if self.protocol_format != WAGNER_HEREDITY_PROTOCOL_FORMAT:
            raise ValueError(f"unsupported Wagner heredity protocol: {self.protocol_format}")
        if not self.cohort_id or not self.phase:
            raise ValueError("heredity cohort and phase cannot be empty")
        if len(self.master_seed) < 32 or len(self.parent_candidate_digest) != 64:
            raise ValueError("heredity identity digests are malformed")
        if not 2 <= self.genes <= 16 or self.source_count < 1:
            raise ValueError("invalid heredity source dimensions")
        if self.midpoint_count not in {1, 2}:
            raise ValueError("heredity midpoint count must be one or two")
        if self.horizon < max(12, self.stable_run, self.strict_run):
            raise ValueError("heredity horizon is too short")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid heredity expression-flip probability")
        if not 0.0 <= self.expression_carryover <= 1.0:
            raise ValueError("invalid heredity expression carryover")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("invalid heredity damage fraction")
        if not 0.0 <= self.minimum_basin_fraction <= 1.0:
            raise ValueError("invalid heredity basin threshold")
        if not 0.0 <= self.minimum_form_distance <= 1.0:
            raise ValueError("invalid heredity form distance")
        if self.maximum_source_proposals < 1 or self.wagner_max_sweeps < 1:
            raise ValueError("invalid heredity execution limits")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid heredity interval configuration")
        if not self.writers or not self.mark_settings or not self.conditions:
            raise ValueError("heredity phase requires writers, marks, and conditions")
        for writer in self.writers:
            writer.validate()
        writer_names = [writer.name for writer in self.writers]
        if len(writer_names) != len(set(writer_names)):
            raise ValueError("heredity writer names must be unique")
        for writer in self.writers:
            if writer.ceiling_writer is not None and writer.ceiling_writer not in writer_names:
                raise ValueError(f"writer {writer.name} references an unknown ceiling")
        for mark in self.mark_settings:
            mark.validate()
        mark_names = [mark.name for mark in self.mark_settings]
        if len(mark_names) != len(set(mark_names)):
            raise ValueError("heredity mark names must be unique")
        for condition in self.conditions:
            condition.validate()
            if condition.writer not in writer_names:
                raise ValueError(f"condition {condition.name} references an unknown writer")
            if not set(condition.mark_settings).issubset(mark_names):
                raise ValueError(f"condition {condition.name} references an unknown mark")
        condition_names = [condition.name for condition in self.conditions]
        if len(condition_names) != len(set(condition_names)):
            raise ValueError("heredity condition names must be unique")

    def writer(self, name: str) -> HeredityWriterSpec:
        return next(writer for writer in self.writers if writer.name == name)

    def mark(self, name: str) -> MarkSetting:
        return next(mark for mark in self.mark_settings if mark.name == name)

    def condition(self, name: str) -> HeredityCondition:
        return next(condition for condition in self.conditions if condition.name == name)

    def memory_spec(self) -> PlasticMemorySpec:
        """Return a metric-compatible view without changing legacy protocols."""

        models = tuple(
            MemoryModelSpec(
                writer.name,
                "wagner_n%d" % self.genes,
                "wagner_sequential",
                writer.gamma_variance,
                writer.primary,
            )
            for writer in self.writers
        )
        conditions = tuple(
            MemoryCondition(
                condition.name,
                condition.writer,
                CueDose(
                    self.writer(condition.writer).intervention.fraction,
                    self.writer(condition.writer).intervention.dwell,
                ),
                condition.mark_settings,
                condition.carrier_arms,
                condition.descendant_ages,
                condition.challenges,
                condition.futures_per_cell,
            )
            for condition in self.conditions
        )
        return PlasticMemorySpec(
            cohort_id=self.cohort_id,
            phase=self.phase,
            master_seed=self.master_seed,
            sources=(
                MemorySourceSpec(
                    "wagner_n%d" % self.genes,
                    "wagner",
                    self.genes,
                    self.source_count,
                    "wagner_sequential",
                ),
            ),
            models=models,
            mark_settings=self.mark_settings,
            conditions=conditions,
            midpoint_count=self.midpoint_count,
            horizon=self.horizon,
            stable_run=self.stable_run,
            strict_run=self.strict_run,
            expression_flip_probability=self.expression_flip_probability,
            expression_carryover=self.expression_carryover,
            neutral_damage_fraction=self.neutral_damage_fraction,
            minimum_basin_fraction=self.minimum_basin_fraction,
            minimum_form_distance=self.minimum_form_distance,
            maximum_source_proposals=self.maximum_source_proposals,
            wagner_max_sweeps=self.wagner_max_sweeps,
            bootstrap_repetitions=self.bootstrap_repetitions,
            interval_level=self.interval_level,
            exploratory=self.exploratory,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WagnerHereditySpec":
        fields = dict(value)
        writers = []
        for item in fields["writers"]:
            if isinstance(item, HeredityWriterSpec):
                writers.append(item)
                continue
            writer = dict(item)
            intervention = writer["intervention"]
            writer["intervention"] = (
                intervention
                if isinstance(intervention, CueIntervention)
                else CueIntervention(**intervention)
            )
            writers.append(HeredityWriterSpec(**writer))
        fields["writers"] = tuple(writers)
        fields["mark_settings"] = tuple(
            item if isinstance(item, MarkSetting) else MarkSetting(**item)
            for item in fields["mark_settings"]
        )
        fields["conditions"] = tuple(
            item
            if isinstance(item, HeredityCondition)
            else HeredityCondition(
                **{
                    **item,
                    "mark_settings": tuple(item["mark_settings"]),
                    "carrier_arms": tuple(item["carrier_arms"]),
                    "descendant_ages": tuple(item["descendant_ages"]),
                    "challenges": tuple(item["challenges"]),
                }
            )
            for item in fields["conditions"]
        )
        result = cls(**fields)
        result.validate()
        return result
