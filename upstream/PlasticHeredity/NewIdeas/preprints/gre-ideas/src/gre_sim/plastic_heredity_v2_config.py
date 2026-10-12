"""Independent contracts for the Plastic Heredity v2 research program.

The v2 contracts deliberately wrap, rather than modify, the completed v1
plastic-memory protocols.  A v2 state-channel phase can be lowered to the
well-tested memory executor while retaining a separate registration and
scientific analysis at the v2 campaign boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
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


PLASTIC_HEREDITY_V2_FORMAT = "gre-plastic-heredity-v2-spec-v1"
PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT = (
    "gre-plastic-heredity-v2-campaign-registration-v1"
)
PLASTIC_HEREDITY_V2_ANALYSIS_FORMAT = "gre-plastic-heredity-v2-analysis-v1"
PLASTIC_HEREDITY_V2_WAVE_FORMAT = "gre-plastic-heredity-v2-wave-manifest-v1"

V2_ENGINES = ("boolean", "wagner")
V2_WRITER_MODES = ("exact_target", "natural_clamp")
V2_CARRIER_MECHANISMS = (
    "state",
    "trace",
    "recurrent_field",
    "latch",
    "wagner_edge_trace",
    "boolean_transition_trace",
)
V2_SELECTION_ENDPOINTS = ("descendant_memory", "cue_only", "neutral")


@dataclass(frozen=True)
class WriterV2Spec:
    """A registered way of writing an A/B history into a developing system."""

    name: str
    mode: str
    fraction: float
    dwell: int
    engines: tuple[str, ...] = V2_ENGINES
    gamma_variance: float = 0.0
    field_strength: float = 0.0

    def validate(self) -> None:
        if not self.name or self.mode not in V2_WRITER_MODES:
            raise ValueError("invalid v2 writer identity or mode")
        if not self.engines or not set(self.engines).issubset(V2_ENGINES):
            raise ValueError("v2 writer has an unknown engine")
        if not 0.0 < self.fraction <= 1.0 or self.dwell < 1:
            raise ValueError("invalid v2 writer dose")
        if self.mode == "exact_target" and self.fraction != 1.0:
            raise ValueError("exact-target writer must write every discriminating node")
        if not isfinite(self.gamma_variance) or self.gamma_variance < 0.0:
            raise ValueError("v2 writer noise must be nonnegative")
        if not isfinite(self.field_strength) or self.field_strength < 0.0:
            raise ValueError("v2 writer field strength must be nonnegative")


@dataclass(frozen=True)
class CarrierV2Spec:
    """A state or engineered carrier and its causal intervention arm."""

    name: str
    mechanism: str
    arm: str
    half_life: int = 0
    coupling: float = 0.0
    write_threshold: int = 1
    retention: int = 0
    primary: bool = True
    engines: tuple[str, ...] = V2_ENGINES

    @property
    def rho(self) -> float:
        if self.half_life == 0:
            return 0.0
        return float(2.0 ** (-1.0 / self.half_life))

    def validate(self) -> None:
        if not self.name or self.mechanism not in V2_CARRIER_MECHANISMS:
            raise ValueError("invalid v2 carrier identity or mechanism")
        if not self.engines or not set(self.engines).issubset(V2_ENGINES):
            raise ValueError("v2 carrier has an unknown engine")
        if not self.arm:
            raise ValueError("v2 carrier arm cannot be empty")
        if self.half_life < 0 or not 0.0 <= self.coupling <= 1.0:
            raise ValueError("invalid v2 carrier decay or coupling")
        if self.write_threshold not in {1, 2} or self.retention < 0:
            raise ValueError("invalid v2 carrier latch parameters")
        if self.mechanism == "state" and (self.half_life or self.coupling):
            raise ValueError("ordinary state carrier cannot have hidden coupling")
        if self.mechanism in {"trace", "recurrent_field"}:
            if self.half_life < 1 or self.coupling <= 0.0:
                raise ValueError("trace and field carriers require decay and coupling")
        if self.mechanism == "latch":
            if self.retention < 1 or self.coupling <= 0.0:
                raise ValueError("latch carrier requires retention and coupling")
        if self.mechanism in {"wagner_edge_trace", "boolean_transition_trace"}:
            if self.half_life < 1 or self.coupling <= 0.0:
                raise ValueError("substrate-native traces require decay and coupling")
        if self.mechanism == "wagner_edge_trace" and self.engines != ("wagner",):
            raise ValueError("Wagner edge trace is substrate-specific")
        if self.mechanism == "boolean_transition_trace" and self.engines != ("boolean",):
            raise ValueError("Boolean transition trace is substrate-specific")


@dataclass(frozen=True)
class V2Condition:
    """One compact Cartesian block in a v2 state-channel phase."""

    name: str
    writer: str
    carriers: tuple[str, ...]
    descendant_ages: tuple[int, ...]
    challenges: tuple[str, ...]
    futures_per_cell: int

    def validate(self) -> None:
        if not self.name or not self.writer or not self.carriers:
            raise ValueError("v2 condition identity cannot be empty")
        if not self.descendant_ages or any(age < 0 for age in self.descendant_ages):
            raise ValueError("v2 descendant ages must be nonnegative")
        if not self.challenges or not set(self.challenges).issubset(MEMORY_CHALLENGES):
            raise ValueError("v2 condition has an unknown challenge")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("v2 futures per cell must be even and at least four")


@dataclass(frozen=True)
class PlasticHeredityV2Spec:
    """Complete immutable contract for one v2 state-channel phase."""

    cohort_id: str
    phase: str
    master_seed: str
    genes: int
    source_count_per_engine: int
    writers: tuple[WriterV2Spec, ...]
    carriers: tuple[CarrierV2Spec, ...]
    conditions: tuple[V2Condition, ...]
    engines: tuple[str, ...] = V2_ENGINES
    protocol_format: str = PLASTIC_HEREDITY_V2_FORMAT
    midpoint_count: int = 2
    horizon: int = 32
    stable_run: int = 3
    strict_run: int = 8
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    minimum_basin_fraction: float = 0.05
    minimum_form_distance: float = 0.40
    maximum_source_proposals: int = 500_000
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if self.protocol_format != PLASTIC_HEREDITY_V2_FORMAT:
            raise ValueError("unsupported plastic-heredity v2 protocol")
        if not self.cohort_id or not self.phase or len(self.master_seed) < 32:
            raise ValueError("invalid v2 phase identity")
        if not 2 <= self.genes <= 16 or self.source_count_per_engine < 1:
            raise ValueError("invalid v2 phase dimensions")
        if not self.engines or not set(self.engines).issubset(V2_ENGINES):
            raise ValueError("v2 phase has an unknown engine")
        if self.midpoint_count not in {1, 2}:
            raise ValueError("v2 midpoint count must be one or two")
        if self.horizon < max(12, self.stable_run, self.strict_run):
            raise ValueError("v2 horizon cannot certify registered endpoints")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid v2 expression noise")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("invalid v2 damage fraction")
        if self.maximum_source_proposals < 1 or self.wagner_max_sweeps < 1:
            raise ValueError("invalid v2 execution limit")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid v2 interval configuration")
        for writer in self.writers:
            writer.validate()
        for carrier in self.carriers:
            carrier.validate()
        for condition in self.conditions:
            condition.validate()
        writer_names = [value.name for value in self.writers]
        carrier_names = [value.name for value in self.carriers]
        condition_names = [value.name for value in self.conditions]
        if len(writer_names) != len(set(writer_names)):
            raise ValueError("v2 writer names must be unique")
        if len(carrier_names) != len(set(carrier_names)):
            raise ValueError("v2 carrier names must be unique")
        if len(condition_names) != len(set(condition_names)):
            raise ValueError("v2 condition names must be unique")
        for condition in self.conditions:
            if condition.writer not in writer_names:
                raise ValueError("v2 condition references an unknown writer")
            if not set(condition.carriers).issubset(carrier_names):
                raise ValueError("v2 condition references an unknown carrier")

    def writer(self, name: str) -> WriterV2Spec:
        return next(value for value in self.writers if value.name == name)

    def carrier(self, name: str) -> CarrierV2Spec:
        return next(value for value in self.carriers if value.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlasticHeredityV2Spec":
        fields = dict(value)
        fields["engines"] = tuple(fields.get("engines", V2_ENGINES))
        fields["writers"] = tuple(
            item
            if isinstance(item, WriterV2Spec)
            else WriterV2Spec(**{**item, "engines": tuple(item["engines"])})
            for item in fields["writers"]
        )
        fields["carriers"] = tuple(
            item
            if isinstance(item, CarrierV2Spec)
            else CarrierV2Spec(**{**item, "engines": tuple(item.get("engines", V2_ENGINES))})
            for item in fields["carriers"]
        )
        fields["conditions"] = tuple(
            item
            if isinstance(item, V2Condition)
            else V2Condition(
                **{
                    **item,
                    "carriers": tuple(item["carriers"]),
                    "descendant_ages": tuple(item["descendant_ages"]),
                    "challenges": tuple(item["challenges"]),
                }
            )
            for item in fields["conditions"]
        )
        result = cls(**fields)
        result.validate()
        return result

    def memory_spec(self) -> PlasticMemorySpec:
        """Lower a state-channel phase to the audited v1-compatible executor."""

        self.validate()
        sources = tuple(
            MemorySourceSpec(
                f"{engine}_n{self.genes}",
                engine,
                self.genes,
                self.source_count_per_engine,
                "boolean_sync" if engine == "boolean" else "wagner_sequential",
            )
            for engine in self.engines
        )
        models: list[MemoryModelSpec] = []
        conditions: list[MemoryCondition] = []
        for writer in self.writers:
            for engine in self.engines:
                if engine not in writer.engines:
                    continue
                model_name = f"{engine}.{writer.name}"
                models.append(
                    MemoryModelSpec(
                        model_name,
                        f"{engine}_n{self.genes}",
                        "boolean_sync" if engine == "boolean" else "wagner_sequential",
                        0.0 if engine == "boolean" else writer.gamma_variance,
                        True,
                    )
                )
                for condition in self.conditions:
                    if condition.writer != writer.name:
                        continue
                    arms = tuple(self.carrier(name).arm for name in condition.carriers)
                    if not set(arms).issubset(MEMORY_CARRIERS):
                        raise ValueError("custom v2 carrier cannot use the memory executor")
                    conditions.append(
                        MemoryCondition(
                            f"{condition.name}.{engine}",
                            model_name,
                            CueDose(writer.fraction, writer.dwell),
                            ("none",),
                            arms,
                            condition.descendant_ages,
                            condition.challenges,
                            condition.futures_per_cell,
                        )
                    )
        return PlasticMemorySpec(
            cohort_id=self.cohort_id,
            phase=self.phase,
            master_seed=self.master_seed,
            sources=sources,
            models=tuple(models),
            mark_settings=(MarkSetting("none", 0, 0.0),),
            conditions=tuple(conditions),
            midpoint_count=self.midpoint_count,
            horizon=self.horizon,
            stable_run=self.stable_run,
            strict_run=self.strict_run,
            expression_flip_probability=self.expression_flip_probability,
            neutral_damage_fraction=self.neutral_damage_fraction,
            minimum_basin_fraction=self.minimum_basin_fraction,
            minimum_form_distance=self.minimum_form_distance,
            maximum_source_proposals=self.maximum_source_proposals,
            wagner_max_sweeps=self.wagner_max_sweeps,
            bootstrap_repetitions=self.bootstrap_repetitions,
            interval_level=self.interval_level,
            exploratory=self.exploratory,
        )


@dataclass(frozen=True)
class EvolutionV2Spec:
    """Prospective evolution contract with selection and assay kept separate."""

    cohort_id: str
    master_seed: str
    parent_population_root: str
    populations_per_treatment: int
    population_size: int
    generations: int
    selection_replicates: int
    heldout_replicates: int
    training_replicates: int = 4
    selection_endpoint_memory: str = "descendant_memory"
    selection_endpoint_cue: str = "cue_only"
    selection_endpoint_neutral: str = "neutral"
    common_assay_endpoint: str = "descendant_memory"
    genes: int = 10
    descendant_age: int = 1
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    post_horizon: int = 12
    hold_run: int = 4
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid v2 evolution identity")
        if not self.parent_population_root:
            raise ValueError("v2 evolution parent root cannot be empty")
        for endpoint in (
            self.selection_endpoint_memory,
            self.selection_endpoint_cue,
            self.selection_endpoint_neutral,
            self.common_assay_endpoint,
        ):
            if endpoint not in V2_SELECTION_ENDPOINTS:
                raise ValueError("unknown v2 evolution endpoint")
        if self.common_assay_endpoint != "descendant_memory":
            raise ValueError("v2 common assay must measure descendant memory")
        for value in (
            self.populations_per_treatment,
            self.population_size,
            self.generations,
            self.selection_replicates,
            self.heldout_replicates,
            self.training_replicates,
            self.genes,
            self.descendant_age,
            self.post_horizon,
            self.hold_run,
        ):
            if value < 1:
                raise ValueError("v2 evolution counts must be positive")
        if self.post_horizon < self.hold_run:
            raise ValueError("v2 evolution horizon cannot certify its hold endpoint")

    def selection_endpoint(self, treatment: str) -> str:
        mapping = {
            "memory_selection": self.selection_endpoint_memory,
            "cue_performance_sham": self.selection_endpoint_cue,
            "neutral": self.selection_endpoint_neutral,
        }
        try:
            return mapping[treatment]
        except KeyError as error:
            raise ValueError(f"unknown v2 evolution treatment: {treatment}") from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvolutionV2Spec":
        result = cls(**value)
        result.validate()
        return result

    @property
    def parent_path(self) -> Path:
        return Path(self.parent_population_root)


@dataclass(frozen=True)
class CarrierStudyV2Spec:
    """Immutable engine-neutral carrier screen or confirmation contract."""

    cohort_id: str
    phase: str
    master_seed: str
    source_count_per_engine: int
    carriers: tuple[CarrierV2Spec, ...]
    futures_per_cell: int
    arms: tuple[str, ...]
    descendant_ages: tuple[int, ...]
    challenges: tuple[str, ...]
    genes: int = 10
    midpoint_count: int = 2
    horizon: int = 32
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    maximum_source_proposals: int = 500_000
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or not self.phase or len(self.master_seed) < 32:
            raise ValueError("invalid v2 carrier-study identity")
        if self.source_count_per_engine < 1 or not 2 <= self.genes <= 16:
            raise ValueError("invalid v2 carrier-study dimensions")
        if not self.carriers or not self.arms:
            raise ValueError("v2 carrier study requires candidates and arms")
        for carrier in self.carriers:
            carrier.validate()
            if carrier.mechanism == "state":
                raise ValueError("carrier study is reserved for engineered carriers")
        if len({value.name for value in self.carriers}) != len(self.carriers):
            raise ValueError("v2 carrier candidate names must be unique")
        allowed_arms = {
            "carrier_transplant",
            "reset",
            "write_disabled",
            "inert",
            "pattern_shuffle",
            "ablation_0",
            "ablation_25",
            "ablation_50",
            "ablation_100",
            "random_ablation_25",
            "random_ablation_50",
            "rescue",
        }
        if not set(self.arms).issubset(allowed_arms):
            raise ValueError("v2 carrier study has an unknown intervention arm")
        if not self.descendant_ages or any(value < 0 for value in self.descendant_ages):
            raise ValueError("v2 carrier ages must be nonnegative")
        if not self.challenges or not set(self.challenges).issubset(MEMORY_CHALLENGES):
            raise ValueError("v2 carrier study has an unknown challenge")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("v2 carrier futures must be even and at least four")
        if self.midpoint_count not in {1, 2}:
            raise ValueError("v2 carrier midpoint count must be one or two")
        if self.horizon < max(12, self.strict_run, self.stable_run):
            raise ValueError("v2 carrier horizon cannot certify its endpoints")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CarrierStudyV2Spec":
        fields = dict(value)
        fields["carriers"] = tuple(
            item
            if isinstance(item, CarrierV2Spec)
            else CarrierV2Spec(**{**item, "engines": tuple(item.get("engines", V2_ENGINES))})
            for item in fields["carriers"]
        )
        for name in ("arms", "descendant_ages", "challenges"):
            fields[name] = tuple(fields[name])
        result = cls(**fields)
        result.validate()
        return result
