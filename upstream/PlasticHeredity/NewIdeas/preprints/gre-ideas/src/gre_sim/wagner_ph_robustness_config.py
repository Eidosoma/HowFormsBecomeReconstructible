"""Frozen contract for the Wagner PH mutation-autopsy/robustness campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import direct_prediction_spec


ROBUSTNESS_CAMPAIGN_FORMAT = "gre-wagner-ph-robustness-ratchet-campaign-v1"
ROBUSTNESS_AUTOPSY_FORMAT = "gre-wagner-ph-mutation-autopsy-v1"
ROBUSTNESS_EVOLUTION_FORMAT = "gre-wagner-ph-robustness-evolution-v1"
ROBUSTNESS_AUDIT_FORMAT = "gre-wagner-ph-robustness-audit-v1"
ROBUSTNESS_PEDIGREE_FORMAT = "gre-wagner-ph-robustness-pedigree-v1"
ROBUSTNESS_ANALYSIS_FORMAT = "gre-wagner-ph-robustness-analysis-v1"

ROBUSTNESS_ARMS = (
    "individual_independent",
    "offspring_independent",
    "individual_protected",
    "offspring_protected",
    "individual_linked",
    "offspring_linked",
    "offspring_fixed_k1",
    "offspring_inert",
)

AUTOPSY_COMPONENTS = (
    "grn_weights",
    "writer_reader_strengths",
    "storage_layout",
    "copy_dynamics",
)

AUTOPSY_INTERVENTIONS = (
    "natural",
    "independent_history",
    "opposite_history",
    "zero",
    "reader_off",
    "renewal_off",
)


def arm_settings(name: str) -> dict[str, Any]:
    if name not in ROBUSTNESS_ARMS:
        raise ValueError(f"unknown robustness arm: {name}")
    return {
        "selection_mode": "offspring" if name.startswith("offspring_") else "individual",
        "mutation_architecture": "linked" if name.endswith("linked") else "independent",
        "carrier_mutation_multiplier": 0.25 if name.endswith("protected") else 1.0,
        "carrier_constraint": (
            "fixed_k1" if name.endswith("fixed_k1") else "inert" if name.endswith("inert") else None
        ),
    }


@dataclass(frozen=True)
class RobustnessSpec:
    """Four-hour, CPU-only development experiment on the sealed 12-task cohort."""

    cohort_id: str
    master_seed: str
    autopsy_seed: str
    audit_seed: str
    pedigree_seed: str
    unused_confirmation_seed: str
    parent_cohort_id: str = "wagner-ph-direct-prediction-v1"
    parent_variant: str = "rho90_full"
    arms: tuple[str, ...] = ROBUSTNESS_ARMS
    autopsy_components: tuple[str, ...] = AUTOPSY_COMPONENTS
    autopsy_interventions: tuple[str, ...] = AUTOPSY_INTERVENTIONS
    autopsy_persistence: tuple[float, ...] = (0.0, 0.9)
    autopsy_futures_per_history: int = 4
    task_count: int = 12
    population_size: int = 16
    generations: int = 24
    elite_count: int = 2
    tournament_size: int = 3
    virtual_offspring: int = 3
    predictive_persistence: float = 0.9
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)
    audit_cue_fractions: tuple[float, ...] = (0.0, 0.25)
    pedigree_parents_per_task: int = 2
    pedigree_children_per_parent: int = 2
    pedigree_grandchildren_per_child: int = 2
    pedigree_futures_per_history: int = 16
    retention_fraction: float = 0.70
    retention_mean_gate: float = 0.70
    retention_lower_gate: float = 0.50
    information_advantage_gate: float = 0.08
    retention_advantage_gate: float = 0.30
    performance_loss_gate: float = 0.05
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    maximum_workers: int = 4
    hard_wall_seconds: int = 14_400
    soft_wall_seconds: int = 13_500
    stage_reservations_seconds: tuple[int, ...] = (1800, 7500, 2400, 1500, 300)
    exploratory: bool = True
    evidence_strategy: str = "develop_then_confirm"

    def validate(self) -> None:
        seeds = (
            self.master_seed,
            self.autopsy_seed,
            self.audit_seed,
            self.pedigree_seed,
            self.unused_confirmation_seed,
        )
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != len(seeds):
            raise ValueError("robustness identities and seed families must be distinct")
        if self.arms != ROBUSTNESS_ARMS:
            raise ValueError("robustness arms are frozen and ordered")
        if self.autopsy_components != AUTOPSY_COMPONENTS:
            raise ValueError("autopsy components are frozen and ordered")
        if self.autopsy_interventions != AUTOPSY_INTERVENTIONS:
            raise ValueError("autopsy interventions are frozen and ordered")
        dimensions = (
            self.autopsy_futures_per_history,
            self.task_count,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.virtual_offspring,
            self.audit_futures_per_history,
            self.pedigree_parents_per_task,
            self.pedigree_children_per_parent,
            self.pedigree_grandchildren_per_child,
            self.pedigree_futures_per_history,
            self.bootstrap_repetitions,
        )
        if min(dimensions) < 1 or self.population_size <= self.elite_count:
            raise ValueError("invalid robustness dimensions")
        if any(value % 2 for value in (
            self.autopsy_futures_per_history,
            self.audit_futures_per_history,
            self.pedigree_futures_per_history,
        )):
            raise ValueError("paired future counts must be even")
        for grid in (self.autopsy_persistence, self.audit_persistence, self.audit_cue_fractions):
            if tuple(sorted(set(grid))) != grid or min(grid) < 0.0 or max(grid) > 1.0:
                raise ValueError("ecology grids must be ordered and unique in [0, 1]")
        if self.autopsy_persistence != (0.0, 0.9):
            raise ValueError("autopsy predictability contrast is frozen")
        if self.audit_persistence != (0.0, 0.5, 0.9, 1.0):
            raise ValueError("audit predictability gradient is frozen")
        if self.audit_cue_fractions != (0.0, 0.25):
            raise ValueError("audit pre-cue primary and cue sensitivity are frozen")
        if not 0.0 <= self.predictive_persistence <= 1.0:
            raise ValueError("invalid predictive persistence")
        if not 0.0 < self.retention_fraction <= 1.0:
            raise ValueError("invalid retention fraction")
        if not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid interval level")
        if min(
            self.retention_mean_gate,
            self.retention_lower_gate,
            self.information_advantage_gate,
            self.retention_advantage_gate,
            self.performance_loss_gate,
        ) < 0.0:
            raise ValueError("decision gates cannot be negative")
        if self.maximum_workers != 4:
            raise ValueError("robustness campaign is capped at four CPU workers")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (14_400, 13_500):
            raise ValueError("robustness campaign is frozen at four hours")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("stage reservations must cover the scientific soft boundary")
        if self.evidence_strategy != "develop_then_confirm":
            raise ValueError("fresh confirmation tasks must remain reserved")

    @property
    def population_count(self) -> int:
        return len(self.arms) * self.task_count

    @property
    def pedigree_descendant_count(self) -> int:
        return self.population_count * self.pedigree_parents_per_task * (
            self.pedigree_children_per_parent
            + self.pedigree_children_per_parent * self.pedigree_grandchildren_per_child
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RobustnessSpec":
        fields = dict(value)
        for name in (
            "arms",
            "autopsy_components",
            "autopsy_interventions",
            "autopsy_persistence",
            "audit_persistence",
            "audit_cue_fractions",
            "stage_reservations_seconds",
        ):
            fields[name] = tuple(fields[name])
        result = cls(**fields)
        result.validate()
        return result

    def kernel(self) -> CooptionSpec:
        direct = direct_prediction_spec(smoke=self.task_count == 1)
        kernel = direct.cooption_spec()
        result = replace(
            kernel,
            cohort_id=self.cohort_id,
            master_seed=self.master_seed,
            confirmation_seed=self.unused_confirmation_seed,
            evolution_tasks=self.task_count,
            population_size=self.population_size,
            audit_futures_per_history=self.audit_futures_per_history,
            audit_persistence=self.audit_persistence,
            cue_fractions=self.audit_cue_fractions,
            bootstrap_repetitions=self.bootstrap_repetitions,
        )
        result.validate()
        return result

    def smoke(self) -> "RobustnessSpec":
        result = replace(
            self,
            cohort_id=f"{self.cohort_id}-smoke",
            master_seed=canonical_digest((self.master_seed, "software-smoke")),
            autopsy_seed=canonical_digest((self.autopsy_seed, "software-smoke")),
            audit_seed=canonical_digest((self.audit_seed, "software-smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "software-smoke")),
            unused_confirmation_seed=canonical_digest(
                (self.unused_confirmation_seed, "software-smoke")
            ),
            task_count=1,
            population_size=4,
            generations=2,
            elite_count=1,
            virtual_offspring=1,
            audit_futures_per_history=4,
            pedigree_parents_per_task=1,
            pedigree_children_per_parent=1,
            pedigree_grandchildren_per_child=1,
            pedigree_futures_per_history=4,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result


ROBUSTNESS_MASTER_SEED = canonical_digest(
    "wagner-ph-robustness-ratchet-v1-development-2026-08-29"
)
ROBUSTNESS_AUTOPSY_SEED = canonical_digest(
    "wagner-ph-mutation-autopsy-v1-development-2026-08-29"
)
ROBUSTNESS_AUDIT_SEED = canonical_digest(
    "wagner-ph-robustness-ratchet-v1-audit-2026-08-29"
)
ROBUSTNESS_PEDIGREE_SEED = canonical_digest(
    "wagner-ph-robustness-ratchet-v1-pedigree-2026-08-29"
)
ROBUSTNESS_UNUSED_CONFIRMATION_SEED = canonical_digest(
    "wagner-ph-robustness-ratchet-v1-unused-confirmation-2026-08-29"
)


def robustness_spec(*, smoke: bool = False) -> RobustnessSpec:
    result = RobustnessSpec(
        cohort_id="wagner-ph-robustness-ratchet-v1",
        master_seed=ROBUSTNESS_MASTER_SEED,
        autopsy_seed=ROBUSTNESS_AUTOPSY_SEED,
        audit_seed=ROBUSTNESS_AUDIT_SEED,
        pedigree_seed=ROBUSTNESS_PEDIGREE_SEED,
        unused_confirmation_seed=ROBUSTNESS_UNUSED_CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result
