"""Immutable contracts for the Wagner plastic-heredity bridge campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .local_ph_config import CopyNoiseSpec, LocalCarrierGenome, LocalStudySpec


BRIDGE_CAMPAIGN_FORMAT = "gre-wagner-ph-bridge-campaign-v1"
BRIDGE_STAGE_FORMAT = "gre-wagner-ph-bridge-stage-v1"
BRIDGE_ANALYSIS_FORMAT = "gre-wagner-ph-bridge-analysis-v1"
BRIDGE_EVOLUTION_FORMAT = "gre-wagner-ph-bridge-coevolution-v1"
BRIDGE_EVOLUTION_MANIFEST_FORMAT = "gre-wagner-ph-bridge-coevolution-manifest-v1"

BRIDGE_TREATMENTS = (
    "descendant_memory_cost",
    "descendant_memory_no_cost",
    "acute_performance_cost",
    "neutral_drift",
)


@dataclass(frozen=True)
class ReliabilityMetricSpec:
    """Prospective block-stability gate that remains meaningful at saturation."""

    blocks: int = 4
    block_size: int = 16
    minimum_risk_gain: float = 0.05
    equivalence_margin: float = 0.05
    minimum_sign_concordance: float = 0.80
    minimum_positive_blocks: int = 3
    interval_level: float = 0.95
    equivalence_interval_level: float = 0.90

    def validate(self, futures_per_history: int) -> None:
        if self.blocks < 2 or self.block_size < 2:
            raise ValueError("repeatability requires at least two nontrivial blocks")
        if self.blocks * self.block_size != futures_per_history:
            raise ValueError("repeatability blocks must partition all futures")
        if not 0.0 < self.minimum_risk_gain < 1.0:
            raise ValueError("invalid minimum repeatability effect")
        if not 0.0 < self.equivalence_margin < 1.0:
            raise ValueError("invalid block equivalence margin")
        if not 0.0 <= self.minimum_sign_concordance <= 1.0:
            raise ValueError("invalid sign-concordance threshold")
        if not 1 <= self.minimum_positive_blocks <= self.blocks:
            raise ValueError("invalid positive-block threshold")
        for level in (self.interval_level, self.equivalence_interval_level):
            if not 0.0 < level < 1.0:
                raise ValueError("invalid reliability interval level")


@dataclass(frozen=True)
class PrecisionReplicationSpec:
    study: LocalStudySpec
    reliability: ReliabilityMetricSpec = field(default_factory=ReliabilityMetricSpec)

    def validate(self) -> None:
        self.study.validate()
        self.reliability.validate(self.study.futures_per_history)
        if self.study.checkpoint_generations != (0, 4, 8, 16):
            raise ValueError("precision checkpoints must be generations 0, 4, 8, and 16")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PrecisionReplicationSpec":
        result = cls(
            LocalStudySpec.from_dict(value["study"]),
            ReliabilityMetricSpec(**value["reliability"]),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class PhaseCellSpec:
    name: str
    axis: str
    level: str
    condition: str
    genome: str | None
    noise: str
    intervention: str = "intact"

    def validate(self) -> None:
        if not all((self.name, self.axis, self.level, self.condition, self.noise)):
            raise ValueError("phase-map cells require complete labels")


@dataclass(frozen=True)
class PhaseDiagramSpec:
    screening: LocalStudySpec
    cells: tuple[PhaseCellSpec, ...]
    confirmation_sources: int = 48
    confirmation_futures_per_history: int = 16
    confirmation_checkpoints: tuple[int, ...] = (0, 2, 4, 8, 16)
    confirmation_challenges: tuple[str, ...] = ("forced_break", "release_only")
    maximum_nominees: int = 2

    def validate(self) -> None:
        self.screening.validate()
        if len(self.screening.conditions) != 30 or len(self.cells) != 30:
            raise ValueError("phase map must contain exactly thirty explicit cells")
        for value in self.cells:
            value.validate()
        names = [value.name for value in self.cells]
        if len(names) != len(set(names)):
            raise ValueError("phase-map cell names must be unique")
        if {value.condition for value in self.cells} != {
            value.name for value in self.screening.conditions
        }:
            raise ValueError("phase-map design and study conditions disagree")
        if self.confirmation_sources < 3 or self.confirmation_futures_per_history < 4:
            raise ValueError("causal confirmation is too small")
        if self.maximum_nominees not in {1, 2}:
            raise ValueError("causal confirmation permits one or two nominees")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PhaseDiagramSpec":
        result = cls(
            screening=LocalStudySpec.from_dict(value["screening"]),
            cells=tuple(PhaseCellSpec(**item) for item in value["cells"]),
            confirmation_sources=int(value.get("confirmation_sources", 48)),
            confirmation_futures_per_history=int(
                value.get("confirmation_futures_per_history", 16)
            ),
            confirmation_checkpoints=tuple(
                value.get("confirmation_checkpoints", (0, 2, 4, 8, 16))
            ),
            confirmation_challenges=tuple(
                value.get("confirmation_challenges", ("forced_break", "release_only"))
            ),
            maximum_nominees=int(value.get("maximum_nominees", 2)),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class CoevolutionSpec:
    cohort_id: str
    master_seed: str
    initial_carrier: LocalCarrierGenome
    nominal_noise: CopyNoiseSpec
    strong_noise: CopyNoiseSpec
    treatments: tuple[str, ...] = BRIDGE_TREATMENTS
    populations_per_treatment: int = 8
    population_size: int = 32
    generations: int = 30
    elite_count: int = 4
    tournament_size: int = 3
    training_replicates: int = 4
    heldout_replicates: int = 16
    heritability_offspring: int = 4
    genes: int = 10
    generation_cycles: int = 4
    horizon: int = 16
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    capacity_cost: float = 0.05
    coupling_cost: float = 0.025
    writing_cost: float = 0.025
    bootstrap_repetitions: int = 2048
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid coevolution identity")
        self.initial_carrier.validate(self.genes)
        self.nominal_noise.validate()
        self.strong_noise.validate()
        if self.treatments != BRIDGE_TREATMENTS:
            raise ValueError("coevolution treatments are frozen and ordered")
        counts = (
            self.populations_per_treatment,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.training_replicates,
            self.heldout_replicates,
            self.heritability_offspring,
        )
        if min(counts) < 1 or self.elite_count >= self.population_size:
            raise ValueError("invalid coevolution dimensions")
        if self.training_replicates % 2 or self.heldout_replicates % 2:
            raise ValueError("coevolution replicate counts must be even")
        if self.horizon < max(8, self.strict_run) or self.generation_cycles < 1:
            raise ValueError("invalid coevolution development horizon")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid coevolution expression noise")
        costs = (self.capacity_cost, self.coupling_cost, self.writing_cost)
        if min(costs) < 0.0 or sum(costs) > 0.10 + 1e-12:
            raise ValueError("coevolution resource cost must lie in [0, 0.10]")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid coevolution interval configuration")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CoevolutionSpec":
        fields = dict(value)
        fields["initial_carrier"] = LocalCarrierGenome(**fields["initial_carrier"])
        fields["nominal_noise"] = CopyNoiseSpec(**fields["nominal_noise"])
        fields["strong_noise"] = CopyNoiseSpec(**fields["strong_noise"])
        fields["treatments"] = tuple(fields.get("treatments", BRIDGE_TREATMENTS))
        result = cls(**fields)
        result.validate()
        return result

    @property
    def population_count(self) -> int:
        return len(self.treatments) * self.populations_per_treatment


@dataclass(frozen=True)
class BridgeCampaignSpec:
    cohort_id: str
    master_seed: str
    precision: PrecisionReplicationSpec
    phase_diagram: PhaseDiagramSpec
    coevolution_template: CoevolutionSpec
    maximum_workers: int = 4
    hard_wall_seconds: int = 28_800
    soft_wall_seconds: int = 27_000
    stage_reservations_seconds: tuple[int, ...] = (2700, 7200, 14400, 4500)

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid bridge campaign identity")
        self.precision.validate()
        self.phase_diagram.validate()
        self.coevolution_template.validate()
        if self.maximum_workers != 4:
            raise ValueError("bridge campaign is capped at four workers")
        if self.hard_wall_seconds != 28_800 or not 0 < self.soft_wall_seconds < self.hard_wall_seconds:
            raise ValueError("bridge campaign must retain its cumulative eight-hour boundary")
        if sum(self.stage_reservations_seconds) != self.hard_wall_seconds:
            raise ValueError("stage reservations must exactly cover the wall budget")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BridgeCampaignSpec":
        result = cls(
            cohort_id=str(value["cohort_id"]),
            master_seed=str(value["master_seed"]),
            precision=PrecisionReplicationSpec.from_dict(value["precision"]),
            phase_diagram=PhaseDiagramSpec.from_dict(value["phase_diagram"]),
            coevolution_template=CoevolutionSpec.from_dict(value["coevolution_template"]),
            maximum_workers=int(value.get("maximum_workers", 4)),
            hard_wall_seconds=int(value.get("hard_wall_seconds", 28_800)),
            soft_wall_seconds=int(value.get("soft_wall_seconds", 27_000)),
            stage_reservations_seconds=tuple(
                value.get("stage_reservations_seconds", (2700, 7200, 14400, 4500))
            ),
        )
        result.validate()
        return result
