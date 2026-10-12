"""Immutable contracts for the exploratory Wagner induction-rescue campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


WAGNER_RESCUE_PROTOCOL_FORMAT = "gre-wagner-induction-rescue-v1"
WAGNER_RESCUE_REGISTRATION_FORMAT = "gre-wagner-rescue-registration-v1"
WAGNER_RESCUE_RAW_FORMAT = "gre-wagner-rescue-futures-v1"
WAGNER_RESCUE_ANALYSIS_FORMAT = "gre-wagner-rescue-analysis-v1"

RESCUE_VARIANTS = ("wagner_sequential", "wagner_synchronous")
RESCUE_CUE_MODES = (
    "initialization",
    "persistent_hard",
    "target_field",
    "no_cue",
    "target_injection",
)
RESCUE_ROLES = ("candidate", "baseline", "no_cue", "target_injection")


@dataclass(frozen=True)
class RescueModelSpec:
    """One Wagner update/noise regime."""

    name: str
    variant: str
    gamma_variance: float

    def validate(self) -> None:
        if not self.name:
            raise ValueError("rescue model name cannot be empty")
        if self.variant not in RESCUE_VARIANTS:
            raise ValueError(f"unknown Wagner rescue variant: {self.variant}")
        if not isfinite(self.gamma_variance) or self.gamma_variance < 0.0:
            raise ValueError("Wagner rescue gamma variance must be nonnegative")


@dataclass(frozen=True)
class CueIntervention:
    """A temporary, explicitly removable Wagner induction intervention."""

    mode: str
    fraction: float
    dwell: int
    field_strength: float = 0.0

    @property
    def name(self) -> str:
        if self.mode in {"no_cue", "target_injection"}:
            return self.mode.replace("_", "-")
        suffix = f"f-{self.fraction:g}.d-{self.dwell}"
        if self.mode == "target_field":
            suffix += f".s-{self.field_strength:g}"
        return f"{self.mode.replace('_', '-')}.{suffix}"

    def validate(self) -> None:
        if self.mode not in RESCUE_CUE_MODES:
            raise ValueError(f"unknown rescue cue mode: {self.mode}")
        if self.dwell < 1:
            raise ValueError("rescue cue dwell must be positive")
        if self.mode == "no_cue":
            if self.fraction != 0.0 or self.field_strength != 0.0:
                raise ValueError("no-cue control must have zero fraction and strength")
            return
        if self.mode == "target_injection":
            if self.fraction != 1.0 or self.field_strength != 0.0:
                raise ValueError("target injection must use fraction one and zero strength")
            return
        if not 0.0 < self.fraction <= 1.0:
            raise ValueError("rescue cue fraction must lie in (0, 1]")
        if self.mode == "target_field":
            if not isfinite(self.field_strength) or self.field_strength <= 0.0:
                raise ValueError("target field requires positive finite strength")
        elif self.field_strength != 0.0:
            raise ValueError("only target-field cues may specify field strength")


@dataclass(frozen=True)
class WagnerRescueCondition:
    """One registered model/intervention cell."""

    name: str
    model: str
    intervention: CueIntervention
    role: str
    futures_per_cell: int

    def validate(self) -> None:
        if not self.name or not self.model:
            raise ValueError("rescue condition and model names cannot be empty")
        self.intervention.validate()
        if self.role not in RESCUE_ROLES:
            raise ValueError(f"unknown rescue condition role: {self.role}")
        expected_role = {
            "no_cue": "no_cue",
            "target_injection": "target_injection",
        }.get(self.intervention.mode)
        if expected_role is not None and self.role != expected_role:
            raise ValueError("control cue mode and condition role disagree")
        if expected_role is None and self.role not in {"candidate", "baseline"}:
            raise ValueError("active rescue intervention must be a candidate or baseline")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("rescue futures per cell must be even and at least four")


@dataclass(frozen=True)
class WagnerRescueSpec:
    """Complete immutable contract for one rescue phase."""

    cohort_id: str
    phase: str
    master_seed: str
    genes: int
    source_count: int
    eligibility_variants: tuple[str, ...]
    models: tuple[RescueModelSpec, ...]
    conditions: tuple[WagnerRescueCondition, ...]
    protocol_format: str = WAGNER_RESCUE_PROTOCOL_FORMAT
    midpoint_count: int = 2
    horizon: int = 32
    stable_run: int = 3
    strict_run: int = 8
    expression_flip_probability: float = 0.05
    expression_carryover: float = 1.0
    minimum_basin_fraction: float = 0.05
    minimum_form_distance: float = 0.40
    maximum_source_proposals: int = 500_000
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    simultaneous_tests: int = 1
    exploratory: bool = True

    def validate(self) -> None:
        if self.protocol_format != WAGNER_RESCUE_PROTOCOL_FORMAT:
            raise ValueError(f"unsupported Wagner rescue protocol: {self.protocol_format}")
        if not self.cohort_id or not self.phase:
            raise ValueError("rescue cohort and phase cannot be empty")
        if len(self.master_seed) < 32:
            raise ValueError("rescue master seed must contain at least 128 bits")
        if not 2 <= self.genes <= 16:
            raise ValueError("rescue genes must lie in [2, 16]")
        if self.source_count < 1:
            raise ValueError("rescue source count must be positive")
        if not self.eligibility_variants or not set(self.eligibility_variants).issubset(
            RESCUE_VARIANTS
        ):
            raise ValueError("invalid rescue eligibility variants")
        if len(self.eligibility_variants) != len(set(self.eligibility_variants)):
            raise ValueError("rescue eligibility variants must be unique")
        if self.midpoint_count not in {1, 2}:
            raise ValueError("rescue midpoint count must be one or two")
        if self.horizon < max(12, self.stable_run, self.strict_run):
            raise ValueError("rescue horizon is too short")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid rescue expression flip probability")
        if not 0.0 <= self.expression_carryover <= 1.0:
            raise ValueError("invalid rescue expression carryover")
        if not 0.0 <= self.minimum_basin_fraction <= 1.0:
            raise ValueError("invalid rescue minimum basin fraction")
        if not 0.0 <= self.minimum_form_distance <= 1.0:
            raise ValueError("invalid rescue minimum form distance")
        if self.maximum_source_proposals < 1 or self.wagner_max_sweeps < 1:
            raise ValueError("invalid rescue execution limit")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid rescue interval configuration")
        if self.simultaneous_tests < 1:
            raise ValueError("rescue simultaneous-test count must be positive")
        if not self.models or not self.conditions:
            raise ValueError("rescue phase requires models and conditions")
        for model in self.models:
            model.validate()
        model_names = [model.name for model in self.models]
        if len(model_names) != len(set(model_names)):
            raise ValueError("rescue model names must be unique")
        for condition in self.conditions:
            condition.validate()
            if condition.model not in model_names:
                raise ValueError(f"condition {condition.name} references an unknown model")
        condition_names = [condition.name for condition in self.conditions]
        if len(condition_names) != len(set(condition_names)):
            raise ValueError("rescue condition names must be unique")
        used_variants = {model.variant for model in self.models}
        if not used_variants.issubset(self.eligibility_variants):
            raise ValueError("every rescue model variant must be an eligibility variant")

    def model(self, name: str) -> RescueModelSpec:
        return next(model for model in self.models if model.name == name)

    def condition(self, name: str) -> WagnerRescueCondition:
        return next(condition for condition in self.conditions if condition.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WagnerRescueSpec":
        fields = dict(value)
        fields["eligibility_variants"] = tuple(fields["eligibility_variants"])
        fields["models"] = tuple(
            item if isinstance(item, RescueModelSpec) else RescueModelSpec(**item)
            for item in fields["models"]
        )
        conditions = []
        for item in fields["conditions"]:
            if isinstance(item, WagnerRescueCondition):
                conditions.append(item)
                continue
            condition = dict(item)
            intervention = condition["intervention"]
            condition["intervention"] = (
                intervention
                if isinstance(intervention, CueIntervention)
                else CueIntervention(**intervention)
            )
            conditions.append(WagnerRescueCondition(**condition))
        fields["conditions"] = tuple(conditions)
        spec = cls(**fields)
        spec.validate()
        return spec
