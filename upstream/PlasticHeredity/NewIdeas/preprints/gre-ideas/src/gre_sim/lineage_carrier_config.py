"""Frozen contracts for the multigeneration GRN carrier experiment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from .plastic_heredity_v2_config import CarrierV2Spec


LINEAGE_CAMPAIGN_FORMAT = "gre-wagner-lineage-carrier-campaign-v1"
LINEAGE_STUDY_FORMAT = "gre-wagner-lineage-carrier-study-v1"
LINEAGE_REGISTRATION_FORMAT = "gre-wagner-lineage-carrier-registration-v1"
LINEAGE_RAW_FORMAT = "gre-wagner-lineage-carrier-futures-v1"
LINEAGE_ANALYSIS_FORMAT = "gre-wagner-lineage-carrier-analysis-v1"
LINEAGE_MANIFEST_FORMAT = "gre-wagner-lineage-carrier-manifest-v1"
LINEAGE_SELECTION_FORMAT = "gre-wagner-lineage-carrier-selection-v1"
LINEAGE_EVOLUTION_FORMAT = "gre-wagner-lineage-evolution-v1"

ENGINES = ("boolean", "wagner")
CHALLENGES = ("release_only", "neutral_damage", "forced_break")
WRITER_MODES = ("natural", "exact")
BOTTLENECKS = ("full", "targeted", "random", "shuffle", "opposite", "zero")
RECIPIENT_MODES = ("clone", "destination_matched", "descriptor_matched")


@dataclass(frozen=True)
class LineageSourceSpec:
    """Fresh rulebook count for one engine."""

    engine: str
    count: int

    def validate(self) -> None:
        if self.engine not in ENGINES or self.count < 1:
            raise ValueError("invalid lineage source specification")


@dataclass(frozen=True)
class LineageWriterSpec:
    """Founder writer selected without looking at descendant outcomes."""

    name: str
    engine: str
    mode: str
    cue_fraction: float
    cue_dwell: int

    def validate(self) -> None:
        if not self.name or self.engine not in ENGINES or self.mode not in WRITER_MODES:
            raise ValueError("invalid lineage writer identity")
        if not isfinite(self.cue_fraction) or not 0.0 < self.cue_fraction <= 1.0:
            raise ValueError("lineage cue fraction must lie in (0, 1]")
        if self.cue_dwell < 1:
            raise ValueError("lineage cue dwell must be positive")


@dataclass(frozen=True)
class LineageArmSpec:
    """One prospective transmission or causal-intervention arm."""

    name: str
    writer_mode: str = "natural"
    bottleneck: str = "full"
    k: int = 0
    rewrite: bool = True
    read_enabled: bool = True
    write_enabled: bool = True
    ablate_generation: int | None = None
    rescue_generation: int | None = None
    primary: bool = False

    def validate(self, genes: int) -> None:
        if not self.name or self.writer_mode not in WRITER_MODES:
            raise ValueError("invalid lineage arm identity")
        if self.bottleneck not in BOTTLENECKS:
            raise ValueError("unknown lineage bottleneck")
        if self.k < 0 or self.k > genes:
            raise ValueError("lineage bottleneck k lies outside the genome")
        if self.bottleneck in {"targeted", "random"} and self.k < 1:
            raise ValueError("targeted and random bottlenecks require k >= 1")
        if self.bottleneck not in {"targeted", "random"} and self.k != 0:
            raise ValueError("only targeted and random bottlenecks accept k")
        for value in (self.ablate_generation, self.rescue_generation):
            if value is not None and value < 1:
                raise ValueError("timed lineage interventions start at generation one")
        if self.rescue_generation is not None and self.ablate_generation is None:
            raise ValueError("lineage rescue requires an earlier ablation")
        if (
            self.rescue_generation is not None
            and self.ablate_generation is not None
            and self.rescue_generation <= self.ablate_generation
        ):
            raise ValueError("lineage rescue must follow ablation")


@dataclass(frozen=True)
class LineageStudySpec:
    """Immutable multigeneration carrier study contract."""

    cohort_id: str
    phase: str
    master_seed: str
    sources: tuple[LineageSourceSpec, ...]
    writers: tuple[LineageWriterSpec, ...]
    carriers: tuple[CarrierV2Spec, ...]
    arms: tuple[LineageArmSpec, ...]
    checkpoint_generations: tuple[int, ...]
    challenges: tuple[str, ...]
    futures_per_cell: int
    recipient_modes: tuple[str, ...] = ("clone",)
    genes: int = 10
    midpoint_count: int = 2
    generation_cycles: int = 4
    horizon: int = 32
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    minimum_basin_fraction: float = 0.05
    minimum_form_distance: float = 0.40
    maximum_source_proposals: int = 500_000
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True
    protocol_format: str = LINEAGE_STUDY_FORMAT

    def validate(self) -> None:
        if self.protocol_format != LINEAGE_STUDY_FORMAT:
            raise ValueError("unsupported lineage carrier protocol")
        if not self.cohort_id or not self.phase or len(self.master_seed) < 32:
            raise ValueError("invalid lineage study identity")
        if not 2 <= self.genes <= 16 or self.midpoint_count not in {1, 2}:
            raise ValueError("invalid lineage study dimensions")
        if not self.sources or len({value.engine for value in self.sources}) != len(self.sources):
            raise ValueError("lineage sources must contain unique engines")
        for value in self.sources:
            value.validate()
        for value in self.writers:
            value.validate()
        writer_engines = [value.engine for value in self.writers]
        if len(writer_engines) != len(set(writer_engines)):
            raise ValueError("lineage study accepts one selected writer per engine")
        if not set(writer_engines).issubset({value.engine for value in self.sources}):
            raise ValueError("lineage writer lacks a matching source engine")
        if not self.carriers or len({value.name for value in self.carriers}) != len(self.carriers):
            raise ValueError("lineage carriers must be nonempty and unique")
        for value in self.carriers:
            value.validate()
            if value.mechanism == "state":
                raise ValueError("lineage study requires an explicit engineered carrier")
        if not self.arms or len({value.name for value in self.arms}) != len(self.arms):
            raise ValueError("lineage arms must be nonempty and unique")
        for value in self.arms:
            value.validate(self.genes)
        if tuple(sorted(set(self.checkpoint_generations))) != self.checkpoint_generations:
            raise ValueError("lineage checkpoints must be unique and increasing")
        if not self.checkpoint_generations or self.checkpoint_generations[0] != 0:
            raise ValueError("lineage checkpoints must begin at generation zero")
        if not self.challenges or not set(self.challenges).issubset(CHALLENGES):
            raise ValueError("lineage study has an unknown challenge")
        if not self.recipient_modes or not set(self.recipient_modes).issubset(
            RECIPIENT_MODES
        ):
            raise ValueError("lineage study has an unknown recipient mode")
        if self.futures_per_cell < 4 or self.futures_per_cell % 2:
            raise ValueError("lineage futures must be even and at least four")
        if self.generation_cycles < 1 or self.horizon < max(12, self.strict_run, self.stable_run):
            raise ValueError("invalid lineage development or assay horizon")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid lineage expression noise")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("invalid lineage damage fraction")
        if self.maximum_source_proposals < 1 or self.wagner_max_sweeps < 1:
            raise ValueError("invalid lineage execution limit")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid lineage interval configuration")

    def source_count(self, engine: str) -> int:
        return next(value.count for value in self.sources if value.engine == engine)

    def writer(self, engine: str) -> LineageWriterSpec:
        return next(value for value in self.writers if value.engine == engine)

    def carrier(self, name: str) -> CarrierV2Spec:
        return next(value for value in self.carriers if value.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LineageStudySpec":
        fields = dict(value)
        fields["sources"] = tuple(
            item if isinstance(item, LineageSourceSpec) else LineageSourceSpec(**item)
            for item in fields["sources"]
        )
        fields["writers"] = tuple(
            item if isinstance(item, LineageWriterSpec) else LineageWriterSpec(**item)
            for item in fields["writers"]
        )
        fields["carriers"] = tuple(
            item
            if isinstance(item, CarrierV2Spec)
            else CarrierV2Spec(
                **{**item, "engines": tuple(item.get("engines", ENGINES))}
            )
            for item in fields["carriers"]
        )
        fields["arms"] = tuple(
            item if isinstance(item, LineageArmSpec) else LineageArmSpec(**item)
            for item in fields["arms"]
        )
        fields["checkpoint_generations"] = tuple(fields["checkpoint_generations"])
        fields["challenges"] = tuple(fields["challenges"])
        fields["recipient_modes"] = tuple(fields.get("recipient_modes", ("clone",)))
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class LineageEvolutionSpec:
    """Prospective pilot for evolvability of a confirmed lineage carrier."""

    cohort_id: str
    master_seed: str
    carrier: CarrierV2Spec
    writer: LineageWriterSpec
    bottleneck_k: int
    populations_per_treatment: int = 32
    population_size: int = 64
    generations: int = 100
    training_replicates: int = 4
    assay_replicates: int = 32
    heritability_offspring: int = 8
    genes: int = 10
    generation_cycles: int = 4
    horizon: int = 32
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    wagner_max_sweeps: int = 100
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True
    protocol_format: str = LINEAGE_EVOLUTION_FORMAT

    def validate(self) -> None:
        if self.protocol_format != LINEAGE_EVOLUTION_FORMAT:
            raise ValueError("unsupported lineage evolution protocol")
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid lineage evolution identity")
        self.carrier.validate()
        self.writer.validate()
        if self.writer.engine != "wagner" or "wagner" not in self.carrier.engines:
            raise ValueError("lineage evolution is Wagner-only")
        if not 1 <= self.bottleneck_k <= self.genes:
            raise ValueError("invalid evolved lineage bottleneck")
        if min(
            self.populations_per_treatment,
            self.population_size,
            self.generations,
            self.training_replicates,
            self.assay_replicates,
            self.heritability_offspring,
        ) < 1:
            raise ValueError("lineage evolution dimensions must be positive")
        if self.generation_cycles < 1 or self.horizon < max(12, self.strict_run):
            raise ValueError("invalid lineage evolution horizon")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid lineage evolution expression noise")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("invalid lineage evolution damage fraction")
        if self.wagner_max_sweeps < 1 or self.bootstrap_repetitions < 1:
            raise ValueError("invalid lineage evolution execution limit")
        if not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid lineage evolution interval level")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LineageEvolutionSpec":
        fields = dict(value)
        carrier = fields["carrier"]
        writer = fields["writer"]
        fields["carrier"] = (
            carrier
            if isinstance(carrier, CarrierV2Spec)
            else CarrierV2Spec(
                **{**carrier, "engines": tuple(carrier.get("engines", ENGINES))}
            )
        )
        fields["writer"] = (
            writer if isinstance(writer, LineageWriterSpec) else LineageWriterSpec(**writer)
        )
        result = cls(**fields)
        result.validate()
        return result
