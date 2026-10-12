"""Immutable contracts for the plastic-memory causal campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


PLASTIC_MEMORY_PROTOCOL_FORMAT = "gre-plastic-memory-study-v1"
PLASTIC_MEMORY_REGISTRATION_FORMAT = "gre-plastic-memory-registration-v1"
PLASTIC_MEMORY_RAW_FORMAT = "gre-plastic-memory-futures-v1"
PLASTIC_MEMORY_ANALYSIS_FORMAT = "gre-plastic-memory-analysis-v1"

MEMORY_VARIANTS = (
    "boolean_sync",
    "boolean_sequential",
    "wagner_sequential",
    "wagner_synchronous",
)
MEMORY_CHALLENGES = ("release_only", "neutral_damage", "forced_break")
MEMORY_CARRIERS = (
    "self_continuation",
    "state_transplant",
    "mark_transplant",
    "state_and_mark_transplant",
    "reset_both",
    "destination_matched_donor",
    "descriptor_matched_null",
    "state_pattern_shuffle",
    "mark_pattern_shuffle",
    "write_disabled",
    "mark_inert",
    "mark_ablation",
    "mark_random_ablation",
    "mark_rescue",
)


@dataclass(frozen=True)
class MemorySourceSpec:
    """One independently sampled source-rulebook collection."""

    name: str
    engine: str
    genes: int
    count: int
    eligibility_variant: str

    def validate(self) -> None:
        if not self.name:
            raise ValueError("memory source name cannot be empty")
        if self.engine not in {"boolean", "wagner"}:
            raise ValueError(f"unknown memory source engine: {self.engine}")
        if not 2 <= self.genes <= 16:
            raise ValueError("memory source genes must lie in [2, 16]")
        if self.count < 1:
            raise ValueError("memory source count must be positive")
        if self.eligibility_variant not in MEMORY_VARIANTS:
            raise ValueError("unknown memory eligibility variant")
        if not self.eligibility_variant.startswith(self.engine):
            raise ValueError("source engine and eligibility variant disagree")


@dataclass(frozen=True)
class MemoryModelSpec:
    """One dynamical view of a source-rulebook collection."""

    name: str
    source_set: str
    variant: str
    gamma_variance: float = 0.0
    primary: bool = True

    def validate(self) -> None:
        if not self.name or not self.source_set:
            raise ValueError("memory model names cannot be empty")
        if self.variant not in MEMORY_VARIANTS:
            raise ValueError(f"unknown memory model variant: {self.variant}")
        if not isfinite(self.gamma_variance) or self.gamma_variance < 0.0:
            raise ValueError("memory model gamma variance must be nonnegative")
        if self.variant.startswith("boolean") and self.gamma_variance != 0.0:
            raise ValueError("Boolean memory models do not use gamma noise")


@dataclass(frozen=True)
class CueDose:
    """Fraction of target-discriminating nodes clamped for a dwell duration."""

    fraction: float
    dwell: int

    @property
    def name(self) -> str:
        return f"clamp-{self.fraction:g}.dwell-{self.dwell}"

    def validate(self) -> None:
        if not 0.0 < self.fraction <= 1.0:
            raise ValueError("cue clamp fraction must lie in (0, 1]")
        if self.dwell < 1:
            raise ValueError("cue dwell must be positive")


@dataclass(frozen=True)
class MarkSetting:
    """One explicit slow-mark mechanism setting."""

    name: str
    half_life: int
    coupling: float

    @property
    def rho(self) -> float:
        if self.half_life == 0:
            return 0.0
        return float(2.0 ** (-1.0 / self.half_life))

    @property
    def active(self) -> bool:
        return self.half_life > 0 and self.coupling > 0.0

    def validate(self) -> None:
        if not self.name:
            raise ValueError("mark-setting name cannot be empty")
        if self.half_life < 0:
            raise ValueError("mark half-life cannot be negative")
        if not 0.0 <= self.coupling <= 1.0:
            raise ValueError("mark coupling must lie in [0, 1]")
        if (self.half_life == 0) != (self.coupling == 0.0):
            raise ValueError("inactive mark must have zero half-life and coupling")


@dataclass(frozen=True)
class MemoryCondition:
    """A compact registered Cartesian block."""

    name: str
    model: str
    cue: CueDose
    mark_settings: tuple[str, ...]
    carrier_arms: tuple[str, ...]
    washout_ages: tuple[int, ...]
    challenges: tuple[str, ...]
    futures_per_cell: int

    def validate(self) -> None:
        if not self.name or not self.model:
            raise ValueError("memory condition names cannot be empty")
        self.cue.validate()
        if not self.mark_settings:
            raise ValueError("memory condition needs mark settings")
        if not self.carrier_arms or not set(self.carrier_arms).issubset(MEMORY_CARRIERS):
            raise ValueError(f"unknown memory carrier arm: {self.carrier_arms}")
        if not self.washout_ages or any(age < 0 for age in self.washout_ages):
            raise ValueError("washout ages must be nonnegative")
        if not self.challenges or not set(self.challenges).issubset(MEMORY_CHALLENGES):
            raise ValueError(f"unknown memory challenge: {self.challenges}")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("memory futures per cell must be even and at least four")


@dataclass(frozen=True)
class PlasticMemorySpec:
    """Complete immutable contract for one plastic-memory phase."""

    cohort_id: str
    phase: str
    master_seed: str
    sources: tuple[MemorySourceSpec, ...]
    models: tuple[MemoryModelSpec, ...]
    mark_settings: tuple[MarkSetting, ...]
    conditions: tuple[MemoryCondition, ...]
    protocol_format: str = PLASTIC_MEMORY_PROTOCOL_FORMAT
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
        if self.protocol_format != PLASTIC_MEMORY_PROTOCOL_FORMAT:
            raise ValueError(f"unsupported plastic-memory protocol: {self.protocol_format}")
        if not self.cohort_id or not self.phase:
            raise ValueError("memory cohort and phase cannot be empty")
        if len(self.master_seed) < 32:
            raise ValueError("memory master seed must contain at least 128 bits")
        if self.midpoint_count not in {1, 2}:
            raise ValueError("memory midpoint count must be one or two")
        if self.horizon < max(12, self.stable_run, self.strict_run):
            raise ValueError("memory horizon is too short for registered endpoints")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("expression flip probability must lie in [0, 1]")
        if not 0.0 <= self.expression_carryover <= 1.0:
            raise ValueError("expression carryover must lie in [0, 1]")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("neutral damage fraction must lie in [0, 1]")
        if not 0.0 <= self.minimum_basin_fraction <= 1.0:
            raise ValueError("minimum basin fraction must lie in [0, 1]")
        if not 0.0 <= self.minimum_form_distance <= 1.0:
            raise ValueError("minimum form distance must lie in [0, 1]")
        if self.maximum_source_proposals < 1 or self.wagner_max_sweeps < 1:
            raise ValueError("memory execution limits must be positive")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid memory interval configuration")
        if not self.sources or not self.models or not self.mark_settings or not self.conditions:
            raise ValueError("memory phase needs sources, models, marks, and conditions")
        for source in self.sources:
            source.validate()
        source_names = [source.name for source in self.sources]
        if len(source_names) != len(set(source_names)):
            raise ValueError("memory source names must be unique")
        for model in self.models:
            model.validate()
            if model.source_set not in source_names:
                raise ValueError(f"model {model.name} references an unknown source set")
            source = self.source(model.source_set)
            if not model.variant.startswith(source.engine):
                raise ValueError("memory model variant and source engine disagree")
        model_names = [model.name for model in self.models]
        if len(model_names) != len(set(model_names)):
            raise ValueError("memory model names must be unique")
        for mark in self.mark_settings:
            mark.validate()
        mark_names = [mark.name for mark in self.mark_settings]
        if len(mark_names) != len(set(mark_names)):
            raise ValueError("memory mark-setting names must be unique")
        for condition in self.conditions:
            condition.validate()
            if condition.model not in model_names:
                raise ValueError(f"condition {condition.name} references an unknown model")
            if not set(condition.mark_settings).issubset(mark_names):
                raise ValueError(f"condition {condition.name} references an unknown mark")
        condition_names = [condition.name for condition in self.conditions]
        if len(condition_names) != len(set(condition_names)):
            raise ValueError("memory condition names must be unique")

    def source(self, name: str) -> MemorySourceSpec:
        return next(value for value in self.sources if value.name == name)

    def model(self, name: str) -> MemoryModelSpec:
        return next(value for value in self.models if value.name == name)

    def mark(self, name: str) -> MarkSetting:
        return next(value for value in self.mark_settings if value.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlasticMemorySpec":
        fields = dict(value)
        fields["sources"] = tuple(
            item if isinstance(item, MemorySourceSpec) else MemorySourceSpec(**item)
            for item in fields["sources"]
        )
        fields["models"] = tuple(
            item if isinstance(item, MemoryModelSpec) else MemoryModelSpec(**item)
            for item in fields["models"]
        )
        fields["mark_settings"] = tuple(
            item if isinstance(item, MarkSetting) else MarkSetting(**item)
            for item in fields["mark_settings"]
        )
        conditions = []
        for item in fields["conditions"]:
            if isinstance(item, MemoryCondition):
                conditions.append(item)
                continue
            condition = dict(item)
            condition["cue"] = (
                condition["cue"]
                if isinstance(condition["cue"], CueDose)
                else CueDose(**condition["cue"])
            )
            for name in ("mark_settings", "carrier_arms", "washout_ages", "challenges"):
                condition[name] = tuple(condition[name])
            conditions.append(MemoryCondition(**condition))
        fields["conditions"] = tuple(conditions)
        spec = cls(**fields)
        spec.validate()
        return spec

