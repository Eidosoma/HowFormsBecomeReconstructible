"""Immutable contracts for the Wagner PH origin/discrimination campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .local_ph_config import CopyNoiseSpec, LocalCarrierGenome


ORIGIN_CAMPAIGN_FORMAT = "gre-wagner-ph-origin-campaign-v1"
ORIGIN_SCREEN_FORMAT = "gre-wagner-ph-origin-screen-v1"
ORIGIN_EVOLUTION_FORMAT = "gre-wagner-ph-origin-evolution-v1"
ORIGIN_AUDIT_FORMAT = "gre-wagner-ph-origin-audit-v1"

ORIGIN_TREATMENTS = (
    "dormant_explicit_renewal",
    "dormant_permissive_performance",
    "dormant_passive_locked",
    "weak_explicit_renewal",
    "weak_permissive_performance",
    "weak_passive_locked",
)

EXPLICIT_TREATMENTS = (
    "dormant_explicit_renewal",
    "weak_explicit_renewal",
)

ORIGIN_INTERVENTION_SCHEDULES = (
    "intact",
    "founder_write_off",
    "reader_off",
    "renewal_off",
    "renewal_block_g1_g4",
    "renewal_block_g9_g12",
    "shuffle",
    "erase_g6",
    "erase_g6_rescue_g7",
    "opposite_history_transplant",
)


def treatment_scaffold(treatment: str) -> str:
    if treatment not in ORIGIN_TREATMENTS:
        raise ValueError(f"unknown origin treatment: {treatment}")
    return "dormant" if treatment.startswith("dormant_") else "weak"


def treatment_objective(treatment: str) -> str:
    if treatment.endswith("explicit_renewal"):
        return "explicit_renewal"
    if treatment.endswith("permissive_performance"):
        return "permissive_performance"
    if treatment.endswith("passive_locked"):
        return "passive_locked"
    raise ValueError(f"unknown origin treatment: {treatment}")


@dataclass(frozen=True)
class OriginScreenSpec:
    """Fresh adaptive screen whose mechanical choice is frozen before evolution."""

    cohort_id: str
    master_seed: str
    environments: tuple[CopyNoiseSpec, ...]
    parent_populations: int = 6
    futures_per_history: int = 32
    checkpoint_generations: tuple[int, ...] = (0, 8, 12)
    challenges: tuple[str, ...] = ("forced_break", "release_only")
    minimum_intact_g8: float = 0.25
    minimum_renewal_contrast: float = 0.10
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid origin screen identity")
        if len(self.environments) != 8:
            raise ValueError("origin screen requires eight ordered environments")
        names = [value.name for value in self.environments]
        if len(set(names)) != len(names):
            raise ValueError("origin screen environments must be uniquely named")
        for value in self.environments:
            value.validate()
        if self.parent_populations != 6:
            raise ValueError("origin screen requires six sealed-parent populations")
        if self.futures_per_history < 4 or self.futures_per_history % 2:
            raise ValueError("origin screen futures must be even and at least four")
        if self.checkpoint_generations != (0, 8, 12):
            raise ValueError("origin screen checkpoints are frozen")
        if self.challenges != ("forced_break", "release_only"):
            raise ValueError("origin screen challenges are frozen")
        if not 0.0 < self.minimum_intact_g8 < 1.0:
            raise ValueError("invalid intact-g8 screen threshold")
        if not 0.0 < self.minimum_renewal_contrast < 1.0:
            raise ValueError("invalid renewal screen threshold")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid origin screen inference")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OriginScreenSpec":
        fields = dict(value)
        fields["environments"] = tuple(
            CopyNoiseSpec(**item) for item in fields["environments"]
        )
        fields["checkpoint_generations"] = tuple(fields["checkpoint_generations"])
        fields["challenges"] = tuple(fields["challenges"])
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class OriginEvolutionSpec:
    """Paired factorial evolution from dormant and weak carrier scaffolds."""

    cohort_id: str
    master_seed: str
    scaffolds: tuple[LocalCarrierGenome, ...]
    selected_noise: CopyNoiseSpec
    harsher_noise: CopyNoiseSpec
    selected_environment: str
    harsher_environment: str
    treatments: tuple[str, ...] = ORIGIN_TREATMENTS
    populations_per_treatment: int = 6
    population_size: int = 24
    generations: int = 28
    elite_count: int = 3
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
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid origin evolution identity")
        if tuple(value.name for value in self.scaffolds) != (
            "origin-dormant",
            "origin-weak",
        ):
            raise ValueError("origin scaffold identities are frozen")
        for value in self.scaffolds:
            value.validate(self.genes)
        dormant, weak = self.scaffolds
        if (dormant.write_rate, dormant.coupling) != (0.0, 0.0):
            raise ValueError("dormant origin scaffold must have writer and reader off")
        if (weak.write_rate, weak.coupling) != (0.10, 0.10):
            raise ValueError("weak origin scaffold is frozen at 0.10/0.10")
        self.selected_noise.validate()
        self.harsher_noise.validate()
        if self.treatments != ORIGIN_TREATMENTS:
            raise ValueError("origin treatments are frozen and ordered")
        if not self.selected_environment or not self.harsher_environment:
            raise ValueError("origin environments require labels")
        if min(
            self.populations_per_treatment,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.training_replicates,
        ) < 1:
            raise ValueError("invalid origin evolution dimensions")
        if self.elite_count >= self.population_size:
            raise ValueError("origin elite count must be smaller than population")
        if self.training_replicates < 4 or self.training_replicates % 2:
            raise ValueError("origin training futures must be even and at least four")
        if self.genes != 10 or self.horizon < max(12, self.strict_run):
            raise ValueError("origin evolution requires ten-gene Wagner tasks")
        if self.generation_cycles < 1:
            raise ValueError("origin generation cycles must be positive")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid origin expression noise")
        costs = (self.capacity_cost, self.coupling_cost, self.writing_cost)
        if min(costs) < 0.0 or sum(costs) > 0.10 + 1e-12:
            raise ValueError("origin carrier cost must be nonnegative and capped")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid origin evolution inference")

    @property
    def population_count(self) -> int:
        return len(self.treatments) * self.populations_per_treatment

    def scaffold(self, name: str) -> LocalCarrierGenome:
        return next(value for value in self.scaffolds if value.name == f"origin-{name}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OriginEvolutionSpec":
        fields = dict(value)
        fields["scaffolds"] = tuple(
            LocalCarrierGenome(**item) for item in fields["scaffolds"]
        )
        fields["selected_noise"] = CopyNoiseSpec(**fields["selected_noise"])
        fields["harsher_noise"] = CopyNoiseSpec(**fields["harsher_noise"])
        fields["treatments"] = tuple(fields.get("treatments", ORIGIN_TREATMENTS))
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class OriginAuditSpec:
    """Untouched causal, state-transplant, and two-generation pedigree audit."""

    cohort_id: str
    master_seed: str
    futures_per_history: int = 64
    checkpoint_generations: tuple[int, ...] = (0, 4, 8, 12, 16)
    challenges: tuple[str, ...] = ("forced_break", "release_only")
    schedules: tuple[str, ...] = ORIGIN_INTERVENTION_SCHEDULES
    parents_per_population: int = 4
    children_per_parent: int = 2
    grandchildren_per_child: int = 2
    retention_fraction: float = 0.70
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid origin audit identity")
        if self.futures_per_history < 4 or self.futures_per_history % 2:
            raise ValueError("origin audit futures must be even and at least four")
        if self.checkpoint_generations != (0, 4, 8, 12, 16):
            raise ValueError("origin audit checkpoints are frozen")
        if self.challenges != ("forced_break", "release_only"):
            raise ValueError("origin audit challenges are frozen")
        if self.schedules != ORIGIN_INTERVENTION_SCHEDULES:
            raise ValueError("origin causal schedules are frozen")
        if (
            self.parents_per_population,
            self.children_per_parent,
            self.grandchildren_per_child,
        ) != (4, 2, 2):
            raise ValueError("origin pedigree branching is frozen at four-by-two-by-two")
        if not 0.0 < self.retention_fraction <= 1.0:
            raise ValueError("invalid origin retention fraction")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid origin audit inference")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OriginAuditSpec":
        fields = dict(value)
        fields["checkpoint_generations"] = tuple(fields["checkpoint_generations"])
        fields["challenges"] = tuple(fields["challenges"])
        fields["schedules"] = tuple(fields["schedules"])
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class OriginCampaignSpec:
    cohort_id: str
    master_seed: str
    screen: OriginScreenSpec
    evolution_template: OriginEvolutionSpec
    audit: OriginAuditSpec
    maximum_workers: int = 4
    hard_wall_seconds: int = 14_400
    soft_wall_seconds: int = 13_500
    projected_wall_seconds: int = 12_600
    stage_reservations_seconds: tuple[int, ...] = (1200, 7200, 4800, 1200)

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid origin campaign identity")
        self.screen.validate()
        self.evolution_template.validate()
        self.audit.validate()
        if self.maximum_workers != 4:
            raise ValueError("origin campaign is capped at four CPU workers")
        if self.hard_wall_seconds != 14_400:
            raise ValueError("origin campaign must retain its four-hour hard wall")
        if self.soft_wall_seconds != 13_500:
            raise ValueError("origin campaign soft wall is frozen at 13,500 seconds")
        if self.projected_wall_seconds > self.soft_wall_seconds:
            raise ValueError("origin projection exceeds soft wall")
        if self.stage_reservations_seconds != (1200, 7200, 4800, 1200):
            raise ValueError("origin stage reservations are frozen")
        if sum(self.stage_reservations_seconds) != self.hard_wall_seconds:
            raise ValueError("origin stage reservations must cover exactly four hours")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OriginCampaignSpec":
        result = cls(
            cohort_id=str(value["cohort_id"]),
            master_seed=str(value["master_seed"]),
            screen=OriginScreenSpec.from_dict(value["screen"]),
            evolution_template=OriginEvolutionSpec.from_dict(
                value["evolution_template"]
            ),
            audit=OriginAuditSpec.from_dict(value["audit"]),
            maximum_workers=int(value.get("maximum_workers", 4)),
            hard_wall_seconds=int(value.get("hard_wall_seconds", 14_400)),
            soft_wall_seconds=int(value.get("soft_wall_seconds", 13_500)),
            projected_wall_seconds=int(value.get("projected_wall_seconds", 12_600)),
            stage_reservations_seconds=tuple(
                int(item)
                for item in value.get(
                    "stage_reservations_seconds", (1200, 7200, 4800, 1200)
                )
            ),
        )
        result.validate()
        return result
