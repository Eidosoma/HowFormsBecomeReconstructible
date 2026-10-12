"""Frozen contract for the direct-prediction origin experiment."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_protocols import wagner_ph_cooption_spec


DIRECT_CAMPAIGN_FORMAT = "gre-wagner-ph-direct-prediction-campaign-v1"
DIRECT_ANALYSIS_FORMAT = "gre-wagner-ph-direct-prediction-analysis-v1"
DIRECT_EMERGENCE_FORMAT = "gre-wagner-ph-direct-prediction-emergence-v1"
DIRECT_PEDIGREE_FORMAT = "gre-wagner-ph-direct-prediction-pedigree-v1"

DIRECT_VARIANTS = (
    "rho50_full",
    "rho75_full",
    "rho90_full",
    "rho100_full",
    "rho90_inert",
    "rho90_writer_only",
    "rho90_reader_only",
    "rho90_fixed_k1",
    "rho90_cost2",
)


def variant_settings(name: str) -> dict[str, Any]:
    if name not in DIRECT_VARIANTS:
        raise ValueError(f"unknown direct-prediction variant: {name}")
    persistence = {
        "rho50_full": 0.50,
        "rho75_full": 0.75,
        "rho90_full": 0.90,
        "rho100_full": 1.00,
    }.get(name, 0.90)
    constraint = {
        "rho90_inert": "inert",
        "rho90_writer_only": "writer_only",
        "rho90_reader_only": "reader_only",
        "rho90_fixed_k1": "fixed_k1",
    }.get(name)
    return {
        "predictive_persistence": persistence,
        "carrier_constraint": constraint,
        "resource_cost_multiplier": 2.0 if name == "rho90_cost2" else 1.0,
    }


@dataclass(frozen=True)
class DirectPredictionSpec:
    """Fresh-seed, four-hour exploration of direct PH origin."""

    cohort_id: str
    master_seed: str
    emergence_seed: str
    pedigree_seed: str
    unused_confirmation_seed: str
    parent_cohort_id: str = "wagner-ph-cooption-v1"
    variants: tuple[str, ...] = DIRECT_VARIANTS
    task_count: int = 12
    population_size: int = 16
    generations: int = 30
    training_panel_size: int = 16
    training_panels_per_generation: int = 4
    validation_panels: int = 4
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.75, 0.9, 1.0)
    lineage_generations: int = 16
    lineage_checkpoints: tuple[int, ...] = (1, 8, 16)
    emergence_generations: tuple[int, ...] = (0, 10, 20, 30)
    emergence_futures_per_history: int = 8
    pedigree_parents_per_task: int = 2
    pedigree_children_per_parent: int = 2
    pedigree_grandchildren_per_child: int = 2
    pedigree_retention_fraction: float = 0.70
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    contrast_gate: float = 0.10
    maximum_workers: int = 4
    hard_wall_seconds: int = 14_400
    soft_wall_seconds: int = 13_500
    stage_reservations_seconds: tuple[int, ...] = (300, 6000, 3900, 1500, 1200, 600)
    exploratory: bool = True

    def validate(self) -> None:
        seeds = (
            self.master_seed,
            self.emergence_seed,
            self.pedigree_seed,
            self.unused_confirmation_seed,
        )
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != 4:
            raise ValueError("direct-prediction identities and seed families must be distinct")
        if self.variants != DIRECT_VARIANTS:
            raise ValueError("direct-prediction variants are frozen and ordered")
        dimensions = (
            self.task_count,
            self.population_size,
            self.generations,
            self.training_panel_size,
            self.training_panels_per_generation,
            self.validation_panels,
            self.audit_futures_per_history,
            self.lineage_generations,
            self.emergence_futures_per_history,
            self.pedigree_parents_per_task,
            self.pedigree_children_per_parent,
            self.pedigree_grandchildren_per_child,
            self.bootstrap_repetitions,
        )
        if min(dimensions) < 1:
            raise ValueError("direct-prediction dimensions must be positive")
        if self.population_size < 2 or self.training_panel_size % self.training_panels_per_generation:
            raise ValueError("invalid direct-prediction population or panel rotation")
        if self.audit_futures_per_history % 2 or self.emergence_futures_per_history % 2:
            raise ValueError("paired future counts must be even")
        if tuple(sorted(set(self.audit_persistence))) != self.audit_persistence:
            raise ValueError("audit persistences must be increasing and unique")
        if not {0.0, 0.5, 0.75, 0.9, 1.0} <= set(self.audit_persistence):
            raise ValueError("audit must contain the complete predictability gradient")
        if self.lineage_checkpoints[-1] != self.lineage_generations:
            raise ValueError("lineage checkpoints must end at the lineage horizon")
        if tuple(sorted(set(self.emergence_generations))) != self.emergence_generations:
            raise ValueError("emergence generations must be increasing and unique")
        if self.emergence_generations[0] != 0 or self.emergence_generations[-1] != self.generations:
            raise ValueError("emergence assay must span founder to final generation")
        if not 0.0 < self.pedigree_retention_fraction <= 1.0:
            raise ValueError("invalid pedigree retention fraction")
        if not 0.0 < self.interval_level < 1.0 or self.contrast_gate < 0.0:
            raise ValueError("invalid prospective inference settings")
        if self.maximum_workers != 4:
            raise ValueError("direct-prediction campaign is capped at four CPU workers")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (14_400, 13_500):
            raise ValueError("direct-prediction campaign is frozen at four hours")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("stage reservations must cover the scientific soft boundary")

    @property
    def population_count(self) -> int:
        return len(self.variants) * self.task_count

    @property
    def descendant_count(self) -> int:
        return self.task_count * self.pedigree_parents_per_task * (
            self.pedigree_children_per_parent
            + self.pedigree_children_per_parent * self.pedigree_grandchildren_per_child
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DirectPredictionSpec":
        fields = dict(value)
        for field in (
            "variants",
            "audit_persistence",
            "lineage_checkpoints",
            "emergence_generations",
            "stage_reservations_seconds",
        ):
            fields[field] = tuple(fields[field])
        result = cls(**fields)
        result.validate()
        return result

    def smoke(self) -> "DirectPredictionSpec":
        result = replace(
            self,
            cohort_id=f"{self.cohort_id}-smoke",
            master_seed=canonical_digest((self.master_seed, "software-smoke")),
            emergence_seed=canonical_digest((self.emergence_seed, "software-smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "software-smoke")),
            unused_confirmation_seed=canonical_digest(
                (self.unused_confirmation_seed, "software-smoke")
            ),
            task_count=1,
            population_size=4,
            generations=2,
            training_panel_size=4,
            training_panels_per_generation=2,
            validation_panels=2,
            audit_futures_per_history=4,
            lineage_generations=2,
            lineage_checkpoints=(1, 2),
            emergence_generations=(0, 2),
            emergence_futures_per_history=4,
            pedigree_parents_per_task=1,
            pedigree_children_per_parent=1,
            pedigree_grandchildren_per_child=1,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result

    def cooption_spec(self) -> CooptionSpec:
        """Return the frozen simulation kernel contract used by every paired arm."""

        base = wagner_ph_cooption_spec()
        smoke = self.generations <= 2
        result = replace(
            base,
            cohort_id=self.cohort_id,
            master_seed=self.master_seed,
            confirmation_seed=self.unused_confirmation_seed,
            evolution_tasks=self.task_count,
            population_size=self.population_size,
            generations=self.generations,
            cooption_switch_generation=1 if smoke else 15,
            elite_count=1 if smoke else base.elite_count,
            training_panel_size=self.training_panel_size,
            training_panels_per_generation=self.training_panels_per_generation,
            training_episode_generations=2 if smoke else base.training_episode_generations,
            validation_panels=self.validation_panels,
            audit_futures_per_history=self.audit_futures_per_history,
            audit_persistence=self.audit_persistence,
            lineage_generations=self.lineage_generations,
            checkpoints=self.lineage_checkpoints,
            horizon=8 if smoke else base.horizon,
            strict_run=4 if smoke else base.strict_run,
            stable_run=2 if smoke else base.stable_run,
            bootstrap_repetitions=self.bootstrap_repetitions,
            confirmation_tasks=self.task_count,
        )
        result.validate()
        return result


DIRECT_MASTER_SEED = canonical_digest(
    "wagner-ph-direct-prediction-v1-production-2026-08-28"
)
DIRECT_EMERGENCE_SEED = canonical_digest(
    "wagner-ph-direct-prediction-v1-untouched-emergence-2026-08-28"
)
DIRECT_PEDIGREE_SEED = canonical_digest(
    "wagner-ph-direct-prediction-v1-untouched-pedigree-2026-08-28"
)
DIRECT_UNUSED_CONFIRMATION_SEED = canonical_digest(
    "wagner-ph-direct-prediction-v1-unspent-confirmation-2026-08-28"
)


def direct_prediction_spec(*, smoke: bool = False) -> DirectPredictionSpec:
    result = DirectPredictionSpec(
        cohort_id="wagner-ph-direct-prediction-v1",
        master_seed=DIRECT_MASTER_SEED,
        emergence_seed=DIRECT_EMERGENCE_SEED,
        pedigree_seed=DIRECT_PEDIGREE_SEED,
        unused_confirmation_seed=DIRECT_UNUSED_CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result
