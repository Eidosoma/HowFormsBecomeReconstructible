"""Configuration contracts for the exploratory Boolean--Wagner mechanism campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MECHANISM_PROTOCOL_FORMAT = "gre-mechanism-study-v1"
MECHANISM_REGISTRATION_FORMAT = "gre-mechanism-registration-v1"
MECHANISM_RAW_FORMAT = "gre-mechanism-futures-v1"
MECHANISM_ANALYSIS_FORMAT = "gre-mechanism-analysis-v1"

MECHANISM_VARIANTS = (
    "boolean_sync",
    "boolean_sequential",
    "wagner_sequential",
    "wagner_synchronous",
    "wagner_compiled",
)
MECHANISM_INHERITANCE_MODES = (
    "self",
    "donor_shuffled",
    "destination_matched_donor",
    "exact_state_donor",
)
MECHANISM_ARMS = (
    "natural",
    "joint_isomorphic",
    "acute_mismatch",
    "target_aligned_own_anchor",
    "single_attractor",
)


@dataclass(frozen=True)
class SourceSetSpec:
    """One independently generated or imported collection of rulebooks."""

    name: str
    engine: str
    genes: int
    count: int
    origin: str = "sampled"
    parent_engine: str | None = None
    require_both_update_modes: bool = False

    def validate(self) -> None:
        if not self.name:
            raise ValueError("source-set name cannot be empty")
        if self.engine not in {"boolean", "wagner"}:
            raise ValueError(f"unknown source engine: {self.engine}")
        if not 2 <= self.genes <= 16:
            raise ValueError("source-set genes must lie in [2, 16]")
        if self.count < 1:
            raise ValueError("source-set count must be positive")
        if self.origin not in {"sampled", "parent"}:
            raise ValueError(f"unknown source origin: {self.origin}")
        if self.origin == "parent":
            expected = self.parent_engine or self.engine
            if expected not in {"boolean", "wagner"}:
                raise ValueError("parent source set needs a valid parent engine")


@dataclass(frozen=True)
class MechanismCondition:
    """A compact Cartesian block within one mechanism phase."""

    name: str
    source_set: str
    variant: str
    arms: tuple[str, ...]
    carryover_values: tuple[float, ...]
    inheritance_modes: tuple[str, ...]
    gamma_variances: tuple[float, ...] = (0.0,)
    futures_per_cell: int = 16
    compiled_update_mode: str = "sequential"

    def validate(self) -> None:
        if not self.name:
            raise ValueError("condition name cannot be empty")
        if self.variant not in MECHANISM_VARIANTS:
            raise ValueError(f"unknown mechanism variant: {self.variant}")
        if not self.arms or not set(self.arms).issubset(MECHANISM_ARMS):
            raise ValueError(f"unknown mechanism arms: {self.arms}")
        if not self.carryover_values or any(
            value < 0.0 or value > 1.0 for value in self.carryover_values
        ):
            raise ValueError("carryover values must lie in [0, 1]")
        if not self.inheritance_modes or not set(self.inheritance_modes).issubset(
            MECHANISM_INHERITANCE_MODES
        ):
            raise ValueError(
                f"unknown mechanism inheritance modes: {self.inheritance_modes}"
            )
        if not self.gamma_variances or any(value < 0.0 for value in self.gamma_variances):
            raise ValueError("gamma variances must be nonnegative")
        if self.variant.startswith("boolean") or self.variant == "wagner_compiled":
            if self.gamma_variances != (0.0,):
                raise ValueError(f"{self.variant} supports only zero rulebook noise")
        if self.compiled_update_mode not in {"sequential", "synchronous"}:
            raise ValueError("compiled update mode must be sequential or synchronous")
        if self.variant != "wagner_compiled" and self.compiled_update_mode != "sequential":
            raise ValueError("compiled update mode applies only to compiled Wagner")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("futures per mechanism cell must be even and at least four")


@dataclass(frozen=True)
class MechanismSpec:
    """Complete immutable contract for one exploratory mechanism phase."""

    cohort_id: str
    phase: str
    master_seed: str
    source_sets: tuple[SourceSetSpec, ...]
    conditions: tuple[MechanismCondition, ...]
    protocol_format: str = MECHANISM_PROTOCOL_FORMAT
    launch_states_per_rulebook: int = 5
    horizon: int = 32
    stable_destination_run: int = 3
    strict_run: int = 8
    old_distinct_distance: float = 0.20
    expression_flip_probability: float = 0.05
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    parent_protocol_digest: str | None = None
    exploratory: bool = True

    def validate(self) -> None:
        if self.protocol_format != MECHANISM_PROTOCOL_FORMAT:
            raise ValueError(f"unsupported mechanism protocol: {self.protocol_format}")
        if not self.cohort_id or not self.phase:
            raise ValueError("cohort id and phase cannot be empty")
        if len(self.master_seed) < 32:
            raise ValueError("mechanism master seed must contain at least 128 bits")
        if not self.exploratory:
            raise ValueError("mechanism campaigns are exploratory by contract")
        if self.launch_states_per_rulebook < 1:
            raise ValueError("launch-state count must be positive")
        if self.horizon < max(self.stable_destination_run, self.strict_run, 12):
            raise ValueError("mechanism horizon must support all registered run lengths")
        if not 0.0 <= self.old_distinct_distance <= 1.0:
            raise ValueError("old-state distance must lie in [0, 1]")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("expression flip probability must lie in [0, 1]")
        if self.wagner_max_sweeps < 1:
            raise ValueError("Wagner maximum sweeps must be positive")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid mechanism interval configuration")
        if not self.source_sets or not self.conditions:
            raise ValueError("mechanism phase needs source sets and conditions")
        for source in self.source_sets:
            source.validate()
        source_names = [source.name for source in self.source_sets]
        if len(set(source_names)) != len(source_names):
            raise ValueError("mechanism source-set names must be unique")
        for condition in self.conditions:
            condition.validate()
            if condition.source_set not in source_names:
                raise ValueError(
                    f"condition {condition.name} references unknown source set "
                    f"{condition.source_set}"
                )
            source = next(item for item in self.source_sets if item.name == condition.source_set)
            if condition.variant.startswith("boolean") and source.engine != "boolean":
                raise ValueError("Boolean variants require Boolean sources")
            if condition.variant.startswith("wagner") and source.engine != "wagner":
                raise ValueError("Wagner variants require Wagner sources")
        condition_names = [condition.name for condition in self.conditions]
        if len(set(condition_names)) != len(condition_names):
            raise ValueError("mechanism condition names must be unique")

    def source(self, name: str) -> SourceSetSpec:
        return next(value for value in self.source_sets if value.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MechanismSpec":
        fields = dict(value)
        fields["source_sets"] = tuple(
            item if isinstance(item, SourceSetSpec) else SourceSetSpec(**item)
            for item in fields["source_sets"]
        )
        conditions = []
        for item in fields["conditions"]:
            if isinstance(item, MechanismCondition):
                conditions.append(item)
                continue
            condition = dict(item)
            for name in (
                "arms",
                "carryover_values",
                "inheritance_modes",
                "gamma_variances",
            ):
                condition[name] = tuple(condition[name])
            conditions.append(MechanismCondition(**condition))
        fields["conditions"] = tuple(conditions)
        spec = cls(**fields)
        spec.validate()
        return spec

    @classmethod
    def quick(cls) -> "MechanismSpec":
        """Small end-to-end mechanism fixture with imported quick-v2 sources."""

        return cls(
            cohort_id="quick-mechanism-v1",
            phase="quick",
            master_seed=(
                "d0db803ffac28af145018904d4dd20a4269565fa32f030a57663422ec880ed8f"
            ),
            source_sets=(
                SourceSetSpec("parent_boolean", "boolean", 6, 1, "parent", "boolean"),
                SourceSetSpec("parent_wagner", "wagner", 10, 1, "parent", "wagner"),
            ),
            conditions=(
                MechanismCondition(
                    "boolean-main",
                    "parent_boolean",
                    "boolean_sync",
                    ("natural", "acute_mismatch"),
                    (0.0, 1.0),
                    ("self", "donor_shuffled"),
                    (0.0,),
                    4,
                ),
                MechanismCondition(
                    "wagner-main",
                    "parent_wagner",
                    "wagner_sequential",
                    ("natural", "acute_mismatch"),
                    (0.0, 1.0),
                    ("self", "donor_shuffled"),
                    (0.0, 0.1),
                    4,
                ),
                MechanismCondition(
                    "wagner-bridge",
                    "parent_wagner",
                    "wagner_compiled",
                    ("acute_mismatch",),
                    (1.0,),
                    ("self",),
                    (0.0,),
                    4,
                ),
            ),
            launch_states_per_rulebook=2,
            horizon=12,
            stable_destination_run=2,
            strict_run=2,
            bootstrap_repetitions=64,
        )


def expected_mechanism_futures(spec: MechanismSpec) -> int:
    """Return the exact record count implied by a condition-block protocol."""

    total = 0
    for condition in spec.conditions:
        source = spec.source(condition.source_set)
        total += (
            source.count
            * spec.launch_states_per_rulebook
            * len(condition.arms)
            * len(condition.carryover_values)
            * len(condition.inheritance_modes)
            * len(condition.gamma_variances)
            * condition.futures_per_cell
        )
    return total
