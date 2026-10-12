"""Frozen contract for Wagner PH Interpreter Resilience v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import direct_prediction_spec


RESILIENCE_FORMAT = "gre-wagner-ph-interpreter-resilience-v1"
RESILIENCE_ARMS = (
    "cvar8_reset",
    "lineage4_reset",
    "individual_repair",
    "lineage4_repair",
    "individual_triplicate",
    "lineage4_triplicate",
)
REFERENCE_ARMS = ("individual_reset", "offspring8_reset")
CANDIDATE_ARMS = RESILIENCE_ARMS
DIAGNOSTIC_CONDITIONS = (
    "ordinary_reset",
    "repair_03",
    "repair_06",
    "repair_09",
    "triplicate_independent",
    "triplicate_concerted",
)


def arm_settings(name: str) -> dict[str, Any]:
    if name not in RESILIENCE_ARMS + REFERENCE_ARMS:
        raise ValueError(f"unknown interpreter-resilience arm: {name}")
    if name == "offspring8_reset":
        selection = "mean8"
    elif name.startswith("cvar8_"):
        selection = "cvar8"
    elif name.startswith("lineage4_"):
        selection = "lineage4_cvar50"
    else:
        selection = "individual"
    architecture = (
        "repair" if name.endswith("_repair")
        else "triplicate" if name.endswith("_triplicate")
        else "single"
    )
    return {"selection_mode": selection, "architecture": architecture}


def evidence_tier(name: str) -> str:
    architecture = arm_settings(name)["architecture"]
    return {
        "single": "ordinary_full_reset",
        "repair": "engineered_global_repair",
        "triplicate": "engineered_regulatory_redundancy",
    }[architecture]


def architecture_control(name: str) -> str:
    architecture = arm_settings(name)["architecture"]
    return {
        "single": "individual_reset",
        "repair": "individual_repair",
        "triplicate": "individual_triplicate",
    }[architecture]


@dataclass(frozen=True)
class ResilienceSpec:
    cohort_id: str
    master_seed: str
    diagnostic_seed: str
    audit_seed: str
    pedigree_seed: str
    confirmation_seed: str
    task_count: int = 12
    confirmation_task_count: int = 16
    population_size: int = 16
    generations: int = 24
    confirmation_burnin_generations: int = 30
    elite_count: int = 2
    tournament_size: int = 3
    predictive_persistence: float = 0.9
    repair_maximum: float = 0.9
    repair_mutation_sigma: float = 0.05
    repair_cost: float = 0.04
    triplicate_cost: float = 0.04
    diagnostic_roots_per_task: int = 2
    diagnostic_chains_per_root: int = 16
    diagnostic_futures_per_history: int = 8
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)
    audit_cue_fractions: tuple[float, ...] = (0.0, 0.25)
    pedigree_roots_per_task: int = 2
    pedigree_lineages_per_root: int = 4
    pedigree_depths: tuple[int, ...] = (1, 2, 4)
    pedigree_futures_per_history: int = 16
    retention_fraction: float = 0.70
    retention_mean_gate: float = 0.70
    retention_lower_gate: float = 0.50
    distance_two_gate: float = 0.55
    distance_four_gate: float = 0.35
    information_advantage_gate: float = 0.08
    distance_one_advantage_gate: float = 0.30
    distance_four_advantage_gate: float = 0.20
    mechanism_off_gate: float = 0.15
    performance_loss_gate: float = 0.05
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    maximum_workers: int = 4
    hard_wall_seconds: int = 21_600
    soft_wall_seconds: int = 20_700
    stage_reservations_seconds: tuple[int, ...] = (1800, 7800, 3300, 300, 4200, 2700, 600)
    arms: tuple[str, ...] = RESILIENCE_ARMS
    diagnostic_conditions: tuple[str, ...] = DIAGNOSTIC_CONDITIONS
    exploratory: bool = True
    evidence_strategy: str = "develop_then_confirm"

    def validate(self) -> None:
        seeds = (self.master_seed, self.diagnostic_seed, self.audit_seed, self.pedigree_seed, self.confirmation_seed)
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != 5:
            raise ValueError("resilience identities and seed families must be distinct")
        if self.arms != RESILIENCE_ARMS or self.diagnostic_conditions != DIAGNOSTIC_CONDITIONS:
            raise ValueError("resilience arms and diagnostic conditions are frozen")
        if self.population_size not in {4, 16} or self.generations < 1 or self.population_size <= self.elite_count:
            raise ValueError("invalid resilience evolution dimensions")
        if self.task_count != 1 and self.population_size != 16:
            raise ValueError("production resilience populations are frozen at 16")
        if self.pedigree_depths != (1, 2, 4):
            raise ValueError("resilience pedigree distances are frozen")
        if self.maximum_workers != 4 or (self.hard_wall_seconds, self.soft_wall_seconds) != (21600, 20700):
            raise ValueError("resilience runtime contract changed")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("resilience reservations must cover the soft wall")
        if not 0.0 < self.repair_maximum < 1.0 or min(self.repair_mutation_sigma, self.repair_cost, self.triplicate_cost) <= 0.0:
            raise ValueError("invalid repair or triplication contract")
        if any(value % 2 for value in (self.diagnostic_futures_per_history, self.audit_futures_per_history, self.pedigree_futures_per_history)):
            raise ValueError("paired future counts must be even")
        if self.evidence_strategy != "develop_then_confirm":
            raise ValueError("development and confirmation must remain separate")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResilienceSpec":
        payload = dict(value)
        for field in ("arms", "diagnostic_conditions", "audit_persistence", "audit_cue_fractions", "pedigree_depths", "stage_reservations_seconds"):
            payload[field] = tuple(payload[field])
        result = cls(**payload)
        result.validate()
        return result

    def kernel(self, *, confirmation: bool = False) -> CooptionSpec:
        base = direct_prediction_spec(smoke=self.task_count == 1).cooption_spec()
        tasks = self.confirmation_task_count if confirmation else self.task_count
        result = replace(
            base,
            cohort_id=self.cohort_id + ("-confirmation" if confirmation else ""),
            master_seed=self.confirmation_seed if confirmation else self.master_seed,
            confirmation_seed=canonical_digest((self.confirmation_seed, "sealed-reserve")),
            evolution_tasks=tasks,
            confirmation_tasks=max(tasks, base.confirmation_tasks),
            population_size=self.population_size,
            generations=self.generations,
            elite_count=self.elite_count,
            tournament_size=self.tournament_size,
            audit_futures_per_history=self.audit_futures_per_history,
            audit_persistence=self.audit_persistence,
            cue_fractions=self.audit_cue_fractions,
            bootstrap_repetitions=self.bootstrap_repetitions,
        )
        result.validate()
        return result

    def smoke(self) -> "ResilienceSpec":
        result = replace(
            self,
            cohort_id=self.cohort_id + "-smoke",
            master_seed=canonical_digest((self.master_seed, "smoke")),
            diagnostic_seed=canonical_digest((self.diagnostic_seed, "smoke")),
            audit_seed=canonical_digest((self.audit_seed, "smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "smoke")),
            confirmation_seed=canonical_digest((self.confirmation_seed, "smoke")),
            task_count=1,
            confirmation_task_count=2,
            population_size=4,
            generations=2,
            confirmation_burnin_generations=2,
            elite_count=1,
            diagnostic_roots_per_task=1,
            diagnostic_chains_per_root=2,
            diagnostic_futures_per_history=4,
            audit_futures_per_history=4,
            pedigree_roots_per_task=1,
            pedigree_lineages_per_root=1,
            pedigree_futures_per_history=4,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result


MASTER_SEED = canonical_digest("wagner-ph-interpreter-resilience-v1-development-2026-08-30")
DIAGNOSTIC_SEED = canonical_digest("wagner-ph-interpreter-resilience-v1-diagnosis-2026-08-30")
AUDIT_SEED = canonical_digest("wagner-ph-interpreter-resilience-v1-audit-2026-08-30")
PEDIGREE_SEED = canonical_digest("wagner-ph-interpreter-resilience-v1-pedigree-2026-08-30")
CONFIRMATION_SEED = canonical_digest("wagner-ph-interpreter-resilience-v1-confirmation-2026-08-30")


def resilience_spec(*, smoke: bool = False) -> ResilienceSpec:
    result = ResilienceSpec(
        cohort_id="wagner-ph-interpreter-resilience-v1",
        master_seed=MASTER_SEED,
        diagnostic_seed=DIAGNOSTIC_SEED,
        audit_seed=AUDIT_SEED,
        pedigree_seed=PEDIGREE_SEED,
        confirmation_seed=CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result
