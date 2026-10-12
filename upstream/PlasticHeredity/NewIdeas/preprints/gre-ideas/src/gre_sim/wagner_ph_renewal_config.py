"""Immutable contracts for the Wagner PH renewal/evolvability campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .local_ph_config import CopyNoiseSpec, LocalCarrierGenome, LocalStudySpec


RENEWAL_CAMPAIGN_FORMAT = "gre-wagner-ph-renewal-campaign-v1"
RENEWAL_FRONTIER_FORMAT = "gre-wagner-ph-renewal-frontier-v1"
RENEWAL_EVOLUTION_FORMAT = "gre-wagner-ph-renewal-evolution-v1"
RENEWAL_AUDIT_FORMAT = "gre-wagner-ph-renewal-audit-v1"

RENEWAL_TREATMENTS = (
    "renewal_standard_cost",
    "renewal_high_cost",
    "renewal_k5_feasibility",
    "memory_standard_cost",
    "acute_standard_cost",
    "neutral_drift",
)


@dataclass(frozen=True)
class RenewalFrontierSpec:
    """Prospective capacity-by-copy-environment renewal frontier."""

    study: LocalStudySpec
    environment_order: tuple[str, ...]
    capacities: tuple[int, ...] = (3, 5, 7, 10)
    minimum_generation_8_gain: float = 0.15
    minimum_renewal_contrast: float = 0.10
    fallback_environment: str = "mixed-moderate"

    def validate(self) -> None:
        self.study.validate()
        if self.capacities != (3, 5, 7, 10):
            raise ValueError("renewal frontier capacities are frozen")
        if len(self.environment_order) != 6 or len(set(self.environment_order)) != 6:
            raise ValueError("renewal frontier requires six ordered environments")
        if self.fallback_environment not in self.environment_order:
            raise ValueError("renewal fallback environment is not registered")
        if self.study.checkpoint_generations != (0, 4, 8, 12, 16):
            raise ValueError("renewal frontier checkpoints are frozen")
        if self.study.challenges != ("forced_break", "release_only"):
            raise ValueError("renewal frontier challenges are frozen")
        expected_conditions = len(self.capacities) * len(self.environment_order) * 2 + 2
        if len(self.study.conditions) != expected_conditions:
            raise ValueError("renewal frontier condition count differs from design")
        if not 0.0 < self.minimum_generation_8_gain < 1.0:
            raise ValueError("invalid renewal frontier effect threshold")
        if not 0.0 < self.minimum_renewal_contrast < 1.0:
            raise ValueError("invalid renewal contrast threshold")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RenewalFrontierSpec":
        result = cls(
            study=LocalStudySpec.from_dict(value["study"]),
            environment_order=tuple(value["environment_order"]),
            capacities=tuple(int(item) for item in value.get("capacities", (3, 5, 7, 10))),
            minimum_generation_8_gain=float(value.get("minimum_generation_8_gain", 0.15)),
            minimum_renewal_contrast=float(value.get("minimum_renewal_contrast", 0.10)),
            fallback_environment=str(value.get("fallback_environment", "mixed-moderate")),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class RenewalEvolutionSpec:
    """Paired joint evolution under renewal, memory, acute, and neutral objectives."""

    cohort_id: str
    master_seed: str
    initial_carrier: LocalCarrierGenome
    selected_noise: CopyNoiseSpec
    harsher_noise: CopyNoiseSpec
    selected_environment: str
    harsher_environment: str
    treatments: tuple[str, ...] = RENEWAL_TREATMENTS
    populations_per_treatment: int = 10
    population_size: int = 32
    generations: int = 32
    elite_count: int = 4
    tournament_size: int = 3
    training_replicates: int = 4
    genes: int = 10
    generation_cycles: int = 4
    horizon: int = 16
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    capacity_cost: float = 0.05
    coupling_cost: float = 0.025
    writing_cost: float = 0.025
    high_cost_multiplier: float = 2.0
    hard_capacity: int = 5
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid renewal evolution identity")
        self.initial_carrier.validate(self.genes)
        self.selected_noise.validate()
        self.harsher_noise.validate()
        if not self.selected_environment or not self.harsher_environment:
            raise ValueError("renewal evolution environments require labels")
        if self.treatments != RENEWAL_TREATMENTS:
            raise ValueError("renewal evolution treatments are frozen and ordered")
        values = (
            self.populations_per_treatment,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.training_replicates,
        )
        if min(values) < 1 or self.elite_count >= self.population_size:
            raise ValueError("invalid renewal evolution dimensions")
        if self.training_replicates < 4 or self.training_replicates % 2:
            raise ValueError("renewal training futures must be even and at least four")
        if self.genes != 10 or self.horizon < max(12, self.strict_run):
            raise ValueError("renewal evolution requires ten-gene Wagner tasks")
        if self.generation_cycles < 1 or not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid renewal development settings")
        costs = (self.capacity_cost, self.coupling_cost, self.writing_cost)
        if min(costs) < 0.0 or sum(costs) > 0.10 + 1e-12:
            raise ValueError("standard renewal resource cost must be at most 0.10")
        if self.high_cost_multiplier != 2.0:
            raise ValueError("high-cost treatment must exactly double the standard cost")
        if self.hard_capacity != 5:
            raise ValueError("engineering feasibility treatment is hard-capped at k=5")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid renewal evolution inference settings")

    @property
    def population_count(self) -> int:
        return len(self.treatments) * self.populations_per_treatment

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RenewalEvolutionSpec":
        fields = dict(value)
        fields["initial_carrier"] = LocalCarrierGenome(**fields["initial_carrier"])
        fields["selected_noise"] = CopyNoiseSpec(**fields["selected_noise"])
        fields["harsher_noise"] = CopyNoiseSpec(**fields["harsher_noise"])
        fields["treatments"] = tuple(fields.get("treatments", RENEWAL_TREATMENTS))
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class MutationNeighborhoodSpec:
    """Untouched high-precision and saturation-safe mutational audit."""

    cohort_id: str
    master_seed: str
    futures_per_history: int = 64
    checkpoint_generations: tuple[int, ...] = (0, 4, 8, 12, 16)
    challenges: tuple[str, ...] = ("forced_break", "release_only")
    parents_per_population: int = 6
    offspring_per_parent: int = 4
    retention_fraction: float = 0.70
    minimum_positive_population_fraction: float = 0.80
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid mutation-neighborhood identity")
        if self.futures_per_history < 4 or self.futures_per_history % 2:
            raise ValueError("mutation audit futures must be even and at least four")
        if self.checkpoint_generations != (0, 4, 8, 12, 16):
            raise ValueError("mutation audit checkpoints are frozen")
        if self.challenges != ("forced_break", "release_only"):
            raise ValueError("mutation audit challenges are frozen")
        if self.parents_per_population != 6 or self.offspring_per_parent != 4:
            raise ValueError("mutation neighborhood must sample six-by-four offspring")
        if not 0.0 < self.retention_fraction <= 1.0:
            raise ValueError("invalid mutation retention fraction")
        if not 0.0 < self.minimum_positive_population_fraction <= 1.0:
            raise ValueError("invalid positive-population threshold")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid mutation inference settings")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MutationNeighborhoodSpec":
        fields = dict(value)
        fields["checkpoint_generations"] = tuple(fields["checkpoint_generations"])
        fields["challenges"] = tuple(fields["challenges"])
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class RenewalCampaignSpec:
    cohort_id: str
    master_seed: str
    frontier: RenewalFrontierSpec
    evolution_template: RenewalEvolutionSpec
    mutation_audit: MutationNeighborhoodSpec
    maximum_workers: int = 4
    hard_wall_seconds: int = 21_600
    soft_wall_seconds: int = 20_400
    projected_wall_seconds: int = 19_800
    stage_reservations_seconds: tuple[int, ...] = (2700, 12_600, 4200, 2100)

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid renewal campaign identity")
        self.frontier.validate()
        self.evolution_template.validate()
        self.mutation_audit.validate()
        if self.maximum_workers != 4:
            raise ValueError("renewal campaign is capped at four workers")
        if self.hard_wall_seconds != 21_600:
            raise ValueError("renewal campaign must retain its cumulative six-hour boundary")
        if not 0 < self.soft_wall_seconds < self.hard_wall_seconds:
            raise ValueError("renewal soft wall boundary must precede the hard boundary")
        if self.projected_wall_seconds > self.soft_wall_seconds:
            raise ValueError("renewal campaign projection exceeds its soft wall budget")
        if sum(self.stage_reservations_seconds) != self.hard_wall_seconds:
            raise ValueError("renewal stage reservations must exactly cover six hours")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RenewalCampaignSpec":
        result = cls(
            cohort_id=str(value["cohort_id"]),
            master_seed=str(value["master_seed"]),
            frontier=RenewalFrontierSpec.from_dict(value["frontier"]),
            evolution_template=RenewalEvolutionSpec.from_dict(value["evolution_template"]),
            mutation_audit=MutationNeighborhoodSpec.from_dict(value["mutation_audit"]),
            maximum_workers=int(value.get("maximum_workers", 4)),
            hard_wall_seconds=int(value.get("hard_wall_seconds", 21_600)),
            soft_wall_seconds=int(value.get("soft_wall_seconds", 20_400)),
            projected_wall_seconds=int(value.get("projected_wall_seconds", 19_800)),
            stage_reservations_seconds=tuple(
                int(item)
                for item in value.get(
                    "stage_reservations_seconds", (2700, 12_600, 4200, 2100)
                )
            ),
        )
        result.validate()
        return result
